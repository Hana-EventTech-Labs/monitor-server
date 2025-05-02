import os
from dotenv import load_dotenv

load_dotenv() # .env 파일 로드

class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_NAME: str = os.getenv("DB_NAME", "monitor_db")

    ITEMS_TABLE_NAME: str = os.getenv("ITEMS_TABLE_NAME", "event")

    SERVER_TIMEZONE: str = os.getenv("SERVER_TIMEZONE", "Asia/Seoul")

    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "10"))
    OLD_DATA_THRESHOLD_MINUTES: int = int(os.getenv("OLD_DATA_THRESHOLD_MINUTES", "5"))

    MONITOR_COUNT: int = int(os.getenv("MONITOR_COUNT", "3"))
    # 모니터 수가 1보다 작으면 오류 발생
    if MONITOR_COUNT < 1:
         raise ValueError("MONITOR_COUNT must be at least 1.")

settings = Settings()