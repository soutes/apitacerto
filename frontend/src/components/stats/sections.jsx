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
import COPY from "../../statsCopy";
import { displayClubName, displayRefereeName } from "../../nameFormat";
import EvidenceChip from "./EvidenceChip";
import FunnelChart from "./FunnelChart";
import MethodNote from "./MethodNote";
import PairTable from "./PairTable";
import { fmt, fmtP, fmtPct, fmtSigned } from "./format";

const TEAL = "oklch(50% 0.12 195)";
const CORAL = "oklch(56% 0.17 25)";
const AMBER = "oklch(70% 0.15 75)";
const GREY = "oklch(80% 0.01 260)";

function Card({ copy, children }) {
  return (
    <section className="stat-card">
      <div>
        <h3>{copy.title}</h3>
        {copy.subtitle && <div className="stat-sub">{copy.subtitle}</div>}
      </div>
      {children}
      <MethodNote {...copy} />
    </section>
  );
}

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

// ------------------------------------------------------------ introducao
const ANALYSES = [
  ["cards", "Cartões ao clube"],
  ["rivalCards", "Cartões ao adversário"],
  ["points", "Pontos acima do esperado"],
  ["ease", "Jogos mais fáceis"],
];

export function IntroSection({ report }) {
  const { overview, pairs, partialSeasons } = report;
  return (
    <section className="stat-card">
      <h3>{COPY.intro.title}</h3>
      <p className="stat-note">{COPY.intro.body}</p>
      <div className="legend-list">
        {COPY.intro.levels.map(([level, text]) => (
          <div key={level} className="legend-item">
            <EvidenceChip level={level} />
            <span>{text}</span>
          </div>
        ))}
      </div>
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
              <th className="num">Sinal forte</th>
              <th className="num">Sinal fraco</th>
              <th className="num">Fraco esperado só por acaso</th>
            </tr>
          </thead>
          <tbody>
            {ANALYSES.map(([key, label]) => {
              const s = pairs[key].summary;
              return (
                <tr key={key}>
                  <td>{label}</td>
                  <td className="num">{s.tested}</td>
                  <td className="num">{s.strong}</td>
                  <td className="num">{s.weak}</td>
                  <td className="num">~{fmt(s.expectedWeakByChance, 1)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {partialSeasons.length > 0 && (
        <p className="hint">
          Temporada {partialSeasons.join(", ")} em andamento: os números mudam toda semana. Os vereditos das hipóteses
          usam só temporadas encerradas.
        </p>
      )}
      <p className="hint">
        {COPY.intro.prereg}{" "}
        <a href={COPY.intro.preregUrl} target="_blank" rel="noreferrer">
          Ver o registro público
        </a>
        .
      </p>
    </section>
  );
}

// ------------------------------------------------------------ L1
export function LeagueSection({ league, selected }) {
  const rows = league.seasons.map((s) => ({
    ...s,
    cardsErr: s.cardsDiffCi[0] == null ? [0, 0] : [s.cardsDiff - s.cardsDiffCi[0], s.cardsDiffCi[1] - s.cardsDiff],
    pensErr: s.pensDiffCi[0] == null ? [0, 0] : [s.pensDiff - s.pensDiffCi[0], s.pensDiffCi[1] - s.pensDiff],
  }));
  const color = (s) => (s === selected ? CORAL : s === 2020 ? AMBER : TEAL);
  const diffChart = (key, err, title) => (
    <div>
      <h4 className="chart-title">{title}</h4>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="oklch(92% 0.006 80)" vertical={false} />
          <XAxis dataKey="season" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(v) => fmt(v, 1)} tick={{ fontSize: 11 }} />
          <ReferenceLine y={0} stroke="oklch(55% 0.01 260)" />
          <Tooltip formatter={(v) => fmtSigned(v, 2)} labelFormatter={(s) => `Temporada ${s}${s === 2020 ? " (sem público)" : ""}`} />
          <Bar dataKey={key} name="mandante − visitante" isAnimationActive={false}>
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
    <Card copy={COPY.league}>
      <div className="chart-pair">
        {diffChart("cardsDiff", "cardsErr", "Cartões por jogo: mandante − visitante")}
        {diffChart("pensDiff", "pensErr", "Gols de pênalti por jogo: mandante − visitante")}
      </div>
      <div>
        <h4 className="chart-title">Resultado do mandante (%)</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="oklch(92% 0.006 80)" vertical={false} />
            <XAxis dataKey="season" tick={{ fontSize: 11 }} />
            <YAxis unit="%" tick={{ fontSize: 11 }} domain={[0, 100]} />
            <Tooltip formatter={(v) => fmtPct(v)} labelFormatter={(s) => `Temporada ${s}`} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="homeWinPct" stackId="r" name="Vitória" fill={TEAL} isAnimationActive={false} />
            <Bar dataKey="drawPct" stackId="r" name="Empate" fill={GREY} isAnimationActive={false} />
            <Bar dataKey="awayWinPct" stackId="r" name="Derrota" fill={CORAL} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="stat-note">
        Em destaque: temporada selecionada (coral) e 2020, jogada sem público (âmbar).
      </p>
    </Card>
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

export function RefereeSection({ data }) {
  const [showAll, setShowAll] = useState(false);
  if (!data.referees.length) {
    return (
      <Card copy={COPY.referee}>
        <p className="hint">Nenhum árbitro com {data.floorGames}+ jogos neste recorte.</p>
      </Card>
    );
  }
  const refs = showAll ? data.referees : data.referees.slice(0, 12);
  return (
    <Card copy={COPY.referee}>
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
    </Card>
  );
}

// ------------------------------------------------------------ A1-A3
export function PairSection({ kind, data }) {
  const isCount = kind !== "points";
  return (
    <Card copy={COPY[kind]}>
      <Summary summary={data.summary} />
      {data.points.length === 0 ? (
        <p className="hint">Nenhum par com {data.floor}+ jogos neste recorte.</p>
      ) : (
        <>
          <FunnelChart
            points={data.points}
            funnel={data.funnel}
            xKey={isCount ? "expected" : "n"}
            yKey={isCount ? "ratio" : "perGame"}
            center={isCount ? 1 : 0}
            xLabel={isCount ? "cartões esperados no par" : "jogos do par"}
            yLabel={isCount ? "observado ÷ esperado" : "pontos/jogo vs esperado"}
          />
          <PairTable points={data.points} columns={isCount ? COUNT_COLUMNS : POINT_COLUMNS} />
        </>
      )}
    </Card>
  );
}

// ------------------------------------------------------------ A4
export function EaseSection({ data }) {
  return (
    <Card copy={COPY.ease}>
      <Summary summary={data.summary} />
      {data.points.length === 0 ? (
        <p className="hint">Nenhum par com {data.floor}+ jogos neste recorte.</p>
      ) : (
        <>
          <FunnelChart points={data.points} funnel={data.funnel} xKey="n" yKey="perGame" center={0}
            xLabel="jogos do par" yLabel="xPts/jogo vs sorteio" />
          <PairTable points={data.points} columns={EASE_COLUMNS} />
        </>
      )}
    </Card>
  );
}

// ------------------------------------------------------------ A5
function RepeatTable({ repeats }) {
  if (!repeats.pairs.length) return null;
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
          {repeats.pairs.map((p) => (
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

export function CrossSeasonSection({ data }) {
  if (!data?.available) {
    return (
      <Card copy={COPY.cross}>
        <p className="hint">Sem pares com jogos em temporadas seguidas.</p>
      </Card>
    );
  }
  const c = data.correlation;
  return (
    <Card copy={COPY.cross}>
      <div className="stat-kpis">
        <Kpi
          value={c ? fmt(c.r, 2) : "—"}
          label={c ? `correlação entre uma temporada e a seguinte (IC 95%: ${fmt(c.lo, 2)} a ${fmt(c.hi, 2)}; ${c.n} comparações)` : "sem comparações suficientes"}
        />
        <Kpi
          value={`${data.favorRepeats.observed} vs ${fmt(data.favorRepeats.expected, 1)}`}
          label="pares com sinal de favorecimento repetido em 2+ temporadas (observado vs. acaso)"
        />
        <Kpi
          value={`${data.harshRepeats.observed} vs ${fmt(data.harshRepeats.expected, 1)}`}
          label="árbitro mais duro com o mesmo clube em 2+ temporadas (observado vs. acaso)"
        />
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 16, bottom: 28, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="oklch(92% 0.006 80)" />
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
          <Scatter data={data.scatter} fill={TEAL} fillOpacity={0.45} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
      <RepeatTable repeats={data.favorRepeats} />
      <RepeatTable repeats={data.harshRepeats} />
    </Card>
  );
}

// ------------------------------------------------------------ E1-E3
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

export function EscalaSection({ data }) {
  const fed = data.federation;
  const cat = data.category;
  const conc = data.concentration;
  return (
    <>
      <Card copy={COPY.federation}>
        {!fed.total ? (
          <p className="hint">Sem UF de árbitro e de clube neste recorte.</p>
        ) : (
          <>
            <div className="stat-kpis">
              <Kpi value={fmtPct(fed.total.observedPct)} label={`dos jogos com árbitro da UF de um dos clubes (${fed.total.observedCount} de ${fed.total.matches})`} />
              <Kpi value={fmtPct(fed.total.expectedPct)} label="se a escala fosse sorteio" />
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={fed.seasons} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(92% 0.006 80)" vertical={false} />
                <XAxis dataKey="season" tick={{ fontSize: 11 }} />
                <YAxis unit="%" tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtPct(v)} labelFormatter={(s) => `Temporada ${s}`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="observedPct" name="Observado" fill={CORAL} isAnimationActive={false} />
                <Bar dataKey="expectedPct" name="Sorteio" fill={GREY} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </>
        )}
      </Card>

      <Card copy={COPY.category}>
        {!cat.groups.length ? (
          <p className="hint">Sem categoria de árbitro neste recorte.</p>
        ) : (
          <>
            <p className="stat-note">Árbitro FIFA em {fmtPct(cat.fifaSharePct)} de todos os jogos do recorte.</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={cat.groups} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(92% 0.006 80)" vertical={false} />
                <XAxis dataKey="group" tick={{ fontSize: 11 }} />
                <YAxis unit="%" tick={{ fontSize: 11 }} domain={[0, 100]} />
                <Tooltip formatter={(v) => fmtPct(v)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="fifaPct" name="Árbitro FIFA no grupo" fill={TEAL} isAnimationActive={false} />
                <Bar dataKey="restPct" name="Nos demais jogos" fill={GREY} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
            <p className="stat-note">
              {cat.groups.map((g) => `${g.group}: ${g.matches} jogos, p ${fmtP(g.p)}`).join(" · ")}
            </p>
          </>
        )}
      </Card>

      <Card copy={COPY.concentration}>
        <div className="stat-kpis">
          <ConcentrationSummary label="Regras: carga, rodada e federação" v={conc.plain} />
          <ConcentrationSummary label="Regras + categoria do árbitro" v={conc.category} />
        </div>
        {conc.category?.top?.length > 0 && (
          <>
            <h4 className="chart-title">Pares mais acima do esperado (sorteio com categoria)</h4>
            <PairTable points={conc.category.top} columns={CONC_COLUMNS} />
          </>
        )}
      </Card>
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

export function HypothesesSection({ data }) {
  return (
    <Card copy={COPY.hypotheses}>
      {data.map((h) => (
        <div className="hyp-card" key={h.id}>
          <div className="hyp-head">
            <b>
              {h.id} · {h.title}
            </b>
            <span className="hyp-status">
              Temporadas {h.seasons}
              {h.n ? ` · ${h.n} jogos` : ""}
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
      ))}
    </Card>
  );
}
