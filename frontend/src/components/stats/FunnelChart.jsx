import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import EvidenceChip from "./EvidenceChip";
import { fmt, fmtP, fmtSigned } from "./format";

// Grafico de funil (Spiegelhalter, 2005): cada ponto e um par; as linhas
// marcam ate onde o acaso chega (95% tracejado, 99,8% pontilhado).
const LEVELS = [
  ["acaso", "oklch(68% 0.03 250)", "Compatível com o acaso"],
  ["fraco", "oklch(70% 0.15 75)", "Sinal fraco"],
  ["forte", "oklch(56% 0.18 25)", "Sinal forte"],
];

function PairTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload.find((item) => item.payload?.team)?.payload;
  if (!p) return null;
  return (
    <div className="chart-tooltip">
      <b>
        {p.team} × {p.referee}
      </b>
      <div>
        {p.n} jogos · z {fmtSigned(p.z, 2)} · p {fmtP(p.p)}
      </div>
      {p.easeWithReferee != null ? (
        <div>
          xPts médio {fmt(p.easeWithReferee, 2)} vs {fmt(p.easeTeam, 2)} no sorteio
        </div>
      ) : (
        <div>
          Observado {fmt(p.observed, 1)} · esperado {fmt(p.expected, 1)}
        </div>
      )}
      <EvidenceChip level={p.level} />
    </div>
  );
}

export default function FunnelChart({ points, funnel, xKey, yKey, xLabel, yLabel, center = 0 }) {
  const data = points
    .filter((p) => p[xKey] != null && p[yKey] != null)
    .map((p) => ({ ...p, x: p[xKey], y: p[yKey] }));
  return (
    <div className="funnel-wrap">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart margin={{ top: 10, right: 16, bottom: 28, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="oklch(92% 0.006 80)" />
          <XAxis
            type="number"
            dataKey="x"
            domain={["auto", "auto"]}
            tickFormatter={(v) => fmt(v, 0)}
            label={{ value: xLabel, position: "insideBottom", offset: -16, fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={["auto", "auto"]}
            tickFormatter={(v) => fmt(v, 1)}
            label={{ value: yLabel, angle: -90, position: "insideLeft", fontSize: 12, dy: 60 }}
          />
          <ReferenceLine y={center} stroke="oklch(55% 0.01 260)" />
          {["lo95", "hi95"].map((key) => (
            <Line key={key} data={funnel} dataKey={key} dot={false} stroke="oklch(45% 0.01 260)"
              strokeDasharray="6 4" strokeWidth={1.2} isAnimationActive={false} legendType="none" />
          ))}
          {["lo998", "hi998"].map((key) => (
            <Line key={key} data={funnel} dataKey={key} dot={false} stroke="oklch(45% 0.01 260)"
              strokeDasharray="1 4" strokeWidth={1.4} isAnimationActive={false} legendType="none" />
          ))}
          {LEVELS.map(([level, color, name]) => (
            <Scatter key={level} name={name} data={data.filter((d) => d.level === level)} fill={color}
              fillOpacity={level === "acaso" ? 0.55 : 0.95} isAnimationActive={false} />
          ))}
          <Tooltip content={<PairTooltip />} cursor={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="funnel-legend">
        <span><i className="swatch dashed" /> limite de 95%</span>
        <span><i className="swatch dotted" /> limite de 99,8%</span>
        {LEVELS.map(([level, color, name]) => (
          <span key={level}><i className="swatch dot" style={{ background: color }} /> {name}</span>
        ))}
      </div>
    </div>
  );
}
