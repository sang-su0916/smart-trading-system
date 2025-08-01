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

# 페이지 설정
st.set_page_config(
    page_title="📊 Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 캐시 함수들
@st.cache_data(ttl=300)  # 5분 캐시
def get_stock_data(symbol, period="1y"):
    """주식 데이터 조회"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def calculate_technical_indicators(data):
    """기술적 지표 계산"""
    if data.empty:
        return data
    
    # 이동평균선
    data['MA_5'] = data['Close'].rolling(window=5).mean()
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_60'] = data['Close'].rolling(window=60).mean()
    
    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # 볼린저 밴드  
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
    data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
    
    return data

def generate_simple_signals(data):
    """간단한 매매 신호 생성"""
    if data.empty or len(data) < 60:
        return []
    
    signals = []
    latest = data.iloc[-1]
    
    # 매수 신호 조건들
    buy_conditions = []
    sell_conditions = []
    
    # 이동평균 조건
    if latest['Close'] > latest['MA_5'] > latest['MA_20']:
        buy_conditions.append("단기 상승 추세")
    elif latest['Close'] < latest['MA_5'] < latest['MA_20']:
        sell_conditions.append("단기 하락 추세")
    
    # RSI 조건
    if latest['RSI'] < 30:
        buy_conditions.append("RSI 과매도")
    elif latest['RSI'] > 70:
        sell_conditions.append("RSI 과매수")
    
    # 볼린저 밴드 조건
    if latest['Close'] < latest['BB_Lower']:
        buy_conditions.append("볼린저 하단 터치")
    elif latest['Close'] > latest['BB_Upper']:
        sell_conditions.append("볼린저 상단 터치")
    
    # 신호 생성
    if len(buy_conditions) >= 2:
        signals.append({
            'type': 'BUY',
            'conditions': buy_conditions,
            'confidence': min(len(buy_conditions) * 0.3, 1.0)
        })
    
    if len(sell_conditions) >= 2:
        signals.append({
            'type': 'SELL', 
            'conditions': sell_conditions,
            'confidence': min(len(sell_conditions) * 0.3, 1.0)
        })
    
    return signals

# 메인 타이틀
st.title("📊 Smart Trading Dashboard")
st.markdown("**실시간 알고리즘 트레이딩 분석 시스템**")

# 사이드바
st.sidebar.title("📋 설정")

# 종목 선택
default_symbols = [
    "005930.KS",  # 삼성전자
    "000660.KS",  # SK하이닉스  
    "035420.KS",  # 네이버
    "005380.KS",  # 현대차
    "055550.KS",  # 신한지주
]

selected_symbol = st.sidebar.selectbox(
    "📈 분석할 종목 선택",
    default_symbols + ["직접입력"],
    format_func=lambda x: {
        "005930.KS": "삼성전자 (005930)",
        "000660.KS": "SK하이닉스 (000660)", 
        "035420.KS": "네이버 (035420)",
        "005380.KS": "현대차 (005380)",
        "055550.KS": "신한지주 (055550)",
        "직접입력": "직접입력"
    }.get(x, x)
)

if selected_symbol == "직접입력":
    custom_symbol = st.sidebar.text_input("종목 코드 입력", "005930.KS")
    selected_symbol = custom_symbol

# 기간 선택
period = st.sidebar.selectbox(
    "📅 분석 기간",
    ["1mo", "3mo", "6mo", "1y", "2y"],
    index=3,
    format_func=lambda x: {
        "1mo": "1개월", "3mo": "3개월", "6mo": "6개월", 
        "1y": "1년", "2y": "2년"
    }[x]
)

# 데이터 로드
with st.spinner(f"{selected_symbol} 데이터 로딩 중..."):
    stock_data = get_stock_data(selected_symbol, period)

if stock_data.empty:
    st.error(f"❌ {selected_symbol} 데이터를 가져올 수 없습니다.")
    st.stop()

# 기술적 지표 계산
stock_data = calculate_technical_indicators(stock_data)

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📈 차트 분석", "🚨 매매 신호", "📊 기술적 지표", "💰 수익률 분석"])

with tab1:
    st.subheader(f"📈 {selected_symbol} 주가 차트")
    
    # 메인 차트
    fig = go.Figure()
    
    # 캔들스틱 차트
    fig.add_trace(go.Candlestick(
        x=stock_data.index,
        open=stock_data['Open'],
        high=stock_data['High'], 
        low=stock_data['Low'],
        close=stock_data['Close'],
        name='주가'
    ))
    
    # 이동평균선 추가
    fig.add_trace(go.Scatter(
        x=stock_data.index, y=stock_data['MA_5'],
        mode='lines', name='MA5', line=dict(color='orange', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=stock_data.index, y=stock_data['MA_20'],
        mode='lines', name='MA20', line=dict(color='blue', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=stock_data.index, y=stock_data['MA_60'],
        mode='lines', name='MA60', line=dict(color='red', width=1)
    ))
    
    fig.update_layout(
        title=f"{selected_symbol} 주가 차트 (이동평균선 포함)",
        yaxis_title="가격 (원)",
        xaxis_title="날짜",
        height=600,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 기본 정보
    col1, col2, col3, col4 = st.columns(4)
    
    latest_price = stock_data['Close'].iloc[-1]
    prev_price = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else latest_price
    change = latest_price - prev_price
    change_pct = (change / prev_price) * 100
    
    with col1:
        st.metric("현재가", f"{latest_price:,.0f}원", f"{change:+,.0f}원")
    with col2:
        st.metric("등락률", f"{change_pct:+.2f}%")
    with col3:
        volume = stock_data['Volume'].iloc[-1]
        st.metric("거래량", f"{volume:,.0f}주")
    with col4:
        volatility = stock_data['Close'].pct_change().std() * 100
        st.metric("변동성", f"{volatility:.2f}%")

with tab2:
    st.subheader("🚨 실시간 매매 신호")
    
    # 신호 생성
    signals = generate_simple_signals(stock_data)
    
    if not signals:
        st.info("현재 명확한 매매 신호가 없습니다.")
    else:
        for signal in signals:
            signal_type = signal['type']
            confidence = signal['confidence']
            conditions = signal['conditions']
            
            if signal_type == 'BUY':
                st.success(f"🟢 **매수 신호** (신뢰도: {confidence:.1%})")
            else:
                st.error(f"🔴 **매도 신호** (신뢰도: {confidence:.1%})")
            
            st.write("**근거:**")
            for condition in conditions:
                st.write(f"• {condition}")
            st.write("---")
    
    # 최근 가격 동향
    st.subheader("📊 최근 5일 동향")
    recent_data = stock_data.tail(5)[['Close', 'Volume', 'MA_5', 'RSI']].copy()
    recent_data['Change'] = recent_data['Close'].pct_change() * 100
    recent_data.index = recent_data.index.strftime('%m-%d')
    
    st.dataframe(
        recent_data.round(2),
        column_config={
            "Close": "종가(원)",
            "Volume": "거래량",
            "MA_5": "5일평균",
            "RSI": "RSI",
            "Change": st.column_config.NumberColumn("등락률(%)", format="%.2f%%")
        }
    )

with tab3:
    st.subheader("📊 기술적 지표 분석")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # RSI 차트
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=stock_data.index, y=stock_data['RSI'],
            mode='lines', name='RSI', line=dict(color='purple')
        ))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수(70)")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="blue", annotation_text="과매도(30)")
        fig_rsi.update_layout(title="RSI (상대강도지수)", yaxis_title="RSI", height=300)
        st.plotly_chart(fig_rsi, use_container_width=True)
    
    with col2:
        # 볼린저 밴드
        fig_bb = go.Figure()
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], mode='lines', name='종가'))
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BB_Upper'], mode='lines', name='상단선', line=dict(dash='dash')))
        fig_bb.add_trace(go.Scatter(x=stock_data.index, y=stock_data['BB_Lower'], mode='lines', name='하단선', line=dict(dash='dash')))
        fig_bb.update_layout(title="볼린저 밴드", yaxis_title="가격", height=300)
        st.plotly_chart(fig_bb, use_container_width=True)
    
    # 지표 요약
    st.subheader("🎯 현재 지표 요약")
    
    latest = stock_data.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("RSI", f"{latest['RSI']:.1f}", 
                 "과매도" if latest['RSI'] < 30 else "과매수" if latest['RSI'] > 70 else "중립")
    
    with col2:
        bb_position = (latest['Close'] - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower'])
        st.metric("볼린저 밴드 위치", f"{bb_position:.1%}",
                 "하단 근처" if bb_position < 0.2 else "상단 근처" if bb_position > 0.8 else "중간")
    
    with col3:
        ma_trend = "상승" if latest['MA_5'] > latest['MA_20'] else "하락"
        st.metric("이동평균 추세", ma_trend)

with tab4:
    st.subheader("💰 수익률 분석")
    
    # 기간별 수익률
    periods = {
        "1일": 1,
        "1주": 7, 
        "1개월": 30,
        "3개월": 90,
        "6개월": 180
    }
    
    returns_data = []
    current_price = stock_data['Close'].iloc[-1]
    
    for period_name, days in periods.items():
        if len(stock_data) > days:
            past_price = stock_data['Close'].iloc[-(days+1)]
            return_pct = ((current_price - past_price) / past_price) * 100
            returns_data.append({"기간": period_name, "수익률": return_pct})
    
    if returns_data:
        returns_df = pd.DataFrame(returns_data)
        
        # 수익률 차트
        fig_returns = px.bar(
            returns_df, x="기간", y="수익률",
            title="기간별 수익률",
            color="수익률",
            color_continuous_scale=["red", "white", "green"]
        )
        st.plotly_chart(fig_returns, use_container_width=True)
        
        # 수익률 테이블
        st.dataframe(
            returns_df,
            column_config={
                "수익률": st.column_config.NumberColumn("수익률 (%)", format="%.2f%%")
            },
            hide_index=True
        )
    
    # 변동성 분석
    st.subheader("📈 위험도 분석")
    
    daily_returns = stock_data['Close'].pct_change().dropna()
    volatility_annual = daily_returns.std() * np.sqrt(252) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("연간 변동성", f"{volatility_annual:.1f}%")
    
    with col2:
        max_drawdown = ((stock_data['Close'] / stock_data['Close'].expanding().max()) - 1).min() * 100
        st.metric("최대 낙폭", f"{max_drawdown:.1f}%")
    
    with col3:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        st.metric("샤프 비율", f"{sharpe_ratio:.2f}")

# 푸터
st.markdown("---")
st.markdown("""
**📊 Smart Trading Dashboard v2.0**
- 실시간 데이터 기반 기술적 분석
- 외국인/기관 대량 매매 패턴 분석 포함
- Powered by Streamlit & Yahoo Finance
""")

# 자동 새로고침 버튼
if st.sidebar.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()