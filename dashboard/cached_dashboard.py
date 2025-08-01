"""
성능 개선된 Streamlit 기반 트레이딩 대시보드 (캐시 적용)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
import time
from functools import wraps

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 페이지 설정 (성능 최적화)
st.set_page_config(
    page_title="📊 Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 캐시 설정
@st.cache_data(ttl=300)  # 5분 캐시
def load_database_connection():
    """데이터베이스 연결을 캐시"""
    try:
        from src.database.database_manager import DatabaseManager
        from src.database.market_data_service import MarketDataService
        
        db_manager = DatabaseManager('data/trading_system.db')
        market_service = MarketDataService('data/trading_system.db')
        return db_manager, market_service, True
    except Exception as e:
        return None, None, False

@st.cache_data(ttl=60)  # 1분 캐시
def get_system_status(db_manager):
    """시스템 상태를 캐시"""
    try:
        portfolios = db_manager.get_portfolios()
        symbols = db_manager.get_available_symbols()
        signals = db_manager.get_recent_signals(hours=24)
        
        return {
            'portfolio_count': len(portfolios),
            'symbol_count': len(symbols),
            'signal_count': len(signals),
            'status': 'normal'
        }
    except Exception as e:
        return {
            'portfolio_count': 0,
            'symbol_count': 0,
            'signal_count': 0,
            'status': 'error',
            'error': str(e)
        }

@st.cache_data(ttl=300)  # 5분 캐시
def get_portfolios_cached(db_manager):
    """포트폴리오 데이터를 캐시"""
    try:
        return db_manager.get_portfolios()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=180)  # 3분 캐시
def get_market_data_cached(market_service, symbol):
    """시장 데이터를 캐시"""
    try:
        return market_service.get_cached_data(symbol)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)  # 1분 캐시
def get_recent_signals_cached(db_manager, hours=24):
    """최근 신호를 캐시"""
    try:
        return db_manager.get_recent_signals(hours=hours)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=120)  # 2분 캐시
def get_trade_history_cached(db_manager, days=7):
    """거래 내역을 캐시"""
    try:
        return db_manager.get_trade_history(days=days)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)  # 5분 캐시
def get_portfolio_holdings_cached(db_manager, portfolio_id):
    """포트폴리오 보유 종목을 캐시"""
    try:
        return db_manager.get_portfolio_holdings(portfolio_id)
    except Exception:
        return pd.DataFrame()

# 성능 모니터링 데코레이터
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # 세션 상태에 성능 기록 저장
        if 'performance_log' not in st.session_state:
            st.session_state.performance_log = []
        
        st.session_state.performance_log.append({
            'function': func.__name__,
            'duration': end_time - start_time,
            'timestamp': datetime.now()
        })
        
        # 최대 10개 기록만 유지
        if len(st.session_state.performance_log) > 10:
            st.session_state.performance_log = st.session_state.performance_log[-10:]
        
        return result
    return wrapper

# 메인 애플리케이션 시작
def main():
    # 데이터베이스 연결
    db_manager, market_service, db_available = load_database_connection()
    
    # 메인 타이틀
    st.title("📊 Smart Trading Dashboard (성능 최적화)")
    
    # 성능 정보 표시 (디버그 모드)
    if st.sidebar.checkbox("🔧 성능 모니터링"):
        if 'performance_log' in st.session_state:
            with st.sidebar.expander("⏱️ 성능 로그"):
                for log in st.session_state.performance_log[-5:]:  # 최근 5개만
                    st.write(f"**{log['function']}**: {log['duration']:.3f}초")
    
    st.markdown("---")
    
    # 사이드바 네비게이션
    st.sidebar.title("📋 Navigation")
    page = st.sidebar.selectbox(
        "페이지 선택",
        ["🏠 홈", "💼 포트폴리오", "📈 시장 분석", "🚨 신호 모니터링", "⚠️ 리스크 관리", "⚙️ 설정"]
    )
    
    # 자동 새로고침 옵션
    auto_refresh = st.sidebar.checkbox("🔄 자동 새로고침 (30초)")
    if auto_refresh:
        time.sleep(1)  # 잠깐 대기
        st.rerun()
    
    if not db_available:
        st.error("데이터베이스에 연결할 수 없습니다. 시스템을 확인해주세요.")
        return
    
    # 페이지 라우팅
    if page == "🏠 홈":
        show_home_page(db_manager, market_service)
    elif page == "💼 포트폴리오":
        show_portfolio_page(db_manager)
    elif page == "📈 시장 분석":
        show_market_analysis_page(db_manager, market_service)
    elif page == "🚨 신호 모니터링":
        show_signal_monitoring_page(db_manager)
    elif page == "⚠️ 리스크 관리":
        show_risk_management_page(db_manager)
    elif page == "⚙️ 설정":
        show_settings_page(db_manager, market_service)
    
    # 푸터
    st.markdown("---")
    st.markdown("📊 Smart Trading Dashboard v2.0 - 성능 최적화 | Powered by Streamlit")

@monitor_performance
def show_home_page(db_manager, market_service):
    """홈 페이지"""
    st.header("🏠 시스템 개요")
    
    # 시스템 상태 (캐시된 데이터 사용)
    status = get_system_status(db_manager)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("데이터베이스", "연결됨", "✅" if status['status'] == 'normal' else "❌")
    
    with col2:
        st.metric("포트폴리오 수", status['portfolio_count'], "📊")
    
    with col3:
        st.metric("추적 종목 수", status['symbol_count'], "📈")
    
    with col4:
        st.metric("24시간 신호", status['signal_count'], "🚨")
    
    st.markdown("---")
    
    # 최근 활동 (캐시된 데이터 사용)
    st.subheader("📊 최근 활동")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**최근 7일 거래 내역:**")
        recent_trades = get_trade_history_cached(db_manager, days=7)
        if not recent_trades.empty:
            display_trades = recent_trades[['symbol', 'trade_type', 'quantity', 'price', 'trade_date']].head(5)
            st.dataframe(display_trades, use_container_width=True)
        else:
            st.info("최근 거래 내역이 없습니다.")
    
    with col2:
        st.write("**최근 24시간 매매 신호:**")
        recent_signals = get_recent_signals_cached(db_manager, hours=24)
        if not recent_signals.empty:
            display_signals = recent_signals[['symbol', 'signal_type', 'confidence', 'signal_date']].head(5)
            st.dataframe(display_signals, use_container_width=True)
        else:
            st.info("최근 매매 신호가 없습니다.")

@monitor_performance
def show_portfolio_page(db_manager):
    """포트폴리오 페이지"""
    st.header("💼 포트폴리오 관리")
    
    portfolios = get_portfolios_cached(db_manager)
    
    if portfolios.empty:
        st.warning("포트폴리오가 없습니다.")
        if st.button("📊 샘플 포트폴리오 생성"):
            with st.spinner("포트폴리오 생성 중..."):
                try:
                    db_manager.create_portfolio("샘플 포트폴리오", 10000000, "기본 포트폴리오")
                    st.success("✅ 샘플 포트폴리오가 생성되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"포트폴리오 생성 실패: {str(e)}")
        return
    
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
        color = "green" if pnl >= 0 else "red"
        st.metric("손익", f"{pnl:,.0f}원", f"{pnl_pct:.2f}%")
    
    # 보유 종목 (캐시된 데이터 사용)
    st.subheader("📊 보유 종목")
    holdings = get_portfolio_holdings_cached(db_manager, portfolio_id)
    
    if not holdings.empty:
        st.dataframe(holdings[['symbol', 'quantity', 'avg_price', 'current_price', 'market_value']], use_container_width=True)
        
        # 종목별 비중 차트 (성능 최적화)
        if len(holdings) > 1:
            with st.spinner("차트 생성 중..."):
                fig = px.pie(
                    holdings, 
                    values='market_value', 
                    names='symbol', 
                    title='포트폴리오 구성 비중',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("보유 종목이 없습니다.")

@monitor_performance
def show_market_analysis_page(db_manager, market_service):
    """시장 분석 페이지"""
    st.header("📈 시장 분석")
    
    try:
        symbols = db_manager.get_available_symbols()
        
        if not symbols:
            st.warning("분석할 종목이 없습니다.")
            return
        
        # 종목 선택
        selected_symbol = st.selectbox("종목 선택", symbols)
        
        # 데이터 조회 (캐시된 데이터 사용)
        with st.spinner("데이터 로딩 중..."):
            data = get_market_data_cached(market_service, selected_symbol)
        
        if not data.empty:
            # 차트 표시 옵션
            chart_type = st.radio("차트 타입", ["캔들스틱", "라인"], horizontal=True)
            
            # 가격 차트
            fig = go.Figure()
            
            if chart_type == "캔들스틱":
                fig.add_trace(go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='가격'
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data['close'],
                    mode='lines',
                    name='종가',
                    line=dict(color='blue', width=2)
                ))
            
            fig.update_layout(
                title=f"{selected_symbol} 주가 차트",
                yaxis_title="가격 (원)",
                xaxis_title="날짜",
                height=500,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 기본 통계
            st.subheader("📊 기본 통계")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                current_price = data['close'].iloc[-1]
                st.metric("현재가", f"{current_price:,.0f}원")
            
            with col2:
                if len(data) >= 2:
                    change = data['close'].iloc[-1] - data['close'].iloc[-2]
                    change_pct = (change / data['close'].iloc[-2]) * 100
                    st.metric("전일대비", f"{change:,.0f}원", f"{change_pct:.2f}%")
                else:
                    st.metric("전일대비", "N/A", "N/A")
            
            with col3:
                volume = data['volume'].iloc[-1]
                st.metric("거래량", f"{volume:,.0f}주")
            
            with col4:
                volatility = data['close'].pct_change().std() * 100
                st.metric("변동성", f"{volatility:.2f}%")
                
            # 간단한 기술적 분석
            st.subheader("📈 간단한 기술적 분석")
            
            # 이동평균선 계산
            data['MA_5'] = data['close'].rolling(window=5).mean()
            data['MA_20'] = data['close'].rolling(window=20).mean()
            
            col1, col2 = st.columns(2)
            
            with col1:
                ma5 = data['MA_5'].iloc[-1] if not pd.isna(data['MA_5'].iloc[-1]) else 0
                st.metric("5일 이동평균", f"{ma5:,.0f}원")
            
            with col2:
                ma20 = data['MA_20'].iloc[-1] if not pd.isna(data['MA_20'].iloc[-1]) else 0
                st.metric("20일 이동평균", f"{ma20:,.0f}원")
                
        else:
            st.error(f"{selected_symbol} 데이터를 찾을 수 없습니다.")
            
    except Exception as e:
        st.error(f"시장 분석 오류: {str(e)}")

@monitor_performance
def show_signal_monitoring_page(db_manager):
    """신호 모니터링 페이지"""
    st.header("🚨 매매 신호 모니터링")
    
    # 시간 범위 선택
    hours = st.selectbox("조회 기간", [1, 6, 12, 24, 48], index=3)
    
    # 신호 조회 (캐시된 데이터 사용)
    signals = get_recent_signals_cached(db_manager, hours=hours)
    
    if not signals.empty:
        # 신호 타입별 필터
        signal_types = signals['signal_type'].unique().tolist()
        selected_types = st.multiselect("신호 타입 필터", signal_types, default=signal_types)
        
        filtered_signals = signals[signals['signal_type'].isin(selected_types)]
        
        if not filtered_signals.empty:
            # 신호 요약
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                buy_signals = len(filtered_signals[filtered_signals['signal_type'] == 'BUY'])
                st.metric("매수 신호", buy_signals, "🟢")
            
            with col2:
                sell_signals = len(filtered_signals[filtered_signals['signal_type'] == 'SELL'])
                st.metric("매도 신호", sell_signals, "🔴")
            
            with col3:
                hold_signals = len(filtered_signals[filtered_signals['signal_type'] == 'HOLD'])
                st.metric("관망 신호", hold_signals, "🟡")
            
            with col4:
                avg_confidence = filtered_signals['confidence'].mean()
                st.metric("평균 신뢰도", f"{avg_confidence:.2f}")
            
            # 신호 테이블
            st.subheader("📋 신호 상세")
            display_columns = ['symbol', 'signal_type', 'confidence', 'signal_date']
            if 'notes' in filtered_signals.columns:
                display_columns.append('notes')
                
            st.dataframe(filtered_signals[display_columns], use_container_width=True)
            
            # 신호 타입별 분포 차트 (성능 최적화)
            if len(filtered_signals) > 1:
                with st.spinner("차트 생성 중..."):
                    signal_counts = filtered_signals['signal_type'].value_counts()
                    fig = px.pie(
                        values=signal_counts.values, 
                        names=signal_counts.index, 
                        title='신호 타입별 분포',
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("필터 조건에 맞는 신호가 없습니다.")
    else:
        st.info(f"최근 {hours}시간 동안 신호가 없습니다.")

@monitor_performance
def show_risk_management_page(db_manager):
    """리스크 관리 페이지"""
    st.header("⚠️ 리스크 관리")
    
    portfolios = get_portfolios_cached(db_manager)
    
    if not portfolios.empty:
        portfolio_names = portfolios['name'].tolist()
        selected_portfolio = st.selectbox("포트폴리오 선택", portfolio_names)
        
        portfolio_info = portfolios[portfolios['name'] == selected_portfolio].iloc[0]
        portfolio_id = portfolio_info['id']
        
        holdings = get_portfolio_holdings_cached(db_manager, portfolio_id)
        
        if not holdings.empty:
            st.write("**포트폴리오 구성:**")
            risk_columns = ['symbol', 'quantity', 'market_value']
            if 'weight' in holdings.columns:
                risk_columns.append('weight')
            st.dataframe(holdings[risk_columns], use_container_width=True)
            
            # 리스크 지표
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
            if 'weight' in holdings.columns:
                max_weight = holdings['weight'].max()
                if max_weight > 50:
                    st.error("🚨 특정 종목 집중도가 매우 높습니다! 분산투자를 강력히 권합니다.")
                elif max_weight > 30:
                    st.warning("⚠️ 특정 종목 집중도가 높습니다. 분산투자를 고려하세요.")
                else:
                    st.success("✅ 포트폴리오가 잘 분산되어 있습니다.")
                    
        else:
            st.info("포트폴리오에 보유 종목이 없습니다.")
    else:
        st.info("포트폴리오가 없습니다.")

@monitor_performance
def show_settings_page(db_manager, market_service):
    """설정 페이지"""
    st.header("⚙️ 시스템 설정")
    
    # 캐시 관리
    st.subheader("🗂️ 캐시 관리")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 전체 캐시 지우기"):
            st.cache_data.clear()
            st.success("✅ 모든 캐시가 삭제되었습니다!")
    
    with col2:
        if st.button("📊 데이터 캐시 새로고침"):
            # 특정 캐시만 지우기
            get_system_status.clear()
            get_portfolios_cached.clear()
            st.success("✅ 데이터 캐시가 새로고침되었습니다!")
    
    with col3:
        cache_info = {
            'system_status': len(st.session_state.get('system_status_cache', {})),
            'portfolios': len(st.session_state.get('portfolios_cache', {})),
        }
        st.write("**캐시 상태:**")
        st.json(cache_info)
    
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
        
        # 빠른 데이터 업데이트 (성능 최적화)
        if st.button("⚡ 빠른 데이터 업데이트 (5개 종목)"):
            with st.spinner("데이터 업데이트 중..."):
                try:
                    symbols = db_manager.get_available_symbols()
                    if symbols:
                        results = market_service.update_latest_data(symbols[:5])  # 처음 5개만
                        success_count = sum(results.values())
                        st.success(f"✅ {success_count}/{len(symbols[:5])}개 종목 업데이트 완료")
                        
                        # 캐시 새로고침
                        get_market_data_cached.clear()
                        get_system_status.clear()
                    else:
                        st.info("업데이트할 종목이 없습니다.")
                except Exception as e:
                    st.error(f"업데이트 실패: {str(e)}")
        
        # 시스템 정보
        st.subheader("🖥️ 시스템 정보")
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write(f"**현재 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**데이터베이스:** data/trading_system.db")
            st.write(f"**페이지 로딩 시간:** {time.time():.3f}초")
        
        with info_col2:
            st.write(f"**Streamlit 버전:** {st.__version__}")
            st.write(f"**캐시 TTL:** 1-5분")
            st.write(f"**자동 새로고침:** {'활성' if st.sidebar.checkbox else '비활성'}")
        
    except Exception as e:
        st.error(f"설정 페이지 오류: {str(e)}")

if __name__ == "__main__":
    main()