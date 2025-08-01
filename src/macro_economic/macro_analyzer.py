"""
거시경제 지표 분석기
경제 지표 기반 시장 리스크 및 투자 환경 분석
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
from enum import Enum
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.macro_economic.ecos_collector import ECOSCollector

class EconomicRegime(Enum):
    """경제 체제 분류"""
    GROWTH = "GROWTH"           # 성장기
    STAGFLATION = "STAGFLATION" # 스태그플레이션
    RECESSION = "RECESSION"     # 경기침체
    RECOVERY = "RECOVERY"       # 회복기
    NEUTRAL = "NEUTRAL"         # 중립

class MarketRisk(Enum):
    """시장 리스크 수준"""
    VERY_LOW = "VERY_LOW"       # 매우 낮음
    LOW = "LOW"                 # 낮음
    MODERATE = "MODERATE"       # 보통
    HIGH = "HIGH"               # 높음
    VERY_HIGH = "VERY_HIGH"     # 매우 높음

class MacroAnalyzer:
    """거시경제 지표 분석기"""
    
    def __init__(self, ecos_api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            ecos_api_key: ECOS API 키 (옵션)
        """
        self.ecos_collector = ECOSCollector(ecos_api_key)
        self.logger = self._setup_logger()
        
        # 분석 임계값 설정
        self.thresholds = {
            # 금리 관련
            'rate_volatility_high': 0.5,  # 금리 변동성 높음 기준 (%)
            'rate_increase_significant': 1.0,  # 유의미한 금리 인상 기준 (%)
            
            # 환율 관련
            'fx_volatility_high': 5.0,    # 환율 변동성 높음 기준 (%)
            'fx_depreciation_significant': 10.0,  # 유의미한 환율 상승 기준 (%)
            
            # 인플레이션 관련
            'inflation_target': 2.0,      # 인플레이션 목표 (%)
            'inflation_high': 4.0,        # 고인플레이션 기준 (%)
            
            # 성장률 관련
            'gdp_growth_low': 1.0,        # 저성장 기준 (%)
            'gdp_contraction': 0.0,       # 마이너스 성장 기준
        }
        
        self.logger.info("거시경제 분석기 초기화 완료")
    
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
    
    def analyze_economic_regime(self, 
                              economic_data: pd.DataFrame) -> Dict[str, Any]:
        """
        경제 체제 분석
        
        Args:
            economic_data: 경제 지표 데이터 (피벗된 형태)
            
        Returns:
            경제 체제 분석 결과
        """
        try:
            if economic_data.empty:
                return {'regime': EconomicRegime.NEUTRAL, 'confidence': 0.0}
            
            latest = economic_data.iloc[-1]
            
            # 각 지표별 신호 수집
            signals = []
            
            # 1. GDP 성장률 분석 (전년 동월 대비)
            if 'gdp_yoy' in latest.index and not pd.isna(latest['gdp_yoy']):
                gdp_growth = latest['gdp_yoy']
                if gdp_growth < self.thresholds['gdp_contraction']:
                    signals.append(('recession', 0.8))
                elif gdp_growth < self.thresholds['gdp_growth_low']:
                    signals.append(('recession', 0.4))
                else:
                    signals.append(('growth', 0.6))
            
            # 2. 인플레이션 분석
            if 'consumer_price_yoy' in latest.index and not pd.isna(latest['consumer_price_yoy']):
                inflation = latest['consumer_price_yoy']
                if inflation > self.thresholds['inflation_high']:
                    signals.append(('stagflation', 0.7))
                elif inflation > self.thresholds['inflation_target']:
                    signals.append(('neutral', 0.3))
                else:
                    signals.append(('recovery', 0.4))
            
            # 3. 기준금리 변화 분석
            if 'base_rate_diff' in latest.index and not pd.isna(latest['base_rate_diff']):
                rate_change = latest['base_rate_diff']
                if abs(rate_change) > self.thresholds['rate_increase_significant']:
                    if rate_change > 0:
                        signals.append(('neutral', 0.5))  # 긴축 정책
                    else:
                        signals.append(('recovery', 0.6))  # 완화 정책
            
            # 4. 산업생산지수 분석
            if 'industrial_production_yoy' in latest.index and not pd.isna(latest['industrial_production_yoy']):
                production_growth = latest['industrial_production_yoy']
                if production_growth < -2.0:
                    signals.append(('recession', 0.6))
                elif production_growth > 3.0:
                    signals.append(('growth', 0.7))
            
            # 신호 집계 및 체제 결정
            regime_scores = {
                'growth': 0.0,
                'stagflation': 0.0,
                'recession': 0.0,
                'recovery': 0.0,
                'neutral': 0.0
            }
            
            total_weight = 0.0
            for regime, weight in signals:
                if regime in regime_scores:
                    regime_scores[regime] += weight
                    total_weight += weight
            
            if total_weight > 0:
                for regime in regime_scores:
                    regime_scores[regime] /= total_weight
            
            # 최고 점수 체제 선택
            best_regime = max(regime_scores.items(), key=lambda x: x[1])
            
            regime_mapping = {
                'growth': EconomicRegime.GROWTH,
                'stagflation': EconomicRegime.STAGFLATION,
                'recession': EconomicRegime.RECESSION,
                'recovery': EconomicRegime.RECOVERY,
                'neutral': EconomicRegime.NEUTRAL
            }
            
            return {
                'regime': regime_mapping[best_regime[0]],
                'confidence': best_regime[1],
                'scores': regime_scores,
                'signals_count': len(signals),
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"경제 체제 분석 오류: {str(e)}")
            return {'regime': EconomicRegime.NEUTRAL, 'confidence': 0.0}
    
    def assess_market_risk(self, 
                         economic_data: pd.DataFrame,
                         lookback_periods: int = 6) -> Dict[str, Any]:
        """
        시장 리스크 평가
        
        Args:
            economic_data: 경제 지표 데이터
            lookback_periods: 분석 기간 (개월)
            
        Returns:
            시장 리스크 평가 결과
        """
        try:
            if economic_data.empty or len(economic_data) < lookback_periods:
                return {'risk_level': MarketRisk.MODERATE, 'confidence': 0.0}
            
            recent_data = economic_data.tail(lookback_periods)
            
            risk_factors = []
            
            # 1. 금리 변동성 리스크
            if 'base_rate' in recent_data.columns:
                rate_volatility = recent_data['base_rate'].std()
                if rate_volatility > self.thresholds['rate_volatility_high']:
                    risk_factors.append(('high_volatility', 0.7))
                elif rate_volatility > self.thresholds['rate_volatility_high'] / 2:
                    risk_factors.append(('moderate_volatility', 0.4))
            
            # 2. 환율 변동성 리스크
            if 'usd_krw' in recent_data.columns:
                fx_volatility = recent_data['usd_krw'].pct_change().std() * 100
                if fx_volatility > self.thresholds['fx_volatility_high']:
                    risk_factors.append(('fx_volatility', 0.6))
                
                # 환율 상승 트렌드 (원화 약세)
                fx_change = recent_data['usd_krw'].pct_change(periods=lookback_periods-1).iloc[-1] * 100
                if fx_change > self.thresholds['fx_depreciation_significant']:
                    risk_factors.append(('currency_weakness', 0.8))
            
            # 3. 인플레이션 리스크
            if 'consumer_price_yoy' in economic_data.columns:
                latest_inflation = economic_data['consumer_price_yoy'].iloc[-1]
                if not pd.isna(latest_inflation):
                    if latest_inflation > self.thresholds['inflation_high']:
                        risk_factors.append(('high_inflation', 0.9))
                    elif latest_inflation > self.thresholds['inflation_target'] * 1.5:
                        risk_factors.append(('rising_inflation', 0.5))
            
            # 4. 경제 성장 리스크
            if 'gdp_yoy' in economic_data.columns:
                latest_gdp = economic_data['gdp_yoy'].iloc[-1]
                if not pd.isna(latest_gdp):
                    if latest_gdp < self.thresholds['gdp_contraction']:
                        risk_factors.append(('recession_risk', 1.0))
                    elif latest_gdp < self.thresholds['gdp_growth_low']:
                        risk_factors.append(('slow_growth', 0.6))
            
            # 5. 금리 급변 리스크
            if 'base_rate_diff' in economic_data.columns:
                recent_rate_changes = economic_data['base_rate_diff'].tail(3)
                if (recent_rate_changes > self.thresholds['rate_increase_significant']).any():
                    risk_factors.append(('rate_shock', 0.7))
            
            # 리스크 점수 계산
            total_risk_score = sum(weight for _, weight in risk_factors)
            risk_count = len(risk_factors)
            
            if risk_count == 0:
                risk_level = MarketRisk.LOW
                confidence = 0.3
            else:
                avg_risk_score = total_risk_score / risk_count
                
                if avg_risk_score >= 0.8:
                    risk_level = MarketRisk.VERY_HIGH
                elif avg_risk_score >= 0.6:
                    risk_level = MarketRisk.HIGH
                elif avg_risk_score >= 0.4:
                    risk_level = MarketRisk.MODERATE
                elif avg_risk_score >= 0.2:
                    risk_level = MarketRisk.LOW
                else:
                    risk_level = MarketRisk.VERY_LOW
                
                confidence = min(0.95, 0.5 + risk_count * 0.1)
            
            return {
                'risk_level': risk_level,
                'confidence': confidence,
                'risk_score': total_risk_score,
                'risk_factors': risk_factors,
                'risk_factors_count': risk_count,
                'analysis_period': lookback_periods,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"시장 리스크 평가 오류: {str(e)}")
            return {'risk_level': MarketRisk.MODERATE, 'confidence': 0.0}
    
    def generate_macro_signals(self, 
                             economic_data: pd.DataFrame) -> Dict[str, Any]:
        """
        거시경제 기반 투자 신호 생성
        
        Args:
            economic_data: 경제 지표 데이터
            
        Returns:
            투자 신호 및 권장사항
        """
        try:
            # 경제 체제 분석
            regime_analysis = self.analyze_economic_regime(economic_data)
            
            # 시장 리스크 평가
            risk_analysis = self.assess_market_risk(economic_data)
            
            # 신호 생성
            signals = {
                'equity_signal': 0,      # 주식 신호 (-1: 매도, 0: 중립, 1: 매수)
                'bond_signal': 0,        # 채권 신호
                'cash_signal': 0,        # 현금 신호
                'defensive_signal': 0,   # 방어적 투자 신호
                'signal_strength': 0.0,  # 신호 강도 (0~1)
                'confidence': 0.0        # 신호 신뢰도 (0~1)
            }
            
            regime = regime_analysis.get('regime', EconomicRegime.NEUTRAL)
            risk_level = risk_analysis.get('risk_level', MarketRisk.MODERATE)
            
            # 경제 체제별 기본 신호
            if regime == EconomicRegime.GROWTH:
                signals['equity_signal'] = 1
                signals['bond_signal'] = -1
                signals['signal_strength'] = 0.7
            elif regime == EconomicRegime.RECOVERY:
                signals['equity_signal'] = 1
                signals['bond_signal'] = 0
                signals['signal_strength'] = 0.6
            elif regime == EconomicRegime.RECESSION:
                signals['equity_signal'] = -1
                signals['bond_signal'] = 1
                signals['cash_signal'] = 1
                signals['signal_strength'] = 0.8
            elif regime == EconomicRegime.STAGFLATION:
                signals['equity_signal'] = -1
                signals['bond_signal'] = -1
                signals['defensive_signal'] = 1
                signals['signal_strength'] = 0.6
            else:  # NEUTRAL
                signals['signal_strength'] = 0.3
            
            # 리스크 수준에 따른 신호 조정
            if risk_level in [MarketRisk.HIGH, MarketRisk.VERY_HIGH]:
                signals['equity_signal'] = min(0, signals['equity_signal'])  # 주식 비중 축소
                signals['cash_signal'] = 1  # 현금 비중 확대
                signals['defensive_signal'] = 1  # 방어적 투자 확대
                signals['signal_strength'] *= 1.2  # 신호 강도 증폭
            elif risk_level == MarketRisk.LOW:
                if signals['equity_signal'] <= 0:
                    signals['equity_signal'] = 0  # 중립으로 조정
            
            # 신뢰도 계산
            regime_confidence = regime_analysis.get('confidence', 0.0)
            risk_confidence = risk_analysis.get('confidence', 0.0)
            signals['confidence'] = (regime_confidence + risk_confidence) / 2
            
            # 권장사항 생성
            recommendations = self._generate_recommendations(regime, risk_level, signals)
            
            return {
                'signals': signals,
                'regime_analysis': regime_analysis,
                'risk_analysis': risk_analysis,
                'recommendations': recommendations,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"거시경제 신호 생성 오류: {str(e)}")
            return {'signals': signals}
    
    def _generate_recommendations(self, 
                                regime: EconomicRegime,
                                risk_level: MarketRisk,
                                signals: Dict[str, Any]) -> List[str]:
        """투자 권장사항 생성"""
        recommendations = []
        
        # 경제 체제별 권장사항
        if regime == EconomicRegime.GROWTH:
            recommendations.append("성장기: 성장주 및 기술주 비중 확대 고려")
            recommendations.append("금리 상승 압력으로 장기채권 주의")
        elif regime == EconomicRegime.RECOVERY:
            recommendations.append("회복기: 경기민감주 및 소형주 투자 기회")
            recommendations.append("부동산 및 원자재 관련 자산 고려")
        elif regime == EconomicRegime.RECESSION:
            recommendations.append("경기침체: 방어주 및 고배당주 선호")
            recommendations.append("정부채권 및 현금 비중 확대")
        elif regime == EconomicRegime.STAGFLATION:
            recommendations.append("스태그플레이션: 인플레이션 헤지 자산 고려")
            recommendations.append("원자재, 부동산, 인플레이션 연동채권 검토")
        
        # 리스크 수준별 권장사항
        if risk_level in [MarketRisk.HIGH, MarketRisk.VERY_HIGH]:
            recommendations.append("고위험 환경: 포트폴리오 방어 포지션 강화")
            recommendations.append("변동성 확대 대비 헤지 전략 검토")
        elif risk_level == MarketRisk.LOW:
            recommendations.append("저위험 환경: 위험자산 비중 확대 고려")
            recommendations.append("레버리지 전략 활용 검토")
        
        # 신호별 구체적 권장사항
        if signals['defensive_signal'] > 0:
            recommendations.append("방어적 자산 배분: 유틸리티, 필수소비재 섹터 고려")
        
        if signals['cash_signal'] > 0:
            recommendations.append("현금 비중 확대: 단기 자금시장 펀드 활용")
        
        return recommendations
    
    def get_latest_macro_analysis(self, months_back: int = 12) -> Dict[str, Any]:
        """
        최신 거시경제 분석 실행
        
        Args:
            months_back: 분석할 과거 개월 수
            
        Returns:
            완전한 거시경제 분석 결과
        """
        try:
            self.logger.info(f"최신 거시경제 분석 시작 ({months_back}개월)")
            
            # 핵심 지표 수집
            key_indicators = [
                'base_rate', 'usd_krw', 'consumer_price', 
                'gdp', 'industrial_production', 'bond_10y'
            ]
            
            # 데이터 수집
            raw_data = self.ecos_collector.get_latest_indicators(key_indicators, months_back)
            
            if raw_data.empty:
                self.logger.warning("경제 지표 데이터를 수집할 수 없습니다.")
                return {'error': 'No data available'}
            
            # 데이터 변환
            pivot_data = self.ecos_collector.pivot_indicators_by_date(raw_data)
            economic_data = self.ecos_collector.calculate_indicator_changes(pivot_data)
            
            # 분석 실행
            macro_analysis = self.generate_macro_signals(economic_data)
            
            # 데이터 요약 추가
            macro_analysis['data_summary'] = {
                'data_points': len(economic_data),
                'indicators_count': len([col for col in economic_data.columns if col != 'date']),
                'data_period': f"{economic_data['date'].min().strftime('%Y-%m')} ~ {economic_data['date'].max().strftime('%Y-%m')}",
                'latest_values': {}
            }
            
            # 최신 값들 저장
            if not economic_data.empty:
                latest = economic_data.iloc[-1]
                for indicator in key_indicators:
                    if indicator in latest.index and not pd.isna(latest[indicator]):
                        macro_analysis['data_summary']['latest_values'][indicator] = float(latest[indicator])
            
            self.logger.info("거시경제 분석 완료")
            return macro_analysis
            
        except Exception as e:
            self.logger.error(f"최신 거시경제 분석 오류: {str(e)}")
            return {'error': str(e)}


