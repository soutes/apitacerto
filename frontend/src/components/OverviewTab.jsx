import KpiCards from "./KpiCards";
import WinRateLineChart from "./WinRateLineChart";
import CardsBarChart from "./CardsBarChart";

export default function OverviewTab({ options, team, referee, onChangeTeam, onChangeReferee, kpis, timeseries }) {
  // Aba 1 e sobre o RECORTE selecionado (spec secao 5) -- sem time nem
  // arbitro escolhido nao ha recorte, so daria pra somar a temporada
  // inteira contada em dobro (cada jogo entra pro mandante e o visitante).
  // Em vez de mostrar esse total sem sentido, pede pra escolher um filtro.
  const hasFilter = Boolean(team || referee);
  const hasData = hasFilter && kpis.games > 0;

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

      {!hasFilter && (
        <p className="hint">
          Escolha um time e/ou um arbitro acima pra ver os indicadores desse
          recorte. Pra visao agregada de todos os times e arbitros, use as
          abas Tabela Geral ou Classificacao.
        </p>
      )}

      {hasFilter && (
        <>
          <KpiCards kpis={kpis} />

          {!hasData && (
            <p className="hint">
              Sem jogos para esse recorte (temporada/time/arbitro) ainda
              ingeridos. Os indicadores acima ficam zerados ate ter dado real.
            </p>
          )}

          {hasData && (
            <div className="chart-row">
              <WinRateLineChart data={timeseries} />
              <CardsBarChart data={timeseries} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
