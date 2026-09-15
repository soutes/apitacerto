import Logo from "./Logo";

const NAV = [
  { key: "dashboard", label: "Dashboard" },
  { key: "classificacao", label: "Classificação" },
  { key: "arbitros", label: "Árbitros" },
  { key: "clubes", label: "Clubes" },
  { key: "confrontos", label: "Favorecimento" },
  { key: "estatisticas", label: "Dados estatísticos" },
];

export default function Sidebar({ active, onChange, dataBlurb }) {
  return (
    <nav className="sidebar" aria-label="Navegação principal">
      <div className="sidebar-logo">
        <Logo />
        <span>ApitaCerto</span>
      </div>
      <div className="sidebar-nav" role="tablist" aria-orientation="vertical">
        {NAV.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={active === item.key}
            className={`nav-pill${active === item.key ? " active" : ""}`}
            onClick={() => onChange(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {dataBlurb && (
        <div className="sidebar-footer">
          <div className="sidebar-footer-label">Dado</div>
          <div className="sidebar-footer-text">{dataBlurb}</div>
        </div>
      )}
    </nav>
  );
}
