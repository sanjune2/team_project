// 결과 파일의 overview (LLM 정리본) 읽기. 형식: docs 🧩 "결과 문장 품질 개선" 페이지
// 필드마다 따로 검사해서, 있는 것만 쓰고 없거나 깨진 것은 null → 화면이 규칙 기반 문장으로 대체
const str = (v) => (typeof v === "string" && v.trim() ? v.trim() : null);

// 묶음의 리뷰 수: 스크립트가 채운 basis 우선, 없으면 review_ids 개수
const size = (g) =>
  Number.isFinite(g?.basis) ? g.basis : Array.isArray(g?.review_ids) ? new Set(g.review_ids).size : 0;

export function readOverview(result) {
  const o = result?.overview;
  return o && typeof o === "object" && !Array.isArray(o) ? o : null;
}

// 유지할 점 / 개선 검토, 추천 / 고려: [{ name, text }] 최대 3개
export function ovList(ov, side) {
  const list = ov?.[side];
  if (!Array.isArray(list)) return null;
  const items = list
    .map((it) => ({ name: str(it?.keyword), text: str(it?.text) }))
    .filter((it) => it.text)
    .slice(0, 3);
  return items.length ? items : null;
}

// 교수자 방향 제안 문단
export function ovSuggestion(ov) {
  return str(ov?.suggestion);
}

function category(ov, code) {
  return Array.isArray(ov?.categories) ? ov.categories.find((c) => c?.category === code) : null;
}

// 리뷰 수 많은 순으로 정렬한 의견 묶음
function groups(ov, code) {
  const list = category(ov, code)?.groups;
  if (!Array.isArray(list)) return [];
  return list.filter((g) => g && typeof g === "object").sort((a, b) => size(b) - size(a));
}

// 요약 TOP 3 항목 아래 한 줄
export function ovHeadline(ov, code, sentiment) {
  return str(category(ov, code)?.headline?.[sentiment]);
}

// 요약 TOP 3 펼친 목록: 그 감성의 묶음 short, 많은 순 3개
export function ovShort(ov, code, sentiment) {
  const list = groups(ov, code)
    .filter((g) => g.sentiment === sentiment)
    .map((g) => str(g.short))
    .filter(Boolean)
    .slice(0, 3);
  return list.length ? list : null;
}

// 상세 분석 진단 목록: 모든 묶음 detail, 많은 순 최대 5개
export function ovDetail(ov, code) {
  const list = groups(ov, code)
    .map((g) => str(g.detail))
    .filter(Boolean)
    .slice(0, 5);
  return list.length ? list : null;
}
