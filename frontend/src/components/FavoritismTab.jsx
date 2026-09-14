import PairMatrix from "./PairMatrix";
import { divergingColor, INSUFFICIENT_SAMPLE_COLOR } from "../colorScales";

export default function FavoritismTab({ rows, onSelect }) {
  function cellFor(row) {
    if (row.insufficientSample) {
      return {
        text: "·",
        background: INSUFFICIENT_SAMPLE_COLOR,
        title: `${row.team} x ${row.referee}: amostra insuficiente (n=${row.n}, minimo 5)`,
      };
    }
    return {
      text: row.index.toFixed(1),
      background: divergingColor(row.index),
      title:
        `${row.team} x ${row.referee}\n` +
        `n=${row.n} | V${row.wins} E${row.draws} D${row.losses}\n` +
        `cartoes: ${row.yellow} amarelos, ${row.red} vermelhos\n` +
        `Indice de Favorecimento: ${row.index.toFixed(2)}`,
    };
  }

  return (
    <div className="chart-box">
      <h2>Indice de Favorecimento</h2>
      <p className="hint">
        Vermelho = possivel favorecimento ao time. Azul = possivel prejuizo.
        Cinza = amostra insuficiente (menos de 5 jogos do par nesta temporada).
        Sinalizacao exploratoria, nao prova de manipulacao — ver{" "}
        <code>_docs/specs.md</code> secao 6. Clique numa celula pra ver o
        detalhe na aba Visao Geral.
      </p>
      <PairMatrix rows={rows} cellFor={cellFor} onSelect={onSelect} />
    </div>
  );
}
