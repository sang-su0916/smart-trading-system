"""
실행 파일(.exe) 생성 스크립트
PyInstaller를 사용해서 독립실행 가능한 파일 생성
"""
import os
import subprocess
import sys

def build_executable():
    """실행 파일 빌드"""
    print("🔨 실행 파일 빌드 시작...")
    
    # PyInstaller 설치 확인
    try:
        import PyInstaller
    except ImportError:
        print("📦 PyInstaller 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 빌드 명령어
    build_command = [
        "pyinstaller",
        "--onefile",                    # 단일 파일로 생성
        "--windowed",                   # 콘솔 창 숨기기
        "--name=SmartTradingDashboard", # 실행 파일 이름
        "--icon=📊",                   # 아이콘 (선택사항)
        "--add-data=src;src",          # 소스 파일 포함
        "--add-data=config;config",    # 설정 파일 포함
        "streamlit_app.py"             # 메인 파일
    ]
    
    try:
        subprocess.check_call(build_command)
        print("✅ 실행 파일 생성 완료!")
        print("📁 파일 위치: dist/SmartTradingDashboard.exe")
        print("💡 이 파일을 다른 사람에게 전달하면 바로 실행 가능합니다!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    build_executable()