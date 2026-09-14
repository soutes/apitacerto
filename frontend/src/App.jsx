import { useEffect, useState } from "react";
import { getFilters, getDashboard } from "./api";
import SeasonPicker from "./components/SeasonPicker";
import Tabs from "./components/Tabs";
import OverviewTab from "./components/OverviewTab";
import FavoritismTab from "./components/FavoritismTab";
import MatrixTab from "./components/MatrixTab";
import "./App.css";

const TABS = [
  { key: "overview", label: "Visao Geral" },
  { key: "favoritism", label: "Indice de Favorecimento" },
  { key: "matrix", label: "Tabela Geral" },
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
          {activeTab === "overview" && (
            <OverviewTab
              options={options}
              team={team}
              referee={referee}
              onChangeTeam={setTeam}
              onChangeReferee={setReferee}
              kpis={dashboard.kpis}
              timeseries={dashboard.timeseries}
            />
          )}
          {activeTab === "favoritism" && (
            <FavoritismTab rows={dashboard.heatmap} onSelect={selectFromMatrix} />
          )}
          {activeTab === "matrix" && (
            <MatrixTab rows={dashboard.heatmap} onSelect={selectFromMatrix} />
          )}
        </div>
      )}
    </div>
  );
}
