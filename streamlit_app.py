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
    
    return data

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