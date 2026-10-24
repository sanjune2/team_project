import { useEffect, useState } from "react";
import ResultView from "../components/ResultView.jsx";

// 고객사가 보관 중인 결과 파일을 불러와 그리는 화면 (서버 호출 없음)
// 실제 레퍼런스 데이터(reference/)가 있으면 그것을, 없으면 샘플(reference_sample/)을 씀
const BASE = import.meta.env.BASE_URL;
const DIRS = ["reference", "reference_sample"];

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok || !res.headers.get("content-type")?.includes("json")) throw new Error(path);
  return res.json();
}

async function loadIndex() {
  for (const dir of DIRS) {
    try {
      return { dir, index: await loadJson(`${BASE}${dir}/index.json`) };
    } catch {
      // 다음 폴더 시도
    }
  }
  throw new Error("index");
}

// mode: "instructor" → 교수 1명의 한 학기 과목 / "learner" → 과목의 전체 학기
export default function ReferencePage({ labels, mode }) {
  const [view, setView] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setView(null);
    (async () => {
      const { dir, index } = await loadIndex();
      let target, meta;
      if (mode === "learner") {
        target = index.courses[0];
        meta = [target.professor_name, "전체 학기"];
      } else {
        const prof = index.professors[0];
        target = prof.courses[0];
        meta = [`${target.semester}학기`];
      }
      const result = await loadJson(`${BASE}${dir}/${target.file}`);
      if (active) setView({ result, title: target.course_name, meta });
    })().catch(() => active && setError("분석 결과를 불러오지 못했어요."));
    return () => {
      active = false;
    };
  }, [mode]);

  return (
    <main>
      {!view && !error && <p className="hint">불러오는 중</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {view && <ResultView result={view.result} labels={labels} mode={mode} title={view.title} meta={view.meta} />}
    </main>
  );
}
