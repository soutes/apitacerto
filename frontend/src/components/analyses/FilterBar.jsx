// Uma linha de filtros acima de tudo (estilo Power BI): temporada, clube e
// arbitro valem para todos os graficos da aba que dependem deles.
export default function FilterBar({ seasons, partialSeasons, season, onSeason, options, team, referee, onTeam, onReferee, computedAt }) {
  const newestFirst = [...seasons].sort((a, b) => b - a);
  const hasFilter = Boolean(team || referee);
  return (
    <div className="an-filters" role="search" aria-label="Filtros da análise">
      <label className="an-filter">
        <span>Temporada</span>
        <select value={season ?? ""} onChange={(e) => onSeason(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">Todas</option>
          {newestFirst.map((s) => (
            <option key={s} value={s}>
              {s}
              {partialSeasons.includes(s) ? " (em andamento)" : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="an-filter">
        <span>Clube</span>
        <select value={team ?? ""} onChange={(e) => onTeam(e.target.value || undefined)}>
          <option value="">Todos os clubes</option>
          {options.teams.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className="an-filter an-filter-wide">
        <span>Árbitro</span>
        <select value={referee ?? ""} onChange={(e) => onReferee(e.target.value || undefined)}>
          <option value="">Todos os árbitros</option>
          {options.referees.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>
      {hasFilter && (
        <button
          type="button"
          className="an-clear"
          onClick={() => {
            onTeam(undefined);
            onReferee(undefined);
          }}
        >
          Limpar filtros
        </button>
      )}
      {computedAt && <span className="an-filters-meta">Atualizado em {computedAt}</span>}
    </div>
  );
}
