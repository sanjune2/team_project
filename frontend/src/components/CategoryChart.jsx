import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SENTIMENT_LABEL } from "../constants.js";

// App.css의 --pos / --neg 색과 맞춤 (SVG fill에는 CSS 변수가 먹지 않아 직접 지정)
const COLORS = { positive: "#1a7f4b", negative: "#c2410c", neutral: "#9ca3af" };
const KEYS = ["positive", "negative", "neutral"];

// 툴팁: 0건인 감성은 제외 후 표시
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="chart-tip">
      <strong>{label}</strong>
      {KEYS.filter((k) => row[k] > 0).map((k) => (
        <div key={k} style={{ color: COLORS[k] }}>
          {SENTIMENT_LABEL[k]} {row[k]}건 ({Math.round((row[k] / row.total) * 100)}%)
        </div>
      ))}
    </div>
  );
}

export default function CategoryChart({ summary, labels }) {
  const data = (summary ?? [])
    .map(({ category, counts }) => {
      const total = counts.positive + counts.negative + counts.neutral;
      return { name: `${labels[category] ?? category} · ${total}건`, total, ...counts };
    })
    .filter((d) => d.total > 0)
    .sort((a, b) => b.total - a.total); // 언급 많은 항목 먼저

  if (data.length === 0) {
    return <p className="note">분석된 결과가 없어 통계를 표시할 수 없어요.</p>;
  }

  return (
    <section className="chart">
      <h2>항목별 만족도</h2>
      <ResponsiveContainer width="100%" height={data.length * 44 + 70}>
        <BarChart data={data} layout="vertical" stackOffset="expand" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)}%`} />
          <YAxis type="category" dataKey="name" width={170} /> {/* ★ 140 → 170 */}
          <Tooltip content={<ChartTooltip />} /> {/* ★ 직접 만든 툴팁 사용 */}
          <Legend />
          {KEYS.map((k) => (
            <Bar
              key={k}
              dataKey={k}
              name={SENTIMENT_LABEL[k]}
              stackId="s"
              fill={COLORS[k]}
              isAnimationActive={false} // ★ 캡처할 때도 바로 보이게 (애니메이션 원하면 이 줄 삭제)
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}