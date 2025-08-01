"""
통합 거시경제 분석기
한국 경제지표(ECOS) + 미국 시장 동향을 통합한 종합 거시경제 분석
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
from enum import Enum
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.macro_economic.macro_analyzer import MacroAnalyzer, EconomicRegime, MarketRisk
from src.macro_economic.us_market_collector import USMarketCollector

class GlobalMarketRegime(Enum):
    """글로벌 시장 체제"""
    RISK_ON = "RISK_ON"                 # 위험자산 선호
    RISK_OFF = "RISK_OFF"               # 안전자산 선호
    MIXED_SIGNALS = "MIXED_SIGNALS"     # 혼재된 신호
    TRANSITION = "TRANSITION"           # 전환기
    UNCERTAIN = "UNCERTAIN"             # 불확실

class IntegratedMacroAnalyzer:
    """통합 거시경제 분석기"""
    
    def __init__(self, ecos_api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            ecos_api_key: ECOS API 키 (옵션)
        """
        self.macro_analyzer = MacroAnalyzer(ecos_api_key)
        self.us_market_collector = USMarketCollector()
        self.logger = self._setup_logger()
        
        # 통합 분석 가중치
        self.weights = {
            'korean_macro': 0.4,    # 한국 거시경제 가중치
            'us_market': 0.4,       # 미국 시장 가중치
            'global_sentiment': 0.2  # 글로벌 심리 가중치
        }
        
        self.logger.info("통합 거시경제 분석기 초기화 완료")
    
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
    
    def analyze_integrated_macro_environment(self, 
                                           analysis_period_months: int = 12) -> Dict[str, Any]:
        """
        통합 거시경제 환경 분석
        
        Args:
            analysis_period_months: 분석 기간 (개월)
            
        Returns:
            통합 거시경제 분석 결과
        """
        try:
            self.logger.info(f"통합 거시경제 분석 시작 ({analysis_period_months}개월)")
            
            # 1. 한국 거시경제 분석
            korean_analysis = self._analyze_korean_macro(analysis_period_months)
            
            # 2. 미국 시장 분석
            us_analysis = self._analyze_us_market()
            
            # 3. 글로벌 시장 심리 분석
            sentiment_analysis = self._analyze_global_sentiment()
            
            # 4. 통합 분석
            integrated_result = self._integrate_analyses(
                korean_analysis, us_analysis, sentiment_analysis
            )
            
            # 5. 투자 권장사항 생성
            recommendations = self._generate_integrated_recommendations(integrated_result)
            
            final_result = {
                'integrated_analysis': integrated_result,
                'korean_macro': korean_analysis,
                'us_market': us_analysis,
                'global_sentiment': sentiment_analysis,
                'recommendations': recommendations,
                'analysis_date': datetime.now().isoformat(),
                'analysis_period_months': analysis_period_months
            }
            
            self.logger.info("통합 거시경제 분석 완료")
            return final_result
            
        except Exception as e:
            self.logger.error(f"통합 거시경제 분석 오류: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_korean_macro(self, months: int) -> Dict[str, Any]:
        """한국 거시경제 분석"""
        try:
            self.logger.info("한국 거시경제 분석 실행")
            
            # 한국 거시경제 분석 실행
            korean_result = self.macro_analyzer.get_latest_macro_analysis(months)
            
            if 'error' in korean_result:
                self.logger.warning(f"한국 거시경제 분석 실패: {korean_result['error']}")
                return {'status': 'failed', 'error': korean_result['error']}
            
            # 핵심 지표 추출
            signals = korean_result.get('signals', {})
            regime_analysis = korean_result.get('regime_analysis', {})
            risk_analysis = korean_result.get('risk_analysis', {})
            
            return {
                'status': 'success',
                'regime': regime_analysis.get('regime', EconomicRegime.NEUTRAL).value,
                'regime_confidence': regime_analysis.get('confidence', 0.0),
                'risk_level': risk_analysis.get('risk_level', MarketRisk.MODERATE).value,
                'risk_confidence': risk_analysis.get('confidence', 0.0),
                'equity_signal': signals.get('equity_signal', 0),
                'signal_strength': signals.get('signal_strength', 0.0),
                'signal_confidence': signals.get('confidence', 0.0),
                'full_analysis': korean_result
            }
            
        except Exception as e:
            self.logger.error(f"한국 거시경제 분석 오류: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _analyze_us_market(self) -> Dict[str, Any]:
        """미국 시장 분석"""
        try:
            self.logger.info("미국 시장 분석 실행")
            
            # 미국 주요 지수 데이터 수집
            us_data = self.us_market_collector.get_key_indices(period="1y")
            
            if us_data.empty:
                self.logger.warning("미국 시장 데이터 수집 실패")
                return {'status': 'failed', 'error': 'No US market data'}
            
            # 시장 지표 계산
            calculated_data = self.us_market_collector.calculate_market_indicators(us_data)
            
            # 시장 체제 분석
            regime_analysis = self.us_market_collector.analyze_market_regime(calculated_data)
            
            # 최신 시장 상황 요약
            latest = calculated_data.iloc[-1]
            
            return {
                'status': 'success',
                'market_regime': regime_analysis.get('regime', 'NEUTRAL'),
                'regime_confidence': regime_analysis.get('confidence', 0.0),
                'sp500_momentum': latest.get('sp500_momentum_60', 0.0),
                'nasdaq_momentum': latest.get('nasdaq_momentum_60', 0.0),
                'vix_level': latest.get('vix_close', 20.0),
                'market_volatility': latest.get('sp500_volatility', 1.0),
                'regime_analysis': regime_analysis,
                'latest_data': latest.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"미국 시장 분석 오류: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _analyze_global_sentiment(self) -> Dict[str, Any]:
        """글로벌 시장 심리 분석"""
        try:
            self.logger.info("글로벌 시장 심리 분석 실행")
            
            # 미국 시장 심리 지표
            us_sentiment = self.us_market_collector.get_market_sentiment_indicators(period="3mo")
            
            return {
                'status': 'success',
                'sentiment': us_sentiment.get('sentiment', 'NEUTRAL'),
                'sentiment_confidence': us_sentiment.get('confidence', 0.0),
                'sentiment_score': us_sentiment.get('sentiment_score', 0.0),
                'sentiment_indicators': us_sentiment.get('indicators', []),
                'full_analysis': us_sentiment
            }
            
        except Exception as e:
            self.logger.error(f"글로벌 심리 분석 오류: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _integrate_analyses(self, 
                          korean_analysis: Dict[str, Any],
                          us_analysis: Dict[str, Any],
                          sentiment_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """분석 결과 통합"""
        try:
            # 각 분석의 성공/실패 확인
            korean_success = korean_analysis.get('status') == 'success'
            us_success = us_analysis.get('status') == 'success'
            sentiment_success = sentiment_analysis.get('status') == 'success'
            
            # 통합 신호 초기화
            integrated_signals = {
                'equity_signal': 0,
                'bond_signal': 0,
                'defensive_signal': 0,
                'cash_signal': 0,
                'signal_strength': 0.0,
                'confidence': 0.0
            }
            
            signal_components = []
            total_weight = 0.0
            
            # 1. 한국 거시경제 신호
            if korean_success:
                korean_weight = self.weights['korean_macro']
                korean_equity_signal = korean_analysis.get('equity_signal', 0)
                korean_strength = korean_analysis.get('signal_strength', 0.0)
                korean_confidence = korean_analysis.get('signal_confidence', 0.0)
                
                signal_components.append({
                    'source': 'korean_macro',
                    'equity_signal': korean_equity_signal,
                    'strength': korean_strength,
                    'confidence': korean_confidence,
                    'weight': korean_weight
                })
                total_weight += korean_weight
            
            # 2. 미국 시장 신호
            if us_success:
                us_weight = self.weights['us_market']
                
                # 미국 시장 체제를 한국 주식 신호로 변환
                us_regime = us_analysis.get('market_regime', 'NEUTRAL')
                us_confidence = us_analysis.get('regime_confidence', 0.0)
                
                if us_regime in ['BULL_MARKET']:
                    us_equity_signal = 1
                    us_strength = 0.7
                elif us_regime in ['BEAR_MARKET']:
                    us_equity_signal = -1
                    us_strength = 0.7
                elif us_regime in ['HIGH_VOLATILITY']:
                    us_equity_signal = -1
                    us_strength = 0.5
                else:
                    us_equity_signal = 0
                    us_strength = 0.3
                
                signal_components.append({
                    'source': 'us_market',
                    'equity_signal': us_equity_signal,
                    'strength': us_strength,
                    'confidence': us_confidence,
                    'weight': us_weight
                })
                total_weight += us_weight
            
            # 3. 글로벌 심리 신호
            if sentiment_success:
                sentiment_weight = self.weights['global_sentiment']
                sentiment_type = sentiment_analysis.get('sentiment', 'NEUTRAL')
                sentiment_confidence = sentiment_analysis.get('sentiment_confidence', 0.0)
                
                if sentiment_type in ['VERY_BULLISH', 'BULLISH']:
                    sentiment_equity_signal = 1
                    sentiment_strength = 0.6
                elif sentiment_type in ['VERY_BEARISH', 'BEARISH']:
                    sentiment_equity_signal = -1
                    sentiment_strength = 0.6
                else:
                    sentiment_equity_signal = 0
                    sentiment_strength = 0.3
                
                signal_components.append({
                    'source': 'global_sentiment',
                    'equity_signal': sentiment_equity_signal,
                    'strength': sentiment_strength,
                    'confidence': sentiment_confidence,
                    'weight': sentiment_weight
                })
                total_weight += sentiment_weight
            
            # 가중 평균 신호 계산
            if signal_components and total_weight > 0:
                weighted_equity_signal = sum(
                    comp['equity_signal'] * comp['strength'] * comp['weight']
                    for comp in signal_components
                ) / total_weight
                
                weighted_strength = sum(
                    comp['strength'] * comp['weight']
                    for comp in signal_components
                ) / total_weight
                
                weighted_confidence = sum(
                    comp['confidence'] * comp['weight']
                    for comp in signal_components
                ) / total_weight
                
                # 최종 신호 결정
                if weighted_equity_signal > 0.3:
                    integrated_signals['equity_signal'] = 1
                elif weighted_equity_signal < -0.3:
                    integrated_signals['equity_signal'] = -1
                    integrated_signals['defensive_signal'] = 1
                    integrated_signals['cash_signal'] = 1
                else:
                    integrated_signals['equity_signal'] = 0
                
                integrated_signals['signal_strength'] = weighted_strength
                integrated_signals['confidence'] = weighted_confidence
            
            # 글로벌 시장 체제 결정
            global_regime = self._determine_global_regime(
                korean_analysis, us_analysis, sentiment_analysis
            )
            
            return {
                'global_regime': global_regime,
                'integrated_signals': integrated_signals,
                'signal_components': signal_components,
                'analysis_success': {
                    'korean_macro': korean_success,
                    'us_market': us_success,
                    'global_sentiment': sentiment_success
                },
                'total_weight': total_weight,
                'integration_confidence': min(0.95, weighted_confidence + 0.1) if signal_components else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"분석 통합 오류: {str(e)}")
            return {'error': str(e)}
    
    def _determine_global_regime(self, 
                               korean_analysis: Dict[str, Any],
                               us_analysis: Dict[str, Any],
                               sentiment_analysis: Dict[str, Any]) -> GlobalMarketRegime:
        """글로벌 시장 체제 결정"""
        try:
            regime_signals = []
            
            # 한국 경제 체제 신호
            if korean_analysis.get('status') == 'success':
                korean_regime = korean_analysis.get('regime', 'NEUTRAL')
                if korean_regime in ['GROWTH', 'RECOVERY']:
                    regime_signals.append('RISK_ON')
                elif korean_regime in ['RECESSION', 'STAGFLATION']:
                    regime_signals.append('RISK_OFF')
                else:
                    regime_signals.append('MIXED')
            
            # 미국 시장 체제 신호
            if us_analysis.get('status') == 'success':
                us_regime = us_analysis.get('market_regime', 'NEUTRAL')
                if us_regime in ['BULL_MARKET', 'TECH_LED']:
                    regime_signals.append('RISK_ON')
                elif us_regime in ['BEAR_MARKET', 'HIGH_VOLATILITY']:
                    regime_signals.append('RISK_OFF')
                else:
                    regime_signals.append('MIXED')
            
            # 글로벌 심리 신호
            if sentiment_analysis.get('status') == 'success':
                sentiment = sentiment_analysis.get('sentiment', 'NEUTRAL')
                if sentiment in ['VERY_BULLISH', 'BULLISH']:
                    regime_signals.append('RISK_ON')
                elif sentiment in ['VERY_BEARISH', 'BEARISH']:
                    regime_signals.append('RISK_OFF')
                else:
                    regime_signals.append('MIXED')
            
            # 신호 집계
            if not regime_signals:
                return GlobalMarketRegime.UNCERTAIN
            
            risk_on_count = regime_signals.count('RISK_ON')
            risk_off_count = regime_signals.count('RISK_OFF')
            mixed_count = regime_signals.count('MIXED')
            
            total_signals = len(regime_signals)
            
            if risk_on_count >= total_signals * 0.6:
                return GlobalMarketRegime.RISK_ON
            elif risk_off_count >= total_signals * 0.6:
                return GlobalMarketRegime.RISK_OFF
            elif mixed_count >= total_signals * 0.5:
                return GlobalMarketRegime.MIXED_SIGNALS
            else:
                return GlobalMarketRegime.TRANSITION
            
        except Exception as e:
            self.logger.error(f"글로벌 체제 결정 오류: {str(e)}")
            return GlobalMarketRegime.UNCERTAIN
    
    def _generate_integrated_recommendations(self, 
                                           integrated_result: Dict[str, Any]) -> List[str]:
        """통합 투자 권장사항 생성"""
        try:
            recommendations = []
            
            if 'error' in integrated_result:
                return ["데이터 부족으로 권장사항 생성 불가"]
            
            global_regime = integrated_result.get('global_regime', GlobalMarketRegime.UNCERTAIN)
            integrated_signals = integrated_result.get('integrated_signals', {})
            
            equity_signal = integrated_signals.get('equity_signal', 0)
            signal_strength = integrated_signals.get('signal_strength', 0.0)
            confidence = integrated_signals.get('confidence', 0.0)
            
            # 글로벌 체제별 권장사항
            if global_regime == GlobalMarketRegime.RISK_ON:
                recommendations.append("Risk-On 환경: 성장주 및 기술주 비중 확대 검토")
                recommendations.append("신흥시장 및 위험자산 투자 기회 포착")
                recommendations.append("채권 비중 축소 고려")
                
            elif global_regime == GlobalMarketRegime.RISK_OFF:
                recommendations.append("Risk-Off 환경: 방어주 및 안전자산 비중 확대")
                recommendations.append("정부채권, 금, 현금 등 안전자산 선호")
                recommendations.append("변동성 확대 대비 헤지 전략 검토")
                
            elif global_regime == GlobalMarketRegime.MIXED_SIGNALS:
                recommendations.append("혼재된 신호: 균형잡힌 포트폴리오 유지")
                recommendations.append("섹터 로테이션 전략 고려")
                recommendations.append("변동성 장세 대비 적극적 리밸런싱")
                
            elif global_regime == GlobalMarketRegime.TRANSITION:
                recommendations.append("전환기: 신호 변화 주의깊게 모니터링")
                recommendations.append("점진적 포지션 조정 권장")
                recommendations.append("단기 변동성 확대 가능성 대비")
                
            else:  # UNCERTAIN
                recommendations.append("불확실한 환경: 보수적 포트폴리오 운용")
                recommendations.append("현금 비중 확대 및 관망세 유지")
            
            # 신호 강도별 권장사항
            if confidence > 0.7:
                if signal_strength > 0.6:
                    recommendations.append(f"고신뢰도 강신호: 적극적 포지션 조정 권장")
                elif signal_strength > 0.4:
                    recommendations.append(f"고신뢰도 중간신호: 점진적 포지션 조정")
            elif confidence > 0.4:
                recommendations.append(f"중간신뢰도: 신중한 포지션 관리 필요")
            else:
                recommendations.append(f"저신뢰도: 추가 정보 확인 후 투자 결정")
            
            # 한국 주식 시장 특화 권장사항
            if equity_signal > 0:
                recommendations.append("한국 주식 긍정적: 코스피 대형주 중심 매수 검토")
                recommendations.append("수출주 및 기술주 관심 확대")
            elif equity_signal < 0:
                recommendations.append("한국 주식 부정적: 방어주 또는 현금 비중 확대")
                recommendations.append("해외 분산투자 검토")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"통합 권장사항 생성 오류: {str(e)}")
            return ["권장사항 생성 중 오류 발생"]


def main():
    """테스트 실행"""
    print("=== 통합 거시경제 분석기 테스트 ===")
    
    analyzer = IntegratedMacroAnalyzer()
    
    try:
        print(f"\n통합 거시경제 분석 실행 중...")
        
        # 통합 분석 실행 (6개월 데이터)
        result = analyzer.analyze_integrated_macro_environment(analysis_period_months=6)
        
        if 'error' in result:
            print(f"   ❌ 분석 실패: {result['error']}")
            return
        
        print(f"   ✅ 통합 분석 완료")
        
        # 통합 결과 출력
        integrated = result.get('integrated_analysis', {})
        
        print(f"\n=== 통합 분석 결과 ===")
        print(f"글로벌 시장 체제: {integrated.get('global_regime', 'Unknown').value if hasattr(integrated.get('global_regime'), 'value') else integrated.get('global_regime', 'Unknown')}")
        
        # 통합 신호
        signals = integrated.get('integrated_signals', {})
        print(f"통합 주식 신호: {signals.get('equity_signal', 0)} ({'매수' if signals.get('equity_signal', 0) > 0 else '매도' if signals.get('equity_signal', 0) < 0 else '중립'})")
        print(f"신호 강도: {signals.get('signal_strength', 0):.2f}")
        print(f"통합 신뢰도: {signals.get('confidence', 0):.2f}")
        
        # 분석 성공 현황
        success_status = integrated.get('analysis_success', {})
        print(f"\n=== 분석 성공 현황 ===")
        print(f"한국 거시경제: {'✅' if success_status.get('korean_macro', False) else '❌'}")
        print(f"미국 시장: {'✅' if success_status.get('us_market', False) else '❌'}")
        print(f"글로벌 심리: {'✅' if success_status.get('global_sentiment', False) else '❌'}")
        
        # 개별 분석 결과
        korean = result.get('korean_macro', {})
        if korean.get('status') == 'success':
            print(f"\n=== 한국 거시경제 ===")
            print(f"경제 체제: {korean.get('regime', 'Unknown')}")
            print(f"리스크 수준: {korean.get('risk_level', 'Unknown')}")
            print(f"주식 신호: {korean.get('equity_signal', 0)}")
        
        us = result.get('us_market', {})
        if us.get('status') == 'success':
            print(f"\n=== 미국 시장 ===")
            print(f"시장 체제: {us.get('market_regime', 'Unknown')}")
            print(f"S&P500 모멘텀: {us.get('sp500_momentum', 0):.1f}%")
            print(f"VIX 수준: {us.get('vix_level', 0):.1f}")
        
        sentiment = result.get('global_sentiment', {})
        if sentiment.get('status') == 'success':
            print(f"\n=== 글로벌 심리 ===")
            print(f"시장 심리: {sentiment.get('sentiment', 'Unknown')}")
            print(f"심리 점수: {sentiment.get('sentiment_score', 0):.2f}")
        
        # 투자 권장사항
        recommendations = result.get('recommendations', [])
        print(f"\n=== 투자 권장사항 ({len(recommendations)}개) ===")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i:2d}. {rec}")
        
    except Exception as e:
        print(f"   ❌ 테스트 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()