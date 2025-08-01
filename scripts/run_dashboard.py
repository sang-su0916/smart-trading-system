#!/usr/bin/env python3
"""
성능 최적화된 대시보드 실행 스크립트
간단한 실행 및 모니터링 기능 포함
"""
import os
import sys
import subprocess
import time
import argparse
from datetime import datetime

def run_dashboard(dashboard_type="cached", port=8501, debug=False):
    """대시보드 실행"""
    
    # 현재 스크립트 위치에서 상위 디렉토리로 이동
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    # 대시보드 파일 경로 설정
    dashboard_files = {
        "simple": os.path.join(project_dir, "dashboard", "simple_dashboard.py"),
        "cached": os.path.join(project_dir, "dashboard", "cached_dashboard.py")
    }
    
    if dashboard_type not in dashboard_files:
        print(f"❌ 지원하지 않는 대시보드 타입: {dashboard_type}")
        print(f"사용 가능한 타입: {list(dashboard_files.keys())}")
        return False
    
    dashboard_file = dashboard_files[dashboard_type]
    
    # 파일 존재 확인
    if not os.path.exists(dashboard_file):
        print(f"❌ 대시보드 파일을 찾을 수 없습니다: {dashboard_file}")
        return False
    
    print(f"🚀 {dashboard_type} 대시보드 시작")
    print(f"📁 파일: {dashboard_file}")
    print(f"🌐 포트: {port}")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        # Streamlit 명령어 구성
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            dashboard_file,
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ]
        
        # 디버그 모드일 때 추가 옵션
        if debug:
            cmd.extend([
                "--logger.level", "debug",
                "--server.enableCORS", "false"
            ])
        
        print(f"💻 실행 명령어: {' '.join(cmd)}")
        print("\n📊 대시보드가 시작되었습니다!")
        print(f"🔗 URL: http://localhost:{port}")
        print("\n⚡ 종료하려면 Ctrl+C를 누르세요")
        print("=" * 50)
        
        # 프로세스 실행
        process = subprocess.Popen(cmd, cwd=project_dir)
        
        # 프로세스 모니터링
        try:
            while True:
                # 프로세스 상태 확인
                if process.poll() is not None:
                    print(f"\n⚠️ 대시보드 프로세스가 종료되었습니다 (코드: {process.returncode})")
                    break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n🛑 사용자에 의해 중단되었습니다")
            print("🔄 대시보드를 종료하는 중...")
            
            # 프로세스 종료
            process.terminate()
            
            # 강제 종료 대기
            try:
                process.wait(timeout=5)
                print("✅ 대시보드가 정상적으로 종료되었습니다")
            except subprocess.TimeoutExpired:
                print("⚠️ 강제 종료합니다...")
                process.kill()
                process.wait()
            
        return True
        
    except FileNotFoundError:
        print("❌ Streamlit를 찾을 수 없습니다.")
        print("💡 다음 명령어로 설치하세요: pip install streamlit")
        return False
        
    except Exception as e:
        print(f"❌ 대시보드 실행 중 오류: {str(e)}")
        return False

def check_dependencies():
    """필수 의존성 확인"""
    print("🔍 의존성 확인 중...")
    
    required_packages = [
        "streamlit",
        "pandas", 
        "plotly",
        "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 누락된 패키지: {', '.join(missing_packages)}")
        print("💡 다음 명령어로 설치하세요:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 모든 의존성이 설치되어 있습니다")
    return True

def show_status():
    """시스템 상태 표시"""
    print("📊 대시보드 시스템 상태")
    print("=" * 50)
    
    # 현재 위치
    current_dir = os.getcwd()
    print(f"📁 현재 디렉토리: {current_dir}")
    
    # 데이터베이스 파일 확인
    db_path = "data/trading_system.db"
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / 1024 / 1024  # MB
        print(f"💾 데이터베이스: {db_path} ({db_size:.1f} MB)")
    else:
        print(f"⚠️ 데이터베이스 파일이 없습니다: {db_path}")
    
    # 대시보드 파일 확인
    dashboard_dir = "dashboard"
    if os.path.exists(dashboard_dir):
        dashboard_files = [f for f in os.listdir(dashboard_dir) if f.endswith('.py')]
        print(f"📊 대시보드 파일: {len(dashboard_files)}개")
        for file in dashboard_files:
            print(f"  - {file}")
    else:
        print("⚠️ 대시보드 디렉토리가 없습니다")
    
    print("=" * 50)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="성능 최적화된 대시보드 실행")
    parser.add_argument('--type', '-t', choices=['simple', 'cached'], default='cached', 
                       help='대시보드 타입 (기본: cached)')
    parser.add_argument('--port', '-p', type=int, default=8501, 
                       help='서버 포트 (기본: 8501)')
    parser.add_argument('--debug', '-d', action='store_true', 
                       help='디버그 모드')
    parser.add_argument('--status', '-s', action='store_true', 
                       help='시스템 상태만 표시')
    parser.add_argument('--check', '-c', action='store_true', 
                       help='의존성만 확인')
    
    args = parser.parse_args()
    
    # 상태 표시만
    if args.status:
        show_status()
        return
    
    # 의존성 확인만
    if args.check:
        success = check_dependencies()
        sys.exit(0 if success else 1)
    
    # 의존성 확인
    if not check_dependencies():
        sys.exit(1)
    
    # 대시보드 실행
    success = run_dashboard(
        dashboard_type=args.type,
        port=args.port,
        debug=args.debug
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()