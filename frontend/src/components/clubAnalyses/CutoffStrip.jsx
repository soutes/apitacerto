import { useState } from "react";
import { displayClubName } from "../../nameFormat";
import { AnalysisCard, Empty, Legend } from "../analyses/ui";
import { FATES, HOW } from "./copy";
import { cutoffs, FATE_ORDER, pointsAt } from "./derive";

const MODES = [
  ["relegation", "Rebaixamento"],
  ["top", "G-6"],
  ["title", "Título"],
];

const who = (x) => (x ? x.who.map((w) => `${displayClubName(w.team)} ${w.season}`).join(", ") : "");

// Linhas de corte de cada modo: "abaixo daqui ninguem..." e "acima daqui...".
function lines(cut, mode) {
  if (mode === "relegation") {
    return {
      low: cut.safeMin && { at: cut.safeMin.points - 0.5, label: `Abaixo de ${cut.safeMin.points}: ninguém escapou`, tone: "bad" },
      high: cut.relegatedMax && { at: cut.relegatedMax.points + 0.5, label: `Acima de ${cut.relegatedMax.points}: ninguém caiu`, tone: "good" },
      headline: cut.safeMin && cut.relegatedMax && (
        <>
          Nenhum clube com menos de <b>{cut.safeMin.points} pontos</b> escapou da queda — e nenhum com mais de{" "}
          <b>{cut.relegatedMax.points}</b> caiu.
        </>
      ),
      records: cut.safeMin && `Menor pontuação que escapou: ${who(cut.safeMin)}. Maior que caiu: ${who(cut.relegatedMax)}.`,
    };
  }
  if (mode === "top") {
    return {
      low: cut.topMin && { at: cut.topMin.points - 0.5, label: `Abaixo de ${cut.topMin.points}: ninguém chegou ao G-6`, tone: "bad" },
      high: cut.outsideTopMax && { at: cut.outsideTopMax.points + 0.5, label: `Acima de ${cut.outsideTopMax.points}: todos no G-6`, tone: "good" },
      headline: cut.topMin && cut.outsideTopMax && (
        <>
          Para terminar no G-6, ninguém tinha menos de <b>{cut.topMin.points} pontos</b> — e com mais de{" "}
          <b>{cut.outsideTopMax.points}</b>, todos terminaram lá.
        </>
      ),
      records: cut.topMin && `Menor pontuação que chegou ao G-6: ${who(cut.topMin)}. Maior que ficou fora: ${who(cut.outsideTopMax)}.`,
    };
  }
  const champMax = Math.max(...cut.rows.filter((r) => r.fate === "champion").map((r) => r.pts));
  const sureTitle = cut.nonChampionMax && cut.nonChampionMax.points < champMax;
  return {
    low: cut.championMin && { at: cut.championMin.points - 0.5, label: `Abaixo de ${cut.championMin.points}: ninguém foi campeão`, tone: "bad" },
    high: sureTitle && { at: cut.nonChampionMax.points + 0.5, label: `Acima de ${cut.nonChampionMax.points}: só campeões`, tone: "good" },
    headline: cut.championMin && (
      <>
        Todo campeão tinha pelo menos <b>{cut.championMin.points} pontos</b> nesta rodada
        {sureTitle ? (
          <>
            {" "}— e com mais de <b>{cut.nonChampionMax.points}</b>, ninguém deixou escapar o título.
          </>
        ) : (
          "."
        )}
      </>
    ),
    records: cut.championMin && `Campeão com menos pontos nesta rodada: ${who(cut.championMin)}.`,
  };
}

function stack(items) {
  const seen = new Map();
  return items.map((it) => {
    const k = seen.get(it.pts) ?? 0;
    seen.set(it.pts, k + 1);
    return { ...it, level: k };
  });
}

