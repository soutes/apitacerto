import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { displayClubName } from "../../nameFormat";
import { fmt } from "../stats/format";
import { AlertIcon, AnalysisCard, CheckIcon, CompareBar, Legend, StatTile } from "../analyses/ui";
import { HOW } from "./copy";

const LINE_COLORS = ["#006e9a", "#c43f3e", "#d48e00", "#6a4c93"];

// 0 vira "—", quase certeza vira ">99%": nunca "100%" para o que ainda
// depende de jogo, nem "0%" para o que ainda pode acontecer.
function pct(v) {
  if (v == null) return "—";
  if (v <= 0) return "—";
  if (v < 1) return "<1%";
  if (v > 99) return ">99%";
  return `${fmt(v, 0)}%`;
}

const names = (list) =>
  list.length <= 1 ? list.join("") : `${list.slice(0, -1).join(", ")} e ${list[list.length - 1]}`;

// ------------------------------------------------------------ resposta curta
export function ProjectionHero({ proj }) {
  const byTitle = [...proj.teams].sort((a, b) => b.title - a.title);
  const byDrop = [...proj.teams].sort((a, b) => b.relegation - a.relegation);
  const fav = byTitle[0];
  const rival = byTitle[1];
  const almostDown = byDrop.filter((t) => t.relegation >= 90);
  const openSpots = 4 - almostDown.length;
  const fight = byDrop.filter((t) => t.relegation < 90 && t.relegation >= 10);
  const left = proj.gamesTotal - proj.gamesPlayed;
  return (
    <section className="an-hero tone-ok ca-proj-hero" aria-live="polite">
      <div className="an-hero-main">
        <span className="an-hero-icon" aria-hidden="true">
          <CheckIcon />
        </span>
        <div>
          <span className="an-eyebrow">
            Projeção {proj.season} · {fmt(proj.sims, 0)} simulações dos {left} jogos que faltam
          </span>
          <h3 className="an-hero-title">
            {displayClubName(fav.team)} tem {pct(fav.title)} de chance de ser campeão
            {rival && rival.title >= 1 ? `; ${displayClubName(rival.team)}, ${pct(rival.title)}.` : "."}
          </h3>
          <p className="an-hero-body">
            {almostDown.length > 0 && (
              <>
                {names(almostDown.map((t) => `${displayClubName(t.team)} (${pct(t.relegation)})`))}{" "}
                {almostDown.length === 1 ? "está" : "estão"} muito perto da queda.{" "}
              </>
            )}
            {openSpots > 0 && fight.length > 0 && (
              <>
                {openSpots === 1 ? "A última vaga" : `As outras ${openSpots} vagas`} do rebaixamento{" "}
                {openSpots === 1 ? "se decide" : "se decidem"} entre{" "}
                {names(fight.map((t) => `${displayClubName(t.team)} (${pct(t.relegation)})`))}.
              </>
            )}
          </p>
        </div>
      </div>
      <div className="an-hero-tiles">
        <StatTile label="Favorito ao título" value={pct(fav.title)} sub={displayClubName(fav.team)} />
        <StatTile
          label="Pontos do favorito"
          value={`${fav.low}–${fav.high}`}
          sub={`faixa provável do ${displayClubName(fav.team)}`}
        />
        <StatTile label="Maior risco de queda" value={pct(byDrop[0].relegation)} sub={displayClubName(byDrop[0].team)} tone="alert" />
        <StatTile label="Jogos que faltam" value={left} sub={`de ${proj.gamesTotal} · dados até ${proj.asOf.split("-").reverse().join("/")}`} />
      </div>
      <p className="an-hero-coin">
        <AlertIcon />
        <span>
          São chances, não certezas: o modelo usa a força de cada time até hoje e o calendário que falta (quem joga contra
          quem, em casa ou fora). Lesão, reforço e troca de técnico não entram.
        </span>
      </p>
    </section>
  );
}

