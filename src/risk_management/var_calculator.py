"""
VaR(Value at Risk) 계산기
포트폴리오의 잠재적 손실 위험을 정량화하는 시스템
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
from enum import Enum
import yfinance as yf
from scipy import stats
import warnings
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

warnings.filterwarnings('ignore')

class VaRMethod(Enum):
    """VaR 계산 방법"""
    HISTORICAL = "HISTORICAL"           # 역사적 시뮬레이션
    PARAMETRIC = "PARAMETRIC"           # 모수적 방법 (정규분포 가정)
    MONTE_CARLO = "MONTE_CARLO"         # 몬테카를로 시뮬레이션

class RiskLevel(Enum):
    """리스크 수준"""
    LOW = "LOW"                         # 낮음
    MODERATE = "MODERATE"               # 보통
    HIGH = "HIGH"                       # 높음
    EXTREME = "EXTREME"                 # 극도로 높음

class VaRCalculator:
    """VaR 계산기"""
    
    def __init__(self):
        """초기화"""
        self.logger = self._setup_logger()
        
        # VaR 계산 설정
        self.var_config = {
            'confidence_levels': [0.90, 0.95, 0.99],      # 신뢰수준
            'time_horizons': [1, 5, 10],                   # 시간지평 (일)
            'lookback_window': 252,                        # 역사적 데이터 기간 (일)
            'monte_carlo_simulations': 10000,              # 몬테카를로 시뮬레이션 수
            'risk_free_rate': 0.02,                        # 무위험 수익률 (연율)
        }
        
        # 리스크 임계값
        self.risk_thresholds = {
            'low_var_threshold': 0.02,      # 2% 이하: 낮은 리스크
            'moderate_var_threshold': 0.05,  # 5% 이하: 보통 리스크
            'high_var_threshold': 0.10,     # 10% 이하: 높은 리스크
            # 10% 초과: 극도로 높은 리스크
        }
        
        self.logger.info("VaR 계산기 초기화 완료")
    
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
    
    def collect_portfolio_data(self, 
                             portfolio: Dict[str, float],
                             period: str = "2y") -> pd.DataFrame:
        """
        포트폴리오 데이터 수집
        
        Args:
            portfolio: {종목코드: 비중} 딕셔너리
            period: 데이터 수집 기간
            
        Returns:
            포트폴리오 가격 데이터
        """
        try:
            self.logger.info(f"포트폴리오 데이터 수집 시작: {len(portfolio)}개 종목")
            
            symbols = list(portfolio.keys())
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
            
            # 결측값 처리
            combined_data = combined_data.fillna(method='ffill').fillna(method='bfill')
            
            self.logger.info(f"포트폴리오 데이터 수집 완료: {len(combined_data.columns)}개 종목, {len(combined_data)}일")
            return combined_data
            
        except Exception as e:
            self.logger.error(f"포트폴리오 데이터 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def calculate_portfolio_returns(self, 
                                  price_data: pd.DataFrame,
                                  portfolio_weights: Dict[str, float]) -> pd.Series:
        """
        포트폴리오 수익률 계산
        
        Args:
            price_data: 가격 데이터
            portfolio_weights: 포트폴리오 비중
            
        Returns:
            포트폴리오 일간 수익률
        """
        try:
            if price_data.empty:
                return pd.Series()
            
            # 개별 종목 수익률 계산
            returns = price_data.pct_change().dropna()
            
            # 포트폴리오 비중 정규화
            total_weight = sum(portfolio_weights.values())
            normalized_weights = {k: v/total_weight for k, v in portfolio_weights.items()}
            
            # 포트폴리오 수익률 계산
            portfolio_returns = pd.Series(0.0, index=returns.index)
            
            for symbol, weight in normalized_weights.items():
                if symbol in returns.columns:
                    portfolio_returns += returns[symbol] * weight
            
            self.logger.info(f"포트폴리오 수익률 계산 완료: {len(portfolio_returns)}일")
            return portfolio_returns
            
        except Exception as e:
            self.logger.error(f"포트폴리오 수익률 계산 오류: {str(e)}")
            return pd.Series()
    
    def calculate_historical_var(self, 
                               returns: pd.Series,
                               confidence_level: float = 0.95,
                               time_horizon: int = 1) -> Dict[str, float]:
        """
        역사적 VaR 계산
        
        Args:
            returns: 수익률 시계열
            confidence_level: 신뢰수준
            time_horizon: 시간지평 (일)
            
        Returns:
            VaR 계산 결과
        """
        try:
            if returns.empty:
                return {}
            
            # 시간지평 조정된 수익률
            if time_horizon > 1:
                scaled_returns = returns * np.sqrt(time_horizon)
            else:
                scaled_returns = returns
            
            # 백분위수 계산
            alpha = 1 - confidence_level
            var_percentile = np.percentile(scaled_returns, alpha * 100)
            
            # 조건부 VaR (Expected Shortfall) 계산
            cvar = scaled_returns[scaled_returns <= var_percentile].mean()
            
            return {
                'method': 'Historical',
                'var': abs(float(var_percentile)),
                'cvar': abs(float(cvar)),
                'confidence_level': confidence_level,
                'time_horizon': time_horizon,
                'sample_size': len(returns)
            }
            
        except Exception as e:
            self.logger.error(f"역사적 VaR 계산 오류: {str(e)}")
            return {}
    
    def calculate_parametric_var(self, 
                               returns: pd.Series,
                               confidence_level: float = 0.95,
                               time_horizon: int = 1) -> Dict[str, float]:
        """
        모수적 VaR 계산 (정규분포 가정)
        
        Args:
            returns: 수익률 시계열
            confidence_level: 신뢰수준
            time_horizon: 시간지평 (일)
            
        Returns:
            VaR 계산 결과
        """
        try:
            if returns.empty:
                return {}
            
            # 평균과 표준편차 계산
            mean_return = returns.mean()
            std_return = returns.std()
            
            # 시간지평 조정
            if time_horizon > 1:
                mean_return = mean_return * time_horizon
                std_return = std_return * np.sqrt(time_horizon)
            
            # 정규분포 분위수
            alpha = 1 - confidence_level
            z_score = stats.norm.ppf(alpha)
            
            # VaR 계산
            var = -(mean_return + z_score * std_return)
            
            # 조건부 VaR 계산
            phi_z = stats.norm.pdf(z_score)
            cvar = -(mean_return - std_return * phi_z / alpha)
            
            return {
                'method': 'Parametric',
                'var': abs(float(var)),
                'cvar': abs(float(cvar)),
                'confidence_level': confidence_level,
                'time_horizon': time_horizon,
                'mean_return': float(mean_return),
                'volatility': float(std_return)
            }
            
        except Exception as e:
            self.logger.error(f"모수적 VaR 계산 오류: {str(e)}")
            return {}
    
    def calculate_monte_carlo_var(self, 
                                returns: pd.Series,
                                confidence_level: float = 0.95,
                                time_horizon: int = 1,
                                num_simulations: int = 10000) -> Dict[str, float]:
        """
        몬테카를로 VaR 계산
        
        Args:
            returns: 수익률 시계열
            confidence_level: 신뢰수준
            time_horizon: 시간지평 (일)
            num_simulations: 시뮬레이션 수
            
        Returns:
            VaR 계산 결과
        """
        try:
            if returns.empty:
                return {}
            
            # 평균과 표준편차 계산
            mean_return = returns.mean()
            std_return = returns.std()
            
            # 몬테카를로 시뮬레이션
            np.random.seed(42)  # 재현 가능성을 위한 시드 설정
            
            simulated_returns = []
            
            for _ in range(num_simulations):
                # 정규분포에서 랜덤 샘플링
                random_returns = np.random.normal(mean_return, std_return, time_horizon)
                period_return = np.sum(random_returns)
                simulated_returns.append(period_return)
            
            simulated_returns = np.array(simulated_returns)
            
            # VaR 계산
            alpha = 1 - confidence_level
            var_percentile = np.percentile(simulated_returns, alpha * 100)
            
            # 조건부 VaR 계산
            cvar = simulated_returns[simulated_returns <= var_percentile].mean()
            
            return {
                'method': 'Monte Carlo',
                'var': abs(float(var_percentile)),
                'cvar': abs(float(cvar)),
                'confidence_level': confidence_level,
                'time_horizon': time_horizon,
                'num_simulations': num_simulations,
                'mean_simulated': float(np.mean(simulated_returns)),
                'std_simulated': float(np.std(simulated_returns))
            }
            
        except Exception as e:
            self.logger.error(f"몬테카를로 VaR 계산 오류: {str(e)}")
            return {}
    
    def calculate_comprehensive_var(self, 
                                  portfolio: Dict[str, float],
                                  period: str = "2y") -> Dict[str, Any]:
        """
        종합적인 VaR 분석
        
        Args:
            portfolio: 포트폴리오 구성 {종목코드: 비중}
            period: 분석 기간
            
        Returns:
            종합 VaR 분석 결과
        """
        try:
            self.logger.info("종합적인 VaR 분석 시작")
            
            # 포트폴리오 데이터 수집
            price_data = self.collect_portfolio_data(portfolio, period)
            
            if price_data.empty:
                return {'error': '포트폴리오 데이터 수집 실패'}
            
            # 포트폴리오 수익률 계산
            portfolio_returns = self.calculate_portfolio_returns(price_data, portfolio)
            
            if portfolio_returns.empty:
                return {'error': '포트폴리오 수익률 계산 실패'}
            
            # 다양한 방법으로 VaR 계산
            var_results = {}
            
            for confidence_level in self.var_config['confidence_levels']:
                for time_horizon in self.var_config['time_horizons']:
                    key = f"VaR_{int(confidence_level*100)}_{time_horizon}d"
                    
                    var_results[key] = {
                        'historical': self.calculate_historical_var(
                            portfolio_returns, confidence_level, time_horizon
                        ),
                        'parametric': self.calculate_parametric_var(
                            portfolio_returns, confidence_level, time_horizon
                        ),
                        'monte_carlo': self.calculate_monte_carlo_var(
                            portfolio_returns, confidence_level, time_horizon,
                            self.var_config['monte_carlo_simulations']
                        )
                    }
            
            # 포트폴리오 기본 통계
            portfolio_stats = self._calculate_portfolio_statistics(portfolio_returns)
            
            # 리스크 등급 평가
            risk_assessment = self._assess_risk_level(var_results)
            
            # 백테스팅 결과
            backtesting_results = self._backtest_var_models(portfolio_returns, var_results)
            
            return {
                'portfolio': portfolio,
                'portfolio_statistics': portfolio_stats,
                'var_results': var_results,
                'risk_assessment': risk_assessment,
                'backtesting_results': backtesting_results,
                'analysis_date': datetime.now().isoformat(),
                'data_period': period,
                'total_observations': len(portfolio_returns)
            }
            
        except Exception as e:
            self.logger.error(f"종합적인 VaR 분석 오류: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_portfolio_statistics(self, returns: pd.Series) -> Dict[str, float]:
        """포트폴리오 기본 통계 계산"""
        try:
            if returns.empty:
                return {}
            
            return {
                'mean_daily_return': float(returns.mean()),
                'daily_volatility': float(returns.std()),
                'annualized_return': float(returns.mean() * 252),
                'annualized_volatility': float(returns.std() * np.sqrt(252)),
                'sharpe_ratio': float((returns.mean() * 252) / (returns.std() * np.sqrt(252))),
                'skewness': float(returns.skew()),
                'kurtosis': float(returns.kurtosis()),
                'min_return': float(returns.min()),
                'max_return': float(returns.max()),
                'positive_days_ratio': float((returns > 0).mean())
            }
            
        except Exception as e:
            self.logger.error(f"포트폴리오 통계 계산 오류: {str(e)}")
            return {}
    
    def _assess_risk_level(self, var_results: Dict[str, Any]) -> Dict[str, Any]:
        """리스크 수준 평가"""
        try:
            # VaR 95%, 1일 기준으로 리스크 평가
            base_key = "VaR_95_1d"
            
            if base_key not in var_results:
                return {'risk_level': 'UNKNOWN', 'reason': 'VaR 계산 결과 없음'}
            
            historical_var = var_results[base_key]['historical'].get('var', 0)
            parametric_var = var_results[base_key]['parametric'].get('var', 0)
            monte_carlo_var = var_results[base_key]['monte_carlo'].get('var', 0)
            
            # 평균 VaR 계산
            avg_var = np.mean([historical_var, parametric_var, monte_carlo_var])
            
            # 리스크 수준 결정
            if avg_var <= self.risk_thresholds['low_var_threshold']:
                risk_level = RiskLevel.LOW
                risk_message = f"낮은 리스크 (VaR: {avg_var:.2%})"
            elif avg_var <= self.risk_thresholds['moderate_var_threshold']:
                risk_level = RiskLevel.MODERATE
                risk_message = f"보통 리스크 (VaR: {avg_var:.2%})"
            elif avg_var <= self.risk_thresholds['high_var_threshold']:
                risk_level = RiskLevel.HIGH
                risk_message = f"높은 리스크 (VaR: {avg_var:.2%})"
            else:
                risk_level = RiskLevel.EXTREME
                risk_message = f"극도로 높은 리스크 (VaR: {avg_var:.2%})"
            
            return {
                'risk_level': risk_level.value,
                'average_var_95_1d': float(avg_var),
                'historical_var': float(historical_var),
                'parametric_var': float(parametric_var),
                'monte_carlo_var': float(monte_carlo_var),
                'risk_message': risk_message,
                'assessment_criteria': self.risk_thresholds
            }
            
        except Exception as e:
            self.logger.error(f"리스크 수준 평가 오류: {str(e)}")
            return {'risk_level': 'ERROR', 'reason': str(e)}
    
    def _backtest_var_models(self, returns: pd.Series, var_results: Dict[str, Any]) -> Dict[str, Any]:
        """VaR 모델 백테스팅"""
        try:
            if returns.empty:
                return {}
            
            # VaR 95%, 1일 기준으로 백테스팅
            base_key = "VaR_95_1d"
            
            if base_key not in var_results:
                return {'error': 'VaR 결과 없음'}
            
            backtesting_results = {}
            
            for method in ['historical', 'parametric', 'monte_carlo']:
                var_value = var_results[base_key][method].get('var', 0)
                
                if var_value > 0:
                    # VaR 위반 횟수 계산 (실제 손실이 VaR보다 큰 경우)
                    violations = (returns < -var_value).sum()
                    total_observations = len(returns)
                    violation_rate = violations / total_observations
                    
                    # 예상 위반율 (5% for 95% confidence level)
                    expected_violation_rate = 0.05
                    
                    # 백테스팅 결과 평가
                    if abs(violation_rate - expected_violation_rate) < 0.01:
                        model_performance = 'Good'
                    elif violation_rate > expected_violation_rate + 0.02:
                        model_performance = 'Underestimating Risk'
                    elif violation_rate < expected_violation_rate - 0.02:
                        model_performance = 'Overestimating Risk'
                    else:
                        model_performance = 'Acceptable'
                    
                    backtesting_results[method] = {
                        'var_value': float(var_value),
                        'violations': int(violations),
                        'violation_rate': float(violation_rate),
                        'expected_violation_rate': expected_violation_rate,
                        'model_performance': model_performance
                    }
            
            return backtesting_results
            
        except Exception as e:
            self.logger.error(f"VaR 백테스팅 오류: {str(e)}")
            return {'error': str(e)}
    
    def generate_var_report(self, var_analysis: Dict[str, Any]) -> List[str]:
        """VaR 분석 보고서 생성"""
        try:
            if 'error' in var_analysis:
                return [f"VaR 분석 실패: {var_analysis['error']}"]
            
            report = []
            
            # 1. 기본 정보
            portfolio = var_analysis.get('portfolio', {})
            total_symbols = len(portfolio)
            report.append(f"포트폴리오 구성: {total_symbols}개 종목")
            
            # 2. 포트폴리오 통계
            stats = var_analysis.get('portfolio_statistics', {})
            if stats:
                annual_return = stats.get('annualized_return', 0)
                annual_volatility = stats.get('annualized_volatility', 0)
                sharpe_ratio = stats.get('sharpe_ratio', 0)
                
                report.append(f"연간 기대수익률: {annual_return:.2%}")
                report.append(f"연간 변동성: {annual_volatility:.2%}")
                report.append(f"샤프 비율: {sharpe_ratio:.2f}")
            
            # 3. 리스크 평가
            risk_assessment = var_analysis.get('risk_assessment', {})
            if risk_assessment:
                risk_level = risk_assessment.get('risk_level', 'UNKNOWN')
                risk_message = risk_assessment.get('risk_message', '')
                report.append(f"전체 리스크 수준: {risk_level}")
                report.append(f"리스크 평가: {risk_message}")
            
            # 4. VaR 결과 요약
            var_results = var_analysis.get('var_results', {})
            if var_results and 'VaR_95_1d' in var_results:
                var_95_1d = var_results['VaR_95_1d']
                
                hist_var = var_95_1d['historical'].get('var', 0)
                param_var = var_95_1d['parametric'].get('var', 0)
                mc_var = var_95_1d['monte_carlo'].get('var', 0)
                
                report.append(f"일간 VaR (95% 신뢰수준):")
                report.append(f"  • 역사적 방법: {hist_var:.2%}")
                report.append(f"  • 모수적 방법: {param_var:.2%}")
                report.append(f"  • 몬테카를로: {mc_var:.2%}")
            
            # 5. 백테스팅 결과
            backtesting = var_analysis.get('backtesting_results', {})
            if backtesting and 'historical' in backtesting:
                hist_backtest = backtesting['historical']
                violation_rate = hist_backtest.get('violation_rate', 0)
                model_perf = hist_backtest.get('model_performance', 'Unknown')
                
                report.append(f"백테스팅 결과 (역사적 방법):")
                report.append(f"  • 위반율: {violation_rate:.2%} (예상: 5.00%)")
                report.append(f"  • 모델 성능: {model_perf}")
            
            # 6. 리스크 관리 권장사항
            recommendations = self._generate_var_recommendations(var_analysis)
            if recommendations:
                report.append("리스크 관리 권장사항:")
                for rec in recommendations:
                    report.append(f"  • {rec}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"VaR 보고서 생성 오류: {str(e)}")
            return ["보고서 생성 중 오류 발생"]
    
    def _generate_var_recommendations(self, var_analysis: Dict[str, Any]) -> List[str]:
        """VaR 기반 권장사항 생성"""
        try:
            recommendations = []
            
            # 리스크 수준별 권장사항
            risk_assessment = var_analysis.get('risk_assessment', {})
            risk_level = risk_assessment.get('risk_level', 'UNKNOWN')
            
            if risk_level == 'EXTREME':
                recommendations.append("즉시 포지션 축소 및 헤지 전략 검토")
                recommendations.append("손실 한도 재설정 및 엄격한 리스크 관리")
            elif risk_level == 'HIGH':
                recommendations.append("포트폴리오 분산도 개선 검토")
                recommendations.append("일일 손실 한도 모니터링 강화")
            elif risk_level == 'MODERATE':
                recommendations.append("현재 리스크 수준 유지 가능")
                recommendations.append("정기적인 VaR 모니터링 지속")
            elif risk_level == 'LOW':
                recommendations.append("적정 리스크 수준 - 수익 기회 확대 검토")
            
            # 백테스팅 결과 기반 권장사항
            backtesting = var_analysis.get('backtesting_results', {})
            if backtesting:
                for method, result in backtesting.items():
                    perf = result.get('model_performance', '')
                    if perf == 'Underestimating Risk':
                        recommendations.append(f"{method} 모델이 리스크를 과소평가 - 보수적 접근 필요")
                    elif perf == 'Overestimating Risk':
                        recommendations.append(f"{method} 모델이 리스크를 과대평가 - 기회 손실 가능성")
            
            # 포트폴리오 통계 기반 권장사항
            stats = var_analysis.get('portfolio_statistics', {})
            if stats:
                sharpe_ratio = stats.get('sharpe_ratio', 0)
                if sharpe_ratio < 0.5:
                    recommendations.append("낮은 샤프 비율 - 수익성 개선 필요")
                elif sharpe_ratio > 2.0:
                    recommendations.append("높은 샤프 비율 - 우수한 위험조정수익률")
                
                skewness = stats.get('skewness', 0)
                if skewness < -1:
                    recommendations.append("음의 왜도 높음 - 극단적 손실 위험 주의")
                
                kurtosis = stats.get('kurtosis', 0)
                if kurtosis > 3:
                    recommendations.append("높은 첨도 - 극값 발생 가능성 높음")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"VaR 권장사항 생성 오류: {str(e)}")
            return []


def main():
    """테스트 실행"""
    print("=== VaR 계산기 테스트 ===")
    
    calculator = VaRCalculator()
    
    # 테스트용 포트폴리오 (한국 대형주)
    test_portfolio = {
        "005930.KS": 0.3,   # 삼성전자 30%
        "000660.KS": 0.2,   # SK하이닉스 20%
        "035420.KS": 0.15,  # NAVER 15%
        "051910.KS": 0.15,  # LG화학 15%
        "005490.KS": 0.2    # POSCO홀딩스 20%
    }
    
    print(f"\n1. 포트폴리오 데이터 수집 테스트")
    
    try:
        # 포트폴리오 데이터 수집
        price_data = calculator.collect_portfolio_data(test_portfolio, period="1y")
        
        if not price_data.empty:
            print(f"   ✅ 데이터 수집 성공: {len(price_data.columns)}개 종목, {len(price_data)}일")
        else:
            print("   ❌ 데이터 수집 실패")
            return
            
    except Exception as e:
        print(f"   ❌ 데이터 수집 오류: {str(e)}")
        return
    
    print(f"\n2. 포트폴리오 수익률 계산 테스트")
    
    try:
        # 포트폴리오 수익률 계산
        portfolio_returns = calculator.calculate_portfolio_returns(price_data, test_portfolio)
        
        if not portfolio_returns.empty:
            print(f"   ✅ 수익률 계산 성공: {len(portfolio_returns)}일")
            print(f"   평균 일간 수익률: {portfolio_returns.mean():.4f}")
            print(f"   일간 변동성: {portfolio_returns.std():.4f}")
        else:
            print("   ❌ 수익률 계산 실패")
            return
            
    except Exception as e:
        print(f"   ❌ 수익률 계산 오류: {str(e)}")
        return
    
    print(f"\n3. VaR 계산 테스트")
    
    try:
        # 각 방법별 VaR 계산
        confidence_level = 0.95
        time_horizon = 1
        
        # 역사적 VaR
        hist_var = calculator.calculate_historical_var(portfolio_returns, confidence_level, time_horizon)
        print(f"   역사적 VaR (95%, 1일): {hist_var.get('var', 0):.4f} ({hist_var.get('var', 0)*100:.2f}%)")
        
        # 모수적 VaR
        param_var = calculator.calculate_parametric_var(portfolio_returns, confidence_level, time_horizon)
        print(f"   모수적 VaR (95%, 1일): {param_var.get('var', 0):.4f} ({param_var.get('var', 0)*100:.2f}%)")
        
        # 몬테카를로 VaR
        mc_var = calculator.calculate_monte_carlo_var(portfolio_returns, confidence_level, time_horizon, 5000)
        print(f"   몬테카를로 VaR (95%, 1일): {mc_var.get('var', 0):.4f} ({mc_var.get('var', 0)*100:.2f}%)")
        
    except Exception as e:
        print(f"   ❌ VaR 계산 오류: {str(e)}")
    
    print(f"\n4. 종합적인 VaR 분석 테스트")
    
    try:
        # 종합 분석 실행
        comprehensive_analysis = calculator.calculate_comprehensive_var(test_portfolio, period="1y")
        
        if 'error' not in comprehensive_analysis:
            print(f"   ✅ 종합 분석 완료")
            
            # 리스크 평가 출력
            risk_assessment = comprehensive_analysis.get('risk_assessment', {})
            risk_level = risk_assessment.get('risk_level', 'UNKNOWN')
            avg_var = risk_assessment.get('average_var_95_1d', 0)
            
            print(f"   전체 리스크 수준: {risk_level}")
            print(f"   평균 VaR (95%, 1일): {avg_var:.2%}")
            
            # 백테스팅 결과
            backtesting = comprehensive_analysis.get('backtesting_results', {})
            if backtesting and 'historical' in backtesting:
                hist_backtest = backtesting['historical']
                violation_rate = hist_backtest.get('violation_rate', 0)
                model_perf = hist_backtest.get('model_performance', 'Unknown')
                
                print(f"   백테스팅 (역사적): 위반율 {violation_rate:.2%}, 성능 {model_perf}")
        else:
            print(f"   ❌ 종합 분석 실패: {comprehensive_analysis['error']}")
            
    except Exception as e:
        print(f"   ❌ 종합 분석 오류: {str(e)}")
    
    print(f"\n5. VaR 보고서 생성 테스트")
    
    try:
        if 'error' not in comprehensive_analysis:
            report = calculator.generate_var_report(comprehensive_analysis)
            
            print(f"   ✅ 보고서 생성 완료: {len(report)}개 항목")
            
            print(f"\n   === VaR 분석 보고서 ===")
            for item in report[:10]:  # 처음 10개 항목만 출력
                print(f"   {item}")
            
            if len(report) > 10:
                print(f"   ... (총 {len(report)}개 항목)")
        
    except Exception as e:
        print(f"   ❌ 보고서 생성 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()