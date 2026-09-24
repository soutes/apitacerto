import { CrossDetail } from "../stats/details";
import EvidenceChip from "../stats/EvidenceChip";
import COPY from "../../statsCopy";
import { displayClubName, displayRefereeName } from "../../nameFormat";
import { fmt } from "../stats/format";
import { correlationWord, matchesFilters, niceMax } from "./derive";
import { PLAIN } from "./copy";
import { AnalysisCard, CompareBar, Empty, Legend } from "./ui";

const joinPt = (xs) => (xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} e ${xs[xs.length - 1]}`);

// Repeticao entre temporadas: favorecimento real deveria voltar no ano
// seguinte; sorte nao volta.
export default function RepeatCard({ data, filters }) {
  const filter = (p) => matchesFilters(p, filters);
  const blocks = data?.available
    ? [
        ["favorRepeats", "A favor do mesmo clube em 2+ temporadas", "a favor"],
        ["harshRepeats", "Mais duro com o mesmo clube em 2+ temporadas", "mais duro"],
      ].map(([key, label, word]) => ({ key, label, word, ...data[key] }))
    : [];
  const max = niceMax(Math.max(...blocks.map((b) => Math.max(b.observed, b.expected)), 1));
  const listed = blocks.flatMap((b) => b.pairs.filter(filter).map((p) => ({ ...p, word: b.word })));
  const c = data?.correlation;

  return (
    <AnalysisCard
      className="span-4 md-full"
      title={PLAIN.cross.title}
      subtitle={PLAIN.cross.subtitle}
      how={{ copy: COPY.cross, render: () => <CrossDetail data={data} filter={filter} /> }}
    >
      {!data?.available ? (
        <Empty>Sem duplas que se enfrentaram em temporadas seguidas neste recorte.</Empty>
      ) : (
        <>
          <p className="an-headline">
            {blocks.every((b) => b.p >= 0.05) ? (
              <>
                Não se repete <b>além do que o acaso daria</b>.
              </>
            ) : (
              <>Há mais repetição do que o acaso daria.</>
            )}
          </p>
          <Legend
            items={[
              ["found", "Encontradas"],
              ["chance", "Só por sorte"],
            ]}
          />
          <div className="an-groups">
            {blocks.map((b) => (
              <div className="an-group" key={b.key}>
                <span className="an-group-head">
                  <b>{b.label}</b>
                  <EvidenceChip level={b.p < 0.05 ? "fraco" : "acaso"} />
                </span>
                <CompareBar label="Encontradas" value={b.observed} max={max} tone="found" text={fmt(b.observed, 0)} />
                <CompareBar label="Só por sorte" value={b.expected} max={max} tone="chance" text={`~${fmt(b.expected, 1)}`} />
              </div>
            ))}
          </div>
          {listed.length > 0 && (
            <ul className="an-list">
              {listed.map((p) => (
                <li key={`${p.team}|${p.referee}|${p.word}`}>
                  <b>
                    {displayClubName(p.team)} com {displayRefereeName(p.referee)}
                  </b>
                  : {p.word} em {joinPt(p.seasons.map((s) => String(s.season)))}
                </li>
              ))}
            </ul>
          )}
          {c && (
            <p className="an-note">
              Relação entre o que uma dupla faz num ano e no seguinte: <b>{correlationWord(c.r)}</b> ({fmt(c.r, 2)}; 0 = nenhuma,
              1 = total).
            </p>
          )}
        </>
      )}
    </AnalysisCard>
  );
}
