# 3일차 팀 전달 내용

기준: 평가 PR #7이 병합된 main d0e7798. 아래는 팀에 붙여 넣을 전달문이다.
Discord나 팀원에게 직접 발송하지 않았다. 노션 변경은 아래에 구분했다.

## 팀 전달문

```text
[동렬 / 3일차 후속 작업 / PR #10]

1. v2 동일 설정 재실행 1회 완료
- 프롬프트·사전·45개 데이터 해시 동일. Luna / none / temperature=0 / 30초 / retry=0 / 출력4000 유지.
- 45/45 성공. 항목 F1 95.14%, 감성 91.58%, 근거 exact 98.99%.
- g07·c02의 반어 총평 부정 누락이 동일하게 재현됐습니다.
- mentions_change도 3/5로 재현됐습니다. c06 attendance·neutral item 누락 + delivery·positive의 false입니다.
- 재실행 결과를 보고 프롬프트를 추가 수정하거나 다시 호출하지 않았습니다.

2. 17시 통합용 리뷰 20개 준비 완료
- 단일4 / 중립4 / 혼합5 / 반어4 / 평가없음3.
- 순서: m01, g01, t02, t04, g07, g10, t01, m02, g05, t07, c02, c08, m09, t08, c14, c10, m10, m04, c15, c05.
- data/integration_reviews_20.txt: 웹에 원문 20줄 전체 붙여 넣기.
- data/integration_reviews_20.json: /docs·HTTP 요청 본문. 원본 ID·학기 보존.
- 현재 main 웹은 r001~r020으로 ID를 다시 만듭니다. 원본 ID 매핑은 docs/integration_reviews_20.md에 있습니다.
- 선택·형식 검사만 완료했습니다. 실제 17시 HTTP·웹 통합 검증은 아직입니다.

3. 데이터 분리 PR #10 제출 완료 (미병합)
- PR: https://github.com/sanjune2/team_project/pull/10 / sanjune2님 리뷰 요청.
- 기존 로컬 후보10개: data/local_review_candidates.jsonl. 모두 과거 Qwen/프롬프트 실험 사용 기록이 있어 엄격한 미사용 holdout은 아닙니다.
- 신규 합성 holdout20개: data/holdout_reviews.jsonl. v2 동결 후 새로 작성했고 이 파일의 대상 모델 호출은 0회입니다.
- 신규 holdout 정답은 AI 지원 초안입니다. 사람이 검토·합의하고 다시 해시를 동결한 뒤 첫 평가를 진행해야 합니다.
- 기존45개는 수정·합치지 않았습니다. 새20개를 기존45개 점수와 섞지 않습니다.

4. 라벨 검토 및 경계 정리안 작성 완료 / 팀 확정 대기
- c05: 시험 수행의 어려움이므로 exam·negative 유지안. 수업을 따라가는 어려움이면 delivery로 구분하자는 안입니다.
- m04: delivery·positive + etc·negative 유지안. 명시된 학습 성과가 있을 때 learning으로 분류하자는 안입니다.
- 노션에도 선수지식 일반 규칙과 c05 예시 충돌이 있습니다. 팀 확인 전 정답·가이드·프롬프트는 변경하지 않았습니다.
- m06의 grade 감성과 t09 workload 라벨도 사람 확인이 필요합니다.
- 동렬 담당15개 전부의 검토 결론은 docs/label_boundary_decision.md에 있습니다. 사람 교차 검토 완료를 대신하지 않습니다.

5. 모델 확정 노션 기록 일부 완료
- 3일차 본문의 결론을 gpt-6-luna 확정으로 최소 수정했고 새로고침으로 저장 확인했습니다.
- 기술스택 OPENAI_MODEL에는 이미 gpt-6-luna가 있습니다. 다만 문서가 읽기 전용이고 추론 설정의 non 표기와 추후 확정 문구가 남았습니다.
- 기술스택 문서 편집 권한이 있는 분이 OPENAI_REASONING_EFFORT=none으로 확인·정리하고 확정 기록을 완료해 주세요.
- 기술스택 반영이 끝나지 않아 7번은 미체크로 유지했습니다. 5·6번의 기존 체크는 보존했습니다.

[남은 확인]
- c05·m04 유지안 팀 합의, m06·t09 및 신규 holdout 사람 라벨 검토.
- 기술스택 확정 문구·non 표기 정리 후 7번 완료 체크.
- 17시 실제 웹20개 실행과 집계·근거·실패 제외 확인.
- HTTP·웹 통합과 신규 holdout 정확도를 완료했다고 표시하지 않았습니다.
```

## 근거와 파일

- 재현 점검: [eval_v2_recheck_comparison.md](eval_v2_recheck_comparison.md)
- 통합20개·ID 매핑·원문: [integration_reviews_20.md](integration_reviews_20.md)
- 라벨 경계안: [label_boundary_decision.md](label_boundary_decision.md)
- 후보 사용 이력: [local_review_candidates.md](local_review_candidates.md)
- 신규 holdout 절차: [holdout_protocol.md](holdout_protocol.md)
- 노션 3일차: https://app.notion.com/p/3-7a5ab1969cf582f7a9b701ddf43f896b
- 노션 기술 스택·가이드: https://app.notion.com/p/1-75cab1969cf583119c7f015c2da91b0b

## 신규 holdout 동결

- 동결 시각 UTC: 2026-10-22T05:15:58.913982+00:00
- 데이터 SHA-256: `1692bb1d079b2373e33a25df0dc9f3e224edcbcd676b2665008511a03212511f`
- 평가 대상 v2 instructions SHA-256: `8044b7c8d55019191f1cce7410342823fce605c915180e8caa32cf670f618491`
- 신규20개에 모델 호출 0회. 첫 정확도 수치는 아직 없음.

## 이번 검증

- 기존 분석·평가 테스트 24개 통과.
- 통합20개 요청 스키마·원문 일치·한 줄당 한 리뷰·웹 ID 매핑 검사 통과.
- 재사용 후보10개 JSON 필드·LF 정규화·사용 이력과 신규 holdout20개 ID·라벨·근거·해시 검사 통과.
- 원본45개·분석 코드·프롬프트·사전·가이드·Backend는 변경하지 않음.
- 검증 과정에서 API를 추가 호출하지 않음. 요청한 v2 재실행 45회만 수행.
