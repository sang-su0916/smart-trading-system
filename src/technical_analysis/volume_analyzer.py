"""
거래량 분석기 (Volume Analysis)
OBV, 거래량 가중 평균, 대량 거래 감지를 통한 고정확도 매매 신호 생성
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

class VolumeAnalyzer:
    """거래량 분석기 - OBV + 대량거래 감지 + 거래량 패턴"""
    
    def __init__(self, 
                 vwap_periods: List[int] = [10, 20, 50],
                 volume_ma_period: int = 20):
        """
        Args:
            vwap_periods: VWAP 계산 기간들 (기본: 10, 20, 50일)
            volume_ma_period: 거래량 이동평균 기간 (기본: 20일)
        """
        self.vwap_periods = vwap_periods
        self.volume_ma_period = volume_ma_period
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
    
    def calculate_obv(self, data: pd.DataFrame,
                     price_column: str = 'close',
                     volume_column: str = 'volume') -> pd.DataFrame:
        """
        OBV (On-Balance Volume) 계산
        
        Args:
            data: 주가 및 거래량 데이터
            price_column: 가격 컬럼명
            volume_column: 거래량 컬럼명
            
        Returns:
            OBV가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 가격 변화 방향 계산
            price_change = result[price_column].diff()
            
            # OBV 계산
            obv = np.zeros(len(result))
            obv[0] = result[volume_column].iloc[0] if len(result) > 0 else 0
            
            for i in range(1, len(result)):
                if price_change.iloc[i] > 0:
                    # 상승일 때: 거래량 더하기
                    obv[i] = obv[i-1] + result[volume_column].iloc[i]
                elif price_change.iloc[i] < 0:
                    # 하락일 때: 거래량 빼기
                    obv[i] = obv[i-1] - result[volume_column].iloc[i]
                else:
                    # 보합일 때: 유지
                    obv[i] = obv[i-1]
            
            result['obv'] = obv
            
            # OBV 이동평균 (트렌드 확인용)
            result['obv_ma'] = result['obv'].rolling(window=self.volume_ma_period).mean()
            
            # OBV 변화율
            result['obv_change'] = result['obv'].pct_change()
            
            # OBV 모멘텀 (5일 평균 변화율)
            result['obv_momentum'] = result['obv_change'].rolling(window=5).mean()
            
            self.logger.info(f"OBV calculated with {self.volume_ma_period}-day moving average")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating OBV: {str(e)}")
            return data
    
    def calculate_vwap(self, data: pd.DataFrame,
                      price_column: str = 'close',
                      volume_column: str = 'volume',
                      high_column: str = 'high',
                      low_column: str = 'low') -> pd.DataFrame:
        """
        VWAP (Volume Weighted Average Price) 계산
        
        Args:
            data: 주가 및 거래량 데이터
            price_column: 가격 컬럼명 (기본값으로만 사용)
            volume_column: 거래량 컬럼명
            high_column: 고가 컬럼명
            low_column: 저가 컬럼명
            
        Returns:
            VWAP이 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 일반적인 가격 (HLC3)
            typical_price = (result[high_column] + result[low_column] + result[price_column]) / 3
            
            # 각 기간별 VWAP 계산
            for period in self.vwap_periods:
                vwap_values = []
                
                for i in range(len(result)):
                    start_idx = max(0, i - period + 1)
                    
                    # 해당 기간의 데이터
                    period_typical = typical_price.iloc[start_idx:i+1]
                    period_volume = result[volume_column].iloc[start_idx:i+1]
                    
                    # VWAP 계산 = Σ(전형가격 × 거래량) / Σ거래량
                    if period_volume.sum() > 0:
                        vwap = (period_typical * period_volume).sum() / period_volume.sum()
                    else:
                        vwap = typical_price.iloc[i] if i < len(typical_price) else 0
                    
                    vwap_values.append(vwap)
                
                result[f'vwap_{period}'] = vwap_values
                
                # VWAP 대비 현재가 위치 (%)
                result[f'vwap_{period}_ratio'] = (result[price_column] / result[f'vwap_{period}'] - 1) * 100
            
            self.logger.info(f"VWAP calculated for periods: {self.vwap_periods}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating VWAP: {str(e)}")
            return data
    
    def detect_volume_patterns(self, data: pd.DataFrame,
                              volume_column: str = 'volume') -> pd.DataFrame:
        """
        거래량 패턴 감지 (대량거래, 돌파거래량 등)
        
        Args:
            data: 거래량 데이터
            volume_column: 거래량 컬럼명
            
        Returns:
            거래량 패턴이 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 거래량 이동평균 및 표준편차
            volume_ma = result[volume_column].rolling(window=self.volume_ma_period).mean()
            volume_std = result[volume_column].rolling(window=self.volume_ma_period).std()
            
            # 거래량 상태 분류 초기화
            result['volume_status'] = 'NORMAL'
            result['volume_strength'] = 0
            result['volume_anomaly'] = 0
            
            # 1. 대량 거래 감지 (평균 + 2 표준편차 이상)
            high_volume_threshold = volume_ma + (2 * volume_std)
            high_volume = result[volume_column] > high_volume_threshold
            result.loc[high_volume, 'volume_status'] = 'HIGH_VOLUME'
            
            # 2. 초대량 거래 감지 (평균의 3배 이상)
            extreme_volume = result[volume_column] > (volume_ma * 3)
            result.loc[extreme_volume, 'volume_status'] = 'EXTREME_VOLUME'
            
            # 3. 저거래량 감지 (평균 - 1 표준편차 이하)
            low_volume_threshold = volume_ma - volume_std
            low_volume = result[volume_column] < low_volume_threshold
            result.loc[low_volume, 'volume_status'] = 'LOW_VOLUME'
            
            # 거래량 강도 계산 (표준편차 배수)
            volume_z_score = (result[volume_column] - volume_ma) / volume_std
            result['volume_strength'] = volume_z_score.fillna(0)
            
            # 거래량 이상 신호 (급격한 증가/감소)
            volume_change_pct = result[volume_column].pct_change()
            volume_spike = abs(volume_change_pct) > 2.0  # 200% 이상 변화
            result.loc[volume_spike, 'volume_anomaly'] = np.where(
                volume_change_pct[volume_spike] > 0, 1, -1
            )
            
            # 연속 대량거래 감지 (3일 연속)
            consecutive_high = (
                (result['volume_status'] == 'HIGH_VOLUME') |
                (result['volume_status'] == 'EXTREME_VOLUME')
            ).rolling(window=3).sum() >= 2
            
            result['consecutive_high_volume'] = consecutive_high.astype(int)
            
            pattern_count = (result['volume_status'] != 'NORMAL').sum()
            anomaly_count = (result['volume_anomaly'] != 0).sum()
            
            self.logger.info(f"Detected {pattern_count} volume patterns, {anomaly_count} anomalies")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting volume patterns: {str(e)}")
            return data
    
    def detect_price_volume_divergence(self, data: pd.DataFrame,
                                      price_column: str = 'close') -> pd.DataFrame:
        """
        가격-거래량 다이버전스 감지
        
        Args:
            data: 가격 및 OBV 데이터
            price_column: 가격 컬럼명
            
        Returns:
            다이버전스 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            if 'obv' not in result.columns:
                result = self.calculate_obv(result, price_column)
            
            # 다이버전스 신호 초기화
            result['pv_divergence'] = 0
            result['pv_divergence_strength'] = 0
            
            # 20일 기간으로 고점/저점 비교
            lookback = 20
            
            # 가격과 OBV의 변화율 계산 (lookback 기간)
            price_change = result[price_column].pct_change(periods=lookback)
            obv_change = result['obv'].pct_change(periods=lookback)
            
            # 강세 다이버전스: 가격 하락, OBV 상승
            bullish_divergence = (price_change < -0.05) & (obv_change > 0.02)
            
            # 약세 다이버전스: 가격 상승, OBV 하락  
            bearish_divergence = (price_change > 0.05) & (obv_change < -0.02)
            
            # 다이버전스 강도 계산
            divergence_strength = abs(price_change) + abs(obv_change)
            
            # 신호 설정
            result.loc[bullish_divergence, 'pv_divergence'] = 1
            result.loc[bearish_divergence, 'pv_divergence'] = -1
            
            result.loc[bullish_divergence | bearish_divergence, 'pv_divergence_strength'] = \
                divergence_strength[bullish_divergence | bearish_divergence]
            
            divergence_count = (result['pv_divergence'] != 0).sum()
            self.logger.info(f"Detected {divergence_count} price-volume divergences")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting price-volume divergence: {str(e)}")
            return data
    
    def generate_volume_signals(self, data: pd.DataFrame,
                               price_column: str = 'close',
                               confirmation_period: int = 2) -> pd.DataFrame:
        """
        거래량 기반 매매 신호 생성 (고정확도)
        
        Args:
            data: 거래량 분석된 데이터
            price_column: 가격 컬럼명
            confirmation_period: 신호 확인 기간
            
        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 신호 초기화
            result['volume_buy_signal'] = 0
            result['volume_sell_signal'] = 0
            result['volume_signal_strength'] = 0
            result['volume_confidence'] = 0
            
            # 1. OBV 트렌드 + 가격 확인 신호 (최고 신뢰도)
            if 'obv' in result.columns and 'obv_ma' in result.columns:
                # OBV 상승 트렌드 + 가격도 상승
                obv_uptrend = result['obv'] > result['obv_ma']
                obv_momentum_up = result['obv_momentum'] > 0.01
                price_uptrend = result[price_column] > result[price_column].rolling(10).mean()
                
                strong_buy_obv = obv_uptrend & obv_momentum_up & price_uptrend
                
                # OBV 하락 트렌드 + 가격도 하락
                obv_downtrend = result['obv'] < result['obv_ma']
                obv_momentum_down = result['obv_momentum'] < -0.01
                price_downtrend = result[price_column] < result[price_column].rolling(10).mean()
                
                strong_sell_obv = obv_downtrend & obv_momentum_down & price_downtrend
                
                # 최고 신뢰도 신호
                result.loc[strong_buy_obv, 'volume_buy_signal'] = 1
                result.loc[strong_buy_obv, 'volume_signal_strength'] = 3
                result.loc[strong_buy_obv, 'volume_confidence'] = 0.85
                
                result.loc[strong_sell_obv, 'volume_sell_signal'] = 1
                result.loc[strong_sell_obv, 'volume_signal_strength'] = -3
                result.loc[strong_sell_obv, 'volume_confidence'] = 0.85
            
            # 2. 다이버전스 신호 (높은 신뢰도)
            if 'pv_divergence' in result.columns:
                strong_div_buy = (result['pv_divergence'] == 1) & (result['pv_divergence_strength'] > 0.1)
                strong_div_sell = (result['pv_divergence'] == -1) & (result['pv_divergence_strength'] > 0.1)
                
                # 다이버전스 신호가 없는 경우만 적용
                div_buy_condition = strong_div_buy & (result['volume_buy_signal'] == 0)
                div_sell_condition = strong_div_sell & (result['volume_sell_signal'] == 0)
                
                result.loc[div_buy_condition, 'volume_buy_signal'] = 1
                result.loc[div_buy_condition, 'volume_signal_strength'] = 2
                result.loc[div_buy_condition, 'volume_confidence'] = 0.75
                
                result.loc[div_sell_condition, 'volume_sell_signal'] = 1
                result.loc[div_sell_condition, 'volume_signal_strength'] = -2
                result.loc[div_sell_condition, 'volume_confidence'] = 0.75
            
            # 3. 대량거래 + VWAP 돌파 신호 (높은 신뢰도)
            if 'vwap_20' in result.columns:
                # 대량거래와 함께 VWAP 상향 돌파
                vwap_breakout_buy = (
                    (result[price_column] > result['vwap_20']) &
                    (result[price_column].shift(1) <= result['vwap_20'].shift(1)) &
                    (result['volume_status'].isin(['HIGH_VOLUME', 'EXTREME_VOLUME']))
                )
                
                # 대량거래와 함께 VWAP 하향 돌파
                vwap_breakout_sell = (
                    (result[price_column] < result['vwap_20']) &
                    (result[price_column].shift(1) >= result['vwap_20'].shift(1)) &
                    (result['volume_status'].isin(['HIGH_VOLUME', 'EXTREME_VOLUME']))
                )
                
                # 기존 신호가 없는 경우만 적용
                vwap_buy_condition = vwap_breakout_buy & (result['volume_buy_signal'] == 0)
                vwap_sell_condition = vwap_breakout_sell & (result['volume_sell_signal'] == 0)
                
                result.loc[vwap_buy_condition, 'volume_buy_signal'] = 1
                result.loc[vwap_buy_condition, 'volume_signal_strength'] = 2
                result.loc[vwap_buy_condition, 'volume_confidence'] = 0.7
                
                result.loc[vwap_sell_condition, 'volume_sell_signal'] = 1
                result.loc[vwap_sell_condition, 'volume_signal_strength'] = -2
                result.loc[vwap_sell_condition, 'volume_confidence'] = 0.7
            
            # 4. 연속 대량거래 신호 (중간 신뢰도)
            if 'consecutive_high_volume' in result.columns:
                consecutive_buy = (
                    (result['consecutive_high_volume'] == 1) &
                    (result['obv_momentum'] > 0) &
                    (result['volume_buy_signal'] == 0)
                )
                
                result.loc[consecutive_buy, 'volume_buy_signal'] = 1
                result.loc[consecutive_buy, 'volume_signal_strength'] = 1
                result.loc[consecutive_buy, 'volume_confidence'] = 0.6
            
            # 신호 확인 (잡음 제거)
            if confirmation_period > 1:
                result = self._apply_volume_confirmation(result, confirmation_period)
            
            buy_signals = (result['volume_buy_signal'] == 1).sum()
            sell_signals = (result['volume_sell_signal'] == 1).sum()
            avg_confidence = result[result['volume_confidence'] > 0]['volume_confidence'].mean()
            
            self.logger.info(f"Generated Volume signals - Buy: {buy_signals}, Sell: {sell_signals}, Avg Confidence: {avg_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating volume signals: {str(e)}")
            return data
    
    def _apply_volume_confirmation(self, data: pd.DataFrame, 
                                  confirmation_period: int) -> pd.DataFrame:
        """거래량 신호 확인 적용"""
        try:
            result = data.copy()
            
            # 확인된 신호만 유지
            buy_confirmed = result['volume_buy_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            sell_confirmed = result['volume_sell_signal'].rolling(
                window=confirmation_period, min_periods=1
            ).max()
            
            result['volume_buy_signal_confirmed'] = buy_confirmed
            result['volume_sell_signal_confirmed'] = sell_confirmed
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying volume confirmation: {str(e)}")
            return data
    
    def get_volume_summary(self, data: pd.DataFrame) -> Dict:
        """거래량 분석 요약"""
        try:
            if data.empty or 'volume' not in data.columns:
                return {}
            
            latest = data.iloc[-1]
            
            # 거래량 통계
            volume_stats = {
                'current_volume': int(latest['volume']) if not pd.isna(latest['volume']) else 0,
                'volume_status': str(latest['volume_status']) if 'volume_status' in data.columns else 'UNKNOWN',
                'volume_strength': float(latest['volume_strength']) if 'volume_strength' in data.columns and not pd.isna(latest['volume_strength']) else 0.0,
                'obv': float(latest['obv']) if 'obv' in data.columns and not pd.isna(latest['obv']) else 0.0,
                'obv_momentum': float(latest['obv_momentum']) if 'obv_momentum' in data.columns and not pd.isna(latest['obv_momentum']) else 0.0
            }
            
            # VWAP 정보
            vwap_info = {}
            for period in self.vwap_periods:
                vwap_col = f'vwap_{period}'
                ratio_col = f'vwap_{period}_ratio'
                if vwap_col in data.columns:
                    vwap_info[f'VWAP_{period}'] = {
                        'value': float(latest[vwap_col]) if not pd.isna(latest[vwap_col]) else 0.0,
                        'ratio': float(latest[ratio_col]) if ratio_col in data.columns and not pd.isna(latest[ratio_col]) else 0.0
                    }
            
            # 신호 통계
            signal_stats = {
                'total_buy_signals': int((data['volume_buy_signal'] == 1).sum()) if 'volume_buy_signal' in data.columns else 0,
                'total_sell_signals': int((data['volume_sell_signal'] == 1).sum()) if 'volume_sell_signal' in data.columns else 0,
                'pv_divergences': int((data['pv_divergence'] != 0).sum()) if 'pv_divergence' in data.columns else 0,
                'volume_anomalies': int((data['volume_anomaly'] != 0).sum()) if 'volume_anomaly' in data.columns else 0,
                'avg_confidence': float(data[data['volume_confidence'] > 0]['volume_confidence'].mean()) if 'volume_confidence' in data.columns else 0.0
            }
            
            summary = {
                'volume_stats': volume_stats,
                'vwap_info': vwap_info,
                'signal_stats': signal_stats,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating volume summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 거래량 분석기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 50:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 거래량 분석기 초기화
        volume_analyzer = VolumeAnalyzer(vwap_periods=[10, 20, 50], volume_ma_period=20)
        
        # 2. OBV 계산
        print(f"\n2. OBV 계산 중...")
        obv_data = volume_analyzer.calculate_obv(stock_data)
        
        # 3. VWAP 계산
        print(f"3. VWAP 계산 중...")
        vwap_data = volume_analyzer.calculate_vwap(obv_data)
        
        # 4. 거래량 패턴 감지
        print(f"4. 거래량 패턴 감지 중...")
        pattern_data = volume_analyzer.detect_volume_patterns(vwap_data)
        
        # 5. 가격-거래량 다이버전스 감지
        print(f"5. 가격-거래량 다이버전스 감지 중...")
        divergence_data = volume_analyzer.detect_price_volume_divergence(pattern_data)
        
        # 6. 매매 신호 생성
        print(f"6. 거래량 매매 신호 생성 중...")
        signal_data = volume_analyzer.generate_volume_signals(divergence_data)
        
        # 7. 결과 분석
        print(f"\n=== 거래량 분석 결과 ===")
        
        latest = signal_data.iloc[-1]
        print(f"현재 거래량: {latest['volume']:,}주")
        print(f"거래량 상태: {latest['volume_status']}")
        print(f"거래량 강도: {latest['volume_strength']:+.2f}")
        print(f"현재 OBV: {latest['obv']:,.0f}")
        print(f"OBV 모멘텀: {latest['obv_momentum']:+.4f}")
        
        # VWAP 현황
        for period in [10, 20, 50]:
            if f'vwap_{period}' in signal_data.columns:
                vwap_val = latest[f'vwap_{period}']
                vwap_ratio = latest[f'vwap_{period}_ratio']
                print(f"VWAP{period}: {vwap_val:,.0f}원 ({vwap_ratio:+.1f}%)")
        
        # 신호 통계
        buy_signals = (signal_data['volume_buy_signal'] == 1).sum()
        sell_signals = (signal_data['volume_sell_signal'] == 1).sum()
        pv_divergences = (signal_data['pv_divergence'] != 0).sum()
        volume_anomalies = (signal_data['volume_anomaly'] != 0).sum()
        avg_confidence = signal_data[signal_data['volume_confidence'] > 0]['volume_confidence'].mean()
        
        print(f"\n매수 신호: {buy_signals}회")
        print(f"매도 신호: {sell_signals}회")
        print(f"가격-거래량 다이버전스: {pv_divergences}회")
        print(f"거래량 이상 신호: {volume_anomalies}회")
        print(f"평균 신뢰도: {avg_confidence:.2f}")
        
        # 최근 신호
        recent_buy = signal_data[signal_data['volume_buy_signal'] == 1].tail(1)
        recent_sell = signal_data[signal_data['volume_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            buy_strength = recent_buy.iloc[0]['volume_signal_strength']
            buy_confidence = recent_buy.iloc[0]['volume_confidence']
            print(f"최근 매수 신호: {buy_date} (강도: {buy_strength}, 신뢰도: {buy_confidence:.2f})")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']
            sell_strength = recent_sell.iloc[0]['volume_signal_strength']
            sell_confidence = recent_sell.iloc[0]['volume_confidence']
            print(f"최근 매도 신호: {sell_date} (강도: {sell_strength}, 신뢰도: {sell_confidence:.2f})")
        
        # 거래량 패턴 통계
        volume_counts = signal_data['volume_status'].value_counts()
        print(f"\n거래량 패턴 분포:")
        for pattern, count in volume_counts.items():
            print(f"  {pattern}: {count}회")
        
        # 요약 정보
        summary = volume_analyzer.get_volume_summary(signal_data)
        print(f"\n=== 요약 ===")
        print(f"거래량 분석 완료 - OBV + VWAP + 패턴 감지")
        print(f"신호 품질: 3단계 신뢰도 (0.6~0.85)")
        
    else:
        print("   데이터 부족 - 최소 50일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()