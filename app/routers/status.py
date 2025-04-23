import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["status"],
)

@router.get("/")
async def read_root():
    """서버 상태 확인용 루트 엔드포인트"""
    return {"message": "Monitor Data Server is running"}

@router.post("/mock_monitor_endpoint/")
async def mock_monitor_endpoint(request: Request):
    """
    모니터 역할을 하는 가상 엔드포인트입니다.
    서버로부터 POST된 HTML 콘텐츠를 받아서 로그로 출력합니다.
    """
    content = await request.body()
    content_str = content.decode('utf-8')
    logger.info(f"Received data at mock monitor endpoint:")
    logger.info("--- HTML Content Start ---")
    logger.info(content_str)
    logger.info("--- HTML Content End ---")
    return {"status": "received"}