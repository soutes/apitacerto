import { useEffect, useState } from "react";
import { getClubInsights, getProjection } from "../../api";
import { displayClubName } from "../../nameFormat";
import { fmt } from "../stats/format";
import { AlertIcon, CheckIcon, Empty, StatTile } from "../analyses/ui";
import CutoffStrip from "./CutoffStrip";
import FortyFive from "./FortyFive";
import LeaderCurve from "./LeaderCurve";
import { FirstGoalCard, NextYearCard, PromotedCard, TrendsCard, TurnoCard } from "./PatternCards";
import Thermometer from "./Thermometer";
import { EvolutionChart, PositionHeatmap, ProjectionHero, ProjectionTable, TrustCard } from "./ProjectionCards";
import { closedSeasons, currentSeason, cutoffs, gamesPlayed, pointsAt, roundRates } from "./derive";
import "../stats/stats.css";
import "../analyses/analyses.css";
import "./clubAnalyses.css";

function Section({ eyebrow, title, children }) {
  return (
    <header className="an-section">
      <span className="an-eyebrow">{eyebrow}</span>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </header>
  );
}

function Hero({ closed, current, round }) {
  const cut = cutoffs(closed, round);
  const rate = roundRates(closed)[round - 1];
  const seasons = closed.length;
  const below = current
    ? current.teams.filter((t) => pointsAt(t, round) != null && cut.safeMin && pointsAt(t, round) < cut.safeMin.points)
    : [];
  const first = Math.min(...closed.map((s) => s.season));
  const alert = below.length > 0;
  return (
    <section className={`an-hero tone-${alert ? "alert" : "ok"}`} aria-live="polite">
      <div className="an-hero-main">
        <span className="an-hero-icon" aria-hidden="true">
          {alert ? <AlertIcon /> : <CheckIcon />}
        </span>
        <div>
          <span className="an-eyebrow">
            Depois de {round} jogos · {seasons} temporadas completas ({first} em diante)
          </span>
          <h3 className="an-hero-title">
            {cut.safeMin && cut.relegatedMax
              ? `Ninguém com menos de ${cut.safeMin.points} pontos escapou da queda. Ninguém com mais de ${cut.relegatedMax.points} caiu.`
              : "A tabela desta rodada"}
          </h3>
          <p className="an-hero-body">
            {alert ? (
              <>
                Em {current.season}, {below.map((t) => `${displayClubName(t.team)} (${pointsAt(t, round)})`).join(" e ")}{" "}
                {below.length === 1 ? "está" : "estão"} abaixo da linha: para escapar, {below.length === 1 ? "precisa" : "precisam"} fazer o
                que nenhum clube fez desde {first}.
              </>
            ) : (
              <>A linha muda a cada rodada: mova o controle acima para ver quando cada destino começa a ficar decidido.</>
            )}
          </p>
        </div>
      </div>
      <div className="an-hero-tiles">
        <StatTile label="Ninguém escapou com menos de" value={cut.safeMin ? `${cut.safeMin.points} pts` : "—"} sub={`depois de ${round} jogos`} tone={alert ? "alert" : undefined} />
        <StatTile label="Ninguém caiu com mais de" value={cut.relegatedMax ? `${cut.relegatedMax.points} pts` : "—"} sub={`depois de ${round} jogos`} />
        <StatTile label="G-6: ninguém chegou com menos de" value={cut.topMin ? `${cut.topMin.points} pts` : "—"} sub="a faixa que costuma dar Libertadores" />
        <StatTile
          label="O líder desta rodada foi campeão"
          value={`${fmt((rate.leader / 100) * seasons, rate.leader % 12.5 ? 1 : 0)} de ${seasons}`}
          sub="temporadas"
        />
      </div>
    </section>
  );
}

function ClubFooter({ closed, current }) {
  const first = Math.min(...closed.map((s) => s.season));
  const last = Math.max(...closed.map((s) => s.season));
  return (
    <footer className="an-footer" aria-label="Sobre estas análises">
      <div className="an-footer-col">
        <h4>O que é “rodada” aqui</h4>
        <p>
          Depois de R jogos do próprio clube, em ordem de data. Jogo adiado entra quando é jogado — assim todo mundo é
          comparado com o mesmo número de partidas.
        </p>
      </div>
      <div className="an-footer-col">
        <h4>“Nunca” desde quando</h4>
        <p>
          Desde {first}: são {closed.length} temporadas completas ({first}–{last}). Um recorde de {closed.length} anos pode cair no
          próximo — leia “nunca” como “nunca até agora”.
        </p>
      </div>
      <div className="an-footer-col">
        <h4>G-6 e Libertadores</h4>
        <p>
          G-6 (1º ao 6º) é a faixa que costuma dar vaga na Libertadores, direta ou na fase prévia. O número exato de vagas
          muda de ano para ano com os campeões de outras competições.
        </p>
      </div>
      <div className="an-footer-col">
        <h4>De onde vêm os números</h4>
        <p>
          Placares oficiais da CBF. Classificação com os critérios de desempate da CBF: pontos, vitórias, saldo e gols pró.
          {current && ` Temporada ${current.season} em andamento: entra no termômetro, não nas linhas de corte.`}
        </p>
      </div>
    </footer>
  );
}

