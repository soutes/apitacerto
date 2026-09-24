import { useEffect, useId, useRef, useState } from "react";
import MethodNote from "../stats/MethodNote";

// Pecas da aba Analises: card com o botao "Como foi criado" (painel com o
// metodo e os numeros completos), barras de comparacao e blocos de numero.

export function InfoIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle cx="8" cy="8" r="6.8" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 7.2v4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="8" cy="4.9" r="1" fill="currentColor" />
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M6 12.5l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AlertIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M12 7v6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="12" cy="17" r="1.4" fill="currentColor" />
    </svg>
  );
}

// Painel "Como foi criado": <dialog> nativo (Esc fecha, foco preso e
// devolvido ao botao). Montado so enquanto aberto.
function HowItWasMade({ title, copy, onClose, children }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);
  const close = () => ref.current?.close();
  return (
    <dialog
      ref={ref}
      className="an-drawer"
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
    >
      <div className="an-drawer-inner">
        <header className="an-drawer-head">
          <div>
            <span className="an-eyebrow">Como foi criado</span>
            <h3 id={titleId}>{title}</h3>
          </div>
          <button type="button" className="an-drawer-close" onClick={close} aria-label="Fechar">
            ×
          </button>
        </header>
        <div className="an-drawer-body">
          {copy?.title && copy.title !== title && <p className="an-drawer-tech-title">No método: {copy.title}</p>}
          {copy && <MethodNote {...copy} />}
          {children && (
            <section className="an-drawer-numbers">
              <h4>Os números completos</h4>
              {children}
            </section>
          )}
        </div>
      </div>
    </dialog>
  );
}

export function AnalysisCard({ id, title, subtitle, how, tag, className = "", children }) {
  const [open, setOpen] = useState(false);
  const headingId = useId();
  return (
    <section id={id} className={`an-card ${className}`} aria-labelledby={headingId}>
      <header className="an-card-head">
        <h3 id={headingId}>{title}</h3>
        {subtitle && <p className="an-card-sub">{subtitle}</p>}
        {(tag || how) && (
          <div className="an-card-actions">
            {tag && <span className="an-tag">{tag}</span>}
            {how && (
              <button type="button" className="an-how" aria-haspopup="dialog" onClick={() => setOpen(true)}>
                <InfoIcon />
                Como foi criado
              </button>
            )}
          </div>
        )}
      </header>
      {children}
      {open && (
        <HowItWasMade title={title} copy={how.copy} onClose={() => setOpen(false)}>
          {how.render?.()}
        </HowItWasMade>
      )}
    </section>
  );
}

// Barra horizontal simples com o valor na ponta (fora da barra: nunca corta).
// tone: found (o que aconteceu), chance (o acaso / sorteio), more, less.
export function CompareBar({ label, value, max, tone, text, title }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <span className={`an-cbar tone-${tone}`} title={title}>
      <span className="an-cbar-label">{label}</span>
      <span className="an-cbar-track">
        <span className="an-cbar-area">
          <span className="an-cbar-fill" style={{ width: `${pct}%` }} />
          <span className="an-cbar-value" style={{ left: `${pct}%` }}>
            {text}
          </span>
        </span>
      </span>
    </span>
  );
}

export function StatTile({ label, value, sub, tone }) {
  return (
    <div className={`an-tile${tone ? ` tone-${tone}` : ""}`}>
      <span className="an-tile-label">{label}</span>
      <b className="an-tile-value">{value}</b>
      {sub && <span className="an-tile-sub">{sub}</span>}
    </div>
  );
}

export function Empty({ children }) {
  return <p className="an-empty">{children}</p>;
}

export function Legend({ items }) {
  return (
    <div className="an-legend">
      {items.map(([kind, label]) => (
        <span key={label}>
          <i className={`an-key key-${kind}`} aria-hidden="true" />
          {label}
        </span>
      ))}
    </div>
  );
}
