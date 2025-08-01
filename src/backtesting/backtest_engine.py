"""
백테스팅 엔진 (Backtesting Engine)
통합 매매 신호의 과거 성과를 검증하는 시스템
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.trading_signals.signal_integrator import SignalIntegrator
from src.risk_management.risk_manager import RiskManager

class BacktestEngine:
    """백테스팅 엔진 - 매매 신호 성과 검증"""
    
    def __init__(self, 
                 initial_capital: float = 10000000,  # 초기 자본 1천만원
                 commission_rate: float = 0.003,     # 수수료 0.3%
                 slippage_rate: float = 0.001,       # 슬리피지 0.1%
                 max_position_size: float = 1.0,     # 최대 포지션 크기
                 use_risk_management: bool = True):   # 리스크 관리 사용 여부
        """
        Args:
            initial_capital: 초기 자본금
            commission_rate: 거래 수수료율
            slippage_rate: 슬리피지율
            max_position_size: 최대 포지션 크기 (1.0 = 100%)
            use_risk_management: 리스크 관리 사용 여부
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.max_position_size = max_position_size
        self.use_risk_management = use_risk_management
        self.logger = self._setup_logger()
        
        # 리스크 관리자 초기화
        if self.use_risk_management:
            self.risk_manager = RiskManager(
                stop_loss_pct=0.12,      # 12% 손절매
                take_profit_pct=0.25,    # 25% 익절매
                trailing_stop_pct=0.06   # 6% 추적손절매
            )
        else:
            self.risk_manager = None
        
        # 백테스트 결과 저장
        self.trades = []
        self.portfolio_history = []
        self.performance_metrics = {}
        
    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def run_backtest(self, data: pd.DataFrame, 
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        백테스트 실행
        
        Args:
            data: 통합 신호가 포함된 주가 데이터
            start_date: 백테스트 시작일 (YYYY-MM-DD)
            end_date: 백테스트 종료일 (YYYY-MM-DD)
            
        Returns:
            백테스트 결과 딕셔너리
        """
        try:
            self.logger.info("Starting backtest...")
            
            # 날짜 범위 필터링
            backtest_data = self._filter_date_range(data, start_date, end_date)
            
            if backtest_data.empty:
                self.logger.error("No data available for backtest period")
                return {}
            
            # 백테스트 초기화
            self._initialize_backtest(backtest_data)
            
            # 매일 포트폴리오 업데이트
            for idx, row in backtest_data.iterrows():
                self._process_day(row, idx)
            
            # 성과 지표 계산
            self.performance_metrics = self._calculate_performance_metrics()
            
            self.logger.info("Backtest completed successfully")
            
            return {
                'trades': self.trades,
                'portfolio_history': self.portfolio_history,
                'performance_metrics': self.performance_metrics,
                'backtest_period': {
                    'start_date': backtest_data.iloc[0]['date'].strftime('%Y-%m-%d'),
                    'end_date': backtest_data.iloc[-1]['date'].strftime('%Y-%m-%d'),
                    'total_days': len(backtest_data)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in backtest: {str(e)}")
            return {}
    
    def _filter_date_range(self, data: pd.DataFrame,
                          start_date: Optional[str],
                          end_date: Optional[str]) -> pd.DataFrame:
        """날짜 범위 필터링"""
        try:
            result = data.copy()
            
            if 'date' not in result.columns:
                # 인덱스가 날짜인 경우
                result = result.reset_index()
                if result.columns[0] not in ['date', 'Date']:
                    result = result.rename(columns={result.columns[0]: 'date'})
            
            # 날짜 컬럼을 datetime으로 변환
            result['date'] = pd.to_datetime(result['date'])
            
            # 날짜 범위 적용
            if start_date:
                start_dt = pd.to_datetime(start_date)
                result = result[result['date'] >= start_dt]
            
            if end_date:
                end_dt = pd.to_datetime(end_date)
                result = result[result['date'] <= end_dt]
            
            return result.sort_values('date').reset_index(drop=True)
            
        except Exception as e:
            self.logger.error(f"Error filtering date range: {str(e)}")
            return data
    
    def _initialize_backtest(self, data: pd.DataFrame):
        """백테스트 초기화"""
        self.trades = []
        self.portfolio_history = []
        
        # 초기 포트폴리오 상태
        initial_portfolio = {
            'date': data.iloc[0]['date'],
            'cash': self.initial_capital,
            'stock_value': 0.0,
            'total_value': self.initial_capital,
            'position': 0,  # 0: 현금, 1: 매수, -1: 매도(공매도 없음)
            'shares': 0,
            'returns': 0.0,
            'cumulative_returns': 0.0
        }
        
        self.portfolio_history.append(initial_portfolio)
        self.logger.info(f"Backtest initialized with capital: {self.initial_capital:,.0f}")
    
    def _process_day(self, row: pd.Series, idx: int):
        """일일 포트폴리오 처리"""
        try:
            current_price = row['close']
            current_date = row['date']
            
            # 이전 포트폴리오 상태
            prev_portfolio = self.portfolio_history[-1].copy()
            
            # 현재 포트폴리오 상태 계산
            current_portfolio = {
                'date': current_date,
                'cash': prev_portfolio['cash'],
                'shares': prev_portfolio['shares'],
                'position': prev_portfolio['position']
            }
            
            # 주식 가치 업데이트
            current_portfolio['stock_value'] = current_portfolio['shares'] * current_price
            current_portfolio['total_value'] = current_portfolio['cash'] + current_portfolio['stock_value']
            
            # 리스크 관리 확인 (포지션이 있는 경우)
            risk_exit = False
            risk_reason = ""
            
            if self.use_risk_management and current_portfolio['position'] == 1:
                should_exit, reason, exit_info = self.risk_manager.check_exit_conditions(
                    symbol='BACKTEST', 
                    current_price=current_price,
                    current_date=current_date
                )
                
                if should_exit:
                    self._execute_sell(current_portfolio, current_price, 0.5, current_date, reason)
                    self.risk_manager.close_position('BACKTEST')
                    risk_exit = True
                    risk_reason = reason
            
            # 매매 신호 처리 (리스크 관리로 매도하지 않은 경우에만)
            if not risk_exit:
                buy_signal = row.get('integrated_buy_signal', 0) == 1
                sell_signal = row.get('integrated_sell_signal', 0) == 1
                signal_confidence = row.get('integrated_confidence', 0)
                
                # 매수 신호 처리
                if buy_signal and current_portfolio['position'] == 0:
                    self._execute_buy(current_portfolio, current_price, signal_confidence, current_date)
                
                # 매도 신호 처리
                elif sell_signal and current_portfolio['position'] == 1:
                    self._execute_sell(current_portfolio, current_price, signal_confidence, current_date, 'SIGNAL')
                    if self.use_risk_management:
                        self.risk_manager.close_position('BACKTEST')
            
            # 수익률 계산
            prev_total = self.portfolio_history[-1]['total_value']
            current_portfolio['returns'] = (current_portfolio['total_value'] - prev_total) / prev_total
            
            if len(self.portfolio_history) == 1:  # 첫날
                current_portfolio['cumulative_returns'] = current_portfolio['returns']
            else:
                prev_cum_returns = self.portfolio_history[-1]['cumulative_returns']
                current_portfolio['cumulative_returns'] = (1 + prev_cum_returns) * (1 + current_portfolio['returns']) - 1
            
            self.portfolio_history.append(current_portfolio)
            
        except Exception as e:
            self.logger.error(f"Error processing day {idx}: {str(e)}")
    
    def _execute_buy(self, portfolio: Dict, price: float, confidence: float, date):
        """매수 실행"""
        try:
            # 사용 가능한 현금으로 매수
            available_cash = portfolio['cash']
            
            # 슬리피지 적용 (매수시 불리하게)
            actual_price = price * (1 + self.slippage_rate)
            
            # 리스크 관리자를 통한 포지션 사이징
            if self.use_risk_management:
                investment_amount, shares = self.risk_manager.calculate_position_size(
                    available_cash / (1 + self.commission_rate),  # 수수료 고려
                    actual_price,
                    confidence,
                    volatility=0.2  # 기본 변동성 20%
                )
            else:
                # 기본 포지션 사이징
                max_investment = available_cash / (1 + self.commission_rate)
                position_size = min(self.max_position_size, confidence * 1.2)
                investment_amount = max_investment * position_size
                shares = int(investment_amount / actual_price)
            
            if shares == 0 or investment_amount < actual_price:
                return
            
            actual_investment = shares * actual_price
            commission = actual_investment * self.commission_rate
            total_cost = actual_investment + commission
            
            if total_cost <= available_cash:
                # 매수 실행
                portfolio['shares'] += shares
                portfolio['cash'] -= total_cost
                portfolio['position'] = 1
                
                # 리스크 관리 설정
                if self.use_risk_management:
                    self.risk_manager.set_position_stops(
                        symbol='BACKTEST',
                        entry_price=actual_price,
                        entry_date=date,
                        shares=shares,
                        signal_confidence=confidence,
                        volatility=0.2
                    )
                
                # 거래 기록
                trade = {
                    'date': date,
                    'type': 'BUY',
                    'shares': shares,
                    'price': actual_price,
                    'amount': actual_investment,
                    'commission': commission,
                    'total_cost': total_cost,
                    'confidence': confidence,
                    'cash_after': portfolio['cash']
                }
                
                self.trades.append(trade)
                self.logger.debug(f"BUY executed: {shares} shares at {actual_price:.0f} (confidence: {confidence:.2f})")
            
        except Exception as e:
            self.logger.error(f"Error executing buy: {str(e)}")
    
    def _execute_sell(self, portfolio: Dict, price: float, confidence: float, date, reason: str = 'SIGNAL'):
        """매도 실행"""
        try:
            if portfolio['shares'] <= 0:
                return
            
            # 슬리피지 적용 (매도시 불리하게)
            actual_price = price * (1 - self.slippage_rate)
            
            # 전량 매도
            shares = portfolio['shares']
            sale_amount = shares * actual_price
            commission = sale_amount * self.commission_rate
            net_proceeds = sale_amount - commission
            
            # 매도 실행
            portfolio['cash'] += net_proceeds
            portfolio['shares'] = 0
            portfolio['position'] = 0
            
            # 거래 기록
            trade = {
                'date': date,
                'type': 'SELL',
                'shares': shares,
                'price': actual_price,
                'amount': sale_amount,
                'commission': commission,
                'net_proceeds': net_proceeds,
                'confidence': confidence,
                'cash_after': portfolio['cash'],
                'reason': reason  # 매도 이유 추가
            }
            
            self.trades.append(trade)
            self.logger.debug(f"SELL executed: {shares} shares at {actual_price:.0f} (reason: {reason}, confidence: {confidence:.2f})")
            
        except Exception as e:
            self.logger.error(f"Error executing sell: {str(e)}")
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """성과 지표 계산"""
        try:
            if not self.portfolio_history:
                return {}
            
            df = pd.DataFrame(self.portfolio_history)
            
            # 기본 수익률 지표
            total_return = df['cumulative_returns'].iloc[-1]
            final_value = df['total_value'].iloc[-1]
            
            # 연간 수익률
            days = len(df)
            years = days / 365.25
            annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
            
            # 변동성 (일간 수익률의 연간 표준편차)
            daily_returns = df['returns'].dropna()
            volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
            
            # 샤프 비율 (무위험 수익률 3% 가정)
            risk_free_rate = 0.03
            sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # 최대 낙폭 (MDD) 계산
            df['peak'] = df['total_value'].expanding().max()
            df['drawdown'] = (df['total_value'] - df['peak']) / df['peak']
            max_drawdown = df['drawdown'].min()
            
            # 거래 분석
            trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
            
            total_trades = len(trades_df)
            buy_trades = len(trades_df[trades_df['type'] == 'BUY']) if not trades_df.empty else 0
            sell_trades = len(trades_df[trades_df['type'] == 'SELL']) if not trades_df.empty else 0
            
            # 승률 계산
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            
            if sell_trades > 0 and buy_trades > 0:
                # 매수-매도 쌍 분석
                buy_sells = []
                buy_idx = 0
                for _, trade in trades_df.iterrows():
                    if trade['type'] == 'BUY':
                        buy_price = trade['price']
                        buy_date = trade['date']
                    elif trade['type'] == 'SELL' and buy_idx < buy_trades:
                        sell_price = trade['price']
                        profit_pct = (sell_price - buy_price) / buy_price
                        buy_sells.append(profit_pct)
                        buy_idx += 1
                
                if buy_sells:
                    wins = [p for p in buy_sells if p > 0]
                    losses = [p for p in buy_sells if p < 0]
                    
                    win_rate = len(wins) / len(buy_sells)
                    avg_win = np.mean(wins) if wins else 0
                    avg_loss = abs(np.mean(losses)) if losses else 0
                    
                    total_profit = sum(wins)
                    total_loss = abs(sum(losses))
                    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            # 총 수수료
            total_commission = trades_df['commission'].sum() if not trades_df.empty else 0
            
            metrics = {
                'period': {
                    'start_date': df['date'].iloc[0].strftime('%Y-%m-%d'),
                    'end_date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
                    'total_days': days,
                    'years': round(years, 2)
                },
                'returns': {
                    'total_return': round(total_return * 100, 2),
                    'annual_return': round(annual_return * 100, 2),
                    'final_value': round(final_value, 0),
                    'profit_loss': round(final_value - self.initial_capital, 0)
                },
                'risk': {
                    'volatility': round(volatility * 100, 2),
                    'sharpe_ratio': round(sharpe_ratio, 2),
                    'max_drawdown': round(max_drawdown * 100, 2)
                },
                'trading': {
                    'total_trades': total_trades,
                    'buy_trades': buy_trades,
                    'sell_trades': sell_trades,
                    'win_rate': round(win_rate * 100, 2),
                    'avg_win': round(avg_win * 100, 2),
                    'avg_loss': round(avg_loss * 100, 2),
                    'profit_factor': round(profit_factor, 2),
                    'total_commission': round(total_commission, 0)
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {str(e)}")
            return {}
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """백테스트 결과 리포트 생성"""
        try:
            if not results or 'performance_metrics' not in results:
                return "백테스트 결과가 없습니다."
            
            metrics = results['performance_metrics']
            
            report = []
            report.append("=" * 60)
            report.append("백테스팅 결과 리포트")
            report.append("=" * 60)
            
            # 기간 정보
            if 'period' in metrics:
                period = metrics['period']
                report.append(f"\n📅 백테스트 기간")
                report.append(f"   시작일: {period['start_date']}")
                report.append(f"   종료일: {period['end_date']}")
                report.append(f"   총 기간: {period['total_days']}일 ({period['years']}년)")
            
            # 수익률 지표
            if 'returns' in metrics:
                returns = metrics['returns']
                report.append(f"\n💰 수익률 지표")
                report.append(f"   총 수익률: {returns['total_return']:+.2f}%")
                report.append(f"   연간 수익률: {returns['annual_return']:+.2f}%")
                report.append(f"   최종 자산: {returns['final_value']:,.0f}원")
                report.append(f"   손익: {returns['profit_loss']:+,.0f}원")
            
            # 위험 지표
            if 'risk' in metrics:
                risk = metrics['risk']
                report.append(f"\n⚠️  위험 지표")
                report.append(f"   변동성: {risk['volatility']:.2f}%")
                report.append(f"   샤프 비율: {risk['sharpe_ratio']:.2f}")
                report.append(f"   최대 낙폭(MDD): {risk['max_drawdown']:.2f}%")
            
            # 거래 분석
            if 'trading' in metrics:
                trading = metrics['trading']
                report.append(f"\n📊 거래 분석")
                report.append(f"   총 거래 수: {trading['total_trades']}회")
                report.append(f"   매수 거래: {trading['buy_trades']}회")
                report.append(f"   매도 거래: {trading['sell_trades']}회")
                report.append(f"   승률: {trading['win_rate']:.1f}%")
                report.append(f"   평균 수익: {trading['avg_win']:.2f}%")
                report.append(f"   평균 손실: {trading['avg_loss']:.2f}%")
                report.append(f"   수익 비율: {trading['profit_factor']:.2f}")
                report.append(f"   총 수수료: {trading['total_commission']:,.0f}원")
            
            report.append("\n" + "=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            return f"리포트 생성 중 오류: {str(e)}"


def main():
    """백테스팅 테스트 실행"""
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 백테스팅 엔진 테스트 ===")
    
    # 데이터 수집 및 신호 생성
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    # 3년 데이터 수집
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="3y")
    
    if stock_data is not None and len(stock_data) > 200:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 신호 통합기로 매매 신호 생성
        print(f"\n2. 통합 매매 신호 생성 중...")
        integrator = SignalIntegrator(confidence_threshold=0.5, min_indicators=2)  # 더 많은 신호 생성
        
        analyzed_data = integrator.analyze_all_indicators(stock_data)
        scored_data = integrator.calculate_signal_scores(analyzed_data)
        integrated_data = integrator.generate_integrated_signals(scored_data)
        filtered_data = integrator.filter_high_confidence_signals(integrated_data)
        
        # 백테스팅 실행
        print(f"\n3. 백테스팅 실행 중...")
        backtest_engine = BacktestEngine(
            initial_capital=10000000,    # 1천만원
            commission_rate=0.003,       # 0.3%
            slippage_rate=0.001,         # 0.1%
            use_risk_management=True     # 리스크 관리 활성화
        )
        
        # 최근 2년 데이터로 백테스트
        two_years_ago = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        
        results = backtest_engine.run_backtest(
            filtered_data,
            start_date=two_years_ago
        )
        
        # 결과 출력
        if results:
            print(f"\n4. 백테스트 결과:")
            report = backtest_engine.generate_report(results)
            print(report)
            
            # 신호 통계
            buy_signals = (filtered_data['integrated_buy_signal'] == 1).sum()
            sell_signals = (filtered_data['integrated_sell_signal'] == 1).sum()
            print(f"\n📈 신호 통계:")
            print(f"   생성된 매수 신호: {buy_signals}회")
            print(f"   생성된 매도 신호: {sell_signals}회")
            
        else:
            print("   백테스트 실행 실패")
        
    else:
        print("   데이터 부족 - 최소 200일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()