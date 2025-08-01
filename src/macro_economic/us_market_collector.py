"""
미국 시장 지수 및 지표 수집기
S&P500, 나스닥, VIX, 미국 국채 수익률 등 주요 지표 수집
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class USMarketCollector:
    """미국 시장 데이터 수집기"""
    
    def __init__(self):
        """초기화"""
        self.logger = self._setup_logger()
        
        # 주요 미국 지수 및 지표 심볼
        self.symbols = {
            # 주요 지수
            'sp500': '^GSPC',        # S&P 500
            'nasdaq': '^IXIC',       # NASDAQ Composite
            'dow': '^DJI',           # Dow Jones Industrial Average
            'russell2000': '^RUT',   # Russell 2000 (소형주)
            
            # 섹터별 ETF
            'tech': 'XLK',           # Technology Select Sector
            'financials': 'XLF',     # Financial Select Sector
            'healthcare': 'XLV',     # Health Care Select Sector
            'energy': 'XLE',         # Energy Select Sector
            
            # 변동성 지수
            'vix': '^VIX',           # CBOE Volatility Index
            'vxn': '^VXN',           # NASDAQ Volatility Index
            
            # 채권 관련
            'tnx': '^TNX',           # 10년 국채 수익률
            'tyx': '^TYX',           # 30년 국채 수익률
            'fvx': '^FVX',           # 5년 국채 수익률
            'irx': '^IRX',           # 3개월 국채 수익률
            
            # 통화 및 원자재
            'dxy': 'DX-Y.NYB',       # 달러 인덱스
            'gold': 'GC=F',          # 금 선물
            'oil': 'CL=F',           # 원유 선물
            
            # 주요 개별주 (시장 선도주)
            'aapl': 'AAPL',          # Apple
            'msft': 'MSFT',          # Microsoft
            'googl': 'GOOGL',        # Google
            'amzn': 'AMZN',          # Amazon
            'tsla': 'TSLA',          # Tesla
        }
        
        self.logger.info("미국 시장 데이터 수집기 초기화 완료")
    
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
    
    def get_market_data(self, 
                       symbol_keys: List[str],
                       period: str = "1y",
                       interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        미국 시장 데이터 수집
        
        Args:
            symbol_keys: 수집할 심볼 키 리스트 (self.symbols의 키)
            period: 데이터 기간 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            interval: 데이터 간격 ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
            
        Returns:
            {symbol_key: DataFrame} 형태의 딕셔너리
        """
        try:
            results = {}
            
            for symbol_key in symbol_keys:
                if symbol_key not in self.symbols:
                    self.logger.warning(f"지원하지 않는 심볼 키: {symbol_key}")
                    continue
                
                symbol = self.symbols[symbol_key]
                
                try:
                    self.logger.info(f"미국 시장 데이터 수집: {symbol_key} ({symbol})")
                    
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period=period, interval=interval)
                    
                    if not data.empty:
                        # 인덱스를 date 컬럼으로 변환
                        data = data.reset_index()
                        data['symbol_key'] = symbol_key
                        data['symbol'] = symbol
                        
                        # 컬럼명 소문자로 통일
                        data.columns = [col.lower().replace(' ', '_') for col in data.columns]
                        
                        results[symbol_key] = data
                        self.logger.info(f"데이터 수집 완료: {symbol_key} ({len(data)}개 레코드)")
                    else:
                        self.logger.warning(f"데이터 없음: {symbol_key}")
                        
                except Exception as e:
                    self.logger.error(f"데이터 수집 오류 {symbol_key}: {str(e)}")
                    continue
            
            self.logger.info(f"미국 시장 데이터 수집 완료: {len(results)}개 심볼")
            return results
            
        except Exception as e:
            self.logger.error(f"미국 시장 데이터 수집 오류: {str(e)}")
            return {}
    
    def get_key_indices(self, period: str = "1y") -> pd.DataFrame:
        """
        주요 미국 지수 수집 및 통합
        
        Args:
            period: 데이터 기간
            
        Returns:
            통합된 주요 지수 DataFrame
        """
        try:
            key_indices = ['sp500', 'nasdaq', 'dow', 'vix']
            market_data = self.get_market_data(key_indices, period)
            
            if not market_data:
                return pd.DataFrame()
            
            # 데이터 통합
            combined_data = []
            
            for symbol_key, data in market_data.items():
                if not data.empty:
                    # 필요한 컬럼만 선택
                    subset = data[['date', 'close', 'symbol_key']].copy()
                    subset.rename(columns={'close': f'{symbol_key}_close'}, inplace=True)
                    combined_data.append(subset[['date', f'{symbol_key}_close']])
            
            if not combined_data:
                return pd.DataFrame()
            
            # 날짜 기준으로 병합
            result = combined_data[0]
            for df in combined_data[1:]:
                result = pd.merge(result, df, on='date', how='outer')
            
            result = result.sort_values('date').reset_index(drop=True)
            
            self.logger.info(f"주요 지수 통합 완료: {len(result)}일, {len(result.columns)-1}개 지수")
            return result
            
        except Exception as e:
            self.logger.error(f"주요 지수 수집 오류: {str(e)}")
            return pd.DataFrame()
    
    def calculate_market_indicators(self, 
                                  market_data: pd.DataFrame) -> pd.DataFrame:
        """
        시장 지표 계산 (변화율, 변동성, 상관관계 등)
        
        Args:
            market_data: 시장 데이터 DataFrame
            
        Returns:
            지표가 추가된 DataFrame
        """
        try:
            if market_data.empty:
                return market_data
            
            result = market_data.copy()
            
            # 가격 컬럼들 찾기
            price_columns = [col for col in result.columns if col.endswith('_close')]
            
            for col in price_columns:
                base_name = col.replace('_close', '')
                
                # 1. 일간 수익률
                result[f'{base_name}_daily_return'] = result[col].pct_change() * 100
                
                # 2. 누적 수익률 (기간 시작 대비)
                result[f'{base_name}_cumulative_return'] = (result[col] / result[col].iloc[0] - 1) * 100
                
                # 3. 이동평균 (5일, 20일, 60일)
                result[f'{base_name}_ma5'] = result[col].rolling(window=5).mean()
                result[f'{base_name}_ma20'] = result[col].rolling(window=20).mean()
                result[f'{base_name}_ma60'] = result[col].rolling(window=60).mean()
                
                # 4. 변동성 (20일 롤링)
                result[f'{base_name}_volatility'] = result[f'{base_name}_daily_return'].rolling(window=20).std()
                
                # 5. 모멘텀 (20일, 60일)
                result[f'{base_name}_momentum_20'] = result[col].pct_change(periods=20) * 100
                result[f'{base_name}_momentum_60'] = result[col].pct_change(periods=60) * 100
                
                # 6. RSI (14일)
                result[f'{base_name}_rsi'] = self._calculate_rsi(result[col], window=14)
            
            # 7. 시장 간 상관관계 (60일 롤링)
            if 'sp500_close' in result.columns and 'nasdaq_close' in result.columns:
                result['sp500_nasdaq_corr'] = result['sp500_daily_return'].rolling(window=60).corr(
                    result['nasdaq_daily_return']
                )
            
            # 8. 시장 강도 지표 (상승일 비율 - 20일 롤링)
            for col in price_columns:
                base_name = col.replace('_close', '')
                return_col = f'{base_name}_daily_return'
                if return_col in result.columns:
                    result[f'{base_name}_up_days_ratio'] = (
                        result[return_col] > 0
                    ).rolling(window=20).mean() * 100
            
            self.logger.info(f"시장 지표 계산 완료: {len(result.columns)}개 컬럼")
            return result
            
        except Exception as e:
            self.logger.error(f"시장 지표 계산 오류: {str(e)}")
            return market_data
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
            
        except Exception:
            return pd.Series(index=prices.index, dtype=float)
    
    def analyze_market_regime(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        미국 시장 체제 분석
        
        Args:
            market_data: 계산된 시장 지표 DataFrame
            
        Returns:
            시장 체제 분석 결과
        """
        try:
            if market_data.empty or len(market_data) < 60:
                return {'regime': 'INSUFFICIENT_DATA', 'confidence': 0.0}
            
            latest = market_data.iloc[-1]
            recent_data = market_data.tail(60)  # 최근 60일
            
            signals = []
            
            # 1. S&P 500 트렌드 분석
            if 'sp500_momentum_60' in latest.index and not pd.isna(latest['sp500_momentum_60']):
                sp500_momentum = latest['sp500_momentum_60']
                if sp500_momentum > 10:
                    signals.append(('bull_market', 0.8))
                elif sp500_momentum < -10:
                    signals.append(('bear_market', 0.8))
                else:
                    signals.append(('sideways', 0.5))
            
            # 2. VIX 분석 (공포 지수)
            if 'vix_close' in latest.index and not pd.isna(latest['vix_close']):
                vix_level = latest['vix_close']
                if vix_level > 30:
                    signals.append(('high_volatility', 0.7))
                elif vix_level > 20:
                    signals.append(('medium_volatility', 0.5))
                else:
                    signals.append(('low_volatility', 0.6))
            
            # 3. 시장 폭 분석 (나스닥 vs S&P 500)
            if ('nasdaq_momentum_60' in latest.index and 'sp500_momentum_60' in latest.index and
                not pd.isna(latest['nasdaq_momentum_60']) and not pd.isna(latest['sp500_momentum_60'])):
                
                nasdaq_momentum = latest['nasdaq_momentum_60']
                sp500_momentum = latest['sp500_momentum_60']
                
                if nasdaq_momentum > sp500_momentum + 5:
                    signals.append(('tech_leadership', 0.6))
                elif sp500_momentum > nasdaq_momentum + 5:
                    signals.append(('broad_market_leadership', 0.6))
            
            # 4. 이동평균 트렌드
            if ('sp500_close' in latest.index and 'sp500_ma20' in latest.index and 
                'sp500_ma60' in latest.index):
                
                price = latest['sp500_close']
                ma20 = latest['sp500_ma20']
                ma60 = latest['sp500_ma60']
                
                if price > ma20 > ma60:
                    signals.append(('uptrend', 0.7))
                elif price < ma20 < ma60:
                    signals.append(('downtrend', 0.7))
                else:
                    signals.append(('sideways', 0.4))
            
            # 5. 시장 강도 (상승일 비율)
            if 'sp500_up_days_ratio' in latest.index and not pd.isna(latest['sp500_up_days_ratio']):
                up_ratio = latest['sp500_up_days_ratio']
                if up_ratio > 60:
                    signals.append(('strong_market', 0.6))
                elif up_ratio < 40:
                    signals.append(('weak_market', 0.6))
            
            # 신호 집계
            regime_scores = {
                'BULL_MARKET': 0.0,
                'BEAR_MARKET': 0.0,
                'SIDEWAYS': 0.0,
                'HIGH_VOLATILITY': 0.0,
                'TECH_LED': 0.0
            }
            
            signal_mapping = {
                'bull_market': 'BULL_MARKET',
                'uptrend': 'BULL_MARKET',
                'strong_market': 'BULL_MARKET',
                'bear_market': 'BEAR_MARKET',
                'downtrend': 'BEAR_MARKET',
                'weak_market': 'BEAR_MARKET',
                'sideways': 'SIDEWAYS',
                'high_volatility': 'HIGH_VOLATILITY',
                'medium_volatility': 'HIGH_VOLATILITY',
                'tech_leadership': 'TECH_LED'
            }
            
            total_weight = 0.0
            for signal_type, weight in signals:
                if signal_type in signal_mapping:
                    regime = signal_mapping[signal_type]
                    regime_scores[regime] += weight
                    total_weight += weight
            
            # 정규화
            if total_weight > 0:
                for regime in regime_scores:
                    regime_scores[regime] /= total_weight
            
            # 최고 점수 체제 선택
            best_regime = max(regime_scores.items(), key=lambda x: x[1])
            
            return {
                'regime': best_regime[0],
                'confidence': best_regime[1],
                'regime_scores': regime_scores,
                'signals': signals,
                'signals_count': len(signals),
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"시장 체제 분석 오류: {str(e)}")
            return {'regime': 'ERROR', 'confidence': 0.0}
    
    def get_market_sentiment_indicators(self, period: str = "3mo") -> Dict[str, Any]:
        """
        시장 심리 지표 수집 및 분석
        
        Args:
            period: 분석 기간
            
        Returns:
            시장 심리 분석 결과
        """
        try:
            # 심리 관련 지표들
            sentiment_symbols = ['vix', 'sp500', 'nasdaq', 'gold', 'dxy']
            
            market_data = self.get_market_data(sentiment_symbols, period)
            
            if not market_data:
                return {'sentiment': 'NEUTRAL', 'confidence': 0.0}
            
            sentiment_scores = []
            
            # VIX 분석
            if 'vix' in market_data:
                vix_data = market_data['vix']
                if not vix_data.empty:
                    latest_vix = vix_data['close'].iloc[-1]
                    avg_vix = vix_data['close'].mean()
                    
                    if latest_vix > avg_vix * 1.5:
                        sentiment_scores.append(('fearful', 0.8))
                    elif latest_vix < avg_vix * 0.7:
                        sentiment_scores.append(('greedy', 0.7))
                    else:
                        sentiment_scores.append(('neutral', 0.5))
            
            # 주식 모멘텀 분석
            for index in ['sp500', 'nasdaq']:
                if index in market_data:
                    data = market_data[index]
                    if not data.empty and len(data) > 20:
                        recent_return = (data['close'].iloc[-1] / data['close'].iloc[-20] - 1) * 100
                        
                        if recent_return > 5:
                            sentiment_scores.append(('bullish', 0.6))
                        elif recent_return < -5:
                            sentiment_scores.append(('bearish', 0.6))
            
            # 안전자산 선호도 (금 vs 주식)
            if 'gold' in market_data and 'sp500' in market_data:
                gold_data = market_data['gold']
                sp500_data = market_data['sp500']
                
                if not gold_data.empty and not sp500_data.empty and len(gold_data) > 20:
                    gold_return = (gold_data['close'].iloc[-1] / gold_data['close'].iloc[-20] - 1) * 100
                    sp500_return = (sp500_data['close'].iloc[-1] / sp500_data['close'].iloc[-20] - 1) * 100
                    
                    if gold_return > sp500_return + 3:
                        sentiment_scores.append(('risk_averse', 0.6))
                    elif sp500_return > gold_return + 3:
                        sentiment_scores.append(('risk_seeking', 0.6))
            
            # 심리 점수 집계
            if not sentiment_scores:
                return {'sentiment': 'NEUTRAL', 'confidence': 0.0}
            
            sentiment_mapping = {
                'fearful': -0.8,
                'bearish': -0.6,
                'risk_averse': -0.4,
                'neutral': 0.0,
                'bullish': 0.6,
                'greedy': 0.8,
                'risk_seeking': 0.4
            }
            
            total_score = sum(sentiment_mapping.get(sentiment, 0) * weight 
                            for sentiment, weight in sentiment_scores)
            total_weight = sum(weight for _, weight in sentiment_scores)
            
            if total_weight > 0:
                avg_sentiment = total_score / total_weight
            else:
                avg_sentiment = 0.0
            
            # 심리 분류
            if avg_sentiment > 0.4:
                final_sentiment = 'VERY_BULLISH'
            elif avg_sentiment > 0.2:
                final_sentiment = 'BULLISH'
            elif avg_sentiment > -0.2:
                final_sentiment = 'NEUTRAL'
            elif avg_sentiment > -0.4:
                final_sentiment = 'BEARISH'
            else:
                final_sentiment = 'VERY_BEARISH'
            
            confidence = min(0.95, abs(avg_sentiment) + 0.3)
            
            return {
                'sentiment': final_sentiment,
                'confidence': confidence,
                'sentiment_score': avg_sentiment,
                'indicators': sentiment_scores,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"시장 심리 분석 오류: {str(e)}")
            return {'sentiment': 'NEUTRAL', 'confidence': 0.0}


def main():
    """테스트 실행"""
    print("=== 미국 시장 데이터 수집기 테스트 ===")
    
    collector = USMarketCollector()
    
    # 1. 주요 지수 데이터 수집 테스트
    print(f"\n1. 주요 지수 데이터 수집 테스트")
    
    try:
        key_indices_data = collector.get_key_indices(period="6mo")
        
        if not key_indices_data.empty:
            print(f"   ✅ 주요 지수 수집 성공: {len(key_indices_data)}일")
            
            # 최신 데이터 출력
            latest = key_indices_data.iloc[-1]
            print(f"   최신 데이터 ({latest['date'].strftime('%Y-%m-%d')}):")
            
            for col in key_indices_data.columns:
                if col != 'date' and not pd.isna(latest[col]):
                    print(f"     {col}: {latest[col]:,.2f}")
        else:
            print("   ❌ 주요 지수 수집 실패")
    
    except Exception as e:
        print(f"   ❌ 테스트 오류: {str(e)}")
    
    # 2. 시장 지표 계산 테스트
    print(f"\n2. 시장 지표 계산 테스트")
    
    try:
        if not key_indices_data.empty:
            calculated_data = collector.calculate_market_indicators(key_indices_data)
            
            print(f"   ✅ 지표 계산 완료: {len(calculated_data.columns)}개 컬럼")
            
            # 주요 지표 출력
            latest_calc = calculated_data.iloc[-1]
            
            indicators_to_show = [
                'sp500_daily_return', 'sp500_volatility', 'sp500_rsi',
                'nasdaq_daily_return', 'vix_close'
            ]
            
            print(f"   주요 지표 (최신):")
            for indicator in indicators_to_show:
                if indicator in latest_calc.index and not pd.isna(latest_calc[indicator]):
                    print(f"     {indicator}: {latest_calc[indicator]:.2f}")
        else:
            print("   ❌ 기본 데이터가 없어 지표 계산 생략")
    
    except Exception as e:
        print(f"   ❌ 지표 계산 오류: {str(e)}")
    
    # 3. 시장 체제 분석 테스트
    print(f"\n3. 시장 체제 분석 테스트")
    
    try:
        if not calculated_data.empty:
            regime_analysis = collector.analyze_market_regime(calculated_data)
            
            print(f"   시장 체제: {regime_analysis.get('regime', 'Unknown')}")
            print(f"   신뢰도: {regime_analysis.get('confidence', 0):.2f}")
            print(f"   분석 신호 수: {regime_analysis.get('signals_count', 0)}개")
            
            # 체제별 점수
            scores = regime_analysis.get('regime_scores', {})
            print(f"   체제별 점수:")
            for regime, score in scores.items():
                if score > 0:
                    print(f"     {regime}: {score:.2f}")
        else:
            print("   ❌ 계산된 데이터가 없어 체제 분석 생략")
    
    except Exception as e:
        print(f"   ❌ 시장 체제 분석 오류: {str(e)}")
    
    # 4. 시장 심리 지표 테스트
    print(f"\n4. 시장 심리 지표 테스트")
    
    try:
        sentiment_analysis = collector.get_market_sentiment_indicators(period="3mo")
        
        print(f"   시장 심리: {sentiment_analysis.get('sentiment', 'Unknown')}")
        print(f"   신뢰도: {sentiment_analysis.get('confidence', 0):.2f}")
        print(f"   심리 점수: {sentiment_analysis.get('sentiment_score', 0):.2f}")
        
        indicators = sentiment_analysis.get('indicators', [])
        print(f"   심리 지표 ({len(indicators)}개):")
        for indicator, weight in indicators:
            print(f"     {indicator}: {weight:.2f}")
    
    except Exception as e:
        print(f"   ❌ 시장 심리 분석 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()