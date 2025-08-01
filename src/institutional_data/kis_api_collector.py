"""
한국투자증권(KIS) Open API 기반 외국인·기관 매매 데이터 수집기
KIS Open API를 활용한 실시간 투자자별 거래 동향 분석
"""
import pandas as pd
import numpy as np
import requests
import json
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import time
import sys
import os

class KISAPICollector:
    """한국투자증권 Open API 기반 외국인·기관 매매 데이터 수집기"""
    
    def __init__(self, 
                 app_key: Optional[str] = None,
                 app_secret: Optional[str] = None,
                 base_url: str = "https://openapi.koreainvestment.com:9443"):
        """
        초기화
        
        Args:
            app_key: KIS Open API App Key
            app_secret: KIS Open API App Secret
            base_url: KIS Open API Base URL
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.access_token = None
        self.token_expires_at = None
        self.logger = self._setup_logger()
        
        if not self.app_key or not self.app_secret:
            self.logger.warning("KIS API 키가 설정되지 않았습니다. 환경변수 또는 직접 설정이 필요합니다.")
            # 환경변수에서 읽기 시도
            self.app_key = os.getenv('KIS_APP_KEY')
            self.app_secret = os.getenv('KIS_APP_SECRET')
            
            if not self.app_key or not self.app_secret:
                self.logger.error("KIS API 키를 찾을 수 없습니다.")
        else:
            self.logger.info("KIS API 외국인·기관 데이터 수집기 초기화 완료")
        
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
    
    def _get_access_token(self) -> bool:
        """액세스 토큰 발급"""
        try:
            if not self.app_key or not self.app_secret:
                self.logger.error("API 키가 설정되지 않았습니다.")
                return False
            
            # 토큰이 아직 유효한지 확인
            if (self.access_token and self.token_expires_at and 
                datetime.now() < self.token_expires_at):
                return True
            
            url = f"{self.base_url}/oauth2/tokenP"
            headers = {
                "Content-Type": "application/json"
            }
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 86400)  # 기본 24시간
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5분 여유
                
                self.logger.info("KIS API 토큰 발급 성공")
                return True
            else:
                self.logger.error(f"KIS API 토큰 발급 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"토큰 발급 오류: {str(e)}")
            return False
    
    def _make_api_request(self, 
                         endpoint: str, 
                         params: Dict[str, str],
                         tr_id: str) -> Optional[Dict]:
        """API 요청 실행"""
        try:
            if not self._get_access_token():
                return None
            
            url = f"{self.base_url}{endpoint}"
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API 요청 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"API 요청 오류: {str(e)}")
            return None
    
    def get_foreign_institutional_aggregation(self, 
                                            market_div: str = "J",
                                            sort_type: str = "1") -> pd.DataFrame:
        """
        외국인기관 매매종목가집계 조회
        
        Args:
            market_div: 시장분류 (J:주식, ETF, ETN, ELW 전체)
            sort_type: 정렬구분 (1:외국인순매수상위, 2:외국인순매도상위)
            
        Returns:
            외국인·기관 매매 집계 DataFrame
        """
        try:
            self.logger.info("외국인기관 매매종목가집계 조회 시작")
            
            endpoint = "/uapi/domestic-stock/v1/ranking/foreigners-institutions"
            params = {
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": "",
                "FID_INPUT_DATE_2": ""
            }
            
            tr_id = "FHPST01710000"
            
            response = self._make_api_request(endpoint, params, tr_id)
            
            if response and 'output' in response:
                output_data = response['output']
                
                if output_data:
                    df = pd.DataFrame(output_data)
                    
                    # 컬럼명 정리
                    column_mapping = {
                        'mksc_shrn_iscd': 'symbol',  # 종목코드
                        'hts_kor_isnm': 'name',      # 종목명
                        'data_rank': 'rank',         # 순위
                        'stck_prpr': 'current_price', # 현재가
                        'prdy_vrss': 'price_change', # 전일대비
                        'prdy_vrss_sign': 'change_sign', # 전일대비부호
                        'prdy_ctrt': 'change_rate',  # 전일대비율
                        'acml_vol': 'volume',        # 거래량
                        'acml_tr_pbmn': 'trading_value', # 거래대금
                        'frgn_ntby_qty': 'foreign_net_buy_qty',  # 외국인순매수수량
                        'frgn_ntby_tr_pbmn': 'foreign_net_buy_value',  # 외국인순매수거래대금
                        'inst_ntby_qty': 'institutional_net_buy_qty',  # 기관순매수수량
                        'inst_ntby_tr_pbmn': 'institutional_net_buy_value'  # 기관순매수거래대금
                    }
                    
                    # 컬럼명 변경
                    df = df.rename(columns=column_mapping)
                    
                    # 숫자형 컬럼 변환
                    numeric_columns = ['current_price', 'price_change', 'change_rate', 
                                     'volume', 'trading_value', 'foreign_net_buy_qty',
                                     'foreign_net_buy_value', 'institutional_net_buy_qty',
                                     'institutional_net_buy_value']
                    
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 메타데이터 추가
                    df['date'] = datetime.now().date()
                    df['data_source'] = 'KIS_API'
                    df['market_div'] = market_div
                    df['sort_type'] = sort_type
                    
                    self.logger.info(f"외국인기관 매매집계 조회 완료: {len(df)}개 종목")
                    return df
                
            self.logger.warning("외국인기관 매매집계 데이터 없음")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"외국인기관 매매집계 조회 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_stock_investor_info(self, symbol: str) -> pd.DataFrame:
        """
        개별 종목 투자자별 정보 조회
        
        Args:
            symbol: 종목코드 (6자리)
            
        Returns:
            투자자별 정보 DataFrame
        """
        try:
            self.logger.info(f"종목 투자자 정보 조회: {symbol}")
            
            endpoint = "/uapi/domestic-stock/v1/quotations/inquire-investor"
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol
            }
            
            tr_id = "FHKST01010900"
            
            response = self._make_api_request(endpoint, params, tr_id)
            
            if response and 'output' in response:
                output_data = response['output']
                
                if output_data:
                    # 단일 응답을 DataFrame으로 변환
                    df = pd.DataFrame([output_data])
                    
                    # 컬럼명 정리
                    column_mapping = {
                        'stck_shrn_iscd': 'symbol',
                        'stck_prpr': 'current_price',
                        'prdy_vrss': 'price_change',
                        'prdy_ctrt': 'change_rate',
                        'acml_vol': 'volume',
                        'acml_tr_pbmn': 'trading_value',
                        'frgn_ntby_qty': 'foreign_net_buy_qty',
                        'frgn_ntby_tr_pbmn': 'foreign_net_buy_value',
                        'frgn_hldn_qty': 'foreign_holding_qty',
                        'frgn_hldn_rt': 'foreign_holding_rate',
                        'inst_ntby_qty': 'institutional_net_buy_qty',
                        'inst_ntby_tr_pbmn': 'institutional_net_buy_value'
                    }
                    
                    df = df.rename(columns=column_mapping)
                    
                    # 숫자형 변환
                    numeric_columns = ['current_price', 'price_change', 'change_rate',
                                     'volume', 'trading_value', 'foreign_net_buy_qty',
                                     'foreign_net_buy_value', 'foreign_holding_qty',
                                     'foreign_holding_rate', 'institutional_net_buy_qty',
                                     'institutional_net_buy_value']
                    
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 메타데이터 추가
                    df['date'] = datetime.now().date()
                    df['data_source'] = 'KIS_API'
                    
                    self.logger.info(f"종목 투자자 정보 조회 완료: {symbol}")
                    return df
                
            self.logger.warning(f"종목 투자자 정보 없음: {symbol}")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"종목 투자자 정보 조회 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_market_investor_trends(self, 
                                 market_div: str = "J") -> pd.DataFrame:
        """
        시장별 투자자 동향 조회
        
        Args:
            market_div: 시장분류 (J:전체, S:코스피, Q:코스닥)
            
        Returns:
            시장 투자자 동향 DataFrame
        """
        try:
            self.logger.info("시장 투자자 동향 조회 시작")
            
            endpoint = "/uapi/domestic-stock/v1/quotations/inquire-market-investor"
            params = {
                "FID_COND_MRKT_DIV_CODE": market_div,
                "FID_INPUT_DATE_1": datetime.now().strftime("%Y%m%d")
            }
            
            tr_id = "FHKST01020000"
            
            response = self._make_api_request(endpoint, params, tr_id)
            
            if response and 'output' in response:
                output_data = response['output']
                
                if output_data:
                    df = pd.DataFrame([output_data])
                    
                    # 메타데이터 추가
                    df['date'] = datetime.now().date()
                    df['data_source'] = 'KIS_API'
                    df['market_div'] = market_div
                    
                    self.logger.info("시장 투자자 동향 조회 완료")
                    return df
                
            self.logger.warning("시장 투자자 동향 데이터 없음")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"시장 투자자 동향 조회 오류: {str(e)}")
            return pd.DataFrame()
    
    def analyze_kis_trading_data(self, 
                               aggregation_data: pd.DataFrame,
                               top_n: int = 20) -> Dict[str, Any]:
        """
        KIS API 매매 데이터 분석
        
        Args:
            aggregation_data: 외국인기관 매매집계 데이터
            top_n: 상위 N개 종목 분석
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            if aggregation_data.empty:
                return {}
            
            analysis = {
                'data_date': datetime.now().strftime('%Y-%m-%d'),
                'total_stocks': len(aggregation_data)
            }
            
            # 상위 종목으로 제한
            top_data = aggregation_data.head(top_n)
            
            # 외국인 매매 분석
            if 'foreign_net_buy_value' in top_data.columns:
                foreign_net_buy = top_data['foreign_net_buy_value'].sum()
                foreign_buy_stocks = len(top_data[top_data['foreign_net_buy_value'] > 0])
                foreign_sell_stocks = len(top_data[top_data['foreign_net_buy_value'] < 0])
                
                analysis['foreign_analysis'] = {
                    'net_buy_value': float(foreign_net_buy),
                    'net_buying_stocks': int(foreign_buy_stocks),
                    'net_selling_stocks': int(foreign_sell_stocks),
                    'trend': 'BUYING' if foreign_net_buy > 0 else 'SELLING',
                    'top_buy_stock': self._get_top_stock(top_data, 'foreign_net_buy_value', True),
                    'top_sell_stock': self._get_top_stock(top_data, 'foreign_net_buy_value', False)
                }
            
            # 기관 매매 분석
            if 'institutional_net_buy_value' in top_data.columns:
                inst_net_buy = top_data['institutional_net_buy_value'].sum()
                inst_buy_stocks = len(top_data[top_data['institutional_net_buy_value'] > 0])
                inst_sell_stocks = len(top_data[top_data['institutional_net_buy_value'] < 0])
                
                analysis['institutional_analysis'] = {
                    'net_buy_value': float(inst_net_buy),
                    'net_buying_stocks': int(inst_buy_stocks),
                    'net_selling_stocks': int(inst_sell_stocks),
                    'trend': 'BUYING' if inst_net_buy > 0 else 'SELLING',
                    'top_buy_stock': self._get_top_stock(top_data, 'institutional_net_buy_value', True),
                    'top_sell_stock': self._get_top_stock(top_data, 'institutional_net_buy_value', False)
                }
            
            analysis['analysis_scope'] = f'TOP_{top_n}_STOCKS'
            analysis['analysis_date'] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"KIS 매매 데이터 분석 오류: {str(e)}")
            return {}
    
    def _get_top_stock(self, 
                      data: pd.DataFrame, 
                      column: str, 
                      is_buy: bool) -> Dict[str, Any]:
        """상위 매수/매도 종목 조회"""
        try:
            if column not in data.columns:
                return {}
            
            if is_buy:
                top_stock = data.loc[data[column].idxmax()]
            else:
                top_stock = data.loc[data[column].idxmin()]
            
            return {
                'symbol': str(top_stock.get('symbol', '')),
                'name': str(top_stock.get('name', '')),
                'net_value': float(top_stock.get(column, 0)),
                'current_price': float(top_stock.get('current_price', 0)),
                'change_rate': float(top_stock.get('change_rate', 0))
            }
            
        except Exception:
            return {}


