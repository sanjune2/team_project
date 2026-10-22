# 45개 1차 분석 평가

- 평가 시각(UTC): 2026-10-22T03:18:17.064523+00:00
- 데이터: `data/test_reviews.jsonl` / SHA-256 `4e461319942440f4199aa14ceb74949171e08eb7a6107296b4f53bdce2aeb170`
- 정답 상태: 제공된 1차 라벨 대비 잠정 평가. 사람 교차 검토 완료 미확인.
- 분석 함수의 실제 API 평가다. HTTP·웹 통합 검증은 포함하지 않는다.
- 로컬 데이터 병합 후보는 포함하지 않았다.

| 지표 | 결과 | 분모 또는 건수 |
|---|---:|---|
| 리뷰 수 | 45 | 전체 |
| 항목 정밀도 | 90.43% | TP 85 / FP 9 |
| 항목 재현율 | 91.40% | TP 85 / FN 8 |
| 항목 F1 | 90.91% | 리뷰별 고유 항목을 합산 |
| 감성 정확도 | 92.31% | 84/91 |
| 근거 원문 exact | 98.99% | 98/99 |
| 실패율 | 0.00% | 0/45 |
| 평균 처리 시간 | 2644.6 ms | 성공·실패 포함 45개 |

## 평가 규칙

- 항목은 리뷰별 고유 category로 센다. accept_also는 한 정답의 대안이며 이중 정답으로 세지 않는다.
- 최대 일대일 매칭을 사용한다. 감성은 매칭된 항목에서 정답·예측 감성 수 중 큰 수를 분모로 쓴다.
- 실패 리뷰도 정답 항목을 FN으로 센다. 모든 예측 근거를 exact 비율의 분모로 쓴다.
- 근거 exact는 원문의 부분 문자열인지 확인한다. 감성을 뒷받침하는지는 별도 사람 검토가 필요하다.
- 누락된 condition·mentions_change 정답을 null·false로 간주하지 않는다.
- condition 문자열 일치율은 진단 지표다. 조건 내용의 의미 정확도는 사람이 확인해야 한다.

## 추가 지표

- merged_item_count 분포: `{"0": 40, "1": 5}`
- 1개 이상 병합한 리뷰: ['t02', 't09', 'g02', 'c11', 'c12'] / 비율 11.11%

| 필드 | 명시 정답 수 | 정답 누락 수 | 항목·감성 매칭 수 | 유무 정확도 | 문자열/값 일치율 |
|---|---:|---:|---:|---:|---:|
| condition | 4 | 93 | 3 | 75.00% | 0.00% |
| mentions_change | 5 | 92 | 4 | 80.00% | 80.00% |

명시된 condition은 모두 조건이 있는 사례이며 mentions_change 정답은 모두 true다.
조건·변경이 없는 사례의 오탐률과 전체 정확도는 이 라벨만으로 계산할 수 없다.

## 호출 조건

```json
{
  "created_at": "2026-10-22T03:18:17.064523+00:00",
  "data_path": "data/test_reviews.jsonl",
  "data_sha256": "4e461319942440f4199aa14ceb74949171e08eb7a6107296b4f53bdce2aeb170",
  "label_status": "제공된 1차 라벨 대비 잠정 평가. 사람 교차 검토 완료 미확인.",
  "models": [
    "gpt-6-luna"
  ],
  "prompt_sha256": [
    "f9c58176a7bd2acfa7ed98e7cac2fb1ae5e4b2c8a6bb2f8bb0ed5f3ef96a2e22"
  ],
  "reasoning_effort": [
    "none"
  ],
  "temperature": 0,
  "max_retries": 0,
  "timeout_seconds": 30,
  "usage_total": {
    "input_tokens": 120774,
    "output_tokens": 7222,
    "total_tokens": 127996
  },
  "max_output_tokens": 4000
}
```

## 경계 사례 및 표현 노출

- c14·c15는 은어 사전에 패턴이 등록되어 있다. 독립적인 일반화 점수로 해석하지 않는다.
- t02·c11은 few-shot과 표현 일부가 겹친다. 아래 제외 점수도 함께 본다.

- exclude_glossary_c14_c15: 43개, 항목 F1 91.30%, 감성 92.22%
- exclude_overlap_t02_c11: 43개, 항목 F1 91.53%, 감성 91.95%
- exclude_all_four: 41개, 항목 F1 91.95%, 감성 91.86%

## 검토할 차이

| ID | 누락 항목 | 추가 항목 | 감성 정답/분모 |
|---|---|---|---|
| t01 |  | workload | 1/1 |
| t02 | exam |  | 2/2 |
| t07 | etc | professor | 2/2 |
| t08 |  |  | 2/3 |
| t09 |  |  | 6/7 |
| g03 |  | grade | 4/4 |
| g05 | exam | workload | 1/1 |
| g08 | learning |  | 2/2 |
| g10 |  | exam, general_impression | 0/0 |
| m03 | learning |  | 1/1 |
| m06 |  |  | 1/2 |
| m08 |  | general_impression | 1/1 |
| c01 |  |  | 4/5 |
| c02 |  |  | 1/2 |
| c04 |  | grade | 1/1 |
| c05 |  | delivery | 2/3 |
| c06 |  |  | 3/4 |
| c11 | exam |  | 2/2 |
| c13 | exam |  | 1/1 |
| c14 | grade |  | 0/0 |

## 해석과 후속 확인

- 라벨 교차 검토 완료 확인과 condition 의미 검토가 필요하다.
- 실행 간 비교와 6·7번 진행 상태는 docs/eval_comparison.md를 확인한다.
- 노션 완료 체크는 요구사항 전체를 검증한 뒤 처리한다.
