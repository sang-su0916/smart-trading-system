"""
매개변수 최적화기 (Grid Search)
백테스팅 결과를 기반으로 최적의 매개변수 조합 탐색
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
import logging
from datetime import datetime
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.backtesting.backtest_engine import BacktestEngine
from src.trading_signals.enhanced_signal_integrator import EnhancedSignalIntegrator

class ParameterOptimizer:
    """매개변수 최적화기 - 그리드 서치 기반"""
    
    def __init__(self, 
                 optimization_metric: str = 'sharpe_ratio',
                 max_workers: Optional[int] = None,
                 verbose: bool = True):
        """
        초기화
        
        Args:
            optimization_metric: 최적화 목표 지표 ('sharpe_ratio', 'total_return', 'win_rate', 'profit_factor')
            max_workers: 병렬 처리 워커 수 (None이면 CPU 코어 수)
            verbose: 상세 로그 출력 여부
        """
        self.optimization_metric = optimization_metric
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        self.verbose = verbose
        self.logger = self._setup_logger()
        
        # 최적화 가능한 지표 목록
        self.available_metrics = {
            'sharpe_ratio': '샤프 비율',
            'total_return': '총 수익률',
            'win_rate': '승률',
            'profit_factor': '손익비',
            'max_drawdown': '최대 낙폭 (최소화)',
            'calmar_ratio': '칼마 비율'
        }
        
        if optimization_metric not in self.available_metrics:
            raise ValueError(f"지원하지 않는 최적화 지표: {optimization_metric}")
        
        self.logger.info(f"매개변수 최적화기 초기화 완료 - 목표: {self.available_metrics[optimization_metric]}")
    
    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO if self.verbose else logging.WARNING)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def optimize_signal_integrator(self, 
                                 symbol: str,
                                 period: str = "2y",
                                 parameter_space: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
        """
        신호 통합기 매개변수 최적화
        
        Args:  
            symbol: 최적화 대상 종목
            period: 백테스팅 기간
            parameter_space: 매개변수 공간 정의
            
        Returns:
            최적화 결과
        """
        try:
            self.logger.info(f"신호 통합기 매개변수 최적화 시작: {symbol}")
            
            # 기본 매개변수 공간 정의
            if parameter_space is None:
                parameter_space = self._get_default_parameter_space()
            
            # 매개변수 조합 생성
            param_combinations = self._generate_parameter_combinations(parameter_space)
            
            self.logger.info(f"총 {len(param_combinations)}개 매개변수 조합 테스트")
            
            # 병렬 최적화 실행
            results = self._run_parallel_optimization(
                symbol, period, param_combinations
            )
            
            if not results:
                raise ValueError("최적화 결과가 없습니다.")
            
            # 결과 분석 및 최적 매개변수 선택
            optimization_result = self._analyze_optimization_results(
                results, parameter_space
            )
            
            self.logger.info(f"매개변수 최적화 완료 - 최적 {self.optimization_metric}: {optimization_result['best_score']:.4f}")
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"매개변수 최적화 오류: {str(e)}")
            return {'error': str(e)}
    
    def _get_default_parameter_space(self) -> Dict[str, List]:
        """기본 매개변수 공간 정의"""
        return {
            # 신뢰도 임계값
            'confidence_threshold': [0.6, 0.65, 0.7, 0.75, 0.8],
            
            # 최소 동의 지표 수
            'min_indicators': [2, 3, 4],
            
            # 기관 신호 가중치
            'institutional_weight': [0.2, 0.25, 0.3, 0.35, 0.4],
            
            # 지표별 가중치 조합 (간소화)
            'ma_weight': [0.15, 0.20, 0.25],
            'rsi_weight': [0.10, 0.15, 0.20],
            'macd_weight': [0.15, 0.20, 0.25],
            'bb_weight': [0.10, 0.15, 0.20],
            'volume_weight': [0.10, 0.15, 0.20],
            'stoch_weight': [0.10, 0.15, 0.20]
        }
    
    def _generate_parameter_combinations(self, parameter_space: Dict[str, List]) -> List[Dict[str, Any]]:
        """매개변수 조합 생성"""
        try:
            # 매개변수 키와 값들 분리
            keys = list(parameter_space.keys())
            values = list(parameter_space.values())
            
            combinations = []
            
            # 전체 조합이 너무 많으면 샘플링
            total_combinations = np.prod([len(v) for v in values])
            
            if total_combinations > 1000:  # 1000개 초과시 샘플링
                self.logger.warning(f"매개변수 조합이 {total_combinations}개로 많음. 랜덤 샘플링 적용")
                
                # 랜덤 샘플링
                np.random.seed(42)  # 재현 가능성을 위한 시드 설정
                
                for _ in range(min(500, total_combinations)):  # 최대 500개 조합
                    combination = {}
                    for key, value_list in parameter_space.items():
                        combination[key] = np.random.choice(value_list)
                    
                    # 가중치 정규화 체크
                    if self._is_valid_weight_combination(combination):
                        combinations.append(combination)
            else:
                # 전체 그리드 서치
                for combination_values in itertools.product(*values):
                    combination = dict(zip(keys, combination_values))
                    
                    # 가중치 정규화 체크
                    if self._is_valid_weight_combination(combination):
                        combinations.append(combination)
            
            self.logger.info(f"유효한 매개변수 조합 생성: {len(combinations)}개")
            return combinations
            
        except Exception as e:
            self.logger.error(f"매개변수 조합 생성 오류: {str(e)}")
            return []
    
    def _is_valid_weight_combination(self, params: Dict[str, Any]) -> bool:
        """가중치 조합 유효성 검사"""
        try:
            # 기술적 지표 가중치들
            technical_weights = [
                params.get('ma_weight', 0.2),
                params.get('rsi_weight', 0.15),
                params.get('macd_weight', 0.2),
                params.get('bb_weight', 0.15),
                params.get('volume_weight', 0.15),
                params.get('stoch_weight', 0.15)
            ]
            
            institutional_weight = params.get('institutional_weight', 0.25)
            
            # 기술적 지표 가중치 합계
            technical_sum = sum(technical_weights)
            
            # 전체 가중치 = 기술적 지표 * (1 - 기관 가중치) + 기관 가중치
            total_weight = technical_sum * (1 - institutional_weight) + institutional_weight
            
            # 0.95 ~ 1.05 범위 허용 (부동소수점 오차 고려)
            return 0.95 <= total_weight <= 1.05
            
        except Exception:
            return False
    
    def _run_parallel_optimization(self, 
                                 symbol: str,
                                 period: str,
                                 param_combinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """병렬 최적화 실행"""
        try:
            results = []
            
            # 배치 크기 설정 (메모리 효율성)
            batch_size = min(50, len(param_combinations))
            
            for i in range(0, len(param_combinations), batch_size):
                batch = param_combinations[i:i+batch_size]
                
                self.logger.info(f"배치 {i//batch_size + 1}/{(len(param_combinations) + batch_size - 1)//batch_size} 처리 중... ({len(batch)}개 조합)")
                
                # 병렬 처리
                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    # 작업 제출
                    future_to_params = {}
                    for params in batch:
                        future = executor.submit(
                            self._evaluate_parameter_combination,
                            symbol, period, params
                        )
                        future_to_params[future] = params
                    
                    # 결과 수집
                    for future in as_completed(future_to_params):
                        params = future_to_params[future]
                        try:
                            result = future.result(timeout=300)  # 5분 타임아웃
                            if result and 'error' not in result:
                                result['parameters'] = params
                                results.append(result)
                        except Exception as e:
                            self.logger.warning(f"매개변수 조합 평가 실패: {str(e)}")
                            continue
                
                # 진행률 출력
                progress = min(100, (i + batch_size) / len(param_combinations) * 100)
                self.logger.info(f"진행률: {progress:.1f}% (완료: {len(results)}개)")
            
            self.logger.info(f"병렬 최적화 완료: {len(results)}개 유효 결과")
            return results
            
        except Exception as e:
            self.logger.error(f"병렬 최적화 실행 오류: {str(e)}")
            return []
    
    def _evaluate_parameter_combination(self, 
                                      symbol: str,
                                      period: str,
                                      params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """개별 매개변수 조합 평가"""
        try:
            # 신호 통합기 생성
            integrator = EnhancedSignalIntegrator(
                confidence_threshold=params.get('confidence_threshold', 0.7),
                min_indicators=params.get('min_indicators', 3),
                use_institutional_signals=True,
                institutional_weight=params.get('institutional_weight', 0.25)
            )
            
            # 지표별 가중치 설정
            technical_weight = 1.0 - params.get('institutional_weight', 0.25)
            
            integrator.indicator_weights = {
                'ma': params.get('ma_weight', 0.2) * technical_weight,
                'rsi': params.get('rsi_weight', 0.15) * technical_weight,
                'macd': params.get('macd_weight', 0.2) * technical_weight,
                'bb': params.get('bb_weight', 0.15) * technical_weight,
                'volume': params.get('volume_weight', 0.15) * technical_weight,
                'stoch': params.get('stoch_weight', 0.15) * technical_weight,
                'institutional': params.get('institutional_weight', 0.25)
            }
            
            # 백테스팅 엔진 초기화
            backtester = BacktestEngine(
                initial_capital=10000000,  # 1000만원
                commission_rate=0.00015,   # 0.015%
                use_risk_management=True
            )
            
            # 백테스팅 실행
            backtest_result = backtester.run_backtest(
                symbol=symbol,
                period=period,
                strategy_type='enhanced_signal_integration',
                signal_integrator=integrator
            )
            
            if 'error' in backtest_result:
                return None
            
            # 성과 지표 추출
            performance = backtest_result.get('performance_metrics', {})
            
            return {
                'optimization_score': performance.get(self.optimization_metric, 0),
                'total_return': performance.get('total_return', 0),
                'sharpe_ratio': performance.get('sharpe_ratio', 0),
                'max_drawdown': performance.get('max_drawdown', 0),
                'win_rate': performance.get('win_rate', 0),
                'profit_factor': performance.get('profit_factor', 1),
                'total_trades': performance.get('total_trades', 0),
                'calmar_ratio': performance.get('calmar_ratio', 0)
            }
            
        except Exception as e:
            # 개별 오류는 조용히 처리 (로그 스팸 방지)
            return None
    
    def _analyze_optimization_results(self, 
                                    results: List[Dict[str, Any]],
                                    parameter_space: Dict[str, List]) -> Dict[str, Any]:
        """최적화 결과 분석"""
        try:
            if not results:
                return {'error': '분석할 결과가 없습니다.'}
            
            # 결과를 DataFrame으로 변환
            df_results = pd.DataFrame(results)
            
            # 최적화 지표별 정렬 (max_drawdown은 최소화)
            ascending = self.optimization_metric == 'max_drawdown'
            df_sorted = df_results.sort_values('optimization_score', ascending=ascending)
            
            # 최적 결과
            best_result = df_sorted.iloc[0] if not ascending else df_sorted.iloc[0]
            best_params = best_result['parameters']
            
            # 상위 결과들 분석
            top_n = min(10, len(df_sorted))
            top_results = df_sorted.head(top_n) if not ascending else df_sorted.head(top_n)
            
            # 매개변수 민감도 분석
            sensitivity_analysis = self._perform_sensitivity_analysis(df_results, parameter_space)
            
            # 결과 통계
            result_stats = {
                'mean_score': df_results['optimization_score'].mean(),
                'std_score': df_results['optimization_score'].std(),
                'median_score': df_results['optimization_score'].median(),
                'min_score': df_results['optimization_score'].min(),
                'max_score': df_results['optimization_score'].max()
            }
            
            return {
                'best_parameters': best_params,
                'best_score': float(best_result['optimization_score']),
                'best_performance': {
                    'total_return': float(best_result['total_return']),
                    'sharpe_ratio': float(best_result['sharpe_ratio']),
                    'max_drawdown': float(best_result['max_drawdown']),
                    'win_rate': float(best_result['win_rate']),
                    'profit_factor': float(best_result['profit_factor']),
                    'total_trades': int(best_result['total_trades']),
                    'calmar_ratio': float(best_result['calmar_ratio'])
                },
                'top_results': top_results.to_dict('records'),
                'sensitivity_analysis': sensitivity_analysis,
                'result_statistics': result_stats,
                'total_combinations_tested': len(results),
                'optimization_metric': self.optimization_metric,
                'optimization_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"최적화 결과 분석 오류: {str(e)}")
            return {'error': str(e)}
    
    def _perform_sensitivity_analysis(self, 
                                    df_results: pd.DataFrame,
                                    parameter_space: Dict[str, List]) -> Dict[str, Any]:
        """매개변수 민감도 분석"""
        try:
            sensitivity = {}
            
            for param_name in parameter_space.keys():
                param_values = []
                scores = []
                
                for _, row in df_results.iterrows():
                    param_values.append(row['parameters'][param_name])
                    scores.append(row['optimization_score'])
                
                # 매개변수 값별 평균 점수
                param_df = pd.DataFrame({
                    'param_value': param_values,
                    'score': scores
                })
                
                param_grouped = param_df.groupby('param_value')['score'].agg(['mean', 'std', 'count'])
                
                # 상관계수
                correlation = param_df['param_value'].corr(param_df['score'])
                
                sensitivity[param_name] = {
                    'correlation': float(correlation) if not pd.isna(correlation) else 0.0,
                    'value_impact': param_grouped.to_dict(),
                    'best_value': float(param_grouped['mean'].idxmax()),
                    'impact_range': float(param_grouped['mean'].max() - param_grouped['mean'].min())
                }
            
            return sensitivity
            
        except Exception as e:
            self.logger.error(f"민감도 분석 오류: {str(e)}")
            return {}
    
    def optimize_multiple_symbols(self, 
                                symbols: List[str],
                                period: str = "2y",
                                parameter_space: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
        """다중 종목 매개변수 최적화"""
        try:
            self.logger.info(f"다중 종목 최적화 시작: {len(symbols)}개 종목")
            
            individual_results = {}
            
            # 각 종목별 개별 최적화
            for i, symbol in enumerate(symbols, 1):
                self.logger.info(f"종목 {i}/{len(symbols)}: {symbol} 최적화 중...")
                
                result = self.optimize_signal_integrator(symbol, period, parameter_space)
                
                if 'error' not in result:
                    individual_results[symbol] = result
                    self.logger.info(f"{symbol} 최적화 완료 - 점수: {result['best_score']:.4f}")
                else:
                    self.logger.warning(f"{symbol} 최적화 실패: {result['error']}")
            
            if not individual_results:
                return {'error': '최적화된 종목이 없습니다.'}
            
            # 종목간 공통 최적 매개변수 도출
            consensus_params = self._derive_consensus_parameters(individual_results)
            
            return {
                'individual_results': individual_results,
                'consensus_parameters': consensus_params,
                'optimized_symbols': list(individual_results.keys()),
                'optimization_summary': self._create_multi_symbol_summary(individual_results)
            }
            
        except Exception as e:
            self.logger.error(f"다중 종목 최적화 오류: {str(e)}")
            return {'error': str(e)}
    
    def _derive_consensus_parameters(self, individual_results: Dict[str, Any]) -> Dict[str, Any]:
        """종목간 공통 최적 매개변수 도출"""
        try:
            all_params = []
            
            for symbol, result in individual_results.items():
                if 'best_parameters' in result:
                    all_params.append(result['best_parameters'])
            
            if not all_params:
                return {}
            
            consensus = {}
            
            # 각 매개변수별 중앙값 또는 최빈값 계산
            for param_name in all_params[0].keys():
                values = [p[param_name] for p in all_params]
                
                if isinstance(values[0], (int, float)):
                    # 수치형: 중앙값 사용
                    consensus[param_name] = float(np.median(values))
                else:
                    # 범주형: 최빈값 사용
                    from collections import Counter
                    counter = Counter(values)
                    consensus[param_name] = counter.most_common(1)[0][0]
            
            return consensus
            
        except Exception as e:
            self.logger.error(f"합의 매개변수 도출 오류: {str(e)}")
            return {}
    
    def _create_multi_symbol_summary(self, individual_results: Dict[str, Any]) -> Dict[str, Any]:
        """다중 종목 최적화 요약"""
        try:
            scores = []
            returns = []
            sharpe_ratios = []
            
            for symbol, result in individual_results.items():
                scores.append(result['best_score'])
                perf = result['best_performance']
                returns.append(perf['total_return'])
                sharpe_ratios.append(perf['sharpe_ratio'])
            
            return {
                'average_optimization_score': float(np.mean(scores)),
                'std_optimization_score': float(np.std(scores)),
                'average_return': float(np.mean(returns)),
                'average_sharpe_ratio': float(np.mean(sharpe_ratios)),
                'best_symbol': max(individual_results.items(), key=lambda x: x[1]['best_score'])[0],
                'worst_symbol': min(individual_results.items(), key=lambda x: x[1]['best_score'])[0],
                'total_symbols_optimized': len(individual_results)
            }
            
        except Exception as e:
            self.logger.error(f"다중 종목 요약 생성 오류: {str(e)}")  
            return {}


# 병렬 처리를 위한 독립 함수들
def _evaluate_single_combination(args):
    """단일 매개변수 조합 평가 (병렬 처리용)"""
    symbol, period, params, optimization_metric = args
    
    try:
        # 여기서 실제 백테스팅 실행
        # (실제 구현에서는 BacktestingEngine 호출)
        
        # 시뮬레이션 결과 반환
        import random
        random.seed(hash(str(params)) % 2147483647)
        
        return {
            'parameters': params,
            'optimization_score': random.uniform(0.5, 2.0),
            'total_return': random.uniform(0.05, 0.30),
            'sharpe_ratio': random.uniform(0.5, 2.0),
            'max_drawdown': random.uniform(0.05, 0.25),
            'win_rate': random.uniform(0.45, 0.65),
            'profit_factor': random.uniform(1.1, 2.5),
            'total_trades': random.randint(50, 200)
        }
        
    except Exception:
        return None


def main():
    """테스트 실행"""
    print("=== 매개변수 최적화기 테스트 ===")
    
    # 최적화기 초기화
    optimizer = ParameterOptimizer(
        optimization_metric='sharpe_ratio',
        max_workers=4,  # 테스트용 제한
        verbose=True
    )
    
    print(f"\n1. 단일 종목 최적화 테스트")
    
    try:
        # 간소화된 매개변수 공간 (테스트용)
        test_param_space = {
            'confidence_threshold': [0.6, 0.7, 0.8],
            'min_indicators': [2, 3],
            'institutional_weight': [0.2, 0.3],
            'ma_weight': [0.15, 0.20],
            'rsi_weight': [0.10, 0.15],
            'macd_weight': [0.15, 0.20],
            'bb_weight': [0.10, 0.15],
            'volume_weight': [0.10, 0.15],
            'stoch_weight': [0.10, 0.15]
        }
        
        print(f"   매개변수 조합 생성 테스트...")
        
        # 매개변수 조합 생성 테스트
        combinations = optimizer._generate_parameter_combinations(test_param_space)
        print(f"   ✅ 유효한 조합 생성: {len(combinations)}개")
        
        # 첫 번째 조합 출력
        if combinations:
            print(f"   예시 조합:")
            for key, value in list(combinations[0].items())[:5]:
                print(f"     {key}: {value}")
        
        # 민감도 분석 시뮬레이션
        print(f"\n2. 민감도 분석 시뮬레이션")
        
        # 가상의 결과 데이터 생성
        import random
        random.seed(42)
        
        simulated_results = []
        for combo in combinations[:20]:  # 처음 20개만 테스트
            result = {
                'parameters': combo,
                'optimization_score': random.uniform(0.8, 1.5),
                'total_return': random.uniform(0.1, 0.25),
                'sharpe_ratio': random.uniform(0.8, 1.5),
                'max_drawdown': random.uniform(0.05, 0.15),
                'win_rate': random.uniform(0.45, 0.65),
                'profit_factor': random.uniform(1.1, 2.5),
                'total_trades': random.randint(50, 200),
                'calmar_ratio': random.uniform(1.0, 3.0)
            }
            simulated_results.append(result)
        
        # 결과 분석
        analysis_result = optimizer._analyze_optimization_results(
            simulated_results, test_param_space
        )
        
        if 'error' not in analysis_result:
            print(f"   ✅ 결과 분석 성공")
            print(f"   최적 점수: {analysis_result['best_score']:.4f}")
            print(f"   테스트된 조합: {analysis_result['total_combinations_tested']}개")
            
            # 최적 매개변수 일부 출력
            best_params = analysis_result['best_parameters']
            print(f"   최적 매개변수 (일부):")
            for key, value in list(best_params.items())[:3]:
                print(f"     {key}: {value}")
            
            # 민감도 분석 결과
            sensitivity = analysis_result['sensitivity_analysis']
            print(f"   민감도 분석: {len(sensitivity)}개 매개변수")
            
            # 가장 영향력 있는 매개변수
            if sensitivity:
                param_impacts = [(k, abs(v.get('correlation', 0))) for k, v in sensitivity.items()]
                param_impacts.sort(key=lambda x: x[1], reverse=True)
                
                print(f"   영향력 순위:")
                for i, (param, impact) in enumerate(param_impacts[:3], 1):
                    print(f"     {i}. {param}: 상관관계 {impact:.3f}")
        else:
            print(f"   ❌ 결과 분석 실패: {analysis_result['error']}")
        
        print(f"\n3. 가중치 유효성 검사 테스트")
        
        # 유효한 조합과 무효한 조합 테스트
        valid_combo = {
            'ma_weight': 0.2, 'rsi_weight': 0.15, 'macd_weight': 0.2,
            'bb_weight': 0.15, 'volume_weight': 0.15, 'stoch_weight': 0.15,
            'institutional_weight': 0.25
        }
        
        invalid_combo = {
            'ma_weight': 0.5, 'rsi_weight': 0.5, 'macd_weight': 0.5,
            'bb_weight': 0.5, 'volume_weight': 0.5, 'stoch_weight': 0.5,
            'institutional_weight': 0.25
        }
        
        print(f"   유효한 조합 테스트: {'✅' if optimizer._is_valid_weight_combination(valid_combo) else '❌'}")
        print(f"   무효한 조합 테스트: {'❌' if not optimizer._is_valid_weight_combination(invalid_combo) else '✅'}")
        
    except Exception as e:
        print(f"   ❌ 테스트 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()