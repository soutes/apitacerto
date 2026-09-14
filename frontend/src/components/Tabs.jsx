// Tab bar acessivel (ARIA tablist/tab/tabpanel + navegacao por seta), sem
// dependencia externa.
export default function Tabs({ tabs, active, onChange }) {
  function onKeyDown(e) {
    const idx = tabs.findIndex((t) => t.key === active);
    if (e.key === "ArrowRight") onChange(tabs[(idx + 1) % tabs.length].key);
    if (e.key === "ArrowLeft") onChange(tabs[(idx - 1 + tabs.length) % tabs.length].key);
  }

  return (
    <div className="tabs" role="tablist" aria-label="Visoes do dashboard" onKeyDown={onKeyDown}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          role="tab"
          type="button"
          aria-selected={active === tab.key}
          tabIndex={active === tab.key ? 0 : -1}
          className={`tab-btn${active === tab.key ? " active" : ""}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
