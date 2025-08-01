"""
이동평균선 계산 및 교차점 감지
정확도 높은 매매 신호 생성을 위한 핵심 모듈
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

class MovingAverageAnalyzer:
    """이동평균선 분석기 - 정확한 매매 신호 생성"""
    
    def __init__(self, periods: List[int] = [5, 10, 20, 60, 120]):
        """
        Args:
            periods: 이동평균 기간 리스트 (기본: 5일, 10일, 20일, 60일, 120일)
        """
        self.periods = sorted(periods)
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
    
    def calculate_moving_averages(self, data: pd.DataFrame, 
                                 price_column: str = 'close') -> pd.DataFrame:
        """
        다중 이동평균선 계산
        
        Args:
            data: 주가 데이터 (OHLCV)
            price_column: 계산할 가격 컬럼명
            
        Returns:
            이동평균선이 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 각 기간별 이동평균 계산
            for period in self.periods:
                ma_column = f'ma_{period}'
                result[ma_column] = result[price_column].rolling(window=period).mean()
                
                # 이동평균 대비 현재가 위치 (%)
                result[f'ma_{period}_ratio'] = (result[price_column] / result[ma_column] - 1) * 100
            
            self.logger.info(f"Moving averages calculated for periods: {self.periods}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {str(e)}")
            return data
    
    def detect_crossovers(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        골든크로스/데드크로스 감지 (정확도 핵심)
        
        Args:
            data: 이동평균선이 계산된 데이터
            
        Returns:
            교차 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 주요 교차점들
            crossover_pairs = [
                (5, 20),   # 단기 크로스
                (10, 20),  # 중기 크로스  
                (20, 60),  # 장기 크로스
                (5, 60),   # 초단기-장기 크로스
            ]
            
            for fast_period, slow_period in crossover_pairs:
                fast_ma = f'ma_{fast_period}'
                slow_ma = f'ma_{slow_period}'
                signal_name = f'cross_{fast_period}_{slow_period}'
                
                if fast_ma in result.columns and slow_ma in result.columns:
                    # 교차점 감지
                    result[f'{signal_name}_signal'] = 0
                    
                    # 골든크로스 (상승 돌파): 1
                    golden_cross = (
                        (result[fast_ma] > result[slow_ma]) & 
                        (result[fast_ma].shift(1) <= result[slow_ma].shift(1))
                    )
                    result.loc[golden_cross, f'{signal_name}_signal'] = 1
                    
                    # 데드크로스 (하락 돌파): -1  
                    dead_cross = (
                        (result[fast_ma] < result[slow_ma]) & 
                        (result[fast_ma].shift(1) >= result[slow_ma].shift(1))
                    )
                    result.loc[dead_cross, f'{signal_name}_signal'] = -1
                    
                    # 현재 상태 (상위/하위)
                    result[f'{signal_name}_position'] = np.where(
                        result[fast_ma] > result[slow_ma], 1, -1
                    )
            
            self.logger.info(f"Crossover signals detected for {len(crossover_pairs)} pairs")
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting crossovers: {str(e)}")
            return data
    
    def get_trend_strength(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        트렌드 강도 분석 (정확도 향상)
        
        Args:
            data: 이동평균선 데이터
            
        Returns:
            트렌드 강도가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 이동평균선 정렬 상태 확인
            ma_columns = [f'ma_{period}' for period in self.periods if f'ma_{period}' in result.columns]
            
            if len(ma_columns) >= 3:
                # 상승 정렬 강도 (단기 > 중기 > 장기)
                uptrend_score = 0
                downtrend_score = 0
                
                for i in range(len(ma_columns) - 1):
                    uptrend_condition = result[ma_columns[i]] > result[ma_columns[i + 1]]
                    uptrend_score += uptrend_condition.astype(int)
                    
                    downtrend_condition = result[ma_columns[i]] < result[ma_columns[i + 1]]  
                    downtrend_score += downtrend_condition.astype(int)
                
                # 트렌드 강도 점수 (0~1)
                max_score = len(ma_columns) - 1
                result['uptrend_strength'] = uptrend_score / max_score
                result['downtrend_strength'] = downtrend_score / max_score
                
                # 전체 트렌드 점수 (-1 ~ 1)
                result['trend_score'] = result['uptrend_strength'] - result['downtrend_strength']
                
                # 트렌드 상태 분류
                result['trend_status'] = 'SIDEWAYS'
                result.loc[result['trend_score'] >= 0.6, 'trend_status'] = 'STRONG_UPTREND'
                result.loc[result['trend_score'] >= 0.3, 'trend_status'] = 'UPTREND'
                result.loc[result['trend_score'] <= -0.6, 'trend_status'] = 'STRONG_DOWNTREND'
                result.loc[result['trend_score'] <= -0.3, 'trend_status'] = 'DOWNTREND'
            
            self.logger.info("Trend strength analysis completed")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {str(e)}")
            return data
    
    def generate_ma_signals(self, data: pd.DataFrame, 
                           min_confirmation_days: int = 2) -> pd.DataFrame:
        """
        이동평균 기반 매매 신호 생성 (고정확도)
        
        Args:
            data: 분석된 데이터
            min_confirmation_days: 신호 확인 기간
            
        Returns:
            매매 신호가 추가된 DataFrame
        """
        try:
            result = data.copy()
            
            # 기본 매매 신호 초기화
            result['ma_buy_signal'] = 0
            result['ma_sell_signal'] = 0
            result['ma_signal_strength'] = 0
            
            # 강한 매수 신호 조건들
            buy_conditions = []
            
            # 1. 골든크로스 발생
            if 'cross_5_20_signal' in result.columns:
                golden_cross_5_20 = result['cross_5_20_signal'] == 1
                buy_conditions.append(golden_cross_5_20)
            
            # 2. 상승 트렌드 확인
            if 'trend_score' in result.columns:
                strong_uptrend = result['trend_score'] >= 0.5
                buy_conditions.append(strong_uptrend)
            
            # 3. 현재가가 주요 이동평균선 위에 위치
            if 'ma_20' in result.columns:
                above_ma20 = result['close'] > result['ma_20']
                buy_conditions.append(above_ma20)
            
            # 강한 매도 신호 조건들
            sell_conditions = []
            
            # 1. 데드크로스 발생
            if 'cross_5_20_signal' in result.columns:
                dead_cross_5_20 = result['cross_5_20_signal'] == -1
                sell_conditions.append(dead_cross_5_20)
            
            # 2. 하락 트렌드 확인  
            if 'trend_score' in result.columns:
                strong_downtrend = result['trend_score'] <= -0.5
                sell_conditions.append(strong_downtrend)
            
            # 3. 현재가가 주요 이동평균선 아래 위치
            if 'ma_20' in result.columns:
                below_ma20 = result['close'] < result['ma_20']
                sell_conditions.append(below_ma20)
            
            # 다중 조건 확인으로 신호 생성
            if buy_conditions:
                buy_score = sum(condition.astype(int) for condition in buy_conditions)
                result['ma_signal_strength'] = buy_score
                
                # 2개 이상 조건 만족 시 매수 신호
                strong_buy = buy_score >= min(2, len(buy_conditions))
                result.loc[strong_buy, 'ma_buy_signal'] = 1
            
            if sell_conditions:
                sell_score = sum(condition.astype(int) for condition in sell_conditions)
                
                # 2개 이상 조건 만족 시 매도 신호
                strong_sell = sell_score >= min(2, len(sell_conditions))
                result.loc[strong_sell, 'ma_sell_signal'] = 1
                result.loc[strong_sell, 'ma_signal_strength'] = -sell_score
            
            # 신호 확인 기간 적용 (잡음 제거)
            if min_confirmation_days > 1:
                result = self._apply_signal_confirmation(result, min_confirmation_days)
            
            signal_count = (result['ma_buy_signal'] == 1).sum() + (result['ma_sell_signal'] == 1).sum()
            self.logger.info(f"Generated {signal_count} high-confidence MA signals")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating MA signals: {str(e)}")
            return data
    
    def _apply_signal_confirmation(self, data: pd.DataFrame, 
                                 confirmation_days: int) -> pd.DataFrame:
        """신호 확인 기간 적용 (잡음 제거)"""
        try:
            result = data.copy()
            
            # 매수 신호 확인
            buy_confirmed = result['ma_buy_signal'].rolling(
                window=confirmation_days
            ).sum() >= 1
            
            # 매도 신호 확인
            sell_confirmed = result['ma_sell_signal'].rolling(
                window=confirmation_days
            ).sum() >= 1
            
            # 확인된 신호만 유지
            result['ma_buy_signal_confirmed'] = buy_confirmed.astype(int)
            result['ma_sell_signal_confirmed'] = sell_confirmed.astype(int)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error applying signal confirmation: {str(e)}")
            return data
    
    def get_ma_summary(self, data: pd.DataFrame) -> Dict:
        """이동평균 분석 요약"""
        try:
            if data.empty:
                return {}
            
            latest = data.iloc[-1]
            
            # 현재 이동평균선 상태
            ma_positions = {}
            for period in self.periods:
                ma_col = f'ma_{period}'
                if ma_col in data.columns:
                    ma_positions[f'MA{period}'] = {
                        'value': float(latest[ma_col]) if not pd.isna(latest[ma_col]) else None,
                        'ratio': float(latest[f'ma_{period}_ratio']) if f'ma_{period}_ratio' in data.columns and not pd.isna(latest[f'ma_{period}_ratio']) else None
                    }
            
            # 최근 신호
            recent_signals = {
                'buy_signals': int((data['ma_buy_signal'] == 1).sum()) if 'ma_buy_signal' in data.columns else 0,
                'sell_signals': int((data['ma_sell_signal'] == 1).sum()) if 'ma_sell_signal' in data.columns else 0,
                'latest_trend': str(latest['trend_status']) if 'trend_status' in data.columns else 'UNKNOWN',
                'trend_strength': float(latest['trend_score']) if 'trend_score' in data.columns and not pd.isna(latest['trend_score']) else 0.0
            }
            
            summary = {
                'ma_positions': ma_positions,
                'signals': recent_signals,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating MA summary: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.data_collection.data_manager import DataManager
    from config.korean_stocks import TEST_SYMBOLS
    
    print("=== 이동평균선 분석기 테스트 ===")
    
    # 데이터 수집
    data_manager = DataManager()
    test_symbol = TEST_SYMBOLS[0]  # 삼성전자
    
    print(f"\n1. {test_symbol} 데이터 로딩 중...")
    # 기존 수집된 데이터 사용
    stock_data = data_manager.yahoo_collector.get_stock_data(test_symbol, period="1y")
    
    if stock_data is not None and len(stock_data) > 120:
        print(f"   데이터 로딩 완료: {len(stock_data)}개 레코드")
        
        # 이동평균 분석기 초기화
        ma_analyzer = MovingAverageAnalyzer()
        
        # 2. 이동평균선 계산
        print(f"\n2. 이동평균선 계산 중...")
        ma_data = ma_analyzer.calculate_moving_averages(stock_data)
        
        # 3. 교차점 감지
        print(f"3. 교차점 감지 중...")
        cross_data = ma_analyzer.detect_crossovers(ma_data)
        
        # 4. 트렌드 강도 분석
        print(f"4. 트렌드 강도 분석 중...")
        trend_data = ma_analyzer.get_trend_strength(cross_data)
        
        # 5. 매매 신호 생성
        print(f"5. 매매 신호 생성 중...")
        signal_data = ma_analyzer.generate_ma_signals(trend_data)
        
        # 6. 결과 분석
        print(f"\n=== 분석 결과 ===")
        
        # 최근 이동평균선 현황
        latest = signal_data.iloc[-1]
        print(f"현재가: {latest['close']:,.0f}원")
        
        for period in [5, 20, 60]:
            if f'ma_{period}' in signal_data.columns:
                ma_val = latest[f'ma_{period}']
                ratio = latest[f'ma_{period}_ratio']
                print(f"MA{period}: {ma_val:,.0f}원 ({ratio:+.1f}%)")
        
        # 트렌드 상태
        if 'trend_status' in signal_data.columns:
            trend_status = latest['trend_status']
            trend_score = latest['trend_score']
            print(f"트렌드: {trend_status} (점수: {trend_score:.2f})")
        
        # 매매 신호 현황
        buy_signals = (signal_data['ma_buy_signal'] == 1).sum()
        sell_signals = (signal_data['ma_sell_signal'] == 1).sum()
        print(f"매수 신호: {buy_signals}회")
        print(f"매도 신호: {sell_signals}회")
        
        # 최근 신호
        recent_buy = signal_data[signal_data['ma_buy_signal'] == 1].tail(1)
        recent_sell = signal_data[signal_data['ma_sell_signal'] == 1].tail(1)
        
        if not recent_buy.empty:
            buy_date = recent_buy.iloc[0]['date']
            print(f"최근 매수 신호: {buy_date}")
        
        if not recent_sell.empty:
            sell_date = recent_sell.iloc[0]['date']
            print(f"최근 매도 신호: {sell_date}")
        
        # 요약 정보
        summary = ma_analyzer.get_ma_summary(signal_data)
        print(f"\n=== 요약 ===")
        print(f"분석 완료: {len(summary['ma_positions'])}개 이동평균선")
        print(f"신호 품질: 다중 조건 확인 방식")
        
    else:
        print("   데이터 부족 - 최소 120일 데이터 필요")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()