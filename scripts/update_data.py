#!/usr/bin/env python3
"""
데이터베이스 자동 업데이트 스크립트
매일 실행하여 주가 데이터를 최신으로 유지
"""
import sys
import os
from datetime import datetime
import logging

# 상위 디렉토리 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database.database_manager import DatabaseManager
from src.database.market_data_service import MarketDataService

def setup_logging():
    """로깅 설정"""
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'update_data_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def update_database():
    """데이터베이스 업데이트"""
    logger = setup_logging()
    
    try:
        logger.info("=== 데이터베이스 업데이트 시작 ===")
        
        # 데이터베이스 및 서비스 초기화
        db_manager = DatabaseManager('data/trading_system.db')
        market_service = MarketDataService('data/trading_system.db')
        
        # 현재 저장된 종목 리스트 조회
        symbols = db_manager.get_available_symbols()
        
        if not symbols:
            logger.warning("업데이트할 종목이 없습니다.")
            
            # 기본 종목 추가
            default_symbols = [
                "005930.KS",  # 삼성전자
                "000660.KS",  # SK하이닉스
                "035420.KS",  # 네이버
                "005380.KS",  # 현대차
                "055550.KS",  # 신한지주
                "105560.KS",  # KB금융
                "012330.KS",  # 현대모비스
                "028260.KS",  # 삼성물산
                "017670.KS",  # SK텔레콤
                "051910.KS"   # LG화학
            ]
            
            logger.info(f"기본 종목 {len(default_symbols)}개 데이터 수집 시작")
            results = market_service.collect_and_store_data(default_symbols, period="1y")
            
        else:
            logger.info(f"기존 종목 {len(symbols)}개 데이터 업데이트 시작")
            results = market_service.update_latest_data(symbols)
        
        # 결과 요약
        total_symbols = len(results) if results else 0
        success_count = sum(results.values()) if results else 0
        fail_count = total_symbols - success_count
        
        logger.info(f"업데이트 완료: 성공 {success_count}개, 실패 {fail_count}개")
        
        # 성공/실패 상세
        if results:
            for symbol, success in results.items():
                status = "✅" if success else "❌"
                logger.info(f"  {status} {symbol}")
        
        # 데이터베이스 상태 확인
        status = market_service.get_data_status()
        logger.info(f"데이터베이스 상태: {status.get('status', 'unknown')}")
        logger.info(f"총 종목 수: {status.get('total_symbols', 0)}")
        
        # 오래된 데이터 정리 (옵션)
        if status.get('outdated_symbols', 0) > 0:
            logger.info("오래된 데이터 정리 시작...")
            cleanup_result = market_service.cleanup_old_data(days_to_keep=365)  # 1년 데이터만 보관
            if cleanup_result:
                logger.info("데이터 정리 완료")
        
        logger.info("=== 데이터베이스 업데이트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"업데이트 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """메인 실행 함수"""
    success = update_database()
    
    if success:
        print("✅ 데이터 업데이트 성공")
        sys.exit(0)
    else:
        print("❌ 데이터 업데이트 실패")
        sys.exit(1)

if __name__ == "__main__":
    main()