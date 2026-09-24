import { IntroDetail } from "../stats/details";
import EvidenceChip from "../stats/EvidenceChip";
import COPY from "../../statsCopy";
import { fmt } from "../stats/format";
import { niceMax } from "./derive";
import { PLAIN } from "./copy";
import { AnalysisCard, CompareBar, Legend } from "./ui";

function Verdict({ s }) {
  if (s.tested === 0) return <EvidenceChip level="sem dado" />;
  if (s.strong > 0) {
    return <EvidenceChip level="forte">{s.strong === 1 ? "1 sinal forte" : `${s.strong} sinais fortes`}</EvidenceChip>;
  }
  if (s.moreThanChance) return <EvidenceChip level="fraco">Acima do acaso</EvidenceChip>;
  return <EvidenceChip level="acaso" />;
}

// "Encontrado x acaso" das quatro perguntas par a par. Clicar numa linha
// abre essa pergunta no grafico de duplas ao lado.
export default function ChanceScoreboard({ report, summary, metric, onPickMetric }) {
  const max = niceMax(Math.max(...summary.per.map((s) => Math.max(s.outside, s.expectedOutside)), 1));
  const anyMore = summary.per.some((s) => s.moreThanChance && s.strong === 0);
  return (
    <AnalysisCard
      className="span-5"
      title={PLAIN.scoreboard.title}
      subtitle={PLAIN.scoreboard.subtitle}
      how={{ copy: COPY.intro, render: () => <IntroDetail report={report} /> }}
    >
      <Legend
        items={[
          ["found", PLAIN.scoreboard.found],
          ["chance", PLAIN.scoreboard.chance],
        ]}
      />
      <div className="an-score-list">
        {summary.per.map((s) => (
          <button
            type="button"
            key={s.key}
            className={`an-score-row${metric === s.key ? " is-active" : ""}`}
            aria-pressed={metric === s.key}
            onClick={() => onPickMetric(s.key)}
          >
            <span className="an-score-head">
              <span className="an-score-q">{PLAIN.questions[s.key].question}</span>
              <Verdict s={s} />
            </span>
            <CompareBar label={PLAIN.scoreboard.found} value={s.outside} max={max} tone="found" text={fmt(s.outside, 0)} />
            <CompareBar
              label={PLAIN.scoreboard.chance}
              value={s.expectedOutside}
              max={max}
              tone="chance"
              text={`~${fmt(s.expectedOutside, s.expectedOutside < 10 ? 1 : 0)}`}
            />
            <span className="an-score-more" aria-hidden="true">
              {metric === s.key ? "No gráfico ao lado" : "Ver duplas →"}
            </span>
          </button>
        ))}
      </div>
      {summary.pairs > 0 && (
        <p className="an-note">
          De {fmt(summary.pairs, 0)} {summary.pairs === 1 ? "dupla testada" : "duplas testadas"}, cerca de 1 em cada 20 fica fora
          do normal só por sorte.
          {anyMore &&
            " Onde há mais casos que o acaso daria, mas nenhum sinal forte, vale olhar a escala da CBF mais abaixo: ela não é um sorteio."}
        </p>
      )}
    </AnalysisCard>
  );
}
