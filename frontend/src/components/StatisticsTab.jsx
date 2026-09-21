import { useEffect, useState } from "react";
import { getStatistics } from "../api";
import {
  CrossSeasonSection,
  EaseSection,
  EscalaSection,
  HypothesesSection,
  IntroSection,
  LeagueSection,
  PairSection,
  RefereeSection,
} from "./stats/sections";
import "./stats/stats.css";

// Aba Favorecimento (spec secao 9). Seletor proprio: cada temporada ou
// todas juntas -- "todas" soma o observado - esperado de cada temporada.
export default function StatisticsTab({ seasons, defaultSeason }) {
  const [season, setSeason] = useState(defaultSeason);
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getStatistics({ season })
      .then((r) => {
        if (cancelled) return;
        setReport(r);
        setStatus(r ? "ready" : "missing");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [season]);

  const computedAt = report?.computedAt
    ? new Date(report.computedAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : null;

  return (
    <div className="stats-tab">
      <div className="stats-toolbar">
        <label className="season-picker">
          Recorte
          <select value={season ?? ""} onChange={(e) => setSeason(e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">Todas as temporadas</option>
            {seasons.map((s) => (
              <option key={s} value={s}>
                Temporada {s}
              </option>
            ))}
          </select>
        </label>
        {computedAt && status === "ready" && <span className="stats-meta">Calculado em {computedAt}</span>}
      </div>

      {status === "loading" && <p className="loading-text">Carregando…</p>}
      {status === "missing" && <p className="hint">Estatísticas ainda não calculadas para esse recorte.</p>}
      {status === "error" && <p className="hint">Não foi possível carregar as estatísticas agora.</p>}

      {status === "ready" && (
        <>
          <IntroSection report={report} />
          <LeagueSection league={report.league} selected={report.season} />
          <RefereeSection data={report.refereeStrictness} />
          <PairSection kind="cards" data={report.pairs.cards} />
          <PairSection kind="rivalCards" data={report.pairs.rivalCards} />
          <PairSection kind="points" data={report.pairs.points} />
          <EaseSection data={report.pairs.ease} />
          <CrossSeasonSection data={report.crossSeason} />
          <EscalaSection data={report.escala} />
          <HypothesesSection data={report.hypotheses} />
        </>
      )}
    </div>
  );
}
