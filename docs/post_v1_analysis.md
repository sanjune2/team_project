# v1.0 이후 분석 후속 작업

작업 기준은 main `8feda82`이며 제출 태그 `v1.0`은 변경하지 않았다.
이 문서는 로컬 구현과 검증 결과다. PR 검토·병합 전에는 제출본에 반영된 것으로 표시하지 않는다.

## 9-1 판정 기준 합의

2026-10-26 사용자가 혜린·상준·동렬 전원 동의를 확인했다.
판정 기준 14/14 동의, 이견 0이다. 앞서 제시한 개인 제안은 기준에 적용하지 않았다.
이는 기준에 대한 팀 합의다. 개별 정답 라벨의 독립 사람 검수나 기존 F1 수치 승인은 아니다.
원본 `docs/labeling_boundary_v2.md`와 동결 평가 자료는 유지했다. Notion 결과에 별도 기록했다.

## 생성기 비교와 통합

GitHub `feat/backend-overview`의 `scripts/build_reference_data.py`와 main의 같은 파일은
동일한 Git blob `23e38d0083cda04adba9064ce924b7f82db9f7c8`이었다.
PR #27의 실제 main 변경은 API 문서 35줄이며 overview 생성 코드 변경은 없었다.
따라서 GitHub에서 비교 가능한 생성 경로를 공용 `analysis/overview_runner.py`로 통합했다.

- `scripts/build_reference_data.py --overview-only`: 저장 결과를 읽고 overview만 생성한다.
- 같은 명령의 `--with-overview`: 기존 리뷰 분석과 집계 뒤 overview 단계를 실행한다. 실제 재분석 호출이 발생한다.
- `scripts/build_overview_data.py`: 기존 명령을 유지하는 호환 진입점이다. 별도의 생성 로직을 두지 않는다.
- 기존 분석·집계·API 계약은 유지한다. 입력·검토 결과·감사 폴더는 서로 분리한다.

```powershell
# 리뷰 재분석 없이 기존 12개 결과로 실행 (실제 overview API 호출)
python scripts/build_reference_data.py --overview-only --out frontend/public/reference --overview-out staging/overview --overview-audit staging/overview-audit

# 기존 명령도 같은 공용 생성기를 사용
python scripts/build_overview_data.py --out-dir staging/overview --audit-dir staging/overview-audit
```

생성 결과는 staging에 둔다. 기존 배포 결과를 자동 교체하지 않는다.
품질 검사 지적이 있으면 `generated_needs_review`로 기록한다. 이 상태는 사람 검토 완료가 아니다.

## 출력 잘림에 대한 분할 호출

전체 overview 응답이 `max_output_tokens`로 잘린 경우에만 분할한다.
요약(left/right/suggestion)을 먼저 받고, 언급된 category를 하나씩 호출한다.
각 category의 입력은 해당 항목의 집계와 분석 요약·조건·ID만 포함한다. 원문을 모델에 보내지 않는다.
응답의 category가 요청한 항목과 정확히 일치하는지 확인하고 기존 검증·basis 계산·정렬을 재사용한다.
분할 응답도 잘리거나 형식이 잘못되면 실패한다. 무제한 재시도와 부분 결과 배포는 하지 않는다.

호출별 상태·출력·usage와 실제 시도 수를 audit에 남긴다.
완료 상태를 먼저 확인한 뒤 JSON을 검증하므로 잘린 JSON을 SDK 자동 파서에 먼저 넘기지 않는다.
분할 실패 시 기존 입력과 이미 있던 결과 파일을 보존하는 모의 시험을 통과했다.
실제 smoke는 저장된 `c02_2026-1.json` 한 파일로 1회 성공했다. 분할 경로의 검증은 모의 응답 시험이다.

## 합성 holdout 20개 잠정 평가

사람 라벨 검수 전 AI 초안 대비 잠정 평가를 실행하라는 사용자 승인을 받고 진행했다.
기존 계획의 v2 첫 측정과 구분하여 현재 main의 v3를 평가했다.
20개 원문과 22개 라벨, 기존 manifest는 수정하지 않았다. 실제 호출 전 프롬프트·사전·스키마·설정을 동결했다.
모델에는 text/semester만 보냈으며 정답 라벨은 보내지 않았다.

- 모델 `gpt-6-luna`, reasoning `none`, temperature 0, timeout 30초, retry 0.
- 새 리뷰 분석 호출 20회, 성공 20, 실패 0.
- 항목 F1 100%, 항목+감성 F1 100%, 리뷰 조합 완전 일치 20/20.
- 근거 원문 일치 22/22. 조건 유무·문구 일치 21/22. 변경 표시 일치 22/22.
- 조건의 의미적 적절성은 별도 사람 검토 대상이다. 결과를 본 뒤 라벨이나 프롬프트를 수정하지 않았다.
- AI 지원 합성 초안 라벨 대비 작은 잠정 평가다. 독립 사람 정답 평가, 실제 사용자 정확도, 학습 데이터 미포함을 보장하지 않는다.
- 이 결과로 프롬프트를 개선한다면 이 20개는 이후 개발 데이터로 구분하고 새로운 미사용 세트를 마련한다.

상세 결과와 동결 정보는 `docs/evaluation/post_v1_holdout20/`에 있다.

```powershell
# 준비만 수행: API 호출 없음
python scripts/evaluate_holdout.py --out-dir staging/holdout20
# 실제 평가: 사용자 승인과 잠정 평가 표시를 전제로 실행
python scripts/evaluate_holdout.py --out-dir staging/holdout20 --run --allow-ai-draft-labels
```

실행 시작 파일이나 예측 결과가 있는 폴더는 재실행하지 않는다. 재평가를 첫 측정으로 덮어쓰지 않도록 보호한다.

## 운영체제 검증과 담당 범위

Windows Python 3.14에서 오프라인 테스트 66개 통과.
`.github/workflows/analysis-portability.yml`에서 Ubuntu/macOS/Windows Python 3.11 검증을 실행했다.
워크플로는 API 키 없이 오프라인 테스트와 저장 평가 재현을 실행한다.
이 PC에는 사용 가능한 WSL과 Mac 실행 환경이 없어 GitHub 호스팅 러너를 사용했다.
세 환경 모두 의존성 설치, 테스트 66개, 저장 평가 재현을 통과했다.
실제 결과: https://github.com/sanjune2/team_project/actions/runs/40206977157
검증한 구현 커밋은 `aa4746f`다. 이 결과는 서버 분석 모듈·도구의 이식성 검증이며 Mac/Linux 브라우저 UI 검증은 아니다.

fallback 첫 문장, 같은 항목의 긍정·부정 반복, 좁은 두 단 양쪽 정렬은 화면 담당 후속 작업으로 남겼다.
프론트 소스와 기존 화면 결과 JSON, 리뷰 분석 프롬프트는 변경하지 않았다.
