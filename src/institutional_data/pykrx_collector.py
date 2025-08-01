"""
PyKRX 기반 외국인·기관 매매 데이터 수집기
KRX 공식 데이터를 활용한 투자자별 거래 동향 분석
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import sys
import os

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("PyKRX가 설치되지 않았습니다. pip install pykrx로 설치해주세요.")

class PyKRXInstitutionalCollector:
    """PyKRX 기반 외국인·기관 매매 데이터 수집기"""
    
    def __init__(self):
        """초기화"""
        self.logger = self._setup_logger()
        
        if not PYKRX_AVAILABLE:
            self.logger.error("PyKRX 라이브러리가 필요합니다. pip install pykrx로 설치해주세요.")
            return
        
        self.logger.info("PyKRX 외국인·기관 데이터 수집기 초기화 완료")
        
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
    
    def get_foreign_ownership_data(self, 
                                 date: str, 
                                 market: str = "KOSPI") -> pd.DataFrame:
        """
        외국인 보유 현황 데이터 수집
        
        Args:
            date: 조회일자 (YYYYMMDD)
            market: 시장구분 (KOSPI, KOSDAQ)
            
        Returns:
            외국인 보유 현황 DataFrame
        """
        try:
            if not PYKRX_AVAILABLE:
                return pd.DataFrame()
            
            self.logger.info(f"외국인 보유현황 수집 시작: {date} ({market})")
            
            # 외국인 보유현황 조회
            foreign_holdings = stock.get_market_cap_by_date(date, date, market)
            
            # 외국인 지분율 데이터 추가
            foreign_exhaustion = stock.get_exhaustion_rates_of_foreign_investment(date, market)
            
            if not foreign_exhaustion.empty:
                # 데이터 병합
                foreign_data = foreign_holdings.merge(
                    foreign_exhaustion, 
                    left_index=True, 
                    right_index=True, 
                    how='left'
                )
            else:
                foreign_data = foreign_holdings
            
            # 메타데이터 추가
            foreign_data['date'] = pd.to_datetime(date)
            foreign_data['market'] = market
            foreign_data['data_source'] = 'PyKRX'
            
            self.logger.info(f"외국인 보유현황 수집 완료: {len(foreign_data)}개 종목")
            return foreign_data
            
        except Exception as e:
            self.logger.error(f"외국인 보유현황 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_trading_by_investor_type(self, 
                                   start_date: str, 
                                   end_date: str, 
                                   symbol: str) -> pd.DataFrame:
        """
        투자자별 거래 동향 데이터 수집
        
        Args:
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)  
            symbol: 종목코드 (6자리)
            
        Returns:
            투자자별 거래 동향 DataFrame
        """
        try:
            if not PYKRX_AVAILABLE:
                return pd.DataFrame()
            
            self.logger.info(f"투자자별 거래동향 수집: {symbol} ({start_date}~{end_date})")
            
            # 투자자별 거래대금 수집
            trading_value = stock.get_market_trading_value_by_investor(
                start_date, end_date, symbol
            )
            
            # 투자자별 거래량 수집
            trading_volume = stock.get_market_trading_volume_by_date(
                start_date, end_date, symbol
            )
            
            if trading_value.empty or trading_volume.empty:
                self.logger.warning(f"거래 데이터 없음: {symbol}")
                return pd.DataFrame()
            
            # 데이터 정리 및 병합
            result = self._process_trading_data(trading_value, trading_volume, symbol)
            
            self.logger.info(f"투자자별 거래동향 수집 완료: {len(result)}일")
            return result
            
        except Exception as e:
            self.logger.error(f"투자자별 거래동향 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def _process_trading_data(self, 
                            trading_value: pd.DataFrame, 
                            trading_volume: pd.DataFrame, 
                            symbol: str) -> pd.DataFrame:
        """거래 데이터 처리 및 정리"""
        try:
            result = []
            
            for date in trading_value.index:
                # 날짜 처리 수정
                try:
                    parsed_date = pd.to_datetime(str(date))
                except:
                    # 날짜 파싱 실패 시 현재 날짜 사용
                    parsed_date = pd.to_datetime('today')
                
                daily_data = {
                    'date': parsed_date,
                    'symbol': symbol,
                    'data_source': 'PyKRX'
                }
                
                # 거래대금 데이터 (억원 단위)
                if '금융투자' in trading_value.columns:
                    daily_data['institutional_value'] = trading_value.loc[date, '금융투자']
                if '보험' in trading_value.columns:
                    daily_data['insurance_value'] = trading_value.loc[date, '보험']
                if '투신' in trading_value.columns:
                    daily_data['trust_value'] = trading_value.loc[date, '투신']
                if '사모' in trading_value.columns:
                    daily_data['private_fund_value'] = trading_value.loc[date, '사모']
                if '은행' in trading_value.columns:
                    daily_data['bank_value'] = trading_value.loc[date, '은행']
                if '기타법인' in trading_value.columns:
                    daily_data['other_corp_value'] = trading_value.loc[date, '기타법인']
                if '개인' in trading_value.columns:
                    daily_data['individual_value'] = trading_value.loc[date, '개인']
                if '외국인계' in trading_value.columns:
                    daily_data['foreign_value'] = trading_value.loc[date, '외국인계']
                elif '외국인' in trading_value.columns:
                    daily_data['foreign_value'] = trading_value.loc[date, '외국인']
                
                # 기관 전체 거래대금 계산
                institutional_total = 0
                for key in ['institutional_value', 'insurance_value', 'trust_value', 
                           'private_fund_value', 'bank_value', 'other_corp_value']:
                    if key in daily_data:
                        institutional_total += daily_data[key]
                daily_data['institutional_total_value'] = institutional_total
                
                # 거래량 데이터 (주식 수)
                if date in trading_volume.index:
                    daily_data['total_volume'] = trading_volume.loc[date, '거래량']
                
                result.append(daily_data)
            
            return pd.DataFrame(result)
            
        except Exception as e:
            self.logger.error(f"거래 데이터 처리 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_market_summary_by_investor(self, 
                                     date: str, 
                                     market: str = "ALL") -> pd.DataFrame:
        """
        시장 전체 투자자별 거래 요약
        
        Args:
            date: 조회일자 (YYYYMMDD)
            market: 시장구분 (KOSPI, KOSDAQ, ALL)
            
        Returns:
            시장별 투자자 거래 요약 DataFrame
        """
        try:
            if not PYKRX_AVAILABLE:
                return pd.DataFrame()
            
            self.logger.info(f"시장 투자자별 거래요약 수집: {date} ({market})")
            
            markets_to_check = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]
            all_data = []
            
            for mkt in markets_to_check:
                try:
                    # 투자자별 거래대금 (시장 전체)
                    market_trading = stock.get_market_trading_value_by_investor(
                        date, date, mkt
                    )
                    
                    if not market_trading.empty:
                        market_data = {
                            'date': pd.to_datetime(date),
                            'market': mkt,
                            'data_source': 'PyKRX'
                        }
                        
                        # 각 투자자 유형별 데이터 추가
                        for col in market_trading.columns:
                            if col in ['금융투자', '보험', '투신', '사모', '은행', 
                                     '기타법인', '개인', '외국인계', '외국인']:
                                market_data[f"{col}_value"] = market_trading.iloc[0][col]
                        
                        all_data.append(market_data)
                    
                except Exception as e:
                    self.logger.warning(f"{mkt} 시장 데이터 수집 실패: {str(e)}")
                    continue
            
            result = pd.DataFrame(all_data)
            self.logger.info(f"시장 투자자별 요약 수집 완료: {len(result)}개 시장")
            return result
            
        except Exception as e:
            self.logger.error(f"시장 투자자별 요약 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def analyze_foreign_institutional_trends(self, 
                                           data: pd.DataFrame) -> Dict[str, Any]:
        """
        외국인·기관 매매 동향 분석
        
        Args:
            data: 투자자별 거래 데이터
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            if data.empty:
                return {}
            
            analysis = {
                'period': {
                    'start_date': data['date'].min().strftime('%Y-%m-%d'),
                    'end_date': data['date'].max().strftime('%Y-%m-%d'),
                    'total_days': len(data)
                }
            }
            
            # 외국인 매매 분석
            if 'foreign_value' in data.columns:
                foreign_data = data['foreign_value'].dropna()
                analysis['foreign_analysis'] = {
                    'net_total': float(foreign_data.sum()),
                    'daily_average': float(foreign_data.mean()),
                    'net_buying_days': int((foreign_data > 0).sum()),
                    'net_selling_days': int((foreign_data < 0).sum()),
                    'max_net_buying': float(foreign_data.max()),
                    'max_net_selling': float(foreign_data.min()),
                    'trend': 'BUYING' if foreign_data.sum() > 0 else 'SELLING'
                }
            
            # 기관 매매 분석
            if 'institutional_total_value' in data.columns:
                institutional_data = data['institutional_total_value'].dropna()
                analysis['institutional_analysis'] = {
                    'net_total': float(institutional_data.sum()),
                    'daily_average': float(institutional_data.mean()),
                    'net_buying_days': int((institutional_data > 0).sum()),
                    'net_selling_days': int((institutional_data < 0).sum()),
                    'max_net_buying': float(institutional_data.max()),
                    'max_net_selling': float(institutional_data.min()),
                    'trend': 'BUYING' if institutional_data.sum() > 0 else 'SELLING'
                }
            
            # 세부 기관별 분석
            institutional_types = ['institutional_value', 'insurance_value', 'trust_value', 
                                 'private_fund_value', 'bank_value', 'other_corp_value']
            
            detailed_institutional = {}
            for inst_type in institutional_types:
                if inst_type in data.columns:
                    inst_data = data[inst_type].dropna()
                    if not inst_data.empty:
                        detailed_institutional[inst_type] = {
                            'net_total': float(inst_data.sum()),
                            'daily_average': float(inst_data.mean()),
                            'trend': 'BUYING' if inst_data.sum() > 0 else 'SELLING'
                        }
            
            if detailed_institutional:
                analysis['detailed_institutional'] = detailed_institutional
            
            analysis['analysis_date'] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"매매 동향 분석 오류: {str(e)}")
            return {}
    
    def get_stock_symbols_list(self, market: str = "KOSPI") -> List[str]:
        """
        시장별 종목 코드 리스트 조회
        
        Args:
            market: 시장구분 (KOSPI, KOSDAQ)
            
        Returns:
            종목코드 리스트
        """
        try:
            if not PYKRX_AVAILABLE:
                return []
            
            today = datetime.now().strftime("%Y%m%d")
            
            # 최근 영업일로 조정 (주말/공휴일 고려)
            for i in range(7):  # 최대 7일 이전까지 확인
                try:
                    check_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                    tickers = stock.get_market_ticker_list(check_date, market=market)
                    if tickers:
                        self.logger.info(f"{market} 종목 리스트 조회: {len(tickers)}개 ({check_date})")
                        return tickers
                except:
                    continue
            
            self.logger.warning(f"{market} 종목 리스트 조회 실패")
            return []
            
        except Exception as e:
            self.logger.error(f"종목 리스트 조회 오류: {str(e)}")
            return []


