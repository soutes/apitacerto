import { HypothesesDetail } from "../stats/details";
import EvidenceChip from "../stats/EvidenceChip";
import COPY from "../../statsCopy";
import { fmt } from "../stats/format";
import { hypothesisVerdict } from "./derive";
import { HYPOTHESES, PLAIN } from "./copy";
import { AnalysisCard, Empty } from "./ui";

// H1-H4 em pergunta de torcedor + veredito grande. Intervalos e p no painel.
export default function HypothesisCards({ data, tag }) {
  return (
    <AnalysisCard
      className="span-8"
      title={PLAIN.hypotheses.title}
      subtitle={PLAIN.hypotheses.subtitle}
      tag={tag}
      how={{ copy: COPY.hypotheses, render: () => <HypothesesDetail data={data} /> }}
    >
      {!data.length ? (
        <Empty>Sem hipóteses calculadas para este recorte.</Empty>
      ) : (
        <div className="an-hyps">
          {data.map((h) => {
            const verdict = hypothesisVerdict(h);
            const plain = HYPOTHESES[h.id];
            return (
              <article className={`an-hyp verdict-${verdict === "apoia" ? "yes" : verdict === "sem dado" ? "none" : "no"}`} key={h.id}>
                <span className="an-hyp-id">{h.id}</span>
                <h4>{plain?.question ?? h.title}</h4>
                <EvidenceChip level={verdict} />
                <p>{plain?.[verdict] ?? h.prediction}</p>
                <small>
                  Temporadas {h.seasons}
                  {h.n ? ` · ${fmt(h.n, 0)} jogos` : ""}
                </small>
              </article>
            );
          })}
        </div>
      )}
    </AnalysisCard>
  );
}
