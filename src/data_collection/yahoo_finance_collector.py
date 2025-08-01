"""
Yahoo Finance API를 이용한 주가 데이터 수집기
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from typing import Optional, List, Dict
import time

class YahooFinanceCollector:
    """Yahoo Finance API 데이터 수집기"""
    
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = output_dir
        self.logger = self._setup_logger()
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
    
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
    
    def get_stock_data(self, 
                      symbol: str, 
                      period: str = "2y",
                      interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        단일 종목 주가 데이터 수집
        
        Args:
            symbol: 종목 코드 (예: '005930.KS' for 삼성전자)
            period: 기간 ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            interval: 간격 ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        
        Returns:
            주가 데이터 DataFrame 또는 None
        """
        try:
            self.logger.info(f"Fetching data for {symbol}")
            
            # Yahoo Finance 객체 생성
            stock = yf.Ticker(symbol)
            
            # 주가 데이터 다운로드
            data = stock.history(period=period, interval=interval)
            
            if data.empty:
                self.logger.warning(f"No data found for {symbol}")
                return None
            
            # 인덱스를 날짜 컬럼으로 변환
            data.reset_index(inplace=True)
            
            # 컬럼명 정리
            data.columns = [col.replace(' ', '_').lower() for col in data.columns]
            
            # 종목 코드 추가
            data['symbol'] = symbol
            
            self.logger.info(f"Successfully fetched {len(data)} records for {symbol}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """
        실시간 주가 정보 조회
        
        Args:
            symbol: 종목 코드
            
        Returns:
            현재 주가 정보 딕셔너리
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            current_data = {
                'symbol': symbol,
                'current_price': info.get('currentPrice'),
                'previous_close': info.get('previousClose'),
                'open': info.get('open'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'volume': info.get('volume'),
                'market_cap': info.get('marketCap'),
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"Current price for {symbol}: {current_data['current_price']}")
            return current_data
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def get_multiple_stocks(self, 
                           symbols: List[str], 
                           period: str = "2y",
                           interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        여러 종목 데이터 수집
        
        Args:
            symbols: 종목 코드 리스트
            period: 기간
            interval: 간격
            
        Returns:
            종목별 데이터 딕셔너리
        """
        results = {}
        
        for symbol in symbols:
            self.logger.info(f"Processing {symbol}...")
            
            data = self.get_stock_data(symbol, period, interval)
            if data is not None:
                results[symbol] = data
            
            # API 호출 제한을 위한 지연
            time.sleep(0.5)
        
        self.logger.info(f"Successfully collected data for {len(results)} out of {len(symbols)} symbols")
        return results
    
    def save_to_csv(self, data: pd.DataFrame, symbol: str, suffix: str = "") -> str:
        """
        데이터를 CSV 파일로 저장
        
        Args:
            data: 저장할 데이터
            symbol: 종목 코드
            suffix: 파일명 접미사
            
        Returns:
            저장된 파일 경로
        """
        try:
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{symbol}_{timestamp}"
            if suffix:
                filename += f"_{suffix}"
            filename += ".csv"
            
            filepath = os.path.join(self.output_dir, filename)
            
            # CSV 저장
            data.to_csv(filepath, index=False, encoding='utf-8')
            
            self.logger.info(f"Data saved to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving data to CSV: {str(e)}")
            return ""
    
    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """
        기업 정보 조회
        
        Args:
            symbol: 종목 코드
            
        Returns:
            기업 정보 딕셔너리
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            company_info = {
                'symbol': symbol,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'employees': info.get('fullTimeEmployees'),
                'website': info.get('website', ''),
                'business_summary': info.get('businessSummary', '')
            }
            
            return company_info
            
        except Exception as e:
            self.logger.error(f"Error getting company info for {symbol}: {str(e)}")
            return None


def main():
    """메인 실행 함수"""
    # 데이터 수집기 초기화
    collector = YahooFinanceCollector()
    
    # 테스트용 종목 (삼성전자)
    test_symbol = "005930.KS"
    
    print("=== Yahoo Finance 데이터 수집 테스트 ===")
    
    # 1. 주가 데이터 수집
    print(f"\n1. {test_symbol} 주가 데이터 수집 중...")
    stock_data = collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None:
        print(f"   데이터 수집 완료: {len(stock_data)}개 레코드")
        print(f"   기간: {stock_data['date'].iloc[0]} ~ {stock_data['date'].iloc[-1]}")
        print(f"   최근 종가: {stock_data['close'].iloc[-1]:,.0f}원")
        
        # CSV 저장
        filepath = collector.save_to_csv(stock_data, test_symbol, "daily")
        print(f"   저장 완료: {filepath}")
    
    # 2. 실시간 주가 조회
    print(f"\n2. {test_symbol} 실시간 주가 조회 중...")
    current_price = collector.get_current_price(test_symbol)
    
    if current_price:
        print(f"   현재가: {current_price['current_price']:,}원")
        print(f"   전일대비: {current_price['previous_close']:,}원")
        print(f"   거래량: {current_price['volume']:,}주")
    
    # 3. 기업 정보 조회
    print(f"\n3. {test_symbol} 기업 정보 조회 중...")
    company_info = collector.get_company_info(test_symbol)
    
    if company_info:
        print(f"   회사명: {company_info['company_name']}")
        print(f"   섹터: {company_info['sector']}")
        print(f"   시가총액: {company_info['market_cap']:,}원")
        print(f"   PER: {company_info['pe_ratio']}")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()