"""
Streamlit Cloud용 간단한 알고리즘 트레이딩 대시보드
데이터베이스 없이 실시간 데이터로 작동
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta
import warnings
from streamlit_searchbox import st_searchbox

# 경고 메시지 숨기기
warnings.filterwarnings('ignore')

# 페이지 설정
st.set_page_config(
    page_title="📊 Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# pykrx import with error handling for Streamlit Cloud
PYKRX_AVAILABLE = False
stock = None

try:
    import pykrx.stock as stock
    PYKRX_AVAILABLE = True
except ImportError:
    pass  # pykrx 없이도 동작하도록 설계됨

# 캐시 함수들
@st.cache_data(ttl=3600)  # 1시간 캐시 (종목 리스트는 자주 변하지 않음)
def get_all_korean_stocks():
    """한국거래소 전체 종목 리스트 가져오기"""
    if not PYKRX_AVAILABLE or stock is None:
        # pykrx가 없으면 기본 종목들 반환 (주요 50개 종목)
        return {
            # 대형주 (시가총액 상위)
            "삼성전자 (005930)": "005930.KS",
            "SK하이닉스 (000660)": "000660.KS", 
            "NAVER (035420)": "035420.KS",
            "카카오 (035720)": "035720.KS",
            "LG에너지솔루션 (373220)": "373220.KS",
            "현대차 (005380)": "005380.KS",
            "기아 (000270)": "000270.KS",
            "삼성바이오로직스 (207940)": "207940.KS",
            "POSCO홀딩스 (005490)": "005490.KS",
            "LG화학 (051910)": "051910.KS",
            
            # 금융주
            "KB금융 (105560)": "105560.KS",
            "신한지주 (055550)": "055550.KS",
            "하나금융지주 (086790)": "086790.KS",
            "우리금융지주 (316140)": "316140.KS",
            "삼성화재 (000810)": "000810.KS",
            
            # 통신주
            "SK텔레콤 (017670)": "017670.KS",
            "KT (030200)": "030200.KS",
            "LG유플러스 (032640)": "032640.KS",
            
            # 화학/소재
            "LG화학 (051910)": "051910.KS",
            "한화솔루션 (009830)": "009830.KS",
            "롯데케미칼 (011170)": "011170.KS",
            "코오롱인더 (120110)": "120110.KS",
            
            # 바이오/제약
            "셀트리온 (068270)": "068270.KS",
            "삼성바이오로직스 (207940)": "207940.KS",
            "유한양행 (000100)": "000100.KS",
            "종근당 (185750)": "185750.KS",
            
            # 코스닥 대표주
            "에코프로비엠 (247540)": "247540.KQ",
            "에코프로 (086520)": "086520.KQ",
            "알테오젠 (196170)": "196170.KQ",
            "펄어비스 (263750)": "263750.KQ",
            "위메이드 (112040)": "112040.KQ",
            
            # 게임주
            "엔씨소프트 (036570)": "036570.KS",
            "넷마블 (251270)": "251270.KS",
            "위메이드 (112040)": "112040.KQ",
            
            # 항공/운송
            "대한항공 (003490)": "003490.KS",
            "아시아나항공 (020560)": "020560.KS",
            "HMM (011200)": "011200.KS",
            
            # 유통/소비재
            "신세계 (004170)": "004170.KS",
            "롯데쇼핑 (023530)": "023530.KS",
            "이마트 (139480)": "139480.KS",
            
            # 건설/부동산
            "삼성물산 (028260)": "028260.KS",
            "현대건설 (000720)": "000720.KS",
            "GS건설 (006360)": "006360.KS",
            
            # 식품/음료
            "농심 (004370)": "004370.KS",
            "오뚜기 (007310)": "007310.KS",
            "하이트진로 (000080)": "000080.KS",
            
            # 엔터테인먼트
            "SM (041510)": "041510.KQ",
            "YG엔터테인먼트 (122870)": "122870.KQ",
            "JYP Ent. (035900)": "035900.KQ"
        }
    
    try:
        today = datetime.now().strftime('%Y%m%d')
        
        # 코스피, 코스닥 종목 리스트 가져오기
        kospi_tickers = stock.get_market_ticker_list(today, market='KOSPI')
        kosdaq_tickers = stock.get_market_ticker_list(today, market='KOSDAQ')
        
        all_stocks = {}
        
        # 코스피 종목들 추가
        for ticker in kospi_tickers:
            try:
                name = stock.get_market_ticker_name(ticker)
                all_stocks[f"{name} ({ticker})"] = f"{ticker}.KS"
            except:
                continue
                
        # 코스닥 종목들 추가  
        for ticker in kosdaq_tickers:
            try:
                name = stock.get_market_ticker_name(ticker)
                all_stocks[f"{name} ({ticker})"] = f"{ticker}.KQ"
            except:
                continue
                
        return all_stocks
    except Exception as e:
        # 실패시 기본 종목들 반환
        return {
            "삼성전자 (005930)": "005930.KS",
            "SK하이닉스 (000660)": "000660.KS", 
            "NAVER (035420)": "035420.KS",
            "카카오 (035720)": "035720.KS",
            "LG에너지솔루션 (373220)": "373220.KS",
            "현대차 (005380)": "005380.KS",
            "기아 (000270)": "000270.KS",
            "삼성바이오로직스 (207940)": "207940.KS",
            "POSCO홀딩스 (005490)": "005490.KS",
            "LG화학 (051910)": "051910.KS"
        }

def search_stocks(search_term, all_stocks):
    """고급 종목 검색 함수 - 종목명, 코드, 초성 검색 지원"""
    if not search_term:
        # 검색어가 없으면 인기 종목들 반환
        popular_stocks = [
            "삼성전자 (005930)", "SK하이닉스 (000660)", "NAVER (035420)", 
            "카카오 (035720)", "LG에너지솔루션 (373220)", "현대차 (005380)",
            "기아 (000270)", "삼성바이오로직스 (207940)", "POSCO홀딩스 (005490)", "LG화학 (051910)"
        ]
        return [stock for stock in popular_stocks if stock in all_stocks]
    
    search_term = search_term.lower().strip()
    exact_matches = []      # 정확 매치
    partial_matches = []    # 부분 매치
    code_matches = []       # 코드 매치
    
    for stock_name in all_stocks.keys():
        stock_lower = stock_name.lower()
        
        # 코드에서 괄호 제거
        code_part = stock_name.split('(')[-1].replace(')', '').lower()
        name_part = stock_name.split('(')[0].strip().lower()
        
        # 1. 정확한 종목명 매치 (최고 우선순위)
        if name_part == search_term:
            exact_matches.append(stock_name)
        
        # 2. 정확한 코드 매치 (높은 우선순위)
        elif code_part == search_term:
            code_matches.append(stock_name)
        
        # 3. 종목명 시작 매치 (중간 우선순위)
        elif name_part.startswith(search_term):
            partial_matches.insert(0, stock_name)
        
        # 4. 코드 시작 매치
        elif code_part.startswith(search_term):
            code_matches.append(stock_name)
        
        # 5. 종목명 포함 매치 (낮은 우선순위)
        elif search_term in name_part:
            partial_matches.append(stock_name)
        
        # 6. 코드 포함 매치
        elif search_term in code_part:
            code_matches.append(stock_name)
    
    # 우선순위에 따라 결과 합치기
    results = exact_matches + code_matches + partial_matches
    
    # 중복 제거하면서 순서 유지
    seen = set()
    final_results = []
    for item in results:
        if item not in seen:
            seen.add(item)
            final_results.append(item)
            
        # 최대 20개 결과만 반환 (성능 최적화)
        if len(final_results) >= 20:
            break
    
    return final_results

@st.cache_data(ttl=3600)  # 1시간 캐시
def get_industry_classification():
    """업종별 종목 분류"""
    return {
        '반도체': ['005930', '000660', '042700', '357780', '403870', '095340', '067310', '058470'],
        'IT서비스': ['035420', '035720', '181710', '376300', '122870', '053800', '041190'],
        '자동차': ['005380', '000270', '012330', '161390', '018880', '086280', '030200'],
        '화학': ['051910', '009830', '011170', '001060', '064350', '003550', '005420'],
        '바이오': ['207940', '326030', '068270', '145720', '196170', '008930'],
        '금융': ['105560', '055550', '086790', '000810', '032830', '138930'],
        '엔터테인먼트': ['035900', '122870', '041440', '263750', '299900'],
        '이차전지': ['373220', '096770', '006400', '051910', '003490'],
        '조선': ['009540', '010140', '034020', '067630'],
        '철강': ['005490', '000020', '014820', '016360'],
        '건설': ['028260', '006360', '036460', '000720'],
        '유통': ['282330', '051600', '000120', '161890'],
        '통신': ['017670', '030200', '032640'],
        '게임': ['251270', '112040', '263750', '078340'],
        '항공': ['003490', '020560', '034230'],
        '해운': ['028670', '096770', '011200'],
        '석유화학': ['011170', '010950', '009830'],
        '식품': ['007310', '004370', '001680', '097950'],
        'REIT': ['351330', '448730', '357120'],
        '전력': ['015760', '001570', '009540']
    }

def get_stock_industry(stock_code):
    """종목 코드로 업종 찾기"""
    industry_map = get_industry_classification()
    
    # 종목 코드에서 숫자만 추출
    code_only = stock_code.replace('.KS', '').replace('.KQ', '')
    
    for industry, codes in industry_map.items():
        if code_only in codes:
            return industry
    
    return "기타"

@st.cache_data(ttl=300)  # 5분 캐시
def get_stock_data(symbol, period="1y"):
    """주식 데이터 조회 - 조용한 에러 처리"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data
    except Exception:
        # 에러 시 빈 데이터프레임 반환 (메시지 없음)
        return pd.DataFrame()

