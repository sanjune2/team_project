import { Bar, BarChart, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SENTIMENT_LABEL } from "../constants.js";

// App.css의 --pos / --neg 색과 맞춤 (SVG fill에는 CSS 변수가 안 먹어서 직접 지정)
const COLORS = { positive: "#1a7f4b", negative: "#c2410c", neutral: "#9ca3af" };
const KEYS = ["positive", "negative", "neutral"];

// 비율은 백엔드가 계산한 ratios(0~100)를 그대로 사용. 혹시 없으면 건수로 계산
function percent(row, key) {
  const fromBackend = row.ratios?.[key];
  if (typeof fromBackend === "number") return Math.round(fromBackend);
  return row.total > 0 ? Math.round((row[key] / row.total) * 100) : 0;
}

// 툴팁: 0건인 감성은 빼고 보여 줌
function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="chart-tip">
      <strong>
        {row.label} · 언급 리뷰 {row.mentioned}개
      </strong>
      {KEYS.filter((k) => row[k] > 0).map((k) => (
        <div key={k} style={{ color: COLORS[k] }}>
          {SENTIMENT_LABEL[k]} {row[k]}건 ({percent(row, k)}%)
        </div>
      ))}
      <span className="note">클릭하면 이 항목 리뷰만 보기</span>
    </div>
  );
}

export default function CategoryChart({ summary, labels, succeeded, selected, onSelect }) {
  const data = (summary ?? [])
    .map(({ category, counts, mentioned, ratios }) => {
      const total = counts.positive + counts.negative + counts.neutral;
      const label = labels[category] ?? category;
      return {
        category,
        label,
        mentioned: mentioned ?? total, // 백엔드 9번 이전 응답 대비
        ratios,
        total,
        name: `${label} · 리뷰 ${mentioned ?? total}개`,
        ...counts,
      };
    })
    .filter((d) => d.total > 0)
    .sort((a, b) => b.mentioned - a.mentioned || b.total - a.total); // 언급 리뷰 많은 항목 먼저

  if (data.length === 0) {
    return <p className="note">분석된 결과가 없어 통계를 표시할 수 없어요.</p>;
  }

  return (
    <section className="chart">
      <h2>
        항목별 만족도 <span className="note">분석 성공 {succeeded}개 기준</span>
      </h2>
      <ResponsiveContainer width="100%" height={data.length * 44 + 70}>
        <BarChart data={data} layout="vertical" stackOffset="expand" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)}%`} />
          <YAxis type="category" dataKey="name" width={210} />
          <Tooltip content={<ChartTooltip />} />
          <Legend />
          {KEYS.map((k) => (
            <Bar
              key={k}
              dataKey={k}
              name={SENTIMENT_LABEL[k]}
              stackId="s"
              fill={COLORS[k]}
              isAnimationActive={false}
              cursor="pointer"
              onClick={(d) => onSelect?.(d.payload?.category ?? d.category)}
            >
              {/* 선택된 항목이 있으면 나머지 막대는 흐리게 */}
              {data.map((row) => (
                <Cell key={row.category} fillOpacity={selected && row.category !== selected ? 0.3 : 1} />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}