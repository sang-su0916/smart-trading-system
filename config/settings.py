"""
Trading System Settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
YAHOO_FINANCE_API_KEY = os.getenv('YAHOO_FINANCE_API_KEY')
KIS_APP_KEY = os.getenv('KIS_APP_KEY')
KIS_APP_SECRET = os.getenv('KIS_APP_SECRET')
ECOS_API_KEY = os.getenv('ECOS_API_KEY')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/trading_system.db')

# Trading Parameters
DEFAULT_POSITION_SIZE = float(os.getenv('DEFAULT_POSITION_SIZE', 0.02))
STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', 0.05))
TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', 0.10))
MAX_PORTFOLIO_RISK = float(os.getenv('MAX_PORTFOLIO_RISK', 0.20))

# Technical Analysis Parameters
MA_PERIODS = [5, 10, 20, 60, 120]
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

# Signal Generation
MIN_SIGNAL_STRENGTH = 3  # Minimum number of indicators agreeing
SIGNAL_THRESHOLD = 0.6   # Signal confidence threshold

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_system.log')

# Data Paths
RAW_DATA_PATH = 'data/raw'
PROCESSED_DATA_PATH = 'data/processed'
RESULTS_PATH = 'data/results'

# Korean Stock Market
KOSPI_200_SYMBOLS = [
    '005930.KS',  # 삼성전자
    '000660.KS',  # SK하이닉스
    '035420.KS',  # NAVER
    '207940.KS',  # 삼성바이오로직스
    '006400.KS',  # 삼성SDI
    '051910.KS',  # LG화학
    '005380.KS',  # 현대차
    '012330.KS',  # 현대모비스
    '028260.KS',  # 삼성물산
    '066570.KS',  # LG전자
]