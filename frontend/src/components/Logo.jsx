// Logomarca inline: apito + bolinha (pentagono), sem asset externo --
// design handoff secao "Assets".
export default function Logo() {
  return (
    <div className="logo-badge">
      <svg width="16" height="16" viewBox="0 0 16 16">
        <rect x="1.4" y="7.1" width="8" height="4.2" rx="2.1" fill="#fff" transform="rotate(-30 5.4 9.2)" />
        <circle cx="10.4" cy="5.5" r="1.6" fill="none" stroke="#fff" strokeWidth="1.2" />
        <polygon points="12.6,10.6 13.9,11.6 13.4,13.1 11.7,13.1 11.2,11.6" fill="#fff" />
      </svg>
    </div>
  );
}
