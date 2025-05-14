import os
from dotenv import load_dotenv
import logging

# .env 파일 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

class Settings:
    # 데이터베이스 설정
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_NAME: str = os.getenv("DB_NAME", "monitor_db")

    # 테이블 설정
    ITEMS_TABLE_NAME: str = os.getenv("ITEMS_TABLE_NAME", "event")

    # 시간대 설정
    SERVER_TIMEZONE: str = os.getenv("SERVER_TIMEZONE", "Asia/Seoul")

    # 워커 설정
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "10"))
    OLD_DATA_THRESHOLD_MINUTES: float = float(os.getenv("OLD_DATA_THRESHOLD_MINUTES", "5"))

    # 모니터 설정
    MONITOR_COUNT: int = int(os.getenv("MONITOR_COUNT", "3"))
    
    def __init__(self):
        # 설정 유효성 검사
        self._validate_settings()
        # 설정 로깅
        self._log_settings()
    
    def _validate_settings(self):
        """설정값 유효성 검사"""
        # 모니터 수가 1보다 작으면 오류 발생
        if self.MONITOR_COUNT < 1:
            raise ValueError("MONITOR_COUNT must be at least 1.")
        
        # 체크 간격이 너무 짧으면 경고
        if self.CHECK_INTERVAL_SECONDS < 5:
            logger.warning(f"CHECK_INTERVAL_SECONDS is set to {self.CHECK_INTERVAL_SECONDS}, which might be too short.")
        
        # 데이터 임계값이 너무 작으면 경고
        if self.OLD_DATA_THRESHOLD_MINUTES < 0.1:
            logger.warning(f"OLD_DATA_THRESHOLD_MINUTES is set to {self.OLD_DATA_THRESHOLD_MINUTES}, which might be too short.")
    
    def _log_settings(self):
        """현재 설정 로깅"""
        logger.info("=== 애플리케이션 설정 ===")
        logger.info(f"데이터베이스: {self.DB_NAME} @ {self.DB_HOST}:{self.DB_PORT}")
        logger.info(f"테이블: {self.ITEMS_TABLE_NAME}")
        logger.info(f"시간대: {self.SERVER_TIMEZONE}")
        logger.info(f"모니터 수: {self.MONITOR_COUNT}")
        logger.info(f"체크 간격: {self.CHECK_INTERVAL_SECONDS}초")
        logger.info(f"데이터 임계값: {self.OLD_DATA_THRESHOLD_MINUTES}분")
        logger.info("=====================")

# 설정 인스턴스 생성
settings = Settings()