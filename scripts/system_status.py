#!/usr/bin/env python3
"""
시스템 상태 확인 스크립트
데이터베이스, 포트폴리오, 신호 상태를 간단히 확인
"""
import sys
import os
from datetime import datetime, timedelta
import json

# 상위 디렉토리 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database.database_manager import DatabaseManager
from src.database.market_data_service import MarketDataService

def check_system_status():
    """시스템 전체 상태 확인"""
    print("🔍 알고리즘 트레이딩 시스템 상태 확인")
    print("=" * 50)
    
    try:
        # 데이터베이스 연결
        db_manager = DatabaseManager('data/trading_system.db')
        market_service = MarketDataService('data/trading_system.db')
        
        # 1. 데이터베이스 상태
        print("\n📊 데이터베이스 상태:")
        data_status = market_service.get_data_status()
        
        print(f"  • 총 종목 수: {data_status.get('total_symbols', 0)}개")
        print(f"  • 데이터 상태: {data_status.get('status', 'unknown')}")
        
        if data_status.get('needs_update'):
            print(f"  • 업데이트 필요: {len(data_status['needs_update'])}개 종목")
        else:
            print("  • 모든 데이터가 최신 상태입니다")
        
        # 2. 포트폴리오 상태
        print("\n💼 포트폴리오 상태:")
        portfolios = db_manager.get_portfolios()
        
        if portfolios.empty:
            print("  • 포트폴리오가 없습니다")
        else:
            print(f"  • 활성 포트폴리오: {len(portfolios)}개")
            
            for _, portfolio in portfolios.iterrows():
                pnl = portfolio['current_value'] - portfolio['initial_capital']
                pnl_pct = (pnl / portfolio['initial_capital']) * 100
                
                print(f"    - {portfolio['name']}")
                print(f"      초기자본: {portfolio['initial_capital']:,.0f}원")
                print(f"      현재가치: {portfolio['current_value']:,.0f}원")
                print(f"      손익: {pnl:+,.0f}원 ({pnl_pct:+.2f}%)")
                
                # 보유 종목
                holdings = db_manager.get_portfolio_holdings(portfolio['id'])
                if not holdings.empty:
                    print(f"      보유종목: {len(holdings)}개")
                    for _, holding in holdings.head(3).iterrows():  # 최대 3개만 표시
                        print(f"        • {holding['symbol']}: {holding['quantity']}주")
        
        # 3. 최근 신호 상태
        print("\n🚨 최근 매매 신호:")
        
        # 24시간 내 신호
        recent_signals = db_manager.get_recent_signals(hours=24)
        
        if recent_signals.empty:
            print("  • 최근 24시간 내 신호가 없습니다")
        else:
            print(f"  • 최근 24시간: {len(recent_signals)}개 신호")
            
            signal_counts = recent_signals['signal_type'].value_counts()
            for signal_type, count in signal_counts.items():
                emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal_type, "⚪")
                print(f"    {emoji} {signal_type}: {count}개")
            
            # 최신 신호 3개
            print("  • 최신 신호:")
            for _, signal in recent_signals.head(3).iterrows():
                time_str = signal['signal_date']
                confidence = signal.get('confidence', 0)
                print(f"    - {signal['symbol']}: {signal['signal_type']} (신뢰도: {confidence:.2f}) - {time_str}")
        
        # 4. 최근 거래 상태
        print("\n📈 최근 거래:")
        recent_trades = db_manager.get_trade_history(days=7)
        
        if recent_trades.empty:
            print("  • 최근 7일간 거래가 없습니다")
        else:
            print(f"  • 최근 7일: {len(recent_trades)}건")
            
            for _, trade in recent_trades.head(3).iterrows():  # 최대 3개만 표시
                trade_date = trade['trade_date']
                print(f"    - {trade['symbol']}: {trade['trade_type']} {trade['quantity']}주 @ {trade['price']:,.0f}원 ({trade_date})")
        
        # 5. 시스템 파일 상태
        print("\n🗄️ 시스템 파일:")
        
        # 데이터베이스 파일 크기
        db_path = 'data/trading_system.db'
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / 1024 / 1024  # MB
            print(f"  • 데이터베이스 크기: {db_size:.1f} MB")
        
        # 로그 파일
        log_dir = 'logs'
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            print(f"  • 로그 파일: {len(log_files)}개")
        
        # CSV 데이터 파일
        data_dir = 'data'
        csv_count = 0
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                csv_count += len([f for f in files if f.endswith('.csv')])
        print(f"  • CSV 데이터 파일: {csv_count}개")
        
        print("\n✅ 시스템 상태 확인 완료")
        return True
        
    except Exception as e:
        print(f"\n❌ 시스템 상태 확인 중 오류: {str(e)}")
        return False

def export_status_json():
    """상태 정보를 JSON으로 내보내기"""
    try:
        db_manager = DatabaseManager('data/trading_system.db')
        market_service = MarketDataService('data/trading_system.db')
        
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "database": market_service.get_data_status(),
            "portfolios": len(db_manager.get_portfolios()),
            "recent_signals_24h": len(db_manager.get_recent_signals(hours=24)),
            "recent_trades_7d": len(db_manager.get_trade_history(days=7))
        }
        
        # 상태 파일 저장
        status_file = f"logs/system_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('logs', exist_ok=True)
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 상태 정보가 {status_file}에 저장되었습니다")
        return True
        
    except Exception as e:
        print(f"❌ 상태 내보내기 실패: {str(e)}")
        return False

def main():
    """메인 실행 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        # JSON 모드
        success = export_status_json()
    else:
        # 일반 모드
        success = check_system_status()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()