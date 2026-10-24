import { useState } from "react";
import { analyzeReviews } from "../api/client.js";
import ResultView from "../components/ResultView.jsx";

// 개발·테스트용 입력 화면 (주소 끝에 #analyze)
const SAMPLE = `설명은 좋은데 시험 문제가 수업에서 안 다룬 내용 같아요.
팀플 있음 #neutral
과제 너무 많음 #negative
#empty 학식 맛있음
#fail 테스트`;

const MAX_REVIEWS = 50; // 백엔드 AnalyzeRequest 제한과 같음
const MAX_LENGTH = 3000; // 백엔드 ReviewInput.text 제한과 같음

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

// API 응답에 원문(text)을 붙여 레퍼런스 결과 파일과 같은 형식으로 맞춤
function attachText(response, reviews) {
  const textById = Object.fromEntries(reviews.map((r) => [r.id, r.text]));
  return {
    ...response,
    reviews: response.reviews.map((r) => ({ ...r, text: textById[r.review_id] ?? "" })),
  };
}

export default function AnalyzePage({ labels }) {
  const [input, setInput] = useState(SAMPLE);
  const [semester, setSemester] = useState("");
  const [result, setResult] = useState(null);
  const [runId, setRunId] = useState(0); // 새로 분석하면 결과 화면 상태(필터) 초기화
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(0);

  async function handleAnalyze() {
    const reviews = toReviews(input, semester);
    if (reviews.length === 0) return;
    if (reviews.length > MAX_REVIEWS) {
      setError(`리뷰는 한 번에 ${MAX_REVIEWS}개까지 분석할 수 있어요. (현재 ${reviews.length}개)`);
      return;
    }
    // 서버로 보내기 전에 길이 확인 (서버 422의 일반 문구 대신 몇 번째인지 알려 줌)
    const tooLong = reviews.map((r, i) => (r.text.length > MAX_LENGTH ? i + 1 : null)).filter(Boolean);
    if (tooLong.length > 0) {
      const shown = tooLong.slice(0, 3).join(", ");
      const more = tooLong.length > 3 ? ` 외 ${tooLong.length - 3}개` : "";
      setError(`${shown}번째${more} 리뷰가 너무 길어요. 한 리뷰는 ${MAX_LENGTH.toLocaleString()}자까지 분석할 수 있어요.`);
      return;
    }
    setPending(reviews.length);
    setLoading(true);
    setError("");
    try {
      setResult(attachText(await analyzeReviews(reviews), reviews));
      setRunId((n) => n + 1);
    } catch (e) {
      setError(e.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const reviewCount = toReviews(input, semester).length;

  return (
    <main>
      <h1>강의평 분석 테스트</h1>
      <label className="field">
        수강 학기 (선택)
        <input value={semester} onChange={(e) => setSemester(e.target.value)} placeholder="예: 25-2" />
      </label>
      <p className="hint">한 줄에 리뷰 하나씩 입력하세요. (최대 {MAX_REVIEWS}개, 현재 {reviewCount}개)</p>
      <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={7} />
      <button onClick={handleAnalyze} disabled={loading || reviewCount === 0}>
        {loading ? `${pending}개 분석 중…` : "분석하기"}
      </button>
      {loading && <p className="hint">리뷰가 많으면 수십 초 걸릴 수 있어요.</p>}
      {!loading && reviewCount === 0 && <p className="hint">분석할 리뷰를 한 줄 이상 입력해 주세요.</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {result && <ResultView key={runId} result={result} labels={labels} />}
    </main>
  );
}
