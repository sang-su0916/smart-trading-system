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

# pykrx import with error handling for Streamlit Cloud
try:
    import pykrx.stock as stock
    PYKRX_AVAILABLE = True
except ImportError:
    st.error("⚠️ pykrx 모듈을 불러올 수 없습니다. 일부 기능이 제한될 수 있습니다.")
    PYKRX_AVAILABLE = False
    stock = None

# 경고 메시지 숨기기
warnings.filterwarnings('ignore')

# 페이지 설정
st.set_page_config(
    page_title="📊 Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 캐시 함수들
@st.cache_data(ttl=3600)  # 1시간 캐시 (종목 리스트는 자주 변하지 않음)
def get_all_korean_stocks():
    """한국거래소 전체 종목 리스트 가져오기"""
    if not PYKRX_AVAILABLE or stock is None:
        # pykrx가 없으면 기본 종목들 반환
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
    
    # 메인 컨텐츠
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📈 {selected_name} ({selected_symbol})")
        
        # 데이터 로드
        with st.spinner("데이터 로딩 중..."):
            data = get_stock_data(selected_symbol, period)
            
        if not data.empty:
            # 기술적 지표 계산
            data = calculate_technical_indicators(data)
            
            # 차트 생성
            chart = create_candlestick_chart(data, selected_name)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # 현재 가격 정보
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
            
            # 적정가 분석 섹션 추가
            st.markdown("---")
            st.subheader("📊 적정가 분석")
            
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
        
        else:
            st.error(f"{selected_name} 데이터를 불러올 수 없습니다. 다른 종목을 선택해 주세요.")
    
    with col2:
        st.subheader("⚡ 과매수/과매도 분석")
        
        if not data.empty:
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
                signal_color = "#ffc107"
                bg_color = "#fff3cd"
                icon = "🟡"
            elif "강력 매도" in signal_type:
                signal_color = "#dc3545"
                bg_color = "#f8d7da"
                icon = "🔴"
            elif "매도" in signal_type:
                signal_color = "#fd7e14"
                bg_color = "#fff0e6"
                icon = "🟠"
            else:
                signal_color = "#6c757d"
                bg_color = "#f8f9fa"
                icon = "⚪"
            
            # 신호 카드 표시
            st.markdown(f"""
            <div style='padding: 15px; border-radius: 10px; 
                 background-color: {bg_color}; 
                 border-left: 5px solid {signal_color}; 
                 margin-bottom: 15px;'>
                <strong style='font-size: 1.1em;'>{icon} {signal_type}</strong><br>
                <small>신호 강도: {signal_strength:.1f} | 신뢰도: {confidence:.1f}%</small>
            </div>
            """, unsafe_allow_html=True)
            
            # 추천 사항
            st.markdown("**💡 추천 사항:**")
            for recommendation in overbought_analysis['recommendations']:
                st.markdown(f"• {recommendation}")
            
            # 상세 지표 분석
            with st.expander("📊 상세 지표 분석"):
                analysis = overbought_analysis['detailed_analysis']
                
                # RSI 분석
                rsi_data = analysis.get('rsi', {})
                st.markdown(f"**RSI ({rsi_data.get('value', 0):.1f}):** {rsi_data.get('signal', 'N/A')}")
                
                # 스토캐스틱 분석
                stoch_data = analysis.get('stochastic', {})
                st.markdown(f"**스토캐스틱 (%K: {stoch_data.get('k_value', 0):.1f}):** {stoch_data.get('signal', 'N/A')}")
                
                # 볼린저 밴드 분석
                bb_data = analysis.get('bollinger_bands', {})
                st.markdown(f"**볼린저밴드 (위치: {bb_data.get('position', 0):.1f}%):** {bb_data.get('signal', 'N/A')}")
                
                # 이동평균 분석
                ma_data = analysis.get('moving_average', {})
                st.markdown(f"**이동평균 편향 ({ma_data.get('avg_deviation', 0):.1f}%):** {ma_data.get('signal', 'N/A')}")
                
                # 거래량 분석
                vol_data = analysis.get('volume', {})
                st.markdown(f"**거래량 (비율: {vol_data.get('ratio', 0):.1f}배):** {vol_data.get('signal', 'N/A')}")
        
        # 기술적 지표 요약
        st.subheader("📊 핵심 지표 요약")
        
        if not data.empty:
            latest = data.iloc[-1]
            
            # 종합 상태 표시
            col_indicator1, col_indicator2 = st.columns(2)
            
            with col_indicator1:
                # RSI 상태
                rsi_value = latest['RSI']
                if rsi_value < 30:
                    rsi_status = "🔵 과매도"
                elif rsi_value > 70:
                    rsi_status = "🔴 과매수"
                else:
                    rsi_status = "⚪ 중립"
                
                st.metric("RSI (14일)", f"{rsi_value:.1f}", rsi_status)
                
                # 스토캐스틱 상태
                stoch_value = latest['Stoch_K']
                if stoch_value < 20:
                    stoch_status = "🔵 과매도"
                elif stoch_value > 80:
                    stoch_status = "🔴 과매수"
                else:
                    stoch_status = "⚪ 중립"
                
                st.metric("스토캐스틱", f"{stoch_value:.1f}", stoch_status)
            
            with col_indicator2:
                # 볼린저 밴드 위치
                bb_position = latest['BB_Position']
                if bb_position < 20:
                    bb_status = "🔵 하단권"
                elif bb_position > 80:
                    bb_status = "🔴 상단권"
                else:
                    bb_status = "⚪ 중간권"
                
                st.metric("볼린저밴드", f"{bb_position:.1f}%", bb_status)
                
                # 거래량 상태
                volume_ratio = latest['Volume_Ratio']
                if volume_ratio > 2:
                    vol_status = "📈 높음"
                elif volume_ratio < 0.5:
                    vol_status = "📉 낮음"
                else:
                    vol_status = "📊 보통"
                
                st.metric("거래량 비율", f"{volume_ratio:.1f}배", vol_status)
        
        # === 새로운 고도화된 매매 신호 시스템 ===
        st.subheader("🎯 고도화된 매매 신호")
        
        if not data.empty:
            # 고도화된 매매 신호 분석 실행
            advanced_signals = generate_advanced_trading_signals(data)
            
            # 주요 신호들 표시
            signals = advanced_signals['signals']
            
            if signals:
                st.markdown("**📈 우선순위 매매 신호:**")
                
                for i, signal in enumerate(signals):
                    # 신호별 색상 및 아이콘 설정
                    if '매수' in signal['signal']:
                        if signal['confidence'] >= 85:
                            color = "#28a745"
                            bg_color = "#d4edda"
                        else:
                            color = "#ffc107"
                            bg_color = "#fff3cd"
                    elif '매도' in signal['signal']:
                        if signal['confidence'] >= 85:
                            color = "#dc3545"
                            bg_color = "#f8d7da"
                        else:
                            color = "#fd7e14"
                            bg_color = "#fff0e6"
                    else:
                        color = "#6c757d"
                        bg_color = "#f8f9fa"
                    
                    # 신호 카드 표시
                    st.markdown(f"""
                    <div style='padding: 12px; border-radius: 8px; 
                         background-color: {bg_color}; 
                         border-left: 4px solid {color}; 
                         margin-bottom: 10px;'>
                        <strong>{signal['icon']} {signal['type']}</strong><br>
                        <span style='color: {color}; font-weight: bold;'>{signal['signal']}</span> 
                        | 신뢰도: {signal['confidence']}% | {signal['timeframe']}<br>
                        <small>{signal['description']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("현재 명확한 매매 신호가 감지되지 않습니다.")
            
            # 상세 분석 정보
            with st.expander("🔍 상세 신호 분석"):
                # 트렌드 분석
                trend_analysis = advanced_signals['trend_analysis']
                if trend_analysis:
                    st.markdown("**📈 트렌드 분석:**")
                    st.markdown(f"• 현재 추세: {trend_analysis.get('trend_direction', 'N/A')}")
                    st.markdown(f"• 추세 강도: {trend_analysis.get('trend_strength', 0)}%")
                    st.markdown(f"• 최근 모멘텀: {trend_analysis.get('recent_momentum', 0)}%")
                    
                    if trend_analysis.get('reversal_signals'):
                        st.markdown("• 전환 신호:")
                        for reversal in trend_analysis['reversal_signals']:
                            st.markdown(f"  - {reversal}")
                    
                    st.markdown("---")
                
                # 지지/저항선 분석
                support_resistance = advanced_signals['support_resistance']
                if support_resistance:
                    st.markdown("**📊 지지/저항선 분석:**")
                    st.markdown(f"• 저항선: {support_resistance.get('resistance_level', 0):,.0f}원 (거리: {support_resistance.get('resistance_distance', 0):+.1f}%)")
                    st.markdown(f"• 지지선: {support_resistance.get('support_level', 0):,.0f}원 (거리: {support_resistance.get('support_distance', 0):+.1f}%)")
                    
                    breakout_signals = support_resistance.get('breakout_signals', [])
                    if breakout_signals:
                        st.markdown("• 돌파 신호:")
                        for breakout in breakout_signals:
                            st.markdown(f"  - {breakout['type']}: {breakout['description']}")
                    
                    st.markdown("---")
                
                # 패턴 인식
                pattern_recognition = advanced_signals['pattern_recognition']
                if pattern_recognition and pattern_recognition.get('patterns'):
                    st.markdown("**🔍 차트 패턴 인식:**")
                    for pattern in pattern_recognition['patterns']:
                        st.markdown(f"• {pattern['pattern']}: {pattern['description']}")
                    
                    st.markdown("---")
                
                # 다중 시간프레임 분석
                timeframe_analysis = advanced_signals['timeframe_analysis']
                if timeframe_analysis:
                    st.markdown("**⏰ 다중 시간프레임 분석:**")
                    
                    timeframes = timeframe_analysis.get('timeframes', {})
                    if timeframes:
                        col_tf1, col_tf2, col_tf3 = st.columns(3)
                        
                        with col_tf1:
                            short_term = timeframes.get('short_term', {})
                            st.metric("단기 (5일)", 
                                    short_term.get('signal', 'N/A'),
                                    f"{short_term.get('period_return', 0):+.1f}%")
                        
                        with col_tf2:
                            medium_term = timeframes.get('medium_term', {})
                            st.metric("중기 (20일)", 
                                    medium_term.get('signal', 'N/A'),
                                    f"{medium_term.get('period_return', 0):+.1f}%")
                        
                        with col_tf3:
                            long_term = timeframes.get('long_term', {})
                            st.metric("장기 (60일)", 
                                    long_term.get('signal', 'N/A'),
                                    f"{long_term.get('period_return', 0):+.1f}%")
                    
                    consensus = timeframe_analysis.get('consensus', 'N/A')
                    consensus_strength = timeframe_analysis.get('consensus_strength', 0)
                    st.markdown(f"**종합 합의:** {consensus} ({consensus_strength}%)")
        
        # === 위험도 평가 및 포지션 관리 시스템 ===
        st.subheader("⚠️ 위험도 평가 & 포지션 관리")
        
        if not data.empty:
            # 투자금액 입력 
            investment_amount = st.number_input(
                "💰 투자 예정 금액 (원)", 
                min_value=100000, 
                max_value=100000000, 
                value=1000000, 
                step=100000,
                help="위험도 평가 및 포지션 크기 계산을 위한 투자 금액"
            )
            
            # 위험도 평가 실행
            risk_assessment = calculate_risk_assessment(data, latest['Close'], investment_amount)
            
            if risk_assessment:
                # 종합 위험 등급 표시
                overall_risk = risk_assessment['overall_risk_grade']
                st.markdown(f"""
                <div style='padding: 15px; border-radius: 10px; 
                     background-color: {'#d4edda' if overall_risk['color'] == '🟢' else '#fff3cd' if overall_risk['color'] == '🟡' else '#fff0e6' if overall_risk['color'] == '🟠' else '#f8d7da'}; 
                     border-left: 5px solid {'#28a745' if overall_risk['color'] == '🟢' else '#ffc107' if overall_risk['color'] == '🟡' else '#fd7e14' if overall_risk['color'] == '🟠' else '#dc3545'}; 
                     margin-bottom: 15px;'>
                    <strong style='font-size: 1.1em;'>{overall_risk['color']} 종합 위험도: {overall_risk['grade']}</strong><br>
                    <small>위험 점수: {overall_risk['score']}/100 | {overall_risk['investment_advice']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                # 주요 메트릭 표시
                col_risk1, col_risk2, col_risk3 = st.columns(3)
                
                with col_risk1:
                    # 포지션 크기
                    position_sizing = risk_assessment['position_sizing']
                    st.metric(
                        "권장 포지션 크기",
                        f"{position_sizing['color']} {position_sizing['position_ratio']}%",
                        f"{position_sizing['recommended_amount']:,}원",
                        help="위험도를 고려한 권장 투자 비중"
                    )
                
                with col_risk2:
                    # 변동성
                    volatility = risk_assessment['volatility_analysis']
                    st.metric(
                        "연환산 변동성",
                        f"{volatility['volatility_color']} {volatility['volatility_20d']}%",
                        f"{volatility['volatility_grade']}",
                        help="20일 기준 연환산 변동성"
                    )
                
                with col_risk3:
                    # 손익비
                    sltp = risk_assessment['stop_loss_take_profit']
                    risk_reward_color = "🟢" if sltp['risk_reward_1'] >= 2 else "🟡" if sltp['risk_reward_1'] >= 1.5 else "🔴"
                    st.metric(
                        "손익비 (Risk:Reward)",
                        f"{risk_reward_color} 1:{sltp['risk_reward_1']}",
                        f"손절 {sltp['potential_loss']:.1f}% | 익절 {sltp['potential_gain_1']:.1f}%",
                        help="위험 대비 수익 비율"
                    )
                
                # 손절매/익절매 가격대
                st.markdown("**💹 손절매/익절매 가격대:**")
                col_sltp1, col_sltp2, col_sltp3 = st.columns(3)
                
                with col_sltp1:
                    st.metric(
                        "🛑 손절매",
                        f"{sltp['stop_loss_price']:,}원",
                        f"{sltp['potential_loss']:.1f}%",
                        delta_color="inverse",
                        help=f"방법: {sltp['stop_loss_method']}"
                    )
                
                with col_sltp2:
                    st.metric(
                        "🎯 1차 익절",
                        f"{sltp['take_profit_1']:,}원",
                        f"+{sltp['potential_gain_1']:.1f}%",
                        help="첫 번째 익절매 목표가"
                    )
                
                with col_sltp3:
                    st.metric(
                        "🚀 2차 익절",
                        f"{sltp['take_profit_2']:,}원",
                        f"+{sltp['potential_gain_2']:.1f}%",
                        help="두 번째 익절매 목표가"
                    )
                
                # 포지션 분할 제안
                position_sizing = risk_assessment['position_sizing']
                if position_sizing['split_amounts']:
                    st.markdown("**📊 분할 매수 제안:**")
                    st.markdown(f"• {position_sizing['split_suggestion']}")
                    
                    split_info = ""
                    for i, amount in enumerate(position_sizing['split_amounts'], 1):
                        split_info += f"**{i}차:** {amount:,}원 "
                    st.markdown(split_info)
                
                # 위험 관리 추천사항
                st.markdown("**💡 위험 관리 추천사항:**")
                recommendations = risk_assessment['recommendations']
                for recommendation in recommendations:
                    st.markdown(f"• {recommendation}")
                
                # 상세 위험 분석
                with st.expander("🔍 상세 위험 분석"):
                    # 위험 점수 구성 요소
                    st.markdown("**📊 위험 점수 구성:**")
                    risk_score = risk_assessment['risk_score']
                    
                    for factor_name, factor_score in risk_score['risk_factors']:
                        progress_ratio = factor_score / 30 if factor_name == '변동성' else factor_score / 20 if factor_name in ['추세', '기술적지표'] else factor_score / 15
                        progress_ratio = min(1.0, progress_ratio)
                        
                        st.markdown(f"• **{factor_name}**: {factor_score:.1f}점")
                        st.progress(progress_ratio)
                    
                    st.markdown(f"**총 위험 점수: {risk_score['total_score']:.1f}/100점**")
                    
                    st.markdown("---")
                    
                    # 시장 상황 분석
                    market_condition = risk_assessment['market_condition_risk']
                    if market_condition:
                        st.markdown("**🌍 시장 상황 분석:**")
                        st.markdown(f"• **종합 상황**: {market_condition['overall_color']} {market_condition['overall_condition']}")
                        st.markdown(f"• {market_condition['condition_description']}")
                        
                        st.markdown("**세부 상황:**")
                        for condition_name, status, color in market_condition['market_conditions']:
                            st.markdown(f"• {condition_name}: {color} {status}")
                    
                    st.markdown("---")
                    
                    # 변동성 상세 분석
                    volatility = risk_assessment['volatility_analysis']
                    st.markdown("**📈 변동성 상세 분석:**")
                    st.markdown(f"• 20일 변동성: {volatility['volatility_20d']}%")
                    st.markdown(f"• 60일 변동성: {volatility['volatility_60d']}%")
                    st.markdown(f"• ATR: {volatility['atr_percentage']}%")
                    st.markdown(f"• 볼린저밴드 폭: {volatility['bb_width']}%")
                    st.markdown(f"• 최대 낙폭: {volatility['max_drawdown']}%")
                    st.markdown(f"• 현재 낙폭: {volatility['current_drawdown']}%")
        
        # === 시간프레임별 투자 전략 시스템 ===
        st.subheader("⏰ 시간프레임별 투자 전략")
        
        if not data.empty:
            # 시간프레임별 신호 분석 실행
            timeframe_signals = generate_timeframe_specific_signals(data, latest['Close'])
            
            if timeframe_signals:
                # 종합 점수 및 권장 전략 표시
                recommended_strategy = timeframe_signals['recommended_strategy']
                timeframe_scores = timeframe_signals['timeframe_scores']
                
                # 권장 전략 카드
                st.markdown(f"""
                <div style='padding: 15px; border-radius: 10px; 
                     background-color: {'#d4edda' if recommended_strategy['color'] == '🟢' else '#fff3cd' if recommended_strategy['color'] == '🟡' else '#fff0e6' if recommended_strategy['color'] == '🟠' else '#f8d7da'}; 
                     border-left: 5px solid {'#28a745' if recommended_strategy['color'] == '🟢' else '#ffc107' if recommended_strategy['color'] == '🟡' else '#fd7e14' if recommended_strategy['color'] == '🟠' else '#dc3545'}; 
                     margin-bottom: 15px;'>
                    <strong style='font-size: 1.1em;'>{recommended_strategy['color']} 권장 전략: {recommended_strategy['strategy']}</strong><br>
                    <small>{recommended_strategy['description']}</small><br>
                    <small><strong>자금 배분:</strong> {recommended_strategy['allocation']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                # 시간프레임별 점수 표시
                col_tf1, col_tf2, col_tf3 = st.columns(3)
                
                scores = timeframe_scores['individual_scores']
                
                with col_tf1:
                    # 스윙 트레이딩 (1-5일)
                    swing_data = timeframe_signals.get('swing_trading', {})
                    if swing_data:
                        swing_color = swing_data['recommendation_color']
                        st.metric(
                            "🔄 스윙 트레이딩 (1-5일)",
                            f"{swing_color} {swing_data['score']}/100",
                            f"{swing_data['recommendation']}",
                            help=f"기간: {swing_data['time_horizon']} | {swing_data['strategy_description']}"
                        )
                
                with col_tf2:
                    # 포지션 트레이딩 (1-4주)
                    position_data = timeframe_signals.get('position_trading', {})
                    if position_data:
                        position_color = position_data['recommendation_color']
                        st.metric(
                            "📈 포지션 트레이딩 (1-4주)",
                            f"{position_color} {position_data['score']}/100",
                            f"{position_data['recommendation']}",
                            help=f"기간: {position_data['time_horizon']} | {position_data['strategy_description']}"
                        )
                
                with col_tf3:
                    # 장기 투자 (1-6개월)
                    longterm_data = timeframe_signals.get('long_term_investment', {})
                    if longterm_data:
                        longterm_color = longterm_data['recommendation_color']
                        st.metric(
                            "🏦 장기 투자 (1-6개월)",
                            f"{longterm_color} {longterm_data['score']}/100",
                            f"{longterm_data['recommendation']}",
                            help=f"기간: {longterm_data['time_horizon']} | {longterm_data['strategy_description']}"
                        )
                
                # 종합 점수
                overall_score = timeframe_scores['overall_score']
                best_timeframe = timeframe_scores.get('best_timeframe', 'N/A')
                worst_timeframe = timeframe_scores.get('worst_timeframe', 'N/A')
                
                st.markdown(f"""
                **🎯 종합 분석:**
                • **전체 점수**: {overall_score}/100
                • **최적 시간프레임**: {best_timeframe}
                • **주의 시간프레임**: {worst_timeframe}
                """)
                
                # 시간프레임별 상세 신호
                with st.expander("🔍 시간프레임별 상세 신호"):
                    
                    # 탭으로 구분
                    tab1, tab2, tab3 = st.tabs(["📊 스윙 트레이딩", "📈 포지션 트레이딩", "🏦 장기 투자"])
                    
                    with tab1:
                        # 스윙 트레이딩 상세
                        swing_data = timeframe_signals.get('swing_trading', {})
                        if swing_data:
                            st.markdown(f"**{swing_data['recommendation_color']} {swing_data['recommendation']}** (점수: {swing_data['score']}/100)")
                            st.markdown(f"**투자 기간:** {swing_data['time_horizon']}")
                            st.markdown(f"**전략 설명:** {swing_data['strategy_description']}")
                            
                            st.markdown("**📋 주요 신호:**")
                            for signal in swing_data.get('signals', []):
                                st.markdown(f"• {signal}")
                        else:
                            st.info("데이터가 부족하여 스윙 트레이딩 분석을 할 수 없습니다.")
                    
                    with tab2:
                        # 포지션 트레이딩 상세
                        position_data = timeframe_signals.get('position_trading', {})
                        if position_data:
                            st.markdown(f"**{position_data['recommendation_color']} {position_data['recommendation']}** (점수: {position_data['score']}/100)")
                            st.markdown(f"**투자 기간:** {position_data['time_horizon']}")
                            st.markdown(f"**전략 설명:** {position_data['strategy_description']}")
                            
                            st.markdown("**📋 주요 신호:**")
                            for signal in position_data.get('signals', []):
                                st.markdown(f"• {signal}")
                        else:
                            st.info("데이터가 부족하여 포지션 트레이딩 분석을 할 수 없습니다.")
                    
                    with tab3:
                        # 장기 투자 상세
                        longterm_data = timeframe_signals.get('long_term_investment', {})
                        if longterm_data:
                            st.markdown(f"**{longterm_data['recommendation_color']} {longterm_data['recommendation']}** (점수: {longterm_data['score']}/100)")
                            st.markdown(f"**투자 기간:** {longterm_data['time_horizon']}")
                            st.markdown(f"**전략 설명:** {longterm_data['strategy_description']}")
                            
                            st.markdown("**📋 주요 신호:**")
                            for signal in longterm_data.get('signals', []):
                                st.markdown(f"• {signal}")
                        else:
                            st.info("데이터가 부족하여 장기 투자 분석을 할 수 없습니다. (120일 이상 필요)")
                
                # 실행 가이드
                st.markdown("**🎯 실행 가이드:**")
                
                if recommended_strategy['strategy'] == '다중 시간프레임 투자':
                    st.markdown("""
                    • **1단계**: 장기 포지션 30% 먼저 구축
                    • **2단계**: 중기 추세 확인 후 40% 추가 투자  
                    • **3단계**: 단기 기회 포착으로 30% 스윙 매매
                    • **관리**: 각 시간프레임별 손절매 라인 준수
                    """)
                elif '집중 투자' in recommended_strategy['strategy']:
                    best_tf = timeframe_scores.get('best_timeframe', '')
                    if best_tf == 'swing':
                        st.markdown("""
                        • **1단계**: 단기 기술적 신호 확인 (RSI, 스토캐스틱)
                        • **2단계**: 80% 자금으로 스윙 포지션 구축
                        • **3단계**: 1-5일 내 익절/손절 실행
                        • **주의**: 빠른 의사결정과 엄격한 손절매 필수
                        """)
                    elif best_tf == 'position':
                        st.markdown("""
                        • **1단계**: 중기 추세 확인 (이동평균, MACD)
                        • **2단계**: 80% 자금으로 포지션 구축
                        • **3단계**: 1-4주 보유하며 추세 추종
                        • **관리**: 주간 단위 점검 및 추세 변화 모니터링
                        """)
                    elif best_tf == 'long_term':
                        st.markdown("""
                        • **1단계**: 장기 펀더멘털 및 기술적 분석
                        • **2단계**: 80% 자금으로 장기 포지션 구축  
                        • **3단계**: 1-6개월 보유하며 큰 흐름 추종
                        • **관리**: 월간 단위 점검 및 기본면 변화 모니터링
                        """)
                else:
                    st.markdown("""
                    • **보수적 접근**: 소액 분할 투자로 시작
                    • **지속적 모니터링**: 신호 변화 추적
                    • **리스크 관리**: 엄격한 손절매 및 포지션 관리
                    • **기회 포착**: 명확한 신호 발생시 비중 확대
                    """)

    # 하단 정보
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "📊 현재: Yahoo Finance 데이터 (15-20분 지연) | "
        "🚀 향후 업그레이드: 한국투자증권 API 실시간 연동 예정 (1-2초 지연) | "
        "💡 투자 결정은 신중히 하시기 바랍니다."
        "</div>", 
        unsafe_allow_html=True
    )
    
    # 향후 업그레이드 계획
    with st.expander("🔮 향후 업그레이드 계획"):
        st.markdown("""
        ### 🚀 **실시간 데이터 업그레이드 (v3.0 예정)**
        
        **현재 상태**: 
        - 📊 Yahoo Finance: 15-20분 지연
        - 🇰🇷 pykrx: 20분 지연
        
        **업그레이드 계획**:
        - ⚡ **한국투자증권 API** 연동
        - 🕐 **실시간 데이터**: 1-2초 지연으로 단축
        - 📈 **분봉 차트**: 1분/5분 단위 분석
        - 📋 **실시간 호가창**: 매수/매도 잔량 표시
        - 🔔 **알림 시스템**: 목표가/손절가 도달 알림
        
        **추가 기능**:
        - 📊 **재무제표 데이터**: PER, PBR, ROE 등
        - 🤖 **모의투자**: 가상 포트폴리오 관리
        - 📱 **모바일 최적화**: 반응형 UI 개선
        - 🔐 **개인화**: 관심종목 및 설정 저장
        
        **예상 출시**: 2024년 하반기
        """)
        
        st.info("💡 **참고**: 현재 버전도 일간/주간 투자 분석에는 충분히 정확한 데이터를 제공합니다.")

if __name__ == "__main__":
    main()