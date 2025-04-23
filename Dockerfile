# 1. 기본 이미지 설정 - 빌드 도구가 포함된 이미지 사용
FROM python:3.13

# 2. uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# 3. 애플리케이션 코드를 컨테이너 내부로 복사
COPY . /app

# 4. 작업 디렉터리 설정
WORKDIR /app

# 5. 애플리케이션 의존성 설치 및 가상 환경 생성
RUN uv sync --frozen --no-cache

# --- 보안 및 실행 권한 문제 해결을 위한 추가 단계 ---
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
RUN chown -R appuser:appuser /app
RUN chmod +x /app/.venv/bin/fastapi
USER appuser
# --- 끝 ---

# 10. 컨테이너 시작 시 실행될 실행 파일 정의
ENTRYPOINT ["/app/.venv/bin/fastapi"]

# 11. 컨테이너 시작 시 실행 파일에 전달될 기본 인자 정의
#     $PORT 환경 변수가 이 단계에서 값으로 치환됩니다.
CMD ["run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]

# 12. (정보성) 컨테이너가 리스닝하는 포트 명시 (선택 사항)
# EXPOSE 8080 # Cloud Run 기본 PORT가 8080인 경우 사용 가능