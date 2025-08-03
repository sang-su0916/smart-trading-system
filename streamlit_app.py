# -*- coding: utf-8 -*-
"""
Streamlit Cloud용 간단한 알고리즘 트레이딩 대시보드
실시간 데이터 지원 (한국투자증권 API + yfinance 하이브리드)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
from streamlit_searchbox import st_searchbox
import requests
import json
import os
import time
from functools import wraps
import warnings
warnings.filterwarnings('ignore')

# pykrx 시도, 실패시 폴백
try:
    import pykrx.stock as stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

# 한국투자증권 API 클라이언트
class KISClient:
    """한국투자증권 API 클라이언트"""
    
    def __init__(self):
        self.app_key = self._get_config('app_key')
        self.app_secret = self._get_config('app_secret')
        self.base_url = self._get_config('base_url', 'https://openapi.koreainvestment.com:9443')
        self.access_token = None
        self.last_token_time = None
        
    def _get_config(self, key, default=None):
        """환경 설정 로드 (로컬/클라우드 호환)"""
        try:
            # Streamlit Cloud의 경우
            return st.secrets.get("kis", {}).get(key, default)
        except:
            # 로컬 개발의 경우
            return os.getenv(f'KIS_{key.upper()}', default)
    
    def get_access_token(self):
        """OAuth 토큰 발급"""
        if not self.app_key or not self.app_secret:
            raise Exception("KIS API 설정이 없습니다. 환경 변수 또는 secrets를 확인하세요.")
            
        url = f"{self.base_url}/oauth2/tokenP"
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self.access_token = result['access_token']
                self.last_token_time = time.time()
                return self.access_token
            else:
                raise Exception(f"토큰 발급 실패: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"네트워크 오류: {str(e)}")
    
    def ensure_valid_token(self):
        """토큰 유효성 검사 및 자동 갱신"""
        # 토큰이 없거나 24시간 경과시 갱신
        if (not self.access_token or 
            not self.last_token_time or 
            time.time() - self.last_token_time > 23 * 3600):
            self.get_access_token()
    
    def get_headers(self, tr_id):
        """API 요청 헤더 생성"""
        self.ensure_valid_token()
        return {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }
    
    @st.cache_data(ttl=60)  # 1분 캐시
    def get_current_price(_self, symbol):
        """현재가 조회"""
        url = f"{_self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = _self.get_headers("FHKST01010100")
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                output = data['output']
                return {
                    'symbol': symbol,
                    'current_price': int(output['stck_prpr']),
                    'change': int(output['prdy_vrss']),
                    'change_rate': float(output['prdy_ctrt']),
                    'volume': int(output['acml_vol']),
                    'high': int(output['stck_hgpr']),
                    'low': int(output['stck_lwpr']),
                    'open': int(output['stck_oprc']),
                    'market_cap': int(output.get('mrkv', 0))
                }
            else:
                raise Exception(f"API 오류: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"네트워크 오류: {str(e)}")
    
    @st.cache_data(ttl=30)  # 30초 캐시
    def get_orderbook(_self, symbol):
        """실시간 호가창"""
        url = f"{_self.base_url}/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
        headers = _self.get_headers("FHKST01010200")
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                output = data['output1']
                
                # 매도호가 (10단계)
                ask_prices = [int(output[f'askp{i}']) for i in range(1, 11) if output[f'askp{i}']]
                ask_volumes = [int(output[f'askp_rsqn{i}']) for i in range(1, 11) if output[f'askp_rsqn{i}']]
                
                # 매수호가 (10단계)
                bid_prices = [int(output[f'bidp{i}']) for i in range(1, 11) if output[f'bidp{i}']]
                bid_volumes = [int(output[f'bidp_rsqn{i}']) for i in range(1, 11) if output[f'bidp_rsqn{i}']]
                
                return {
                    'ask_prices': ask_prices,
                    'ask_volumes': ask_volumes,
                    'bid_prices': bid_prices,
                    'bid_volumes': bid_volumes
                }
            else:
                raise Exception(f"API 오류: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"네트워크 오류: {str(e)}")

# 페이지 설정
st.set_page_config(
    page_title="🚀 Smart Trading Dashboard v4.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/sang-su0916/smart-trading-system',
        'Report a bug': 'https://github.com/sang-su0916/smart-trading-system/issues',
        'About': """
        # Smart Trading Dashboard v4.0
        실시간 한국 주식 데이터를 지원하는 AI 기반 종합 투자 분석 도구
        
        **주요 기능:**
        - 🔴 실시간 데이터 (한국투자증권 API)
        - 📋 실시간 호가창
        - ⚖️ 공정가치 분석 
        - 🏭 업종 비교 분석
        - 🚦 매매 신호 시스템
        - 📚 투자 교육 콘텐츠
        
        **⚠️ 교육용 도구입니다. 투자 결정은 신중히 하세요.**
        """
    }
)

def get_fallback_stocks():
    """pykrx 사용 불가시 주요 종목 리스트"""
    return {
        "삼성전자 (005930)": "005930.KS",
        "SK하이닉스 (000660)": "000660.KS", 
        "NAVER (035420)": "035420.KS",
        "카카오 (035720)": "035720.KS",
        "LG에너지솔루션 (373220)": "373220.KS",
        "삼성바이오로직스 (207940)": "207940.KS",
        "POSCO홀딩스 (005490)": "005490.KS",
        "LG화학 (051910)": "051910.KS",
        "현대차 (005380)": "005380.KS",
        "기아 (000270)": "000270.KS"
    }

def get_korean_stocks():
    """한국 주식 목록 가져오기"""
    if not PYKRX_AVAILABLE:
        return get_fallback_stocks()
    
    try:
        # KOSPI
        kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
        kospi_names = [stock.get_market_ticker_name(ticker) for ticker in kospi_tickers[:30]]
        
        all_stocks = {}
        for ticker, name in zip(kospi_tickers[:30], kospi_names):
            all_stocks["{} ({})".format(name, ticker)] = "{}.KS".format(ticker)
            
        return all_stocks
    except:
        return get_fallback_stocks()

def search_stocks(search_term):
    """종목 검색 함수"""
    if not search_term:
        return []
    
    all_stocks = get_korean_stocks()
    results = []
    
    for name, symbol in all_stocks.items():
        if search_term.lower() in name.lower():
            results.append(name)
            if len(results) >= 10:
                break
                
    return results

# KIS API 통합 함수들
def get_stock_data_with_kis(symbol):
    """KIS API를 활용한 실시간 주가 데이터 조회"""
    try:
        # 종목코드 변환 (.KS 제거)
        kis_symbol = symbol.replace('.KS', '') if symbol.endswith('.KS') else symbol
        
        kis = KISClient()
        
        # 실시간 현재가 조회
        current_data = kis.get_current_price(kis_symbol)
        
        # 호가창 데이터
        try:
            orderbook = kis.get_orderbook(kis_symbol)
        except:
            orderbook = None
        
        return {
            'current_data': current_data,
            'orderbook': orderbook,
            'data_source': 'KIS API (실시간)',
            'success': True
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'data_source': 'KIS API 실패',
            'success': False
        }

def get_stock_data_yfinance(symbol, period="1y"):
    """기존 yfinance를 사용한 데이터 조회"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data
    except Exception:
        return pd.DataFrame()

