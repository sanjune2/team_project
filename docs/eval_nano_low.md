# 45개 1차 분석 평가

- 평가 시각(UTC): 2026-10-22T03:31:11.975438+00:00
- 데이터: `data/test_reviews.jsonl` / SHA-256 `4e461319942440f4199aa14ceb74949171e08eb7a6107296b4f53bdce2aeb170`
- 정답 상태: 제공된 1차 라벨 대비 잠정 평가. 사람 교차 검토 완료 미확인.
- 분석 함수의 실제 API 평가다. HTTP·웹 통합 검증은 포함하지 않는다.
- 로컬 데이터 병합 후보는 포함하지 않았다.

| 지표 | 결과 | 분모 또는 건수 |
|---|---:|---|
| 리뷰 수 | 45 | 전체 |
| 항목 정밀도 | 85.71% | TP 72 / FP 12 |
| 항목 재현율 | 77.42% | TP 72 / FN 21 |
| 항목 F1 | 81.36% | 리뷰별 고유 항목을 합산 |
| 감성 정확도 | 85.90% | 67/78 |
| 근거 원문 exact | 100.00% | 87/87 |
| 실패율 | 0.00% | 0/45 |
| 평균 처리 시간 | 4797.533333333334 ms | 성공·실패 포함 45개 |

## 평가 규칙

- 항목은 리뷰별 고유 category로 센다. accept_also는 한 정답의 대안이며 이중 정답으로 세지 않는다.
- 최대 일대일 매칭을 사용한다. 감성은 매칭된 항목에서 정답·예측 감성 수 중 큰 수를 분모로 쓴다.
- 실패 리뷰도 정답 항목을 FN으로 센다. 모든 예측 근거를 exact 비율의 분모로 쓴다.
- 근거 exact는 원문의 부분 문자열인지 확인한다. 감성을 뒷받침하는지는 별도 사람 검토가 필요하다.
- 누락된 condition·mentions_change 정답을 null·false로 간주하지 않는다.
- condition 문자열 일치율은 진단 지표다. 조건 내용의 의미 정확도는 사람이 확인해야 한다.

## 추가 지표

- merged_item_count 분포: `{"0": 45}`
- 1개 이상 병합한 리뷰: [] / 비율 0.00%

| 필드 | 명시 정답 수 | 정답 누락 수 | 항목·감성 매칭 수 | 유무 정확도 | 문자열/값 일치율 |
|---|---:|---:|---:|---:|---:|
| condition | 4 | 93 | 3 | 50.00% | 0.00% |
| mentions_change | 5 | 92 | 2 | 0.00% | 0.00% |

명시된 condition은 모두 조건이 있는 사례이며 mentions_change 정답은 모두 true다.
조건·변경이 없는 사례의 오탐률과 전체 정확도는 이 라벨만으로 계산할 수 없다.

## 호출 조건

```json
{
  "created_at": "2026-10-22T03:31:11.975438+00:00",
  "data_path": "data/test_reviews.jsonl",
  "data_sha256": "4e461319942440f4199aa14ceb74949171e08eb7a6107296b4f53bdce2aeb170",
  "label_status": "제공된 1차 라벨 대비 잠정 평가. 사람 교차 검토 완료 미확인.",
  "models": [
    "gpt-5-nano-2025-08-07"
  ],
  "prompt_sha256": [
    "8044b7c8d55019191f1cce7410342823fce605c915180e8caa32cf670f618491"
  ],
  "reasoning_effort": [
    "low"
  ],
  "temperature": null,
  "max_retries": 0,
  "timeout_seconds": 30,
  "usage_total": {
    "input_tokens": 129774,
    "output_tokens": 33443,
    "total_tokens": 163217
  },
  "max_output_tokens": 4000
}
```

## 경계 사례 및 표현 노출

- c14·c15는 은어 사전에 패턴이 등록되어 있다. 독립적인 일반화 점수로 해석하지 않는다.
- t02·c11은 few-shot과 표현 일부가 겹친다. 아래 제외 점수도 함께 본다.

- exclude_glossary_c14_c15: 43개, 항목 F1 80.92%, 감성 85.53%
- exclude_overlap_t02_c11: 43개, 항목 F1 81.44%, 감성 85.14%
- exclude_all_four: 41개, 항목 F1 80.98%, 감성 84.72%

## 검토할 차이

| ID | 누락 항목 | 추가 항목 | 감성 정답/분모 |
|---|---|---|---|
| t02 | exam |  | 2/2 |
| t03 |  | learning | 3/3 |
| t05 | delivery, grade | professor | 2/2 |
| t06 | general_impression |  | 2/2 |
| t07 | delivery, general_impression | learning, workload | 1/1 |
| t08 |  | delivery | 0/3 |
| t09 | team_project | general_impression, grade | 4/6 |
| t10 | general_impression |  | 1/1 |
| g02 |  | learning | 1/1 |
| g03 | delivery, exam, general_impression | learning | 1/1 |
| g04 |  |  | 2/3 |
| g07 | general_impression |  | 2/3 |
| g10 |  | general_impression | 0/0 |
| m04 | etc |  | 0/1 |
| m06 |  |  | 1/2 |
| m07 | general_impression |  | 1/1 |
| m10 | delivery |  | 0/0 |
| c01 | workload |  | 2/3 |
| c02 |  |  | 1/2 |
| c03 |  | exam | 1/1 |
| c06 | attendance, delivery | general_impression | 1/1 |
| c11 | exam |  | 2/2 |
| c12 | delivery |  | 2/2 |
| c13 | exam |  | 1/1 |

## 해석과 후속 확인

- 라벨 교차 검토 완료 확인과 condition 의미 검토가 필요하다.
- 실행 간 비교와 6·7번 진행 상태는 docs/eval_comparison.md를 확인한다.
- 노션 완료 체크는 요구사항 전체를 검증한 뒤 처리한다.
