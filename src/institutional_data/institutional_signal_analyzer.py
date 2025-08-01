"""
외국인·기관 매매 신호 분석기
기술적 지표와 결합하여 투자자별 매매 동향 기반 매매 신호 생성
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.institutional_data.institutional_data_manager import InstitutionalDataManager

class InstitutionalSignalAnalyzer:
    """외국인·기관 매매 신호 분석기"""
    
    def __init__(self, 
                 volume_threshold: float = 100,  # 거래대금 임계값 (억원)
                 concentration_threshold: float = 0.7,  # 집중도 임계값
                 trend_days: int = 5):  # 추세 분석 기간
        """
        초기화
        
        Args:
            volume_threshold: 유의미한 거래대금 임계값 (억원)
            concentration_threshold: 매수/매도 집중도 임계값
            trend_days: 추세 분석 기간 (일)
        """
        self.volume_threshold = volume_threshold
        self.concentration_threshold = concentration_threshold
        self.trend_days = trend_days
        self.logger = self._setup_logger()
        
        # 기관 데이터 관리자 초기화
        self.data_manager = InstitutionalDataManager(
            use_pykrx=True,
            use_kis_api=False  # 기본적으로 PyKRX만 사용
        )
        
        self.logger.info("외국인·기관 신호 분석기 초기화 완료")
        
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
    
    def analyze_institutional_signals(self, 
                                    symbol: str,
                                    technical_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        종목별 기관·외국인 매매 신호 분석
        
        Args:
            symbol: 종목코드 (6자리)
            technical_data: 기술적 분석 데이터 (옵션)
            
        Returns:
            기관·외국인 신호가 추가된 DataFrame
        """
        try:
            self.logger.info(f"기관·외국인 신호 분석 시작: {symbol}")
            
            # 기관 데이터 수집 (최근 20일)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            institutional_data = self.data_manager.collect_comprehensive_institutional_data(
                symbol, start_date, end_date
            )
            
            if institutional_data.empty:
                self.logger.warning(f"기관 데이터 없음: {symbol}")
                return technical_data if technical_data is not None else pd.DataFrame()
            
            # 기관·외국인 신호 계산
            institutional_signals = self._calculate_institutional_signals(institutional_data)
            
            # 기술적 분석 데이터와 병합
            if technical_data is not None:
                result = self._merge_with_technical_data(technical_data, institutional_signals)
            else:
                result = institutional_signals
            
            self.logger.info(f"기관·외국인 신호 분석 완료: {symbol}")
            return result
            
        except Exception as e:
            self.logger.error(f"기관·외국인 신호 분석 오류: {str(e)}")
            return technical_data if technical_data is not None else pd.DataFrame()
    
    def _calculate_institutional_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """기관·외국인 매매 신호 계산"""
        try:
            result = data.copy()
            
            # 신호 초기화
            result['foreign_signal'] = 0
            result['foreign_signal_strength'] = 0.0
            result['institutional_signal'] = 0
            result['institutional_signal_strength'] = 0.0
            result['combined_institutional_signal'] = 0
            result['combined_institutional_strength'] = 0.0
            result['institutional_confidence'] = 0.0
            
            # 외국인 신호 계산
            if 'foreign_value' in result.columns or 'foreign_net_buy_value' in result.columns:
                result = self._calculate_foreign_signals(result)
            
            # 기관 신호 계산
            institutional_cols = ['institutional_total_value', 'institutional_net_buy_value']
            for col in institutional_cols:
                if col in result.columns:
                    result = self._calculate_institutional_signals_detail(result, col)
                    break
            
            # 통합 신호 계산
            result = self._calculate_combined_institutional_signal(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"기관 신호 계산 오류: {str(e)}")
            return data
    
    def _calculate_foreign_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """외국인 매매 신호 계산"""
        try:
            # 외국인 거래대금 컬럼 선택
            foreign_col = 'foreign_value' if 'foreign_value' in data.columns else 'foreign_net_buy_value'
            
            if foreign_col not in data.columns:
                return data
            
            foreign_values = data[foreign_col].fillna(0)
            
            # 이동평균 기반 추세 분석
            foreign_ma = foreign_values.rolling(window=self.trend_days, min_periods=1).mean()
            foreign_trend = foreign_ma.diff()
            
            for idx in range(len(data)):
                current_value = foreign_values.iloc[idx]
                current_trend = foreign_trend.iloc[idx] if not pd.isna(foreign_trend.iloc[idx]) else 0
                
                # 신호 강도 계산
                signal_strength = 0.0
                signal = 0
                
                # 대량 순매수 신호
                if current_value > self.volume_threshold:
                    signal = 1
                    signal_strength = min(3.0, current_value / self.volume_threshold)
                    
                    # 추세 강화
                    if current_trend > 0:
                        signal_strength *= 1.2
                
                # 대량 순매도 신호
                elif current_value < -self.volume_threshold:
                    signal = -1
                    signal_strength = min(3.0, abs(current_value) / self.volume_threshold)
                    
                    # 추세 강화
                    if current_trend < 0:
                        signal_strength *= 1.2
                
                # 추세 지속 신호 (중간 강도)
                elif abs(current_trend) > self.volume_threshold / 3:
                    if current_trend > 0 and current_value > 0:
                        signal = 1
                        signal_strength = min(2.0, abs(current_trend) / (self.volume_threshold / 3))
                    elif current_trend < 0 and current_value < 0:
                        signal = -1
                        signal_strength = min(2.0, abs(current_trend) / (self.volume_threshold / 3))
                
                data.loc[data.index[idx], 'foreign_signal'] = signal
                data.loc[data.index[idx], 'foreign_signal_strength'] = signal_strength
            
            return data
            
        except Exception as e:
            self.logger.error(f"외국인 신호 계산 오류: {str(e)}")
            return data
    
    def _calculate_institutional_signals_detail(self, 
                                              data: pd.DataFrame, 
                                              inst_col: str) -> pd.DataFrame:
        """기관 매매 신호 상세 계산"""
        try:
            institutional_values = data[inst_col].fillna(0)
            
            # 이동평균 기반 추세 분석
            inst_ma = institutional_values.rolling(window=self.trend_days, min_periods=1).mean()
            inst_trend = inst_ma.diff()
            
            for idx in range(len(data)):
                current_value = institutional_values.iloc[idx]
                current_trend = inst_trend.iloc[idx] if not pd.isna(inst_trend.iloc[idx]) else 0
                
                # 신호 강도 계산
                signal_strength = 0.0
                signal = 0
                
                # 대량 순매수 신호
                if current_value > self.volume_threshold:
                    signal = 1
                    signal_strength = min(3.0, current_value / self.volume_threshold)
                    
                    # 추세 강화
                    if current_trend > 0:
                        signal_strength *= 1.1
                
                # 대량 순매도 신호
                elif current_value < -self.volume_threshold:
                    signal = -1
                    signal_strength = min(3.0, abs(current_value) / self.volume_threshold)
                    
                    # 추세 강화
                    if current_trend < 0:
                        signal_strength *= 1.1
                
                # 추세 지속 신호
                elif abs(current_trend) > self.volume_threshold / 4:
                    if current_trend > 0 and current_value > 0:
                        signal = 1
                        signal_strength = min(2.0, abs(current_trend) / (self.volume_threshold / 4))
                    elif current_trend < 0 and current_value < 0:
                        signal = -1
                        signal_strength = min(2.0, abs(current_trend) / (self.volume_threshold / 4))
                
                data.loc[data.index[idx], 'institutional_signal'] = signal
                data.loc[data.index[idx], 'institutional_signal_strength'] = signal_strength
            
            return data
            
        except Exception as e:
            self.logger.error(f"기관 신호 상세 계산 오류: {str(e)}")
            return data
    
    def _calculate_combined_institutional_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """외국인·기관 통합 신호 계산"""
        try:
            # 가중치 설정
            foreign_weight = 0.6  # 외국인 신호 가중치
            institutional_weight = 0.4  # 기관 신호 가중치
            
            for idx in range(len(data)):
                foreign_signal = data.loc[data.index[idx], 'foreign_signal']
                foreign_strength = data.loc[data.index[idx], 'foreign_signal_strength']
                institutional_signal = data.loc[data.index[idx], 'institutional_signal']
                institutional_strength = data.loc[data.index[idx], 'institutional_signal_strength']
                
                # 가중 평균 신호 강도
                weighted_strength = (
                    foreign_signal * foreign_strength * foreign_weight +
                    institutional_signal * institutional_strength * institutional_weight
                )
                
                # 통합 신호 결정
                combined_signal = 0
                if weighted_strength > 1.0:
                    combined_signal = 1
                elif weighted_strength < -1.0:
                    combined_signal = -1
                
                # 신뢰도 계산 (신호 일치도 기반)
                confidence = 0.0
                if foreign_signal != 0 and institutional_signal != 0:
                    if foreign_signal == institutional_signal:
                        # 같은 방향 신호일 때 높은 신뢰도
                        confidence = min(1.0, (foreign_strength + institutional_strength) / 4.0)
                    else:
                        # 반대 방향 신호일 때 낮은 신뢰도
                        confidence = max(0.0, abs(weighted_strength) / 3.0)
                elif foreign_signal != 0 or institutional_signal != 0:
                    # 한쪽만 신호가 있을 때 중간 신뢰도
                    total_strength = foreign_strength + institutional_strength
                    confidence = min(0.7, total_strength / 3.0)
                
                data.loc[data.index[idx], 'combined_institutional_signal'] = combined_signal
                data.loc[data.index[idx], 'combined_institutional_strength'] = abs(weighted_strength)
                data.loc[data.index[idx], 'institutional_confidence'] = confidence
            
            return data
            
        except Exception as e:
            self.logger.error(f"통합 기관 신호 계산 오류: {str(e)}")
            return data
    
    def _merge_with_technical_data(self, 
                                 technical_data: pd.DataFrame, 
                                 institutional_data: pd.DataFrame) -> pd.DataFrame:
        """기술적 분석 데이터와 기관 데이터 병합"""
        try:
            if technical_data.empty:
                return institutional_data
            
            if institutional_data.empty:
                return technical_data
            
            # 날짜 기준으로 병합
            tech_data = technical_data.copy()
            inst_data = institutional_data.copy()
            
            # 날짜 컬럼 확인 및 생성
            if 'date' not in tech_data.columns:
                if tech_data.index.name == 'date' or 'Date' in str(tech_data.index):
                    tech_data = tech_data.reset_index()
                    tech_data.rename(columns={tech_data.columns[0]: 'date'}, inplace=True)
                else:
                    # 날짜 컬럼이 없으면 인덱스를 날짜로 가정
                    tech_data['date'] = pd.to_datetime(tech_data.index)
            
            # 날짜 형식 통일
            tech_data['date'] = pd.to_datetime(tech_data['date'])
            inst_data['date'] = pd.to_datetime(inst_data['date'])
            
            # 기관 데이터의 기관 관련 컬럼만 선택
            institutional_columns = [
                'date', 'foreign_signal', 'foreign_signal_strength',
                'institutional_signal', 'institutional_signal_strength',
                'combined_institutional_signal', 'combined_institutional_strength',
                'institutional_confidence'
            ]
            
            # 사용 가능한 컬럼만 선택
            available_inst_cols = [col for col in institutional_columns if col in inst_data.columns]
            inst_subset = inst_data[available_inst_cols]
            
            # 날짜 기준 좌측 조인 (기술적 분석 데이터 기준)
            merged_data = pd.merge(
                tech_data, 
                inst_subset, 
                on='date', 
                how='left'
            )
            
            # 누락된 기관 신호 값을 0으로 채움
            institutional_signal_columns = [
                'foreign_signal', 'foreign_signal_strength',
                'institutional_signal', 'institutional_signal_strength',
                'combined_institutional_signal', 'combined_institutional_strength',
                'institutional_confidence'
            ]
            
            for col in institutional_signal_columns:
                if col in merged_data.columns:
                    merged_data[col] = merged_data[col].fillna(0)
            
            self.logger.info(f"기술적 분석과 기관 데이터 병합 완료: {len(merged_data)}일")
            return merged_data
            
        except Exception as e:
            self.logger.error(f"데이터 병합 오류: {str(e)}")
            return technical_data
    
    def get_institutional_summary(self, 
                                institutional_data: pd.DataFrame,
                                symbol: str) -> Dict[str, Any]:
        """기관·외국인 매매 분석 요약"""
        try:
            if institutional_data.empty:
                return {}
            
            latest = institutional_data.iloc[-1]
            
            # 현재 상태
            current_status = {
                'symbol': symbol,
                'date': latest.get('date', datetime.now()).strftime('%Y-%m-%d'),
                'foreign_signal': int(latest.get('foreign_signal', 0)),
                'foreign_strength': float(latest.get('foreign_signal_strength', 0)),
                'institutional_signal': int(latest.get('institutional_signal', 0)),
                'institutional_strength': float(latest.get('institutional_signal_strength', 0)),
                'combined_signal': int(latest.get('combined_institutional_signal', 0)),
                'combined_strength': float(latest.get('combined_institutional_strength', 0)),
                'confidence': float(latest.get('institutional_confidence', 0))
            }
            
            # 최근 N일 통계
            recent_days = min(10, len(institutional_data))
            recent_data = institutional_data.tail(recent_days)
            
            statistics = {
                'analysis_period': recent_days,
                'foreign_buy_signals': int((recent_data.get('foreign_signal', 0) == 1).sum()),
                'foreign_sell_signals': int((recent_data.get('foreign_signal', 0) == -1).sum()),
                'institutional_buy_signals': int((recent_data.get('institutional_signal', 0) == 1).sum()),
                'institutional_sell_signals': int((recent_data.get('institutional_signal', 0) == -1).sum()),
                'combined_buy_signals': int((recent_data.get('combined_institutional_signal', 0) == 1).sum()),
                'combined_sell_signals': int((recent_data.get('combined_institutional_signal', 0) == -1).sum()),
                'avg_confidence': float(recent_data.get('institutional_confidence', 0).mean())
            }
            
            # 신호 품질 평가
            signal_quality = 'NONE'
            if current_status['confidence'] > 0.8:
                signal_quality = 'EXCELLENT'
            elif current_status['confidence'] > 0.6:
                signal_quality = 'GOOD'
            elif current_status['confidence'] > 0.4:
                signal_quality = 'FAIR'
            elif current_status['confidence'] > 0.2:
                signal_quality = 'WEAK'
            
            summary = {
                'current_status': current_status,
                'statistics': statistics,
                'signal_quality': signal_quality,
                'analysis_date': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"기관 매매 요약 생성 오류: {str(e)}")
            return {}


