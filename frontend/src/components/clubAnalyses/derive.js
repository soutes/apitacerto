// Contas da aba Analises dos clubes em cima de GET /club-insights. "Rodada R"
// aqui = depois de R jogos do proprio clube (jogo adiado entra quando e
// jogado), o que deixa todo mundo com o mesmo numero de jogos. "Nunca" vale
// para as temporadas completas do banco (2018 em diante).

export const FATE_ORDER = ["champion", "top6", "mid", "relegated"];

export const closedSeasons = (data) => data.seasons.filter((s) => s.complete);
export const currentSeason = (data) => {
  const open = data.seasons.filter((s) => !s.complete);
  return open.length ? open[open.length - 1] : null;
};

export const pointsAt = (team, r) => (team.points.length >= r ? team.points[r - 1] : null);
export const gamesPlayed = (team) => team.points.length;

function clubSeasons(closed) {
  return closed.flatMap((s) => s.teams.map((t) => ({ ...t, season: s.season })));
}

// Extremos da rodada R: abaixo de quantos pontos ninguem escapou, acima de
// quantos ninguem caiu (e o mesmo para G-6 e titulo), com quem fez o recorde.
function extreme(rows, pick, fn) {
  const vals = rows.filter(pick);
  if (!vals.length) return null;
  const best = fn(...vals.map((r) => r.pts));
  return { points: best, who: vals.filter((r) => r.pts === best).map((r) => ({ team: r.team, season: r.season, position: r.position })) };
}

export function cutoffs(closed, r) {
  const rows = clubSeasons(closed)
    .map((t) => ({ team: t.team, season: t.season, fate: t.fate, position: t.position, pts: pointsAt(t, r) }))
    .filter((t) => t.pts != null);
  const isTop = (t) => t.fate === "top6" || t.fate === "champion";
  return {
    rows,
    seasons: closed.length,
    safeMin: extreme(rows, (t) => t.fate !== "relegated", Math.min),
    relegatedMax: extreme(rows, (t) => t.fate === "relegated", Math.max),
    topMin: extreme(rows, isTop, Math.min),
    outsideTopMax: extreme(rows, (t) => !isTop(t), Math.max),
    championMin: extreme(rows, (t) => t.fate === "champion", Math.min),
    nonChampionMax: extreme(rows, (t) => t.fate !== "champion", Math.max),
  };
}

// Peso de cada clube numa "faixa" da tabela na rodada R so pelos pontos:
// empate na fronteira divide a vaga (sem usar o futuro como desempate).
function band(teams, r, k, fromTop) {
  const pts = teams.map((t) => ({ t, p: pointsAt(t, r) })).filter((x) => x.p != null);
  pts.sort((a, b) => (fromTop ? b.p - a.p : a.p - b.p));
  if (pts.length < k) return [];
  const edge = pts[k - 1].p;
  const inside = pts.filter((x) => (fromTop ? x.p > edge : x.p < edge));
  const tied = pts.filter((x) => x.p === edge);
  const slots = k - inside.length;
  return [...inside.map((x) => ({ t: x.t, w: 1 })), ...tied.map((x) => ({ t: x.t, w: slots / tied.length }))];
}

// Para cada rodada: % de temporadas em que o lider virou campeao e em que o
// lanterna caiu; % dos clubes do Z-4 da rodada que cairam.
export function roundRates(closed, maxRound = 38) {
  const out = [];
  for (let r = 1; r <= maxRound; r += 1) {
    let leader = 0;
    let lanterna = 0;
    let z4 = 0;
    for (const s of closed) {
      leader += band(s.teams, r, 1, true).reduce((a, x) => a + x.w * (x.t.fate === "champion"), 0);
      lanterna += band(s.teams, r, 1, false).reduce((a, x) => a + x.w * (x.t.fate === "relegated"), 0);
      z4 += band(s.teams, r, 4, false).reduce((a, x) => a + x.w * (x.t.fate === "relegated"), 0) / 4;
    }
    const n = closed.length || 1;
    out.push({ round: r, leader: (leader / n) * 100, lanterna: (lanterna / n) * 100, z4: (z4 / n) * 100 });
  }
  return out;
}

