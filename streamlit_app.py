"""
Smart Trading Dashboard v4.0
AI 기반 종합 투자 분석 도구
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
from streamlit_searchbox import st_searchbox
import requests
import json
import os
import time
from functools import wraps
import warnings
warnings.filterwarnings('ignore')

# pykrx 시도, 실패시 폴백
try:
    import pykrx.stock as stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

# API 클라이언트는 별도 관리

# 페이지 설정
st.set_page_config(
    page_title="🚀 Smart Trading Dashboard v4.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/sang-su0916/smart-trading-system',
        'Report a bug': 'https://github.com/sang-su0916/smart-trading-system/issues',
        'About': """
        # Smart Trading Dashboard v4.0
        한국 주식 데이터를 지원하는 AI 기반 종합 투자 분석 도구
        
        **🎯 단기 투자 최적화 도구**
        - 1일~3개월 단기 트레이딩에 특화
        - AI 기반 적응형 매매 신호 시스템
        - 종목별 변동성 분석 및 맞춤 전략
        
        **주요 기능:**
        - 📊 5가지 기술적 지표 종합 분석
        - ⚖️ 공정가치 분석 (단기 기준)
        - 🏭 업종 비교 분석
        - 🚦 AI 매매 신호 시스템
        - 📈 백테스팅 성과 분석
        - 📚 투자 교육 콘텐츠
        
        **⚠️ 중요 주의사항:**
        - 교육용 도구 (투자 권유 아님)
        - 장기 투자 분석에는 부적합
        - 실제 투자 결정은 개인 책임
        - 과거 데이터 기반 (미래 보장 없음)
        
        **개발자:** sang-su0916
        **버전:** v4.0 (2025)
        """
    }
)

def get_us_stocks():
    """미국 주요 종목 리스트"""
    return {
        # 빅테크 (FAANG + 테슬라 등)
        "Apple Inc. (AAPL)": "AAPL",
        "Microsoft Corp. (MSFT)": "MSFT", 
        "Alphabet Inc. (GOOGL)": "GOOGL",
        "Amazon.com Inc. (AMZN)": "AMZN",
        "Meta Platforms Inc. (META)": "META",
        "Tesla Inc. (TSLA)": "TSLA",
        "NVIDIA Corp. (NVDA)": "NVDA",
        "Netflix Inc. (NFLX)": "NFLX",
        "Adobe Inc. (ADBE)": "ADBE",
        "Salesforce Inc. (CRM)": "CRM",
        
        # 반도체/기술
        "Intel Corp. (INTC)": "INTC",
        "AMD Inc. (AMD)": "AMD",
        "Qualcomm Inc. (QCOM)": "QCOM",
        "Broadcom Inc. (AVGO)": "AVGO",
        "Oracle Corp. (ORCL)": "ORCL",
        "IBM Corp. (IBM)": "IBM",
        "Cisco Systems (CSCO)": "CSCO",
        
        # 금융
        "JPMorgan Chase (JPM)": "JPM",
        "Bank of America (BAC)": "BAC",
        "Wells Fargo (WFC)": "WFC",
        "Goldman Sachs (GS)": "GS",
        "Visa Inc. (V)": "V",
        "Mastercard Inc. (MA)": "MA",
        "American Express (AXP)": "AXP",
        
        # 소비재/서비스
        "Coca-Cola Co. (KO)": "KO",
        "PepsiCo Inc. (PEP)": "PEP",
        "Nike Inc. (NKE)": "NKE",
        "McDonald's Corp. (MCD)": "MCD",
        "Starbucks Corp. (SBUX)": "SBUX",
        "Walt Disney Co. (DIS)": "DIS",
        "Home Depot (HD)": "HD",
        "Walmart Inc. (WMT)": "WMT",
        
        # 헬스케어/제약
        "Johnson & Johnson (JNJ)": "JNJ",
        "Pfizer Inc. (PFE)": "PFE",
        "Moderna Inc. (MRNA)": "MRNA",
        "Abbott Labs (ABT)": "ABT",
        "Merck & Co (MRK)": "MRK",
        "UnitedHealth Group (UNH)": "UNH",
        
        # 통신
        "AT&T Inc. (T)": "T",
        "Verizon Communications (VZ)": "VZ",
        "T-Mobile US (TMUS)": "TMUS",
        
        # 에너지
        "ExxonMobil Corp. (XOM)": "XOM",
        "Chevron Corp. (CVX)": "CVX",
        "ConocoPhillips (COP)": "COP",
        
        # 산업/항공
        "Boeing Co. (BA)": "BA",
        "Caterpillar Inc. (CAT)": "CAT",
        "General Electric (GE)": "GE",
        "3M Co. (MMM)": "MMM",
        
        # 자동차
        "Ford Motor Co. (F)": "F",
        "General Motors (GM)": "GM",
        
        # ETF
        "SPDR S&P 500 ETF (SPY)": "SPY",
        "Invesco QQQ Trust (QQQ)": "QQQ",
        "Vanguard Total Stock Market (VTI)": "VTI",
        "iShares Russell 2000 (IWM)": "IWM",
        "Vanguard S&P 500 ETF (VOO)": "VOO",
        
        # 기타 인기 종목
        "Berkshire Hathaway (BRK-B)": "BRK-B",
        "Coinbase Global (COIN)": "COIN",
        "PayPal Holdings (PYPL)": "PYPL",
        "Square Inc. (SQ)": "SQ",
        "Zoom Video (ZM)": "ZM",
        "Palantir Technologies (PLTR)": "PLTR",
        "IonQ Inc. (IONQ)": "IONQ",
        "Advanced Micro Devices (AMD)": "AMD"
    }

def get_fallback_stocks():
    """pykrx 사용 불가시 주요 종목 리스트 (확장된 버전)"""
    return {
        # 대형주 (시가총액 상위)
        "삼성전자 (005930)": "005930.KS",
        "SK하이닉스 (000660)": "000660.KS", 
        "NAVER (035420)": "035420.KS",
        "카카오 (035720)": "035720.KS",
        "LG에너지솔루션 (373220)": "373220.KS",
        "삼성바이오로직스 (207940)": "207940.KS",
        "POSCO홀딩스 (005490)": "005490.KS",
        "LG화학 (051910)": "051910.KS",
        "현대차 (005380)": "005380.KS",
        "기아 (000270)": "000270.KS",
        
        # 금융주
        "삼성물산 (028260)": "028260.KS",
        "KB금융 (105560)": "105560.KS",
        "신한지주 (055550)": "055550.KS",
        "하나금융지주 (086790)": "086790.KS",
        "우리금융지주 (316140)": "316140.KS",
        "NH투자증권 (005940)": "005940.KS",
        
        # IT/통신
        "셀트리온 (068270)": "068270.KS",
        "LG전자 (066570)": "066570.KS",
        "삼성SDI (006400)": "006400.KS",
        "SK텔레콤 (017670)": "017670.KS",
        "KT (030200)": "030200.KS",
        "LG유플러스 (032640)": "032640.KS",
        
        # 바이오/제약
        "삼성생명 (032830)": "032830.KS",
        "셀트리온헬스케어 (091990)": "091990.KS",
        "삼진제약 (005500)": "005500.KS",
        "유한양행 (000100)": "000100.KS",
        "종근당 (185750)": "185750.KS",
        
        # 화학/소재
        "LG화학 (051910)": "051910.KS",
        "한화솔루션 (009830)": "009830.KS",
        "롯데케미칼 (011170)": "011170.KS",
        "코스모화학 (005420)": "005420.KS",
        
        # 자동차
        "현대차 (005380)": "005380.KS",
        "기아 (000270)": "000270.KS",
        "현대모비스 (012330)": "012330.KS",
        "한국타이어앤테크놀로지 (161390)": "161390.KS",
        
        # 에너지/유틸리티
        "한국전력 (015760)": "015760.KS",
        "SK이노베이션 (096770)": "096770.KS",
        "GS (078930)": "078930.KS",
        "S-Oil (010950)": "010950.KS",
        
        # 건설/부동산
        "현대건설 (000720)": "000720.KS",
        "대우건설 (047040)": "047040.KS",
        "롯데물산 (023150)": "023150.KS",
        
        # 식품/유통
        "농심 (004370)": "004370.KS",
        "오리온 (001800)": "001800.KS",
        "롯데제과 (280360)": "280360.KS",
        "신세계 (004170)": "004170.KS",
        "이마트 (139480)": "139480.KS",
        
        # 항공/운송
        "대한항공 (003490)": "003490.KS",
        "아시아나항공 (020560)": "020560.KS",
        "한진칼 (180640)": "180640.KS",
        
        # 코스닥 주요 종목
        "알테오젠 (196170)": "196170.KQ",
        "에코프로 (086520)": "086520.KQ",
        "에코프로비엠 (247540)": "247540.KQ",
        "원익IPS (240810)": "240810.KQ",
        "엘앤에프 (066970)": "066970.KQ",
        "카카오뱅크 (323410)": "323410.KQ",
        "카카오페이 (377300)": "377300.KQ",
        "크래프톤 (259960)": "259960.KQ",
        "펄어비스 (263750)": "263750.KQ",
        "위메이드 (112040)": "112040.KQ",
        "컴투스 (078340)": "078340.KQ",
        "넷마블 (251270)": "251270.KQ",
        "NHN (181710)": "181710.KQ",
        "두산에너빌리티 (034020)": "034020.KS",
        "포스코퓨처엠 (003670)": "003670.KS",
        "메리츠금융지주 (138040)": "138040.KS",
        "현대글로비스 (086280)": "086280.KS",
        "CJ제일제당 (097950)": "097950.KS",
        "아모레퍼시픽 (090430)": "090430.KS",
        "LG생활건강 (051900)": "051900.KS",
        
        # 추가 종목들 (검색 개선용)
        "삼성화재 (000810)": "000810.KS",
        "삼성카드 (029780)": "029780.KS",
        "SK이노베이션 (096770)": "096770.KS",
        "SK바이오팜 (326030)": "326030.KQ",
        "LG디스플레이 (034220)": "034220.KS",
        "LG이노텍 (011070)": "011070.KS",
        "현대중공업 (009540)": "009540.KS",
        "두산 (000150)": "000150.KS",
        "포스코 (005490)": "005490.KS",
        "한국조선해양 (009540)": "009540.KS",
        "KT&G (033780)": "033780.KS",
        "SK (034730)": "034730.KS",
        "LG (003550)": "003550.KS",
        "GS홀딩스 (078930)": "078930.KS",
        "한화 (000880)": "000880.KS",
        "롯데홀딩스 (004990)": "004990.KS",
        "신세계 (004170)": "004170.KS",
        "현대백화점 (069960)": "069960.KS",
        "롯데쇼핑 (023530)": "023530.KS",
        "CJ (001040)": "001040.KS",
        "LG상사 (001120)": "001120.KS",
        "대우조선해양 (042660)": "042660.KS",
        "한국전력공사 (015760)": "015760.KS",
        "한국가스공사 (036460)": "036460.KS",
        "국민은행 (105560)": "105560.KS",
        "우리은행 (316140)": "316140.KS",
        "KEB하나은행 (086790)": "086790.KS",
        "신한은행 (055550)": "055550.KS",
        "IBK기업은행 (024110)": "024110.KS",
        "카카오게임즈 (293490)": "293490.KQ",
        "셀트리온제약 (068760)": "068760.KQ",
        "바이로메드 (206640)": "206640.KQ",
        "씨젠 (096530)": "096530.KQ",
        "에이치엘비 (028300)": "028300.KQ",
        "마크로젠 (038290)": "038290.KQ",
        "제넥신 (095700)": "095700.KQ",
        "녹십자 (006280)": "006280.KS",
        "유한양행 (000100)": "000100.KS",
        "동아에스티 (170900)": "170900.KS",
        "부광약품 (003000)": "003000.KS",
        "일동제약 (249420)": "249420.KS",
        "한미약품 (128940)": "128940.KS",
        "대웅제약 (069620)": "069620.KS",
        "종근당 (185750)": "185750.KS",
        "유유제약 (000220)": "000220.KS",
        "삼천리 (004690)": "004690.KS",
        "KCC (002380)": "002380.KS",
        "삼성엔지니어링 (028050)": "028050.KS",
        "GS건설 (006360)": "006360.KS",
        "대림산업 (000210)": "000210.KS",
        "태영건설 (009410)": "009410.KS"
    }

@st.cache_data(ttl=3600)  # 1시간 캐시
def get_all_stocks():
    """한국 주식 + 미국 주식 목록 가져오기"""
    all_stocks = {}
    
    # 1. 한국 주식 추가
    if PYKRX_AVAILABLE:
        try:
            # KOSPI 전체 종목
            try:
                kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
                for ticker in kospi_tickers:
                    try:
                        name = stock.get_market_ticker_name(ticker)
                        if name and len(name.strip()) > 0:
                            all_stocks["{} ({})".format(name, ticker)] = "{}.KS".format(ticker)
                    except:
                        continue
            except:
                pass
            
            # KOSDAQ 전체 종목
            try:
                kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
                for ticker in kosdaq_tickers:
                    try:
                        name = stock.get_market_ticker_name(ticker)
                        if name and len(name.strip()) > 0:
                            all_stocks["{} ({})".format(name, ticker)] = "{}.KQ".format(ticker)
                    except:
                        continue
            except:
                pass
        except:
            # pykrx 실패 시 한국 주식 fallback 사용
            all_stocks.update(get_fallback_stocks())
    else:
        # pykrx 없을 때 fallback 사용
        all_stocks.update(get_fallback_stocks())
    
    # 2. 미국 주식 추가
    all_stocks.update(get_us_stocks())
    
    return all_stocks

@st.cache_data(ttl=3600)  # 1시간 캐시  
def get_korean_stocks():
    """한국 주식 목록만 가져오기 (호환성을 위해 유지)"""
    if not PYKRX_AVAILABLE:
        return get_fallback_stocks()
    
    try:
        all_stocks = {}
        
        # KOSPI 전체 종목 (개선된 버전)
        try:
            kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
            for ticker in kospi_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if name and len(name.strip()) > 0:
                        all_stocks["{} ({})".format(name, ticker)] = "{}.KS".format(ticker)
                except:
                    continue
        except Exception as e:
            pass  # KOSPI 실패시 계속 진행
        
        # KOSDAQ 전체 종목 (개선된 버전) 
        try:
            kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
            for ticker in kosdaq_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    if name and len(name.strip()) > 0:
                        all_stocks["{} ({})".format(name, ticker)] = "{}.KQ".format(ticker)
                except:
                    continue
        except Exception as e:
            pass  # KOSDAQ 실패시 계속 진행
        
        # 데이터가 로드되었으면 반환, 아니면 fallback 사용
        if len(all_stocks) > 0:
            return all_stocks
        else:
            return get_fallback_stocks()
        
    except Exception as e:
        return get_fallback_stocks()

def search_stocks(search_term):
    """종목 검색 함수 (한국 + 미국 주식 지원)"""
    # 빈 검색어 처리
    if not search_term or len(search_term.strip()) < 1:
        # 빈 검색어일 때는 인기 종목 몇 개를 반환 (한국 + 미국)
        popular_stocks = [
            "삼성전자 (005930)", "SK하이닉스 (000660)", "NAVER (035420)",
            "Apple Inc. (AAPL)", "Microsoft Corp. (MSFT)", "Tesla Inc. (TSLA)"
        ]
        return popular_stocks
    
    try:
        search_term = search_term.strip()
        all_stocks = get_all_stocks()  # 한국 + 미국 주식 모두 가져오기
        
        # 종목 데이터가 없는 경우 기본 리스트에서 검색
        if not all_stocks or len(all_stocks) == 0:
            fallback_stocks = get_fallback_stocks()
            fallback_stocks.update(get_us_stocks())
            all_stocks = fallback_stocks
        
        results = []
        exact_matches = []
        partial_matches = []
        
        # 검색어를 소문자로 변환
        search_lower = search_term.lower()
        
        for name, symbol in all_stocks.items():
            try:
                name_lower = name.lower()
                
                # 정확한 매칭 (회사명이나 코드가 정확히 일치)
                if search_lower in name_lower:
                    # 종목코드 직접 검색 (AAPL, TSLA 등)
                    if search_term.upper() in name.upper() and "(" in name:
                        exact_matches.append(name)
                    # 회사명 시작 부분 매칭
                    elif name_lower.startswith(search_lower):
                        exact_matches.append(name)
                    # 부분 매칭
                    else:
                        partial_matches.append(name)
            except:
                continue  # 개별 종목 처리 오류시 건너뛰기
        
        # 정확한 매칭을 먼저, 그 다음 부분 매칭
        results = exact_matches[:15] + partial_matches[:15]
        
        # 결과가 없으면 유사한 종목 추천
        if len(results) == 0:
            # 부분적으로라도 매칭되는 종목 찾기
            for name in all_stocks.keys():
                if any(char in name.lower() for char in search_lower):
                    results.append(name)
                    if len(results) >= 10:
                        break
        
        # 최대 30개까지 반환 (미국 주식 포함으로 늘림)
        return results[:30]
        
    except Exception as e:
        # 최종 fallback: 기본 종목들 (한국 + 미국)
        basic_stocks = [
            "삼성전자 (005930)", "SK하이닉스 (000660)", "NAVER (035420)",
            "Apple Inc. (AAPL)", "Microsoft Corp. (MSFT)", "Tesla Inc. (TSLA)"
        ]
        if search_term:
            return [stock for stock in basic_stocks if search_term.lower() in stock.lower()]
        return basic_stocks[:6]

# KIS API 통합 함수들
def get_stock_data_with_kis(symbol):
    """KIS API 기능 (현재 비활성화)"""
    return {
        'error': 'KIS API 기능 비활성화됨',
        'data_source': '데이터 소스 없음',
        'success': False
    }

def get_stock_data_yfinance(symbol, period="1y"):
    """기존 yfinance를 사용한 데이터 조회"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return pd.DataFrame()
        return data
    except Exception:
        return pd.DataFrame()

