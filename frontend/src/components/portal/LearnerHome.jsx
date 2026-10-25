// 학생: 과목 검색 → "과목 + 담당 교수" 목록 (전체 학기 합산 파일)
const normalize = (s) => (s ?? "").replace(/\s+/g, "").toLowerCase();

export default function LearnerHome({ courses, query, onQuery, onSelect }) {
  const q = normalize(query);
  const list = q
    ? courses.filter((c) => normalize(c.course_name).includes(q) || normalize(c.professor_name).includes(q))
    : courses;

  return (
    <section>
      <div className="pt-title">
        <h1>과목 찾기</h1>
        <p className="pt-sub">과목명이나 교수명으로 강의평 분석을 찾아보세요.</p>
      </div>

      <input
        type="search"
        className="pt-search"
        placeholder="과목명 또는 교수명"
        aria-label="과목 검색"
        value={query}
        onChange={(e) => onQuery(e.target.value)}
      />

      {list.length === 0 ? (
        <p className="pt-empty">검색 결과가 없어요.</p>
      ) : (
        <ul className="pt-list">
          {list.map((c) => (
            <li key={c.file}>
              <button
                type="button"
                className="pt-row"
                onClick={() => onSelect({ file: c.file, title: c.course_name, meta: [`${c.professor_name} 교수`, "전체 학기"] })}
              >
                <span className="pt-row-name">{c.course_name}</span>
                <span className="pt-row-sub">{c.professor_name} 교수</span>
                <span className="pt-row-count num">리뷰 {c.review_count}개</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
