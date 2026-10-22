# 45개 평가 실행

기준 데이터는 팀 저장소의 `data/test_reviews.jsonl` 45개다.
상위 로컬 폴더의 동명 파일과 `data/archive/`는 사용하지 않는다.
로컬 데이터 병합 후보는 별도 PR 범위다.

Python 환경에서 `requirements.txt`를 설치한 뒤 실행한다.

```powershell
python -m unittest discover -s tests -v
python -m analysis.evaluate --live
```

`--live`는 비공개 `.env`의 모델과 API 키를 사용한다. 유료 API 45회를 호출한다.
모델에는 `text`·`semester`만 전달한다. 정답·태그·메모는 전달하지 않는다.
실제 응답은 `evaluation_v1.local.json`에 저장한다. 이 파일은 Git 제외 대상이다.
결과 표는 `docs/eval_v1.md`에 저장한다.

기존 응답을 다시 평가할 때는 API를 호출하지 않는다.

```powershell
python -m analysis.evaluate --predictions evaluation_v1.local.json
```

모델 비교는 같은 프롬프트·추론 설정·출력 한도·timeout·retry로 실행한다.
추론 설정을 low로 비교하면 두 모델 모두 temperature를 전송하지 않는다.
기존 none/temperature=0 결과와 low 결과를 모델 차이로 해석하지 않는다.

```powershell
python -m analysis.evaluate --live --model gpt-5-nano --reasoning-effort low --stop-on-error --output evaluation_nano_low.local.json --report docs/eval_nano_low.md
python -m analysis.evaluate --live --model gpt-6-luna --reasoning-effort low --stop-on-error --output evaluation_luna_low.local.json --report docs/eval_luna_low.md
```

비교 후보의 첫 호출 실패 시 중단한다. 부분 응답은 남기되 전체 정확도 표는 만들지 않는다.

저장된 예측과 정답의 데이터 해시·리뷰 ID가 다르면 평가를 중단한다.
45개가 아니어도 중단한다. 부분 실행을 전체 정확도로 표시하지 않는다.
실패 리뷰는 FN과 실패율에 포함한다. 오류를 빈 정답 성공으로 처리하지 않는다.
분모가 없는 지표는 `null`로 저장한다.

라벨 교차 검토가 완료되면 동일한 파일인지 확인한 뒤 `--label-status`로 확인 근거를 기록한다.
`condition` 내용은 `evaluation_v1.local.json`의 `field_review`에서 사람이 의미를 비교해야 한다.
정답 필드 누락 수와 일치한 항목 수를 함께 확인한다.
