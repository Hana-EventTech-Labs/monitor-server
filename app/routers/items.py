from fastapi import APIRouter, HTTPException
from ..database import insert_item_db, get_all_items_db # DB 함수 임포트

router = APIRouter(
    prefix="/items",
    tags=["items"],
)

# --- add_test_item 함수 수정: no 인자 제거, 반환 값 변경 ---
@router.post("/add_test/")
# no: str 파라미터를 제거합니다.
async def add_test_item(text: str):
    """
    테스트용 데이터를 DB에 추가합니다 (no 자동 생성, 모니터 주소는 나중에 결정).
    """
    # insert_item_db 함수는 이제 text만 받습니다.
    inserted_no = await insert_item_db(text=text) # 삽입된 no 값을 반환받음
    # insert_item_db가 False를 반환하는 경우는 이제 없으므로 예외 처리는 불필요
    # 만약 no가 이미 존재하면 insert_item_db 내부에서 경고 로깅만 하고 True/False 대신 None을 반환하도록 수정할 수도 있습니다.
    # 현재 코드에서는 동일 no 삽입 시 DB 예외가 발생하고 그대로 위로 전파됩니다.

    # 성공 응답에 자동 생성된 no 포함
    return {"message": "Item added successfully", "no": inserted_no}

# --- list_items 함수는 동일 ---
@router.get("/")
async def list_items():
    """DB의 모든 항목을 조회합니다."""
    items = await get_all_items_db()
    return items