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
    "105560.KS",  # KB금융
    "017670.KS",  # SK텔레콤
    "051910.KS",  # LG화학
    "012330.KS",  # 현대모비스
    "028260.KS",  # 삼성물산
    "207940.KS",  # 삼성바이오로직스
    "006400.KS",  # 삼성SDI
    "068270.KS",  # 셀트리온
    "323410.KS",  # 카카오뱅크
    "035720.KS",  # 카카오
    "003670.KS",  # 포스코홀딩스
    "096770.KS",  # SK이노베이션
    "000270.KS",  # 기아
    "034730.KS",  # SK
    "032830.KS",  # 삼성생명
    # 코스닥 주요 종목
    "091990.KQ",  # 셀트리온헬스케어
    "196170.KQ",  # 알테오젠
    "022100.KQ",  # 포스코ICT
    "357780.KQ",  # 솔브레인
    "263750.KQ",  # 펄어비스
    "039490.KQ",  # 키움증권
    "058470.KQ",  # 리노공업
    "240810.KQ",  # 원익IPS
    "293490.KQ",  # 카카오게임즈
    "256940.KQ",  # 케이팝스타
    # 해외 주요 종목
    "AAPL",       # 애플
    "MSFT",       # 마이크로소프트
    "GOOGL",      # 구글
    "TSLA",       # 테슬라
    "NVDA",       # 엔비디아
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
        "105560.KS": "KB금융 (105560)",
        "017670.KS": "SK텔레콤 (017670)",
        "051910.KS": "LG화학 (051910)",
        "012330.KS": "현대모비스 (012330)",
        "028260.KS": "삼성물산 (028260)",
        "207940.KS": "삼성바이오로직스 (207940)",
        "006400.KS": "삼성SDI (006400)",
        "068270.KS": "셀트리온 (068270)",
        "323410.KS": "카카오뱅크 (323410)",
        "035720.KS": "카카오 (035720)",
        "003670.KS": "포스코홀딩스 (003670)",
        "096770.KS": "SK이노베이션 (096770)",
        "000270.KS": "기아 (000270)",
        "034730.KS": "SK (034730)",
        "032830.KS": "삼성생명 (032830)",
        # 코스닥
        "091990.KQ": "셀트리온헬스케어 (091990)",
        "196170.KQ": "알테오젠 (196170)",
        "022100.KQ": "포스코ICT (022100)",
        "357780.KQ": "솔브레인 (357780)",
        "263750.KQ": "펄어비스 (263750)",
        "039490.KQ": "키움증권 (039490)",
        "058470.KQ": "리노공업 (058470)",
        "240810.KQ": "원익IPS (240810)",
        "293490.KQ": "카카오게임즈 (293490)",
        "256940.KQ": "케이팝스타 (256940)",
        # 해외
        "AAPL": "애플 (AAPL)",
        "MSFT": "마이크로소프트 (MSFT)",
        "GOOGL": "구글 (GOOGL)",
        "TSLA": "테슬라 (TSLA)",
        "NVDA": "엔비디아 (NVDA)",
        "직접입력": "직접입력"
    }.get(x, x)
)

if selected_symbol == "직접입력":
    st.sidebar.markdown("**💡 종목 코드 입력 가이드:**")
    st.sidebar.markdown("- 코스피: 종목코드.KS (예: 005930.KS)")
    st.sidebar.markdown("- 코스닥: 종목코드.KQ (예: 035720.KQ)")  
    st.sidebar.markdown("- 미국: 심볼 (예: AAPL, TSLA)")
    
    # 인기 종목 추천
    st.sidebar.markdown("**🔥 인기 종목 코드:**")
    popular_stocks = {
        "코스피": ["373220.KS (LG에너지솔루션)", "207940.KS (삼성바이오로직스)", "005930.KS (삼성전자)"],
        "코스닥": ["091990.KQ (셀트리온헬스케어)", "196170.KQ (알테오젠)", "293490.KQ (카카오게임즈)"],
        "해외": ["AAPL (애플)", "TSLA (테슬라)", "NVDA (엔비디아)"]
    }
    
    for market, stocks in popular_stocks.items():
        with st.sidebar.expander(f"📊 {market} 인기종목"):
            for stock in stocks:
                if st.button(f"📌 {stock.split('(')[1].replace(')', '')}", key=f"pop_{stock}"):
                    custom_symbol = stock.split()[0]
                    st.sidebar.success(f"선택: {custom_symbol}")
                    selected_symbol = custom_symbol
    
    custom_symbol = st.sidebar.text_input("종목 코드 입력", "005930.KS", 
                                         help="예시: 005930.KS (삼성전자), 035720.KQ (카카오)")
    selected_symbol = custom_symbol
    
    # 종목 유효성 검사 버튼
    if st.sidebar.button("🔍 종목 확인"):
        try:
            test_ticker = yf.Ticker(custom_symbol)
            test_data = test_ticker.history(period="5d")
            if not test_data.empty:
                st.sidebar.success(f"✅ {custom_symbol} 데이터 확인!")
                # 기본 정보 표시
                info = test_ticker.info
                if 'longName' in info:
                    st.sidebar.write(f"**회사명**: {info['longName']}")
            else:
                st.sidebar.error("❌ 해당 종목 데이터가 없습니다")
        except:
            st.sidebar.error("❌ 종목 코드를 확인해주세요")

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