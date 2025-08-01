"""
시장 데이터 서비스
데이터베이스와 연동된 시장 데이터 수집 및 관리 서비스
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import yfinance as yf
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.database.database_manager import DatabaseManager

class MarketDataService:
    """데이터베이스 연동 시장 데이터 서비스"""
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        """
        초기화
        
        Args:
            db_path: 데이터베이스 경로
        """
        self.db_manager = DatabaseManager(db_path)
        self.logger = self._setup_logger()
        
        self.logger.info("시장 데이터 서비스 초기화 완료")
    
    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _collect_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """
        yfinance를 사용한 주가 데이터 수집
        
        Args:
            symbol: 종목 코드
            period: 수집 기간
            
        Returns:
            주가 데이터 DataFrame
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if not data.empty:
                # 인덱스를 날짜로 리셋
                data = data.reset_index()
                return data
            else:
                self.logger.warning(f"데이터 수집 실패: {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"데이터 수집 오류 ({symbol}): {str(e)}")
            return pd.DataFrame()
    
    def collect_and_store_data(self, symbols: List[str], period: str = "1y",
                              force_update: bool = False) -> Dict[str, bool]:
        """
        종목 데이터 수집 및 데이터베이스 저장
        
        Args:
            symbols: 종목 코드 리스트
            period: 수집 기간
            force_update: 강제 업데이트 여부
            
        Returns:
            종목별 저장 성공 여부
        """
        results = {}
        
        for symbol in symbols:
            try:
                self.logger.info(f"데이터 수집 시작: {symbol}")
                
                # 기존 데이터 확인 (강제 업데이트가 아닌 경우)
                if not force_update:
                    existing_data = self.db_manager.get_stock_prices(symbol)
                    if not existing_data.empty:
                        latest_date = existing_data.index.max()
                        days_since_update = (datetime.now().date() - latest_date.date()).days
                        
                        if days_since_update <= 1:  # 1일 이내 데이터가 있으면 스킵
                            self.logger.info(f"최신 데이터 존재로 스킵: {symbol} (최근 업데이트: {latest_date.date()})")
                            results[symbol] = True
                            continue
                
                # 새 데이터 수집
                price_data = self._collect_stock_data(symbol, period)
                
                if not price_data.empty:
                    # 데이터베이스에 저장
                    success = self.db_manager.save_stock_prices(symbol, price_data)
                    results[symbol] = success
                    
                    if success:
                        self.logger.info(f"데이터 저장 완료: {symbol} ({len(price_data)}개 레코드)")
                    else:
                        self.logger.error(f"데이터 저장 실패: {symbol}")
                else:
                    self.logger.warning(f"데이터 수집 실패: {symbol}")
                    results[symbol] = False
                    
            except Exception as e:
                self.logger.error(f"데이터 처리 오류 ({symbol}): {str(e)}")
                results[symbol] = False
        
        return results
    
    def get_cached_data(self, symbol: str, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       fallback_to_api: bool = True) -> pd.DataFrame:
        """
        캐시된 데이터 조회 (필요시 API 호출)
        
        Args:
            symbol: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            fallback_to_api: API 대체 호출 여부
            
        Returns:
            주가 데이터
        """
        try:
            # 먼저 데이터베이스에서 조회
            cached_data = self.db_manager.get_stock_prices(symbol, start_date, end_date)
            
            if not cached_data.empty:
                self.logger.debug(f"캐시된 데이터 반환: {symbol} ({len(cached_data)}개 레코드)")
                return cached_data
            
            # 캐시된 데이터가 없고 API 대체 호출이 허용된 경우
            if fallback_to_api:
                self.logger.info(f"캐시 없음, API에서 데이터 수집: {symbol}")
                
                # 기간 설정
                if start_date and end_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    period_days = (end_dt - start_dt).days
                    
                    # 기간에 따른 period 설정
                    if period_days <= 30:
                        period = "1mo"
                    elif period_days <= 90:
                        period = "3mo"
                    elif period_days <= 365:
                        period = "1y"
                    else:
                        period = "2y"
                else:
                    period = "1y"
                
                # API에서 데이터 수집
                api_data = self._collect_stock_data(symbol, period)
                
                if not api_data.empty:
                    # 데이터베이스에 저장
                    self.db_manager.save_stock_prices(symbol, api_data)
                    
                    # 요청된 기간에 맞게 필터링
                    if start_date:
                        api_data = api_data[api_data.index >= start_date]
                    if end_date:
                        api_data = api_data[api_data.index <= end_date]
                    
                    return api_data
            
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"데이터 조회 오류 ({symbol}): {str(e)}")
            return pd.DataFrame()
    
    def get_multiple_symbols_data(self, symbols: List[str],
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        다중 종목 데이터 조회
        
        Args:
            symbols: 종목 코드 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            종목별 데이터 딕셔너리
        """
        data_dict = {}
        
        for symbol in symbols:
            data = self.get_cached_data(symbol, start_date, end_date)
            if not data.empty:
                data_dict[symbol] = data
            else:
                self.logger.warning(f"데이터 없음: {symbol}")
        
        return data_dict
    
    def update_latest_data(self, symbols: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        최신 데이터 업데이트
        
        Args:
            symbols: 업데이트할 종목 리스트 (None이면 전체)
            
        Returns:
            업데이트 결과
        """
        if symbols is None:
            symbols = self.db_manager.get_available_symbols()
        
        if not symbols:
            self.logger.warning("업데이트할 종목이 없습니다.")
            return {}
        
        self.logger.info(f"최신 데이터 업데이트 시작: {len(symbols)}개 종목")
        
        # 최근 5일 데이터만 업데이트 (효율성)
        results = self.collect_and_store_data(symbols, period="5d", force_update=True)
        
        success_count = sum(results.values())
        self.logger.info(f"데이터 업데이트 완료: {success_count}/{len(symbols)}개 성공")
        
        return results
    
    def get_data_status(self) -> Dict[str, Any]:
        """
        데이터 상태 정보 조회
        
        Returns:
            데이터 상태 정보
        """
        try:
            symbols = self.db_manager.get_available_symbols()
            
            if not symbols:
                return {
                    'total_symbols': 0,
                    'status': 'empty',
                    'message': '저장된 데이터가 없습니다.'
                }
            
            # 각 종목별 최신 데이터 날짜 확인
            latest_dates = {}
            outdated_symbols = []
            
            for symbol in symbols[:10]:  # 처음 10개만 체크 (성능상)
                data = self.db_manager.get_stock_prices(symbol)
                if not data.empty:
                    latest_date = data.index.max().date()
                    latest_dates[symbol] = latest_date
                    
                    # 1일 이상 오래된 데이터 체크
                    if (datetime.now().date() - latest_date).days > 1:
                        outdated_symbols.append(symbol)
            
            return {
                'total_symbols': len(symbols),
                'sampled_symbols': len(latest_dates),
                'outdated_symbols': len(outdated_symbols),
                'latest_dates': latest_dates,
                'needs_update': outdated_symbols,
                'status': 'outdated' if outdated_symbols else 'current'
            }
            
        except Exception as e:
            self.logger.error(f"데이터 상태 조회 오류: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def cleanup_old_data(self, days_to_keep: int = 730) -> bool:
        """
        오래된 데이터 정리 (2년 이상)
        
        Args:
            days_to_keep: 보관할 일수
            
        Returns:
            정리 성공 여부
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # 오래된 데이터 삭제
                cursor.execute('''
                    DELETE FROM stock_prices 
                    WHERE date < ?
                ''', (cutoff_date,))
                
                deleted_rows = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"오래된 데이터 정리 완료: {deleted_rows}개 레코드 삭제")
                return True
                
        except Exception as e:
            self.logger.error(f"데이터 정리 오류: {str(e)}")
            return False


def main():
    """테스트 실행"""
    print("=== 시장 데이터 서비스 테스트 ===")
    
    # 시장 데이터 서비스 초기화
    market_service = MarketDataService("test_market_data.db")
    
    # 테스트용 종목
    test_symbols = ["005930.KS", "000660.KS", "035420.KS"]
    
    print(f"\n1. 데이터 수집 및 저장 테스트")
    
    try:
        # 데이터 수집 및 저장
        results = market_service.collect_and_store_data(test_symbols, period="6mo")
        
        success_count = sum(results.values())
        print(f"   ✅ 데이터 수집 완료: {success_count}/{len(test_symbols)}개 성공")
        
        for symbol, success in results.items():
            status = "✅" if success else "❌"
            print(f"     {status} {symbol}")
        
    except Exception as e:
        print(f"   ❌ 데이터 수집 오류: {str(e)}")
    
    print(f"\n2. 캐시된 데이터 조회 테스트")
    
    try:
        # 캐시된 데이터 조회
        for symbol in test_symbols[:2]:  # 처음 2개만 테스트
            cached_data = market_service.get_cached_data(symbol, fallback_to_api=False)
            
            if not cached_data.empty:
                print(f"   ✅ {symbol}: {len(cached_data)}개 레코드")
                print(f"     기간: {cached_data.index.min().date()} ~ {cached_data.index.max().date()}")
            else:
                print(f"   ❌ {symbol}: 캐시된 데이터 없음")
        
    except Exception as e:
        print(f"   ❌ 캐시 조회 오류: {str(e)}")
    
    print(f"\n3. 다중 종목 데이터 조회 테스트")
    
    try:
        # 다중 종목 데이터 조회
        multi_data = market_service.get_multiple_symbols_data(test_symbols)
        
        print(f"   ✅ 다중 데이터 조회 완료: {len(multi_data)}개 종목")
        
        for symbol, data in multi_data.items():
            print(f"     • {symbol}: {len(data)}개 레코드")
        
    except Exception as e:
        print(f"   ❌ 다중 데이터 조회 오류: {str(e)}")
    
    print(f"\n4. 데이터 상태 확인 테스트")
    
    try:
        # 데이터 상태 확인
        status = market_service.get_data_status()
        
        print(f"   ✅ 데이터 상태 확인 완료")
        print(f"     총 종목 수: {status.get('total_symbols', 0)}")
        print(f"     상태: {status.get('status', 'unknown')}")
        
        if 'latest_dates' in status:
            print(f"     최신 날짜 샘플:")
            for symbol, date in list(status['latest_dates'].items())[:3]:
                print(f"       • {symbol}: {date}")
        
    except Exception as e:
        print(f"   ❌ 데이터 상태 확인 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()