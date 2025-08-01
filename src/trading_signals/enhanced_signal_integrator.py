"""
향상된 다중 지표 신호 통합기 (Enhanced Multi-Indicator Signal Integrator)
6개 기술적 지표 + 외국인·기관 매매 동향을 통합한 고정확도 매매 신호 생성
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.trading_signals.signal_integrator import SignalIntegrator
from src.institutional_data.institutional_signal_analyzer import InstitutionalSignalAnalyzer

class EnhancedSignalIntegrator(SignalIntegrator):
    """향상된 다중 지표 신호 통합기 - 기술적 지표 + 기관·외국인 매매 동향"""
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 min_indicators: int = 3,
                 use_market_condition: bool = True,
                 use_institutional_signals: bool = True,
                 institutional_weight: float = 0.3):
        """
        Args:
            confidence_threshold: 최소 신뢰도 임계값 (기본: 0.7)
            min_indicators: 최소 동의 지표 수 (기본: 3개)
            use_market_condition: 시장 상황 기반 신호 조정 사용 여부
            use_institutional_signals: 기관·외국인 신호 사용 여부
            institutional_weight: 기관·외국인 신호 가중치 (기본: 0.3)
        """
        # 부모 클래스 초기화
        super().__init__(confidence_threshold, min_indicators, use_market_condition)
        
        self.use_institutional_signals = use_institutional_signals
        self.institutional_weight = institutional_weight
        
        # 기관·외국인 신호 분석기 초기화
        if self.use_institutional_signals:
            try:
                self.institutional_analyzer = InstitutionalSignalAnalyzer(
                    volume_threshold=100,  # 100억원 임계값
                    trend_days=5
                )
                self.logger.info("기관·외국인 신호 분석기 초기화 완료")
            except Exception as e:
                self.logger.warning(f"기관·외국인 신호 분석기 초기화 실패: {str(e)}")
                self.use_institutional_signals = False
                self.institutional_analyzer = None
        else:
            self.institutional_analyzer = None
        
        # 가중치 재조정 (기관 신호 포함)
        if self.use_institutional_signals:
            # 기존 기술적 지표 가중치를 (1 - institutional_weight)로 조정
            technical_weight = 1.0 - self.institutional_weight
            self.indicator_weights = {
                'ma': 0.20 * technical_weight,
                'rsi': 0.15 * technical_weight,
                'macd': 0.20 * technical_weight,
                'bb': 0.15 * technical_weight,
                'volume': 0.15 * technical_weight,
                'stoch': 0.15 * technical_weight,
                'institutional': self.institutional_weight  # 기관 신호 가중치
            }
        
        self.logger.info("향상된 신호 통합기 초기화 완료")
        
    def analyze_all_indicators_enhanced(self, 
                                      data: pd.DataFrame,
                                      symbol: str = None) -> pd.DataFrame:
        """
        모든 기술적 지표 + 기관·외국인 매매 신호 분석
        
        Args:
            data: 주가 데이터 (OHLCV)
            symbol: 종목코드 (기관 신호 분석용)
            
        Returns:
            모든 지표가 계산된 DataFrame
        """
        try:
            self.logger.info("Starting enhanced comprehensive analysis...")
            
            # 1. 기존 기술적 지표 분석 (부모 클래스 메서드 사용)
            result = self.analyze_all_indicators(data)
            
            # 2. 기관·외국인 매매 신호 분석
            if self.use_institutional_signals and symbol and self.institutional_analyzer:
                try:
                    self.logger.info("8/8 Institutional signals analysis...")
                    result = self.institutional_analyzer.analyze_institutional_signals(
                        symbol, result
                    )
                    self.logger.info("Institutional signals analysis completed")
                except Exception as e:
                    self.logger.warning(f"기관 신호 분석 실패: {str(e)}")
            
            self.logger.info("Enhanced technical analysis completed for all indicators")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in enhanced comprehensive analysis: {str(e)}")
            return data
    
    def calculate_signal_scores_enhanced(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        각 지표별 신호 점수 계산 (기관 신호 포함)
        
        Args:
            data: 분석 완료된 데이터
            
        Returns:
            신호 점수가 추가된 DataFrame
        """
        try:
            # 1. 기존 기술적 지표 점수 계산 (부모 클래스 메서드 사용)
            result = self.calculate_signal_scores(data)
            
            # 2. 기관·외국인 신호 점수 추가
            if self.use_institutional_signals:
                result['institutional_score'] = 0.0
                
                # 기관 신호가 있는 경우에만 점수 계산
                if 'combined_institutional_signal' in result.columns:
                    result['institutional_score'] = np.where(
                        result['combined_institutional_signal'] == 1,
                        result['combined_institutional_strength'] / 3.0,  # 정규화
                        np.where(
                            result['combined_institutional_signal'] == -1,
                            -result['combined_institutional_strength'] / 3.0,  # 매도 신호
                            0.0
                        )
                    )
                
                # 신뢰도 기반 조정
                if 'institutional_confidence' in result.columns:
                    result['institutional_score'] *= result['institutional_confidence']
            
            self.logger.info("Enhanced signal scores calculated for all indicators")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced signal scores: {str(e)}")
            return data
    
    def generate_integrated_signals_enhanced(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        통합 매매 신호 생성 (기관 신호 포함)
        
        Args:
            data: 신호 점수가 계산된 데이터
            
        Returns:
            통합 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 통합 신호 초기화
            result['integrated_buy_signal'] = 0
            result['integrated_sell_signal'] = 0
            result['integrated_strength'] = 0.0
            result['integrated_confidence'] = 0.0
            result['agreeing_indicators'] = 0
            result['signal_quality'] = 'NONE'
            
            # 각 지표의 신호 방향 계산 (1: 매수, -1: 매도, 0: 중립)
            indicator_signals_dict = {
                'ma_signal': np.where(result['ma_score'] > 0.3, 1, np.where(result['ma_score'] < -0.3, -1, 0)),
                'rsi_signal': np.where(result['rsi_score'] > 0.5, 1, np.where(result['rsi_score'] < -0.5, -1, 0)),
                'macd_signal': np.where(result['macd_score'] > 0.3, 1, np.where(result['macd_score'] < -0.3, -1, 0)),
                'bb_signal': np.where(result['bb_score'] > 0.3, 1, np.where(result['bb_score'] < -0.3, -1, 0)),
                'volume_signal': np.where(result['volume_score'] > 0.3, 1, np.where(result['volume_score'] < -0.3, -1, 0)),
                'stoch_signal': np.where(result['stoch_score'] > 0.3, 1, np.where(result['stoch_score'] < -0.3, -1, 0))
            }
            
            # 기관 신호 추가
            if self.use_institutional_signals and 'institutional_score' in result.columns:
                indicator_signals_dict['institutional_signal'] = np.where(
                    result['institutional_score'] > 0.2, 1, 
                    np.where(result['institutional_score'] < -0.2, -1, 0)
                )
            
            indicator_signals = pd.DataFrame(indicator_signals_dict)
            
            # 가중 평균 신호 강도 계산
            weighted_score = (
                result['ma_score'] * self.indicator_weights['ma'] +
                result['rsi_score'] * self.indicator_weights['rsi'] +
                result['macd_score'] * self.indicator_weights['macd'] +
                result['bb_score'] * self.indicator_weights['bb'] +
                result['volume_score'] * self.indicator_weights['volume'] +
                result['stoch_score'] * self.indicator_weights['stoch']
            )
            
            # 기관 신호 가중치 추가
            if self.use_institutional_signals and 'institutional_score' in result.columns:
                weighted_score += result['institutional_score'] * self.indicator_weights['institutional']
            
            result['integrated_strength'] = weighted_score
            
            # 각 행별로 동의하는 지표 수 계산
            total_indicators = len(indicator_signals.columns)
            
            for idx in result.index:
                buy_signals = (indicator_signals.loc[idx] == 1).sum()
                sell_signals = (indicator_signals.loc[idx] == -1).sum()
                
                # 기관 신호 보너스 (신뢰도가 높으면 추가 가중치)
                institutional_bonus = 0
                if (self.use_institutional_signals and 
                    'institutional_confidence' in result.columns):
                    inst_conf = result.loc[idx, 'institutional_confidence']
                    if inst_conf > 0.7:
                        institutional_bonus = 1
                
                # 매수 신호 조건 (기관 신호 고려)
                required_indicators = max(2, self.min_indicators - institutional_bonus)
                
                if buy_signals >= required_indicators and weighted_score.loc[idx] > 0.5:
                    result.loc[idx, 'integrated_buy_signal'] = 1
                    result.loc[idx, 'agreeing_indicators'] = buy_signals
                    
                    # 신뢰도 계산 (기관 신호 신뢰도 보너스 포함)
                    base_confidence = min(0.95, 0.6 + (buy_signals - 2) * 0.1)
                    if institutional_bonus > 0:
                        base_confidence = min(0.98, base_confidence + 0.1)
                    
                    result.loc[idx, 'integrated_confidence'] = base_confidence
                    result.loc[idx, 'signal_quality'] = self._get_signal_quality_enhanced(
                        buy_signals, weighted_score.loc[idx], total_indicators
                    )
                
                # 매도 신호 조건
                elif sell_signals >= required_indicators and weighted_score.loc[idx] < -0.5:
                    result.loc[idx, 'integrated_sell_signal'] = 1
                    result.loc[idx, 'agreeing_indicators'] = sell_signals
                    
                    # 신뢰도 계산
                    base_confidence = min(0.95, 0.6 + (sell_signals - 2) * 0.1)
                    if institutional_bonus > 0:
                        base_confidence = min(0.98, base_confidence + 0.1)
                    
                    result.loc[idx, 'integrated_confidence'] = base_confidence
                    result.loc[idx, 'signal_quality'] = self._get_signal_quality_enhanced(
                        sell_signals, abs(weighted_score.loc[idx]), total_indicators
                    )
            
            # 시장 상황에 따른 신호 강도 조정
            if self.use_market_condition and 'market_condition' in result.columns:
                result = self.market_analyzer.adjust_signal_strength(result)
                self.logger.info("Signal strength adjusted based on market conditions")
            
            # 통합 신호 통계
            buy_signals = (result['integrated_buy_signal'] == 1).sum()
            sell_signals = (result['integrated_sell_signal'] == 1).sum()
            avg_confidence = result[result['integrated_confidence'] > 0]['integrated_confidence'].mean()
            
            indicator_count = total_indicators if self.use_institutional_signals else total_indicators - 1
            self.logger.info(f"Generated enhanced integrated signals ({indicator_count} indicators) - Buy: {buy_signals}, Sell: {sell_signals}, Avg Confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced integrated signals: {str(e)}")
            return data
    
    def _get_signal_quality_enhanced(self, 
                                   agreeing_count: int, 
                                   strength: float,
                                   total_indicators: int) -> str:
        """신호 품질 분류 (기관 신호 포함)"""
        if total_indicators >= 7:  # 기관 신호 포함
            if agreeing_count >= 6 and strength > 0.8:
                return 'EXCELLENT'
            elif agreeing_count >= 5 and strength > 0.7:
                return 'VERY_GOOD'
            elif agreeing_count >= 4 and strength > 0.6:
                return 'GOOD'
            elif agreeing_count >= 3 and strength > 0.5:
                return 'FAIR'
            else:
                return 'WEAK'
        else:  # 기존 6개 지표만
            return super()._get_signal_quality(agreeing_count, strength)
    
    def get_integration_summary_enhanced(self, data: pd.DataFrame) -> Dict[str, Any]:
        """향상된 통합 분석 요약"""
        try:
            # 기본 요약 정보 가져오기
            summary = self.get_integration_summary(data)
            
            if not summary or data.empty:
                return summary
            
            latest = data.iloc[-1]
            
            # 기관 신호 정보 추가
            if self.use_institutional_signals:
                institutional_info = {
                    'institutional_signal': int(latest.get('combined_institutional_signal', 0)),
                    'institutional_strength': float(latest.get('combined_institutional_strength', 0)),
                    'institutional_confidence': float(latest.get('institutional_confidence', 0)),
                    'foreign_signal': int(latest.get('foreign_signal', 0)),
                    'foreign_strength': float(latest.get('foreign_signal_strength', 0))
                }
                
                summary['institutional_info'] = institutional_info
                
                # 기관 신호 통계
                if 'combined_institutional_signal' in data.columns:
                    institutional_stats = {
                        'institutional_buy_signals': int((data['combined_institutional_signal'] == 1).sum()),
                        'institutional_sell_signals': int((data['combined_institutional_signal'] == -1).sum()),
                        'avg_institutional_confidence': float(data[data['institutional_confidence'] > 0]['institutional_confidence'].mean()) if 'institutional_confidence' in data.columns else 0.0
                    }
                    
                    summary['institutional_stats'] = institutional_stats
            
            # 가중치 정보 업데이트
            summary['weights'] = self.indicator_weights
            summary['enhancement_info'] = {
                'uses_institutional_signals': self.use_institutional_signals,
                'institutional_weight': self.institutional_weight,
                'total_indicators': 7 if self.use_institutional_signals else 6
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating enhanced integration summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 향상된 다중 지표 신호 통합기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 120:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 향상된 신호 통합기 초기화
        integrator = EnhancedSignalIntegrator(
            confidence_threshold=0.7, 
            min_indicators=3,
            use_institutional_signals=True,
            institutional_weight=0.25  # 25% 가중치
        )
        
        # 2. 모든 지표 분석 (기관 신호 포함)
        print(f"\n2. 향상된 기술적 지표 분석 중...")
        analyzed_data = integrator.analyze_all_indicators_enhanced(
            stock_data, 
            symbol=test_symbol
        )
        
        # 3. 신호 점수 계산
        print(f"3. 향상된 신호 점수 계산 중...")
        scored_data = integrator.calculate_signal_scores_enhanced(analyzed_data)
        
        # 4. 통합 신호 생성
        print(f"4. 향상된 통합 매매 신호 생성 중...")
        integrated_data = integrator.generate_integrated_signals_enhanced(scored_data)
        
        # 5. 고신뢰도 신호 필터링
        print(f"5. 고신뢰도 신호 필터링 중...")
        filtered_data = integrator.filter_high_confidence_signals(integrated_data)
        
        # 6. 결과 분석
        print(f"\n=== 향상된 통합 신호 분석 결과 ===")
        
        latest = filtered_data.iloc[-1]
        print(f"현재가: {latest['close']:,.0f}원")
        print(f"통합 신호 강도: {latest['integrated_strength']:+.3f}")
        print(f"동의 지표 수: {latest['agreeing_indicators']}개")
        print(f"신호 품질: {latest['signal_quality']}")
        print(f"통합 신뢰도: {latest['integrated_confidence']:.2f}")
        
        # 기관 신호 정보
        if integrator.use_institutional_signals:
            print(f"\n=== 기관·외국인 신호 ===")
            print(f"외국인 신호: {latest.get('foreign_signal', 0)} (강도: {latest.get('foreign_signal_strength', 0):.2f})")
            print(f"기관 신호: {latest.get('institutional_signal', 0)} (강도: {latest.get('institutional_signal_strength', 0):.2f})")
            print(f"통합 기관 신호: {latest.get('combined_institutional_signal', 0)} (강도: {latest.get('combined_institutional_strength', 0):.2f})")
            print(f"기관 신뢰도: {latest.get('institutional_confidence', 0):.2f}")
        
        # 각 지표별 점수
        print(f"\n=== 지표별 신호 점수 ===")
        print(f"이동평균: {latest['ma_score']:+.3f}")
        print(f"RSI: {latest['rsi_score']:+.3f}")
        print(f"MACD: {latest['macd_score']:+.3f}")
        print(f"볼린저밴드: {latest['bb_score']:+.3f}")
        print(f"거래량: {latest['volume_score']:+.3f}")
        print(f"스토캐스틱: {latest['stoch_score']:+.3f}")
        if integrator.use_institutional_signals and 'institutional_score' in filtered_data.columns:
            print(f"기관·외국인: {latest.get('institutional_score', 0):+.3f}")
        
        # 통합 신호 통계
        buy_signals = (filtered_data['integrated_buy_signal'] == 1).sum()
        sell_signals = (filtered_data['integrated_sell_signal'] == 1).sum()
        avg_confidence = filtered_data[filtered_data['integrated_confidence'] > 0]['integrated_confidence'].mean()
        
        print(f"\n통합 매수 신호: {buy_signals}회")
        print(f"통합 매도 신호: {sell_signals}회")
        print(f"평균 신뢰도: {avg_confidence:.2f}")
        
        # 신호 품질 분포
        quality_counts = filtered_data['signal_quality'].value_counts()
        print(f"\n신호 품질 분포:")
        for quality, count in quality_counts.items():
            if quality != 'NONE':
                print(f"  {quality}: {count}회")
        
        # 요약 정보
        summary = integrator.get_integration_summary_enhanced(filtered_data)
        print(f"\n=== 요약 ===")
        enhancement_info = summary.get('enhancement_info', {})
        print(f"{enhancement_info.get('total_indicators', 6)}개 지표 통합 분석 완료 - 고정확도 신호 생성")
        print(f"기관·외국인 신호 사용: {'✅' if enhancement_info.get('uses_institutional_signals', False) else '❌'}")
        if enhancement_info.get('uses_institutional_signals'):
            print(f"기관 신호 가중치: {enhancement_info.get('institutional_weight', 0):.1%}")
        
    else:
        print("   데이터 부족 - 최소 120일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()