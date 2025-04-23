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

    while True:
        try:
            now = datetime.datetime.now()
            threshold_time = now - datetime.timedelta(minutes=settings.OLD_DATA_THRESHOLD_MINUTES)

            # DB에서 처리할 항목 조회 (state=0, 5분 경과)
            items_to_process = await get_items_to_process(threshold_time)

            if not items_to_process:
                # logger.info("No items found matching criteria.")
                pass # 너무 자주 찍힐 수 있으므로 주석 처리

            # 조회된 각 항목에 대해 순환적으로 모니터 ID 할당 및 DB 업데이트
            for item in items_to_process:
                item_no = item["no"]
                item_text = item["text"] # text는 여기서 직접 사용되진 않지만 조회 결과에 포함됨

                # 다음 모니터 ID 선택 (순환)
                # 모니터 ID는 1부터 시작한다고 가정
                current_monitor_id = str((monitor_index % num_monitors) + 1)
                monitor_index = (monitor_index + 1) % num_monitors # 다음 인덱스로 이동

                logger.info(f"Processing item '{item_no}' and assigning to monitor {current_monitor_id}")

                try:
                    # 데이터 처리 완료 및 모니터 ID 할당 상태로 DB 업데이트
                    await mark_item_processed_and_assign_monitor(item_no, current_monitor_id) # <--- DB 업데이트 함수 호출

                except Exception as e:
                     logger.error(f"An unexpected error occurred processing item '{item_no}' for monitor {current_monitor_id}: {e}")
                     # DB 업데이트 실패 시 state는 0으로 유지되어 다음 주기에서 다시 시도

        except asyncio.CancelledError:
            logger.info("Background worker cancelled (Assigning to Monitors).")
            break
        except Exception as e:
            logger.error(f"An error occurred in the background worker loop: {e}")

        # 다음 확인까지 대기
        await asyncio.sleep(settings.CHECK_INTERVAL_SECONDS)