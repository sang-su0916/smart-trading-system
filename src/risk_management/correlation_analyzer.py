"""
상관관계 분석기
포트폴리오 내 종목간 상관관계 분석을 통한 집중 리스크 관리
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import yfinance as yf
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

try:
    from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
    from scipy.spatial.distance import squareform
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

import warnings
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

warnings.filterwarnings('ignore')

class CorrelationAnalyzer:
    """상관관계 분석기"""
    
    def __init__(self):
        """초기화"""
        self.logger = self._setup_logger()
        
        # 리스크 관리 기준
        self.risk_thresholds = {
            'high_correlation': 0.8,      # 높은 상관관계 기준
            'moderate_correlation': 0.6,   # 중간 상관관계 기준
            'cluster_threshold': 0.7,      # 군집 분석 기준
            'max_cluster_weight': 0.4,     # 단일 클러스터 최대 비중
            'diversification_threshold': 0.3  # 분산투자 기준
        }
        
        self.logger.info("상관관계 분석기 초기화 완료")
    
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
    
    def collect_price_data(self, 
                          symbols: List[str],
                          period: str = "1y") -> pd.DataFrame:
        """
        다중 종목 가격 데이터 수집
        
        Args:
            symbols: 종목 리스트
            period: 데이터 수집 기간
            
        Returns:
            가격 데이터 DataFrame (날짜 x 종목)
        """
        try:
            self.logger.info(f"가격 데이터 수집 시작: {len(symbols)}개 종목")
            
            price_data = {}
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period=period)
                    
                    if not data.empty:
                        price_data[symbol] = data['Close']
                        self.logger.debug(f"데이터 수집 완료: {symbol}")
                    else:
                        self.logger.warning(f"데이터 없음: {symbol}")
                        
                except Exception as e:
                    self.logger.warning(f"데이터 수집 실패 {symbol}: {str(e)}")
                    continue
            
            if not price_data:
                self.logger.error("수집된 가격 데이터가 없습니다.")
                return pd.DataFrame()
            
            # DataFrame으로 결합
            combined_data = pd.DataFrame(price_data)
            
            # 결측값 처리 (forward fill 후 backward fill)
            combined_data = combined_data.fillna(method='ffill').fillna(method='bfill')
            
            self.logger.info(f"가격 데이터 수집 완료: {len(combined_data.columns)}개 종목, {len(combined_data)}일")
            return combined_data
            
        except Exception as e:
            self.logger.error(f"가격 데이터 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def calculate_correlation_matrix(self, 
                                   price_data: pd.DataFrame,
                                   method: str = "pearson",
                                   return_period: int = 1) -> pd.DataFrame:
        """
        상관관계 행렬 계산
        
        Args:
            price_data: 가격 데이터
            method: 상관관계 계산 방법 ('pearson', 'spearman', 'kendall')
            return_period: 수익률 계산 기간 (일)
            
        Returns:
            상관관계 행렬
        """
        try:
            if price_data.empty:
                return pd.DataFrame()
            
            # 수익률 계산
            returns = price_data.pct_change(periods=return_period).dropna()
            
            if returns.empty:
                self.logger.warning("수익률 데이터가 없습니다.")
                return pd.DataFrame()
            
            # 상관관계 계산
            correlation_matrix = returns.corr(method=method)
            
            self.logger.info(f"{method} 상관관계 행렬 계산 완료: {correlation_matrix.shape}")
            return correlation_matrix
            
        except Exception as e:
            self.logger.error(f"상관관계 계산 오류: {str(e)}")
            return pd.DataFrame()
    
    def analyze_correlation_risks(self, 
                                correlation_matrix: pd.DataFrame,
                                portfolio_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        상관관계 리스크 분석
        
        Args:
            correlation_matrix: 상관관계 행렬
            portfolio_weights: 포트폴리오 비중 (None이면 동일 비중 가정)
            
        Returns:
            상관관계 리스크 분석 결과
        """
        try:
            if correlation_matrix.empty:
                return {'error': '상관관계 데이터가 없습니다.'}
            
            symbols = correlation_matrix.columns.tolist()
            n_symbols = len(symbols)
            
            # 기본 포트폴리오 비중 설정
            if portfolio_weights is None:
                portfolio_weights = {symbol: 1.0/n_symbols for symbol in symbols}
            
            # 1. 높은 상관관계 쌍 식별
            high_corr_pairs = self._find_high_correlation_pairs(correlation_matrix)
            
            # 2. 상관관계 클러스터 분석
            clusters = self._perform_correlation_clustering(correlation_matrix)
            
            # 3. 포트폴리오 집중도 분석
            concentration_analysis = self._analyze_portfolio_concentration(
                correlation_matrix, portfolio_weights, clusters
            )
            
            # 4. 분산투자 효과 분석
            diversification_analysis = self._analyze_diversification_benefit(
                correlation_matrix, portfolio_weights
            )
            
            # 5. 리스크 경고 생성
            risk_warnings = self._generate_risk_warnings(
                high_corr_pairs, clusters, concentration_analysis, portfolio_weights
            )
            
            return {
                'high_correlation_pairs': high_corr_pairs,
                'correlation_clusters': clusters,
                'concentration_analysis': concentration_analysis,
                'diversification_analysis': diversification_analysis,
                'risk_warnings': risk_warnings,
                'portfolio_weights': portfolio_weights,
                'analysis_date': datetime.now().isoformat(),
                'total_symbols': n_symbols
            }
            
        except Exception as e:
            self.logger.error(f"상관관계 리스크 분석 오류: {str(e)}")
            return {'error': str(e)}
    
    def _find_high_correlation_pairs(self, correlation_matrix: pd.DataFrame) -> List[Dict[str, Any]]:
        """높은 상관관계 종목 쌍 찾기"""
        try:
            high_corr_pairs = []
            symbols = correlation_matrix.columns.tolist()
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols[i+1:], i+1):
                    correlation = correlation_matrix.loc[symbol1, symbol2]
                    
                    if abs(correlation) >= self.risk_thresholds['high_correlation']:
                        high_corr_pairs.append({
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'correlation': float(correlation),
                            'correlation_type': 'positive' if correlation > 0 else 'negative',
                            'risk_level': 'high' if abs(correlation) >= 0.9 else 'moderate'
                        })
            
            # 상관관계 크기별 정렬
            high_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            return high_corr_pairs
            
        except Exception as e:
            self.logger.error(f"높은 상관관계 쌍 찾기 오류: {str(e)}")
            return []
    
    def _perform_correlation_clustering(self, correlation_matrix: pd.DataFrame) -> Dict[str, Any]:
        """상관관계 기반 클러스터링"""
        try:
            if not SCIPY_AVAILABLE:
                # scipy가 없는 경우 간단한 상관관계 기반 그룹핑
                return self._simple_correlation_grouping(correlation_matrix)
            
            # 거리 행렬 계산 (1 - |correlation|)
            distance_matrix = 1 - correlation_matrix.abs()
            
            # 계층적 클러스터링
            linkage_matrix = linkage(squareform(distance_matrix), method='ward')
            
            # 클러스터 할당 (임계값 기반)
            threshold = 1 - self.risk_thresholds['cluster_threshold']
            cluster_labels = fcluster(linkage_matrix, threshold, criterion='distance')
            
            # 클러스터 정보 정리
            clusters = {}
            symbols = correlation_matrix.columns.tolist()
            
            for i, symbol in enumerate(symbols):
                cluster_id = cluster_labels[i]
                if cluster_id not in clusters:
                    clusters[cluster_id] = {
                        'symbols': [],
                        'avg_correlation': 0.0,
                        'size': 0
                    }
                clusters[cluster_id]['symbols'].append(symbol)
                clusters[cluster_id]['size'] += 1
            
            # 클러스터별 평균 상관관계 계산
            for cluster_id, cluster_info in clusters.items():
                cluster_symbols = cluster_info['symbols']
                if len(cluster_symbols) > 1:
                    cluster_corr = correlation_matrix.loc[cluster_symbols, cluster_symbols]
                    # 대각선 제외한 상관관계 평균
                    mask = np.triu(np.ones_like(cluster_corr, dtype=bool), k=1)
                    avg_corr = cluster_corr.where(mask).stack().mean()
                    clusters[cluster_id]['avg_correlation'] = float(avg_corr)
            
            return {
                'clusters': clusters,
                'linkage_matrix': linkage_matrix.tolist(),
                'total_clusters': len(clusters),
                'largest_cluster_size': max([c['size'] for c in clusters.values()]) if clusters else 0
            }
            
        except Exception as e:
            self.logger.error(f"클러스터링 오류: {str(e)}")
            return {}
    
    def _simple_correlation_grouping(self, correlation_matrix: pd.DataFrame) -> Dict[str, Any]:
        """간단한 상관관계 기반 그룹핑 (scipy 없을 때)"""
        try:
            symbols = correlation_matrix.columns.tolist()
            clusters = {}
            cluster_id = 1
            processed = set()
            
            for symbol in symbols:
                if symbol in processed:
                    continue
                    
                # 새 클러스터 시작
                cluster = [symbol]
                processed.add(symbol)
                
                # 높은 상관관계 종목들 찾기
                for other_symbol in symbols:
                    if other_symbol not in processed:
                        correlation = abs(correlation_matrix.loc[symbol, other_symbol])
                        if correlation >= self.risk_thresholds['cluster_threshold']:
                            cluster.append(other_symbol)
                            processed.add(other_symbol)
                
                # 클러스터 정보 저장
                clusters[cluster_id] = {
                    'symbols': cluster,
                    'avg_correlation': 0.0,
                    'size': len(cluster)
                }
                
                # 평균 상관관계 계산
                if len(cluster) > 1:
                    corr_sum = 0
                    count = 0
                    for i, sym1 in enumerate(cluster):
                        for sym2 in cluster[i+1:]:
                            corr_sum += abs(correlation_matrix.loc[sym1, sym2])
                            count += 1
                    clusters[cluster_id]['avg_correlation'] = float(corr_sum / count) if count > 0 else 0.0
                
                cluster_id += 1
            
            return {
                'clusters': clusters,
                'linkage_matrix': [],
                'total_clusters': len(clusters),
                'largest_cluster_size': max([c['size'] for c in clusters.values()]) if clusters else 0
            }
            
        except Exception as e:
            self.logger.error(f"간단한 그룹핑 오류: {str(e)}")
            return {}
    
    def _analyze_portfolio_concentration(self, 
                                       correlation_matrix: pd.DataFrame,
                                       portfolio_weights: Dict[str, float],
                                       clusters: Dict[str, Any]) -> Dict[str, Any]:
        """포트폴리오 집중도 분석"""
        try:
            symbols = correlation_matrix.columns.tolist()
            
            # 1. 개별 종목 집중도
            max_weight = max(portfolio_weights.values()) if portfolio_weights else 0
            max_weight_symbol = max(portfolio_weights.items(), key=lambda x: x[1])[0] if portfolio_weights else None
            
            # 2. 클러스터별 집중도
            cluster_weights = {}
            if clusters.get('clusters'):
                for cluster_id, cluster_info in clusters['clusters'].items():
                    cluster_weight = sum(
                        portfolio_weights.get(symbol, 0) 
                        for symbol in cluster_info['symbols']
                    )
                    cluster_weights[cluster_id] = {
                        'weight': cluster_weight,
                        'symbols': cluster_info['symbols'],
                        'avg_correlation': cluster_info['avg_correlation']
                    }
            
            # 3. 집중 리스크 평가
            concentration_risk = 'low'
            if max_weight > 0.3:
                concentration_risk = 'high'
            elif max_weight > 0.2:
                concentration_risk = 'medium'
            
            # 클러스터 집중도 체크
            max_cluster_weight = max([cw['weight'] for cw in cluster_weights.values()]) if cluster_weights else 0
            if max_cluster_weight > self.risk_thresholds['max_cluster_weight']:
                concentration_risk = 'high'
            
            return {
                'individual_concentration': {
                    'max_weight': float(max_weight),
                    'max_weight_symbol': max_weight_symbol,
                    'concentration_risk': concentration_risk
                },
                'cluster_concentration': cluster_weights,
                'max_cluster_weight': float(max_cluster_weight),
                'concentration_score': self._calculate_concentration_score(portfolio_weights)
            }
            
        except Exception as e:
            self.logger.error(f"집중도 분석 오류: {str(e)}")
            return {}
    
    def _calculate_concentration_score(self, portfolio_weights: Dict[str, float]) -> float:
        """집중도 점수 계산 (HHI 기반)"""
        try:
            # Herfindahl-Hirschman Index 계산
            weights = list(portfolio_weights.values())
            hhi = sum(w**2 for w in weights)
            
            # 정규화 (0-1 범위, 1이 가장 집중된 상태)
            n = len(weights)
            if n <= 1:
                return 1.0
            
            # 완전 분산시 HHI = 1/n, 완전 집중시 HHI = 1
            normalized_hhi = (hhi - 1/n) / (1 - 1/n)
            
            return float(max(0, min(1, normalized_hhi)))
            
        except Exception:
            return 0.5
    
    def _analyze_diversification_benefit(self, 
                                       correlation_matrix: pd.DataFrame,
                                       portfolio_weights: Dict[str, float]) -> Dict[str, Any]:
        """분산투자 효과 분석"""
        try:
            symbols = correlation_matrix.columns.tolist()
            weights = np.array([portfolio_weights.get(symbol, 0) for symbol in symbols])
            
            # 포트폴리오 평균 상관관계 계산
            weighted_corr_sum = 0
            total_weight_pairs = 0
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    if i != j:
                        correlation = correlation_matrix.loc[symbol1, symbol2]
                        weight_product = weights[i] * weights[j]
                        weighted_corr_sum += correlation * weight_product
                        total_weight_pairs += weight_product
            
            avg_correlation = weighted_corr_sum / total_weight_pairs if total_weight_pairs > 0 else 0
            
            # 분산투자 효과 계산
            # 완전 독립시 분산 = sum(wi^2 * σi^2)
            # 완전 상관시 분산 = (sum(wi * σi))^2
            # 실제 분산 = sum(wi^2 * σi^2) + 2 * sum(wi * wj * σi * σj * ρij)
            
            diversification_ratio = 1 - avg_correlation  # 간단한 근사
            
            # 분산투자 등급
            if diversification_ratio > 0.7:
                diversification_grade = 'excellent'
            elif diversification_ratio > 0.5:
                diversification_grade = 'good'
            elif diversification_ratio > 0.3:
                diversification_grade = 'fair'
            else:
                diversification_grade = 'poor'
            
            return {
                'average_correlation': float(avg_correlation),
                'diversification_ratio': float(diversification_ratio),
                'diversification_grade': diversification_grade,
                'effective_number_of_assets': self._calculate_effective_number_of_assets(weights),
                'diversification_score': float(max(0, min(1, diversification_ratio)))
            }
            
        except Exception as e:
            self.logger.error(f"분산투자 효과 분석 오류: {str(e)}")
            return {}
    
    def _calculate_effective_number_of_assets(self, weights: np.ndarray) -> float:
        """유효한 자산 수 계산"""
        try:
            # Effective Number of Assets = 1 / sum(wi^2)
            return float(1 / np.sum(weights**2)) if np.sum(weights**2) > 0 else 1.0
        except Exception:
            return 1.0
    
    def _generate_risk_warnings(self, 
                              high_corr_pairs: List[Dict],
                              clusters: Dict[str, Any],
                              concentration_analysis: Dict[str, Any],
                              portfolio_weights: Dict[str, float]) -> List[str]:
        """리스크 경고 생성"""
        try:
            warnings = []
            
            # 1. 높은 상관관계 경고
            critical_pairs = [pair for pair in high_corr_pairs if abs(pair['correlation']) > 0.9]
            if critical_pairs:
                warnings.append(f"극도로 높은 상관관계 감지: {len(critical_pairs)}개 종목 쌍")
                for pair in critical_pairs[:3]:  # 상위 3개만
                    warnings.append(f"  • {pair['symbol1']} ↔ {pair['symbol2']}: {pair['correlation']:.3f}")
            
            # 2. 개별 종목 집중도 경고
            conc = concentration_analysis.get('individual_concentration', {})
            if conc.get('concentration_risk') == 'high':
                max_symbol = conc.get('max_weight_symbol')
                max_weight = conc.get('max_weight', 0)
                warnings.append(f"개별 종목 집중도 위험: {max_symbol} {max_weight:.1%}")
            
            # 3. 클러스터 집중도 경고  
            max_cluster_weight = concentration_analysis.get('max_cluster_weight', 0)
            if max_cluster_weight > self.risk_thresholds['max_cluster_weight']:
                warnings.append(f"클러스터 집중도 위험: 단일 클러스터 비중 {max_cluster_weight:.1%}")
            
            # 4. 분산투자 부족 경고
            if len(portfolio_weights) < 5:
                warnings.append("종목 수 부족: 최소 5개 이상 종목 보유 권장")
            
            # 5. 전체 집중도 점수 경고
            conc_score = concentration_analysis.get('concentration_score', 0)
            if conc_score > 0.7:
                warnings.append(f"전체 포트폴리오 집중도 높음: {conc_score:.2f}")
            
            return warnings
            
        except Exception as e:
            self.logger.error(f"리스크 경고 생성 오류: {str(e)}")
            return ["리스크 경고 생성 중 오류 발생"]
    
    def generate_optimization_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """포트폴리오 최적화 권장사항 생성"""
        try:
            recommendations = []
            
            if 'error' in analysis_result:
                return ["분석 결과 부족으로 권장사항 생성 불가"]
            
            # 1. 높은 상관관계 개선
            high_corr_pairs = analysis_result.get('high_correlation_pairs', [])
            if high_corr_pairs:
                recommendations.append("높은 상관관계 종목 비중 조정:")
                for pair in high_corr_pairs[:3]:
                    recommendations.append(f"  • {pair['symbol1']} 또는 {pair['symbol2']} 중 하나 매도 검토")
            
            # 2. 클러스터 기반 조정
            clusters = analysis_result.get('correlation_clusters', {}).get('clusters', {})
            large_clusters = {k: v for k, v in clusters.items() if v['size'] > 2}
            
            if large_clusters:
                recommendations.append("클러스터 분산 개선:")
                for cluster_id, cluster_info in large_clusters.items():
                    if cluster_info['avg_correlation'] > 0.7:
                        symbols_str = ', '.join(cluster_info['symbols'][:3])
                        recommendations.append(f"  • 클러스터 {cluster_id} ({symbols_str}) 일부 매도")
            
            # 3. 분산투자 개선
            div_analysis = analysis_result.get('diversification_analysis', {})
            if div_analysis.get('diversification_grade') in ['poor', 'fair']:
                recommendations.append("분산투자 개선 방안:")
                recommendations.append("  • 다른 섹터/테마 종목 추가")
                recommendations.append("  • 상관관계 낮은 종목 발굴")
                
                avg_corr = div_analysis.get('average_correlation', 0)
                if avg_corr > 0.6:
                    recommendations.append("  • 평균 상관관계가 높음 - 독립적 종목 필요")
            
            # 4. 개별 종목 비중 조정
            conc_analysis = analysis_result.get('concentration_analysis', {})
            individual_conc = conc_analysis.get('individual_concentration', {})
            
            if individual_conc.get('concentration_risk') == 'high':
                max_symbol = individual_conc.get('max_weight_symbol')
                recommendations.append(f"개별 종목 비중 조정: {max_symbol} 비중 축소")
            
            # 5. 포트폴리오 규모 조정
            total_symbols = analysis_result.get('total_symbols', 0)
            if total_symbols < 8:
                recommendations.append("포트폴리오 종목 수 확대 (8-15개 권장)")
            elif total_symbols > 20:
                recommendations.append("포트폴리오 종목 수 축소 (관리 효율성 고려)")
            
            # 6. 정기적 리밸런싱
            recommendations.append("정기적 상관관계 모니터링 및 리밸런싱 (월 1회)")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"최적화 권장사항 생성 오류: {str(e)}")
            return ["권장사항 생성 중 오류 발생"]
    
    def create_correlation_heatmap(self, 
                                 correlation_matrix: pd.DataFrame,
                                 save_path: Optional[str] = None) -> bool:
        """상관관계 히트맵 생성"""
        try:
            if not VISUALIZATION_AVAILABLE:
                self.logger.warning("시각화 라이브러리가 없어 히트맵 생성 불가")
                return False
                
            if correlation_matrix.empty:
                return False
            
            plt.figure(figsize=(12, 10))
            
            # 히트맵 생성
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
            sns.heatmap(
                correlation_matrix, 
                mask=mask,
                annot=True, 
                cmap='RdYlBu_r', 
                center=0,
                square=True,
                fmt='.2f',
                cbar_kws={"shrink": .8}
            )
            
            plt.title('포트폴리오 상관관계 행렬', fontsize=16, pad=20)
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"히트맵 저장: {save_path}")
            
            plt.close()
            return True
            
        except Exception as e:
            self.logger.error(f"히트맵 생성 오류: {str(e)}")
            return False