def main():
    """테스트 실행"""
    print("=== KIS API 외국인·기관 데이터 수집기 테스트 ===")
    
    # 환경변수 설정 안내
    print("\n⚠️  KIS API 테스트를 위해서는 다음 환경변수 설정이 필요합니다:")
    print("   export KIS_APP_KEY='your_app_key'")
    print("   export KIS_APP_SECRET='your_app_secret'")
    print("   또는 직접 생성자에 전달하세요.")
    
    collector = KISAPICollector()
    
    if not collector.app_key or not collector.app_secret:
        print("\n❌ API 키가 설정되지 않았습니다. 테스트를 건너뜁니다.")
        print("\n설정 방법:")
        print("1. KIS 홈페이지에서 Open API 신청")
        print("2. 발급받은 App Key와 App Secret을 환경변수로 설정")
        print("3. 또는 KISAPICollector(app_key='...', app_secret='...')로 직접 설정")
        return
    
    print(f"\n1. 토큰 발급 테스트")
    if collector._get_access_token():
        print("   ✅ 토큰 발급 성공")
        
        print(f"\n2. 외국인기관 매매집계 테스트")
        aggregation_data = collector.get_foreign_institutional_aggregation()
        if not aggregation_data.empty:
            print(f"   ✅ 수집 성공: {len(aggregation_data)}개 종목")
            print(f"   컬럼: {list(aggregation_data.columns)}")
            
            # 상위 5개 종목 출력
            print(f"\n   상위 5개 종목:")
            for idx, row in aggregation_data.head().iterrows():
                print(f"   {row.get('rank', '')}. {row.get('name', '')} ({row.get('symbol', '')})")
                print(f"      외국인 순매수: {row.get('foreign_net_buy_value', 0):,.0f}백만원")
                print(f"      기관 순매수: {row.get('institutional_net_buy_value', 0):,.0f}백만원")
            
            # 데이터 분석
            print(f"\n3. 매매 동향 분석")
            analysis = collector.analyze_kis_trading_data(aggregation_data)
            if analysis:
                if 'foreign_analysis' in analysis:
                    foreign = analysis['foreign_analysis']
                    print(f"   외국인 동향: {foreign['trend']}")
                    print(f"   외국인 순매수 종목수: {foreign['net_buying_stocks']}개")
                    print(f"   외국인 순매도 종목수: {foreign['net_selling_stocks']}개")
                
                if 'institutional_analysis' in analysis:
                    institutional = analysis['institutional_analysis']
                    print(f"   기관 동향: {institutional['trend']}")
                    print(f"   기관 순매수 종목수: {institutional['net_buying_stocks']}개")
                    print(f"   기관 순매도 종목수: {institutional['net_selling_stocks']}개")
        else:
            print("   ❌ 데이터 수집 실패")
        
        print(f"\n4. 개별 종목 투자자 정보 테스트 (삼성전자)")
        stock_info = collector.get_stock_investor_info("005930")
        if not stock_info.empty:
            print(f"   ✅ 수집 성공")
            stock = stock_info.iloc[0]
            print(f"   현재가: {stock.get('current_price', 0):,.0f}원")
            print(f"   외국인 순매수: {stock.get('foreign_net_buy_value', 0):,.0f}백만원")
            print(f"   외국인 보유율: {stock.get('foreign_holding_rate', 0):.2f}%")
            print(f"   기관 순매수: {stock.get('institutional_net_buy_value', 0):,.0f}백만원")
        else:
            print("   ❌ 종목 정보 수집 실패")
        
    else:
        print("   ❌ 토큰 발급 실패")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()