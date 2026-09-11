import { TEAMS, REFEREES } from "../mockData";

// Escala de cor: vermelho (indice alto, possivel favorecimento) -> branco (0)
// -> azul (indice baixo/negativo). Cinza = amostra insuficiente (n < 5).
function colorFor(row) {
  if (row.insufficientSample) return "#e5e5e5";
  const clamped = Math.max(-2, Math.min(2, row.index));
  if (clamped >= 0) {
    const t = clamped / 2;
    return `rgba(192, 57, 43, ${0.15 + t * 0.7})`;
  }
  const t = -clamped / 2;
  return `rgba(41, 98, 155, ${0.15 + t * 0.7})`;
}

export default function FavoritismHeatmap({ rows, onSelect }) {
  const byKey = new Map(rows.map((r) => [`${r.team}|${r.referee}`, r]));

  return (
    <div className="chart-box">
      <h3>Indice de Favorecimento — time x arbitro</h3>
      <p className="hint">
        Vermelho = possivel favorecimento ao time. Azul = possivel prejuizo.
        Cinza = amostra insuficiente (menos de 5 jogos do par nesta temporada).
        Sinalizacao exploratoria, nao prova de manipulacao — ver spec secao 6.
      </p>
      <div className="heatmap-wrap">
        <table className="heatmap">
          <thead>
            <tr>
              <th></th>
              {REFEREES.map((r) => (
                <th key={r} title={r}>{r.split(" ")[0]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TEAMS.map((team) => (
              <tr key={team}>
                <th>{team}</th>
                {REFEREES.map((referee) => {
                  const row = byKey.get(`${team}|${referee}`);
                  if (!row) return <td key={referee} />;
                  const title = row.insufficientSample
                    ? `${team} x ${referee}: amostra insuficiente (n=${row.n})`
                    : `${team} x ${referee}\n` +
                      `n=${row.n} | V${row.wins} E${row.draws} D${row.losses}\n` +
                      `cartoes: ${row.yellow}A ${row.red}V\n` +
                      `Indice: ${row.index.toFixed(2)}`;
                  return (
                    <td
                      key={referee}
                      title={title}
                      style={{ background: colorFor(row), cursor: "pointer" }}
                      onClick={() => onSelect?.({ team, referee })}
                    >
                      {row.insufficientSample ? "·" : row.index.toFixed(1)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
