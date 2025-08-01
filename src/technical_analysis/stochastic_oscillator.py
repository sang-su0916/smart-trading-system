"""
스토캐스틱 오실레이터 (Stochastic Oscillator) 분석기
%K, %D 지표를 통한 과매수/과매도 신호 생성 및 다이버전스 감지
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

class StochasticOscillator:
    """스토캐스틱 오실레이터 분석기 - %K, %D 지표 + 다이버전스"""
    
    def __init__(self, 
                 k_period: int = 14,
                 d_period: int = 3,
                 slow_k_period: int = 3):
        """
        Args:
            k_period: %K 계산 기간 (기본: 14일)
            d_period: %D 계산 기간 (기본: 3일)
            slow_k_period: Slow %K 계산 기간 (기본: 3일)
        """
        self.k_period = k_period
        self.d_period = d_period
        self.slow_k_period = slow_k_period
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
    
    def calculate_stochastic(self, data: pd.DataFrame,
                           high_column: str = 'high',
                           low_column: str = 'low',
                           close_column: str = 'close') -> pd.DataFrame:
        """
        스토캐스틱 오실레이터 계산 (%K, %D, Slow %K)
        
        Args:
            data: OHLC 데이터
            high_column: 고가 컬럼명
            low_column: 저가 컬럼명
            close_column: 종가 컬럼명
            
        Returns:
            스토캐스틱 지표가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 최고가와 최저가 계산 (k_period 기간)
            rolling_high = result[high_column].rolling(window=self.k_period).max()
            rolling_low = result[low_column].rolling(window=self.k_period).min()
            
            # Fast %K 계산
            # %K = (현재 종가 - 최저가) / (최고가 - 최저가) * 100
            high_low_diff = rolling_high - rolling_low
            close_low_diff = result[close_column] - rolling_low
            
            result['stoch_k_fast'] = np.where(
                high_low_diff != 0,
                (close_low_diff / high_low_diff) * 100,
                50.0  # 분모가 0일 때 중립값
            )
            
            # Slow %K 계산 (Fast %K의 이동평균)
            result['stoch_k'] = result['stoch_k_fast'].rolling(window=self.slow_k_period).mean()
            
            # %D 계산 (Slow %K의 이동평균)
            result['stoch_d'] = result['stoch_k'].rolling(window=self.d_period).mean()
            
            # %K와 %D의 차이
            result['stoch_k_d_diff'] = result['stoch_k'] - result['stoch_d']
            
            # 상태 분류
            result['stoch_status'] = 'NEUTRAL'
            result.loc[result['stoch_k'] >= 80, 'stoch_status'] = 'OVERBOUGHT'
            result.loc[result['stoch_k'] <= 20, 'stoch_status'] = 'OVERSOLD'
            result.loc[(result['stoch_k'] > 50) & (result['stoch_k'] < 80), 'stoch_status'] = 'BULLISH'
            result.loc[(result['stoch_k'] < 50) & (result['stoch_k'] > 20), 'stoch_status'] = 'BEARISH'
            
            self.logger.info(f"Stochastic Oscillator calculated with K({self.k_period}), D({self.d_period})")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating Stochastic Oscillator: {str(e)}")
            return data
    
    def detect_stochastic_crossovers(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        %K와 %D 교차점 감지
        
        Args:
            data: 스토캐스틱 지표가 있는 데이터
            
        Returns:
            교차점이 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'stoch_k' not in result.columns or 'stoch_d' not in result.columns:
                result = self.calculate_stochastic(result)
            
            # 교차점 신호 초기화
            result['stoch_crossover'] = 0
            result['stoch_crossover_type'] = 'NONE'
            
            # %K가 %D를 상향 돌파 (골든 크로스)
            k_above_d = result['stoch_k'] > result['stoch_d']
            k_above_d_prev = result['stoch_k'].shift(1) > result['stoch_d'].shift(1)
            golden_cross = k_above_d & ~k_above_d_prev
            
            # %K가 %D를 하향 돌파 (데드 크로스)
            k_below_d = result['stoch_k'] < result['stoch_d']
            k_below_d_prev = result['stoch_k'].shift(1) < result['stoch_d'].shift(1)
            death_cross = k_below_d & ~k_below_d_prev
            
            # 교차점 설정
            result.loc[golden_cross, 'stoch_crossover'] = 1
            result.loc[golden_cross, 'stoch_crossover_type'] = 'GOLDEN_CROSS'
            
            result.loc[death_cross, 'stoch_crossover'] = -1
            result.loc[death_cross, 'stoch_crossover_type'] = 'DEATH_CROSS'
            
            # 교차점 강도 계산 (교차 시 %K와 %D 간 거리)
            result['crossover_strength'] = 0.0
            crossover_mask = result['stoch_crossover'] != 0
            result.loc[crossover_mask, 'crossover_strength'] = abs(
                result.loc[crossover_mask, 'stoch_k_d_diff']
            )
            
            crossover_count = (result['stoch_crossover'] != 0).sum()
            self.logger.info(f"Detected {crossover_count} Stochastic crossovers")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting Stochastic crossovers: {str(e)}")
            return data
    
    def detect_stochastic_divergences(self, data: pd.DataFrame,
                                     price_column: str = 'close',
                                     lookback_period: int = 20) -> pd.DataFrame:
        """
        스토캐스틱 다이버전스 감지
        
        Args:
            data: 스토캐스틱과 가격 데이터
            price_column: 가격 컬럼명
            lookback_period: 다이버전스 감지 기간
            
        Returns:
            다이버전스 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'stoch_k' not in result.columns:
                result = self.calculate_stochastic(result)
            
            # 다이버전스 신호 초기화
            result['stoch_divergence'] = 0
            result['stoch_divergence_strength'] = 0.0
            result['stoch_divergence_type'] = 'NONE'
            
            # 국소 고점/저점 찾기
            price_highs = self._find_local_peaks(result[price_column], lookback_period, 'high')
            price_lows = self._find_local_peaks(result[price_column], lookback_period, 'low')
            stoch_highs = self._find_local_peaks(result['stoch_k'], lookback_period, 'high')
            stoch_lows = self._find_local_peaks(result['stoch_k'], lookback_period, 'low')
            
            # 강세 다이버전스 감지 (가격 저점 하락, 스토캐스틱 저점 상승)
            for i in range(lookback_period, len(result)):
                current_date = result.index[i]
                
                # 최근 lookback_period 내 고점/저점 찾기
                recent_period = slice(max(0, i - lookback_period), i + 1)
                
                recent_price_lows = price_lows[recent_period]
                recent_stoch_lows = stoch_lows[recent_period]
                
                if len(recent_price_lows) >= 2 and len(recent_stoch_lows) >= 2:
                    # 가격 저점들
                    price_low_values = result[price_column].iloc[recent_price_lows].values
                    stoch_low_values = result['stoch_k'].iloc[recent_stoch_lows].values
                    
                    if len(price_low_values) >= 2 and len(stoch_low_values) >= 2:
                        # 강세 다이버전스: 가격은 더 낮은 저점, 스토캐스틱은 더 높은 저점
                        if (price_low_values[-1] < price_low_values[-2] and 
                            stoch_low_values[-1] > stoch_low_values[-2]):
                            
                            price_diff = (price_low_values[-2] - price_low_values[-1]) / price_low_values[-2]
                            stoch_diff = (stoch_low_values[-1] - stoch_low_values[-2]) / 100
                            
                            if price_diff > 0.02 and stoch_diff > 0.05:  # 임계값 확인
                                result.iloc[i, result.columns.get_loc('stoch_divergence')] = 1
                                result.iloc[i, result.columns.get_loc('stoch_divergence_type')] = 'BULLISH'
                                result.iloc[i, result.columns.get_loc('stoch_divergence_strength')] = price_diff + stoch_diff
                
                # 약세 다이버전스 감지 (가격 고점 상승, 스토캐스틱 고점 하락)
                recent_price_highs = price_highs[recent_period]
                recent_stoch_highs = stoch_highs[recent_period]
                
                if len(recent_price_highs) >= 2 and len(recent_stoch_highs) >= 2:
                    price_high_values = result[price_column].iloc[recent_price_highs].values
                    stoch_high_values = result['stoch_k'].iloc[recent_stoch_highs].values
                    
                    if len(price_high_values) >= 2 and len(stoch_high_values) >= 2:
                        # 약세 다이버전스: 가격은 더 높은 고점, 스토캐스틱은 더 낮은 고점
                        if (price_high_values[-1] > price_high_values[-2] and 
                            stoch_high_values[-1] < stoch_high_values[-2]):
                            
                            price_diff = (price_high_values[-1] - price_high_values[-2]) / price_high_values[-2]
                            stoch_diff = (stoch_high_values[-2] - stoch_high_values[-1]) / 100
                            
                            if price_diff > 0.02 and stoch_diff > 0.05:  # 임계값 확인
                                result.iloc[i, result.columns.get_loc('stoch_divergence')] = -1
                                result.iloc[i, result.columns.get_loc('stoch_divergence_type')] = 'BEARISH'
                                result.iloc[i, result.columns.get_loc('stoch_divergence_strength')] = price_diff + stoch_diff
            
            divergence_count = (result['stoch_divergence'] != 0).sum()
            self.logger.info(f"Detected {divergence_count} Stochastic divergences")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting Stochastic divergences: {str(e)}")
            return data
    
    def _find_local_peaks(self, series: pd.Series, window: int, peak_type: str) -> np.ndarray:
        """국소 고점/저점 찾기"""
        try:
            peaks = []
            
            for i in range(window, len(series) - window):
                current_val = series.iloc[i]
                window_data = series.iloc[i-window:i+window+1]
                
                if peak_type == 'high':
                    if current_val == window_data.max():
                        peaks.append(i)
                elif peak_type == 'low':
                    if current_val == window_data.min():
                        peaks.append(i)
            
            return np.array(peaks)
            
        except Exception as e:
            self.logger.error(f"Error finding local peaks: {str(e)}")
            return np.array([])
    
    def generate_stochastic_signals(self, data: pd.DataFrame,
                                   use_divergence: bool = True,
                                   confirmation_period: int = 2) -> pd.DataFrame:
        """
        스토캐스틱 기반 매매 신호 생성 (고정확도)
        
        Args:
            data: 스토캐스틱 분석된 데이터
            use_divergence: 다이버전스 신호 사용 여부
            confirmation_period: 신호 확인 기간
            
        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 신호 초기화
            result['stoch_buy_signal'] = 0
            result['stoch_sell_signal'] = 0
            result['stoch_signal_strength'] = 0
            result['stoch_confidence'] = 0
            
            # 1. 과매도 구간 반등 신호 (최고 신뢰도)
            oversold_bounce = (
                (result['stoch_status'] == 'OVERSOLD') &  # 과매도 구간
                (result['stoch_crossover'] == 1) &        # %K가 %D 상향 돌파
                (result['stoch_k'] < 30)                  # %K가 30 이하
            )
            
            # 2. 과매수 구간 반락 신호 (최고 신뢰도)
            overbought_decline = (
                (result['stoch_status'] == 'OVERBOUGHT') &  # 과매수 구간
                (result['stoch_crossover'] == -1) &         # %K가 %D 하향 돌파
                (result['stoch_k'] > 70)                    # %K가 70 이상
            )
            
            # 최고 신뢰도 신호 설정
            result.loc[oversold_bounce, 'stoch_buy_signal'] = 1
            result.loc[oversold_bounce, 'stoch_signal_strength'] = 3
            result.loc[oversold_bounce, 'stoch_confidence'] = 0.85
            
            result.loc[overbought_decline, 'stoch_sell_signal'] = 1
            result.loc[overbought_decline, 'stoch_signal_strength'] = -3
            result.loc[overbought_decline, 'stoch_confidence'] = 0.85
            
            # 3. 다이버전스 신호 (높은 신뢰도)
            if use_divergence and 'stoch_divergence' in result.columns:
                strong_bullish_div = (
                    (result['stoch_divergence'] == 1) &
                    (result['stoch_divergence_strength'] > 0.1) &
                    (result['stoch_buy_signal'] == 0)  # 기존 신호가 없는 경우만
                )
                
                strong_bearish_div = (
                    (result['stoch_divergence'] == -1) &
                    (result['stoch_divergence_strength'] > 0.1) &
                    (result['stoch_sell_signal'] == 0)  # 기존 신호가 없는 경우만
                )
                
                result.loc[strong_bullish_div, 'stoch_buy_signal'] = 1
                result.loc[strong_bullish_div, 'stoch_signal_strength'] = 2
                result.loc[strong_bullish_div, 'stoch_confidence'] = 0.75
                
                result.loc[strong_bearish_div, 'stoch_sell_signal'] = 1
                result.loc[strong_bearish_div, 'stoch_signal_strength'] = -2
                result.loc[strong_bearish_div, 'stoch_confidence'] = 0.75
            
            # 4. 일반 교차점 신호 (중간 신뢰도)
            general_golden_cross = (
                (result['stoch_crossover'] == 1) &
                (result['stoch_k'] < 50) &  # 중간선 아래에서 교차
                (result['stoch_buy_signal'] == 0)  # 기존 신호가 없는 경우만
            )
            
            general_death_cross = (
                (result['stoch_crossover'] == -1) &
                (result['stoch_k'] > 50) &  # 중간선 위에서 교차
                (result['stoch_sell_signal'] == 0)  # 기존 신호가 없는 경우만
            )
            
            result.loc[general_golden_cross, 'stoch_buy_signal'] = 1
            result.loc[general_golden_cross, 'stoch_signal_strength'] = 1
            result.loc[general_golden_cross, 'stoch_confidence'] = 0.6
            
            result.loc[general_death_cross, 'stoch_sell_signal'] = 1
            result.loc[general_death_cross, 'stoch_signal_strength'] = -1
            result.loc[general_death_cross, 'stoch_confidence'] = 0.6
            
            # 신호 확인 (잡음 제거)
            if confirmation_period > 1:
                result = self._apply_stochastic_confirmation(result, confirmation_period)
            
            buy_signals = (result['stoch_buy_signal'] == 1).sum()
            sell_signals = (result['stoch_sell_signal'] == 1).sum()
            avg_confidence = result[result['stoch_confidence'] > 0]['stoch_confidence'].mean()
            
            self.logger.info(f"Generated Stochastic signals - Buy: {buy_signals}, Sell: {sell_signals}, Avg Confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating Stochastic signals: {str(e)}")
            return data
    
    def _apply_stochastic_confirmation(self, data: pd.DataFrame, 
                                     confirmation_period: int) -> pd.DataFrame:
        """스토캐스틱 신호 확인 적용"""
        try:
            result = data.copy()
            
            # 확인된 신호만 유지
            buy_confirmed = result['stoch_buy_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            sell_confirmed = result['stoch_sell_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            result['stoch_buy_signal_confirmed'] = buy_confirmed
            result['stoch_sell_signal_confirmed'] = sell_confirmed
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying Stochastic confirmation: {str(e)}")
            return data
    
    def get_stochastic_summary(self, data: pd.DataFrame) -> Dict:
        """스토캐스틱 분석 요약"""
        try:
            if data.empty or 'stoch_k' not in data.columns:
                return {}
            
            latest = data.iloc[-1]
            
            # 스토캐스틱 통계
            stoch_stats = {
                'stoch_k': float(latest['stoch_k']) if not pd.isna(latest['stoch_k']) else 0.0,
                'stoch_d': float(latest['stoch_d']) if not pd.isna(latest['stoch_d']) else 0.0,
                'k_d_diff': float(latest['stoch_k_d_diff']) if 'stoch_k_d_diff' in data.columns and not pd.isna(latest['stoch_k_d_diff']) else 0.0,
                'status': str(latest['stoch_status']) if 'stoch_status' in data.columns else 'UNKNOWN',
                'crossover_type': str(latest['stoch_crossover_type']) if 'stoch_crossover_type' in data.columns else 'NONE'
            }
            
            # 신호 통계
            signal_stats = {
                'total_buy_signals': int((data['stoch_buy_signal'] == 1).sum()) if 'stoch_buy_signal' in data.columns else 0,
                'total_sell_signals': int((data['stoch_sell_signal'] == 1).sum()) if 'stoch_sell_signal' in data.columns else 0,
                'crossovers': int((data['stoch_crossover'] != 0).sum()) if 'stoch_crossover' in data.columns else 0,
                'divergences': int((data['stoch_divergence'] != 0).sum()) if 'stoch_divergence' in data.columns else 0,
                'avg_confidence': float(data[data['stoch_confidence'] > 0]['stoch_confidence'].mean()) if 'stoch_confidence' in data.columns else 0.0
            }
            
            summary = {
                'stoch_stats': stoch_stats,
                'signal_stats': signal_stats,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating Stochastic summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 스토캐스틱 오실레이터 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 50:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 스토캐스틱 분석기 초기화
        stoch_analyzer = StochasticOscillator(k_period=14, d_period=3, slow_k_period=3)
        
        # 2. 스토캐스틱 계산
        print(f"\n2. 스토캐스틱 오실레이터 계산 중...")
        stoch_data = stoch_analyzer.calculate_stochastic(stock_data)
        
        # 3. 교차점 감지
        print(f"3. %K/%D 교차점 감지 중...")
        crossover_data = stoch_analyzer.detect_stochastic_crossovers(stoch_data)
        
        # 4. 다이버전스 감지
        print(f"4. 스토캐스틱 다이버전스 감지 중...")
        divergence_data = stoch_analyzer.detect_stochastic_divergences(crossover_data)
        
        # 5. 매매 신호 생성
        print(f"5. 스토캐스틱 매매 신호 생성 중...")
        signal_data = stoch_analyzer.generate_stochastic_signals(divergence_data, use_divergence=True)
        
        # 6. 결과 분석
        print(f"\n=== 스토캐스틱 오실레이터 분석 결과 ===")
        
        latest = signal_data.iloc[-1]
        print(f"현재가: {latest['close']:,.0f}원")
        print(f"%K: {latest['stoch_k']:.1f}")
        print(f"%D: {latest['stoch_d']:.1f}")
        print(f"K-D 차이: {latest['stoch_k_d_diff']:+.1f}")
        print(f"상태: {latest['stoch_status']}")
        print(f"교차점: {latest['stoch_crossover_type']}")
        
        # 신호 통계
        buy_signals = (signal_data['stoch_buy_signal'] == 1).sum()
        sell_signals = (signal_data['stoch_sell_signal'] == 1).sum()
        crossovers = (signal_data['stoch_crossover'] != 0).sum()
        divergences = (signal_data['stoch_divergence'] != 0).sum()
        avg_confidence = signal_data[signal_data['stoch_confidence'] > 0]['stoch_confidence'].mean()
        
        print(f"\n매수 신호: {buy_signals}회")
        print(f"매도 신호: {sell_signals}회")
        print(f"교차점: {crossovers}회")
        print(f"다이버전스: {divergences}회")
        print(f"평균 신뢰도: {avg_confidence:.2f}")
        
        # 최근 신호
        recent_buy = signal_data[signal_data['stoch_buy_signal'] == 1].tail(1)
        recent_sell = signal_data[signal_data['stoch_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            buy_strength = recent_buy.iloc[0]['stoch_signal_strength']
            buy_confidence = recent_buy.iloc[0]['stoch_confidence']
            print(f"최근 매수 신호: {buy_date} (강도: {buy_strength}, 신뢰도: {buy_confidence:.2f})")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']
            sell_strength = recent_sell.iloc[0]['stoch_signal_strength']
            sell_confidence = recent_sell.iloc[0]['stoch_confidence']
            print(f"최근 매도 신호: {sell_date} (강도: {sell_strength}, 신뢰도: {sell_confidence:.2f})")
        
        # 상태 분포
        status_counts = signal_data['stoch_status'].value_counts()
        print(f"\n스토캐스틱 상태 분포:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}회")
        
        # 요약 정보
        summary = stoch_analyzer.get_stochastic_summary(signal_data)
        print(f"\n=== 요약 ===")
        print(f"스토캐스틱 오실레이터 분석 완료 - %K/%D 교차 + 다이버전스 감지")
        print(f"신호 품질: 3단계 신뢰도 (0.6~0.85)")
        
    else:
        print("   데이터 부족 - 최소 50일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()