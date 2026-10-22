# v2 동일 설정 1회 재실행

대상: main d0e7798. 기존 v2와 프롬프트·은어 사전 포함 instructions 해시 및 45개 정답 해시가 일치한다.
gpt-6-luna / reasoning=none / temperature=0 / timeout=30초 / SDK retry=0 / 출력 한도 4000을 유지했다.
전체 45개를 추가 1회만 실행했다. 결과를 보고 다시 실행하거나 프롬프트·정답을 수정하지 않았다.
원본 v2 응답과 재실행 응답은 별도 *.local.json으로 보존하며 Git에 올리지 않는다.

| 지표 | 기존 v2 | 이번 1회 |
|---|---:|---:|
| 항목 정밀도 | 94.62% | 95.65% |
| 항목 재현율 | 94.62% | 94.62% |
| 항목 F1 | 94.62% | 95.14% |
| 감성 정확도 | 92.63% | 91.58% |
| 근거 원문 exact | 99.00% | 98.99% |
| 실패율 | 0.00% | 0.00% |
| 평균 처리 시간 | 2.559초 | 3.318초 |

## 요청한 재현 여부

| 점검 | 기존 v2 | 이번 1회 | 판단 |
|---|---|---|---|
| g07 반어 총평 부정 | 누락 | 누락 | 같은 누락 재현 |
| c02 반어 총평 부정 | 누락 | 누락 | 같은 누락 재현 |
| mentions_change | 3/5 | 3/5 | 기존 v1 4/5 대비 퇴보 재현 |

g07은 learning·negative와 workload·negative를 반환했고 총평 부정을 누락했다.
c02는 workload·negative만 반환했고 총평 부정을 누락했다.
반어를 표면 긍정으로 반환한 것이 아니라 **총평 item 자체를 빠뜨린 오류**다.

## mentions_change 5개 정답의 상세 결과

| ID / 항목·감성 | 정답 | 기존 v2 | 이번 1회 |
|---|---|---|---|
| t08 / exam·neutral | true | true | true |
| g09 / workload·positive | true | true | true |
| g09 / delivery·negative | true | true | true |
| c06 / attendance·neutral | true | 항목·감성 item 누락 | 항목·감성 item 누락 |
| c06 / delivery·positive | true | false | false |

실패한 2개는 c06 attendance·neutral item 누락과 delivery·positive의 false다.
따라서 변경 boolean만 고치는 방식과 항목 누락을 해결하는 방식은 구분해야 한다.

## 해석 범위

- 추가 실제 API 45/45 성공. HTTP·웹 통합 실행이 아니다.
- 모델 서비스는 같은 설정에서도 다른 출력을 낼 수 있다. 이번 한 번의 반복으로 항상 같은 오류가 난다고 단정하지 않는다.
- 정답은 기존 1차 라벨 그대로다. 사람 교차 검토 완료·독립 holdout 성능을 뜻하지 않는다.
- 통합용 20개, 라벨 경계안과 팀 전달문은 별도 문서에 정리했다.

## 동결 근거

```json
{
  "created_at": "2026-10-22T05:07:20.603894+00:00",
  "data_path": "data/test_reviews.jsonl",
  "data_sha256": "4e461319942440f4199aa14ceb74949171e08eb7a6107296b4f53bdce2aeb170",
  "label_status": "제공된 1차 라벨 대비 잠정 평가. 사람 교차 검토 완료 미확인.",
  "models": [
    "gpt-6-luna"
  ],
  "prompt_sha256": [
    "8044b7c8d55019191f1cce7410342823fce605c915180e8caa32cf670f618491"
  ],
  "reasoning_effort": [
    "none"
  ],
  "temperature": 0,
  "max_retries": 0,
  "timeout_seconds": 30,
  "max_output_tokens": 4000,
  "usage_total": {
    "input_tokens": 129774,
    "output_tokens": 7093,
    "total_tokens": 136867
  }
}
```
