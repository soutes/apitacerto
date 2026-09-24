// Textos da aba Analises em linguagem de torcedor/jornalista. O detalhe
// tecnico (metodo, autores, limites) continua em statsCopy.js e aparece so
// no painel "Como foi criado". Mesmo termo para a mesma coisa em toda a aba:
// "fora do normal", "o acaso", "sinal forte", "para acompanhar".

export const PLAIN = {
  header: {
    title: "Análises",
    subtitle: "O árbitro favorece ou persegue algum clube? Veja o que os números dizem.",
  },

  coin:
    "Por que comparar com o acaso? Mesmo sem favorecimento nenhum, algumas duplas árbitro × clube parecem " +
    "estranhas por pura sorte — como uma moeda que dá cara cinco vezes seguidas. Um caso só chama atenção " +
    "quando é raro demais para ser sorte.",

  questions: {
    cards: {
      tab: "Cartões ao clube",
      question: "O árbitro dá mais cartão ao clube?",
      title: "Cartões ao clube: o que aconteceu × o que se esperava",
    },
    rivalCards: {
      tab: "Cartões ao adversário",
      question: "O árbitro dá mais cartão ao adversário?",
      title: "Cartões ao adversário: o que aconteceu × o que se esperava",
    },
    points: {
      tab: "Pontos",
      question: "O clube faz mais pontos com o árbitro?",
      title: "Pontos do clube: o que aconteceu × o que se esperava",
    },
    ease: {
      tab: "Jogos fáceis",
      question: "O árbitro pega os jogos mais fáceis do clube?",
      title: "Jogos fáceis: os jogos do árbitro × a média do clube",
    },
  },

  scoreboard: {
    title: "Casos fora do normal × o que o acaso daria",
    subtitle: "Quatro jeitos de favorecer um clube. Para cada um: quantas duplas saíram da faixa normal e quantas sairiam só por sorte.",
    found: "Fora do normal",
    chance: "Só por sorte",
  },

  explorer: {
    subtitle: "Cada linha é uma dupla árbitro × clube, por jogo. Primeiro, as mais fora do normal.",
  },

  rigor: {
    title: "Quem dá mais (e menos) cartão",
    subtitle:
      "Cartões de cada árbitro comparados com o que os jogos que ele apitou pediriam. 0% = exatamente o esperado.",
    note: "É o estilo do árbitro com todo mundo — não é favorecimento a um clube.",
    faded: "Tom claro: a diferença ainda pode ser acaso.",
  },

  home: {
    title: "Jogar em casa ajuda?",
    subtitle: "Cartões por jogo do time da casa e do visitante, temporada a temporada.",
  },

  federation: {
    title: "Árbitro do mesmo estado?",
    subtitle: "Jogos apitados por árbitro do estado de um dos clubes.",
  },

  category: {
    title: "Árbitro FIFA nos jogos grandes?",
    subtitle: "Quanto de cada tipo de jogo fica com árbitro de selo FIFA.",
  },

  concentration: {
    title: "Mesmo árbitro, mesmo clube, vezes demais?",
    subtitle: "Duplas que se encontraram mais do que um sorteio com as regras da CBF daria.",
    note: "É uma pergunta sobre como a CBF escala — não diz nada sobre como o árbitro apitou.",
  },

  cross: {
    title: "Se repete de um ano para o outro?",
    subtitle: "Favorecimento de verdade se repetiria. Sorte não se repete.",
  },

  hypotheses: {
    title: "Quatro perguntas registradas antes de ver os dados",
    subtitle:
      "Escritas e publicadas em 14/09/2026, antes do código de análise existir — para ninguém escolher a pergunta depois de ver a resposta.",
  },
};

// Hipoteses pre-registradas em pergunta de torcedor + a leitura de cada
// veredito possivel. Id desconhecido cai no titulo/previsao do backend.
export const HYPOTHESES = {
  H1: {
    question: "O árbitro protege clubes da própria região?",
    apoia: "Sim: com árbitro da mesma região, o clube leva menos cartão ou faz mais pontos do que o esperado.",
    contraria: "Ao contrário do previsto: com árbitro da mesma região, o clube se sai pior.",
    "sem evidência": "Não. Com árbitro da mesma região, o clube leva os mesmos cartões e faz os mesmos pontos.",
  },
  H2: {
    question: "A torcida pressiona o árbitro?",
    apoia: "Sim. Em 2020, jogado sem público, a vantagem do time da casa nos cartões diminuiu.",
    contraria: "Ao contrário do previsto: sem público, em 2020, a vantagem do time da casa aumentou.",
    "sem evidência": "Não deu para ver diferença entre 2020, sem público, e as outras temporadas.",
  },
  H3: {
    question: "Árbitro FIFA resiste melhor à pressão da casa?",
    apoia: "Sim. Com árbitro FIFA, a vantagem do time da casa nos cartões é menor.",
    contraria: "Ao contrário do previsto: com árbitro FIFA, a vantagem da casa é maior.",
    "sem evidência": "Não encontramos diferença: com ou sem selo FIFA, a vantagem da casa nos cartões é a mesma.",
  },
  H4: {
    question: "O VAR reduziu pênaltis a favor do time da casa?",
    apoia: "Sim. Com VAR, a vantagem do time da casa em gols de pênalti ficou menor.",
    contraria: "Ao contrário do previsto: com VAR, a vantagem da casa em pênaltis aumentou.",
    "sem evidência": "Não dá para afirmar. Só existe uma temporada sem VAR (2018), e a diferença ficou dentro do acaso.",
  },
};

// Etiquetas: mesma palavra em toda a aba e no painel tecnico.
export const LEVELS = [
  ["forte", "Difícil de explicar só com sorte, mesmo depois de descontar as centenas de comparações feitas. Merece investigação — ainda não é prova."],
  ["fraco", "Chama atenção, mas entre centenas de duplas algumas ficam assim por sorte. Vale acompanhar."],
  ["acaso", "Dentro do que a sorte explica. É onde a maioria das duplas cai quando não há favorecimento."],
];