@st.cache_data(ttl=300)
def calculate_technical_indicators(data):
    """고급 기술적 지표 계산 - 적정가 분석용"""
    if data.empty:
        return data
    
    # 기본 이동평균선
    data['MA_5'] = data['Close'].rolling(window=5).mean()
    data['MA_10'] = data['Close'].rolling(window=10).mean()
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_60'] = data['Close'].rolling(window=60).mean()
    data['MA_120'] = data['Close'].rolling(window=120).mean()
    
    # RSI (14일)
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = data['Close'].ewm(span=12).mean()
    ema_26 = data['Close'].ewm(span=26).mean()
    data['MACD'] = ema_12 - ema_26
    data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
    data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
    
    # 볼린저 밴드 (20일)
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
    data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
    data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Middle'] * 100
    data['BB_Position'] = (data['Close'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower']) * 100
    
    # 스토캐스틱
    lowest_low = data['Low'].rolling(window=14).min()
    highest_high = data['High'].rolling(window=14).max()
    data['Stoch_K'] = ((data['Close'] - lowest_low) / (highest_high - lowest_low)) * 100
    data['Stoch_D'] = data['Stoch_K'].rolling(window=3).mean()
    
    # 거래량 지표
    data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
    data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
    
    # 변동성 지표 (Average True Range)
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    data['ATR'] = true_range.rolling(window=14).mean()
    
    # 가격 모멘텀
    data['Price_Change_1D'] = data['Close'].pct_change(1) * 100
    data['Price_Change_5D'] = data['Close'].pct_change(5) * 100
    data['Price_Change_20D'] = data['Close'].pct_change(20) * 100
    
    return data

def analyze_fair_value(data, current_price):
    """종합 적정가 분석 - 다중 지표 기반"""
    if data.empty or len(data) < 120:
        return {
            'fair_value_score': 50,
            'recommendation': '데이터 부족',
            'confidence': 0,
            'analysis': {},
            'reasons': ['충분한 데이터가 없습니다']
        }
    
    latest = data.iloc[-1]
    analysis = {}
    
    # 1. 이동평균 분석 (가중치: 25%)
    ma_score = 0
    ma_analysis = []
    
    if current_price > latest['MA_5']:
        ma_score += 20
        ma_analysis.append("단기 상승 추세 (5일선 상회)")
    if current_price > latest['MA_20']:
        ma_score += 30
        ma_analysis.append("중기 상승 추세 (20일선 상회)")
    if current_price > latest['MA_60']:
        ma_score += 30
        ma_analysis.append("장기 상승 추세 (60일선 상회)")
    if current_price > latest['MA_120']:
        ma_score += 20
        ma_analysis.append("초장기 상승 추세 (120일선 상회)")
    
    analysis['moving_average'] = {
        'score': ma_score,
        'analysis': ma_analysis,
        'current_vs_ma20': ((current_price / latest['MA_20']) - 1) * 100
    }
    
    # 2. RSI 분석 (가중치: 20%)
    rsi = latest['RSI']
    if rsi < 30:
        rsi_score = 80
        rsi_status = "과매도 (매수 기회)"
    elif rsi < 45:
        rsi_score = 70
        rsi_status = "약간 과매도"
    elif rsi > 70:
        rsi_score = 20
        rsi_status = "과매수 (매도 신호)"
    elif rsi > 55:
        rsi_score = 30
        rsi_status = "약간 과매수"
    else:
        rsi_score = 50
        rsi_status = "중립"
    
    analysis['rsi'] = {
        'score': rsi_score,
        'value': rsi,
        'status': rsi_status
    }
    
    # 3. 볼린저 밴드 분석 (가중치: 20%)
    bb_position = latest['BB_Position']
    if bb_position < 20:
        bb_score = 80
        bb_status = "하단 근접 (매수 기회)"
    elif bb_position < 40:
        bb_score = 60
        bb_status = "하단권"
    elif bb_position > 80:
        bb_score = 20
        bb_status = "상단 근접 (매도 신호)"
    elif bb_position > 60:
        bb_score = 40
        bb_status = "상단권"
    else:
        bb_score = 50
        bb_status = "중간권"
    
    analysis['bollinger_bands'] = {
        'score': bb_score,
        'position': bb_position,
        'status': bb_status,
        'width': latest['BB_Width']
    }
    
    # 4. MACD 분석 (가중치: 15%)
    macd_score = 50
    macd_analysis = []
    
    if latest['MACD'] > latest['MACD_Signal']:
        macd_score += 25
        macd_analysis.append("MACD 상승 신호")
    if latest['MACD_Histogram'] > 0:
        macd_score += 25
        macd_analysis.append("모멘텀 증가")
    
    analysis['macd'] = {
        'score': macd_score,
        'analysis': macd_analysis,
        'histogram': latest['MACD_Histogram']
    }
    
    # 5. 스토캐스틱 분석 (가중치: 10%)
    stoch_k = latest['Stoch_K']
    if stoch_k < 20:
        stoch_score = 80
        stoch_status = "과매도"
    elif stoch_k > 80:
        stoch_score = 20
        stoch_status = "과매수"
    else:
        stoch_score = 50
        stoch_status = "중립"
    
    analysis['stochastic'] = {
        'score': stoch_score,
        'k_value': stoch_k,
        'status': stoch_status
    }
    
    # 6. 거래량 분석 (가중치: 10%)
    volume_ratio = latest['Volume_Ratio']
    if volume_ratio > 2:
        volume_score = 70
        volume_status = "높은 관심"
    elif volume_ratio > 1.5:
        volume_score = 60
        volume_status = "관심 증가"
    elif volume_ratio < 0.5:
        volume_score = 40
        volume_status = "관심 저조"
    else:
        volume_score = 50
        volume_status = "보통"
    
    analysis['volume'] = {
        'score': volume_score,
        'ratio': volume_ratio,
        'status': volume_status
    }
    
    # 종합 점수 계산 (가중 평균)
    weights = {
        'moving_average': 0.25,
        'rsi': 0.20,
        'bollinger_bands': 0.20,
        'macd': 0.15,
        'stochastic': 0.10,
        'volume': 0.10
    }
    
    fair_value_score = sum(analysis[key]['score'] * weights[key] for key in weights.keys())
    
    # 추천 등급 결정
    if fair_value_score >= 70:
        recommendation = "매수"
        confidence = min(95, (fair_value_score - 70) * 3 + 70)
    elif fair_value_score >= 55:
        recommendation = "약매수"
        confidence = min(85, (fair_value_score - 55) * 2 + 60)
    elif fair_value_score <= 30:
        recommendation = "매도"
        confidence = min(95, (30 - fair_value_score) * 3 + 70)
    elif fair_value_score <= 45:
        recommendation = "약매도"
        confidence = min(85, (45 - fair_value_score) * 2 + 60)
    else:
        recommendation = "중립/관망"
        confidence = 50
    
    # 주요 근거 생성
    reasons = []
    if analysis['moving_average']['score'] >= 70:
        reasons.append("이동평균선 상승 배열")
    if analysis['rsi']['score'] >= 70:
        reasons.append(f"RSI 과매도 ({rsi:.1f})")
    if analysis['bollinger_bands']['score'] >= 70:
        reasons.append("볼린저밴드 하단권")
    if analysis['macd']['score'] >= 70:
        reasons.append("MACD 상승 신호")
    
    if analysis['rsi']['score'] <= 30:
        reasons.append(f"RSI 과매수 ({rsi:.1f})")
    if analysis['bollinger_bands']['score'] <= 30:
        reasons.append("볼린저밴드 상단권")
    if analysis['moving_average']['score'] <= 30:
        reasons.append("이동평균선 하락 배열")
    
    if not reasons:
        reasons.append("지표들이 중립적 신호")
    
    return {
        'fair_value_score': round(fair_value_score, 1),
        'recommendation': recommendation,
        'confidence': round(confidence, 1),
        'analysis': analysis,
        'reasons': reasons
    }

def analyze_industry_comparison(selected_symbol, current_data):
    """동종업계 밸류에이션 비교 분석"""
    try:
        # 현재 종목의 업종 확인
        industry = get_stock_industry(selected_symbol)
        if industry == "기타":
            return {
                'industry': '분류 없음',
                'comparison_available': False,
                'message': '업종 분류 정보가 없습니다.'
            }
        
        # 동종업계 종목들 가져오기
        industry_map = get_industry_classification()
        peer_codes = industry_map.get(industry, [])
        
        # 현재 종목 제외
        current_code = selected_symbol.replace('.KS', '').replace('.KQ', '')
        peer_codes = [code for code in peer_codes if code != current_code]
        
        if len(peer_codes) < 2:
            return {
                'industry': industry,
                'comparison_available': False,
                'message': '비교할 동종업계 종목이 부족합니다.'
            }
        
        # 현재 종목 지표 계산
        if current_data.empty or len(current_data) < 60:
            return {
                'industry': industry,
                'comparison_available': False,
                'message': '현재 종목 데이터가 부족합니다.'
            }
        
        current_latest = current_data.iloc[-1]
        current_metrics = {
            'price': current_latest['Close'],
            'rsi': current_latest['RSI'],
            'ma20_ratio': current_latest['Close'] / current_latest['MA_20'],
            'bb_position': current_latest['BB_Position'],
            'volume_ratio': current_latest['Volume_Ratio'],
            'price_change_20d': current_latest['Price_Change_20D']
        }
        
        # 동종업계 종목들 데이터 수집
        peer_metrics = []
        successful_peers = []
        
        for peer_code in peer_codes[:6]:  # 최대 6개 동종업계 종목
            try:
                # KS/KQ 구분
                if peer_code in ['005930', '000660', '035420', '035720', '005380', '000270', '051910', '207940', '005490']:
                    peer_symbol = f"{peer_code}.KS"
                else:
                    peer_symbol = f"{peer_code}.KQ"
                
                peer_data = get_stock_data(peer_symbol, '6mo')
                if not peer_data.empty and len(peer_data) >= 60:
                    peer_data = calculate_technical_indicators(peer_data)
                    peer_latest = peer_data.iloc[-1]
                    
                    peer_metrics.append({
                        'code': peer_code,
                        'symbol': peer_symbol,
                        'price': peer_latest['Close'],
                        'rsi': peer_latest['RSI'],
                        'ma20_ratio': peer_latest['Close'] / peer_latest['MA_20'],
                        'bb_position': peer_latest['BB_Position'],
                        'volume_ratio': peer_latest['Volume_Ratio'],
                        'price_change_20d': peer_latest['Price_Change_20D']
                    })
                    successful_peers.append(peer_code)
            except:
                continue
        
        if len(peer_metrics) < 2:
            return {
                'industry': industry,
                'comparison_available': False,
                'message': '동종업계 데이터 수집에 실패했습니다.'
            }
        
        # 업종 평균 계산
        industry_avg = {
            'rsi': np.mean([p['rsi'] for p in peer_metrics if not np.isnan(p['rsi'])]),
            'ma20_ratio': np.mean([p['ma20_ratio'] for p in peer_metrics if not np.isnan(p['ma20_ratio'])]),
            'bb_position': np.mean([p['bb_position'] for p in peer_metrics if not np.isnan(p['bb_position'])]),
            'volume_ratio': np.mean([p['volume_ratio'] for p in peer_metrics if not np.isnan(p['volume_ratio'])]),
            'price_change_20d': np.mean([p['price_change_20d'] for p in peer_metrics if not np.isnan(p['price_change_20d'])])
        }
        
        # 상대적 위치 분석
        comparison_score = 50  # 기본 점수
        comparison_analysis = []
        
        # RSI 비교
        rsi_diff = current_metrics['rsi'] - industry_avg['rsi']
        if rsi_diff < -10:
            comparison_score += 15
            comparison_analysis.append(f"RSI가 업종 평균보다 {abs(rsi_diff):.1f}p 낮음 (매수 우위)")
        elif rsi_diff > 10:
            comparison_score -= 15
            comparison_analysis.append(f"RSI가 업종 평균보다 {rsi_diff:.1f}p 높음 (과매수 주의)")
        
        # 20일선 대비 비교
        ma20_diff = (current_metrics['ma20_ratio'] - industry_avg['ma20_ratio']) * 100
        if ma20_diff > 2:
            comparison_score += 10
            comparison_analysis.append(f"20일선 대비 위치가 업종 평균보다 {ma20_diff:.1f}%p 높음")
        elif ma20_diff < -2:
            comparison_score -= 10
            comparison_analysis.append(f"20일선 대비 위치가 업종 평균보다 {abs(ma20_diff):.1f}%p 낮음")
        
        # 볼린저밴드 위치 비교
        bb_diff = current_metrics['bb_position'] - industry_avg['bb_position']
        if bb_diff < -15:
            comparison_score += 10
            comparison_analysis.append(f"볼린저밴드 위치가 업종 평균보다 {abs(bb_diff):.1f}%p 낮음 (매수 기회)")
        elif bb_diff > 15:
            comparison_score -= 10
            comparison_analysis.append(f"볼린저밴드 위치가 업종 평균보다 {bb_diff:.1f}%p 높음")
        
        # 20일 수익률 비교
        return_diff = current_metrics['price_change_20d'] - industry_avg['price_change_20d']
        if return_diff > 3:
            comparison_score += 5
            comparison_analysis.append(f"20일 수익률이 업종 평균보다 {return_diff:.1f}%p 높음 (상대 강세)")
        elif return_diff < -3:
            comparison_score -= 5
            comparison_analysis.append(f"20일 수익률이 업종 평균보다 {abs(return_diff):.1f}%p 낮음 (상대 약세)")
        
        # 상대적 추천 등급
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
            'industry': industry,
            'comparison_available': True,
            'peer_count': len(peer_metrics),
            'comparison_score': round(comparison_score, 1),
            'relative_recommendation': relative_recommendation,
            'current_metrics': current_metrics,
            'industry_avg': industry_avg,
            'comparison_analysis': comparison_analysis,
            'peer_codes': successful_peers[:5]  # 최대 5개만 표시
        }
        
    except Exception as e:
        return {
            'industry': '분석 오류',
            'comparison_available': False,
            'message': f'분석 중 오류가 발생했습니다: {str(e)}'
        }

def analyze_overbought_oversold(data, current_price):
    """고도화된 과매수/과매도 판단 시스템"""
    if data.empty or len(data) < 120:
        return {
            'signal_strength': 0,
            'signal_type': '데이터 부족',
            'confidence': 0,
            'detailed_analysis': {},
            'recommendations': ['충분한 데이터가 없습니다']
        }
    
    latest = data.iloc[-1]
    detailed_analysis = {}
    
    # 1. RSI 기반 분석 (가중치: 30%)
    rsi = latest['RSI']
    rsi_score = 0
    rsi_signal = "중립"
    
    if rsi <= 20:
        rsi_score = 90
        rsi_signal = "극도 과매도"
    elif rsi <= 30:
        rsi_score = 75
        rsi_signal = "과매도"
    elif rsi <= 40:
        rsi_score = 60
        rsi_signal = "약한 과매도"
    elif rsi >= 80:
        rsi_score = -90
        rsi_signal = "극도 과매수"
    elif rsi >= 70:
        rsi_score = -75
        rsi_signal = "과매수"
    elif rsi >= 60:
        rsi_score = -60
        rsi_signal = "약한 과매수"
    
    detailed_analysis['rsi'] = {
        'value': rsi,
        'score': rsi_score,
        'signal': rsi_signal,
        'weight': 0.30
    }
    
    # 2. 스토캐스틱 분석 (가중치: 20%)
    stoch_k = latest['Stoch_K']
    stoch_d = latest['Stoch_D']
    stoch_score = 0
    stoch_signal = "중립"
    
    if stoch_k <= 15 and stoch_d <= 15:
        stoch_score = 85
        stoch_signal = "극도 과매도"
    elif stoch_k <= 20 and stoch_d <= 20:
        stoch_score = 70
        stoch_signal = "과매도"
    elif stoch_k <= 30:
        stoch_score = 50
        stoch_signal = "약한 과매도"
    elif stoch_k >= 85 and stoch_d >= 85:
        stoch_score = -85
        stoch_signal = "극도 과매수"
    elif stoch_k >= 80 and stoch_d >= 80:
        stoch_score = -70
        stoch_signal = "과매수"
    elif stoch_k >= 70:
        stoch_score = -50
        stoch_signal = "약한 과매수"
    
    detailed_analysis['stochastic'] = {
        'k_value': stoch_k,
        'd_value': stoch_d,
        'score': stoch_score,
        'signal': stoch_signal,
        'weight': 0.20
    }
    
    # 3. 볼린저 밴드 분석 (가중치: 25%)
    bb_position = latest['BB_Position']
    bb_width = latest['BB_Width']
    bb_score = 0
    bb_signal = "중립"
    
    # 볼린저 밴드 폭 고려 (좁을수록 돌파 가능성 높음)
    width_factor = 1.0
    if bb_width < 5:  # 매우 좁은 밴드
        width_factor = 1.3
    elif bb_width < 8:  # 좁은 밴드
        width_factor = 1.1
    
    if bb_position <= 5:
        bb_score = 80 * width_factor
        bb_signal = "극도 과매도 (하단 이탈)"
    elif bb_position <= 15:
        bb_score = 65 * width_factor
        bb_signal = "과매도 (하단권)"
    elif bb_position <= 25:
        bb_score = 45
        bb_signal = "약한 과매도"
    elif bb_position >= 95:
        bb_score = -80 * width_factor
        bb_signal = "극도 과매수 (상단 이탈)"
    elif bb_position >= 85:
        bb_score = -65 * width_factor
        bb_signal = "과매수 (상단권)"
    elif bb_position >= 75:
        bb_score = -45
        bb_signal = "약한 과매수"
    
    detailed_analysis['bollinger_bands'] = {
        'position': bb_position,
        'width': bb_width,
        'score': bb_score,
        'signal': bb_signal,
        'width_factor': width_factor,
        'weight': 0.25
    }
    
    # 4. 이동평균 편향 분석 (가중치: 15%)
    ma5_ratio = current_price / latest['MA_5']
    ma20_ratio = current_price / latest['MA_20']
    ma60_ratio = current_price / latest['MA_60']
    
    ma_score = 0
    ma_signal = "중립"
    
    # 이동평균선들과의 괴리율 계산
    ma5_deviation = (ma5_ratio - 1) * 100
    ma20_deviation = (ma20_ratio - 1) * 100
    ma60_deviation = (ma60_ratio - 1) * 100
    
    avg_deviation = (ma5_deviation + ma20_deviation + ma60_deviation) / 3
    
    if avg_deviation <= -15:
        ma_score = 70
        ma_signal = "이동평균선 대비 극도 과매도"
    elif avg_deviation <= -8:
        ma_score = 50
        ma_signal = "이동평균선 대비 과매도"
    elif avg_deviation <= -3:
        ma_score = 25
        ma_signal = "이동평균선 대비 약한 과매도"
    elif avg_deviation >= 15:
        ma_score = -70
        ma_signal = "이동평균선 대비 극도 과매수"
    elif avg_deviation >= 8:
        ma_score = -50
        ma_signal = "이동평균선 대비 과매수"
    elif avg_deviation >= 3:
        ma_score = -25
        ma_signal = "이동평균선 대비 약한 과매수"
    
    detailed_analysis['moving_average'] = {
        'ma5_deviation': ma5_deviation,
        'ma20_deviation': ma20_deviation,
        'ma60_deviation': ma60_deviation,
        'avg_deviation': avg_deviation,
        'score': ma_score,
        'signal': ma_signal,
        'weight': 0.15
    }
    
    # 5. 거래량 확산 분석 (가중치: 10%)
    volume_ratio = latest['Volume_Ratio']
    volume_score = 0
    volume_signal = "보통"
    
    if volume_ratio >= 3:
        volume_score = 20  # 높은 거래량은 신호 강화
        volume_signal = "매우 높은 거래량 (신호 강화)"
    elif volume_ratio >= 2:
        volume_score = 15
        volume_signal = "높은 거래량 (신호 강화)"
    elif volume_ratio >= 1.5:
        volume_score = 10
        volume_signal = "증가된 거래량"
    elif volume_ratio <= 0.5:
        volume_score = -10
        volume_signal = "낮은 거래량 (신호 약화)"
    
    detailed_analysis['volume'] = {
        'ratio': volume_ratio,
        'score': volume_score,
        'signal': volume_signal,
        'weight': 0.10
    }
    
    # 종합 신호 강도 계산
    weighted_score = (
        detailed_analysis['rsi']['score'] * detailed_analysis['rsi']['weight'] +
        detailed_analysis['stochastic']['score'] * detailed_analysis['stochastic']['weight'] +
        detailed_analysis['bollinger_bands']['score'] * detailed_analysis['bollinger_bands']['weight'] +
        detailed_analysis['moving_average']['score'] * detailed_analysis['moving_average']['weight'] +
        detailed_analysis['volume']['score'] * detailed_analysis['volume']['weight']
    )
    
    # 신호 타입 및 강도 결정
    signal_strength = abs(weighted_score)
    
    if weighted_score >= 60:
        signal_type = "강력 매수 신호"
        confidence = min(95, signal_strength + 20)
    elif weighted_score >= 40:
        signal_type = "매수 신호"
        confidence = min(90, signal_strength + 15)
    elif weighted_score >= 20:
        signal_type = "약한 매수 신호"
        confidence = min(75, signal_strength + 10)
    elif weighted_score <= -60:
        signal_type = "강력 매도 신호"
        confidence = min(95, signal_strength + 20)
    elif weighted_score <= -40:
        signal_type = "매도 신호"
        confidence = min(90, signal_strength + 15)
    elif weighted_score <= -20:
        signal_type = "약한 매도 신호"
        confidence = min(75, signal_strength + 10)
    else:
        signal_type = "중립 (관망)"
        confidence = 50
    
    # 추천 사항 생성
    recommendations = []
    
    if weighted_score >= 60:
        recommendations.append("🟢 적극적인 매수 타이밍입니다")
        recommendations.append("📈 여러 지표가 강한 과매도 신호를 보입니다")
        if detailed_analysis['volume']['score'] > 10:
            recommendations.append("📊 높은 거래량으로 신호가 더욱 신뢰할 만합니다")
    elif weighted_score >= 20:
        recommendations.append("🟡 매수를 고려해볼 시점입니다")
        recommendations.append("📊 일부 지표에서 과매도 신호가 나타납니다")
    elif weighted_score <= -60:
        recommendations.append("🔴 매도를 고려해야 할 시점입니다")
        recommendations.append("📉 여러 지표가 강한 과매수 신호를 보입니다")
        if detailed_analysis['volume']['score'] > 10:
            recommendations.append("📊 높은 거래량으로 하락 압력이 클 수 있습니다")
    elif weighted_score <= -20:
        recommendations.append("🟠 매도를 검토해볼 시점입니다")
        recommendations.append("📊 일부 지표에서 과매수 신호가 나타납니다")
    else:
        recommendations.append("⚪ 현재는 관망하는 것이 좋겠습니다")
        recommendations.append("📊 지표들이 중립적인 신호를 보입니다")
    
    # 주의사항 추가
    if detailed_analysis['bollinger_bands']['width'] < 5:
        recommendations.append("⚠️ 볼린저밴드가 매우 좁아 큰 변동성이 예상됩니다")
    
    if detailed_analysis['volume']['ratio'] < 0.5:
        recommendations.append("⚠️ 거래량이 적어 신호의 신뢰도가 떨어질 수 있습니다")
    
    return {
        'signal_strength': round(signal_strength, 1),
        'signal_type': signal_type,
        'confidence': round(confidence, 1),
        'weighted_score': round(weighted_score, 1),
        'detailed_analysis': detailed_analysis,
        'recommendations': recommendations
    }

def generate_advanced_trading_signals(data):
    """고도화된 매매 타이밍 신호 생성"""
    if data.empty or len(data) < 60:
        return {
            'signals': [],
            'trend_analysis': {},
            'support_resistance': {},
            'pattern_recognition': {},
            'timeframe_analysis': {}
        }
    
    latest = data.iloc[-1]
    signals = []
    
    # === 1. 트렌드 분석 ===
    trend_analysis = analyze_trend_signals(data)
    
    # === 2. 지지/저항선 분석 ===
    support_resistance = analyze_support_resistance(data)
    
    # === 3. 패턴 인식 ===
    pattern_recognition = analyze_chart_patterns(data)
    
    # === 4. 다중 시간프레임 분석 ===
    timeframe_analysis = analyze_multiple_timeframes(data)
    
    # === 5. 종합 신호 생성 ===
    comprehensive_signals = generate_comprehensive_signals(
        data, trend_analysis, support_resistance, 
        pattern_recognition, timeframe_analysis
    )
    
    return {
        'signals': comprehensive_signals,
        'trend_analysis': trend_analysis,
        'support_resistance': support_resistance,
        'pattern_recognition': pattern_recognition,
        'timeframe_analysis': timeframe_analysis
    }

def analyze_trend_signals(data):
    """트렌드 전환점 및 추세 강도 분석"""
    if len(data) < 60:
        return {}
    
    latest = data.iloc[-1]
    recent_20 = data.tail(20)
    recent_5 = data.tail(5)
    
    # 이동평균 배열 분석
    ma5_trend = 1 if latest['MA_5'] > data.iloc[-2]['MA_5'] else -1
    ma20_trend = 1 if latest['MA_20'] > data.iloc[-2]['MA_20'] else -1
    ma60_trend = 1 if latest['MA_60'] > data.iloc[-2]['MA_60'] else -1
    
    # 트렌드 강도 계산 (0-100)
    price_above_ma5 = (latest['Close'] > latest['MA_5'])
    price_above_ma20 = (latest['Close'] > latest['MA_20']) 
    price_above_ma60 = (latest['Close'] > latest['MA_60'])
    ma_alignment = (latest['MA_5'] > latest['MA_20'] > latest['MA_60'])
    
    trend_strength = 0
    if price_above_ma5: trend_strength += 25
    if price_above_ma20: trend_strength += 25
    if price_above_ma60: trend_strength += 25
    if ma_alignment: trend_strength += 25
    
    # 트렌드 방향 결정
    if trend_strength >= 75:
        trend_direction = "강한 상승추세"
        trend_signal = "매수"
    elif trend_strength >= 50:
        trend_direction = "상승추세"
        trend_signal = "매수"
    elif trend_strength <= 25:
        trend_direction = "강한 하락추세"
        trend_signal = "매도"
    elif trend_strength <= 50:
        trend_direction = "하락추세"
        trend_signal = "매도"
    else:
        trend_direction = "횡보"
        trend_signal = "관망"
    
    # 트렌드 전환 신호
    reversal_signals = []
    
    # 골든크로스/데드크로스 감지
    if latest['MA_5'] > latest['MA_20'] and data.iloc[-2]['MA_5'] <= data.iloc[-2]['MA_20']:
        reversal_signals.append("골든크로스 (5일선 > 20일선)")
    elif latest['MA_5'] < latest['MA_20'] and data.iloc[-2]['MA_5'] >= data.iloc[-2]['MA_20']:
        reversal_signals.append("데드크로스 (5일선 < 20일선)")
    
    # 가격 모멘텀 변화
    recent_momentum = (latest['Close'] - recent_5.iloc[0]['Close']) / recent_5.iloc[0]['Close'] * 100
    
    return {
        'trend_direction': trend_direction,
        'trend_strength': trend_strength,
        'trend_signal': trend_signal,
        'ma5_trend': ma5_trend,
        'ma20_trend': ma20_trend,
        'ma60_trend': ma60_trend,
        'reversal_signals': reversal_signals,
        'recent_momentum': round(recent_momentum, 2)
    }

def analyze_support_resistance(data):
    """지지선/저항선 분석 및 돌파 신호"""
    if len(data) < 60:
        return {}
    
    recent_60 = data.tail(60)
    latest = data.iloc[-1]
    
    # 최근 고점/저점 찾기
    highs = recent_60['High'].rolling(window=5, center=True).max()
    lows = recent_60['Low'].rolling(window=5, center=True).min()
    
    # 지지선/저항선 계산 (최근 20일 기준)
    recent_20 = data.tail(20)
    resistance_level = recent_20['High'].max()
    support_level = recent_20['Low'].min()
    
    # 현재가 대비 지지/저항선 거리 (%)
    resistance_distance = ((resistance_level - latest['Close']) / latest['Close']) * 100
    support_distance = ((latest['Close'] - support_level) / latest['Close']) * 100
    
    # 돌파 신호 감지
    breakout_signals = []
    
    # 저항선 돌파 (상승 돌파)
    if latest['Close'] > resistance_level and latest['Volume'] > recent_20['Volume'].mean() * 1.5:
        breakout_signals.append({
            'type': '저항선 돌파',
            'signal': '매수',
            'strength': 'high',
            'description': f'저항선 {resistance_level:.0f}원 돌파 (거래량 급증)'
        })
    
    # 지지선 이탈 (하락 돌파)
    elif latest['Close'] < support_level and latest['Volume'] > recent_20['Volume'].mean() * 1.5:
        breakout_signals.append({
            'type': '지지선 이탈',
            'signal': '매도',
            'strength': 'high', 
            'description': f'지지선 {support_level:.0f}원 이탈 (거래량 급증)'
        })
    
    # 지지선 근접 매수 기회
    elif support_distance <= 2 and latest['RSI'] < 40:
        breakout_signals.append({
            'type': '지지선 근접',
            'signal': '매수 관심',
            'strength': 'medium',
            'description': f'지지선 {support_level:.0f}원 근접 + RSI 과매도'
        })
    
    # 저항선 근접 매도 기회  
    elif resistance_distance <= 2 and latest['RSI'] > 60:
        breakout_signals.append({
            'type': '저항선 근접',
            'signal': '매도 관심',
            'strength': 'medium',
            'description': f'저항선 {resistance_level:.0f}원 근접 + RSI 과매수'
        })
    
    return {
        'resistance_level': resistance_level,
        'support_level': support_level,
        'resistance_distance': round(resistance_distance, 2),
        'support_distance': round(support_distance, 2),
        'breakout_signals': breakout_signals
    }

def analyze_chart_patterns(data):
    """차트 패턴 인식 (삼각형, 쐐기형 등)"""
    if len(data) < 60:
        return {}
    
    recent_20 = data.tail(20)
    latest = data.iloc[-1]
    
    patterns = []
    
    # === 삼각형 패턴 감지 ===
    highs = recent_20['High']
    lows = recent_20['Low']
    
    # 상승삼각형: 고점은 수평, 저점은 상승
    if len(highs) >= 10 and len(lows) >= 10:
        high_values = highs.iloc[-10:].values
        low_values = lows.iloc[-10:].values
        time_index = np.arange(10)
        
        # correlation 계산
        high_trend = np.corrcoef(high_values, time_index)[0, 1] if len(set(high_values)) > 1 else 0
        low_trend = np.corrcoef(low_values, time_index)[0, 1] if len(set(low_values)) > 1 else 0
    else:
        high_trend = 0
        low_trend = 0
    
    if abs(high_trend) < 0.3 and low_trend > 0.5:
        patterns.append({
            'pattern': '상승삼각형',
            'signal': '매수 준비',
            'strength': 'medium',
            'description': '고점은 수평선 형성, 저점은 지속 상승'
        })
    
    # 하락삼각형: 저점은 수평, 고점은 하락
    elif abs(low_trend) < 0.3 and high_trend < -0.5:
        patterns.append({
            'pattern': '하락삼각형',
            'signal': '매도 준비',
            'strength': 'medium',
            'description': '저점은 수평선 형성, 고점은 지속 하락'
        })
    
    # === 쐐기형 패턴 감지 ===
    if high_trend < -0.3 and low_trend > 0.3:
        # 상승 쐐기형 (하락 신호)
        patterns.append({
            'pattern': '상승 쐐기형',
            'signal': '매도 신호',
            'strength': 'medium',
            'description': '고점과 저점이 모두 상승하나 고점 상승폭이 둔화'
        })
    elif high_trend > 0.3 and low_trend < -0.3:
        # 하락 쐐기형 (상승 신호)
        patterns.append({
            'pattern': '하락 쐐기형', 
            'signal': '매수 신호',
            'strength': 'medium',
            'description': '고점과 저점이 모두 하락하나 저점 하락폭이 둔화'
        })
    
    # === 이중천정/이중바닥 패턴 ===
    if len(recent_20) >= 20:
        # 최근 고점들 찾기
        peak_indices = []
        for i in range(2, len(recent_20)-2):
            if (recent_20.iloc[i]['High'] > recent_20.iloc[i-1]['High'] and 
                recent_20.iloc[i]['High'] > recent_20.iloc[i-2]['High'] and
                recent_20.iloc[i]['High'] > recent_20.iloc[i+1]['High'] and
                recent_20.iloc[i]['High'] > recent_20.iloc[i+2]['High']):
                peak_indices.append(i)
        
        # 이중천정 패턴 확인
        if len(peak_indices) >= 2:
            last_peak = recent_20.iloc[peak_indices[-1]]['High']
            second_last_peak = recent_20.iloc[peak_indices[-2]]['High']
            if abs(last_peak - second_last_peak) / second_last_peak < 0.03:  # 3% 이내 유사
                patterns.append({
                    'pattern': '이중천정',
                    'signal': '매도 신호',
                    'strength': 'high',
                    'description': f'유사한 고점 {last_peak:.0f}원 형성 후 하락 가능성'
                })
    
    return {
        'patterns': patterns,
        'pattern_count': len(patterns)
    }

def analyze_multiple_timeframes(data):
    """다중 시간프레임 분석 (일봉 기준)"""
    if len(data) < 60:
        return {}
    
    # 단기 (5일), 중기 (20일), 장기 (60일) 분석
    timeframes = {
        'short_term': analyze_timeframe_signals(data, 5),
        'medium_term': analyze_timeframe_signals(data, 20), 
        'long_term': analyze_timeframe_signals(data, 60)
    }
    
    # 시간프레임 간 일치도 계산
    signals = [timeframes['short_term']['signal'], 
              timeframes['medium_term']['signal'],
              timeframes['long_term']['signal']]
    
    buy_count = signals.count('매수')
    sell_count = signals.count('매도')
    
    if buy_count >= 2:
        consensus = '매수'
        consensus_strength = buy_count / 3
    elif sell_count >= 2:
        consensus = '매도'
        consensus_strength = sell_count / 3
    else:
        consensus = '중립'
        consensus_strength = 0.33
    
    return {
        'timeframes': timeframes,
        'consensus': consensus,
        'consensus_strength': round(consensus_strength * 100, 1)
    }

def analyze_timeframe_signals(data, period):
    """특정 기간 시간프레임 신호 분석"""
    if len(data) < period * 2:
        return {'signal': '중립', 'strength': 0, 'details': []}
    
    recent_data = data.tail(period)
    latest = data.iloc[-1]
    
    # 해당 기간 수익률
    period_return = ((latest['Close'] - recent_data.iloc[0]['Close']) / recent_data.iloc[0]['Close']) * 100
    
    # RSI 평균
    avg_rsi = recent_data['RSI'].mean()
    
    # 이동평균 관계
    ma_signal = 0
    if period >= 5 and 'MA_5' in latest:
        if latest['Close'] > latest['MA_5']: ma_signal += 1
    if period >= 20 and 'MA_20' in latest:
        if latest['Close'] > latest['MA_20']: ma_signal += 1
    if period >= 60 and 'MA_60' in latest:
        if latest['Close'] > latest['MA_60']: ma_signal += 1
    
    # 종합 신호 결정
    details = []
    if period_return > 5:
        signal = '매수'
        details.append(f"{period}일 수익률 +{period_return:.1f}%")
    elif period_return < -5:
        signal = '매도'
        details.append(f"{period}일 수익률 {period_return:.1f}%")
    else:
        signal = '중립'
        details.append(f"{period}일 수익률 {period_return:.1f}%")
    
    if avg_rsi < 35:
        details.append(f"평균 RSI {avg_rsi:.1f} (과매도)")
    elif avg_rsi > 65:
        details.append(f"평균 RSI {avg_rsi:.1f} (과매수)")
    
    strength = min(100, abs(period_return) * 10 + ma_signal * 20)
    
    return {
        'signal': signal,
        'strength': round(strength, 1),
        'period_return': round(period_return, 2),
        'avg_rsi': round(avg_rsi, 1),
        'details': details
    }

def generate_comprehensive_signals(data, trend_analysis, support_resistance, pattern_recognition, timeframe_analysis):
    """종합적인 매매 신호 생성"""
    signals = []
    latest = data.iloc[-1]
    
    # === 우선순위 기반 신호 생성 ===
    
    # 1. 고우선순위: 저항선/지지선 돌파
    for breakout in support_resistance.get('breakout_signals', []):
        if breakout['strength'] == 'high':
            signals.append({
                'priority': 1,
                'type': '돌파 신호',
                'signal': breakout['signal'],
                'description': breakout['description'],
                'confidence': 90,
                'timeframe': '단기',
                'icon': '🚀' if '매수' in breakout['signal'] else '⬇️'
            })
    
    # 2. 중간우선순위: 트렌드 전환 신호
    if trend_analysis.get('reversal_signals'):
        for reversal in trend_analysis['reversal_signals']:
            signal_type = '매수' if '골든크로스' in reversal else '매도'
            signals.append({
                'priority': 2,
                'type': '트렌드 전환',
                'signal': signal_type,
                'description': reversal,
                'confidence': 75,
                'timeframe': '중기',
                'icon': '📈' if signal_type == '매수' else '📉'
            })
    
    # 3. 패턴 기반 신호
    for pattern in pattern_recognition.get('patterns', []):
        if pattern['strength'] == 'high':
            signals.append({
                'priority': 2,
                'type': '차트 패턴',
                'signal': pattern['signal'],
                'description': f"{pattern['pattern']}: {pattern['description']}",
                'confidence': 80,
                'timeframe': '중기',
                'icon': '📊'
            })
    
    # 4. 다중 시간프레임 합의 신호
    consensus = timeframe_analysis.get('consensus', '중립')
    consensus_strength = timeframe_analysis.get('consensus_strength', 0)
    
    if consensus != '중립' and consensus_strength >= 67:  # 2/3 이상 합의
        signals.append({
            'priority': 3,
            'type': '시간프레임 합의',
            'signal': consensus,
            'description': f"단기/중기/장기 시간프레임에서 {consensus_strength}% 합의",
            'confidence': int(consensus_strength),
            'timeframe': '종합',
            'icon': '🎯'
        })
    
    # 5. 트렌드 추종 신호
    if trend_analysis.get('trend_strength', 0) >= 75:
        trend_signal = trend_analysis['trend_signal']
        if trend_signal != '관망':
            signals.append({
                'priority': 4,
                'type': '트렌드 추종',
                'signal': trend_signal,
                'description': f"{trend_analysis['trend_direction']} (강도: {trend_analysis['trend_strength']}%)",
                'confidence': int(trend_analysis['trend_strength']),
                'timeframe': '장기',
                'icon': '📊'
            })
    
    # 우선순위별 정렬
    signals.sort(key=lambda x: (x['priority'], -x['confidence']))
    
    return signals[:5]  # 상위 5개 신호만 반환

def calculate_risk_assessment(data, current_price, investment_amount=1000000):
    """위험도 평가 및 포지션 관리 시스템"""
    if data.empty or len(data) < 60:
        return {}
    
    latest = data.iloc[-1]
    recent_20 = data.tail(20)
    recent_60 = data.tail(60)
    
    # === 1. 변동성 분석 ===
    volatility_analysis = calculate_volatility_metrics(data)
    
    # === 2. 위험도 점수 계산 ===
    risk_score = calculate_risk_score(data, volatility_analysis)
    
    # === 3. 포지션 크기 제안 ===
    position_sizing = calculate_position_sizing(risk_score, investment_amount, volatility_analysis)
    
    # === 4. 손절매/익절매 가격대 ===
    stop_loss_take_profit = calculate_stop_loss_take_profit(data, current_price, volatility_analysis)
    
    # === 5. 시장 상황별 위험도 조정 ===
    market_condition_risk = assess_market_condition_risk(data)
    
    # === 6. 종합 위험 등급 ===
    overall_risk_grade = determine_risk_grade(risk_score, market_condition_risk)
    
    return {
        'volatility_analysis': volatility_analysis,
        'risk_score': risk_score,
        'position_sizing': position_sizing,
        'stop_loss_take_profit': stop_loss_take_profit,
        'market_condition_risk': market_condition_risk,
        'overall_risk_grade': overall_risk_grade,
        'recommendations': generate_risk_recommendations(overall_risk_grade, position_sizing, stop_loss_take_profit)
    }

def calculate_volatility_metrics(data):
    """변동성 지표 계산"""
    if len(data) < 20:
        return {}
    
    recent_20 = data.tail(20)
    recent_60 = data.tail(60) if len(data) >= 60 else data
    
    # 일일 수익률 계산
    daily_returns = data['Close'].pct_change().dropna()
    
    # 변동성 지표들
    volatility_20d = daily_returns.tail(20).std() * np.sqrt(252) * 100  # 연환산 변동성
    volatility_60d = daily_returns.tail(60).std() * np.sqrt(252) * 100 if len(daily_returns) >= 60 else volatility_20d
    
    # ATR (Average True Range)
    atr_14 = data['ATR'].iloc[-1] if 'ATR' in data.columns else 0
    atr_percentage = (atr_14 / data['Close'].iloc[-1]) * 100
    
    # 볼린저 밴드 폭
    bb_width = ((data['BB_Upper'].iloc[-1] - data['BB_Lower'].iloc[-1]) / data['Close'].iloc[-1]) * 100
    
    # 최대 낙폭 (Maximum Drawdown)
    rolling_max = data['Close'].expanding().max()
    drawdown = ((data['Close'] - rolling_max) / rolling_max * 100)
    max_drawdown = drawdown.min()
    current_drawdown = drawdown.iloc[-1]
    
    # 변동성 등급 결정
    if volatility_20d <= 15:
        volatility_grade = "낮음"
        volatility_color = "🟢"
    elif volatility_20d <= 25:
        volatility_grade = "보통"
        volatility_color = "🟡"
    elif volatility_20d <= 40:
        volatility_grade = "높음"
        volatility_color = "🟠"
    else:
        volatility_grade = "매우 높음"
        volatility_color = "🔴"
    
    return {
        'volatility_20d': round(volatility_20d, 1),
        'volatility_60d': round(volatility_60d, 1),
        'atr_percentage': round(atr_percentage, 2),
        'bb_width': round(bb_width, 2),
        'max_drawdown': round(max_drawdown, 2),
        'current_drawdown': round(current_drawdown, 2),
        'volatility_grade': volatility_grade,
        'volatility_color': volatility_color
    }

def calculate_risk_score(data, volatility_analysis):
    """종합 위험도 점수 계산 (0-100)"""
    latest = data.iloc[-1]
    risk_factors = []
    
    # 1. 변동성 위험 (0-30점)
    volatility_risk = min(30, volatility_analysis['volatility_20d'] * 0.75)
    risk_factors.append(('변동성', volatility_risk))
    
    # 2. 추세 위험 (0-20점) 
    if latest['Close'] < latest['MA_20']:
        trend_risk = 15
        if latest['Close'] < latest['MA_60']:
            trend_risk = 20
    else:
        trend_risk = 5
    risk_factors.append(('추세', trend_risk))
    
    # 3. 거래량 위험 (0-15점)
    volume_ratio = latest['Volume_Ratio']
    if volume_ratio < 0.5:
        volume_risk = 15  # 거래량 부족
    elif volume_ratio > 3:
        volume_risk = 10  # 과도한 거래량
    else:
        volume_risk = 3
    risk_factors.append(('거래량', volume_risk))
    
    # 4. 기술적 지표 위험 (0-20점)
    rsi = latest['RSI']
    bb_position = latest['BB_Position']
    
    technical_risk = 0
    if rsi > 75 or rsi < 25:  # 극단적 RSI
        technical_risk += 10
    if bb_position > 85 or bb_position < 15:  # 볼린저밴드 극단
        technical_risk += 10
    risk_factors.append(('기술적지표', technical_risk))
    
    # 5. 드로다운 위험 (0-15점)
    current_drawdown = abs(volatility_analysis['current_drawdown'])
    drawdown_risk = min(15, current_drawdown * 0.75)
    risk_factors.append(('드로다운', drawdown_risk))
    
    total_risk_score = sum(score for _, score in risk_factors)
    
    return {
        'total_score': round(total_risk_score, 1),
        'risk_factors': risk_factors,
        'max_possible': 100
    }

def calculate_position_sizing(risk_score, investment_amount, volatility_analysis):
    """포지션 크기 계산"""
    base_investment = investment_amount
    
    # 위험도에 따른 포지션 크기 조정
    if risk_score['total_score'] <= 30:
        position_ratio = 0.8  # 낮은 위험: 80%
        risk_level = "낮음"
        color = "🟢"
    elif risk_score['total_score'] <= 50:
        position_ratio = 0.6  # 보통 위험: 60%
        risk_level = "보통"
        color = "🟡"
    elif risk_score['total_score'] <= 70:
        position_ratio = 0.4  # 높은 위험: 40%
        risk_level = "높음"
        color = "🟠"
    else:
        position_ratio = 0.2  # 매우 높은 위험: 20%
        risk_level = "매우 높음"
        color = "🔴"
    
    # 변동성에 따른 추가 조정
    volatility_adjustment = 1.0
    if volatility_analysis['volatility_20d'] > 30:
        volatility_adjustment = 0.8
    elif volatility_analysis['volatility_20d'] > 40:
        volatility_adjustment = 0.6
    
    final_position_ratio = position_ratio * volatility_adjustment
    recommended_amount = int(base_investment * final_position_ratio)
    
    # 포지션 분할 제안
    if final_position_ratio < 0.5:
        split_suggestion = "3회 분할 매수 권장"
        split_amounts = [int(recommended_amount * 0.4), int(recommended_amount * 0.3), int(recommended_amount * 0.3)]
    else:
        split_suggestion = "2회 분할 매수 권장"
        split_amounts = [int(recommended_amount * 0.6), int(recommended_amount * 0.4)]
    
    return {
        'risk_level': risk_level,
        'color': color,
        'position_ratio': round(final_position_ratio * 100, 1),
        'recommended_amount': recommended_amount,
        'split_suggestion': split_suggestion,
        'split_amounts': split_amounts,
        'volatility_adjustment': round(volatility_adjustment, 2)
    }

def calculate_stop_loss_take_profit(data, current_price, volatility_analysis):
    """손절매/익절매 가격대 계산"""
    latest = data.iloc[-1]
    atr = volatility_analysis['atr_percentage']
    
    # ATR 기반 손절매/익절매
    atr_multiplier_sl = 2.0  # 손절매: ATR의 2배
    atr_multiplier_tp1 = 2.5  # 1차 익절: ATR의 2.5배
    atr_multiplier_tp2 = 4.0  # 2차 익절: ATR의 4배
    
    # 지지/저항선 기반 계산
    recent_20 = data.tail(20)
    support_level = recent_20['Low'].min()
    resistance_level = recent_20['High'].max()
    
    # 손절매 가격 (더 보수적인 값 선택)
    atr_stop_loss = current_price * (1 - (atr * atr_multiplier_sl / 100))
    support_stop_loss = support_level * 0.98  # 지지선 2% 아래
    stop_loss_price = max(atr_stop_loss, support_stop_loss)
    
    # 익절매 가격들
    atr_take_profit_1 = current_price * (1 + (atr * atr_multiplier_tp1 / 100))
    atr_take_profit_2 = current_price * (1 + (atr * atr_multiplier_tp2 / 100))
    resistance_take_profit = resistance_level * 1.02  # 저항선 2% 위
    
    take_profit_1 = min(atr_take_profit_1, resistance_take_profit)
    take_profit_2 = atr_take_profit_2
    
    # 손익 비율 계산
    potential_loss = (current_price - stop_loss_price) / current_price * 100
    potential_gain_1 = (take_profit_1 - current_price) / current_price * 100
    potential_gain_2 = (take_profit_2 - current_price) / current_price * 100
    
    risk_reward_1 = potential_gain_1 / potential_loss if potential_loss > 0 else 0
    risk_reward_2 = potential_gain_2 / potential_loss if potential_loss > 0 else 0
    
    return {
        'stop_loss_price': int(stop_loss_price),
        'take_profit_1': int(take_profit_1),
        'take_profit_2': int(take_profit_2),
        'potential_loss': round(potential_loss, 2),
        'potential_gain_1': round(potential_gain_1, 2),
        'potential_gain_2': round(potential_gain_2, 2),
        'risk_reward_1': round(risk_reward_1, 2),
        'risk_reward_2': round(risk_reward_2, 2),
        'stop_loss_method': 'ATR+지지선' if atr_stop_loss > support_stop_loss else '지지선+ATR',
        'take_profit_method': 'ATR+저항선'
    }

def assess_market_condition_risk(data):
    """시장 상황별 위험도 평가"""
    if len(data) < 60:
        return {}
    
    latest = data.iloc[-1]
    recent_5 = data.tail(5)
    recent_20 = data.tail(20)
    
    market_conditions = []
    
    # 1. 추세 안정성
    ma5_slope = (latest['MA_5'] - data.iloc[-5]['MA_5']) / data.iloc[-5]['MA_5'] * 100
    ma20_slope = (latest['MA_20'] - data.iloc[-20]['MA_20']) / data.iloc[-20]['MA_20'] * 100
    
    if abs(ma5_slope) < 1 and abs(ma20_slope) < 2:
        market_conditions.append(("추세 안정성", "안정", "🟢"))
    elif abs(ma5_slope) < 3 and abs(ma20_slope) < 5:
        market_conditions.append(("추세 안정성", "보통", "🟡"))
    else:
        market_conditions.append(("추세 안정성", "불안정", "🔴"))
    
    # 2. 거래량 일관성
    volume_cv = recent_20['Volume'].std() / recent_20['Volume'].mean()  # 변동계수
    if volume_cv < 0.5:
        market_conditions.append(("거래량 일관성", "일관", "🟢"))
    elif volume_cv < 1.0:
        market_conditions.append(("거래량 일관성", "보통", "🟡"))
    else:
        market_conditions.append(("거래량 일관성", "불규칙", "🔴"))
    
    # 3. 가격 변동 패턴
    price_changes = recent_5['Close'].pct_change().dropna()
    if len(price_changes) > 0:
        max_daily_change = abs(price_changes).max() * 100
        if max_daily_change < 3:
            market_conditions.append(("가격 변동", "안정", "🟢"))
        elif max_daily_change < 7:
            market_conditions.append(("가격 변동", "보통", "🟡"))
        else:
            market_conditions.append(("가격 변동", "급격", "🔴"))
    
    # 4. 기술적 신호 일관성
    rsi_trend = "상승" if latest['RSI'] > data.iloc[-5]['RSI'] else "하락"
    ma_trend = "상승" if latest['MA_5'] > latest['MA_20'] else "하락"
    price_trend = "상승" if latest['Close'] > recent_5.iloc[0]['Close'] else "하락"
    
    trend_consistency = sum([rsi_trend == ma_trend, ma_trend == price_trend, price_trend == rsi_trend])
    
    if trend_consistency >= 2:
        market_conditions.append(("신호 일관성", "일관", "🟢"))
    elif trend_consistency == 1:
        market_conditions.append(("신호 일관성", "혼재", "🟡"))
    else:
        market_conditions.append(("신호 일관성", "혼란", "🔴"))
    
    # 전체 시장 상황 평가
    green_count = sum(1 for _, status, color in market_conditions if color == "🟢")
    yellow_count = sum(1 for _, status, color in market_conditions if color == "🟡")
    red_count = sum(1 for _, status, color in market_conditions if color == "🔴")
    
    if green_count >= 3:
        overall_condition = "안정적"
        overall_color = "🟢"
        condition_description = "시장 상황이 안정적이어서 위험도가 낮습니다"
    elif red_count >= 2:
        overall_condition = "불안정"
        overall_color = "🔴"
        condition_description = "시장 상황이 불안정하여 주의가 필요합니다"
    else:
        overall_condition = "보통"
        overall_color = "🟡"
        condition_description = "시장 상황이 혼재되어 있어 신중한 접근이 필요합니다"
    
    return {
        'market_conditions': market_conditions,
        'overall_condition': overall_condition,
        'overall_color': overall_color,
        'condition_description': condition_description,
        'green_count': green_count,
        'yellow_count': yellow_count,
        'red_count': red_count
    }

def determine_risk_grade(risk_score, market_condition_risk):
    """종합 위험 등급 결정"""
    base_score = risk_score['total_score']
    
    # 시장 상황에 따른 조정
    market_adjustment = 0
    if market_condition_risk.get('overall_condition') == '불안정':
        market_adjustment = 15
    elif market_condition_risk.get('overall_condition') == '보통':
        market_adjustment = 5
    
    adjusted_score = min(100, base_score + market_adjustment)
    
    # 위험 등급 결정
    if adjusted_score <= 25:
        risk_grade = "매우 낮음"
        grade_color = "🟢"
        investment_advice = "적극적 투자 가능"
    elif adjusted_score <= 40:
        risk_grade = "낮음"
        grade_color = "🟢"
        investment_advice = "안정적 투자 권장"
    elif adjusted_score <= 55:
        risk_grade = "보통"
        grade_color = "🟡"
        investment_advice = "신중한 투자 필요"
    elif adjusted_score <= 70:
        risk_grade = "높음"
        grade_color = "🟠"
        investment_advice = "소액 투자 권장"
    else:
        risk_grade = "매우 높음"
        grade_color = "🔴"
        investment_advice = "투자 보류 권장"
    
    return {
        'grade': risk_grade,
        'color': grade_color,
        'score': round(adjusted_score, 1),
        'base_score': round(base_score, 1),
        'market_adjustment': market_adjustment,
        'investment_advice': investment_advice
    }

def generate_risk_recommendations(risk_grade, position_sizing, stop_loss_take_profit):
    """위험 관리 추천사항 생성"""
    recommendations = []
    
    # 포지션 크기 기반 추천
    if position_sizing['position_ratio'] <= 30:
        recommendations.append("🚨 고위험 종목으로 소액 투자만 권장합니다")
        recommendations.append(f"📊 {position_sizing['split_suggestion']} - 분할 매수로 위험 분산")
    elif position_sizing['position_ratio'] <= 50:
        recommendations.append("⚠️ 중간 위험도로 신중한 투자가 필요합니다")
        recommendations.append(f"📊 {position_sizing['split_suggestion']} 권장")
    else:
        recommendations.append("✅ 상대적으로 안정적인 투자 기회입니다")
        recommendations.append("📊 계획적인 매수 진행 가능")
    
    # 손익비 기반 추천
    risk_reward_1 = stop_loss_take_profit['risk_reward_1']
    if risk_reward_1 >= 2.0:
        recommendations.append(f"💰 우수한 손익비 {risk_reward_1:.1f}:1 - 매력적인 기회")
    elif risk_reward_1 >= 1.5:
        recommendations.append(f"📈 양호한 손익비 {risk_reward_1:.1f}:1 - 투자 고려 가능")
    else:
        recommendations.append(f"📉 낮은 손익비 {risk_reward_1:.1f}:1 - 신중한 검토 필요")
    
    # 손절매 추천
    if stop_loss_take_profit['potential_loss'] > 8:
        recommendations.append("🛑 손절매 폭이 커서 신중한 진입 필요")
    else:
        recommendations.append("✅ 적절한 손절매 수준으로 위험 관리 용이")
    
    # 시장 상황 기반 추천
    grade = risk_grade['grade']
    if grade in ['매우 높음', '높음']:
        recommendations.append("⏰ 시장 상황 개선 시까지 관망 권장")
        recommendations.append("📱 알림 설정으로 상황 변화 모니터링")
    elif grade == '보통':
        recommendations.append("🎯 엄격한 손절매 준수 필수")
        recommendations.append("📊 포지션 크기 축소 고려")
    else:
        recommendations.append("🚀 좋은 투자 기회 - 계획대로 진행")
        recommendations.append("💪 충분한 여유 자금으로 투자")
    
    return recommendations

def generate_timeframe_specific_signals(data, current_price):
    """단기/중기/장기 투자 기간별 맞춤 신호 제공"""
    if data.empty or len(data) < 60:
        return {}
    
    latest = data.iloc[-1]
    
    # === 1. 스윙 트레이딩 (1-5일) ===
    swing_trading_signals = analyze_swing_trading_signals(data)
    
    # === 2. 포지션 트레이딩 (1-4주) ===
    position_trading_signals = analyze_position_trading_signals(data)
    
    # === 3. 장기 투자 (1-6개월) ===
    long_term_investment_signals = analyze_long_term_investment_signals(data)
    
    # === 4. 시간프레임별 종합 점수 ===
    timeframe_scores = calculate_timeframe_scores(swing_trading_signals, position_trading_signals, long_term_investment_signals)
    
    return {
        'swing_trading': swing_trading_signals,
        'position_trading': position_trading_signals,
        'long_term_investment': long_term_investment_signals,
        'timeframe_scores': timeframe_scores,
        'recommended_strategy': determine_recommended_strategy(timeframe_scores)
    }

def analyze_swing_trading_signals(data):
    """스윙 트레이딩 (1-5일) 신호 분석"""
    if len(data) < 20:
        return {}
    
    latest = data.iloc[-1]
    recent_5 = data.tail(5)
    recent_10 = data.tail(10)
    
    signals = []
    score = 50  # 기본 점수
    
    # 1. 단기 RSI 신호 (가중치: 25%)
    rsi = latest['RSI']
    if rsi < 30:
        signals.append("🟢 RSI 과매도 - 단기 반등 기대")
        score += 15
    elif rsi > 70:
        signals.append("🔴 RSI 과매수 - 단기 조정 위험")
        score -= 15
    elif 45 <= rsi <= 55:
        signals.append("🟡 RSI 중립 - 방향 확인 필요")
    
    # 2. 스토캐스틱 신호 (가중치: 20%)
    stoch_k = latest['Stoch_K']
    if stoch_k < 20:
        signals.append("🟢 스토캐스틱 과매도 - 매수 타이밍")
        score += 12
    elif stoch_k > 80:
        signals.append("🔴 스토캐스틱 과매수 - 매도 타이밍")
        score -= 12
    
    # 3. 볼린저 밴드 신호 (가중치: 20%)
    bb_position = latest['BB_Position']
    if bb_position < 20:
        signals.append("🟢 볼린저밴드 하단 - 매수 관심")
        score += 12
    elif bb_position > 80:
        signals.append("🔴 볼린저밴드 상단 - 매도 관심")
        score -= 12
    
    # 4. 단기 이동평균 신호 (가중치: 15%)
    if latest['Close'] > latest['MA_5']:
        signals.append("🟢 5일선 위 - 단기 상승세")
        score += 8
    else:
        signals.append("🔴 5일선 아래 - 단기 하락세")
        score -= 8
    
    # 5. 거래량 신호 (가중치: 10%)
    volume_ratio = latest['Volume_Ratio']
    if volume_ratio > 1.5:
        signals.append("🟢 거래량 급증 - 변화 신호")
        score += 6
    elif volume_ratio < 0.7:
        signals.append("🟡 거래량 위축 - 관망 필요")
        score -= 3
    
    # 6. 가격 모멘텀 (가중치: 10%)
    price_momentum_3d = ((latest['Close'] - recent_5.iloc[0]['Close']) / recent_5.iloc[0]['Close']) * 100
    if price_momentum_3d > 3:
        signals.append("🟢 3일 상승 모멘텀 강함")
        score += 6
    elif price_momentum_3d < -3:
        signals.append("🔴 3일 하락 모멘텀 강함")
        score -= 6
    
    # 스윙 트레이딩 추천
    if score >= 70:
        recommendation = "적극적 스윙 매수"
        recommendation_color = "🟢"
        time_horizon = "1-3일"
    elif score >= 60:
        recommendation = "스윙 매수 고려"
        recommendation_color = "🟡"
        time_horizon = "2-4일"
    elif score <= 30:
        recommendation = "스윙 매도 고려"
        recommendation_color = "🔴"
        time_horizon = "1-2일"
    elif score <= 40:
        recommendation = "스윙 관망"
        recommendation_color = "🟠"
        time_horizon = "2-3일"
    else:
        recommendation = "스윙 중립"
        recommendation_color = "⚪"
        time_horizon = "3-5일"
    
    return {
        'signals': signals,
        'score': round(score, 1),
        'recommendation': recommendation,
        'recommendation_color': recommendation_color,
        'time_horizon': time_horizon,
        'strategy_description': "단기 기술적 지표 기반 1-5일 스윙 트레이딩"
    }

def analyze_position_trading_signals(data):
    """포지션 트레이딩 (1-4주) 신호 분석"""
    if len(data) < 60:
        return {}
    
    latest = data.iloc[-1]
    recent_20 = data.tail(20)
    recent_60 = data.tail(60)
    
    signals = []
    score = 50  # 기본 점수
    
    # 1. 중기 추세 신호 (가중치: 30%)
    ma20_trend = latest['MA_20'] > data.iloc[-5]['MA_20']
    ma60_trend = latest['MA_60'] > data.iloc[-10]['MA_60']
    
    if ma20_trend and ma60_trend:
        signals.append("🟢 중장기 이동평균 상승 - 상승 추세")
        score += 20
    elif not ma20_trend and not ma60_trend:
        signals.append("🔴 중장기 이동평균 하락 - 하락 추세")
        score -= 20
    else:
        signals.append("🟡 추세 전환기 - 방향 확인 필요")
    
    # 2. 20일 RSI 평균 (가중치: 20%)
    rsi_20d_avg = recent_20['RSI'].mean()
    if rsi_20d_avg < 35:
        signals.append("🟢 20일 평균 RSI 낮음 - 매수 기회")
        score += 15
    elif rsi_20d_avg > 65:
        signals.append("🔴 20일 평균 RSI 높음 - 조정 위험")
        score -= 15
    
    # 3. 가격 대비 이동평균 위치 (가중치: 20%)
    if latest['Close'] > latest['MA_20'] > latest['MA_60']:
        signals.append("🟢 이동평균 정배열 - 강한 상승세")
        score += 15
    elif latest['Close'] < latest['MA_20'] < latest['MA_60']:
        signals.append("🔴 이동평균 역배열 - 강한 하락세")
        score -= 15
    
    # 4. MACD 신호 (가중치: 15%)
    macd = latest['MACD']
    macd_prev = data.iloc[-2]['MACD']
    if macd > 0 and macd > macd_prev:
        signals.append("🟢 MACD 상승 - 상승 모멘텀")
        score += 10
    elif macd < 0 and macd < macd_prev:
        signals.append("🔴 MACD 하락 - 하락 모멘텀")
        score -= 10
    
    # 5. 20일 수익률 (가중치: 15%)
    price_change_20d = ((latest['Close'] - recent_20.iloc[0]['Close']) / recent_20.iloc[0]['Close']) * 100
    if price_change_20d > 10:
        signals.append("🟢 20일 강한 상승 - 지속 가능성")
        score += 10
    elif price_change_20d < -10:
        signals.append("🔴 20일 강한 하락 - 반등 기회 대기")
        score -= 10
    
    # 포지션 트레이딩 추천
    if score >= 75:
        recommendation = "포지션 매수 강추"
        recommendation_color = "🟢"
        time_horizon = "2-4주"
    elif score >= 60:
        recommendation = "포지션 매수 고려"
        recommendation_color = "🟡"
        time_horizon = "1-3주"
    elif score <= 25:
        recommendation = "포지션 매도 강추"
        recommendation_color = "🔴"
        time_horizon = "1-2주"
    elif score <= 40:
        recommendation = "포지션 정리 고려"
        recommendation_color = "🟠"
        time_horizon = "2-3주"
    else:
        recommendation = "포지션 관망"
        recommendation_color = "⚪"
        time_horizon = "2-4주"
    
    return {
        'signals': signals,
        'score': round(score, 1),
        'recommendation': recommendation,
        'recommendation_color': recommendation_color,
        'time_horizon': time_horizon,
        'strategy_description': "중기 추세와 모멘텀 기반 1-4주 포지션 트레이딩"
    }

def analyze_long_term_investment_signals(data):
    """장기 투자 (1-6개월) 신호 분석"""
    if len(data) < 120:
        return {}
    
    latest = data.iloc[-1]
    recent_60 = data.tail(60)
    recent_120 = data.tail(120)
    
    signals = []
    score = 50  # 기본 점수
    
    # 1. 장기 추세 분석 (가중치: 35%)
    ma60_slope = (latest['MA_60'] - data.iloc[-30]['MA_60']) / data.iloc[-30]['MA_60'] * 100
    
    if ma60_slope > 5:
        signals.append("🟢 60일선 강한 상승 - 장기 상승 추세")
        score += 25
    elif ma60_slope > 2:
        signals.append("🟢 60일선 완만한 상승 - 안정적 상승")
        score += 15
    elif ma60_slope < -5:
        signals.append("🔴 60일선 강한 하락 - 장기 하락 추세")
        score -= 25
    elif ma60_slope < -2:
        signals.append("🔴 60일선 완만한 하락 - 조정 지속")
        score -= 15
    else:
        signals.append("🟡 60일선 횡보 - 방향성 부재")
    
    # 2. 60일 RSI 평균 (가중치: 20%)
    rsi_60d_avg = recent_60['RSI'].mean()
    if rsi_60d_avg < 40:
        signals.append("🟢 60일 평균 RSI 낮음 - 장기 매수 기회")
        score += 15
    elif rsi_60d_avg > 60:
        signals.append("🔴 60일 평균 RSI 높음 - 고평가 위험")
        score -= 15
    
    # 3. 장기 수익률 분석 (가중치: 20%)
    price_change_60d = ((latest['Close'] - recent_60.iloc[0]['Close']) / recent_60.iloc[0]['Close']) * 100
    price_change_120d = ((latest['Close'] - recent_120.iloc[0]['Close']) / recent_120.iloc[0]['Close']) * 100
    
    if price_change_60d > 20 and price_change_120d > 30:
        signals.append("🟢 강한 장기 상승 - 트렌드 지속")
        score += 15
    elif price_change_60d < -20 and price_change_120d < -30:
        signals.append("🟢 깊은 조정 - 장기 매수 기회")
        score += 10
    elif price_change_60d > 30:
        signals.append("🔴 과도한 상승 - 조정 위험")
        score -= 10
    
    # 4. 변동성 안정성 (가중치: 15%)
    volatility_60d = recent_60['Close'].pct_change().std() * np.sqrt(252) * 100
    if volatility_60d < 20:
        signals.append("🟢 낮은 변동성 - 안정적 투자")
        score += 10
    elif volatility_60d > 40:
        signals.append("🔴 높은 변동성 - 위험 관리 필요")
        score -= 10
    
    # 5. 거래량 트렌드 (가중치: 10%)
    volume_trend = recent_60['Volume'].mean() / recent_120.iloc[:60]['Volume'].mean()
    if volume_trend > 1.2:
        signals.append("🟢 거래량 증가 - 관심 증대")
        score += 8
    elif volume_trend < 0.8:
        signals.append("🟡 거래량 감소 - 관심 부족")
        score -= 5
    
    # 장기 투자 추천
    if score >= 80:
        recommendation = "장기 투자 강력 추천"
        recommendation_color = "🟢"
        time_horizon = "3-6개월"
    elif score >= 65:
        recommendation = "장기 투자 고려"
        recommendation_color = "🟡"
        time_horizon = "2-4개월"
    elif score <= 20:
        recommendation = "장기 투자 보류"
        recommendation_color = "🔴"
        time_horizon = "관망"
    elif score <= 35:
        recommendation = "장기 관점 신중"
        recommendation_color = "🟠"
        time_horizon = "1-2개월"
    else:
        recommendation = "장기 중립"
        recommendation_color = "⚪"
        time_horizon = "2-3개월"
    
    return {
        'signals': signals,
        'score': round(score, 1),
        'recommendation': recommendation,
        'recommendation_color': recommendation_color,
        'time_horizon': time_horizon,
        'strategy_description': "기본 분석과 장기 추세 기반 1-6개월 투자"
    }

def calculate_timeframe_scores(swing_trading, position_trading, long_term_investment):
    """시간프레임별 종합 점수 계산"""
    scores = {}
    
    if swing_trading:
        scores['swing'] = swing_trading['score']
    if position_trading:
        scores['position'] = position_trading['score']
    if long_term_investment:
        scores['long_term'] = long_term_investment['score']
    
    # 가중 평균 (단기 20%, 중기 35%, 장기 45%)
    weighted_score = 0
    total_weight = 0
    
    if 'swing' in scores:
        weighted_score += scores['swing'] * 0.2
        total_weight += 0.2
    if 'position' in scores:
        weighted_score += scores['position'] * 0.35
        total_weight += 0.35
    if 'long_term' in scores:
        weighted_score += scores['long_term'] * 0.45
        total_weight += 0.45
    
    overall_score = weighted_score / total_weight if total_weight > 0 else 50
    
    return {
        'individual_scores': scores,
        'overall_score': round(overall_score, 1),
        'best_timeframe': max(scores, key=scores.get) if scores else None,
        'worst_timeframe': min(scores, key=scores.get) if scores else None
    }

def determine_recommended_strategy(timeframe_scores):
    """권장 투자 전략 결정"""
    scores = timeframe_scores['individual_scores']
    overall = timeframe_scores['overall_score']
    
    # 각 시간프레임별 점수 차이 분석
    max_score = max(scores.values()) if scores else 50
    min_score = min(scores.values()) if scores else 50
    score_spread = max_score - min_score
    
    strategies = []
    
    # 1. 전체적으로 좋은 경우
    if overall >= 70:
        if score_spread < 10:  # 모든 시간프레임에서 좋음
            strategies.append({
                'strategy': '다중 시간프레임 투자',
                'description': '단기+중기+장기 복합 전략',
                'allocation': '단기 30% + 중기 40% + 장기 30%',
                'color': '🟢'
            })
        else:  # 특정 시간프레임이 특히 좋음
            best_tf = timeframe_scores['best_timeframe']
            strategies.append({
                'strategy': f'{best_tf} 집중 투자',
                'description': f'{best_tf} 시간프레임 집중 전략',
                'allocation': f'{best_tf} 80% + 기타 20%',
                'color': '🟢'
            })
    
    # 2. 전체적으로 나쁜 경우
    elif overall <= 30:
        strategies.append({
            'strategy': '투자 보류',
            'description': '모든 시간프레임에서 부정적 신호',
            'allocation': '현금 비중 확대 권장',
            'color': '🔴'
        })
    
    # 3. 혼재된 경우
    else:
        if 'long_term' in scores and scores['long_term'] >= 60:
            strategies.append({
                'strategy': '장기 중심 + 단기 헷징',
                'description': '장기 투자 + 단기 매매로 변동성 관리',
                'allocation': '장기 70% + 단기 30%',
                'color': '🟡'
            })
        elif 'swing' in scores and scores['swing'] >= 65:
            strategies.append({
                'strategy': '스윙 트레이딩 중심',
                'description': '단기 기회 활용 중심 전략',
                'allocation': '스윙 60% + 현금 40%',
                'color': '🟡'
            })
        else:
            strategies.append({
                'strategy': '선별적 투자',
                'description': '신중한 관망 후 기회 포착',
                'allocation': '소액 분할 투자',
                'color': '🟠'
            })
    
    return strategies[0] if strategies else {
        'strategy': '관망',
        'description': '명확한 신호 부재',
        'allocation': '현금 보유',
        'color': '⚪'
    }

def create_candlestick_chart(data, symbol):
    """캔들스틱 차트 생성"""
    if data.empty:
        st.warning(f"{symbol} 데이터를 불러올 수 없습니다.")
        return None
    
    fig = go.Figure()
    
    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name=symbol
    ))
    
    # 이동평균선
    fig.add_trace(go.Scatter(
        x=data.index, y=data['MA_5'],
        mode='lines', name='MA5',
        line=dict(color='orange', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index, y=data['MA_20'],
        mode='lines', name='MA20',
        line=dict(color='blue', width=1)
    ))
    
    # 볼린저 밴드
    fig.add_trace(go.Scatter(
        x=data.index, y=data['BB_Upper'],
        mode='lines', name='BB상단',
        line=dict(color='gray', width=1, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index, y=data['BB_Lower'],
        mode='lines', name='BB하단',
        line=dict(color='gray', width=1, dash='dash'),
        fill='tonexty', fillcolor='rgba(128,128,128,0.1)'
    ))
    
    fig.update_layout(
        title=f"{symbol} 주가 차트",
        xaxis_title="날짜",
        yaxis_title="가격 (원)",
        height=500,
        xaxis_rangeslider_visible=False
    )
    
    return fig

def main():
    """메인 앱"""
    
    # pykrx 모듈 상태 확인 및 안내
    if not PYKRX_AVAILABLE:
        st.info("💡 주요 한국 종목 50개로 분석을 제공합니다. (코스피/코스닥 대표 종목들)")
    else:
        st.success("✅ 전체 한국 종목 2,759개 분석 가능 (pykrx 활성화)")
    
    # 헤더
    st.title("📊 Smart Trading Dashboard")
    st.markdown("---")
    
    # 사이드바
    st.sidebar.header("📋 설정")
    
    # 전체 종목 리스트 로드
    with st.spinner("📈 종목 리스트 로딩 중..."):
        all_stocks = get_all_korean_stocks()
    
    st.sidebar.success(f"✅ 총 {len(all_stocks):,}개 종목 로딩 완료")
    
    # 종목 검색 및 선택
    st.sidebar.markdown("### 🔍 종목 검색")
    
    selected_name = st_searchbox(
        search_function=lambda search_term: search_stocks(search_term, all_stocks),
        placeholder="종목명 또는 코드 입력 (예: 삼성전자, 005930)",
        label="종목 검색",
        default="삼성전자 (005930)" if "삼성전자 (005930)" in all_stocks else list(all_stocks.keys())[0],
        clear_on_submit=False,
        key="stock_search"
    )
    
    # 검색 도움말
    with st.sidebar.expander("💡 검색 팁"):
        st.markdown("""
        **검색 방법:**
        - 종목명: `삼성전자`, `삼성`, `네이버`
        - 종목코드: `005930`, `035420`
        - 부분검색: `삼성`으로 모든 삼성 계열사 검색
        
        **우선순위:**
        1. 정확한 종목명/코드 매치
        2. 시작 문자 매치
        3. 부분 포함 매치
        """)
    
    # 선택된 종목 처리
    if selected_name and selected_name in all_stocks:
        selected_symbol = all_stocks[selected_name]
        st.sidebar.info(f"선택된 종목: **{selected_name}**")
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
    
    # 메인 컨텐츠 - 탭으로 구성
    st.subheader(f"📈 {selected_name} ({selected_symbol})")
    
    # 데이터 로드
    with st.spinner("데이터 로딩 중..."):
        data = get_stock_data(selected_symbol, period)
        
    if not data.empty:
        # 기술적 지표 계산
        data = calculate_technical_indicators(data)
        
        # 현재 가격 정보 (탭 위에 표시)
        latest = data.iloc[-1]
        prev_close = data.iloc[-2]['Close'] if len(data) > 1 else latest['Close']
        change = latest['Close'] - prev_close
        change_pct = (change / prev_close) * 100
        
        col_price1, col_price2, col_price3, col_price4 = st.columns(4)
        
        with col_price1:
            st.metric("현재가", f"{latest['Close']:,.0f}원", f"{change:+.0f}원")
        
        with col_price2:
            st.metric("변동율", f"{change_pct:+.2f}%")
        
        with col_price3:
            st.metric("거래량", f"{latest['Volume']:,.0f}주")
        
        with col_price4:
            st.metric("RSI", f"{latest['RSI']:.1f}")
        
        st.markdown("---")
        
        # 탭 생성
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 차트 & 기본정보", 
            "⚖️ 공정가치 분석", 
            "🏭 업종 비교", 
            "🎯 매매 신호", 
            "📚 용어 설명"
        ])
        
        with tab1:
            st.subheader("📊 주가 차트")
            
            # 차트 생성
            chart = create_candlestick_chart(data, selected_name)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # 기본 정보 설명
            with st.expander("📖 기본 정보 설명", expanded=False):
                st.markdown("""
                **📈 캔들스틱 차트란?**
                - **빨간색 캔들**: 하락 (시가 > 종가)
                - **파란색 캔들**: 상승 (시가 < 종가)
                - **위아래 선**: 당일 최고가와 최저가
                
                **🔄 이동평균선 (MA):**
                - **MA5 (노란선)**: 5일 평균가격
                - **MA20 (빨간선)**: 20일 평균가격 
                - **MA60 (파란선)**: 60일 평균가격
                
                **📊 거래량:**
                - 차트 하단의 막대그래프
                - 높을수록 관심도가 높음을 의미
                """)
        
        with tab2:
            st.subheader("⚖️ 공정가치 분석")
            
            # 적정가 분석 실행
            fair_value_analysis = analyze_fair_value(data, latest['Close'])
            
            # 분석 결과 표시
            col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
            
            with col_analysis1:
                # 종합 점수 표시
                score = fair_value_analysis['fair_value_score']
                if score >= 70:
                    score_color = "🟢"
                elif score >= 55:
                    score_color = "🟡"
                elif score <= 30:
                    score_color = "🔴"
                elif score <= 45:
                    score_color = "🟠"
                else:
                    score_color = "⚪"
                
                st.metric(
                    "적정가 점수",
                    f"{score_color} {score}/100",
                    help="기술적 지표 종합 점수 (높을수록 매수, 낮을수록 매도)"
                )
            
            with col_analysis2:
                # 추천 등급 표시
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
                    f"{rec_color} {recommendation}",
                    f"신뢰도: {confidence:.1f}%"
                )
            
            with col_analysis3:
                # 20일 이동평균 대비 위치
                ma20_diff = fair_value_analysis['analysis']['moving_average']['current_vs_ma20']
                st.metric(
                    "20일선 대비",
                    f"{ma20_diff:+.1f}%",
                    help="20일 이동평균선 대비 현재가 위치"
                )
            
            # 상세 분석 결과
            with st.expander("📈 상세 분석 결과", expanded=True):
                # 주요 근거
                st.markdown("**🎯 주요 판단 근거:**")
                for reason in fair_value_analysis['reasons']:
                    st.markdown(f"• {reason}")
                
                st.markdown("---")
                
                # 지표별 세부 분석
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.markdown("**📊 기술적 지표 분석:**")
                    
                    # RSI 분석
                    rsi_data = fair_value_analysis['analysis']['rsi']
                    st.markdown(f"**RSI ({rsi_data['value']:.1f}):** {rsi_data['status']}")
                    
                    # 볼린저 밴드 분석
                    bb_data = fair_value_analysis['analysis']['bollinger_bands']
                    st.markdown(f"**볼린저밴드:** {bb_data['status']} (위치: {bb_data['position']:.1f}%)")
                    
                    # 스토캐스틱 분석
                    stoch_data = fair_value_analysis['analysis']['stochastic']
                    st.markdown(f"**스토캐스틱 ({stoch_data['k_value']:.1f}):** {stoch_data['status']}")
                
                with col_detail2:
                    st.markdown("**📈 추세 및 모멘텀:**")
                    
                    # 이동평균 분석
                    ma_data = fair_value_analysis['analysis']['moving_average']
                    if ma_data['analysis']:
                        for analysis_item in ma_data['analysis']:
                            st.markdown(f"• {analysis_item}")
                    else:
                        st.markdown("• 이동평균선 하락 배열")
                    
                    # MACD 분석
                    macd_data = fair_value_analysis['analysis']['macd']
                    if macd_data['analysis']:
                        for analysis_item in macd_data['analysis']:
                            st.markdown(f"• {analysis_item}")
                    
                    # 거래량 분석
                    volume_data = fair_value_analysis['analysis']['volume']
                    st.markdown(f"• 거래량: {volume_data['status']} (평균 대비 {volume_data['ratio']:.1f}배)")
            
            # 동종업계 비교 분석 섹션 추가
            st.markdown("---")
            st.subheader("🏭 동종업계 비교 분석")
            
            # 동종업계 비교 분석 실행
            with st.spinner("동종업계 데이터 분석 중..."):
                industry_comparison = analyze_industry_comparison(selected_symbol, data)
            
            if industry_comparison['comparison_available']:
                # 업종 정보 표시
                st.markdown(f"**📊 업종:** {industry_comparison['industry']} ({industry_comparison['peer_count']}개 종목 비교)")
                
                # 비교 결과 표시
                col_comp1, col_comp2, col_comp3 = st.columns(3)
                
                with col_comp1:
                    # 상대적 점수
                    comp_score = industry_comparison['comparison_score']
                    if comp_score >= 70:
                        comp_color = "🟢"
                    elif comp_score >= 55:
                        comp_color = "🟡"
                    elif comp_score <= 30:
                        comp_color = "🔴"
                    elif comp_score <= 45:
                        comp_color = "🟠"
                    else:
                        comp_color = "⚪"
                    
                    st.metric(
                        "업종 내 위치",
                        f"{comp_color} {comp_score}/100",
                        help="동종업계 대비 상대적 위치 (높을수록 업종 내 우위)"
                    )
                
                with col_comp2:
                    # 상대적 추천
                    relative_rec = industry_comparison['relative_recommendation']
                    if "강력 매수" in relative_rec:
                        rel_color = "🟢"
                    elif "매수" in relative_rec:
                        rel_color = "🟡"
                    elif "매도" in relative_rec:
                        rel_color = "🔴"
                    else:
                        rel_color = "⚪"
                    
                    st.metric(
                        "업종 내 추천",
                        f"{rel_color} {relative_rec}",
                        help="동종업계 대비 상대적 투자 매력도"
                    )
                
                with col_comp3:
                    # RSI 업종 비교
                    current_rsi = industry_comparison['current_metrics']['rsi']
                    avg_rsi = industry_comparison['industry_avg']['rsi']
                    rsi_diff = current_rsi - avg_rsi
                    
                    st.metric(
                        "RSI (업종 평균 대비)",
                        f"{current_rsi:.1f}",
                        f"{rsi_diff:+.1f}p",
                        help="RSI 업종 평균과의 차이"
                    )
                
                # 상세 비교 분석
                with st.expander("🔍 업종 비교 상세 분석", expanded=True):
                    # 비교 분석 결과
                    st.markdown("**📈 주요 비교 포인트:**")
                    if industry_comparison['comparison_analysis']:
                        for analysis_item in industry_comparison['comparison_analysis']:
                            st.markdown(f"• {analysis_item}")
                    else:
                        st.markdown("• 업종 평균과 유사한 수준")
                    
                    st.markdown("---")
                    
                    # 지표별 상세 비교
                    col_detail_comp1, col_detail_comp2 = st.columns(2)
                    
                    with col_detail_comp1:
                        st.markdown("**📊 현재 종목 지표:**")
                        current = industry_comparison['current_metrics']
                        st.markdown(f"• RSI: {current['rsi']:.1f}")
                        st.markdown(f"• 20일선 대비: {((current['ma20_ratio'] - 1) * 100):+.1f}%")
                        st.markdown(f"• 볼린저밴드 위치: {current['bb_position']:.1f}%")
                        st.markdown(f"• 20일 수익률: {current['price_change_20d']:+.1f}%")
                    
                    with col_detail_comp2:
                        st.markdown("**🏭 업종 평균 지표:**")
                        avg = industry_comparison['industry_avg']
                        st.markdown(f"• RSI: {avg['rsi']:.1f}")
                        st.markdown(f"• 20일선 대비: {((avg['ma20_ratio'] - 1) * 100):+.1f}%")
                        st.markdown(f"• 볼린저밴드 위치: {avg['bb_position']:.1f}%")
                        st.markdown(f"• 20일 수익률: {avg['price_change_20d']:+.1f}%")
                    
                    # 비교 대상 종목들
                    if industry_comparison['peer_codes']:
                        st.markdown("**🔗 주요 비교 종목:**")
                        peer_list = ", ".join(industry_comparison['peer_codes'])
                        st.markdown(f"{peer_list}")
                
            else:
                # 비교 불가능한 경우
                st.warning(f"**업종:** {industry_comparison['industry']}")
                st.info(industry_comparison.get('message', '동종업계 비교 분석을 할 수 없습니다.'))
                
            # 용어 설명 추가
            with st.expander("📖 업종 비교 용어 설명", expanded=False):
                st.markdown("""
                **🏭 업종 비교 분석이란?**
                - 같은 업종 내 다른 회사들과 비교분석
                - 해당 종목의 상대적 위치 파악
                
                **📊 업종 내 위치 점수:**
                - **70점 이상**: 업종 내 상위권 (🟢)
                - **55-69점**: 업종 내 중상위권 (🟡)
                - **45-54점**: 업종 내 중간 (⚪)
                - **30-44점**: 업종 내 중하위권 (🟠)
                - **30점 미만**: 업종 내 하위권 (🔴)
                
                **📈 비교 지표들:**
                - **RSI**: 과매수/과매도 상태 비교
                - **20일선 대비**: 단기 추세 비교
                - **볼린저밴드**: 변동성 구간 비교
                """)
        
        with tab3:
            st.subheader("🏭 업종 비교 분석")
            
            # 동종업계 비교 분석 실행
            with st.spinner("동종업계 데이터 분석 중..."):
                industry_comparison = analyze_industry_comparison(selected_symbol, data)
            
            if industry_comparison['comparison_available']:
                # 업종 정보 표시
                st.markdown(f"**📊 업종:** {industry_comparison['industry']} ({industry_comparison['peer_count']}개 종목 비교)")
                
                # 비교 결과 표시
                col_comp1, col_comp2, col_comp3 = st.columns(3)
                
                with col_comp1:
                    # 상대적 점수
                    comp_score = industry_comparison['comparison_score']
                    if comp_score >= 70:
                        comp_color = "🟢"
                    elif comp_score >= 55:
                        comp_color = "🟡"
                    elif comp_score <= 30:
                        comp_color = "🔴"
                    elif comp_score <= 45:
                        comp_color = "🟠"
                    else:
                        comp_color = "⚪"
                    
                    st.metric(
                        "업종 내 위치",
                        f"{comp_color} {comp_score}/100",
                        help="동종업계 대비 상대적 위치 (높을수록 업종 내 우위)"
                    )
                
                with col_comp2:
                    # 상대적 추천
                    relative_rec = industry_comparison['relative_recommendation']
                    if "강력 매수" in relative_rec:
                        rel_color = "🟢"
                    elif "매수" in relative_rec:
                        rel_color = "🟡"
                    elif "매도" in relative_rec:
                        rel_color = "🔴"
                    else:
                        rel_color = "⚪"
                    
                    st.metric(
                        "업종 내 추천",
                        f"{rel_color} {relative_rec}",
                        help="동종업계 대비 상대적 투자 매력도"
                    )
                
                with col_comp3:
                    # RSI 업종 비교
                    current_rsi = industry_comparison['current_metrics']['rsi']
                    avg_rsi = industry_comparison['industry_avg']['rsi']
                    rsi_diff = current_rsi - avg_rsi
                    
                    st.metric(
                        "RSI (업종 평균 대비)",
                        f"{current_rsi:.1f}",
                        f"{rsi_diff:+.1f}p",
                        help="RSI 업종 평균과의 차이"
                    )
                
                # 상세 비교 분석
                with st.expander("🔍 업종 비교 상세 분석", expanded=True):
                    # 비교 분석 결과
                    st.markdown("**📈 주요 비교 포인트:**")
                    if industry_comparison['comparison_analysis']:
                        for analysis_item in industry_comparison['comparison_analysis']:
                            st.markdown(f"• {analysis_item}")
                    else:
                        st.markdown("• 업종 평균과 유사한 수준")
                    
                    st.markdown("---")
                    
                    # 지표별 상세 비교
                    col_detail_comp1, col_detail_comp2 = st.columns(2)
                    
                    with col_detail_comp1:
                        st.markdown("**📊 현재 종목 지표:**")
                        current = industry_comparison['current_metrics']
                        st.markdown(f"• RSI: {current['rsi']:.1f}")
                        st.markdown(f"• 20일선 대비: {((current['ma20_ratio'] - 1) * 100):+.1f}%")
                        st.markdown(f"• 볼린저밴드 위치: {current['bb_position']:.1f}%")
                    
                    with col_detail_comp2:
                        st.markdown("**🏭 업종 평균 지표:**")
                        avg = industry_comparison['industry_avg']
                        st.markdown(f"• RSI: {avg['rsi']:.1f}")
                        st.markdown(f"• 20일선 대비: {((avg['ma20_ratio'] - 1) * 100):+.1f}%")
                        st.markdown(f"• 볼린저밴드 위치: {avg['bb_position']:.1f}%")
                    
                    if industry_comparison['peer_codes']:
                        st.markdown("**🔗 주요 비교 종목:**")
                        peer_list = ", ".join(industry_comparison['peer_codes'])
                        st.markdown(f"{peer_list}")
                
            else:
                # 비교 불가능한 경우
                st.warning(f"**업종:** {industry_comparison['industry']}")
                st.info(industry_comparison.get('message', '동종업계 비교 분석을 할 수 없습니다.'))
                
            # 용어 설명 추가
            with st.expander("📖 업종 비교 용어 설명", expanded=False):
                st.markdown("""
                **🏭 업종 비교 분석이란?**
                - 같은 업종 내 다른 회사들과 비교분석
                - 해당 종목의 상대적 위치 파악
                
                **📊 업종 내 위치 점수:**
                - **70점 이상**: 업종 내 상위권 (🟢)
                - **55-69점**: 업종 내 중상위권 (🟡)
                - **45-54점**: 업종 내 중간 (⚪)
                - **30-44점**: 업종 내 중하위권 (🟠)
                - **30점 미만**: 업종 내 하위권 (🔴)
                
                **📈 비교 지표들:**
                - **RSI**: 과매수/과매도 상태 비교
                - **20일선 대비**: 단기 추세 비교
                - **볼린저밴드**: 변동성 구간 비교
                """)
        
        with tab4:
            st.subheader("🎯 매매 신호")
            
            # 과매수/과매도 분석 실행
            overbought_analysis = analyze_overbought_oversold(data, latest['Close'])
            
            # 신호 강도 및 타입 표시
            signal_type = overbought_analysis['signal_type']
            signal_strength = overbought_analysis['signal_strength']
            confidence = overbought_analysis['confidence']
            
            # 신호 타입에 따른 색상 결정
            if "강력 매수" in signal_type:
                signal_color = "#28a745"
                bg_color = "#d4edda"
                icon = "🟢"
            elif "매수" in signal_type:
                signal_color = "#28a745"
                bg_color = "#d4edda" 
                icon = "🟡"
            elif "강력 매도" in signal_type:
                signal_color = "#dc3545"
                bg_color = "#f8d7da"
                icon = "🔴"
            elif "매도" in signal_type:
                signal_color = "#dc3545"
                bg_color = "#f8d7da"
                icon = "🟠"
            else:
                signal_color = "#6c757d"
                bg_color = "#f8f9fa"
                icon = "⚪"
            
            # 신호 박스 표시
            st.markdown(f"""
            <div style="
                background-color: {bg_color}; 
                border: 2px solid {signal_color}; 
                border-radius: 10px; 
                padding: 20px; 
                text-align: center;
                margin: 10px 0;
            ">
                <h2 style="color: {signal_color}; margin: 0;">
                    {icon} {signal_type}
                </h2>
                <p style="margin: 5px 0; font-size: 16px;">
                    신호 강도: <strong>{signal_strength:.1f}/10</strong> | 
                    신뢰도: <strong>{confidence:.1f}%</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # 상세 분석 결과
            col_signal1, col_signal2 = st.columns(2)
            
            with col_signal1:
                st.markdown("**📊 주요 신호 지표:**")
                for indicator, result in overbought_analysis['indicators'].items():
                    status_icon = "🟢" if "매수" in result['signal'] else "🔴" if "매도" in result['signal'] else "⚪"
                    st.markdown(f"**{indicator}**: {status_icon} {result['signal']} ({result['value']:.1f})")
            
            with col_signal2:
                st.markdown("**🎯 매매 전략:**")
                for strategy in overbought_analysis['trading_strategies']:
                    st.markdown(f"• {strategy}")
            
            # 고급 매매 신호 분석
            advanced_signals = generate_advanced_trading_signals(data)
            
            st.markdown("---")
            st.subheader("🚀 고급 매매 신호")
            
            # 통합 신호 표시
            integrated_signal = advanced_signals['integrated_signal']
            signal_strength = advanced_signals['signal_strength']
            
            col_adv1, col_adv2, col_adv3 = st.columns(3)
            
            with col_adv1:
                if integrated_signal['action'] == 'BUY':
                    action_color = "🟢"
                elif integrated_signal['action'] == 'SELL':
                    action_color = "🔴"
                else:
                    action_color = "⚪"
                
                st.metric(
                    "통합 신호",
                    f"{action_color} {integrated_signal['action']}",
                    f"강도: {signal_strength:.1f}/10"
                )
            
            with col_adv2:
                priority_signal = advanced_signals['priority_signals'][0] if advanced_signals['priority_signals'] else {'type': '없음', 'strength': 0}
                st.metric(
                    "우선순위 신호",
                    priority_signal['type'],
                    f"강도: {priority_signal['strength']:.1f}/10"
                )
            
            with col_adv3:
                risk_level = advanced_signals['risk_assessment']['risk_level']
                if risk_level == 'LOW':
                    risk_color = "🟢"
                elif risk_level == 'MEDIUM':
                    risk_color = "🟡"
                else:
                    risk_color = "🔴"
                
                st.metric(
                    "위험도",
                    f"{risk_color} {risk_level}",
                    f"점수: {advanced_signals['risk_assessment']['risk_score']:.1f}/10"
                )
            
            # 매매 신호 용어 설명
            with st.expander("📖 매매 신호 용어 설명", expanded=False):
                st.markdown("""
                **🎯 매매 신호란?**
                - 기술적 지표를 종합해서 매수/매도 타이밍을 알려주는 신호
                
                **📊 신호 종류:**
                - **강력 매수** (🟢): 여러 지표가 매수 신호 → 적극 매수 고려
                - **매수** (🟡): 일부 지표가 매수 신호 → 신중한 매수 고려
                - **중립** (⚪): 명확한 신호 없음 → 관망
                - **매도** (🟠): 일부 지표가 매도 신호 → 신중한 매도 고려
                - **강력 매도** (🔴): 여러 지표가 매도 신호 → 적극 매도 고려
                
                **🔢 신호 강도 (1-10점):**
                - **8-10점**: 매우 강한 신호
                - **6-7점**: 강한 신호
                - **4-5점**: 보통 신호
                - **1-3점**: 약한 신호
                
                **⚠️ 주의사항:**
                - 매매 신호는 참고용으로 최종 투자 결정은 본인이 하세요
                - 여러 지표를 종합적으로 판단하는 것이 중요합니다
                """)
        
        with tab5:
            st.subheader("📚 투자 용어 완전 가이드")
            
            # 기본 용어
            with st.expander("📈 기본 주식 용어", expanded=True):
                st.markdown("""
                **💰 기본 가격 용어:**
                - **현재가**: 지금 거래되고 있는 주식 가격
                - **시가**: 장 시작할 때 첫 거래 가격
                - **종가**: 장 마감할 때 마지막 거래 가격
                - **고가**: 하루 중 가장 높았던 가격
                - **저가**: 하루 중 가장 낮았던 가격
                
                **📊 거래 관련:**
                - **거래량**: 하루 동안 거래된 주식 수량
                - **거래대금**: 하루 동안 거래된 총 금액
                - **변동율**: 전날 종가 대비 오늘 가격 변화율
                
                **📈 차트 용어:**
                - **캔들**: 하루의 시가, 고가, 저가, 종가를 보여주는 막대
                - **양봉(상승)**: 종가가 시가보다 높은 파란색 캔들
                - **음봉(하락)**: 종가가 시가보다 낮은 빨간색 캔들
                """)
            
            # 기술적 지표
            with st.expander("🔢 기술적 지표 완전 설명", expanded=False):
                st.markdown("""
                **📊 RSI (Relative Strength Index):**
                - **의미**: 주식이 과매수/과매도 상태인지 알려주는 지표
                - **수치**: 0~100 사이
                - **해석**:
                  - 70 이상: 과매수 (가격이 많이 올라서 조정 가능성)
                  - 30 이하: 과매도 (가격이 많이 떨어서 반등 가능성)
                  - 30~70: 정상 구간
                
                **📈 이동평균선 (Moving Average):**
                - **의미**: 일정 기간 동안의 평균 가격선
                - **종류**:
                  - MA5: 5일 평균 (단기 추세)
                  - MA20: 20일 평균 (중기 추세)
                  - MA60: 60일 평균 (장기 추세)
                - **활용**: 현재가가 이동평균선 위에 있으면 상승 추세
                
                **🎯 볼린저 밴드:**
                - **의미**: 주가의 변동 범위를 보여주는 밴드
                - **구성**: 중심선(20일 이동평균) + 상한선 + 하한선
                - **해석**:
                  - 상한선 근처: 고점 구간 (매도 고려)
                  - 하한선 근처: 저점 구간 (매수 고려)
                  - 밴드 폭이 좁아지면: 큰 움직임 예상
                
                **⚡ MACD:**
                - **의미**: 주가의 추세 변화를 보여주는 지표
                - **신호**:
                  - MACD선이 신호선 위로: 매수 신호
                  - MACD선이 신호선 아래로: 매도 신호
                  - 0선 돌파: 추세 전환 신호
                
                **🎲 스토캐스틱:**
                - **의미**: 일정 기간 중 현재 가격의 상대적 위치
                - **수치**: 0~100
                - **해석**:
                  - 80 이상: 과매수
                  - 20 이하: 과매도
                  - %K선과 %D선의 교차로 매매 타이밍 판단
                """)
            
            # 투자 전략
            with st.expander("💡 투자 전략 가이드", expanded=False):
                st.markdown("""
                **🎯 기본 투자 원칙:**
                1. **분산투자**: 여러 종목에 나누어 투자
                2. **장기투자**: 단기 변동에 흔들리지 않기
                3. **손절매**: 손실이 커지기 전에 정리
                4. **수익실현**: 목표 수익률 달성 시 일부 매도
                
                **📊 신호 활용법:**
                - **여러 지표 종합**: 한 지표만 보지 말고 종합 판단
                - **추세 확인**: 전체적인 흐름 파악이 우선
                - **거래량 확인**: 신호와 함께 거래량도 증가해야 신뢰성↑
                - **시장 상황 고려**: 전체 시장 상황도 함께 고려
                
                **⚠️ 위험 관리:**
                - **투자 금액**: 전체 자산의 일부만 투자
                - **손실 한도**: 미리 손실 한도 정하기
                - **감정 조절**: 욕심과 두려움 컨트롤
                - **정보 수집**: 지속적인 학습과 정보 습득
                
                **🎯 매매 타이밍:**
                - **매수**: 여러 지표가 동시에 매수 신호 + 거래량 증가
                - **매도**: 목표가 도달 or 손절가 도달 or 여러 지표 매도 신호
                - **관망**: 신호가 명확하지 않을 때는 기다리기
                """)
        
        else:
            st.error(f"{selected_name} 데이터를 불러올 수 없습니다. 다른 종목을 선택해 주세요.")
    
    # 푸터
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "📊 현재: Yahoo Finance 데이터 (15-20분 지연) | "
        "🚀 향후 업그레이드: 한국투자증권 API 실시간 연동 예정 (1-2초 지연) | "
        "💡 투자 결정은 신중히 하시기 바랍니다."
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
