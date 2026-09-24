import { useState } from "react";
import { CategoryDetail, ConcentrationDetail, FederationDetail } from "../stats/details";
import EvidenceChip from "../stats/EvidenceChip";
import COPY from "../../statsCopy";
import { displayClubName, displayRefereeName } from "../../nameFormat";
import { fmt, fmtPct } from "../stats/format";
import { matchesFilters, niceMax } from "./derive";
import { PLAIN } from "./copy";
import { AnalysisCard, CompareBar, Empty, Legend } from "./ui";

// ------------------------------------------------------------ regra de federacao
export function FederationCard({ fed, tag }) {
  const t = fed.total;
  const times = t && t.observedPct > 0 ? t.expectedPct / t.observedPct : null;
  return (
    <AnalysisCard
      className="span-4"
      title={PLAIN.federation.title}
      subtitle={PLAIN.federation.subtitle}
      tag={tag}
      how={{ copy: COPY.federation, render: () => <FederationDetail fed={fed} /> }}
    >
      {!t ? (
        <Empty>Sem o estado do árbitro e dos clubes neste recorte.</Empty>
      ) : (
        <>
          <p className="an-headline">
            {times && times >= 1.5 ? (
              <>
                A CBF evita: <b>{fmt(times, 0)}× menos</b> do que um sorteio daria.
              </>
            ) : (
              <>Parecido com o que um sorteio daria.</>
            )}
          </p>
          <div className="an-cbars">
            <CompareBar label="Na escala real" value={t.observedPct} max={niceMax(Math.max(t.observedPct, t.expectedPct))} tone="found" text={fmtPct(t.observedPct)} />
            <CompareBar label="Num sorteio" value={t.expectedPct} max={niceMax(Math.max(t.observedPct, t.expectedPct))} tone="chance" text={fmtPct(t.expectedPct)} />
          </div>
          <p className="an-note">
            {fmt(t.observedCount, 0)} de {fmt(t.matches, 0)} jogos tiveram árbitro do mesmo estado: a CBF evita, mas não proíbe.
          </p>
        </>
      )}
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ categoria x tamanho do jogo
const SHORT = {
  "Dois clubes do top-6": "jogos entre times do G-6",
  "Clássico estadual (mesma UF)": "clássicos estaduais",
  "Dois clubes do 13º ao 20º": "jogos entre times de baixo",
};

const joinPt = (xs) => (xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} e ${xs[xs.length - 1]}`);

export function CategoryCard({ cat, tag }) {
  const clear = cat.groups.filter((g) => g.p < 0.05);
  const more = clear.filter((g) => g.fifaPct > g.restPct).map((g) => SHORT[g.group] ?? g.group);
  const less = clear.filter((g) => g.fifaPct < g.restPct).map((g) => SHORT[g.group] ?? g.group);
  return (
    <AnalysisCard
      className="span-4"
      title={PLAIN.category.title}
      subtitle={PLAIN.category.subtitle}
      tag={tag}
      how={{ copy: COPY.category, render: () => <CategoryDetail cat={cat} /> }}
    >
      {!cat.groups.length ? (
        <Empty>Sem a categoria dos árbitros neste recorte.</Empty>
      ) : (
        <>
          <p className="an-headline">
            {more.length ? (
              <>
                Sim: mais árbitro FIFA em <b>{joinPt(more)}</b>
                {less.length ? <> e menos em {joinPt(less)}</> : null}.
              </>
            ) : less.length ? (
              <>
                Menos árbitro FIFA em <b>{joinPt(less)}</b>.
              </>
            ) : (
              <>Neste recorte, a diferença entre os tipos de jogo pode ser acaso.</>
            )}
          </p>
          <Legend
            items={[
              ["found", "Este tipo de jogo"],
              ["chance", "Outros jogos"],
            ]}
          />
          <div className="an-groups">
            {cat.groups.map((g) => (
              <div className="an-group" key={g.group}>
                <span className="an-group-head">
                  <b>{g.group}</b>
                  <small>
                    {fmt(g.matches, 0)} jogos · {g.p < 0.05 ? "diferença clara" : "pode ser acaso"}
                  </small>
                </span>
                <CompareBar label="Este tipo" value={g.fifaPct} max={100} tone="found" text={fmtPct(g.fifaPct, 0)} />
                <CompareBar label="Outros jogos" value={g.restPct} max={100} tone="chance" text={fmtPct(g.restPct, 0)} />
              </div>
            ))}
          </div>
        </>
      )}
    </AnalysisCard>
  );
}

// ------------------------------------------------------------ concentracao arbitro x clube
const RULES = [
  ["category", "Regras + categoria FIFA"],
  ["plain", "Só as regras básicas"],
];

// Manchete (qui-quadrado contra os sorteios) e da liga toda; com filtro, o
// card fica marcado "Liga toda" e so a lista de duplas segue o filtro.
export function ConcentrationCard({ conc, filters, tag }) {
  const [rule, setRule] = useState("category");
  const filtered = Boolean(filters.team || filters.referee);
  const v = conc[rule] ?? conc.plain;
  const filter = (p) => matchesFilters(p, filters);
  const top = (v?.top ?? []).filter(filter).slice(0, 5);
  const max = niceMax(Math.max(...top.map((p) => Math.max(p.observed, p.expected)), 1));
  return (
    <AnalysisCard
      className="span-4"
      title={PLAIN.concentration.title}
      subtitle={PLAIN.concentration.subtitle}
      tag={tag}
      how={{ copy: COPY.concentration, render: () => <ConcentrationDetail conc={conc} filter={filter} /> }}
    >
      {!v ? (
        <Empty>Sem escala suficiente para sortear neste recorte.</Empty>
      ) : (
        <>
          {conc.category && (
            <div className="an-seg an-seg-sm" role="group" aria-label="Sorteio comparado">
              {RULES.map(([key, label]) => (
                <button key={key} type="button" aria-pressed={rule === key} className={rule === key ? "is-active" : undefined} onClick={() => setRule(key)}>
                  {label}
                </button>
              ))}
            </div>
          )}
          <p className="an-headline">
            {v.p < 0.05 ? (
              <>
                Sim: alguns árbitros apitam o mesmo clube <b>mais do que o sorteio explica</b>.
              </>
            ) : (
              <>Não: a repetição cabe num sorteio com as regras da CBF.</>
            )}
          </p>
          {top.length === 0 ? (
            <Empty>{filtered ? "O filtro atual não aparece entre as duplas mais repetidas." : "Nenhuma dupla se destaca."}</Empty>
          ) : (
            <>
              {filtered && <span className="an-list-head">Do filtro atual, entre as duplas mais repetidas</span>}
              <Legend
                items={[
                  ["found", "Jogos juntos"],
                  ["chance", "Num sorteio"],
                ]}
              />
              <div className="an-groups">
                {top.map((p) => (
                  <div className="an-group" key={`${p.team}|${p.referee}`}>
                    <span className="an-group-head">
                      <b title={`${p.team} com ${p.referee}`}>
                        {displayClubName(p.team)} com {displayRefereeName(p.referee)}
                      </b>
                      <EvidenceChip level={p.level} />
                    </span>
                    <CompareBar label="Jogos juntos" value={p.observed} max={max} tone="found" text={fmt(p.observed, 0)} />
                    <CompareBar label="Num sorteio" value={p.expected} max={max} tone="chance" text={`~${fmt(p.expected, 1)}`} />
                  </div>
                ))}
              </div>
            </>
          )}
          <p className="an-note">{PLAIN.concentration.note}</p>
        </>
      )}
    </AnalysisCard>
  );
}
