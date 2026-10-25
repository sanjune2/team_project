// 상세 분석의 항목별 진단 문단
// 1순위: 결과 파일의 overview.details (LLM 정리본, 있을 때만)
// 2순위: 집계 숫자 + 리뷰별 요약 + 조건으로 만든 규칙 기반 문단 (없는 내용 생성 X)
import { josa, splitNotes } from "./summary.js";

// LLM 정리본: overview.details = [{ category, points: ["의미 단위 문장", ...] } 또는 { category, text }]
// 화면에는 의미 단위 3~4줄 목록으로 보여 줌
export function llmDetail(result, category) {
  const list = result?.overview?.details;
  if (!Array.isArray(list)) return null;
  const hit = list.find((d) => d?.category === category);
  if (Array.isArray(hit?.points)) {
    const points = hit.points.filter((t) => typeof t === "string" && t.trim()).map((t) => t.trim());
    return points.length ? points.slice(0, 4) : null;
  }
  if (typeof hit?.text === "string" && hit.text.trim()) {
    return hit.text.split(/\n+/).map((t) => t.trim()).filter(Boolean).slice(0, 4);
  }
  return null;
}

// "~다는 의견" → "~다는 점" (문장 안에 넣기 위해)
function toPoint(summary) {
  const s = summary.replace(/[.\s]+$/, "");
  if (s.endsWith("의견")) return `${s.slice(0, -2).trimEnd()} 점`;
  return `${s}라는 점`;
}

// A, B과 C (모두 "점"으로 끝나므로 받침에 맞춰 과/와)
function joinPoints(points) {
  if (points.length === 1) return points[0];
  const last = points[points.length - 1];
  const head = points.slice(0, -1).join(", ");
  return `${head}${josa(points[points.length - 2], "과", "와")} ${last}`;
}

function collect(entries, sentiment) {
  const points = [];
  for (const { items } of entries) {
    for (const it of items) {
      if (it.sentiment !== sentiment) continue;
      for (const s of splitNotes([it.summary ?? ""])) {
        const p = toPoint(s);
        if (!points.includes(p)) points.push(p);
      }
    }
  }
  return points;
}

const PER_LINE = 3; // 한 줄에 묶는 의견 수

// 의미 단위 목록: 전체 평가 → 많은 쪽 평가(3개씩 묶어 줄 나눔) → 반대쪽 평가 → 사실 언급
// 조건은 따로 덧붙이지 않음 (모델 요약 문장 안에 이미 들어 있는 경우가 많고, LLM 정리본에서 문장 안에 넣음)
export function ruleDetail(row, entries, name) {
  const { positive: p = 0, negative: n = 0, neutral: u = 0 } = row.counts ?? {};
  const topic = `${name}${josa(name, "은", "는")}`;
  const units = [];

  // ① 전체 평가
  const oneSided = (n === 0 && u === 0) || (p === 0 && u === 0);
  if (n === 0 && u === 0) units.push(`${topic} 리뷰 ${row.mentioned}개에서 언급됐고, 모두 좋게 평가됐어요.`);
  else if (p === 0 && u === 0) units.push(`${topic} 리뷰 ${row.mentioned}개에서 언급됐고, 모두 아쉬운 점으로 꼽혔어요.`);
  else if (p === 0 && n === 0)
    units.push(`${topic} 리뷰 ${row.mentioned}개에서 언급됐고, 평가보다는 운영 방식을 설명하는 내용이 중심이었어요.`);
  else {
    const dist = [p && `만족 ${p}건`, n && `불만족 ${n}건`, u && `중립 ${u}건`].filter(Boolean).join(", ");
    const lean = p > n ? "좋게 본 의견이 더 많았어요" : n > p ? "아쉽다는 의견이 더 많았어요" : "평가가 엇갈렸어요";
    units.push(`${topic} 리뷰 ${row.mentioned}개에서 언급됐고, ${dist}으로 ${lean}.`);
  }

  // ②③④ 감성별 (많은 쪽 먼저). 의견은 3개씩 한 줄로 묶고, 남으면 다음 줄로 이어 감
  const order = n > p ? ["negative", "positive", "neutral"] : ["positive", "negative", "neutral"];
  let evaluated = 0;
  for (const s of order) {
    const points = collect(entries, s);
    if (!points.length) continue;
    const lead = evaluated > 0 && s !== "neutral" ? "반면 " : "";
    const verb = s === "positive" ? "을 들었어요" : "이 지적됐어요";

    for (let i = 0; i < points.length; i += PER_LINE) {
      const shown = joinPoints(points.slice(i, i + PER_LINE));
      const next = ["또", "이 밖에도", "그 외에도"][Math.min(i / PER_LINE - 1, 2)];
      if (i > 0) units.push(`${next} ${shown}도 ${s === "positive" ? "좋게 평가됐어요" : s === "negative" ? "지적됐어요" : "언급됐어요"}.`);
      else if (oneSided && s !== "neutral") units.push(`주로 ${shown}${verb}.`);
      else if (s === "positive") units.push(`${lead}좋게 본 리뷰에서는 ${shown}을 들었어요.`);
      else if (s === "negative") units.push(`${lead}아쉬운 점으로는 ${shown}이 지적됐어요.`);
      else if (evaluated === 0) units.push(`구체적으로는 ${shown}이 언급됐어요.`);
      else units.push(`평가와 별개로 ${shown}도 언급됐어요.`);
    }
    if (s !== "neutral") evaluated += 1;

  }

  return units;
}