def get_stock_data_enhanced(symbol, period="1y"):
    """향상된 주가 데이터 조회 (KIS + yfinance 하이브리드)"""
    
    # 1. KIS API로 실시간 데이터 시도
    kis_result = get_stock_data_with_kis(symbol)
    
    # 2. yfinance로 차트 데이터 조회
    chart_data = get_stock_data_yfinance(symbol, period)
    
    if kis_result['success'] and not chart_data.empty:
        # KIS 실시간 + yfinance 차트 데이터 결합
        return {
            'chart_data': chart_data,
            'kis_data': kis_result,
            'data_source': 'KIS API + yfinance (하이브리드)',
            'has_realtime': True
        }
    elif not chart_data.empty:
        # yfinance만 사용
        return {
            'chart_data': chart_data,
            'kis_data': None,
            'data_source': 'yfinance (지연 데이터)',
            'has_realtime': False
        }
    else:
        # 모든 데이터 소스 실패
        return {
            'chart_data': pd.DataFrame(),
            'kis_data': None,
            'data_source': '데이터 없음',
            'has_realtime': False,
            'error': 'All data sources failed'
        }

def get_stock_data(symbol, period="1y"):
    """주가 데이터 가져오기 (호환성을 위한 래퍼)"""
    result = get_stock_data_enhanced(symbol, period)
    return result.get('chart_data', pd.DataFrame())

# 실시간 데이터 표시 함수들
def check_api_status():
    """API 상태 체크"""
    try:
        kis = KISClient()
        if kis.app_key and kis.app_secret:
            kis.get_access_token()
            st.success("✅ 한국투자증권 API 연결됨 (실시간 데이터)")
        else:
            st.warning("⚠️ 한국투자증권 API 설정이 없습니다 (지연 데이터 사용)")
    except Exception as e:
        st.warning("⚠️ 실시간 API 연결 실패: {} (지연 데이터 사용)".format(str(e)))

def display_real_time_data(enhanced_data):
    """실시간 데이터 표시"""
    kis_data = enhanced_data.get('kis_data', {})
    current_data = kis_data.get('current_data', {})
    
    if current_data:
        st.info("🔴 실시간 데이터 ({})".format(enhanced_data.get('data_source', 'KIS API')))
        
        # 실시간 가격 표시
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "현재가", 
                "{:,}원".format(current_data['current_price']),
                "{:+,}원 ({:+.2f}%)".format(
                    current_data['change'], 
                    current_data['change_rate']
                )
            )
        
        with col2:
            st.metric("거래량", "{:,}주".format(current_data['volume']))
            
        with col3:
            st.metric("고가", "{:,}원".format(current_data['high']))
            
        with col4:
            st.metric("저가", "{:,}원".format(current_data['low']))
        
        # 호가창 표시
        orderbook = kis_data.get('orderbook')
        if orderbook:
            display_orderbook(orderbook)
        
        st.markdown("---")

def display_delayed_data(data, data_source):
    """지연 데이터 표시"""
    st.info("🟡 지연 데이터 ({}, ~20분 지연)".format(data_source))
    
    if data.empty:
        st.warning("데이터가 없습니다.")
        return
    
    # 기존 방식으로 표시
    latest = data.iloc[-1]
    prev_close = data.iloc[-2]['Close'] if len(data) > 1 else latest['Close']
    change = latest['Close'] - prev_close
    change_pct = (change / prev_close) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("현재가", "{:,.0f}원".format(latest['Close']), "{:+.0f}원".format(change))
    
    with col2:
        st.metric("변동율", "{:+.2f}%".format(change_pct))
    
    with col3:
        st.metric("거래량", "{:,.0f}주".format(latest['Volume']))
    
    with col4:
        rsi_value = latest['RSI'] if 'RSI' in latest and not pd.isna(latest['RSI']) else 0
        st.metric("RSI", "{:.1f}".format(rsi_value))
    
    st.markdown("---")

def display_orderbook(orderbook):
    """호가창 표시"""
    st.subheader("📋 실시간 호가창")
    
    # 데이터 길이 확인
    ask_prices = orderbook.get('ask_prices', [])
    ask_volumes = orderbook.get('ask_volumes', [])
    bid_prices = orderbook.get('bid_prices', [])
    bid_volumes = orderbook.get('bid_volumes', [])
    
    if not ask_prices or not bid_prices:
        st.warning("호가 데이터가 없습니다.")
        return
    
    # 최대 10단계까지 표시
    max_levels = min(10, len(ask_prices), len(bid_prices), len(ask_volumes), len(bid_volumes))
    
    if max_levels > 0:
        # 호가창 데이터프레임 생성
        orderbook_data = []
        
        # 매도호가 (높은 가격부터)
        for i in range(max_levels-1, -1, -1):
            if i < len(ask_prices):
                orderbook_data.append({
                    '구분': '매도{}'.format(i+1),
                    '잔량': '{:,}'.format(ask_volumes[i]) if i < len(ask_volumes) else '-',
                    '호가': '{:,}'.format(ask_prices[i]),
                    '타입': 'ask'
                })
        
        # 현재가 구분선
        orderbook_data.append({
            '구분': '현재가',
            '잔량': '-',
            '호가': '현재가',
            '타입': 'current'
        })
        
        # 매수호가
        for i in range(min(max_levels, len(bid_prices))):
            orderbook_data.append({
                '구분': '매수{}'.format(i+1),
                '잔량': '{:,}'.format(bid_volumes[i]) if i < len(bid_volumes) else '-',
                '호가': '{:,}'.format(bid_prices[i]),
                '타입': 'bid'
            })
        
        orderbook_df = pd.DataFrame(orderbook_data)
        
        # 스타일링 적용
        def style_orderbook_row(row):
            if row['타입'] == 'ask':
                return ['background-color: #ffebee'] * len(row)
            elif row['타입'] == 'bid':
                return ['background-color: #e8f5e8'] * len(row)
            elif row['타입'] == 'current':
                return ['background-color: #fff3e0; font-weight: bold'] * len(row)
            return [''] * len(row)
        
        styled_df = orderbook_df.drop('타입', axis=1).style.apply(style_orderbook_row, axis=1)
        
        # 호가창 표시
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.warning("호가 데이터를 표시할 수 없습니다.")
    
    st.markdown("---")

def calculate_technical_indicators(data):
    """기술적 지표 계산"""
    if data.empty:
        return data
    
    # RSI 계산
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # 이동평균선
    data['MA_5'] = data['Close'].rolling(window=5).mean()
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_60'] = data['Close'].rolling(window=60).mean()
    
    # 볼린저 밴드 계산
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
    data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
    
    # MACD 계산
    exp1 = data['Close'].ewm(span=12).mean()
    exp2 = data['Close'].ewm(span=26).mean()
    data['MACD'] = exp1 - exp2
    data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
    data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
    
    # 스토캐스틱 계산
    low_14 = data['Low'].rolling(window=14).min()
    high_14 = data['High'].rolling(window=14).max()
    data['Stoch_K'] = 100 * ((data['Close'] - low_14) / (high_14 - low_14))
    data['Stoch_D'] = data['Stoch_K'].rolling(window=3).mean()
    
    return data

