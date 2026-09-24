// Contas da aba Analises em cima do relatorio pronto (GET /statistics).
// Nenhuma estatistica nova aqui: so filtra e conta o que o backend ja
// classificou (p, q, level) -- mesmo corte do backend para "fora da faixa
// normal" (p < 0,05) e para "sinal fraco" esperado por acaso (1% dos pares).

export const PAIR_ANALYSES = ["cards", "rivalCards", "points", "ease"];

const uniqSorted = (xs) => [...new Set(xs)].sort((a, b) => a.localeCompare(b, "pt-BR"));

export function matchesFilters(p, { team, referee }) {
  return (!team || p.team === team) && (!referee || p.referee === referee);
}

export function filterPairs(points, filters) {
  return points.filter((p) => matchesFilters(p, filters));
}

// Slicers dependentes (estilo Power BI): cada lista so oferece o que tem
// dupla testada com o outro filtro -- nunca uma combinacao vazia.
export function filterOptions(report, { team, referee }) {
  const pts = report?.pairs?.cards?.points ?? [];
  return {
    teams: uniqSorted(pts.filter((p) => !referee || p.referee === referee).map((p) => p.team)),
    referees: uniqSorted(pts.filter((p) => !team || p.team === team).map((p) => p.referee)),
  };
}

// P(X >= k) com X ~ Binomial(n, p). n aqui e no maximo ~500 pares.
export function binomialUpperTail(n, p, k) {
  if (k <= 0) return 1;
  if (k > n) return 0;
  let pmf = Math.pow(1 - p, n);
  let below = 0;
  for (let i = 0; i < k; i += 1) {
    below += pmf;
    pmf *= ((n - i) / (i + 1)) * (p / (1 - p));
  }
  return Math.max(0, 1 - below);
}

// Uma pergunta (ex.: cartoes ao clube) num recorte: quantas duplas sairam da
// faixa normal contra quantas o acaso sozinho tiraria.
export function chanceSummary(points) {
  const tested = points.length;
  const outside = points.filter((p) => p.p != null && p.p < 0.05).length;
  const expectedOutside = tested * 0.05;
  return {
    tested,
    outside,
    expectedOutside,
    strong: points.filter((p) => p.level === "forte").length,
    weak: points.filter((p) => p.level === "fraco").length,
    expectedWeak: tested * 0.01,
    // so afirma "acima do acaso" com amostra minima e excesso improvavel
    moreThanChance: tested >= 20 && binomialUpperTail(tested, 0.05, outside) < 0.05,
  };
}

export function overallSummary(report, filters) {
  const per = PAIR_ANALYSES.map((key) => ({ key, ...chanceSummary(filterPairs(report.pairs[key].points, filters)) }));
  const pairs = filterPairs(report.pairs.cards.points, filters);
  const sum = (field) => per.reduce((acc, s) => acc + s[field], 0);
  return {
    per,
    pairs: pairs.length,
    games: pairs.reduce((acc, p) => acc + p.n, 0),
    strong: sum("strong"),
    weak: sum("weak"),
    expectedWeak: sum("expectedWeak"),
    outside: sum("outside"),
    expectedOutside: sum("expectedOutside"),
  };
}

// Como cada pergunta vira um "haltere" (o que aconteceu x o que se
// esperava), por jogo para que duplas com n diferente fiquem na mesma regua.
// favorWhenHigher: valor acima do esperado e bom para o clube?
export const METRICS = {
  cards: {
    actual: (p) => p.observed / p.n,
    expected: (p) => p.expected / p.n,
    favorWhenHigher: false,
    unit: "cartões por jogo",
    actualLabel: "Cartões recebidos",
    expectedLabel: "Esperado",
    digits: 1,
  },
  rivalCards: {
    actual: (p) => p.observed / p.n,
    expected: (p) => p.expected / p.n,
    favorWhenHigher: true,
    unit: "cartões do adversário por jogo",
    actualLabel: "Cartões do adversário",
    expectedLabel: "Esperado",
    digits: 1,
  },
  points: {
    actual: (p) => p.observed / p.n,
    expected: (p) => p.expected / p.n,
    favorWhenHigher: true,
    unit: "pontos por jogo",
    actualLabel: "Pontos feitos",
    expectedLabel: "Esperado",
    digits: 2,
    fixedMax: 3,
  },
  ease: {
    actual: (p) => p.easeWithReferee,
    expected: (p) => p.easeTeam,
    favorWhenHigher: true,
    unit: "pontos esperados por jogo (quanto maior, mais fácil)",
    actualLabel: "Jogos com este árbitro",
    expectedLabel: "Média dos jogos do clube",
    digits: 2,
    fixedMax: 3,
  },
};

// Mais "fora do normal" primeiro (menor p); empate desempata por jogos.
export function byStrength(a, b) {
  return (a.p ?? 1) - (b.p ?? 1) || b.n - a.n;
}

// Topo de eixo "redondo" para as barras (0,5 / 1 / 2 / 2,5 / 5 ...).
export function niceMax(value) {
  if (!(value > 0)) return 1;
  const exp = Math.pow(10, Math.floor(Math.log10(value)));
  const f = value / exp;
  const step = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return step * exp;
}

// Marcas do eixo: passo "redondo" que divide o topo (niceMax) em 3 a 5 partes.
export function axisTicks(max) {
  const step = niceMax(max / 5);
  const n = Math.round(max / step);
  return { step, values: Array.from({ length: n + 1 }, (_, i) => i * step) };
}

export function weightedMean(rows, key, weightKey = "matches") {
  const valid = rows.filter((r) => r[key] != null && r[weightKey]);
  const w = valid.reduce((acc, r) => acc + r[weightKey], 0);
  return w ? valid.reduce((acc, r) => acc + r[key] * r[weightKey], 0) / w : null;
}

// Hipotese com varias medidas (H1 tem 4): basta uma apoiar ou contrariar.
export function hypothesisVerdict(h) {
  if (h.missing || !h.measures?.length) return "sem dado";
  const verdicts = h.measures.map((m) => m.verdict);
  if (verdicts.includes("apoia")) return "apoia";
  if (verdicts.includes("contraria")) return "contraria";
  return "sem evidência";
}

export function correlationWord(r) {
  const a = Math.abs(r);
  if (a < 0.1) return "quase nenhuma";
  if (a < 0.3) return "fraca";
  if (a < 0.5) return "moderada";
  return "forte";
}
