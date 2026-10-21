// evidence_match가 exact인 근거만 원문에서 하이라이트
export default function HighlightedText({ text, items }) {
  const ranges = items
    .filter((it) => it.evidence_match === "exact")
    .map((it) => {
      const start = text.indexOf(it.evidence);
      return { start, end: start + it.evidence.length, sentiment: it.sentiment };
    })
    .filter((r) => r.start >= 0)
    .sort((a, b) => a.start - b.start);

  const parts = [];
  let cursor = 0;
  for (const r of ranges) {
    if (r.start < cursor) continue; // 겹치는 근거는 건너뜀
    if (r.start > cursor) parts.push(text.slice(cursor, r.start));
    parts.push(
      <mark key={r.start} className={`hl ${r.sentiment}`}>
        {text.slice(r.start, r.end)}
      </mark>,
    );
    cursor = r.end;
  }
  parts.push(text.slice(cursor));
  return <p className="original">{parts}</p>;
}

