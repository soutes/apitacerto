export default function Filters({ options, value, onChange }) {
  const { teams = [], referees = [], seasons = [] } = options;

  function set(key, val) {
    onChange({ ...value, [key]: val || undefined });
  }

  return (
    <div className="filters">
      <label>
        Temporada
        <select value={value.season || ""} onChange={(e) => set("season", e.target.value ? Number(e.target.value) : undefined)}>
          {seasons.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </label>

      <label>
        Time
        <select value={value.team || ""} onChange={(e) => set("team", e.target.value)}>
          <option value="">Todos</option>
          {teams.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </label>

      <label>
        Arbitro
        <select value={value.referee || ""} onChange={(e) => set("referee", e.target.value)}>
          <option value="">Todos</option>
          {referees.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
