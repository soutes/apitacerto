import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmt } from "../stats/format";
import { AnalysisCard, Legend, StatTile } from "../analyses/ui";
import { HOW } from "./copy";
import { roundRates } from "./derive";

const LEADER = "#006e9a";
const LAST = "#c43f3e";

function RateTooltip({ active, payload, seasons }) {
  const row = active && payload?.[0]?.payload;
  if (!row) return null;
  const n = (v) => fmt((v / 100) * seasons, v % 1 ? 1 : 0);
  return (
    <div className="chart-tooltip">
      <b>Depois de {row.round} jogos</b>
      <span>
        <i className="an-key key-less" /> Líder virou campeão: <b>{fmt(row.leader, 0)}%</b> ({n(row.leader)} de {seasons})
      </span>
      <span>
        <i className="an-key key-more" /> Lanterna caiu: <b>{fmt(row.lanterna, 0)}%</b> ({n(row.lanterna)} de {seasons})
      </span>
      <span>Z-4 da rodada que caiu: {fmt(row.z4, 0)}%</span>
    </div>
  );
}

// Rodada a rodada: a partir de quando liderar (ou ser lanterna) decide.
export default function LeaderCurve({ closed, round }) {
  const rates = roundRates(closed);
  const at = rates[Math.min(round, rates.length) - 1];
  const seasons = closed.length;
  const firstSure = rates.find((r, i) => rates.slice(i).every((x) => x.lanterna === 100));
  const count = (v) => fmt((v / 100) * seasons, v % 1 ? 1 : 0);
  return (
    <AnalysisCard
      className="span-7"
      title="O líder vira campeão? O lanterna cai?"
      subtitle={`Em quantas das ${seasons} temporadas completas isso aconteceu, rodada a rodada.`}
      how={{ copy: HOW.leader }}
    >
      <Legend
        items={[
          ["less", "Líder virou campeão"],
          ["more", "Lanterna foi rebaixado"],
        ]}
      />
      <div className="an-chart" role="img" aria-label={`Depois de ${round} jogos, o líder virou campeão em ${count(at.leader)} de ${seasons} temporadas e o lanterna caiu em ${count(at.lanterna)}.`}>
        <ResponsiveContainer width="100%" height={230}>
          <LineChart data={rates} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="oklch(93% 0.005 80)" vertical={false} />
            <XAxis dataKey="round" tick={{ fontSize: 11, fill: "oklch(45% 0.01 260)" }} tickLine={false} axisLine={{ stroke: "oklch(85% 0.006 80)" }} ticks={[1, 5, 10, 15, 19, 25, 30, 38]} />
            <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: "oklch(50% 0.01 260)" }} tickLine={false} axisLine={false} width={44} />
            <ReferenceLine x={round} stroke="oklch(45% 0.01 260)" strokeDasharray="4 4" label={{ value: `${round} jogos`, position: "insideTopRight", fontSize: 11, fill: "oklch(40% 0.01 260)" }} />
            <Tooltip content={<RateTooltip seasons={seasons} />} />
            <Line type="stepAfter" dataKey="leader" stroke={LEADER} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="stepAfter" dataKey="lanterna" stroke={LAST} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="an-tiles-3">
        <StatTile label={`Líder após ${round} jogos`} value={`${count(at.leader)} de ${seasons}`} sub="virou campeão" />
        <StatTile label={`Lanterna após ${round} jogos`} value={`${count(at.lanterna)} de ${seasons}`} sub="foi rebaixado" tone={at.lanterna === 100 ? "alert" : undefined} />
        <StatTile label={`Z-4 após ${round} jogos`} value={`${fmt(at.z4, 0)}%`} sub="dos clubes que estavam lá caíram" />
      </div>
      {firstSure && (
        <p className="an-note">
          Desde o jogo {firstSure.round}, o lanterna caiu em todas as {seasons} temporadas.
        </p>
      )}
    </AnalysisCard>
  );
}