def get_stock_data_enhanced(symbol, period="1y"):
    """향상된 주가 데이터 조회 (KIS + yfinance 하이브리드)"""
    
    # 1. KIS API로 실시간 데이터 시도
    kis_result = get_stock_data_with_kis(symbol)
    
    # 2. yfinance로 차트 데이터 조회
    chart_data = get_stock_data_yfinance(symbol, period)
    
    if kis_result['success'] and not chart_data.empty:
        # KIS 실시간 + yfinance 차트 데이터 결합
        return {
            'chart_data': chart_data,
            'kis_data': kis_result,
            'data_source': 'KIS API + yfinance (하이브리드)',
            'has_realtime': True
        }
    elif not chart_data.empty:
        # yfinance만 사용
        return {
            'chart_data': chart_data,
            'kis_data': None,
            'data_source': 'yfinance (지연 데이터)',
            'has_realtime': False
        }
    else:
        # 모든 데이터 소스 실패
        return {
            'chart_data': pd.DataFrame(),
            'kis_data': None,
            'data_source': '데이터 없음',
            'has_realtime': False,
            'error': 'All data sources failed'
        }

def get_stock_data(symbol, period="1y"):
    """주가 데이터 가져오기 (호환성을 위한 래퍼)"""
    result = get_stock_data_enhanced(symbol, period)
    return result.get('chart_data', pd.DataFrame())

def classify_stock_type(data, symbol):
    """종목 특성 분류 시스템"""
    if data.empty or len(data) < 60:
        return {
            'category': 'unknown',
            'name': '분류 불가',
            'volatility': 0,
            'signal_threshold': 30,
            'description': '데이터 부족으로 분류 불가'
        }
    
    # 변동성 계산 (최근 60일 기준)
    recent_data = data.tail(60)
    returns = recent_data['Close'].pct_change().dropna()
    volatility = returns.std() * np.sqrt(252) * 100  # 연환산 변동성(%)
    
    # 평균 거래량 (최근 20일)
    avg_volume = recent_data['Volume'].tail(20).mean()
    
    # 가격 범위 (최근 60일)
    price_range = (recent_data['High'].max() - recent_data['Low'].min()) / recent_data['Close'].mean() * 100
    
    # RSI 변동폭 (얼마나 극단값에 도달하는지)
    if 'RSI' in recent_data.columns:
        rsi_extreme_count = len(recent_data[(recent_data['RSI'] < 25) | (recent_data['RSI'] > 75)])
        rsi_extreme_ratio = rsi_extreme_count / len(recent_data)
    else:
        rsi_extreme_ratio = 0
    
    # 종목 분류 로직
    if volatility >= 45 and price_range >= 35:
        # 극고변동성 (테슬라 타입)
        category = 'ultra_high_volatility'
        name = '극변동성 투기주'
        signal_threshold = 40  # 더 보수적
        target_winrate = 40
        description = '매우 높은 위험, 신중한 접근 필요'
        
    elif volatility >= 30 and rsi_extreme_ratio >= 0.1:
        # 고변동성 성장주 (엔비디아, 메타 타입)
        category = 'high_volatility_growth'
        name = '고변동성 성장주'
        signal_threshold = 35  # 현재 설정 유지
        target_winrate = 65
        description = '높은 수익 가능성, 적극적 전략 적용'
        
    elif volatility >= 20 and rsi_extreme_ratio >= 0.05:
        # 중변동성 기술주 (삼성전자 타입)
        category = 'medium_volatility_tech'
        name = '중변동성 기술주'
        signal_threshold = 30  # 약간 완화
        target_winrate = 55
        description = '안정적 성장, 균형 잡힌 전략'
        
    else:
        # 저변동성 안정주 (마이크로소프트, 애플 타입)
        category = 'low_volatility_stable'
        name = '저변동성 안정주'
        signal_threshold = 25  # 대폭 완화
        target_winrate = 45
        description = '안전한 투자, 보수적 전략'
    
    return {
        'category': category,
        'name': name,
        'volatility': round(volatility, 1),
        'signal_threshold': signal_threshold,
        'target_winrate': target_winrate,
        'description': description,
        'price_range': round(price_range, 1),
        'rsi_extreme_ratio': round(rsi_extreme_ratio * 100, 1),
        'avg_volume': avg_volume
    }

# 실시간 데이터 표시 함수들
def check_api_status():
    """API 상태 체크 (UI에서 숨김)"""
    # API 상태는 내부적으로만 체크, UI에서는 표시하지 않음
    pass

def display_real_time_data(enhanced_data):
    """데이터 표시"""
    kis_data = enhanced_data.get('kis_data', {})
    current_data = kis_data.get('current_data', {})
    
    if current_data:
        st.info("📊 주가 데이터")
        
        # 실시간 가격 표시
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "현재가", 
                "{:,}원".format(current_data['current_price']),
                "{:+,}원 ({:+.2f}%)".format(
                    current_data['change'], 
                    current_data['change_rate']
                )
            )
        
        with col2:
            st.metric("거래량", "{:,}주".format(current_data['volume']))
            
        with col3:
            st.metric("고가", "{:,}원".format(current_data['high']))
            
        with col4:
            st.metric("저가", "{:,}원".format(current_data['low']))
        
        # 호가창 표시
        orderbook = kis_data.get('orderbook')
        if orderbook:
            display_orderbook(orderbook)
        
        st.markdown("---")

def is_us_stock(symbol):
    """미국 주식인지 확인"""
    # 한국 주식은 .KS 또는 .KQ로 끝남
    return not (symbol.endswith('.KS') or symbol.endswith('.KQ'))

def format_price(price, symbol):
    """종목에 따라 적절한 통화로 가격 표시"""
    if is_us_stock(symbol):
        return "${:,.2f}".format(price)
    else:
        return "{:,.0f}원".format(price)

def format_change(change, symbol):
    """종목에 따라 적절한 통화로 변동 표시"""
    if is_us_stock(symbol):
        return "${:+.2f}".format(change)
    else:
        return "{:+.0f}원".format(change)

def display_delayed_data(data, data_source, symbol=""):
    """데이터 표시"""
    st.info("📊 주가 데이터")
    
    if data.empty:
        st.warning("데이터가 없습니다.")
        return
    
    # 기존 방식으로 표시
    latest = data.iloc[-1]
    prev_close = data.iloc[-2]['Close'] if len(data) > 1 else latest['Close']
    change = latest['Close'] - prev_close
    change_pct = (change / prev_close) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("현재가", format_price(latest['Close'], symbol), format_change(change, symbol))
    
    with col2:
        st.metric("변동율", "{:+.2f}%".format(change_pct))
    
    with col3:
        if is_us_stock(symbol):
            st.metric("거래량", "{:,.0f}".format(latest['Volume']))
        else:
            st.metric("거래량", "{:,.0f}주".format(latest['Volume']))
    
    with col4:
        rsi_value = latest['RSI'] if 'RSI' in latest and not pd.isna(latest['RSI']) else 0
        st.metric("RSI", "{:.1f}".format(rsi_value))
    
    st.markdown("---")

