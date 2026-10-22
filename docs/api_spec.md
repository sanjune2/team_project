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

---

## 4. Response Schema (응답 데이터 구조)

### 응답 개요
| Field | Type | Description |
|---|---|---|
| `reviews` | Array[Object] | 개별 리뷰 분석 결과 리스트 |
| `summary_by_category` | Array[Object] | 카테고리별 종합 집계 데이터 |
| `meta` | Object | 메타데이터 (처리 통계, 모델 정보 등) |

---

### 1) 개별 리뷰 분석 결과 (`reviews[]`)
| Field | Type | Description |
|---|---|---|
| `review_id` | Integer / String | 요청된 리뷰 고유 식별자 |
| `semester` | String | 수강 학기 |
| `status` | String | 분석 처리 상태 (`ok`, `failed`) |
| `overall_sentiment` | String / Null | 전체 종합 감성 (`positive`, `negative`, `neutral`, `mixed`, `null`) |
| `items` | Array[Object] | 측면별 분석 항목 리스트 (아래 상세 참고) |
| `error` | String / Null | 실패 시 에러 메시지 |

#### `items[]` (측면별 분석 항목)
| Field | Type | Description |
|---|---|---|
| `category` | String | 평가 카테고리 (`delivery`, `exam`, `assignment`, `learning`, `workload`, `attendance`, `general_impression` 등) |
| `sentiment` | String | 해당 항목의 감성 (`positive`, `negative`, `neutral`) |
| `summary` | String | 해당 항목에 대한 요약 문장 |
| `evidence` | String | 원문에서 추출한 근거 문장 |
| `keywords` | Array[String] | 핵심 키워드 리스트 |
| `condition` | String / Null | 조건부 언급 여부 |
| `mentions_change` | Boolean | 변화 언급 여부 |
| `evidence_match` | String | 원문 일치 여부 (`exact`, `partial`, `none`) |
| `evidence_verified` | Boolean | 근거 검증 여부 (`true`, `false`) |

---

### 2) 카테고리별 종합 집계 (`summary_by_category[]`)
| Field | Type | Description |
|---|---|---|
| `category` | String | 평가 카테고리명 |
| `mentioned` | Integer | **[New]** 해당 항목을 언급한 고유 리뷰 수 |
| `counts` | Object | 감성별 건수 (`positive`, `negative`, `neutral`) |
| `ratios` | Object | **[New]** 감성 건수 기준 백분율 비율(`positive`, `negative`, `neutral`, 합계 100%) |
| `top_pros` | Array[String] | **[New]** 대표 긍정 요약 리스트 (검증 여부 및 키워드 빈도 기준, 최대 3개) |
| `top_cons` | Array[String] | **[New]** 대표 부정 요약 리스트 (검증 여부 및 키워드 빈도 기준, 최대 3개) |

---

### 3) 메타데이터 (`meta`)
| Field | Type | Description |
|---|---|---|
| `total_reviews` | Integer | 총 요청된 리뷰 수 |
| `succeeded` | Integer | 분석 성공한 리뷰 수 |
| `failed` | Integer | 분석 실패한 리뷰 수 |
| `model` | String | 사용된 분석 모델명 (또는 mock 모드 정보) |
| `processed_at` | String | 처리 완료 시각 (ISO 8601 포맷) |

---

### Response Example
```json
{
  "reviews": [
    {
      "review_id": "rev_01",
      "semester": "2024-1",
      "status": "ok",
      "overall_sentiment": "mixed",
      "items": [
        {
          "category": "delivery",
          "sentiment": "positive",
          "summary": "설명이 명쾌하고 피드백이 꼼꼼하다는 의견",
          "evidence": "교수님 설명이 정말 명쾌합니다.",
          "keywords": ["설명"],
          "condition": null,
          "mentions_change": false,
          "evidence_match": "exact",
          "evidence_verified": true
        }
      ],
      "error": null
    }
  ],
  "summary_by_category": [
    {
      "category": "delivery",
      "mentioned": 1,
      "counts": {
        "positive": 1,
        "negative": 0,
        "neutral": 0
      },
      "ratios": {
        "positive": 100,
        "negative": 0,
        "neutral": 0
      },
      "top_pros": [
        "설명이 명쾌하고 피드백이 꼼꼼하다는 의견"
      ],
      "top_cons": []
    }
  ],
  "meta": {
    "total_reviews": 1,
    "succeeded": 1,
    "failed": 0,
    "model": "gpt-6-luna",
    "processed_at": "2026-10-22T06:28:03.780225Z"
  }
}