# 실제 LLM 분석 함수 인계

관련 작업: #2. 기준: Notion 1021 오전 중간점검과 Ver 3.1의 10개 항목.
기존 docs/api-contract.md의 5개 항목 제안과 다르다. 이 PR은 공용 HTTP 계약을 변경하지 않는다.

## 설치와 실행

Python 3.14에서 검증했다. 저장소 루트에서 실행한다.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p test_llm_connect.py -v
```

실제 호출에는 서버의 비공개 .env 또는 환경 변수에 다음 값을 설정한다.
OPENAI_API_KEY는 실제 키, OPENAI_MODEL은 gpt-6-luna,
OPENAI_REASONING_EFFORT는 none을 사용했다. 키를 문서나 Git에 넣지 않는다.
환경 변수 값이 .env보다 우선한다.

```powershell
python scripts/smoke_analysis.py --require-glossary --output analysis_smoke.local.json
```

위 명령은 실제 유료 API를 호출한다. 저장한 실행 결과는 별도로 검토하며 자동 커밋하지 않는다.
`--require-glossary`는 은어 사전이 없거나 성공 응답의 `glossary_loaded`가 true가 아니면 실패한다.
`requirements.txt`에 검증 버전 `openai==2.54.0`, `pydantic==2.14.1`을 통합했다.
별도 `requirements-llm.txt` 설치는 필요하지 않다.
입력은 새로 작성한 가상 리뷰 5개다. 사람 정답 기반 정확도 평가가 아니다.

## 함수와 반환값

```python
from analysis.llm import analyze_review, LLMAnalysisError

def call_llm(text):
    return analyze_review(text)  # dict가 필요하면 .model_dump()
```

모델에는 text만 전달한다. semester는 백엔드가 응답에 붙인다.
반환 객체의 items 각 항목은 category, sentiment, summary, evidence,
keywords, condition, mentions_change의 필수 7개 필드다.
category는 10개 enum, sentiment는 positive/negative/neutral이다.
언급 없는 항목은 생략한다. 평가 대상이 없으면 items=[]다.
같은 항목·감성의 중복 출력은 병합한다. 다른 감성은 따로 유지한다.
병합 근거는 원래 출력 중 긴 연속 구간 하나를 사용한다. 구간을 이어 붙이지 않는다.
전체 감성, 근거 exact/normalized/none, HTTP 상태와 집계는 백엔드 담당이다.
분석 객체와 백엔드 스키마가 같은 클래스라고 가정하지 않는다.

## 호출 조건과 오류

공백과 3000자 초과 입력은 ValueError다.
호출·거부·미완료·파싱 실패는 LLMAnalysisError다. Mock으로 대체하지 않는다.
제한 시간 30초, SDK 재시도 0회, store=false다.
추론 none이면 temperature=0을 사용한다. 추론 low 이상이면 temperature를 생략한다.
temperature=0도 동일 출력을 보장하지 않는다.
SDK 본문과 키는 오류 메시지에 포함하지 않는다.
동기 함수이므로 비동기 API 핸들러에서는 작업 스레드 등 기존 처리 방식에 연결한다.

## 검증 범위와 남은 조건

- 분석 단위 테스트 7개가 통과했다. 실제 유료 API가 아닌 모의 통신을 사용한다.
- 동일 분석 함수의 실제 가상 리뷰 5개 호출이 성공했고 11개 항목의 근거가 원문에 일치했다.
- 별도 로컬 백엔드 어댑터에서도 HTTP 5개 호출이 성공했다. 해당 백엔드 변경은 이 PR에 포함하지 않는다.
- 실제 호출 성공과 문자열 일치는 의미 정확도를 증명하지 않는다.
- docs/slang_glossary.md가 없어 실제 실행은 glossary_loaded=false였다.
- 팀 은어 사전 원본과 c14·c15를 받으면 밈 사례를 추가 검증해야 한다.
- 사람 정답 교차 검토와 팀 웹 화면 통합은 미완료다.
- 동렬님 데이터 병합 후보와 백엔드 연결 수정은 별도 로컬 작업으로 보존했다.

분석 입력 예: `설명에 예시가 많아 이해하기 쉬웠어요.`
반환 형식 예(설명용, 이 문장의 실측 결과가 아님):

```json
{"items":[{"category":"delivery","sentiment":"positive","summary":"예시가 많아 이해하기 쉽다는 의견","evidence":"설명에 예시가 많아 이해하기 쉬웠어요.","keywords":["예시"],"condition":null,"mentions_change":false}]}
```
