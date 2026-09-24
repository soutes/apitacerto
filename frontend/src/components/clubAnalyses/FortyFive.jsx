import { displayClubName } from "../../nameFormat";
import { AnalysisCard, Legend } from "../analyses/ui";
import { HOW } from "./copy";
import { relegationLine } from "./derive";

// "A lenda dos 45 pontos": em cada temporada, o ultimo que escapou (16o) e
// o primeiro que caiu (17o).
export default function FortyFive({ closed }) {
  const rows = relegationLine(closed);
  const maxDown = Math.max(...rows.map((r) => r.firstDown.points));
  const minSafe = Math.min(...rows.map((r) => r.lastSafe.points));
  const maxDownWho = rows.filter((r) => r.firstDown.points === maxDown);
  const minSafeWho = rows.filter((r) => r.lastSafe.points === minSafe);
  const lo = Math.floor((Math.min(...rows.map((r) => r.firstDown.points)) - 2) / 5) * 5;
  const hi = Math.max(46, ...rows.map((r) => r.lastSafe.points)) + 2;
  const pos = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
  const ticks = [];
  for (let t = Math.ceil(lo / 5) * 5; t <= hi; t += 5) ticks.push(t);
  return (
    <AnalysisCard
      className="span-5"
      title="A lenda dos 45 pontos"
      subtitle="Pontos finais do último clube que escapou (16º) e do primeiro que caiu (17º), ano a ano."
      how={{ copy: HOW.fortyFive }}
    >
      <p className="an-headline">
        Nunca caiu quem fez <b>{maxDown + 1} pontos ou mais</b>: o rebaixado com mais pontos fez {maxDown} (
        {maxDownWho.map((r) => `${displayClubName(r.firstDown.team)} ${r.season}`).join(", ")}). E já deu para escapar com{" "}
        <b>{minSafe}</b> ({minSafeWho.map((r) => `${displayClubName(r.lastSafe.team)} ${r.season}`).join(", ")}).
      </p>
      <Legend
        items={[
          ["less", "16º (último que escapou)"],
          ["more", "17º (primeiro que caiu)"],
        ]}
      />
      <div className="ca-dumbbells">
        <div className="ca-db-axis" aria-hidden="true">
          <span />
          <span className="ca-db-ticks">
            {ticks.map((t) => (
              <span key={t} style={{ left: pos(t) }}>
                {t}
              </span>
            ))}
          </span>
        </div>
        {rows.map((r) => (
          <div className="ca-db-row" key={r.season} title={`${r.season}: 16º ${r.lastSafe.team} ${r.lastSafe.points} pts · 17º ${r.firstDown.team} ${r.firstDown.points} pts`}>
            <span className="ca-db-label">{r.season}</span>
            <span className="ca-db-track">
              <span className="ca-db-ref" style={{ left: pos(45) }} />
              <span className="ca-db-seg" style={{ left: pos(r.firstDown.points), width: `calc(${pos(r.lastSafe.points)} - ${pos(r.firstDown.points)})` }} />
              <span className="ca-db-dot down" style={{ left: pos(r.firstDown.points) }}>
                {r.firstDown.points !== r.lastSafe.points && <em>{r.firstDown.points}</em>}
              </span>
              <span className="ca-db-dot safe" style={{ left: pos(r.lastSafe.points) }}>
                <em>{r.lastSafe.points}</em>
              </span>
            </span>
          </div>
        ))}
      </div>
      <p className="an-axis-unit">pontos no fim do campeonato · linha fina = 45 pontos</p>
    </AnalysisCard>
  );
}
