#!/usr/bin/env python3
"""
최종 강화된 에러 억제 시스템 테스트
stdout.write와 stderr.write까지 오버라이드한 시스템
"""

import builtins
import sys

# 원본 함수들 백업
_original_print = builtins.print
_original_stdout_write = sys.stdout.write
_original_stderr_write = sys.stderr.write

def silent_print(*args, **kwargs):
    """에러 메시지가 포함된 print 호출을 차단"""
    if args:
        message = ' '.join(str(arg) for arg in args)
        blocked_keywords = [
            'error 404', 'delisted', 'no price data', 'yahoo error',
            'http error', 'possibly delisted', '$161890', 'symbol may be delisted'
        ]
        if any(keyword in message.lower() for keyword in blocked_keywords):
            return  # 조용히 무시
    _original_print(*args, **kwargs)

def silent_stdout_write(text):
    """stdout.write 호출을 차단"""
    if isinstance(text, str):
        blocked_keywords = [
            'error 404', 'delisted', 'no price data', 'yahoo error',
            'http error', 'possibly delisted', '$161890', 'symbol may be delisted'
        ]
        if any(keyword in text.lower() for keyword in blocked_keywords):
            return len(text)  
    return _original_stdout_write(text)

def silent_stderr_write(text):
    """stderr.write 호출을 차단"""
    if isinstance(text, str):
        blocked_keywords = [
            'error 404', 'delisted', 'no price data', 'yahoo error',
            'http error', 'possibly delisted', '$161890', 'symbol may be delisted'
        ]
        if any(keyword in text.lower() for keyword in blocked_keywords):
            return len(text)  
    return _original_stderr_write(text)

# 전역 함수들 오버라이드
builtins.print = silent_print
sys.stdout.write = silent_stdout_write
sys.stderr.write = silent_stderr_write

# 나머지 설정들
import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger().setLevel(logging.CRITICAL)

import urllib3
urllib3.disable_warnings()

import yfinance as yf
import os
from io import StringIO
from contextlib import redirect_stderr

# 환경 변수 설정
os.environ['YFINANCE_TIMEOUT'] = '5'
os.environ['YFINANCE_RETRY'] = '1'

def safe_call(func, *args, **kwargs):
    try:
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            try:
                with redirect_stderr(StringIO()):
                    return func(*args, **kwargs)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
    except:
        return None

def test_ultimate_suppression():
    print("🚀 최종 에러 억제 시스템 테스트")
    print("=" * 50)
    
    # 직접적인 에러 메시지 테스트
    print("🧪 직접 에러 메시지 테스트...")
    test_messages = [
        "HTTP Error 404: Not Found",
        "$161890: possibly delisted; no price data found",
        "정상 메시지는 출력되어야 함",
        "Yahoo error = No data found"
    ]
    
    for msg in test_messages:
        print(f"테스트: {msg}")
    
    # stdout.write 테스트
    print("\n🧪 stdout.write 테스트...")
    sys.stdout.write("정상 stdout 메시지\n")
    sys.stdout.write("HTTP Error 404: 이 메시지는 차단되어야 함\n")
    sys.stdout.write("$161890: possibly delisted - 이것도 차단\n")
    
    # stderr.write 테스트  
    print("\n🧪 stderr.write 테스트...")
    sys.stderr.write("정상 stderr 메시지\n")
    sys.stderr.write("HTTP Error 404: stderr 차단 테스트\n")
    
    # yfinance 테스트
    print("\n🧪 yfinance 테스트...")
    problem_symbols = ["161890.KS", "INVALID.KS", "NONEXISTENT.KS"]
    
    for symbol in problem_symbols:
        print(f"  📊 {symbol} 테스트 중...")
        try:
            ticker = yf.Ticker(symbol)
            data = safe_call(ticker.history, period="1mo")
            if data is None or data.empty:
                print(f"    ✅ {symbol}: 조용히 처리됨")
            else:
                print(f"    ⚠️  {symbol}: 데이터 있음 ({len(data)}일)")
        except Exception as e:
            print(f"    ❌ {symbol}: 예외 - {str(e)[:30]}...")
    
    print("\n" + "=" * 50)
    print("🎉 모든 테스트 완료!")
    print("❗ HTTP Error 404나 delisted 메시지가 없어야 합니다.")

if __name__ == "__main__":
    test_ultimate_suppression()
    
    # 원본 함수들 복원
    builtins.print = _original_print
    sys.stdout.write = _original_stdout_write  
    sys.stderr.write = _original_stderr_write