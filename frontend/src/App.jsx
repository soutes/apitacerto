import { useEffect, useState } from "react";
import { getFilters, getDashboard } from "./api";
import Filters from "./components/Filters";
import KpiCards from "./components/KpiCards";
import WinRateLineChart from "./components/WinRateLineChart";
import CardsBarChart from "./components/CardsBarChart";
import FavoritismHeatmap from "./components/FavoritismHeatmap";
import "./App.css";

export default function App() {
  const [options, setOptions] = useState({ teams: [], referees: [], seasons: [] });
  const [filters, setFilters] = useState({});
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFilters().then((opts) => {
      setOptions(opts);
      setFilters((f) => ({ ...f, season: f.season ?? opts.seasons[opts.seasons.length - 1] }));
    });
  }, []);

  useEffect(() => {
    if (!filters.season) return;
    setLoading(true);
    getDashboard(filters)
      .then(setDashboard)
      .finally(() => setLoading(false));
  }, [filters.season, filters.team, filters.referee]);

  return (
    <div className="app">
      <header>
        <h1>ApitaCerto</h1>
        <p className="subtitle">
          Desempenho do Brasileirao Serie A segmentado por arbitro — sinalizacao de possivel favorecimento.
        </p>
      </header>

      <Filters options={options} value={filters} onChange={setFilters} />

      {loading || !dashboard ? (
        <p>Carregando...</p>
      ) : (
        <>
          <KpiCards kpis={dashboard.kpis} />
          <div className="chart-row">
            <WinRateLineChart data={dashboard.timeseries} />
            <CardsBarChart data={dashboard.timeseries} />
          </div>
          <FavoritismHeatmap
            rows={dashboard.heatmap}
            onSelect={({ team, referee }) => setFilters((f) => ({ ...f, team, referee }))}
          />
        </>
      )}
    </div>
  );
}