def main():
    """테스트 실행"""
    print("=== 외국인·기관 매매 신호 분석기 테스트 ===")
    
    analyzer = InstitutionalSignalAnalyzer(
        volume_threshold=50,  # 50억원 임계값
        trend_days=5
    )
    
    test_symbol = "005930"  # 삼성전자
    
    print(f"\n1. 기관·외국인 신호 분석 테스트 ({test_symbol})")
    institutional_signals = analyzer.analyze_institutional_signals(test_symbol)
    
    if not institutional_signals.empty:
        print(f"   ✅ 분석 성공: {len(institutional_signals)}일")
        
        # 기관 신호 관련 컬럼 확인
        inst_columns = [col for col in institutional_signals.columns 
                       if 'institutional' in col or 'foreign' in col]
        print(f"   기관 신호 컬럼: {inst_columns}")
        
        # 최근 데이터 출력
        if len(institutional_signals) > 0:
            latest = institutional_signals.iloc[-1]
            print(f"   최신일자: {latest.get('date', 'Unknown')}")
            print(f"   외국인 신호: {latest.get('foreign_signal', 0)} (강도: {latest.get('foreign_signal_strength', 0):.2f})")
            print(f"   기관 신호: {latest.get('institutional_signal', 0)} (강도: {latest.get('institutional_signal_strength', 0):.2f})")
            print(f"   통합 신호: {latest.get('combined_institutional_signal', 0)} (강도: {latest.get('combined_institutional_strength', 0):.2f})")
            print(f"   신뢰도: {latest.get('institutional_confidence', 0):.2f}")
        
        print(f"\n2. 기관·외국인 매매 요약 생성")
        summary = analyzer.get_institutional_summary(institutional_signals, test_symbol)
        
        if summary:
            print(f"   ✅ 요약 생성 성공")
            current = summary.get('current_status', {})
            stats = summary.get('statistics', {})
            
            print(f"   신호 품질: {summary.get('signal_quality', 'UNKNOWN')}")
            print(f"   최근 {stats.get('analysis_period', 0)}일 통계:")
            print(f"     외국인 매수신호: {stats.get('foreign_buy_signals', 0)}회")
            print(f"     외국인 매도신호: {stats.get('foreign_sell_signals', 0)}회")
            print(f"     기관 매수신호: {stats.get('institutional_buy_signals', 0)}회")
            print(f"     기관 매도신호: {stats.get('institutional_sell_signals', 0)}회")
            print(f"     통합 매수신호: {stats.get('combined_buy_signals', 0)}회")
            print(f"     통합 매도신호: {stats.get('combined_sell_signals', 0)}회")
            print(f"     평균 신뢰도: {stats.get('avg_confidence', 0):.2f}")
        else:
            print("   ❌ 요약 생성 실패")
    
    else:
        print("   ❌ 신호 분석 실패")
    
    print(f"\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()