# 3일차 분석 환경 개선 검증 (2026-10-22)

기준: [3일차 체크리스트](https://app.notion.com/p/7a5ab1969cf582f7a9b701ddf43f896b)의 분석 태스크 5~7번.

## 변경

- `requirements.txt`에 `openai==2.54.0`, `pydantic==2.14.1`을 고정했다.
- 중복된 `requirements-llm.txt`를 제거하고 설치 안내를 갱신했다.
- `.gitignore`에 `.runtime/`, `*.local.json`을 추가했다.
- smoke에 `--require-glossary`를 추가했다. 사전 누락 또는 로딩 실패 시 종료 코드가 0이 아니다.

## 실제 검증

Python 3.14에서 `requirements.txt` 전체를 별도 로컬 폴더에 설치했다.
OpenAI 2.54.0, Pydantic 2.14.1 설치를 확인했다. 다른 패키지의 버전 고정은 이번 범위에 포함하지 않는다.
이 설치 환경에서 기존 분석 테스트 7개와 새 smoke 검사 테스트 2개가 모두 통과했다.
`git diff --check`와 `.runtime/`, 루트·하위 폴더의 `*.local.json` 제외 규칙도 확인했다.

분석 PR #4가 병합된 main `01e9ffec3750ba209aef86a91968ed1f9504a3ff`를 별도 worktree로 실행했다.
기존 `scripts/smoke_analysis.py`와 가상 리뷰 5개를 사용했다. 모델은 `gpt-6-luna`다.
키는 기존 비공개 환경 설정에서 읽었다. 결과 파일은 로컬에만 보관했다.

| 항목 | 실측 |
|---|---:|
| 분석 성공 | 5/5 |
| glossary_loaded=true | 5/5 |
| merged_item_count=0 | 5/5 |
| merged_item_count>0 | 0/5 |
| 평균 처리 시간 | 3,243 ms/리뷰 |

이 결과는 분석 함수의 실제 API smoke다. HTTP·웹 통합 또는 사람 정답 기반 정확도 결과가 아니다.
이번 개선 PR 병합 후에는 최신 main에서 아래 명령을 다시 실행한다.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/smoke_analysis.py --require-glossary --output analysis_smoke.local.json
```

## 오늘 정확도 측정 시 확인

- `merged_item_count`는 응답에서 같은 항목·감성을 합쳐 제거한 item 수다. 값별 빈도, 1 이상인 리뷰 비율과 해당 ID를 기록한다.
- `condition`과 `mentions_change`는 사람이 확인한 정답이 있는 항목만 평가한다. 평가 분모와 정답 누락 수를 함께 기록한다.
- `condition`은 조건 유무와 조건 내용의 의미 일치를 따로 검토한다. 문자열 일치만으로 의미 정확도를 주장하지 않는다.
- c14·c15는 사전에 패턴이 등록된 사례다. 독립적인 일반화 성능으로 해석하지 않는다.
- t02·c11은 few-shot과 표현 일부가 겹친다. 전체 점수와 함께 이 사례를 제외한 점수도 구분한다.
- 프롬프트 수정과 저가 모델 비교는 동일한 정답·프롬프트·호출 조건을 유지한다. 테스트셋 문장을 few-shot으로 추가하지 않는다.

현재 main의 `data/testdata_ver2.jsonl`은 43개이며 c14·c15가 없다.
94개 정답 item 중 `condition` 필드는 3개, `mentions_change` 필드는 5개에만 있다.
누락 필드를 임의로 null/false 정답으로 만들지 않는다.
45개 확정 데이터와 라벨 교차 검토 결과를 확보한 뒤 태스크 5번의 정확도 측정을 진행한다.
`analysis/evaluate.py` 구현, 45개 정확도, 프롬프트 재측정, 모델 비교와 노션 수치 기록은 이번 환경 개선에서 완료 처리하지 않았다.
