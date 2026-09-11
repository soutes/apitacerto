// Mock data generator. Deterministic (seeded) so the UI is stable across
// reloads. Mirrors the shape the real backend (Fase 5) will return, per
// _docs/specs.md section 4-6.

export const TEAMS = [
  "Palmeiras", "Flamengo", "Atletico-MG", "Botafogo",
  "Gremio", "Fluminense", "Corinthians", "Sao Paulo",
];

export const REFEREES = [
  "Anderson Daronco", "Wilton Pereira Sampaio", "Raphael Claus",
  "Braulio da Silva Machado", "Edina Alves Batista", "Rodolpho Toski Marques",
];

export const SEASONS = [2022, 2023, 2024];

// tiny seeded PRNG (mulberry32) so mock numbers are stable, not Math.random noise
function seededRng(seed) {
  let t = seed;
  return function () {
    t |= 0;
    t = (t + 0x6d2b79f5) | 0;
    let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

function hashKey(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  return h;
}

function pairStats(team, referee, season) {
  const rng = seededRng(hashKey(`${team}|${referee}|${season}`));
  const n = 1 + Math.floor(rng() * 6); // 1..6 jogos no par, dentro de 1 temporada
  let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
  let yellow = 0, red = 0, yellowRival = 0, redRival = 0;
  for (let i = 0; i < n; i++) {
    const r = rng();
    if (r < 0.45) wins++;
    else if (r < 0.7) draws++;
    else losses++;
    goalsFor += Math.floor(rng() * 4);
    goalsAgainst += Math.floor(rng() * 3);
    yellow += Math.floor(rng() * 3);
    red += rng() < 0.12 ? 1 : 0;
    yellowRival += Math.floor(rng() * 3);
    redRival += rng() < 0.1 ? 1 : 0;
  }
  return { n, wins, draws, losses, goalsFor, goalsAgainst, yellow, red, yellowRival, redRival };
}

function winRate(s) {
  return s.n ? s.wins / s.n : 0;
}

function cardsPerGame(yellow, red, n) {
  return n ? (yellow * 1 + red * 3) / n : 0;
}

function mean(arr) {
  return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
}
function std(arr) {
  const m = mean(arr);
  return arr.length ? Math.sqrt(mean(arr.map((x) => (x - m) ** 2))) : 1;
}

const SAMPLE_FLOOR = 5;

// Builds the full team x referee matrix for a season, with the
// Indice de Favorecimento (spec section 6) computed leave-one-out.
export function buildHeatmap(season) {
  const raw = [];
  for (const team of TEAMS) {
    for (const referee of REFEREES) {
      raw.push({ team, referee, ...pairStats(team, referee, season) });
    }
  }

  // baseline(team) = time contra TODOS os outros arbitros (leave-one-out)
  const deltas = raw.map((row) => {
    const others = raw.filter((r) => r.team === row.team && r.referee !== row.referee);
    const baseWinRate = mean(others.map(winRate));
    const baseCards = mean(others.map((r) => cardsPerGame(r.yellow, r.red, r.n)));
    const baseCardsRival = mean(others.map((r) => cardsPerGame(r.yellowRival, r.redRival, r.n)));

    const deltaWinRate = winRate(row) - baseWinRate;
    const deltaCards = baseCards - cardsPerGame(row.yellow, row.red, row.n);
    const deltaCardsRival = cardsPerGame(row.yellowRival, row.redRival, row.n) - baseCardsRival;
    return { ...row, deltaWinRate, deltaCards, deltaCardsRival };
  });

  const eligible = deltas.filter((r) => r.n >= SAMPLE_FLOOR);
  const zw = { m: mean(eligible.map((r) => r.deltaWinRate)), s: std(eligible.map((r) => r.deltaWinRate)) || 1 };
  const zc = { m: mean(eligible.map((r) => r.deltaCards)), s: std(eligible.map((r) => r.deltaCards)) || 1 };
  const zr = { m: mean(eligible.map((r) => r.deltaCardsRival)), s: std(eligible.map((r) => r.deltaCardsRival)) || 1 };

  return deltas.map((row) => {
    const insufficientSample = row.n < SAMPLE_FLOOR;
    if (insufficientSample) return { ...row, index: null, insufficientSample };
    const z1 = (row.deltaWinRate - zw.m) / zw.s;
    const z2 = (row.deltaCards - zc.m) / zc.s;
    const z3 = (row.deltaCardsRival - zr.m) / zr.s;
    const index = (z1 + z2 + z3) / 3;
    return { ...row, index, insufficientSample };
  });
}

export function kpisFor(heatmapRows, team, referee) {
  const rows = heatmapRows.filter(
    (r) => (!team || r.team === team) && (!referee || r.referee === referee)
  );
  const n = rows.reduce((a, r) => a + r.n, 0);
  const wins = rows.reduce((a, r) => a + r.wins, 0);
  const draws = rows.reduce((a, r) => a + r.draws, 0);
  const losses = rows.reduce((a, r) => a + r.losses, 0);
  const goalsFor = rows.reduce((a, r) => a + r.goalsFor, 0);
  const goalsAgainst = rows.reduce((a, r) => a + r.goalsAgainst, 0);
  const yellow = rows.reduce((a, r) => a + r.yellow, 0);
  const red = rows.reduce((a, r) => a + r.red, 0);
  return {
    games: n,
    wins, draws, losses,
    winRatePct: n ? Math.round((wins / n) * 1000) / 10 : 0,
    goalsFor, goalsAgainst, yellow, red,
  };
}

// Serie temporal mock: aproveitamento % acumulado e cartoes por rodada,
// para o time selecionado (ou media da liga se nenhum time selecionado).
export function timeseriesFor(team, season) {
  const rng = seededRng(hashKey(`ts|${team || "liga"}|${season}`));
  const rounds = 20;
  let winsAcc = 0;
  const out = [];
  for (let round = 1; round <= rounds; round++) {
    const r = rng();
    const win = r < 0.45;
    if (win) winsAcc++;
    out.push({
      round,
      winRatePct: Math.round((winsAcc / round) * 1000) / 10,
      yellow: Math.floor(rng() * 5),
      red: rng() < 0.15 ? 1 : 0,
    });
  }
  return out;
}
