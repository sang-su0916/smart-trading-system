"""
한국 주요 종목 코드 및 정보
"""

# 코스피 200 주요 종목 (시가총액 상위 30개 중심)
KOSPI_TOP_30 = {
    # 반도체/IT
    '005930.KS': {'name': '삼성전자', 'sector': 'IT', 'weight': 'HIGH'},
    '000660.KS': {'name': 'SK하이닉스', 'sector': 'IT', 'weight': 'HIGH'},
    '035420.KS': {'name': 'NAVER', 'sector': 'IT', 'weight': 'MEDIUM'},
    '035720.KS': {'name': '카카오', 'sector': 'IT', 'weight': 'MEDIUM'},
    
    # 바이오/헬스케어
    '207940.KS': {'name': '삼성바이오로직스', 'sector': 'BIO', 'weight': 'HIGH'},
    '068270.KS': {'name': '셀트리온', 'sector': 'BIO', 'weight': 'MEDIUM'},
    '326030.KS': {'name': 'SK바이오팜', 'sector': 'BIO', 'weight': 'MEDIUM'},
    
    # 화학/소재
    '051910.KS': {'name': 'LG화학', 'sector': 'CHEMICAL', 'weight': 'HIGH'},
    '006400.KS': {'name': '삼성SDI', 'sector': 'CHEMICAL', 'weight': 'HIGH'},
    '009150.KS': {'name': '삼성전기', 'sector': 'ELECTRONIC', 'weight': 'MEDIUM'},
    
    # 자동차
    '005380.KS': {'name': '현대차', 'sector': 'AUTO', 'weight': 'HIGH'},
    '012330.KS': {'name': '현대모비스', 'sector': 'AUTO', 'weight': 'MEDIUM'},
    '000270.KS': {'name': '기아', 'sector': 'AUTO', 'weight': 'HIGH'},
    
    # 금융
    '055550.KS': {'name': '신한지주', 'sector': 'FINANCE', 'weight': 'HIGH'},
    '105560.KS': {'name': 'KB금융', 'sector': 'FINANCE', 'weight': 'HIGH'},
    '086790.KS': {'name': '하나금융지주', 'sector': 'FINANCE', 'weight': 'MEDIUM'},
    '323410.KS': {'name': '카카오뱅크', 'sector': 'FINANCE', 'weight': 'MEDIUM'},
    
    # 통신
    '017670.KS': {'name': 'SK텔레콤', 'sector': 'TELECOM', 'weight': 'MEDIUM'},
    '030200.KS': {'name': 'KT', 'sector': 'TELECOM', 'weight': 'MEDIUM'},
    
    # 에너지/화학
    '000810.KS': {'name': '삼성화재', 'sector': 'INSURANCE', 'weight': 'MEDIUM'},
    '018260.KS': {'name': '삼성에스디에스', 'sector': 'IT', 'weight': 'MEDIUM'},
    
    # 건설/부동산
    '028260.KS': {'name': '삼성물산', 'sector': 'CONSTRUCTION', 'weight': 'MEDIUM'},
    '009540.KS': {'name': 'HD한국조선해양', 'sector': 'SHIPBUILDING', 'weight': 'MEDIUM'},
    
    # 소비재
    '051900.KS': {'name': 'LG생활건강', 'sector': 'CONSUMER', 'weight': 'MEDIUM'},
    '097950.KS': {'name': 'CJ제일제당', 'sector': 'FOOD', 'weight': 'LOW'},
    
    # 엔터테인먼트
    '041510.KS': {'name': 'SM', 'sector': 'ENTERTAINMENT', 'weight': 'LOW'},
    '352820.KS': {'name': '하이브', 'sector': 'ENTERTAINMENT', 'weight': 'MEDIUM'},
    
    # 기타 중요 종목
    '066570.KS': {'name': 'LG전자', 'sector': 'ELECTRONIC', 'weight': 'MEDIUM'},
    '003550.KS': {'name': 'LG', 'sector': 'HOLDING', 'weight': 'MEDIUM'},
    '096770.KS': {'name': 'SK이노베이션', 'sector': 'ENERGY', 'weight': 'MEDIUM'},
    '011200.KS': {'name': 'HMM', 'sector': 'SHIPPING', 'weight': 'LOW'},
}

# 섹터별 그룹핑
SECTORS = {
    'IT': ['005930.KS', '000660.KS', '035420.KS', '035720.KS', '018260.KS'],
    'BIO': ['207940.KS', '068270.KS', '326030.KS'],
    'AUTO': ['005380.KS', '012330.KS', '000270.KS'],
    'FINANCE': ['055550.KS', '105560.KS', '086790.KS', '323410.KS'],
    'CHEMICAL': ['051910.KS', '006400.KS'],
    'ELECTRONIC': ['009150.KS', '066570.KS'],
    'TELECOM': ['017670.KS', '030200.KS'],
}

# 투자 가중치별 그룹핑
WEIGHT_GROUPS = {
    'HIGH': [symbol for symbol, info in KOSPI_TOP_30.items() if info['weight'] == 'HIGH'],
    'MEDIUM': [symbol for symbol, info in KOSPI_TOP_30.items() if info['weight'] == 'MEDIUM'],
    'LOW': [symbol for symbol, info in KOSPI_TOP_30.items() if info['weight'] == 'LOW'],
}

# 테스트용 종목 (소규모 테스트)
TEST_SYMBOLS = [
    '005930.KS',  # 삼성전자
    '000660.KS',  # SK하이닉스
    '035420.KS',  # NAVER
    '005380.KS',  # 현대차
    '055550.KS',  # 신한지주
]

# 전체 종목 리스트
ALL_SYMBOLS = list(KOSPI_TOP_30.keys())

def get_symbols_by_sector(sector: str) -> list:
    """섹터별 종목 코드 반환"""
    return SECTORS.get(sector.upper(), [])

def get_symbols_by_weight(weight: str) -> list:
    """가중치별 종목 코드 반환"""
    return WEIGHT_GROUPS.get(weight.upper(), [])

def get_stock_info(symbol: str) -> dict:
    """종목 정보 반환"""
    return KOSPI_TOP_30.get(symbol, {})

def get_all_stock_names() -> dict:
    """전체 종목 이름 딕셔너리 반환"""
    return {symbol: info['name'] for symbol, info in KOSPI_TOP_30.items()}

# 미국 주요 지수 (참고용)
US_INDICES = {
    '^GSPC': 'S&P 500',
    '^IXIC': 'NASDAQ',
    '^DJI': 'Dow Jones',
    '^VIX': 'VIX (변동성 지수)',
}

# 환율 (참고용)  
CURRENCIES = {
    'KRW=X': 'USD/KRW',
    'EURKRW=X': 'EUR/KRW',
    'JPYKRW=X': 'JPY/KRW',
}