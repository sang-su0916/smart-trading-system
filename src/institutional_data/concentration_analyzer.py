"""
외국인·기관 순매수 집중도 분석기
종목별/섹터별 외국인·기관 자금 집중도 분석 및 핫머니 추적
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import sys
import os
from collections import defaultdict

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.institutional_data.institutional_data_manager import InstitutionalDataManager

class ConcentrationAnalyzer:
    """외국인·기관 순매수 집중도 분석기"""
    
    def __init__(self, 
                 concentration_threshold: float = 0.7,  # 집중도 임계값
                 hot_money_threshold: float = 500,      # 핫머니 임계값 (억원)
                 analysis_period: int = 10):            # 분석 기간 (일)
        """
        초기화
        
        Args:
            concentration_threshold: 집중도 임계값 (0~1)
            hot_money_threshold: 핫머니 감지 임계값 (억원)
            analysis_period: 분석 기간 (일)
        """
        self.concentration_threshold = concentration_threshold
        self.hot_money_threshold = hot_money_threshold
        self.analysis_period = analysis_period
        self.logger = self._setup_logger()
        
        # 기관 데이터 관리자 초기화
        self.data_manager = InstitutionalDataManager(
            use_pykrx=True,
            use_kis_api=False
        )
        
        self.logger.info("외국인·기관 집중도 분석기 초기화 완료")
        
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
    
    def analyze_market_concentration(self, 
                                   symbols: List[str],
                                   analysis_date: str = None) -> pd.DataFrame:
        """
        시장 전체 집중도 분석
        
        Args:
            symbols: 분석 대상 종목 리스트
            analysis_date: 분석 기준일 (YYYYMMDD, None이면 최근일)
            
        Returns:
            집중도 분석 결과 DataFrame
        """
        try:
            if analysis_date is None:
                analysis_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            
            start_date = (datetime.now() - timedelta(days=self.analysis_period * 2)).strftime("%Y%m%d")
            
            self.logger.info(f"시장 집중도 분석 시작: {len(symbols)}개 종목")
            
            concentration_results = []
            
            for symbol in symbols:
                try:
                    # 개별 종목 데이터 수집
                    stock_data = self.data_manager.collect_comprehensive_institutional_data(
                        symbol, start_date, analysis_date
                    )
                    
                    if not stock_data.empty:
                        # 집중도 계산
                        concentration = self._calculate_stock_concentration(stock_data, symbol)
                        if concentration:
                            concentration_results.append(concentration)
                    
                except Exception as e:
                    self.logger.warning(f"종목 {symbol} 집중도 분석 실패: {str(e)}")
                    continue
            
            if concentration_results:
                result_df = pd.DataFrame(concentration_results)
                
                # 집중도 순 정렬
                result_df = result_df.sort_values('total_concentration_score', ascending=False)
                
                # 집중도 등급 부여
                result_df = self._assign_concentration_grades(result_df)
                
                self.logger.info(f"시장 집중도 분석 완료: {len(result_df)}개 종목")
                return result_df
            else:
                self.logger.warning("집중도 분석 결과 없음")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"시장 집중도 분석 오류: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_stock_concentration(self, data: pd.DataFrame, symbol: str) -> Optional[Dict[str, Any]]:
        """개별 종목 집중도 계산"""
        try:
            if data.empty:
                return None
            
            # 최근 데이터로 제한
            recent_data = data.tail(self.analysis_period)
            
            concentration_info = {
                'symbol': symbol,
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'analysis_period': len(recent_data)
            }
            
            # 1. 외국인 집중도 분석
            if 'foreign_value' in recent_data.columns:
                foreign_analysis = self._analyze_investor_concentration(
                    recent_data['foreign_value'], 'foreign'
                )
                concentration_info.update(foreign_analysis)
            
            # 2. 기관 집중도 분석
            institutional_cols = ['institutional_total_value', 'institutional_net_buy_value']
            for col in institutional_cols:
                if col in recent_data.columns:
                    institutional_analysis = self._analyze_investor_concentration(
                        recent_data[col], 'institutional'
                    )
                    concentration_info.update(institutional_analysis)
                    break
            
            # 3. 통합 집중도 점수 계산
            concentration_info['total_concentration_score'] = self._calculate_total_concentration_score(
                concentration_info
            )
            
            # 4. 핫머니 감지
            concentration_info['hot_money_detected'] = self._detect_hot_money(recent_data)
            
            # 5. 집중도 추세 분석
            concentration_info['concentration_trend'] = self._analyze_concentration_trend(recent_data)
            
            return concentration_info
            
        except Exception as e:
            self.logger.error(f"종목 {symbol} 집중도 계산 오류: {str(e)}")
            return None
    
    def _analyze_investor_concentration(self, 
                                     values: pd.Series, 
                                     investor_type: str) -> Dict[str, Any]:
        """투자자별 집중도 분석"""
        try:
            values = values.fillna(0)
            analysis = {}
            prefix = f"{investor_type}_"
            
            # 기본 통계
            total_volume = abs(values).sum()
            net_volume = values.sum()
            positive_days = (values > 0).sum()
            negative_days = (values < 0).sum()
            total_days = len(values)
            
            analysis[f"{prefix}total_volume"] = float(total_volume)
            analysis[f"{prefix}net_volume"] = float(net_volume)
            analysis[f"{prefix}positive_days"] = int(positive_days)
            analysis[f"{prefix}negative_days"] = int(negative_days)
            
            # 집중도 지표들
            if total_days > 0:
                # 1. 방향성 일관성 (같은 방향 거래 비율)
                if net_volume > 0:
                    consistency = positive_days / total_days
                else:
                    consistency = negative_days / total_days
                
                analysis[f"{prefix}consistency"] = float(consistency)
                
                # 2. 거래 집중도 (대량 거래일 비율)
                large_trade_threshold = total_volume / total_days * 2  # 평균의 2배
                large_trade_days = (abs(values) > large_trade_threshold).sum()
                trade_concentration = large_trade_days / total_days
                
                analysis[f"{prefix}trade_concentration"] = float(trade_concentration)
                
                # 3. 변동성 집중도 (표준편차 대비 평균)
                if values.std() > 0:
                    volatility_concentration = abs(values.mean()) / values.std()
                else:
                    volatility_concentration = 0
                
                analysis[f"{prefix}volatility_concentration"] = float(volatility_concentration)
                
                # 4. 종합 집중도 점수 (0~1)
                concentration_score = (
                    consistency * 0.4 +
                    trade_concentration * 0.3 +
                    min(1.0, volatility_concentration / 2) * 0.3
                )
                
                analysis[f"{prefix}concentration_score"] = float(concentration_score)
                
                # 5. 집중도 등급
                if concentration_score >= 0.8:
                    grade = 'VERY_HIGH'
                elif concentration_score >= 0.6:
                    grade = 'HIGH'
                elif concentration_score >= 0.4:
                    grade = 'MEDIUM'
                elif concentration_score >= 0.2:
                    grade = 'LOW'
                else:
                    grade = 'VERY_LOW'
                
                analysis[f"{prefix}concentration_grade"] = grade
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"{investor_type} 집중도 분석 오류: {str(e)}")
            return {}
    
    def _calculate_total_concentration_score(self, concentration_info: Dict[str, Any]) -> float:
        """통합 집중도 점수 계산"""
        try:
            foreign_score = concentration_info.get('foreign_concentration_score', 0)
            institutional_score = concentration_info.get('institutional_concentration_score', 0)
            
            # 외국인과 기관의 가중 평균 (외국인 60%, 기관 40%)
            total_score = foreign_score * 0.6 + institutional_score * 0.4
            
            # 핫머니 보너스
            if concentration_info.get('hot_money_detected', False):
                total_score = min(1.0, total_score * 1.2)
            
            return float(total_score)
            
        except Exception as e:
            self.logger.error(f"통합 집중도 점수 계산 오류: {str(e)}")
            return 0.0
    
    def _detect_hot_money(self, data: pd.DataFrame) -> bool:
        """핫머니 감지"""
        try:
            # 핫머니 조건들
            conditions = []
            
            # 1. 대량 거래 감지
            for col in ['foreign_value', 'institutional_total_value']:
                if col in data.columns:
                    values = data[col].abs()
                    large_trades = (values > self.hot_money_threshold).sum()
                    if large_trades >= 2:  # 2일 이상 대량 거래
                        conditions.append(True)
            
            # 2. 급격한 변화 감지
            for col in ['foreign_value', 'institutional_total_value']:
                if col in data.columns:
                    values = data[col]
                    if len(values) >= 3:
                        # 최근 3일 중 급격한 변화
                        recent_change = abs(values.iloc[-1] - values.iloc[-3])
                        if recent_change > self.hot_money_threshold:
                            conditions.append(True)
            
            # 핫머니 감지: 조건 중 하나라도 충족
            return any(conditions)
            
        except Exception as e:
            self.logger.error(f"핫머니 감지 오류: {str(e)}")
            return False
    
    def _analyze_concentration_trend(self, data: pd.DataFrame) -> str:
        """집중도 추세 분석"""
        try:
            if len(data) < 3:
                return 'INSUFFICIENT_DATA'
            
            # 전반부와 후반부 비교
            mid_point = len(data) // 2
            first_half = data.iloc[:mid_point]
            second_half = data.iloc[mid_point:]
            
            trend_scores = []
            
            # 외국인 추세
            if 'foreign_value' in data.columns:
                first_foreign = first_half['foreign_value'].abs().mean()
                second_foreign = second_half['foreign_value'].abs().mean()
                
                if second_foreign > first_foreign * 1.2:
                    trend_scores.append(1)  # 상승
                elif second_foreign < first_foreign * 0.8:
                    trend_scores.append(-1)  # 하락
                else:
                    trend_scores.append(0)  # 유지
            
            # 기관 추세
            institutional_cols = ['institutional_total_value', 'institutional_net_buy_value']
            for col in institutional_cols:
                if col in data.columns:
                    first_inst = first_half[col].abs().mean()
                    second_inst = second_half[col].abs().mean()
                    
                    if second_inst > first_inst * 1.2:
                        trend_scores.append(1)
                    elif second_inst < first_inst * 0.8:
                        trend_scores.append(-1)
                    else:
                        trend_scores.append(0)
                    break
            
            # 전체 추세 결정
            if not trend_scores:
                return 'NO_DATA'
            
            avg_trend = sum(trend_scores) / len(trend_scores)
            
            if avg_trend > 0.5:
                return 'INCREASING'
            elif avg_trend < -0.5:
                return 'DECREASING'
            else:
                return 'STABLE'
            
        except Exception as e:
            self.logger.error(f"집중도 추세 분석 오류: {str(e)}")
            return 'ERROR'
    
    def _assign_concentration_grades(self, df: pd.DataFrame) -> pd.DataFrame:
        """집중도 등급 부여"""
        try:
            result = df.copy()
            
            # 백분위수 기반 등급 부여
            scores = result['total_concentration_score']
            
            result['concentration_rank'] = range(1, len(result) + 1)
            
            # 등급 부여
            result['overall_grade'] = 'D'
            
            # 상위 5% - S등급
            top_5_pct = max(1, int(len(result) * 0.05))
            result.iloc[:top_5_pct, result.columns.get_loc('overall_grade')] = 'S'
            
            # 상위 5~15% - A등급
            top_15_pct = max(1, int(len(result) * 0.15))
            result.iloc[top_5_pct:top_15_pct, result.columns.get_loc('overall_grade')] = 'A'
            
            # 상위 15~40% - B등급
            top_40_pct = max(1, int(len(result) * 0.40))
            result.iloc[top_15_pct:top_40_pct, result.columns.get_loc('overall_grade')] = 'B'
            
            # 상위 40~70% - C등급
            top_70_pct = max(1, int(len(result) * 0.70))
            result.iloc[top_40_pct:top_70_pct, result.columns.get_loc('overall_grade')] = 'C'
            
            return result
            
        except Exception as e:
            self.logger.error(f"집중도 등급 부여 오류: {str(e)}")
            return df
    
    def get_hot_money_alerts(self, concentration_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """핫머니 알림 생성"""
        try:
            alerts = []
            
            if concentration_data.empty:
                return alerts
            
            # 핫머니 감지된 종목들
            hot_money_stocks = concentration_data[
                concentration_data['hot_money_detected'] == True
            ]
            
            for idx, stock in hot_money_stocks.iterrows():
                alert = {
                    'symbol': stock['symbol'],
                    'alert_type': 'HOT_MONEY',
                    'concentration_score': stock.get('total_concentration_score', 0),
                    'concentration_grade': stock.get('overall_grade', 'N/A'),
                    'concentration_trend': stock.get('concentration_trend', 'UNKNOWN'),
                    'foreign_net_volume': stock.get('foreign_net_volume', 0),
                    'institutional_net_volume': stock.get('institutional_net_volume', 0),
                    'alert_time': datetime.now().isoformat(),
                    'priority': self._calculate_alert_priority(stock)
                }
                
                alerts.append(alert)
            
            # 우선순위 순 정렬
            alerts.sort(key=lambda x: x['priority'], reverse=True)
            
            self.logger.info(f"핫머니 알림 생성: {len(alerts)}개")
            return alerts
            
        except Exception as e:
            self.logger.error(f"핫머니 알림 생성 오류: {str(e)}")
            return []
    
    def _calculate_alert_priority(self, stock_data: pd.Series) -> float:
        """알림 우선순위 계산"""
        try:
            priority = 0.0
            
            # 집중도 점수 (0~50점)
            concentration_score = stock_data.get('total_concentration_score', 0)
            priority += concentration_score * 50
            
            # 등급 보너스 (0~30점)
            grade = stock_data.get('overall_grade', 'D')
            grade_bonus = {'S': 30, 'A': 25, 'B': 15, 'C': 5, 'D': 0}
            priority += grade_bonus.get(grade, 0)
            
            # 추세 보너스 (0~20점)
            trend = stock_data.get('concentration_trend', 'STABLE')
            trend_bonus = {'INCREASING': 20, 'STABLE': 10, 'DECREASING': 0}
            priority += trend_bonus.get(trend, 0)
            
            return priority
            
        except Exception as e:
            self.logger.error(f"알림 우선순위 계산 오류: {str(e)}")
            return 0.0
    
    def analyze_sector_concentration(self, 
                                   sector_symbols: Dict[str, List[str]]) -> pd.DataFrame:
        """섹터별 집중도 분석"""
        try:
            self.logger.info(f"섹터별 집중도 분석 시작: {len(sector_symbols)}개 섹터")
            
            sector_results = []
            
            for sector_name, symbols in sector_symbols.items():
                try:
                    # 섹터 내 종목들 분석
                    sector_data = self.analyze_market_concentration(symbols)
                    
                    if not sector_data.empty:
                        # 섹터 요약 계산
                        sector_summary = self._calculate_sector_summary(
                            sector_data, sector_name
                        )
                        sector_results.append(sector_summary)
                
                except Exception as e:
                    self.logger.warning(f"섹터 {sector_name} 분석 실패: {str(e)}")
                    continue
            
            if sector_results:
                result_df = pd.DataFrame(sector_results)
                result_df = result_df.sort_values('sector_concentration_score', ascending=False)
                
                self.logger.info(f"섹터별 집중도 분석 완료: {len(result_df)}개 섹터")
                return result_df
            else:
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"섹터별 집중도 분석 오류: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_sector_summary(self, 
                                sector_data: pd.DataFrame, 
                                sector_name: str) -> Dict[str, Any]:
        """섹터 요약 계산"""
        try:
            summary = {
                'sector_name': sector_name,
                'total_stocks': len(sector_data),
                'analysis_date': datetime.now().strftime('%Y-%m-%d')
            }
            
            # 집중도 통계
            summary['avg_concentration_score'] = float(sector_data['total_concentration_score'].mean())
            summary['max_concentration_score'] = float(sector_data['total_concentration_score'].max())
            summary['min_concentration_score'] = float(sector_data['total_concentration_score'].min())
            
            # 등급 분포
            grade_counts = sector_data['overall_grade'].value_counts().to_dict()
            for grade in ['S', 'A', 'B', 'C', 'D']:
                summary[f'{grade}_grade_count'] = grade_counts.get(grade, 0)
            
            # 핫머니 통계
            hot_money_count = (sector_data['hot_money_detected'] == True).sum()
            summary['hot_money_stocks'] = int(hot_money_count)
            summary['hot_money_ratio'] = float(hot_money_count / len(sector_data))
            
            # 추세 분포
            trend_counts = sector_data['concentration_trend'].value_counts().to_dict()
            summary['increasing_trend_count'] = trend_counts.get('INCREASING', 0)
            summary['stable_trend_count'] = trend_counts.get('STABLE', 0)
            summary['decreasing_trend_count'] = trend_counts.get('DECREASING', 0)
            
            # 섹터 집중도 점수 (0~100)
            sector_score = (
                summary['avg_concentration_score'] * 50 +  # 평균 집중도
                summary['hot_money_ratio'] * 30 +         # 핫머니 비율
                (summary['S_grade_count'] + summary['A_grade_count']) / summary['total_stocks'] * 20  # 고등급 비율
            )
            
            summary['sector_concentration_score'] = float(sector_score)
            
            # 섹터 등급
            if sector_score >= 80:
                summary['sector_grade'] = 'VERY_HIGH'
            elif sector_score >= 60:
                summary['sector_grade'] = 'HIGH'
            elif sector_score >= 40:
                summary['sector_grade'] = 'MEDIUM'
            elif sector_score >= 20:
                summary['sector_grade'] = 'LOW'
            else:
                summary['sector_grade'] = 'VERY_LOW'
            
            return summary
            
        except Exception as e:
            self.logger.error(f"섹터 요약 계산 오류: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    print("=== 외국인·기관 순매수 집중도 분석기 테스트 ===")
    
    analyzer = ConcentrationAnalyzer(
        concentration_threshold=0.7,
        hot_money_threshold=200,  # 200억원
        analysis_period=10
    )
    
    # 테스트용 종목 리스트
    test_symbols = ["005930", "000660", "005490", "005380", "051910"]  # 주요 대형주
    
    print(f"\n1. 시장 집중도 분석 테스트 ({len(test_symbols)}개 종목)")
    concentration_data = analyzer.analyze_market_concentration(test_symbols)
    
    if not concentration_data.empty:
        print(f"   ✅ 분석 성공: {len(concentration_data)}개 종목")
        
        # 상위 종목 출력
        print(f"\n   상위 3개 종목:")
        for idx, row in concentration_data.head(3).iterrows():
            symbol = row['symbol']
            score = row['total_concentration_score']
            grade = row.get('overall_grade', 'N/A')
            trend = row.get('concentration_trend', 'UNKNOWN')
            hot_money = row.get('hot_money_detected', False)
            
            print(f"   {idx+1}. {symbol}")
            print(f"      집중도 점수: {score:.3f} (등급: {grade})")
            print(f"      추세: {trend}")
            print(f"      핫머니: {'🔥' if hot_money else '❌'}")
            
            if 'foreign_concentration_score' in row:
                print(f"      외국인 집중도: {row['foreign_concentration_score']:.3f}")
            if 'institutional_concentration_score' in row:
                print(f"      기관 집중도: {row['institutional_concentration_score']:.3f}")
        
        print(f"\n2. 핫머니 알림 생성 테스트")
        hot_money_alerts = analyzer.get_hot_money_alerts(concentration_data)
        
        if hot_money_alerts:
            print(f"   ✅ 핫머니 알림: {len(hot_money_alerts)}개")
            for alert in hot_money_alerts[:3]:  # 상위 3개만 출력
                print(f"   🔥 {alert['symbol']}: 우선순위 {alert['priority']:.1f}")
                print(f"      등급: {alert['concentration_grade']}, 추세: {alert['concentration_trend']}")
        else:
            print(f"   ❌ 핫머니 알림 없음")
        
        print(f"\n3. 섹터별 집중도 분석 테스트")
        # 테스트용 섹터 구성
        test_sectors = {
            "기술주": ["005930", "000660"],  # 삼성전자, SK하이닉스
            "제조업": ["005490", "005380"],  # POSCO홀딩스, 현대차
            "통신": ["051910"]              # LG화학
        }
        
        sector_data = analyzer.analyze_sector_concentration(test_sectors)
        
        if not sector_data.empty:
            print(f"   ✅ 섹터 분석 성공: {len(sector_data)}개 섹터")
            
            for idx, row in sector_data.iterrows():
                sector_name = row['sector_name']
                sector_score = row['sector_concentration_score']
                sector_grade = row['sector_grade']
                hot_money_ratio = row.get('hot_money_ratio', 0)
                
                print(f"   📊 {sector_name}: {sector_score:.1f}점 ({sector_grade})")
                print(f"      핫머니 비율: {hot_money_ratio:.1%}")
                print(f"      종목 수: {row['total_stocks']}개")
        else:
            print(f"   ❌ 섹터 분석 실패")
        
    else:
        print("   ❌ 집중도 분석 실패")
    
    print(f"\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()