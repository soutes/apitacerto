// Rotulos das etiquetas de evidencia (nivel do backend -> palavra da tela).
const LABELS = {
  forte: "Sinal forte",
  fraco: "Para acompanhar",
  acaso: "Dentro do normal",
  "sem comparação": "Sem comparação",
  apoia: "Os dados confirmam",
  contraria: "Os dados contrariam",
  "sem evidência": "Sem efeito claro",
  "sem dado": "Sem dados",
};

export const HINTS = {
  forte: "Difícil de explicar só com sorte. Merece investigação — ainda não é prova.",
  fraco: "Chama atenção, mas entre centenas de duplas algumas ficam assim por sorte.",
  acaso: "Dentro do que a sorte explica.",
  apoia: "O intervalo não cruza a linha do 'sem efeito' e a direção é a prevista.",
  "sem evidência": "O resultado é compatível com 'nenhum efeito'.",
};

export function levelLabel(level) {
  return LABELS[level] ?? level;
}
