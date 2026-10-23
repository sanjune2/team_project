# Lecture Evaluation AI - B2B API Specification & Integration Guide (v2.1)

본 문서는 '강의평가 AI' 백엔드의 리뷰 분석 API 규격서 및 고객사(대학 학사 시스템, LMS 등) 연동 가이드입니다.
FastAPI 기반의 `/api/analyze` 엔드포인트를 통해 리뷰 텍스트를 수집하고, ABSA(Aspect-Based Sentiment Analysis) 기준에 맞춘 분석 결과 및 카테고리별 집계를 반환합니다.

---

## 1. 개요 및 인증 방식

- **URL**: `/api/analyze`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **인증 (고객사 식별)**: Request Body가 아닌 **HTTP Request Header의 API Key**를 통해 고객사를 식별 및 검증합니다.
  - Header 예시: `X-API-Key: YOUR_CUSTOMER_API_KEY`

---

## 2. Request Schema (요청 데이터 구조)

### 1) 요청 필드 규격
| Field | Type | Required | Description |
|---|---|---|---|
| `reviews` | Array[Object] | **필수** | 분석할 리뷰 객체 리스트 (1회 요청당 최대 50개) |
| `reviews[].id` | Integer / String | **필수** | 리뷰 고유 식별자 (`review_id` 호환) |
| `reviews[].text` | String | **필수** | 리뷰 원문 (최대 3,000자, 원문 수정 없이 그대로 입력) |
| `reviews[].semester` | String | 선택 | 수강 학기 (예: `"2026-2"`, `"2025-2"`) |
| `reviews[].question` | String | 선택 (확장) | 문항 유형 (예: `"좋았던 점"`, `"개선할 점"`) |
| `reviews[].course_id` | String | 선택 (확장) | 과목 코드 (예: `"CS101"`, `"c03"`) |
| `reviews[].section_id` | String | 선택 (확장) | 분반 코드 (예: `"01"`) |
| `reviews[].source` | String | 선택 (확장) | 데이터 출처 (예: `"official_evaluation"`, `"community"`) |
| `reviews[].visibility` | String | 선택 (확장) | 공개 범위 (`"instructor_only"`, `"student_public"`) |

> 💡 `source` 및 `visibility` 필드는 AI 분석 로직에 직접 사용되지 않으며, 고객사 측에서 결과 반환 후 권한 제어 및 화면 노출 범위를 관리할 때 활용됩니다.

### 2) Request Example
```json
{
  "reviews": [
    {
      "id": "101",
      "text": "과제너무많음ㅠㅠ 근데 설명은 잘하심",
      "semester": "2026-2",
      "question": "개선할 점",
      "course_id": "CS101",
      "section_id": "01",
      "source": "official_evaluation",
      "visibility": "instructor_only"
    }
  ]
}