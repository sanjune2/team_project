import { useState } from "react";
import "../styles/result.css";
import Overview from "./Overview.jsx";
import ReviewCard from "./ReviewCard.jsx";
import SummaryBoard from "./SummaryBoard.jsx";

// 결과 화면: /api/analyze 응답 형식의 JSON만 받으면 그려짐 (reviews[*].text에 원문)
// mode: "instructor" 교수자 / "learner" 학습자 (종합 의견 문구만 다름)
export default function ResultView({ result, labels, mode = "instructor", title, meta = [] }) {
  const [evidence, setEvidence] = useState(null); // 근거 문장을 볼 항목 코드
  const failed = result.meta.failed;
  const evidenceReviews = evidence
    ? result.reviews.filter((r) => r.items.some((i) => i.category === evidence))
    : [];

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

      <SummaryBoard summary={result.summary_by_category} labels={labels} onEvidence={setEvidence} />
      <Overview result={result} mode={mode} labels={labels} />

      {evidence && (
        <section className="rv-evidence">
          <div className="rv-evidence-head">
            <h2>{labels[evidence] ?? evidence} 근거 문장</h2>
            <button type="button" className="sb-more" onClick={() => setEvidence(null)}>
              닫기
            </button>
          </div>
          {evidenceReviews.map((review) => (
            <ReviewCard key={review.review_id} review={review} text={review.text ?? ""} labels={labels} />
          ))}
        </section>
      )}
    </article>
  );
}
