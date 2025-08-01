"""
데이터 수집 및 관리 통합 모듈
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from typing import Optional, List, Dict, Union
import time

# 절대 경로로 변경
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.data_collection.yahoo_finance_collector import YahooFinanceCollector
from config.korean_stocks import KOSPI_TOP_30, TEST_SYMBOLS, get_stock_info

class DataManager:
    """데이터 수집 및 관리 통합 클래스"""
    
    def __init__(self, 
                 output_dir: str = "data/raw",
                 processed_dir: str = "data/processed"):
        self.output_dir = output_dir
        self.processed_dir = processed_dir
        self.logger = self._setup_logger()
        
        # 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        
        # 데이터 수집기 초기화
        self.yahoo_collector = YahooFinanceCollector(output_dir)
    
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
    
    def collect_stock_data(self, 
                          symbols: List[str],
                          period: str = "2y",
                          interval: str = "1d",
                          save_individual: bool = True,
                          save_combined: bool = True) -> Dict[str, pd.DataFrame]:
        """
        여러 종목 데이터 수집 및 저장
        
        Args:
            symbols: 종목 코드 리스트
            period: 데이터 기간
            interval: 데이터 간격
            save_individual: 개별 파일 저장 여부
            save_combined: 통합 파일 저장 여부
            
        Returns:
            종목별 데이터 딕셔너리
        """
        self.logger.info(f"Starting data collection for {len(symbols)} symbols")
        
        # 데이터 수집
        stock_data = self.yahoo_collector.get_multiple_stocks(symbols, period, interval)
        
        if not stock_data:
            self.logger.error("No data collected")
            return {}
        
        # 개별 파일 저장
        if save_individual:
            for symbol, data in stock_data.items():
                filepath = self.yahoo_collector.save_to_csv(data, symbol, f"{period}_{interval}")
                self.logger.info(f"Saved individual data: {filepath}")
        
        # 통합 파일 저장
        if save_combined:
            self._save_combined_data(stock_data, period, interval)
        
        self.logger.info(f"Data collection completed for {len(stock_data)} symbols")
        return stock_data
    
    def _save_combined_data(self, stock_data: Dict[str, pd.DataFrame], period: str, interval: str):
        """통합 데이터 파일 저장"""
        try:
            # 모든 데이터를 하나로 합치기
            combined_data = pd.concat(stock_data.values(), ignore_index=True)
            
            # 종목 정보 추가
            combined_data['stock_name'] = combined_data['symbol'].apply(
                lambda x: get_stock_info(x).get('name', 'Unknown')
            )
            combined_data['sector'] = combined_data['symbol'].apply(
                lambda x: get_stock_info(x).get('sector', 'Unknown')
            )
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"combined_stocks_{timestamp}_{period}_{interval}.csv"
            filepath = os.path.join(self.processed_dir, filename)
            
            # 저장
            combined_data.to_csv(filepath, index=False, encoding='utf-8')
            self.logger.info(f"Combined data saved: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving combined data: {str(e)}")
    
    def get_latest_data(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """최근 N일 데이터 조회"""
        try:
            data = self.yahoo_collector.get_stock_data(symbol, period=f"{days}d")
            if data is not None:
                self.logger.info(f"Retrieved {len(data)} days of data for {symbol}")
            return data
        except Exception as e:
            self.logger.error(f"Error getting latest data for {symbol}: {str(e)}")
            return None
    
    def get_market_overview(self, symbols: List[str] = None) -> pd.DataFrame:
        """시장 현황 조회"""
        if symbols is None:
            symbols = TEST_SYMBOLS
        
        overview_data = []
        
        for symbol in symbols:
            try:
                current_price = self.yahoo_collector.get_current_price(symbol)
                if current_price:
                    stock_info = get_stock_info(symbol)
                    
                    overview_data.append({
                        'symbol': symbol,
                        'name': stock_info.get('name', 'Unknown'),
                        'sector': stock_info.get('sector', 'Unknown'),
                        'current_price': current_price['current_price'],
                        'previous_close': current_price['previous_close'],
                        'change': current_price['current_price'] - current_price['previous_close'] if current_price['current_price'] and current_price['previous_close'] else 0,
                        'change_percent': ((current_price['current_price'] - current_price['previous_close']) / current_price['previous_close'] * 100) if current_price['current_price'] and current_price['previous_close'] else 0,
                        'volume': current_price['volume'],
                        'market_cap': current_price['market_cap'],
                    })
                
                time.sleep(0.5)  # API 호출 제한
                
            except Exception as e:
                self.logger.error(f"Error getting overview for {symbol}: {str(e)}")
                continue
        
        if overview_data:
            df = pd.DataFrame(overview_data)
            
            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"market_overview_{timestamp}.csv"
            filepath = os.path.join(self.processed_dir, filename)
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            self.logger.info(f"Market overview saved: {filepath}")
            return df
        else:
            self.logger.warning("No market overview data collected")
            return pd.DataFrame()
    
    def update_stock_database(self, symbols: List[str] = None, days: int = 5):
        """주식 데이터베이스 업데이트 (최근 N일)"""
        if symbols is None:
            symbols = list(KOSPI_TOP_30.keys())
        
        self.logger.info(f"Updating database for {len(symbols)} symbols (last {days} days)")
        
        updated_count = 0
        for symbol in symbols:
            try:
                # 최근 데이터 가져오기
                data = self.get_latest_data(symbol, days)
                if data is not None:
                    # 개별 파일로 저장
                    timestamp = datetime.now().strftime("%Y%m%d")
                    filename = f"{symbol}_update_{timestamp}.csv"
                    filepath = os.path.join(self.output_dir, filename)
                    data.to_csv(filepath, index=False, encoding='utf-8')
                    updated_count += 1
                
                time.sleep(0.5)  # API 호출 제한
                
            except Exception as e:
                self.logger.error(f"Error updating {symbol}: {str(e)}")
                continue
        
        self.logger.info(f"Database update completed: {updated_count}/{len(symbols)} symbols updated")
        return updated_count
    
    def get_data_summary(self) -> Dict:
        """수집된 데이터 요약 정보"""
        try:
            raw_files = os.listdir(self.output_dir)
            processed_files = os.listdir(self.processed_dir)
            
            summary = {
                'raw_files_count': len([f for f in raw_files if f.endswith('.csv')]),
                'processed_files_count': len([f for f in processed_files if f.endswith('.csv')]),
                'latest_raw_file': max([f for f in raw_files if f.endswith('.csv')], default='None', key=lambda x: os.path.getctime(os.path.join(self.output_dir, x))),
                'latest_processed_file': max([f for f in processed_files if f.endswith('.csv')], default='None', key=lambda x: os.path.getctime(os.path.join(self.processed_dir, x))),
                'total_size_mb': sum(os.path.getsize(os.path.join(self.output_dir, f)) for f in raw_files) / (1024 * 1024),
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting data summary: {str(e)}")
            return {}


def main():
    """메인 실행 함수"""
    print("=== 데이터 관리자 테스트 ===")
    
    # 데이터 관리자 초기화
    data_manager = DataManager()
    
    # 1. 테스트 종목 데이터 수집
    print(f"\n1. 테스트 종목 데이터 수집 중... ({len(TEST_SYMBOLS)}개 종목)")
    stock_data = data_manager.collect_stock_data(
        symbols=TEST_SYMBOLS,
        period="6mo",
        interval="1d"
    )
    
    if stock_data:
        print(f"   수집 완료: {len(stock_data)}개 종목")
        for symbol, data in stock_data.items():
            stock_info = get_stock_info(symbol)
            print(f"   - {symbol} ({stock_info.get('name', 'Unknown')}): {len(data)}개 레코드")
    
    # 2. 시장 현황 조회
    print(f"\n2. 시장 현황 조회 중...")
    market_overview = data_manager.get_market_overview(TEST_SYMBOLS)
    
    if not market_overview.empty:
        print(f"   현황 수집 완료: {len(market_overview)}개 종목")
        print("\n   주요 종목 현황:")
        for _, row in market_overview.iterrows():
            print(f"   - {row['name']}: {row['current_price']:,.0f}원 ({row['change_percent']:+.1f}%)")
    
    # 3. 데이터 요약 정보
    print(f"\n3. 데이터 요약 정보")
    summary = data_manager.get_data_summary()
    if summary:
        print(f"   원본 파일: {summary['raw_files_count']}개")
        print(f"   처리된 파일: {summary['processed_files_count']}개") 
        print(f"   총 용량: {summary['total_size_mb']:.1f}MB")
        print(f"   최신 파일: {summary['latest_raw_file']}")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()