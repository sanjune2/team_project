import { useEffect, useState } from "react";
import ResultView from "../components/ResultView.jsx";
import PortalHeader from "../components/portal/PortalHeader.jsx";
import InstructorHome from "../components/portal/InstructorHome.jsx";
import LearnerHome from "../components/portal/LearnerHome.jsx";
import "../styles/portal.css";

// 가나대학교 포털 (고객사 연동을 보여 주는 레퍼런스 예시, 서버 호출 없음)
// index.json으로 과목과 결과 파일을 찾고, 고른 과목의 결과 파일을 읽어 결과 화면을 그림
// 실제 레퍼런스 데이터(reference/)가 있으면 그것을, 없으면 샘플(reference_sample/)을 씀
const BASE = import.meta.env.BASE_URL;
const DIRS = ["reference", "reference_sample"];
// 주소에 ?ov=sample 을 붙이면 overview_sample/의 예시 overview를 덮어씌워 화면 확인 (개발용)
const OV_SAMPLE = new URLSearchParams(window.location.search).get("ov") === "sample";

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

// mode: "instructor" 교직원 로그인 / "learner" 학생 로그인
export default function ReferencePage({ labels, mode, onModeChange }) {
  const [data, setData] = useState(null); // { dir, index }
  const [indexError, setIndexError] = useState(false);
  const [selected, setSelected] = useState(null); // { file, title, meta }
  const [result, setResult] = useState(null);
  const [resultError, setResultError] = useState(false);
  // 목록으로 돌아왔을 때 고른 학기와 검색어를 유지
  const [semester, setSemester] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    loadIndex()
      .then(setData)
      .catch(() => setIndexError(true));
  }, []);

  // 로그인을 바꾸면 목록으로
  useEffect(() => {
    setSelected(null);
  }, [mode]);

  useEffect(() => {
    if (!selected || !data) return;
    let active = true;
    setResult(null);
    setResultError(false);
    loadJson(`${BASE}${data.dir}/${selected.file}`)
      .then((r) => {
        if (!Array.isArray(r?.summary_by_category) || !Array.isArray(r?.reviews) || !r?.meta) throw new Error("shape");
        if (!OV_SAMPLE) return r;
        return loadJson(`${BASE}overview_sample/${selected.file}`)
          .then((s) => ({ ...r, overview: s.overview }))
          .catch(() => r);
      })
      .then((r) => {
        if (active) setResult(r);
      })
      .catch(() => active && setResultError(true));
    return () => {
      active = false;
    };
  }, [selected, data]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [selected]);

  const school = data?.index.school?.replace(/\s*\(.*\)\s*$/, "") ?? "";

  let body;
  if (indexError) {
    body = (
      <p className="error" role="alert">
        과목 목록을 불러오지 못했어요.
      </p>
    );
  } else if (!data) {
    body = <p className="hint">불러오는 중</p>;
  } else if (selected) {
    body = (
      <>
        {resultError && (
          <p className="error" role="alert">
            분석 결과를 불러오지 못했어요.
          </p>
        )}
        {!result && !resultError && <p className="hint">불러오는 중</p>}
        {result && (
          <ResultView
            result={result}
            labels={labels}
            mode={mode}
            title={selected.title}
            meta={selected.meta}
            onBack={() => setSelected(null)}
          />
        )}
        {/* 결과가 없을 때(불러오는 중, 오류)만 따로 표시. 결과가 있으면 결과 화면 맨 아래 탐색 줄에 있음 */}
        {!result && (
        <div className="pt-foot">
          <button type="button" className="pt-back" onClick={() => setSelected(null)}>
            목록으로
          </button>
        </div>
        )}
      </>
    );
  } else if (mode === "learner") {
    body = <LearnerHome courses={data.index.courses ?? []} query={query} onQuery={setQuery} onSelect={setSelected} />;
  } else {
    body = (
      <InstructorHome
        professor={data.index.professors?.[0]}
        semester={semester}
        onSemester={setSemester}
        onSelect={setSelected}
      />
    );
  }

  return (
    <>
      <PortalHeader school={school} mode={mode} onModeChange={onModeChange} />
      <main className="pt-main">{body}</main>
    </>
  );
}
