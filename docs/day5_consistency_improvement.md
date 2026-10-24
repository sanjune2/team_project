# 라벨 일관성 정리와 모델 개선 결과

## 결론

v3 개선안이 사전 품질 기준을 통과했다. 이 PR은 검증한 프롬프트와 버전별 라벨·재현 도구를 제안한다.
변경은 분석 모듈과 평가 자료에 한정된다. API 계약·백엔드·프런트 코드는 변경하지 않으며, 병합과 배포는 별도다.

## 라벨 효과와 모델 효과 구분

| 단계     | 라벨    | 예측        | 항목 F1  | 감성 정확도 | 항목+감성 F1 | 리뷰 완전 일치 |
| ------ | ----- | --------- | ------:| ------:| --------:| --------:|
| 기존 평가  | v1    | 저장된 기존 응답 | 91.87% | 85.34% | 82.50%   | 26/64    |
| 라벨만 수정 | v2    | 같은 저장 응답  | 92.05% | 86.70% | 83.30%   | 27/64    |
| 모델 개선  | 같은 v2 | v3 새 응답   | 96.15% | 89.84% | 90.20%   | 36/64    |

라벨 변경만으로 생긴 pair F1 변화는 +0.80%p다. 모델의 변화는 고정한 v2 기준에서 +6.91%p다. 둘을 합쳐 모델 개선으로 주장하지 않는다.

## 실제 변경

- 원문·기존 v1·기존 45개 라벨·기존 저장 JSON을 보존했다. 64개 중 16개 리뷰에 수정 작업 20건을 적용했고 원문 근거·이유를 기록했다.
- 질문 게시판 응대와 과제 채점 피드백, 단독 엄격한 출석과 불편 평가, 시험 유형과 시간 부족, 팀플 발표와 개인 참여, 변경 추론의 경계를 고정했다.
- v2 라벨 237개를 모델 실행 전에 해시로 고정했다. 이후 모델 결과에 맞춰 정답을 바꾸지 않았다.
- 첫 후보 v2는 과다 추출로 감성/완전 일치 회귀가 발생해 기각했다. 첫 후보의 채택 실패 수치와 검사는 evaluation/day5_consistency/manifest.json에 보존했다. 원시 실험 전체는 로컬에 보관하며 이 PR에는 최종 후보 재채점에 필요한 응답만 포함한다.
- 실패 원인에 따라 최소 수정한 v3를 별도 동결 후 1회 평가했다. 라벨과 통과 기준은 그대로 유지했다. 후보 추가 탐색은 하지 않았다.
- v3는 기존 예시 3개·모델·응답 스키마를 유지하며 항목 경계와 중복 중립 추출 규칙을 보완한다.
- 근거 복원 방어 코드는 별도 테스트했다. v3 개발 64개 원시 응답 자체가 253/253 exact다. 근거를 복원해 분류 점수를 올린 것은 아니다.

## 최종 검증

| 검증 데이터         | 기존 pair F1 | 개선 pair F1 | 기존 완전 일치 | 개선 완전 일치 |
| -------------- | ----------:| ----------:| --------:| --------:|
| 개발 64개, 고정 v2  | 83.30%     | 90.20%     | 27/64    | 36/64    |
| 기존 45개, 라벨 유지  | 88.32%     | 88.78%     | 31/45    | 31/45    |
| 새 합성 경계 확인 24개 | 86.57%     | 95.24%     | 18/24    | 21/24    |
| 64개 중 장문 24개   | 84.81%     | 89.66%     | 3/24     | 7/24     |

기존 45개 기준선은 이전 저장 응답을 그대로 현재 45개 라벨에 재채점했다. 이 데이터도 과거 개발에 사용됐다. 새 24개는 프롬프트 동결 후 새로 쓴 합성 경계 확인용이며 독립 사람 holdout은 아니다. 두 프롬프트 모두 같은 설정으로 각각 1회 호출했다.

| 채택 검사        | 결과                                                                                                                                                         |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 개발 64개       | {'pair_f1_min_2pp': True, 'category_f1': True, 'sentiment_accuracy': True, 'exact_reviews': True, 'overall': True, 'evidence_exact': True, 'failed': True} |
| 기존 45개 원시 출력 | {'category_f1': True, 'sentiment_accuracy': True, 'evidence_exact': True, 'failed': True}                                                                  |
| 새 24개        | {'pair_f1': True, 'category_f1': True, 'evidence_exact': True, 'failed': True}                                                                             |
| 최종 통과        | True                                                                                                                                                       |

## 남은 오류와 회귀

최신 라벨을 더 바꾸지 않고 남은 차이를 그대로 기록한다. 아래 명령으로 64개 전수 원문과 정답/기존/개선 결과를 재계산할 수 있다. 같은 항목의 근거 문구 자체는 완전 일치 판정 조건이 아니다.

완전 일치로 개선된 리뷰 14개: c01-2025-2-r04, c01-2026-1-r03, c01-2026-1-r04, c01-2026-1-r06, c02-2025-2-r06, c02-2025-2-r07, c02-2026-1-r08, c03-2025-2-r03, c03-2025-2-r05, c03-2025-2-r06, c03-2025-2-r08, c04-2026-1-r01, c04-2026-1-r03, c04-2026-1-r04.
기존 완전 일치에서 회귀한 리뷰 5개: c01-2026-1-r05, c01-2026-1-r07, c01-2026-1-r08, c02-2025-2-r04, c03-2026-1-r08.

