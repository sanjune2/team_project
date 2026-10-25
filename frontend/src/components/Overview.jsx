import { ovList, ovSuggestion, readOverview } from "../utils/overview.js";
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
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// 종합 의견: 첫 문단(규칙 기반, 집계 숫자) + (교수자) 유지할 점·개선할 점·방향 제안 / (학습자) 추천·고려 필요
// 목록과 방향 제안은 overview(LLM 정리본)가 있으면 그것, 없으면 규칙 기반
export default function Overview({ result, mode, labels }) {
  const o = buildOverview(result, mode, labels);
  const ov = readOverview(result);
  const left = { ...o.left, items: ovList(ov, "left") ?? o.left.items };
  const right = { ...o.right, items: ovList(ov, "right") ?? o.right.items };
  const suggestion = mode === "instructor" ? ovSuggestion(ov) : null;
  return (
    <section className="rv-sec ov">
      <header className="sec-head">
        <h2>종합 의견</h2>
        <p className="sec-desc">{mode === "instructor" ? "유지할 점과 개선할 점, 다음 학기 방향" : "추천하는 점과 미리 알아 둘 점"}</p>
      </header>
      <div className="sec-body">
        <p className="ov-lead">
          {o.lead} {o.tail}
        </p>
        <div className="ov-cols">
          <List block={left} cls="pos" />
          <List block={right} cls="neg" />
        </div>
        {suggestion && (
          <div className="ov-suggest">
            <h3>방향 제안</h3>
            <p>{suggestion}</p>
          </div>
        )}
      </div>
    </section>
  );
}
