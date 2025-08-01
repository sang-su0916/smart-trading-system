#!/usr/bin/env python3
"""
기본 로깅 및 모니터링 시스템
간단한 시스템 상태 모니터링 및 로그 관리
"""
import sys
import os
import time
import logging
import json
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 상위 디렉토리 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database.database_manager import DatabaseManager
from src.database.market_data_service import MarketDataService

class SystemMonitor:
    """시스템 모니터링 및 로깅"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 로깅 설정
        self.setup_logging()
        
        # 상태 파일
        self.status_file = self.log_dir / 'system_status.json'
        self.performance_file = self.log_dir / 'performance_log.json'
        
        self.logger = logging.getLogger(__name__)
    
    def setup_logging(self):
        """로깅 시스템 설정"""
        log_file = self.log_dir / f'system_monitor_{datetime.now().strftime("%Y%m%d")}.log'
        
        # 로그 포맷
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 파일 핸들러
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 루트 로거 설정
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    def get_system_resources(self):
        """시스템 리소스 정보 수집"""
        if not PSUTIL_AVAILABLE:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_available_gb': 0,
                'disk_percent': 0,
                'disk_free_gb': 0,
                'timestamp': datetime.now().isoformat(),
                'note': 'psutil not available - using dummy values'
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"시스템 리소스 수집 오류: {str(e)}")
            return None
    
    def get_database_status(self):
        """데이터베이스 상태 확인"""
        try:
            db_manager = DatabaseManager('data/trading_system.db')
            market_service = MarketDataService('data/trading_system.db')
            
            # 데이터베이스 파일 크기
            db_path = Path('data/trading_system.db')
            db_size_mb = db_path.stat().st_size / (1024*1024) if db_path.exists() else 0
            
            # 데이터 상태
            data_status = market_service.get_data_status()
            
            # 포트폴리오 수
            portfolios = db_manager.get_portfolios()
            portfolio_count = len(portfolios)
            
            # 최근 신호 수
            recent_signals = db_manager.get_recent_signals(hours=24)
            signal_count = len(recent_signals)
            
            return {
                'database_size_mb': db_size_mb,
                'total_symbols': data_status.get('total_symbols', 0),
                'portfolio_count': portfolio_count,
                'recent_signals_24h': signal_count,
                'status': data_status.get('status', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"데이터베이스 상태 확인 오류: {str(e)}")
            return None
    
    def get_log_files_status(self):
        """로그 파일 상태 확인"""
        try:
            log_files = []
            total_size = 0
            
            for log_file in self.log_dir.glob('*.log'):
                size_mb = log_file.stat().st_size / (1024*1024)
                total_size += size_mb
                
                log_files.append({
                    'name': log_file.name,
                    'size_mb': round(size_mb, 2),
                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
            
            return {
                'log_file_count': len(log_files),
                'total_size_mb': round(total_size, 2),
                'files': log_files[-5:],  # 최근 5개만
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"로그 파일 상태 확인 오류: {str(e)}")
            return None
    
    def collect_status(self):
        """전체 시스템 상태 수집"""
        status = {
            'collection_time': datetime.now().isoformat(),
            'system_resources': self.get_system_resources(),
            'database_status': self.get_database_status(),
            'log_files_status': self.get_log_files_status()
        }
        
        return status
    
    def save_status(self, status):
        """상태 정보 저장"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"시스템 상태가 {self.status_file}에 저장되었습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"상태 저장 오류: {str(e)}")
            return False
    
    def log_performance(self, operation_name, duration, details=None):
        """성능 로그 기록"""
        try:
            perf_entry = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation_name,
                'duration_seconds': round(duration, 3),
                'details': details or {}
            }
            
            # 성능 로그 파일 읽기
            performance_log = []
            if self.performance_file.exists():
                with open(self.performance_file, 'r', encoding='utf-8') as f:
                    performance_log = json.load(f)
            
            # 새 항목 추가
            performance_log.append(perf_entry)
            
            # 최대 100개 항목만 유지
            if len(performance_log) > 100:
                performance_log = performance_log[-100:]
            
            # 파일에 저장
            with open(self.performance_file, 'w', encoding='utf-8') as f:
                json.dump(performance_log, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"성능 로그 기록: {operation_name} ({duration:.3f}초)")
            return True
            
        except Exception as e:
            self.logger.error(f"성능 로그 기록 오류: {str(e)}")
            return False
    
    def check_system_health(self):
        """시스템 건강도 확인"""
        issues = []
        warnings = []
        
        # 시스템 리소스 확인
        resources = self.get_system_resources()
        if resources:
            if resources['cpu_percent'] > 90:
                issues.append(f"CPU 사용률이 높습니다: {resources['cpu_percent']:.1f}%")
            elif resources['cpu_percent'] > 70:
                warnings.append(f"CPU 사용률 주의: {resources['cpu_percent']:.1f}%")
            
            if resources['memory_percent'] > 90:
                issues.append(f"메모리 사용률이 높습니다: {resources['memory_percent']:.1f}%")
            elif resources['memory_percent'] > 80:
                warnings.append(f"메모리 사용률 주의: {resources['memory_percent']:.1f}%")
            
            if resources['disk_percent'] > 90:
                issues.append(f"디스크 사용률이 높습니다: {resources['disk_percent']:.1f}%")
            elif resources['disk_percent'] > 80:
                warnings.append(f"디스크 사용률 주의: {resources['disk_percent']:.1f}%")
        
        # 데이터베이스 상태 확인
        db_status = self.get_database_status()
        if db_status:
            if db_status['database_size_mb'] > 1000:  # 1GB
                warnings.append(f"데이터베이스 크기가 큽니다: {db_status['database_size_mb']:.1f}MB")
            
            if db_status['total_symbols'] == 0:
                issues.append("데이터베이스에 종목 데이터가 없습니다")
        
        # 로그 파일 확인
        log_status = self.get_log_files_status()
        if log_status and log_status['total_size_mb'] > 500:  # 500MB
            warnings.append(f"로그 파일 크기가 큽니다: {log_status['total_size_mb']:.1f}MB")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'status': 'error' if issues else ('warning' if warnings else 'healthy'),
            'timestamp': datetime.now().isoformat()
        }
    
    def cleanup_old_logs(self, days_to_keep=30):
        """오래된 로그 파일 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            for log_file in self.log_dir.glob('*.log'):
                file_date = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    self.logger.info(f"오래된 로그 파일 삭제: {log_file.name}")
            
            self.logger.info(f"로그 정리 완료: {deleted_count}개 파일 삭제")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"로그 정리 오류: {str(e)}")
            return 0
    
    def run_single_check(self):
        """단일 상태 확인 실행"""
        self.logger.info("=== 시스템 모니터링 시작 ===")
        
        start_time = time.time()
        
        # 상태 수집
        status = self.collect_status()
        
        # 건강도 확인
        health = self.check_system_health()
        status['health_check'] = health
        
        # 상태 저장
        self.save_status(status)
        
        # 성능 로그
        duration = time.time() - start_time
        self.log_performance('system_status_check', duration)
        
        # 결과 출력
        print("\n" + "="*60)
        print("🖥️ 시스템 모니터링 결과")
        print("="*60)
        
        if status['system_resources']:
            res = status['system_resources']
            print(f"📊 시스템 리소스:")
            print(f"  • CPU: {res['cpu_percent']:.1f}%")
            print(f"  • 메모리: {res['memory_percent']:.1f}% (여유: {res['memory_available_gb']:.1f}GB)")
            print(f"  • 디스크: {res['disk_percent']:.1f}% (여유: {res['disk_free_gb']:.1f}GB)")
        
        if status['database_status']:
            db = status['database_status']
            print(f"\n💾 데이터베이스:")
            print(f"  • 크기: {db['database_size_mb']:.1f}MB")
            print(f"  • 종목 수: {db['total_symbols']}개")
            print(f"  • 포트폴리오: {db['portfolio_count']}개")
            print(f"  • 24시간 신호: {db['recent_signals_24h']}개")
        
        if status['log_files_status']:
            log = status['log_files_status']
            print(f"\n📄 로그 파일:")
            print(f"  • 파일 수: {log['log_file_count']}개")
            print(f"  • 총 크기: {log['total_size_mb']}MB")
        
        # 건강도 표시
        print(f"\n🏥 시스템 건강도: {health['status']}")
        
        if health['issues']:
            print("🚨 문제점:")
            for issue in health['issues']:
                print(f"  • {issue}")
        
        if health['warnings']:
            print("⚠️ 주의사항:")
            for warning in health['warnings']:
                print(f"  • {warning}")
        
        if health['status'] == 'healthy':
            print("✅ 시스템이 정상 상태입니다")
        
        print(f"\n⏱️ 확인 시간: {duration:.3f}초")
        print("="*60)
        
        self.logger.info("=== 시스템 모니터링 완료 ===")
        
        return status
    
    def run_continuous_monitoring(self, interval=300):
        """지속적인 모니터링"""
        self.logger.info(f"지속적인 시스템 모니터링 시작 (간격: {interval}초)")
        
        try:
            cycle = 0
            while True:
                cycle += 1
                self.logger.info(f"모니터링 사이클 {cycle} 시작")
                
                try:
                    self.run_single_check()
                    
                    # 주기적으로 로그 정리 (하루에 한 번)
                    if cycle % (24 * 60 * 60 // interval) == 0:  # 대략 하루
                        self.cleanup_old_logs()
                    
                except Exception as e:
                    self.logger.error(f"모니터링 사이클 {cycle} 오류: {str(e)}")
                
                self.logger.info(f"다음 확인까지 {interval}초 대기...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 모니터링이 중단되었습니다")
            return True
        except Exception as e:
            self.logger.error(f"지속적인 모니터링 오류: {str(e)}")
            return False

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="시스템 모니터링 및 로깅")
    parser.add_argument('--mode', '-m', choices=['once', 'continuous', 'cleanup'], default='once',
                       help='실행 모드 (once: 단일실행, continuous: 지속모니터링, cleanup: 로그정리)')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='모니터링 간격 (초, 기본: 300=5분)')
    parser.add_argument('--log-dir', default='logs',
                       help='로그 디렉토리 (기본: logs)')
    parser.add_argument('--cleanup-days', type=int, default=30,
                       help='로그 보관 기간 (일, 기본: 30)')
    
    args = parser.parse_args()
    
    # 시스템 모니터 초기화
    try:
        monitor = SystemMonitor(log_dir=args.log_dir)
    except Exception as e:
        print(f"❌ 모니터 초기화 실패: {str(e)}")
        sys.exit(1)
    
    # 모드별 실행
    if args.mode == 'once':
        print("🔍 단일 모니터링 실행")
        status = monitor.run_single_check()
        health_status = status.get('health_check', {}).get('status', 'unknown')
        sys.exit(0 if health_status != 'error' else 1)
        
    elif args.mode == 'continuous':
        print("🔄 지속적인 모니터링 모드")
        success = monitor.run_continuous_monitoring(interval=args.interval)
        sys.exit(0 if success else 1)
        
    elif args.mode == 'cleanup':
        print("🧹 로그 정리 모드")
        deleted_count = monitor.cleanup_old_logs(days_to_keep=args.cleanup_days)
        print(f"✅ {deleted_count}개 로그 파일이 삭제되었습니다")
        sys.exit(0)

if __name__ == "__main__":
    main()