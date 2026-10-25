import { Fragment, useState } from "react";
import useMediaQuery from "../hooks/useMediaQuery.js";
import { ovHeadline, ovShort } from "../utils/overview.js";
import { splitNotes, topItems } from "../utils/summary.js";

const SIDES = [
  { key: "positive", title: "만족", cls: "pos", notes: "top_pros" },
  { key: "negative", title: "불만족", cls: "neg", notes: "top_cons" },
];

// 항목 한 칸: 접힌 상태는 대표 요약 한 줄, 펼치면 비율 + 그쪽 의견 최대 3개
// overview(LLM 정리본)가 있으면 그 문장, 없으면 집계의 대표 요약
function Cell({ row, rank, side, open, onToggle, onDetail, labels, last, ov }) {
  if (!row) return <div className={`sb-cell empty${last ? " last" : ""}`} />;
  const notes = ovShort(ov, row.category, side.key) ?? splitNotes(row[side.notes]).slice(0, 3);
  const headline = ovHeadline(ov, row.category, side.key) ?? notes[0];
  const r = row.ratios ?? {};
  return (
    <div className={`sb-cell${open ? " open" : ""}${last ? " last" : ""}`}>
      <button type="button" className="sb-head" aria-expanded={open} onClick={onToggle}>
        <span className="sb-rank num">{rank}</span>
        <span className="sb-name">{labels[row.category] ?? row.category}</span>
        <span className="sb-count num">리뷰 {row.counts[side.key]}개</span>
      </button>
      {!open && headline && <p className="sb-note">{headline}</p>}
      {open && (
        <div className="sb-detail">
          <div className="sb-ratio num">
            <div className="sb-bar" aria-hidden="true">
              <span className="p" style={{ width: `${r.positive ?? 0}%` }} />
              <span className="n" style={{ width: `${r.negative ?? 0}%` }} />
              <span className="u" style={{ width: `${r.neutral ?? 0}%` }} />
            </div>
            <span>만족 {Math.round(r.positive ?? 0)}%</span>
            <span>불만족 {Math.round(r.negative ?? 0)}%</span>
            <span>중립 {Math.round(r.neutral ?? 0)}%</span>
          </div>
          <ul>
            {notes.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
          <button type="button" className="sb-more" onClick={() => onDetail(row.category)}>
            상세 분석 보기
          </button>
        </div>
      )}
    </div>
  );
}

// 만족 TOP 3 │ 불만족 TOP 3. 데스크톱은 같은 순위끼리 한 줄로 묶어 높이를 맞춤
export default function SummaryBoard({ summary, labels, onDetail, ov }) {
  const [open, setOpen] = useState(null); // { side, category }
  const stacked = useMediaQuery("(max-width: 640px)");
  const lists = SIDES.map((s) => topItems(summary, s.key));
  const rows = Math.max(...lists.map((l) => l.length), 1);

  const cell = (sideIdx, i, last) => {
    const side = SIDES[sideIdx];
    const row = lists[sideIdx][i];
    const isOpen = !!row && open?.side === side.key && open?.category === row.category;
    const toggle = () => setOpen(isOpen ? null : { side: side.key, category: row.category });
    return (
      <Cell
        key={`${side.key}-${i}`}
        row={row}
        rank={i + 1}
        side={side}
        open={isOpen}
        onToggle={toggle}
        onDetail={onDetail}
        ov={ov}
        labels={labels}
        last={last}
      />
    );
  };

  if (stacked) {
    return (
      <div className="sb stacked">
        {SIDES.map((side, s) => (
          <section key={side.key}>
            <h2 className={`sb-title ${side.cls}`}>{side.title}</h2>
            {lists[s].length === 0 ? (
              <p className="sb-none">해당 의견 없음</p>
            ) : (
              lists[s].map((_, i) => cell(s, i, i === lists[s].length - 1))
            )}
          </section>
        ))}
      </div>
    );
  }

  return (
    <div className="sb">
      {SIDES.map((side) => (
        <h2 key={side.key} className={`sb-title ${side.cls}`}>{side.title}</h2>
      ))}
      {Array.from({ length: rows }, (_, i) => (
        <Fragment key={i}>
          {cell(0, i, i === rows - 1)}
          {cell(1, i, i === rows - 1)}
        </Fragment>
      ))}
    </div>
  );
}