def main():
    """테스트 실행"""
    print("=== PyKRX 외국인·기관 데이터 수집기 테스트 ===")
    
    if not PYKRX_AVAILABLE:
        print("PyKRX가 설치되지 않았습니다.")
        print("설치 명령: pip install pykrx")
        return
    
    collector = PyKRXInstitutionalCollector()
    
    # 테스트 파라미터
    test_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")  # 3일전
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")  # 10일전
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")  # 1일전
    test_symbol = "005930"  # 삼성전자
    
    print(f"\n1. 외국인 보유현황 테스트 ({test_date})")
    foreign_holdings = collector.get_foreign_ownership_data(test_date, "KOSPI")
    if not foreign_holdings.empty:
        print(f"   수집 성공: {len(foreign_holdings)}개 종목")
        print(f"   컬럼: {list(foreign_holdings.columns)}")
    else:
        print("   수집 실패 또는 데이터 없음")
    
    print(f"\n2. 투자자별 거래동향 테스트 ({test_symbol})")
    trading_data = collector.get_trading_by_investor_type(start_date, end_date, test_symbol)
    if not trading_data.empty:
        print(f"   수집 성공: {len(trading_data)}일")
        print(f"   컬럼: {list(trading_data.columns)}")
        
        # 최신 데이터 샘플 출력
        latest = trading_data.iloc[-1]
        print(f"   최신일자: {latest['date']}")
        if 'foreign_value' in trading_data.columns:
            print(f"   외국인 순매수: {latest.get('foreign_value', 0):,.0f}억원")
        if 'institutional_total_value' in trading_data.columns:
            print(f"   기관 순매수: {latest.get('institutional_total_value', 0):,.0f}억원")
        
        # 동향 분석
        print(f"\n3. 매매 동향 분석")
        analysis = collector.analyze_foreign_institutional_trends(trading_data)
        if analysis:
            if 'foreign_analysis' in analysis:
                foreign = analysis['foreign_analysis']
                print(f"   외국인 동향: {foreign['trend']} (순매수: {foreign['net_total']:,.0f}억원)")
                print(f"   외국인 순매수일: {foreign['net_buying_days']}일, 순매도일: {foreign['net_selling_days']}일")
            
            if 'institutional_analysis' in analysis:
                institutional = analysis['institutional_analysis']
                print(f"   기관 동향: {institutional['trend']} (순매수: {institutional['net_total']:,.0f}억원)")
                print(f"   기관 순매수일: {institutional['net_buying_days']}일, 순매도일: {institutional['net_selling_days']}일")
    else:
        print("   수집 실패 또는 데이터 없음")
    
    print(f"\n4. 시장 투자자별 요약 테스트")
    market_summary = collector.get_market_summary_by_investor(test_date, "KOSPI")
    if not market_summary.empty:
        print(f"   수집 성공: {len(market_summary)}개 시장")
        print(f"   컬럼: {list(market_summary.columns)}")
    else:
        print("   수집 실패 또는 데이터 없음")
    
    print(f"\n5. 종목 리스트 테스트")
    symbols = collector.get_stock_symbols_list("KOSPI")
    if symbols:
        print(f"   KOSPI 종목 수: {len(symbols)}개")
        print(f"   첫 10개 종목: {symbols[:10]}")
    else:
        print("   종목 리스트 조회 실패")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()