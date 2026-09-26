import { displayClubName } from "../../nameFormat";
import { fmt } from "../stats/format";
import { AnalysisCard, Legend } from "../analyses/ui";
import { HOW } from "./copy";
import { thermometer } from "./derive";

const SEGMENTS = [
  ["relegatedPct", "relegated", "caíram"],
  ["midPct", "mid", "meio da tabela"],
  ["topPct", "top6", "G-6"],
  ["championPct", "champion", "campeões"],
];

// Termometro da temporada em andamento: o que aconteceu, no passado, com
// quem tinha a mesma pontuacao depois do mesmo numero de jogos.
export default function Thermometer({ closed, current, highlight }) {
  const rows = thermometer(closed, current);
  return (
    <AnalysisCard
      className="span-12"
      title={`Termômetro ${current.season}: quem já esteve aqui, como terminou?`}
      subtitle="Para cada clube, os casos de 2007 em diante com pontos parecidos (2 a mais ou a menos) depois do mesmo número de jogos — e o fim que tiveram."
      how={{ copy: HOW.thermometer }}
    >
      <Legend
        items={[
          ["relegated", "Caíram"],
          ["mid", "Meio da tabela"],
          ["top6", "G-6"],
          ["champion", "Campeões"],
        ]}
      />
      <div className="ca-thermo" role="table" aria-label={`Termômetro da temporada ${current.season}`}>
        <div className="ca-thermo-row is-head" role="row">
          <span role="columnheader">#</span>
          <span role="columnheader">Clube</span>
          <span role="columnheader" className="num">Pts (J)</span>
          <span role="columnheader">Como terminaram os casos parecidos</span>
        </div>
        {rows.map((r) => (
          <div role="row" key={r.team} className={`ca-thermo-row${highlight === r.team ? " is-highlight" : ""}`}>
            <span role="cell" className="ca-thermo-pos">{r.position}</span>
            <span role="cell" className="ca-thermo-club" title={r.team}>
              {displayClubName(r.team)}
              {r.belowSurvivors && <small className="ca-flag bad">ninguém escapou com tão pouco</small>}
            </span>
            <span role="cell" className="num ca-thermo-pts">
              {r.points} <small>({r.games})</small>
            </span>
            <span role="cell" className="ca-thermo-bar">
              {r.peers < 3 ? (
                <small className="ca-thermo-few">
                  {r.peers === 0 ? "Nenhum caso parecido desde 2007" : `Só ${r.peers} caso${r.peers > 1 ? "s" : ""} parecido${r.peers > 1 ? "s" : ""}`}
                </small>
              ) : (
                <>
                  <span className="ca-stack" title={SEGMENTS.map(([k, , l]) => `${fmt(r[k], 0)}% ${l}`).join(" · ")}>
                    {SEGMENTS.map(([k, cls]) =>
                      r[k] > 0 ? <span key={k} className={`ca-seg fate-${cls}`} style={{ width: `${r[k]}%` }} /> : null,
                    )}
                  </span>
                  <small className="ca-thermo-read">
                    {r.relegatedPct >= 50
                      ? `${fmt(r.relegatedPct, 0)}% caíram`
                      : r.topPct + r.championPct >= 50
                        ? `${fmt(r.topPct + r.championPct, 0)}% no G-6${r.championPct > 0 ? ` (${fmt(r.championPct, 0)}% campeões)` : ""}`
                        : r.relegatedPct > 0
                          ? `${fmt(r.relegatedPct, 0)}% caíram`
                          : "ninguém caiu"}{" "}
                    · {r.peers} casos
                  </small>
                </>
              )}
            </span>
          </div>
        ))}
      </div>
      <p className="an-note">
        Não é previsão: o calendário que falta, os confrontos diretos e o elenco não entram na conta. É só o que aconteceu com
        quem estava no mesmo lugar.
      </p>
    </AnalysisCard>
  );
}
