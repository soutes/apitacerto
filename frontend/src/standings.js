// Pontos = vitoria x3 + empate x1 (formula oficial da CBF). V/E/D/gols
// batem exatos com a tabela real (conferido -- o pipeline de dado esta
// correto); so os pontos usavam vitorias+empates antes, o que mudava a
// ordem em relacao a classificacao de verdade. Compartilhado entre
// StandingsTab (Classificacao) e DashboardTab (previa).
export function aggregateStandings(rows, teams, referee) {
  const filtered = referee ? rows.filter((r) => r.referee === referee) : rows;

  const byTeam = new Map(teams.map((t) => [t, {
    team: t, n: 0, wins: 0, draws: 0, losses: 0,
    goalsFor: 0, goalsAgainst: 0, yellow: 0, red: 0,
  }]));

  for (const row of filtered) {
    const acc = byTeam.get(row.team);
    if (!acc) continue; // time fora da lista global (nao deveria acontecer)
    acc.n += row.n;
    acc.wins += row.wins;
    acc.draws += row.draws;
    acc.losses += row.losses;
    acc.goalsFor += row.goalsFor;
    acc.goalsAgainst += row.goalsAgainst;
    acc.yellow += row.yellow;
    acc.red += row.red;
  }

  const table = [...byTeam.values()].map((t) => ({
    ...t,
    points: t.wins * 3 + t.draws,
    goalDiff: t.goalsFor - t.goalsAgainst,
    winRatePct: t.n ? Math.round((t.wins / t.n) * 1000) / 10 : 0,
  }));

  table.sort((a, b) =>
    b.points - a.points || b.goalDiff - a.goalDiff || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team)
  );
  return table;
}
