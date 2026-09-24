// Textos tecnicos da aba Analises (spec secao 9), mostrados no painel "Como
// foi criado" de cada grafico: como o dado foi construido, o metodo, quem
// criou/referencia, por que usamos e como ler (com os limites). A versao em
// linguagem de torcedor fica em components/analyses/copy.js. Se mudar o
// metodo no backend (app/analysis/*), mudar aqui tambem.

const COPY = {
  intro: {
    title: "Como ler esta aba",
    body:
      "Tudo aqui compara o que aconteceu com o que se esperaria. O esperado considera o mando de campo, o estilo e a " +
      "força de cada clube na temporada, o adversário e o rigor de cada árbitro. Diferença pequena é normal — o acaso " +
      "sozinho produz diferenças. Por isso cada número vem com um nível de evidência:",
    levels: [
      ["forte", "Sobrevive à correção de múltiplas comparações (Benjamini-Hochberg, q ≤ 0,10). Merece investigação — ainda não é prova."],
      ["fraco", "p < 0,01, mas não sobrevive à correção. Em cada 100 pares, cerca de 1 aparece aqui por puro acaso. Acompanhar."],
      ["acaso", "O acaso explica. É onde a maioria dos pares cai quando não há favorecimento."],
    ],
    prereg:
      "As hipóteses, os métodos e essas réguas foram registrados em 14/09/2026, antes de o código de análise existir.",
    preregUrl: "https://github.com/soutes/apitacerto/commit/85e9b06",
  },

  league: {
    title: "Mandante × visitante, temporada a temporada",
    subtitle: "A linha de base: o que a liga inteira já faz antes de olhar para qualquer árbitro.",
    built:
      "Em cada jogo, cartões do mandante menos cartões do visitante (e o mesmo para gols de pênalti). Média por " +
      "temporada, com intervalo de 95%.",
    method: "Média com intervalo de confiança pela distribuição t de Student.",
    origin:
      "William Sealy Gosset criou a distribuição t em 1908, trabalhando na cervejaria Guinness — assinava 'Student'. " +
      "O efeito da torcida sobre a arbitragem é um dos resultados mais estudados da economia do esporte: Nevill, " +
      "Balmer & Williams (2002) mostraram árbitros marcando menos faltas contra o mandante ao ver o mesmo lance com o " +
      "som da torcida; Pettersson-Lidbom & Priks (2010) e Reade, Schreyer & Singleton (2022) mediram o viés caindo em " +
      "jogos sem público.",
    why:
      "Qualquer suspeita sobre um árbitro precisa ser comparada com o que a liga inteira já faz. A temporada 2020, " +
      "jogada sem público, funciona como um experimento natural.",
    read:
      "Barra abaixo de zero = mandante leva menos cartão. Isso sozinho não prova viés: o mandante costuma atacar mais, " +
      "e o visitante, se defender (e fazer mais falta).",
  },

  referee: {
    title: "Rigor de cada árbitro",
    subtitle: "Quanto cada árbitro dá de cartão além (ou aquém) do que aqueles jogos pediriam.",
    built:
      "Cartões nos jogos do árbitro ÷ cartões esperados para aqueles mesmos jogos, dado quem jogou e onde. 1,20 = 20% " +
      "mais cartão que o esperado.",
    method:
      "Regressão de Poisson para o esperado; encolhimento empírico-bayesiano no ranking — quem apitou poucos jogos é " +
      "puxado para a média na medida da própria incerteza. Intervalo exato de Poisson (Garwood, 1936).",
    origin:
      "Siméon Denis Poisson publicou a distribuição em 1837, num livro sobre a probabilidade de julgamentos em " +
      "tribunais. O encolhimento vem de Charles Stein (1956) e ficou famoso com Efron & Morris (1975), que previram " +
      "médias de rebatida do beisebol melhor do que as próprias médias.",
    why:
      "Sem encolhimento, o topo e o fundo de qualquer ranking são sempre de quem tem pouca amostra — Howard Wainer " +
      "chamou isso de 'a equação mais perigosa' (2007).",
    read:
      "A barra mostra o rigor encolhido; o número entre parênteses é o bruto. 'Mandante' é a diferença mandante − " +
      "visitante desse árbitro já descontada a média da liga — no diagnóstico, essa medida foi quase toda ruído.",
  },

  cards: {
    title: "Árbitro × clube: cartões ao clube (implicância)",
    subtitle: "Algum árbitro é mais duro com um clube específico?",
    built:
      "Para cada par árbitro × clube, a soma dos cartões que o clube recebeu nos jogos daquele árbitro, comparada com " +
      "o esperado. O esperado já desconta o rigor geral do árbitro, o estilo do clube na temporada, o adversário e o " +
      "mando — sobra só o que é específico daquela dupla.",
    method:
      "Regressão de Poisson ajustada temporada a temporada, com o rigor de cada árbitro encolhido para a média " +
      "(quem apitou pouco fica perto do árbitro médio). O esperado de cada par é calculado SEM os jogos do próprio " +
      "par — senão o excesso do par vira 'rigor geral' do árbitro e 'estilo' do clube, e o sinal some. Par com sinal " +
      "forte vira termo próprio no modelo e tudo é recalculado. Teste exato de Poisson (binomial negativa quando o " +
      "próprio esperado é incerto) — conservador de propósito: a aproximação normal inventava sinal em contagem " +
      "pequena. Correção de Benjamini-Hochberg entre todos os pares testados. Calibrado em ligas simuladas sem " +
      "nenhum favorecimento: o 'sinal forte' falso fica no nível prometido pela régua.",
    origin:
      "Deixar o grupo de fora é a ideia do jackknife (Quenouille, 1949; Tukey, 1958); retirar casos extremos passo a " +
      "passo é a 'busca progressiva' (Atkinson & Riani, 2000). O gráfico de funil é de David Spiegelhalter (2005), " +
      "criado para comparar hospitais sem condenar os pequenos por azar. A correção de múltiplas comparações é de " +
      "Yoav Benjamini e Yosef Hochberg (1995).",
    why:
      "É a pergunta 'esse árbitro é mais duro com o clube X?'. Com centenas de pares, uns 5% passam do limite de 95% " +
      "por puro acaso — sem correção, sempre haveria um 'culpado'.",
    read:
      "Cada ponto é um par. Quanto menos cartões esperados, mais largo o funil, porque o acaso pesa mais. Ponto fora " +
      "da linha pontilhada (99,8%) é candidato a investigar — não conclusão.",
  },

  rivalCards: {
    title: "Árbitro × clube: cartões ao adversário",
    subtitle: "Favorecimento também pode aparecer punindo o rival.",
    built:
      "A mesma conta, olhando para os cartões do adversário nos jogos daquele par. Favorecimento apareceria como " +
      "adversário levando mais cartão do que o esperado.",
    method:
      "Mesmo modelo de Poisson, com o esperado calculado sem os jogos do próprio par, e mesma correção de " +
      "Benjamini-Hochberg da análise anterior.",
    origin: "Idem: Poisson (1837), jackknife (Quenouille, 1949), Spiegelhalter (2005), Benjamini & Hochberg (1995).",
    why: "Um árbitro pode favorecer um clube sem poupá-lo — sendo mais duro com quem o enfrenta.",
    read: "Acima de 1 = o adversário do clube levou mais cartão que o esperado com esse árbitro.",
  },

  points: {
    title: "Árbitro × clube: pontos acima do esperado",
    subtitle: "O clube pontua mais do que devia quando esse árbitro apita?",
    built:
      "Pontos que o clube fez nos jogos daquele árbitro menos os pontos esperados (xPts). Os pontos esperados vêm da " +
      "força de ataque e defesa dos dois times e do mando.",
    method:
      "Modelo de gols de Poisson (ataque × defesa × mando), ajustado sem os jogos do próprio par → probabilidades de " +
      "vitória, empate e derrota → xPts = 3 × P(vitória) + P(empate). O teste usa a distribuição exata da soma de " +
      "pontos jogo a jogo (0, 1 ou 3), com a incerteza do xPts pelo método delta.",
    origin:
      "Modelo de Mike Maher (1982), refinado por Mark Dixon e Stuart Coles (1997) — a base dos modelos usados por " +
      "casas de aposta.",
    why:
      "Resultado é o que mais importa para quem suspeita de favorecimento. Comparar com o esperado evita confundir " +
      "'time bom' com 'time favorecido'.",
    read:
      "Eixo vertical: pontos por jogo acima (ou abaixo) do esperado. O modelo prevê um pouco menos empates do que " +
      "acontecem — limitação conhecida de gols independentes.",
  },

  ease: {
    title: "Escala favorável: o mesmo árbitro nos jogos mais fáceis?",
    subtitle: "Favorecer também pode ser escalar o mesmo árbitro sempre nos jogos 'fáceis' de um clube.",
    built:
      "Facilidade de um jogo = pontos que se esperava do clube (adversário + mando). Para cada par, comparamos a " +
      "facilidade média dos jogos do clube que aquele árbitro apitou com a de um sorteio, sem reposição, entre os " +
      "jogos do clube na temporada. Ex.: se o mesmo árbitro sempre pega o líder contra os últimos colocados, esse par " +
      "sai do funil.",
    method:
      "Amostragem sem reposição com correção de população finita; z e Benjamini-Hochberg. A segunda versão compara " +
      "só com árbitros da mesma categoria.",
    origin:
      "A variância de uma amostra sem reposição é resultado clássico da teoria de amostragem (William Cochran, " +
      "Sampling Techniques, 1977).",
    why:
      "A CBF escala árbitro FIFA para jogo grande (ver 'Escala da CBF'). Sem a comparação por categoria, isso viraria " +
      "falso sinal: o árbitro FIFA pegaria os jogos difíceis do líder, e os outros, os fáceis.",
    read:
      "Acima de zero = o árbitro pegou jogos mais fáceis do clube do que o sorteio daria. 'Mesma categoria' repete o " +
      "teste só entre árbitros da mesma categoria.",
  },

  cross: {
    title: "Repetição entre temporadas",
    subtitle: "O mesmo árbitro favorece o mesmo clube em anos diferentes?",
    built:
      "Para cada par com pelo menos 2 jogos numa temporada, um índice de favorecimento padronizado (menos cartão ao " +
      "clube + mais cartão ao rival + pontos acima do esperado). Cada ponto compara uma temporada com a seguinte.",
    method:
      "Correlação de Pearson com intervalo pela transformação de Fisher (1915); pares que repetem sinal forte em 2+ " +
      "temporadas, contados contra o esperado pela distribuição binomial.",
    origin:
      "Francis Galton (1886) descreveu a regressão à média: um resultado extremo tende a voltar ao normal na medição " +
      "seguinte.",
    why: "Favorecimento real deveria se repetir; sorte não se repete.",
    read:
      "Nuvem sem inclinação = o que um par faz num ano não prevê o ano seguinte. Pares que repetem sinal aparecem na " +
      "lista, ao lado do número que o acaso produziria.",
  },

  federation: {
    title: "Escala da CBF: regra de federação",
    subtitle: "Quanto a CBF evita escalar árbitro do mesmo estado dos clubes.",
    built:
      "Porcentagem de jogos em que o árbitro é da mesma federação (UF) de um dos clubes, contra o que um sorteio daria " +
      "— cada árbitro pesando pelo tanto que apitou na temporada.",
    method: "Proporção observada vs. esperada por sorteio proporcional.",
    origin: "Conta direta sobre a escala oficial publicada pela CBF.",
    why:
      "A regra cria 'buracos' na matriz árbitro × clube que não são favorecimento nem perseguição. Por isso os " +
      "sorteios de escala desta aba respeitam a regra.",
    read: "A CBF evita, mas não proíbe: sobram exceções todo ano.",
  },

  category: {
    title: "Escala da CBF: categoria do árbitro × tamanho do jogo",
    subtitle: "Árbitro com selo FIFA vai mais para jogo grande?",
    built:
      "Participação de árbitros com selo FIFA em jogos entre times de cima, clássicos estaduais e jogos entre times de " +
      "baixo (classificação da própria temporada).",
    method: "Teste exato de Fisher.",
    origin:
      "Ronald Fisher (1935), no experimento da senhora que dizia distinguir se o leite foi posto antes ou depois do chá.",
    why:
      "Se a escala depende do tamanho do jogo, comparar árbitros direto mistura o árbitro com o tipo de jogo que ele " +
      "recebe.",
    read: "p pequeno = diferença grande demais para ser acaso.",
  },

  concentration: {
    title: "Escala da CBF: mesmo árbitro, mesmo clube, mais do que um sorteio explicaria?",
    subtitle: "Algum árbitro apita um clube mais vezes do que as regras da escala explicam?",
    built:
      "Quantas vezes cada árbitro apitou cada clube, comparado com escalas sorteadas que respeitam as regras reais: " +
      "quantos jogos cada árbitro apitou, 1 jogo por rodada, as exceções da regra de federação e — na segunda versão " +
      "— a categoria de cada jogo.",
    method:
      "Qui-quadrado de Pearson comparado com a distribuição dos sorteios (Monte Carlo); pares testados um a um com " +
      "Poisson (conservador) e Benjamini-Hochberg.",
    origin:
      "Karl Pearson criou o qui-quadrado (1900). Sorteios que preservam as restrições de uma tabela: Besag & Clifford " +
      "(1989) e Diaconis & Sturmfels (1998).",
    why:
      "É a pergunta 'um árbitro apita mais jogos de um clube do que deveria?', respondida contra as regras da CBF, não " +
      "contra um sorteio ingênuo.",
    read:
      "Sobrar concentração é uma pergunta sobre como a CBF escala — não prova nada sobre o comportamento do árbitro " +
      "em campo.",
  },

  hypotheses: {
    title: "Hipóteses pré-registradas",
    subtitle: "Perguntas agregadas, com muito mais precisão do que olhar par a par.",
    built:
      "Quatro perguntas escritas e fixadas em 14/09/2026, antes do código existir. Agregar centenas de jogos dá de 8 a " +
      "20 vezes mais precisão do que olhar par a par.",
    method:
      "Regressão de Poisson (cartões, pênaltis) e mínimos quadrados (pontos) com efeitos fixos de clube-temporada, " +
      "adversário e árbitro; erro-padrão robusto agrupado por jogo (White, 1980; Liang & Zeger, 1986). Só temporadas " +
      "encerradas: veredito não pode mudar toda semana.",
    origin:
      "Pré-registro: Nosek et al. (2018). Evita o 'jardim dos caminhos que se bifurcam' (Gelman & Loken, 2013) — " +
      "testar recortes até algum dar certo.",
    why:
      "Resultado negativo também é notícia: 'não há sinal de X maior que Y' é uma afirmação forte quando o intervalo " +
      "é estreito.",
    read:
      "Ponto = estimativa; traço = intervalo de 95%; linha vertical = 'sem efeito'. 'Apoia' só quando o intervalo não " +
      "cruza a linha e a direção é a prevista.",
  },
};

export default COPY;
