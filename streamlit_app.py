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
    """pykrx 사용 불가시 주요 종목 리스트 (확장된 버전)"""
    return {
        # 대형주 (시가총액 상위)
        "삼성전자 (005930)": "005930.KS",
        "SK하이닉스 (000660)": "000660.KS", 
        "NAVER (035420)": "035420.KS",
        "카카오 (035720)": "035720.KS",
        "LG에너지솔루션 (373220)": "373220.KS",
        "삼성바이오로직스 (207940)": "207940.KS",
        "POSCO홀딩스 (005490)": "005490.KS",
        "LG화학 (051910)": "051910.KS",
        "현대차 (005380)": "005380.KS",
        "기아 (000270)": "000270.KS",
        
        # 금융주
        "삼성물산 (028260)": "028260.KS",
        "KB금융 (105560)": "105560.KS",
        "신한지주 (055550)": "055550.KS",
        "하나금융지주 (086790)": "086790.KS",
        "우리금융지주 (316140)": "316140.KS",
        "NH투자증권 (005940)": "005940.KS",
        
        # IT/통신
        "셀트리온 (068270)": "068270.KS",
        "LG전자 (066570)": "066570.KS",
        "삼성SDI (006400)": "006400.KS",
        "SK텔레콤 (017670)": "017670.KS",
        "KT (030200)": "030200.KS",
        "LG유플러스 (032640)": "032640.KS",
        
        # 바이오/제약
        "삼성생명 (032830)": "032830.KS",
        "셀트리온헬스케어 (091990)": "091990.KS",
        "삼진제약 (005500)": "005500.KS",
        "유한양행 (000100)": "000100.KS",
        "종근당 (185750)": "185750.KS",
        
        # 화학/소재
        "LG화학 (051910)": "051910.KS",
        "한화솔루션 (009830)": "009830.KS",
        "롯데케미칼 (011170)": "011170.KS",
        "코스모화학 (005420)": "005420.KS",
        
        # 자동차
        "현대차 (005380)": "005380.KS",
        "기아 (000270)": "000270.KS",
        "현대모비스 (012330)": "012330.KS",
        "한국타이어앤테크놀로지 (161390)": "161390.KS",
        
        # 에너지/유틸리티
        "한국전력 (015760)": "015760.KS",
        "SK이노베이션 (096770)": "096770.KS",
        "GS (078930)": "078930.KS",
        "S-Oil (010950)": "010950.KS",
        
        # 건설/부동산
        "현대건설 (000720)": "000720.KS",
        "대우건설 (047040)": "047040.KS",
        "롯데물산 (023150)": "023150.KS",
        
        # 식품/유통
        "농심 (004370)": "004370.KS",
        "오리온 (001800)": "001800.KS",
        "롯데제과 (280360)": "280360.KS",
        "신세계 (004170)": "004170.KS",
        "이마트 (139480)": "139480.KS",
        
        # 항공/운송
        "대한항공 (003490)": "003490.KS",
        "아시아나항공 (020560)": "020560.KS",
        "한진칼 (180640)": "180640.KS",
        
        # 코스닥 주요 종목
        "알테오젠 (196170)": "196170.KQ",
        "에코프로 (086520)": "086520.KQ",
        "에코프로비엠 (247540)": "247540.KQ",
        "원익IPS (240810)": "240810.KQ",
        "엘앤에프 (066970)": "066970.KQ",
        "카카오뱅크 (323410)": "323410.KQ",
        "카카오페이 (377300)": "377300.KQ",
        "크래프톤 (259960)": "259960.KQ",
        "펄어비스 (263750)": "263750.KQ",
        "위메이드 (112040)": "112040.KQ",
        "컴투스 (078340)": "078340.KQ",
        "넷마블 (251270)": "251270.KQ",
        "NHN (181710)": "181710.KQ",
        "두산에너빌리티 (034020)": "034020.KS",
        "포스코퓨처엠 (003670)": "003670.KS",
        "메리츠금융지주 (138040)": "138040.KS",
        "현대글로비스 (086280)": "086280.KS",
        "CJ제일제당 (097950)": "097950.KS",
        "아모레퍼시픽 (090430)": "090430.KS",
        "LG생활건강 (051900)": "051900.KS",
        
        # 추가 종목들 (검색 개선용)
        "삼성화재 (000810)": "000810.KS",
        "삼성카드 (029780)": "029780.KS",
        "SK이노베이션 (096770)": "096770.KS",
        "SK바이오팜 (326030)": "326030.KQ",
        "LG디스플레이 (034220)": "034220.KS",
        "LG이노텍 (011070)": "011070.KS",
        "현대중공업 (009540)": "009540.KS",
        "두산 (000150)": "000150.KS",
        "포스코 (005490)": "005490.KS",
        "한국조선해양 (009540)": "009540.KS",
        "KT&G (033780)": "033780.KS",
        "SK (034730)": "034730.KS",
        "LG (003550)": "003550.KS",
        "GS홀딩스 (078930)": "078930.KS",
        "한화 (000880)": "000880.KS",
        "롯데홀딩스 (004990)": "004990.KS",
        "신세계 (004170)": "004170.KS",
        "현대백화점 (069960)": "069960.KS",
        "롯데쇼핑 (023530)": "023530.KS",
        "CJ (001040)": "001040.KS",
        "LG상사 (001120)": "001120.KS",
        "대우조선해양 (042660)": "042660.KS",
        "한국전력공사 (015760)": "015760.KS",
        "한국가스공사 (036460)": "036460.KS",
        "국민은행 (105560)": "105560.KS",
        "우리은행 (316140)": "316140.KS",
        "KEB하나은행 (086790)": "086790.KS",
        "신한은행 (055550)": "055550.KS",
        "IBK기업은행 (024110)": "024110.KS",
        "카카오게임즈 (293490)": "293490.KQ",
        "셀트리온제약 (068760)": "068760.KQ",
        "바이로메드 (206640)": "206640.KQ",
        "씨젠 (096530)": "096530.KQ",
        "에이치엘비 (028300)": "028300.KQ",
        "마크로젠 (038290)": "038290.KQ",
        "제넥신 (095700)": "095700.KQ",
        "녹십자 (006280)": "006280.KS",
        "유한양행 (000100)": "000100.KS",
        "동아에스티 (170900)": "170900.KS",
        "부광약품 (003000)": "003000.KS",
        "일동제약 (249420)": "249420.KS",
        "한미약품 (128940)": "128940.KS",
        "대웅제약 (069620)": "069620.KS",
        "종근당 (185750)": "185750.KS",
        "유유제약 (000220)": "000220.KS",
        "삼천리 (004690)": "004690.KS",
        "KCC (002380)": "002380.KS",
        "삼성엔지니어링 (028050)": "028050.KS",
        "GS건설 (006360)": "006360.KS",
        "대림산업 (000210)": "000210.KS",
        "태영건설 (009410)": "009410.KS"
    }