def analyze_fair_value(data, current_price):
    """공정가치 분석"""
    if data.empty or len(data) < 60:
        return {
            'fair_value_score': 50,
            'recommendation': '중립',
            'confidence': 50,
            'reasons': ['데이터 부족으로 분석 불가'],
            'details': {}
        }
    
    latest = data.iloc[-1]
    score = 0
    reasons = []
    details = {}
    
    # RSI 분석 (30점 만점)
    rsi = latest['RSI']
    if rsi < 30:
        rsi_score = 25
        reasons.append("RSI 과매도 상태 ({:.1f}) - 매수 신호".format(rsi))
    elif rsi < 45:
        rsi_score = 15
        reasons.append("RSI 다소 과매도 ({:.1f})".format(rsi))
    elif rsi > 70:
        rsi_score = -15
        reasons.append("RSI 과매수 상태 ({:.1f}) - 매도 신호".format(rsi))
    elif rsi > 55:
        rsi_score = -5
        reasons.append("RSI 다소 과매수 ({:.1f})".format(rsi))
    else:
        rsi_score = 5
        reasons.append("RSI 중립 구간 ({:.1f})".format(rsi))
    
    details['rsi'] = {'value': rsi, 'score': rsi_score}
    
    # 볼린저 밴드 분석 (25점 만점)
    bb_position = ((current_price - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower'])) * 100
    if bb_position < 20:
        bb_score = 20
        reasons.append("볼린저밴드 하단 근처 - 매수 신호")
    elif bb_position < 40:
        bb_score = 10
        reasons.append("볼린저밴드 하단권")
    elif bb_position > 80:
        bb_score = -15
        reasons.append("볼린저밴드 상단 근처 - 매도 신호")
    elif bb_position > 60:
        bb_score = -5
        reasons.append("볼린저밴드 상단권")
    else:
        bb_score = 0
        reasons.append("볼린저밴드 중간권")
    
    details['bollinger'] = {'position': bb_position, 'score': bb_score}
    
    # 이동평균선 분석 (25점 만점)
    ma_score = 0
    if current_price > latest['MA_5']:
        ma_score += 8
        reasons.append("5일선 상향돌파")
    if current_price > latest['MA_20']:
        ma_score += 10
        reasons.append("20일선 상향돌파")
    if current_price > latest['MA_60']:
        ma_score += 7
        reasons.append("60일선 상향돌파")
    
    if ma_score == 0:
        reasons.append("주요 이동평균선 하락 배열")
        ma_score = -15
    
    details['moving_average'] = {'score': ma_score}
    
    # MACD 분석 (20점 만점)
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']
    if macd > macd_signal and macd > 0:
        macd_score = 15
        reasons.append("MACD 강한 상승 신호")
    elif macd > macd_signal:
        macd_score = 10
        reasons.append("MACD 상승 신호")
    elif macd < macd_signal and macd < 0:
        macd_score = -10
        reasons.append("MACD 하락 신호")
    else:
        macd_score = 0
    
    details['macd'] = {'score': macd_score}
    
    # 최종 점수 계산 (100점 만점)
    total_score = rsi_score + bb_score + ma_score + macd_score
    fair_value_score = max(0, min(100, 50 + total_score))
    
    # 추천 등급 결정
    if fair_value_score >= 70:
        recommendation = "매수"
        confidence = min(90, fair_value_score + 10)
    elif fair_value_score >= 55:
        recommendation = "약매수"
        confidence = min(80, fair_value_score + 5)
    elif fair_value_score <= 30:
        recommendation = "매도"
        confidence = min(85, (50 - fair_value_score) + 60)
    elif fair_value_score <= 45:
        recommendation = "약매도"
        confidence = min(75, (50 - fair_value_score) + 55)
    else:
        recommendation = "중립"
        confidence = 60
    
    return {
        'fair_value_score': fair_value_score,
        'recommendation': recommendation,
        'confidence': confidence,
        'reasons': reasons,
        'details': details
    }

def get_industry_peers(symbol):
    """업종별 동종 종목 리스트 반환 (간소화된 버전)"""
    # 주요 업종별 대표 종목들
    industry_map = {
        # 전자/반도체
        '005930': {'industry': '반도체', 'peers': ['000660', '035420', '373220']},
        '000660': {'industry': '반도체', 'peers': ['005930', '035420', '373220']}, 
        '035420': {'industry': 'IT서비스', 'peers': ['035720', '005930', '000660']},
        '035720': {'industry': 'IT서비스', 'peers': ['035420', '005930', '000660']},
        
        # 에너지/화학
        '373220': {'industry': '전기전자', 'peers': ['051910', '005490', '005930']},
        '051910': {'industry': '화학', 'peers': ['373220', '005490', '009830']},
        
        # 자동차
        '005380': {'industry': '자동차', 'peers': ['000270', '012330', '161390']},
        '000270': {'industry': '자동차', 'peers': ['005380', '012330', '161390']},
        
        # 바이오/제약
        '207940': {'industry': '바이오', 'peers': ['068270', '326030', '145020']},
        
        # 철강/소재
        '005490': {'industry': '철강', 'peers': ['051910', '009830', '010130']},
    }
    
    # 종목코드에서 .KS 제거
    clean_symbol = symbol.replace('.KS', '').replace('.KQ', '')
    
    if clean_symbol in industry_map:
        return industry_map[clean_symbol]
    else:
        # 기본 비교군 (대형주)
        return {
            'industry': '기타', 
            'peers': ['005930', '000660', '035420', '035720']
        }

def analyze_industry_comparison(symbol, current_data):
    """업종 비교 분석"""
    if current_data.empty or len(current_data) < 20:
        return {
            'comparison_available': False,
            'industry': '정보 없음',
            'message': '데이터 부족으로 업종 비교 불가'
        }
    
    # 업종 정보 가져오기
    industry_info = get_industry_peers(symbol)
    industry = industry_info['industry']
    peer_codes = industry_info['peers']
    
    if len(peer_codes) < 2:
        return {
            'comparison_available': False,
            'industry': industry,
            'message': '비교 가능한 동종업계 종목 부족'
        }
    
    # 현재 종목 지표
    current_latest = current_data.iloc[-1]
    current_metrics = {
        'rsi': current_latest['RSI'] if not pd.isna(current_latest['RSI']) else 50,
        'ma20_ratio': current_latest['Close'] / current_latest['MA_20'] if not pd.isna(current_latest['MA_20']) else 1,
        'bb_position': ((current_latest['Close'] - current_latest['BB_Lower']) / 
                       (current_latest['BB_Upper'] - current_latest['BB_Lower'])) * 100 
                       if not pd.isna(current_latest['BB_Lower']) else 50
    }
    
    # 동종업계 평균 계산
    peer_metrics = []
    successful_peers = []
    
    for peer_code in peer_codes:
        try:
            # KS/KQ 구분
            if peer_code in ['005930', '000660', '035420', '035720', '005380', '000270', '051910', '207940', '005490']:
                peer_symbol = "{}.KS".format(peer_code)
            else:
                peer_symbol = "{}.KQ".format(peer_code)
            
            peer_data = get_stock_data(peer_symbol, '3mo')
            if not peer_data.empty and len(peer_data) >= 20:
                peer_data = calculate_technical_indicators(peer_data)
                peer_latest = peer_data.iloc[-1]
                
                peer_metric = {
                    'rsi': peer_latest['RSI'] if not pd.isna(peer_latest['RSI']) else 50,
                    'ma20_ratio': peer_latest['Close'] / peer_latest['MA_20'] if not pd.isna(peer_latest['MA_20']) else 1,
                    'bb_position': ((peer_latest['Close'] - peer_latest['BB_Lower']) / 
                                   (peer_latest['BB_Upper'] - peer_latest['BB_Lower'])) * 100 
                                   if not pd.isna(peer_latest['BB_Lower']) else 50
                }
                peer_metrics.append(peer_metric)
                successful_peers.append(peer_code)
        except:
            continue
    
    if len(peer_metrics) < 2:
        return {
            'comparison_available': False,
            'industry': industry,
            'message': '동종업계 데이터 수집 실패'
        }
    
    # 업종 평균 계산
    industry_avg = {
        'rsi': sum(p['rsi'] for p in peer_metrics) / len(peer_metrics),
        'ma20_ratio': sum(p['ma20_ratio'] for p in peer_metrics) / len(peer_metrics),
        'bb_position': sum(p['bb_position'] for p in peer_metrics) / len(peer_metrics)
    }
    
    # 비교 분석
    comparison_analysis = []
    rsi_diff = current_metrics['rsi'] - industry_avg['rsi']
    if abs(rsi_diff) > 5:
        if rsi_diff < 0:
            comparison_analysis.append("RSI가 업종 평균보다 {:.1f}p 낮음 (상대적 매수 우위)".format(abs(rsi_diff)))
        else:
            comparison_analysis.append("RSI가 업종 평균보다 {:.1f}p 높음 (상대적 과매수)".format(rsi_diff))
    
    ma20_diff = ((current_metrics['ma20_ratio'] - 1) * 100) - ((industry_avg['ma20_ratio'] - 1) * 100)
    if abs(ma20_diff) > 1:
        if ma20_diff > 0:
            comparison_analysis.append("20일선 대비 위치가 업종 평균보다 {:.1f}%p 높음".format(ma20_diff))
        else:
            comparison_analysis.append("20일선 대비 위치가 업종 평균보다 {:.1f}%p 낮음".format(abs(ma20_diff)))
    
    bb_diff = current_metrics['bb_position'] - industry_avg['bb_position']
    if abs(bb_diff) > 10:
        if bb_diff < 0:
            comparison_analysis.append("볼린저밴드 위치가 업종 평균보다 낮음 (상대적 저평가)")
        else:
            comparison_analysis.append("볼린저밴드 위치가 업종 평균보다 높음 (상대적 고평가)")
    
    # 종합 점수 계산
    comparison_score = 50
    if rsi_diff < -5:
        comparison_score += 15
    elif rsi_diff > 10:
        comparison_score -= 10
        
    if ma20_diff > 2:
        comparison_score += 10
    elif ma20_diff < -2:
        comparison_score -= 10
        
    if bb_diff < -10:
        comparison_score += 10
    elif bb_diff > 15:
        comparison_score -= 10
    
    comparison_score = max(0, min(100, comparison_score))
    
    # 상대적 추천
    if comparison_score >= 70:
        relative_recommendation = "업종 내 강력 매수"
    elif comparison_score >= 55:
        relative_recommendation = "업종 내 매수"
    elif comparison_score <= 30:
        relative_recommendation = "업종 내 매도"
    elif comparison_score <= 45:
        relative_recommendation = "업종 내 약매도"
    else:
        relative_recommendation = "업종 평균 수준"
    
    return {
        'comparison_available': True,
        'industry': industry,
        'peer_count': len(successful_peers),
        'peer_codes': successful_peers,
        'current_metrics': current_metrics,
        'industry_avg': industry_avg,
        'comparison_score': comparison_score,
        'relative_recommendation': relative_recommendation,
        'comparison_analysis': comparison_analysis
    }

def analyze_trading_signals(data, current_price):
    """매매 신호 분석"""
    if data.empty or len(data) < 60:
        return {
            'signals_available': False,
            'message': '데이터 부족으로 매매 신호 분석 불가'
        }
    
    latest = data.iloc[-1]
    prev = data.iloc[-2] if len(data) > 1 else latest
    signals = []
    signal_strength = 0
    entry_signals = []
    exit_signals = []
    
    # 1. RSI 신호 분석
    rsi = latest['RSI']
    rsi_prev = prev['RSI'] if not pd.isna(prev['RSI']) else rsi
    
    if rsi < 30 and rsi_prev >= 30:
        entry_signals.append("RSI 과매도권 진입 - 반등 신호")
        signal_strength += 20
    elif rsi > 70 and rsi_prev <= 70:
        exit_signals.append("RSI 과매수권 진입 - 매도 신호")
        signal_strength -= 15
    elif rsi < 25:
        entry_signals.append("RSI 극도 과매도 - 강한 매수 신호")
        signal_strength += 30
    elif rsi > 75:
        exit_signals.append("RSI 극도 과매수 - 강한 매도 신호")
        signal_strength -= 25
    
    # 2. 이동평균선 신호 분석
    ma5 = latest['MA_5']
    ma20 = latest['MA_20']
    ma60 = latest['MA_60']
    
    ma5_prev = prev['MA_5'] if not pd.isna(prev['MA_5']) else ma5
    ma20_prev = prev['MA_20'] if not pd.isna(prev['MA_20']) else ma20
    
    # 골든크로스/데드크로스 감지
    if ma5 > ma20 and ma5_prev <= ma20_prev:
        entry_signals.append("골든크로스 - 5일선이 20일선 상향돌파")
        signal_strength += 25
    elif ma5 < ma20 and ma5_prev >= ma20_prev:
        exit_signals.append("데드크로스 - 5일선이 20일선 하향돌파")
        signal_strength -= 20
    
    # 정배열/역배열 확인
    if ma5 > ma20 > ma60:
        signals.append("이동평균선 정배열 - 상승 추세")
        signal_strength += 15
    elif ma5 < ma20 < ma60:
        signals.append("이동평균선 역배열 - 하락 추세")
        signal_strength -= 15
    
    # 3. 볼린저밴드 신호 분석
    bb_upper = latest['BB_Upper']
    bb_lower = latest['BB_Lower']
    bb_middle = latest['BB_Middle']
    
    bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100
    prev_price = prev['Close']
    prev_bb_position = ((prev_price - prev['BB_Lower']) / (prev['BB_Upper'] - prev['BB_Lower'])) * 100 if not pd.isna(prev['BB_Lower']) else bb_position
    
    if bb_position < 20 and prev_bb_position >= 20:
        entry_signals.append("볼린저밴드 하단 터치 - 반등 신호")
        signal_strength += 20
    elif bb_position > 80 and prev_bb_position <= 80:
        exit_signals.append("볼린저밴드 상단 터치 - 조정 신호")
        signal_strength -= 15
    
    # 볼린저밴드 스퀴즈 감지 (변동성 축소)
    bb_width = ((bb_upper - bb_lower) / bb_middle) * 100
    if bb_width < 10:  # 볼린저밴드 폭이 좁을 때
        signals.append("볼린저밴드 스퀴즈 - 큰 변동성 임박")
    
    # 4. MACD 신호 분석
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']
    macd_hist = latest['MACD_Histogram']
    
    macd_prev = prev['MACD'] if not pd.isna(prev['MACD']) else macd
    macd_signal_prev = prev['MACD_Signal'] if not pd.isna(prev['MACD_Signal']) else macd_signal
    macd_hist_prev = prev['MACD_Histogram'] if not pd.isna(prev['MACD_Histogram']) else macd_hist
    
    # MACD 크로스 신호
    if macd > macd_signal and macd_prev <= macd_signal_prev:
        entry_signals.append("MACD 골든크로스 - 상승 신호")
        signal_strength += 20
    elif macd < macd_signal and macd_prev >= macd_signal_prev:
        exit_signals.append("MACD 데드크로스 - 하락 신호")
        signal_strength -= 20
    
    # MACD 히스토그램 분석
    if macd_hist > 0 and macd_hist_prev <= 0:
        signals.append("MACD 히스토그램 양전환 - 모멘텀 증가")
        signal_strength += 10
    elif macd_hist < 0 and macd_hist_prev >= 0:
        signals.append("MACD 히스토그램 음전환 - 모멘텀 감소")
        signal_strength -= 10
    
    # 5. 스토캐스틱 신호 분석
    stoch_k = latest['Stoch_K']
    stoch_d = latest['Stoch_D']
    stoch_k_prev = prev['Stoch_K'] if not pd.isna(prev['Stoch_K']) else stoch_k
    stoch_d_prev = prev['Stoch_D'] if not pd.isna(prev['Stoch_D']) else stoch_d
    
    if stoch_k < 20 and stoch_d < 20:
        if stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev:
            entry_signals.append("스토캐스틱 과매도권 골든크로스")
            signal_strength += 15
    elif stoch_k > 80 and stoch_d > 80:
        if stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev:
            exit_signals.append("스토캐스틱 과매수권 데드크로스")
            signal_strength -= 15
    
    # 6. 종합 신호 강도 계산 및 추천
    signal_strength = max(-100, min(100, signal_strength))  # -100 ~ 100 범위로 제한
    
    if signal_strength >= 50:
        overall_signal = "강한 매수"
        signal_color = "🟢"
        confidence = min(95, 70 + (signal_strength - 50) * 0.5)
    elif signal_strength >= 25:
        overall_signal = "매수"
        signal_color = "🟡"
        confidence = min(85, 60 + (signal_strength - 25) * 0.4)
    elif signal_strength <= -50:
        overall_signal = "강한 매도"
        signal_color = "🔴"
        confidence = min(90, 70 + abs(signal_strength + 50) * 0.4)
    elif signal_strength <= -25:
        overall_signal = "매도"
        signal_color = "🟠"
        confidence = min(80, 60 + abs(signal_strength + 25) * 0.4)
    else:
        overall_signal = "관망"
        signal_color = "⚪"
        confidence = 50
    
    # 7. 목표가 및 손절가 계산
    volatility = data['Close'].rolling(window=20).std().iloc[-1] / current_price
    
    if signal_strength > 0:  # 매수 신호일 때
        target_price_1 = current_price * (1 + volatility * 1.5)  # 1차 목표가
        target_price_2 = current_price * (1 + volatility * 2.5)  # 2차 목표가
        stop_loss = current_price * (1 - volatility * 1.0)  # 손절가
    else:  # 매도 신호일 때
        target_price_1 = current_price * (1 - volatility * 1.5)  # 1차 목표가
        target_price_2 = current_price * (1 - volatility * 2.5)  # 2차 목표가
        stop_loss = current_price * (1 + volatility * 1.0)  # 손절가
    
    return {
        'signals_available': True,
        'overall_signal': overall_signal,
        'signal_color': signal_color,
        'signal_strength': signal_strength,
        'confidence': confidence,
        'entry_signals': entry_signals,
        'exit_signals': exit_signals,
        'general_signals': signals,
        'target_price_1': target_price_1,
        'target_price_2': target_price_2,
        'stop_loss': stop_loss,
        'volatility': volatility * 100
    }

def create_candlestick_chart(data, symbol):
    """캔들스틱 차트 생성"""
    if data.empty:
        st.warning("차트 데이터를 불러올 수 없습니다.")
        return None
        
    fig = go.Figure()
    
    # 캔들스틱 추가
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name=symbol
    ))
    
    # 이동평균선 추가
    if 'MA_5' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA_5'],
            mode='lines', name='MA5',
            line=dict(color='orange', width=1)
        ))
    
    if 'MA_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA_20'],
            mode='lines', name='MA20',
            line=dict(color='red', width=1)
        ))
    
    fig.update_layout(
        title="주가 차트",
        yaxis_title="가격 (원)",
        xaxis_title="날짜",
        height=500,
        showlegend=True
    )
    
    return fig

