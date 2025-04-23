# 1. 기본 이미지 설정
#    python:3.12-slim 이미지를 사용합니다. 가볍고 필요한 것만 포함합니다.
FROM python:3.12-slim

# 2. uv 설치
#    멀티스테이지 빌드를 사용하여 uv 실행 파일을 공식 이미지에서 가져옵니다.
#    이는 시스템 전체에 uv를 설치하는 것보다 더 빠르고 안전합니다.
#    /usr/local/bin 은 기본적으로 PATH에 포함되어 있어 uv 실행이 용이합니다.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# 3. 애플리케이션 코드를 컨테이너 내부로 복사
#    로컬의 모든 파일(Dockerfild 제외)을 컨테이너의 /app 디렉터리로 복사합니다.
#    이 시점에서는 기본적으로 root 사용자로 복사됩니다.
COPY . /app

# 4. 작업 디렉터리 설정
#    이후 명령(RUN, CMD 등)이 실행될 기본 디렉터리를 설정합니다.
WORKDIR /app

# 5. 애플리케이션 의존성 설치 및 가상 환경 생성
#    uv를 사용하여 pyproject.toml 또는 requirements.txt에 명시된 의존성을 설치하고
#    /app/.venv에 가상 환경을 생성합니다. 이 과정도 root 권한으로 실행됩니다.
RUN uv sync --frozen --no-cache

# --- 보안 및 실행 권한 문제 해결을 위한 추가 단계 ---

# 6. 비-루트 사용자 생성 및 설정
#    보안을 위해 컨테이너 실행 시 root가 아닌 별도의 사용자로 실행하는 것을 권장합니다.
#    'appuser'라는 이름의 시스템 사용자 및 그룹을 생성합니다.
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# 7. 애플리케이션 디렉터리 소유권 변경
#    /app 디렉터리 및 그 하위 모든 파일들의 소유권을 방금 생성한 'appuser'에게 넘깁니다.
#    이렇게 해야 'appuser'가 /app 디렉터리 내의 파일들에 접근하고 실행할 수 있습니다.
RUN chown -R appuser:appuser /app

# 8. 필요한 스크립트에 실행 권한 부여 (선택적이지만 안전빵)
#    uv sync로 생성된 /app/.venv/bin/fastapi 스크립트에 모든 사용자에게 실행 권한을 부여합니다.
#    step 7에서 소유권을 넘겼으므로 필수적이지 않을 수 있으나, 권한 문제 재발 방지에 도움이 됩니다.
#    RUN 명령은 root 권한으로 실행되므로 가능합니다.
RUN chmod +x /app/.venv/bin/fastapi

# 9. 이후 명령을 실행할 사용자 전환
#    이 시점부터 CMD로 지정된 명령은 'appuser' 사용자의 권한으로 실행됩니다.
USER appuser

# --- 핵심 애플리케이션 실행 명령 설정 ---

# 10. 컨테이너 시작 시 실행될 명령 정의
#     FastAPI 애플리케이션을 Uvicorn으로 실행합니다.
#     --host 0.0.0.0: 모든 네트워크 인터페이스에서 접속 허용 (컨테이너 외부 노출 필수)
#     --port $PORT: 클라우드 서비스(Cloud Run 등)가 주입하는 PORT 환경 변수를 사용합니다.
#                   이것이 클라우드 환경에서 포트를 지정하는 가장 표준적인 방법입니다.
#                   클라우드 서비스 설정에서 "컨테이너 포트"를 $PORT 환경변수가 바라보는 값(기본 8080)으로 설정해야 합니다.
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "$PORT"]

# 11. (정보성) 컨테이너가 리스닝하는 포트 명시 (선택 사항)
#     이 명령어는 컨테이너가 어떤 포트를 사용할 예정인지 문서화하는 역할만 합니다.
#     실제로 포트를 열거나 설정하지는 않습니다. 위 CMD의 --port 설정이 중요합니다.
# EXPOSE 8080 # Cloud Run 기본 PORT가 8080인 경우 사용 가능