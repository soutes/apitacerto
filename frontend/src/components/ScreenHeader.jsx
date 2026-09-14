export default function ScreenHeader({ title, subtitle, statusLabel, season, seasons, onChangeSeason, showSeasonPicker = true }) {
  return (
    <div className="screen-header">
      <div className="screen-header-text">
        <h2>{title}</h2>
        <div className="screen-header-subtitle">{subtitle}</div>
      </div>
      <div className="screen-header-actions">
        {statusLabel && (
          <div className="status-pill">
            <span className="status-dot" />
            {statusLabel}
          </div>
        )}
        {showSeasonPicker && (
          <label className="season-pill">
            <span className="sr-only">Temporada</span>
            <select value={season ?? ""} onChange={(e) => onChangeSeason(Number(e.target.value))}>
              {seasons.map((s) => (
                <option key={s} value={s}>Temporada {s}</option>
              ))}
            </select>
          </label>
        )}
      </div>
    </div>
  );
}