function Detail({ cut, current, round }) {
  const rows = [...cut.rows].sort((a, b) => b.pts - a.pts || a.season - b.season);
  return (
    <div className="table-wrap">
      <table className="stats-table">
        <thead>
          <tr>
            <th>Clube</th>
            <th className="num">Temporada</th>
            <th className="num">Pontos após {round} jogos</th>
            <th>Terminou</th>
          </tr>
        </thead>
        <tbody>
          {current?.map((t) => (
            <tr key={`c-${t.team}`}>
              <td>{t.team}</td>
              <td className="num">{t.season} (em andamento)</td>
              <td className="num">{t.pts}</td>
              <td>—</td>
            </tr>
          ))}
          {rows.map((r) => (
            <tr key={`${r.team}-${r.season}`}>
              <td>{r.team}</td>
              <td className="num">{r.season}</td>
              <td className="num">{r.pts}</td>
              <td>
                {r.position}º · {FATES[r.fate]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CutoffStrip({ closed, current, round, highlight }) {
  const [mode, setMode] = useState("relegation");
  const [hover, setHover] = useState(null);
  const cut = cutoffs(closed, round);
  const now = current
    ? current.teams
        .map((t) => ({ team: t.team, season: current.season, pts: pointsAt(t, round) }))
        .filter((t) => t.pts != null)
    : [];
  if (!cut.rows.length) {
    return (
      <AnalysisCard className="span-12" title="A linha da tabela" how={{ copy: HOW.cutoff }}>
        <Empty>Sem temporada completa para comparar.</Empty>
      </AnalysisCard>
    );
  }
  const maxPts = Math.max(...cut.rows.map((r) => r.pts), ...now.map((t) => t.pts), 5);
  const xMax = Math.ceil((maxPts + 1) / 5) * 5;
  const frac = (v) => Math.max(0, Math.min(1, v / xMax));
  const pos = (v) => `${frac(v) * 100}%`;
  const tickStep = xMax > 60 ? 10 : 5;
  const ticks = Array.from({ length: Math.floor(xMax / tickStep) + 1 }, (_, i) => i * tickStep);
  const L = lines(cut, mode);
  const lanes = [
    ...FATE_ORDER.map((fate) => ({
      key: fate,
      label: FATES[fate],
      dots: stack(cut.rows.filter((r) => r.fate === fate).sort((a, b) => a.season - b.season)),
    })),
    ...(now.length ? [{ key: "now", label: `${current.season} agora`, dots: stack(now) }] : []),
  ];
  const below = L.low ? now.filter((t) => t.pts < L.low.at) : [];
  const above = L.high ? now.filter((t) => t.pts > L.high.at) : [];

  return (
    <AnalysisCard
      className="span-12"
      title={`A linha da tabela depois de ${round} jogos`}
      subtitle="Cada ponto é um clube em uma temporada (2018 em diante), na altura dos pontos que tinha nesta rodada — separado por como terminou o campeonato."
      how={{ copy: HOW.cutoff, render: () => <Detail cut={cut} current={now} round={round} /> }}
    >
      <div className="an-seg" role="group" aria-label="Linha de corte">
        {MODES.map(([key, label]) => (
          <button key={key} type="button" aria-pressed={mode === key} className={mode === key ? "is-active" : undefined} onClick={() => setMode(key)}>
            {label}
          </button>
        ))}
      </div>
      {L.headline && <p className="an-headline ca-cut-headline">{L.headline}</p>}

      <div className="ca-strip" role="img" aria-label={`Pontos após ${round} jogos de cada clube em cada temporada, por destino final. ${L.records ?? ""}`}>
        <div className="ca-strip-plot">
          {L.low && <span className={`ca-zone tone-${L.low.tone}`} style={{ "--x0": 0, "--x1": frac(L.low.at) }} />}
          {L.high && <span className={`ca-zone tone-${L.high.tone}`} style={{ "--x0": frac(L.high.at), "--x1": 1 }} />}
          {lanes.map((lane) => {
            const height = Math.max(...lane.dots.map((d) => d.level + 1), 1);
            return (
              <div className={`ca-lane lane-${lane.key}`} key={lane.key} style={{ "--stack": height }}>
                <span className="ca-lane-label">{lane.label}</span>
                <span className="ca-lane-track">
                  {lane.dots.map((d) => {
                    const mine = highlight && d.team === highlight;
                    return (
                      <span
                        key={`${d.team}-${d.season}`}
                        className={`ca-dot${lane.key === "now" ? " is-now" : ""}${mine ? " is-mine" : ""}${highlight && !mine ? " is-dim" : ""}`}
                        style={{ left: pos(d.pts), "--level": d.level }}
                        onMouseEnter={() => setHover({ ...d, lane: lane.key })}
                        onMouseLeave={() => setHover(null)}
                      >
                        {mine && lane.key !== "now" && <em>{String(d.season).slice(2)}</em>}
                      </span>
                    );
                  })}
                </span>
              </div>
            );
          })}
          {[L.low, L.high].filter(Boolean).map((l) => (
            <span
              key={l.label}
              className={`ca-cutline tone-${l.tone}${(l === L.low ? frac(l.at) > 0.3 : frac(l.at) > 0.75) ? " is-right" : ""}`}
              style={{ "--x": frac(l.at) }}
            >
              <span>{l.label}</span>
            </span>
          ))}
          {hover && (
            <span className={`ca-tip${frac(hover.pts) > 0.7 ? " is-right" : ""}`} style={{ "--x": frac(hover.pts) }}>
              <b>
                {hover.team} · {hover.season}
              </b>
              <span>
                {hover.pts} pontos após {round} jogos
              </span>
              <span>{hover.lane === "now" ? "Temporada em andamento" : `Terminou em ${hover.position}º · ${FATES[hover.fate]}`}</span>
            </span>
          )}
        </div>
        <div className="ca-axis" aria-hidden="true">
          <span />
          <span className="ca-axis-ticks">
            {ticks.map((t) => (
              <span key={t} style={{ left: pos(t) }}>
                {t}
              </span>
            ))}
          </span>
        </div>
        <p className="an-axis-unit">pontos depois de {round} jogos</p>
      </div>

      <Legend
        items={[
          ["dot", "Clube em uma temporada completa"],
          ...(now.length ? [["now", `${current.season}, em andamento`]] : []),
        ]}
      />
      {L.records && <p className="an-note">{L.records}</p>}
      {current && (below.length > 0 || above.length > 0) && (
        <div className="ca-now-flags">
          {below.length > 0 && (
            <p>
              <span className="chip chip-forte">
                <i className="chip-dot" aria-hidden="true" />
                Abaixo da linha em {current.season}
              </span>{" "}
              {below.map((t) => `${displayClubName(t.team)} (${t.pts})`).join(", ")}
            </p>
          )}
          {above.length > 0 && (
            <p>
              <span className="chip chip-apoia">
                <i className="chip-dot" aria-hidden="true" />
                Acima da linha em {current.season}
              </span>{" "}
              {above.map((t) => `${displayClubName(t.team)} (${t.pts})`).join(", ")}
            </p>
          )}
        </div>
      )}
    </AnalysisCard>
  );
}
