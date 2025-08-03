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
            
            **📊 RSI:**
            - 0~100 사이 값
            - 70 이상: 과매수
            - 30 이하: 과매도
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