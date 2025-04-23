# app/routers/monitors.py
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..database import get_latest_processed_item_by_monitor_id # 새로 추가된 DB 함수 임포트
from ..core.config import settings # settings 임포트

logger = logging.getLogger(__name__)

# 중앙 서버의 템플릿 디렉토리를 지정
# main.py 파일과 같은 레벨에 monitor_templates 디렉토리가 있다고 가정
templates = Jinja2Templates(directory="monitor_templates")

router = APIRouter(
    prefix="/monitor", # 예: /monitor/1, /monitor/2, /monitor/3
    tags=["monitors"],
)

@router.get("/{monitor_id}/", response_class=HTMLResponse)
async def display_for_monitor(monitor_id: int, request: Request): # monitor_id를 int로 받음
    """
    특정 모니터 ID에 할당된 최신 데이터를 HTML 페이지로 표시합니다.
    """
    # 모니터 ID 유효성 검사
    if not (1 <= monitor_id <= settings.MONITOR_COUNT):
         raise HTTPException(status_code=404, detail=f"Monitor ID {monitor_id} not found. Valid IDs are 1 to {settings.MONITOR_COUNT}.")

    try:
        # DB에서 해당 모니터 ID에 할당된 최신 데이터 조회
        # DB 함수는 문자열 ID를 받으므로 변환
        item = await get_latest_processed_item_by_monitor_id(str(monitor_id))

        html_content = "<html><body><h1>Waiting for content...</h1></body></html>" # 기본 내용
        if item:
             # 조회된 데이터로 HTML 콘텐츠 생성
             html_content = f"""
             <html>
             <head><title>Monitor {monitor_id} Display</title></head>
             <body>
                 <h1>Order: {str(item['no'])}</h1>
                 <p>{item['text']}</p>
                 <p>Processed at: {item['get_time'].isoformat()}</p>
                 <p>Displayed for Monitor {monitor_id}</p>
             </body>
             </html>
             """
        else:
             logger.info(f"No item found for monitor {monitor_id} yet.")


        # 템플릿을 사용하여 HTML 렌더링
        return templates.TemplateResponse(
            "display.html", # 중앙 서버의 템플릿 사용
            {"request": request, "html_content": html_content, "monitor_id": monitor_id} # 템플릿에 monitor_id 전달 가능
        )

    except Exception as e:
         logger.error(f"Error rendering monitor display for {monitor_id}: {e}")
         # 실제 에러 메시지를 클라이언트에 노출하지 않도록 주의
         raise HTTPException(status_code=500, detail="Internal Server Error while fetching data")