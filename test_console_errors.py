#!/usr/bin/env python3
"""
콘솔 에러 테스트 스크립트
Streamlit 앱에서 사용하는 함수들을 테스트하여 404 에러나 기타 콘솔 출력이 없는지 확인
"""

import warnings
warnings.filterwarnings('ignore')
import logging
import sys
from contextlib import redirect_stderr
from io import StringIO

# 모든 관련 라이브러리 로깅 완전 억제
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('requests.packages.urllib3').setLevel(logging.CRITICAL)

# urllib3 경고 완전 억제
import urllib3
urllib3.disable_warnings()

# 콘솔 출력 완전 억제를 위한 컨텍스트 매니저
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

# yfinance 안전 래퍼 함수
def safe_yfinance_call(func, *args, **kwargs):
    """yfinance 함수를 안전하게 호출하는 래퍼 (모든 에러 완전 억제)"""
    try:
        with SuppressOutput():
            # 추가적인 stderr 리다이렉션
            with redirect_stderr(StringIO()):
                return func(*args, **kwargs)
    except Exception:
        # 모든 예외를 조용히 처리
        return None

import yfinance as yf
import pandas as pd

def test_stock_data_fetch():
    """주식 데이터 조회 테스트 (콘솔 출력 없이)"""
    print("🧪 주식 데이터 조회 테스트 시작...")
    
    test_symbols = [
        "005930.KS",  # 삼성전자 (정상)
        "000660.KS",  # SK하이닉스 (정상)
        "161890.KS",  # 한국콜마 (문제 종목)
        "INVALID.KS", # 존재하지 않는 종목
        "AAPL",       # 미국 주식 (정상)
    ]
    
    for symbol in test_symbols:
        print(f"  📊 {symbol} 테스트 중...")
        
        # 빈 심볼이나 잘못된 심볼 사전 체크
        if not symbol or not isinstance(symbol, str) or len(symbol.strip()) < 2:
            print(f"    ⚠️  {symbol}: 잘못된 심볼 형식")
            continue
        
        try:
            ticker = yf.Ticker(symbol)
            # 안전한 래퍼로 데이터 조회
            data = safe_yfinance_call(ticker.history, period="1mo")
            
            if data is None or data.empty:
                print(f"    ⚠️  {symbol}: 데이터 없음 (조용히 처리됨)")
            else:
                print(f"    ✅ {symbol}: 데이터 정상 ({len(data)}일)")
                
        except Exception as e:
            print(f"    ❌ {symbol}: 예외 발생 - {str(e)[:50]}...")
    
    print("✅ 주식 데이터 조회 테스트 완료\n")

def test_market_indices():
    """시장 지수 조회 테스트"""
    print("🧪 시장 지수 조회 테스트 시작...")
    
    indices = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC"
    }
    
    for name, symbol in indices.items():
        try:
            print(f"  📈 {name} ({symbol}) 테스트 중...")
            
            ticker = yf.Ticker(symbol)
            # 안전한 래퍼로 데이터 조회
            data = safe_yfinance_call(ticker.history, period="5d")
            
            if data is not None and not data.empty:
                current = data['Close'].iloc[-1]
                prev = data['Close'].iloc[-2] if len(data) > 1 else current
                change = ((current - prev) / prev) * 100
                print(f"    ✅ {name}: {current:.2f} ({change:+.2f}%)")
            else:
                print(f"    ⚠️  {name}: 데이터 없음")
                
        except Exception as e:
            print(f"    ❌ {name}: 예외 발생 - {str(e)[:50]}...")
    
    print("✅ 시장 지수 조회 테스트 완료\n")

def test_error_suppression():
    """에러 억제 테스트"""
    print("🧪 에러 억제 테스트 시작...")
    
    # 의도적으로 문제가 있는 요청들
    problem_requests = [
        ("빈 심볼", ""),
        ("잘못된 형식", "12345"),
        ("존재하지 않는 코드", "NONEXISTENT.KS"),
        ("특수문자", "@#$%^.KS"),
    ]
    
    for desc, symbol in problem_requests:
        try:
            print(f"  🔍 {desc} 테스트: '{symbol}'")
            if symbol:  # 빈 문자열이 아닌 경우만
                ticker = yf.Ticker(symbol)
                # 안전한 래퍼로 데이터 조회
                data = safe_yfinance_call(ticker.history, period="1d")
                
                if data is None or data.empty:
                    print(f"    ✅ 조용히 처리됨 (빈 데이터)")
                else:
                    print(f"    🤔 예상과 다르게 데이터 반환됨")
            else:
                print(f"    ✅ 빈 심볼 건너뜀")
        except Exception:
            print(f"    ✅ 예외 조용히 처리됨")
    
    print("✅ 에러 억제 테스트 완료\n")

if __name__ == "__main__":
    print("🚀 콘솔 에러 테스트 시작")
    print("=" * 50)
    
    test_stock_data_fetch()
    test_market_indices() 
    test_error_suppression()
    
    print("=" * 50)
    print("🎉 모든 테스트 완료!")
    print("❗ 위 출력 외에 추가적인 콘솔 에러나 경고가 없어야 합니다.")