// Escalas de cor pro PairMatrix (spec _docs/specs.md secao 6, skill
// data-visualization: sequential de matiz unico pra contagem, diverging
// pra algo que tem sinal). Cor nunca e a unica pista -- toda celula sempre
// mostra o numero tambem (ver PairMatrix/MatrixTab).

export function divergingColor(value, maxAbs = 2) {
  const clamped = Math.max(-maxAbs, Math.min(maxAbs, value));
  if (clamped >= 0) {
    const t = clamped / maxAbs;
    return `rgba(192, 57, 43, ${0.12 + t * 0.72})`; // vermelho: favorecimento
  }
  const t = -clamped / maxAbs;
  return `rgba(41, 98, 155, ${0.12 + t * 0.72})`; // azul: prejuizo
}

// Sequencial, matiz unico (azul) -- seguro pra daltonismo (nao depende de
// distinguir hue, so intensidade), evita colormap arco-iris.
export function sequentialColor(value, max) {
  if (!max || max <= 0) return "rgba(41, 98, 155, 0.08)";
  const t = Math.max(0, Math.min(1, value / max));
  return `rgba(41, 98, 155, ${0.08 + t * 0.82})`;
}

