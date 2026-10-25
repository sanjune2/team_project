import { useEffect, useState } from "react";
import useCategoryLabels from "./hooks/useCategoryLabels.js";
import AnalyzePage from "./pages/AnalyzePage.jsx";
import ReferencePage from "./pages/ReferencePage.jsx";

// 기본: 결과 파일을 읽어 그리는 레퍼런스 화면
// 주소 끝 #learner: 학습자 화면 (과목 전체 학기)
// 주소 끝 #analyze: 리뷰를 직접 넣어 보는 테스트 화면
function useHash() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const labels = useCategoryLabels();
  const hash = useHash();

  if (hash === "#analyze") return <AnalyzePage labels={labels} />;

  // 포털 상단 예시 로그인 전환 = 주소 끝 # 바꾸기 (교직원: 없음 / 학생: #learner)
  const mode = hash === "#learner" ? "learner" : "instructor";
  const changeMode = (next) => {
    if (next === mode) return;
    if (next === "learner") window.location.hash = "learner";
    else history.pushState(null, "", window.location.pathname + window.location.search);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  };
  return <ReferencePage labels={labels} mode={mode} onModeChange={changeMode} />;
}