def display_orderbook(orderbook):
    """호가창 표시"""
    st.subheader("📋 실시간 호가창")
    
    # 데이터 길이 확인
    ask_prices = orderbook.get('ask_prices', [])
    ask_volumes = orderbook.get('ask_volumes', [])
    bid_prices = orderbook.get('bid_prices', [])
    bid_volumes = orderbook.get('bid_volumes', [])
    
    if not ask_prices or not bid_prices:
        st.warning("호가 데이터가 없습니다.")
        return
    
    # 최대 10단계까지 표시
    max_levels = min(10, len(ask_prices), len(bid_prices), len(ask_volumes), len(bid_volumes))
    
    if max_levels > 0:
        # 호가창 데이터프레임 생성
        orderbook_data = []
        
        # 매도호가 (높은 가격부터)
        for i in range(max_levels-1, -1, -1):
            if i < len(ask_prices):
                orderbook_data.append({
                    '구분': '매도{}'.format(i+1),
                    '잔량': '{:,}'.format(ask_volumes[i]) if i < len(ask_volumes) else '-',
                    '호가': '{:,}'.format(ask_prices[i]),
                    '타입': 'ask'
                })
        
        # 현재가 구분선
        orderbook_data.append({
            '구분': '현재가',
            '잔량': '-',
            '호가': '현재가',
            '타입': 'current'
        })
        
        # 매수호가
        for i in range(min(max_levels, len(bid_prices))):
            orderbook_data.append({
                '구분': '매수{}'.format(i+1),
                '잔량': '{:,}'.format(bid_volumes[i]) if i < len(bid_volumes) else '-',
                '호가': '{:,}'.format(bid_prices[i]),
                '타입': 'bid'
            })
        
        orderbook_df = pd.DataFrame(orderbook_data)
        
        # 스타일링 적용
        def style_orderbook_row(row):
            if row['타입'] == 'ask':
                return ['background-color: #ffebee'] * len(row)
            elif row['타입'] == 'bid':
                return ['background-color: #e8f5e8'] * len(row)
            elif row['타입'] == 'current':
                return ['background-color: #fff3e0; font-weight: bold'] * len(row)
            return [''] * len(row)
        
        styled_df = orderbook_df.drop('타입', axis=1).style.apply(style_orderbook_row, axis=1)
        
        # 호가창 표시
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.warning("호가 데이터를 표시할 수 없습니다.")
    
    st.markdown("---")

def calculate_technical_indicators(data):
    """기술적 지표 계산"""
    if data.empty:
        return data
    
    # RSI 계산
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # 이동평균선
    data['MA_5'] = data['Close'].rolling(window=5).mean()
    data['MA_20'] = data['Close'].rolling(window=20).mean()
    data['MA_60'] = data['Close'].rolling(window=60).mean()
    
    # 볼린저 밴드 계산
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    bb_std = data['Close'].rolling(window=20).std()
    data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
    data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
    
    # MACD 계산
    exp1 = data['Close'].ewm(span=12).mean()
    exp2 = data['Close'].ewm(span=26).mean()
    data['MACD'] = exp1 - exp2
    data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
    data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
    
    # 스토캐스틱 계산
    low_14 = data['Low'].rolling(window=14).min()
    high_14 = data['High'].rolling(window=14).max()
    data['Stoch_K'] = 100 * ((data['Close'] - low_14) / (high_14 - low_14))
    data['Stoch_D'] = data['Stoch_K'].rolling(window=3).mean()
    
    return data

