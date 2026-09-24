import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LEVELS } from "../analyses/copy";
import { displayClubName, displayRefereeName } from "../../nameFormat";
import EvidenceChip from "./EvidenceChip";
import FunnelChart from "./FunnelChart";
import PairTable from "./PairTable";
import { fmt, fmtP, fmtPct, fmtSigned } from "./format";

// Parte tecnica de cada grafico da aba Analises: os numeros completos (z, p,
// intervalos, funil, tabelas). Aparece so no painel "Como foi criado" -- a
// visao principal fica com os graficos amigaveis (components/analyses).

const BLUE = "#006e9a";
const CORAL = "#c43f3e";
const AMBER = "#d48e00";
const GREY = "#c9c6c0";
const GRID = "oklch(92% 0.006 80)";

function Kpi({ value, label }) {
  return (
    <div className="stat-kpi">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function Summary({ summary }) {
  if (!summary?.tested) return null;
  return (
    <p className="stat-note">
      {summary.tested} pares testados · fora do limite de 95%: <b>{summary.above95}</b> (o acaso daria ~
      {fmt(summary.expectedAbove95, 0)}) · sinal fraco: <b>{summary.weak}</b> (acaso ~{fmt(summary.expectedWeakByChance, 0)}) ·
      sinal forte: <b>{summary.strong}</b>
    </p>
  );
}

const who = [
  { label: "Clube", render: (p) => displayClubName(p.team), title: (p) => p.team },
  { label: "Árbitro", render: (p) => displayRefereeName(p.referee), title: (p) => p.referee },
  { label: "Jogos", num: true, render: (p) => p.n },
];
const evidence = [
  { label: "z", num: true, render: (p) => fmtSigned(p.z, 1) },
  { label: "p", num: true, render: (p) => fmtP(p.p) },
  { label: "Evidência", render: (p) => <EvidenceChip level={p.level} /> },
];
const COUNT_COLUMNS = [
  ...who,
  { label: "Observado", num: true, render: (p) => fmt(p.observed, 0) },
  { label: "Esperado", num: true, render: (p) => fmt(p.expected, 1) },
  { label: "Obs ÷ esp", num: true, render: (p) => fmt(p.ratio, 2) },
  ...evidence,
];
const POINT_COLUMNS = [
  ...who,
  { label: "Pontos", num: true, render: (p) => fmt(p.observed, 0) },
  { label: "xPts", num: true, render: (p) => fmt(p.expected, 1) },
  { label: "Por jogo", num: true, render: (p) => fmtSigned(p.perGame, 2) },
  ...evidence,
];
const EASE_COLUMNS = [
  ...who,
  { label: "xPts c/ árbitro", num: true, render: (p) => fmt(p.easeWithReferee, 2) },
  { label: "xPts sorteio", num: true, render: (p) => fmt(p.easeTeam, 2) },
  { label: "Dif./jogo", num: true, render: (p) => fmtSigned(p.perGame, 2) },
  ...evidence,
  { label: "Mesma categoria", render: (p) => <EvidenceChip level={p.sameCategory?.level} /> },
];

// ------------------------------------------------------------ niveis + resumo
const ANALYSES = [
  ["cards", "Cartões ao clube"],
  ["rivalCards", "Cartões ao adversário"],
  ["points", "Pontos acima do esperado"],
  ["ease", "Jogos mais fáceis"],
];

export function IntroDetail({ report }) {
  const { overview, pairs } = report;
  return (
    <>
      <div className="legend-list">
        {LEVELS.map(([level, text]) => (
          <div key={level} className="legend-item">
            <EvidenceChip level={level} />
            <span>{text}</span>
          </div>
        ))}
      </div>
      <p className="stat-note">
        Os níveis são fixos: sinal forte = sobrevive à correção de Benjamini-Hochberg (q ≤ 0,10); para acompanhar =
        p &lt; 0,01 sem sobreviver à correção; fora da faixa normal = p &lt; 0,05.
      </p>
      <div className="stat-kpis">
        <Kpi value={overview.matches} label="jogos no recorte" />
        <Kpi value={overview.pairsTested} label={`pares árbitro × clube com ${overview.floor}+ jogos`} />
        <Kpi value={fmt(overview.medianPairGames, 0)} label="jogos por par (mediana)" />
      </div>
      <div className="table-wrap">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Análise par a par</th>
              <th className="num">Testados</th>
              <th className="num">Fora do normal (p &lt; 0,05)</th>
              <th className="num">Acaso daria (5%)</th>
              <th className="num">Sinal forte</th>
              <th className="num">Para acompanhar</th>
              <th className="num">Acaso daria (1%)</th>
            </tr>
          </thead>
          <tbody>
            {ANALYSES.map(([key, label]) => {
              const s = pairs[key].summary;
              return (
                <tr key={key}>
                  <td>{label}</td>
                  <td className="num">{s.tested}</td>
                  <td className="num">{s.above95}</td>
                  <td className="num">~{fmt(s.expectedAbove95, 1)}</td>
                  <td className="num">{s.strong}</td>
                  <td className="num">{s.weak}</td>
                  <td className="num">~{fmt(s.expectedWeakByChance, 1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ------------------------------------------------------------ L1
export function LeagueDetail({ league, selected }) {
  const rows = league.seasons.map((s) => ({
    ...s,
    cardsErr: s.cardsDiffCi[0] == null ? [0, 0] : [s.cardsDiff - s.cardsDiffCi[0], s.cardsDiffCi[1] - s.cardsDiff],
    pensErr: s.pensDiffCi[0] == null ? [0, 0] : [s.pensDiff - s.pensDiffCi[0], s.pensDiffCi[1] - s.pensDiff],
  }));
  const color = (s) => (s === selected ? CORAL : s === 2020 ? AMBER : BLUE);
  const diffChart = (key, err, title) => (
    <div>
      <h4 className="chart-title">{title}</h4>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="season" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => fmt(v, 1)} tick={{ fontSize: 11 }} />
          <ReferenceLine y={0} stroke="oklch(55% 0.01 260)" />
          <Tooltip formatter={(v) => fmtSigned(v, 2)} labelFormatter={(s) => `Temporada ${s}${s === 2020 ? " (sem público)" : ""}`} />
          <Bar dataKey={key} name="mandante − visitante" isAnimationActive={false} maxBarSize={24} radius={[4, 4, 0, 0]}>
            {rows.map((r) => (
              <Cell key={r.season} fill={color(r.season)} />
            ))}
            <ErrorBar dataKey={err} width={4} strokeWidth={1.4} stroke="oklch(30% 0.01 260)" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
  return (
    <>
      <div className="chart-pair">
        {diffChart("cardsDiff", "cardsErr", "Cartões por jogo: mandante − visitante (IC 95%)")}
        {diffChart("pensDiff", "pensErr", "Gols de pênalti por jogo: mandante − visitante (IC 95%)")}
      </div>
      <div>
        <h4 className="chart-title">Resultado do mandante (%)</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="season" tick={{ fontSize: 11 }} />
            <YAxis unit="%" tick={{ fontSize: 11 }} domain={[0, 100]} />
            <Tooltip formatter={(v) => fmtPct(v)} labelFormatter={(s) => `Temporada ${s}`} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="homeWinPct" stackId="r" name="Vitória" fill={BLUE} isAnimationActive={false} maxBarSize={24} />
            <Bar dataKey="drawPct" stackId="r" name="Empate" fill={GREY} isAnimationActive={false} maxBarSize={24} />
            <Bar dataKey="awayWinPct" stackId="r" name="Derrota" fill={CORAL} isAnimationActive={false} maxBarSize={24} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="stat-note">Em destaque: temporada selecionada (coral) e 2020, jogada sem público (âmbar).</p>
      <div className="table-wrap">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Temporada</th>
              <th className="num">Jogos</th>
              <th className="num">Cartões casa</th>
              <th className="num">Cartões fora</th>
              <th className="num">Dif. (IC 95%)</th>
              <th className="num">Pênalti dif.</th>
              <th className="num">V / E / D casa</th>
            </tr>
          </thead>
          <tbody>
            {league.seasons.map((s) => (
              <tr key={s.season}>
                <td>{s.season}</td>
                <td className="num">{s.matches}</td>
                <td className="num">{fmt(s.homeCards, 2)}</td>
                <td className="num">{fmt(s.awayCards, 2)}</td>
                <td className="num">
                  {fmtSigned(s.cardsDiff, 2)} [{fmt(s.cardsDiffCi[0], 2)}; {fmt(s.cardsDiffCi[1], 2)}]
                </td>
                <td className="num">{fmtSigned(s.pensDiff, 3)}</td>
                <td className="num">
                  {fmt(s.homeWinPct, 0)} / {fmt(s.drawPct, 0)} / {fmt(s.awayWinPct, 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ------------------------------------------------------------ L2
function ratioBar(value) {
  const lo = 0.5;
  const hi = 1.5;
  const clamp = (v) => Math.min(hi, Math.max(lo, v));
  const a = ((clamp(Math.min(value, 1)) - lo) / (hi - lo)) * 100;
  const b = ((clamp(Math.max(value, 1)) - lo) / (hi - lo)) * 100;
  return { left: `${a}%`, width: `${Math.max(b - a, 0.8)}%` };
}

export function RefereeDetail({ data }) {
  const [showAll, setShowAll] = useState(false);
  if (!data.referees.length) return <p className="hint">Nenhum árbitro com {data.floorGames}+ jogos neste recorte.</p>;
  const refs = showAll ? data.referees : data.referees.slice(0, 12);
  return (
    <>
      <div className="stat-kpis">
        <Kpi value={data.referees.length} label={`árbitros com ${data.floorGames}+ jogos`} />
        <Kpi value={fmt(data.typicalReliability * 100, 0) + "%"} label="confiabilidade de um árbitro típico (quanto do número é sinal)" />
      </div>
      <div className="ratio-list">
        <div className="ratio-row ratio-head">
          <span>Árbitro</span>
          <span>0,5 ← rigor (1 = esperado) → 1,5</span>
          <span className="num">Encolhido (bruto)</span>
          <span className="num">Jogos</span>
          <span>Evidência</span>
          <span>Mandante vs liga</span>
        </div>
        {refs.map((r) => (
          <div className="ratio-row" key={r.referee}>
            <span className="truncate" title={r.referee}>{displayRefereeName(r.referee)}</span>
            <div className="ratio-track" title={`IC 95% do bruto: ${fmt(r.ci[0], 2)} a ${fmt(r.ci[1], 2)}`}>
              <div className="ratio-center" />
              <div className={`ratio-bar${r.shrunk > 1 ? " over" : ""}`} style={ratioBar(r.shrunk)} />
            </div>
            <span className="num mono">
              {fmt(r.shrunk, 2)} <span className="muted">({fmt(r.ratio, 2)})</span>
            </span>
            <span className="num mono">{r.games}</span>
            <EvidenceChip level={r.level} />
            <span className="bias-cell">
              <span className="mono">{fmtSigned(r.homeBias.perGame, 2)}</span>
              <EvidenceChip level={r.homeBias.level} />
            </span>
          </div>
        ))}
      </div>
      {data.referees.length > 12 && (
        <button type="button" className="link-button" onClick={() => setShowAll((v) => !v)}>
          {showAll ? "Mostrar só os 12 mais rigorosos" : `Ver todos os ${data.referees.length} árbitros`}
        </button>
      )}
    </>
  );
}

// ------------------------------------------------------------ A1-A4
export function PairDetail({ kind, data, points }) {
  const isCount = kind === "cards" || kind === "rivalCards";
  const isEase = kind === "ease";
  return (
    <>
      <Summary summary={data.summary} />
      {points.length === 0 ? (
        <p className="hint">Nenhum par com {data.floor}+ jogos neste recorte.</p>
      ) : (
        <>
          <FunnelChart
            points={points}
            funnel={data.funnel}
            xKey={isCount ? "expected" : "n"}
            yKey={isCount ? "ratio" : "perGame"}
            center={isCount ? 1 : 0}
            xLabel={isCount ? "cartões esperados no par" : "jogos do par"}
            yLabel={isCount ? "observado ÷ esperado" : isEase ? "xPts/jogo vs sorteio" : "pontos/jogo vs esperado"}
          />
          <PairTable points={points} columns={isCount ? COUNT_COLUMNS : isEase ? EASE_COLUMNS : POINT_COLUMNS} />
        </>
      )}
    </>
  );
}

// ------------------------------------------------------------ A5
function RepeatTable({ pairs }) {
  if (!pairs.length) return null;
  return (
    <div className="table-wrap">
      <table className="stats-table">
        <thead>
          <tr>
            <th>Clube</th>
            <th>Árbitro</th>
            <th>Direção</th>
            <th>Temporadas (z)</th>
          </tr>
        </thead>
        <tbody>
          {pairs.map((p) => (
            <tr key={`${p.team}|${p.referee}|${p.direction}`}>
              <td title={p.team}>{displayClubName(p.team)}</td>
              <td title={p.referee}>{displayRefereeName(p.referee)}</td>
              <td>{p.direction === "+" ? "a favor / mais duro" : "contra"}</td>
              <td className="mono">{p.seasons.map((s) => `${s.season} (${fmtSigned(s.z, 1)}; ${s.n}j)`).join(" · ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CrossDetail({ data, filter = () => true }) {
  if (!data?.available) return <p className="hint">Sem pares com jogos em temporadas seguidas.</p>;
  const c = data.correlation;
  return (
    <>
      <div className="stat-kpis">
        <Kpi
          value={c ? fmt(c.r, 2) : "—"}
          label={c ? `correlação entre uma temporada e a seguinte (IC 95%: ${fmt(c.lo, 2)} a ${fmt(c.hi, 2)}; p ${fmtP(c.p)}; ${c.n} comparações)` : "sem comparações suficientes"}
        />
        <Kpi
          value={`${data.favorRepeats.observed} vs ${fmt(data.favorRepeats.expected, 1)}`}
          label={`pares com sinal a favor repetido em 2+ temporadas (observado vs. acaso; p ${fmtP(data.favorRepeats.p)})`}
        />
        <Kpi
          value={`${data.harshRepeats.observed} vs ${fmt(data.harshRepeats.expected, 1)}`}
          label={`árbitro mais duro com o mesmo clube em 2+ temporadas (observado vs. acaso; p ${fmtP(data.harshRepeats.p)})`}
        />
      </div>
      <h4 className="chart-title">Cada ponto: o índice de um par numa temporada (→) e na seguinte (↑)</h4>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 16, bottom: 28, left: 8 }}>
          <CartesianGrid stroke={GRID} />
          <XAxis type="number" dataKey="x" domain={[-4, 4]} allowDataOverflow tickFormatter={(v) => fmt(v, 0)}
            label={{ value: "índice numa temporada", position: "insideBottom", offset: -16, fontSize: 12 }} />
          <YAxis type="number" dataKey="y" domain={[-4, 4]} allowDataOverflow tickFormatter={(v) => fmt(v, 0)}
            label={{ value: "na temporada seguinte", angle: -90, position: "insideLeft", fontSize: 12, dy: 60 }} />
          <ReferenceLine x={0} stroke="oklch(55% 0.01 260)" />
          <ReferenceLine y={0} stroke="oklch(55% 0.01 260)" />
          <Tooltip
            cursor={false}
            content={({ active, payload }) => {
              const p = active && payload?.[0]?.payload;
              if (!p) return null;
              return (
                <div className="chart-tooltip">
                  <b>{p.team} × {p.referee}</b>
                  <div>
                    {p.season}: {fmtSigned(p.x, 2)} → {p.season + 1}: {fmtSigned(p.y, 2)}
                  </div>
                </div>
              );
            }}
          />
          <Scatter data={data.scatter} fill={BLUE} fillOpacity={0.45} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
      <RepeatTable pairs={data.favorRepeats.pairs.filter(filter)} />
      <RepeatTable pairs={data.harshRepeats.pairs.filter(filter)} />
    </>
  );
}

// ------------------------------------------------------------ E1-E3
export function FederationDetail({ fed }) {
  if (!fed.total) return <p className="hint">Sem UF de árbitro e de clube neste recorte.</p>;
  return (
    <>
      <div className="stat-kpis">
        <Kpi value={fmtPct(fed.total.observedPct)} label={`dos jogos com árbitro da UF de um dos clubes (${fed.total.observedCount} de ${fed.total.matches})`} />
        <Kpi value={fmtPct(fed.total.expectedPct)} label="se a escala fosse sorteio" />
      </div>
      <h4 className="chart-title">Por temporada</h4>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={fed.seasons} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="season" tick={{ fontSize: 11 }} />
          <YAxis unit="%" tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v) => fmtPct(v)} labelFormatter={(s) => `Temporada ${s}`} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="observedPct" name="Observado" fill={BLUE} isAnimationActive={false} maxBarSize={24} radius={[4, 4, 0, 0]} />
          <Bar dataKey="expectedPct" name="Sorteio" fill={GREY} isAnimationActive={false} maxBarSize={24} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

export function CategoryDetail({ cat }) {
  if (!cat.groups.length) return <p className="hint">Sem categoria de árbitro neste recorte.</p>;
  return (
    <>
      <p className="stat-note">Árbitro FIFA em {fmtPct(cat.fifaSharePct)} de todos os jogos do recorte.</p>
      <div className="table-wrap">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Grupo de jogos</th>
              <th className="num">Jogos</th>
              <th className="num">FIFA no grupo</th>
              <th className="num">FIFA nos demais</th>
              <th className="num">p (Fisher)</th>
            </tr>
          </thead>
          <tbody>
            {cat.groups.map((g) => (
              <tr key={g.group}>
                <td>{g.group}</td>
                <td className="num">{g.matches}</td>
                <td className="num">{fmtPct(g.fifaPct)}</td>
                <td className="num">{fmtPct(g.restPct)}</td>
                <td className="num">{fmtP(g.p)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function ConcentrationSummary({ label, v }) {
  if (!v) return null;
  return (
    <div className="stat-kpi wide">
      <span className="kpi-caption">{label}</span>
      <b>{v.p < 0.05 ? "Concentração acima do sorteio" : "Compatível com o sorteio"}</b>
      <span>
        qui-quadrado {fmt(v.x2, 0)} vs {fmt(v.x2Null, 0)} nos sorteios (95%: {fmt(v.x2NullRange[0], 0)}–{fmt(v.x2NullRange[1], 0)}) ·
        p {fmtP(v.p)} · pares com z &gt; 3: {v.cellsZ3} (sorteio ~{fmt(v.cellsZ3Null, 1)}) · sinal forte: {v.strong}
      </span>
    </div>
  );
}

const CONC_COLUMNS = [
  { label: "Clube", render: (p) => displayClubName(p.team), title: (p) => p.team },
  { label: "Árbitro", render: (p) => displayRefereeName(p.referee), title: (p) => p.referee },
  { label: "Jogos", num: true, render: (p) => p.observed },
  { label: "Esperado", num: true, render: (p) => fmt(p.expected, 1) },
  { label: "Obs ÷ esp", num: true, render: (p) => fmt(p.ratio, 2) },
  ...evidence,
];

export function ConcentrationDetail({ conc, filter = () => true }) {
  return (
    <>
      <div className="stat-kpis">
        <ConcentrationSummary label="Regras: carga, rodada e federação" v={conc.plain} />
        <ConcentrationSummary label="Regras + categoria do árbitro" v={conc.category} />
      </div>
      {["plain", "category"].map((key) =>
        conc[key]?.top?.filter(filter).length ? (
          <div key={key}>
            <h4 className="chart-title">
              Pares mais acima do esperado ({key === "plain" ? "sorteio com as regras" : "sorteio com regras + categoria"})
            </h4>
            <PairTable points={conc[key].top.filter(filter)} columns={CONC_COLUMNS} />
          </div>
        ) : null,
      )}
    </>
  );
}

// ------------------------------------------------------------ H1-H4
function Forest({ measure }) {
  const { estimate, ci, null: nullValue } = measure;
  if (estimate == null || ci[0] == null) return <div className="forest" />;
  const lo = Math.min(ci[0], nullValue);
  const hi = Math.max(ci[1], nullValue);
  const pad = (hi - lo) * 0.15 || 0.1;
  const pos = (v) => `${((v - (lo - pad)) / (hi - lo + 2 * pad)) * 100}%`;
  return (
    <div className="forest" title={`IC 95%: ${fmt(ci[0], 3)} a ${fmt(ci[1], 3)}`}>
      <div className="forest-axis" />
      <div className="forest-null" style={{ left: pos(nullValue) }} />
      <div className="forest-ci" style={{ left: pos(ci[0]), width: `calc(${pos(ci[1])} - ${pos(ci[0])})` }} />
      <div className="forest-dot" style={{ left: pos(estimate) }} />
    </div>
  );
}

export function HypothesesDetail({ data }) {
  return data.map((h) => (
    <div className="hyp-card" key={h.id}>
      <div className="hyp-head">
        <b>
          {h.id} · {h.title}
        </b>
        <span className="hyp-status">
          Temporadas {h.seasons}
          {h.n ? ` · ${h.n} jogos` : ""}
          {h.alpha ? ` · α ${fmt(h.alpha, 4)}` : ""}
        </span>
      </div>
      <p className="stat-note">Previsão registrada: {h.prediction}</p>
      {h.missing || !h.measures.length ? (
        <p className="hint">Sem dado suficiente para testar neste banco.</p>
      ) : (
        h.measures.map((m) => (
          <div className="forest-row" key={m.label}>
            <span>{m.label}</span>
            <Forest measure={m} />
            <span className="mono">
              {fmt(m.estimate, 3)} [{fmt(m.ci[0], 2)}; {fmt(m.ci[1], 2)}] · p {fmtP(m.p)}
            </span>
            <EvidenceChip level={m.verdict} />
          </div>
        ))
      )}
      <p className="hyp-status">{h.status}</p>
    </div>
  ));
}
