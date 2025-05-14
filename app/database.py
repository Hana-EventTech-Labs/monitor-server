import aiomysql
import logging
import datetime
import re
from .core.config import settings

logger = logging.getLogger(__name__)

# 연결 풀 변수
DB_POOL = None

# 테이블 이름 안전성 검증 함수 추가
def validate_table_name(table_name: str) -> bool:
    """
    SQL 인젝션 방지를 위해 테이블 이름이 안전한지 검증합니다.
    알파벳, 숫자, 언더스코어만 허용합니다.
    """
    pattern = re.compile(r'^[a-zA-Z0-9_]+$')
    return bool(pattern.match(table_name))

# 테이블 이름 가져오는 함수 추가
def get_safe_table_name() -> str:
    """
    설정에서 안전한 테이블 이름을 가져옵니다.
    테이블 이름이 안전하지 않으면 예외를 발생시킵니다.
    """
    table_name = settings.ITEMS_TABLE_NAME
    if not validate_table_name(table_name):
        raise ValueError(f"테이블 이름 '{table_name}'은(는) 안전하지 않습니다. 알파벳, 숫자, 언더스코어만 허용됩니다.")
    return table_name

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
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # no 컬럼을 INSERT 목록에서 제거, f-string 대신 %s 사용
            query = """
                INSERT INTO {} (text, adr, state)
                VALUES (%s, %s, %s)
            """.format(table_name) # f-string 대신 format 메소드 사용
            
            await cur.execute(query, (text, None, 0)) # no 값 제거

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
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # 트랜잭션 시작 - FOR UPDATE를 사용하여 다른 프로세스가 동일한 행을 선택하지 않도록 함
            await conn.begin()
            
            query = """
                SELECT no, text, adr, update_time -- update_time 컬럼 추가
                FROM {} 
                WHERE state = 0 AND update_time < %s
                ORDER BY update_time ASC
                FOR UPDATE
            """.format(table_name)
            
            await cur.execute(query, (threshold_time,))
            items = await cur.fetchall()
            
            # 항목을 즉시 처리 중으로 표시 (임시 상태 -1)
            # 이렇게 하면 다른 워커가 동일한 항목을 처리하지 않음
            if items:
                item_ids = [item['no'] for item in items]
                placeholders = ', '.join(['%s'] * len(item_ids))
                update_query = f"""
                    UPDATE {table_name}
                    SET state = -1
                    WHERE no IN ({placeholders}) AND state = 0
                """
                await cur.execute(update_query, item_ids)
                
                # 실제로 업데이트된 항목만 가져오기
                await cur.execute(f"""
                    SELECT no, text, adr, update_time
                    FROM {table_name}
                    WHERE no IN ({placeholders}) AND state = -1
                """, item_ids)
                items = await cur.fetchall()
            
            await conn.commit()
            return items
    except Exception as e:
        logger.error(f"Error fetching items to process: {e}")
        if conn:
            try:
                await conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        return []  # 오류 발생 시 빈 리스트 반환
    finally:
        if conn: 
            try:
                await DB_POOL.release(conn)
            except Exception as release_error:
                logger.error(f"Error releasing connection: {release_error}")

# --- mark_item_processed_and_assign_monitor 함수 수정: item_no 타입 확인 ---
async def mark_item_processed_and_assign_monitor(item_no: int, assigned_monitor_id: str): # item_no를 int로 받음
    """데이터 처리 완료 후 state, get_time, adr(모니터 ID)을 업데이트합니다."""
    conn = None
    try:
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # 트랜잭션 시작
            await conn.begin()
            
            # 먼저 현재 상태 확인 (이미 처리된 항목인지 확인)
            check_query = f"SELECT state FROM {table_name} WHERE no = %s FOR UPDATE"
            await cur.execute(check_query, (item_no,))
            result = await cur.fetchone()
            
            if not result:
                logger.warning(f"Item {item_no} not found in database")
                await conn.rollback()
                return False
            
            current_state = result['state']
            if current_state == 1:
                # 이미 처리된 항목
                logger.warning(f"Item {item_no} already processed (state=1)")
                await conn.rollback()
                return False
            
            now = datetime.datetime.now()
            # no 컬럼이 INT이므로 %s로 바인딩할 때 정수 그대로 전달
            query = """
                UPDATE {} 
                SET state = 1, get_time = %s, adr = %s
                WHERE no = %s AND (state = 0 OR state = -1)
            """.format(table_name)
            
            await cur.execute(query, (now, assigned_monitor_id, item_no)) # item_no는 이제 int
            
            # 실제로 업데이트된 행 수 확인
            rows_affected = cur.rowcount
            
            if rows_affected == 0:
                logger.warning(f"No rows updated for item {item_no} - may have been processed by another worker")
                await conn.rollback()
                return False
            
            await conn.commit()
            logger.info(f"Marked item '{item_no}' as processed and assigned to monitor {assigned_monitor_id}.")
            return True
            
    except Exception as e:
        logger.error(f"Error updating item state for '{item_no}': {e}")
        if conn: 
            try:
                await conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        raise
    finally:
        if conn: await DB_POOL.release(conn)

