# 라벨링 가이드 (Ver 3.1)

> 원본: 노션 '라벨링 가이드라인 & JSON 스키마 보완안 Ver 3.1' (10/20). 변경 시 노션과 이 파일을 함께 수정합니다.

## 2. 평가 항목 기준

| 코드 | 항목 | 포함 내용 | 경계 규칙 |
| --- | --- | --- | --- |
| `workload` | 과제량·로드 | 과제 빈도·분량, 리딩, 예습·복습 부담, **체감 학습 부담** | 팀플은 team_project / 퀴즈·시험 **횟수 부담**은 workload, 시험 **내용**은 exam |
| `exam` | 시험·평가 방식 | 난이도, 범위, 유형, 수업과 시험의 괴리, **출제·평가 비중의 명확성** | 학점 결과·성적 부여 기준은 grade |
| `team_project` | 팀 프로젝트 | 유무, 운영 방식, 역할 분담, 팀원 운, 성적 반영 비중 | 팀 단위 과제 부담은 여기로 |
| `delivery` | 전달력·수업 구성 | 설명 방식, 강의 자료, 진도, 흥미도, 수업 내용 난이도·기초 설명, 강의 언어(영강) 전달력, 과제 피드백 | 배운 게 많다/없다는 learning / 교수 인품은 professor |
| `attendance` | 출석·참여 | 출석 확인 방식, 지각·결석 처리, 참여점수, 발표 | |
| `grade` | 성적·학점 | 학점 관대함, 학점 결과 보고, **성적 부여 기준의 불명확함(의문사·랜덤박스)** | 시험 출제 기준이 불명확한 건 exam |
| `learning` | 학습 가치 | 배운 것, 인사이트, 실력 향상, "명강" | 전달력과 반대 방향일 수 있으므로 delivery와 분리 |
| `professor` | 교수자 태도 | 인품, 친절함, 소통, 질문 응대, 권위적 태도 | 설명 능력은 delivery / **외모 언급은 제외** |
| `general_impression` | 총평 | 특정 항목에 속하지 않는 총평·추천·비추천 ("GOAT", "최악", "그냥 들으세요", "꿀강") | 구체적 근거가 있으면 해당 항목으로 |
| `etc` | 기타 | 수업 시간대, 공지 방식, 휴강, 수업 형식(녹강·줌강), 조교, 강의실·시설 자체 | |

**난이도 표현 주의**: "어렵다"는 그 자체로 불만이 아님. 불만으로 표현됐으면 negative, 단순한 난이도 설명이면 neutral ("어려웠지만 실력이 늘었음" → delivery · neutral + learning · positive)

**추출 제외 대상**
- 메타 리뷰: 다른 강의평·별점에 대한 언급 **자체**는 제외하되, 그 안에 담긴 강의 정보는 추출
  - "평점 맞추려고 5점 드림" → 제외 / "학점 잘 준다는 평 믿지 마셈" → grade · negative
- 교수자 외모 언급
- 강의와 무관한 글 (스팸, 잡담)
- 평가 대상이 하나도 없으면 `items: []`

---

## 3. 감성 분류 기준

**기본 규칙**
- 감성은 **항목 단위**로 `positive` / `negative` / `neutral` 중 하나를 부여
- `neutral`: 평가 없이 사실만 언급 (예: "팀플 있음", "중간·기말 두 번", "팀플: 없음")
- **존재 ≠ 불만:** 팀플·과제가 있다는 사실만으로 negative 처리하지 않음
- **원문 외 추론 금지:** 리뷰에 없는 교수자 태도나 수업 문제를 추가하지 않음

**리뷰 단위 감성 (`overall_sentiment`, 코드가 계산)**

| 상황 | `status` | `items` | `overall_sentiment` |
| --- | --- | --- | --- |
| 사실만 언급 | ok | 전부 neutral | `neutral` |
| 긍정만 (중립 섞여도) | ok | positive (+ neutral) | `positive` |
| 부정만 (중립 섞여도) | ok | negative (+ neutral) | `negative` |
| 긍정·부정 모두 | ok | positive + negative | `mixed` |
| 평가 대상 없음 (잡담·메타) | ok | `[]` | `null` |
| LLM 호출·파싱 실패 | **failed** | `[]` | `null` (`error`에 사유) |

