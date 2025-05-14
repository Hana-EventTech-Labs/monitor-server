import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .core.config import settings

# 로깅 설정 (main에서 하는 것이 일반적)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 모듈 임포트
# database에서 create_items_table 임포트는 이제 불필요
from .database import create_db_pool, close_db_pool # create_items_table 임포트 제거
# 워커 함수 이름 변경되었으므로 임포트도 변경
from .internal.worker import check_and_assign_data_worker # <-- 함수 이름 변경
from .routers import items, status, monitors # ***monitors 라우터 임포트***

# 백그라운드 작업 변수
background_task = None

# FastAPI Lifespan 컨텍스트 매니저
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행될 작업을 정의합니다."""
    logger.info("App starting up...")

    # 1. MariaDB 연결 풀 초기화
    await create_db_pool()
    logger.info("MariaDB pool created.")

    # 2. 데이터베이스 테이블 확인/생성 단계 제거
    # await create_items_table() # <-- 이 줄을 제거합니다.
    logger.info(f"Assuming database table '{settings.ITEMS_TABLE_NAME}' already exists.") # 로그 메시지 변경

    # 3. 백그라운드 작업 시작 (함수 이름 변경)
    global background_task
    background_task = asyncio.create_task(check_and_assign_data_worker()) # <-- 함수 이름 변경
    logger.info("Background worker task started.")

    # 애플리케이션이 실행되는 동안 대기
    yield

    # 4. 애플리케이션 종료 시 정리 작업
    logger.info("App shutting down...")

    # 백그라운드 작업 취소 및 완료 대기
    if background_task and not background_task.done():
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Background worker task successfully cancelled.")

    # MariaDB 연결 풀 종료
    await close_db_pool()
    logger.info("MariaDB pool closed.")

    logger.info("App shut down complete.")


# FastAPI 애플리케이션 인스턴스 생성 (lifespan 적용)
app = FastAPI(lifespan=lifespan)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")

# 라우터 포함
app.include_router(status.router) # 상태 확인 및 모의 엔드포인트
app.include_router(items.router)  # 데이터 추가/조회 엔드포인트
app.include_router(monitors.router) # ***새 라우터 포함***

# 모니터 라우터 초기화 함수 호출
@app.on_event("startup")
async def app_startup():
    """애플리케이션 시작 시 모니터 초기화를 수행합니다."""
    from .routers.monitors import initialize_monitor_state
    await initialize_monitor_state()
    logger.info("모니터 상태가 초기화되었습니다.")