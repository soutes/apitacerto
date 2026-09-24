import EvidenceChip from "../stats/EvidenceChip";
import COPY from "../../statsCopy";
import { fmt } from "../stats/format";
import { LEVELS } from "./copy";

const REPO_URL = "https://github.com/soutes/apitacerto";

// Rodape da aba: o que vale para todos os graficos (etiquetas, limites do
// dado, postura editorial, metodo aberto). O detalhe de cada grafico fica
// no "Como foi criado" dele.
export default function AnalysesFooter({ report, computedAt }) {
  const { overview, partialSeasons } = report;
  const noReferee = overview.matches - overview.matchesWithReferee;
  return (
    <footer className="an-footer" aria-label="Sobre estas análises">
      <div className="an-footer-col">
        <h4>Como ler as etiquetas</h4>
        <ul className="an-footer-levels">
          {LEVELS.map(([level, text]) => (
            <li key={level}>
              <EvidenceChip level={level} />
              <span>{text}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="an-footer-col">
        <h4>Padrão não é prova</h4>
        <p>
          Estatística aponta padrões ao longo de muitos jogos. Não julga lance, intenção nem caráter de ninguém. Um número fora
          do normal é convite para investigar — nunca acusação.
        </p>
        <p>
          Cada “esperado” já desconta o mando de campo, a força e o estilo de cada clube na temporada, o adversário e o rigor
          geral do árbitro.
        </p>
      </div>

      <div className="an-footer-col">
        <h4>De onde vêm os números</h4>
        <p>
          Súmulas e escalas oficiais publicadas pela{" "}
          <a href="https://www.cbf.com.br/futebol-brasileiro" target="_blank" rel="noreferrer">
            CBF
          </a>
          : {fmt(overview.matches, 0)} jogos da Série A neste recorte.
          {noReferee > 0 && ` ${fmt(noReferee, 0)} deles vieram sem o árbitro na escala publicada e só entram nas contas da liga.`}
        </p>
        <p>
          Uma dupla árbitro × clube se encontra poucas vezes (metade tem até {fmt(overview.medianPairGames, 0)} jogos). Por isso só
          entram duplas com {overview.floor}+ jogos, e um resultado isolado pesa pouco.
        </p>
        {partialSeasons.length > 0 && (
          <p>
            Temporada {partialSeasons.join(", ")} em andamento: os números mudam toda semana. As quatro perguntas registradas
            usam só temporadas encerradas.
          </p>
        )}
      </div>

      <div className="an-footer-col">
        <h4>Método aberto</h4>
        <p>
          As perguntas e as réguas foram registradas em público antes de o código existir (
          <a href={COPY.intro.preregUrl} target="_blank" rel="noreferrer">
            ver registro
          </a>
          ). O método foi testado em campeonatos simulados sem favorecimento nenhum: o alarme falso fica no nível prometido.
        </p>
        <p>
          Código e cálculos:{" "}
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            github.com/soutes/apitacerto
          </a>
          .{computedAt && ` Calculado em ${computedAt}.`}
        </p>
      </div>
    </footer>
  );
}
