# 강의평 분석 API

자유 서술 강의평을 **평가 항목별 만족과 불만족, 원문 근거 문장**으로 정리하는 분석 API와 결과 화면입니다.
대학 학사 시스템(고객사) 안에 들어가는 B2B 기능을 목표로 합니다. 강의평 수집, 저장, 로그인, 열람 권한은 고객사가 맡고, 이 서비스는 분석과 집계, 결과 화면을 제공합니다.

이어드림스쿨 AI 실무 기본과정 팀 프로젝트 (2026-10-20 ~ 10-26)

| 담당 | 역할 |
| --- | --- |
| 동렬 (AI 분석가반) | 라벨링 기준, 분석 프롬프트, 정량 평가 |
| 상준 (AI 서비스 개발자반) | 백엔드 API, 결과 생성 스크립트, API 명세 |
| 혜린 (AI 서비스 개발자반) | 기획, 프론트엔드, 통합 |

---

## 무엇을 볼 수 있나

| 주소 (프론트 실행 후) | 화면 | 백엔드 필요 |
| --- | --- | --- |
| http://localhost:5173/ | 가나대학교 포털, **교직원**: 학기 → 담당 과목 → 학기 결과 | 아니요 |
| http://localhost:5173/#learner | 가나대학교 포털, **학생**: 과목 검색 → 전체 학기 결과 | 아니요 |
| http://localhost:5173/#analyze | 강의평을 직접 넣어 분석해 보는 테스트 화면 | **예** |

- 교직원과 학생 화면은 상단의 **예시 로그인 (교직원 / 학생)** 으로도 바꿀 수 있습니다.
- 결과 화면은 **요약** (만족·불만족 TOP 3, 종합 의견)과 **상세 분석** (모든 항목, 정렬과 항목 필터, 근거 문장과 원문 하이라이트) 두 탭입니다.

> **가나대학교 포털과 예시 로그인은 고객사 연동을 보여 주는 가상 예시입니다.**
> 실제 로그인, 권한, 데이터베이스는 없습니다. 포털은 미리 분석해 둔 결과 파일(`frontend/public/reference/`)을 읽어 그립니다.
> 강의평은 학생 커뮤니티 말투로 만든 가상 강의평 64개이며, 실제 학생 강의평이 아닙니다.

---

## 실행 방법 (Windows PowerShell 기준)

준비물: Python 3.10 이상, Node.js 20.19 이상

### 1. 백엔드 (`#analyze` 화면을 쓸 때만 필요)

저장소 루트에서:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.main:app --port 8000
```

- `.env`의 `USE_MOCK=true`(기본값)이면 LLM을 부르지 않고 예시 응답을 돌려줍니다. API 키가 없어도 실행됩니다.
- 실제 분석은 `.env`에 `OPENAI_API_KEY`를 넣고 `USE_MOCK=false`로 바꾼 뒤 서버를 다시 켭니다.
- 확인: http://127.0.0.1:8000/api/health → `{"status":"ok", ...}`

### 2. 프론트엔드

새 터미널에서:

```powershell
cd frontend
npm install
npm run dev
```

http://localhost:5173/ 을 엽니다. `/api` 요청은 개발 서버가 백엔드(8000번 포트)로 전달합니다.

배포용 빌드: `npm run build` (결과는 `frontend/dist/`)

---

## API 요약

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/api/analyze` | 강의평 묶음 분석 (최대 50개, 1개당 3,000자) |
| GET | `/api/health` | 서버 상태, mock 여부 |
| GET | `/api/categories` | 평가 항목 목록 |

요청 예시:

```json
{ "reviews": [{ "id": "101", "text": "과제너무많음ㅠㅠ 근데 설명은 잘하심", "semester": "2026-1" }] }
```

응답은 리뷰별 결과(`reviews`), 항목별 집계(`summary_by_category`), 처리 정보(`meta`)입니다.
필드 설명과 고객사 연동 안내는 [docs/api_spec.md](docs/api_spec.md)에 있습니다.

