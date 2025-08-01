"""
다중 지표 신호 통합기 (Multi-Indicator Signal Integrator)
5개 핵심 기술적 지표의 신호를 통합하여 고정확도 매매 신호 생성
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

from src.technical_analysis.moving_averages import MovingAverageAnalyzer
from src.technical_analysis.rsi_analyzer import RSIAnalyzer
from src.technical_analysis.macd_analyzer import MACDAnalyzer
from src.technical_analysis.bollinger_bands import BollingerBandsAnalyzer
from src.technical_analysis.volume_analyzer import VolumeAnalyzer

class SignalIntegrator:
    """다중 지표 신호 통합기 - 정확도 우선 매매신호 생성"""
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 min_indicators: int = 3):
        """
        Args:
            confidence_threshold: 최소 신뢰도 임계값 (기본: 0.7)
            min_indicators: 최소 동의 지표 수 (기본: 3개)
        """
        self.confidence_threshold = confidence_threshold
        self.min_indicators = min_indicators
        self.logger = self._setup_logger()
        
        # 각 분석기 초기화
        self.ma_analyzer = MovingAverageAnalyzer()
        self.rsi_analyzer = RSIAnalyzer()
        self.macd_analyzer = MACDAnalyzer()
        self.bb_analyzer = BollingerBandsAnalyzer()
        self.volume_analyzer = VolumeAnalyzer()
        
        # 지표별 가중치 (신뢰도 기반)
        self.indicator_weights = {
            'ma': 0.25,      # 이동평균 (트렌드)
            'rsi': 0.20,     # RSI (과매수/과매도)
            'macd': 0.25,    # MACD (모멘텀)
            'bb': 0.15,      # 볼린저밴드 (변동성)
            'volume': 0.15   # 거래량 (확인)
        }
        
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
    
    def analyze_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        모든 기술적 지표 분석 실행
        
        Args:
            data: 주가 데이터 (OHLCV)
            
        Returns:
            모든 지표가 계산된 DataFrame
        """
        try:
            result = data.copy()
            
            self.logger.info("Starting comprehensive technical analysis...")
            
            # 1. 이동평균 분석
            self.logger.info("1/5 Moving Average analysis...")
            result = self.ma_analyzer.calculate_moving_averages(result)
            result = self.ma_analyzer.detect_crossovers(result)
            result = self.ma_analyzer.get_trend_strength(result)
            result = self.ma_analyzer.generate_ma_signals(result)
            
            # 2. RSI 분석
            self.logger.info("2/5 RSI analysis...")
            result = self.rsi_analyzer.calculate_rsi(result)
            result = self.rsi_analyzer.detect_divergences(result)
            result = self.rsi_analyzer.generate_rsi_signals(result)
            
            # 3. MACD 분석
            self.logger.info("3/5 MACD analysis...")
            result = self.macd_analyzer.calculate_macd(result)
            result = self.macd_analyzer.detect_macd_crossovers(result)
            result = self.macd_analyzer.analyze_histogram_patterns(result)
            result = self.macd_analyzer.generate_macd_signals(result)
            
            # 4. 볼린저 밴드 분석
            self.logger.info("4/5 Bollinger Bands analysis...")
            result = self.bb_analyzer.calculate_bollinger_bands(result)
            result = self.bb_analyzer.detect_squeeze_patterns(result)
            result = self.bb_analyzer.detect_band_touches(result)
            result = self.bb_analyzer.generate_bb_signals(result)
            
            # 5. 거래량 분석
            self.logger.info("5/5 Volume analysis...")
            result = self.volume_analyzer.calculate_obv(result)
            result = self.volume_analyzer.calculate_vwap(result)
            result = self.volume_analyzer.detect_volume_patterns(result)
            result = self.volume_analyzer.detect_price_volume_divergence(result)
            result = self.volume_analyzer.generate_volume_signals(result)
            
            self.logger.info("Technical analysis completed for all indicators")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {str(e)}")
            return data
    
    def calculate_signal_scores(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        각 지표별 신호 점수 계산
        
        Args:
            data: 분석 완료된 데이터
            
        Returns:
            신호 점수가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 각 지표별 신호 점수 초기화
            result['ma_score'] = 0.0
            result['rsi_score'] = 0.0 
            result['macd_score'] = 0.0
            result['bb_score'] = 0.0
            result['volume_score'] = 0.0
            
            # 1. 이동평균 점수 (-1 ~ +1)
            if 'ma_buy_signal' in result.columns and 'ma_sell_signal' in result.columns:
                result['ma_score'] = np.where(
                    result['ma_buy_signal'] == 1, 
                    result['ma_signal_strength'] / 3.0,  # 정규화
                    np.where(
                        result['ma_sell_signal'] == 1,
                        result['ma_signal_strength'] / 3.0,  # 이미 음수
                        0.0
                    )
                )
            
            # 2. RSI 점수 (-1 ~ +1)
            if 'rsi_buy_signal' in result.columns and 'rsi_sell_signal' in result.columns:
                result['rsi_score'] = np.where(
                    result['rsi_buy_signal'] == 1,
                    result['rsi_signal_strength'] / 2.0,  # 정규화
                    np.where(
                        result['rsi_sell_signal'] == 1,
                        result['rsi_signal_strength'] / 2.0,  # 이미 음수
                        0.0
                    )
                )
            
            # 3. MACD 점수 (-1 ~ +1)
            if 'macd_buy_signal' in result.columns and 'macd_sell_signal' in result.columns:
                result['macd_score'] = np.where(
                    result['macd_buy_signal'] == 1,
                    result['macd_signal_strength'] / 3.0,  # 정규화
                    np.where(
                        result['macd_sell_signal'] == 1,
                        result['macd_signal_strength'] / 3.0,  # 이미 음수
                        0.0
                    )
                )
            
            # 4. 볼린저 밴드 점수 (-1 ~ +1)
            if 'bb_buy_signal' in result.columns and 'bb_sell_signal' in result.columns:
                result['bb_score'] = np.where(
                    result['bb_buy_signal'] == 1,
                    result['bb_signal_strength'] / 3.0,  # 정규화
                    np.where(
                        result['bb_sell_signal'] == 1,
                        result['bb_signal_strength'] / 3.0,  # 이미 음수
                        0.0
                    )
                )
            
            # 5. 거래량 점수 (-1 ~ +1)
            if 'volume_buy_signal' in result.columns and 'volume_sell_signal' in result.columns:
                result['volume_score'] = np.where(
                    result['volume_buy_signal'] == 1,
                    result['volume_signal_strength'] / 3.0,  # 정규화
                    np.where(
                        result['volume_sell_signal'] == 1,
                        result['volume_signal_strength'] / 3.0,  # 이미 음수
                        0.0
                    )
                )
            
            self.logger.info("Signal scores calculated for all indicators")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating signal scores: {str(e)}")
            return data
    
    def generate_integrated_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        통합 매매 신호 생성 (고정확도)
        
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
            indicator_signals = pd.DataFrame({
                'ma_signal': np.where(result['ma_score'] > 0.3, 1, np.where(result['ma_score'] < -0.3, -1, 0)),
                'rsi_signal': np.where(result['rsi_score'] > 0.5, 1, np.where(result['rsi_score'] < -0.5, -1, 0)),
                'macd_signal': np.where(result['macd_score'] > 0.3, 1, np.where(result['macd_score'] < -0.3, -1, 0)),
                'bb_signal': np.where(result['bb_score'] > 0.3, 1, np.where(result['bb_score'] < -0.3, -1, 0)),
                'volume_signal': np.where(result['volume_score'] > 0.3, 1, np.where(result['volume_score'] < -0.3, -1, 0))
            })
            
            # 가중 평균 신호 강도 계산
            weighted_score = (
                result['ma_score'] * self.indicator_weights['ma'] +
                result['rsi_score'] * self.indicator_weights['rsi'] +
                result['macd_score'] * self.indicator_weights['macd'] +
                result['bb_score'] * self.indicator_weights['bb'] +
                result['volume_score'] * self.indicator_weights['volume']
            )
            
            result['integrated_strength'] = weighted_score
            
            # 각 행별로 동의하는 지표 수 계산
            for idx in result.index:
                buy_signals = (indicator_signals.loc[idx] == 1).sum()
                sell_signals = (indicator_signals.loc[idx] == -1).sum()
                
                # 매수 신호 조건
                if buy_signals >= self.min_indicators and weighted_score.loc[idx] > 0.5:
                    result.loc[idx, 'integrated_buy_signal'] = 1
                    result.loc[idx, 'agreeing_indicators'] = buy_signals
                    result.loc[idx, 'integrated_confidence'] = min(0.95, 0.6 + (buy_signals - 2) * 0.1)
                    result.loc[idx, 'signal_quality'] = self._get_signal_quality(buy_signals, weighted_score.loc[idx])
                
                # 매도 신호 조건
                elif sell_signals >= self.min_indicators and weighted_score.loc[idx] < -0.5:
                    result.loc[idx, 'integrated_sell_signal'] = 1
                    result.loc[idx, 'agreeing_indicators'] = sell_signals
                    result.loc[idx, 'integrated_confidence'] = min(0.95, 0.6 + (sell_signals - 2) * 0.1)
                    result.loc[idx, 'signal_quality'] = self._get_signal_quality(sell_signals, abs(weighted_score.loc[idx]))
            
            # 통합 신호 통계
            buy_signals = (result['integrated_buy_signal'] == 1).sum()
            sell_signals = (result['integrated_sell_signal'] == 1).sum()
            avg_confidence = result[result['integrated_confidence'] > 0]['integrated_confidence'].mean()
            
            self.logger.info(f"Generated integrated signals - Buy: {buy_signals}, Sell: {sell_signals}, Avg Confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating integrated signals: {str(e)}")
            return data
    
    def _get_signal_quality(self, agreeing_count: int, strength: float) -> str:
        """신호 품질 분류"""
        if agreeing_count >= 5 and strength > 0.8:
            return 'EXCELLENT'
        elif agreeing_count >= 4 and strength > 0.7:
            return 'VERY_GOOD'
        elif agreeing_count >= 3 and strength > 0.6:
            return 'GOOD'
        elif agreeing_count >= 3 and strength > 0.5:
            return 'FAIR'
        else:
            return 'WEAK'
    
    def filter_high_confidence_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        고신뢰도 신호만 필터링
        
        Args:
            data: 통합 신호가 있는 데이터
            
        Returns:
            고신뢰도 신호만 남긴 DataFrame
        """
        try:
            result = data.copy()
            
            # 신뢰도 기준 미달 신호 제거
            low_confidence_mask = result['integrated_confidence'] < self.confidence_threshold
            
            result.loc[low_confidence_mask, 'integrated_buy_signal'] = 0
            result.loc[low_confidence_mask, 'integrated_sell_signal'] = 0
            result.loc[low_confidence_mask, 'signal_quality'] = 'FILTERED_OUT'
            
            # 필터링 후 통계
            remaining_buy = (result['integrated_buy_signal'] == 1).sum()
            remaining_sell = (result['integrated_sell_signal'] == 1).sum()
            filtered_count = low_confidence_mask.sum()
            
            self.logger.info(f"Filtered {filtered_count} low-confidence signals. Remaining: Buy {remaining_buy}, Sell {remaining_sell}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error filtering signals: {str(e)}")
            return data
    
    def get_integration_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """통합 분석 요약"""
        try:
            if data.empty:
                return {}
            
            latest = data.iloc[-1]
            
            # 현재 상태
            current_status = {
                'integrated_strength': float(latest['integrated_strength']) if 'integrated_strength' in data.columns and not pd.isna(latest['integrated_strength']) else 0.0,
                'agreeing_indicators': int(latest['agreeing_indicators']) if 'agreeing_indicators' in data.columns else 0,
                'signal_quality': str(latest['signal_quality']) if 'signal_quality' in data.columns else 'UNKNOWN',
                'integrated_confidence': float(latest['integrated_confidence']) if 'integrated_confidence' in data.columns and not pd.isna(latest['integrated_confidence']) else 0.0
            }
            
            # 각 지표별 점수
            indicator_scores = {
                'ma_score': float(latest['ma_score']) if 'ma_score' in data.columns and not pd.isna(latest['ma_score']) else 0.0,
                'rsi_score': float(latest['rsi_score']) if 'rsi_score' in data.columns and not pd.isna(latest['rsi_score']) else 0.0,
                'macd_score': float(latest['macd_score']) if 'macd_score' in data.columns and not pd.isna(latest['macd_score']) else 0.0,
                'bb_score': float(latest['bb_score']) if 'bb_score' in data.columns and not pd.isna(latest['bb_score']) else 0.0,
                'volume_score': float(latest['volume_score']) if 'volume_score' in data.columns and not pd.isna(latest['volume_score']) else 0.0
            }
            
            # 통합 신호 통계
            signal_stats = {
                'total_buy_signals': int((data['integrated_buy_signal'] == 1).sum()) if 'integrated_buy_signal' in data.columns else 0,
                'total_sell_signals': int((data['integrated_sell_signal'] == 1).sum()) if 'integrated_sell_signal' in data.columns else 0,
                'avg_confidence': float(data[data['integrated_confidence'] > 0]['integrated_confidence'].mean()) if 'integrated_confidence' in data.columns else 0.0,
                'excellent_signals': int((data['signal_quality'] == 'EXCELLENT').sum()) if 'signal_quality' in data.columns else 0,
                'very_good_signals': int((data['signal_quality'] == 'VERY_GOOD').sum()) if 'signal_quality' in data.columns else 0,
                'good_signals': int((data['signal_quality'] == 'GOOD').sum()) if 'signal_quality' in data.columns else 0
            }
            
            summary = {
                'current_status': current_status,
                'indicator_scores': indicator_scores,
                'signal_stats': signal_stats,
                'weights': self.indicator_weights,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating integration summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 다중 지표 신호 통합기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 120:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 신호 통합기 초기화
        integrator = SignalIntegrator(confidence_threshold=0.7, min_indicators=3)
        
        # 2. 모든 지표 분석
        print(f"\n2. 모든 기술적 지표 분석 중...")
        analyzed_data = integrator.analyze_all_indicators(stock_data)
        
        # 3. 신호 점수 계산
        print(f"3. 지표별 신호 점수 계산 중...")
        scored_data = integrator.calculate_signal_scores(analyzed_data)
        
        # 4. 통합 신호 생성
        print(f"4. 통합 매매 신호 생성 중...")
        integrated_data = integrator.generate_integrated_signals(scored_data)
        
        # 5. 고신뢰도 신호 필터링
        print(f"5. 고신뢰도 신호 필터링 중...")
        filtered_data = integrator.filter_high_confidence_signals(integrated_data)
        
        # 6. 결과 분석
        print(f"\n=== 통합 신호 분석 결과 ===")
        
        latest = filtered_data.iloc[-1]
        print(f"현재가: {latest['close']:,.0f}원")
        print(f"통합 신호 강도: {latest['integrated_strength']:+.3f}")
        print(f"동의 지표 수: {latest['agreeing_indicators']}개")
        print(f"신호 품질: {latest['signal_quality']}")
        print(f"통합 신뢰도: {latest['integrated_confidence']:.2f}")
        
        # 각 지표별 점수
        print(f"\n=== 지표별 신호 점수 ===")
        print(f"이동평균: {latest['ma_score']:+.3f}")
        print(f"RSI: {latest['rsi_score']:+.3f}")
        print(f"MACD: {latest['macd_score']:+.3f}")
        print(f"볼린저밴드: {latest['bb_score']:+.3f}")
        print(f"거래량: {latest['volume_score']:+.3f}")
        
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
        
        # 최근 통합 신호
        recent_buy = filtered_data[filtered_data['integrated_buy_signal'] == 1].tail(1)
        recent_sell = filtered_data[filtered_data['integrated_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            buy_strength = recent_buy.iloc[0]['integrated_strength']
            buy_confidence = recent_buy.iloc[0]['integrated_confidence']
            buy_quality = recent_buy.iloc[0]['signal_quality']
            print(f"최근 통합 매수 신호: {buy_date} (강도: {buy_strength:.3f}, 신뢰도: {buy_confidence:.2f}, 품질: {buy_quality})")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']  
            sell_strength = recent_sell.iloc[0]['integrated_strength']
            sell_confidence = recent_sell.iloc[0]['integrated_confidence']
            sell_quality = recent_sell.iloc[0]['signal_quality']
            print(f"최근 통합 매도 신호: {sell_date} (강도: {sell_strength:.3f}, 신뢰도: {sell_confidence:.2f}, 품질: {sell_quality})")
        
        # 요약 정보
        summary = integrator.get_integration_summary(filtered_data)
        print(f"\n=== 요약 ===")
        print(f"5개 지표 통합 분석 완료 - 고정확도 신호 생성")
        print(f"최소 {integrator.min_indicators}개 지표 동의 + {integrator.confidence_threshold:.0%} 이상 신뢰도")
        
    else:
        print("   데이터 부족 - 최소 120일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()