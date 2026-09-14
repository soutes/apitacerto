function formatUpdated(iso) {
  if (!iso) return null;
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// Rodape discreto (nao e o conteudo da pagina, e proveniencia do dado --
// nao devia competir visualmente com o titulo/KPIs). Fonte sempre visivel,
// independente do estado.
export default function DataCompletenessBanner({ completeness }) {
  if (!completeness) return null;

  const { isReal, fixtures, fixturesWithCards, lastUpdated } = completeness;
  const updatedText = formatUpdated(lastUpdated);

  let statusClass = "footer-dot-complete";
  let message;

  if (!isReal) {
    statusClass = "footer-dot-mock";
    message = "Temporada sem partida real ingerida ainda — números de demonstração (mock), não resultado de jogo de verdade.";
  } else if (fixturesWithCards < fixtures) {
    const pct = fixtures ? Math.round((fixturesWithCards / fixtures) * 100) : 0;
    statusClass = "footer-dot-partial";
    message = `${fixtures} partidas já jogadas · cartões processados em ${fixturesWithCards} (${pct}%), resto na fila de ingestão`;
  } else {
    message = `${fixtures} partidas já jogadas, cartões processados em todas`;
  }

  return (
    <footer className="app-footer">
      <span className={`footer-dot ${statusClass}`} />
      <span>{message}</span>
      {updatedText && <span>· Atualizado em {updatedText}</span>}
      <span>· Fonte: <a href="https://www.cbf.com.br/futebol-brasileiro" target="_blank" rel="noreferrer">CBF</a></span>
    </footer>
  );
}
