import { displayClubName, displayRefereeName } from "../../nameFormat";
import { fmt } from "../stats/format";
import { PLAIN } from "./copy";
import { AlertIcon, CheckIcon, InfoIcon, StatTile } from "./ui";

const approx = (x) => fmt(x, x < 10 ? 1 : 0);

// A resposta curta, antes de qualquer grafico: tem ou nao tem sinal?
export default function HeroSummary({ report, filters, summary }) {
  const { team, referee } = filters;
  const { overview } = report;
  const club = team && displayClubName(team);
  const ref = referee && displayRefereeName(referee);
  const period = report.season
    ? `temporada ${report.season}`
    : `${Math.min(...report.seasons)} a ${Math.max(...report.seasons)}`;

  let tone = "ok";
  let headline;
  let body;
  if (summary.pairs === 0) {
    tone = "empty";
    headline = "Poucos jogos para comparar";
    body = `${club ?? ref ?? "Neste recorte"} não tem dupla árbitro × clube que se enfrentou ${overview.floor}+ vezes (${period}). Tente “Todas” as temporadas.`;
  } else if (summary.strong > 0) {
    tone = "alert";
    const n = `${summary.strong} ${summary.strong === 1 ? "sinal forte" : "sinais fortes"}`;
    headline = club || ref ? `${[club, ref].filter(Boolean).join(" com ")}: ${n}` : `${n} entre ${summary.pairs} duplas árbitro × clube`;
    body = "Difícil de explicar só com sorte. Merece investigação — ainda não é prova de favorecimento.";
  } else {
    if (club && ref) headline = `${club} com ${ref}: nenhum sinal forte`;
    else if (club) headline = `${club}: nenhum árbitro mostrou sinal forte de favorecimento ou perseguição`;
    else if (ref) headline = `${ref}: nenhum sinal forte de favorecer ou perseguir algum clube`;
    else headline = "Nenhuma dupla árbitro × clube mostrou sinal forte de favorecimento ou perseguição";
    body =
      `Somando as quatro perguntas, ${summary.outside} ${summary.outside === 1 ? "resultado ficou" : "resultados ficaram"} fora da faixa normal — ` +
      `o acaso sozinho produziria cerca de ${approx(summary.expectedOutside)}.`;
    if (summary.weak > 0) {
      body += ` ${summary.weak} ${summary.weak === 1 ? "caso fica" : "casos ficam"} para acompanhar.`;
    }
  }

  const filtered = Boolean(team || referee);
  return (
    <section className={`an-hero tone-${tone}`} aria-live="polite">
      <div className="an-hero-main">
        <span className="an-hero-icon" aria-hidden="true">
          {tone === "alert" ? <AlertIcon /> : tone === "ok" ? <CheckIcon /> : <InfoIcon />}
        </span>
        <div>
          <span className="an-eyebrow">A resposta curta · {period}</span>
          <h3 className="an-hero-title">{headline}</h3>
          <p className="an-hero-body">{body}</p>
        </div>
      </div>
      <div className="an-hero-tiles">
        {filtered ? (
          <StatTile label="Jogos dessas duplas" value={fmt(summary.games, 0)} sub={club && ref ? `${club} com ${ref}` : club ?? ref} />
        ) : (
          <StatTile label="Jogos analisados" value={fmt(overview.matches, 0)} sub={period} />
        )}
        <StatTile
          label={filtered ? "Duplas analisadas" : "Duplas árbitro × clube"}
          value={fmt(summary.pairs, 0)}
          sub={`que se enfrentaram ${overview.floor}+ vezes`}
        />
        <StatTile label="Sinais fortes" value={summary.strong} sub="nas quatro perguntas" tone={summary.strong > 0 ? "alert" : undefined} />
        <StatTile label="Para acompanhar" value={summary.weak} sub={`o acaso daria ~${approx(summary.expectedWeak)}`} />
      </div>
      <p className="an-hero-coin">
        <InfoIcon />
        <span>{PLAIN.coin}</span>
      </p>
    </section>
  );
}