// ------------------------------------------------------------ tabela projetada
function Chance({ value, tone }) {
  const strong = value >= 50;
  return (
    <span className={`ca-chance tone-${tone}${strong ? " is-strong" : ""}${value <= 0 ? " is-zero" : ""}`}
      style={{ "--a": Math.min(1, value / 100) }}>
      {pct(value)}
    </span>
  );
}

function ProjectionDetail({ proj }) {
  const bt = proj.backtest;
  return (
    <>
      <h4 className="chart-title">Qual peso dar ao passado? (jogos restantes de 2019–2025, quanto menor melhor)</h4>
      <div className="table-wrap">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Variante</th>
              <th className="num">Log-loss</th>
              <th className="num">Brier</th>
              <th className="num">Jogos</th>
            </tr>
          </thead>
          <tbody>
            {bt.variants.map((v) => (
              <tr key={v.label}>
                <td>{v.label}</td>
                <td className="num">{fmt(v.logLoss, 4)}</td>
                <td className="num">{fmt(v.brier, 4)}</td>
                <td className="num">{v.games}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h4 className="chart-title">Erro médio nos pontos finais, por fase (2019–2025)</h4>
      <div className="table-wrap">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Projetando a partir de</th>
              <th className="num">Modelo</th>
              <th className="num">Ritmo atual</th>
            </tr>
          </thead>
          <tbody>
            {bt.stages.map((s) => (
              <tr key={s.cutGames}>
                <td>rodada {s.round} ({s.cutGames} jogos)</td>
                <td className="num">{fmt(s.pointsErrorModel, 1)} pts</td>
                <td className="num">{fmt(s.pointsErrorPace, 1)} pts</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="stat-note">
        Na mesma rodada de hoje: dos {bt.table.relegationCalls.n} clubes que o modelo deu com 80% ou mais de chance de cair,{" "}
        {bt.table.relegationCalls.fell} caíram; dos {bt.table.safeCalls.n} dados como salvos (5% ou menos), {bt.table.safeCalls.fell}{" "}
        caiu. Brier do rebaixamento {fmt(bt.table.brierRelegation, 3)}; do título {fmt(bt.table.brierTitle, 3)}.
      </p>
      <p className="stat-note">
        Confronto direto: em {fmt(proj.headToHead.pairs, 0)} reencontros, o saldo "a mais" dos jogos anteriores entre os mesmos
        dois clubes não prevê o do jogo seguinte (correlação {fmt(proj.headToHead.correlation, 2)}, p {fmt(proj.headToHead.p, 2)}).
        Por isso o confronto direto não entra como efeito próprio: a força atual dos times já resume o que importa.
      </p>
      <h4 className="chart-title">Chances completas por clube</h4>
      <div className="table-wrap">
        <table className="stats-table">
          <thead>
            <tr>
              <th>Clube</th>
              <th className="num">Pts</th>
              <th className="num">Projeção (10%–90%)</th>
              <th className="num">Título</th>
              <th className="num">G-4</th>
              <th className="num">G-6</th>
              <th className="num">Queda</th>
            </tr>
          </thead>
          <tbody>
            {proj.teams.map((t) => (
              <tr key={t.team}>
                <td>{t.team}</td>
                <td className="num">{t.points}</td>
                <td className="num">
                  {fmt(t.expPoints, 1)} ({t.low}–{t.high})
                </td>
                <td className="num">{fmt(t.title, 1)}%</td>
                <td className="num">{fmt(t.top4, 1)}%</td>
                <td className="num">{fmt(t.top6, 1)}%</td>
                <td className="num">{fmt(t.relegation, 1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function ProjectionTable({ proj, highlight }) {
  const max = Math.ceil(Math.max(...proj.teams.map((t) => t.high)) / 10) * 10 + 5;
  const min = Math.max(0, Math.floor(Math.min(...proj.teams.map((t) => t.points)) / 10) * 10);
  const pos = (v) => `${((v - min) / (max - min)) * 100}%`;
  const ticks = [];
  for (let v = Math.ceil(min / 10) * 10; v <= max; v += 10) ticks.push(v);
  return (
    <AnalysisCard
      className="span-12"
      title="A tabela final mais provável"
      subtitle="Ordem pelos pontos esperados no fim. A barra vai do ponto de hoje até a faixa provável do total final."
      how={{ copy: HOW.projection, render: () => <ProjectionDetail proj={proj} /> }}
    >
      <Legend
        items={[
          ["now", "Pontos hoje"],
          ["range", "Faixa provável no fim (8 em cada 10 simulações)"],
          ["exp", "Pontos esperados"],
        ]}
      />
      <div className="ca-proj" role="table" aria-label="Tabela projetada">
        <div className="ca-proj-row is-head" role="row">
          <span role="columnheader">#</span>
          <span role="columnheader">Clube</span>
          <span role="columnheader" className="ca-proj-axis" aria-hidden="true">
            {ticks.map((t) => (
              <span key={t} style={{ left: pos(t) }}>
                {t}
              </span>
            ))}
          </span>
          <span role="columnheader" className="num">Título</span>
          <span role="columnheader" className="num">G-6</span>
          <span role="columnheader" className="num">Queda</span>
        </div>
        {proj.teams.map((t, i) => (
          <div
            role="row"
            key={t.team}
            className={`ca-proj-row${i === 3 || i === 5 || i === proj.teams.length - 5 ? " has-line" : ""}${highlight === t.team ? " is-highlight" : ""}`}
          >
            <span role="cell" className="ca-proj-pos">{i + 1}</span>
            <span role="cell" className="ca-proj-club" title={t.team}>
              <b>{displayClubName(t.team)}</b>
              <small>
                {t.points} pts em {t.games} jogos
              </small>
            </span>
            <span role="cell" className="ca-proj-bar" aria-label={`${t.points} pontos hoje; projeção ${fmt(t.expPoints, 0)} (entre ${t.low} e ${t.high})`}>
              <span className="ca-proj-grid">
                {ticks.map((v) => (
                  <i key={v} style={{ left: pos(v) }} />
                ))}
              </span>
              <span className="ca-proj-seg" style={{ left: pos(t.points), width: `calc(${pos(t.low)} - ${pos(t.points)})` }} />
              <span className="ca-proj-range" style={{ left: pos(t.low), width: `calc(${pos(t.high)} - ${pos(t.low)})` }} />
              <span className="ca-proj-now" style={{ left: pos(t.points) }} />
              <span className="ca-proj-exp" style={{ left: pos(t.expPoints) }}>
                <em>{fmt(t.expPoints, 0)}</em>
              </span>
            </span>
            <span role="cell" className="num"><Chance value={t.title} tone="title" /></span>
            <span role="cell" className="num"><Chance value={t.top6} tone="top" /></span>
            <span role="cell" className="num"><Chance value={t.relegation} tone="drop" /></span>
          </div>
        ))}
      </div>
      <p className="an-axis-unit">pontos no fim do campeonato · linhas separam G-4, G-6 e Z-4 da projeção</p>
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ chances por posição
export function PositionHeatmap({ proj, highlight }) {
  const n = proj.teams.length;
  return (
    <AnalysisCard
      className="span-12"
      title="Chance de cada clube terminar em cada posição"
      subtitle="Quanto mais escuro, mais provável. Os números são porcentagens (em branco: menos de 3%)."
      how={{ copy: HOW.projection }}
    >
      <p className="an-axis-unit ca-heat-hint">Arraste a tabela para o lado para ver todas as posições.</p>
      <div className="ca-heat-wrap">
        <div className="ca-heat" style={{ "--cols": n }} role="table" aria-label="Chance por posição final">
          <span className="ca-heat-corner" />
          {Array.from({ length: n }, (_, i) => (
            <span key={i} className={`ca-heat-col${i === 3 || i === 5 || i === n - 5 ? " has-line" : ""}`}>
              {i + 1}º
            </span>
          ))}
          {proj.teams.map((t) => (
            <div className={`ca-heat-row${highlight === t.team ? " is-highlight" : ""}`} key={t.team} role="row">
              <span className="ca-heat-club" title={t.team}>
                {displayClubName(t.team)}
              </span>
              {t.positions.map((p, i) => (
                <span
                  key={i}
                  role="cell"
                  className={`ca-heat-cell${i === 3 || i === 5 || i === n - 5 ? " has-line" : ""}${p >= 45 ? " is-dark" : ""}`}
                  style={{ "--a": Math.min(1, p / 60) }}
                  title={`${t.team}: ${fmt(p, 1)}% de terminar em ${i + 1}º`}
                >
                  {p >= 3 ? fmt(p, 0) : ""}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ evolução das chances
const MODES = [
  ["title", "Título"],
  ["top6", "G-6"],
  ["relegation", "Queda"],
];

function EvolutionTooltip({ active, payload, label, mode, focus }) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((p) => focus.includes(p.dataKey)).sort((a, b) => b.value - a.value);
  return (
    <div className="chart-tooltip">
      <b>
        Depois da rodada {label} · {MODES.find(([k]) => k === mode)[1].toLowerCase()}
      </b>
      {rows.map((p) => (
        <span key={p.dataKey}>
          <i className="an-key" style={{ background: p.stroke }} /> {displayClubName(p.dataKey)}: <b>{pct(p.value)}</b>
        </span>
      ))}
    </div>
  );
}

export function EvolutionChart({ proj, highlight }) {
  const [mode, setMode] = useState("title");
  const teams = proj.teams.map((t) => t.team);
  const data = proj.evolution.map((e) => ({ round: e.round, ...Object.fromEntries(teams.map((t) => [t, e.teams[t]?.[mode] ?? 0])) }));
  const latest = proj.evolution[proj.evolution.length - 1].teams;
  const focus = [...teams].sort((a, b) => (latest[b]?.[mode] ?? 0) - (latest[a]?.[mode] ?? 0)).filter((t) => (latest[t]?.[mode] ?? 0) >= 1).slice(0, 4);
  if (highlight && teams.includes(highlight) && !focus.includes(highlight)) focus.splice(3, 1, highlight);
  const color = (t) => LINE_COLORS[focus.indexOf(t)];
  const lastRound = data[data.length - 1].round;
  return (
    <AnalysisCard
      className="span-12"
      title={`Como as chances mudaram em ${proj.season}`}
      subtitle="A projeção refeita depois de cada rodada, só com os jogos que já tinham acontecido."
      how={{ copy: HOW.projectionEvolution }}
    >
      <div className="an-seg" role="group" aria-label="Chance mostrada">
        {MODES.map(([key, label]) => (
          <button key={key} type="button" aria-pressed={mode === key} className={mode === key ? "is-active" : undefined} onClick={() => setMode(key)}>
            {label}
          </button>
        ))}
      </div>
      <Legend items={[...focus.map((t) => [`line-${focus.indexOf(t)}`, displayClubName(t)]), ["line-rest", "Demais clubes"]]} />
      <div className="an-chart" role="img" aria-label={`Chance de ${MODES.find(([k]) => k === mode)[1].toLowerCase()} por rodada. Hoje: ${focus.map((t) => `${displayClubName(t)} ${pct(latest[t][mode])}`).join(", ")}.`}>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 10, right: 96, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="oklch(93% 0.005 80)" vertical={false} />
            <XAxis dataKey="round" tick={{ fontSize: 11, fill: "oklch(45% 0.01 260)" }} tickLine={false} axisLine={{ stroke: "oklch(85% 0.006 80)" }} />
            <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: "oklch(50% 0.01 260)" }} tickLine={false} axisLine={false} width={44} />
            <Tooltip content={<EvolutionTooltip mode={mode} focus={focus} />} />
            {teams
              .filter((t) => !focus.includes(t))
              .map((t) => (
                <Line key={t} dataKey={t} stroke="oklch(80% 0.01 260)" strokeWidth={1} dot={false} isAnimationActive={false} />
              ))}
            {focus.map((t) => (
              <Line
                key={t}
                dataKey={t}
                stroke={color(t)}
                strokeWidth={2.5}
                dot={false}
                isAnimationActive={false}
                label={({ x, y, index }) =>
                  data[index].round === lastRound ? (
                    <text key={t} x={x + 8} y={y + 4} className="ca-line-label">
                      {displayClubName(t)} {pct(latest[t][mode])}
                    </text>
                  ) : null
                }
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="an-axis-unit">rodada (a cada 10 jogos do campeonato)</p>
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ dá para confiar?
export function TrustCard({ proj }) {
  const bt = proj.backtest;
  const t = bt.table;
  const max = Math.ceil(Math.max(...bt.stages.flatMap((s) => [s.pointsErrorModel, s.pointsErrorPace])));
  const wins = t.titleFavorites.filter((f) => f.won).length;
  return (
    <AnalysisCard
      className="span-12"
      title="Dá para confiar na projeção?"
      subtitle={`O mesmo modelo, rodado nas temporadas ${bt.table.seasons[0]}–${bt.table.seasons[bt.table.seasons.length - 1]} a partir do mesmo ponto do campeonato, comparado com o que aconteceu.`}
      how={{ copy: HOW.projection, render: () => <ProjectionDetail proj={proj} /> }}
    >
      <div className="ca-trust">
        <div className="ca-trust-col">
          <span className="ca-sub-head">Erro médio nos pontos finais de cada clube</span>
          <Legend
            items={[
              ["found", "Projeção"],
              ["chance", "Ritmo atual (pontos por jogo × 38)"],
            ]}
          />
          <div className="an-groups">
            {bt.stages.map((s) => (
              <div className="an-group" key={s.cutGames}>
                <span className="an-group-head">
                  <b>Projetando da rodada {s.round}</b>
                </span>
                <CompareBar label="Projeção" value={s.pointsErrorModel} max={max} tone="found" text={`${fmt(s.pointsErrorModel, 1)} pts`} />
                <CompareBar label="Ritmo atual" value={s.pointsErrorPace} max={max} tone="chance" text={`${fmt(s.pointsErrorPace, 1)} pts`} />
              </div>
            ))}
          </div>
        </div>
        <div className="ca-trust-col">
          <span className="ca-sub-head">Na rodada {Math.round(t.cutGames / 10)}, em anos passados</span>
          <div className="ca-trust-tiles">
            <StatTile
              label="Deu 80%+ de queda"
              value={`${t.relegationCalls.fell} de ${t.relegationCalls.n}`}
              sub="caíram de fato"
            />
            <StatTile label="Deu 5% ou menos de queda" value={`${t.safeCalls.n - t.safeCalls.fell} de ${t.safeCalls.n}`} sub="se salvaram" />
            <StatTile label="Favorito ao título" value={`${wins} de ${t.titleFavorites.length}`} sub="foi campeão" tone={wins < t.titleFavorites.length / 2 ? "alert" : undefined} />
          </div>
          <ul className="an-list">
            {t.titleFavorites.map((f) => (
              <li key={f.season}>
                <b>{f.season}</b>: {displayClubName(f.team)} com {pct(f.chance)} {f.won ? "foi campeão" : "não foi campeão"}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p className="an-note">
        O rebaixamento é bem previsto a esta altura. O título, menos: o returno ainda vira campeonatos, e o modelo não sabe
        de elenco, lesão ou técnico novo. Leia as chances de título com essa folga.
      </p>
    </AnalysisCard>
  );
}
