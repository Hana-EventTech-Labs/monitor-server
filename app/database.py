import aiomysql
import logging
import datetime
from .core.config import settings

logger = logging.getLogger(__name__)

# 연결 풀 변수
DB_POOL = None

# ... (create_db_pool, close_db_pool, get_db_connection 함수는 동일) ...
async def create_db_pool():
    """데이터베이스 연결 풀을 생성합니다."""
    global DB_POOL
    if DB_POOL is None:
        try:
            DB_POOL = await aiomysql.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                db=settings.DB_NAME,
                autocommit=False,
                charset='utf8mb4',
                cursorclass=aiomysql.cursors.DictCursor,
                minsize=1,
                maxsize=10,
            )
            logger.info("MariaDB connection pool created successfully.")
        except Exception as e:
            logger.error(f"Failed to create MariaDB connection pool: {e}")
            raise

async def close_db_pool():
    """데이터베이스 연결 풀을 종료합니다."""
    global DB_POOL
    if DB_POOL:
        DB_POOL.close()
        await DB_POOL.wait_closed()
        DB_POOL = None
        logger.info("MariaDB pool closed.")

async def get_db_connection():
    """연결 풀에서 연결을 가져와 반환합니다."""
    if DB_POOL is None:
         await create_db_pool() # 안전 장치 (lifespan에서 먼저 호출되어야 함)
    conn = await DB_POOL.acquire()
    return conn


# --- insert_item_db 함수 수정: no 인자 제거, 쿼리에서 no 컬럼 생략, LAST_INSERT_ID 가져오기 ---
async def insert_item_db(text: str):
    """새로운 데이터를 DB에 추가합니다 (no 자동 생성, adr 나중, update_time 트리거)."""
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # no 컬럼을 INSERT 목록에서 제거
            await cur.execute(f"""
                INSERT INTO {settings.ITEMS_TABLE_NAME} (text, adr, state)
                VALUES (%s, %s, %s)
            """, (text, None, 0)) # no 값 제거

            # 삽입된 row의 자동 생성된 PK (no) 값 가져오기
            await cur.execute("SELECT LAST_INSERT_ID()")
            result = await cur.fetchone()
            inserted_id = result['LAST_INSERT_ID()'] # 결과에서 값 추출
            await conn.commit() # 커밋은 마지막에 한 번만

            logger.info(f"Inserted item with auto-generated no: {inserted_id}")
            return inserted_id # 삽입된 no 값 반환
    except Exception as e:
        logger.error(f"Error inserting item: {e}")
        if conn: await conn.rollback() # 오류 시 롤백
        raise
    finally:
        if conn: await DB_POOL.release(conn) # 연결 풀에 반환


# --- get_items_to_process 함수 수정 없음 (adr은 조회해도 되지만 사용 안함) ---
async def get_items_to_process(threshold_time: datetime.datetime):
    """state=0 이고 update_time 이 임계값보다 오래된 데이터를 조회합니다."""
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            await cur.execute(f"""
                SELECT no, text, adr, update_time -- update_time 컬럼 추가
                FROM {settings.ITEMS_TABLE_NAME}
                WHERE state = 0 AND update_time < %s
                ORDER BY update_time ASC
            """, (threshold_time,))
            items = await cur.fetchall()
            return items
    except Exception as e:
        logger.error(f"Error fetching items to process: {e}")
        raise
    finally:
        if conn: await DB_POOL.release(conn)

# --- mark_item_processed_and_assign_monitor 함수 수정: item_no 타입 확인 ---
async def mark_item_processed_and_assign_monitor(item_no: int, assigned_monitor_id: str): # item_no를 int로 받음
    """데이터 처리 완료 후 state, get_time, adr(모니터 ID)을 업데이트합니다."""
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            now = datetime.datetime.now()
            # no 컬럼이 INT이므로 %s로 바인딩할 때 정수 그대로 전달
            await cur.execute(f"""
                UPDATE {settings.ITEMS_TABLE_NAME}
                SET state = 1, get_time = %s, adr = %s
                WHERE no = %s
            """, (now, assigned_monitor_id, item_no)) # item_no는 이제 int
            await conn.commit()
            logger.info(f"Marked item '{item_no}' as processed and assigned to monitor {assigned_monitor_id}.")
    except Exception as e:
        logger.error(f"Error updating item state for '{item_no}': {e}")
        if conn: await conn.rollback()
        raise
    finally:
        if conn: await DB_POOL.release(conn)

# --- get_latest_processed_item_by_monitor_id 함수 수정: 반환 타입 주의 ---
async def get_latest_processed_item_by_monitor_id(monitor_id: str):
    """특정 모니터 ID에 할당된 state=1인 최신 데이터를 조회합니다."""
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
             # no 컬럼이 이제 INT일 것입니다. 조회 결과 딕셔너리의 item['no']는 INT 타입
            await cur.execute(f"""
                SELECT no, text, update_time, get_time, adr, state
                FROM {settings.ITEMS_TABLE_NAME}
                WHERE state = 1 AND adr = %s
                ORDER BY get_time DESC
                LIMIT 1
            """, (monitor_id,))
            item = await cur.fetchone()
            return item # 결과가 없으면 None 반환, item['no']는 int
    except Exception as e:
        logger.error(f"Error fetching latest item for monitor {monitor_id}: {e}")
        raise
    finally:
        if conn: await DB_POOL.release(conn)

# --- get_all_items_db 함수는 동일 ---
async def get_all_items_db():
     """DB의 모든 데이터를 조회합니다."""
     conn = None
     try:
         conn = await get_db_connection()
         async with conn.cursor() as cur:
             await cur.execute(f"SELECT no, text, update_time, get_time, adr, state FROM {settings.ITEMS_TABLE_NAME} ORDER BY update_time DESC")
             items = await cur.fetchall() # 각 item 딕셔너리의 'no' 값은 int
             return items
     except Exception as e:
        logger.error(f"Error fetching all items: {e}")
        raise
     finally:
        if conn: await DB_POOL.release(conn)

# --- get_latest_two_processed_items_by_monitor_id 함수 추가 ---
async def get_latest_two_processed_items_by_monitor_id(monitor_id: str):
    """특정 모니터 ID에 할당된 state=1인 최신 데이터 2개를 조회합니다."""
    conn = None
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            await cur.execute(f"""
                SELECT no, text, update_time, get_time, adr, state
                FROM {settings.ITEMS_TABLE_NAME}
                WHERE state = 1 AND adr = %s
                ORDER BY get_time DESC
                LIMIT 2
            """, (monitor_id,))
            items = await cur.fetchall()
            return items # 결과가 없으면 빈 리스트 반환
    except Exception as e:
        logger.error(f"Error fetching latest two items for monitor {monitor_id}: {e}")
        raise
    finally:
        if conn: await DB_POOL.release(conn)