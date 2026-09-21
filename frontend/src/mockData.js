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

// Builds the full team x referee matrix for a season (same shape as the
// backend's /dashboard heatmap cells).
export function buildHeatmap(season) {
  const rows = [];
  for (const team of TEAMS) {
    for (const referee of REFEREES) {
      const { n, wins, draws, losses, goalsFor, goalsAgainst, yellow, red } = pairStats(team, referee, season);
      rows.push({ team, referee, n, wins, draws, losses, goalsFor, goalsAgainst, yellow, red });
    }
  }
  return rows;
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
