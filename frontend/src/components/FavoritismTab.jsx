import { useEffect, useState } from "react";
import { getFavoritism } from "../api";
import PairMatrix from "./PairMatrix";
import { divergingColor, INSUFFICIENT_SAMPLE_COLOR } from "../colorScales";

// Slicer de temporada proprio dessa aba (independente do global no topo da
// pagina) -- so aqui "Todos" faz sentido, porque o indice de favorecimento
// e um par time x arbitro que ganha amostra juntando anos; classificacao e
// serie temporal (outras abas) nao podem ser agregadas entre temporadas.
export default function FavoritismTab({ seasons, onSelect }) {
  const [season, setSeason] = useState(undefined); // undefined = "Todos"
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getFavoritism({ season })
      .then((data) => {
        if (!cancelled) setRows(data.heatmap);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [season]);

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
      <label className="season-picker">
        Temporada
        <select
          value={season ?? ""}
          onChange={(e) => setSeason(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">Todos</option>
          {seasons.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </label>
      <p className="hint">
        Vermelho = possivel favorecimento ao time. Azul = possivel prejuizo.
        Cinza = amostra insuficiente (menos de 5 jogos do par na temporada
        escolhida, ou em todas juntas se "Todos"). E um sinal estatistico
        pra investigar, nao uma acusacao nem prova de manipulacao — um
        numero alto pode vir de coincidencia, calendario ou amostra pequena.
        Clique numa celula pra ver o detalhe.
      </p>
      {loading ? <p>Carregando...</p> : <PairMatrix rows={rows} cellFor={cellFor} onSelect={onSelect} />}
    </div>
  );
}
