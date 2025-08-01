#!/usr/bin/env python3
"""
단순한 매매 신호 알림 시스템
콘솔 출력 및 파일 기반 간단한 알림 시스템
"""
import sys
import os
import time
from datetime import datetime, timedelta
import json
import argparse

# 상위 디렉토리 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database.database_manager import DatabaseManager

class SimpleSignalAlert:
    """간단한 매매 신호 알림 시스템"""
    
    def __init__(self, db_path='data/trading_system.db'):
        self.db_manager = DatabaseManager(db_path)
        self.alert_file = 'logs/signal_alerts.json'
        self.last_check_file = 'logs/last_alert_check.txt'
        
        # 로그 디렉토리 생성
        os.makedirs('logs', exist_ok=True)
        
    def get_last_check_time(self):
        """마지막 확인 시간 조회"""
        try:
            if os.path.exists(self.last_check_file):
                with open(self.last_check_file, 'r') as f:
                    time_str = f.read().strip()
                    return datetime.fromisoformat(time_str)
            else:
                # 파일이 없으면 1시간 전으로 설정
                return datetime.now() - timedelta(hours=1)
        except Exception:
            return datetime.now() - timedelta(hours=1)
    
    def save_last_check_time(self):
        """마지막 확인 시간 저장"""
        try:
            with open(self.last_check_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            print(f"⚠️ 확인 시간 저장 실패: {str(e)}")
    
    def check_new_signals(self, hours=1):
        """새로운 신호 확인"""
        try:
            # 최근 신호 조회
            signals = self.db_manager.get_recent_signals(hours=hours)
            
            if signals.empty:
                return []
            
            # 마지막 확인 시간 이후 신호만 필터링
            last_check = self.get_last_check_time()
            
            # signal_date를 datetime으로 변환 후 필터링
            new_signals = []
            for _, signal in signals.iterrows():
                try:
                    # 문자열을 datetime으로 변환
                    signal_time = datetime.fromisoformat(signal['signal_date'].replace('Z', '+09:00'))
                    if signal_time > last_check:
                        new_signals.append(signal.to_dict())
                except Exception:
                    # 변환 실패 시 최근 신호로 간주
                    new_signals.append(signal.to_dict())
            
            return new_signals
            
        except Exception as e:
            print(f"❌ 신호 확인 중 오류: {str(e)}")
            return []
    
    def format_signal_message(self, signal):
        """신호 메시지 포맷팅"""
        symbol = signal.get('symbol', 'Unknown')
        signal_type = signal.get('signal_type', 'Unknown')
        confidence = signal.get('confidence', 0)
        signal_date = signal.get('signal_date', 'Unknown')
        
        # 신호 타입별 이모지
        emoji_map = {
            'BUY': '🟢',
            'SELL': '🔴', 
            'HOLD': '🟡'
        }
        emoji = emoji_map.get(signal_type, '⚪')
        
        # 신뢰도에 따른 강도 표시
        if confidence >= 0.8:
            strength = "🔥 강력"
        elif confidence >= 0.6:
            strength = "⚡ 보통"
        else:
            strength = "💡 약함"
        
        return f"{emoji} {symbol}: {signal_type} 신호 ({strength}, 신뢰도: {confidence:.2f}) - {signal_date}"
    
    def save_alert_log(self, alerts):
        """알림 로그 저장"""
        try:
            # 기존 로그 읽기
            alert_history = []
            if os.path.exists(self.alert_file):
                with open(self.alert_file, 'r', encoding='utf-8') as f:
                    alert_history = json.load(f)
            
            # 새 알림 추가
            for alert in alerts:
                alert_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'signal': alert,
                    'notified': True
                }
                alert_history.append(alert_entry)
            
            # 최대 100개 기록만 유지
            if len(alert_history) > 100:
                alert_history = alert_history[-100:]
            
            # 파일에 저장
            with open(self.alert_file, 'w', encoding='utf-8') as f:
                json.dump(alert_history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ 알림 로그 저장 실패: {str(e)}")
    
    def send_console_alerts(self, signals):
        """콘솔 알림 출력"""
        if not signals:
            return
        
        print("\n" + "="*60)
        print(f"🚨 매매 신호 알림 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 신호 타입별 분류
        buy_signals = [s for s in signals if s.get('signal_type') == 'BUY']
        sell_signals = [s for s in signals if s.get('signal_type') == 'SELL']
        hold_signals = [s for s in signals if s.get('signal_type') == 'HOLD']
        
        # 매수 신호
        if buy_signals:
            print(f"\n🟢 매수 신호 ({len(buy_signals)}개):")
            for signal in buy_signals:
                print(f"  {self.format_signal_message(signal)}")
        
        # 매도 신호
        if sell_signals:
            print(f"\n🔴 매도 신호 ({len(sell_signals)}개):")
            for signal in sell_signals:
                print(f"  {self.format_signal_message(signal)}")
        
        # 관망 신호
        if hold_signals:
            print(f"\n🟡 관망 신호 ({len(hold_signals)}개):")
            for signal in hold_signals:
                print(f"  {self.format_signal_message(signal)}")
        
        print("\n" + "="*60)
        print(f"💡 총 {len(signals)}개의 새로운 신호가 발생했습니다.")
        print("="*60)
    
    def send_file_alert(self, signals):
        """파일 기반 알림 생성"""
        if not signals:
            return
        
        alert_summary_file = f"logs/alert_summary_{datetime.now().strftime('%Y%m%d')}.txt"
        
        try:
            with open(alert_summary_file, 'a', encoding='utf-8') as f:
                f.write(f"\n=== 알림 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                
                for signal in signals:
                    f.write(f"{self.format_signal_message(signal)}\n")
                
                f.write(f"총 {len(signals)}개 신호\n")
                f.write("-" * 50 + "\n")
            
            print(f"📄 알림이 파일에 저장되었습니다: {alert_summary_file}")
            
        except Exception as e:
            print(f"⚠️ 파일 알림 저장 실패: {str(e)}")
    
    def run_once(self, hours=1, console=True, file_alert=True):
        """단일 실행 모드"""
        print(f"🔍 최근 {hours}시간 새로운 신호 확인 중...")
        
        new_signals = self.check_new_signals(hours=hours)
        
        if new_signals:
            print(f"✅ {len(new_signals)}개의 새로운 신호를 발견했습니다!")
            
            # 콘솔 알림
            if console:
                self.send_console_alerts(new_signals)
            
            # 파일 알림
            if file_alert:
                self.send_file_alert(new_signals)
            
            # 알림 로그 저장
            self.save_alert_log(new_signals)
            
        else:
            print("ℹ️ 새로운 신호가 없습니다.")
        
        # 마지막 확인 시간 저장
        self.save_last_check_time()
        
        return len(new_signals)
    
    def run_monitor(self, interval=300, hours=1):
        """모니터링 모드 (지속 실행)"""
        print(f"🔄 매매 신호 모니터링 시작")
        print(f"📊 확인 간격: {interval}초 ({interval//60}분)")
        print(f"⏰ 신호 범위: 최근 {hours}시간")
        print("🛑 종료하려면 Ctrl+C를 누르세요")
        print("=" * 50)
        
        try:
            cycle_count = 0
            while True:
                cycle_count += 1
                print(f"\n🔍 [{cycle_count}] 신호 확인 중... ({datetime.now().strftime('%H:%M:%S')})")
                
                new_count = self.run_once(hours=hours, console=True, file_alert=True)
                
                if new_count > 0:
                    print(f"🎯 {new_count}개 신호 알림 완료")
                else:
                    print("😴 새로운 신호 없음")
                
                print(f"⏰ {interval}초 후 다시 확인합니다...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 모니터링이 중단되었습니다.")
            print(f"📊 총 {cycle_count}번 확인했습니다.")
            return True
        
        except Exception as e:
            print(f"\n❌ 모니터링 중 오류: {str(e)}")
            return False
    
    def show_alert_history(self, days=7):
        """알림 기록 조회"""
        try:
            if not os.path.exists(self.alert_file):
                print("📋 알림 기록이 없습니다.")
                return
            
            with open(self.alert_file, 'r', encoding='utf-8') as f:
                alert_history = json.load(f)
            
            if not alert_history:
                print("📋 알림 기록이 없습니다.")
                return
            
            # 최근 N일 기록만 필터링
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_alerts = []
            
            for alert in alert_history:
                try:
                    alert_time = datetime.fromisoformat(alert['timestamp'])
                    if alert_time > cutoff_date:
                        recent_alerts.append(alert)
                except Exception:
                    continue
            
            if not recent_alerts:
                print(f"📋 최근 {days}일간 알림 기록이 없습니다.")
                return
            
            print(f"📋 최근 {days}일간 알림 기록 ({len(recent_alerts)}개)")
            print("=" * 60)
            
            for alert in recent_alerts[-10:]:  # 최근 10개만 표시
                timestamp = alert['timestamp']
                signal = alert['signal']
                
                print(f"⏰ {timestamp}")
                print(f"   {self.format_signal_message(signal)}")
                print()
            
            if len(recent_alerts) > 10:
                print(f"... 총 {len(recent_alerts)}개 기록 중 최근 10개만 표시")
                
        except Exception as e:
            print(f"❌ 알림 기록 조회 오류: {str(e)}")

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="단순한 매매 신호 알림 시스템")
    parser.add_argument('--mode', '-m', choices=['once', 'monitor', 'history'], default='once',
                       help='실행 모드 (once: 단일실행, monitor: 지속모니터링, history: 기록조회)')
    parser.add_argument('--hours', '-hr', type=int, default=1,
                       help='신호 확인 범위 (시간, 기본: 1)')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='모니터링 간격 (초, 기본: 300=5분)')
    parser.add_argument('--days', '-d', type=int, default=7,
                       help='기록 조회 기간 (일, 기본: 7)')
    parser.add_argument('--no-console', action='store_true',
                       help='콘솔 출력 비활성화')
    parser.add_argument('--no-file', action='store_true',
                       help='파일 저장 비활성화')
    
    args = parser.parse_args()
    
    # 알림 시스템 초기화
    try:
        alert_system = SimpleSignalAlert()
    except Exception as e:
        print(f"❌ 알림 시스템 초기화 실패: {str(e)}")
        sys.exit(1)
    
    # 모드별 실행
    if args.mode == 'once':
        print("🔍 단일 실행 모드")
        signal_count = alert_system.run_once(
            hours=args.hours,
            console=not args.no_console,
            file_alert=not args.no_file
        )
        sys.exit(0 if signal_count >= 0 else 1)
        
    elif args.mode == 'monitor':
        print("🔄 모니터링 모드")
        success = alert_system.run_monitor(
            interval=args.interval,
            hours=args.hours
        )
        sys.exit(0 if success else 1)
        
    elif args.mode == 'history':
        print("📋 기록 조회 모드")
        alert_system.show_alert_history(days=args.days)
        sys.exit(0)

if __name__ == "__main__":
    main()