# AI-백엔드 JSON 계약 v0.1

상태: 협업 시작을 위한 제안 계약. 구현 전에 3인이 확정합니다.
이 문서는 구현 완료를 뜻하지 않습니다.
외부 HTTP API는 백엔드가 담당합니다. AI 모듈은 같은 응답 구조를 반환합니다.

## 요청
POST /api/v1/analyze
Content-Type: application/json

```json
{
  "review_id": "demo-001",
  "text": "설명이 명확했지만 진도가 빨랐어요."
}
```

- review_id: 요청 추적용 문자열. 1~100자.
- text: 공백 제거 후 1~5000자. 한국어 강의평을 우선 지원합니다.
- 서버는 개인정보가 포함된 원문을 기본 로그에 남기지 않습니다.

## 평가 항목
| key | 의미 |
|---|---|
| content | 강의 내용의 유용성과 구성 |
| delivery | 설명의 명확성과 전달 |
| pace | 진행 속도 |
| materials | 교재와 실습 자료 |
| interaction | 질문 응답과 소통 |

항목은 예시로 정했습니다. AI-Hub 라벨과 같다고 가정하지 않습니다.
변경 시 AI, 백엔드, 프런트엔드 담당자가 함께 확인합니다.

## 성공 응답
HTTP 200. 아래 값은 설명용 예시입니다.

```json
{
  "schema_version": "0.1",
  "review_id": "demo-001",
  "aspects": [
    {"aspect": "content", "sentiment": "not_mentioned", "evidence": []},
    {"aspect": "delivery", "sentiment": "positive", "evidence": ["설명이 명확했지만"]},
    {"aspect": "pace", "sentiment": "negative", "evidence": ["진도가 빨랐어요"]},
    {"aspect": "materials", "sentiment": "not_mentioned", "evidence": []},
    {"aspect": "interaction", "sentiment": "not_mentioned", "evidence": []}
  ],
  "model": {"mode": "mock", "name": "example-only", "prompt_version": null},
  "latency_ms": 120
}
```

- aspects에는 위 5개 항목을 각각 1번씩 고정 순서로 반환합니다.
- sentiment: positive, neutral, negative, mixed, not_mentioned 중 하나.
- mixed: 같은 항목에서 긍정과 부정이 함께 나타납니다.
- not_mentioned: 해당 항목의 근거가 없습니다. neutral과 구분합니다.
- evidence: 입력 원문에 실제로 있는 근거 구절의 배열입니다.
- not_mentioned의 evidence는 빈 배열입니다. 다른 감성에는 근거를 1개 이상 제공합니다.
- model.mode: mock, pretrained, llm 중 하나.
- model.name은 실제 사용 모델 식별자입니다. mock이면 mock임을 명시합니다.
- prompt_version은 LLM 프롬프트 버전입니다. 해당하지 않으면 null입니다.
- latency_ms는 0 이상 정수입니다.
- 모델 확률과 LLM의 주관적 확신을 섞지 않도록 confidence는 v0.1에서 제외합니다.

## 오류 응답
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "강의평을 1~5000자로 입력해 주세요.",
    "request_id": "req-example"
  }
}
```

| HTTP | code | 조건 |
|---|---|---|
| 400 | INVALID_INPUT | 공백, 길이 초과, 필수 값 누락 |
| 502 | INVALID_MODEL_OUTPUT | AI 응답이 계약과 다름 |
| 503 | MODEL_UNAVAILABLE | AI 호출 실패 |
| 504 | MODEL_TIMEOUT | 제한 시간 초과 |

실패 시 정상 응답으로 위장한 mock 결과를 반환하지 않습니다.
mock 모드는 개발자가 명시적으로 선택할 때만 사용합니다.
AI 호출 제한 시간의 초기 제안은 30초입니다.

## 대시보드 집계
항목별로 not_mentioned를 제외한 리뷰 수를 분모로 사용합니다.
positive, neutral, negative, mixed의 개수와 비율을 각각 표시합니다.
분모가 0이면 비율을 0으로 계산하고 화면에는 '언급 없음'을 표시합니다.
not_mentioned 개수도 별도로 표시합니다.
리뷰는 review_id로 중복 집계를 막습니다.
전체 리뷰 감성을 항목 감성의 단순 평균으로 만들지 않습니다.

## 계약 확인 예시
- 긍정만 있는 리뷰.
- 부정만 있는 리뷰.
- 한 항목에 긍정과 부정이 함께 있는 리뷰.
- 일부 항목만 언급한 리뷰.
- 공백 입력, 5000자 초과 입력.
- AI 지연, 잘못된 JSON, 허용되지 않은 라벨.
