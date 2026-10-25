import { useEffect, useRef, useState } from "react";
import { SENTIMENT_LABEL } from "../constants.js";
import { ruleDetail } from "../utils/detailText.js";
import { ovDetail, readOverview } from "../utils/overview.js";

const SORTS = [
  { key: "mentioned", label: "리뷰순" },
  { key: "positive", label: "만족순" },
  { key: "negative", label: "불만순" },
];

// 원문에서 이 항목의 근거만 강조. 근거가 원문과 정확히 일치할 때만 강조
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
      <mark key={r.start} className={`da-hl ${r.sentiment}`}>
        {text.slice(r.start, r.end)}
      </mark>,
    );
    cursor = r.end;
  }
  parts.push(text.slice(cursor));
  return <p className="da-original">{parts}</p>;
}

// 근거 문장 한 줄 (리뷰 하나), 원문은 기본 접힘
function EvidenceRow({ review, items, showSemester }) {
  const [open, setOpen] = useState(false);
  const text = review.text ?? "";
  return (
    <li className="da-ev">
      {items.map((it, i) => (
        <p key={i} className="da-ev-line">
          <span className={`da-sent ${it.sentiment}`}>{SENTIMENT_LABEL[it.sentiment] ?? it.sentiment}</span>
          <span className="da-quote">“{it.evidence}”</span>
        </p>
      ))}
      <div className="da-ev-foot">
        {showSemester && review.semester && <span className="num">{review.semester}학기</span>}
        {text && (
          <button type="button" className="da-link" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? "원문 접기" : "원문 보기"}
          </button>
        )}
      </div>
      {open && <Original text={text} items={items} />}
    </li>
  );
}

// 항목 하나: 비율 + 진단 (의미 단위 3~4줄) + 근거 문장(펼치기)
function Block({ row, entries, labels, result, showSemester }) {
  const [open, setOpen] = useState(false);
  const r = row.ratios ?? {};
  const name = labels[row.category] ?? row.category;
  const units = ovDetail(readOverview(result), row.category) ?? ruleDetail(row, entries, name);

  return (
    <section className="da-block">
      <div className="da-aside">
        <h2>{name}</h2>
        <p className="da-count num">언급 리뷰 {row.mentioned}개</p>
        <div className="sb-bar" aria-hidden="true">
          <span className="p" style={{ width: `${r.positive ?? 0}%` }} />
          <span className="n" style={{ width: `${r.negative ?? 0}%` }} />
          <span className="u" style={{ width: `${r.neutral ?? 0}%` }} />
        </div>
        <dl className="da-nums num">
          <div className="pos">
            <dt>만족</dt>
            <dd>{row.counts.positive}</dd>
          </div>
          <div className="neg">
            <dt>불만족</dt>
            <dd>{row.counts.negative}</dd>
          </div>
          <div>
            <dt>중립</dt>
            <dd>{row.counts.neutral}</dd>
          </div>
        </dl>
      </div>

      <div className="da-body">
      <ul className="da-text">
        {units.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>

      {entries.length > 0 && (
        <button type="button" className="da-link da-more" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "근거 문장 접기" : `근거 문장 보기 ${entries.length}`}
        </button>
      )}
      {open && (
        <ul className="da-evs">
          {entries.map((e) => (
            <EvidenceRow key={e.review.review_id} review={e.review} items={e.items} showSemester={showSemester} />
          ))}
        </ul>
      )}
      </div>
    </section>
  );
}

// 항목 선택 드롭다운 (전체 또는 여러 항목)
function FilterMenu({ options, selected, onChange, labels }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (e.type === "keydown" ? e.key === "Escape" : !ref.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const name = (c) => labels[c] ?? c;
  const label =
    selected.length === 0 ? "전체" : selected.length === 1 ? name(selected[0]) : `${name(selected[0])} 외 ${selected.length - 1}개`;
  const toggle = (c) => onChange(selected.includes(c) ? selected.filter((x) => x !== c) : [...selected, c]);

  return (
    <div className="da-menu" ref={ref}>
      <button type="button" className="da-select" aria-haspopup="true" aria-expanded={open} onClick={() => setOpen(!open)}>
        항목: {label}
      </button>
      {open && (
        <div className="da-pop">
          <label className="da-check">
            <input type="checkbox" checked={selected.length === 0} onChange={() => onChange([])} />
            전체
          </label>
          {options.map((c) => (
            <label key={c} className="da-check">
              <input type="checkbox" checked={selected.includes(c)} onChange={() => toggle(c)} />
              {name(c)}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

// 상세 분석 탭: 모든 항목을 펼친 상태로 나열, 정렬과 항목 필터
// filter: 고른 항목 코드 배열 ([] = 전체)
export default function DetailAnalysis({ result, labels, filter, onFilter, showSemester }) {
  const [sort, setSort] = useState("mentioned");

  const rows = result.summary_by_category.filter((s) => s.mentioned > 0);
  const sorted = [...rows].sort((a, b) =>
    sort === "mentioned"
      ? b.mentioned - a.mentioned
      : b.counts[sort] - a.counts[sort] || b.mentioned - a.mentioned,
  );
  const shown = filter.length === 0 ? sorted : sorted.filter((s) => filter.includes(s.category));
  const options = [...rows].sort((a, b) => b.mentioned - a.mentioned).map((s) => s.category);

  const entriesFor = (category) =>
    result.reviews
      .filter((rv) => rv.status !== "failed")
      .map((rv) => ({ review: rv, items: (rv.items ?? []).filter((it) => it.category === category) }))
      .filter((e) => e.items.length > 0);

  return (
    <div className="da">
      <div className="da-controls">
        <span className="da-selwrap">
        <select className="da-select" aria-label="정렬" value={sort} onChange={(e) => setSort(e.target.value)}>
          {SORTS.map((s) => (
            <option key={s.key} value={s.key}>
              {s.label}
            </option>
          ))}
        </select>
        </span>
        <FilterMenu options={options} selected={filter} onChange={onFilter} labels={labels} />
        {filter.length > 0 && (
          <>
            <span className="da-active">필터 적용 중</span>
            <button type="button" className="da-link" onClick={() => onFilter([])}>
              해제
            </button>
          </>
        )}
      </div>

      {shown.map((row) => (
        <Block
          key={row.category}
          row={row}
          entries={entriesFor(row.category)}
          labels={labels}
          result={result}
          showSemester={showSemester}
        />
      ))}
    </div>
  );
}
