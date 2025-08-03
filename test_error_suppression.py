#!/usr/bin/env python3
"""
강화된 에러 억제 시스템 테스트 - HTTP 404 에러 완전 억제 확인
"""

import warnings
warnings.filterwarnings('ignore')
import logging
import sys
import os

# 모든 yfinance 관련 로깅 완전 억제
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('requests.packages.urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.CRITICAL)

# urllib3 경고 억제
import urllib3
urllib3.disable_warnings()

# 환경 변수 설정으로 네트워크 타임아웃 단축
os.environ['REQUESTS_TIMEOUT'] = '5'
os.environ['URLLIB3_TIMEOUT'] = '5'

# yfinance에서 나오는 모든 출력 억제를 위한 강화된 컨텍스트 매니저
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

class SilentYFinance:
    def __enter__(self):
        # stdout과 stderr를 모두 무효화
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._devnull = open(os.devnull, 'w')
        
        # 둘 다 devnull로 리다이렉트
        sys.stdout = self._devnull
        sys.stderr = self._devnull
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 원래 상태로 복원
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._devnull.close()

# 완전한 에러 억제를 위한 안전한 yfinance 래퍼
def safe_yfinance_call(func, *args, **kwargs):
    """yfinance 함수를 완전히 안전하게 호출하는 래퍼"""
    try:
        with SilentYFinance():
            # 추가적인 stdout/stderr 리다이렉션
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                return func(*args, **kwargs)
    except Exception:
        return None

import yfinance as yf

def test_problematic_stocks():
    """문제가 되는 종목들로 HTTP 404 에러 억제 테스트"""
    print("🧪 HTTP 404 에러 억제 테스트 시작...")
    print("=" * 50)
    
    # 404 에러나 delisted 에러가 발생할 수 있는 종목들
    problem_symbols = [
        "161890.KS",    # 한국콜마 (이전에 문제됐던 종목)
        "INVALID.KS",   # 존재하지 않는 종목
        "DELISTED.KS",  # 상장폐지 테스트
        "000000.KS",    # 잘못된 코드
        "999999.KS",    # 존재하지 않는 코드
        "ERROR404.KS"   # 404 에러 유발 테스트
    ]
    
    success_count = 0
    
    for i, symbol in enumerate(problem_symbols, 1):
        print(f"  {i}. 📊 {symbol} 테스트 중...")
        
        try:
            ticker = yf.Ticker(symbol)
            
            # 안전한 래퍼로 데이터 조회 (5일)
            data_5d = safe_yfinance_call(ticker.history, period="5d")
            
            # 안전한 래퍼로 데이터 조회 (1개월)
            data_1mo = safe_yfinance_call(ticker.history, period="1mo")
            
            # 안전한 래퍼로 정보 조회
            info = safe_yfinance_call(lambda: ticker.info)
            
            # 결과 확인
            if data_5d is None or data_5d.empty:
                if data_1mo is None or data_1mo.empty:
                    print(f"     ✅ {symbol}: 조용히 처리됨 (데이터 없음)")
                    success_count += 1
                else:
                    print(f"     ⚠️  {symbol}: 1개월 데이터만 있음 ({len(data_1mo)}일)")
                    success_count += 1
            else:
                print(f"     🤔 {symbol}: 예상과 다르게 데이터 반환됨 ({len(data_5d)}일)")
                success_count += 1
                
        except Exception as e:
            print(f"     ❌ {symbol}: 예외 발생 - {str(e)[:30]}...")
    
    print("=" * 50)
    print(f"🎉 테스트 완료: {success_count}/{len(problem_symbols)} 성공")
    print("❗ 위 출력에서 'HTTP Error 404', 'possibly delisted', 'No data found' 등의")
    print("   에러 메시지가 없으면 에러 억제가 성공한 것입니다.")
    print()

def test_normal_stocks():
    """정상 종목들로 데이터 조회 테스트"""
    print("🧪 정상 종목 데이터 조회 테스트...")
    print("=" * 30)
    
    normal_symbols = [
        "005930.KS",    # 삼성전자
        "000660.KS",    # SK하이닉스
        "AAPL"          # 애플 (미국 주식)
    ]
    
    for symbol in normal_symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = safe_yfinance_call(ticker.history, period="5d")
            
            if data is not None and not data.empty:
                latest_price = data['Close'].iloc[-1]
                print(f"  ✅ {symbol}: {latest_price:.2f} ({len(data)}일 데이터)")
            else:
                print(f"  ⚠️  {symbol}: 데이터 조회 실패")
        except Exception as e:
            print(f"  ❌ {symbol}: 예외 - {str(e)[:30]}...")
    
    print("=" * 30)
    print()

if __name__ == "__main__":
    print("🚀 강화된 HTTP 404 에러 억제 시스템 테스트")
    print()
    
    test_problematic_stocks()
    test_normal_stocks()
    
    print("🎯 테스트 결과:")
    print("   - HTTP Error 404, possibly delisted 등의 에러 메시지가 출력되지 않으면 성공")
    print("   - 모든 요청이 조용히 처리되어야 함")
    print("   - 정상 종목은 데이터가 정상적으로 조회되어야 함")