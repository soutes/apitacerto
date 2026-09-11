const CARDS = [
  { key: "games", label: "Jogos" },
  { key: "wins", label: "Vitorias" },
  { key: "draws", label: "Empates" },
  { key: "losses", label: "Derrotas" },
  { key: "winRatePct", label: "Aproveitamento", suffix: "%" },
  { key: "goalsFor", label: "Gols pro" },
  { key: "goalsAgainst", label: "Gols contra" },
  { key: "yellow", label: "Cartoes amarelos" },
  { key: "red", label: "Cartoes vermelhos" },
];

export default function KpiCards({ kpis }) {
  return (
    <div className="kpi-grid">
      {CARDS.map((c) => (
        <div className="kpi-card" key={c.key} title={c.label}>
          <div className="kpi-value">{kpis[c.key]}{c.suffix || ""}</div>
          <div className="kpi-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
