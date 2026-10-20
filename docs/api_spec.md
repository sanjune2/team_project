# Lecture Evaluation AI - API Specification (v1.0)

## 1. 개요
본 문서는 '강의평가 AI' 백엔드의 리뷰 분석 API 규격서입니다. 
FastAPI 기반의 `/api/analyze` 엔드포인트를 통해 리뷰 텍스트를 수집하고, ABSA(Aspect-Based Sentiment Analysis) 기준에 맞춘 분석 결과를 반환합니다.

---

## 2. API Endpoint

- **URL**: `/api/analyze`
- **Method**: `POST`
- **Content-Type**: `application/json`

---

## 3. Request Schema (요청 데이터 구조)

| Field | Type | Required | Description |
|---|---|---|---|
| `reviews` | Array[Object] | **필수** | 분석할 리뷰 객체 리스트 |
| `reviews[].id` | Integer / String | **필수** | 리뷰 고유 식별자 |
| `reviews[].text` | String | **필수** | 리뷰 원문 (최대 3,000자) |
| `reviews[].semester` | String | 선택 | 수강 학기 (예: "25-2") |

### Request Example
```json
{
  "reviews": [
    {
      "id": 101,
      "text": "강의 내용은 너무 좋은데 마이크 소리가 잘 안 들려요.",
      "semester": "25-2"
    }
  ]
}