@st.cache_data(ttl=3600)  # 1시간 캐시
def get_korean_stocks():
    """한국 주식 목록 가져오기 (전체 종목)"""
    if not PYKRX_AVAILABLE:
        return get_fallback_stocks()
    
    try:
        all_stocks = {}
        
        # KOSPI 전체 종목 (개선된 버전)
        try:
            kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
            for ticker in kospi_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if name and len(name.strip()) > 0:
                        all_stocks["{} ({})".format(name, ticker)] = "{}.KS".format(ticker)
                except:
                    continue
        except Exception as e:
            pass  # KOSPI 실패시 계속 진행
        
        # KOSDAQ 전체 종목 (개선된 버전) 
        try:
            kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
            for ticker in kosdaq_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if name and len(name.strip()) > 0:
                        all_stocks["{} ({})".format(name, ticker)] = "{}.KQ".format(ticker)
                except:
                    continue
        except Exception as e:
            pass  # KOSDAQ 실패시 계속 진행
        
        # 데이터가 로드되었으면 반환, 아니면 fallback 사용
        if len(all_stocks) > 0:
            return all_stocks
        else:
            return get_fallback_stocks()
        
    except Exception as e:
        return get_fallback_stocks()

def search_stocks(search_term):
    """종목 검색 함수 (안정화된 버전)"""
    # 빈 검색어 처리
    if not search_term or len(search_term.strip()) < 1:
        # 빈 검색어일 때는 인기 종목 몇 개를 반환
        popular_stocks = [
            "삼성전자 (005930)", "SK하이닉스 (000660)", "NAVER (035420)", 
            "카카오 (035720)", "LG에너지솔루션 (373220)", "삼성바이오로직스 (207940)"
        ]
        return popular_stocks
    
    try:
        search_term = search_term.strip()
        all_stocks = get_korean_stocks()
        
        # 종목 데이터가 없는 경우 기본 리스트에서 검색
        if not all_stocks or len(all_stocks) == 0:
            all_stocks = get_fallback_stocks()
        
        results = []
        exact_matches = []
        partial_matches = []
        
        # 검색어를 소문자로 변환
        search_lower = search_term.lower()
        
        for name, symbol in all_stocks.items():
            try:
                name_lower = name.lower()
                
                # 정확한 매칭 (회사명이나 코드가 정확히 일치)
                if search_lower in name_lower:
                    # 종목코드 직접 검색
                    if search_term in name and "(" in name:
                        exact_matches.append(name)
                    # 회사명 시작 부분 매칭
                    elif name_lower.startswith(search_lower):
                        exact_matches.append(name)
                    # 부분 매칭
                    else:
                        partial_matches.append(name)
            except:
                continue  # 개별 종목 처리 오류시 건너뛰기
        
        # 정확한 매칭을 먼저, 그 다음 부분 매칭
        results = exact_matches[:10] + partial_matches[:10]
        
        # 결과가 없으면 유사한 종목 추천
        if len(results) == 0:
            # 부분적으로라도 매칭되는 종목 찾기
            for name in all_stocks.keys():
                if any(char in name.lower() for char in search_lower):
                    results.append(name)
                    if len(results) >= 5:
                        break
        
        # 최대 20개까지 반환
        return results[:20]
        
    except Exception as e:
        # 최종 fallback: 기본 종목들
        basic_stocks = [
            "삼성전자 (005930)", "SK하이닉스 (000660)", "NAVER (035420)", 
            "카카오 (035720)", "LG에너지솔루션 (373220)"
        ]
        if search_term:
            return [stock for stock in basic_stocks if search_term.lower() in stock.lower()]
        return basic_stocks[:3]

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
            **🎯 국내 전 종목 검색으로 공정가치 분석, 업종 비교, 매매 신호를 확인하세요!**  
            🔍 **KOSPI + KOSDAQ 전 종목 지원** | 📊 5가지 기술적 지표 종합 분석 | 🏭 동종업계 비교 | 🚦 실시간 매매 신호
            """)
        with col_intro2:
            if st.button("📚 사용법 보기", help="대시보드 사용법과 투자 가이드를 확인하세요"):
                st.info("👇 화면 하단의 '📚 투자 용어 가이드' 섹션을 확인해주세요!")
    
    st.markdown("---")
    
    # 사이드바
    st.sidebar.header("🔍 종목 선택")
    st.sidebar.markdown("🚀 **전체 종목 검색 가능** (KOSPI + KOSDAQ)")
    
    # 검색 상태 표시
    with st.sidebar.container():
        stocks_count = len(get_korean_stocks())
        if stocks_count > 100:
            st.sidebar.success(f"✅ {stocks_count:,}개 종목 로드 완료")
        elif stocks_count > 50:
            st.sidebar.info(f"ℹ️ {stocks_count}개 주요 종목 사용 중")
        else:
            st.sidebar.warning(f"⚠️ 기본 {stocks_count}개 종목만 사용 가능")
    
    st.sidebar.markdown("💡 **검색 방법:**")
    st.sidebar.markdown("- 회사명: 삼성전자, LG전자, 카카오")
    st.sidebar.markdown("- 종목코드: 005930, 035420, 035720")
    st.sidebar.markdown("- 영문명: NAVER, SK Hynix")
    st.sidebar.markdown("- 부분검색: 삼성, LG, 현대")
    
    # 종목 검색
    try:
        selected_name = st_searchbox(
            search_function=search_stocks,
            placeholder="🔍 회사명 또는 종목코드로 검색 (예: 삼성전자, 005930)",
            key="stock_searchbox",
            clear_on_submit=False,
            rerun_on_update=True
        )
    except Exception as e:
        st.sidebar.error(f"검색박스 오류: {e}")
        # 기본 선택박스로 fallback
        all_stocks_list = list(get_korean_stocks().keys())[:50]  # 상위 50개만
        selected_name = st.sidebar.selectbox(
            "종목 선택",
            options=all_stocks_list,
            index=0 if len(all_stocks_list) > 0 else None
        )
    
    # 디버그 정보 표시 (더 안정화된 버전)
    with st.sidebar.expander("🔧 디버그 정보", expanded=False):
        try:
            st.write("**시스템 상태:**")
            st.write(f"• pykrx 사용 가능: {PYKRX_AVAILABLE}")
            
            all_stocks_debug = get_korean_stocks()
            st.write(f"• 로드된 종목 수: {len(all_stocks_debug)}")
            
            if len(all_stocks_debug) > 0:
                st.write("**샘플 종목 (처음 5개):**")
                for i, (name, symbol) in enumerate(list(all_stocks_debug.items())[:5]):
                    st.write(f"{i+1}. {name} → {symbol}")
                
                # 검색 테스트
                st.write("**검색 테스트:**")
                test_queries = ["삼성", "LG", "005930"]
                for query in test_queries:
                    test_results = search_stocks(query)
                    st.write(f"'{query}' → {len(test_results)}개 결과")
                    if len(test_results) > 0:
                        st.write(f"  예: {test_results[0]}")
            else:
                st.error("❌ 종목 데이터 로드 실패!")
                fallback = get_fallback_stocks()
                st.write(f"• Fallback 종목 수: {len(fallback)}")
                
            # 현재 선택된 종목 표시
            if selected_name:
                st.write(f"**현재 선택:** {selected_name}")
                
        except Exception as e:
            st.error(f"디버그 정보 표시 오류: {e}")
            st.write("기본 검색 기능을 사용합니다.")
    
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
        
        # 현재 가격 정보 (전체 탭에서 사용)
        current_price = data['Close'].iloc[-1] if not data.empty else 0
        
        # 탭 구조로 콘텐츠 분리
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 차트 분석", 
            "⚖️ 공정가치 분석", 
            "🏭 업종 비교", 
            "🚦 매매 신호", 
            "📚 투자 가이드"
        ])
        
        with tab1:
            st.subheader("📊 주가 차트 및 기술적 지표")
            chart = create_candlestick_chart(data, selected_name)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # 기술적 지표 요약
            if not data.empty:
                latest = data.iloc[-1]
                
                st.markdown("### 📈 주요 기술적 지표")
                
                col_tech1, col_tech2, col_tech3, col_tech4 = st.columns(4)
                
                with col_tech1:
                    rsi_value = latest['RSI'] if 'RSI' in latest and not pd.isna(latest['RSI']) else 0
                    if rsi_value > 70:
                        rsi_status = "과매수"
                        rsi_color = "🔴"
                    elif rsi_value < 30:
                        rsi_status = "과매도"
                        rsi_color = "🟢"
                    else:
                        rsi_status = "중립"
                        rsi_color = "🟡"
                    st.metric("RSI", f"{rsi_value:.1f}", f"{rsi_color} {rsi_status}")
                
                with col_tech2:
                    macd = latest['MACD'] if 'MACD' in latest and not pd.isna(latest['MACD']) else 0
                    macd_signal = latest['MACD_Signal'] if 'MACD_Signal' in latest and not pd.isna(latest['MACD_Signal']) else 0
                    macd_diff = macd - macd_signal
                    macd_status = "상승" if macd_diff > 0 else "하락"
                    macd_color = "🟢" if macd_diff > 0 else "🔴"
                    st.metric("MACD", f"{macd:.2f}", f"{macd_color} {macd_status}")
                
                with col_tech3:
                    ma20 = latest['MA_20'] if 'MA_20' in latest and not pd.isna(latest['MA_20']) else current_price
                    ma_ratio = ((current_price / ma20 - 1) * 100) if ma20 > 0 else 0
                    ma_status = "돌파" if ma_ratio > 0 else "이탈"
                    ma_color = "🟢" if ma_ratio > 0 else "🔴"
                    st.metric("MA20 대비", f"{ma_ratio:+.1f}%", f"{ma_color} {ma_status}")
                
                with col_tech4:
                    bb_upper = latest['BB_Upper'] if 'BB_Upper' in latest and not pd.isna(latest['BB_Upper']) else current_price
                    bb_lower = latest['BB_Lower'] if 'BB_Lower' in latest and not pd.isna(latest['BB_Lower']) else current_price
                    if bb_upper > bb_lower:
                        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100
                        if bb_position > 80:
                            bb_status = "상단"
                            bb_color = "🔴"
                        elif bb_position < 20:
                            bb_status = "하단"
                            bb_color = "🟢"
                        else:
                            bb_status = "중간"
                            bb_color = "🟡"
                        st.metric("볼린저밴드", f"{bb_position:.0f}%", f"{bb_color} {bb_status}")
                    else:
                        st.metric("볼린저밴드", "N/A", "🔄 계산중")
        
        with tab2:
            st.subheader("⚖️ 공정가치 분석")
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
                    if macd_score > 0:
                        st.markdown("• MACD 상승 신호")
                    elif macd_score < 0:
                        st.markdown("• MACD 하락 신호")
                    else:
                        st.markdown("• MACD 중립")
        
        with tab3:
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
            else:
                st.info("📊 업종 비교 분석: {}".format(industry_analysis['message']))
                st.markdown("**참고:** 충분한 데이터가 확보되면 동종업계 대비 상대적 위치를 분석하여 제공합니다.")
        
        with tab4:
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
                    st.metric(
                        "신호 강도",
                        "{:.1f}".format(abs(trading_signals['signal_strength'])),
                        help="매매 신호의 강도 (0-10, 높을수록 강함)"
                    )
                
                with col_signal3:
                    st.metric(
                        "신뢰도",
                        "{:.1f}%".format(trading_signals['confidence']),
                        help="신호의 신뢰도 (60% 이상 권장)"
                    )
                
                with col_signal4:
                    st.metric(
                        "위험도",
                        trading_signals['risk_level'],
                        help="현재 시장 상황의 위험도"
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
            else:
                st.info("🚦 매매 신호 분석: {}".format(trading_signals['message']))
        
        with tab5:
            st.subheader("📚 투자 가이드 및 용어 설명")
            
            # 기본 사용법
            with st.expander("🚀 대시보드 사용법", expanded=True):
                st.markdown("""
                **📈 Smart Trading Dashboard 활용 가이드**
                
                1. **종목 선택**: 상단 검색창에서 관심 종목을 검색하고 선택하세요
                2. **차트 분석**: 첫 번째 탭에서 가격 차트와 기술적 지표를 확인하세요
                3. **공정가치**: 두 번째 탭에서 AI 기반 종합 분석 점수를 확인하세요
                4. **업종 비교**: 세 번째 탭에서 동종업계 대비 상대적 위치를 파악하세요
                5. **매매 신호**: 네 번째 탭에서 구체적인 매매 타이밍과 목표가를 확인하세요
                
                **🎯 투자 의사결정 프로세스:**
                - 모든 탭의 정보를 종합적으로 검토
                - 70점 이상의 공정가치 점수와 60% 이상의 신호 신뢰도 확인
                - 개인의 투자 목표와 리스크 허용도 고려
                """)
            
            # 기술적 지표 설명
            with st.expander("📊 기술적 지표 설명"):
                st.markdown("""
                **RSI (Relative Strength Index)**
                - 의미: 상대강도지수, 과매수/과매도 판단
                - 해석: 70 이상(과매수), 30 이하(과매도), 30-70(중립)
                
                **MACD (Moving Average Convergence Divergence)**
                - 의미: 이동평균수렴확산지수, 추세 변화 감지
                - 해석: MACD > Signal(상승), MACD < Signal(하락)
                
                **볼린저 밴드 (Bollinger Bands)**
                - 의미: 가격의 변동성과 상대적 고저 판단
                - 해석: 상단 터치(고점권), 하단 터치(저점권)
                
                **이동평균선 (Moving Average)**
                - 의미: 일정 기간 평균가격, 추세 방향 확인
                - 해석: 가격 > 이평선(상승), 가격 < 이평선(하락)
                """)
            
            # 투자 원칙
            with st.expander("💡 성공적인 투자를 위한 원칙"):
                st.markdown("""
                **🎯 기본 투자 원칙**
                
                1. **분산투자**: 한 종목에 집중하지 말고 여러 종목에 분산
                2. **장기투자**: 단기 변동에 휩쓸리지 말고 장기적 관점 유지
                3. **리스크 관리**: 손절매 기준을 정하고 철저히 준수
                4. **감정 제어**: 욕심과 공포를 제어하고 원칙에 따라 투자
                5. **지속적 학습**: 시장과 기업에 대한 지식을 꾸준히 습득
                
                **📚 투자 전 체크리스트**
                
                ✅ 기업의 사업 모델과 경쟁력 이해
                ✅ 재무상태와 성장성 검토
                ✅ 기술적 지표와 차트 패턴 분석
                ✅ 시장 상황과 업종 동향 파악
                ✅ 개인의 투자 목표와 기간 설정
                ✅ 리스크 관리 방안 수립
                """)
            
            # 면책사항
            with st.expander("⚠️ 투자 유의사항 및 면책사항"):
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
                """)
            
            # 추가 기능 안내
            with st.expander("🔮 향후 개선 계획"):
                st.markdown("""
                **🚀 예정된 업데이트**
                
                - 한국투자증권 API 연동으로 실시간 데이터 제공
                - 더 많은 기술적 지표와 분석 기능 추가
                - 포트폴리오 관리 기능
                - 백테스팅 및 성과 분석 도구
                - 뉴스 및 공시 정보 연동
                - 사용자 피드백을 반영한 지속적인 개선
                
                **💬 피드백 및 제안**
                
                여러분의 소중한 의견을 기다립니다!
                GitHub Issues를 통해 버그 신고나 기능 제안을 해주세요.
                """)
            
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
