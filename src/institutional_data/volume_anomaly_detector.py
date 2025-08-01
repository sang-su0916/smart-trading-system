"""
대량 거래 감지 및 호재성 판단 시스템
비정상적인 거래량과 기관·외국인 매매 패턴을 감지하여 호재/악재성 이벤트 판단
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
from enum import Enum
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.institutional_data.institutional_data_manager import InstitutionalDataManager

class AnomalyType(Enum):
    """이상 거래 유형"""
    VOLUME_SPIKE = "VOLUME_SPIKE"           # 거래량 급증
    INSTITUTIONAL_SURGE = "INSTITUTIONAL_SURGE"  # 기관 대량 매수
    FOREIGN_SURGE = "FOREIGN_SURGE"        # 외국인 대량 매수
    MIXED_SURGE = "MIXED_SURGE"            # 복합 대량 매수
    SELLING_PRESSURE = "SELLING_PRESSURE"   # 대량 매도 압력
    UNUSUAL_PATTERN = "UNUSUAL_PATTERN"     # 비정상 패턴

class VolumeAnomalyDetector:
    """대량 거래 감지 및 호재성 판단 시스템"""
    
    def __init__(self, 
                 volume_threshold_multiplier: float = 3.0,  # 거래량 임계값 배수
                 amount_threshold: float = 1000,            # 거래대금 임계값 (억원)
                 analysis_period: int = 20,                 # 분석 기간 (일)
                 lookback_period: int = 60):                # 기준선 계산 기간 (일)
        """
        초기화
        
        Args:
            volume_threshold_multiplier: 평균 거래량 대비 임계값 배수
            amount_threshold: 대량 거래 판단 임계값 (억원)
            analysis_period: 이상 거래 분석 기간 (일)
            lookback_period: 기준선 계산을 위한 과거 데이터 기간 (일)
        """
        self.volume_threshold_multiplier = volume_threshold_multiplier
        self.amount_threshold = amount_threshold
        self.analysis_period = analysis_period
        self.lookback_period = lookback_period
        self.logger = self._setup_logger()
        
        # 기관 데이터 관리자 초기화
        self.data_manager = InstitutionalDataManager(
            use_pykrx=True,
            use_kis_api=False
        )
        
        self.logger.info("대량 거래 감지 시스템 초기화 완료")
        
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
    
    def detect_volume_anomalies(self, 
                              symbol: str,
                              price_data: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
        """
        종목별 대량 거래 이상 감지
        
        Args:
            symbol: 종목코드 (6자리)
            price_data: 주가 데이터 (옵션, 없으면 자동 수집)
            
        Returns:
            감지된 이상 거래 리스트
        """
        try:
            self.logger.info(f"대량 거래 이상 감지 시작: {symbol}")
            
            # 데이터 수집
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=self.lookback_period + self.analysis_period)).strftime("%Y%m%d")
            
            # 기관 데이터 수집
            institutional_data = self.data_manager.collect_comprehensive_institutional_data(
                symbol, start_date, end_date
            )
            
            if institutional_data.empty:
                self.logger.warning(f"기관 데이터 없음: {symbol}")
                return []
            
            # 기준선 계산 (분석 기간 이전 데이터)
            baseline_data = institutional_data.iloc[:-self.analysis_period] if len(institutional_data) > self.analysis_period else institutional_data.iloc[:len(institutional_data)//2]
            analysis_data = institutional_data.iloc[-self.analysis_period:] if len(institutional_data) > self.analysis_period else institutional_data
            
            # 기준선 통계 계산
            baseline_stats = self._calculate_baseline_stats(baseline_data)
            
            # 이상 거래 감지
            anomalies = []
            
            for idx, row in analysis_data.iterrows():
                daily_anomalies = self._detect_daily_anomalies(
                    row, baseline_stats, symbol
                )
                anomalies.extend(daily_anomalies)
            
            # 중요도 순 정렬
            anomalies.sort(key=lambda x: x['severity_score'], reverse=True)
            
            self.logger.info(f"대량 거래 이상 감지 완료: {len(anomalies)}개 발견")
            return anomalies
            
        except Exception as e:
            self.logger.error(f"대량 거래 이상 감지 오류: {str(e)}")
            return []
    
    def _calculate_baseline_stats(self, baseline_data: pd.DataFrame) -> Dict[str, Any]:
        """기준선 통계 계산"""
        try:
            stats = {}
            
            # 외국인 매매 기준선
            if 'foreign_value' in baseline_data.columns:
                foreign_values = baseline_data['foreign_value'].fillna(0)
                stats['foreign_mean'] = foreign_values.mean()
                stats['foreign_std'] = foreign_values.std()
                stats['foreign_abs_mean'] = foreign_values.abs().mean()
                stats['foreign_abs_std'] = foreign_values.abs().std()
            
            # 기관 매매 기준선
            institutional_cols = ['institutional_total_value', 'institutional_net_buy_value']
            for col in institutional_cols:
                if col in baseline_data.columns:
                    inst_values = baseline_data[col].fillna(0)
                    stats['institutional_mean'] = inst_values.mean()
                    stats['institutional_std'] = inst_values.std()
                    stats['institutional_abs_mean'] = inst_values.abs().mean()
                    stats['institutional_abs_std'] = inst_values.abs().std()
                    break
            
            # 거래량 기준선 (있는 경우)
            if 'total_volume' in baseline_data.columns:
                volume_values = baseline_data['total_volume'].fillna(0)
                stats['volume_mean'] = volume_values.mean()
                stats['volume_std'] = volume_values.std()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"기준선 통계 계산 오류: {str(e)}")
            return {}
    
    def _detect_daily_anomalies(self, 
                               daily_data: pd.Series, 
                               baseline_stats: Dict[str, Any],
                               symbol: str) -> List[Dict[str, Any]]:
        """일일 이상 거래 감지"""
        try:
            anomalies = []
            current_date = daily_data.get('date', datetime.now())
            
            # 1. 외국인 대량 거래 감지
            if 'foreign_value' in daily_data.index:
                foreign_anomaly = self._detect_foreign_anomaly(
                    daily_data, baseline_stats, symbol, current_date
                )
                if foreign_anomaly:
                    anomalies.append(foreign_anomaly)
            
            # 2. 기관 대량 거래 감지
            institutional_cols = ['institutional_total_value', 'institutional_net_buy_value']
            for col in institutional_cols:
                if col in daily_data.index:
                    institutional_anomaly = self._detect_institutional_anomaly(
                        daily_data, baseline_stats, symbol, current_date, col
                    )
                    if institutional_anomaly:
                        anomalies.append(institutional_anomaly)
                    break
            
            # 3. 복합 이상 거래 감지
            mixed_anomaly = self._detect_mixed_anomaly(
                daily_data, baseline_stats, symbol, current_date
            )
            if mixed_anomaly:
                anomalies.append(mixed_anomaly)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"일일 이상 거래 감지 오류: {str(e)}")
            return []
    
    def _detect_foreign_anomaly(self, 
                              daily_data: pd.Series,
                              baseline_stats: Dict[str, Any],
                              symbol: str,
                              current_date) -> Optional[Dict[str, Any]]:
        """외국인 매매 이상 감지"""
        try:
            foreign_value = daily_data.get('foreign_value', 0)
            
            if abs(foreign_value) < self.amount_threshold:
                return None
            
            # Z-스코어 계산
            foreign_mean = baseline_stats.get('foreign_abs_mean', 0)
            foreign_std = baseline_stats.get('foreign_abs_std', 1)
            
            if foreign_std > 0:
                z_score = abs(abs(foreign_value) - foreign_mean) / foreign_std
            else:
                z_score = 0
            
            # 이상 거래 판단
            if z_score > 2.0:  # 2 시그마 이상
                anomaly_type = AnomalyType.FOREIGN_SURGE
                severity = min(10.0, z_score)
                
                # 호재성 판단
                bullish_signal = self._judge_bullish_nature(
                    foreign_value, 'foreign', daily_data
                )
                
                return {
                    'symbol': symbol,
                    'date': current_date,
                    'anomaly_type': anomaly_type.value,
                    'investor_type': 'FOREIGN',
                    'trade_amount': float(foreign_value),
                    'z_score': float(z_score),
                    'severity_score': float(severity),
                    'is_bullish': bullish_signal['is_bullish'],
                    'bullish_confidence': bullish_signal['confidence'],
                    'description': f"외국인 {'대량 매수' if foreign_value > 0 else '대량 매도'}: {foreign_value:,.0f}억원 (Z-score: {z_score:.2f})",
                    'detected_at': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"외국인 이상 감지 오류: {str(e)}")
            return None
    
    def _detect_institutional_anomaly(self, 
                                    daily_data: pd.Series,
                                    baseline_stats: Dict[str, Any],
                                    symbol: str,
                                    current_date,
                                    col: str) -> Optional[Dict[str, Any]]:
        """기관 매매 이상 감지"""
        try:
            institutional_value = daily_data.get(col, 0)
            
            if abs(institutional_value) < self.amount_threshold:
                return None
            
            # Z-스코어 계산
            inst_mean = baseline_stats.get('institutional_abs_mean', 0)
            inst_std = baseline_stats.get('institutional_abs_std', 1)
            
            if inst_std > 0:
                z_score = abs(abs(institutional_value) - inst_mean) / inst_std
            else:
                z_score = 0
            
            # 이상 거래 판단
            if z_score > 2.0:  # 2 시그마 이상
                anomaly_type = AnomalyType.INSTITUTIONAL_SURGE
                severity = min(10.0, z_score)
                
                # 호재성 판단
                bullish_signal = self._judge_bullish_nature(
                    institutional_value, 'institutional', daily_data
                )
                
                return {
                    'symbol': symbol,
                    'date': current_date,
                    'anomaly_type': anomaly_type.value,
                    'investor_type': 'INSTITUTIONAL',
                    'trade_amount': float(institutional_value),
                    'z_score': float(z_score),
                    'severity_score': float(severity),
                    'is_bullish': bullish_signal['is_bullish'],
                    'bullish_confidence': bullish_signal['confidence'],
                    'description': f"기관 {'대량 매수' if institutional_value > 0 else '대량 매도'}: {institutional_value:,.0f}억원 (Z-score: {z_score:.2f})",
                    'detected_at': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"기관 이상 감지 오류: {str(e)}")
            return None
    
    def _detect_mixed_anomaly(self, 
                            daily_data: pd.Series,
                            baseline_stats: Dict[str, Any],
                            symbol: str,
                            current_date) -> Optional[Dict[str, Any]]:
        """복합 이상 거래 감지"""
        try:
            foreign_value = daily_data.get('foreign_value', 0)
            institutional_value = daily_data.get('institutional_total_value', 
                                                daily_data.get('institutional_net_buy_value', 0))
            
            # 둘 다 대량 거래인 경우만 감지
            if abs(foreign_value) < self.amount_threshold / 2 or abs(institutional_value) < self.amount_threshold / 2:
                return None
            
            # 같은 방향 거래인지 확인
            same_direction = (foreign_value > 0 and institutional_value > 0) or \
                           (foreign_value < 0 and institutional_value < 0)
            
            if same_direction:
                total_amount = foreign_value + institutional_value
                
                # 복합 강도 계산
                foreign_z = self._calculate_z_score(foreign_value, baseline_stats, 'foreign')
                institutional_z = self._calculate_z_score(institutional_value, baseline_stats, 'institutional')
                
                combined_severity = (foreign_z + institutional_z) / 2
                
                if combined_severity > 1.5:  # 낮은 임계값 (복합 효과)
                    anomaly_type = AnomalyType.MIXED_SURGE
                    
                    # 호재성 판단
                    bullish_signal = self._judge_bullish_nature(
                        total_amount, 'mixed', daily_data
                    )
                    
                    return {
                        'symbol': symbol,
                        'date': current_date,
                        'anomaly_type': anomaly_type.value,
                        'investor_type': 'MIXED',
                        'trade_amount': float(total_amount),
                        'foreign_amount': float(foreign_value),
                        'institutional_amount': float(institutional_value),
                        'z_score': float(combined_severity),
                        'severity_score': float(combined_severity * 1.5),  # 복합 보너스
                        'is_bullish': bullish_signal['is_bullish'],
                        'bullish_confidence': bullish_signal['confidence'],
                        'description': f"외국인·기관 동반 {'매수' if total_amount > 0 else '매도'}: {total_amount:,.0f}억원",
                        'detected_at': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"복합 이상 감지 오류: {str(e)}")
            return None
    
    def _calculate_z_score(self, 
                          value: float, 
                          baseline_stats: Dict[str, Any], 
                          investor_type: str) -> float:
        """Z-스코어 계산"""
        try:
            if investor_type == 'foreign':
                mean = baseline_stats.get('foreign_abs_mean', 0)
                std = baseline_stats.get('foreign_abs_std', 1)
            else:
                mean = baseline_stats.get('institutional_abs_mean', 0)
                std = baseline_stats.get('institutional_abs_std', 1)
            
            if std > 0:
                return abs(abs(value) - mean) / std
            else:
                return 0
            
        except Exception:
            return 0
    
    def _judge_bullish_nature(self, 
                            trade_amount: float, 
                            investor_type: str,
                            daily_data: pd.Series) -> Dict[str, Any]:
        """호재성 판단"""
        try:
            # 기본적으로 대량 매수는 호재, 대량 매도는 악재
            is_buying = trade_amount > 0
            base_confidence = 0.7 if is_buying else 0.3
            
            # 추가 신호들로 신뢰도 조정
            confidence_adjustments = []
            
            # 1. 거래량 확인 (있는 경우)
            if 'total_volume' in daily_data.index:
                # 대량 거래와 함께 거래량도 증가했으면 신뢰도 상승
                volume = daily_data.get('total_volume', 0)
                if volume > 0:  # 임계값은 별도 계산 필요
                    confidence_adjustments.append(0.1)
            
            # 2. 투자자 유형별 가중치
            if investor_type == 'foreign':
                # 외국인 매수는 일반적으로 더 신뢰도 높음
                if is_buying:
                    confidence_adjustments.append(0.1)
            elif investor_type == 'mixed':
                # 외국인+기관 동반 매수는 매우 높은 신뢰도
                if is_buying:
                    confidence_adjustments.append(0.2)
            
            # 3. 거래 규모별 가중치
            if abs(trade_amount) > self.amount_threshold * 2:
                confidence_adjustments.append(0.1)  # 매우 대량 거래
            
            # 최종 신뢰도 계산
            final_confidence = base_confidence + sum(confidence_adjustments)
            final_confidence = max(0.1, min(0.95, final_confidence))  # 0.1~0.95 범위
            
            return {
                'is_bullish': is_buying,
                'confidence': float(final_confidence),
                'reasoning': f"{'매수' if is_buying else '매도'} 신호 (신뢰도: {final_confidence:.2f})"
            }
            
        except Exception as e:
            self.logger.error(f"호재성 판단 오류: {str(e)}")
            return {'is_bullish': trade_amount > 0, 'confidence': 0.5, 'reasoning': 'Default'}
    
    def generate_anomaly_report(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """이상 거래 리포트 생성"""
        try:
            if not anomalies:
                return {'total_anomalies': 0, 'report_date': datetime.now().isoformat()}
            
            report = {
                'total_anomalies': len(anomalies),
                'report_date': datetime.now().isoformat()
            }
            
            # 이상 유형별 분류
            type_counts = {}
            investor_type_counts = {}
            bullish_counts = {'bullish': 0, 'bearish': 0}
            severity_distribution = {'high': 0, 'medium': 0, 'low': 0}
            
            total_amount = 0
            max_severity = 0
            
            for anomaly in anomalies:
                # 유형별 카운트
                anomaly_type = anomaly.get('anomaly_type', 'UNKNOWN')
                type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1
                
                # 투자자별 카운트
                investor_type = anomaly.get('investor_type', 'UNKNOWN')
                investor_type_counts[investor_type] = investor_type_counts.get(investor_type, 0) + 1
                
                # 호재/악재 분류
                if anomaly.get('is_bullish', False):
                    bullish_counts['bullish'] += 1
                else:
                    bullish_counts['bearish'] += 1
                
                # 심각도 분류
                severity = anomaly.get('severity_score', 0)
                if severity >= 5.0:
                    severity_distribution['high'] += 1
                elif severity >= 2.0:
                    severity_distribution['medium'] += 1
                else:
                    severity_distribution['low'] += 1
                
                # 통계
                total_amount += abs(anomaly.get('trade_amount', 0))
                max_severity = max(max_severity, severity)
            
            report.update({
                'anomaly_types': type_counts,
                'investor_types': investor_type_counts,
                'bullish_bearish': bullish_counts,
                'severity_distribution': severity_distribution,
                'total_trade_amount': float(total_amount),
                'max_severity_score': float(max_severity),
                'avg_severity_score': float(sum(a.get('severity_score', 0) for a in anomalies) / len(anomalies))
            })
            
            # 상위 이상 거래들
            top_anomalies = sorted(anomalies, key=lambda x: x.get('severity_score', 0), reverse=True)[:5]
            report['top_anomalies'] = [
                {
                    'symbol': a.get('symbol', ''),
                    'type': a.get('anomaly_type', ''),
                    'amount': a.get('trade_amount', 0),
                    'severity': a.get('severity_score', 0),
                    'is_bullish': a.get('is_bullish', False)
                }
                for a in top_anomalies
            ]
            
            return report
            
        except Exception as e:
            self.logger.error(f"이상 거래 리포트 생성 오류: {str(e)}")
            return {'error': str(e), 'report_date': datetime.now().isoformat()}


def main():
    """테스트 실행"""
    print("=== 대량 거래 감지 및 호재성 판단 시스템 테스트 ===")
    
    detector = VolumeAnomalyDetector(
        volume_threshold_multiplier=2.5,
        amount_threshold=500,  # 500억원
        analysis_period=10,
        lookback_period=30
    )
    
    # 테스트용 종목들
    test_symbols = ["005930", "000660", "005490"]
    
    all_anomalies = []
    
    for symbol in test_symbols:
        print(f"\n{symbol} 대량 거래 이상 감지 중...")
        
        anomalies = detector.detect_volume_anomalies(symbol)
        
        if anomalies:
            print(f"   ✅ {len(anomalies)}개 이상 거래 감지")
            
            for anomaly in anomalies[:3]:  # 상위 3개만 출력
                print(f"   🚨 {anomaly['description']}")
                print(f"      심각도: {anomaly['severity_score']:.2f}")
                print(f"      {'🔥 호재' if anomaly['is_bullish'] else '❄️ 악재'} (신뢰도: {anomaly['bullish_confidence']:.2f})")
                print(f"      날짜: {anomaly['date']}")
            
            all_anomalies.extend(anomalies)
        else:
            print(f"   ❌ 이상 거래 없음")
    
    # 종합 리포트 생성
    if all_anomalies:
        print(f"\n=== 종합 이상 거래 리포트 ===")
        report = detector.generate_anomaly_report(all_anomalies)
        
        print(f"총 이상 거래: {report['total_anomalies']}건")
        print(f"총 거래대금: {report['total_trade_amount']:,.0f}억원")
        print(f"최대 심각도: {report['max_severity_score']:.2f}")
        print(f"평균 심각도: {report['avg_severity_score']:.2f}")
        
        print(f"\n호재/악재 분포:")
        bullish_bearish = report['bullish_bearish']
        print(f"  호재: {bullish_bearish['bullish']}건")
        print(f"  악재: {bullish_bearish['bearish']}건")
        
        print(f"\n투자자별 분포:")
        for investor_type, count in report['investor_types'].items():
            print(f"  {investor_type}: {count}건")
        
        print(f"\n상위 이상 거래:")
        for i, anomaly in enumerate(report['top_anomalies'], 1):
            print(f"  {i}. {anomaly['symbol']}: {anomaly['amount']:,.0f}억원 (심각도: {anomaly['severity']:.2f})")
    
    else:
        print(f"\n❌ 전체적으로 이상 거래 없음")
    
    print(f"\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()