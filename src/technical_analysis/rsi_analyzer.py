"""
RSI (Relative Strength Index) 분석기
다이버전스 패턴 감지를 통한 고정확도 매매 신호 생성
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from scipy.signal import find_peaks, find_peaks_cwt

class RSIAnalyzer:
    """RSI 분석기 - 과매수/과매도 + 다이버전스 패턴 감지"""
    
    def __init__(self, 
                 period: int = 14,
                 oversold_level: float = 30.0,
                 overbought_level: float = 70.0):
        """
        Args:
            period: RSI 계산 기간 (기본: 14일)
            oversold_level: 과매도 기준선 (기본: 30)
            overbought_level: 과매수 기준선 (기본: 70)
        """
        self.period = period
        self.oversold_level = oversold_level
        self.overbought_level = overbought_level
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
    
    def calculate_rsi(self, data: pd.DataFrame, 
                     price_column: str = 'close') -> pd.DataFrame:
        """
        RSI 계산
        
        Args:
            data: 주가 데이터
            price_column: 계산할 가격 컬럼명
            
        Returns:
            RSI가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 가격 변화 계산
            price_diff = result[price_column].diff()
            
            # 상승분과 하락분 분리
            gains = price_diff.where(price_diff > 0, 0)
            losses = -price_diff.where(price_diff < 0, 0)
            
            # 지수 이동평균 계산 (Wilder's smoothing)
            alpha = 1.0 / self.period
            avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
            avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()
            
            # RSI 계산
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            result['rsi'] = rsi
            
            # RSI 상태 분류
            result['rsi_status'] = 'NEUTRAL'
            result.loc[result['rsi'] <= self.oversold_level, 'rsi_status'] = 'OVERSOLD'
            result.loc[result['rsi'] >= self.overbought_level, 'rsi_status'] = 'OVERBOUGHT'
            
            # RSI 변화율
            result['rsi_change'] = result['rsi'].diff()
            
            # RSI 모멘텀 (5일 평균 변화율)
            result['rsi_momentum'] = result['rsi_change'].rolling(window=5).mean()
            
            self.logger.info(f"RSI calculated with period {self.period}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {str(e)}")
            return data
    
    def detect_divergences(self, data: pd.DataFrame,
                          price_column: str = 'close',
                          lookback_period: int = 20) -> pd.DataFrame:
        """
        다이버전스 패턴 감지 (정확도 핵심)
        
        Args:
            data: RSI가 계산된 데이터
            price_column: 가격 컬럼명
            lookback_period: 고점/저점 탐지 기간
            
        Returns:
            다이버전스 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'rsi' not in result.columns:
                self.logger.warning("RSI not found in data. Calculating RSI first.")
                result = self.calculate_rsi(result, price_column)
            
            # 다이버전스 신호 초기화
            result['bullish_divergence'] = 0
            result['bearish_divergence'] = 0
            result['divergence_strength'] = 0
            
            # 고점과 저점 찾기
            price_highs = self._find_local_peaks(result[price_column], lookback_period, 'high')
            price_lows = self._find_local_peaks(result[price_column], lookback_period, 'low')
            rsi_highs = self._find_local_peaks(result['rsi'], lookback_period, 'high')
            rsi_lows = self._find_local_peaks(result['rsi'], lookback_period, 'low')
            
            # 강세 다이버전스 (Bullish Divergence) 감지
            # 가격은 더 낮은 저점, RSI는 더 높은 저점
            for i in range(1, len(price_lows)):
                if i < len(rsi_lows):
                    curr_price_idx = price_lows[i]
                    prev_price_idx = price_lows[i-1]
                    curr_rsi_idx = rsi_lows[i] if i < len(rsi_lows) else curr_price_idx
                    prev_rsi_idx = rsi_lows[i-1] if i-1 < len(rsi_lows) else prev_price_idx
                    
                    # 조건 확인
                    price_lower = result.iloc[curr_price_idx][price_column] < result.iloc[prev_price_idx][price_column]
                    rsi_higher = result.iloc[curr_rsi_idx]['rsi'] > result.iloc[prev_rsi_idx]['rsi']
                    
                    if price_lower and rsi_higher:
                        # 강세 다이버전스 발생
                        strength = self._calculate_divergence_strength(
                            result.iloc[prev_price_idx][price_column],
                            result.iloc[curr_price_idx][price_column],
                            result.iloc[prev_rsi_idx]['rsi'],
                            result.iloc[curr_rsi_idx]['rsi']
                        )
                        
                        if strength > 0.3:  # 임계값 이상인 경우만
                            result.iloc[curr_price_idx, result.columns.get_loc('bullish_divergence')] = 1
                            result.iloc[curr_price_idx, result.columns.get_loc('divergence_strength')] = strength
            
            # 약세 다이버전스 (Bearish Divergence) 감지
            # 가격은 더 높은 고점, RSI는 더 낮은 고점
            for i in range(1, len(price_highs)):
                if i < len(rsi_highs):
                    curr_price_idx = price_highs[i]
                    prev_price_idx = price_highs[i-1]
                    curr_rsi_idx = rsi_highs[i] if i < len(rsi_highs) else curr_price_idx
                    prev_rsi_idx = rsi_highs[i-1] if i-1 < len(rsi_highs) else prev_price_idx
                    
                    # 조건 확인
                    price_higher = result.iloc[curr_price_idx][price_column] > result.iloc[prev_price_idx][price_column]
                    rsi_lower = result.iloc[curr_rsi_idx]['rsi'] < result.iloc[prev_rsi_idx]['rsi']
                    
                    if price_higher and rsi_lower:
                        # 약세 다이버전스 발생
                        strength = self._calculate_divergence_strength(
                            result.iloc[prev_price_idx][price_column],
                            result.iloc[curr_price_idx][price_column],
                            result.iloc[prev_rsi_idx]['rsi'],
                            result.iloc[curr_rsi_idx]['rsi']
                        )
                        
                        if strength > 0.3:  # 임계값 이상인 경우만
                            result.iloc[curr_price_idx, result.columns.get_loc('bearish_divergence')] = 1
                            result.iloc[curr_price_idx, result.columns.get_loc('divergence_strength')] = -strength
            
            divergence_count = (result['bullish_divergence'] == 1).sum() + (result['bearish_divergence'] == 1).sum()
            self.logger.info(f"Detected {divergence_count} divergence patterns")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting divergences: {str(e)}")
            return data
    
    def _find_local_peaks(self, series: pd.Series, 
                         lookback: int, 
                         peak_type: str) -> List[int]:
        """고점/저점 찾기"""
        try:
            if peak_type == 'high':
                # 고점 찾기
                peaks, _ = find_peaks(series, distance=lookback//2)
                return peaks.tolist()
            else:
                # 저점 찾기 (음수로 변환 후 고점 찾기)
                peaks, _ = find_peaks(-series, distance=lookback//2)
                return peaks.tolist()
                
        except Exception as e:
            self.logger.error(f"Error finding peaks: {str(e)}")
            return []
    
    def _calculate_divergence_strength(self, prev_price: float, curr_price: float,
                                      prev_rsi: float, curr_rsi: float) -> float:
        """다이버전스 강도 계산"""
        try:
            # 가격 변화율과 RSI 변화율의 차이로 강도 계산
            price_change = (curr_price - prev_price) / prev_price
            rsi_change = (curr_rsi - prev_rsi) / prev_rsi
            
            # 강도는 두 변화율의 차이의 절댓값
            strength = abs(price_change - rsi_change)
            
            # 0~1 범위로 정규화
            return min(strength, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating divergence strength: {str(e)}")
            return 0.0
    
    def generate_rsi_signals(self, data: pd.DataFrame,
                            use_divergence: bool = True,
                            confirmation_period: int = 2) -> pd.DataFrame:
        """
        RSI 기반 매매 신호 생성 (고정확도)
        
        Args:
            data: RSI 분석된 데이터
            use_divergence: 다이버전스 신호 사용 여부
            confirmation_period: 신호 확인 기간
            
        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 신호 초기화
            result['rsi_buy_signal'] = 0
            result['rsi_sell_signal'] = 0
            result['rsi_signal_strength'] = 0
            
            # 기본 RSI 신호
            oversold_recovery = (
                (result['rsi'] > self.oversold_level) & 
                (result['rsi'].shift(1) <= self.oversold_level) &
                (result['rsi_momentum'] > 0)  # 상승 모멘텀 확인
            )
            
            overbought_decline = (
                (result['rsi'] < self.overbought_level) & 
                (result['rsi'].shift(1) >= self.overbought_level) &
                (result['rsi_momentum'] < 0)  # 하락 모멘텀 확인
            )
            
            # 다이버전스 신호 (높은 신뢰도)
            if use_divergence and 'bullish_divergence' in result.columns:
                strong_bullish_div = (
                    (result['bullish_divergence'] == 1) &
                    (result['divergence_strength'] > 0.5)
                )
                
                strong_bearish_div = (
                    (result['bearish_divergence'] == 1) &
                    (result['divergence_strength'] < -0.5)
                )
                
                # 다이버전스 신호가 있으면 우선 적용
                result.loc[strong_bullish_div, 'rsi_buy_signal'] = 1
                result.loc[strong_bullish_div, 'rsi_signal_strength'] = 2  # 높은 신뢰도
                
                result.loc[strong_bearish_div, 'rsi_sell_signal'] = 1
                result.loc[strong_bearish_div, 'rsi_signal_strength'] = -2  # 높은 신뢰도
            
            # 기본 RSI 신호 (다이버전스 신호가 없는 경우)
            no_divergence_buy = (oversold_recovery) & (result['rsi_buy_signal'] == 0)
            no_divergence_sell = (overbought_decline) & (result['rsi_sell_signal'] == 0)
            
            result.loc[no_divergence_buy, 'rsi_buy_signal'] = 1
            result.loc[no_divergence_buy, 'rsi_signal_strength'] = 1  # 보통 신뢰도
            
            result.loc[no_divergence_sell, 'rsi_sell_signal'] = 1
            result.loc[no_divergence_sell, 'rsi_signal_strength'] = -1  # 보통 신뢰도
            
            # 신호 확인 (잡음 제거)
            if confirmation_period > 1:
                result = self._apply_rsi_confirmation(result, confirmation_period)
            
            buy_signals = (result['rsi_buy_signal'] == 1).sum()
            sell_signals = (result['rsi_sell_signal'] == 1).sum()
            self.logger.info(f"Generated RSI signals - Buy: {buy_signals}, Sell: {sell_signals}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating RSI signals: {str(e)}")
            return data
    
    def _apply_rsi_confirmation(self, data: pd.DataFrame, 
                               confirmation_period: int) -> pd.DataFrame:
        """RSI 신호 확인 적용"""
        try:
            result = data.copy()
            
            # 확인된 신호만 유지
            buy_confirmed = result['rsi_buy_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            sell_confirmed = result['rsi_sell_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            result['rsi_buy_signal_confirmed'] = buy_confirmed
            result['rsi_sell_signal_confirmed'] = sell_confirmed
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying RSI confirmation: {str(e)}")
            return data
    
    def get_rsi_summary(self, data: pd.DataFrame) -> Dict:
        """RSI 분석 요약"""
        try:
            if data.empty or 'rsi' not in data.columns:
                return {}
            
            latest = data.iloc[-1]
            
            # RSI 통계
            rsi_stats = {
                'current_rsi': float(latest['rsi']) if not pd.isna(latest['rsi']) else None,
                'rsi_status': str(latest['rsi_status']) if 'rsi_status' in data.columns else 'UNKNOWN',
                'rsi_momentum': float(latest['rsi_momentum']) if 'rsi_momentum' in data.columns and not pd.isna(latest['rsi_momentum']) else 0.0,
                'oversold_level': self.oversold_level,
                'overbought_level': self.overbought_level
            }
            
            # 신호 통계
            signal_stats = {
                'total_buy_signals': int((data['rsi_buy_signal'] == 1).sum()) if 'rsi_buy_signal' in data.columns else 0,
                'total_sell_signals': int((data['rsi_sell_signal'] == 1).sum()) if 'rsi_sell_signal' in data.columns else 0,
                'bullish_divergences': int((data['bullish_divergence'] == 1).sum()) if 'bullish_divergence' in data.columns else 0,
                'bearish_divergences': int((data['bearish_divergence'] == 1).sum()) if 'bearish_divergence' in data.columns else 0
            }
            
            summary = {
                'rsi_stats': rsi_stats,
                'signal_stats': signal_stats,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating RSI summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== RSI 분석기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 50:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # RSI 분석기 초기화
        rsi_analyzer = RSIAnalyzer(period=14, oversold_level=30, overbought_level=70)
        
        # 2. RSI 계산
        print(f"\n2. RSI 계산 중...")
        rsi_data = rsi_analyzer.calculate_rsi(stock_data)
        
        # 3. 다이버전스 감지
        print(f"3. 다이버전스 패턴 감지 중...")
        divergence_data = rsi_analyzer.detect_divergences(rsi_data)
        
        # 4. 매매 신호 생성
        print(f"4. RSI 매매 신호 생성 중...")
        signal_data = rsi_analyzer.generate_rsi_signals(divergence_data, use_divergence=True)
        
        # 5. 결과 분석
        print(f"\n=== RSI 분석 결과 ===")
        
        latest = signal_data.iloc[-1]
        print(f"현재 RSI: {latest['rsi']:.1f}")
        print(f"RSI 상태: {latest['rsi_status']}")
        print(f"RSI 모멘텀: {latest['rsi_momentum']:+.2f}")
        
        # 신호 통계
        buy_signals = (signal_data['rsi_buy_signal'] == 1).sum()
        sell_signals = (signal_data['rsi_sell_signal'] == 1).sum()
        bullish_div = (signal_data['bullish_divergence'] == 1).sum()
        bearish_div = (signal_data['bearish_divergence'] == 1).sum()
        
        print(f"\n매수 신호: {buy_signals}회")
        print(f"매도 신호: {sell_signals}회")
        print(f"강세 다이버전스: {bullish_div}회")
        print(f"약세 다이버전스: {bearish_div}회")
        
        # 최근 신호
        recent_buy = signal_data[signal_data['rsi_buy_signal'] == 1].tail(1)
        recent_sell = signal_data[signal_data['rsi_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            buy_strength = recent_buy.iloc[0]['rsi_signal_strength']
            print(f"최근 매수 신호: {buy_date} (강도: {buy_strength})")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']
            sell_strength = recent_sell.iloc[0]['rsi_signal_strength']
            print(f"최근 매도 신호: {sell_date} (강도: {sell_strength})")
        
        # 다이버전스 예시
        if bullish_div > 0:
            latest_bullish = signal_data[signal_data['bullish_divergence'] == 1].tail(1)
            if not latest_bullish.empty:
                div_date = latest_bullish.iloc[0]['date']
                div_strength = latest_bullish.iloc[0]['divergence_strength']
                print(f"최근 강세 다이버전스: {div_date} (강도: {div_strength:.2f})")
        
        # 요약 정보
        summary = rsi_analyzer.get_rsi_summary(signal_data)
        print(f"\n=== 요약 ===")
        print(f"RSI 분석 완료 - 다이버전스 패턴 감지 포함")
        print(f"신호 품질: 다중 조건 확인 + 모멘텀 검증")
        
    else:
        print("   데이터 부족 - 최소 50일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()