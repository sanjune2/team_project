// 교직원: 학기 선택 → 담당 과목 목록 (학기 파일)
export default function InstructorHome({ professor, semester: picked, onSemester, onSelect }) {
  const courses = professor?.courses ?? [];
  const semesters = [...new Set(courses.map((c) => c.semester))].sort().reverse();
  const semester = semesters.includes(picked) ? picked : semesters[0];
  const list = courses.filter((c) => c.semester === semester);

  return (
    <section>
      <div className="pt-title">
        <h1>담당 과목</h1>
        {professor && <p className="pt-sub">{professor.name} 교수</p>}
      </div>

      {semesters.length > 0 && (
        <div className="pt-tabs" role="group" aria-label="학기">
          {semesters.map((s) => (
            <button
              key={s}
              type="button"
              className="pt-tab num"
              aria-pressed={s === semester}
              onClick={() => onSemester(s)}
            >
              {s}학기
            </button>
          ))}
        </div>
      )}

      {list.length === 0 ? (
        <p className="pt-empty">이 학기에 분석된 과목이 없어요.</p>
      ) : (
        <ul className="pt-list">
          {list.map((c) => (
            <li key={c.file}>
              <button
                type="button"
                className="pt-row"
                onClick={() => onSelect({ file: c.file, title: c.course_name, meta: [`${c.semester}학기`, `${c.section_id}분반`] })}
              >
                <span className="pt-row-name">{c.course_name}</span>
                <span className="pt-row-sub num">{c.section_id}분반</span>
                <span className="pt-row-count num">리뷰 {c.review_count}개</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
