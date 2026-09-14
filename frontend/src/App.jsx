import { useEffect, useState } from "react";
import { getFilters, getDashboard } from "./api";
import SeasonPicker from "./components/SeasonPicker";
import Tabs from "./components/Tabs";
import OverviewTab from "./components/OverviewTab";
import FavoritismTab from "./components/FavoritismTab";
import MatrixTab from "./components/MatrixTab";
import StandingsTab from "./components/StandingsTab";
import DataCompletenessBanner from "./components/DataCompletenessBanner";
import "./App.css";

const TABS = [
  { key: "overview", label: "Visao Geral" },
  { key: "favoritism", label: "Indice de Favorecimento" },
  { key: "matrix", label: "Tabela Geral" },
  { key: "standings", label: "Classificacao" },
];

export default function App() {
  const [options, setOptions] = useState({ teams: [], referees: [], seasons: [] });
  const [season, setSeason] = useState();
  const [team, setTeam] = useState();
  const [referee, setReferee] = useState();
  const [activeTab, setActiveTab] = useState("overview");
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

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

  function selectFromMatrix({ team: t, referee: r }) {
    setTeam(t);
    setReferee(r);
    setActiveTab("overview");
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

  return (
    <div className="app">
      <header>
        <h1>ApitaCerto</h1>
        <p className="subtitle">
          Desempenho do Brasileirao Serie A segmentado por arbitro — sinalizacao de possivel favorecimento.
        </p>
      </header>

      <SeasonPicker seasons={options.seasons} value={season} onChange={setSeason} />

      <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {loading || !dashboard ? (
        <p>Carregando...</p>
      ) : (
        <div role="tabpanel" className="tab-panel">
          <DataCompletenessBanner completeness={dashboard.dataCompleteness} />
          {activeTab === "overview" && (
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
          {activeTab === "favoritism" && (
            <FavoritismTab seasons={options.seasons} onSelect={selectFromMatrix} />
          )}
          {activeTab === "matrix" && (
            <MatrixTab rows={dashboard.heatmap} onSelect={selectFromMatrix} />
          )}
          {activeTab === "standings" && <StandingsTab rows={dashboard.heatmap} />}
        </div>
      )}
    </div>
  );
}
