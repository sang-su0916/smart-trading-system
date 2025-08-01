"""
MACD (Moving Average Convergence Divergence) 분석기
히스토그램 분석 및 신호선 교차를 통한 고정확도 매매 신호 생성
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

class MACDAnalyzer:
    """MACD 분석기 - 신호선 교차 + 히스토그램 + 다이버전스"""
    
    def __init__(self, 
                 fast_period: int = 12,
                 slow_period: int = 26,
                 signal_period: int = 9):
        """
        Args:
            fast_period: 빠른 EMA 기간 (기본: 12일)
            slow_period: 느린 EMA 기간 (기본: 26일)
            signal_period: 신호선 EMA 기간 (기본: 9일)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.logger = self._setup_logger()
        
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
    
    def calculate_macd(self, data: pd.DataFrame, 
                      price_column: str = 'close') -> pd.DataFrame:
        """
        MACD 계산
        
        Args:
            data: 주가 데이터
            price_column: 계산할 가격 컬럼명
            
        Returns:
            MACD가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # EMA 계산
            ema_fast = result[price_column].ewm(span=self.fast_period).mean()
            ema_slow = result[price_column].ewm(span=self.slow_period).mean()
            
            # MACD Line = Fast EMA - Slow EMA
            result['macd_line'] = ema_fast - ema_slow
            
            # Signal Line = MACD Line의 EMA
            result['macd_signal'] = result['macd_line'].ewm(span=self.signal_period).mean()
            
            # Histogram = MACD Line - Signal Line
            result['macd_histogram'] = result['macd_line'] - result['macd_signal']
            
            # MACD 상태 분류
            result['macd_trend'] = np.where(result['macd_line'] > 0, 'BULLISH', 'BEARISH')
            result['macd_momentum'] = np.where(result['macd_line'] > result['macd_signal'], 'POSITIVE', 'NEGATIVE')
            
            # MACD 변화율
            result['macd_line_change'] = result['macd_line'].diff()
            result['macd_histogram_change'] = result['macd_histogram'].diff()
            
            # 히스토그램 강도 (절댓값)
            result['macd_histogram_strength'] = abs(result['macd_histogram'])
            
            self.logger.info(f"MACD calculated with periods: {self.fast_period}, {self.slow_period}, {self.signal_period}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {str(e)}")
            return data
    
    def detect_macd_crossovers(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        MACD 신호선 교차 감지 (정확도 핵심)
        
        Args:
            data: MACD가 계산된 데이터
            
        Returns:
            교차 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'macd_line' not in result.columns:
                self.logger.warning("MACD not found in data. Calculating MACD first.")
                result = self.calculate_macd(result)
            
            # 교차 신호 초기화
            result['macd_cross_signal'] = 0
            result['macd_cross_strength'] = 0
            
            # 황금 교차 (Golden Cross): MACD Line이 Signal Line을 상향 돌파
            golden_cross = (
                (result['macd_line'] > result['macd_signal']) & 
                (result['macd_line'].shift(1) <= result['macd_signal'].shift(1))
            )
            
            # 죽음의 교차 (Death Cross): MACD Line이 Signal Line을 하향 돌파
            death_cross = (
                (result['macd_line'] < result['macd_signal']) & 
                (result['macd_line'].shift(1) >= result['macd_signal'].shift(1))
            )
            
            # 교차 강도 계산 (히스토그램 변화량 기반)
            cross_strength_golden = abs(result['macd_histogram']) * golden_cross
            cross_strength_death = abs(result['macd_histogram']) * death_cross
            
            # 신호 설정
            result.loc[golden_cross, 'macd_cross_signal'] = 1
            result.loc[death_cross, 'macd_cross_signal'] = -1
            
            result.loc[golden_cross, 'macd_cross_strength'] = cross_strength_golden[golden_cross]
            result.loc[death_cross, 'macd_cross_strength'] = -cross_strength_death[death_cross]
            
            cross_count = (result['macd_cross_signal'] != 0).sum()
            self.logger.info(f"Detected {cross_count} MACD crossover signals")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting MACD crossovers: {str(e)}")
            return data
    
    def analyze_histogram_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        히스토그램 패턴 분석 (모멘텀 변화 감지)
        
        Args:
            data: MACD 데이터
            
        Returns:
            히스토그램 패턴이 분석된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'macd_histogram' not in result.columns:
                result = self.calculate_macd(result)
            
            # 히스토그램 패턴 초기화
            result['histogram_pattern'] = 'NEUTRAL'
            result['histogram_divergence'] = 0
            result['momentum_acceleration'] = 0
            
            # 히스토그램 기울기 계산 (3일 평균)
            result['histogram_slope'] = result['macd_histogram'].diff().rolling(window=3).mean()
            
            # 모멘텀 가속도 (2차 미분)
            result['momentum_acceleration'] = result['histogram_slope'].diff()
            
            # 히스토그램 패턴 분류
            # 1. 상승 확산 (Rising Expansion): 히스토그램이 양수이면서 증가
            rising_expansion = (
                (result['macd_histogram'] > 0) & 
                (result['macd_histogram_change'] > 0) &
                (result['histogram_slope'] > 0)
            )
            result.loc[rising_expansion, 'histogram_pattern'] = 'RISING_EXPANSION'
            
            # 2. 상승 수축 (Rising Contraction): 히스토그램이 양수이지만 감소
            rising_contraction = (
                (result['macd_histogram'] > 0) & 
                (result['macd_histogram_change'] < 0) &
                (result['histogram_slope'] < 0)
            )
            result.loc[rising_contraction, 'histogram_pattern'] = 'RISING_CONTRACTION'
            
            # 3. 하락 확산 (Falling Expansion): 히스토그램이 음수이면서 더 감소
            falling_expansion = (
                (result['macd_histogram'] < 0) & 
                (result['macd_histogram_change'] < 0) &
                (result['histogram_slope'] < 0)
            )
            result.loc[falling_expansion, 'histogram_pattern'] = 'FALLING_EXPANSION'
            
            # 4. 하락 수축 (Falling Contraction): 히스토그램이 음수이지만 상승
            falling_contraction = (
                (result['macd_histogram'] < 0) & 
                (result['macd_histogram_change'] > 0) &
                (result['histogram_slope'] > 0)
            )
            result.loc[falling_contraction, 'histogram_pattern'] = 'FALLING_CONTRACTION'
            
            # 히스토그램 다이버전스 감지 (간단한 버전)
            # 가격이 상승하는데 히스토그램이 감소하는 경우 (약세 다이버전스)
            price_rising = result['close'] > result['close'].shift(5)
            histogram_falling = result['macd_histogram'] < result['macd_histogram'].shift(5)
            bearish_divergence = price_rising & histogram_falling & (result['macd_histogram'] > 0)
            result.loc[bearish_divergence, 'histogram_divergence'] = -1
            
            # 가격이 하락하는데 히스토그램이 증가하는 경우 (강세 다이버전스)  
            price_falling = result['close'] < result['close'].shift(5)
            histogram_rising = result['macd_histogram'] > result['macd_histogram'].shift(5)
            bullish_divergence = price_falling & histogram_rising & (result['macd_histogram'] < 0)
            result.loc[bullish_divergence, 'histogram_divergence'] = 1
            
            pattern_count = (result['histogram_pattern'] != 'NEUTRAL').sum()
            divergence_count = (result['histogram_divergence'] != 0).sum()
            self.logger.info(f"Analyzed histogram patterns: {pattern_count}, divergences: {divergence_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing histogram patterns: {str(e)}")
            return data
    
    def generate_macd_signals(self, data: pd.DataFrame,
                             use_histogram: bool = True,
                             confirmation_period: int = 2) -> pd.DataFrame:
        """
        MACD 기반 매매 신호 생성 (고정확도)
        
        Args:
            data: MACD 분석된 데이터
            use_histogram: 히스토그램 패턴 사용 여부
            confirmation_period: 신호 확인 기간
            
        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 신호 초기화
            result['macd_buy_signal'] = 0
            result['macd_sell_signal'] = 0
            result['macd_signal_strength'] = 0
            result['macd_confidence'] = 0
            
            # 1. 기본 교차 신호
            golden_cross = result['macd_cross_signal'] == 1
            death_cross = result['macd_cross_signal'] == -1
            
            # 2. 히스토그램 확인 신호 (더 높은 신뢰도)
            if use_histogram and 'histogram_pattern' in result.columns:
                # 강한 매수 신호: 골든크로스 + 상승 확산
                strong_buy = golden_cross & (result['histogram_pattern'] == 'RISING_EXPANSION')
                
                # 조기 매수 신호: 하락 수축 (바닥 근처)
                early_buy = (result['histogram_pattern'] == 'FALLING_CONTRACTION') & (result['momentum_acceleration'] > 0)
                
                # 강한 매도 신호: 데드크로스 + 하락 확산  
                strong_sell = death_cross & (result['histogram_pattern'] == 'FALLING_EXPANSION')
                
                # 조기 매도 신호: 상승 수축 (고점 근처)
                early_sell = (result['histogram_pattern'] == 'RISING_CONTRACTION') & (result['momentum_acceleration'] < 0)
                
                # 다이버전스 신호 (최고 신뢰도)
                div_buy = result['histogram_divergence'] == 1
                div_sell = result['histogram_divergence'] == -1
                
                # 신호 강도별 설정
                # 최고 신뢰도 (3점)
                result.loc[strong_buy | div_buy, 'macd_buy_signal'] = 1
                result.loc[strong_buy | div_buy, 'macd_signal_strength'] = 3
                result.loc[strong_buy | div_buy, 'macd_confidence'] = 0.9
                
                result.loc[strong_sell | div_sell, 'macd_sell_signal'] = 1
                result.loc[strong_sell | div_sell, 'macd_signal_strength'] = -3
                result.loc[strong_sell | div_sell, 'macd_confidence'] = 0.9
                
                # 높은 신뢰도 (2점) - 강한 신호가 없는 경우만
                high_confidence_buy = golden_cross & (result['macd_buy_signal'] == 0)
                high_confidence_sell = death_cross & (result['macd_sell_signal'] == 0)
                
                result.loc[high_confidence_buy, 'macd_buy_signal'] = 1
                result.loc[high_confidence_buy, 'macd_signal_strength'] = 2
                result.loc[high_confidence_buy, 'macd_confidence'] = 0.7
                
                result.loc[high_confidence_sell, 'macd_sell_signal'] = 1
                result.loc[high_confidence_sell, 'macd_signal_strength'] = -2
                result.loc[high_confidence_sell, 'macd_confidence'] = 0.7
                
                # 중간 신뢰도 (1점) - 조기 신호
                medium_confidence_buy = early_buy & (result['macd_buy_signal'] == 0)
                medium_confidence_sell = early_sell & (result['macd_sell_signal'] == 0)
                
                result.loc[medium_confidence_buy, 'macd_buy_signal'] = 1
                result.loc[medium_confidence_buy, 'macd_signal_strength'] = 1
                result.loc[medium_confidence_buy, 'macd_confidence'] = 0.5
                
                result.loc[medium_confidence_sell, 'macd_sell_signal'] = 1
                result.loc[medium_confidence_sell, 'macd_signal_strength'] = -1
                result.loc[medium_confidence_sell, 'macd_confidence'] = 0.5
                
            else:
                # 히스토그램 미사용 시 기본 교차 신호만
                result.loc[golden_cross, 'macd_buy_signal'] = 1
                result.loc[golden_cross, 'macd_signal_strength'] = 2
                result.loc[golden_cross, 'macd_confidence'] = 0.6
                
                result.loc[death_cross, 'macd_sell_signal'] = 1
                result.loc[death_cross, 'macd_signal_strength'] = -2
                result.loc[death_cross, 'macd_confidence'] = 0.6
            
            # 신호 확인 (잡음 제거)
            if confirmation_period > 1:
                result = self._apply_macd_confirmation(result, confirmation_period)
            
            buy_signals = (result['macd_buy_signal'] == 1).sum()
            sell_signals = (result['macd_sell_signal'] == 1).sum()
            avg_confidence = result[result['macd_confidence'] > 0]['macd_confidence'].mean()
            
            self.logger.info(f"Generated MACD signals - Buy: {buy_signals}, Sell: {sell_signals}, Avg Confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating MACD signals: {str(e)}")
            return data
    
    def _apply_macd_confirmation(self, data: pd.DataFrame, 
                                confirmation_period: int) -> pd.DataFrame:
        """MACD 신호 확인 적용"""
        try:
            result = data.copy()
            
            # 확인된 신호만 유지
            buy_confirmed = result['macd_buy_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            sell_confirmed = result['macd_sell_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            result['macd_buy_signal_confirmed'] = buy_confirmed
            result['macd_sell_signal_confirmed'] = sell_confirmed
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying MACD confirmation: {str(e)}")
            return data
    
    def get_macd_summary(self, data: pd.DataFrame) -> Dict:
        """MACD 분석 요약"""
        try:
            if data.empty or 'macd_line' not in data.columns:
                return {}
            
            latest = data.iloc[-1]
            
            # MACD 통계
            macd_stats = {
                'macd_line': float(latest['macd_line']) if not pd.isna(latest['macd_line']) else 0.0,
                'macd_signal': float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) else 0.0,
                'macd_histogram': float(latest['macd_histogram']) if not pd.isna(latest['macd_histogram']) else 0.0,
                'macd_trend': str(latest['macd_trend']) if 'macd_trend' in data.columns else 'UNKNOWN',
                'macd_momentum': str(latest['macd_momentum']) if 'macd_momentum' in data.columns else 'UNKNOWN',
                'histogram_pattern': str(latest['histogram_pattern']) if 'histogram_pattern' in data.columns else 'UNKNOWN'
            }
            
            # 신호 통계
            signal_stats = {
                'total_buy_signals': int((data['macd_buy_signal'] == 1).sum()) if 'macd_buy_signal' in data.columns else 0,
                'total_sell_signals': int((data['macd_sell_signal'] == 1).sum()) if 'macd_sell_signal' in data.columns else 0,
                'crossover_signals': int((data['macd_cross_signal'] != 0).sum()) if 'macd_cross_signal' in data.columns else 0,
                'histogram_divergences': int((data['histogram_divergence'] != 0).sum()) if 'histogram_divergence' in data.columns else 0,
                'avg_confidence': float(data[data['macd_confidence'] > 0]['macd_confidence'].mean()) if 'macd_confidence' in data.columns else 0.0
            }
            
            summary = {
                'macd_stats': macd_stats,
                'signal_stats': signal_stats,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating MACD summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== MACD 분석기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 50:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # MACD 분석기 초기화
        macd_analyzer = MACDAnalyzer(fast_period=12, slow_period=26, signal_period=9)
        
        # 2. MACD 계산
        print(f"\n2. MACD 계산 중...")
        macd_data = macd_analyzer.calculate_macd(stock_data)
        
        # 3. 신호선 교차 감지
        print(f"3. MACD 신호선 교차 감지 중...")
        cross_data = macd_analyzer.detect_macd_crossovers(macd_data)
        
        # 4. 히스토그램 패턴 분석
        print(f"4. 히스토그램 패턴 분석 중...")
        histogram_data = macd_analyzer.analyze_histogram_patterns(cross_data)
        
        # 5. 매매 신호 생성
        print(f"5. MACD 매매 신호 생성 중...")
        signal_data = macd_analyzer.generate_macd_signals(histogram_data, use_histogram=True)
        
        # 6. 결과 분석
        print(f"\n=== MACD 분석 결과 ===")
        
        latest = signal_data.iloc[-1]
        print(f"MACD Line: {latest['macd_line']:.4f}")
        print(f"Signal Line: {latest['macd_signal']:.4f}")
        print(f"히스토그램: {latest['macd_histogram']:.4f}")
        print(f"MACD 트렌드: {latest['macd_trend']}")
        print(f"MACD 모멘텀: {latest['macd_momentum']}")
        print(f"히스토그램 패턴: {latest['histogram_pattern']}")
        
        # 신호 통계
        buy_signals = (signal_data['macd_buy_signal'] == 1).sum()
        sell_signals = (signal_data['macd_sell_signal'] == 1).sum()
        crossovers = (signal_data['macd_cross_signal'] != 0).sum()
        divergences = (signal_data['histogram_divergence'] != 0).sum()
        avg_confidence = signal_data[signal_data['macd_confidence'] > 0]['macd_confidence'].mean()
        
        print(f"\n매수 신호: {buy_signals}회")
        print(f"매도 신호: {sell_signals}회")
        print(f"교차 신호: {crossovers}회")
        print(f"히스토그램 다이버전스: {divergences}회")
        print(f"평균 신뢰도: {avg_confidence:.2f}")
        
        # 최근 신호
        recent_buy = signal_data[signal_data['macd_buy_signal'] == 1].tail(1)
        recent_sell = signal_data[signal_data['macd_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            buy_strength = recent_buy.iloc[0]['macd_signal_strength']
            buy_confidence = recent_buy.iloc[0]['macd_confidence']
            print(f"최근 매수 신호: {buy_date} (강도: {buy_strength}, 신뢰도: {buy_confidence:.2f})")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']
            sell_strength = recent_sell.iloc[0]['macd_signal_strength']
            sell_confidence = recent_sell.iloc[0]['macd_confidence']
            print(f"최근 매도 신호: {sell_date} (강도: {sell_strength}, 신뢰도: {sell_confidence:.2f})")
        
        # 히스토그램 패턴 통계
        pattern_counts = signal_data['histogram_pattern'].value_counts()
        print(f"\n히스토그램 패턴 분포:")
        for pattern, count in pattern_counts.items():
            print(f"  {pattern}: {count}회")
        
        # 요약 정보
        summary = macd_analyzer.get_macd_summary(signal_data)
        print(f"\n=== 요약 ===")
        print(f"MACD 분석 완료 - 히스토그램 패턴 + 다이버전스 감지")
        print(f"신호 품질: 3단계 신뢰도 (0.5~0.9)")
        
    else:
        print("   데이터 부족 - 최소 50일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()