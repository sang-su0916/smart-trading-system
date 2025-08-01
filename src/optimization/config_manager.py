"""
최적화된 설정 관리자
매개변수 최적화 결과를 저장하고 관리하는 시스템
"""
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys

# 상위 디렉토리 경로 추가  
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class ConfigManager:
    """최적화된 설정 관리자"""
    
    def __init__(self, config_dir: str = "config/optimized"):
        """
        초기화
        
        Args:
            config_dir: 설정 파일 저장 디렉토리
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logger()
        
        # 설정 파일 경로들
        self.global_config_path = self.config_dir / "global_optimized_config.json"
        self.symbol_configs_dir = self.config_dir / "symbol_specific"
        self.symbol_configs_dir.mkdir(exist_ok=True)
        
        # 기본 설정 로드
        self.global_config = self._load_global_config()
        
        self.logger.info(f"설정 관리자 초기화 완료 - 디렉토리: {self.config_dir}")
    
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
    
    def save_optimization_result(self, 
                                symbol: str,
                                optimization_result: Dict[str, Any],
                                overwrite: bool = True) -> bool:
        """
        최적화 결과 저장
        
        Args:
            symbol: 종목 코드
            optimization_result: 최적화 결과
            overwrite: 기존 결과 덮어쓰기 여부
            
        Returns:
            저장 성공 여부
        """
        try:
            # 종목별 설정 파일 경로
            symbol_config_path = self.symbol_configs_dir / f"{symbol}_config.json"
            
            # 기존 파일 존재 체크
            if symbol_config_path.exists() and not overwrite:
                self.logger.warning(f"설정 파일이 이미 존재합니다: {symbol}")
                return False
            
            # 저장할 데이터 구성
            config_data = {
                'symbol': symbol,
                'optimization_date': optimization_result.get('optimization_date', datetime.now().isoformat()),
                'optimization_metric': optimization_result.get('optimization_metric', 'sharpe_ratio'),
                'best_parameters': optimization_result.get('best_parameters', {}),
                'best_performance': optimization_result.get('best_performance', {}),
                'result_statistics': optimization_result.get('result_statistics', {}),
                'total_combinations_tested': optimization_result.get('total_combinations_tested', 0),
                'sensitivity_analysis': optimization_result.get('sensitivity_analysis', {}),
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'config_version': '1.0'
                }
            }
            
            # JSON 파일로 저장
            with open(symbol_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"최적화 결과 저장 완료: {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"최적화 결과 저장 오류 ({symbol}): {str(e)}")  
            return False
    
    def load_symbol_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        종목별 최적화된 설정 로드
        
        Args:
            symbol: 종목 코드
            
        Returns:
            최적화된 설정 딕셔너리
        """
        try:
            symbol_config_path = self.symbol_configs_dir / f"{symbol}_config.json"
            
            if not symbol_config_path.exists():
                self.logger.warning(f"종목 설정 파일이 없습니다: {symbol}")
                return None
            
            with open(symbol_config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 설정 유효성 검사
            if self._validate_config(config_data):
                return config_data
            else:
                self.logger.warning(f"유효하지 않은 설정 파일: {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"종목 설정 로드 오류 ({symbol}): {str(e)}")
            return None
    
    def get_optimized_parameters(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        종목의 최적화된 매개변수만 반환
        
        Args:
            symbol: 종목 코드
            
        Returns:
            최적화된 매개변수 딕셔너리
        """
        config = self.load_symbol_config(symbol)
        if config:
            return config.get('best_parameters')
        return None
    
    def save_global_config(self, config_data: Dict[str, Any]) -> bool:
        """
        전역 설정 저장
        
        Args:
            config_data: 전역 설정 데이터
            
        Returns:
            저장 성공 여부
        """
        try:
            global_data = {
                'last_updated': datetime.now().isoformat(),
                'config_version': '1.0',
                **config_data
            }
            
            with open(self.global_config_path, 'w', encoding='utf-8') as f:
                json.dump(global_data, f, indent=2, ensure_ascii=False)
            
            # 메모리의 전역 설정도 업데이트
            self.global_config = global_data
            
            self.logger.info("전역 설정 저장 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"전역 설정 저장 오류: {str(e)}")
            return False
    
    def _load_global_config(self) -> Dict[str, Any]:
        """전역 설정 로드"""
        try:
            if self.global_config_path.exists():
                with open(self.global_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 전역 설정
                default_config = {
                    'created_at': datetime.now().isoformat(),
                    'config_version': '1.0',
                    'default_optimization_metric': 'sharpe_ratio',
                    'default_backtest_period': '2y',
                    'max_optimization_workers': 8
                }
                
                # 기본 설정 저장
                self.save_global_config(default_config)
                return default_config
                
        except Exception as e:
            self.logger.error(f"전역 설정 로드 오류: {str(e)}")
            return {}
    
    def _validate_config(self, config_data: Dict[str, Any]) -> bool:
        """설정 데이터 유효성 검사"""
        try:
            required_keys = ['symbol', 'best_parameters', 'optimization_date']
            
            for key in required_keys:
                if key not in config_data:
                    return False
            
            # 매개변수 유효성 검사
            params = config_data['best_parameters']
            if not isinstance(params, dict) or len(params) == 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def list_optimized_symbols(self) -> List[str]:
        """최적화된 종목 목록 반환"""
        try:
            symbols = []
            
            for config_file in self.symbol_configs_dir.glob("*_config.json"):
                symbol = config_file.stem.replace('_config', '')
                symbols.append(symbol)
            
            return sorted(symbols)
            
        except Exception as e:
            self.logger.error(f"종목 목록 조회 오류: {str(e)}")
            return []
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """전체 최적화 요약 정보"""
        try:
            symbols = self.list_optimized_symbols()
            
            summary = {
                'total_optimized_symbols': len(symbols),
                'optimized_symbols': symbols,
                'summary_generated_at': datetime.now().isoformat()
            }
            
            if symbols:
                # 종목별 성과 수집
                performances = []
                optimization_dates = []
                metrics_used = []
                
                for symbol in symbols:
                    config = self.load_symbol_config(symbol)
                    if config:
                        perf = config.get('best_performance', {})
                        if perf:
                            performances.append(perf)
                        
                        opt_date = config.get('optimization_date')
                        if opt_date:
                            optimization_dates.append(opt_date)
                        
                        metric = config.get('optimization_metric')
                        if metric:
                            metrics_used.append(metric)
                
                # 성과 통계
                if performances:
                    returns = [p.get('total_return', 0) for p in performances]
                    sharpe_ratios = [p.get('sharpe_ratio', 0) for p in performances]
                    win_rates = [p.get('win_rate', 0) for p in performances]
                    
                    summary['performance_statistics'] = {
                        'average_return': float(np.mean(returns)),
                        'median_return': float(np.median(returns)),
                        'std_return': float(np.std(returns)),
                        'average_sharpe_ratio': float(np.mean(sharpe_ratios)),
                        'average_win_rate': float(np.mean(win_rates)),
                        'best_performing_symbol': symbols[np.argmax(returns)],
                        'highest_sharpe_symbol': symbols[np.argmax(sharpe_ratios)]
                    }
                
                # 최적화 메타데이터
                if optimization_dates:
                    summary['optimization_metadata'] = {
                        'latest_optimization': max(optimization_dates),
                        'oldest_optimization': min(optimization_dates),
                        'most_common_metric': max(set(metrics_used), key=metrics_used.count) if metrics_used else 'unknown'
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"최적화 요약 생성 오류: {str(e)}")
            return {'error': str(e)}
    
    def export_configurations(self, output_file: str = None) -> bool:
        """
        모든 설정을 하나의 파일로 내보내기
        
        Args:
            output_file: 출력 파일 경로 (None이면 자동 생성)
            
        Returns:
            내보내기 성공 여부
        """
        try:
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.config_dir / f"all_configurations_{timestamp}.json"
            
            # 모든 설정 수집
            export_data = {
                'export_date': datetime.now().isoformat(),
                'global_config': self.global_config,
                'symbol_configs': {}
            }
            
            symbols = self.list_optimized_symbols()
            for symbol in symbols:
                config = self.load_symbol_config(symbol)
                if config:
                    export_data['symbol_configs'][symbol] = config
            
            # 파일로 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"설정 내보내기 완료: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 내보내기 오류: {str(e)}")
            return False
    
    def import_configurations(self, import_file: str) -> bool:
        """
        설정 파일 가져오기
        
        Args:
            import_file: 가져올 파일 경로
            
        Returns:
            가져오기 성공 여부
        """
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 전역 설정 가져오기
            if 'global_config' in import_data:
                self.save_global_config(import_data['global_config'])
            
            # 종목별 설정 가져오기
            imported_count = 0
            if 'symbol_configs' in import_data:
                for symbol, config in import_data['symbol_configs'].items():
                    # 최적화 결과 형태로 변환
                    optimization_result = {
                        'best_parameters': config.get('best_parameters', {}),
                        'best_performance': config.get('best_performance', {}),
                        'optimization_date': config.get('optimization_date'),
                        'optimization_metric': config.get('optimization_metric', 'sharpe_ratio'),
                        'result_statistics': config.get('result_statistics', {}),
                        'sensitivity_analysis': config.get('sensitivity_analysis', {}),
                        'total_combinations_tested': config.get('total_combinations_tested', 0)
                    }
                    
                    if self.save_optimization_result(symbol, optimization_result, overwrite=True):
                        imported_count += 1
            
            self.logger.info(f"설정 가져오기 완료: {imported_count}개 종목")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 가져오기 오류: {str(e)}")
            return False
    
    def cleanup_old_configs(self, days_old: int = 30) -> int:
        """
        오래된 설정 파일 정리
        
        Args:
            days_old: 정리할 파일의 최소 나이 (일)
            
        Returns:
            정리된 파일 수
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cleaned_count = 0
            
            for config_file in self.symbol_configs_dir.glob("*_config.json"):
                try:
                    # 파일 수정 시간 확인
                    file_mtime = datetime.fromtimestamp(config_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_date:
                        config_file.unlink()  # 파일 삭제
                        cleaned_count += 1
                        self.logger.info(f"오래된 설정 파일 삭제: {config_file.name}")
                        
                except Exception as e:
                    self.logger.warning(f"파일 정리 실패 ({config_file.name}): {str(e)}")
                    continue
            
            self.logger.info(f"설정 파일 정리 완료: {cleaned_count}개 파일 삭제")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"설정 파일 정리 오류: {str(e)}")
            return 0


def main():
    """테스트 실행"""
    print("=== 설정 관리자 테스트 ===")
    
    # 설정 관리자 초기화
    config_manager = ConfigManager(config_dir="test_config")
    
    print(f"\n1. 설정 관리자 초기화 테스트")
    print(f"   ✅ 초기화 완료")
    print(f"   설정 디렉토리: {config_manager.config_dir}")
    
    # 가상의 최적화 결과 생성
    sample_optimization_result = {
        'optimization_date': datetime.now().isoformat(),
        'optimization_metric': 'sharpe_ratio',
        'best_parameters': {
            'confidence_threshold': 0.75,
            'min_indicators': 3,
            'institutional_weight': 0.25,
            'ma_weight': 0.20,
            'rsi_weight': 0.15,
            'macd_weight': 0.20,
            'bb_weight': 0.15,
            'volume_weight': 0.15,
            'stoch_weight': 0.15
        },
        'best_performance': {
            'total_return': 0.23,
            'sharpe_ratio': 1.45,
            'max_drawdown': 0.08,
            'win_rate': 0.62,
            'profit_factor': 1.85,
            'total_trades': 145,
            'calmar_ratio': 2.1
        },
        'result_statistics': {
            'mean_score': 1.25,
            'std_score': 0.15,
            'median_score': 1.28
        },
        'total_combinations_tested': 324,
        'sensitivity_analysis': {
            'confidence_threshold': {
                'correlation': 0.65,
                'best_value': 0.75,
                'impact_range': 0.25
            }
        }
    }
    
    print(f"\n2. 최적화 결과 저장 테스트")
    test_symbols = ['005930', '000660', '005490']
    
    for symbol in test_symbols:
        # 각 종목별로 약간 다른 결과 생성
        import random
        random.seed(hash(symbol))
        
        modified_result = sample_optimization_result.copy()
        modified_result['best_performance'] = sample_optimization_result['best_performance'].copy()
        modified_result['best_performance']['total_return'] *= random.uniform(0.8, 1.2)
        modified_result['best_performance']['sharpe_ratio'] *= random.uniform(0.9, 1.1)
        
        success = config_manager.save_optimization_result(symbol, modified_result)
        print(f"   {symbol}: {'✅' if success else '❌'}")
    
    print(f"\n3. 설정 로드 테스트")
    for symbol in test_symbols:
        config = config_manager.load_symbol_config(symbol)
        if config:
            params = config['best_parameters']
            perf = config['best_performance']
            print(f"   {symbol}: ✅ (샤프비율: {perf['sharpe_ratio']:.2f})")
        else:
            print(f"   {symbol}: ❌")
    
    print(f"\n4. 최적화된 매개변수 조회 테스트")
    params = config_manager.get_optimized_parameters('005930')
    if params:
        print(f"   ✅ 매개변수 조회 성공")
        print(f"   신뢰도 임계값: {params.get('confidence_threshold', 'N/A')}")
        print(f"   최소 지표 수: {params.get('min_indicators', 'N/A')}")
        print(f"   기관 가중치: {params.get('institutional_weight', 'N/A')}")
    else:
        print(f"   ❌ 매개변수 조회 실패")
    
    print(f"\n5. 전체 요약 정보 테스트")
    summary = config_manager.get_optimization_summary()
    
    if 'error' not in summary:
        print(f"   ✅ 요약 생성 성공")
        print(f"   최적화된 종목 수: {summary['total_optimized_symbols']}")
        
        perf_stats = summary.get('performance_statistics', {})
        if perf_stats:
            print(f"   평균 수익률: {perf_stats.get('average_return', 0):.2%}")
            print(f"   평균 샤프비율: {perf_stats.get('average_sharpe_ratio', 0):.2f}")
            print(f"   최고 성과 종목: {perf_stats.get('best_performing_symbol', 'N/A')}")
    else:
        print(f"   ❌ 요약 생성 실패: {summary['error']}")
    
    print(f"\n6. 설정 내보내기/가져오기 테스트")
    
    # 내보내기 테스트
    export_success = config_manager.export_configurations()
    print(f"   내보내기: {'✅' if export_success else '❌'}")
    
    # 종목 목록 테스트
    symbols = config_manager.list_optimized_symbols()
    print(f"   종목 목록: {symbols}")
    
    # 정리 테스트 (0일로 설정하여 모든 파일 정리)
    print(f"\n7. 정리 기능 테스트")
    try:
        # 테스트 파일들을 정리하지 않도록 주석 처리
        # cleaned_count = config_manager.cleanup_old_configs(days_old=0)
        # print(f"   정리된 파일 수: {cleaned_count}개")
        print(f"   정리 기능 테스트 건너뜀 (테스트 파일 보존)")
    except Exception as e:
        print(f"   정리 테스트 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()