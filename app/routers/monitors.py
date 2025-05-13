# app/routers/monitors.py
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from ..database import get_latest_processed_item_by_monitor_id, get_latest_two_processed_items_by_monitor_id, get_assigned_items_queue, get_new_items_for_monitor # 새 DB 함수 임포트
from ..core.config import settings # settings 임포트
import json
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# 중앙 서버의 템플릿 디렉토리를 지정
# main.py 파일과 같은 레벨에 monitor_templates 디렉토리가 있다고 가정
templates = Jinja2Templates(directory="monitor_templates")

router = APIRouter(
    prefix="/monitor", # 예: /monitor/1, /monitor/2, /monitor/3
    tags=["monitors"],
)

# 모니터별 현재 표시 중인 항목과 큐를 저장하는 전역 변수
MONITOR_QUEUES: Dict[str, List[dict]] = {}  # 모니터별 표시할 항목 큐
CURRENT_ITEMS: Dict[str, Optional[dict]] = {}  # 모니터별 현재 표시 중인 항목
DISPLAY_TIMES: Dict[str, float] = {}  # 모니터별 항목 표시 시작 시간
LAST_DISPLAYED_ITEMS: Dict[str, int] = {}  # 모니터별 마지막으로 표시된 항목의 no값

# 항목 표시 시간(초)
ITEM_DISPLAY_DURATION = 20  # 각 항목이 표시되는 시간(초)
NO_NEW_ITEMS_DISPLAY_DURATION = 5  # 새 항목이 없을 때 표시 시간(초)

@router.get("/{monitor_id}/", response_class=HTMLResponse)
async def display_for_monitor(monitor_id: int, request: Request): # monitor_id를 int로 받음
    """
    특정 모니터 ID에 할당된 최신 데이터를 HTML 페이지로 표시합니다.
    """
    # 모니터 ID 유효성 검사
    if not (1 <= monitor_id <= settings.MONITOR_COUNT):
         raise HTTPException(status_code=404, detail=f"Monitor ID {monitor_id} not found. Valid IDs are 1 to {settings.MONITOR_COUNT}.")

    try:
        # 템플릿을 바로 사용하여 HTML 렌더링
        return templates.TemplateResponse(
            "display.html", 
            {"request": request, "monitor_id": monitor_id}
        )
    except Exception as e:
         logger.error(f"Error rendering monitor display for {monitor_id}: {e}")
         # 실제 에러 메시지를 클라이언트에 노출하지 않도록 주의
         raise HTTPException(status_code=500, detail="Internal Server Error while fetching data")

async def update_monitor_queue(monitor_id: str):
    """모니터의 항목 큐를 업데이트합니다"""
    try:
        # 마지막으로 표시된 항목의 no 값 가져오기 (없으면 0으로 기본값 설정)
        last_item_no = LAST_DISPLAYED_ITEMS.get(monitor_id, 0)
        
        # DB에서 마지막으로 표시된 항목 이후의 항목들만 가져오기
        items = await get_new_items_for_monitor(monitor_id, last_item_no, limit=20)
        
        if items:
            MONITOR_QUEUES[monitor_id] = items
            logger.info(f"Updated queue for monitor {monitor_id} with {len(items)} items (after item no: {last_item_no})")
        else:
            MONITOR_QUEUES[monitor_id] = []
            logger.info(f"No new items found for monitor {monitor_id}")
    except Exception as e:
        logger.error(f"Error updating queue for monitor {monitor_id}: {e}")

async def get_next_item_for_monitor(monitor_id: str) -> Optional[dict]:
    """모니터의 큐에서 다음 항목을 가져옵니다"""
    
    # 큐가 없거나 비어있으면 업데이트
    if monitor_id not in MONITOR_QUEUES or not MONITOR_QUEUES[monitor_id]:
        await update_monitor_queue(monitor_id)
    
    # 큐에 항목이 있으면 첫 번째 항목 반환
    queue = MONITOR_QUEUES.get(monitor_id, [])
    if queue:
        return queue[0]  # 첫 번째 항목 반환 (아직 제거하지 않음)
    return None

