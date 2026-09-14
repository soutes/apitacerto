// Grid generico time x arbitro. Tab 2 (Indice de Favorecimento) e Tab 3
// (Tabela Geral) sao a mesma grade renderizando valores diferentes -- so
// muda o `cellFor(row)` que cada aba passa.
//
// cellFor(row) -> { text, title, background } | null (null = celula em
// branco, sem estilo -- usado quando o valor nao faz sentido pro par).
export default function PairMatrix({ rows, cellFor, onSelect, emptyMessage }) {
  const byKey = new Map(rows.map((r) => [`${r.team}|${r.referee}`, r]));
  const teams = [...new Set(rows.map((r) => r.team))].sort();
  const referees = [...new Set(rows.map((r) => r.referee))].sort();

  if (teams.length === 0) {
    return <p className="hint">{emptyMessage || "Sem dados para este recorte ainda."}</p>;
  }

  return (
    <div className="heatmap-wrap">
      <table className="heatmap" role="table">
        <thead>
          <tr>
            <th scope="col"></th>
            {referees.map((r) => (
              <th key={r} scope="col" title={r}>{r.split(" ")[0]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map((team) => (
            <tr key={team}>
              <th scope="row">{team}</th>
              {referees.map((referee) => {
                const row = byKey.get(`${team}|${referee}`);
                if (!row) return <td key={referee} className="empty-cell" />;
                const cell = cellFor(row);
                if (!cell) return <td key={referee} className="empty-cell" />;
                return (
                  <td
                    key={referee}
                    title={cell.title}
                    tabIndex={0}
                    role="button"
                    aria-label={cell.title}
                    style={{ background: cell.background }}
                    onClick={() => onSelect?.({ team, referee })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") onSelect?.({ team, referee });
                    }}
                  >
                    {cell.text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
