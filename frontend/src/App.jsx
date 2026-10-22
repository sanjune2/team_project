import { useEffect, useState } from "react";
import { analyzeReviews, fetchCategories } from "./api/client.js";
import ReviewCard from "./components/ReviewCard.jsx";

const SAMPLE = `설명은 좋은데 시험 문제가 수업에서 안 다룬 내용 같아요.
팀플 있음 #neutral
과제 너무 많음 #negative
#empty 학식 맛있음
#fail 테스트`;

// 한 줄 = 리뷰 하나
function toReviews(input, semester) {
  return input
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((text, i) => ({
      id: `r${String(i + 1).padStart(3, "0")}`,
      text,
      ...(semester.trim() && { semester: semester.trim() }),
    }));
}

export default function App() {
  const [input, setInput] = useState(SAMPLE);
  const [semester, setSemester] = useState("");
  const [labels, setLabels] = useState({});
  const [result, setResult] = useState(null);
  const [submitted, setSubmitted] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCategories()
      .then((list) => setLabels(Object.fromEntries(list.map((c) => [c.code, c.label]))))
      .catch(() => {}); // 실패해도 영문 코드로 표시
  }, []);

  async function handleAnalyze() {
    const reviews = toReviews(input, semester);
    if (reviews.length === 0) return;
    setLoading(true);
    setError("");
    try {
      setResult(await analyzeReviews(reviews));
      setSubmitted(reviews);
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const textById = Object.fromEntries(submitted.map((r) => [r.id, r.text]));

  return (
    <main>
      <h1>강의평 분석</h1>
      <label className="field">
        수강 학기 (선택)
        <input value={semester} onChange={(e) => setSemester(e.target.value)} placeholder="예: 25-2" />
      </label>
      <p className="hint">한 줄에 리뷰 하나씩 입력하세요. (최대 50개)</p>
      <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={7} />
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? "분석 중…" : "분석하기"}
      </button>
      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <p className="meta">
            {result.meta.total_reviews}개 중 {result.meta.succeeded}개 분석 완료
            {result.meta.failed > 0 && ` · ${result.meta.failed}개 실패`} · 모델 {result.meta.model}
          </p>
          {result.reviews.map((review) => (
            <ReviewCard
              key={review.review_id}
              review={review}
              text={textById[review.review_id] ?? ""}
              labels={labels}
            />
          ))}
        </>
      )}
    </main>
  );
}
