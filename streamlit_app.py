# -*- coding: utf-8 -*-
"""
Streamlit Cloud용 간단한 알고리즘 트레이딩 대시보드
데이터베이스 없이 실시간 데이터로 작동
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
from streamlit_searchbox import st_searchbox
import warnings
warnings.filterwarnings('ignore')

# pykrx 시도, 실패시 폴백
try:
    import pykrx.stock as stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
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

def get_stock_data(symbol, period="1y"):
    """주가 데이터 가져오기"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data
    except Exception:
        return pd.DataFrame()

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
    st.title("📈 Smart Trading Dashboard")
    
    # 사이드바
    st.sidebar.header("종목 선택")
    
    # 종목 검색
    selected_name = st_searchbox(
        search_function=search_stocks,
        placeholder="종목명 또는 종목코드를 입력하세요...",
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
    
    # 데이터 로드
    with st.spinner("데이터 로딩 중..."):
        data = get_stock_data(selected_symbol, period)
        
    if not data.empty:
        # 기술적 지표 계산
        data = calculate_technical_indicators(data)
        
        # 현재 가격 정보
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
        
        # 차트 표시
        st.subheader("📊 주가 차트")
        chart = create_candlestick_chart(data, selected_name)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        
        # 공정가치 분석
        st.markdown("---")
        st.subheader("⚖️ 공정가치 분석")
        
        fair_value_analysis = analyze_fair_value(data, latest['Close'])
        
        # 분석 결과 표시
        col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
        
        with col_analysis1:
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
                "종합 점수",
                "{} {}/100".format(score_color, score),
                help="기술적 지표 종합 점수 (높을수록 매수, 낮을수록 매도)"
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
        
        trading_signals = analyze_trading_signals(data, latest['Close'])
        
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
                        "{:+.1f}%".format((target1 / latest['Close'] - 1) * 100)
                    )
                
                with col_price2:
                    target2 = trading_signals['target_price_2']
                    st.metric(
                        "2차 목표가" if trading_signals['signal_strength'] > 0 else "2차 목표가(하락)",
                        "{:,.0f}원".format(target2),
                        "{:+.1f}%".format((target2 / latest['Close'] - 1) * 100)
                    )
                
                with col_price3:
                    stop_loss = trading_signals['stop_loss']
                    st.metric(
                        "손절가",
                        "{:,.0f}원".format(stop_loss),
                        "{:+.1f}%".format((stop_loss / latest['Close'] - 1) * 100)
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
        
        # 기본 정보
        with st.expander("📖 기본 정보", expanded=False):
            st.markdown("""
            **📈 캔들스틱 차트란?**
            - **빨간색 캔들**: 하락 (시가 > 종가)
            - **파란색 캔들**: 상승 (시가 < 종가)
            - **위아래 선**: 당일 최고가와 최저가
            
            **🔄 이동평균선 (MA):**
            - **MA5**: 5일 평균가격
            - **MA20**: 20일 평균가격
            - **골든크로스**: 단기선이 장기선을 상향돌파 (매수신호)
            - **데드크로스**: 단기선이 장기선을 하향돌파 (매도신호)
            
            **📊 RSI (상대강도지수):**
            - 0~100 사이 값으로 과매수/과매도 측정
            - 70 이상: 과매수 (매도 고려)
            - 30 이하: 과매도 (매수 고려)
            
            **📈 볼린저밴드:**
            - 중심선(20일 이동평균) ± 2표준편차
            - 하단 터치: 매수 신호 가능성
            - 상단 터치: 매도 신호 가능성
            - 밴드 폭 축소: 큰 변동성 임박
            
            **⚡ MACD:**
            - 단기/장기 이동평균의 차이로 추세 변화 포착
            - MACD선 > 시그널선: 상승 신호
            - MACD선 < 시그널선: 하락 신호
            
            **🎯 스토캐스틱:**
            - 일정기간 고가/저가 대비 현재가 위치
            - 80 이상: 과매수권
            - 20 이하: 과매도권
            
            **🚦 매매 신호 해석:**
            - **신호 강도**: -100(강한 매도) ~ +100(강한 매수)
            - **종합 판단**: 여러 지표를 종합하여 최종 신호 결정
            - **목표가/손절가**: 변동성 기반 리스크 관리 가격
            """)
    
    # 데이터가 비어있는 경우 처리
    if data.empty:
        error_message = "{} 데이터를 불러올 수 없습니다. 다른 종목을 선택해 주세요.".format(selected_name)
        st.error(error_message)
    
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