**세부 규칙**
- **같은 항목이 여러 번:** 같은 감성이면 item 1개로 합치고, 가장 명확하게 뒷받침하는 원문 구간 하나를 대표 evidence로 저장. 다른 감성이면 item 분리
- **비교 표현:** "다른 분반보다 과제 적음"은 비교가 가리키는 평가로 판단 (workload · positive)
- **반어·밈:** 표면이 아니라 실제 의미로 판단, evidence에 반어 부분 포함
  - 밈의 함의가 평가 대상과 연결되면 **은어 사전의 해석을 우선 적용** ("○○아 울지마 사실 산타는 없거든" → grade · negative)
  - 밈의 뜻을 알아도 평가 대상이 불명확하면 항목을 임의로 지정하지 않음
  - 호칭 은어(○○붕이 등)는 평가 정보가 아니므로 감성 판단·summary에 쓰지 않음
  - 원문에 없는 평가로 넓히지 않음 ("산타는 없다"에서 workload · negative까지 추론하지 않음)
- **조건부 평가:** 조건은 `condition`에 기록하고, 감성은 그대로 유지
  - 조건에 따라 추천·비추천이 갈리면 **조건별로 item을 나눔**
    - "전공 살릴 거면 강추, 졸업요건용이면 비추" → general_impression · positive (전공 심화 목적) + general_impression · negative (졸업요건 충족 목적) → 리뷰는 mixed
  - 조건이 붙었지만 방향이 하나면 그 감성 유지
    - "미적 노베면 많이 고생함" → exam · negative (미적분 선수지식이 없는 경우)
- **학점 결과 보고:** "q3로 A0"처럼 평가 표현이 없으면 grade · neutral, "잘 주신 듯"이 있으면 positive
- **약한 평가어:** "무난", "평이"는 positive
- **은어:** 은어 사전(slang_glossary.md) 기준으로 해석, 모르는 약어는 추론하지 않음
- **사실만 언급:** neutral이되, 항목은 **언급한 주제의 항목**으로 분류 ("팀플 있음" → team_project · neutral)
- **문맥 우선:** 감성은 텍스트 문맥으로만 판단. 별점은 입력으로 받지 않음
- **판단 불가:** 은어 사전과 문장 속 단서로도 평가 대상을 확정할 수 없을 때만 `items: []`. 사전으로 해석되는 밈은 판단 불가가 아님

**시기 변화 (`mentions_change`)**
- 학생이 변경을 **명시적으로 언급**하면 `true` ("이번 학기부터 개인 과제 없어짐")
- 현황 설명만 있으면 `false` ("개인 과제가 적어서 좋음")
- summary는 "~가 없어졌다는 의견"처럼 학생의 서술임을 드러냄. 실제 변경 여부는 리뷰만으로 확정하지 않음
- 학기는 입력의 `semester`로만 받고, 본문에서 추론하지 않음

**summary 작성 규칙**
- 욕설·비난 표현을 제거하고 구체적인 문제나 요구로 작성
  - 예: "교수 인성 노답, 질문하면 면박줌" → "질문에 대한 응대 방식이 학생을 위축시킨다는 의견"
- 교수자 실명 포함 금지

---

## 4. 테스트 데이터 구성

**유형별 목표 (30개 기준, `primary_type`으로 검증)**

| 유형 | primary_type | 목표 | 현재 (45개) |
| --- | --- | --- | --- |
| 단일 항목 | `single` | 6 | 5 |
| 다중 항목 · 같은 감성 | `multi_same` | 4 | 4 |
| 다중 항목 · 혼합 감성 | `multi_mixed` | 7 | 10 |
| 중립 (사실만 언급) | `neutral` | 4 | 4 |
| 감정적·공격적 표현 포함 | `emotional` | 3 | 6 |
| 반어·밈 표현 | `irony` | 3 | 8 |
| 노이즈 (오타·은어·띄어쓰기) | `noise` | 2 | 4 |
| 평가 없음 (메타·무관한 글) | `meta` | 1 | 4 |

**분량 분포 (공백 포함 글자 수)**

| 분량 | 기준 | 목표 비율 | 현재 (45개) |
| --- | --- | --- | --- |
| 한 줄 | 50자 이하 | 30% | 21개 (47%) |
| 보통 | 51~199자 | 50% | 23개 (51%) |
| 장문 | 200자 이상 | 20% | **1개 (2%)** |

⚠️ **보강 필요**: 장문(200자 이상), `single`, 항목 중 `etc`(2)·`attendance`(5)·`team_project`(5). 마지막 팀원 분량은 이 유형 위주로 작성