| ID             | 개선안 누락                                    | 개선안 추가                                                                      |
| -------------- | ----------------------------------------- | --------------------------------------------------------------------------- |
| c01-2025-2-r06 | general_impression/positive               | learning/positive                                                           |
| c01-2025-2-r07 | -                                         | exam/neutral, general_impression/negative                                   |
| c01-2025-2-r08 | general_impression/positive               | -                                                                           |
| c01-2026-1-r05 | workload/neutral                          | -                                                                           |
| c01-2026-1-r07 | -                                         | general_impression/negative, workload/neutral                               |
| c01-2026-1-r08 | -                                         | general_impression/positive                                                 |
| c02-2025-2-r04 | -                                         | workload/negative                                                           |
| c02-2025-2-r05 | exam/neutral                              | exam/negative                                                               |
| c02-2025-2-r08 | professor/positive                        | -                                                                           |
| c02-2026-1-r05 | workload/neutral                          | -                                                                           |
| c02-2026-1-r06 | -                                         | professor/neutral                                                           |
| c02-2026-1-r07 | professor/negative                        | delivery/negative                                                           |
| c03-2025-2-r04 | grade/neutral                             | grade/positive                                                              |
| c03-2026-1-r01 | -                                         | attendance/neutral                                                          |
| c03-2026-1-r04 | exam/neutral                              | exam/positive                                                               |
| c03-2026-1-r05 | exam/positive                             | learning/positive                                                           |
| c03-2026-1-r06 | -                                         | workload/neutral                                                            |
| c03-2026-1-r07 | -                                         | delivery/neutral, learning/neutral                                          |
| c03-2026-1-r08 | -                                         | workload/neutral                                                            |
| c04-2025-2-r04 | -                                         | workload/negative                                                           |
| c04-2025-2-r05 | professor/negative, team_project/positive | professor/neutral, team_project/neutral                                     |
| c04-2025-2-r06 | -                                         | general_impression/positive, team_project/neutral, workload/negative        |
| c04-2025-2-r07 | -                                         | team_project/neutral                                                        |
| c04-2025-2-r08 | exam/neutral                              | exam/negative                                                               |
| c04-2026-1-r05 | learning/positive                         | exam/neutral                                                                |
| c04-2026-1-r06 | exam/neutral                              | -                                                                           |
| c04-2026-1-r07 | -                                         | team_project/negative                                                       |
| c04-2026-1-r08 | workload/negative                         | exam/negative, exam/positive, general_impression/negative, workload/neutral |

## 재현 방법

저장소 루트에서 기존 의존성을 설치하고 실행한다. 재채점은 저장 응답만 사용하며 API 키와 서버가 필요하지 않다.

```powershell
python -m pip install -r requirements.txt
python scripts/rescore_consistency.py --output consistency_eval.local.json
python -m unittest discover -s tests -v
```

첫 명령은 패키지를 설치한다. 나머지 명령에는 모델/API 호출이 없다. 결과 JSON의 checks가 모두 true인지 확인한다. gold와 예측은 모델 입력과 분리되어 있다.

## PR 포함 파일

- `analysis/prompt.py`: 기존 build_instructions(glossary) 인터페이스와 예시 3개를 유지한 v3 프롬프트.
- `docs/labeling_boundary_v2.md`, `docs/labeling_guide.md`: 적용 범위와 AI 판정 기준. 팀 승인 완료로 표시하지 않음.
- `data/reference_gold64_v1.jsonl`, `data/reference_gold64_v2.jsonl`: 라벨 수정 효과와 모델 효과를 분리하는 버전별 라벨.
- `data/consistency_challenge24.jsonl`: 새 합성 경계 확인 데이터. 독립 사람 holdout 아님.
- `docs/evaluation/day5_consistency/`: 수정 전후, 설정/해시/실패 후보 요약, 최종 후보 및 비교 기준선의 저장 응답.
- `scripts/rescore_consistency.py`, `tests/test_consistency_reference.py`: 오프라인 재채점과 회귀 확인.

## 실행과 한계

- 모델 gpt-6-luna, reasoning none, temperature 0, timeout 30초, retry 0, max_output_tokens 4000.
- 실험의 새 리뷰 호출은 총 221회다. 실패한 첫 후보 64회도 포함한다. 이 PR의 재현 도구는 추가 호출을 하지 않는다.
- 후보 v3 원시 응답은 개발 64개·기존 45개·새 확인셋 24개 모두 근거 exact 100%, 호출 실패 0이다. 근거 복원 코드는 최종 결과에 필요하지 않았으므로 PR에 포함하지 않는다.
- 기존 프로젝트와 정책/재채점 테스트 총 36개가 통과했다. 오프라인 재채점에서 모든 수치와 해시가 재현됐고 추가 API 호출은 0회다. HTTP/웹에서 변경 프롬프트를 호출하는 통합 검증은 실행하지 않았다.
- 전체 지표가 개선돼도 일부 리뷰는 회귀했다. 위의 5개 회귀와 28개 미완전 일치 사례를 숨기지 않는다.
- 이 수치는 AI가 정리한 기준과 합성 데이터에 대한 개발 평가다. 사람 정답·팀 승인·실제 사용자 일반화 성능으로 주장하지 않는다.
- 키·실제 .env·실제 학생 강의평·모델 가중치는 포함하지 않는다.