// Termometro da temporada em andamento: para cada clube, o que aconteceu
// com quem tinha pontos parecidos (+-window) depois do mesmo numero de jogos.
export function thermometer(closed, current, window = 2) {
  if (!current) return [];
  const all = clubSeasons(closed);
  return current.teams.map((t) => {
    const g = gamesPlayed(t);
    const p = pointsAt(t, g);
    const peers = all.filter((x) => {
      const xp = pointsAt(x, g);
      return xp != null && Math.abs(xp - p) <= window;
    });
    const share = (f) => (peers.length ? (peers.filter(f).length / peers.length) * 100 : null);
    const cut = cutoffs(closed, g);
    return {
      team: t.team,
      position: t.position,
      games: g,
      points: p,
      peers: peers.length,
      relegatedPct: share((x) => x.fate === "relegated"),
      midPct: share((x) => x.fate === "mid"),
      topPct: share((x) => x.fate === "top6"),
      championPct: share((x) => x.fate === "champion"),
      belowSurvivors: cut.safeMin != null && p < cut.safeMin.points,
      aboveRelegated: cut.relegatedMax != null && p > cut.relegatedMax.points,
    };
  });
}

// "A lenda dos 45 pontos": o ultimo que escapou e o primeiro que caiu.
export function relegationLine(closed) {
  return closed.map((s) => {
    const byPos = [...s.teams].sort((a, b) => a.position - b.position);
    const n = byPos.length;
    const lastSafe = byPos[n - 5];
    const firstDown = byPos[n - 4];
    const final = (t) => t.points[t.points.length - 1];
    return {
      season: s.season,
      lastSafe: { team: lastSafe.team, points: final(lastSafe) },
      firstDown: { team: firstDown.team, points: final(firstDown) },
    };
  });
}

export function promotedFates(closed) {
  return clubSeasons(closed)
    .filter((t) => t.promoted)
    .map((t) => ({ team: t.team, season: t.season, position: t.position, fate: t.fate }))
    .sort((a, b) => a.position - b.position);
}

export function pearson(xs, ys) {
  const n = xs.length;
  if (n < 3) return null;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < n; i += 1) {
    sxy += (xs[i] - mx) * (ys[i] - my);
    sxx += (xs[i] - mx) ** 2;
    syy += (ys[i] - my) ** 2;
  }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : null;
}

// De um ano para o outro: onde o campeao terminou, quem foi do G-6 ao Z-4,
// e o quanto os pontos de um ano preveem os do seguinte.
export function nextYear(seasons) {
  const bySeason = new Map(seasons.map((s) => [s.season, s]));
  const champions = [];
  const falls = [];
  const xs = [];
  const ys = [];
  for (const s of seasons.filter((x) => x.complete)) {
    const next = bySeason.get(s.season + 1);
    if (!next) continue;
    const nextPos = new Map(next.teams.map((t) => [t.team, t]));
    for (const t of s.teams) {
      const n = nextPos.get(t.team);
      if (t.fate === "champion") champions.push({ team: t.team, season: s.season, next: n ? n.position : null, nextComplete: next.complete });
      if (!n) continue;
      if (next.complete && t.position <= 6 && n.fate === "relegated") {
        falls.push({ team: t.team, season: s.season, from: t.position, to: n.position });
      }
      if (next.complete) {
        xs.push(t.points[t.points.length - 1]);
        ys.push(n.points[n.points.length - 1]);
      }
    }
  }
  return { champions, falls, correlation: pearson(xs, ys), pairs: xs.length };
}

// Teste binomial bicaudal com moeda honesta (p = 0,5): "melhor no returno
// em X de Y temporadas" e padrao ou acaso?
export function coinFlipP(k, n) {
  if (!n) return 1;
  const pmf = [];
  let c = 1;
  for (let i = 0; i <= n; i += 1) {
    pmf.push(c / 2 ** n);
    c = (c * (n - i)) / (i + 1);
  }
  const limit = pmf[k] * (1 + 1e-9);
  return Math.min(1, pmf.reduce((a, x) => a + (x <= limit ? x : 0), 0));
}

export function turnoReturno(closed, minSeasons = 5) {
  const byClub = new Map();
  for (const s of closed) {
    for (const t of s.teams) {
      if (t.points.length < 38) continue;
      const turno = t.points[18];
      const returno = t.points[37] - turno;
      if (!byClub.has(t.team)) byClub.set(t.team, []);
      byClub.get(t.team).push({ season: s.season, diff: returno - turno });
    }
  }
  return [...byClub.entries()]
    .filter(([, rows]) => rows.length >= minSeasons)
    .map(([team, rows]) => {
      const better = rows.filter((r) => r.diff > 0).length;
      const worse = rows.filter((r) => r.diff < 0).length;
      const mean = rows.reduce((a, r) => a + r.diff, 0) / rows.length;
      return { team, rows, better, worse, mean, p: coinFlipP(Math.max(better, worse), better + worse) };
    })
    .sort((a, b) => b.mean - a.mean);
}

export function niceMax(value) {
  if (!(value > 0)) return 1;
  const exp = 10 ** Math.floor(Math.log10(value));
  const f = value / exp;
  const step = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return step * exp;
}
