import { useMemo } from "react";
import ScreenHeader from "./ScreenHeader";
import { aggregateStandings } from "../standings";
import { crestFor, displayClubName, displayRefereeName } from "../nameFormat";

const KPI_GLOWS = [
  "oklch(52% 0.12 195 / 0.14)",
  "oklch(58% 0.15 30 / 0.14)",
  "oklch(48% 0.13 145 / 0.14)",
  "oklch(45% 0.13 60 / 0.14)",
];

export default function DashboardTab({ season, seasons, onChangeSeason, heatmap, overview, loading }) {
  const teams = useMemo(() => [...new Set(heatmap.map((r) => r.team))].sort(), [heatmap]);
  const standings = useMemo(() => aggregateStandings(heatmap, teams), [heatmap, teams]);
  const preview = useMemo(() => {
    const top = standings.slice(0, 5);
    const extra = standings[11]; // posicao 12, igual ao mock
    return extra ? [...top, extra] : top;
  }, [standings]);

  const kpis = overview
    ? [
        { label: "Rodada", value: overview.currentRound || "—", sub: `${overview.gamesPlayed} jogos disputados` },
        { label: "Cartões por jogo", value: overview.cardsPerGame.toFixed(2), sub: "média da temporada" },
        { label: "Aproveitamento do mandante", value: `${overview.homeWinPct}%`, sub: "vitórias em casa" },
        { label: "Gols por jogo", value: overview.goalsPerGame.toFixed(2), sub: "média da temporada" },
      ]
    : [];

  return (
    <div className="screen">
      <ScreenHeader
        title="Visão da temporada"
        subtitle={`Painel geral · Série A ${season}`}
        statusLabel={overview?.currentRound ? `Rodada ${overview.currentRound} · em andamento` : undefined}
        season={season}
        seasons={seasons}
        onChangeSeason={onChangeSeason}
      />

      {loading || !overview ? (
        <p>Carregando…</p>
      ) : overview.gamesPlayed === 0 ? (
        <p className="hint">Sem dado real ainda pra essa temporada.</p>
      ) : (
        <>
          <div className="kpi-grid-v2">
            {kpis.map((k, i) => (
              <div key={k.label} className="kpi-card-v2" style={{ boxShadow: `0 6px 20px ${KPI_GLOWS[i]}`, animationDelay: `${i * 0.05}s` }}>
                <div className="kpi-label-v2">{k.label}</div>
                <div className="kpi-value-v2">{k.value}</div>
                <div className="kpi-sub-v2">{k.sub}</div>
              </div>
            ))}
          </div>

          <div className="dashboard-columns">
            <div className="card-v2 card-teal">
              <div className="card-header-dashed teal">
                <span>Prévia da classificação</span>
              </div>
              <div className="preview-rows">
                {preview.map((r, i) => {
                  const crest = crestFor(r.team, standings.indexOf(r));
                  return (
                    <div className="preview-row" key={r.team}>
                      <div className="preview-pos">{standings.indexOf(r) + 1}</div>
                      <div className="preview-club">
                        <span className="crest" style={{ background: crest.background }}>{crest.initials}</span>
                        <span title={r.team} className="truncate">{displayClubName(r.team)}</span>
                      </div>
                      <div className="preview-pts">{r.points}</div>
                      <div className="preview-j">{r.n}j</div>
                      <div className="preview-sg" style={{ color: r.goalDiff >= 0 ? "var(--positive)" : "var(--negative)" }}>
                        {r.goalDiff > 0 ? `+${r.goalDiff}` : r.goalDiff}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="card-footnote">Mostrando {preview.length} de {standings.length} posições — tabela completa com os {standings.length} clubes, zonas e histórico de forma na aba Classificação.</div>
            </div>

            <div className="dashboard-side">
              <div className="card-v2 card-coral">
                <div className="card-header-dashed coral">
                  <span>Árbitros que mais punem</span>
                </div>
                <p className="editorial-note">
                  Padrão estatístico ao longo de várias partidas — não é veredito sobre uma
                  decisão isolada. Sem ranking de medalhas de propósito: não é uma competição
                  a se comemorar.
                </p>
                {overview.mostCardsReferees.length === 0 && (
                  <p className="hint">Sem árbitro com jogos suficientes ainda nesta temporada.</p>
                )}
                {overview.mostCardsReferees.map((ref) => (
                  <div className="referee-bar-row" key={ref.name}>
                    <div className="referee-bar-head">
                      <span title={ref.name} className="truncate">{displayRefereeName(ref.name)}</span>
                      <span className="mono-strong">{ref.cardsPerGame.toFixed(2)}</span>
                    </div>
                    <div className="referee-bar-track">
                      <div className="referee-bar-fill" style={{ width: `${ref.barPct}%` }} />
                    </div>
                    <div className="referee-bar-games">{ref.games} jogos</div>
                  </div>
                ))}
              </div>

              <div className="card-v2 card-teal">
                <div className="card-header-dashed teal small">
                  <span>Viés de mandante</span>
                </div>
                <p className="editorial-note">Diferença de cartões, casa vs. visitante — negativo significa que o visitante recebe mais.</p>
                {overview.homeBiasReferees.length === 0 && (
                  <p className="hint">Sem árbitro com jogos suficientes ainda nesta temporada.</p>
                )}
                {overview.homeBiasReferees.map((ref) => (
                  <div className="bias-row" key={ref.name}>
                    <span title={ref.name} className="truncate">{displayRefereeName(ref.name)}</span>
                    <span className="bias-pill">{ref.bias.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
