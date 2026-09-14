import { useEffect, useState } from "react";
import { getFilters, getDashboard, getSeasonOverview } from "./api";
import Sidebar from "./components/Sidebar";
import DashboardTab from "./components/DashboardTab";
import StandingsTab from "./components/StandingsTab";
import OverviewTab from "./components/OverviewTab";
import FavoritismTab from "./components/FavoritismTab";
import MatrixTab from "./components/MatrixTab";
import ScreenHeader from "./components/ScreenHeader";
import DataCompletenessBanner from "./components/DataCompletenessBanner";
import "./App.css";

export default function App() {
  const [options, setOptions] = useState({ teams: [], referees: [], seasons: [] });
  const [season, setSeason] = useState();
  const [team, setTeam] = useState();
  const [referee, setReferee] = useState();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);

  useEffect(() => {
    getFilters().then((opts) => {
      setOptions(opts);
      setSeason((s) => s ?? opts.seasons[opts.seasons.length - 1]);
    });
  }, []);

  useEffect(() => {
    if (!season) return;
    setLoading(true);
    getDashboard({ season, team, referee })
      .then(setDashboard)
      .finally(() => setLoading(false));
  }, [season, team, referee]);

  useEffect(() => {
    if (!season) return;
    setOverviewLoading(true);
    getSeasonOverview({ season })
      .then(setOverview)
      .finally(() => setOverviewLoading(false));
  }, [season]);

  function goToDetail({ team: t, referee: r }) {
    setTeam(t);
    setReferee(r);
    setActiveTab("detail");
  }

  // slicer dependente (estilo Power BI): so oferece arbitro que ja apitou
  // esse time (e vice-versa) -- evita escolher uma combinacao sem jogo.
  // Base sempre vem do heatmap da temporada selecionada (dashboard.heatmap
  // ja veio filtrado por season) -- nunca do options.* global, que lista
  // time/arbitro de todo ano ja ingerido (misturaria time rebaixado).
  const heatmapRows = dashboard?.heatmap || [];
  const seasonTeams = [...new Set(heatmapRows.map((r) => r.team))].sort();
  const seasonReferees = [...new Set(heatmapRows.map((r) => r.referee))].sort();
  const availableReferees = team
    ? [...new Set(heatmapRows.filter((r) => r.team === team).map((r) => r.referee))].sort()
    : seasonReferees.length
      ? seasonReferees
      : options.referees;
  const availableTeams = referee
    ? [...new Set(heatmapRows.filter((r) => r.referee === referee).map((r) => r.team))].sort()
    : seasonTeams.length
      ? seasonTeams
      : options.teams;

  function changeTeam(t) {
    setTeam(t);
    if (referee && t && !heatmapRows.some((r) => r.team === t && r.referee === referee)) {
      setReferee(undefined);
    }
  }

  function changeReferee(r) {
    setReferee(r);
    if (team && r && !heatmapRows.some((r2) => r2.team === team && r2.referee === r)) {
      setTeam(undefined);
    }
  }

  const dataBlurb = options.seasons.length
    ? `${options.referees.length} árbitros · ${options.seasons.length} temporadas`
    : undefined;

  return (
    <div className="app-shell">
      <Sidebar active={activeTab === "detail" ? null : activeTab} onChange={setActiveTab} dataBlurb={dataBlurb} />

      <main className="app-main">
        {!dashboard ? (
          <p className="loading-text">Carregando…</p>
        ) : (
          <>
            {activeTab === "dashboard" && (
              <DashboardTab
                season={season}
                seasons={options.seasons}
                onChangeSeason={setSeason}
                heatmap={heatmapRows}
                overview={overview}
                loading={overviewLoading}
              />
            )}

            {activeTab === "classificacao" && (
              <StandingsTab season={season} seasons={options.seasons} onChangeSeason={setSeason} rows={heatmapRows} />
            )}

            {activeTab === "confrontos" && (
              <div className="screen">
                <ScreenHeader
                  title="Confrontos"
                  subtitle="Matriz clube × árbitro — Índice de Favorecimento"
                  season={season}
                  seasons={options.seasons}
                  onChangeSeason={setSeason}
                />
                <FavoritismTab seasons={options.seasons} onSelect={goToDetail} />
              </div>
            )}

            {activeTab === "clubes" && (
              <div className="screen">
                <ScreenHeader
                  title="Clubes"
                  subtitle="Indicadores por clube × árbitro"
                  season={season}
                  seasons={options.seasons}
                  onChangeSeason={setSeason}
                />
                <MatrixTab rows={heatmapRows} onSelect={goToDetail} />
              </div>
            )}

            {activeTab === "arbitros" && (
              <div className="screen">
                <ScreenHeader
                  title="Árbitros"
                  subtitle={`Ranking por rigor — Série A ${season} · ${overview?.allReferees?.length ?? 0} árbitros com amostra suficiente`}
                  season={season}
                  seasons={options.seasons}
                  onChangeSeason={setSeason}
                />
                {overviewLoading || !overview ? (
                  <p>Carregando…</p>
                ) : overview.allReferees.length === 0 ? (
                  <p className="hint">Sem árbitro com jogos suficientes ainda nesta temporada.</p>
                ) : (
                  <div className="referee-list-table">
                    <div className="referee-list-header">
                      <div>Árbitro</div><div className="num">Jogos</div><div className="num">Cartões/jogo</div><div className="num">Viés de mandante</div>
                    </div>
                    {overview.allReferees.map((ref) => (
                      <div className="referee-list-row" key={ref.name}>
                        <div title={ref.name} className="truncate">{ref.name}</div>
                        <div className="num mono">{ref.games}</div>
                        <div className="num mono-strong">{ref.cardsPerGame.toFixed(2)}</div>
                        <div className="num mono">{ref.bias.toFixed(2)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "detail" && (
              <div className="screen">
                <button type="button" className="back-link" onClick={() => setActiveTab("dashboard")}>← Voltar</button>
                <ScreenHeader
                  title="Visão Geral"
                  subtitle="Detalhe do recorte selecionado"
                  season={season}
                  seasons={options.seasons}
                  onChangeSeason={setSeason}
                />
                {loading ? (
                  <p>Carregando…</p>
                ) : (
                  <OverviewTab
                    options={{ teams: availableTeams, referees: availableReferees }}
                    team={team}
                    referee={referee}
                    onChangeTeam={changeTeam}
                    onChangeReferee={changeReferee}
                    kpis={dashboard.kpis}
                    timeseries={dashboard.timeseries}
                  />
                )}
              </div>
            )}

            <DataCompletenessBanner completeness={dashboard.dataCompleteness} />
          </>
        )}
      </main>
    </div>
  );
}
