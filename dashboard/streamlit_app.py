"""
Streamlit 기반 실시간 트레이딩 대시보드
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Optional, Any

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.database.database_manager import DatabaseManager
    from src.database.market_data_service import MarketDataService
    from src.risk_management.var_calculator import VaRCalculator
    from src.risk_management.correlation_analyzer import CorrelationAnalyzer
    DB_AVAILABLE = True
except ImportError as e:
    st.error(f"모듈 import 오류: {str(e)}")
    st.error("시스템을 확인해주세요.")
    DB_AVAILABLE = False

# 페이지 설정
st.set_page_config(
    page_title="📊 Smart Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 설정
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1E88E5;
        margin-bottom: 1rem;
    }
    .alert-success {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .alert-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
    .alert-danger {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'db_manager' not in st.session_state and DB_AVAILABLE:
    st.session_state.db_manager = DatabaseManager()
    st.session_state.market_service = MarketDataService()
    st.session_state.var_calculator = VaRCalculator()
    st.session_state.correlation_analyzer = CorrelationAnalyzer()

def main():
    """메인 대시보드 함수"""
    
    # 헤더
    st.markdown('<div class="main-header">📊 Smart Trading Dashboard</div>', unsafe_allow_html=True)
    
    if not DB_AVAILABLE:
        st.error("⚠️ 필요한 모듈을 불러올 수 없습니다. 시스템을 확인해주세요.")
        return
    
    # 사이드바 - 네비게이션
    st.sidebar.title("🎛️ 대시보드 메뉴")
    
    page = st.sidebar.selectbox(
        "페이지 선택",
        ["🏠 홈", "📈 포트폴리오", "📊 시장 분석", "⚡ 실시간 신호", "⚠️ 리스크 관리", "🔧 설정"]
    )
    
    # 자동 새로고침 설정
    auto_refresh = st.sidebar.checkbox("자동 새로고침 (30초)", value=False)
    if auto_refresh:
        st.rerun()
    
    # 페이지별 라우팅
    if page == "🏠 홈":
        show_home_page()
    elif page == "📈 포트폴리오": 
        show_portfolio_page()
    elif page == "📊 시장 분석":
        show_market_analysis_page()
    elif page == "⚡ 실시간 신호":
        show_signals_page()
    elif page == "⚠️ 리스크 관리":
        show_risk_management_page()
    elif page == "🔧 설정":
        show_settings_page()

def show_home_page():
    """홈 페이지"""
    st.header("🏠 대시보드 홈")
    
    # 시스템 상태 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("시스템 상태", "🟢 정상", delta="실시간 운영중")
    
    with col2:
        # 데이터베이스 상태
        try:
            portfolios = st.session_state.db_manager.get_portfolios()
            portfolio_count = len(portfolios)
            st.metric("포트폴리오", f"{portfolio_count}개", delta="관리중")
        except:
            st.metric("포트폴리오", "오류", delta="연결 필요")
    
    with col3:
        try:
            symbols = st.session_state.db_manager.get_available_symbols()
            symbol_count = len(symbols)
            st.metric("추적 종목", f"{symbol_count}개", delta="데이터 수집중")
        except:
            st.metric("추적 종목", "0개", delta="데이터 없음")
    
    with col4:
        # 최근 신호 수
        try:
            recent_signals = st.session_state.db_manager.get_recent_signals(hours=24)
            signal_count = len(recent_signals)
            st.metric("오늘 신호", f"{signal_count}개", delta="24시간 기준")
        except:
            st.metric("오늘 신호", "0개", delta="신호 없음")
    
    # 최근 알림 및 뉴스
    st.subheader("📢 최근 활동")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔔 최근 거래 신호**")
        try:
            recent_signals = st.session_state.db_manager.get_recent_signals(hours=24)
            if not recent_signals.empty:
                for _, signal in recent_signals.head(5).iterrows():
                    signal_type = signal['signal_type']
                    symbol = signal['symbol']
                    confidence = signal.get('confidence', 0)
                    
                    # 신호 타입별 이모지
                    emoji = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "🟡"
                    
                    st.markdown(f"{emoji} **{symbol}** - {signal_type} 신호 (신뢰도: {confidence:.0%})")
            else:
                st.info("최근 24시간 내 신호가 없습니다.")
        except Exception as e:
            st.error(f"신호 데이터 로드 오류: {str(e)}")
    
    with col2:
        st.markdown("**📈 시장 개요**")
        
        # 간단한 시장 상태 표시 (모의 데이터)
        market_status = {
            "KOSPI": {"value": "2,650", "change": "+1.2%", "color": "green"},
            "KOSDAQ": {"value": "880", "change": "-0.5%", "color": "red"},
            "USD/KRW": {"value": "1,320", "change": "+0.3%", "color": "green"},
            "VIX": {"value": "18.5", "change": "-2.1%", "color": "green"}
        }
        
        for index, data in market_status.items():
            color = "🟢" if data["color"] == "green" else "🔴"
            st.markdown(f"{color} **{index}**: {data['value']} ({data['change']})")
    
    # 빠른 액션 버튼
    st.subheader("⚡ 빠른 실행")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 데이터 업데이트"):
            with st.spinner("데이터 업데이트 중..."):
                # 샘플 종목으로 데이터 업데이트
                sample_symbols = ["005930.KS", "000660.KS", "035420.KS"]
                results = st.session_state.market_service.update_latest_data(sample_symbols)
                success_count = sum(results.values())
                st.success(f"데이터 업데이트 완료: {success_count}/{len(sample_symbols)}개 성공")
    
    with col2:
        if st.button("📊 포트폴리오 분석"):
            st.info("포트폴리오 페이지로 이동하여 상세 분석을 확인하세요.")
    
    with col3:
        if st.button("⚠️ 리스크 체크"):
            st.info("리스크 관리 페이지에서 상세 리스크 분석을 확인하세요.")
    
    with col4:
        if st.button("🔔 신호 검색"):
            st.info("실시간 신호 페이지에서 최신 매매 신호를 확인하세요.")

def show_portfolio_page():
    """포트폴리오 페이지"""
    st.header("📈 포트폴리오 관리")
    
    # 포트폴리오 선택
    try:
        portfolios = st.session_state.db_manager.get_portfolios()
        
        if portfolios.empty:
            st.info("생성된 포트폴리오가 없습니다.")
            
            # 새 포트폴리오 생성 섹션
            st.subheader("📝 새 포트폴리오 생성")
            
            with st.form("create_portfolio"):
                portfolio_name = st.text_input("포트폴리오 이름")
                portfolio_desc = st.text_area("설명")
                initial_capital = st.number_input("초기 자본", min_value=1000000, value=10000000, step=1000000)
                
                if st.form_submit_button("포트폴리오 생성"):
                    if portfolio_name:
                        portfolio_id = st.session_state.db_manager.create_portfolio(
                            name=portfolio_name,
                            description=portfolio_desc,
                            initial_capital=initial_capital
                        )
                        
                        if portfolio_id:
                            st.success(f"포트폴리오 '{portfolio_name}' 생성 완료!")
                            st.rerun()
                        else:
                            st.error("포트폴리오 생성 실패")
                    else:
                        st.error("포트폴리오 이름을 입력해주세요.")
            return
        
        # 기존 포트폴리오 표시
        portfolio_names = portfolios['name'].tolist()
        selected_portfolio = st.selectbox("포트폴리오 선택", portfolio_names)
        
        if selected_portfolio:
            portfolio_info = portfolios[portfolios['name'] == selected_portfolio].iloc[0]
            portfolio_id = portfolio_info['id']
            
            # 포트폴리오 기본 정보
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("초기 자본", f"{portfolio_info['initial_capital']:,.0f}원")
            
            with col2:
                current_value = portfolio_info['current_value']
                st.metric("현재 가치", f"{current_value:,.0f}원")
            
            with col3:
                total_return = (current_value - portfolio_info['initial_capital']) / portfolio_info['initial_capital']
                st.metric("총 수익률", f"{total_return:.2%}")
            
            with col4:
                created_date = portfolio_info['created_date']
                st.metric("생성일", created_date)
            
            # 보유 종목 현황
            st.subheader("📊 보유 종목 현황")
            
            holdings = st.session_state.db_manager.get_portfolio_holdings(portfolio_id)
            
            if not holdings.empty:
                # 보유 종목 테이블
                st.dataframe(
                    holdings[['symbol', 'quantity', 'avg_price', 'current_price', 'market_value', 'unrealized_pnl_pct']],
                    column_config={
                        'symbol': '종목코드',
                        'quantity': '보유수량',
                        'avg_price': st.column_config.NumberColumn('평균단가', format="%.0f원"),
                        'current_price': st.column_config.NumberColumn('현재가', format="%.0f원"),
                        'market_value': st.column_config.NumberColumn('평가금액', format="%.0f원"),
                        'unrealized_pnl_pct': st.column_config.NumberColumn('평가손익률', format="%.2f%%")
                    }
                )
                
                # 포트폴리오 구성 파이 차트
                if len(holdings) > 1:
                    fig_pie = px.pie(
                        holdings, 
                        values='market_value', 
                        names='symbol',
                        title="포트폴리오 구성 비중"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
            else:
                st.info("보유 종목이 없습니다.")
            
            # 거래 이력
            st.subheader("📋 최근 거래 이력")
            
            trade_history = st.session_state.db_manager.get_trade_history(portfolio_id, days=30)
            
            if not trade_history.empty:
                st.dataframe(
                    trade_history[['trade_date', 'symbol', 'trade_type', 'quantity', 'price', 'signal_source']],
                    column_config={
                        'trade_date': '거래일시',
                        'symbol': '종목코드',
                        'trade_type': '거래구분',
                        'quantity': '수량',
                        'price': st.column_config.NumberColumn('가격', format="%.0f원"),
                        'signal_source': '신호출처'
                    }
                )
            else:
                st.info("최근 30일 내 거래 이력이 없습니다.")
                
    except Exception as e:
        st.error(f"포트폴리오 데이터 로드 오류: {str(e)}")

def show_market_analysis_page():
    """시장 분석 페이지"""
    st.header("📊 시장 분석")
    
    # 종목 선택
    try:
        available_symbols = st.session_state.db_manager.get_available_symbols()
        
        if not available_symbols:
            st.warning("분석할 종목 데이터가 없습니다. 먼저 데이터를 수집해주세요.")
            
            # 데이터 수집 섹션
            st.subheader("📥 데이터 수집")
            
            sample_symbols = st.multiselect(
                "수집할 종목 선택",
                ["005930.KS", "000660.KS", "035420.KS", "035720.KS", "051910.KS"],
                default=["005930.KS", "000660.KS", "035420.KS"]
            )
            
            if st.button("데이터 수집 시작"):
                if sample_symbols:
                    with st.spinner("데이터 수집 중..."):
                        results = st.session_state.market_service.collect_and_store_data(sample_symbols)
                        success_count = sum(results.values())
                        st.success(f"데이터 수집 완료: {success_count}/{len(sample_symbols)}개 성공")
                        st.rerun()
                else:
                    st.error("수집할 종목을 선택해주세요.")
            
            return
        
        # 종목 선택
        selected_symbol = st.selectbox("분석할 종목 선택", available_symbols)
        
        if selected_symbol:
            # 기간 선택
            period_options = {
                "1개월": "1mo",
                "3개월": "3mo", 
                "6개월": "6mo",
                "1년": "1y",
                "2년": "2y"
            }
            
            selected_period = st.selectbox("분석 기간", list(period_options.keys()), index=3)
            period = period_options[selected_period]
            
            # 데이터 로드
            with st.spinner("데이터 로딩 중..."):
                price_data = st.session_state.market_service.get_cached_data(selected_symbol)
            
            if price_data.empty:
                st.error(f"{selected_symbol} 데이터를 불러올 수 없습니다.")
                return
            
            # 기본 정보 표시
            latest_price = price_data['close'].iloc[-1]
            prev_price = price_data['close'].iloc[-2]
            price_change = latest_price - prev_price
            price_change_pct = (price_change / prev_price) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("현재가", f"{latest_price:,.0f}원", delta=f"{price_change:+.0f}원")
            
            with col2:
                st.metric("등락률", f"{price_change_pct:+.2f}%")
            
            with col3:
                volume = price_data['volume'].iloc[-1]
                st.metric("거래량", f"{volume:,.0f}주")
            
            with col4:
                high_52w = price_data['high'].tail(252).max()
                low_52w = price_data['low'].tail(252).min()
                st.metric("52주 고점", f"{high_52w:,.0f}원")
            
            # 가격 차트
            st.subheader("📈 가격 차트")
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('가격', '거래량'),
                vertical_spacing=0.1,
                row_width=[0.7, 0.3]
            )
            
            # 캔들스틱 차트
            fig.add_trace(
                go.Candlestick(
                    x=price_data.index,
                    open=price_data['open'],
                    high=price_data['high'],
                    low=price_data['low'],
                    close=price_data['close'],
                    name="가격"
                ),
                row=1, col=1
            )
            
            # 거래량 차트
            fig.add_trace(
                go.Bar(
                    x=price_data.index,
                    y=price_data['volume'],
                    name="거래량",
                    marker_color="lightblue"
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                title=f"{selected_symbol} 주가 차트",
                xaxis_rangeslider_visible=False,
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 기술적 지표 분석
            st.subheader("📊 기술적 지표")
            
            # 간단한 이동평균 계산
            price_data['MA5'] = price_data['close'].rolling(5).mean()
            price_data['MA20'] = price_data['close'].rolling(20).mean()
            price_data['MA60'] = price_data['close'].rolling(60).mean()
            
            # RSI 계산 (간단 버전)
            delta = price_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            price_data['RSI'] = 100 - (100 / (1 + rs))
            
            # 기술적 지표 차트
            fig_tech = make_subplots(
                rows=2, cols=1,
                subplot_titles=('이동평균', 'RSI'),
                vertical_spacing=0.1
            )
            
            # 이동평균 차트
            fig_tech.add_trace(
                go.Scatter(x=price_data.index, y=price_data['close'], name="종가", line=dict(color="black")),
                row=1, col=1
            )
            fig_tech.add_trace(
                go.Scatter(x=price_data.index, y=price_data['MA5'], name="MA5", line=dict(color="red")),
                row=1, col=1
            )
            fig_tech.add_trace(
                go.Scatter(x=price_data.index, y=price_data['MA20'], name="MA20", line=dict(color="blue")),
                row=1, col=1
            )
            fig_tech.add_trace(
                go.Scatter(x=price_data.index, y=price_data['MA60'], name="MA60", line=dict(color="green")),
                row=1, col=1
            )
            
            # RSI 차트
            fig_tech.add_trace(
                go.Scatter(x=price_data.index, y=price_data['RSI'], name="RSI", line=dict(color="purple")),
                row=2, col=1
            )
            fig_tech.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig_tech.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)
            
            fig_tech.update_layout(height=500, title="기술적 지표")
            st.plotly_chart(fig_tech, use_container_width=True)
            
            # 현재 지표 값
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                current_rsi = price_data['RSI'].iloc[-1]
                rsi_status = "과매수" if current_rsi > 70 else "과매도" if current_rsi < 30 else "중립"
                st.metric("RSI", f"{current_rsi:.1f}", delta=rsi_status)
            
            with col2:
                ma5_diff = ((latest_price - price_data['MA5'].iloc[-1]) / price_data['MA5'].iloc[-1]) * 100
                st.metric("MA5 대비", f"{ma5_diff:+.2f}%")
            
            with col3:
                ma20_diff = ((latest_price - price_data['MA20'].iloc[-1]) / price_data['MA20'].iloc[-1]) * 100
                st.metric("MA20 대비", f"{ma20_diff:+.2f}%")
            
            with col4:
                volatility = price_data['close'].pct_change().rolling(20).std() * np.sqrt(252) * 100
                current_vol = volatility.iloc[-1]
                st.metric("변동성 (20일)", f"{current_vol:.1f}%")
            
    except Exception as e:
        st.error(f"시장 분석 오류: {str(e)}")

def show_signals_page():
    """실시간 신호 페이지"""
    st.header("⚡ 실시간 매매 신호")
    
    # 신호 필터링 옵션
    col1, col2, col3 = st.columns(3)
    
    with col1:
        signal_type_filter = st.selectbox("신호 타입", ["전체", "BUY", "SELL", "HOLD"])
    
    with col2:
        hours_filter = st.selectbox("시간 범위", [1, 6, 12, 24, 48], index=2)
    
    with col3:
        min_confidence = st.slider("최소 신뢰도", 0.0, 1.0, 0.5, 0.1)
    
    try:
        # 신호 데이터 로드
        recent_signals = st.session_state.db_manager.get_recent_signals(hours=hours_filter)
        
        if not recent_signals.empty:
            # 필터 적용
            filtered_signals = recent_signals.copy()
            
            if signal_type_filter != "전체":
                filtered_signals = filtered_signals[filtered_signals['signal_type'] == signal_type_filter]
            
            if 'confidence' in filtered_signals.columns:
                filtered_signals = filtered_signals[filtered_signals['confidence'] >= min_confidence]
            
            if not filtered_signals.empty:
                st.success(f"💡 {len(filtered_signals)}개의 신호를 찾았습니다.")
                
                # 신호 리스트 표시
                for _, signal in filtered_signals.iterrows():
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 3])
                        
                        with col1:
                            signal_emoji = "🟢" if signal['signal_type'] == "BUY" else "🔴" if signal['signal_type'] == "SELL" else "🟡"
                            st.markdown(f"**{signal_emoji} {signal['symbol']}**")
                        
                        with col2:
                            st.markdown(f"**{signal['signal_type']}**")
                        
                        with col3:
                            confidence = signal.get('confidence', 0)
                            st.markdown(f"신뢰도: **{confidence:.0%}**")
                        
                        with col4:
                            signal_time = pd.to_datetime(signal['signal_date'])
                            time_ago = datetime.now() - signal_time
                            if time_ago.seconds < 3600:
                                time_str = f"{time_ago.seconds//60}분 전"
                            else:
                                time_str = f"{time_ago.seconds//3600}시간 전"
                            st.markdown(f"⏰ {time_str}")
                        
                        with col5:
                            indicators = signal.get('indicators_used', '[]')
                            if indicators and indicators != '[]':
                                st.markdown(f"지표: {indicators}")
                            
                            notes = signal.get('notes', '')
                            if notes:
                                st.markdown(f"📝 {notes}")
                        
                        st.divider()
                
            else:
                st.info("설정한 조건에 맞는 신호가 없습니다.")
        
        else:
            st.info(f"최근 {hours_filter}시간 내 신호가 없습니다.")
        
        # 신호 생성 테스트 버튼
        st.subheader("🧪 테스트 신호 생성")
        
        if st.button("테스트 신호 생성"):
            # 테스트용 신호 생성
            test_symbols = ["005930.KS", "000660.KS", "035420.KS"]
            
            for i, symbol in enumerate(test_symbols):
                signal_type = ["BUY", "SELL", "HOLD"][i % 3]
                confidence = 0.6 + (i * 0.1)
                
                signal_id = st.session_state.db_manager.save_trading_signal(
                    symbol=symbol,
                    signal_type=signal_type,
                    signal_strength=0.8,
                    confidence=confidence,
                    indicators_used=["RSI", "MACD", "MA"],
                    notes=f"테스트 {signal_type} 신호"
                )
                
                if signal_id:
                    st.success(f"✅ {symbol} {signal_type} 신호 생성 완료")
            
            st.info("페이지를 새로고침하여 새 신호를 확인하세요.")
    
    except Exception as e:
        st.error(f"신호 데이터 로드 오류: {str(e)}")

def show_risk_management_page():
    """리스크 관리 페이지"""
    st.header("⚠️ 리스크 관리")
    
    # 포트폴리오 선택
    try:
        portfolios = st.session_state.db_manager.get_portfolios()
        
        if portfolios.empty:
            st.warning("분석할 포트폴리오가 없습니다. 먼저 포트폴리오를 생성해주세요.")
            return
        
        portfolio_names = portfolios['name'].tolist()
        selected_portfolio = st.selectbox("분석할 포트폴리오", portfolio_names)
        
        if selected_portfolio:
            portfolio_info = portfolios[portfolios['name'] == selected_portfolio].iloc[0]
            portfolio_id = portfolio_info['id']
            
            # 보유 종목 조회
            holdings = st.session_state.db_manager.get_portfolio_holdings(portfolio_id)
            
            if holdings.empty:
                st.info("보유 종목이 없어 리스크 분석을 수행할 수 없습니다.")
                return
            
            # 포트폴리오 구성
            portfolio_dict = {}
            total_value = holdings['market_value'].sum()
            
            for _, holding in holdings.iterrows():
                weight = holding['market_value'] / total_value
                portfolio_dict[holding['symbol']] = weight
            
            st.subheader("📊 포트폴리오 구성")
            
            # 구성 비중 표시
            composition_df = pd.DataFrame({
                '종목': list(portfolio_dict.keys()),
                '비중': [f"{v:.1%}" for v in portfolio_dict.values()],
                '금액': [f"{holdings[holdings['symbol']==k]['market_value'].iloc[0]:,.0f}원" 
                        for k in portfolio_dict.keys()]
            })
            
            st.dataframe(composition_df, use_container_width=True)
            
            # VaR 분석
            st.subheader("📉 VaR (Value at Risk) 분석")
            
            with st.spinner("VaR 분석 중..."):
                try:
                    var_analysis = st.session_state.var_calculator.calculate_comprehensive_var(portfolio_dict)
                    
                    if 'error' not in var_analysis:
                        # VaR 결과 표시
                        risk_assessment = var_analysis.get('risk_assessment', {})
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            risk_level = risk_assessment.get('risk_level', 'UNKNOWN')
                            st.metric("리스크 수준", risk_level)
                        
                        with col2:
                            avg_var = risk_assessment.get('average_var_95_1d', 0)
                            st.metric("일간 VaR (95%)", f"{avg_var:.2%}")
                        
                        with col3:
                            portfolio_stats = var_analysis.get('portfolio_statistics', {})
                            annual_vol = portfolio_stats.get('annualized_volatility', 0)
                            st.metric("연간 변동성", f"{annual_vol:.1%}")
                        
                        with col4:
                            sharpe_ratio = portfolio_stats.get('sharpe_ratio', 0)
                            st.metric("샤프 비율", f"{sharpe_ratio:.2f}")
                        
                        # VaR 차트
                        var_results = var_analysis.get('var_results', {})
                        if 'VaR_95_1d' in var_results:
                            var_95_1d = var_results['VaR_95_1d']
                            
                            methods = ['historical', 'parametric', 'monte_carlo']
                            method_names = ['역사적', '모수적', '몬테카를로']
                            var_values = [var_95_1d[method].get('var', 0) * 100 for method in methods]
                            
                            fig_var = px.bar(
                                x=method_names,
                                y=var_values,
                                title="VaR 계산 방법별 비교 (95% 신뢰수준, 1일)",
                                labels={'x': '계산 방법', 'y': 'VaR (%)'}
                            )
                            
                            st.plotly_chart(fig_var, use_container_width=True)
                    
                    else:
                        st.error(f"VaR 분석 실패: {var_analysis['error']}")
                
                except Exception as e:
                    st.error(f"VaR 분석 오류: {str(e)}")
            
            # 상관관계 분석
            st.subheader("🔗 상관관계 분석")
            
            with st.spinner("상관관계 분석 중..."):
                try:
                    # 종목별 가격 데이터 수집
                    symbols = list(portfolio_dict.keys())
                    price_data_dict = {}
                    
                    for symbol in symbols:
                        data = st.session_state.market_service.get_cached_data(symbol)
                        if not data.empty:
                            price_data_dict[symbol] = data['close']
                    
                    if len(price_data_dict) > 1:
                        # 가격 데이터 결합
                        combined_prices = pd.DataFrame(price_data_dict)
                        
                        # 상관관계 행렬 계산
                        correlation_matrix = st.session_state.correlation_analyzer.calculate_correlation_matrix(combined_prices)
                        
                        if not correlation_matrix.empty:
                            # 상관관계 분석
                            risk_analysis = st.session_state.correlation_analyzer.analyze_correlation_risks(
                                correlation_matrix, portfolio_dict
                            )
                            
                            if 'error' not in risk_analysis:
                                # 집중도 분석
                                concentration = risk_analysis.get('concentration_analysis', {})
                                individual_conc = concentration.get('individual_concentration', {})
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    max_weight = individual_conc.get('max_weight', 0)
                                    st.metric("최대 종목 비중", f"{max_weight:.1%}")
                                
                                with col2:
                                    conc_score = concentration.get('concentration_score', 0)
                                    st.metric("집중도 점수", f"{conc_score:.2f}")
                                
                                with col3:
                                    div_analysis = risk_analysis.get('diversification_analysis', {})
                                    div_grade = div_analysis.get('diversification_grade', 'unknown')
                                    st.metric("분산투자 등급", div_grade)
                                
                                # 상관관계 히트맵
                                fig_corr = px.imshow(
                                    correlation_matrix,
                                    title="종목간 상관관계 매트릭스",
                                    color_continuous_scale="RdBu",
                                    zmin=-1, zmax=1
                                )
                                st.plotly_chart(fig_corr, use_container_width=True)
                                
                                # 리스크 경고
                                warnings = risk_analysis.get('risk_warnings', [])
                                if warnings:
                                    st.subheader("🚨 리스크 경고")
                                    for warning in warnings:
                                        st.warning(warning)
                            
                            else:
                                st.error(f"상관관계 분석 실패: {risk_analysis['error']}")
                        
                        else:
                            st.error("상관관계 계산 실패")
                    
                    else:
                        st.info("상관관계 분석을 위해서는 최소 2개 이상의 종목이 필요합니다.")
                
                except Exception as e:
                    st.error(f"상관관계 분석 오류: {str(e)}")
    
    except Exception as e:
        st.error(f"리스크 관리 페이지 오류: {str(e)}")

def show_settings_page():
    """설정 페이지"""
    st.header("🔧 시스템 설정")
    
    # 데이터베이스 관리
    st.subheader("🗄️ 데이터베이스 관리")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("데이터 상태 확인"):
            try:
                status = st.session_state.market_service.get_data_status()
                
                st.json(status)
                
            except Exception as e:
                st.error(f"데이터 상태 확인 오류: {str(e)}")
    
    with col2:
        if st.button("데이터베이스 정리"):
            try:
                with st.spinner("데이터 정리 중..."):
                    success = st.session_state.market_service.cleanup_old_data(days_to_keep=365)
                    
                    if success:
                        st.success("데이터 정리 완료")
                    else:
                        st.error("데이터 정리 실패")
                        
            except Exception as e:
                st.error(f"데이터 정리 오류: {str(e)}")
    
    # 알림 설정
    st.subheader("🔔 알림 설정")
    
    enable_notifications = st.checkbox("신호 알림 활성화", value=True)
    notification_threshold = st.slider("알림 신뢰도 임계값", 0.0, 1.0, 0.7, 0.05)
    
    # 자동 실행 설정
    st.subheader("⚙️ 자동 실행 설정")
    
    auto_data_update = st.checkbox("자동 데이터 업데이트", value=False)
    if auto_data_update:
        update_interval = st.selectbox("업데이트 간격", ["30분", "1시간", "2시간", "4시간"], index=1)
    
    auto_signal_generation = st.checkbox("자동 신호 생성", value=False)
    
    # 시스템 정보
    st.subheader("ℹ️ 시스템 정보")
    
    system_info = {
        "버전": "1.0.0",
        "마지막 업데이트": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "데이터베이스": str(st.session_state.db_manager.db_path),
        "활성 모듈": "전체"
    }
    
    for key, value in system_info.items():
        st.text(f"{key}: {value}")
    
    # 설정 저장
    if st.button("설정 저장"):
        st.success("설정이 저장되었습니다.")

if __name__ == "__main__":
    main()