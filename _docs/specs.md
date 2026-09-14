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

### Primária (desde 2026-09-14): scraping da API JSON pública da CBF

A CBF não documenta uma API pública, mas o site (`cbf.com.br`, Next.js) busca
os dados de tabelas/jogos via endpoints JSON abertos, achados inspecionando
a rede da página de tabelas. Sem autenticação, **sem limite diário
conhecido** (ao contrário da API-Football abaixo).

- Mapa ano → `competitionId` (extraído do payload SSR da página de tabelas,
  hardcoded em `app/cbf_scraper.py::COMPETITION_IDS`): 2018→12414,
  2019→12430, 2020→12464, 2021→12487, 2022→12518, 2023→12555, 2024→12584,
  2025→12606, 2026→1260611.
- `GET /api/cbf/jogos/campeonato/{competitionId}/rodada/{n}/fase` — **um
  request por rodada** (38 por temporada) já traz times, placar, `arbitros`
  (com `funcao`; filtramos só `"Arbitro"`, ignora assistente/quarto
  árbitro/VAR/assessor) e `penalidades` (gol e cartão de TODAS as partidas
  da rodada) — não precisa de uma segunda chamada por partida como a
  API-Football precisava.
- `penalidades[].tipo`: `GOL` ou `PENALIDADE`. Para `PENALIDADE`,
  `resultado` é `AMARELO`, `VERMELHO` ou `VERMELHO2AMARELO` (segundo
  amarelo). Para `GOL`, `resultado` é `NR` (normal), `PN` (pênalti) ou `CT`
  (gol contra — o `atleta`/`clube` listado é de quem marcou contra o
  próprio time, não de quem "ganhou" o gol).
- **Achado de qualidade de dado**: o mesmo clube pode ter `cod_time`
  diferente entre temporadas (ex.: Atlético Mineiro), e o campo `nome` do
  clube muda entre temporadas (conversão pra SAF, ou nome truncado num ano
  específico — ex.: "Atlético" sozinho em 2022 era Atlético Goianiense,
  identificado pelo `local` do jogo = Goiânia-GO). `TEAM_NAME_ALIASES` em
  `app/cbf_scraper.py` normaliza os casos conhecidos; time é casado por
  **nome** (não por id), justamente por causa disso.
- Rodado de verdade em 2026-09-14: as 3 temporadas (2022, 2023, 2024) — 1140
  partidas, 100% com árbitro e cartão/gol, ~9360 eventos — em menos de 2
  minutos (`uv run python scripts/scrape_cbf.py --season 2022 --season 2023
  --season 2024`). Sem restrição de temporada como a API-Football: 2025 e
  2026 (em andamento) já funcionam do mesmo jeito, só não estão na v1
  porque `main.py`/`openapi.yaml` ainda travam `season` em 2022-2024.

### Secundária / historico: API-Football (api-sports.io / RapidAPI)

Usada na Fase 5 original antes de achar o scraping da CBF. Mantida em
`scripts/ingest.py` como fallback caso o endpoint da CBF pare de funcionar
um dia (não documentado oficialmente, pode mudar sem aviso).

- Free tier: 100 req/dia **+ limite por minuto não documentado**, só
  `season=2022/2023/2024`, evento = 1 request por partida (1140 no total —
  levaria ~13 dias pra completar 3 temporadas, contra ~2 minutos do
  scraping da CBF).
- Chave em variável de ambiente (`API_FOOTBALL_KEY`), nunca commitada.
- Estado quando foi abandonada: 116/1140 partidas com cartão real
  (34 de 2023 + 82 de 2022), 2022/2024 sem nem a lista de partidas.

## 4. Modelo de dados (SQLAlchemy)

- `Team(id, api_id, name)` — `name` é a identidade real (ver seção 3 sobre
  clube com id/nome inconsistente entre temporadas na CBF)
- `Referee(id, name, cbf_id)`
- `Fixture(id, api_id, source [cbf|api-football], competition, season,
  round, date, home_team_id, away_team_id, referee_id, home_score,
  away_score, venue_stadium, venue_city, venue_state, events_ingested)` —
  único por `(source, api_id)`
- `MatchEvent(id, fixture_id, team_id, player_name, minute, type
  [GOAL|YELLOW_CARD|RED_CARD], detail)`

Métricas derivadas (calculadas a partir de `Fixture` + `MatchEvent`, não
guardadas): jogos, vitórias, empates, derrotas, gols pró, gols contra,
cartões amarelos, cartões vermelhos, aproveitamento % — por combinação de
time + árbitro + intervalo de datas.

## 5. Dashboard — telas e componentes

Filtro global (topo, afeta as 3 abas): temporada (2022 / 2023 / 2024).
Competição fixa em v1. Organizado em abas (redesenho 2026-09-14, guiado pela
skill `data-visualization` — overview→zoom/filter→details on demand de
Shneiderman):

**Aba 1 — Visão Geral**: filtros locais de time e árbitro (drill-down; ficam
vazios = "Todos" por padrão). KPI cards (jogos, V/E/D, aproveitamento %,
gols pró/contra, cartões amarelos/vermelhos) e série temporal (linha =
aproveitamento % por rodada, coluna = cartões por rodada) para o recorte
selecionado. Sem jogos no recorte → cards zerados e mensagem explícita, não
gráfico vazio silencioso.

**Aba 2 — Índice de Favorecimento**: a matriz time × árbitro da regra de
negócio (seção 6), cor diverging vermelho/azul, cinza = amostra
insuficiente. Clicar numa célula manda pra Aba 1 já filtrada por aquele
time+árbitro (drill-down).

