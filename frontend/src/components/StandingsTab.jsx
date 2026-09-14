import { useMemo, useState } from "react";
import ScreenHeader from "./ScreenHeader";
import { aggregateStandings } from "../standings";
import { crestFor, displayClubName } from "../nameFormat";
import { ZONES, zoneColorForPosition } from "../zones";

export default function StandingsTab({ season, seasons, onChangeSeason, rows }) {
  const [referee, setReferee] = useState();

  // times e arbitros vem do heatmap DESSA temporada, nao da lista global de
  // filtros -- os 20 clubes da Serie A mudam a cada ano (acesso/queda), lista
  // global misturava clube que so jogou em outra temporada (bug reportado).
  const teams = useMemo(() => [...new Set(rows.map((r) => r.team))].sort(), [rows]);
  const referees = useMemo(() => [...new Set(rows.map((r) => r.referee))].sort(), [rows]);

  const table = useMemo(() => aggregateStandings(rows, teams, referee), [rows, teams, referee]);

  const games = table.map((t) => t.n).filter((n) => n > 0);
  const roundRange = games.length
    ? (Math.min(...games) === Math.max(...games) ? `${Math.max(...games)}` : `${Math.min(...games)}–${Math.max(...games)}`)
    : "0";

  return (
    <div className="screen">
      <ScreenHeader
        title="Classificação"
        subtitle={`Série A ${season} · ${table.length} clubes`}
        statusLabel={games.length ? `Jogos por clube variam ${roundRange}` : undefined}
        season={season}
        seasons={seasons}
        onChangeSeason={onChangeSeason}
      />

      <div className="referee-filter-row">
        <label>
          Árbitro
          <select value={referee || ""} onChange={(e) => setReferee(e.target.value || undefined)}>
            <option value="">Todos</option>
            {referees.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="zones-row">
        <div className="zones-label">ZONAS</div>
        <div className="zones-legend">
          {ZONES.map((z) => (
            <div key={z.key} className="zone-chip" style={{ background: z.bg }}>
              <span className="zone-dot" style={{ background: z.color }} />
              <span style={{ color: z.text }}>{z.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="standings-table-wrap">
        <div className="standings-header-row">
          <div>#</div>
          <div>Clube</div>
          <div className="num">Pts</div>
          <div className="num">J</div>
          <div className="num">V</div>
          <div className="num">E</div>
          <div className="num">D</div>
          <div className="num">GP</div>
          <div className="num">GC</div>
          <div className="num">SG</div>
          <div className="num">CA</div>
          <div className="num">CV</div>
          <div className="num">Forma</div>
        </div>
        {table.map((t, i) => {
          const pos = i + 1;
          const crest = crestFor(t.team, i);
          const noData = t.n === 0;
          return (
            <div
              key={t.team}
              className="standings-row"
              style={{ borderLeftColor: zoneColorForPosition(pos), opacity: noData ? 0.55 : 1 }}
            >
              <div className="mono-strong">{pos}</div>
              <div className="standings-club">
                <span className="crest" style={{ background: crest.background }}>{crest.initials}</span>
                <span title={t.team} className="truncate">{displayClubName(t.team)}</span>
              </div>
              {noData ? (
                <>
                  <div className="num">—</div><div className="num">—</div><div className="num">—</div>
                  <div className="num">—</div><div className="num">—</div><div className="num">—</div>
                  <div className="num">—</div><div className="num">—</div><div className="num">—</div>
                  <div className="num">—</div>
                </>
              ) : (
                <>
                  <div className="num mono-strong">{t.points}</div>
                  <div className="num mono">{t.n}</div>
                  <div className="num mono positive">{t.wins}</div>
                  <div className="num mono">{t.draws}</div>
                  <div className="num mono negative">{t.losses}</div>
                  <div className="num mono">{t.goalsFor}</div>
                  <div className="num mono">{t.goalsAgainst}</div>
                  <div className="num mono" style={{ color: t.goalDiff >= 0 ? "var(--positive)" : "var(--negative)" }}>
                    {t.goalDiff > 0 ? `+${t.goalDiff}` : t.goalDiff}
                  </div>
                  <div className="num mono amber">{t.yellow}</div>
                  <div className="num mono negative">{t.red}</div>
                </>
              )}
              <div className="forma-dots">
                {Array.from({ length: 5 }).map((_, d) => <span key={d} className="forma-dot" />)}
              </div>
            </div>
          );
        })}
      </div>
      <p className="hint">Coluna Forma pendente de integração (histórico jogo a jogo). Clube sem jogo no recorte aparece com "—" e opacidade reduzida.</p>
    </div>
  );
}
