# Backend

FastAPI 서버입니다. 강의평 묶음을 받아 분석하고, 근거 문장을 검사하고, 항목별로 집계합니다.

- 실행: 저장소 루트에서 `uvicorn backend.main:app --port 8000` (자세한 방법은 [루트 README](../README.md))
- API 명세: [docs/api_spec.md](../docs/api_spec.md)
- `USE_MOCK=true`이면 LLM을 부르지 않고 예시 응답을 돌려줍니다.
- API 키는 서버 환경변수(`.env`)로만 읽습니다.
