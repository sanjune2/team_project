import { useEffect, useState } from "react";
import ResultView from "../components/ResultView.jsx";

// 고객사가 보관 중인 결과 파일을 불러와 그리는 화면 (서버 호출 없음)
// BASE_URL을 붙여 두면 하위 경로·iframe으로 띄워도 경로가 깨지지 않음
const RESULT_FILE = `${import.meta.env.BASE_URL}reference_sample/c00_2026-1.json`;

export default function ReferencePage({ labels }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true; // 화면이 사라진 뒤 도착한 응답은 무시
    fetch(RESULT_FILE)
      .then((res) => {
        if (!res.ok) throw new Error();
        return res.json();
      })
      .then((data) => active && setResult(data))
      .catch(() => active && setError("분석 결과를 불러오지 못했어요."));
    return () => {
      active = false;
    };
  }, []);

  return (
    <main>
      <h1>강의평 분석</h1>
      {!result && !error && <p className="hint">불러오는 중</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {result && <ResultView result={result} labels={labels} />}
    </main>
  );
}
