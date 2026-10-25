# 8번 overview 전체 생성과 품질 검토

기준 main: `5b8bf58` (PR #25 병합).
7번은 Notion 형식 사용 합의와 혜린님의 시험 확인을 완료했다.
혜린님 피드백 5가지를 반영해 교수자 8개와 학습자 4개를 생성했다.

## 반영 결과

1. 소수 의견은 근거 건수를 표시한다. 검증한 review_ids의 고유 개수로 basis를 계산하며 문장 건수도 여기서 채운다. 교수자 소수 의견에는 권고 문구를 붙이지 않았다.
2. 교수자 right에서 학생의 취향·성향 조건을 제외했다.
3. 교수자 suggestion은 구체적인 1~2문장으로 정리하고 반복적인 '~볼 수 있어요'를 제거했다.
4. 에쁠은 A+처럼 은어를 풀어 썼다.
5. 학습자 left는 건수와 함께 '~한 학생에게 맞아요'로 끝나는 추천 문장으로 정리했다.

기존 리뷰별 결과, summary_by_category, counts, ratios, top_pros, top_cons, meta는 모두 보존했다.
실제 overview 호출은 12회이며 리뷰 재분석은 0회다. 생성 실패는 0개다.
기존 `/api/analyze` 응답 계약과 `scripts/build_reference_data.py`는 변경하지 않았다.

## 생성 도구

원격 main에 11번 overview 단계가 없어 기존 시험 생성기를 별도 도구로 확장했다.
`scripts/build_overview_data.py`는 저장 결과만 읽고, 별도 staging 폴더에 결과와 감사 기록을 저장한다.
검사 실패 시 입력 파일을 덮어쓰지 않는다. 모델의 미완료·형식 오류를 기록한다.
기존 백엔드 생성 스크립트와 병합하지 않았으므로 상준 담당 11번의 통합 완료를 의미하지 않는다.

```powershell
python scripts/build_overview_data.py --out-dir staging/overview --audit-dir staging/overview-audit
```

실행에는 기존 OPENAI_API_KEY와 OPENAI_MODEL 설정이 필요하다. 위 명령은 실제 API 호출을 한다.
입력은 항목별 집계와 분석 요약·조건·ID다. 강의평 원문을 overview 모델에 보내지 않는다.

## 검증과 문제 건수

- 교수자 8개, 학습자 4개 전수 검사.
- 근거 ID와 항목·감성 일치, 고유 ID 기준 basis, 문장 건수, 내림차순 정렬, 원본 분석·집계 보존 확인.
- 근거 검증 4곳에서 잘못 연결된 ID 6개를 제거하고 남은 근거로 문장을 재검토했다.
- 학습자 추천 형태 12건, 근거 없는 조건·미래 결과 표현 2건을 수정했다.
- 의미 범위·중복 묶음·불필요한 상세 표현 10건을 추가 수정했다.
- 가운뎃점 등 구분자 표현 13곳을 풀어 썼다. 건수 누락 문장은 검증된 ID 수로 보완했다.
- 최종 기계 검사에서 남은 형식·ID·건수·정렬·피드백 규칙 오류 0건.
- Python 테스트 54개, 프론트 결과 읽기 12개, production build 통과.
- 기본 포털 주소에서 교수자·학습자 결과와 상세 분석을 확인했다. 390px 모바일 가로 넘침 없음.

자세한 근거는 `docs/evaluation/day6_overview/`에 있다. 수정 전 모델 출력과 전체 수정 스냅샷은 로컬 감사 폴더에 보존했다.

## 변경 파일과 역할

- `analysis/overview_prompt.py`: 합의 형식과 혜린 피드백을 포함한 생성 지침.
- `analysis/overview_contract.py:validate_overview`: 형식·근거 ID·basis·정렬 검증.
- `analysis/overview_generation.py:make_input`, `finalize`, `policy_findings`: 입력 구성, 건수 치환, 피드백 규칙 검사.
- `scripts/build_overview_data.py`: 별도 결과 생성 명령.
- `frontend/public/reference/*.json`: overview를 추가한 12개 결과.
- `tests/test_overview_contract.py`, `tests/test_overview_generation.py`, `scripts/check_overview_data.mjs`: 오프라인 및 프론트 읽기 검사.

## 한계와 남은 일

의미 검토는 AI 지원 전수 검토다. 독립 사람 검수나 일반화 성능 검증이 아니다.
ID가 맞아도 모든 의미가 정확하다는 보장은 없다. 전체 12개에 대한 팀 최종 화면 확인이 남아 있다.
기존 분석의 분류 오류와 AI 지원 라벨 한계는 그대로 남는다.
첫 문단에서 같은 항목이 긍정·부정에 반복되는 문제와 좁은 두 단의 양쪽 정렬은 혜린님 마무리 PR 범위다.
팀 검토와 병합, 최신 main 통합, 최종 캡처·태그는 별도다.
