export default function DataCompletenessBanner({ completeness }) {
  if (!completeness) return null;

  if (!completeness.isReal) {
    return (
      <p className="data-banner data-banner-mock">
        Temporada ainda sem nenhuma partida real ingerida da API-Football —
        estes numeros sao dado sintetico (mock) so pra visualizar o layout,
        nao resultado de jogo de verdade.
      </p>
    );
  }

  const { fixtures, fixturesWithCards } = completeness;
  if (fixturesWithCards < fixtures) {
    const pct = fixtures ? Math.round((fixturesWithCards / fixtures) * 100) : 0;
    return (
      <p className="data-banner data-banner-partial">
        Dado real: {fixtures} partidas com placar confirmado. Cartoes
        (amarelo/vermelho) processados em {fixturesWithCards} delas ({pct}%)
        — o resto ainda esta na fila de ingestao (limite de request/dia da
        API-Football, ver <code>_docs/specs.md</code> secao 8). Vitoria/
        empate/derrota/gols ja refletem todas as {fixtures} partidas;
        cartoes e o Indice de Favorecimento ainda vao crescer.
      </p>
    );
  }

  return (
    <p className="data-banner data-banner-complete">
      Dado real completo: {fixtures} partidas, cartoes processados em todas.
    </p>
  );
}
