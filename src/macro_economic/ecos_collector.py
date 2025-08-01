"""
한국은행 ECOS API 데이터 수집기
금리, 환율, 인플레이션 등 주요 거시경제 지표 수집
"""
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import time
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class ECOSCollector:
    """한국은행 ECOS API 데이터 수집기"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: ECOS API 키 (없으면 환경변수에서 가져옴)
        """
        self.api_key = api_key or os.getenv('ECOS_API_KEY')
        self.base_url = "https://ecos.bok.or.kr/api"
        
        # 주요 지표 코드 매핑
        self.indicator_codes = {
            # 금리
            'base_rate': '722Y001',  # 한국은행 기준금리
            'cd_rate': '817Y002',    # CD 금리 (91일)
            'bond_3y': '817Y003',    # 국고채 3년
            'bond_10y': '817Y006',   # 국고채 10년
            
            # 환율
            'usd_krw': '731Y001',    # 원/달러 환율
            'eur_krw': '731Y002',    # 원/유로 환율
            'jpy_krw': '731Y003',    # 원/엔(100엔) 환율
            'cny_krw': '731Y004',    # 원/위안 환율
            
            # 경제 활동
            'gdp': '200Y001',        # GDP(실질, 계절조정)
            'industrial_production': '402Y014',  # 산업생산지수
            'consumer_price': '901Y009',  # 소비자물가지수
            'producer_price': '404Y014',  # 생산자물가지수
            
            # 통화
            'm1': '101Y002',         # 통화(M1)
            'm2': '101Y003',         # 통화(M2)
            
            # 무역
            'export': '403Y001',     # 수출(통관기준)
            'import': '403Y002',     # 수입(통관기준)
        }
        
        self.logger = self._setup_logger()
        
        if not self.api_key:
            self.logger.warning("ECOS API 키가 설정되지 않았습니다. 환경변수 'ECOS_API_KEY'를 설정하세요.")
        else:
            self.logger.info("한국은행 ECOS API 수집기 초기화 완료")
            
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
    
    def get_economic_indicator(self, 
                             indicator_key: str,
                             start_date: str,
                             end_date: str,
                             frequency: str = 'M') -> Optional[pd.DataFrame]:
        """
        경제 지표 데이터 수집
        
        Args:
            indicator_key: 지표 키 (self.indicator_codes의 키)
            start_date: 시작일 (YYYYMM 또는 YYYYMMDD)
            end_date: 종료일 (YYYYMM 또는 YYYYMMDD)
            frequency: 주기 ('D': 일, 'M': 월, 'Q': 분기, 'A': 년)
            
        Returns:
            경제 지표 DataFrame
        """
        try:
            if not self.api_key:
                self.logger.error("API 키가 설정되지 않았습니다.")
                return None
                
            if indicator_key not in self.indicator_codes:
                self.logger.error(f"지원하지 않는 지표: {indicator_key}")
                return None
            
            stat_code = self.indicator_codes[indicator_key]
            
            # API 엔드포인트 구성
            url = f"{self.base_url}/StatisticSearch/{self.api_key}/json/kr/1/10000/{stat_code}/{frequency}/{start_date}/{end_date}"
            
            self.logger.info(f"ECOS API 요청: {indicator_key} ({start_date}~{end_date})")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 에러 체크
            if 'RESULT' in data:
                error_code = data['RESULT'].get('CODE', 'UNKNOWN')
                error_msg = data['RESULT'].get('MESSAGE', 'Unknown error')
                self.logger.error(f"ECOS API 오류 ({error_code}): {error_msg}")
                return None
            
            # 데이터 추출
            if 'StatisticSearch' not in data or 'row' not in data['StatisticSearch']:
                self.logger.warning(f"데이터 없음: {indicator_key}")
                return None
            
            rows = data['StatisticSearch']['row']
            
            # DataFrame 생성
            df_data = []
            for row in rows:
                try:
                    date_str = row.get('TIME', '')
                    value_str = row.get('DATA_VALUE', '0')
                    
                    # 값 변환 (쉼표 제거 후 float 변환)
                    value = float(value_str.replace(',', '')) if value_str and value_str != '-' else np.nan
                    
                    # 날짜 변환
                    if len(date_str) == 6:  # YYYYMM
                        date = pd.to_datetime(date_str + '01', format='%Y%m%d')
                    elif len(date_str) == 8:  # YYYYMMDD
                        date = pd.to_datetime(date_str, format='%Y%m%d')
                    else:
                        continue
                    
                    df_data.append({
                        'date': date,
                        'indicator': indicator_key,
                        'value': value,
                        'unit': row.get('UNIT_NAME', ''),
                        'frequency': frequency
                    })
                    
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"데이터 파싱 오류: {str(e)}")
                    continue
            
            if not df_data:
                self.logger.warning(f"유효한 데이터 없음: {indicator_key}")
                return None
            
            df = pd.DataFrame(df_data)
            df = df.sort_values('date').reset_index(drop=True)
            
            self.logger.info(f"ECOS 데이터 수집 완료: {indicator_key} ({len(df)}개 레코드)")
            return df
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"ECOS API 요청 오류: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"ECOS 데이터 수집 오류: {str(e)}")
            return None
    
    def get_multiple_indicators(self, 
                              indicator_keys: List[str],
                              start_date: str,
                              end_date: str,
                              frequency: str = 'M') -> pd.DataFrame:
        """
        여러 경제 지표 동시 수집
        
        Args:
            indicator_keys: 지표 키 리스트
            start_date: 시작일
            end_date: 종료일
            frequency: 주기
            
        Returns:
            통합된 경제 지표 DataFrame
        """
        try:
            all_data = []
            
            for indicator_key in indicator_keys:
                data = self.get_economic_indicator(indicator_key, start_date, end_date, frequency)
                if data is not None:
                    all_data.append(data)
                
                # API 호출 제한 대응 (초당 1회)
                time.sleep(1)
            
            if not all_data:
                self.logger.warning("수집된 지표 데이터가 없습니다.")
                return pd.DataFrame()
            
            # 데이터 통합
            combined_df = pd.concat(all_data, ignore_index=True)
            
            self.logger.info(f"다중 지표 수집 완료: {len(indicator_keys)}개 지표, {len(combined_df)}개 레코드")
            return combined_df
            
        except Exception as e:
            self.logger.error(f"다중 지표 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_latest_indicators(self, 
                            indicator_keys: List[str],
                            months_back: int = 12) -> pd.DataFrame:
        """
        최신 경제 지표 수집 (최근 N개월)
        
        Args:
            indicator_keys: 지표 키 리스트
            months_back: 과거 몇 개월까지 수집할지
            
        Returns:
            최신 경제 지표 DataFrame
        """
        try:
            end_date = datetime.now().strftime('%Y%m')
            start_date = (datetime.now() - timedelta(days=months_back * 30)).strftime('%Y%m')
            
            return self.get_multiple_indicators(indicator_keys, start_date, end_date, 'M')
            
        except Exception as e:
            self.logger.error(f"최신 지표 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_key_rates_and_fx(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        주요 금리 및 환율 데이터 수집
        
        Args:
            start_date: 시작일 (YYYYMM)
            end_date: 종료일 (YYYYMM)
            
        Returns:
            {'rates': 금리 DataFrame, 'fx': 환율 DataFrame}
        """
        try:
            result = {}
            
            # 금리 지표
            rate_indicators = ['base_rate', 'cd_rate', 'bond_3y', 'bond_10y']
            rates_data = self.get_multiple_indicators(rate_indicators, start_date, end_date, 'M')
            if not rates_data.empty:
                result['rates'] = rates_data
            
            # 환율 지표  
            fx_indicators = ['usd_krw', 'eur_krw', 'jpy_krw']
            fx_data = self.get_multiple_indicators(fx_indicators, start_date, end_date, 'M')
            if not fx_data.empty:
                result['fx'] = fx_data
            
            self.logger.info(f"주요 금리/환율 데이터 수집 완료: {len(result)}개 카테고리")
            return result
            
        except Exception as e:
            self.logger.error(f"금리/환율 수집 오류: {str(e)}")
            return {}
    
    def pivot_indicators_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        지표별 컬럼으로 변환 (pivot)
        
        Args:
            df: 경제 지표 DataFrame
            
        Returns:
            날짜별 지표 값들을 컬럼으로 한 DataFrame
        """
        try:
            if df.empty:
                return pd.DataFrame()
            
            # 피벗 테이블 생성
            pivot_df = df.pivot_table(
                index='date',
                columns='indicator', 
                values='value',
                aggfunc='first'
            ).fillna(np.nan)
            
            # 컬럼명 정리
            pivot_df.columns.name = None
            pivot_df = pivot_df.reset_index()
            
            self.logger.info(f"지표 피벗 완료: {len(pivot_df)}일, {len(pivot_df.columns)-1}개 지표")
            return pivot_df
            
        except Exception as e:
            self.logger.error(f"지표 피벗 오류: {str(e)}")
            return df
    
    def calculate_indicator_changes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        지표 변화율 계산 (전월 대비, 전년 동월 대비)
        
        Args:
            df: 피벗된 경제 지표 DataFrame
            
        Returns:
            변화율이 추가된 DataFrame
        """
        try:
            if df.empty or 'date' not in df.columns:
                return df
            
            result = df.copy()
            result = result.sort_values('date')
            
            # 지표 컬럼들 (date 제외)
            indicator_cols = [col for col in df.columns if col != 'date']
            
            for col in indicator_cols:
                if col in result.columns:
                    # 전월 대비 변화율
                    result[f'{col}_mom'] = result[col].pct_change() * 100
                    
                    # 전년 동월 대비 변화율 (12개월 전 대비)
                    result[f'{col}_yoy'] = result[col].pct_change(periods=12) * 100
                    
                    # 절대 변화량
                    result[f'{col}_diff'] = result[col].diff()
            
            self.logger.info(f"지표 변화율 계산 완료: {len(indicator_cols)}개 지표")
            return result
            
        except Exception as e:
            self.logger.error(f"지표 변화율 계산 오류: {str(e)}")
            return df


def main():
    """테스트 실행"""
    print("=== 한국은행 ECOS API 수집기 테스트 ===")
    
    # API 키 없이 테스트 (시뮬레이션)
    collector = ECOSCollector()
    
    if not collector.api_key:
        print("\n⚠️ ECOS API 키가 설정되지 않았습니다.")
        print("실제 사용을 위해서는 다음 단계를 수행하세요:")
        print("1. 한국은행 ECOS 홈페이지(https://ecos.bok.or.kr)에서 API 키 발급")
        print("2. 환경변수 'ECOS_API_KEY' 설정")
        print("3. 또는 코드에서 직접 API 키 전달")
        print("\n사용 가능한 지표 목록:")
        
        for key, code in collector.indicator_codes.items():
            print(f"  {key}: {code}")
        
        print("\n=== 테스트 완료 (API 키 없음) ===")
        return
    
    # 실제 API 키가 있는 경우 테스트
    try:
        print(f"\n1. 최근 12개월 주요 지표 수집 테스트")
        key_indicators = ['base_rate', 'usd_krw', 'consumer_price']
        
        latest_data = collector.get_latest_indicators(key_indicators, months_back=12)
        
        if not latest_data.empty:
            print(f"   ✅ 수집 성공: {len(latest_data)}개 레코드")
            
            # 피벗 테이블 생성
            pivot_data = collector.pivot_indicators_by_date(latest_data)
            if not pivot_data.empty:
                print(f"   피벗 테이블: {len(pivot_data)}일, {len(pivot_data.columns)-1}개 지표")
                
                # 최신 값 출력
                if len(pivot_data) > 0:
                    latest = pivot_data.iloc[-1]
                    print(f"   최신 데이터 ({latest['date'].strftime('%Y-%m')}):")
                    for col in pivot_data.columns:
                        if col != 'date' and not pd.isna(latest[col]):
                            print(f"     {col}: {latest[col]:.2f}")
                
                # 변화율 계산
                changes_data = collector.calculate_indicator_changes(pivot_data)
                if not changes_data.empty:
                    print(f"   변화율 계산 완료: {len(changes_data.columns)}개 컬럼")
        else:
            print("   ❌ 데이터 수집 실패")
        
        print(f"\n2. 금리/환율 데이터 수집 테스트")
        start_date = "202301"
        end_date = "202412"
        
        rates_fx_data = collector.get_key_rates_and_fx(start_date, end_date)
        
        if rates_fx_data:
            for category, data in rates_fx_data.items():
                print(f"   {category}: {len(data)}개 레코드")
        else:
            print("   ❌ 금리/환율 데이터 수집 실패")
        
    except Exception as e:
        print(f"   ❌ 테스트 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()