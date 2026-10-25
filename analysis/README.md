# Analysis

항목별 감성 분석 프롬프트, LLM 호출, 평가 함수입니다.

- 프롬프트: `prompt.py` (v3). 규칙 원본은 [docs/labeling_guide.md](../docs/labeling_guide.md), 경계 기준은 [docs/labeling_boundary_v2.md](../docs/labeling_boundary_v2.md)
- LLM 호출: `llm.py` (백엔드가 `USE_MOCK=false`일 때 사용)
- 평가: `evaluate.py`, 재현은 `python scripts/rescore_consistency.py --output consistency_eval.local.json`
- 평가 기록: [docs/day5_consistency_improvement.md](../docs/day5_consistency_improvement.md)
- 원본 데이터, 실제 학생 강의평, 모델 가중치는 Git에 올리지 않습니다.
