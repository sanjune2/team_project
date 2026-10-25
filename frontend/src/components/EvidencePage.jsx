import { useEffect, useState } from "react";
import { SENTIMENT_LABEL } from "../constants.js";
import { splitNotes } from "../utils/summary.js";
import "../styles/detail.css";

const FILTERS = ["all", "positive", "negative", "neutral"];
const FILTER_LABEL = { all: "전체", ...SENTIMENT_LABEL };

// 원문에서 이 항목의 근거만 표시. 근거가 원문과 정확히 일치할 때만 강조
function Original({ text, items }) {
  const ranges = items
    .filter((it) => it.evidence_match === "exact" && it.evidence)
    .map((it) => {
      const start = text.indexOf(it.evidence);
      return { start, end: start + it.evidence.length, sentiment: it.sentiment };
    })
    .filter((r) => r.start >= 0)
    .sort((a, b) => a.start - b.start);

  const parts = [];
  let cursor = 0;
  for (const r of ranges) {
    if (r.start < cursor) continue; // 겹치는 근거는 앞의 것만
    if (r.start > cursor) parts.push(text.slice(cursor, r.start));
    parts.push(
      <mark key={r.start} className={`dt-hl ${r.sentiment}`}>
        {text.slice(r.start, r.end)}
      </mark>,
    );
    cursor = r.end;
  }
  parts.push(text.slice(cursor));
  return <p className="dt-original">{parts}</p>;
}

function ReviewRow({ review, items, showSemester }) {
  const [open, setOpen] = useState(false);
  const text = review.text ?? "";
  return (
    <li className="dt-row">
      <ul className="dt-items">
        {items.map((it, i) => (
          <li key={i}>
            <span className={`dt-sent ${it.sentiment}`}>{SENTIMENT_LABEL[it.sentiment] ?? it.sentiment}</span>
            <div className="dt-item-body">
              {splitNotes([it.summary]).map((s) => (
                <p key={s} className="dt-summary">
                  {s}
                </p>
              ))}
              {it.evidence && <p className="dt-quote">“{it.evidence}”</p>}
            </div>
          </li>
        ))}
      </ul>
      <div className="dt-foot">
        {showSemester && review.semester && <span className="num">{review.semester}학기</span>}
        {text && (
          <button type="button" className="dt-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? "원문 접기" : "원문 보기"}
          </button>
        )}
      </div>
      {open && <Original text={text} items={items} />}
    </li>
  );
}

// 상세 분석: 고른 항목이 언급된 리뷰만, 요약과 근거 → 원문(기본 접힘)
export default function EvidencePage({ result, category, side, labels, backLabel, onBack, showSemester }) {
  const [filter, setFilter] = useState(side ?? "all");
  const name = labels[category] ?? category;

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const rows = result.reviews
    .filter((r) => r.status !== "failed")
    .map((r) => ({ review: r, items: (r.items ?? []).filter((it) => it.category === category) }))
    .filter((x) => x.items.length > 0);

  const counts = { all: rows.length, positive: 0, negative: 0, neutral: 0 };
  for (const x of rows) {
    for (const s of new Set(x.items.map((it) => it.sentiment))) counts[s] = (counts[s] ?? 0) + 1;
  }

  const shown =
    filter === "all"
      ? rows
      : rows
          .map((x) => ({ ...x, items: x.items.filter((it) => it.sentiment === filter) }))
          .filter((x) => x.items.length > 0);

  return (
    <article className="result dt">
      <button type="button" className="dt-back" onClick={onBack}>
        {backLabel}
      </button>
      <header className="rv-head">
        <h1>{name}</h1>
        <p className="rv-meta num">
          <span>언급 리뷰 {rows.length}개</span>
        </p>
      </header>

      <div className="dt-tabs" role="group" aria-label="감성">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            className="dt-tab num"
            aria-pressed={filter === f}
            disabled={f !== "all" && !counts[f]}
            onClick={() => setFilter(f)}
          >
            {FILTER_LABEL[f]} {counts[f] ?? 0}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <p className="dt-empty">해당하는 리뷰가 없어요.</p>
      ) : (
        <ul className="dt-list">
          {shown.map((x) => (
            <ReviewRow key={x.review.review_id} review={x.review} items={x.items} showSemester={showSemester} />
          ))}
        </ul>
      )}
    </article>
  );
}
