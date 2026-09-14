export default function SeasonPicker({ seasons, value, onChange }) {
  return (
    <label className="season-picker">
      Temporada
      <select value={value || ""} onChange={(e) => onChange(Number(e.target.value))}>
        {seasons.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
    </label>
  );
}