async def advance_monitor_queue(monitor_id: str):
    """모니터의 큐에서 현재 항목을 제거하고 다음 항목으로 이동합니다"""
    if monitor_id in MONITOR_QUEUES and MONITOR_QUEUES[monitor_id]:
        # 현재 항목의 no 값을 저장 (마지막으로 표시된 항목으로 기록)
        current_item = MONITOR_QUEUES[monitor_id][0]
        if current_item and 'no' in current_item:
            LAST_DISPLAYED_ITEMS[monitor_id] = current_item['no']
            logger.info(f"Recorded last displayed item for monitor {monitor_id}: item no {current_item['no']}")
        
        # 첫 번째 항목 제거
        MONITOR_QUEUES[monitor_id].pop(0)
        logger.info(f"Advanced queue for monitor {monitor_id}, {len(MONITOR_QUEUES[monitor_id])} items left")
        
        # 큐가 비었으면 다시 로드
        if not MONITOR_QUEUES[monitor_id]:
            await update_monitor_queue(monitor_id)

@router.get("/{monitor_id}/stream")
async def stream_monitor_updates(monitor_id: int):
    """모니터 데이터의 실시간 업데이트를 위한 SSE 스트림"""
    monitor_id_str = str(monitor_id)
    
    # 모니터 큐 초기화
    if monitor_id_str not in MONITOR_QUEUES:
        await update_monitor_queue(monitor_id_str)
    
    async def event_generator():
        while True:
            current_time = time.time()
            
            # 현재 항목이 표시된 시간을 가져옴
            display_time = DISPLAY_TIMES.get(monitor_id_str, 0)
            
            # 현재 표시 중인 항목이 새 항목이 없는 경우인지 확인
            is_no_new_items = (monitor_id_str in CURRENT_ITEMS and 
                              not MONITOR_QUEUES.get(monitor_id_str, []))
            
            # 적용할 표시 시간 결정
            display_duration = NO_NEW_ITEMS_DISPLAY_DURATION if is_no_new_items else ITEM_DISPLAY_DURATION
            
            # 현재 항목이 지정된 시간을 초과했는지 확인
            if (monitor_id_str in CURRENT_ITEMS and 
                monitor_id_str in DISPLAY_TIMES and 
                current_time - display_time >= display_duration):
                
                # 다음 항목으로 이동 (항상 큐를 진행)
                await advance_monitor_queue(monitor_id_str)
                
                # 새 항목을 검색하기 위해 큐 업데이트
                await update_monitor_queue(monitor_id_str)
                
                # 큐가 비어있고 현재 항목이 있으면 현재 항목을 유지 (새 항목이 없을 때)
                if not MONITOR_QUEUES.get(monitor_id_str, []) and monitor_id_str in CURRENT_ITEMS and CURRENT_ITEMS[monitor_id_str]:
                    # 표시 시간만 리셋
                    DISPLAY_TIMES[monitor_id_str] = current_time
                    logger.info(f"No new items for monitor {monitor_id_str}, continuing to display current item {CURRENT_ITEMS[monitor_id_str]['no']} for {NO_NEW_ITEMS_DISPLAY_DURATION} seconds")
                else:
                    # 대기열에 항목이 있으면 현재 항목 초기화 (다음 항목을 표시하기 위해)
                    CURRENT_ITEMS[monitor_id_str] = None
            
            # 표시할 항목이 없으면 다음 항목 가져오기
            if monitor_id_str not in CURRENT_ITEMS or CURRENT_ITEMS[monitor_id_str] is None:
                next_item = await get_next_item_for_monitor(monitor_id_str)
                
                if next_item:
                    CURRENT_ITEMS[monitor_id_str] = next_item
                    DISPLAY_TIMES[monitor_id_str] = current_time
                    logger.info(f"Now displaying item {next_item['no']} on monitor {monitor_id_str}")
            
            # SSE 이벤트로 현재 항목 전송
            current_item = CURRENT_ITEMS.get(monitor_id_str)
            
            if current_item:
                # 현재 표시 중인 항목이 새 항목이 없는 경우인지 다시 확인
                is_no_new_items = not MONITOR_QUEUES.get(monitor_id_str, [])
                # 적용할 표시 시간 결정
                display_duration = NO_NEW_ITEMS_DISPLAY_DURATION if is_no_new_items else ITEM_DISPLAY_DURATION
                
                # 남은 표시 시간 계산
                elapsed_time = current_time - DISPLAY_TIMES.get(monitor_id_str, current_time)
                remaining_time = max(0, display_duration - elapsed_time)
                
                response_data = {
                    "item": current_item,
                    "remaining_time": remaining_time,
                    "queue_length": len(MONITOR_QUEUES.get(monitor_id_str, []))
                }
            else:
                response_data = {
                    "item": None,
                    "remaining_time": 0,
                    "queue_length": len(MONITOR_QUEUES.get(monitor_id_str, []))
                }
                
            yield f"data: {json.dumps(response_data, default=str)}\n\n"
            await asyncio.sleep(1)  # 1초 간격으로 업데이트
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )