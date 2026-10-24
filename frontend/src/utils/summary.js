// 결과 JSON(/api/analyze 응답 + reviews[].text)에서 종합 요약 화면에 필요한 값을 계산
// 모든 문장은 모델 결과(요약·조건)나 집계 숫자에서만 만든다 (없는 내용 생성 X)

// TOP 3에서 제외하는 항목 (총평은 종합 의견에서 다룸)
const EXCLUDE = new Set(["general_impression", "etc"]);

// 만족 TOP 3 = 긍정 리뷰 수 순, 불만족 TOP 3 = 부정 리뷰 수 순, 동률이면 언급 리뷰 수 순
export function topItems(summary, sentiment) {
  return summary
    .filter((s) => !EXCLUDE.has(s.category) && s.counts[sentiment] > 0)
    .sort((a, b) => b.counts[sentiment] - a.counts[sentiment] || b.mentioned - a.mentioned)
    .slice(0, 3);
}

// 모델이 "A / B"처럼 이어 붙인 요약을 한 줄씩 나눔
export function splitNotes(list = []) {
  return list.flatMap((t) => t.split(" / ").map((s) => s.trim()).filter(Boolean));
}

// 받침에 따라 조사 선택 (예: 전달력은 / 학습 가치는)
export function josa(word, withFinal, withoutFinal) {
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  if (code < 0 || code > 11171) return withoutFinal;
  return code % 28 ? withFinal : withoutFinal;
}

// 조건(condition)을 항목별로 모음: { 항목코드: [조건, ...] }
function conditionsBy(reviews, sentiment) {
  const groups = {};
  for (const r of reviews) {
    for (const item of r.items ?? []) {
      if (item.sentiment !== sentiment || !item.condition || item.category === "etc") continue;
      const list = (groups[item.category] ??= []);
      if (!list.includes(item.condition)) list.push(item.condition);
    }
  }
  return groups;
}

function joinNames(codes, labels) {
  return codes.map((c) => labels[c] ?? c).join(", ");
}

// 종합 의견: 총평 한 문장 + 왼쪽·오른쪽 목록 (교수자 / 학습자)
export function buildOverview(result, mode, labels) {
  const ok = result.reviews.filter((r) => r.status === "ok");
  const count = (s) => ok.filter((r) => r.overall_sentiment === s).length;
  const parts = [
    [count("positive"), "만족"],
    [count("mixed"), "장단점을 함께 언급"],
    [count("negative"), "불만족"],
  ].filter(([n]) => n > 0);

  const pos = topItems(result.summary_by_category, "positive");
  const neg = topItems(result.summary_by_category, "negative");
  const good = pos.slice(0, 2).map((s) => s.category);
  const bad = neg.slice(0, 2).map((s) => s.category);

  let lead = `리뷰 ${ok.length}개`;
  if (parts.length) lead += ` 중 ${parts.map(([n, t]) => `${n}개는 ${t}`).join(", ")}이에요.`;
  else lead += "를 분석했어요.";
  const tail = [];
  if (good.length) {
    const names = joinNames(good, labels);
    tail.push(`${names}${josa(names, "은", "는")} 좋게`);
  }
  if (bad.length) {
    const names = joinNames(bad, labels);
    tail.push(`${names}${josa(names, "은", "는")} 아쉽게`);
  }

  const posCond = conditionsBy(ok, "positive");
  const negCond = conditionsBy(ok, "negative");

  if (mode === "learner") {
    const recommend = Object.values(posCond).flat().slice(0, 3).map((text) => ({ text }));
    const caution = Object.entries(negCond)
      .slice(0, 3)
      .map(([code, list]) => ({ name: labels[code] ?? code, text: list.slice(0, 2).join(", ") }));
    return {
      lead,
      tail: tail.length ? `${tail.join(", ")} 평가됐어요.` : "",
      left: { title: "이런 학생에게 추천", items: recommend },
      right: { title: "이런 경우라면 고려 필요", items: caution },
    };
  }

  const keep = pos.map((s) => ({ name: labels[s.category] ?? s.category, text: splitNotes(s.top_pros)[0] }));
  const improve = neg.map((s) => {
    const conds = (negCond[s.category] ?? []).slice(0, 3);
    const note = splitNotes(s.top_cons)[0];
    return { name: labels[s.category] ?? s.category, text: note, extra: conds.length ? `특히 ${conds.join(", ")}` : "" };
  });
  return {
    lead,
    tail: tail.length ? `${tail.join(", ")} 평가됐어요.` : "",
    left: { title: "유지하면 좋을 점", items: keep },
    right: { title: "개선을 검토할 점", items: improve },
  };
}
