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
    모니터가 1개일 경우 최신 데이터와 이전 데이터를 함께 표시합니다.
    """
    # 모니터 ID 유효성 검사
    if not (1 <= monitor_id <= settings.MONITOR_COUNT):
         raise HTTPException(status_code=404, detail=f"Monitor ID {monitor_id} not found. Valid IDs are 1 to {settings.MONITOR_COUNT}.")

    try:
        html_content = "<html><body><h1>Waiting for content...</h1></body></html>" # 기본 내용
        
        # 모니터가 1개인 경우 최신 2개 항목 표시
        if settings.MONITOR_COUNT == 1:
            items = await get_latest_two_processed_items_by_monitor_id(str(monitor_id))
            
            if items and len(items) > 0:
                # HTML 컨텐츠 시작
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
                        }
                        .container {
                            display: flex;
                            height: 100vh;
                            width: 100%;
                        }
                        .previous-item,
                        .current-item { 
                            flex: 1;
                            padding: 40px; 
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            background-color: #ffffff;
                            overflow: hidden;
                            box-sizing: border-box;
                        }
                        .previous-item {
                            border-right: 1px solid #dddddd;
                        }
                        h1, h2 { 
                            font-size: 3rem; 
                            margin: 0 0 20px 0; 
                        }
                        h1 { color: #000000; }
                        h2 { color: #333333; }
                        p { 
                            margin: 5px 0; 
                            font-size: 1.2rem;
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
                
                # 이전 항목 (왼쪽에 표시, 있는 경우)
                if len(items) > 1:
                    previous_item = items[1]
                    html_content += f"""
                    <div class="previous-item">
                        <h2>{previous_item['text']}</h2>
                        <p>Order: {str(previous_item['no'])}</p>
                        <p>Processed at: {previous_item['get_time'].isoformat()}</p>
                    </div>
                    """
                else:
                    # 이전 항목이 없는 경우 빈 왼쪽 패널
                    html_content += """
                    <div class="previous-item">
                        <h2>이전 항목 없음</h2>
                    </div>
                    """
                
                # 최신 항목 (오른쪽에 표시)
                current_item = items[0]
                html_content += f"""
                <div class="current-item">
                    <h1>{current_item['text']}</h1>
                    <p>Order: {str(current_item['no'])}</p>
                    <p>Processed at: {current_item['get_time'].isoformat()}</p>
                </div>
                """
                
                html_content += f"""
                </div>
                <div class="monitor-info">Monitor {monitor_id}</div>
                </body>
                </html>
                """
            else:
                logger.info(f"No items found for monitor {monitor_id} yet.")
        else:
            # 기존 코드: 하나의 항목만 표시
            item = await get_latest_processed_item_by_monitor_id(str(monitor_id))
            
            if item:
                 # 조회된 데이터로 HTML 콘텐츠 생성
                 html_content = f"""
                 <html>
                 <head><title>Monitor {monitor_id} Display</title></head>
                 <body>
                     <h1>{item['text']}</h1>
                     <p>Order: {str(item['no'])}</p>
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

@router.get("/{monitor_id}/stream")
async def stream_monitor_updates(monitor_id: int):
    """모니터 데이터의 실시간 업데이트를 위한 SSE 스트림"""
    
    async def event_generator():
        last_item = None
        while True:
            # 모니터가 1개인 경우
            if settings.MONITOR_COUNT == 1:
                items = await get_latest_two_processed_items_by_monitor_id(str(monitor_id))
                if items and len(items) > 0:
                    current_item = {
                        "current": items[0],
                        "previous": items[1] if len(items) > 1 else None
                    }
                    
                    if current_item != last_item:
                        yield f"data: {json.dumps(current_item, default=str)}\n\n"
                        last_item = current_item
            else:
                # 일반 모니터 (단일 항목 표시)
                item = await get_latest_processed_item_by_monitor_id(str(monitor_id))
                if item and item != last_item:
                    yield f"data: {json.dumps(item, default=str)}\n\n"
                    last_item = item
                    
            await asyncio.sleep(1)  # 1초 간격으로 확인
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )