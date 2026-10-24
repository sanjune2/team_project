export const SENTIMENT_LABEL = {
  positive: "만족",
  negative: "불만족",
  neutral: "중립",
  mixed: "혼합",
};

// 평가 항목 한글 이름 (backend/schemas.py CATEGORY_LABELS와 같음)
// 서버 없이 결과 파일만 읽는 화면에서도 쓰기 위해 프론트에도 둠
export const CATEGORY_LABEL = {
  workload: "과제량·로드",
  exam: "시험·평가 방식",
  team_project: "팀 프로젝트",
  delivery: "전달력·수업 구성",
  attendance: "출석·참여",
  grade: "성적·학점",
  learning: "학습 가치",
  professor: "교수자 태도",
  general_impression: "총평",
  etc: "기타",
};
