import KpiCards from "./KpiCards";
import WinRateLineChart from "./WinRateLineChart";
import CardsBarChart from "./CardsBarChart";

export default function OverviewTab({ options, team, referee, onChangeTeam, onChangeReferee, kpis, timeseries }) {
  const hasData = kpis.games > 0;

  return (
    <div>
      <div className="filters">
        <label>
          Time
          <select value={team || ""} onChange={(e) => onChangeTeam(e.target.value || undefined)}>
            <option value="">Todos</option>
            {options.teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>

        <label>
          Arbitro
          <select value={referee || ""} onChange={(e) => onChangeReferee(e.target.value || undefined)}>
            <option value="">Todos</option>
            {options.referees.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
      </div>

      <KpiCards kpis={kpis} />

      {!hasData && (
        <p className="hint">
          Sem jogos para esse recorte (temporada/time/arbitro) ainda ingeridos.
          Os indicadores acima ficam zerados ate ter dado real.
        </p>
      )}

      {hasData && (
        <div className="chart-row">
          <WinRateLineChart data={timeseries} />
          <CardsBarChart data={timeseries} />
        </div>
      )}
    </div>
  );
}
