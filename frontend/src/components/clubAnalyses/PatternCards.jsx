import { displayClubName } from "../../nameFormat";
import EvidenceChip from "../stats/EvidenceChip";
import { fmt, fmtSigned } from "../stats/format";
import { AnalysisCard, CompareBar, Empty, Legend, StatTile } from "../analyses/ui";
import { FATES, HOW } from "./copy";
import { niceMax, nextYear, promotedFates, turnoReturno } from "./derive";

const posLeft = (p) => `${((p - 1) / 19) * 100}%`;

function PositionAxis() {
  return (
    <div className="ca-pos-axis" aria-hidden="true">
      {[1, 4, 6, 10, 16, 20].map((p) => (
        <span key={p} style={{ left: posLeft(p) }}>
          {p}º
        </span>
      ))}
    </div>
  );
}

// ------------------------------------------------------------ promovidos
export function PromotedCard({ closed, highlight }) {
  const rows = promotedFates(closed);
  if (!rows.length) {
    return (
      <AnalysisCard className="span-6" title="Quem sobe, fica?" how={{ copy: HOW.promoted }}>
        <Empty>Precisa de duas temporadas seguidas no banco.</Empty>
      </AnalysisCard>
    );
  }
  const down = rows.filter((r) => r.fate === "relegated");
  const top = rows.filter((r) => r.fate === "top6" || r.fate === "champion");
  return (
    <AnalysisCard
      className="span-6"
      title="Quem sobe, fica?"
      subtitle={`Onde terminaram os ${rows.length} clubes que chegaram da Série B desde ${Math.min(...rows.map((r) => r.season))}.`}
      how={{ copy: HOW.promoted }}
    >
      <p className="an-headline">
        <b>
          {down.length} de {rows.length}
        </b>{" "}
        caíram no mesmo ano — cerca de 1 em cada {fmt(rows.length / Math.max(down.length, 1), 0)}.
        {top.length > 0 && (
          <>
            {" "}
            E {top.length === 1 ? "um chegou" : `${top.length} chegaram`} ao G-6:{" "}
            {top.map((r) => `${displayClubName(r.team)} ${r.season} (${r.position}º)`).join(", ")}.
          </>
        )}
      </p>
      <div className="ca-pos-strip" role="img" aria-label="Posição final de cada clube promovido">
        <span className="ca-pos-zone top" style={{ left: 0, width: posLeft(6.5) }} />
        <span className="ca-pos-zone down" style={{ left: posLeft(16.5), right: 0 }} />
        {rows.map((r, i) => (
          <span
            key={`${r.team}-${r.season}`}
            className={`ca-pos-dot fate-${r.fate}${highlight && r.team === highlight ? " is-mine" : ""}`}
            style={{ left: posLeft(r.position), "--level": rows.slice(0, i).filter((x) => x.position === r.position).length }}
            title={`${r.team} ${r.season}: ${r.position}º · ${FATES[r.fate]}`}
          />
        ))}
      </div>
      <PositionAxis />
      <p className="an-axis-unit">posição final no ano em que subiram</p>
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ ano seguinte
export function NextYearCard({ seasons }) {
  const ny = nextYear(seasons);
  return (
    <AnalysisCard
      className="span-6"
      title="Do topo ao fundo em um ano"
      subtitle="O que acontece no ano seguinte com quem brilhou — e o quanto os pontos de um ano preveem os do outro."
      how={{ copy: HOW.nextYear }}
    >
      {ny.falls.length > 0 && (
        <p className="an-headline">
          {ny.falls.length === 1 ? "Um clube foi" : `${ny.falls.length} clubes foram`} do G-6 ao rebaixamento na temporada seguinte:{" "}
          <b>{ny.falls.map((f) => `${displayClubName(f.team)} (${f.from}º em ${f.season}, ${f.to}º em ${f.season + 1})`).join(" e ")}</b>.
        </p>
      )}
      <div className="ca-champs">
        <span className="ca-champs-head">Campeão no ano seguinte</span>
        {ny.champions.map((c) => (
          <div className="ca-champ-row" key={c.season} title={`${c.team}: campeão em ${c.season}, ${c.next ? `${c.next}º` : "fora"} em ${c.season + 1}`}>
            <span className="ca-champ-label">
              {c.season} <b>{displayClubName(c.team)}</b>
            </span>
            <span className="ca-champ-track">
              <span className="ca-champ-from" style={{ left: posLeft(1) }} />
              {c.next && <span className="ca-champ-seg" style={{ left: posLeft(1), width: posLeft(c.next) }} />}
              {c.next && (
                <span className={`ca-champ-to${c.nextComplete ? "" : " is-open"}`} style={{ left: posLeft(c.next) }}>
                  <em>
                    {c.next}º{c.nextComplete ? "" : "*"}
                  </em>
                </span>
              )}
            </span>
          </div>
        ))}
        <PositionAxis />
      </div>
      {ny.champions.some((c) => !c.nextComplete) && <p className="an-note">* temporada em andamento, posição de hoje.</p>}
      {ny.correlation != null && (
        <p className="an-note">
          Pontos de um ano × pontos do seguinte: correlação de <b>{fmt(ny.correlation, 2)}</b> ({ny.pairs} casos). Ano
          muito acima (ou abaixo) do normal costuma voltar ao meio no seguinte.
        </p>
      )}
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ turno x returno
export function TurnoCard({ closed, highlight }) {
  const rows = turnoReturno(closed);
  if (!rows.length) {
    return (
      <AnalysisCard className="span-7" title="Existe “time de returno”?" how={{ copy: HOW.turno }}>
        <Empty>Precisa de clubes com 5 ou mais temporadas completas.</Empty>
      </AnalysisCard>
    );
  }
  const dom = Math.ceil(Math.max(...rows.flatMap((r) => r.rows.map((x) => Math.abs(x.diff))), 5) / 5) * 5;
  const pos = (v) => `${50 + (v / dom) * 50}%`;
  const patterns = rows.filter((r) => r.p < 0.05);
  const strongest = [...rows].sort((a, b) => Math.max(b.better, b.worse) / (b.better + b.worse || 1) - Math.max(a.better, a.worse) / (a.better + a.worse || 1))[0];
  return (
    <AnalysisCard
      className="span-7"
      title="Existe “time de returno”?"
      subtitle="Pontos no returno menos pontos no turno, em cada temporada. À direita do meio, o clube cresceu na segunda metade."
      how={{ copy: HOW.turno }}
    >
      <p className="an-headline">
        {patterns.length === 0 ? (
          <>
            Nenhum clube cresce (ou some) no returno de forma que o acaso não explique.{" "}
            {strongest && (
              <>
                O caso mais “consistente” — {displayClubName(strongest.team)},{" "}
                {strongest.better >= strongest.worse ? "melhor" : "pior"} no returno em{" "}
                {Math.max(strongest.better, strongest.worse)} de {strongest.rows.length} anos — ainda cabe no cara ou coroa.
              </>
            )}
          </>
        ) : (
          <>
            Padrão que passa no teste: {patterns.map((p) => `${displayClubName(p.team)} (${p.better >= p.worse ? "melhor" : "pior"} em ${Math.max(p.better, p.worse)} de ${p.rows.length})`).join(", ")}.
          </>
        )}
      </p>
      <Legend
        items={[
          ["less", "Returno melhor"],
          ["more", "Returno pior"],
        ]}
      />
      <div className="ca-turno">
        <div className="ca-turno-row is-head" aria-hidden="true">
          <span />
          <span className="ca-turno-scale">
            <span style={{ left: "0%" }}>−{dom}</span>
            <span style={{ left: "50%" }}>0</span>
            <span style={{ left: "100%" }}>+{dom}</span>
          </span>
          <span />
        </div>
        {rows.map((r) => (
          <div className={`ca-turno-row${highlight === r.team ? " is-highlight" : ""}`} key={r.team}>
            <span className="ca-turno-name" title={r.team}>
              {displayClubName(r.team)}
            </span>
            <span className="ca-turno-track">
              {r.rows.map((x) => (
                <span
                  key={x.season}
                  className={`ca-turno-dot ${x.diff > 0 ? "up" : x.diff < 0 ? "down" : "flat"}`}
                  style={{ left: pos(x.diff) }}
                  title={`${r.team} ${x.season}: returno ${fmtSigned(x.diff, 0)} pontos em relação ao turno`}
                />
              ))}
            </span>
            <span className="ca-turno-count">
              <b>
                {r.better}–{r.worse}
              </b>
              <EvidenceChip level={r.p < 0.05 ? "fraco" : "acaso"}>{r.p < 0.05 ? "Padrão" : "Pode ser acaso"}</EvidenceChip>
            </span>
          </div>
        ))}
      </div>
      <p className="an-axis-unit">pontos a mais (ou a menos) no returno · placar = anos melhor–pior</p>
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ primeiro gol
function ComebackRow({ r, max, highlight }) {
  return (
    <CompareBar
      label={displayClubName(r.team)}
      value={r.pointsPerGame}
      max={max}
      tone={highlight === r.team ? "chance" : "found"}
      text={fmt(r.pointsPerGame, 2)}
      title={`${r.team}: ${fmt(r.pointsPerGame, 2)} pontos por jogo em ${r.games} jogos saindo atrás · ${r.wins} viradas`}
    />
  );
}

export function FirstGoalCard({ data, highlight }) {
  const fg = data.firstGoal;
  const ranking = data.comebacks.filter((c) => c.games >= 60);
  const pct = (a, b) => (b ? (a / b) * 100 : 0);
  const top = ranking.slice(0, 5);
  const bottom = ranking.slice(-3);
  const max = niceMax(Math.max(...ranking.map((r) => r.pointsPerGame), 0.5));
  const mine = highlight && ranking.find((r) => r.team === highlight);
  const comeback = 100 - pct(fg.firstWins + fg.firstDraws, fg.games);
  return (
    <AnalysisCard
      className="span-5"
      title="O peso do primeiro gol"
      subtitle="O que acontece depois que alguém abre o placar — e quem mais reage quando sofre primeiro."
      how={{ copy: HOW.firstGoal }}
    >
      <div className="an-tiles-3 ca-tiles-2">
        <StatTile label="Quem marca primeiro vence" value={`${fmt(pct(fg.firstWins, fg.games), 0)}%`} sub={`dos ${fmt(fg.games, 0)} jogos com gol`} />
        <StatTile
          label="Virada (sofre o 1º e vence)"
          value={`${fmt(comeback, 0)}%`}
          sub={`cerca de 1 jogo em cada ${fmt(100 / Math.max(comeback, 1), 0)}`}
        />
      </div>
      <p className="an-note">
        Saindo na frente, o mandante vence {fmt(pct(fg.homeFirstWins, fg.homeFirst), 0)}% das vezes; o visitante,{" "}
        {fmt(pct(fg.awayFirstWins, fg.awayFirst), 0)}%.
      </p>
      <span className="ca-sub-head">Pontos por jogo depois de sofrer o primeiro gol</span>
      <div className="an-cbars">
        {top.map((r) => (
          <ComebackRow key={r.team} r={r} max={max} highlight={highlight} />
        ))}
        {mine && !top.includes(mine) && !bottom.includes(mine) && <ComebackRow r={mine} max={max} highlight={highlight} />}
        <span className="ca-gap" aria-hidden="true">⋯</span>
        {bottom.map((r) => (
          <ComebackRow key={r.team} r={r} max={max} highlight={highlight} />
        ))}
      </div>
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ o campeonato mudou
export function TrendsCard({ seasons }) {
  const metrics = [
    ["goalsPerGame", "Gols por jogo", (v) => fmt(v, 2)],
    ["zeroZeroPct", "0 x 0", (v) => `${fmt(v, 0)}%`],
    ["homeWinPct", "Vitória do mandante", (v) => `${fmt(v, 0)}%`],
  ];
  const first = seasons[0];
  const last = seasons[seasons.length - 1];
  return (
    <AnalysisCard
      className="span-12"
      title="O campeonato mudou"
      subtitle={`Três medidas, temporada a temporada, de ${first.season} a ${last.season}${last.complete ? "" : " (em andamento)"}.`}
      how={{ copy: HOW.trends }}
    >
      <div className="ca-trends">
        {metrics.map(([key, label, f]) => {
          const max = Math.max(...seasons.map((s) => s[key]));
          return (
            <div className="ca-trend" key={key}>
              <span className="ca-trend-head">
                <b>{label}</b>
                <small>
                  {first.season}: {f(first[key])} → {last.season}: {f(last[key])}
                </small>
              </span>
              <span className="ca-trend-bars" role="img" aria-label={`${label} por temporada`}>
                {seasons.map((s) => (
                  <span key={s.season} className={`ca-trend-bar${s.complete ? "" : " is-open"}`} title={`${s.season}: ${f(s[key])}`}>
                    <span className="ca-trend-fill" style={{ height: `${(s[key] / max) * 100}%` }} />
                    <em>{String(s.season).slice(2)}</em>
                  </span>
                ))}
              </span>
            </div>
          );
        })}
      </div>
    </AnalysisCard>
  );
}
