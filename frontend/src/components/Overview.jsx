import { buildOverview } from "../utils/summary.js";

function List({ block, cls }) {
  return (
    <div className={cls}>
      <h3>{block.title}</h3>
      {block.items.length === 0 ? (
        <p className="ov-none">해당 의견 없음</p>
      ) : (
        <ul>
          {block.items.map((it, i) => (
            <li key={i}>
              {it.name && <strong>{it.name} </strong>}
              <span className={it.name ? "ov-sub" : undefined}>{it.text}</span>
              {it.extra && <span className="ov-extra">{it.extra}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// 종합 의견: 총평 + (교수자) 유지할 점·개선할 점 / (학습자) 추천·고려 필요
export default function Overview({ result, mode, labels }) {
  const o = buildOverview(result, mode, labels);
  return (
    <section className="ov">
      <h2>종합 의견</h2>
      <p>
        {o.lead} {o.tail}
      </p>
      <div className="ov-cols">
        <List block={o.left} cls="pos" />
        <List block={o.right} cls="neg" />
      </div>
    </section>
  );
}
