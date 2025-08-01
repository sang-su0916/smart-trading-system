"""
리스크 관리 시스템 (Risk Management System)
손절매, 익절매, 포지션 사이징 등 리스크 관리 기능
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime

class RiskManager:
    """리스크 관리자 - 손절매/익절매 자동 실행"""
    
    def __init__(self, 
                 stop_loss_pct: float = 0.10,      # 손절매 10%
                 take_profit_pct: float = 0.20,    # 익절매 20%
                 trailing_stop_pct: float = 0.05,  # 추적 손절매 5%
                 max_position_pct: float = 0.95,   # 최대 포지션 95%
                 volatility_adjustment: bool = True):
        """
        Args:
            stop_loss_pct: 손절매 비율
            take_profit_pct: 익절매 비율  
            trailing_stop_pct: 추적 손절매 비율
            max_position_pct: 최대 포지션 비율
            volatility_adjustment: 변동성 기반 조정 여부
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_position_pct = max_position_pct
        self.volatility_adjustment = volatility_adjustment
        self.logger = self._setup_logger()
        
        # 포지션 추적
        self.active_positions = {}
        
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
    
    def calculate_position_size(self, 
                              available_cash: float,
                              current_price: float,
                              signal_confidence: float,
                              volatility: Optional[float] = None) -> Tuple[float, int]:
        """
        포지션 사이징 계산
        
        Args:
            available_cash: 사용 가능한 현금
            current_price: 현재가
            signal_confidence: 신호 신뢰도 (0-1)
            volatility: 변동성 (선택사항)
            
        Returns:
            (투자금액, 주식수량)
        """
        try:
            # 기본 포지션 크기 (신뢰도 기반)
            base_position_pct = min(self.max_position_pct, signal_confidence * 1.2)
            
            # 변동성 조정
            if self.volatility_adjustment and volatility is not None:
                # 변동성이 높으면 포지션 크기 줄이기
                volatility_factor = max(0.3, 1 - volatility)  # 최소 30%까지 감소
                base_position_pct *= volatility_factor
                self.logger.debug(f"Position adjusted for volatility: {volatility:.2f} -> factor: {volatility_factor:.2f}")
            
            # 투자 금액 계산
            investment_amount = available_cash * base_position_pct
            shares = int(investment_amount / current_price)
            actual_investment = shares * current_price
            
            return actual_investment, shares
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {str(e)}")
            return 0.0, 0
    
    def set_position_stops(self, 
                          symbol: str,
                          entry_price: float,
                          entry_date: datetime,
                          shares: int,
                          signal_confidence: float,
                          volatility: Optional[float] = None) -> Dict[str, float]:
        """
        포지션 진입시 손절매/익절매 설정
        
        Args:
            symbol: 종목 코드
            entry_price: 진입가
            entry_date: 진입일
            shares: 보유 주식 수
            signal_confidence: 신호 신뢰도
            volatility: 변동성
            
        Returns:
            설정된 stop levels
        """
        try:
            # 기본 손절매/익절매 비율
            stop_loss_pct = self.stop_loss_pct
            take_profit_pct = self.take_profit_pct
            
            # 신뢰도별 조정
            if signal_confidence >= 0.8:
                # 높은 신뢰도: 손절매 완화, 익절매 확대
                stop_loss_pct *= 1.2
                take_profit_pct *= 1.3
            elif signal_confidence <= 0.6:
                # 낮은 신뢰도: 손절매 강화, 익절매 축소
                stop_loss_pct *= 0.8
                take_profit_pct *= 0.9
            
            # 변동성 조정
            if self.volatility_adjustment and volatility is not None:
                # 변동성이 높으면 손절매 폭 확대
                volatility_multiplier = 1 + min(volatility, 0.5)  # 최대 50% 확대
                stop_loss_pct *= volatility_multiplier
                take_profit_pct *= volatility_multiplier
            
            # 실제 가격 계산
            stop_loss_price = entry_price * (1 - stop_loss_pct)
            take_profit_price = entry_price * (1 + take_profit_pct)
            trailing_stop_price = entry_price * (1 - self.trailing_stop_pct)
            
            # 포지션 정보 저장
            position_info = {
                'symbol': symbol,
                'entry_price': entry_price,
                'entry_date': entry_date,
                'shares': shares,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'trailing_stop_price': trailing_stop_price,
                'highest_price': entry_price,
                'signal_confidence': signal_confidence,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct
            }
            
            self.active_positions[symbol] = position_info
            
            self.logger.info(f"Position stops set for {symbol}: SL={stop_loss_price:.0f} ({stop_loss_pct:.1%}), TP={take_profit_price:.0f} ({take_profit_pct:.1%})")
            
            return {
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'trailing_stop_price': trailing_stop_price,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct
            }
            
        except Exception as e:
            self.logger.error(f"Error setting position stops: {str(e)}")
            return {}
    
    def check_exit_conditions(self, 
                            symbol: str,
                            current_price: float,
                            current_date: datetime) -> Tuple[bool, str, Dict]:
        """
        매도 조건 확인
        
        Args:
            symbol: 종목 코드
            current_price: 현재가
            current_date: 현재일
            
        Returns:
            (매도여부, 매도사유, 상세정보)
        """
        try:
            if symbol not in self.active_positions:
                return False, "", {}
            
            position = self.active_positions[symbol]
            
            # 현재 수익률 계산
            entry_price = position['entry_price']
            current_return = (current_price - entry_price) / entry_price
            
            # 최고가 업데이트 (추적 손절매용)
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
                # 추적 손절매 가격 업데이트
                position['trailing_stop_price'] = current_price * (1 - self.trailing_stop_pct)
            
            exit_info = {
                'symbol': symbol,
                'entry_price': entry_price,
                'current_price': current_price,
                'current_return': current_return,
                'entry_date': position['entry_date'],
                'current_date': current_date,
                'holding_days': (current_date - position['entry_date']).days
            }
            
            # 1. 손절매 확인
            if current_price <= position['stop_loss_price']:
                exit_info['exit_reason'] = 'STOP_LOSS'
                exit_info['target_price'] = position['stop_loss_price']
                return True, 'STOP_LOSS', exit_info
            
            # 2. 익절매 확인
            if current_price >= position['take_profit_price']:
                exit_info['exit_reason'] = 'TAKE_PROFIT'
                exit_info['target_price'] = position['take_profit_price']
                return True, 'TAKE_PROFIT', exit_info
            
            # 3. 추적 손절매 확인
            if current_price <= position['trailing_stop_price'] and position['highest_price'] > entry_price * 1.05:
                # 최소 5% 이상 상승했을 때만 추적 손절매 적용
                exit_info['exit_reason'] = 'TRAILING_STOP'
                exit_info['target_price'] = position['trailing_stop_price']
                exit_info['highest_price'] = position['highest_price']
                return True, 'TRAILING_STOP', exit_info
            
            # 4. 장기 보유 확인 (90일 이상 + 신뢰도 낮음)
            holding_days = (current_date - position['entry_date']).days
            if (holding_days >= 90 and 
                position['signal_confidence'] < 0.7 and 
                current_return < -0.05):  # 5% 이상 손실
                exit_info['exit_reason'] = 'LONG_HOLD_LOSS'
                return True, 'LONG_HOLD_LOSS', exit_info
            
            return False, "", exit_info
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {str(e)}")
            return False, "", {}
    
    def close_position(self, symbol: str) -> bool:
        """
        포지션 종료
        
        Args:
            symbol: 종목 코드
            
        Returns:
            성공 여부
        """
        try:
            if symbol in self.active_positions:
                position = self.active_positions.pop(symbol)
                self.logger.info(f"Position closed for {symbol}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")
            return False
    
    def get_position_info(self, symbol: str) -> Optional[Dict]:
        """포지션 정보 조회"""
        return self.active_positions.get(symbol)
    
    def get_all_positions(self) -> Dict:
        """모든 포지션 정보 조회"""
        return self.active_positions.copy()
    
    def calculate_portfolio_risk(self, 
                               positions: Dict,
                               current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        포트폴리오 전체 리스크 계산
        
        Args:
            positions: 현재 포지션들
            current_prices: 현재가격들
            
        Returns:
            리스크 지표들
        """
        try:
            if not positions:
                return {'total_var': 0, 'max_loss': 0, 'risk_level': 'LOW'}
            
            total_value = 0
            total_potential_loss = 0
            
            for symbol, position in positions.items():
                if symbol in current_prices:
                    current_price = current_prices[symbol]
                    position_value = position['shares'] * current_price
                    potential_loss = position['shares'] * (current_price - position['stop_loss_price'])
                    
                    total_value += position_value
                    total_potential_loss += max(0, potential_loss)  # 손실만 계산
            
            # 리스크 수준 계산
            risk_ratio = total_potential_loss / total_value if total_value > 0 else 0
            
            if risk_ratio > 0.15:
                risk_level = 'HIGH'
            elif risk_ratio > 0.08:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'total_value': total_value,
                'total_potential_loss': total_potential_loss,
                'risk_ratio': risk_ratio,
                'risk_level': risk_level,
                'position_count': len(positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk: {str(e)}")
            return {'total_var': 0, 'max_loss': 0, 'risk_level': 'UNKNOWN'}


def main():
    """리스크 관리자 테스트"""
    print("=== 리스크 관리 시스템 테스트 ===")
    
    # 리스크 관리자 초기화
    risk_manager = RiskManager(
        stop_loss_pct=0.10,      # 10% 손절매
        take_profit_pct=0.20,    # 20% 익절매
        trailing_stop_pct=0.05   # 5% 추적손절매
    )
    
    # 테스트 시나리오
    print("\n1. 포지션 사이징 테스트")
    investment, shares = risk_manager.calculate_position_size(
        available_cash=1000000,  # 100만원
        current_price=70000,     # 7만원
        signal_confidence=0.8,   # 80% 신뢰도
        volatility=0.2          # 20% 변동성
    )
    print(f"   투자금액: {investment:,.0f}원")
    print(f"   주식수량: {shares}주")
    
    # 포지션 설정
    print("\n2. 손절매/익절매 설정 테스트")
    stops = risk_manager.set_position_stops(
        symbol='005930.KS',
        entry_price=70000,
        entry_date=datetime.now(),
        shares=shares,
        signal_confidence=0.8,
        volatility=0.2
    )
    
    for key, value in stops.items():
        if 'price' in key:
            print(f"   {key}: {value:,.0f}원")
        else:
            print(f"   {key}: {value:.2%}")
    
    # 매도 조건 테스트
    print("\n3. 매도 조건 테스트")
    
    # 손절매 테스트
    should_exit, reason, info = risk_manager.check_exit_conditions(
        symbol='005930.KS',
        current_price=63000,  # 10% 하락
        current_date=datetime.now()
    )
    print(f"   가격 63,000원: 매도={should_exit}, 사유={reason}")
    
    # 익절매 테스트
    should_exit, reason, info = risk_manager.check_exit_conditions(
        symbol='005930.KS', 
        current_price=85000,  # 21% 상승
        current_date=datetime.now()
    )
    print(f"   가격 85,000원: 매도={should_exit}, 사유={reason}")
    
    # 포지션 정보 확인
    print("\n4. 포지션 정보")
    position = risk_manager.get_position_info('005930.KS')
    if position:
        print(f"   진입가: {position['entry_price']:,.0f}원")
        print(f"   보유수량: {position['shares']}주")
        print(f"   손절가: {position['stop_loss_price']:,.0f}원")
        print(f"   익절가: {position['take_profit_price']:,.0f}원")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    main()