import { useState } from "react";
import "../styles/result.css";
import "../styles/detail.css";
import DetailAnalysis from "./DetailAnalysis.jsx";
import Overview from "./Overview.jsx";
import SummaryBoard from "./SummaryBoard.jsx";
import { readOverview } from "../utils/overview.js";

const TABS = [
  { key: "summary", label: "요약" },
  { key: "detail", label: "상세 분석" },
];

// 결과 화면: /api/analyze 응답 형식의 JSON만 받으면 그려짐 (reviews[*].text에 원문)
// mode: "instructor" 교수자 / "learner" 학습자 (종합 의견 문구만 다름)
// 탭: 요약 (TOP 3 + 종합 의견, 근거 문장 없음) │ 상세 분석 (모든 항목 + 근거 문장 펼치기)
export default function ResultView({ result, labels, mode = "instructor", title, meta = [] }) {
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

  return (
    <article className="result">
      <header className="rv-head">
        {title && <h1>{title}</h1>}
        <p className="rv-meta num">
          {meta.map((m) => (
            <span key={m}>{m}</span>
          ))}
          <span>리뷰 {result.meta.succeeded}개</span>
          {failed > 0 && <span>분석 실패 {failed}개</span>}
        </p>
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
          <SummaryBoard summary={result.summary_by_category} labels={labels} onDetail={openDetail} ov={ov} />
          <Overview result={result} mode={mode} labels={labels} />
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
    </article>
  );
}
