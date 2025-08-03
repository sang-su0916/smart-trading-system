#!/usr/bin/env python3
"""
강화된 에러 억제 시스템 테스트
"""

# 전역 print 오버라이드 테스트
original_print = print
def silent_print(*args, **kwargs):
    message = ' '.join(str(arg) for arg in args)
    if any(keyword in message.lower() for keyword in ['error 404', 'delisted', 'no price data', 'yahoo error']):
        pass  # 조용히 무시
    else:
        original_print(*args, **kwargs)

import builtins
builtins.print = silent_print

# 나머지 설정들
import warnings
warnings.filterwarnings('ignore')
import logging
import sys
import os
from contextlib import redirect_stderr
from io import StringIO

# 모든 관련 라이브러리 로깅 완전 억제
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('requests.packages.urllib3').setLevel(logging.CRITICAL)

import urllib3
urllib3.disable_warnings()

# 강화된 안전 래퍼
def safe_yfinance_call(func, *args, **kwargs):
    """최고 강도 에러 억제 래퍼"""
    try:
        with open(os.devnull, 'w') as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            
            try:
                with redirect_stderr(StringIO()):
                    result = func(*args, **kwargs)
                    return result
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
    except Exception:
        return None

import yfinance as yf

def test_problematic_symbols():
    """문제가 되는 심볼들 테스트"""
    print("🧪 문제 심볼 테스트 시작...")
    
    problem_symbols = [
        "161890.KS",    # 한국콜마
        "INVALID.KS",   # 존재하지 않는 종목
        "DELISTED.KS",  # 상장폐지 테스트
        "404ERROR.KS"   # 404 에러 테스트
    ]
    
    for symbol in problem_symbols:
        print(f"  📊 {symbol} 테스트 중...")
        
        try:
            ticker = yf.Ticker(symbol)
            data = safe_yfinance_call(ticker.history, period="1mo")
            
            if data is None or data.empty:
                print(f"    ✅ {symbol}: 조용히 처리됨")
            else:
                print(f"    ⚠️  {symbol}: 데이터 반환됨 ({len(data)}일)")
        except Exception as e:
            print(f"    ❌ {symbol}: 예외 - {str(e)[:30]}...")
    
    print("✅ 문제 심볼 테스트 완료\n")

def test_direct_error_messages():
    """직접적인 에러 메시지 테스트"""
    print("🧪 에러 메시지 억제 테스트...")
    
    # 이런 메시지들이 출력되면 안됨
    test_messages = [
        "HTTP Error 404: Not Found",
        "$161890: possibly delisted; no price data found",
        "Yahoo error = No data found, symbol may be delisted",
        "정상 메시지는 출력되어야 함"
    ]
    
    for msg in test_messages:
        print(f"테스트 메시지: {msg}")
    
    print("✅ 에러 메시지 억제 테스트 완료\n")

if __name__ == "__main__":
    print("🚀 강화된 에러 억제 시스템 테스트")
    print("=" * 50)
    
    test_problematic_symbols()
    test_direct_error_messages()
    
    print("=" * 50)
    print("🎉 모든 테스트 완료!")
    print("❗ 위에 HTTP Error 404나 delisted 메시지가 없어야 합니다.")
    
    # print 함수 복원
    builtins.print = original_print