import { useMemo, useState } from "react";
import PairMatrix from "./PairMatrix";
import { sequentialColor, divergingColor } from "../colorScales";

const METRICS = {
  jogos: { label: "Jogos", get: (r) => r.n, kind: "seq" },
  vitorias: { label: "Vitorias", get: (r) => r.wins, kind: "seq" },
  empates: { label: "Empates", get: (r) => r.draws, kind: "seq" },
  derrotas: { label: "Derrotas", get: (r) => r.losses, kind: "seq" },
  aproveitamento: {
    label: "Aproveitamento",
    get: (r) => (r.n ? (r.wins / r.n) * 100 : 0),
    kind: "seq",
    suffix: "%",
    decimals: 0,
  },
  amarelos: { label: "Cartoes amarelos", get: (r) => r.yellow, kind: "seq" },
  vermelhos: { label: "Cartoes vermelhos", get: (r) => r.red, kind: "seq" },
  saldo: {
    label: "Saldo de gols",
    get: (r) => r.goalsFor - r.goalsAgainst,
    kind: "div",
  },
};

export default function MatrixTab({ rows, onSelect }) {
  const [metricKey, setMetricKey] = useState("jogos");
  const metric = METRICS[metricKey];

  const { max, maxAbs } = useMemo(() => {
    const values = rows.map(metric.get);
    return {
      max: values.length ? Math.max(...values, 0) : 0,
      maxAbs: values.length ? Math.max(...values.map(Math.abs), 1) : 1,
    };
  }, [rows, metricKey]);

  function cellFor(row) {
    const value = metric.get(row);
    const decimals = metric.decimals ?? 0;
    const text = `${value.toFixed(decimals)}${metric.suffix || ""}`;
    const background = metric.kind === "div" ? divergingColor(value, maxAbs) : sequentialColor(value, max);
    return {
      text,
      background,
      title: `${row.team} x ${row.referee}\n${metric.label}: ${text} (n=${row.n} jogos)`,
    };
  }

  return (
    <div className="chart-box">
      <div className="metric-picker">
        <label>
          Indicador
          <select value={metricKey} onChange={(e) => setMetricKey(e.target.value)}>
            {Object.entries(METRICS).map(([key, m]) => (
              <option key={key} value={key}>{m.label}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="hint">
        Cada celula e o par time x arbitro na temporada selecionada. Cor mais
        forte = valor mais alto (ou saldo mais negativo, em azul, pro saldo de
        gols). Clique numa celula pra ver o detalhe na aba Visao Geral.
      </p>
      <PairMatrix rows={rows} cellFor={cellFor} onSelect={onSelect} />
    </div>
  );
}
