# ApitaCerto — Spec

## 1. O que é

Dashboard interativo (estilo BI, sem Power BI/Looker) que mostra o desempenho de
times do Campeonato Brasileiro Série A **segmentado por árbitro**. Pergunta que
o usuário quer responder: "quando o árbitro X apitou o time Y, quantos gols
o time fez, quantos cartões levou, quantas vitórias/empates/derrotas, qual o
aproveitamento?"

Esta é a opção **Sports-league scoreboard** do HW2, modelada como dashboard de
métricas em vez de placar ao vivo.

## 2. Escopo (v1)

- Competição: Brasileirão Série A, temporadas **2022, 2023 e 2024** (validado
  em 2026-09-10 contra a API real — ver seção 3; free tier não cobre 2025/2026).
- Todos os times da liga, todos os árbitros que apitaram partidas da liga —
  não só um time. Time e árbitro são **filtros**, não dado fixo.
- Sem autenticação, single-user, leitura apenas (nenhuma escrita feita pelo
  usuário final).
- Dado é histórico e fechado (não muda), não ao vivo. Ingestão é um script
  rodado uma vez (ou sob demanda), não um cron contínuo. O dashboard sempre
  lê do banco, nunca da API diretamente.

Fora de escopo v1: outras ligas, outras temporadas, multi-usuário, alertas,
exportação.

## 3. Fonte de dados

**API-Football** (api-sports.io / RapidAPI), plano free (100 req/dia, todos os
endpoints liberados):

- `GET /fixtures` — retorna `referee` (nome do árbitro), times, placar, data,
  liga, temporada.
- `GET /fixtures/events` — retorna eventos por partida: gol (`Goal`), cartão
  (`Card`, detail `Yellow Card` / `Red Card` / `Yellow Red Card`), com minuto,
  time e jogador.

**Validado em 2026-09-10** com key real (`league=71`, cada temporada testada
individualmente): free plan libera exatamente `season=2022`, `2023` e `2024`
(380 jogos cada, `referee` presente em 100% dos jogos finalizados, eventos de
gol/cartão completos com minuto e jogador). `2021` e `2025`/`2026` (atual)
retornam erro de plano: `"Free plans do not have access to this season, try
from 2022 to 2024."` — confirma que **não dá pra ter temporada atual/ao vivo
no free tier**; o dashboard é sobre histórico 2022-2024, não "atualização em
tempo real" como pensado originalmente.

Chave de API fica em variável de ambiente (`API_FOOTBALL_KEY`), nunca commitada.

## 4. Modelo de dados (SQLAlchemy)

- `Team(id, api_id, name)`
- `Referee(id, api_id, name)`
- `Fixture(id, api_id, competition, season, round, date, home_team_id,
  away_team_id, referee_id, home_score, away_score)`
- `MatchEvent(id, fixture_id, team_id, player_name, minute, type
  [GOAL|YELLOW_CARD|RED_CARD], detail)`

Métricas derivadas (calculadas a partir de `Fixture` + `MatchEvent`, não
guardadas): jogos, vitórias, empates, derrotas, gols pró, gols contra,
cartões amarelos, cartões vermelhos, aproveitamento % — por combinação de
time + árbitro + intervalo de datas.

## 5. Dashboard — telas e componentes

Filtros globais (topo, afetam todos os componentes): competição (fixo em v1),
temporada (2022 / 2023 / 2024 / todas), time, árbitro, intervalo de datas.

- **KPI cards**: jogos, vitórias/empates/derrotas, aproveitamento %, gols
  pró/contra, cartões amarelos, cartões vermelhos — para o recorte de
  filtros atual.
- **Série temporal (linha)**: aproveitamento % por rodada, ao longo da
  temporada, para o time filtrado.
- **Série temporal (coluna)**: cartões (amarelo/vermelho) por rodada.
- **Heatmap**: matriz time × árbitro, cor = aproveitamento % (ou média de
  cartões por jogo, alternável). Tooltip na célula mostra os números exatos
  (jogos, V/E/D, cartões).
- Tooltip em todos os gráficos ao passar o mouse (paridade com Power BI).

## 6. Regra de negócio — Índice de Favorecimento

Objetivo do dashboard: sinalizar possíveis favorecimentos de árbitro a time.
Não compara árbitro isolado — compara **o time sob esse árbitro vs o mesmo
time sob todos os outros árbitros** (baseline leave-one-out), pra isolar o
efeito árbitro-time e não confundir com "esse time é bom".

