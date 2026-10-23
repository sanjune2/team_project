// 항목별 주요 의견: 백엔드 summary_by_category의 top_pros / top_cons를 표시
// 백엔드 10번 병합 전에는 값이 비어 있어서 아무것도 표시하지 않음
export default function TopOpinions({ summary, labels, selected, onSelect }) {
  const rows = (summary ?? [])
    .filter(({ category }) => !selected || category === selected)
    .filter(({ top_pros, top_cons }) => (top_pros?.length ?? 0) + (top_cons?.length ?? 0) > 0)
    .map((row) => ({
      ...row,
      total: row.counts.positive + row.counts.negative + row.counts.neutral,
    }))
    .sort((a, b) => b.total - a.total); // 차트와 같은 순서 (언급 많은 항목 먼저)

  if (rows.length === 0) return null;

  return (
    <section className="opinions">
      <h2>항목별 주요 의견</h2>
      {rows.map(({ category, top_pros = [], top_cons = [] }) => (
        <div key={category} className="opinion-row">
          <button className="link opinion-title" onClick={() => onSelect?.(category)}>
            {labels[category] ?? category}
          </button>
          <ul>
            {top_pros.slice(0, 3).map((text) => (
              <li key={`p-${text}`} className="pro">👍 {text}</li>
            ))}
            {top_cons.slice(0, 3).map((text) => (
              <li key={`c-${text}`} className="con">👎 {text}</li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}