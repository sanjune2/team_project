// 항목별 평가 한눈에: 가운데 축을 기준으로 왼쪽 불만족, 오른쪽 만족 비율 (중립은 숫자로만)
// 한 줄을 누르면 상세 분석에서 그 항목만 보기
export default function BalanceChart({ summary, labels, onSelect }) {
  const rows = (summary ?? []).filter((s) => s.mentioned > 0).sort((a, b) => b.mentioned - a.mentioned);
  if (rows.length === 0) return null;
  const pct = (v) => Math.round(v ?? 0);

  return (
    <section className="bc" aria-label="항목별 만족과 불만족 비율">
      <div className="bc-legend" aria-hidden="true">
        <span className="neg">불만족</span>
        <span className="pos">만족</span>
      </div>
      <ul className="bc-list">
        {rows.map((r) => {
          const name = labels[r.category] ?? r.category;
          const p = pct(r.ratios?.positive);
          const n = pct(r.ratios?.negative);
          return (
            <li key={r.category}>
              <button
                type="button"
                className="bc-row"
                onClick={() => onSelect(r.category)}
                aria-label={`${name}: 만족 ${p}%, 불만족 ${n}%, 언급 리뷰 ${r.mentioned}개. 상세 분석 보기`}
              >
                <span className="bc-name">{name}</span>
                <span className="bc-side neg">
                  <span className="bc-val num">{n > 0 ? `${n}%` : ""}</span>
                  <span className="bc-bar" style={{ width: `${n}%` }} />
                </span>
                <span className="bc-side pos">
                  <span className="bc-bar" style={{ width: `${p}%` }} />
                  <span className="bc-val num">{p > 0 ? `${p}%` : ""}</span>
                </span>
                <span className="bc-count num">{r.mentioned}개</span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