# --- get_latest_processed_item_by_monitor_id 함수 수정: 반환 타입 주의 ---
async def get_latest_processed_item_by_monitor_id(monitor_id: str):
    """특정 모니터 ID에 할당된 state=1인 최신 데이터를 조회합니다."""
    conn = None
    try:
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # no 컬럼이 이제 INT일 것입니다. 조회 결과 딕셔너리의 item['no']는 INT 타입
            query = """
                SELECT no, text, update_time, get_time, adr, state
                FROM {} 
                WHERE state = 1 AND adr = %s
                ORDER BY get_time DESC
                LIMIT 1
            """.format(table_name)
            
            await cur.execute(query, (monitor_id,))
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
         # 안전한 테이블 이름 가져오기
         table_name = get_safe_table_name()
         
         conn = await get_db_connection()
         async with conn.cursor() as cur:
             query = """
                 SELECT no, text, update_time, get_time, adr, state 
                 FROM {} 
                 ORDER BY update_time DESC
             """.format(table_name)
             
             await cur.execute(query)
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
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            query = """
                SELECT no, text, update_time, get_time, adr, state
                FROM {} 
                WHERE state = 1 AND adr = %s
                ORDER BY get_time DESC
                LIMIT 2
            """.format(table_name)
            
            await cur.execute(query, (monitor_id,))
            items = await cur.fetchall()
            return items # 결과가 없으면 빈 리스트 반환
    except Exception as e:
        logger.error(f"Error fetching latest two items for monitor {monitor_id}: {e}")
        raise
    finally:
        if conn: await DB_POOL.release(conn)

# --- get_assigned_items_queue 함수 추가 ---
async def get_assigned_items_queue(monitor_id: str, limit: int = 10):
    """특정 모니터 ID에 할당된 state=1인 데이터를 get_time 순서대로 조회합니다."""
    conn = None
    try:
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            query = """
                SELECT no, text, update_time, get_time, adr, state
                FROM {} 
                WHERE state = 1 AND adr = %s
                ORDER BY get_time ASC
                LIMIT %s
            """.format(table_name)
            
            await cur.execute(query, (monitor_id, limit))
            items = await cur.fetchall()
            return items # 결과가 없으면 빈 리스트 반환
    except Exception as e:
        logger.error(f"Error fetching item queue for monitor {monitor_id}: {e}")
        raise
    finally:
        if conn: await DB_POOL.release(conn)

# --- get_new_items_for_monitor 함수 수정 ---
async def get_new_items_for_monitor(monitor_id: str, last_displayed_item_no: int = 0, limit: int = 10, should_log: bool = False):
    """
    마지막으로 표시된 항목 이후의 새 항목들을 가져옵니다.
    이전에 표시된 항목의 번호(no)보다 큰 항목들만 반환합니다.
    
    Args:
        monitor_id: 모니터 ID
        last_displayed_item_no: 마지막으로 표시된 항목 번호
        limit: 최대 항목 수
        should_log: 로그 출력 여부
    """
    conn = None
    try:
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            # 디버깅: 데이터베이스의 모든 항목 개수 확인
            if should_log:
                query_count = f"SELECT COUNT(*) as total FROM {table_name} WHERE state = 1 AND adr = %s"
                await cur.execute(query_count, (monitor_id,))
                count_result = await cur.fetchone()
                total_items = count_result['total'] if count_result else 0
                
                # 디버깅: 조건을 만족하는 항목 개수 확인
                query_count_after = f"SELECT COUNT(*) as matching FROM {table_name} WHERE state = 1 AND adr = %s AND no > %s"
                await cur.execute(query_count_after, (monitor_id, last_displayed_item_no))
                count_after = await cur.fetchone()
                matching_items = count_after['matching'] if count_after else 0
                
                # 로그 출력
                logger.info(f"DB 조회: 모니터 {monitor_id} - 총 {total_items}개 항목 중 {matching_items}개가 no > {last_displayed_item_no} 조건 만족")
            
            query = """
                SELECT no, text, update_time, get_time, adr, state
                FROM {} 
                WHERE state = 1 
                AND adr = %s
                AND no > %s
                ORDER BY get_time ASC
                LIMIT %s
            """.format(table_name)
            
            await cur.execute(query, (monitor_id, last_displayed_item_no, limit))
            items = await cur.fetchall()
            
            # 로그 출력 여부에 따라 로그 출력
            if should_log:
                if items:
                    item_nos = [item['no'] for item in items]
                    logger.info(f"모니터 {monitor_id}를 위해 {len(items)}개 항목 가져옴. 항목 번호: {item_nos}")
                else:
                    logger.info(f"모니터 {monitor_id}를 위한 새 항목 없음 (no > {last_displayed_item_no})")
            
            # 새 항목이 없으면 빈 리스트를 반환
            return items
    except Exception as e:
        logger.error(f"Error fetching new items for monitor {monitor_id}: {e}")
        return []  # 오류 발생 시 빈 리스트 반환
    finally:
        if conn: 
            try:
                await DB_POOL.release(conn)
            except Exception as release_error:
                logger.error(f"Error releasing connection: {release_error}")

# --- get_latest_item_no 함수 추가 ---
async def get_latest_item_no():
    """DB에서 가장 최신 항목의 no 값을 가져옵니다."""
    conn = None
    try:
        # 안전한 테이블 이름 가져오기
        table_name = get_safe_table_name()
        
        conn = await get_db_connection()
        async with conn.cursor() as cur:
            query = """
                SELECT MAX(no) as latest_no
                FROM {}
            """.format(table_name)
            
            await cur.execute(query)
            result = await cur.fetchone()
            
            # 결과가 없거나 NULL이면 0 반환
            if not result or result['latest_no'] is None:
                return 0
                
            return result['latest_no']
    except Exception as e:
        logger.error(f"Error fetching latest item no: {e}")
        return 0  # 오류 발생 시 기본값 0 반환
    finally:
        if conn: await DB_POOL.release(conn)