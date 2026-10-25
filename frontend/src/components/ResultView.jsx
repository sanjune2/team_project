import { useState } from "react";
import "../styles/result.css";
import "../styles/detail.css";
import BalanceChart from "./BalanceChart.jsx";
import DetailAnalysis from "./DetailAnalysis.jsx";
import Overview from "./Overview.jsx";
import SummaryBoard from "./SummaryBoard.jsx";
import { readOverview } from "../utils/overview.js";

// 머리 오른쪽: 전체 언급의 만족·중립·불만족 구성 (막대 + 숫자)
function Composition({ result }) {
  const rows = result.summary_by_category ?? [];
  const sum = (k) => rows.reduce((n, r) => n + (r.counts?.[k] ?? 0), 0);
  const parts = [
    { key: "positive", cls: "p", label: "만족", n: sum("positive") },
    { key: "neutral", cls: "u", label: "중립", n: sum("neutral") },
    { key: "negative", cls: "n", label: "불만족", n: sum("negative") },
  ];
  const total = parts.reduce((n, x) => n + x.n, 0);
  if (!total) return null;
  const pct = (n) => Math.round((n / total) * 100);
  return (
    <div className="rv-comp">
      <p className="rv-comp-title num">
        항목 언급 <strong>{total}건</strong>의 평가
      </p>
      <div className="rv-comp-bar" aria-hidden="true">
        {parts.map((x) => (
          <span key={x.key} className={x.cls} style={{ width: `${(x.n / total) * 100}%` }} />
        ))}
      </div>
      <dl className="rv-comp-legend num">
        {parts.map((x) => (
          <div key={x.key} className={x.cls}>
            <dt>{x.label}</dt>
            <dd>{pct(x.n)}%</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

const TABS = [
  { key: "summary", label: "요약" },
  { key: "detail", label: "상세 분석" },
];

// 결과 화면: /api/analyze 응답 형식의 JSON만 받으면 그려짐 (reviews[*].text에 원문)
// mode: "instructor" 교수자 / "learner" 학습자 (종합 의견 문구만 다름)
// 탭: 요약 (TOP 3 + 종합 의견, 근거 문장 없음) │ 상세 분석 (모든 항목 + 근거 문장 펼치기)
// onBack: 있으면 맨 아래 탐색 줄에 "목록으로" 표시 (포털)
export default function ResultView({ result, labels, mode = "instructor", title, meta = [], onBack }) {
  const [tab, setTab] = useState("summary");
  const [filter, setFilter] = useState([]); // 상세 분석에서 고른 항목 ([] = 전체)
  const failed = result.meta.failed;
  const ov = readOverview(result);

  // 요약의 "상세 분석 보기" → 상세 분석 탭에서 그 항목만
  const openDetail = (category) => {
    setFilter([category]);
    setTab("detail");
    window.scrollTo(0, 0);
  };

  const toTop = () => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <article className="result">
      <header className="rv-head rv-hero">
        <div className="rv-hero-main">
          {title && <h1>{title}</h1>}
          <ul className="rv-chips num">
            {meta.map((m) => (
              <li key={m}>{m}</li>
            ))}
            <li>리뷰 {result.meta.succeeded}개</li>
            {failed > 0 && <li>분석 실패 {failed}개</li>}
          </ul>
        </div>
        <Composition result={result} />
      </header>
      <div className="rv-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            className="rv-tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "summary" ? (
        <>
          <section className="rv-sec">
            <header className="sec-head">
              <h2>많이 나온 의견</h2>
              <p className="sec-desc">항목을 누르면 대표 의견을 펼쳐 볼 수 있어요.</p>
            </header>
            <div className="sec-body">
              <SummaryBoard summary={result.summary_by_category} labels={labels} onDetail={openDetail} ov={ov} />
            </div>
          </section>
          <Overview result={result} mode={mode} labels={labels} />
          <section className="rv-sec">
            <header className="sec-head">
              <h2>항목별 평가</h2>
              <p className="sec-desc">항목을 누르면 상세 분석으로 이동해요.</p>
            </header>
            <div className="sec-body">
              <BalanceChart summary={result.summary_by_category} labels={labels} onSelect={openDetail} />
            </div>
          </section>
        </>
      ) : (
        <DetailAnalysis
          result={result}
          labels={labels}
          filter={filter}
          onFilter={setFilter}
          showSemester={mode === "learner"}
        />
      )}
      {/* 맨 아래 오른쪽: 목록으로, 맨 위로. 글자를 줄이지 않고 그대로 표시 */}
      <nav className="rv-foot" aria-label="결과 화면 이동">
        {onBack && (
          <button type="button" className="btn btn-secondary" onClick={onBack}>
            <span className="chev chev-left" aria-hidden="true" />
            목록으로
          </button>
        )}
        <button type="button" className="btn btn-secondary" aria-label="맨 위로" onClick={toTop}>
          <span className="chev chev-up" aria-hidden="true" />
          TOP
        </button>
      </nav>
    </article>
  );
}
