"""
데이터베이스 관리자
SQLite 기반 트레이딩 시스템 데이터 저장 및 관리
"""
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class DatabaseManager:
    """데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        """
        초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logger()
        
        # 데이터베이스 초기화
        self._initialize_database()
        
        self.logger.info(f"데이터베이스 관리자 초기화 완료: {self.db_path}")
    
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
    
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 획득"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn
    
    def _initialize_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. 주가 데이터 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_prices (
                        symbol TEXT NOT NULL,
                        date DATE NOT NULL,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        adj_close REAL,
                        volume INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, date)
                    )
                ''')
                
                # 2. 포트폴리오 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS portfolios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        initial_capital REAL DEFAULT 10000000,
                        current_value REAL DEFAULT 0,
                        created_date DATE DEFAULT CURRENT_DATE,
                        is_active BOOLEAN DEFAULT 1,
                        strategy_config TEXT  -- JSON 형태로 전략 설정 저장
                    )
                ''')
                
                # 3. 포트폴리오 구성 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS portfolio_holdings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        quantity INTEGER DEFAULT 0,
                        avg_price REAL DEFAULT 0,
                        current_price REAL DEFAULT 0,
                        weight REAL DEFAULT 0,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id),
                        UNIQUE(portfolio_id, symbol)
                    )
                ''')
                
                # 4. 거래 이력 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        trade_type TEXT NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
                        quantity INTEGER NOT NULL,
                        price REAL NOT NULL,
                        commission REAL DEFAULT 0,
                        trade_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        signal_source TEXT,  -- 신호 출처 (예: 'RSI', 'MACD', etc.)
                        signal_confidence REAL,
                        notes TEXT,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                ''')
                
                # 5. 백테스팅 결과 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backtest_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_name TEXT NOT NULL,
                        symbol TEXT,
                        portfolio_config TEXT,  -- JSON 형태로 포트폴리오 설정
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        initial_capital REAL,
                        final_value REAL,
                        total_return REAL,
                        annualized_return REAL,
                        volatility REAL,
                        sharpe_ratio REAL,
                        max_drawdown REAL,
                        win_rate REAL,
                        profit_factor REAL,
                        total_trades INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 6. 신호 이력 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        signal_type TEXT NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
                        signal_strength REAL,
                        confidence REAL,
                        indicators_used TEXT,  -- JSON 배열
                        signal_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_executed BOOLEAN DEFAULT 0,
                        execution_price REAL,
                        notes TEXT
                    )
                ''')
                
                # 7. 리스크 지표 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS risk_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id INTEGER NOT NULL,
                        calculation_date DATE DEFAULT CURRENT_DATE,
                        var_95_1d REAL,
                        var_99_1d REAL,
                        expected_shortfall REAL,
                        portfolio_volatility REAL,
                        correlation_risk_score REAL,
                        concentration_score REAL,
                        max_individual_weight REAL,
                        effective_assets_count REAL,
                        risk_level TEXT,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                ''')
                
                # 8. 최적화 결과 테이블
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS optimization_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        optimization_type TEXT NOT NULL,  -- 'PARAMETER', 'PORTFOLIO', etc.
                        optimization_date DATE DEFAULT CURRENT_DATE,
                        objective_function TEXT,  -- 'sharpe_ratio', 'total_return', etc.
                        best_parameters TEXT,  -- JSON 형태
                        performance_metrics TEXT,  -- JSON 형태
                        optimization_score REAL,
                        combinations_tested INTEGER,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # 인덱스 생성 (성능 최적화)
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_date ON stock_prices(symbol, date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_portfolio_date ON trades(portfolio_id, trade_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol_date ON trading_signals(symbol, signal_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_backtest_strategy_date ON backtest_results(strategy_name, created_at)')
                
                conn.commit()
                self.logger.info("데이터베이스 테이블 초기화 완료")
                
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 오류: {str(e)}")
            raise
    
    # =============== 주가 데이터 관리 ===============
    
    def save_stock_prices(self, symbol: str, price_data: pd.DataFrame) -> bool:
        """
        주가 데이터 저장
        
        Args:
            symbol: 종목 코드
            price_data: 주가 데이터 (OHLCV)
            
        Returns:
            저장 성공 여부
        """
        try:
            with self._get_connection() as conn:
                # 기존 데이터와 중복 제거를 위해 REPLACE 사용
                data_to_save = price_data.copy()
                data_to_save['symbol'] = symbol
                data_to_save = data_to_save.reset_index()
                
                # 컬럼명 정규화
                column_mapping = {
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high', 
                    'Low': 'low',
                    'Close': 'close',
                    'Adj Close': 'adj_close',
                    'Volume': 'volume'
                }
                data_to_save = data_to_save.rename(columns=column_mapping)
                
                # 날짜 형식 정규화
                if 'date' in data_to_save.columns:
                    data_to_save['date'] = pd.to_datetime(data_to_save['date']).dt.strftime('%Y-%m-%d')
                
                # 데이터베이스에 저장 (REPLACE INTO 사용하여 중복 처리)
                for _, row in data_to_save.iterrows():
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_prices 
                        (symbol, date, open, high, low, close, adj_close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['symbol'], row['date'], row.get('open'), row.get('high'),
                        row.get('low'), row.get('close'), row.get('adj_close'), row.get('volume')
                    ))
                
                self.logger.info(f"주가 데이터 저장 완료: {symbol} ({len(data_to_save)}개 레코드)")
                return True
                
        except Exception as e:
            self.logger.error(f"주가 데이터 저장 오류 ({symbol}): {str(e)}")
            return False
    
    def get_stock_prices(self, symbol: str, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        주가 데이터 조회
        
        Args:
            symbol: 종목 코드
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            주가 데이터 DataFrame
        """
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM stock_prices WHERE symbol = ?"
                params = [symbol]
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)
                
                query += " ORDER BY date"
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                
                return df
                
        except Exception as e:
            self.logger.error(f"주가 데이터 조회 오류 ({symbol}): {str(e)}")
            return pd.DataFrame()
    
    def get_available_symbols(self) -> List[str]:
        """저장된 종목 코드 목록 조회"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol")
                symbols = [row[0] for row in cursor.fetchall()]
                return symbols
                
        except Exception as e:
            self.logger.error(f"종목 목록 조회 오류: {str(e)}")
            return []
    
    # =============== 포트폴리오 관리 ===============
    
    def create_portfolio(self, name: str, description: str = "", 
                        initial_capital: float = 10000000,
                        strategy_config: Optional[Dict] = None) -> Optional[int]:
        """
        포트폴리오 생성
        
        Args:
            name: 포트폴리오 이름
            description: 설명
            initial_capital: 초기 자본
            strategy_config: 전략 설정
            
        Returns:
            생성된 포트폴리오 ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO portfolios (name, description, initial_capital, 
                                          current_value, strategy_config)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, description, initial_capital, initial_capital,
                      json.dumps(strategy_config) if strategy_config else None))
                
                portfolio_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"포트폴리오 생성 완료: {name} (ID: {portfolio_id})")
                return portfolio_id
                
        except Exception as e:
            self.logger.error(f"포트폴리오 생성 오류: {str(e)}")
            return None
    
    def get_portfolios(self, active_only: bool = True) -> pd.DataFrame:
        """포트폴리오 목록 조회"""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM portfolios"
                if active_only:
                    query += " WHERE is_active = 1"
                query += " ORDER BY created_date DESC"
                
                df = pd.read_sql_query(query, conn)
                return df
                
        except Exception as e:
            self.logger.error(f"포트폴리오 목록 조회 오류: {str(e)}")
            return pd.DataFrame()
    
    def update_portfolio_value(self, portfolio_id: int, current_value: float) -> bool:
        """포트폴리오 현재 가치 업데이트"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE portfolios 
                    SET current_value = ?, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (current_value, portfolio_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"포트폴리오 가치 업데이트 오류: {str(e)}")
            return False
    
    # =============== 거래 이력 관리 ===============
    
    def record_trade(self, portfolio_id: int, symbol: str, trade_type: str,
                    quantity: int, price: float, commission: float = 0,
                    signal_source: str = None, signal_confidence: float = None,
                    notes: str = None) -> Optional[int]:
        """
        거래 기록
        
        Args:
            portfolio_id: 포트폴리오 ID
            symbol: 종목 코드
            trade_type: 거래 유형 ('BUY' or 'SELL')
            quantity: 수량
            price: 가격
            commission: 수수료
            signal_source: 신호 출처
            signal_confidence: 신호 신뢰도
            notes: 메모
            
        Returns:
            거래 ID
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO trades (portfolio_id, symbol, trade_type, quantity, 
                                      price, commission, signal_source, 
                                      signal_confidence, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (portfolio_id, symbol, trade_type, quantity, price, 
                      commission, signal_source, signal_confidence, notes))
                
                trade_id = cursor.lastrowid
                
                # 포트폴리오 보유 현황 업데이트
                self._update_portfolio_holdings(conn, portfolio_id, symbol, 
                                              trade_type, quantity, price)
                
                conn.commit()
                
                self.logger.info(f"거래 기록 완료: {trade_type} {symbol} {quantity}주 @ {price}")
                return trade_id
                
        except Exception as e:
            self.logger.error(f"거래 기록 오류: {str(e)}")
            return None
    
    def _update_portfolio_holdings(self, conn: sqlite3.Connection, 
                                 portfolio_id: int, symbol: str,
                                 trade_type: str, quantity: int, price: float):
        """포트폴리오 보유 현황 업데이트"""
        cursor = conn.cursor()
        
        # 현재 보유 현황 조회
        cursor.execute('''
            SELECT quantity, avg_price FROM portfolio_holdings 
            WHERE portfolio_id = ? AND symbol = ?
        ''', (portfolio_id, symbol))
        
        result = cursor.fetchone()
        
        if result:
            current_qty, current_avg_price = result
            
            if trade_type == 'BUY':
                new_qty = current_qty + quantity
                new_avg_price = ((current_qty * current_avg_price) + (quantity * price)) / new_qty
            else:  # SELL
                new_qty = current_qty - quantity
                new_avg_price = current_avg_price  # 매도시 평균 단가는 유지
            
            # 기존 레코드 업데이트
            cursor.execute('''
                UPDATE portfolio_holdings 
                SET quantity = ?, avg_price = ?, current_price = ?, 
                    last_updated = CURRENT_TIMESTAMP
                WHERE portfolio_id = ? AND symbol = ?
            ''', (new_qty, new_avg_price, price, portfolio_id, symbol))
            
        else:
            # 새 보유 종목 추가 (매수인 경우만)
            if trade_type == 'BUY':
                cursor.execute('''
                    INSERT INTO portfolio_holdings 
                    (portfolio_id, symbol, quantity, avg_price, current_price)
                    VALUES (?, ?, ?, ?, ?)
                ''', (portfolio_id, symbol, quantity, price, price))
    
    def get_portfolio_holdings(self, portfolio_id: int) -> pd.DataFrame:
        """포트폴리오 보유 현황 조회"""
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query('''
                    SELECT h.*, p.name as portfolio_name,
                           (h.quantity * h.current_price) as market_value,
                           (h.current_price - h.avg_price) / h.avg_price * 100 as unrealized_pnl_pct
                    FROM portfolio_holdings h
                    JOIN portfolios p ON h.portfolio_id = p.id
                    WHERE h.portfolio_id = ? AND h.quantity > 0
                    ORDER BY market_value DESC
                ''', conn, params=[portfolio_id])
                
                return df
                
        except Exception as e:
            self.logger.error(f"포트폴리오 보유 현황 조회 오류: {str(e)}")
            return pd.DataFrame()
    
    def get_trade_history(self, portfolio_id: Optional[int] = None,
                         symbol: Optional[str] = None,
                         days: int = 30) -> pd.DataFrame:
        """거래 이력 조회"""
        try:
            with self._get_connection() as conn:
                query = '''
                    SELECT t.*, p.name as portfolio_name
                    FROM trades t
                    JOIN portfolios p ON t.portfolio_id = p.id
                    WHERE t.trade_date >= date('now', '-{} days')
                '''.format(days)
                
                params = []
                
                if portfolio_id:
                    query += " AND t.portfolio_id = ?"
                    params.append(portfolio_id)
                
                if symbol:
                    query += " AND t.symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY t.trade_date DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            self.logger.error(f"거래 이력 조회 오류: {str(e)}")
            return pd.DataFrame()
    
    # =============== 신호 관리 ===============
    
    def save_trading_signal(self, symbol: str, signal_type: str,
                          signal_strength: float = None, confidence: float = None,
                          indicators_used: List[str] = None, notes: str = None) -> Optional[int]:
        """거래 신호 저장"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO trading_signals 
                    (symbol, signal_type, signal_strength, confidence, 
                     indicators_used, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (symbol, signal_type, signal_strength, confidence,
                      json.dumps(indicators_used) if indicators_used else None, notes))
                
                signal_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"거래 신호 저장 완료: {signal_type} {symbol}")
                return signal_id
                
        except Exception as e:
            self.logger.error(f"거래 신호 저장 오류: {str(e)}")
            return None
    
    def get_recent_signals(self, symbol: Optional[str] = None, 
                          hours: int = 24) -> pd.DataFrame:
        """최근 거래 신호 조회"""
        try:
            with self._get_connection() as conn:
                query = '''
                    SELECT * FROM trading_signals 
                    WHERE signal_date >= datetime('now', '-{} hours')
                '''.format(hours)
                
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY signal_date DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            self.logger.error(f"최근 신호 조회 오류: {str(e)}")
            return pd.DataFrame()


def main():
    """테스트 실행"""
    print("=== 데이터베이스 관리자 테스트 ===")
    
    # 데이터베이스 관리자 초기화
    db_manager = DatabaseManager("test_trading.db")
    
    print(f"\n1. 데이터베이스 초기화 테스트")
    print(f"   ✅ 데이터베이스 초기화 완료")
    
    print(f"\n2. 포트폴리오 생성 테스트")
    
    try:
        # 테스트 포트폴리오 생성
        portfolio_id = db_manager.create_portfolio(
            name="테스트 포트폴리오",
            description="데이터베이스 테스트를 위한 포트폴리오",
            initial_capital=10000000,
            strategy_config={"strategy": "enhanced_signal_integration"}
        )
        
        if portfolio_id:
            print(f"   ✅ 포트폴리오 생성 성공: ID {portfolio_id}")
        else:
            print(f"   ❌ 포트폴리오 생성 실패")
            
    except Exception as e:
        print(f"   ❌ 포트폴리오 생성 오류: {str(e)}")
    
    print(f"\n3. 거래 기록 테스트")
    
    try:
        if portfolio_id:
            # 테스트 거래 기록
            trade_id = db_manager.record_trade(
                portfolio_id=portfolio_id,
                symbol="005930.KS",
                trade_type="BUY",
                quantity=100,
                price=75000,
                commission=150,
                signal_source="RSI",
                signal_confidence=0.85,
                notes="테스트 매수"
            )
            
            if trade_id:
                print(f"   ✅ 거래 기록 성공: ID {trade_id}")
                
                # 포트폴리오 보유 현황 조회
                holdings = db_manager.get_portfolio_holdings(portfolio_id)
                print(f"   보유 종목 수: {len(holdings)}")
                
                if not holdings.empty:
                    for _, holding in holdings.iterrows():
                        print(f"     • {holding['symbol']}: {holding['quantity']}주 @ {holding['avg_price']:,.0f}원")
            else:
                print(f"   ❌ 거래 기록 실패")
        
    except Exception as e:
        print(f"   ❌ 거래 기록 오류: {str(e)}")
    
    print(f"\n4. 신호 저장 테스트")
    
    try:
        # 테스트 신호 저장
        signal_id = db_manager.save_trading_signal(
            symbol="005930.KS",
            signal_type="BUY",
            signal_strength=0.8,
            confidence=0.85,
            indicators_used=["RSI", "MACD", "BB"],
            notes="강한 매수 신호"
        )
        
        if signal_id:
            print(f"   ✅ 신호 저장 성공: ID {signal_id}")
            
            # 최근 신호 조회
            recent_signals = db_manager.get_recent_signals(hours=1)
            print(f"   최근 신호 수: {len(recent_signals)}")
        else:
            print(f"   ❌ 신호 저장 실패")
            
    except Exception as e:
        print(f"   ❌ 신호 저장 오류: {str(e)}")
    
    print(f"\n5. 포트폴리오 조회 테스트")
    
    try:
        # 포트폴리오 목록 조회
        portfolios = db_manager.get_portfolios()
        print(f"   ✅ 포트폴리오 조회 성공: {len(portfolios)}개")
        
        if not portfolios.empty:
            for _, portfolio in portfolios.iterrows():
                print(f"     • {portfolio['name']}: {portfolio['current_value']:,.0f}원")
        
    except Exception as e:
        print(f"   ❌ 포트폴리오 조회 오류: {str(e)}")
    
    print(f"\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()