// Aba Analises dos clubes: o que a tabela da rodada conta sobre o fim do
// campeonato e os padroes de campanha que se repetem (ou nao) entre anos.
export default function ClubAnalysesTab() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  const [round, setRound] = useState(null);
  const [club, setClub] = useState("");
  const [proj, setProj] = useState(null);

  useEffect(() => {
    let cancelled = false;
    // projecao e opcional: sem ela (ainda nao calculada) a aba segue normal
    getProjection()
      .then((p) => !cancelled && setProj(p))
      .catch(() => {});
    getClubInsights()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") return <p className="loading-text">Carregando…</p>;
  if (status === "error") return <Empty>Não foi possível carregar as análises dos clubes agora.</Empty>;

  const closed = closedSeasons(data);
  if (!closed.length) return <Empty>Ainda não há temporada completa para comparar.</Empty>;
  const current = currentSeason(data);
  const nowGames = current ? Math.min(...current.teams.map(gamesPlayed)) : null;
  const r = round ?? nowGames ?? 19;
  const clubs = [...new Set(data.seasons.flatMap((s) => s.teams.map((t) => t.team)))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const presets = [
    [10, "10"],
    [19, "19 · fim do turno"],
    ...(nowGames ? [[nowGames, `${nowGames} · hoje`]] : []),
    [30, "30"],
    [34, "34"],
  ].filter(([v], i, arr) => arr.findIndex(([w]) => w === v) === i);

  return (
    <div className="an-tab ca-tab">
      <div className="an-filters ca-filters" role="search" aria-label="Controles da análise">
        <label className="an-filter ca-round">
          <span>
            Rodada (jogos disputados): <b>{r}</b>
          </span>
          <input type="range" min={1} max={38} value={r} onChange={(e) => setRound(Number(e.target.value))} aria-valuetext={`${r} jogos`} />
        </label>
        <div className="ca-presets" role="group" aria-label="Atalhos de rodada">
          {presets.map(([v, label]) => (
            <button key={v} type="button" aria-pressed={r === v} className={r === v ? "is-active" : undefined} onClick={() => setRound(v)}>
              {label}
            </button>
          ))}
        </div>
        <label className="an-filter">
          <span>Destacar clube</span>
          <select value={club} onChange={(e) => setClub(e.target.value)}>
            <option value="">Nenhum</option>
            {clubs.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="an-body">
        {proj && (
          <>
            <Section eyebrow={`Projeção ${proj.season}`} title="Como deve terminar o campeonato">
              {fmt(proj.sims, 0)} simulações dos jogos que faltam, com a força de cada time medida em todos os jogos desde
              2007 (os recentes pesam mais) e o mando de campo de cada partida.
            </Section>
            <ProjectionHero proj={proj} />
            <div className="an-grid">
              <ProjectionTable proj={proj} highlight={club} />
              <EvolutionChart proj={proj} highlight={club} />
              <PositionHeatmap proj={proj} highlight={club} />
              <TrustCard proj={proj} />
            </div>
            <Section eyebrow="A tabela da rodada" title="O que a pontuação de hoje já disse no passado" />
          </>
        )}
        <Hero closed={closed} current={current} round={r} />

        <Section eyebrow="A tabela da rodada" title="Com esses pontos, dá para respirar?">
          Cada temporada completa desde {Math.min(...closed.map((s) => s.season))}, empilhada pelos pontos que o clube tinha
          na rodada escolhida e separada por como terminou.
        </Section>
        <div className="an-grid">
          <CutoffStrip closed={closed} current={current} round={r} highlight={club} />
          {current && <Thermometer closed={closed} current={current} highlight={club} />}
        </div>

        <Section eyebrow="Rodada a rodada" title="Quando o campeonato fica decidido" />
        <div className="an-grid">
          <LeaderCurve closed={closed} round={r} />
          <FortyFive closed={closed} />
        </div>

        <Section eyebrow="Padrões" title="O que se repete — e o que é só impressão">
          Rótulos como “time de returno” ou “rei da virada” testados contra o acaso.
        </Section>
        <div className="an-grid">
          <TurnoCard closed={closed} highlight={club} />
          <FirstGoalCard data={data} highlight={club} />
        </div>

        <Section eyebrow="De um ano para o outro" title="Subir, cair, repetir" />
        <div className="an-grid">
          <PromotedCard closed={closed} highlight={club} />
          <NextYearCard seasons={data.seasons} />
          <TrendsCard seasons={data.seasons} />
        </div>

        <ClubFooter closed={closed} current={current} />
      </div>
    </div>
  );
}
