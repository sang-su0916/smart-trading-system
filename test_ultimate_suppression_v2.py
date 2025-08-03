#!/usr/bin/env python3
"""
최종 강화된 에러 억제 시스템 테스트 v2
전역 print, stdout.write, stderr.write 오버라이드 테스트
"""

# 최우선으로 전역 함수 오버라이드 (yfinance import 전에)
import builtins
import sys
import os

# 원본 함수들 백업
_original_print = builtins.print
_original_stdout_write = sys.stdout.write
_original_stderr_write = sys.stderr.write

def global_silent_print(*args, **kwargs):
    """전역 print 함수 오버라이드 - 에러 메시지 완전 차단"""
    if args:
        message = ' '.join(str(arg) for arg in args)
        blocked_keywords = [
            'error 404', 'delisted', 'no price data', 'yahoo error',
            'http error', 'possibly delisted', '$161890', 'symbol may be delisted',
            '404:', 'not found', 'no data found', 'http error 404',
            '$161890:', '$005930.ks:', 'period=1y', 'period=5d', '(yah',
            'may be delisted', 'no price data found'
        ]
        if any(keyword in message.lower() for keyword in blocked_keywords):
            return  # 완전히 차단
    # 정상 메시지만 출력
    _original_print(*args, **kwargs)

def silent_stdout_write(text):
    """stdout.write 오버라이드"""
    if isinstance(text, str):
        blocked_keywords = [
            'error 404', 'delisted', 'no price data', 'yahoo error',
            'http error', 'possibly delisted', '$161890', 'symbol may be delisted',
            '404:', 'not found', 'no data found', 'http error 404',
            '$161890:', '$005930.ks:', 'period=1y', 'period=5d', '(yah',
            'may be delisted', 'no price data found'
        ]
        if any(keyword in text.lower() for keyword in blocked_keywords):
            return len(text)  # 길이만 반환하고 출력 차단
    return _original_stdout_write(text)

def silent_stderr_write(text):
    """stderr.write 오버라이드"""
    if isinstance(text, str):
        blocked_keywords = [
            'error 404', 'delisted', 'no price data', 'yahoo error',
            'http error', 'possibly delisted', '$161890', 'symbol may be delisted',
            '404:', 'not found', 'no data found', 'http error 404',
            '$161890:', '$005930.ks:', 'period=1y', 'period=5d', '(yah',
            'may be delisted', 'no price data found'
        ]
        if any(keyword in text.lower() for keyword in blocked_keywords):
            return len(text)  # 길이만 반환하고 출력 차단
    return _original_stderr_write(text)

# 전역 함수들 오버라이드 적용
builtins.print = global_silent_print
sys.stdout.write = silent_stdout_write
sys.stderr.write = silent_stderr_write

import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('requests.packages.urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.CRITICAL)

import urllib3
urllib3.disable_warnings()

import yfinance as yf

def test_ultimate_suppression_v2():
    print("🚀 최종 강화된 에러 억제 시스템 테스트 v2")
    print("=" * 60)
    
    # 직접적인 에러 메시지 테스트
    print("🧪 1. 직접 에러 메시지 테스트...")
    test_messages = [
        "HTTP Error 404: Not Found",
        "$161890: possibly delisted; no price data found",
        "$005930.KS: possibly delisted; no price data found (period=1y) (Yahoo",
        "정상 메시지는 출력되어야 함",
        "Yahoo error = No data found"
    ]
    
    for msg in test_messages:
        print(f"테스트: {msg}")
    
    # stdout.write 테스트
    print("\n🧪 2. stdout.write 테스트...")
    sys.stdout.write("정상 stdout 메시지\n")
    sys.stdout.write("HTTP Error 404: 이 메시지는 차단되어야 함\n")
    sys.stdout.write("$161890: possibly delisted - 이것도 차단\n")
    
    # stderr.write 테스트  
    print("\n🧪 3. stderr.write 테스트...")
    sys.stderr.write("정상 stderr 메시지\n")
    sys.stderr.write("HTTP Error 404: stderr 차단 테스트\n")
    
    # yfinance 테스트
    print("\n🧪 4. yfinance 실제 호출 테스트...")
    problem_symbols = [
        "161890.KS",    # 한국콜마
        "INVALID.KS",   # 존재하지 않는 종목
        "NONEXISTENT.KS"  # 존재하지 않는 종목
    ]
    
    for symbol in problem_symbols:
        print(f"  📊 {symbol} 테스트 중...")
        try:
            ticker = yf.Ticker(symbol)
            # 다양한 기간으로 테스트
            for period in ["1y", "5d", "1mo"]:
                data = ticker.history(period=period)
                if data is None or data.empty:
                    print(f"    ✅ {symbol} ({period}): 조용히 처리됨")
                else:
                    print(f"    ⚠️  {symbol} ({period}): 데이터 있음 ({len(data)}일)")
        except Exception as e:
            print(f"    ❌ {symbol}: 예외 - {str(e)[:30]}...")
    
    print("\n" + "=" * 60)
    print("🎉 모든 테스트 완료!")
    print("❗ HTTP Error 404나 delisted 메시지가 없어야 합니다.")
    print("❗ '차단되어야 함' 메시지들이 출력되지 않았으면 성공입니다.")

if __name__ == "__main__":
    test_ultimate_suppression_v2()
    
    # 원본 함수들 복원
    builtins.print = _original_print
    sys.stdout.write = _original_stdout_write
    sys.stderr.write = _original_stderr_write
    print("\n✅ 원본 함수들 복원 완료")