def analyze_fair_value(data, current_price):
    """공정가치 분석"""
    if data.empty or len(data) < 60:
        return {
            'fair_value_score': 50,
            'recommendation': '중립',
            'confidence': 50,
            'reasons': ['데이터 부족으로 분석 불가'],
            'details': {}
        }
    
    latest = data.iloc[-1]
    score = 0
    reasons = []
    details = {}
    
    # RSI 분석 (30점 만점)
    rsi = latest['RSI']
    if rsi < 30:
        rsi_score = 25
        reasons.append("RSI 과매도 상태 ({:.1f}) - 매수 신호".format(rsi))
    elif rsi < 45:
        rsi_score = 15
        reasons.append("RSI 다소 과매도 ({:.1f})".format(rsi))
    elif rsi > 70:
        rsi_score = -15
        reasons.append("RSI 과매수 상태 ({:.1f}) - 매도 신호".format(rsi))
    elif rsi > 55:
        rsi_score = -5
        reasons.append("RSI 다소 과매수 ({:.1f})".format(rsi))
    else:
        rsi_score = 5
        reasons.append("RSI 중립 구간 ({:.1f})".format(rsi))
    
    details['rsi'] = {'value': rsi, 'score': rsi_score}
    
    # 볼린저 밴드 분석 (25점 만점)
    bb_position = ((current_price - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower'])) * 100
    if bb_position < 20:
        bb_score = 20
        reasons.append("볼린저밴드 하단 근처 - 매수 신호")
    elif bb_position < 40:
        bb_score = 10
        reasons.append("볼린저밴드 하단권")
    elif bb_position > 80:
        bb_score = -15
        reasons.append("볼린저밴드 상단 근처 - 매도 신호")
    elif bb_position > 60:
        bb_score = -5
        reasons.append("볼린저밴드 상단권")
    else:
        bb_score = 0
        reasons.append("볼린저밴드 중간권")
    
    details['bollinger'] = {'position': bb_position, 'score': bb_score}
    
    # 이동평균선 분석 (25점 만점)
    ma_score = 0
    if current_price > latest['MA_5']:
        ma_score += 8
        reasons.append("5일선 상향돌파")
    if current_price > latest['MA_20']:
        ma_score += 10
        reasons.append("20일선 상향돌파")
    if current_price > latest['MA_60']:
        ma_score += 7
        reasons.append("60일선 상향돌파")
    
    if ma_score == 0:
        reasons.append("주요 이동평균선 하락 배열")
        ma_score = -15
    
    details['moving_average'] = {'score': ma_score}
    
    # MACD 분석 (20점 만점)
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']
    if macd > macd_signal and macd > 0:
        macd_score = 15
        reasons.append("MACD 강한 상승 신호")
    elif macd > macd_signal:
        macd_score = 10
        reasons.append("MACD 상승 신호")
    elif macd < macd_signal and macd < 0:
        macd_score = -10
        reasons.append("MACD 하락 신호")
    else:
        macd_score = 0
    
    details['macd'] = {'score': macd_score}
    
    # 최종 점수 계산 (100점 만점)
    total_score = rsi_score + bb_score + ma_score + macd_score
    fair_value_score = max(0, min(100, 50 + total_score))
    
    # 추천 등급 결정
    if fair_value_score >= 70:
        recommendation = "매수"
        confidence = min(90, fair_value_score + 10)
    elif fair_value_score >= 55:
        recommendation = "약매수"
        confidence = min(80, fair_value_score + 5)
    elif fair_value_score <= 30:
        recommendation = "매도"
        confidence = min(85, (50 - fair_value_score) + 60)
    elif fair_value_score <= 45:
        recommendation = "약매도"
        confidence = min(75, (50 - fair_value_score) + 55)
    else:
        recommendation = "중립"
        confidence = 60
    
    return {
        'fair_value_score': fair_value_score,
        'recommendation': recommendation,
        'confidence': confidence,
        'reasons': reasons,
        'details': details
    }

def get_industry_peers(symbol):
    """업종별 동종 종목 리스트 반환 (간소화된 버전)"""
    # 주요 업종별 대표 종목들
    industry_map = {
        # 전자/반도체
        '005930': {'industry': '반도체', 'peers': ['000660', '035420', '373220']},
        '000660': {'industry': '반도체', 'peers': ['005930', '035420', '373220']}, 
        '035420': {'industry': 'IT서비스', 'peers': ['035720', '005930', '000660']},
        '035720': {'industry': 'IT서비스', 'peers': ['035420', '005930', '000660']},
        
        # 에너지/화학
        '373220': {'industry': '전기전자', 'peers': ['051910', '005490', '005930']},
        '051910': {'industry': '화학', 'peers': ['373220', '005490', '009830']},
        
        # 자동차
        '005380': {'industry': '자동차', 'peers': ['000270', '012330', '161390']},
        '000270': {'industry': '자동차', 'peers': ['005380', '012330', '161390']},
        
        # 바이오/제약
        '207940': {'industry': '바이오', 'peers': ['068270', '326030', '145020']},
        
        # 철강/소재
        '005490': {'industry': '철강', 'peers': ['051910', '009830', '010130']},
    }
    
    # 종목코드에서 .KS 제거
    clean_symbol = symbol.replace('.KS', '').replace('.KQ', '')
    
    if clean_symbol in industry_map:
        return industry_map[clean_symbol]
    else:
        # 기본 비교군 (대형주)
        return {
            'industry': '기타', 
            'peers': ['005930', '000660', '035420', '035720']
        }

def analyze_industry_comparison(symbol, current_data):
    """업종 비교 분석"""
    if current_data.empty or len(current_data) < 20:
        return {
            'comparison_available': False,
            'industry': '정보 없음',
            'message': '데이터 부족으로 업종 비교 불가'
        }
    
    # 업종 정보 가져오기
    industry_info = get_industry_peers(symbol)
    industry = industry_info['industry']
    peer_codes = industry_info['peers']
    
    if len(peer_codes) < 2:
        return {
            'comparison_available': False,
            'industry': industry,
            'message': '비교 가능한 동종업계 종목 부족'
        }
    
    # 현재 종목 지표
    current_latest = current_data.iloc[-1]
    current_metrics = {
        'rsi': current_latest['RSI'] if not pd.isna(current_latest['RSI']) else 50,
        'ma20_ratio': current_latest['Close'] / current_latest['MA_20'] if not pd.isna(current_latest['MA_20']) else 1,
        'bb_position': ((current_latest['Close'] - current_latest['BB_Lower']) / 
                       (current_latest['BB_Upper'] - current_latest['BB_Lower'])) * 100 
                       if not pd.isna(current_latest['BB_Lower']) else 50
    }
    
    # 동종업계 평균 계산
    peer_metrics = []
    successful_peers = []
    
    for peer_code in peer_codes:
        try:
            # KS/KQ 구분
            if peer_code in ['005930', '000660', '035420', '035720', '005380', '000270', '051910', '207940', '005490']:
                peer_symbol = "{}.KS".format(peer_code)
            else:
                peer_symbol = "{}.KQ".format(peer_code)
            
            peer_data = get_stock_data(peer_symbol, '3mo')
            if not peer_data.empty and len(peer_data) >= 20:
                peer_data = calculate_technical_indicators(peer_data)
                peer_latest = peer_data.iloc[-1]
                
                peer_metric = {
                    'rsi': peer_latest['RSI'] if not pd.isna(peer_latest['RSI']) else 50,
                    'ma20_ratio': peer_latest['Close'] / peer_latest['MA_20'] if not pd.isna(peer_latest['MA_20']) else 1,
                    'bb_position': ((peer_latest['Close'] - peer_latest['BB_Lower']) / 
                                   (peer_latest['BB_Upper'] - peer_latest['BB_Lower'])) * 100 
                                   if not pd.isna(peer_latest['BB_Lower']) else 50
                }
                peer_metrics.append(peer_metric)
                successful_peers.append(peer_code)
        except:
            continue
    
    if len(peer_metrics) < 2:
        return {
            'comparison_available': False,
            'industry': industry,
            'message': '동종업계 데이터 수집 실패'
        }
    
    # 업종 평균 계산
    industry_avg = {
        'rsi': sum(p['rsi'] for p in peer_metrics) / len(peer_metrics),
        'ma20_ratio': sum(p['ma20_ratio'] for p in peer_metrics) / len(peer_metrics),
        'bb_position': sum(p['bb_position'] for p in peer_metrics) / len(peer_metrics)
    }
    
    # 비교 분석
    comparison_analysis = []
    rsi_diff = current_metrics['rsi'] - industry_avg['rsi']
    if abs(rsi_diff) > 5:
        if rsi_diff < 0:
            comparison_analysis.append("RSI가 업종 평균보다 {:.1f}p 낮음 (상대적 매수 우위)".format(abs(rsi_diff)))
        else:
            comparison_analysis.append("RSI가 업종 평균보다 {:.1f}p 높음 (상대적 과매수)".format(rsi_diff))
    
    ma20_diff = ((current_metrics['ma20_ratio'] - 1) * 100) - ((industry_avg['ma20_ratio'] - 1) * 100)
    if abs(ma20_diff) > 1:
        if ma20_diff > 0:
            comparison_analysis.append("20일선 대비 위치가 업종 평균보다 {:.1f}%p 높음".format(ma20_diff))
        else:
            comparison_analysis.append("20일선 대비 위치가 업종 평균보다 {:.1f}%p 낮음".format(abs(ma20_diff)))
    
    bb_diff = current_metrics['bb_position'] - industry_avg['bb_position']
    if abs(bb_diff) > 10:
        if bb_diff < 0:
            comparison_analysis.append("볼린저밴드 위치가 업종 평균보다 낮음 (상대적 저평가)")
        else:
            comparison_analysis.append("볼린저밴드 위치가 업종 평균보다 높음 (상대적 고평가)")
    
    # 종합 점수 계산
    comparison_score = 50
    if rsi_diff < -5:
        comparison_score += 15
    elif rsi_diff > 10:
        comparison_score -= 10
        
    if ma20_diff > 2:
        comparison_score += 10
    elif ma20_diff < -2:
        comparison_score -= 10
        
    if bb_diff < -10:
        comparison_score += 10
    elif bb_diff > 15:
        comparison_score -= 10
    
    comparison_score = max(0, min(100, comparison_score))
    
    # 상대적 추천
    if comparison_score >= 70:
        relative_recommendation = "업종 내 강력 매수"
    elif comparison_score >= 55:
        relative_recommendation = "업종 내 매수"
    elif comparison_score <= 30:
        relative_recommendation = "업종 내 매도"
    elif comparison_score <= 45:
        relative_recommendation = "업종 내 약매도"
    else:
        relative_recommendation = "업종 평균 수준"
    
    return {
        'comparison_available': True,
        'industry': industry,
        'peer_count': len(successful_peers),
        'peer_codes': successful_peers,
        'current_metrics': current_metrics,
        'industry_avg': industry_avg,
        'comparison_score': comparison_score,
        'relative_recommendation': relative_recommendation,
        'comparison_analysis': comparison_analysis
    }

def backtest_trading_signals(data, symbol, lookback_days=120):
    """백테스팅을 통한 매매 신호 성과 분석"""
    if data.empty or len(data) < lookback_days:
        return {
            'backtesting_available': False,
            'message': '백테스팅을 위한 충분한 데이터 없음'
        }
    
    # 백테스팅용 데이터 (최근 120일 제외하고 과거 데이터 사용)
    backtest_data = data.iloc[:-30]  # 최근 30일은 제외하고 백테스팅
    
    if len(backtest_data) < 90:
        return {
            'backtesting_available': False,
            'message': '백테스팅 기간이 너무 짧음'
        }
    
    trades = []
    
    # 과거 데이터로 매매 신호 시뮬레이션
    for i in range(60, len(backtest_data) - 10):  # 60일 이후부터, 마지막 10일 전까지
        # 현재 시점까지의 데이터로 신호 생성
        current_data = backtest_data.iloc[:i+1].copy()
        current_data = calculate_technical_indicators(current_data)
        
        if len(current_data) < 60:
            continue
            
        current_price = current_data.iloc[-1]['Close']
        signals = analyze_trading_signals(current_data, current_price, symbol)
        
        if not signals.get('signals_available'):
            continue
            
        signal_strength = signals.get('signal_strength', 0)
        stock_type = signals.get('stock_type', {})
        threshold = stock_type.get('signal_threshold', 35)
        
        # 종목별 맞춤 신호 강도 임계값 적용
        if abs(signal_strength) >= threshold:
            trade_type = 'BUY' if signal_strength > 0 else 'SELL'
            entry_price = current_price
            target_price = signals.get('target_price_1', current_price)
            stop_loss = signals.get('stop_loss', current_price)
            
            # 향후 10일간 결과 확인
            future_data = backtest_data.iloc[i+1:i+11]
            if len(future_data) == 0:
                continue
                
            trade_result = simulate_trade(
                trade_type, entry_price, target_price, stop_loss, 
                future_data, symbol
            )
            
            if trade_result:
                trade_result['entry_date'] = current_data.index[-1]
                trade_result['signal_strength'] = signal_strength
                trades.append(trade_result)
    
    # 백테스팅 결과 분석
    if len(trades) == 0:
        return {
            'backtesting_available': False,
            'message': '분석 기간 동안 거래 신호 없음'
        }
    
    return analyze_backtest_results(trades, symbol)

def simulate_trade(trade_type, entry_price, target_price, stop_loss, future_data, symbol):
    """개별 거래 시뮬레이션"""
    if future_data.empty:
        return None
    
    for i, (date, row) in enumerate(future_data.iterrows()):
        high_price = row['High']
        low_price = row['Low']
        close_price = row['Close']
        
        if trade_type == 'BUY':
            # 매수의 경우: 목표가 달성하면 수익, 손절가 터치하면 손실
            if high_price >= target_price:
                return {
                    'trade_type': trade_type,
                    'entry_price': entry_price,
                    'exit_price': target_price,
                    'exit_date': date,
                    'days_held': i + 1,
                    'return_pct': ((target_price - entry_price) / entry_price) * 100,
                    'result': 'WIN'
                }
            elif low_price <= stop_loss:
                return {
                    'trade_type': trade_type,
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'exit_date': date,
                    'days_held': i + 1,
                    'return_pct': ((stop_loss - entry_price) / entry_price) * 100,
                    'result': 'LOSS'
                }
        else:  # SELL
            # 매도의 경우: 목표가(하락) 달성하면 수익, 손절가(상승) 터치하면 손실
            if low_price <= target_price:
                return {
                    'trade_type': trade_type,
                    'entry_price': entry_price,
                    'exit_price': target_price,
                    'exit_date': date,
                    'days_held': i + 1,
                    'return_pct': ((entry_price - target_price) / entry_price) * 100,
                    'result': 'WIN'
                }
            elif high_price >= stop_loss:
                return {
                    'trade_type': trade_type,
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'exit_date': date,
                    'days_held': i + 1,
                    'return_pct': ((entry_price - stop_loss) / entry_price) * 100,
                    'result': 'LOSS'
                }
    
    # 10일 후에도 목표가/손절가에 도달하지 않으면 종가로 청산
    final_price = future_data.iloc[-1]['Close']
    if trade_type == 'BUY':
        return_pct = ((final_price - entry_price) / entry_price) * 100
    else:
        return_pct = ((entry_price - final_price) / entry_price) * 100
    
    return {
        'trade_type': trade_type,
        'entry_price': entry_price,
        'exit_price': final_price,
        'exit_date': future_data.index[-1],
        'days_held': len(future_data),
        'return_pct': return_pct,
        'result': 'WIN' if return_pct > 0 else 'LOSS'
    }

def analyze_backtest_results(trades, symbol):
    """백테스팅 결과 분석"""
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['result'] == 'WIN']
    losing_trades = [t for t in trades if t['result'] == 'LOSS']
    
    win_rate = (len(winning_trades) / total_trades) * 100
    
    total_return = sum(t['return_pct'] for t in trades)
    avg_return = total_return / total_trades
    
    max_gain = max(t['return_pct'] for t in trades)
    max_loss = min(t['return_pct'] for t in trades)
    
    avg_win = sum(t['return_pct'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['return_pct'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    avg_holding_days = sum(t['days_held'] for t in trades) / total_trades
    
    # 신뢰도 계산 (승률 기반)
    if win_rate >= 70:
        confidence = min(95, win_rate + 10)
    elif win_rate >= 60:
        confidence = min(85, win_rate + 5)
    elif win_rate >= 50:
        confidence = win_rate
    else:
        confidence = max(30, win_rate - 10)
    
    return {
        'backtesting_available': True,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'total_return': total_return,
        'max_gain': max_gain,
        'max_loss': max_loss,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_holding_days': avg_holding_days,
        'confidence': confidence,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'trades': trades[:10]  # 최근 10개 거래만 저장
    }

def analyze_trading_signals(data, current_price, symbol=""):
    """적응형 매매 신호 분석 - 종목 특성별 맞춤 전략"""
    if data.empty or len(data) < 60:
        return {
            'signals_available': False,
            'message': '데이터 부족으로 매매 신호 분석 불가'
        }
    
    # 종목 특성 분류
    stock_type = classify_stock_type(data, symbol)
    
    latest = data.iloc[-1]
    prev = data.iloc[-2] if len(data) > 1 else latest
    signals = []
    signal_strength = 0
    entry_signals = []
    exit_signals = []
    
    # 종목별 맞춤 파라미터 설정
    category = stock_type['category']
    if category == 'high_volatility_growth':
        # 고변동성 성장주 (엔비디아, 메타 타입)
        rsi_buy_threshold = 15
        rsi_sell_threshold = 85
        bb_buy_threshold = 2
        bb_sell_threshold = 98
        volume_multiplier = 1.5
        ma_distance_threshold = 12
        price_change_threshold = 8
        volatility_threshold = 5
        required_filters = 3
    elif category == 'medium_volatility_tech':
        # 중변동성 기술주 (삼성전자 타입)
        rsi_buy_threshold = 20
        rsi_sell_threshold = 80
        bb_buy_threshold = 5
        bb_sell_threshold = 95
        volume_multiplier = 1.3
        ma_distance_threshold = 15
        price_change_threshold = 10
        volatility_threshold = 6
        required_filters = 2
    elif category == 'low_volatility_stable':
        # 저변동성 안정주 (마이크로소프트, 애플 타입)
        rsi_buy_threshold = 25
        rsi_sell_threshold = 75
        bb_buy_threshold = 10
        bb_sell_threshold = 90
        volume_multiplier = 1.2
        ma_distance_threshold = 20
        price_change_threshold = 12
        volatility_threshold = 8
        required_filters = 2
    else:
        # 극변동성 투기주 (테슬라 타입) - 매우 보수적
        rsi_buy_threshold = 10
        rsi_sell_threshold = 90
        bb_buy_threshold = 1
        bb_sell_threshold = 99
        volume_multiplier = 2.0
        ma_distance_threshold = 10
        price_change_threshold = 5
        volatility_threshold = 3
        required_filters = 4
    
    # 1. RSI 신호 분석 (더 엄격한 기준)
    rsi = latest['RSI']
    rsi_prev = prev['RSI'] if not pd.isna(prev['RSI']) else rsi
    
    # 적응형 RSI 기준: 종목별 맞춤 임계값
    if rsi < rsi_buy_threshold and rsi_prev >= rsi_buy_threshold:
        entry_signals.append(f"RSI {stock_type['name']} 맞춤 과매도권 진입 - 반등 신호")
        signal_strength += 30
    elif rsi > rsi_sell_threshold and rsi_prev <= rsi_sell_threshold:
        exit_signals.append(f"RSI {stock_type['name']} 맞춤 과매수권 진입 - 매도 신호")
        signal_strength -= 25
    elif rsi < rsi_buy_threshold * 0.75:  # 매우 극단적인 경우
        entry_signals.append(f"RSI 극도 과매도 - 매우 강한 매수 신호 ({stock_type['name']})")
        signal_strength += 40
    elif rsi > rsi_sell_threshold * 1.06:  # 매우 극단적인 경우 (85*1.06=90)
        exit_signals.append(f"RSI 극도 과매수 - 매우 강한 매도 신호 ({stock_type['name']})")
        signal_strength -= 35
    
    # 2. 이동평균선 신호 분석
    ma5 = latest['MA_5']
    ma20 = latest['MA_20']
    ma60 = latest['MA_60']
    
    ma5_prev = prev['MA_5'] if not pd.isna(prev['MA_5']) else ma5
    ma20_prev = prev['MA_20'] if not pd.isna(prev['MA_20']) else ma20
    
    # 골든크로스/데드크로스 감지
    if ma5 > ma20 and ma5_prev <= ma20_prev:
        entry_signals.append("골든크로스 - 5일선이 20일선 상향돌파")
        signal_strength += 25
    elif ma5 < ma20 and ma5_prev >= ma20_prev:
        exit_signals.append("데드크로스 - 5일선이 20일선 하향돌파")
        signal_strength -= 20
    
    # 정배열/역배열 확인
    if ma5 > ma20 > ma60:
        signals.append("이동평균선 정배열 - 상승 추세")
        signal_strength += 15
    elif ma5 < ma20 < ma60:
        signals.append("이동평균선 역배열 - 하락 추세")
        signal_strength -= 15
    
    # 3. 볼린저밴드 신호 분석
    bb_upper = latest['BB_Upper']
    bb_lower = latest['BB_Lower']
    bb_middle = latest['BB_Middle']
    
    bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100
    prev_price = prev['Close']
    prev_bb_position = ((prev_price - prev['BB_Lower']) / (prev['BB_Upper'] - prev['BB_Lower'])) * 100 if not pd.isna(prev['BB_Lower']) else bb_position
    
    # 적응형 볼린저밴드 기준: 종목별 맞춤 임계값
    if bb_position < bb_buy_threshold and prev_bb_position >= bb_buy_threshold:
        entry_signals.append(f"볼린저밴드 {stock_type['name']} 맞춤 하단 터치 - 반등 신호")
        signal_strength += 30
    elif bb_position > bb_sell_threshold and prev_bb_position <= bb_sell_threshold:
        exit_signals.append(f"볼린저밴드 {stock_type['name']} 맞춤 상단 터치 - 조정 신호")
        signal_strength -= 25
    elif bb_position < bb_buy_threshold * 0.5:  # 매우 극단적인 경우
        entry_signals.append(f"볼린저밴드 최하단 - 매우 강한 반등 신호 ({stock_type['name']})")
        signal_strength += 35
    elif bb_position > bb_sell_threshold + (100-bb_sell_threshold)*0.5:  # 매우 극단적인 경우
        exit_signals.append(f"볼린저밴드 최상단 - 매우 강한 조정 신호 ({stock_type['name']})")
        signal_strength -= 30
    
    # 볼린저밴드 스퀴즈 감지 (변동성 축소)
    bb_width = ((bb_upper - bb_lower) / bb_middle) * 100
    if bb_width < 10:  # 볼린저밴드 폭이 좁을 때
        signals.append("볼린저밴드 스퀴즈 - 큰 변동성 임박")
    
    # 4. MACD 신호 분석
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']
    macd_hist = latest['MACD_Histogram']
    
    macd_prev = prev['MACD'] if not pd.isna(prev['MACD']) else macd
    macd_signal_prev = prev['MACD_Signal'] if not pd.isna(prev['MACD_Signal']) else macd_signal
    macd_hist_prev = prev['MACD_Histogram'] if not pd.isna(prev['MACD_Histogram']) else macd_hist
    
    # MACD 크로스 신호
    if macd > macd_signal and macd_prev <= macd_signal_prev:
        entry_signals.append("MACD 골든크로스 - 상승 신호")
        signal_strength += 20
    elif macd < macd_signal and macd_prev >= macd_signal_prev:
        exit_signals.append("MACD 데드크로스 - 하락 신호")
        signal_strength -= 20
    
    # MACD 히스토그램 분석
    if macd_hist > 0 and macd_hist_prev <= 0:
        signals.append("MACD 히스토그램 양전환 - 모멘텀 증가")
        signal_strength += 10
    elif macd_hist < 0 and macd_hist_prev >= 0:
        signals.append("MACD 히스토그램 음전환 - 모멘텀 감소")
        signal_strength -= 10
    
    # 5. 스토캐스틱 신호 분석
    stoch_k = latest['Stoch_K']
    stoch_d = latest['Stoch_D']
    stoch_k_prev = prev['Stoch_K'] if not pd.isna(prev['Stoch_K']) else stoch_k
    stoch_d_prev = prev['Stoch_D'] if not pd.isna(prev['Stoch_D']) else stoch_d
    
    if stoch_k < 20 and stoch_d < 20:
        if stoch_k > stoch_d and stoch_k_prev <= stoch_d_prev:
            entry_signals.append("스토캐스틱 과매도권 골든크로스")
            signal_strength += 15
    elif stoch_k > 80 and stoch_d > 80:
        if stoch_k < stoch_d and stoch_k_prev >= stoch_d_prev:
            exit_signals.append("스토캐스틱 과매수권 데드크로스")
            signal_strength -= 15
    
    # 6. 추가 보수적 필터 조건
    additional_filters_passed = 0
    
    # 적응형 필터 1: 거래량 확인 (종목별 맞춤 배수)
    avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1]
    if latest['Volume'] > avg_volume * volume_multiplier:
        additional_filters_passed += 1
        signals.append(f"거래량 {volume_multiplier}배 증가 확인 ({stock_type['name']})")
    
    # 적응형 필터 2: 가격이 20일 평균선 근처에 있는지 확인
    ma20_distance = abs((current_price - ma20) / ma20) * 100
    if ma20_distance < ma_distance_threshold:
        additional_filters_passed += 1
        signals.append(f"적정 가격 범위 내 ({ma_distance_threshold}% 이내)")
    
    # 적응형 필터 3: 최근 5일간 과도한 움직임 확인
    if len(data) >= 6:
        recent_5day_change = abs((current_price - data['Close'].iloc[-6]) / data['Close'].iloc[-6]) * 100
        if recent_5day_change < price_change_threshold:
            additional_filters_passed += 1
            signals.append(f"안정적 가격 움직임 ({price_change_threshold}% 이내)")
    
    # 적응형 필터 4: ATR 기반 변동성 체크
    atr_recent = data['Close'].rolling(window=14).std().iloc[-1] / current_price * 100
    if atr_recent < volatility_threshold:
        additional_filters_passed += 1
        signals.append(f"변동성 안정화 ({volatility_threshold}% 미만)")
    
    # 적응형 필터 적용: 종목별 요구 조건 수 다름
    if additional_filters_passed < required_filters:
        signal_strength = signal_strength * 0.3  # 신호 강도 70% 감소
        signals.append(f"⚠️ {stock_type['name']} 조건 미달 ({additional_filters_passed}/{required_filters}) - 신호 강도 감소")
    
    # 6. 종합 신호 강도 계산 및 추천
    signal_strength = max(-100, min(100, signal_strength))  # -100 ~ 100 범위로 제한
    
    if signal_strength >= 50:
        overall_signal = "강한 매수"
        signal_color = "🟢"
        confidence = min(95, 70 + (signal_strength - 50) * 0.5)
    elif signal_strength >= 25:
        overall_signal = "매수"
        signal_color = "🟡"
        confidence = min(85, 60 + (signal_strength - 25) * 0.4)
    elif signal_strength <= -50:
        overall_signal = "강한 매도"
        signal_color = "🔴"
        confidence = min(90, 70 + abs(signal_strength + 50) * 0.4)
    elif signal_strength <= -25:
        overall_signal = "매도"
        signal_color = "🟠"
        confidence = min(80, 60 + abs(signal_strength + 25) * 0.4)
    else:
        overall_signal = "관망"
        signal_color = "⚪"
        confidence = 50
    
    # 7. 목표가 및 손절가 계산 (고승률 전략 - 더 보수적)
    volatility = data['Close'].rolling(window=20).std().iloc[-1] / current_price
    
    if signal_strength > 0:  # 매수 신호일 때
        target_price_1 = current_price * (1 + volatility * 0.5)  # 1차 목표가 (매우 빠른 익절)
        target_price_2 = current_price * (1 + volatility * 1.0)  # 2차 목표가 (보수적)
        stop_loss = current_price * (1 - volatility * 0.5)  # 손절가 (매우 빠른 손절)
    else:  # 매도 신호일 때
        target_price_1 = current_price * (1 - volatility * 0.5)  # 1차 목표가 (매우 빠른 익절)
        target_price_2 = current_price * (1 - volatility * 1.0)  # 2차 목표가 (보수적)
        stop_loss = current_price * (1 + volatility * 0.5)  # 손절가 (매우 빠른 손절)
    
    return {
        'signals_available': True,
        'overall_signal': overall_signal,
        'signal_color': signal_color,
        'signal_strength': signal_strength,
        'confidence': confidence,
        'entry_signals': entry_signals,
        'exit_signals': exit_signals,
        'general_signals': signals,
        'target_price_1': target_price_1,
        'target_price_2': target_price_2,
        'stop_loss': stop_loss,
        'volatility': volatility * 100,
        'stock_type': stock_type  # 종목 분류 정보 추가
    }

def create_candlestick_chart(data, symbol):
    """캔들스틱 차트 생성"""
    if data.empty:
        st.warning("차트 데이터를 불러올 수 없습니다.")
        return None
        
    fig = go.Figure()
    
    # 캔들스틱 추가
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name=symbol
    ))
    
    # 이동평균선 추가
    if 'MA_5' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA_5'],
            mode='lines', name='MA5',
            line=dict(color='orange', width=1)
        ))
    
    if 'MA_20' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA_20'],
            mode='lines', name='MA20',
            line=dict(color='red', width=1)
        ))
    
    # Y축 제목을 종목에 따라 다르게 설정
    y_title = "가격 (USD)" if is_us_stock(symbol) else "가격 (원)"
    
    fig.update_layout(
        title="주가 차트",
        yaxis_title=y_title,
        xaxis_title="날짜",
        height=500,
        showlegend=True
    )
    
    return fig

