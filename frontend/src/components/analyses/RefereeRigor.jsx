import { useState } from "react";
import { RefereeDetail } from "../stats/details";
import COPY from "../../statsCopy";
import { displayRefereeName } from "../../nameFormat";
import { fmt, fmtSigned } from "../stats/format";
import { niceMax } from "./derive";
import { PLAIN } from "./copy";
import { AnalysisCard, Empty, Legend } from "./ui";

const EDGE = 6; // mostra os 6 mais rigorosos e os 6 mais tolerantes

// Barra divergente a partir do 0% (= o esperado para aqueles jogos): coral
// para mais cartao, azul para menos. Tom claro quando pode ser acaso.
export default function RefereeRigor({ data, highlight, tag }) {
  const [showAll, setShowAll] = useState(false);
  const refs = [...data.referees].sort((a, b) => b.shrunk - a.shrunk);
  let visible = refs;
  if (!showAll && refs.length > EDGE * 2) {
    visible = refs.filter((r, i) => i < EDGE || i >= refs.length - EDGE || r.referee === highlight);
  }
  const pct = (r) => (r.shrunk - 1) * 100;
  const dom = niceMax(Math.max(...refs.map((r) => Math.abs(pct(r))), 5));

  return (
    <AnalysisCard
      className="span-6"
      title={PLAIN.rigor.title}
      subtitle={PLAIN.rigor.subtitle}
      tag={tag}
      how={{ copy: COPY.referee, render: () => <RefereeDetail data={data} /> }}
    >
      {refs.length === 0 ? (
        <Empty>Nenhum árbitro apitou {data.floorGames}+ jogos neste recorte.</Empty>
      ) : (
        <>
          <Legend
            items={[
              ["more", "Mais cartão que o esperado"],
              ["less", "Menos cartão"],
              ["faded", "Tom claro: pode ser acaso"],
            ]}
          />
          <div className="an-rigor" role="list">
            <div className="an-rigor-axis" aria-hidden="true">
              <span />
              <span className="an-rigor-scale">
                <span style={{ left: "0%" }}>−{fmt(dom, 0)}%</span>
                <span style={{ left: "50%" }}>0%</span>
                <span style={{ left: "100%" }}>+{fmt(dom, 0)}%</span>
              </span>
              <span />
            </div>
            {visible.map((r, i) => {
              const v = pct(r);
              const half = (Math.min(Math.abs(v), dom) / dom) * 50;
              const gap = i > 0 && refs.indexOf(r) - refs.indexOf(visible[i - 1]) > 1;
              return (
                <div
                  key={r.referee}
                  role="listitem"
                  tabIndex={0}
                  className={`an-rigor-row${r.level === "acaso" ? " is-faded" : ""}${r.referee === highlight ? " is-highlight" : ""}${gap ? " has-gap" : ""}`}
                  aria-label={`${r.referee}: ${fmtSigned(v, 0)}% de cartões em relação ao esperado, ${r.games} jogos.`}
                >
                  <span className="an-rigor-name" title={r.referee}>
                    {displayRefereeName(r.referee)}
                  </span>
                  <span className="an-rigor-track" aria-hidden="true">
                    <span
                      className={`an-rigor-bar ${v >= 0 ? "more" : "less"}`}
                      style={v >= 0 ? { left: "50%", width: `${half}%` } : { right: "50%", width: `${half}%` }}
                    />
                  </span>
                  <span className="an-rigor-val" aria-hidden="true">
                    {fmtSigned(Math.round(v), 0)}%
                  </span>
                  <span className="an-tip" role="tooltip">
                    <b>{r.referee}</b>
                    <span>{r.games} jogos apitados</span>
                    <span>
                      Cartões: <b>{fmt(r.observed, 0)}</b> · esperado para esses jogos: <b>{fmt(r.expected, 0)}</b>
                    </span>
                    <span>
                      Rigor: <b>{fmtSigned(v, 0)}%</b>
                      {r.level === "acaso" ? " — ainda pode ser acaso" : " — diferença clara"}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
          {refs.length > EDGE * 2 && (
            <button type="button" className="an-more" onClick={() => setShowAll((v) => !v)}>
              {showAll ? "Mostrar só os extremos" : `Ver todos os ${refs.length} árbitros`}
            </button>
          )}
          <p className="an-note">{PLAIN.rigor.note} Só entram árbitros com {data.floorGames}+ jogos.</p>
        </>
      )}
    </AnalysisCard>
  );
}
