"""
시장 상황 분석기 (Market Condition Analyzer)
상승장/하락장/횡보장 감지 및 시장 상황별 신호 강도 조정
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
from enum import Enum

class MarketCondition(Enum):
    """시장 상황 분류"""
    BULL_MARKET = "BULL_MARKET"      # 상승장
    BEAR_MARKET = "BEAR_MARKET"      # 하락장
    SIDEWAYS = "SIDEWAYS"            # 횡보장
    VOLATILE = "VOLATILE"            # 변동성 장세
    RECOVERY = "RECOVERY"            # 회복장
    CRASH = "CRASH"                  # 급락장

class MarketConditionAnalyzer:
    """시장 상황 분석기 - 트렌드 및 변동성 기반 시장 상황 분류"""
    
    def __init__(self, 
                 trend_periods: List[int] = [20, 60, 120],
                 volatility_period: int = 20,
                 volume_period: int = 20):
        """
        Args:
            trend_periods: 트렌드 분석 기간들 (기본: 20, 60, 120일)
            volatility_period: 변동성 계산 기간 (기본: 20일)
            volume_period: 거래량 분석 기간 (기본: 20일)
        """
        self.trend_periods = trend_periods
        self.volatility_period = volatility_period
        self.volume_period = volume_period
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
    
    def analyze_market_condition(self, data: pd.DataFrame,
                                price_column: str = 'close',
                                volume_column: str = 'volume') -> pd.DataFrame:
        """
        시장 상황 종합 분석
        
        Args:
            data: 주가 및 거래량 데이터
            price_column: 가격 컬럼명
            volume_column: 거래량 컬럼명
            
        Returns:
            시장 상황이 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            self.logger.info("Starting comprehensive market condition analysis...")
            
            # 1. 트렌드 분석
            result = self._analyze_trend(result, price_column)
            
            # 2. 변동성 분석
            result = self._analyze_volatility(result, price_column)
            
            # 3. 거래량 분석
            result = self._analyze_volume_pattern(result, volume_column)
            
            # 4. 모멘텀 분석
            result = self._analyze_momentum(result, price_column)
            
            # 5. 시장 상황 분류
            result = self._classify_market_condition(result)
            
            # 6. 신뢰도 점수 계산
            result = self._calculate_condition_confidence(result)
            
            self.logger.info("Market condition analysis completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in market condition analysis: {str(e)}")
            return data
    
    def _analyze_trend(self, data: pd.DataFrame, price_column: str) -> pd.DataFrame:
        """트렌드 분석"""
        try:
            result = data.copy()
            
            # 각 기간별 이동평균과 기울기 계산
            for period in self.trend_periods:
                ma_col = f'ma_{period}'
                slope_col = f'trend_slope_{period}'
                strength_col = f'trend_strength_{period}'
                
                # 이동평균
                result[ma_col] = result[price_column].rolling(window=period).mean()
                
                # 트렌드 기울기 (선형 회귀 기울기)
                slopes = []
                for i in range(len(result)):
                    if i < period - 1:
                        slopes.append(0)
                    else:
                        y = result[price_column].iloc[i-period+1:i+1].values
                        x = np.arange(len(y))
                        if len(y) > 1:
                            slope = np.polyfit(x, y, 1)[0]
                            slopes.append(slope)
                        else:
                            slopes.append(0)
                
                result[slope_col] = slopes
                
                # 트렌드 강도 (기울기의 절댓값 정규화)
                result[strength_col] = abs(result[slope_col]) / result[ma_col] * 100
            
            # 종합 트렌드 점수 계산
            result['overall_trend'] = 0.0
            for period in self.trend_periods:
                weight = 1.0 / period  # 단기일수록 높은 가중치
                result['overall_trend'] += result[f'trend_slope_{period}'] * weight
            
            # 트렌드 정규화 (-1 ~ +1)
            result['overall_trend'] = np.tanh(result['overall_trend'] / result[price_column] * 1000)
            
            # 트렌드 방향 분류
            result['trend_direction'] = 'SIDEWAYS'
            result.loc[result['overall_trend'] > 0.3, 'trend_direction'] = 'UP'
            result.loc[result['overall_trend'] < -0.3, 'trend_direction'] = 'DOWN'
            result.loc[abs(result['overall_trend']) <= 0.1, 'trend_direction'] = 'FLAT'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in trend analysis: {str(e)}")
            return data
    
    def _analyze_volatility(self, data: pd.DataFrame, price_column: str) -> pd.DataFrame:
        """변동성 분석"""
        try:
            result = data.copy()
            
            # 일간 수익률
            result['daily_return'] = result[price_column].pct_change()
            
            # 변동성 (일간 수익률의 표준편차)
            result['volatility'] = result['daily_return'].rolling(
                window=self.volatility_period
            ).std() * np.sqrt(252)  # 연간화
            
            # 변동성 상태 분류
            volatility_mean = result['volatility'].rolling(window=60).mean()
            volatility_std = result['volatility'].rolling(window=60).std()
            
            result['volatility_status'] = 'NORMAL'
            high_vol_threshold = volatility_mean + volatility_std
            low_vol_threshold = volatility_mean - volatility_std
            
            result.loc[result['volatility'] > high_vol_threshold, 'volatility_status'] = 'HIGH'
            result.loc[result['volatility'] < low_vol_threshold, 'volatility_status'] = 'LOW'
            
            # VIX 스타일 변동성 지수 계산
            result['vix_like'] = result['volatility'] * 100
            
            # 변동성 변화율
            result['volatility_change'] = result['volatility'].pct_change()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in volatility analysis: {str(e)}")
            return data
    
    def _analyze_volume_pattern(self, data: pd.DataFrame, volume_column: str) -> pd.DataFrame:
        """거래량 패턴 분석"""
        try:
            result = data.copy()
            
            if volume_column not in result.columns:
                # 거래량 데이터가 없는 경우 기본값 설정
                result['volume_trend'] = 0
                result['volume_pressure'] = 'NEUTRAL'
                return result
            
            # 거래량 이동평균
            result['volume_ma'] = result[volume_column].rolling(window=self.volume_period).mean()
            
            # 거래량 트렌드
            result['volume_trend'] = (result[volume_column] / result['volume_ma'] - 1) * 100
            
            # 가격-거래량 압력 분석
            price_change = result['daily_return'].fillna(0)
            volume_ratio = result['volume_trend'].fillna(0)
            
            result['volume_pressure'] = 'NEUTRAL'
            
            # 상승 압력 (가격 상승 + 거래량 증가)
            buying_pressure = (price_change > 0.01) & (volume_ratio > 20)
            result.loc[buying_pressure, 'volume_pressure'] = 'BUYING'
            
            # 하락 압력 (가격 하락 + 거래량 증가)
            selling_pressure = (price_change < -0.01) & (volume_ratio > 20)
            result.loc[selling_pressure, 'volume_pressure'] = 'SELLING'
            
            # 무관심 (거래량 감소)
            low_interest = volume_ratio < -20
            result.loc[low_interest, 'volume_pressure'] = 'LOW_INTEREST'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in volume pattern analysis: {str(e)}")
            return data
    
    def _analyze_momentum(self, data: pd.DataFrame, price_column: str) -> pd.DataFrame:
        """모멘텀 분석"""
        try:
            result = data.copy()
            
            # RSI 계산 (14일)
            delta = result[price_column].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            result['rsi'] = 100 - (100 / (1 + rs))
            
            # 모멘텀 지표들
            result['momentum'] = result[price_column] / result[price_column].shift(10) - 1  # 10일 모멘텀
            result['rate_of_change'] = result[price_column].pct_change(20) * 100  # 20일 변화율
            
            # 가격 위치 (52주 고가/저가 대비)
            result['high_52w'] = result[price_column].rolling(window=252).max()
            result['low_52w'] = result[price_column].rolling(window=252).min()
            result['price_position'] = (result[price_column] - result['low_52w']) / (result['high_52w'] - result['low_52w'])
            
            # 모멘텀 강도 계산
            result['momentum_strength'] = (
                (result['rsi'] - 50) / 50 * 0.4 +  # RSI 기여도 40%
                np.tanh(result['momentum'] * 5) * 0.3 +  # 모멘텀 기여도 30%
                np.tanh(result['rate_of_change'] / 10) * 0.3  # 변화율 기여도 30%
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in momentum analysis: {str(e)}")
            return data
    
    def _classify_market_condition(self, data: pd.DataFrame) -> pd.DataFrame:
        """시장 상황 분류"""
        try:
            result = data.copy()
            
            result['market_condition'] = MarketCondition.SIDEWAYS.value
            
            for i in range(len(result)):
                row = result.iloc[i]
                
                # 기본 지표 추출
                trend = row.get('overall_trend', 0)
                volatility = row.get('volatility', 0.2)
                momentum = row.get('momentum_strength', 0)
                volume_pressure = row.get('volume_pressure', 'NEUTRAL')
                price_position = row.get('price_position', 0.5)
                
                # 1. 급락장 감지 (최우선)
                if (trend < -0.7 and volatility > 0.4 and momentum < -0.5):
                    condition = MarketCondition.CRASH.value
                
                # 2. 상승장 감지
                elif (trend > 0.5 and momentum > 0.3 and 
                      volume_pressure in ['BUYING', 'NEUTRAL'] and price_position > 0.6):
                    condition = MarketCondition.BULL_MARKET.value
                
                # 3. 하락장 감지
                elif (trend < -0.5 and momentum < -0.3 and 
                      volume_pressure in ['SELLING', 'NEUTRAL'] and price_position < 0.4):
                    condition = MarketCondition.BEAR_MARKET.value
                
                # 4. 회복장 감지
                elif (trend > 0.3 and momentum > 0.4 and 
                      price_position < 0.5 and volume_pressure == 'BUYING'):
                    condition = MarketCondition.RECOVERY.value
                
                # 5. 변동성 장세 감지
                elif volatility > 0.35:
                    condition = MarketCondition.VOLATILE.value
                
                # 6. 횡보장 (기본값)
                else:
                    condition = MarketCondition.SIDEWAYS.value
                
                result.iloc[i, result.columns.get_loc('market_condition')] = condition
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in market condition classification: {str(e)}")
            return data
    
    def _calculate_condition_confidence(self, data: pd.DataFrame) -> pd.DataFrame:
        """시장 상황 분류 신뢰도 계산"""
        try:
            result = data.copy()
            
            result['condition_confidence'] = 0.5  # 기본 신뢰도
            
            for i in range(len(result)):
                row = result.iloc[i]
                condition = row.get('market_condition', MarketCondition.SIDEWAYS.value)
                
                # 지표들의 일치도 기반 신뢰도 계산
                trend = abs(row.get('overall_trend', 0))
                volatility = row.get('volatility', 0.2)
                momentum = abs(row.get('momentum_strength', 0))
                
                if condition == MarketCondition.BULL_MARKET.value:
                    confidence = min(0.95, 0.6 + trend * 0.3 + momentum * 0.2)
                elif condition == MarketCondition.BEAR_MARKET.value:
                    confidence = min(0.95, 0.6 + trend * 0.3 + momentum * 0.2)
                elif condition == MarketCondition.CRASH.value:
                    confidence = min(0.98, 0.8 + volatility * 0.3)
                elif condition == MarketCondition.VOLATILE.value:
                    confidence = min(0.9, 0.5 + volatility * 0.4)
                elif condition == MarketCondition.RECOVERY.value:
                    confidence = min(0.85, 0.6 + momentum * 0.25)
                else:  # SIDEWAYS
                    confidence = max(0.4, 0.7 - trend * 0.3 - momentum * 0.2)
                
                result.iloc[i, result.columns.get_loc('condition_confidence')] = confidence
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating condition confidence: {str(e)}")
            return data
    
    def adjust_signal_strength(self, signals_data: pd.DataFrame) -> pd.DataFrame:
        """
        시장 상황에 따른 신호 강도 조정
        
        Args:
            signals_data: 매매 신호가 포함된 데이터 (시장 상황 분석 완료)
            
        Returns:
            신호 강도가 조정된 DataFrame
        """
        try:
            result = signals_data.copy()
            
            # 조정 전 원본 신호 보존
            signal_columns = [col for col in result.columns if 'signal_strength' in col]
            for col in signal_columns:
                result[f'{col}_original'] = result[col].copy()
            
            # 시장 상황별 조정 계수
            condition_multipliers = {
                MarketCondition.BULL_MARKET.value: {'buy': 1.3, 'sell': 0.7},
                MarketCondition.BEAR_MARKET.value: {'buy': 0.7, 'sell': 1.3},
                MarketCondition.CRASH.value: {'buy': 0.3, 'sell': 1.8},
                MarketCondition.RECOVERY.value: {'buy': 1.5, 'sell': 0.5},
                MarketCondition.VOLATILE.value: {'buy': 0.8, 'sell': 0.8},
                MarketCondition.SIDEWAYS.value: {'buy': 1.0, 'sell': 1.0}
            }
            
            for i in range(len(result)):
                condition = result.iloc[i].get('market_condition', MarketCondition.SIDEWAYS.value)
                confidence = result.iloc[i].get('condition_confidence', 0.5)
                
                if condition in condition_multipliers:
                    multipliers = condition_multipliers[condition]
                    
                    # 신뢰도 기반 조정 강도
                    adjustment_factor = 0.3 + (confidence * 0.7)  # 0.3 ~ 1.0
                    
                    for col in signal_columns:
                        original_strength = result.iloc[i][col]
                        
                        if original_strength > 0:  # 매수 신호
                            adjusted_strength = original_strength * (
                                1 + (multipliers['buy'] - 1) * adjustment_factor
                            )
                        elif original_strength < 0:  # 매도 신호
                            adjusted_strength = original_strength * (
                                1 + (multipliers['sell'] - 1) * adjustment_factor
                            )
                        else:  # 신호 없음
                            adjusted_strength = original_strength
                        
                        # 조정된 강도를 적용 (최대 ±5 제한)
                        result.iloc[i, result.columns.get_loc(col)] = np.clip(
                            adjusted_strength, -5, 5
                        )
            
            adjustment_count = sum(1 for col in signal_columns 
                                 if not result[col].equals(result[f'{col}_original']))
            
            self.logger.info(f"Signal strength adjusted for {adjustment_count} indicators based on market conditions")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error adjusting signal strength: {str(e)}")
            return signals_data
    
    def get_market_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """시장 상황 분석 요약"""
        try:
            if data.empty or 'market_condition' not in data.columns:
                return {}
            
            latest = data.iloc[-1]
            
            # 현재 시장 상황
            current_condition = {
                'market_condition': str(latest.get('market_condition', 'UNKNOWN')),
                'condition_confidence': float(latest.get('condition_confidence', 0.0)),
                'overall_trend': float(latest.get('overall_trend', 0.0)),
                'volatility': float(latest.get('volatility', 0.0)),
                'momentum_strength': float(latest.get('momentum_strength', 0.0)),
                'volume_pressure': str(latest.get('volume_pressure', 'UNKNOWN')),
                'price_position': float(latest.get('price_position', 0.0))
            }
            
            # 시장 상황 분포 (최근 60일)
            recent_data = data.tail(60) if len(data) >= 60 else data
            condition_distribution = recent_data['market_condition'].value_counts().to_dict()
            
            # 평균 지표들
            avg_metrics = {
                'avg_volatility': float(recent_data['volatility'].mean()),
                'avg_trend': float(recent_data['overall_trend'].mean()),
                'avg_momentum': float(recent_data['momentum_strength'].mean()),
                'avg_confidence': float(recent_data['condition_confidence'].mean())
            }
            
            summary = {
                'current_condition': current_condition,
                'condition_distribution': condition_distribution,
                'avg_metrics': avg_metrics,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating market summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 시장 상황 분석기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="2y")
    
    if stock_data is not None and len(stock_data) > 200:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 시장 상황 분석기 초기화
        market_analyzer = MarketConditionAnalyzer()
        
        # 2. 시장 상황 분석
        print(f"\n2. 시장 상황 종합 분석 중...")
        analyzed_data = market_analyzer.analyze_market_condition(stock_data)
        
        # 3. 결과 분석
        print(f"\n=== 시장 상황 분석 결과 ===")
        
        latest = analyzed_data.iloc[-1]
        print(f"현재가: {latest['close']:,.0f}원")
        print(f"시장 상황: {latest['market_condition']}")
        print(f"신뢰도: {latest['condition_confidence']:.2f}")
        print(f"전체 트렌드: {latest['overall_trend']:+.3f}")
        print(f"변동성: {latest['volatility']:.2%}")
        print(f"모멘텀 강도: {latest['momentum_strength']:+.3f}")
        print(f"거래량 압력: {latest['volume_pressure']}")
        print(f"가격 위치: {latest['price_position']:.1%}")
        
        # 시장 상황 분포
        condition_counts = analyzed_data['market_condition'].value_counts()
        print(f"\n시장 상황 분포:")
        for condition, count in condition_counts.items():
            percentage = count / len(analyzed_data) * 100
            print(f"  {condition}: {count}일 ({percentage:.1f}%)")
        
        # 최근 변화 추이
        recent_30 = analyzed_data.tail(30)
        recent_conditions = recent_30['market_condition'].value_counts()
        print(f"\n최근 30일 시장 상황:")
        for condition, count in recent_conditions.items():
            percentage = count / 30 * 100
            print(f"  {condition}: {count}일 ({percentage:.1f}%)")
        
        # 요약 정보
        summary = market_analyzer.get_market_summary(analyzed_data)
        print(f"\n=== 요약 ===")
        print(f"시장 상황 분석 완료 - 6가지 상황 분류")
        print(f"평균 신뢰도: {summary['avg_metrics']['avg_confidence']:.2f}")
        print(f"평균 변동성: {summary['avg_metrics']['avg_volatility']:.2%}")
        
    else:
        print("   데이터 부족 - 최소 200일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()