from fastapi import APIRouter, HTTPException
import re # 정규식 임포트 추가
from ..database import insert_item_db, get_all_items_db # DB 함수 임포트

router = APIRouter(
    prefix="/items",
    tags=["items"],
)

# 텍스트 유효성 검사 함수 추가
def validate_text(text: str) -> str:
    """
    텍스트 입력을 유효성 검사하고 안전한 형태로 반환합니다.
    위험한 문자를 제거하고 길이 제한을 적용합니다.
    """
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="텍스트는 비어 있을 수 없습니다")
    
    # 최대 길이 제한 (ex: 1000자)
    if len(text) > 1000:
        text = text[:1000]
    
    # HTML 태그 제거 (XSS 방지 목적)
    text = re.sub(r'<[^>]*>', '', text)
    
    # SQL 인젝션 방지를 위한 특수 문자 이스케이프
    # (이 부분은 파라미터화된 쿼리를 사용하므로 실제로는 필요하지 않지만, 
    # 추가 보안 계층으로 유지)
    text = text.replace("'", "''")
    
    return text

# --- add_test_item 함수 수정: no 인자 제거, 반환 값 변경, 텍스트 유효성 검사 추가 ---
@router.post("/add_test/")
# no: str 파라미터를 제거합니다.
async def add_test_item(text: str):
    """
    테스트용 데이터를 DB에 추가합니다 (no 자동 생성, 모니터 주소는 나중에 결정).
    """
    # 텍스트 유효성 검사
    validated_text = validate_text(text)
    
    # insert_item_db 함수는 이제 text만 받습니다.
    try:
        inserted_no = await insert_item_db(text=validated_text) # 삽입된 no 값을 반환받음
        # 성공 응답에 자동 생성된 no 포함
        return {"message": "Item added successfully", "no": inserted_no}
    except Exception as e:
        # 데이터베이스 오류 처리
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")

# --- list_items 함수는 동일 ---
@router.get("/")
async def list_items():
    """DB의 모든 항목을 조회합니다."""
    try:
        items = await get_all_items_db()
        return items
    except Exception as e:
        # 데이터베이스 오류 처리
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")