def main():
    """메인 함수"""
    st.title("🚀 Smart Trading Dashboard v4.0")
    st.caption("한국 주식 종합 분석 플랫폼")
    
    # 사용법 간단 안내
    with st.container():
        col_intro1, col_intro2 = st.columns([3, 1])
        with col_intro1:
            st.markdown("""
            **🎯 글로벌 주식 검색으로 공정가치 분석, 업종 비교, 매매 신호를 확인하세요!**  
            🌐 **한국 + 미국 주식 지원** | 📊 5가지 기술적 지표 종합 분석 | 🏭 동종업계 비교 | 🚦 매매 신호
            """)
        with col_intro2:
            if st.button("📚 사용법 보기", help="대시보드 사용법과 투자 가이드를 확인하세요"):
                st.info("👇 화면 하단의 '📚 투자 용어 가이드' 섹션을 확인해주세요!")
    
    # 프로그램 특징 및 주의사항
    with st.expander("⚠️ 프로그램 특징 및 주의사항 (필독)", expanded=False):
        col_feature1, col_feature2 = st.columns(2)
        
        with col_feature1:
            st.markdown("""
            ### 📈 **프로그램 특징**
            
            **🎯 단기 투자 최적화**
            - 1일~3개월 단기 트레이딩에 최적화
            - RSI, MACD, 볼린저밴드 등 단기 지표 중심
            - 백테스팅: 최근 120일 기준 성과 분석
            
            **🤖 AI 기반 적응형 전략**
            - 종목별 변동성에 따른 맞춤 신호
            - 극변동성/고변동성/중변동성/저변동성 4단계 분류
            - 종목 특성별 최적화된 매매 임계값 적용
            
            **📊 종합 기술 분석**
            - 5가지 핵심 기술적 지표 통합 분석
            - 실시간 신호 강도 및 신뢰도 계산
            - 업종별 상대 비교 분석
            """)
        
        with col_feature2:
            st.markdown("""
            ### ⚠️ **중요 주의사항**
            
            **🚨 교육용 도구 (투자 권유 아님)**
            - 실제 투자 결정은 개인 책임
            - 과거 데이터 기반 분석 (미래 보장 없음)
            - 반드시 추가 검증 후 투자 결정
            
            **❌ 장기 투자 부적합**
            - 1년 이상 장기 투자 분석에는 부적합
            - 기업 펀더멘털 분석 제한적
            - 거시경제 지표 미반영
            
            **⚡ 실시간 데이터 한계**
            - 일부 데이터는 15-20분 지연
            - 급격한 시장 변화 시 신호 지연 가능
            - 시장 개장 시간 외 분석 결과 제한
            
            **💡 권장 사용법**
            - 여러 지표를 종합적으로 판단
            - 리스크 관리 원칙 준수
            - 분산 투자 및 손절 규칙 설정
            """)
    
    st.markdown("---")
    
    # 사이드바
    st.sidebar.header("🔍 종목 선택")
    st.sidebar.markdown("🌐 **글로벌 종목 검색** (한국 + 미국 주식)")
    
    # 검색 상태 표시
    with st.sidebar.container():
        all_stocks_count = len(get_all_stocks())
        korean_stocks_count = len(get_korean_stocks())
        us_stocks_count = len(get_us_stocks())
        
        st.sidebar.success(f"✅ 총 {all_stocks_count:,}개 종목 지원")
        st.sidebar.markdown(f"• 🇰🇷 한국: {korean_stocks_count:,}개")
        st.sidebar.markdown(f"• 🇺🇸 미국: {us_stocks_count:,}개")
    
    st.sidebar.markdown("💡 **검색 방법:**")
    st.sidebar.markdown("**🇰🇷 한국 주식:**")
    st.sidebar.markdown("- 회사명: 삼성전자, NAVER, 카카오")
    st.sidebar.markdown("- 종목코드: 005930, 035420, 035720")
    st.sidebar.markdown("**🇺🇸 미국 주식:**")
    st.sidebar.markdown("- 회사명: Apple, Tesla, Microsoft")
    st.sidebar.markdown("- 종목코드: AAPL, TSLA, MSFT")
    
    # 종목 검색
    try:
        selected_name = st_searchbox(
            search_function=search_stocks,
            placeholder="🔍 한국/미국 주식 검색 (예: 삼성전자, AAPL, Tesla)",
            key="stock_searchbox",
            clear_on_submit=False,
            rerun_on_update=True
        )
    except Exception as e:
        st.sidebar.error(f"검색박스 오류: {e}")
        # 기본 선택박스로 fallback
        all_stocks_list = list(get_korean_stocks().keys())[:50]  # 상위 50개만
        selected_name = st.sidebar.selectbox(
            "종목 선택",
            options=all_stocks_list,
            index=0 if len(all_stocks_list) > 0 else None
        )
    
    # 종목 현황 (디버그 정보 숨김처리)
    # 내부적으로는 동작하지만 UI에서는 표시하지 않음
    
    # 전체 종목 리스트 (한국 + 미국)
    all_stocks = get_all_stocks()
    
    # 선택된 종목 처리
    if selected_name and selected_name in all_stocks:
        selected_symbol = all_stocks[selected_name]
        st.sidebar.info("선택된 종목: **{}**".format(selected_name))
    else:
        # 기본값 설정
        default_stock = "삼성전자 (005930)" if "삼성전자 (005930)" in all_stocks else list(all_stocks.keys())[0]
        selected_name = default_stock
        selected_symbol = all_stocks[selected_name]
        st.sidebar.warning("종목을 검색해주세요")
    
    # 기간 선택
    period = st.sidebar.selectbox(
        "조회 기간",
        ["1mo", "3mo", "6mo", "1y", "2y"],
        index=3
    )
    
    # 메인 컨텐츠
    st.subheader("📈 {} ({})".format(selected_name, selected_symbol))
    
    # API 상태 확인
    check_api_status()
    
    # 향상된 데이터 로드
    with st.spinner("데이터 로딩 중..."):
        enhanced_data = get_stock_data_enhanced(selected_symbol, period)
        data = enhanced_data.get('chart_data', pd.DataFrame())
        
    if not data.empty:
        # 기술적 지표 계산
        data = calculate_technical_indicators(data)
        
        # 실시간 데이터 표시
        if enhanced_data.get('has_realtime'):
            display_real_time_data(enhanced_data)
        else:
            display_delayed_data(data, enhanced_data.get('data_source', 'yfinance'), selected_symbol)
        
        # 현재 가격 정보 (전체 탭에서 사용)
        current_price = data['Close'].iloc[-1] if not data.empty else 0
        
        # 탭 구조로 콘텐츠 분리
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 차트 분석", 
            "⚖️ 공정가치 분석", 
            "🏭 업종 비교", 
            "🚦 매매 신호", 
            "📚 투자 가이드"
        ])
        
        with tab1:
            st.subheader("📊 주가 차트 및 기술적 지표")
            chart = create_candlestick_chart(data, selected_symbol)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            
            # 기술적 지표 요약
            if not data.empty:
                latest = data.iloc[-1]
                
                st.markdown("### 📈 주요 기술적 지표")
                
                col_tech1, col_tech2, col_tech3, col_tech4 = st.columns(4)
                
                with col_tech1:
                    rsi_value = latest['RSI'] if 'RSI' in latest and not pd.isna(latest['RSI']) else 0
                    if rsi_value > 70:
                        rsi_status = "과매수"
                        rsi_color = "🔴"
                    elif rsi_value < 30:
                        rsi_status = "과매도"
                        rsi_color = "🟢"
                    else:
                        rsi_status = "중립"
                        rsi_color = "🟡"
                    st.metric("RSI", f"{rsi_value:.1f}", f"{rsi_color} {rsi_status}")
                
                with col_tech2:
                    macd = latest['MACD'] if 'MACD' in latest and not pd.isna(latest['MACD']) else 0
                    macd_signal = latest['MACD_Signal'] if 'MACD_Signal' in latest and not pd.isna(latest['MACD_Signal']) else 0
                    macd_diff = macd - macd_signal
                    macd_status = "상승" if macd_diff > 0 else "하락"
                    macd_color = "🟢" if macd_diff > 0 else "🔴"
                    st.metric("MACD", f"{macd:.2f}", f"{macd_color} {macd_status}")
                
                with col_tech3:
                    ma20 = latest['MA_20'] if 'MA_20' in latest and not pd.isna(latest['MA_20']) else current_price
                    ma_ratio = ((current_price / ma20 - 1) * 100) if ma20 > 0 else 0
                    ma_status = "돌파" if ma_ratio > 0 else "이탈"
                    ma_color = "🟢" if ma_ratio > 0 else "🔴"
                    st.metric("MA20 대비", f"{ma_ratio:+.1f}%", f"{ma_color} {ma_status}")
                
                with col_tech4:
                    bb_upper = latest['BB_Upper'] if 'BB_Upper' in latest and not pd.isna(latest['BB_Upper']) else current_price
                    bb_lower = latest['BB_Lower'] if 'BB_Lower' in latest and not pd.isna(latest['BB_Lower']) else current_price
                    if bb_upper > bb_lower:
                        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100
                        if bb_position > 80:
                            bb_status = "상단"
                            bb_color = "🔴"
                        elif bb_position < 20:
                            bb_status = "하단"
                            bb_color = "🟢"
                        else:
                            bb_status = "중간"
                            bb_color = "🟡"
                        st.metric("볼린저밴드", f"{bb_position:.0f}%", f"{bb_color} {bb_status}")
                    else:
                        st.metric("볼린저밴드", "N/A", "🔄 계산중")
        
        with tab2:
            st.subheader("⚖️ 공정가치 분석")
            fair_value_analysis = analyze_fair_value(data, current_price)
            
            # 분석 결과 표시
            col_analysis1, col_analysis2, col_analysis3 = st.columns(3)
            
            with col_analysis1:
                score = fair_value_analysis['fair_value_score']
                if score >= 70:
                    score_color = "🟢"
                    score_desc = "매수 권장"
                elif score >= 55:
                    score_color = "🟡"
                    score_desc = "약매수"
                elif score <= 30:
                    score_color = "🔴"
                    score_desc = "매도 권장"
                elif score <= 45:
                    score_color = "🟠"
                    score_desc = "약매도"
                else:
                    score_color = "⚪"
                    score_desc = "중립"
                
                st.metric(
                    "공정가치 점수",
                    "{} {}/100".format(score_color, score),
                    "({})".format(score_desc),
                    help="RSI, 볼린저밴드, 이동평균선, MACD를 종합한 점수입니다. 70점 이상은 매수, 30점 이하는 매도를 의미합니다."
                )
            
            with col_analysis2:
                recommendation = fair_value_analysis['recommendation']
                confidence = fair_value_analysis['confidence']
                
                if recommendation == "매수":
                    rec_color = "🟢"
                elif recommendation == "약매수":
                    rec_color = "🟡"
                elif recommendation == "매도":
                    rec_color = "🔴"
                elif recommendation == "약매도":
                    rec_color = "🟠"
                else:
                    rec_color = "⚪"
                
                st.metric(
                    "투자 추천",
                    "{} {}".format(rec_color, recommendation),
                    "신뢰도: {:.1f}%".format(confidence)
                )
            
            with col_analysis3:
                # 볼린저밴드 위치 표시
                bb_position = fair_value_analysis['details'].get('bollinger', {}).get('position', 50)
                st.metric(
                    "볼린저밴드 위치",
                    "{:.1f}%".format(bb_position),
                    help="볼린저밴드 내 현재가 위치 (0%=하단, 100%=상단)"
                )
        
        # 상세 분석 결과
        with st.expander("📈 상세 분석 결과", expanded=True):
            st.markdown("**🎯 주요 판단 근거:**")
            for reason in fair_value_analysis['reasons']:
                st.markdown("• {}".format(reason))
            
            st.markdown("---")
            
            # 지표별 세부 분석
            col_detail1, col_detail2 = st.columns(2)
            
            with col_detail1:
                st.markdown("**📊 기술적 지표:**")
                
                # RSI 분석
                rsi_data = fair_value_analysis['details'].get('rsi', {})
                if rsi_data:
                    rsi_value = rsi_data.get('value', 0)
                    st.markdown("**RSI ({:.1f}):** {}".format(
                        rsi_value,
                        "과매도" if rsi_value < 30 else "과매수" if rsi_value > 70 else "중립"
                    ))
                
                # 볼린저밴드 분석
                bb_data = fair_value_analysis['details'].get('bollinger', {})
                if bb_data:
                    bb_pos = bb_data.get('position', 50)
                    st.markdown("**볼린저밴드:** {}".format(
                        "하단권" if bb_pos < 30 else "상단권" if bb_pos > 70 else "중간권"
                    ))
            
            with col_detail2:
                st.markdown("**📈 추세 분석:**")
                
                # 이동평균선 분석
                ma_score = fair_value_analysis['details'].get('moving_average', {}).get('score', 0)
                if ma_score > 15:
                    st.markdown("• 주요 이동평균선 상향 돌파")
                elif ma_score > 0:
                    st.markdown("• 일부 이동평균선 상향 돌파")
                else:
                    st.markdown("• 이동평균선 하락 배열")
                
                # MACD 분석
                macd_score = fair_value_analysis['details'].get('macd', {}).get('score', 0)
                if macd_score > 10:
                    st.markdown("• MACD 강한 상승 신호")
                elif macd_score > 0:
                    st.markdown("• MACD 상승 신호")
                elif macd_score < 0:
                    st.markdown("• MACD 하락 신호")
                else:
                    st.markdown("• MACD 중립")
            
            # 상세 분석 결과
            with st.expander("📈 상세 분석 결과", expanded=True):
                st.markdown("**🎯 주요 판단 근거:**")
                for reason in fair_value_analysis['reasons']:
                    st.markdown("• {}".format(reason))
                
                st.markdown("---")
                
                # 지표별 세부 분석
                col_detail1, col_detail2 = st.columns(2)
                
                with col_detail1:
                    st.markdown("**📊 기술적 지표:**")
                    
                    # RSI 분석
                    rsi_data = fair_value_analysis['details'].get('rsi', {})
                    if rsi_data:
                        rsi_value = rsi_data.get('value', 0)
                        st.markdown("**RSI ({:.1f}):** {}".format(
                            rsi_value,
                            "과매도" if rsi_value < 30 else "과매수" if rsi_value > 70 else "중립"
                        ))
                    
                    # 볼린저밴드 분석
                    bb_data = fair_value_analysis['details'].get('bollinger', {})
                    if bb_data:
                        bb_pos = bb_data.get('position', 50)
                        st.markdown("**볼린저밴드:** {}".format(
                            "하단권" if bb_pos < 30 else "상단권" if bb_pos > 70 else "중간권"
                        ))
                
                with col_detail2:
                    st.markdown("**📈 추세 분석:**")
                    
                    # 이동평균선 분석
                    ma_score = fair_value_analysis['details'].get('moving_average', {}).get('score', 0)
                    if ma_score > 15:
                        st.markdown("• 주요 이동평균선 상향 돌파")
                    elif ma_score > 0:
                        st.markdown("• 일부 이동평균선 상향 돌파")
                    else:
                        st.markdown("• 이동평균선 하락 배열")
                    
                    # MACD 분석
                    macd_score = fair_value_analysis['details'].get('macd', {}).get('score', 0)
                    if macd_score > 0:
                        st.markdown("• MACD 상승 신호")
                    elif macd_score < 0:
                        st.markdown("• MACD 하락 신호")
                    else:
                        st.markdown("• MACD 중립")
        
        with tab3:
            st.subheader("🏭 업종 비교 분석")
            industry_analysis = analyze_industry_comparison(selected_symbol, data)
            
            if industry_analysis['comparison_available']:
                # 업종 정보 표시
                col_industry1, col_industry2, col_industry3 = st.columns(3)
                
                with col_industry1:
                    st.metric(
                        "업종",
                        industry_analysis['industry'],
                        help="현재 종목이 속한 업종 분류"
                    )
                
                with col_industry2:
                    comparison_score = industry_analysis['comparison_score']
                    if comparison_score >= 70:
                        score_color = "🟢"
                    elif comparison_score >= 55:
                        score_color = "🟡"
                    elif comparison_score <= 30:
                        score_color = "🔴"
                    elif comparison_score <= 45:
                        score_color = "🟠"
                    else:
                        score_color = "⚪"
                    
                    st.metric(
                        "업종 내 상대 점수",
                        "{} {}/100".format(score_color, comparison_score),
                        help="동종업계 대비 상대적 매력도 (높을수록 업종 내 우위)"
                    )
                
                with col_industry3:
                    relative_rec = industry_analysis['relative_recommendation']
                    if "강력 매수" in relative_rec:
                        rec_color = "🟢"
                    elif "매수" in relative_rec:
                        rec_color = "🟡"
                    elif "매도" in relative_rec:
                        rec_color = "🔴"
                    else:
                        rec_color = "⚪"
                    
                    st.metric(
                        "업종 내 추천",
                        "{} {}".format(rec_color, relative_rec),
                        help="동종업계 대비 상대적 투자 추천"
                    )
            else:
                st.info("📊 업종 비교 분석: {}".format(industry_analysis['message']))
                st.markdown("**참고:** 충분한 데이터가 확보되면 동종업계 대비 상대적 위치를 분석하여 제공합니다.")
        
        with tab4:
            st.subheader("🚦 매매 신호 분석")
            
            # 백테스팅 결과 먼저 표시
            with st.expander("📊 백테스팅 성과 분석", expanded=True):
                with st.spinner("백테스팅 분석 중..."):
                    backtest_results = backtest_trading_signals(data, selected_symbol)
                
                if backtest_results['backtesting_available']:
                    # 백테스팅 주요 지표 표시
                    col_bt1, col_bt2, col_bt3, col_bt4 = st.columns(4)
                    
                    with col_bt1:
                        win_rate = backtest_results['win_rate']
                        if win_rate >= 70:
                            rate_color = "🟢"
                        elif win_rate >= 60:
                            rate_color = "🟡"
                        elif win_rate >= 50:
                            rate_color = "🟠"
                        else:
                            rate_color = "🔴"
                        
                        st.metric(
                            "실제 승률",
                            f"{rate_color} {win_rate:.1f}%",
                            f"{backtest_results['winning_trades']}승 {backtest_results['losing_trades']}패"
                        )
                    
                    with col_bt2:
                        avg_return = backtest_results['avg_return']
                        total_trades = backtest_results['total_trades']
                        st.metric(
                            "평균 수익률",
                            f"{avg_return:+.2f}%",
                            f"총 {total_trades}건 거래"
                        )
                    
                    with col_bt3:
                        max_gain = backtest_results['max_gain']
                        max_loss = backtest_results['max_loss']
                        st.metric(
                            "최대 수익/손실",
                            f"+{max_gain:.1f}%",
                            f"{max_loss:.1f}%"
                        )
                    
                    with col_bt4:
                        confidence = backtest_results['confidence']
                        holding_days = backtest_results['avg_holding_days']
                        st.metric(
                            "실제 신뢰도",
                            f"{confidence:.1f}%",
                            f"평균 {holding_days:.1f}일 보유"
                        )
                    
                    # 상세 백테스팅 결과
                    st.markdown("**📈 백테스팅 상세 결과:**")
                    col_detail1, col_detail2 = st.columns(2)
                    
                    with col_detail1:
                        st.markdown(f"• **평균 수익 거래**: +{backtest_results['avg_win']:.2f}%")
                        st.markdown(f"• **평균 손실 거래**: {backtest_results['avg_loss']:.2f}%")
                        st.markdown(f"• **총 수익률**: {backtest_results['total_return']:+.2f}%")
                    
                    with col_detail2:
                        # 거래 품질 평가
                        if win_rate >= 70:
                            quality = "🟢 매우 우수"
                        elif win_rate >= 60:
                            quality = "🟡 우수"
                        elif win_rate >= 50:
                            quality = "🟠 보통"
                        else:
                            quality = "🔴 주의 필요"
                        
                        st.markdown(f"• **신호 품질**: {quality}")
                        st.markdown(f"• **분석 기간**: 과거 {len(data)}일")
                        
                        # 신뢰도 기반 추천
                        if confidence >= 70:
                            st.markdown("• **추천**: 🟢 신호 신뢰 가능")
                        elif confidence >= 60:
                            st.markdown("• **추천**: 🟡 조건부 신뢰")
                        else:
                            st.markdown("• **추천**: 🔴 추가 검증 필요")
                
                else:
                    st.info(f"📊 백테스팅 분석: {backtest_results['message']}")
                    st.markdown("**참고:** 충분한 데이터가 있는 종목에서 백테스팅 결과를 확인할 수 있습니다.")
            
            st.markdown("---")
            
            # 종목 분류 정보 표시
            st.subheader("📊 종목 특성 분석")
            stock_classification = classify_stock_type(data, selected_symbol)
            
            col_class1, col_class2, col_class3, col_class4 = st.columns(4)
            
            with col_class1:
                st.metric(
                    "종목 분류",
                    stock_classification['name'],
                    help="AI가 분석한 종목의 특성 분류"
                )
            
            with col_class2:
                st.metric(
                    "연환산 변동성",
                    f"{stock_classification['volatility']}%",
                    help="최근 60일 기준 연환산 변동성"
                )
            
            with col_class3:
                st.metric(
                    "신호 임계값",
                    f"{stock_classification['signal_threshold']}",
                    help="이 종목에 최적화된 매매 신호 임계값"
                )
            
            with col_class4:
                st.metric(
                    "목표 승률",
                    f"{stock_classification['target_winrate']}%",
                    help="이 전략의 목표 승률"
                )
            
            # 종목 특성 설명
            st.info(f"💡 **{stock_classification['name']}**: {stock_classification['description']}")
            
            st.markdown("---")
            
            # 현재 매매 신호 표시
            st.subheader("🎯 현재 매매 신호")
            trading_signals = analyze_trading_signals(data, current_price, selected_symbol)
            
            if trading_signals['signals_available']:
                # 종합 신호 표시
                col_signal1, col_signal2, col_signal3, col_signal4 = st.columns(4)
                
                with col_signal1:
                    st.metric(
                        "종합 신호",
                        "{} {}".format(trading_signals['signal_color'], trading_signals['overall_signal']),
                        help="기술적 지표 종합 매매 신호"
                    )
                
                with col_signal2:
                    st.metric(
                        "신호 강도",
                        "{:.1f}".format(abs(trading_signals['signal_strength'])),
                        help="매매 신호의 강도 (0-10, 높을수록 강함)"
                    )
                
                with col_signal3:
                    # 백테스팅 결과가 있으면 실제 신뢰도 사용
                    if 'backtest_results' in locals() and backtest_results.get('backtesting_available'):
                        actual_confidence = backtest_results['confidence']
                        confidence_source = "실제 데이터"
                    else:
                        actual_confidence = trading_signals['confidence'] 
                        confidence_source = "이론적 계산"
                    
                    st.metric(
                        "신뢰도",
                        "{:.1f}%".format(actual_confidence),
                        help=f"신호의 신뢰도 ({confidence_source} 기반)"
                    )
                
                with col_signal4:
                    volatility = trading_signals.get('volatility', 0)
                    if volatility > 5:
                        risk_display = "높음"
                        risk_color = "🔴"
                    elif volatility > 3:
                        risk_display = "보통"
                        risk_color = "🟡"
                    else:
                        risk_display = "낮음"
                        risk_color = "🟢"
                    
                    st.metric(
                        "위험도",
                        "{} {}".format(risk_color, risk_display),
                        help="20일 변동성 기준 위험도 ({:.1f}%)".format(volatility)
                    )
                
                # 목표가 및 손절가 표시 (강한 신호가 아니어도 참고용으로 제공)
                st.markdown("### 💰 가격 목표 및 손절선")
                
                # 신호 강도별 안내 메시지
                signal_strength = trading_signals['signal_strength']
                if abs(signal_strength) >= 25:
                    price_guide_msg = "🟢 **강한 신호 - 적극적 진입 검토**"
                elif abs(signal_strength) >= 10:
                    price_guide_msg = "🟡 **약한 신호 - 신중한 접근 권장**"
                else:
                    price_guide_msg = "⚪ **관망 권장 - 아래는 참고용 가격대**"
                
                st.markdown(price_guide_msg)
                
                col_price1, col_price2, col_price3 = st.columns(3)
                
                with col_price1:
                    target1 = trading_signals['target_price_1']
                    price_type = "목표가" if signal_strength >= 0 else "하락 목표"
                    st.metric(
                        f"1차 {price_type}",
                        format_price(target1, selected_symbol),
                        "{:+.1f}%".format((target1 / current_price - 1) * 100),
                        help="현재 변동성 기준 단기 목표 가격"
                    )
                
                with col_price2:
                    target2 = trading_signals['target_price_2']
                    st.metric(
                        f"2차 {price_type}",
                        format_price(target2, selected_symbol),
                        "{:+.1f}%".format((target2 / current_price - 1) * 100),
                        help="현재 변동성 기준 확장 목표 가격"
                    )
                
                with col_price3:
                    stop_loss = trading_signals['stop_loss']
                    st.metric(
                        "손절가",
                        format_price(stop_loss, selected_symbol),
                        "{:+.1f}%".format((stop_loss / current_price - 1) * 100),
                        help="리스크 관리를 위한 손절 기준가"
                    )
                
                # 신호 강도별 추가 안내
                if abs(signal_strength) < 25:
                    st.info("""
                    **ℹ️ 현재 신호 강도가 임계값(25) 미달입니다.**
                    
                    **현재 상황:**
                    - 신호 강도: {:.1f} (임계값: 25)
                    - 상태: {} 
                    - 권장: 추가 조건 확인 후 진입 고려
                    
                    **확인 사항:**
                    - 거래량 증가 여부
                    - 20일 평균선과의 거리
                    - 최근 가격 안정성
                    - 변동성 수준
                    """.format(signal_strength, trading_signals['overall_signal']))
            else:
                st.info("🚦 매매 신호 분석: {}".format(trading_signals['message']))
        
        with tab5:
            st.subheader("📚 완전 초보자를 위한 투자 가이드")
            st.markdown("*투자가 처음이신가요? 걱정마세요! 차근차근 설명해드릴게요* 😊")
            
            # 1. 프로그램 소개
            with st.expander("🎯 이 프로그램이 무엇인가요? (꼭 읽어보세요!)", expanded=True):
                st.markdown("""
                ### 🤖 Smart Trading Dashboard란?
                
                **쉽게 말해서:** 주식을 언제 사고 팔지 도와주는 AI 도우미입니다!
                
                **🎯 누구에게 유용한가요?**
                - 📱 **1일~3개월 단기 투자**를 하시는 분
                - 📊 **기술적 분석**을 배우고 싶은 분
                - 🤖 **AI의 도움**을 받아 투자하고 싶은 분
                - 📈 **매매 타이밍**을 놓치기 싫은 분
                
                **❌ 이런 분들께는 맞지 않아요:**
                - 💰 **몇 년간 길게 투자**하려는 분 (장기투자)
                - 🏢 **기업의 재무제표**를 중심으로 투자하는 분
                - 📰 **뉴스나 공시** 위주로 투자하는 분
                
                ### 🚨 **매우 중요한 안내**
                이 도구는 **교육용**입니다. 실제 투자는 본인 판단으로 하세요!
                """)
            
            # 2. 처음 사용하는 방법
            with st.expander("🚀 처음 사용하는 방법 (단계별 가이드)", expanded=False):
                st.markdown("""
                ### 📝 **STEP 1: 종목 찾기**
                1. 왼쪽 사이드바에서 **"종목 검색"** 찾기
                2. 회사 이름이나 코드 입력 (예: 삼성전자, 005930, 애플, AAPL)
                3. 나타나는 목록에서 원하는 종목 선택
                
                ### 📊 **STEP 2: 차트 보기 (첫 번째 탭)**
                - **초록색 선**: 주가가 올라가고 있어요
                - **빨간색 선**: 주가가 내려가고 있어요  
                - **파란색 선**: 20일 평균 가격이에요
                
                ### ⚖️ **STEP 3: 점수 확인 (두 번째 탭)**
                - **70점 이상**: 좋은 종목일 가능성 높음 ✅
                - **50-70점**: 보통 종목 ⚠️
                - **50점 미만**: 주의 필요 ❌
                
                ### 🏭 **STEP 4: 업종 비교 (세 번째 탭)**
                - 같은 업종의 다른 회사들과 비교해요
                - **65점 이상**: 업종 내에서 좋은 편 ✅
                
                ### 🚦 **STEP 5: 매매 신호 (네 번째 탭)**
                - **강한 매수 🟢**: 사기 좋은 타이밍
                - **매수 🟡**: 조심스럽게 매수 고려
                - **관망 ⚪**: 지금은 기다리세요
                - **매도 🟠/🔴**: 팔기 좋은 타이밍
                """)
            
            # 3. 용어 설명 (초보자용)
            with st.expander("📖 주식 용어 쉽게 설명 (모르는 용어가 있다면 여기서!)", expanded=False):
                col_term1, col_term2 = st.columns(2)
                
                with col_term1:
                    st.markdown("""
                    ### 🔢 **기본 용어**
                    
                    **📈 현재가**: 지금 이 순간의 주식 가격
                    **📊 거래량**: 오늘 몇 주가 거래되었는지
                    **💹 시가총액**: 회사의 전체 가치
                    **📉 등락률**: 어제 대비 얼마나 올랐거나 떨어졌는지
                    
                    ### 🎯 **매매 용어**
                    
                    **🟢 매수**: 주식을 사는 것
                    **🔴 매도**: 주식을 파는 것  
                    **💰 목표가**: 이 가격까지 오르면 팔자!
                    **✂️ 손절가**: 이 가격까지 떨어지면 팔자! (손해 제한)
                    **📊 수익률**: 얼마나 돈을 벌었는지 (%)
                    """)
                
                with col_term2:
                    st.markdown("""
                    ### 📊 **기술적 지표 쉽게**
                    
                    **RSI**: 주식이 너무 많이 올랐는지 떨어졌는지 알려줌
                    - 70 이상: 너무 많이 올라서 조정받을 수 있음
                    - 30 이하: 너무 많이 떨어져서 반등할 수 있음
                    
                    **MACD**: 주식 흐름이 바뀌는 신호
                    - 위로 올라가면: 상승 신호
                    - 아래로 내려가면: 하락 신호
                    
                    **볼린저밴드**: 주식 가격이 정상 범위에 있는지 확인
                    - 위쪽 선 터치: 너무 높을 수 있음
                    - 아래쪽 선 터치: 너무 낮을 수 있음
                    
                    **이동평균선**: 최근 N일간의 평균 가격
                    - 주가가 평균선 위에: 상승 추세
                    - 주가가 평균선 아래: 하락 추세
                    """)
            
            # 4. 실전 사용법
            with st.expander("💡 실전에서 이렇게 사용하세요! (경험자 팁)", expanded=False):
                st.markdown("""
                ### 🎯 **좋은 매수 타이밍 찾는 법**
                
                **✅ 이런 조건들이 동시에 나타나면 좋아요:**
                1. **공정가치 점수 70점 이상** ⚖️
                2. **업종 점수 65점 이상** 🏭  
                3. **매매 신호가 "강한 매수" 또는 "매수"** 🟢🟡
                4. **신뢰도 60% 이상** 📊
                5. **RSI가 30-70 사이** (너무 극단적이지 않음)
                
                ### 🛡️ **리스크 관리 (가장 중요!)** 
                
                **💰 돈 관리:**
                - 전체 투자금의 **10-20%만** 한 종목에 투자
                - 잃어도 **생활에 지장 없는 돈**만 투자
                - **생활비, 비상금은 절대 건드리지 마세요**
                
                **✂️ 손절 규칙:**
                - 매수가 대비 **5-10% 손실**시 무조건 매도
                - 감정에 휩쓸리지 말고 **미리 정한 규칙** 지키기
                - "조금만 더 기다리면..."이라는 생각 금지 ⛔
                
                **🎯 목표 설정:**
                - **1차 목표**: 5-10% 수익 시 절반 매도
                - **2차 목표**: 15-20% 수익 시 나머지 매도
                - 욕심부리지 말고 **적당한 수익에서 매도**
                
                ### 📅 **언제 거래하면 좋을까요?**
                
                **⏰ 시간대:**
                - **오전 9:30-10:30**: 시장 개장 직후 (변동성 큼)
                - **오후 2:30-3:20**: 마감 전 (거래량 많음)
                - **점심시간**: 거래 적음, 큰 변화 없음
                
                **📅 요일:**
                - **월요일**: 주말 뉴스 반영으로 변동성 큼
                - **화-목요일**: 비교적 안정적
                - **금요일**: 주말 전 포지션 정리로 변동성 있음
                """)
            
            # 5. 자주 묻는 질문
            with st.expander("❓ 자주 묻는 질문 (FAQ)", expanded=False):
                st.markdown("""
                ### 🤔 **Q1: 이 프로그램만 믿고 투자해도 될까요?**
                **A1:** ❌ **절대 안됩니다!** 이 도구는 참고용일 뿐입니다. 
                - 다른 정보도 함께 확인하세요 (뉴스, 재무제표 등)
                - 본인만의 판단이 가장 중요합니다
                
                ### 💰 **Q2: 얼마부터 시작하면 좋을까요?**
                **A2:** 
                - **완전 초보**: 10-50만원으로 연습
                - **어느 정도 아시는 분**: 100-500만원  
                - **경험 있는 분**: 본인 여유자금의 20% 이내
                
                ### 📊 **Q3: 신호가 나와도 주가가 반대로 움직여요**
                **A3:** 정상입니다! 
                - **60-70% 확률**로 맞추는 것이 목표
                - **100% 맞는 도구는 세상에 없어요**
                - 손절 규칙을 지키는 것이 더 중요합니다
                
                ### ⏰ **Q4: 얼마나 자주 확인해야 하나요?**
                **A4:**
                - **데이 트레이딩**: 1-2시간마다
                - **스윙 트레이딩**: 하루 1-2번
                - **너무 자주 보면** 감정적 판단을 할 수 있어요
                
                ### 🏢 **Q5: 한국 주식과 미국 주식 차이가 있나요?**
                **A5:**
                - **한국 주식**: 원화 표시, 한국 시간
                - **미국 주식**: 달러 표시, 미국 시간 (밤 10:30-새벽 5:00)
                - **분석 방법은 동일**합니다
                """)
            
            # 6. 초보자 주의사항
            with st.expander("🚨 초보자가 꼭 알아야 할 주의사항", expanded=False):
                st.markdown("""
                ### ⛔ **절대 하지 마세요!**
                
                **💸 돈 관리 실수:**
                - 생활비나 대출받은 돈으로 투자 ❌
                - 한 종목에 모든 돈 투자 ❌  
                - 손실 보전하려고 더 큰 돈 투자 ❌
                
                **😰 감정적 판단:**
                - "이번만은 다를 거야" 생각 ❌
                - 손절가 정해놓고 지키지 않기 ❌
                - 남의 말만 믿고 투자하기 ❌
                
                **📱 중독적 행동:**
                - 하루 종일 주가만 보기 ❌
                - 손실 나면 밤잠 못 이루기 ❌
                - 투자 때문에 일상생활 방해받기 ❌
                
                ### ✅ **이렇게 해보세요!**
                
                **📚 학습:**
                - 매일 30분씩 투자 공부하기
                - 성공/실패 사례 기록하기
                - 투자 커뮤니티에서 정보 교환하기
                
                **💪 멘탈 관리:**
                - 손실도 학습의 일부라고 생각하기
                - 단기 결과에 일희일비하지 않기
                - 꾸준함이 가장 중요하다는 마음가짐
                
                **🎯 목표 설정:**
                - 월 수익률 목표: 5-10% (욕심내지 마세요)
                - 연 수익률 목표: 15-25%  
                - 장기적 관점에서 꾸준한 수익 추구
                """)
            
            # 7. 면책사항 (이해하기 쉽게)
            with st.expander("⚠️ 꼭 읽어보세요! (면책사항)", expanded=False):
                st.markdown("""
                ### 🚨 **정말 중요한 내용입니다!**
                
                **📚 이 프로그램은:**
                - ✅ **교육 목적**으로 만들어졌어요
                - ✅ **기술적 분석 학습**을 도와줘요  
                - ✅ **참고 자료**를 제공해요
                
                **❌ 이 프로그램은:**
                - ❌ **투자 권유가 아니에요**
                - ❌ **100% 정확하지 않아요**
                - ❌ **수익을 보장하지 않아요**
                
                ### 💰 **투자 결정은 본인 책임**
                
                - 이 도구의 분석을 참고만 하세요
                - **최종 결정은 본인이** 내리세요  
                - 손실이 발생해도 **본인 책임**입니다
                - **다양한 정보를 종합**해서 판단하세요
                
                ### 📊 **데이터 한계**
                
                - **15-20분 지연** 데이터 사용
                - **시스템 오류** 가능성 있음
                - **실제 거래 전** 최신 데이터 재확인 필수
                - **인터넷 연결 상태**에 따라 데이터 차이 있을 수 있음
                
                ### 🤝 **우리의 약속**  
                
                - 최선을 다해 정확한 정보 제공
                - 지속적인 개선과 업데이트
                - 사용자 안전을 최우선으로 고려
                - 투명하고 정직한 서비스 제공
                """)
            
            # 8. 연락처 및 피드백
            with st.expander("📞 문의사항이나 건의사항이 있으시면", expanded=False):
                st.markdown("""
                ### 💬 **소통 채널**
                
                **🐛 버그 신고:**
                [GitHub Issues](https://github.com/sang-su0916/smart-trading-system/issues)
                
                **💡 기능 제안:**  
                GitHub에서 새로운 기능을 제안해 주세요
                
                **📚 사용법 문의:**
                - 이 가이드를 먼저 읽어보세요
                - 자주 묻는 질문(FAQ) 확인해 보세요
                
                ### 🙏 **함께 만들어가요**
                
                이 도구는 여러분의 피드백으로 더 좋아집니다!
                - 사용하시면서 불편한 점
                - 추가되었으면 하는 기능  
                - 개선이 필요한 부분
                
                언제든지 의견을 보내주세요! 😊
                """)
            
            # 9. 향후 개선 계획
            with st.expander("🔮 앞으로 이런 기능들이 추가될 예정이에요", expanded=False):
                st.markdown("""
                ### 🚀 **개발 예정 기능**
                
                **📊 분석 기능 강화:**
                - 더 많은 기술적 지표 추가
                - 패턴 인식 AI 도입
                - 시장 심리 지표 연동
                
                **💼 포트폴리오 관리:**
                - 개인 보유 종목 관리
                - 수익률 계산 및 분석
                - 리스크 분산 도구
                
                **📰 정보 연동:**
                - 실시간 뉴스 분석
                - 공시 정보 알림
                - 경제 지표 연동
                
                **🎓 교육 콘텐츠:**
                - 투자 기초 강의
                - 실전 사례 분석
                - 전문가 인사이트
                
                ### 💡 **여러분의 아이디어를 기다려요!**
                
                어떤 기능이 있으면 좋을지 알려주세요.
                GitHub Issues에 제안해 주시면 검토 후 개발할게요!
                """)
    
    # 여기에 업종 비교 분석 부분을 탭3으로 이동해야 함 (별도 수정 필요)
        
        
    # 데이터가 비어있는 경우 처리
    if data.empty:
        error_message = "{} 데이터를 불러올 수 없습니다. 다른 종목을 선택해 주세요.".format(selected_name)
        st.error(error_message)
    
    # 푸터
    st.markdown("---")
    
    # 푸터 정보를 3개 컬럼으로 구성
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.markdown("""
        **📊 데이터 소스**
        - Yahoo Finance (해외 데이터)
        - pykrx (국내 종목)
        - 종합 분석 알고리즘
        """)
    
    with footer_col2:
        st.markdown("""
        **🔧 주요 기능**
        - 5가지 기술적 지표 분석
        - 업종별 비교 분석
        - 매매 신호 및 목표가 제시
        """)
    
    with footer_col3:
        st.markdown("""
        **⚠️ 투자 유의사항**
        - 교육용 도구입니다
        - 투자 결정은 신중히 하세요
        - 분산투자를 권장합니다
        """)
    
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #888; font-size: 0.9em;'>"
        "💼 Smart Trading Dashboard v4.0 | "
        "🤖 AI 기반 종합 투자 분석 도구 | "
        "📈 여러분의 현명한 투자를 응원합니다"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