def main():
    """메인 함수"""
    st.title("🚀 Smart Trading Dashboard v4.0")
    st.caption("실시간 데이터 지원 (한국투자증권 API + Yahoo Finance 하이브리드)")
    
    # 사용법 간단 안내
    with st.container():
        col_intro1, col_intro2 = st.columns([3, 1])
        with col_intro1:
            st.markdown("""
            **🎯 종목을 검색하여 공정가치 분석, 업종 비교, 매매 신호를 확인하세요!**  
            📊 5가지 기술적 지표 종합 분석 | 🏭 동종업계 비교 | 🚦 실시간 매매 신호 | 📚 상세한 용어 설명
            """)
        with col_intro2:
            if st.button("📚 사용법 보기", help="대시보드 사용법과 투자 가이드를 확인하세요"):
                st.info("👇 화면 하단의 '📚 투자 용어 가이드' 섹션을 확인해주세요!")
    
    st.markdown("---")
    
    # 사이드바
    st.sidebar.header("🔍 종목 선택")
    st.sidebar.markdown("📝 **사용법:** 검색창에 종목명을 입력하세요")
    st.sidebar.markdown("💡 **예시:** 삼성전자, 네이버, 카카오")
    
    # 종목 검색
    selected_name = st_searchbox(
        search_function=search_stocks,
        placeholder="예: 삼성전자, NAVER, 005930...",
        key="stock_searchbox"
    )
    
    # 전체 종목 리스트
    all_stocks = get_korean_stocks()
    
    # 선택된 종목 처리
    if selected_name and selected_name in all_stocks:
        selected_symbol = all_stocks[selected_name]
        st.sidebar.info("선택된 종목: **{}**".format(selected_name))
    else:
        # 기본값 설정
        default_stock = "삼성전자 (005930)" if "삼성전자 (005930)" in all_stocks else list(all_stocks.keys())[0]
        selected_name = default_stock
        selected_symbol = all_stocks[selected_name]
        st.sidebar.warning("종목을 검색해주세요")
    
    # 기간 선택
    period = st.sidebar.selectbox(
        "조회 기간",
        ["1mo", "3mo", "6mo", "1y", "2y"],
        index=3
    )
    
    # 메인 컨텐츠
    st.subheader("📈 {} ({})".format(selected_name, selected_symbol))
    
    # API 상태 확인
    check_api_status()
    
    # 향상된 데이터 로드
    with st.spinner("데이터 로딩 중..."):
        enhanced_data = get_stock_data_enhanced(selected_symbol, period)
        data = enhanced_data.get('chart_data', pd.DataFrame())
        
    if not data.empty:
        # 기술적 지표 계산
        data = calculate_technical_indicators(data)
        
        # 실시간 데이터 표시
        if enhanced_data.get('has_realtime'):
            display_real_time_data(enhanced_data)
        else:
            display_delayed_data(data, enhanced_data.get('data_source', 'yfinance'))
        
        st.markdown("---")
        
        # 차트 표시
        st.subheader("📊 주가 차트")
        chart = create_candlestick_chart(data, selected_name)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        
        # 공정가치 분석
        st.markdown("---")
        st.subheader("⚖️ 공정가치 분석")
        
        # 현재 가격 정보 (데이터에서 가져오기)
        current_price = data['Close'].iloc[-1] if not data.empty else 0
        fair_value_analysis = analyze_fair_value(data, current_price)
        
        # 분석 결과 표시
        col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
        
        with col_analysis1:
            score = fair_value_analysis['fair_value_score']
            if score >= 70:
                score_color = "🟢"
                score_desc = "매수 권장"
            elif score >= 55:
                score_color = "🟡"
                score_desc = "약매수"
            elif score <= 30:
                score_color = "🔴"
                score_desc = "매도 권장"
            elif score <= 45:
                score_color = "🟠"
                score_desc = "약매도"
            else:
                score_color = "⚪"
                score_desc = "중립"
            
            st.metric(
                "공정가치 점수",
                "{} {}/100".format(score_color, score),
                "({})".format(score_desc),
                help="RSI, 볼린저밴드, 이동평균선, MACD를 종합한 점수입니다. 70점 이상은 매수, 30점 이하는 매도를 의미합니다."
            )
        
        with col_analysis2:
            recommendation = fair_value_analysis['recommendation']
            confidence = fair_value_analysis['confidence']
            
            if recommendation == "매수":
                rec_color = "🟢"
            elif recommendation == "약매수":
                rec_color = "🟡"
            elif recommendation == "매도":
                rec_color = "🔴"
            elif recommendation == "약매도":
                rec_color = "🟠"
            else:
                rec_color = "⚪"
            
            st.metric(
                "투자 추천",
                "{} {}".format(rec_color, recommendation),
                "신뢰도: {:.1f}%".format(confidence)
            )
        
        with col_analysis3:
            # 볼린저밴드 위치 표시
            bb_position = fair_value_analysis['details'].get('bollinger', {}).get('position', 50)
            st.metric(
                "볼린저밴드 위치",
                "{:.1f}%".format(bb_position),
                help="볼린저밴드 내 현재가 위치 (0%=하단, 100%=상단)"
            )
        
        # 상세 분석 결과
        with st.expander("📈 상세 분석 결과", expanded=True):
            st.markdown("**🎯 주요 판단 근거:**")
            for reason in fair_value_analysis['reasons']:
                st.markdown("• {}".format(reason))
            
            st.markdown("---")
            
            # 지표별 세부 분석
            col_detail1, col_detail2 = st.columns(2)
            
            with col_detail1:
                st.markdown("**📊 기술적 지표:**")
                
                # RSI 분석
                rsi_data = fair_value_analysis['details'].get('rsi', {})
                if rsi_data:
                    rsi_value = rsi_data.get('value', 0)
                    st.markdown("**RSI ({:.1f}):** {}".format(
                        rsi_value,
                        "과매도" if rsi_value < 30 else "과매수" if rsi_value > 70 else "중립"
                    ))
                
                # 볼린저밴드 분석
                bb_data = fair_value_analysis['details'].get('bollinger', {})
                if bb_data:
                    bb_pos = bb_data.get('position', 50)
                    st.markdown("**볼린저밴드:** {}".format(
                        "하단권" if bb_pos < 30 else "상단권" if bb_pos > 70 else "중간권"
                    ))
            
            with col_detail2:
                st.markdown("**📈 추세 분석:**")
                
                # 이동평균선 분석
                ma_score = fair_value_analysis['details'].get('moving_average', {}).get('score', 0)
                if ma_score > 15:
                    st.markdown("• 주요 이동평균선 상향 돌파")
                elif ma_score > 0:
                    st.markdown("• 일부 이동평균선 상향 돌파")
                else:
                    st.markdown("• 이동평균선 하락 배열")
                
                # MACD 분석
                macd_score = fair_value_analysis['details'].get('macd', {}).get('score', 0)
                if macd_score > 10:
                    st.markdown("• MACD 강한 상승 신호")
                elif macd_score > 0:
                    st.markdown("• MACD 상승 신호")
                elif macd_score < 0:
                    st.markdown("• MACD 하락 신호")
                else:
                    st.markdown("• MACD 중립")
        
        # 업종 비교 분석
        st.markdown("---")
        st.subheader("🏭 업종 비교 분석")
        
        industry_analysis = analyze_industry_comparison(selected_symbol, data)
        
        if industry_analysis['comparison_available']:
            # 업종 정보 표시
            col_industry1, col_industry2, col_industry3 = st.columns(3)
            
            with col_industry1:
                st.metric(
                    "업종",
                    industry_analysis['industry'],
                    help="현재 종목이 속한 업종 분류"
                )
            
            with col_industry2:
                comparison_score = industry_analysis['comparison_score']
                if comparison_score >= 70:
                    score_color = "🟢"
                elif comparison_score >= 55:
                    score_color = "🟡"
                elif comparison_score <= 30:
                    score_color = "🔴"
                elif comparison_score <= 45:
                    score_color = "🟠"
                else:
                    score_color = "⚪"
                
                st.metric(
                    "업종 내 상대 점수",
                    "{} {}/100".format(score_color, comparison_score),
                    help="동종업계 대비 상대적 매력도 (높을수록 업종 내 우위)"
                )
            
            with col_industry3:
                relative_rec = industry_analysis['relative_recommendation']
                if "강력 매수" in relative_rec:
                    rec_color = "🟢"
                elif "매수" in relative_rec:
                    rec_color = "🟡"
                elif "매도" in relative_rec:
                    rec_color = "🔴"
                else:
                    rec_color = "⚪"
                
                st.metric(
                    "업종 내 추천",
                    "{} {}".format(rec_color, relative_rec),
                    help="동종업계 대비 상대적 투자 추천"
                )
            
            # 상세 비교 분석
            with st.expander("📊 업종 비교 상세 분석", expanded=True):
                st.markdown("**🏭 업종 비교 현황 ({} 업종, {} 종목 비교)**".format(
                    industry_analysis['industry'], 
                    industry_analysis['peer_count']
                ))
                
                if industry_analysis['comparison_analysis']:
                    for analysis in industry_analysis['comparison_analysis']:
                        st.markdown("• {}".format(analysis))
                
                st.markdown("---")
                
                # 지표별 비교 테이블
                col_compare1, col_compare2 = st.columns(2)
                
                with col_compare1:
                    st.markdown("**📈 현재 종목 지표:**")
                    current = industry_analysis['current_metrics']
                    st.markdown("• **RSI**: {:.1f}".format(current['rsi']))
                    st.markdown("• **20일선 대비**: {:.1f}%".format((current['ma20_ratio'] - 1) * 100))
                    st.markdown("• **볼린저밴드 위치**: {:.1f}%".format(current['bb_position']))
                
                with col_compare2:
                    st.markdown("**🏭 업종 평균 지표:**")
                    industry_avg = industry_analysis['industry_avg']
                    st.markdown("• **RSI**: {:.1f}".format(industry_avg['rsi']))
                    st.markdown("• **20일선 대비**: {:.1f}%".format((industry_avg['ma20_ratio'] - 1) * 100))
                    st.markdown("• **볼린저밴드 위치**: {:.1f}%".format(industry_avg['bb_position']))
        
        else:
            st.info("📊 업종 비교 분석: {}".format(industry_analysis['message']))
            st.markdown("**참고:** 충분한 데이터가 확보되면 동종업계 대비 상대적 위치를 분석하여 제공합니다.")
        
        # 매매 신호 분석
        st.markdown("---")
        st.subheader("🚦 매매 신호 분석")
        
        trading_signals = analyze_trading_signals(data, current_price)
        
        if trading_signals['signals_available']:
            # 종합 신호 표시
            col_signal1, col_signal2, col_signal3, col_signal4 = st.columns(4)
            
            with col_signal1:
                st.metric(
                    "종합 신호",
                    "{} {}".format(trading_signals['signal_color'], trading_signals['overall_signal']),
                    help="기술적 지표 종합 매매 신호"
                )
            
            with col_signal2:
                signal_strength = trading_signals['signal_strength']
                strength_display = "+" + str(signal_strength) if signal_strength > 0 else str(signal_strength)
                st.metric(
                    "신호 강도",
                    "{}/100".format(strength_display),
                    help="매매 신호 강도 (-100~+100, 양수=매수, 음수=매도)"
                )
            
            with col_signal3:
                confidence = trading_signals['confidence']
                st.metric(
                    "신뢰도",
                    "{:.1f}%".format(confidence),
                    help="신호 분석 신뢰도"
                )
            
            with col_signal4:
                volatility = trading_signals['volatility']
                st.metric(
                    "변동성",
                    "{:.1f}%".format(volatility),
                    help="20일 기준 가격 변동성"
                )
            
            # 목표가 및 손절가 표시
            if trading_signals['signal_strength'] != 0:
                col_price1, col_price2, col_price3 = st.columns(3)
                
                with col_price1:
                    target1 = trading_signals['target_price_1']
                    st.metric(
                        "1차 목표가" if trading_signals['signal_strength'] > 0 else "1차 목표가(하락)",
                        "{:,.0f}원".format(target1),
                        "{:+.1f}%".format((target1 / current_price - 1) * 100)
                    )
                
                with col_price2:
                    target2 = trading_signals['target_price_2']
                    st.metric(
                        "2차 목표가" if trading_signals['signal_strength'] > 0 else "2차 목표가(하락)",
                        "{:,.0f}원".format(target2),
                        "{:+.1f}%".format((target2 / current_price - 1) * 100)
                    )
                
                with col_price3:
                    stop_loss = trading_signals['stop_loss']
                    st.metric(
                        "손절가",
                        "{:,.0f}원".format(stop_loss),
                        "{:+.1f}%".format((stop_loss / current_price - 1) * 100)
                    )
            
            # 상세 신호 분석
            with st.expander("🔍 상세 매매 신호 분석", expanded=True):
                col_signals1, col_signals2 = st.columns(2)
                
                with col_signals1:
                    if trading_signals['entry_signals']:
                        st.markdown("**🟢 매수 신호:**")
                        for signal in trading_signals['entry_signals']:
                            st.markdown("• {}".format(signal))
                    
                    if trading_signals['general_signals']:
                        st.markdown("**📊 추세 분석:**")
                        for signal in trading_signals['general_signals']:
                            st.markdown("• {}".format(signal))
                
                with col_signals2:
                    if trading_signals['exit_signals']:
                        st.markdown("**🔴 매도 신호:**")
                        for signal in trading_signals['exit_signals']:
                            st.markdown("• {}".format(signal))
                
                # 매매 가이드라인
                st.markdown("---")
                st.markdown("**📋 매매 가이드라인:**")
                
                if trading_signals['signal_strength'] >= 25:
                    st.markdown("""
                    **🟢 매수 포지션 권장**
                    • 분할 매수 전략 고려 (2-3회 분할)
                    • 1차 목표가 도달 시 일부 수익 실현
                    • 손절가 설정으로 리스크 관리
                    """)
                elif trading_signals['signal_strength'] <= -25:
                    st.markdown("""
                    **🔴 매도 포지션 권장**
                    • 보유 종목 있다면 분할 매도 고려
                    • 반등 시 추가 매도 기회 활용
                    • 손절가 상향 돌파 시 추가 하락 주의
                    """)
                else:
                    st.markdown("""
                    **⚪ 관망 권장**
                    • 명확한 신호 나타날 때까지 대기
                    • 지지/저항선 돌파 여부 관찰
                    • 거래량 증가와 함께 신호 확인
                    """)
        
        else:
            st.info("🚦 매매 신호 분석: {}".format(trading_signals['message']))
            st.markdown("**참고:** 충분한 데이터가 확보되면 기술적 지표 기반 매매 신호를 제공합니다.")
        
        # 용어 설명 및 도움말
        st.markdown("---")
        st.subheader("📚 투자 용어 가이드")
        
        # 탭으로 구분된 용어 설명
        tab1, tab2, tab3, tab4 = st.tabs(["📈 차트 기초", "📊 기술 지표", "🚦 매매 신호", "💡 투자 가이드"])
        
        with tab1:
            st.markdown("""
            ### 📈 캔들스틱 차트 이해하기
            
            **🕯️ 캔들의 구성 요소:**
            - **몸통(실체)**: 시가와 종가 사이의 구간
            - **꼬리(그림자)**: 고가와 저가를 나타내는 선
            
            **🎨 색깔의 의미:**
            - **🟢 파란색/초록색 캔들**: 상승 (시가 < 종가)
              - 해당 기간 동안 주가가 올랐음을 의미
              - 매수세가 강했던 시점
            - **🔴 빨간색 캔들**: 하락 (시가 > 종가)
              - 해당 기간 동안 주가가 내렸음을 의미
              - 매도세가 강했던 시점
            
            **📏 캔들의 형태가 말하는 것:**
            - **긴 몸통**: 강한 상승 또는 하락
            - **짧은 몸통**: 보합세, 방향성 부족
            - **긴 위꼬리**: 고점에서 저항, 매도 압력
            - **긴 아래꼬리**: 저점에서 지지, 매수 관심
            
            ---
            
            ### 🔄 이동평균선의 의미
            
            **📊 이동평균선이란?**
            - 일정 기간 동안의 주가 평균을 연결한 선
            - 주가의 전반적인 흐름과 추세를 파악하는 도구
            
            **🏃‍♂️ 단기 vs 장기 이동평균:**
            - **MA5 (5일선)**: 단기 추세, 빠른 반응
            - **MA20 (20일선)**: 중기 추세, 안정적 신호
            - **MA60 (60일선)**: 장기 추세, 큰 흐름 파악
            
            **🎯 이동평균선 활용법:**
            - **지지선**: 주가가 이동평균선 위에서 지지받는 경우
            - **저항선**: 주가가 이동평균선에서 막히는 경우
            - **정배열**: 단기선 > 중기선 > 장기선 (상승추세)
            - **역배열**: 단기선 < 중기선 < 장기선 (하락추세)
            """)
        
        with tab2:
            st.markdown("""
            ### 📊 주요 기술적 지표 완전 해설
            
            **🔥 RSI (상대강도지수) - 과매수/과매도 측정기**
            
            RSI는 주식이 과도하게 많이 팔렸는지, 많이 사졌는지 알려주는 지표입니다.
            
            - **0~30**: 🟢 과매도 구간 (너무 많이 팔려서 반등 가능)
            - **30~70**: ⚪ 정상 구간 (적절한 거래)
            - **70~100**: 🔴 과매수 구간 (너무 많이 사져서 조정 가능)
            
            **💡 실전 활용법:**
            - RSI 30 이하에서 매수 타이밍 포착
            - RSI 70 이상에서 매도 타이밍 고려
            - 다른 지표와 함께 봐야 더 정확함
            
            ---
            
            **🎈 볼린저밴드 - 주가의 정상 범위 측정기**
            
            주가가 보통 움직이는 범위를 보여주는 밴드입니다.
            
            - **상단밴드**: 평소보다 높은 가격대 (매도 신호 가능)
            - **중심선**: 20일 평균가격 (균형점)
            - **하단밴드**: 평소보다 낮은 가격대 (매수 신호 가능)
            
            **💡 실전 활용법:**
            - 하단밴드 터치 시 반등 기대
            - 상단밴드 터치 시 조정 가능성
            - 밴드가 좁아지면 큰 움직임 임박
            
            ---
            
            **⚡ MACD - 추세 변화의 신호등**
            
            주가 추세가 바뀌는 시점을 알려주는 지표입니다.
            
            - **MACD선**: 단기/장기 이동평균의 차이
            - **시그널선**: MACD의 평균선
            - **히스토그램**: MACD와 시그널선의 차이
            
            **💡 실전 활용법:**
            - MACD선이 시그널선을 위로 뚫으면 매수 신호
            - MACD선이 시그널선을 아래로 뚫으면 매도 신호
            - 히스토그램이 0선 위로 올라오면 상승 모멘텀
            
            ---
            
            **🎯 스토캐스틱 - 현재 위치 파악기**
            
            현재 주가가 최근 고점과 저점 사이 어디에 위치하는지 알려줍니다.
            
            - **%K선**: 빠른 선 (민감한 반응)
            - **%D선**: 느린 선 (%K의 평균)
            - **80 이상**: 고점 근처 (매도 고려)
            - **20 이하**: 저점 근처 (매수 고려)
            
            **💡 실전 활용법:**
            - 20 이하에서 골든크로스 발생 시 매수 신호
            - 80 이상에서 데드크로스 발생 시 매도 신호
            """)
        
        with tab3:
            st.markdown("""
            ### 🚦 매매 신호 해석 가이드
            
            **📊 신호 강도 점수 이해하기**
            
            시스템에서 제공하는 -100~+100 점수의 의미:
            
            - **+75~+100**: 🟢 매우 강한 매수 신호
              - 여러 지표가 동시에 매수 신호
              - 적극적인 매수 포지션 고려
            
            - **+25~+74**: 🟡 매수 신호
              - 일부 지표에서 매수 신호
              - 신중한 매수 접근
            
            - **-24~+24**: ⚪ 관망
              - 명확한 방향성 없음
              - 추가 신호 대기 권장
            
            - **-74~-25**: 🟠 매도 신호
              - 일부 지표에서 매도 신호
              - 보유 시 일부 매도 고려
            
            - **-100~-75**: 🔴 매우 강한 매도 신호
              - 여러 지표가 동시에 매도 신호
              - 적극적인 매도 포지션 고려
            
            ---
            
            **🎯 목표가와 손절가 설정 원리**
            
            **📈 목표가 (Target Price):**
            - 최근 20일 변동성을 기준으로 계산
            - 1차 목표가: 변동성 × 1.5배
            - 2차 목표가: 변동성 × 2.5배
            - 단계별 수익 실현 전략 권장
            
            **🛡️ 손절가 (Stop Loss):**
            - 변동성 × 1.0배 하락 지점
            - 추가 손실 방지를 위한 안전장치
            - 감정적 판단보다 기계적 실행 중요
            
            ---
            
            **⚠️ 신호 해석 시 주의사항**
            
            1. **단일 지표 의존 금지**: 여러 지표 종합 판단
            2. **시장 상황 고려**: 전체 시장 흐름과 함께 분석
            3. **거래량 확인**: 신호와 함께 거래량 증가 여부 확인
            4. **리스크 관리**: 손절가 설정으로 위험 관리
            5. **분할 매매**: 한 번에 모든 자금 투입 금지
            """)
        
        with tab4:
            st.markdown("""
            ### 💡 현명한 투자를 위한 가이드
            
            **🏗️ 투자 포트폴리오 구성 원칙**
            
            **📊 자산 배분 전략:**
            - **핵심 자산 (50-60%)**: 안정적인 대형주, ETF
            - **성장 자산 (20-30%)**: 중소형 성장주
            - **투기 자산 (10-20%)**: 고위험 고수익 종목
            - **현금 (5-10%)**: 기회 포착용 대기자금
            
            **⏰ 시간 분산 투자:**
            - 정기적 적립식 투자로 시점 리스크 분산
            - 일시 투자보다 꾸준한 적립이 유리
            - 하락장에서도 꾸준히 매수하는 인내심
            
            ---
            
            **🧠 심리적 함정 피하기**
            
            **😰 공포와 탐욕의 함정:**
            - **공포**: 하락 시 패닉 매도 금지
            - **탐욕**: 상승 시 과도한 추격매수 금지
            - **FOMO**: 남들이 산다고 무작정 따라하기 금지
            
            **📈 장기 관점 유지:**
            - 단기 변동에 일희일비하지 않기
            - 기업의 본질적 가치에 집중
            - 시장 타이밍보다 시간의 힘 활용
            
            ---
            
            **📚 지속적인 학습의 중요성**
            
            **📰 정보 수집:**
            - 기업 재무제표 읽기 능력 배양
            - 산업 동향 및 경제 지표 파악
            - 다양한 관점의 분석 리포트 참고
            
            **🔄 투자 일지 작성:**
            - 매매 이유와 결과 기록
            - 실수에서 배우는 학습 태도
            - 전략 수정 및 개선 지속
            
            ---
            
            **🚨 투자 시 절대 금기사항**
            
            1. **💳 빚내서 투자**: 절대 금지
            2. **🎰 한 종목 올인**: 분산투자 필수
            3. **📰 소문만 믿고 투자**: 직접 분석 후 투자
            4. **😤 감정적 매매**: 계획된 전략 준수
            5. **⏰ 단타 중독**: 장기 관점 유지
            6. **📊 무작정 따라하기**: 본인만의 투자 철학 구축
            
            **✅ 기억하세요: 투자는 마라톤이지 단거리 달리기가 아닙니다!**
            """)
        
        # 추가 도움말 섹션
        st.markdown("---")
        
        with st.expander("❓ 자주 묻는 질문 (FAQ)", expanded=False):
            st.markdown("""
            **Q1: 언제 매수하는 것이 좋나요?**
            A: 여러 지표가 동시에 매수 신호를 보내고, 거래량이 증가할 때입니다. 특히 RSI가 30 이하에서 반등하거나, 골든크로스가 발생할 때 주목하세요.
            
            **Q2: 손절가를 꼭 지켜야 하나요?**
            A: 네, 매우 중요합니다. 감정에 휘둘리지 않고 기계적으로 실행하는 것이 장기적으로 수익에 도움됩니다.
            
            **Q3: 모든 지표가 다른 신호를 보내면 어떻게 하나요?**
            A: 이런 경우 관망하는 것이 좋습니다. 명확한 신호가 나올 때까지 기다리세요.
            
            **Q4: 공정가치 점수가 낮아도 주가가 오를 수 있나요?**
            A: 네, 가능합니다. 시장은 항상 합리적이지 않으며, 단기적으로는 감정이나 이슈에 따라 움직일 수 있습니다.
            
            **Q5: 업종 비교에서 평균보다 낮으면 무조건 매수인가요?**
            A: 아닙니다. 업종 전체가 하락 추세일 수도 있으므로, 절대적 지표와 함께 봐야 합니다.
            """)
        
        with st.expander("⚠️ 투자 유의사항 및 면책사항", expanded=False):
            st.markdown("""
            **🚨 중요한 면책사항**
            
            이 대시보드에서 제공하는 모든 정보와 분석은:
            
            1. **교육 목적**으로만 제공됩니다
            2. **투자 권유나 추천이 아닙니다**
            3. **투자 결정은 본인의 책임**입니다
            4. **과거 데이터 기반 분석**으로 미래를 보장하지 않습니다
            
            **💰 투자 시 유의사항**
            
            - 잃어도 괜찮은 여유자금으로만 투자하세요
            - 투자 전 충분한 공부와 분석을 하세요
            - 분산투자로 리스크를 관리하세요
            - 본인만의 투자 원칙을 세우고 지키세요
            
            **📊 데이터 정확성 안내**
            
            - 현재 Yahoo Finance 데이터 사용 (15-20분 지연)
            - 실시간 매매에는 실시간 데이터를 별도로 확인하세요
            - 시스템 오류나 데이터 오류 가능성 항상 존재
            
            **🤝 향후 개선 계획**
            
            - 한국투자증권 API 연동으로 실시간 데이터 제공 예정
            - 더 많은 기술적 지표와 분석 기능 추가 예정
            - 사용자 피드백을 반영한 지속적인 개선
            """)
        
        # 기존 기본 정보는 삭제하고 위의 상세한 탭 구조로 대체
    
    # 데이터가 비어있는 경우 처리
    if data.empty:
        error_message = "{} 데이터를 불러올 수 없습니다. 다른 종목을 선택해 주세요.".format(selected_name)
        st.error(error_message)
    
    # 푸터
    st.markdown("---")
    
    # 푸터 정보를 3개 컬럼으로 구성
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.markdown("""
        **📊 데이터 소스**
        - 한국투자증권 API (실시간)
        - Yahoo Finance (15-20분 지연)
        - 실시간 호가창 제공
        """)
    
    with footer_col2:
        st.markdown("""
        **🔧 주요 기능**
        - 5가지 기술적 지표 분석
        - 업종별 비교 분석
        - 매매 신호 및 목표가 제시
        """)
    
    with footer_col3:
        st.markdown("""
        **⚠️ 투자 유의사항**
        - 교육용 도구입니다
        - 투자 결정은 신중히 하세요
        - 분산투자를 권장합니다
        """)
    
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #888; font-size: 0.9em;'>"
        "💼 Smart Trading Dashboard v4.0 | "
        "🤖 AI 기반 종합 투자 분석 도구 | "
        "📈 여러분의 현명한 투자를 응원합니다"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()