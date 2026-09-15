import { useState } from "react";

// Pares ordenados pela forca do sinal (|z|); mostra os 10 primeiros e deixa
// abrir o resto -- sem esconder quem ficou "compativel com o acaso".
export default function PairTable({ points, columns, limit = 10 }) {
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? points : points.slice(0, limit);
  return (
    <div className="table-wrap">
      <table className="stats-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.label} className={c.num ? "num" : undefined}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={`${p.team}|${p.referee}|${p.direction ?? ""}`}>
              {columns.map((c) => (
                <td key={c.label} className={c.num ? "num" : undefined} title={c.title ? c.title(p) : undefined}>
                  {c.render(p)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {points.length > limit && (
        <button type="button" className="link-button" onClick={() => setShowAll((v) => !v)}>
          {showAll ? "Mostrar só os 10 maiores sinais" : `Ver todos os ${points.length} pares`}
        </button>
      )}
    </div>
  );
}
