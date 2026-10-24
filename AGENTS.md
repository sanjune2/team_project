# Project guidance

- 답변과 문서는 짧고 명확한 한국어로 작성합니다.
- 프로젝트 목표: 강의평 입력, 항목별 감성 분석, 웹 대시보드.
- MVP를 먼저 완성합니다. AI-Hub 모델 개선은 후속 작업입니다.
- frontend/, backend/, ai/, docs/의 역할을 유지합니다.
- API 계약은 docs/api-contract.md가 기준입니다. 현재 v0.1은 제안 상태입니다.
- main에서 직접 구현하지 않습니다. 이슈별 브랜치와 PR을 사용합니다.
- API 키, 실제 .env, 개인정보가 있는 데이터와 모델 가중치를 커밋하지 않습니다.
- 변경에 맞는 검증을 실행합니다. 실행하지 못한 검증은 명시합니다.
- 현재 실행 앱이 없습니다. 구현 PR에 실제 설치와 실행 방법을 추가합니다.
- 프론트 화면 작업은 frontend/DESIGN_GUIDE.md를 따릅니다. 색·글자·간격은 frontend/src/styles/tokens.css 변수만 씁니다.