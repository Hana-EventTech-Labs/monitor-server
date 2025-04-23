# app/dependencies.py
# 현재 예시에서는 사용되지 않습니다.
# from .database import get_db_connection

# async def get_db():
#     conn = await get_db_connection()
#     try:
#         yield conn
#     finally:
#         if conn:
#             # 연결 풀 사용 시 release를 호출해야 합니다.
#             # pool.release(conn) 방식은 get_db_connection 내부나
#             # 사용하는 함수 내에서 finally 블록에서 처리하는 것이 좋습니다.
#             # 의존성 주입 시에는 별도의 패턴이 필요할 수 있습니다.
#             pass # aiomysql connection release should be managed