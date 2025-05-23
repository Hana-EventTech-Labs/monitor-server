import asyncio
import datetime
import logging
# DB 함수 임포트 변경: get_items_to_process와 mark_item_processed_and_assign_monitor 사용
from ..database import get_items_to_process, mark_item_processed_and_assign_monitor
from ..core.config import settings # settings 임포트

logger = logging.getLogger(__name__)

async def check_and_assign_data_worker(): # 함수 이름 변경 (전송 -> 할당)
    """
    주기적으로 DB를 확인하여 조건을 만족하는 데이터를 찾아 모니터에 할당하고 상태를 업데이트합니다.
    """
    logger.info(f"Background worker started (Assigning to Monitors). Checking every {settings.CHECK_INTERVAL_SECONDS} seconds.")

    num_monitors = settings.MONITOR_COUNT
    if num_monitors == 0:
        logger.error("No monitor count configured. Background worker cannot assign data.")
        return # 워커 실행 중지

    # 모니터 순환을 위한 인덱스 (워커 실행마다 초기화)
    # 여러 워커 인스턴스가 실행되지 않는다고 가정 (단일 프로세스)
    monitor_index = 0
    
    # 워커 활동 추적을 위한 카운터 변수들
    check_count = 0
    last_heartbeat_time = datetime.datetime.now()
    total_items_processed = 0
    
    # 이미 처리한 항목의 ID를 추적하기 위한 세트
    recently_processed_items = set()
    # 세트 크기 제한 (메모리 사용 제한)
    MAX_RECENT_ITEMS = 1000
    # 하트비트 로그 간격 설정 (초)
    HEARTBEAT_INTERVAL = 300  # 5분마다 하트비트 로그 출력 (1분에서 5분으로 변경)

    while True:
        try:
            check_count += 1
            if settings.SERVER_TIMEZONE == "Asia/Seoul":
                now = datetime.datetime.now()
            else:
                now = datetime.datetime.now() + datetime.timedelta(hours=9)
            threshold_time = now - datetime.timedelta(minutes=settings.OLD_DATA_THRESHOLD_MINUTES)

            # 주기적으로 워커가 살아있음을 알리는 하트비트 로그 (5분마다)
            if (now - last_heartbeat_time).total_seconds() >= HEARTBEAT_INTERVAL:
                logger.info(f"Worker heartbeat: Active for {check_count} checks, processed {total_items_processed} items so far {now}, threshold_time: {threshold_time}")
                last_heartbeat_time = now

            # DB에서 처리할 항목 조회 (state=0, 5분 경과)
            try:
                items_to_process = await get_items_to_process(threshold_time)
            except Exception as e:
                logger.error(f"Error fetching items to process: {e}")
                items_to_process = []

            if items_to_process:
                logger.info(f"Found {len(items_to_process)} items to process")
            else:
                # 30회 체크마다 한 번씩 로그 출력 (너무 많은 로그 방지)
                if check_count % 30 == 0:
                    logger.info(f"Worker check #{check_count}: No items found matching criteria")

            # 조회된 각 항목에 대해 순환적으로 모니터 ID 할당 및 DB 업데이트
            for item in items_to_process:
                item_no = item["no"]
                
                # 이미 최근에 처리한 항목이면 건너뛰기
                if item_no in recently_processed_items:
                    logger.info(f"Skipping already processed item '{item_no}' (duplicate detection)")
                    continue
                
                item_update_time = item["update_time"]
                item_text = item["text"] # text는 여기서 직접 사용되진 않지만 조회 결과에 포함됨

                # 다음 모니터 ID 선택 (순환)
                # 모니터 ID는 1부터 시작한다고 가정
                current_monitor_id = str((monitor_index % num_monitors) + 1)
                monitor_index = (monitor_index + 1) % num_monitors # 다음 인덱스로 이동

                logger.info(f"Processing item '{item_no}' (update_time: {item_update_time}) and assigning to monitor {current_monitor_id}")

                try:
                    # 데이터 처리 완료 및 모니터 ID 할당 상태로 DB 업데이트
                    success = await mark_item_processed_and_assign_monitor(item_no, current_monitor_id) # <--- DB 업데이트 함수 호출
                    
                    if not success:
                        logger.warning(f"Item {item_no} could not be processed - skipping")
                        continue
                    
                    # 처리 성공 시 최근 처리 항목 목록에 추가
                    recently_processed_items.add(item_no)
                    # 세트 크기 제한
                    if len(recently_processed_items) > MAX_RECENT_ITEMS:
                        # 가장 오래된 항목 제거 (세트에서는 순서가 없으므로 아무 항목이나 제거)
                        recently_processed_items.pop()
                    
                    total_items_processed += 1
                    logger.info(f"✅ Successfully assigned item '{item_no}' to monitor {current_monitor_id}")

                except Exception as e:
                     logger.error(f"An unexpected error occurred processing item '{item_no}' for monitor {current_monitor_id}: {e}")
                     # DB 업데이트 실패 시 state는 0으로 유지되어 다음 주기에서 다시 시도

        except asyncio.CancelledError:
            logger.info("Background worker cancelled (Assigning to Monitors).")
            break
        except Exception as e:
            logger.error(f"An error occurred in the background worker loop: {e}")
            # 치명적인 오류가 발생했음을 눈에 띄게 로깅
            logger.error("⚠️ WORKER ERROR: Background worker encountered an error but will continue running")

        # 다음 확인까지 대기
        await asyncio.sleep(settings.CHECK_INTERVAL_SECONDS)