Para cada par (Time T, Árbitro R), com `n` = jogos de T apitados por R:

- `winRate(T,R)` = vitórias / n
- `baseline(T)` = winRate de T em todos os jogos da temporada **exceto** os
  apitados por R
- `deltaWinRate = winRate(T,R) − baseline(T)` (positivo = ganha mais que o
  normal sob R)
- `cardsPerGame(T,R)` = cartões sofridos por T sob R (peso amarelo=1,
  vermelho=3) / n
- `deltaCards = baselineCards(T) − cardsPerGame(T,R)` (positivo = leva menos
  cartão que o normal sob R → sinal de proteção)
- `deltaCardsRival(T,R)` = mesma conta para cartões dados ao **adversário**
  nos jogos de T sob R, vs média do adversário sob outros árbitros (positivo
  = R é mais duro com quem enfrenta T)

Os três deltas viram **z-score** (média/desvio calculados sobre todos os
pares time-árbitro que passam no piso de amostra) para ficarem comparáveis
apesar de unidades diferentes (% vs cartões/jogo):

```
ÍndiceFavorecimento(T,R) = (z(deltaWinRate) + z(deltaCards) + z(deltaCardsRival)) / 3
```

Pesos iguais até haver dado real para calibrar.

### Regras de exibição

- **Piso de amostra**: `n < 5` → par não entra no ranking; aparece cinza /
  "amostra insuficiente" no heatmap. Sem isso, 1 jogo com resultado bom vira
  "favorecimento" por ruído.
- **Destaque**: `|Índice| ≥ 1.5` desvio-padrão → célula marcada no heatmap
  (ex.: borda vermelha).
- Heatmap (seção 5) usa o Índice como escala de cor por padrão; tooltip
  mostra os três deltas + `n` + o Índice final.
- Tabela "Maiores desvios", ordenada por `|Índice|` desc, só com pares acima
  do piso de amostra.

### Limitações (mostrar na UI, não só documentar)

- É sinalização exploratória, **não prova de manipulação**.
- Confunde com: mando de campo, força do adversário naquele jogo específico,
  decisão revisada por VAR (sem esse dado). Não controla por isso na v1.
- Free tier não traz faltas cometidas nem pênaltis marcados — deixaria o
  índice mais robusto, mas não está disponível agora (mesmo risco já
  registrado na seção 3).
- Amostra por par time-árbitro melhora usando as 3 temporadas juntas
  (2022-2024, ~1140 jogos) em vez de uma só, mas ainda pode ficar abaixo do
  piso (`n<5`) pra árbitros que apitaram pouco um time específico — o
  heatmap deve deixar isso visualmente claro (cinza), não escondido.

## 7. Arquitetura (fluxo do HW2)

```
apitacerto/
  _docs/specs.md      (este arquivo)
  frontend/           React + Vite + Recharts — protótipo com backend mockado
  backend/            FastAPI + uv + SQLAlchemy + SQLite
  openapi.yaml         contrato entre frontend e backend
  README.md
  AGENTS.md
  .gitignore
```

Ordem de construção (igual ao HW2):
1. Frontend com chamadas de backend centralizadas e mockadas.
2. `openapi.yaml` a partir do que o frontend precisa.
3. Backend FastAPI com banco mock (dict/lista em memória), testes primeiro.
4. Conectar frontend → backend real.
5. Trocar mock por SQLAlchemy + SQLite; script de ingestão separado (não
   dentro da request) popula o banco a partir da API-Football.

## 8. Fora de escopo / perguntas em aberto

- ~~Validar cobertura de temporada do free tier~~ — feito em 2026-09-10, ver
  seção 3. Decisão: v1 usa 2022-2024 fechado, não temporada atual.
- Drill-down (clicar numa célula do heatmap e filtrar o resto do dashboard)
  é stretch goal, não obrigatório pro HW2.
- Ainda não testado: `/fixtures/events` pro conjunto completo das 1140
  partidas custa ~1140 requests (1 por fixture) — free tier é 100/dia, então
  a ingestão precisa rodar em lotes ao longo de vários dias, ou usar algum
  endpoint em lote se existir. Validar isso antes de implementar o script de
  ingestão (Fase 5).
