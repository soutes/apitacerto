import { useMemo, useState } from "react";

// Pontos = vitoria x3 + empate x1 (formula oficial da CBF). V/E/D/gols
// batem exatos com a tabela real (conferido -- o pipeline de dado esta
// correto); so os pontos usavam vitorias+empates antes, o que mudava a
// ordem em relacao a classificacao de verdade.
function aggregateStandings(rows, teams, referee) {
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

export default function StandingsTab({ rows }) {
  const [referee, setReferee] = useState();

  // times e arbitros vem do heatmap DESSA temporada, nao da lista global de
  // filtros -- os 20 clubes da Serie A mudam a cada ano (acesso/queda), lista
  // global misturava clube que so jogou em outra temporada (bug reportado).
  const teams = useMemo(() => [...new Set(rows.map((r) => r.team))].sort(), [rows]);
  const referees = useMemo(() => [...new Set(rows.map((r) => r.referee))].sort(), [rows]);

  const table = useMemo(() => aggregateStandings(rows, teams, referee), [rows, teams, referee]);

  return (
    <div className="chart-box">
      <h2>Tabela de Classificacao</h2>
      <p className="hint">
        Pontos = vitoria x3 + empate x1 (regra oficial), no recorte de
        arbitro escolhido (ou de todos, se nenhum arbitro for selecionado).
        Time sem jogo nesse recorte aparece zerado, no fim da tabela.
      </p>

      <div className="metric-picker">
        <label>
          Arbitro
          <select value={referee || ""} onChange={(e) => setReferee(e.target.value || undefined)}>
            <option value="">Todos</option>
            {referees.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="heatmap-wrap">
        <table className="standings">
          <thead>
            <tr>
              <th>#</th>
              <th className="col-team">Time</th>
              <th>Pontos</th>
              <th>Jogos</th>
              <th>Cartoes amarelos</th>
              <th>Cartoes vermelhos</th>
              <th>Vitorias</th>
              <th>Empates</th>
              <th>Derrotas</th>
              <th>Aproveitamento</th>
              <th>Saldo de gols</th>
            </tr>
          </thead>
          <tbody>
            {table.map((t, i) => (
              <tr key={t.team} className={t.n === 0 ? "no-data-row" : undefined}>
                <td>{i + 1}</td>
                <td className="col-team">{t.team}</td>
                <td className="col-strong">{t.points}</td>
                <td>{t.n}</td>
                <td>{t.yellow}</td>
                <td>{t.red}</td>
                <td>{t.wins}</td>
                <td>{t.draws}</td>
                <td>{t.losses}</td>
                <td>{t.winRatePct}%</td>
                <td>{t.goalDiff > 0 ? `+${t.goalDiff}` : t.goalDiff}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