def main():
    """테스트 실행"""
    print("=== 거시경제 지표 분석기 테스트 ===")
    
    analyzer = MacroAnalyzer()
    
    # 시뮬레이션 데이터로 테스트
    print("\n1. 시뮬레이션 데이터로 분석 테스트")
    
    # 가상의 경제 데이터 생성
    dates = pd.date_range('2023-01-01', '2024-12-01', freq='MS')
    
    # 성장기 시나리오 시뮬레이션
    simulation_data = pd.DataFrame({
        'date': dates,
        'base_rate': np.linspace(1.0, 3.5, len(dates)) + np.random.normal(0, 0.1, len(dates)),
        'usd_krw': np.linspace(1300, 1350, len(dates)) + np.random.normal(0, 20, len(dates)),
        'consumer_price': np.full(len(dates), 2.5) + np.random.normal(0, 0.5, len(dates)),
        'gdp': np.full(len(dates), 2.8) + np.random.normal(0, 0.3, len(dates)),
        'industrial_production': np.full(len(dates), 3.2) + np.random.normal(0, 1.0, len(dates)),
        'bond_10y': np.linspace(2.5, 4.0, len(dates)) + np.random.normal(0, 0.2, len(dates))
    })
    
    # 변화율 컬럼 추가 (시뮬레이션)
    for col in ['base_rate', 'consumer_price', 'gdp', 'industrial_production']:
        simulation_data[f'{col}_yoy'] = simulation_data[col].pct_change(periods=12) * 100
        simulation_data[f'{col}_diff'] = simulation_data[col].diff()
    
    # 경제 체제 분석
    regime_result = analyzer.analyze_economic_regime(simulation_data)
    print(f"   경제 체제: {regime_result['regime'].value}")
    print(f"   신뢰도: {regime_result['confidence']:.2f}")
    print(f"   분석 신호 수: {regime_result.get('signals_count', 0)}개")
    
    # 시장 리스크 평가
    risk_result = analyzer.assess_market_risk(simulation_data)
    print(f"   시장 리스크: {risk_result['risk_level'].value}")
    print(f"   리스크 점수: {risk_result.get('risk_score', 0):.2f}")
    print(f"   리스크 요인: {risk_result.get('risk_factors_count', 0)}개")
    
    # 투자 신호 생성
    signals_result = analyzer.generate_macro_signals(simulation_data)
    signals = signals_result.get('signals', {})
    
    print(f"\n2. 투자 신호 결과")
    print(f"   주식 신호: {signals.get('equity_signal', 0)} ({'매수' if signals.get('equity_signal', 0) > 0 else '매도' if signals.get('equity_signal', 0) < 0 else '중립'})")
    print(f"   채권 신호: {signals.get('bond_signal', 0)}")
    print(f"   현금 신호: {signals.get('cash_signal', 0)}")
    print(f"   방어 신호: {signals.get('defensive_signal', 0)}")
    print(f"   신호 강도: {signals.get('signal_strength', 0):.2f}")
    print(f"   신뢰도: {signals.get('confidence', 0):.2f}")
    
    # 권장사항
    recommendations = signals_result.get('recommendations', [])
    print(f"\n3. 투자 권장사항 ({len(recommendations)}개)")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # 실제 API 테스트 (API 키가 있는 경우)
    if analyzer.ecos_collector.api_key:
        print(f"\n4. 실제 API 데이터 분석 테스트")
        try:
            real_analysis = analyzer.get_latest_macro_analysis(months_back=6)
            
            if 'error' not in real_analysis:
                print("   ✅ 실제 데이터 분석 성공")
                
                data_summary = real_analysis.get('data_summary', {})
                print(f"   데이터 기간: {data_summary.get('data_period', 'Unknown')}")
                print(f"   데이터 포인트: {data_summary.get('data_points', 0)}개")
                print(f"   지표 수: {data_summary.get('indicators_count', 0)}개")
                
                real_signals = real_analysis.get('signals', {})
                print(f"   실제 주식 신호: {real_signals.get('equity_signal', 0)}")
                print(f"   실제 신호 강도: {real_signals.get('signal_strength', 0):.2f}")
            else:
                print(f"   ❌ 실제 데이터 분석 실패: {real_analysis['error']}")
        except Exception as e:
            print(f"   ❌ 실제 API 테스트 오류: {str(e)}")
    else:
        print(f"\n4. 실제 API 키가 없어 시뮬레이션만 실행")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()