**Aba 3 — Tabela Geral**: mesma matriz time × árbitro, mas com um seletor de
indicador (jogos, vitórias, empates, derrotas, aproveitamento, cartões
amarelos, cartões vermelhos, saldo de gols) e cor sequencial (azul, um único
matiz — seguro pra daltonismo) exceto saldo de gols, que é diverging (pode
ser negativo). Clicar numa célula também dá drill-down pra Aba 1.

**Aba 4 — Classificação** (2026-09-14): tabela de classificação por
temporada, com filtro próprio de árbitro (independente do drill da Aba 1).
Linhas = clubes, colunas = jogos, cartões amarelos, cartões vermelhos,
vitórias, empates, derrotas, aproveitamento %, saldo de gols, ordenada por
**pontos = vitória×3 + empate×1** (regra oficial — v1 usava
vitórias+empates por pedido inicial, corrigido em 2026-09-14 depois de
conferir contra a tabela real de 2024 e não bater), desempate por saldo de
gols e depois gols pró. Sem árbitro selecionado, soma todos; com árbitro
selecionado, mostra como cada clube se saiu especificamente sob aquele
árbitro. Clube sem jogo no recorte aparece zerado, no fim da tabela.

Toda célula/KPI sempre mostra o número junto da cor (cor nunca é a única
pista, WCAG/skill data-visualization). Navegação de abas acessível
(`role="tablist"`, seta esquerda/direita, foco visível).

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
- ~~Validar custo de `/fixtures/events` em lote~~ — feito em 2026-09-10/11:
  não existe endpoint em lote, é 1 request por partida (1140 no total). Além
  do limite de 100/dia, o free tier também tem **limite por minuto** (achado
  em produção, não documentado claramente na doc pública) — o script de
  ingestão (`backend/scripts/ingest.py`) throttla 7s entre chamadas e faz
  1 retry com backoff de 65s se estourar. Rodando `--max-requests 90`/dia
  isso dá pra cobrir ~90 partidas por dia — 3 temporadas completas (1140
  jogos) levam ~13 dias corridos rodando 1x/dia.
- Estado real em 2026-09-11: 34/380 partidas de 2023 com eventos
  ingeridos. Dashboard já funciona sobre esse dado parcial (a maioria dos
  pares time-árbitro ainda cai no piso de amostra `n<5`, corretamente).
  Continuar rodando `uv run python scripts/ingest.py --max-requests 90`
  diariamente até completar as 3 temporadas.
- **Bug real encontrado e corrigido em 2026-09-14**: `build_heatmap` e
  `timeseries_for` só consideravam fixtures com `events_ingested=True`,
  excluindo até V/E/D/gols (que já existem desde o `/fixtures`, sem
  depender de cartão nenhum) de qualquer partida ainda sem cartão buscado.
  Como as temporadas 2022 e 2024 nunca tinham tido nem o `/fixtures`
  rodado, isso fazia o dashboard cair 100% no mock sintético pra elas —
  reportado pelo usuário como "São Paulo campeão 2024" (São Paulo não foi
  campeão; era dado fake). Corrigido: `_scored_fixtures` (placar) alimenta
  V/E/D/gols/pontos incondicionalmente; só cartões dependem de
  `events_ingested`. `has_ingested_data` também passou a checar placar, não
  cartão — evita o fallback mock assim que `/fixtures` roda, mesmo antes de
  `/fixtures/events` começar. Resposta do `/dashboard` ganhou
  `dataCompleteness` (`isReal`, `fixtures`, `fixturesWithCards`) e o
  frontend mostra um banner com isso — nunca mais silenciar que o dado é
  parcial ou sintético. Validado: 2024 real bate com a Série A de verdade
  (Botafogo campeão, 23V-10E-5D); 2022 idem (Palmeiras campeão, 23V-12E-3D).
- **Migração pra scraping da CBF, 2026-09-14** (ver seção 3): a API-Football
  levaria ~13 dias corridos pra completar 3 temporadas por causa dos
  limites de request. Achado que `cbf.com.br` tem uma API JSON pública não
  documentada com tudo numa chamada por rodada, sem limite diário — as 3
  temporadas (1140 partidas, ~9360 eventos) foram completadas em menos de
  2 minutos. `scripts/scrape_cbf.py` é a ingestão principal agora;
  `scripts/ingest.py` (API-Football) fica só como fallback documentado.
  Dois bugs reais pegos e corrigidos durante a implementação (cobertos por
  teste, `tests/test_cbf_scraper.py`): (1) `clube_id` do evento vinha como
  string vs `Team.api_id` inteiro — comparação sempre falhava,
  descartando TODO cartão/gol silenciosamente; (2) mesmo clube com
  `cod_time` ou nome diferente entre temporadas (SAF, nome truncado)
  duplicava o clube em vez de casar — resolvido casando por nome com alias
  conhecido (`TEAM_NAME_ALIASES`) em vez de por id externo.
- Em aberto: `season` ainda trava em 2022-2024 (`main.py`, `openapi.yaml`)
  por causa do limite antigo da API-Football, que não existe mais pra CBF.
  2025 e 2026 (Brasileirão em andamento) já funcionam com o mesmo scraper
  — extender é so tirar o `ge=2022, le=2024` do `Query` e rodar
  `scrape_cbf.py --season 2025 --season 2026`. Não fiz isso ainda pra não
  mudar o escopo da v1 sem confirmar com o usuário.
