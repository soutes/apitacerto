import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LeagueDetail } from "../stats/details";
import COPY from "../../statsCopy";
import { fmt, fmtPct } from "../stats/format";
import { weightedMean } from "./derive";
import { PLAIN } from "./copy";
import { AnalysisCard, Legend, StatTile } from "./ui";

const HOME = "#006e9a";
const AWAY = "#c43f3e";
const NO_CROWD = 2020;

function SeasonTick({ x, y, payload }) {
  const s = payload.value;
  return (
    <g transform={`translate(${x},${y})`}>
      <text dy={12} textAnchor="middle" className="an-tick">
        {s}
      </text>
      {s === NO_CROWD && (
        <text dy={25} textAnchor="middle" className="an-tick an-tick-note">
          sem público
        </text>
      )}
    </g>
  );
}

function SeasonTooltip({ active, payload }) {
  const row = active && payload?.[0]?.payload;
  if (!row) return null;
  const diff = row.awayCards - row.homeCards;
  return (
    <div className="chart-tooltip">
      <b>
        Temporada {row.season}
        {row.season === NO_CROWD ? " — sem público" : ""}
      </b>
      <span>
        <i className="an-key key-home" /> Time da casa: <b>{fmt(row.homeCards, 2)}</b> cartões/jogo
      </span>
      <span>
        <i className="an-key key-away" /> Visitante: <b>{fmt(row.awayCards, 2)}</b> cartões/jogo
      </span>
      <span>
        {Math.abs(diff) < 0.05 ? "Praticamente igual" : `Visitante leva ${fmt(Math.abs(diff), 2)} ${diff > 0 ? "a mais" : "a menos"}`}
      </span>
      <span>
        Casa vence {fmtPct(row.homeWinPct, 0)} · empate {fmtPct(row.drawPct, 0)} · visitante vence {fmtPct(row.awayWinPct, 0)}
      </span>
    </div>
  );
}

// Linha de base da liga: quanto o time da casa ja leva menos cartao antes de
// olhar para qualquer arbitro. 2020 (sem publico) e o experimento natural.
export default function HomeAdvantage({ league, selected, tag }) {
  const rows = league.seasons;
  const others = rows.filter((r) => r.season !== NO_CROWD);
  const noCrowd = rows.find((r) => r.season === NO_CROWD);
  const gap = -weightedMean(rows, "cardsDiff");
  const gapOthers = Math.abs(weightedMean(others, "cardsDiff") ?? 0);
  const homeWin = weightedMean(rows, "homeWinPct");
  const awayWin = weightedMean(rows, "awayWinPct");
  const dim = (s) => (selected && s !== selected ? 0.35 : 1);

  return (
    <AnalysisCard
      className="span-6"
      title={PLAIN.home.title}
      subtitle={PLAIN.home.subtitle}
      tag={tag}
      how={{ copy: COPY.league, render: () => <LeagueDetail league={league} selected={selected} /> }}
    >
      <Legend
        items={[
          ["home", "Time da casa"],
          ["away", "Visitante"],
        ]}
      />
      <div className="an-chart" role="img" aria-label="Cartões por jogo do time da casa e do visitante, por temporada. O visitante leva mais cartão em quase todas; em 2020, sem público, a diferença some.">
        <ResponsiveContainer width="100%" height={230}>
          <BarChart data={rows} margin={{ top: 6, right: 4, bottom: 16, left: -18 }} barGap={2} barCategoryGap="22%">
            <CartesianGrid stroke="oklch(93% 0.005 80)" vertical={false} />
            <XAxis dataKey="season" tick={<SeasonTick />} tickLine={false} axisLine={{ stroke: "oklch(85% 0.006 80)" }} interval={0} />
            <YAxis tick={{ fontSize: 11, fill: "oklch(50% 0.01 260)" }} tickLine={false} axisLine={false} allowDecimals={false} tickFormatter={(v) => fmt(v, 0)} width={40} />
            <Tooltip content={<SeasonTooltip />} cursor={{ fill: "oklch(95% 0.006 80)" }} />
            <Bar dataKey="homeCards" name="Time da casa" fill={HOME} radius={[4, 4, 0, 0]} maxBarSize={14} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.season} fillOpacity={dim(r.season)} />
              ))}
            </Bar>
            <Bar dataKey="awayCards" name="Visitante" fill={AWAY} radius={[4, 4, 0, 0]} maxBarSize={14} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.season} fillOpacity={dim(r.season)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="an-tiles-3">
        <StatTile label="Visitante leva a mais" value={`+${fmt(gap, 2)}`} sub="cartão por jogo, na média" />
        <StatTile label="Time da casa vence" value={fmtPct(homeWin, 0)} sub={`dos jogos; o visitante, ${fmtPct(awayWin, 0)}`} />
        {noCrowd && (
          <StatTile
            label="Em 2020, sem torcida"
            value={fmt(Math.abs(noCrowd.cardsDiff), 2)}
            sub={
              Math.abs(noCrowd.cardsDiff) < gapOthers / 3
                ? `de diferença: quase sumiu (nos outros anos, ${fmt(gapOthers, 2)})`
                : `de diferença (nos outros anos, ${fmt(gapOthers, 2)})`
            }
          />
        )}
      </div>
    </AnalysisCard>
  );
}
