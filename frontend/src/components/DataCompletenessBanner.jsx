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

export default function DataCompletenessBanner({ completeness }) {
  if (!completeness) return null;

  if (!completeness.isReal) {
    return (
      <p className="data-banner data-banner-mock">
        Temporada ainda sem nenhuma partida real ingerida — estes números são
        dado sintético (mock) só pra visualizar o layout, não resultado de
        jogo de verdade.
      </p>
    );
  }

  const { fixtures, fixturesWithCards, lastUpdated } = completeness;
  const updatedText = formatUpdated(lastUpdated);
  const suffix = updatedText ? ` Atualizado em ${updatedText}.` : "";

  if (fixturesWithCards < fixtures) {
    const pct = fixtures ? Math.round((fixturesWithCards / fixtures) * 100) : 0;
    return (
      <p className="data-banner data-banner-partial">
        Dado real: {fixtures} partidas já jogadas nesta temporada. Cartões
        (amarelo/vermelho) processados em {fixturesWithCards} delas ({pct}%)
        — o resto ainda está na fila de ingestão. Vitória/empate/derrota/gols
        já refletem todas as {fixtures} partidas; cartões e o Índice de
        Favorecimento ainda vão crescer.{suffix}
      </p>
    );
  }

  return (
    <p className="data-banner data-banner-complete">
      Dado real completo: {fixtures} partidas já jogadas, cartões processados
      em todas.{suffix}
    </p>
  );
}
