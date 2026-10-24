import { useState } from "react";
import CategoryChart from "./CategoryChart.jsx";
import ReviewCard from "./ReviewCard.jsx";
import TopOpinions from "./TopOpinions.jsx";

// 결과 화면: /api/analyze 응답 형식의 JSON만 받으면 그려짐
// result.reviews[*].text 에 원문이 들어 있어야 함 (레퍼런스 결과 파일 형식)
export default function ResultView({ result, labels }) {
  const [selected, setSelected] = useState(null); // 차트에서 고른 항목 코드

  const visibleReviews = result.reviews.filter(
    (r) => !selected || r.items.some((i) => i.category === selected),
  );
  const toggleCategory = (code) => setSelected((cur) => (cur === code ? null : code));

  return (
    <section className="result">
      <p className="meta">
        리뷰 {result.meta.succeeded}개
        {result.meta.failed > 0 && ` (분석 실패 ${result.meta.failed}개)`}
      </p>
      <CategoryChart
        summary={result.summary_by_category}
        labels={labels}
        succeeded={result.meta.succeeded}
        selected={selected}
        onSelect={toggleCategory}
      />
      <TopOpinions
        summary={result.summary_by_category}
        labels={labels}
        selected={selected}
        onSelect={toggleCategory}
      />
      {selected && (
        <p className="filter">
          <strong>{labels[selected] ?? selected}</strong> 언급 리뷰 {visibleReviews.length}개만 보는 중
          <button className="link" onClick={() => setSelected(null)}>전체 보기</button>
        </p>
      )}
      {visibleReviews.map((review) => (
        <ReviewCard key={review.review_id} review={review} text={review.text ?? ""} labels={labels} />
      ))}
    </section>
  );
}