**형식 (JSONL, 한 줄에 리뷰 하나)**

```json
{"id": "r001", "semester": "25-2", "primary_type": "multi_mixed", "tags": ["multi_mixed", "irony"], "text": "리뷰 원문", "labels": [{"category": "delivery", "sentiment": "positive", "evidence": "원문 부분 문자열"}], "note": "이 데이터로 확인할 점"}
```

**리뷰 단위 필드**

| 필드 | 필수 | 설명 | 모델 입력 |
| --- | --- | --- | --- |
| `id` | ✅ | 사람별 접두어 + 번호 (예: `r001`) | ✅ |
| `semester` | 선택 | 수강 학기 (예: `"25-2"`) | ✅ |
| `text` | ✅ | 리뷰 원문 | ✅ |
| `primary_type` | ✅ | 대표 유형 1개 (위 표) → 유형별 개수 검증용 | ❌ |
| `tags` | ✅ | 해당하는 특성 전부 (아래 목록) → 취약점 분석용 | ❌ |
| `labels` | ✅ | 정답 라벨 배열. 평가 대상이 없으면 `[]` | ❌ |
| `note` | 선택 | 이 데이터로 확인할 점, 라벨링 근거 메모 | ❌ |

**labels 안의 필드**

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `category` | ✅ | 2번의 enum 10개 중 하나 |
| `sentiment` | ✅ | `positive` / `negative` / `neutral` |
| `evidence` | ✅ | 원문의 부분 문자열 (오타 그대로) |
| `condition` | 선택 | 조건부 평가의 조건 |
| `mentions_change` | 선택 | 변경을 명시적으로 언급했으면 `true` |
| `expected_summary` | 선택 | 공격적 표현의 정제 예시 (summary 품질 확인용) |
| `accept_also` | 선택 | 정답으로 함께 인정할 대안 `[{"category", "sentiment"}]`. 사람끼리도 해석이 갈리는 사례에만 사용 |

**tags 목록**: `single`, `multi_same`, `multi_mixed`, `neutral`, `emotional`, `irony`, `noise`, `meta`, `conditional`, `change`, `long`, `ambiguous`, `meme` (여러 개 가능)

**작성·병합 규칙**
- 작성은 사람별 파일(`data/reviews_이름.jsonl`), 병합본은 `data/test_reviews.jsonl`
- id 접두어: 구혜린 `t`·`c` / GPT 재라벨링 `g` / 팀원 `m` / 나머지 담당자는 겹치지 않는 문자로 지정
- 평가 스크립트는 `text`·`semester`만 모델에 입력하고, 나머지는 정답 비교에만 사용
- 쓰지 않는 필드: `rating`(별점), `reviewer_name`(작성자)
- ⚠️ 실제 강의평은 **표현과 분량 참고용**. 원문 복사·단어만 바꾼 문장·교수자 실명 사용 금지

※ 5일 차까지 100개로 확충

---

## 5. JSON 스키마

**요청 필드** (리뷰는 한 번에 1~50개, 리뷰마다 LLM을 따로 호출)

| 필드 | 설명 |
| --- | --- |
| reviews[].id | 리뷰 ID (최대 50자) |
| reviews[].text | 리뷰 원문 (최대 **3,000자**) |
| reviews[].semester | 수강 학기 (선택, 예: "25-2") |

**응답 필드**

| 필드 | 설명 | 생성 주체 |
| --- | --- | --- |
| reviews[].review_id | 리뷰 ID | 입력값 |
| reviews[].semester | 수강 학기 | 입력값 |
| reviews[].status | `ok` / `failed` (LLM 호출·파싱 실패) | 코드 |
| reviews[].overall_sentiment | positive / negative / neutral / mixed, items가 비거나 실패하면 `null` | 코드 |
| reviews[].error | failed일 때 사유 (성공 시 null) | 코드 |
| reviews[].items[] | 평가 항목 배열 (빈 배열 허용) | LLM |
| items[].category | 평가 항목 코드 (enum 10개) | LLM |
| items[].sentiment | positive / negative / neutral | LLM |
| items[].summary | 정제된 한 줄 요약 | LLM |
| items[].evidence | 원문의 부분 문자열인 근거 | LLM |
| items[].keywords | 핵심 키워드 0~3개 | LLM → Pandas 집계 |
| items[].condition | 조건부 평가의 조건 (없으면 null) | LLM |
| items[].mentions_change | 변경 언급 여부 (항상 boolean) | LLM |
| items[].evidence_match | `exact` / `normalized` / `none` | 코드 |
| items[].evidence_verified | evidence_match가 none이 아니면 true | 코드 |
| summary_by_category[].counts | 항목별 감성별 **리뷰 수** | 코드 |
| summary_by_category[].top_pros / top_cons | 항목별 주요 장점·불만 | LLM (21일 이후) |
| meta | 리뷰 수, 성공·실패 건수, 모델명, 처리 시각 | 코드 |

