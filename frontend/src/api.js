// Todas as chamadas ao backend ficam centralizadas aqui (HW2 Fase 1
// requirement). Hoje mockado com dados locais; Fase 4 troca o corpo destas
// funcoes por fetch(`${BACKEND_URL}/...`) sem mexer em quem as chama.

import { TEAMS, REFEREES, SEASONS, buildHeatmap, kpisFor, timeseriesFor } from "./mockData";

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const USE_MOCK = false; // Fase 4: conectado ao backend real (ver _docs/specs.md)

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getFilters() {
  if (USE_MOCK) {
    await delay(120);
    return { teams: TEAMS, referees: REFEREES, seasons: SEASONS };
  }
  const res = await fetch(`${BACKEND_URL}/filters`);
  return res.json();
}

export async function getSeasonOverview({ season }) {
  if (USE_MOCK) {
    await delay(120);
    return {
      currentRound: 0, gamesPlayed: 0, cardsPerGame: 0, homeWinPct: 0, goalsPerGame: 0,
      mostCardsReferees: [], homeBiasReferees: [],
    };
  }
  const res = await fetch(`${BACKEND_URL}/season-overview?season=${season}`);
  if (!res.ok) throw new Error(`season-overview fetch failed: ${res.status}`);
  return res.json();
}

// Aba Favorecimento (spec secao 9): relatorio pre-calculado offline (backend so le).
// season omitido = todas as temporadas. 404 = ainda nao calculado -> null.
export async function getStatistics({ season } = {}) {
  const params = new URLSearchParams();
  if (season) params.set("season", season);
  const res = await fetch(`${BACKEND_URL}/statistics?${params.toString()}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`statistics fetch failed: ${res.status}`);
  return res.json();
}

export async function getDashboard({ season, team, referee }) {
  if (USE_MOCK) {
    await delay(150);
    const heatmap = buildHeatmap(season);
    const kpis = kpisFor(heatmap, team, referee);
    const timeseries = timeseriesFor(team, season);
    return { kpis, timeseries, heatmap };
  }
  const params = new URLSearchParams();
  if (season) params.set("season", season);
  if (team) params.set("team", team);
  if (referee) params.set("referee", referee);
  const res = await fetch(`${BACKEND_URL}/dashboard?${params.toString()}`);
  if (!res.ok) throw new Error(`dashboard fetch failed: ${res.status}`);
  return res.json();
}
