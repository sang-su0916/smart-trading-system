"""
간단한 Streamlit 기반 트레이딩 대시보드
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 페이지 설정
st.set_page_config(
    page_title="📊 Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 기본 데이터베이스 연결 시도
try:
    from src.database.database_manager import DatabaseManager
    from src.database.market_data_service import MarketDataService
    
    db_manager = DatabaseManager('data/trading_system.db')
    market_service = MarketDataService('data/trading_system.db')
    DB_AVAILABLE = True
    st.success("✅ 데이터베이스 연결 성공")
except Exception as e:
    st.error(f"❌ 데이터베이스 연결 실패: {str(e)}")
    DB_AVAILABLE = False

# 메인 타이틀
st.title("📊 Smart Trading Dashboard")
st.markdown("---")

# 사이드바 네비게이션
st.sidebar.title("📋 Navigation")
page = st.sidebar.selectbox(
    "페이지 선택",
    ["🏠 홈", "💼 포트폴리오", "📈 시장 분석", "🚨 신호 모니터링", "⚠️ 리스크 관리", "⚙️ 설정"]
)

if not DB_AVAILABLE:
    st.error("데이터베이스에 연결할 수 없습니다. 시스템을 확인해주세요.")
    st.stop()

# 홈 페이지
if page == "🏠 홈":
    st.header("🏠 시스템 개요")
    
    # 시스템 상태
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("데이터베이스", "연결됨", "✅")
    
    with col2:
        try:
            portfolios = db_manager.get_portfolios()
            portfolio_count = len(portfolios)
            st.metric("포트폴리오 수", portfolio_count, "📊")
        except:
            st.metric("포트폴리오 수", "오류", "❌")
    
    with col3:
        try:
            symbols = db_manager.get_available_symbols()
            st.metric("추적 종목 수", len(symbols), "📈")
        except:
            st.metric("추적 종목 수", "오류", "❌")
    
    with col4:
        try:
            signals = db_manager.get_recent_signals(hours=24)
            st.metric("24시간 신호", len(signals), "🚨")
        except:
            st.metric("24시간 신호", "오류", "❌")
    
    st.markdown("---")
    
    # 최근 활동
    st.subheader("📊 최근 활동")
    
    try:
        # 최근 거래
        recent_trades = db_manager.get_trade_history(days=7)
        if not recent_trades.empty:
            st.write("**최근 7일 거래 내역:**")
            st.dataframe(recent_trades[['symbol', 'trade_type', 'quantity', 'price', 'trade_date']])
        else:
            st.info("최근 거래 내역이 없습니다.")
            
        # 최근 신호
        recent_signals = db_manager.get_recent_signals(hours=24)
        if not recent_signals.empty:
            st.write("**최근 24시간 매매 신호:**")
            st.dataframe(recent_signals[['symbol', 'signal_type', 'confidence', 'signal_date']])
        else:
            st.info("최근 매매 신호가 없습니다.")
            
    except Exception as e:
        st.error(f"데이터 조회 오류: {str(e)}")

# 포트폴리오 페이지
elif page == "💼 포트폴리오":
    st.header("💼 포트폴리오 관리")
    
    try:
        portfolios = db_manager.get_portfolios()
        
        if portfolios.empty:
            st.warning("포트폴리오가 없습니다.")
        else:
            # 포트폴리오 선택
            portfolio_names = portfolios['name'].tolist()
            selected_portfolio = st.selectbox("포트폴리오 선택", portfolio_names)
            
            # 선택된 포트폴리오 정보
            portfolio_info = portfolios[portfolios['name'] == selected_portfolio].iloc[0]
            portfolio_id = portfolio_info['id']
            
            # 포트폴리오 요약
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("초기 자본", f"{portfolio_info['initial_capital']:,.0f}원")
            
            with col2:
                st.metric("현재 가치", f"{portfolio_info['current_value']:,.0f}원")
            
            with col3:
                pnl = portfolio_info['current_value'] - portfolio_info['initial_capital']
                pnl_pct = (pnl / portfolio_info['initial_capital']) * 100
                st.metric("손익", f"{pnl:,.0f}원", f"{pnl_pct:.2f}%")
            
            # 보유 종목
            st.subheader("📊 보유 종목")
            holdings = db_manager.get_portfolio_holdings(portfolio_id)
            
            if not holdings.empty:
                st.dataframe(holdings[['symbol', 'quantity', 'avg_price', 'current_price', 'market_value', 'unrealized_pnl_pct']])
                
                # 종목별 비중 차트
                if len(holdings) > 1:
                    fig = px.pie(holdings, values='market_value', names='symbol', title='포트폴리오 구성 비중')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("보유 종목이 없습니다.")
                
    except Exception as e:
        st.error(f"포트폴리오 조회 오류: {str(e)}")

# 시장 분석 페이지
elif page == "📈 시장 분석":
    st.header("📈 시장 분석")
    
    try:
        symbols = db_manager.get_available_symbols()
        
        if not symbols:
            st.warning("분석할 종목이 없습니다.")
        else:
            # 종목 선택
            selected_symbol = st.selectbox("종목 선택", symbols)
            
            # 데이터 조회
            data = market_service.get_cached_data(selected_symbol)
            
            if not data.empty:
                # 가격 차트
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='가격'
                ))
                
                fig.update_layout(
                    title=f"{selected_symbol} 주가 차트",
                    yaxis_title="가격 (원)",
                    xaxis_title="날짜",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 기본 통계
                st.subheader("📊 기본 통계")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("현재가", f"{data['close'].iloc[-1]:,.0f}원")
                
                with col2:
                    change = data['close'].iloc[-1] - data['close'].iloc[-2]
                    change_pct = (change / data['close'].iloc[-2]) * 100
                    st.metric("전일대비", f"{change:,.0f}원", f"{change_pct:.2f}%")
                
                with col3:
                    st.metric("거래량", f"{data['volume'].iloc[-1]:,.0f}주")
                
                with col4:
                    volatility = data['close'].pct_change().std() * 100
                    st.metric("변동성", f"{volatility:.2f}%")
                    
            else:
                st.error(f"{selected_symbol} 데이터를 찾을 수 없습니다.")
                
    except Exception as e:
        st.error(f"시장 분석 오류: {str(e)}")

# 신호 모니터링 페이지
elif page == "🚨 신호 모니터링":
    st.header("🚨 매매 신호 모니터링")
    
    try:
        # 시간 범위 선택
        hours = st.selectbox("조회 기간", [1, 6, 12, 24, 48], index=3)
        
        signals = db_manager.get_recent_signals(hours=hours)
        
        if not signals.empty:
            # 신호 타입별 필터
            signal_types = signals['signal_type'].unique().tolist()
            selected_types = st.multiselect("신호 타입 필터", signal_types, default=signal_types)
            
            filtered_signals = signals[signals['signal_type'].isin(selected_types)]
            
            if not filtered_signals.empty:
                # 신호 요약
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    buy_signals = len(filtered_signals[filtered_signals['signal_type'] == 'BUY'])
                    st.metric("매수 신호", buy_signals, "🟢")
                
                with col2:
                    sell_signals = len(filtered_signals[filtered_signals['signal_type'] == 'SELL'])
                    st.metric("매도 신호", sell_signals, "🔴")
                
                with col3:
                    hold_signals = len(filtered_signals[filtered_signals['signal_type'] == 'HOLD'])
                    st.metric("관망 신호", hold_signals, "🟡")
                
                # 신호 테이블
                st.subheader("📋 신호 상세")
                display_columns = ['symbol', 'signal_type', 'signal_strength', 'confidence', 'signal_date', 'notes']
                st.dataframe(filtered_signals[display_columns])
                
                # 신호 타입별 분포 차트
                if len(filtered_signals) > 1:
                    signal_counts = filtered_signals['signal_type'].value_counts()
                    fig = px.bar(x=signal_counts.index, y=signal_counts.values, title='신호 타입별 분포')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("필터 조건에 맞는 신호가 없습니다.")
        else:
            st.info(f"최근 {hours}시간 동안 신호가 없습니다.")
            
    except Exception as e:
        st.error(f"신호 모니터링 오류: {str(e)}")

# 리스크 관리 페이지
elif page == "⚠️ 리스크 관리":
    st.header("⚠️ 리스크 관리")
    
    try:
        # VaR 계산 시도
        st.subheader("📊 포트폴리오 리스크 분석")
        
        portfolios = db_manager.get_portfolios()
        if not portfolios.empty:
            portfolio_names = portfolios['name'].tolist()
            selected_portfolio = st.selectbox("포트폴리오 선택", portfolio_names)
            
            portfolio_info = portfolios[portfolios['name'] == selected_portfolio].iloc[0]
            portfolio_id = portfolio_info['id']
            
            holdings = db_manager.get_portfolio_holdings(portfolio_id)
            
            if not holdings.empty:
                st.write("**포트폴리오 구성:**")
                st.dataframe(holdings[['symbol', 'quantity', 'market_value', 'weight']])
                
                # 간단한 리스크 지표
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_value = holdings['market_value'].sum() if 'market_value' in holdings.columns else 0
                    st.metric("총 자산", f"{total_value:,.0f}원")
                
                with col2:
                    max_weight = holdings['weight'].max() if 'weight' in holdings.columns else 0
                    st.metric("최대 비중", f"{max_weight:.1f}%")
                
                with col3:
                    diversification = len(holdings)
                    st.metric("분산도", f"{diversification}개 종목")
                    
                # 집중도 위험 경고
                if max_weight > 50:
                    st.warning("⚠️ 특정 종목 집중도가 높습니다. 분산투자를 고려하세요.")
                elif max_weight > 30:
                    st.info("ℹ️ 포트폴리오가 적절히 분산되어 있습니다.")
                else:
                    st.success("✅ 포트폴리오가 잘 분산되어 있습니다.")
                    
            else:
                st.info("포트폴리오에 보유 종목이 없습니다.")
        else:
            st.info("포트폴리오가 없습니다.")
            
    except Exception as e:
        st.error(f"리스크 관리 오류: {str(e)}")

# 설정 페이지
elif page == "⚙️ 설정":
    st.header("⚙️ 시스템 설정")
    
    # 데이터베이스 상태
    st.subheader("📊 데이터베이스 상태")
    
    try:
        data_status = market_service.get_data_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("총 종목 수", data_status.get('total_symbols', 0))
        
        with col2:
            st.metric("상태", data_status.get('status', 'unknown'))
        
        with col3:
            outdated = data_status.get('outdated_symbols', 0)
            st.metric("업데이트 필요", outdated)
        
        # 데이터 업데이트 버튼
        if st.button("🔄 데이터 업데이트"):
            with st.spinner("데이터 업데이트 중..."):
                try:
                    symbols = db_manager.get_available_symbols()
                    if symbols:
                        results = market_service.update_latest_data(symbols[:5])  # 처음 5개만
                        success_count = sum(results.values())
                        st.success(f"✅ {success_count}/{len(symbols[:5])}개 종목 업데이트 완료")
                    else:
                        st.info("업데이트할 종목이 없습니다.")
                except Exception as e:
                    st.error(f"업데이트 실패: {str(e)}")
        
        # 시스템 정보
        st.subheader("🖥️ 시스템 정보")
        st.write(f"**현재 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**데이터베이스:** data/trading_system.db")
        st.write(f"**상태:** {'정상' if DB_AVAILABLE else '오류'}")
        
    except Exception as e:
        st.error(f"설정 페이지 오류: {str(e)}")

# 푸터
st.markdown("---")
st.markdown("📊 Smart Trading Dashboard - Powered by Streamlit")