**규칙**
- category, sentiment는 영문 enum 고정, 한글 표시는 프론트가 `/api/categories`로 매핑
- category enum: `workload`, `exam`, `team_project`, `delivery`, `attendance`, `grade`, `learning`, `professor`, `general_impression`, `etc`
- 정의되지 않은 category는 생성 금지 (Structured Outputs enum으로 강제)
- LLM 출력 스키마의 필드는 모두 필수 (OpenAI strict 모드). 값이 없으면 LLM이 `null` / `[]` / `false`를 채움
- evidence는 **오타·띄어쓰기까지 원문 그대로** 복사
- evidence 검증: 원문 그대로 일치 → `exact` (프론트 하이라이트 가능) / 공백·문장부호만 다름 → `normalized` / 그 외(조사·단어 차이 포함) → `none`
- evidence 불일치는 리뷰 실패가 아님: `status: ok` 유지, 해당 item만 `evidence_verified: false`로 표시
- evidence가 원문에 있어도 감성을 실제로 뒷받침하는지는 평가 단계에서 사람이 확인
- counts 집계: 리뷰 수 기준. 같은 리뷰에서 같은 항목이 positive·negative 둘 다 나오면 양쪽에 각각 1씩 포함 → 감성별 합계가 리뷰 수보다 클 수 있음


## 6. 4일차 통합 적용 기준 (2026-10-23)

사용자 지정 통합 기준을 적용한 평가 라벨이다. 전체 45개 독립 사람 검토 완료를 뜻하지 않는다. 이 절이 위의 일반 설명과 충돌하면 이 절을 우선한다.

- 선수지식 부족에서 생기는 학습 부담은 `workload`다. 기초 설명 부족·빠른 진도 불만은 `delivery`다.
- 청취를 방해하는 마이크·음향 문제는 `delivery`다. 장소·시설 자체에 대한 평가만 `etc`다.
- 반어·간접 총평은 문맥으로 판단한다. 해석을 독자에게 맡긴다는 표현만으로 부정을 만들지 않는다. 조롱·거리두기 등 부정적 함의가 드러나면 총평을 추출한다.
- t07·c05의 선수지식 부담은 workload/negative, m04의 음향 불만은 delivery/negative다. g10은 general_impression/negative다.
- t09는 힌트를 delivery/neutral로 분류하고 workload/negative를 유지한다. 과제 횟수 workload/neutral과 오픈북 exam/neutral을 보존한다. 다른 리뷰에 중립 정답을 일괄 추가하지 않는다.
- c13은 grade/negative 1개에 exam/negative를 `accept_also`로 인정한다. 별도 exam/negative 필수 정답은 두지 않는다. 이전 시험 불만족 삭제 메모는 별도 필수 라벨 삭제 이력이며 대안 인정과 구분한다.
- g03은 시험 긍정 근거를 “시험도 수업에서 다룬 내용 위주로 나와서 공부한 만큼은 받을 수 있는 듯”까지 확대한다. exam/positive 1개에 grade/positive 대안을 인정한다. 이전 보류 메모는 의견 이력이다.
- 대안은 동일 판단에 대한 일대일 매칭이다. 두 항목 동시 출력을 모두 정답으로 세지 않는다. c13·g03 대안 유무는 이번 기존 저장 응답 점수에 영향이 없다.
- m06은 grade/positive를 유지한다. t04·t05·g08 조건과 c11 exam/negative 삭제 등 기존 통합 기준을 보존한다.
- condition·evidence와 리뷰 원문·메타데이터는 사용자 지정 통합 라벨 파일을 따른다. 라벨과 리뷰 ID는 모델 프롬프트에 넣지 않는다.

이 기준과 활성 프롬프트의 반영 상태는 다를 수 있다. P1 후보는 근거 원문 복사율 회귀로 채택하지 않았다. 실험 결과와 남은 불일치는 `docs/day4_label_rescore_and_prompt.md`에 기록한다.
