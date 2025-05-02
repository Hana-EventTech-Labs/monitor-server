# app/routers/monitors.py
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from ..database import get_latest_processed_item_by_monitor_id, get_latest_two_processed_items_by_monitor_id # 새 DB 함수 임포트
from ..core.config import settings # settings 임포트
import json
import asyncio

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
        html_content = "<html><body><h1>Waiting for content...</h1></body></html>" # 기본 내용
        
        # 모니터에 최신 항목만 표시
        item = await get_latest_processed_item_by_monitor_id(str(monitor_id))
        
        if item:
            # HTML 컨텐츠 작성
            html_content = """
            <html>
            <head>
                <title>Monitor Display</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 0; 
                        padding: 0; 
                        background-color: #ffffff;
                        color: #000000;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                    }
                    .container {
                        width: 80%;
                        padding: 40px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        background-color: #ffffff;
                        overflow: hidden;
                        box-sizing: border-box;
                        text-align: center;
                    }
                    h1 { 
                        font-size: 4rem; 
                        margin: 0 0 30px 0;
                        color: #000000;
                    }
                    p { 
                        margin: 5px 0; 
                        font-size: 1.5rem;
                        color: #555555;
                    }
                    .monitor-info {
                        position: fixed;
                        bottom: 10px;
                        right: 10px;
                        font-size: 1rem;
                        color: #999999;
                    }
                </style>
            </head>
            <body>
            <div class="container">
            """
            
            # 최신 항목만 표시
            html_content += f"""
                <h1>{item['text']}</h1>
                <p>Order: {str(item['no'])}</p>
                <p>Processed at: {item['get_time'].isoformat()}</p>
            </div>
            <div class="monitor-info">Monitor {monitor_id}</div>
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

@router.get("/{monitor_id}/stream")
async def stream_monitor_updates(monitor_id: int):
    """모니터 데이터의 실시간 업데이트를 위한 SSE 스트림"""
    
    async def event_generator():
        last_item = None
        while True:
            # 항상 최신 항목 하나만 표시
            item = await get_latest_processed_item_by_monitor_id(str(monitor_id))
            if item and item != last_item:
                yield f"data: {json.dumps(item, default=str)}\n\n"
                last_item = item
                    
            await asyncio.sleep(1)  # 1초 간격으로 확인
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )