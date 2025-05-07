# 프랙티컬 스트래티지 태블릿 모니터 시스템

태블릿 장치에 실시간으로 데이터를 표시하는 웹 기반 모니터링 시스템입니다.

## 시작하기

### 설치

1. uv 패키지 관리자 초기화:
```
uv init
```

2. 애플리케이션 실행:
```
uv run fastapi dev
```

## 기능

- 여러 태블릿 모니터에 데이터를 실시간으로 표시
- 각 모니터마다 고유한 데이터 큐 관리
- 데이터 추가 및 모니터 할당을 위한 API 제공
- Server-Sent Events(SSE)를 통한 실시간 업데이트

## API 엔드포인트

- `/items` - 데이터 추가 및 조회
- `/items/add_test/?text={text}` - 행 추가
- `/monitor/{monitor_id}` - 특정 모니터 디스플레이 페이지
- `/monitor/{monitor_id}/stream` - 실시간 데이터 스트림 (SSE)
- `/status` - 서버 상태 확인

## 기술 스택

- FastAPI - 웹 프레임워크
- MariaDB - 데이터 저장소
- Jinja2 - HTML 템플릿
- SSE - 실시간 데이터 스트리밍