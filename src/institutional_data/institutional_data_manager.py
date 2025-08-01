"""
외국인·기관 매매 데이터 통합 관리자
PyKRX와 KIS API를 통합하여 포괄적인 투자자별 거래 동향 분석
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.institutional_data.pykrx_collector import PyKRXInstitutionalCollector
from src.institutional_data.kis_api_collector import KISAPICollector

class InstitutionalDataManager:
    """외국인·기관 매매 데이터 통합 관리자"""
    
    def __init__(self, 
                 use_pykrx: bool = True,
                 use_kis_api: bool = False,
                 kis_app_key: Optional[str] = None,
                 kis_app_secret: Optional[str] = None):
        """
        초기화
        
        Args:
            use_pykrx: PyKRX 사용 여부
            use_kis_api: KIS API 사용 여부  
            kis_app_key: KIS API App Key
            kis_app_secret: KIS API App Secret
        """
        self.use_pykrx = use_pykrx
        self.use_kis_api = use_kis_api
        self.logger = self._setup_logger()
        
        # PyKRX 수집기 초기화
        if self.use_pykrx:
            try:
                self.pykrx_collector = PyKRXInstitutionalCollector()
                self.logger.info("PyKRX 수집기 초기화 완료")
            except Exception as e:
                self.logger.warning(f"PyKRX 수집기 초기화 실패: {str(e)}")
                self.use_pykrx = False
                self.pykrx_collector = None
        else:
            self.pykrx_collector = None
        
        # KIS API 수집기 초기화
        if self.use_kis_api:
            try:
                self.kis_collector = KISAPICollector(kis_app_key, kis_app_secret)
                self.logger.info("KIS API 수집기 초기화 완료")
            except Exception as e:
                self.logger.warning(f"KIS API 수집기 초기화 실패: {str(e)}")
                self.use_kis_api = False
                self.kis_collector = None
        else:
            self.kis_collector = None
        
        if not self.use_pykrx and not self.use_kis_api:
            self.logger.error("사용 가능한 데이터 수집기가 없습니다.")
        
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
    
    def collect_comprehensive_institutional_data(self, 
                                               symbol: str,
                                               start_date: str,
                                               end_date: str) -> pd.DataFrame:
        """
        종목별 포괄적 기관·외국인 데이터 수집
        
        Args:
            symbol: 종목코드 (6자리)
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            
        Returns:
            통합 기관·외국인 데이터 DataFrame
        """
        try:
            self.logger.info(f"포괄적 기관데이터 수집 시작: {symbol} ({start_date}~{end_date})")
            
            all_data = []
            
            # PyKRX 데이터 수집
            if self.use_pykrx and self.pykrx_collector:
                try:
                    pykrx_data = self.pykrx_collector.get_trading_by_investor_type(
                        start_date, end_date, symbol
                    )
                    if not pykrx_data.empty:
                        pykrx_data['data_source'] = 'PyKRX'
                        all_data.append(pykrx_data)
                        self.logger.info(f"PyKRX 데이터 수집 완료: {len(pykrx_data)}일")
                    
                except Exception as e:
                    self.logger.warning(f"PyKRX 데이터 수집 실패: {str(e)}")
            
            # KIS API 데이터 수집 (당일)
            if self.use_kis_api and self.kis_collector:
                try:
                    kis_data = self.kis_collector.get_stock_investor_info(symbol)
                    if not kis_data.empty:
                        kis_data['data_source'] = 'KIS_API'
                        all_data.append(kis_data)
                        self.logger.info("KIS API 데이터 수집 완료")
                    
                except Exception as e:
                    self.logger.warning(f"KIS API 데이터 수집 실패: {str(e)}")
            
            # 데이터 통합
            if all_data:
                combined_data = self._merge_institutional_data(all_data, symbol)
                self.logger.info(f"데이터 통합 완료: {len(combined_data)}일")
                return combined_data
            else:
                self.logger.warning("수집된 데이터가 없습니다.")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"포괄적 기관데이터 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def _merge_institutional_data(self, 
                                data_list: List[pd.DataFrame], 
                                symbol: str) -> pd.DataFrame:
        """기관·외국인 데이터 병합"""
        try:
            if not data_list:
                return pd.DataFrame()
            
            # 기본 구조 생성
            merged_data = []
            
            for data in data_list:
                if data.empty:
                    continue
                
                # 공통 컬럼 추출
                common_columns = ['date', 'symbol', 'data_source']
                institutional_columns = [
                    'foreign_value', 'foreign_net_buy_value', 'foreign_holding_rate',
                    'institutional_total_value', 'institutional_net_buy_value',
                    'institutional_value', 'insurance_value', 'trust_value',
                    'private_fund_value', 'bank_value', 'other_corp_value'
                ]
                
                # 사용 가능한 컬럼만 선택
                available_columns = common_columns + [
                    col for col in institutional_columns if col in data.columns
                ]
                
                subset_data = data[available_columns].copy()
                merged_data.append(subset_data)
            
            if merged_data:
                # 모든 데이터 연결
                result = pd.concat(merged_data, ignore_index=True, sort=False)
                
                # 날짜별 정렬
                result['date'] = pd.to_datetime(result['date'])
                result = result.sort_values('date').reset_index(drop=True)
                
                # 중복 제거 (같은 날짜의 경우 최신 데이터 우선)
                result = result.drop_duplicates(subset=['date', 'symbol'], keep='last')
                
                # 누락된 기본 컬럼 추가
                if 'symbol' not in result.columns:
                    result['symbol'] = symbol
                
                return result
            else:
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"데이터 병합 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_market_institutional_summary(self, 
                                       date: str = None,
                                       markets: List[str] = None) -> pd.DataFrame:
        """
        시장별 기관·외국인 매매 요약
        
        Args:
            date: 조회일자 (YYYYMMDD, None이면 최근 영업일)
            markets: 시장 리스트 (["KOSPI", "KOSDAQ"], None이면 전체)
            
        Returns:
            시장별 매매 요약 DataFrame
        """
        try:
            if date is None:
                date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            
            if markets is None:
                markets = ["KOSPI", "KOSDAQ"]
            
            self.logger.info(f"시장 기관매매 요약 수집: {date}")
            
            all_market_data = []
            
            # PyKRX 데이터 수집
            if self.use_pykrx and self.pykrx_collector:
                for market in markets:
                    try:
                        market_data = self.pykrx_collector.get_market_summary_by_investor(
                            date, market
                        )
                        if not market_data.empty:
                            all_market_data.append(market_data)
                        
                    except Exception as e:
                        self.logger.warning(f"{market} 시장 데이터 수집 실패: {str(e)}")
            
            # KIS API 데이터 수집
            if self.use_kis_api and self.kis_collector:
                try:
                    kis_summary = self.kis_collector.get_foreign_institutional_aggregation()
                    if not kis_summary.empty:
                        # KIS 데이터를 시장 요약 형태로 변환
                        market_summary = self._convert_kis_to_market_summary(kis_summary, date)
                        if not market_summary.empty:
                            all_market_data.append(market_summary)
                    
                except Exception as e:
                    self.logger.warning(f"KIS API 시장 요약 수집 실패: {str(e)}")
            
            # 데이터 통합
            if all_market_data:
                result = pd.concat(all_market_data, ignore_index=True, sort=False)
                self.logger.info(f"시장 요약 수집 완료: {len(result)}개 시장")
                return result
            else:
                self.logger.warning("시장 요약 데이터 없음")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"시장 기관매매 요약 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def _convert_kis_to_market_summary(self, 
                                     kis_data: pd.DataFrame, 
                                     date: str) -> pd.DataFrame:
        """KIS 데이터를 시장 요약 형태로 변환"""
        try:
            if kis_data.empty:
                return pd.DataFrame()
            
            # 전체 시장 합계 계산
            summary = {
                'date': pd.to_datetime(date),
                'market': 'ALL',
                'data_source': 'KIS_API',
                'foreign_net_buy_total': kis_data['foreign_net_buy_value'].sum(),
                'institutional_net_buy_total': kis_data['institutional_net_buy_value'].sum(),
                'foreign_buying_stocks': len(kis_data[kis_data['foreign_net_buy_value'] > 0]),
                'foreign_selling_stocks': len(kis_data[kis_data['foreign_net_buy_value'] < 0]),
                'institutional_buying_stocks': len(kis_data[kis_data['institutional_net_buy_value'] > 0]),
                'institutional_selling_stocks': len(kis_data[kis_data['institutional_net_buy_value'] < 0])
            }
            
            return pd.DataFrame([summary])
            
        except Exception as e:
            self.logger.error(f"KIS 데이터 변환 오류: {str(e)}")
            return pd.DataFrame()
    
    def analyze_institutional_signals(self, 
                                    institutional_data: pd.DataFrame,
                                    lookback_days: int = 5,
                                    volume_threshold: float = 1000) -> Dict[str, Any]:
        """
        기관·외국인 매매 신호 분석
        
        Args:
            institutional_data: 기관·외국인 매매 데이터
            lookback_days: 분석 기간 (일)
            volume_threshold: 거래대금 임계값 (백만원)
            
        Returns:
            매매 신호 분석 결과
        """
        try:
            if institutional_data.empty:
                return {}
            
            self.logger.info(f"기관매매 신호 분석 시작: {len(institutional_data)}일 데이터")
            
            # 최근 데이터로 제한
            recent_data = institutional_data.tail(lookback_days)
            
            analysis = {
                'analysis_period': {
                    'lookback_days': lookback_days,
                    'start_date': recent_data['date'].min().strftime('%Y-%m-%d'),
                    'end_date': recent_data['date'].max().strftime('%Y-%m-%d')
                }
            }
            
            # 외국인 매매 신호 분석
            if 'foreign_value' in recent_data.columns or 'foreign_net_buy_value' in recent_data.columns:
                foreign_signal = self._analyze_investor_signal(
                    recent_data, 
                    'foreign', 
                    volume_threshold
                )
                analysis['foreign_signal'] = foreign_signal
            
            # 기관 매매 신호 분석
            institutional_columns = ['institutional_total_value', 'institutional_net_buy_value']
            for col in institutional_columns:
                if col in recent_data.columns:
                    institutional_signal = self._analyze_investor_signal(
                        recent_data, 
                        'institutional', 
                        volume_threshold,
                        value_column=col
                    )
                    analysis['institutional_signal'] = institutional_signal
                    break
            
            # 종합 신호 생성
            analysis['combined_signal'] = self._generate_combined_signal(
                analysis.get('foreign_signal', {}),
                analysis.get('institutional_signal', {})
            )
            
            analysis['analysis_date'] = datetime.now().isoformat()
            
            self.logger.info("기관매매 신호 분석 완료")
            return analysis
            
        except Exception as e:
            self.logger.error(f"기관매매 신호 분석 오류: {str(e)}")
            return {}
    
    def _analyze_investor_signal(self, 
                               data: pd.DataFrame, 
                               investor_type: str,
                               volume_threshold: float,
                               value_column: str = None) -> Dict[str, Any]:
        """투자자별 매매 신호 분석"""
        try:
            if value_column is None:
                if investor_type == 'foreign':
                    value_column = 'foreign_value' if 'foreign_value' in data.columns else 'foreign_net_buy_value'
                else:
                    value_column = 'institutional_total_value' if 'institutional_total_value' in data.columns else 'institutional_net_buy_value'
            
            if value_column not in data.columns:
                return {}
            
            values = data[value_column].dropna()
            
            if values.empty:
                return {}
            
            # 기본 통계
            net_total = values.sum()
            daily_average = values.mean()
            buying_days = (values > 0).sum()
            selling_days = (values < 0).sum()
            
            # 신호 강도 계산
            signal_strength = abs(daily_average) / volume_threshold if volume_threshold > 0 else 0
            
            # 추세 분석
            trend = 'NEUTRAL'
            if net_total > volume_threshold:
                trend = 'STRONG_BUYING'
            elif net_total > volume_threshold / 2:
                trend = 'BUYING'
            elif net_total < -volume_threshold:
                trend = 'STRONG_SELLING'
            elif net_total < -volume_threshold / 2:
                trend = 'SELLING'
            
            # 지속성 분석
            consistency = max(buying_days, selling_days) / len(values) if len(values) > 0 else 0
            
            return {
                'net_total': float(net_total),
                'daily_average': float(daily_average),
                'buying_days': int(buying_days),
                'selling_days': int(selling_days),
                'trend': trend,
                'signal_strength': float(signal_strength),
                'consistency': float(consistency),
                'confidence': min(1.0, signal_strength * consistency)
            }
            
        except Exception as e:
            self.logger.error(f"{investor_type} 신호 분석 오류: {str(e)}")
            return {}
    
    def _generate_combined_signal(self, 
                                foreign_signal: Dict[str, Any],
                                institutional_signal: Dict[str, Any]) -> Dict[str, Any]:
        """외국인·기관 신호 통합"""
        try:
            combined = {
                'signal': 'NEUTRAL',
                'strength': 0.0,
                'confidence': 0.0,
                'agreement': False
            }
            
            # 신호 가중치
            foreign_weight = 0.6  # 외국인 신호 가중치
            institutional_weight = 0.4  # 기관 신호 가중치
            
            total_strength = 0
            total_confidence = 0
            
            # 외국인 신호 처리
            if foreign_signal:
                foreign_trend = foreign_signal.get('trend', 'NEUTRAL')
                foreign_conf = foreign_signal.get('confidence', 0)
                
                if 'BUYING' in foreign_trend:
                    total_strength += foreign_weight * (2 if 'STRONG' in foreign_trend else 1)
                elif 'SELLING' in foreign_trend:
                    total_strength -= foreign_weight * (2 if 'STRONG' in foreign_trend else 1)
                
                total_confidence += foreign_weight * foreign_conf
            
            # 기관 신호 처리
            if institutional_signal:
                inst_trend = institutional_signal.get('trend', 'NEUTRAL')
                inst_conf = institutional_signal.get('confidence', 0)
                
                if 'BUYING' in inst_trend:
                    total_strength += institutional_weight * (2 if 'STRONG' in inst_trend else 1)
                elif 'SELLING' in inst_trend:
                    total_strength -= institutional_weight * (2 if 'STRONG' in inst_trend else 1)
                
                total_confidence += institutional_weight * inst_conf
            
            # 통합 신호 결정
            if total_strength > 1.5:
                combined['signal'] = 'STRONG_BUY'
            elif total_strength > 0.5:
                combined['signal'] = 'BUY'
            elif total_strength < -1.5:
                combined['signal'] = 'STRONG_SELL'
            elif total_strength < -0.5:
                combined['signal'] = 'SELL'
            else:
                combined['signal'] = 'NEUTRAL'
            
            combined['strength'] = abs(total_strength)
            combined['confidence'] = total_confidence
            
            # 외국인·기관 신호 일치도 확인
            if foreign_signal and institutional_signal:
                foreign_trend = foreign_signal.get('trend', 'NEUTRAL')
                inst_trend = institutional_signal.get('trend', 'NEUTRAL')
                
                # 같은 방향 신호인지 확인
                if (('BUYING' in foreign_trend and 'BUYING' in inst_trend) or
                    ('SELLING' in foreign_trend and 'SELLING' in inst_trend)):
                    combined['agreement'] = True
            
            return combined
            
        except Exception as e:
            self.logger.error(f"통합 신호 생성 오류: {str(e)}")
            return {'signal': 'NEUTRAL', 'strength': 0.0, 'confidence': 0.0, 'agreement': False}


def main():
    """테스트 실행"""
    print("=== 외국인·기관 매매 데이터 통합 관리자 테스트 ===")
    
    # PyKRX만 사용하는 관리자 생성
    manager = InstitutionalDataManager(
        use_pykrx=True,
        use_kis_api=False  # KIS API는 키가 필요하므로 기본적으로 비활성화
    )
    
    # 테스트 파라미터
    test_symbol = "005930"  # 삼성전자
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    test_date = (datetime.now() - timedelta(days=2)).strftime("%Y%m%d")
    
    print(f"\n1. 종목별 포괄적 기관데이터 수집 테스트 ({test_symbol})")
    institutional_data = manager.collect_comprehensive_institutional_data(
        test_symbol, start_date, end_date
    )
    
    if not institutional_data.empty:
        print(f"   ✅ 수집 성공: {len(institutional_data)}일")
        print(f"   컬럼: {list(institutional_data.columns)}")
        
        # 최근 데이터 출력
        if len(institutional_data) > 0:
            latest = institutional_data.iloc[-1]
            print(f"   최신일자: {latest['date']}")
            print(f"   데이터 출처: {latest.get('data_source', 'Unknown')}")
            
            if 'foreign_value' in institutional_data.columns:
                print(f"   외국인 순매수: {latest.get('foreign_value', 0):,.0f}억원")
            if 'institutional_total_value' in institutional_data.columns:
                print(f"   기관 순매수: {latest.get('institutional_total_value', 0):,.0f}억원")
    
        print(f"\n2. 기관매매 신호 분석 테스트")
        signal_analysis = manager.analyze_institutional_signals(
            institutional_data, 
            lookback_days=5,
            volume_threshold=100  # 100억원
        )
        
        if signal_analysis:
            print(f"   ✅ 분석 완료")
            
            if 'foreign_signal' in signal_analysis:
                foreign = signal_analysis['foreign_signal']
                print(f"   외국인 신호: {foreign.get('trend', 'UNKNOWN')} (신뢰도: {foreign.get('confidence', 0):.2f})")
            
            if 'institutional_signal' in signal_analysis:
                institutional = signal_analysis['institutional_signal']
                print(f"   기관 신호: {institutional.get('trend', 'UNKNOWN')} (신뢰도: {institutional.get('confidence', 0):.2f})")
            
            if 'combined_signal' in signal_analysis:
                combined = signal_analysis['combined_signal']
                print(f"   통합 신호: {combined.get('signal', 'UNKNOWN')} (강도: {combined.get('strength', 0):.2f})")
                print(f"   신호 일치: {'✅' if combined.get('agreement', False) else '❌'}")
        else:
            print("   ❌ 신호 분석 실패")
    
    else:
        print("   ❌ 데이터 수집 실패")
    
    print(f"\n3. 시장별 기관매매 요약 테스트")
    market_summary = manager.get_market_institutional_summary(
        date=test_date,
        markets=["KOSPI", "KOSDAQ"]
    )
    
    if not market_summary.empty:
        print(f"   ✅ 수집 성공: {len(market_summary)}개 시장")
        
        for idx, row in market_summary.iterrows():
            market = row.get('market', 'Unknown')
            print(f"   {market} 시장:")
            if 'foreign_net_buy_total' in row:
                print(f"     외국인 순매수: {row.get('foreign_net_buy_total', 0):,.0f}억원")
            if 'institutional_net_buy_total' in row:
                print(f"     기관 순매수: {row.get('institutional_net_buy_total', 0):,.0f}억원")
    else:
        print("   ❌ 시장 요약 수집 실패")
    
    print(f"\n=== 테스트 완료 ===")
    print(f"\n💡 KIS API 사용을 원하시면:")
    print(f"   1. KIS 홈페이지에서 Open API 신청")
    print(f"   2. 환경변수 설정: export KIS_APP_KEY='your_key'")
    print(f"   3. use_kis_api=True로 관리자 생성")

if __name__ == "__main__":
    main()