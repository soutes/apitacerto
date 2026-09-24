import { useState } from "react";
import { PairDetail } from "../stats/details";
import EvidenceChip from "../stats/EvidenceChip";
import { levelLabel } from "../stats/levels";
import COPY from "../../statsCopy";
import { displayClubName, displayRefereeName } from "../../nameFormat";
import { fmt } from "../stats/format";
import { axisTicks, byStrength, filterPairs, METRICS, niceMax, PAIR_ANALYSES } from "./derive";
import { PLAIN } from "./copy";
import { AnalysisCard, Empty, Legend } from "./ui";

const LIMIT = 8;

function names(p, { team, referee }) {
  const club = displayClubName(p.team);
  const ref = displayRefereeName(p.referee);
  const games = `${p.n} ${p.n === 1 ? "jogo" : "jogos"}`;
  if (team && referee) return { primary: `${club} com ${ref}`, secondary: games };
  if (team) return { primary: ref, secondary: games, title: p.referee };
  if (referee) return { primary: club, secondary: games, title: p.team };
  return { primary: club, secondary: `com ${ref} · ${games}`, title: `${p.team} com ${p.referee}` };
}

function direction(m, p, a, e) {
  const diff = a - e;
  if (Math.abs(diff) < 0.005) return "Igual ao esperado";
  const favor = m.favorWhenHigher ? diff > 0 : diff < 0;
  return `${favor ? "A favor do" : "Contra o"} ${displayClubName(p.team)}`;
}

function totals(metric, m, p, a, e) {
  if (metric === "ease") return [fmt(a, 2), fmt(e, 2)];
  return [
    `${fmt(p.observed, 0)} (${fmt(a, m.digits)} por jogo)`,
    `${fmt(p.expected, 1)} (${fmt(e, m.digits)} por jogo)`,
  ];
}

// "Haltere" por dupla: o que aconteceu (ponto cheio) x o que se esperava
// (anel), por jogo. Cor so para quem tem sinal (cinza = dentro do normal).
export default function PairExplorer({ report, filters, metric, onMetric }) {
  const [showAll, setShowAll] = useState(false);
  const m = METRICS[metric];
  const data = report.pairs[metric];
  const rows = filterPairs(data.points, filters)
    .filter((p) => m.actual(p) != null && m.expected(p) != null)
    .sort(byStrength);
  const visible = showAll ? rows : rows.slice(0, LIMIT);
  const max = m.fixedMax ?? niceMax(Math.max(...rows.map((p) => Math.max(m.actual(p), m.expected(p))), 0.1));
  const axis = axisTicks(max);
  const tickDigits = Number.isInteger(axis.step) ? 0 : 1;
  const pos = (v) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;
  const q = PLAIN.questions[metric];

  return (
    <AnalysisCard
      id="an-explorer"
      className="span-7"
      title={q.title}
      subtitle={PLAIN.explorer.subtitle}
      how={{ copy: COPY[metric], render: () => <PairDetail kind={metric} data={data} points={rows} /> }}
    >
      <div className="an-seg" role="group" aria-label="Pergunta">
        {PAIR_ANALYSES.map((key) => (
          <button
            key={key}
            type="button"
            aria-pressed={metric === key}
            className={metric === key ? "is-active" : undefined}
            onClick={() => {
              onMetric(key);
              setShowAll(false);
            }}
          >
            {PLAIN.questions[key].tab}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <Empty>
          Nenhuma dupla árbitro × clube se enfrentou {data.floor}+ vezes neste recorte. Tente outra temporada ou “Todas”.
        </Empty>
      ) : (
        <>
          <Legend
            items={[
              ["dot", `${m.actualLabel} (a cor segue a etiqueta)`],
              ["ring", m.expectedLabel],
            ]}
          />
          <div className="an-pairs" role="list" aria-label={q.title} style={{ "--grid-step": `${(axis.step / max) * 100}%` }}>
            <div className="an-pairs-axis" aria-hidden="true">
              <span />
              <span className="an-axis-ticks">
                {axis.values.map((t) => (
                  <span key={t} style={{ left: pos(t) }}>
                    {fmt(t, tickDigits)}
                  </span>
                ))}
              </span>
            </div>
            {visible.map((p) => {
              const a = m.actual(p);
              const e = m.expected(p);
              const n = names(p, filters);
              const [actualText, expectedText] = totals(metric, m, p, a, e);
              const dir = direction(m, p, a, e);
              return (
                <div
                  role="listitem"
                  tabIndex={0}
                  key={`${p.team}|${p.referee}`}
                  className={`an-pair lvl-${p.level}`}
                  aria-label={`${n.primary}: ${m.actualLabel.toLowerCase()} ${fmt(a, m.digits)} por jogo, esperado ${fmt(e, m.digits)}. ${dir}. ${levelLabel(p.level)}.`}
                >
                  <span className="an-pair-name">
                    <b title={n.title}>{n.primary}</b>
                    <small>{n.secondary}</small>
                  </span>
                  <span className="an-pair-track" aria-hidden="true">
                    <span className="an-pair-seg" style={{ left: pos(Math.min(a, e)), width: `calc(${pos(Math.max(a, e))} - ${pos(Math.min(a, e))})` }} />
                    <span className="an-pair-exp" style={{ left: pos(e) }} />
                    <span className="an-pair-dot" style={{ left: pos(a) }} />
                  </span>
                  <span className="an-pair-val" aria-hidden="true">
                    {fmt(a, m.digits)} <small>vs {fmt(e, m.digits)}</small>
                  </span>
                  <span className="an-pair-chip">
                    <EvidenceChip level={p.level} />
                  </span>
                  <span className="an-tip" role="tooltip">
                    <b>
                      {p.team} com {p.referee}
                    </b>
                    <span>{p.n} jogos juntos</span>
                    <span>
                      {m.actualLabel}: <b>{actualText}</b>
                    </span>
                    <span>
                      {m.expectedLabel}: <b>{expectedText}</b>
                    </span>
                    <span>
                      {dir} · {levelLabel(p.level)}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
          <p className="an-axis-unit">{m.unit}</p>
          {rows.length > LIMIT && (
            <button type="button" className="an-more" onClick={() => setShowAll((v) => !v)}>
              {showAll ? `Mostrar só as ${LIMIT} mais fora do normal` : `Ver todas as ${rows.length} duplas`}
            </button>
          )}
        </>
      )}
    </AnalysisCard>
  );
}
