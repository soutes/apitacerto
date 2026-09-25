// Textos da aba Analises dos clubes. Linguagem de torcedor na tela; o
// "Como foi criado" de cada card usa as mesmas chaves do MethodNote
// (built/method/origin/why/read).

export const HEADER = {
  title: "Análises dos clubes",
  subtitle: "O que a tabela da rodada já conta sobre o fim do campeonato — e os padrões que se repetem ano após ano.",
};

export const FATES = {
  champion: "Campeão",
  top6: "G-6 (2º ao 6º)",
  mid: "Meio da tabela",
  relegated: "Rebaixado",
};

const ROUND_NOTE =
  "“Rodada R” = depois de R jogos do próprio clube, em ordem de data. Jogo adiado entra quando é jogado, então todos " +
  "ficam com o mesmo número de jogos na comparação.";

export const HOW = {
  cutoff: {
    built:
      "Para cada clube em cada temporada completa (2018 em diante), os pontos que ele tinha depois de R jogos e onde " +
      "terminou o campeonato: campeão, G-6, meio da tabela ou rebaixado. " + ROUND_NOTE,
    method:
      "Contagem simples, sem modelo: a linha do rebaixamento é o menor número de pontos, na rodada R, de um clube que " +
      "escapou; a outra linha é o maior número de pontos de um clube que caiu. O mesmo vale para o G-6 e para o título.",
    why: "É a pergunta que todo torcedor faz no meio do campeonato: “com esses pontos, já dá para respirar?”.",
    read:
      "“Nunca” quer dizer “nunca desde 2018”: são poucas temporadas, e um recorde pode cair no próximo ano. G-6 é a " +
      "faixa que costuma dar Libertadores; o número exato de vagas muda de ano para ano.",
  },
  thermometer: {
    built:
      "Para cada clube da temporada em andamento: quantos pontos tem e com quantos jogos. Depois, todos os clubes das " +
      "temporadas completas que tinham pontos parecidos (2 a mais ou a menos) depois do mesmo número de jogos, e como " +
      "eles terminaram.",
    method: "Frequência histórica: quantos desses casos parecidos caíram, ficaram no meio, foram ao G-6 ou foram campeões.",
    why: "Dá contexto ao número da tabela sem inventar previsão: é só o que aconteceu com quem estava no mesmo lugar.",
    read:
      "Não é probabilidade de verdade — o calendário que falta, os confrontos diretos e o elenco não entram. Com poucos " +
      "casos parecidos, a barra vale pouco; o número de casos aparece em cada linha.",
  },
  leader: {
    built:
      "Em cada rodada de 1 a 38, quem liderava e quem era o lanterna (só pelos pontos), e se o líder foi campeão e o " +
      "lanterna caiu no fim. Empate de pontos divide a vaga entre os empatados.",
    method: "Porcentagem das temporadas completas em que isso aconteceu, rodada a rodada.",
    why: "Mostra a partir de quando a liderança (e a lanterna) passam a ser definitivas.",
    read: "Com 8 temporadas, cada temporada vale 12,5 pontos percentuais: a curva anda em degraus, não é suave.",
  },
  fortyFive: {
    built:
      "Em cada temporada completa, os pontos finais do 16º colocado (o último que escapou) e do 17º (o primeiro que caiu).",
    method: "Leitura direta da classificação final, com os critérios de desempate da CBF (pontos, vitórias, saldo, gols pró).",
    why: "Todo ano alguém repete que “45 pontos livram”. Aqui dá para ver quanto de fato precisou.",
    read: "A linha muda de ano para ano: depende de quantos pontos os times de baixo somaram naquela temporada.",
  },
  promoted: {
    built: "Clubes que não estavam na Série A no ano anterior (dentro do banco, desde 2019) e onde terminaram.",
    method: "Contagem direta.",
    why: "Mede o tamanho do salto da Série B para a Série A.",
    read: "Clube que voltou depois de um ano fora conta como promovido.",
  },
  nextYear: {
    built:
      "A posição final de cada clube em uma temporada e na seguinte; os pontos finais de uma temporada e da seguinte.",
    method: "Correlação de Pearson entre os pontos de um ano e os do seguinte (0 = nenhuma relação, 1 = total).",
    why: "Separa o que é força de verdade do que foi um ano atípico — que tende a não se repetir.",
    origin:
      "Francis Galton descreveu a regressão à média em 1886: resultado extremo tende a voltar ao normal na medição seguinte.",
    read: "Elenco, técnico e dinheiro mudam de um ano para o outro; a correlação resume tudo isso num número só.",
  },
  turno: {
    built:
      "Em cada temporada completa, os pontos do clube no turno (jogos 1 a 19) e no returno (jogos 20 a 38). Entram os " +
      "clubes com 5 ou mais temporadas completas no banco.",
    method:
      "Para cada clube, em quantas temporadas o returno foi melhor e em quantas foi pior, testado contra o cara ou coroa " +
      "(teste binomial). “Pode ser acaso” quando p ≥ 0,05.",
    why: "“Time de returno” e “time que some no segundo turno” são rótulos comuns. Aqui dá para ver se se repetem.",
    read: "Com 5 a 8 temporadas por clube, só um padrão muito forte passaria no teste.",
  },
  firstGoal: {
    built:
      "Em cada jogo com gol, quem marcou primeiro (gol contra conta para o outro time) e o resultado final. Para cada " +
      "clube, os pontos por jogo nas partidas em que sofreu o primeiro gol.",
    method: "Contagem direta. Entram no ranking os clubes com 60 ou mais jogos saindo atrás no placar.",
    why: "Mede o peso do primeiro gol e quem mais consegue reagir.",
    read: "Clube forte vira mais porque é forte: o ranking mistura reação com qualidade do elenco.",
  },
  projection: {
    built:
      "Todos os jogos com placar desde 2018 e a tabela oficial dos jogos que faltam na temporada em andamento (quem joga " +
      "contra quem, e onde).",
    method:
      "Modelo de gols de Poisson: cada clube tem uma força de ataque e uma de defesa, e o mandante ganha um bônus (o da " +
      "liga mais um ajuste pequeno para cada clube). Jogos antigos pesam menos: um jogo de 2 anos atrás vale metade de " +
      "um de hoje. Depois, os jogos que faltam são sorteados 20 mil vezes (Monte Carlo), sorteando também a força dos " +
      "times dentro da incerteza do ajuste. Cada simulação termina numa tabela final, com o desempate da CBF (pontos, " +
      "vitórias, saldo, gols pró); as chances são a porcentagem de simulações em que cada coisa aconteceu.",
    origin:
      "Modelo de gols de Mike Maher (1982); peso que cai com o tempo, de Mark Dixon e Stuart Coles (1997) — a base dos " +
      "modelos de casas de aposta. Monte Carlo: Metropolis e Ulam (1949).",
    why:
      "Testamos as alternativas nas temporadas 2019–2025, projetando do mesmo ponto do campeonato: meia-vida de 2 anos " +
      "acertou mais do que olhar só a temporada atual ou só os últimos meses (o futebol tem muito acaso; pouco jogo " +
      "engana). O confronto direto entre dois clubes não previu nada além da força atual deles, e a correção de " +
      "placares baixos de Dixon-Coles não melhorou o acerto — os dois ficaram de fora.",
    read:
      "São chances, não certezas. O modelo não sabe de lesão, reforço, troca de técnico nem de time poupado. G-6 é a " +
      "faixa que costuma dar Libertadores; o número exato de vagas muda de ano para ano. A projeção é recalculada toda " +
      "semana, depois da rodada.",
  },
  projectionEvolution: {
    built:
      "A mesma projeção refeita a cada 10 jogos da temporada (uma rodada), usando só os jogos que já tinham acontecido " +
      "até aquele ponto.",
    method: "Mesmo modelo e mesma simulação da projeção atual, com 3 mil simulações por ponto da série.",
    why: "Mostra quando cada briga começou a se definir e como uma sequência de resultados mudou as chances.",
    read:
      "No começo do campeonato os times têm poucos jogos na temporada e o modelo se apoia mais nas temporadas " +
      "anteriores, então as chances mudam rápido. Em destaque, os clubes com mais chance hoje; em cinza, os demais.",
  },
  trends: {
    built: "Média de gols por jogo, porcentagem de 0 x 0 e de vitórias do mandante em cada temporada.",
    method: "Contagem direta sobre todos os jogos com placar.",
    why: "O campeonato muda de estilo com o tempo; essas três medidas resumem a mudança.",
    read: "A temporada em andamento ainda pode mudar.",
  },
};
