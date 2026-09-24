import { useEffect, useState } from "react";
import { getStatistics } from "../../api";
import AnalysesFooter from "./AnalysesFooter";
import ChanceScoreboard from "./ChanceScoreboard";
import { filterOptions, overallSummary } from "./derive";
import FilterBar from "./FilterBar";
import HeroSummary from "./HeroSummary";
import HomeAdvantage from "./HomeAdvantage";
import HypothesisCards from "./HypothesisCards";
import PairExplorer from "./PairExplorer";
import RefereeRigor from "./RefereeRigor";
import RepeatCard from "./RepeatCard";
import { CategoryCard, ConcentrationCard, FederationCard } from "./SchedulingCards";
import { Empty } from "./ui";
import "../stats/stats.css";
import "./analyses.css";

function Section({ eyebrow, title, children }) {
  return (
    <header className="an-section">
      <span className="an-eyebrow">{eyebrow}</span>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </header>
  );
}

// Aba Analises (antes "Favorecimento", spec secao 9): painel amigavel em
// cima do relatorio pre-calculado. Cada grafico tem "Como foi criado" com o
// metodo e os numeros completos; o rodape junta o que vale para todos.
export default function AnalysesTab({ seasons }) {
  const [season, setSeason] = useState(); // undefined = todas as temporadas
  const [team, setTeam] = useState();
  const [referee, setReferee] = useState();
  const [metric, setMetric] = useState("cards");
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("loading");

  // status "loading" e marcado em changeSeason (evento), nao no efeito
  useEffect(() => {
    let cancelled = false;
    getStatistics({ season })
      .then((r) => {
        if (cancelled) return;
        setReport(r);
        setStatus(r ? "ready" : "missing");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [season]);

  // Clube/arbitro que nao existe no recorte novo (ex.: rebaixado) deixa de
  // filtrar, sem apagar a escolha -- volta se o recorte voltar.
  const all = report ? filterOptions(report, {}) : { teams: [], referees: [] };
  const filters = {
    team: all.teams.includes(team) ? team : undefined,
    referee: all.referees.includes(referee) ? referee : undefined,
  };
  const options = report ? filterOptions(report, filters) : all;
  const filtered = Boolean(filters.team || filters.referee);
  const leagueTag = filtered ? "Liga toda" : undefined;

  const computedAt = report?.computedAt
    ? new Date(report.computedAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : null;

  function changeSeason(s) {
    setSeason(s);
    setStatus("loading");
  }

  function pickMetric(key) {
    setMetric(key);
    const el = document.getElementById("an-explorer");
    if (el && el.getBoundingClientRect().top > window.innerHeight * 0.6) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  const summary = report ? overallSummary(report, filters) : null;

  return (
    <div className="an-tab">
      <FilterBar
        seasons={seasons}
        partialSeasons={report?.partialSeasons ?? []}
        season={season}
        onSeason={changeSeason}
        options={options}
        team={filters.team}
        referee={filters.referee}
        onTeam={setTeam}
        onReferee={setReferee}
        computedAt={status === "ready" ? computedAt : null}
      />

      {status === "loading" && !report && <p className="loading-text">Carregando…</p>}
      {status === "missing" && <Empty>As análises desta temporada ainda não foram calculadas. Tente “Todas”.</Empty>}
      {status === "error" && <Empty>Não foi possível carregar as análises agora. Tente de novo em instantes.</Empty>}

      {report && (status === "ready" || status === "loading") && (
        <div className={`an-body${status === "loading" ? " is-refreshing" : ""}`} aria-busy={status === "loading"}>
          <HeroSummary report={report} filters={filters} summary={summary} />

          <Section eyebrow="Árbitro × clube" title="Algum árbitro favorece ou persegue um clube?">
            Quatro jeitos de um árbitro ajudar ou atrapalhar um clube. Cada dupla é comparada com o que se esperaria dos jogos que
            ela teve.
          </Section>
          <div className="an-grid">
            <ChanceScoreboard report={report} summary={summary} metric={metric} onPickMetric={pickMetric} />
            <PairExplorer report={report} filters={filters} metric={metric} onMetric={setMetric} />
          </div>

          <Section eyebrow="A régua" title="O que já é normal no campeonato">
            Antes de olhar para uma dupla, o estilo de cada árbitro e a vantagem de jogar em casa.
          </Section>
          <div className="an-grid">
            <RefereeRigor data={report.refereeStrictness} highlight={filters.referee} tag={leagueTag} />
            <HomeAdvantage league={report.league} selected={report.season} tag={leagueTag} />
          </div>

          <Section eyebrow="A escala da CBF" title="Quem apita o quê">
            Quem escolhe o árbitro de cada jogo é a CBF, e a escala tem regras. Isso muda o que é “normal” para uma dupla.
          </Section>
          <div className="an-grid an-grid-3">
            <FederationCard fed={report.escala.federation} tag={leagueTag} />
            <CategoryCard cat={report.escala.category} tag={leagueTag} />
            <ConcentrationCard conc={report.escala.concentration} filters={filters} />
          </div>

          <Section eyebrow="Provas mais duras" title="Testes que não dependem de um jogo só" />
          <div className="an-grid">
            <RepeatCard data={report.crossSeason} filters={filters} />
            <HypothesisCards data={report.hypotheses} tag={leagueTag} />
          </div>

          <AnalysesFooter report={report} computedAt={computedAt} />
        </div>
      )}
    </div>
  );
}
