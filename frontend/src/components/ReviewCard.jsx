import HighlightedText from "./HighlightedText.jsx";
import { SENTIMENT_LABEL } from "../constants.js";

// 실패 사유 원문(서버·OpenAI 오류 문구)은 화면에 그대로 보여 주지 않음
function failMessage(error) {
  if (error?.includes("제한 시간")) return "응답이 늦어져 이 리뷰는 분석하지 못했어요. 다시 분석해 주세요.";
  return "이 리뷰는 분석하지 못했어요. 잠시 후 다시 분석해 주세요.";
}
export default function ReviewCard({ review, text, labels }) {
  if (review.status === "failed") {
    return (
      <article className="card failed">
        <header>
          <span className="id">{review.review_id}</span>
          <span className="badge failed">분석 실패</span>
        </header>
        <p className="original">{text}</p>
        <p className="note">{failMessage(review.error)}</p>
      </article>
    );
  }

  return (
    <article className="card">
      <header>
        <span className="id">{review.review_id}</span>
        {review.overall_sentiment ? (
          <span className={`badge ${review.overall_sentiment}`}>
            {SENTIMENT_LABEL[review.overall_sentiment]}
          </span>
        ) : (
          <span className="badge none">평가 내용 없음</span>
        )}
      </header>
      <HighlightedText text={text} items={review.items} />
      {review.items.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>항목</th>
              <th>감성</th>
              <th>요약</th>
              <th>근거</th>
            </tr>
          </thead>
          <tbody>
            {review.items.map((item, i) => (
              <tr key={i}>
                <td>{labels[item.category] ?? item.category}</td>
                <td>
                  <span className={`badge ${item.sentiment}`}>
                    {SENTIMENT_LABEL[item.sentiment]}
                  </span>
                </td>
                <td>
                  {item.summary}
                  {item.condition && <div className="note">조건: {item.condition}</div>}
                </td>
                <td>
                  “{item.evidence}”
                  {!item.evidence_verified && <div className="warn">원문 확인 필요</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  );
}

