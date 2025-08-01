"""
볼린저 밴드 (Bollinger Bands) 분석기
변동성 기반 매매 신호 생성 및 %B, 밴드폭 지표
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

class BollingerBandsAnalyzer:
    """볼린저 밴드 분석기 - 변동성 + 밴드 터치 + %B 지표"""
    
    def __init__(self, 
                 window: int = 20,
                 num_std: float = 2.0):
        """
        Args:
            window: 이동평균 기간 (기본: 20일)
            num_std: 표준편차 배수 (기본: 2.0)
        """
        self.window = window
        self.num_std = num_std
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
    
    def calculate_bollinger_bands(self, data: pd.DataFrame, 
                                 price_column: str = 'close') -> pd.DataFrame:
        """
        볼린저 밴드 계산
        
        Args:
            data: 주가 데이터
            price_column: 계산할 가격 컬럼명
            
        Returns:
            볼린저 밴드가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 중심선 (단순 이동평균)
            result['bb_middle'] = result[price_column].rolling(window=self.window).mean()
            
            # 표준편차 계산
            rolling_std = result[price_column].rolling(window=self.window).std()
            
            # 상단 밴드 = 중심선 + (표준편차 × 배수)
            result['bb_upper'] = result['bb_middle'] + (rolling_std * self.num_std)
            
            # 하단 밴드 = 중심선 - (표준편차 × 배수)
            result['bb_lower'] = result['bb_middle'] - (rolling_std * self.num_std)
            
            # %B 지표 계산 (현재가의 밴드 내 위치)
            result['percent_b'] = (result[price_column] - result['bb_lower']) / (result['bb_upper'] - result['bb_lower'])
            
            # 밴드폭 (Band Width) - 변동성 측정
            result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
            
            # 밴드폭 변화율
            result['bb_width_change'] = result['bb_width'].pct_change()
            
            # 가격의 밴드 대비 위치 분류
            result['bb_position'] = 'MIDDLE'
            result.loc[result[price_column] >= result['bb_upper'], 'bb_position'] = 'ABOVE_UPPER'
            result.loc[result[price_column] <= result['bb_lower'], 'bb_position'] = 'BELOW_LOWER'
            result.loc[(result[price_column] > result['bb_middle']) & 
                      (result[price_column] < result['bb_upper']), 'bb_position'] = 'UPPER_HALF'
            result.loc[(result[price_column] < result['bb_middle']) & 
                      (result[price_column] > result['bb_lower']), 'bb_position'] = 'LOWER_HALF'
            
            self.logger.info(f"Bollinger Bands calculated with window={self.window}, std={self.num_std}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            return data
    
    def detect_squeeze_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        볼린저 밴드 스퀴즈 패턴 감지 (변동성 축소/확대)
        
        Args:
            data: 볼린저 밴드 데이터
            
        Returns:
            스퀴즈 패턴이 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'bb_width' not in result.columns:
                result = self.calculate_bollinger_bands(result)
            
            # 스퀴즈 신호 초기화
            result['bb_squeeze'] = 0
            result['bb_squeeze_type'] = 'NORMAL'
            
            # 20일 이동평균 밴드폭 계산
            bb_width_ma = result['bb_width'].rolling(window=20).mean()
            bb_width_std = result['bb_width'].rolling(window=20).std()
            
            # 스퀴즈 감지 (밴드폭이 평균 - 1 표준편차 이하)
            squeeze_threshold = bb_width_ma - bb_width_std
            squeeze_condition = result['bb_width'] < squeeze_threshold
            
            # 확장 감지 (밴드폭이 평균 + 1 표준편차 이상)
            expansion_threshold = bb_width_ma + bb_width_std
            expansion_condition = result['bb_width'] > expansion_threshold
            
            # 스퀴즈 신호 설정
            result.loc[squeeze_condition, 'bb_squeeze'] = -1  # 압축
            result.loc[expansion_condition, 'bb_squeeze'] = 1   # 확장
            
            result.loc[squeeze_condition, 'bb_squeeze_type'] = 'SQUEEZE'
            result.loc[expansion_condition, 'bb_squeeze_type'] = 'EXPANSION'
            
            # 스퀴즈 강도 계산
            result['squeeze_strength'] = 0.0
            
            # 압축 강도 (낮을수록 강한 압축)
            squeeze_mask = squeeze_condition & (squeeze_threshold > 0)
            if squeeze_mask.any():
                result.loc[squeeze_mask, 'squeeze_strength'] = -(squeeze_threshold[squeeze_mask] - result.loc[squeeze_mask, 'bb_width']) / squeeze_threshold[squeeze_mask]
            
            # 확장 강도 (높을수록 강한 확장)
            expansion_mask = expansion_condition & (expansion_threshold > 0)
            if expansion_mask.any():
                result.loc[expansion_mask, 'squeeze_strength'] = (result.loc[expansion_mask, 'bb_width'] - expansion_threshold[expansion_mask]) / expansion_threshold[expansion_mask]
            
            squeeze_count = (result['bb_squeeze'] != 0).sum()
            self.logger.info(f"Detected {squeeze_count} Bollinger Band squeeze/expansion patterns")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting squeeze patterns: {str(e)}")
            return data
    
    def detect_band_touches(self, data: pd.DataFrame,
                           price_column: str = 'close') -> pd.DataFrame:
        """
        밴드 터치 및 돌파 신호 감지
        
        Args:
            data: 볼린저 밴드 데이터
            price_column: 가격 컬럼명
            
        Returns:
            밴드 터치 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'bb_upper' not in result.columns:
                result = self.calculate_bollinger_bands(result, price_column)
            
            # 밴드 터치 신호 초기화
            result['bb_touch_signal'] = 0
            result['bb_breakout_signal'] = 0
            
            # 상단 밴드 터치 (과매수 신호)
            upper_touch = (
                (result[price_column] >= result['bb_upper']) &
                (result[price_column].shift(1) < result['bb_upper'].shift(1))
            )
            
            # 하단 밴드 터치 (과매도 신호)
            lower_touch = (
                (result[price_column] <= result['bb_lower']) &
                (result[price_column].shift(1) > result['bb_lower'].shift(1))
            )
            
            # 상단 밴드 돌파 (강세 신호)
            upper_breakout = (
                (result[price_column] > result['bb_upper']) &
                (result['bb_width'] > result['bb_width'].rolling(10).mean()) &  # 확장 상태에서만
                (result['percent_b'] > 1.1)  # %B > 110%
            )
            
            # 하단 밴드 돌파 (약세 신호)
            lower_breakout = (
                (result[price_column] < result['bb_lower']) &
                (result['bb_width'] > result['bb_width'].rolling(10).mean()) &  # 확장 상태에서만
                (result['percent_b'] < -0.1)  # %B < -10%
            )
            
            # 중심선 회귀 (평균 회귀 신호)
            middle_return_from_upper = (
                (result[price_column] <= result['bb_middle']) &
                (result[price_column].shift(1) > result['bb_middle'].shift(1)) &
                (result['bb_position'].shift(1) == 'UPPER_HALF')
            )
            
            middle_return_from_lower = (
                (result[price_column] >= result['bb_middle']) &
                (result[price_column].shift(1) < result['bb_middle'].shift(1)) &
                (result['bb_position'].shift(1) == 'LOWER_HALF')
            )
            
            # 신호 설정
            result.loc[upper_touch, 'bb_touch_signal'] = -1   # 매도 신호
            result.loc[lower_touch, 'bb_touch_signal'] = 1    # 매수 신호
            
            result.loc[upper_breakout, 'bb_breakout_signal'] = 1    # 강세 돌파
            result.loc[lower_breakout, 'bb_breakout_signal'] = -1   # 약세 돌파
            
            result.loc[middle_return_from_upper, 'bb_touch_signal'] = 1    # 중심선 복귀 매수
            result.loc[middle_return_from_lower, 'bb_touch_signal'] = -1   # 중심선 복귀 매도
            
            touch_count = (result['bb_touch_signal'] != 0).sum()
            breakout_count = (result['bb_breakout_signal'] != 0).sum()
            self.logger.info(f"Detected {touch_count} band touches, {breakout_count} breakouts")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting band touches: {str(e)}")
            return data
    
    def generate_bb_signals(self, data: pd.DataFrame,
                           use_squeeze: bool = True,
                           confirmation_period: int = 2) -> pd.DataFrame:
        """
        볼린저 밴드 기반 매매 신호 생성 (고정확도)
        
        Args:
            data: 볼린저 밴드 분석된 데이터
            use_squeeze: 스퀴즈 패턴 사용 여부
            confirmation_period: 신호 확인 기간
            
        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 신호 초기화
            result['bb_buy_signal'] = 0
            result['bb_sell_signal'] = 0
            result['bb_signal_strength'] = 0
            result['bb_confidence'] = 0
            
            # 1. 기본 평균 회귀 신호 (높은 신뢰도)
            # 하단 밴드 터치 후 반등
            mean_revert_buy = (
                (result['bb_touch_signal'] == 1) &
                (result['percent_b'] < 0.2) &  # %B < 20% (강한 과매도)
                (result['bb_position'] == 'BELOW_LOWER')
            )
            
            # 상단 밴드 터치 후 반락
            mean_revert_sell = (
                (result['bb_touch_signal'] == -1) &
                (result['percent_b'] > 0.8) &  # %B > 80% (강한 과매수)
                (result['bb_position'] == 'ABOVE_UPPER')
            )
            
            # 2. 스퀴즈 브레이크아웃 신호 (최고 신뢰도)
            if use_squeeze and 'bb_squeeze' in result.columns:
                # 스퀴즈 후 상승 돌파
                squeeze_breakout_buy = (
                    (result['bb_squeeze'].shift(1) == -1) &  # 이전에 스퀴즈
                    (result['bb_breakout_signal'] == 1) &    # 상향 돌파
                    (result['bb_width_change'] > 0.1)        # 밴드폭 확장
                )
                
                # 스퀴즈 후 하락 돌파
                squeeze_breakout_sell = (
                    (result['bb_squeeze'].shift(1) == -1) &  # 이전에 스퀴즈
                    (result['bb_breakout_signal'] == -1) &   # 하향 돌파
                    (result['bb_width_change'] > 0.1)        # 밴드폭 확장
                )
                
                # 스퀴즈 브레이크아웃 신호 (최고 신뢰도)
                result.loc[squeeze_breakout_buy, 'bb_buy_signal'] = 1
                result.loc[squeeze_breakout_buy, 'bb_signal_strength'] = 3
                result.loc[squeeze_breakout_buy, 'bb_confidence'] = 0.9
                
                result.loc[squeeze_breakout_sell, 'bb_sell_signal'] = 1
                result.loc[squeeze_breakout_sell, 'bb_signal_strength'] = -3
                result.loc[squeeze_breakout_sell, 'bb_confidence'] = 0.9
            
            # 3. 평균 회귀 신호 (높은 신뢰도) - 스퀴즈 신호가 없는 경우
            high_confidence_buy = mean_revert_buy & (result['bb_buy_signal'] == 0)
            high_confidence_sell = mean_revert_sell & (result['bb_sell_signal'] == 0)
            
            result.loc[high_confidence_buy, 'bb_buy_signal'] = 1
            result.loc[high_confidence_buy, 'bb_signal_strength'] = 2
            result.loc[high_confidence_buy, 'bb_confidence'] = 0.75
            
            result.loc[high_confidence_sell, 'bb_sell_signal'] = 1
            result.loc[high_confidence_sell, 'bb_signal_strength'] = -2
            result.loc[high_confidence_sell, 'bb_confidence'] = 0.75
            
            # 4. 일반 밴드 터치 신호 (중간 신뢰도)
            medium_confidence_buy = (
                (result['bb_touch_signal'] == 1) &
                (result['bb_buy_signal'] == 0) &
                (result['percent_b'] < 0.3)
            )
            
            medium_confidence_sell = (
                (result['bb_touch_signal'] == -1) &
                (result['bb_sell_signal'] == 0) &
                (result['percent_b'] > 0.7)
            )
            
            result.loc[medium_confidence_buy, 'bb_buy_signal'] = 1
            result.loc[medium_confidence_buy, 'bb_signal_strength'] = 1
            result.loc[medium_confidence_buy, 'bb_confidence'] = 0.6
            
            result.loc[medium_confidence_sell, 'bb_sell_signal'] = 1
            result.loc[medium_confidence_sell, 'bb_signal_strength'] = -1
            result.loc[medium_confidence_sell, 'bb_confidence'] = 0.6
            
            # 신호 확인 (잡음 제거)
            if confirmation_period > 1:
                result = self._apply_bb_confirmation(result, confirmation_period)
            
            buy_signals = (result['bb_buy_signal'] == 1).sum()
            sell_signals = (result['bb_sell_signal'] == 1).sum()
            avg_confidence = result[result['bb_confidence'] > 0]['bb_confidence'].mean()
            
            self.logger.info(f"Generated Bollinger Band signals - Buy: {buy_signals}, Sell: {sell_signals}, Avg Confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating Bollinger Band signals: {str(e)}")
            return data
    
    def _apply_bb_confirmation(self, data: pd.DataFrame, 
                              confirmation_period: int) -> pd.DataFrame:
        """볼린저 밴드 신호 확인 적용"""
        try:
            result = data.copy()
            
            # 확인된 신호만 유지
            buy_confirmed = result['bb_buy_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            sell_confirmed = result['bb_sell_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            result['bb_buy_signal_confirmed'] = buy_confirmed
            result['bb_sell_signal_confirmed'] = sell_confirmed
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying Bollinger Band confirmation: {str(e)}")
            return data
    
    def get_bb_summary(self, data: pd.DataFrame) -> Dict:
        """볼린저 밴드 분석 요약"""
        try:
            if data.empty or 'bb_upper' not in data.columns:
                return {}
            
            latest = data.iloc[-1]
            
            # 볼린저 밴드 통계
            bb_stats = {
                'bb_upper': float(latest['bb_upper']) if not pd.isna(latest['bb_upper']) else 0.0,
                'bb_middle': float(latest['bb_middle']) if not pd.isna(latest['bb_middle']) else 0.0,
                'bb_lower': float(latest['bb_lower']) if not pd.isna(latest['bb_lower']) else 0.0,
                'percent_b': float(latest['percent_b']) if not pd.isna(latest['percent_b']) else 0.0,
                'bb_width': float(latest['bb_width']) if not pd.isna(latest['bb_width']) else 0.0,
                'bb_position': str(latest['bb_position']) if 'bb_position' in data.columns else 'UNKNOWN',
                'squeeze_type': str(latest['bb_squeeze_type']) if 'bb_squeeze_type' in data.columns else 'UNKNOWN'
            }
            
            # 신호 통계
            signal_stats = {
                'total_buy_signals': int((data['bb_buy_signal'] == 1).sum()) if 'bb_buy_signal' in data.columns else 0,
                'total_sell_signals': int((data['bb_sell_signal'] == 1).sum()) if 'bb_sell_signal' in data.columns else 0,
                'touch_signals': int((data['bb_touch_signal'] != 0).sum()) if 'bb_touch_signal' in data.columns else 0,
                'breakout_signals': int((data['bb_breakout_signal'] != 0).sum()) if 'bb_breakout_signal' in data.columns else 0,
                'squeeze_patterns': int((data['bb_squeeze'] != 0).sum()) if 'bb_squeeze' in data.columns else 0,
                'avg_confidence': float(data[data['bb_confidence'] > 0]['bb_confidence'].mean()) if 'bb_confidence' in data.columns else 0.0
            }
            
            summary = {
                'bb_stats': bb_stats,
                'signal_stats': signal_stats,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating Bollinger Band summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 볼린저 밴드 분석기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 50:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 볼린저 밴드 분석기 초기화
        bb_analyzer = BollingerBandsAnalyzer(window=20, num_std=2.0)
        
        # 2. 볼린저 밴드 계산
        print(f"\n2. 볼린저 밴드 계산 중...")
        bb_data = bb_analyzer.calculate_bollinger_bands(stock_data)
        
        # 3. 스퀴즈 패턴 감지
        print(f"3. 스퀴즈 패턴 감지 중...")
        squeeze_data = bb_analyzer.detect_squeeze_patterns(bb_data)
        
        # 4. 밴드 터치 감지
        print(f"4. 밴드 터치 신호 감지 중...")
        touch_data = bb_analyzer.detect_band_touches(squeeze_data)
        
        # 5. 매매 신호 생성
        print(f"5. 볼린저 밴드 매매 신호 생성 중...")
        signal_data = bb_analyzer.generate_bb_signals(touch_data, use_squeeze=True)
        
        # 6. 결과 분석
        print(f"\n=== 볼린저 밴드 분석 결과 ===")
        
        latest = signal_data.iloc[-1]
        print(f"현재가: {latest['close']:,.0f}원")
        print(f"상단밴드: {latest['bb_upper']:,.0f}원")
        print(f"중심선: {latest['bb_middle']:,.0f}원")
        print(f"하단밴드: {latest['bb_lower']:,.0f}원")
        print(f"%B 지표: {latest['percent_b']:.2f} ({latest['percent_b']*100:.1f}%)")
        print(f"밴드폭: {latest['bb_width']:.4f}")
        print(f"밴드 위치: {latest['bb_position']}")
        print(f"스퀴즈 상태: {latest['bb_squeeze_type']}")
        
        # 신호 통계
        buy_signals = (signal_data['bb_buy_signal'] == 1).sum()
        sell_signals = (signal_data['bb_sell_signal'] == 1).sum()
        touch_signals = (signal_data['bb_touch_signal'] != 0).sum()
        breakout_signals = (signal_data['bb_breakout_signal'] != 0).sum()
        squeeze_patterns = (signal_data['bb_squeeze'] != 0).sum()
        avg_confidence = signal_data[signal_data['bb_confidence'] > 0]['bb_confidence'].mean()
        
        print(f"\n매수 신호: {buy_signals}회")
        print(f"매도 신호: {sell_signals}회")
        print(f"밴드 터치: {touch_signals}회")
        print(f"밴드 돌파: {breakout_signals}회")
        print(f"스퀴즈 패턴: {squeeze_patterns}회")
        print(f"평균 신뢰도: {avg_confidence:.2f}")
        
        # 최근 신호
        recent_buy = signal_data[signal_data['bb_buy_signal'] == 1].tail(1)
        recent_sell = signal_data[signal_data['bb_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            buy_strength = recent_buy.iloc[0]['bb_signal_strength']
            buy_confidence = recent_buy.iloc[0]['bb_confidence']
            print(f"최근 매수 신호: {buy_date} (강도: {buy_strength}, 신뢰도: {buy_confidence:.2f})")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']
            sell_strength = recent_sell.iloc[0]['bb_signal_strength']
            sell_confidence = recent_sell.iloc[0]['bb_confidence']
            print(f"최근 매도 신호: {sell_date} (강도: {sell_strength}, 신뢰도: {sell_confidence:.2f})")
        
        # 스퀴즈 패턴 통계
        squeeze_counts = signal_data['bb_squeeze_type'].value_counts()
        print(f"\n스퀴즈 패턴 분포:")
        for pattern, count in squeeze_counts.items():
            print(f"  {pattern}: {count}회")
        
        # 요약 정보
        summary = bb_analyzer.get_bb_summary(signal_data)
        print(f"\n=== 요약 ===")
        print(f"볼린저 밴드 분석 완료 - 스퀴즈 패턴 + 밴드 터치 감지")
        print(f"신호 품질: 3단계 신뢰도 (0.6~0.9)")
        
    else:
        print("   데이터 부족 - 최소 50일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()