- 원문은 고치지 않고 그대로 받습니다. 맞춤법 자동 교정을 하지 않습니다.
- 근거 문장(`evidence`)은 원문에서 그대로 가져오고, 원문과 일치하는지 검사합니다.
- 서비스는 강의평이나 결과를 저장하지 않습니다.

---

## 분석 기준

평가 항목 10개: 과제량, 시험, 팀 프로젝트, 전달력, 출석, 성적, 학습 가치, 교수자 태도, 총평, 기타
감성: 항목마다 만족 / 불만족 / 중립, 리뷰 전체 감성

- 라벨링 기준: [docs/labeling_guide.md](docs/labeling_guide.md), 경계 기준 v2: [docs/labeling_boundary_v2.md](docs/labeling_boundary_v2.md)
- 분석 프롬프트: [analysis/prompt.py](analysis/prompt.py) (v3)

## 검증 결과

| 데이터 | 기준 | 항목+감성 F1 |
| --- | --- | --- |
| 짧은 리뷰 45개 | 팀 확정 라벨 | 88.32% → 88.78% (프롬프트 v3, 하락 없음) |
| 가상 강의평 64개 (200자 이상 24개) | AI 지원 라벨 v2 | 83.30% → **90.20%** (프롬프트 v3, 개발용 데이터) |
| 경계 확인용 24개 | AI 지원 라벨 | 86.57% → **95.24%** (프롬프트 고정 뒤 확인) |

- 64개와 24개는 AI가 데이터 생성과 라벨 작성을 함께 한 **탐색적 평가**입니다. 사람 검토를 거친 정답이 아니며, 실제 사용자 환경의 성능이 아닙니다.
- 근거 원문 일치 100%는 문자열이 같다는 뜻이며, 분류가 맞았다는 뜻은 아닙니다.
- 상세: [docs/day5_consistency_improvement.md](docs/day5_consistency_improvement.md)

---

## 개발용 명령

```powershell
# 테스트 (API 호출 없음)
python -m unittest discover -s tests

# 64개 평가 수치 재현 (API 호출 없음)
python scripts/rescore_consistency.py --output consistency_eval.local.json

# 포털 결과 파일 다시 만들기 (백엔드를 USE_MOCK=false로 먼저 실행)
python scripts/build_reference_data.py --input data/reference/reviews_p01.jsonl data/reference/reviews_p02.jsonl
```

- 결과 화면 개발 중 주소 끝에 `?ov=sample`을 붙이면 `frontend/public/overview_sample/`의 **예시 종합 의견**을 덮어씌워 화면을 확인할 수 있습니다. 실제 분석 결과가 아니므로 시연과 캡처에는 쓰지 않습니다.

## 폴더

| 폴더 | 내용 |
| --- | --- |
| `backend/` | FastAPI 서버 (`/api/analyze`), 입력 검사, 후처리, 집계 |
| `analysis/` | 분석 프롬프트, LLM 호출, 평가 함수 |
| `frontend/` | React (Vite) 결과 화면, 가나대학교 포털 레퍼런스, 디자인 가이드 |
| `scripts/` | 결과 파일 생성, 평가 재현 |
| `data/` | 평가용 리뷰와 라벨, 가상 강의평 |
| `docs/` | API 명세, 라벨링 기준, 평가 기록 |
| `tests/` | 평가기와 회귀 테스트 |

## 한계

- 포털, 예시 로그인은 가상 예시이며 실제 고객사 연동과 운영 환경 검증은 하지 않았습니다.
- 가상 강의평은 실제보다 긴 글 비중이 높고(200자 이상 37%, 실제 약 18%), 커뮤니티 말투 기준이라 학사 시스템 강의평가와 다를 수 있습니다.
- 출석처럼 사실 언급과 불만의 경계가 애매한 항목은 감성 판단이 흔들릴 수 있습니다.
- 종합 의견의 LLM 정리본(`overview`)은 포털 결과 파일에만 있는 단계이며, `/api/analyze` 기본 응답에는 없습니다.
- 고객사 인증(X-API-Key)은 아직 구현하지 않았습니다.

## 협업 규칙

브랜치 → PR → 팀원 1명 승인 → Squash merge. API 키, 실제 `.env`, 실제 학생 강의평은 올리지 않습니다. 자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md).