def main():
    """테스트 실행"""
    print("=== 상관관계 분석기 테스트 ===")
    
    analyzer = CorrelationAnalyzer()
    
    # 테스트용 종목 (한국 대형주)
    test_symbols = [
        "005930.KS",  # 삼성전자
        "000660.KS",  # SK하이닉스  
        "005490.KS",  # POSCO홀딩스
        "035420.KS",  # NAVER
        "051910.KS",  # LG화학
        "006400.KS",  # 삼성SDI
        "035720.KS",  # 카카오
        "207940.KS"   # 삼성바이오로직스
    ]
    
    print(f"\n1. 가격 데이터 수집 테스트")
    
    try:
        # 가격 데이터 수집
        price_data = analyzer.collect_price_data(test_symbols, period="6mo")
        
        if not price_data.empty:
            print(f"   ✅ 가격 데이터 수집 성공: {len(price_data.columns)}개 종목, {len(price_data)}일")
            print(f"   수집된 종목: {', '.join(price_data.columns.tolist())}")
        else:
            print("   ❌ 가격 데이터 수집 실패")
            return
            
    except Exception as e:
        print(f"   ❌ 데이터 수집 오류: {str(e)}")
        return
    
    print(f"\n2. 상관관계 행렬 계산 테스트")
    
    try:
        # 상관관계 계산
        correlation_matrix = analyzer.calculate_correlation_matrix(price_data)
        
        if not correlation_matrix.empty:
            print(f"   ✅ 상관관계 계산 완료: {correlation_matrix.shape}")
            
            # 최고/최저 상관관계 출력
            corr_values = []
            symbols = correlation_matrix.columns.tolist()
            
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols[i+1:], i+1):
                    corr_values.append((sym1, sym2, correlation_matrix.loc[sym1, sym2]))
            
            corr_values.sort(key=lambda x: abs(x[2]), reverse=True)
            
            print(f"   최고 상관관계:")
            for i, (s1, s2, corr) in enumerate(corr_values[:3], 1):
                print(f"     {i}. {s1} ↔ {s2}: {corr:.3f}")
        else:
            print("   ❌ 상관관계 계산 실패")
            return
            
    except Exception as e:
        print(f"   ❌ 상관관계 계산 오류: {str(e)}")
        return
    
    print(f"\n3. 상관관계 리스크 분석 테스트")
    
    try:
        # 동일 비중 포트폴리오 가정
        portfolio_weights = {symbol: 1.0/len(test_symbols) for symbol in price_data.columns}
        
        # 리스크 분석
        risk_analysis = analyzer.analyze_correlation_risks(correlation_matrix, portfolio_weights)
        
        if 'error' not in risk_analysis:
            print(f"   ✅ 리스크 분석 완료")
            
            # 높은 상관관계 쌍
            high_corr = risk_analysis.get('high_correlation_pairs', [])
            print(f"   높은 상관관계 쌍: {len(high_corr)}개")
            
            for pair in high_corr[:3]:
                print(f"     • {pair['symbol1']} ↔ {pair['symbol2']}: {pair['correlation']:.3f}")
            
            # 클러스터 정보
            clusters = risk_analysis.get('correlation_clusters', {})
            total_clusters = clusters.get('total_clusters', 0)
            largest_cluster = clusters.get('largest_cluster_size', 0)
            print(f"   상관관계 클러스터: {total_clusters}개 (최대 크기: {largest_cluster})")
            
            # 집중도 분석
            conc_analysis = risk_analysis.get('concentration_analysis', {})
            individual_conc = conc_analysis.get('individual_concentration', {})
            max_weight = individual_conc.get('max_weight', 0)
            conc_score = conc_analysis.get('concentration_score', 0)
            
            print(f"   개별 종목 최대 비중: {max_weight:.1%}")
            print(f"   집중도 점수: {conc_score:.2f}")
            
            # 분산투자 효과
            div_analysis = risk_analysis.get('diversification_analysis', {})
            avg_corr = div_analysis.get('average_correlation', 0)
            div_grade = div_analysis.get('diversification_grade', 'unknown')
            effective_assets = div_analysis.get('effective_number_of_assets', 0)
            
            print(f"   평균 상관관계: {avg_corr:.3f}")
            print(f"   분산투자 등급: {div_grade}")
            print(f"   유효 자산 수: {effective_assets:.1f}")
            
            # 리스크 경고
            warnings = risk_analysis.get('risk_warnings', [])
            print(f"   리스크 경고: {len(warnings)}개")
            for warning in warnings[:3]:
                print(f"     • {warning}")
        else:
            print(f"   ❌ 리스크 분석 실패: {risk_analysis['error']}")
            
    except Exception as e:
        print(f"   ❌ 리스크 분석 오류: {str(e)}")
    
    print(f"\n4. 최적화 권장사항 테스트")
    
    try:
        if 'error' not in risk_analysis:
            recommendations = analyzer.generate_optimization_recommendations(risk_analysis)
            
            print(f"   ✅ 권장사항 생성 완료: {len(recommendations)}개")
            
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"   {i}. {rec}")
        
    except Exception as e:
        print(f"   ❌ 권장사항 생성 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()