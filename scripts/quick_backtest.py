#!/usr/bin/env python3
"""
빠른 백테스팅 실행 스크립트
단일 종목에 대한 간단한 백테스팅 수행
"""
import sys
import os
from datetime import datetime, timedelta
import argparse

# 상위 디렉토리 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_collection.data_manager import DataManager
from src.trading_signals.signal_integrator import SignalIntegrator  
from src.backtesting.backtest_engine import BacktestEngine

def run_quick_backtest(symbol="005930.KS", period="1y", initial_capital=10000000, confidence_threshold=0.7):
    """빠른 백테스팅 실행"""
    
    print(f"🚀 빠른 백테스팅 시작")
    print(f"종목: {symbol}")
    print(f"기간: {period}")
    print(f"초기자본: {initial_capital:,}원")
    print(f"신뢰도 임계값: {confidence_threshold}")
    print("=" * 50)
    
    try:
        # 1. 데이터 수집
        print("📊 데이터 수집 중...")
        data_manager = DataManager()
        stock_data = data_manager.yahoo_collector.get_stock_data(symbol, period=period)
        
        if stock_data.empty:
            print(f"❌ {symbol} 데이터를 가져올 수 없습니다")
            return False
            
        print(f"✅ {len(stock_data)}일 데이터 수집 완료")
        
        # 2. 신호 생성
        print("🔍 매매 신호 생성 중...")
        integrator = SignalIntegrator(
            confidence_threshold=confidence_threshold,
            min_indicators=3
        )
        
        # 기술적 분석 수행
        analyzed_data = integrator.analyze_all_indicators(stock_data)
        scored_data = integrator.calculate_signal_scores(analyzed_data)
        integrated_data = integrator.generate_integrated_signals(scored_data)
        filtered_data = integrator.filter_high_confidence_signals(integrated_data)
        
        # 신호 통계
        buy_signals = (filtered_data['integrated_buy_signal'] == 1).sum()
        sell_signals = (filtered_data['integrated_sell_signal'] == 1).sum()
        
        print(f"✅ 매수 신호: {buy_signals}개, 매도 신호: {sell_signals}개")
        
        if buy_signals == 0 and sell_signals == 0:
            print("⚠️ 신뢰도 기준을 만족하는 신호가 없습니다")
            print("💡 confidence_threshold를 낮춰보세요 (예: 0.6)")
            return False
        
        # 3. 백테스팅 실행
        print("⚡ 백테스팅 실행 중...")
        backtest_engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_rate=0.003,
            use_risk_management=True
        )
        
        results = backtest_engine.run_backtest(filtered_data)
        
        # 4. 결과 출력
        print("\n" + "=" * 50)
        print("📈 백테스팅 결과")
        print("=" * 50)
        
        # 기본 수익률 정보
        total_return_pct = results['total_return_pct']
        final_value = results['final_value']
        total_profit = final_value - initial_capital
        
        print(f"📊 수익률 지표:")
        print(f"  • 최종 자산: {final_value:,.0f}원")
        print(f"  • 총 손익: {total_profit:+,.0f}원")
        print(f"  • 총 수익률: {total_return_pct:+.2f}%")
        
        if 'annualized_return_pct' in results:
            print(f"  • 연간 수익률: {results['annualized_return_pct']:+.2f}%")
        
        # 리스크 지표
        if 'max_drawdown_pct' in results:
            print(f"  • 최대 낙폭: {results['max_drawdown_pct']:.2f}%")
            
        if 'volatility_pct' in results:
            print(f"  • 변동성: {results['volatility_pct']:.2f}%")
            
        if 'sharpe_ratio' in results:
            print(f"  • 샤프 비율: {results['sharpe_ratio']:.2f}")
        
        # 거래 통계
        total_trades = results.get('total_trades', 0)
        if total_trades > 0:
            print(f"\n📊 거래 분석:")
            print(f"  • 총 거래 수: {total_trades}회")
            
            if 'win_rate_pct' in results:
                print(f"  • 승률: {results['win_rate_pct']:.1f}%")
            
            if 'avg_profit_pct' in results:
                print(f"  • 평균 수익: {results['avg_profit_pct']:+.2f}%")
                
            if 'avg_loss_pct' in results:
                print(f"  • 평균 손실: {results['avg_loss_pct']:+.2f}%")
                
            if 'profit_factor' in results:
                print(f"  • 수익 비율: {results['profit_factor']:.2f}")
        
        # 간단한 평가
        print(f"\n📝 평가:")
        if total_return_pct > 0:
            if total_return_pct > 10:
                print("🎉 우수한 수익률입니다!")
            elif total_return_pct > 5:
                print("👍 양호한 수익률입니다")
            else:
                print("✅ 플러스 수익률을 달성했습니다")
        else:
            print("⚠️ 손실이 발생했습니다. 전략을 재검토해보세요")
        
        # 거래 빈도 평가
        days = len(stock_data)
        if total_trades > 0:
            trades_per_month = (total_trades / days) * 30
            if trades_per_month > 4:
                print("⚠️ 거래 빈도가 높습니다. 수수료를 고려하세요")
            elif trades_per_month < 0.5:
                print("💡 거래 빈도가 낮습니다. 더 많은 기회를 찾아보세요")
            else:
                print("✅ 적절한 거래 빈도입니다")
        
        print("\n✅ 백테스팅 완료")
        return True
        
    except Exception as e:
        print(f"❌ 백테스팅 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="빠른 백테스팅 실행")
    parser.add_argument('--symbol', '-s', default='005930.KS', help='종목 코드 (기본: 005930.KS)')
    parser.add_argument('--period', '-p', default='1y', help='분석 기간 (기본: 1y)')
    parser.add_argument('--capital', '-c', type=int, default=10000000, help='초기 자본 (기본: 10000000)')
    parser.add_argument('--confidence', '-conf', type=float, default=0.7, help='신뢰도 임계값 (기본: 0.7)')
    
    args = parser.parse_args()
    
    success = run_quick_backtest(
        symbol=args.symbol,
        period=args.period, 
        initial_capital=args.capital,
        confidence_threshold=args.confidence
    )
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()