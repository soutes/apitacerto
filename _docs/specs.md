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

- Competição: Brasileirão Série A, temporadas **2022 a 2026** (estendido em
  2026-09-14 — migrar pra scraping da CBF, seção 3, tirou a trava de
  2022-2024 que vinha do free tier da API-Football). 2026 é a temporada em
  andamento: cresce partida a partida conforme as rodadas acontecem.
- Todos os times da liga, todos os árbitros que apitaram partidas da liga —
  não só um time. Time e árbitro são **filtros**, não dado fixo.
- Sem autenticação, single-user, leitura apenas (nenhuma escrita feita pelo
  usuário final).
- Temporada fechada (2022-2025) é histórico, não muda mais. 2026 (em
  andamento) é atualizado por um **cron semanal** (seção 3.1) — o dashboard
  sempre lê do banco, nunca faz scraping/chamada externa dentro do request.

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
- Rodado de verdade em 2026-09-14: **5 temporadas (2022-2026)** — 1900
  partidas cadastradas (1520 já jogadas + 380 futuras de 2026 ainda sem
  placar), 14525 eventos, em poucos minutos
  (`uv run python scripts/scrape_cbf.py --season 2022 --season 2023
  --season 2024 --season 2025 --season 2026`). `_scored_fixtures`
  (seção 5/queries.py) só usa partida com placar — rodada futura de 2026
  não polui V/E/D/gols nem conta como "faltando cartão" (`ingestion_progress`
  usa só jogo já jogado como denominador).

### 3.1 Atualização — cron semanal

Só a temporada em andamento muda. Um scheduled task do Claude Code
(`apitacerto-cbf-refresh`, terça 23:59 horário do Brasil) roda:

```bash
cd backend
uv run python scripts/scrape_cbf.py --season <ano atual> --delay 0.4
uv run pytest -q
```

Só o ano atual — temporada anterior já está completa e não muda mais,
reprocessá-la de novo seria trabalho à toa (ajustado depois de rodar o
teste manual em 2026-09-14 e o usuário confirmar que não precisa).

`scrape_cbf.py` é idempotente — reprocessar uma rodada já gravada só
atualiza (upsert), nunca duplica. Cada rodada processada grava uma linha em
`IngestionLog`, e `GET /dashboard` expõe `dataCompleteness.lastUpdated`
(máximo `finished_at` da temporada) — o frontend mostra "Atualizado em
DD/MM/AAAA, HH:MM" no banner.

**Limitação real**: um scheduled task do Claude Code só dispara com o app
aberto (se fechado na hora marcada, roda no próximo launch) — não é cron de
SO de verdade. Pra produção/deploy isso vira um GitHub Actions com
`schedule: cron` (ver conversa sobre deploy) ou uma tarefa do Windows Task
Scheduler rodando o mesmo comando acima.

Manutenção anual: `COMPETITION_IDS` em `app/cbf_scraper.py` precisa de uma
entrada nova quando o Brasileirão de um ano novo começar (2027 em diante) —
o valor sai do payload SSR de
`https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-a/{ano}`.
O prompt do scheduled task já instrui a IA a fazer isso sozinha se o
scraper falhar por competitionId desconhecido.

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
- `IngestionLog(id, source, season, round, finished_at, matches, events)` —
  1 linha por rodada processada com sucesso; alimenta o "atualizado em"
  (`GET /dashboard` → `dataCompleteness.lastUpdated`, max `finished_at` da
  temporada) e dá rastro pro cron semanal (seção 3).

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
gráfico vazio silencioso. **Sem nenhum filtro** (time e árbitro os dois em
"Todos") a aba não mostra indicador nenhum — pede pra escolher um filtro,
em vez de somar a temporada inteira contada em dobro (cada jogo conta pro
mandante e pro visitante nas linhas agregadas do heatmap, então "todos os
times" não tem uma leitura de "vitórias" que faça sentido). Visão agregada
de todo mundo é o que as abas 3 e 4 já fazem.

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

## 5.1 Redesign visual — handoff Claude Design (2026-09-14)

Handoff em `_docs/ApitaCerto referee dashboard mockups/design_handoff_apitacerto_dashboard/`
(`README.md`, `design-brief.md`, `ApitaCerto Mockups.dc.html`). Substitui o
shell de abas horizontais por sidebar escura + 5 itens, tokens OKLCH,
Plus Jakarta Sans (UI) + JetBrains Mono (números, `font-variant-numeric:
tabular-nums`), sombras glow coloridas, divisores tracejados. Tensão
editorial carregada no texto da UI: sinaliza **padrão estatístico**, nunca
**acusação** (frase fixa perto de todo ranking punitivo de árbitro).

Nova IA da sidebar, mapeada em cima da lógica das abas antigas (nenhuma
regra de negócio mudou, só a casca visual + 2 telas novas):

- **Dashboard** (novo, `DashboardTab.jsx`): KPIs da temporada (rodada
  atual, cartões/jogo, aproveitamento do mandante, gols/jogo — endpoint
  novo `GET /season-overview`), prévia da classificação (posições
  1-5 + 12, como no mock), "Árbitros que mais punem" (top 5 por
  cartões/jogo) e "Viés de mandante" (top 4 por diferença de cartão
  casa-visitante, mais negativo primeiro).
- **Classificação** = Aba 4 antiga, com legenda de zonas continentais
  (Libertadores grupos/playoff, Sul-Americana, Rebaixamento — faixas de
  posição aproximadas, `frontend/src/zones.js`) e crachá-monograma por
  clube (`nameFormat.js::crestFor`, iniciais + cor de paleta fixa ciclada
  por índice — **não** é a cor do clube, e não carrega imagem de escudo
  externa: decisão de escopo pra não precisar de `Team.crest_url` nem
  tratar falha de carregamento de imagem).
- **Confrontos** = Aba 2 antiga (Índice de Favorecimento), casca nova.
- **Clubes** = Aba 3 antiga (Tabela Geral), casca nova, renomeada.
- **Árbitros** (novo): lista completa de árbitros elegíveis (piso de
  amostra ≥ 8 jogos, `REFEREE_SAMPLE_FLOOR` em `queries.py`) com
  jogos/cartões-por-jogo/viés — não é só o top 5/4 do Dashboard,
  `season-overview` devolve `allReferees` com a lista inteira.
- **Visão Geral** (Aba 1 antiga) não é mais item de sidebar — vira uma
  "tela de detalhe" (`activeTab==="detail"`) alcançada só clicando numa
  célula de Confrontos/Clubes, com link "← Voltar". Mantém 100% da lógica
  (slicer dependente time↔árbitro, zerado explícito).

Regra de nome longo do handoff implementada em
`nameFormat.js::displayRefereeName`: primeiro nome + último sobrenome; se
o último token for um sufixo composto (Filho/Junior/Neto/Sobrinho), inclui
o penúltimo token também (ex.: "Fernando Antonio Mendes de Salles
Nascimento Filho" → "Fernando Nascimento Filho", não "Fernando Filho").
Nome completo sempre no `title` (tooltip nativo).

Validado com o dado real: números do ranking de árbitro (`Davi De Oliveira
Lacerda 6,95 cartões/jogo, 19 jogos`, viés `Savio Pereira Sampaio -1,27`) e
da prévia de classificação bateram com os que o `design-brief.md` já
documentava como "dado real" — confirma que a implementação usa a mesma
fonte, não valores inventados pro mockup.

Escopo não implementado (fora do handoff atual, que só cobre 2 das 6 telas
do brief original): perfil individual de árbitro/clube, coluna "Forma"
(histórico V/E/D recente — placeholder cinza, sem dado ainda), estado
vazio dedicado além do "—"/opacidade reduzida já usado nas linhas sem
dado.

## 6. Regra de negócio — Índice de Favorecimento (RETIRADO em 2026-09-21)

> **Retirado do produto em 2026-09-21** (emenda em 9.8): o diagnóstico de
> 2026-09-14 mostrou que o índice não se distingue do acaso. A seção fica
> como registro histórico; a pergunta de favorecimento é respondida pela
> seção 9 (aba Favorecimento).

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
- ~~`season` travado em 2022-2024~~ — estendido em 2026-09-14 pra 2022-2026
  (pedido do usuário). `main.py`/`openapi.yaml`/`mock_store.SEASONS`
  atualizados; 2025 e 2026 scrapeados de verdade (2026 com 265/380 jogadas
  até a data, atualizando via cron — seção 3.1).
- **Bug real encontrado e corrigido em 2026-09-14 (2)**: mesmo problema de
  clube duplicado por nome inconsistente apareceu de novo com temporadas
  novas — "Fortaleza SAF" (2025) não batia com o alias que eu tinha escrito
  errado (`"Fortaleza"` em vez de `"Fortaleza SAF"`, a chave tem que ser o
  nome CRU que a API manda, não o nome já normalizado). `_canonical_team_name`
  agora **avisa no log** quando cai no fallback genérico (sufixo "Saf" sem
  alias explícito), pra não passar despercebido de novo com o cron rodando
  sem supervisão.
- **Aba 1 sem filtro mostrava a base inteira** (reportado pelo usuário,
  print com "Jogos: 760" numa temporada de 380 partidas — dobrado porque a
  agregação soma mandante+visitante). Corrigido: sem time nem árbitro
  selecionado, a aba pede pra escolher um filtro em vez de mostrar esse
  total sem sentido (seção 5).
- Cron semanal criado (scheduled task do Claude Code, `apitacerto-cbf-refresh`,
  terça 23:59 horário do Brasil) — seção 3.1 tem o comando exato e a
  limitação real dele. Testado manualmente em 2026-09-14 (rodou de
  verdade, 21 testes passaram); o usuário deu feedback direto na sessão do
  cron pra só buscar o ano atual, já aplicado no `SKILL.md` da task.

## 9. Aba "Dados estatísticos" — metodologia e pré-registro (2026-09-14)

Esta seção foi escrita e commitada **antes** do código de análise existir,
para que as hipóteses e os critérios de decisão fiquem fixados antes de
qualquer resultado ser visto (pré-registro — Nosek et al., 2018, *PNAS*).
Se algo mudar depois, a mudança entra como emenda datada, nunca como
reescrita silenciosa.

### 9.0 Por que existe

Diagnóstico de 2026-09-14 no banco real (1.785 jogos, 2022–2026): o Índice
de Favorecimento par a par (seção 6) não se distingue do acaso —
confiabilidade split-half ~0,20; teste de permutação com 10 mil sorteios deu
3 pares destacados contra 2,5 esperados por acaso (p=0,45); nenhum par
sobrevive à correção de Benjamini-Hochberg em 6 medidas; os 10 pares mais
extremos de 2022–24 caem para índice médio +0,02 em 2025–26. O teste
funciona (detecta rigor do árbitro e força do clube, traços reais) — o que
falta é amostra por par (mediana de 2 jogos). A aba nova mostra isso com
honestidade; as abas antigas ficam intactas até o usuário validar a nova.

### 9.1 Princípio: observado vs. esperado

Toda análise compara o que aconteceu com o que se esperaria dado mando de
campo, estilo/força do clube na temporada, adversário e rigor do árbitro.

- Contagens (cartões, gols de pênalti): regressão de Poisson com efeitos
  fixos (Poisson, 1837; modelos lineares generalizados, Nelder & Wedderburn,
  1972), ajustada **por temporada**: `cartões ~ clube + adversário + árbitro
  + mando`. Erro-padrão robusto agrupado por jogo (os dois lados de um jogo
  não são independentes).
- Resultado: pontos esperados (xPts) a partir de um modelo de gols
  `gols ~ ataque(clube) + defesa(adversário) + mando` (Maher, 1982; Dixon &
  Coles, 1997), convertido em P(vitória/empate/derrota).
- "Todas as temporadas" = soma dos observado − esperado de cada temporada
  (cada jogo comparado com o esperado da **sua** temporada).

### 9.2 Níveis de evidência (fixados antes de rodar)

- `z = (O − E) / √V` por par; `p` bicaudal.
- `q` = Benjamini & Hochberg (1995), dentro de cada análise × recorte.
- **Sinal forte**: q ≤ 0,10 (sobrevive à correção de múltiplas comparações).
- **Sinal fraco — acompanhar**: p < 0,01 e q > 0,10.
- **Compatível com o acaso**: todo o resto.
- Piso de exibição: par com n ≥ 3 jogos na temporada; n ≥ 5 em "todas".
- Cron semanal recalcula tudo toda semana → risco de "parar quando der
  significativo" (Simmons, Nelson & Simonsohn, 2011). Regra: veredito de
  hipótese só é oficial com a temporada encerrada; temporada em andamento
  é marcada como parcial.

### 9.3 Análises (exploratórias, sempre com correção)

- **A1 — Rigor do árbitro com o clube ("implicância")**: cartões recebidos
  pelo clube nos jogos daquele árbitro vs. esperado (já descontado o rigor
  geral do árbitro e o estilo do clube).
- **A2 — Cartões ao adversário**: cartões do adversário do clube nos jogos
  daquele árbitro vs. esperado.
- **A3 — Pontos acima do esperado**: pontos do clube com aquele árbitro vs.
  xPts.
- **A4 — Escala favorável ("jogos mais fáceis")**: facilidade de um jogo =
  xPts do clube (adversário + mando). Compara a facilidade média dos jogos
  do clube apitados por aquele árbitro com a média dos jogos do clube na
  temporada. Nulo = escala sorteada sem reposição dentro de clube ×
  temporada (correção de população finita — Cochran, 1977). Versão
  adicional comparando só com árbitros da mesma categoria (a CBF escala
  FIFA para jogo grande — seção 9.0).
- **A5 — Repetição entre temporadas**: mesmo árbitro × mesmo clube em anos
  diferentes. (a) correlação do z do par entre temporadas consecutivas;
  (b) nº de pares com sinal na mesma direção (|z| ≥ 1,96) em ≥ 2
  temporadas vs. o esperado por acaso (binomial). Expectativa declarada
  pelo usuário: não aconteceu.
- **L1 — Linha de base da liga**: por temporada, mandante vs. visitante em
  cartões, gols de pênalti e resultado, com IC 95%.
- **L2 — Rigor do árbitro**: cartões observados ÷ esperados, com
  encolhimento empírico-bayesiano (Efron & Morris, 1975) e confiabilidade;
  viés de mandante por árbitro medido **contra a média da liga**, não
  contra zero.
- **E1 — Regra de federação**: % de jogos com árbitro da UF de um dos
  clubes vs. o esperado num sorteio.
- **E2 — Categoria × importância do jogo**: participação de árbitro FIFA em
  jogos entre times de cima, clássicos estaduais e jogos de baixo (Fisher
  exato).
- **E3 — Concentração de escala clube × árbitro**: comparada com sorteios
  que respeitam as regras reais (trocas de Monte Carlo que preservam a
  carga de cada árbitro, 1 jogo por rodada e o nº de exceções de
  federação; versão estratificada por categoria) — Besag & Clifford
  (1989); Diaconis & Sturmfels (1998).

### 9.4 Hipóteses pré-registradas (confirmatórias)

α = 0,05 bicaudal; resultado publicado na aba qualquer que seja.

- **H1 — Afinidade regional**: o clube recebe menos cartões e faz mais
  pontos que o esperado quando o árbitro é da mesma região (de outro
  estado), e o contrário quando o árbitro é da região do adversário.
  *Transparência*: já olhada no diagnóstico de 14/09 (nulo: pontos
  +0,00/jogo [−0,10; +0,10]; cartões ×1,03 [0,98; 1,09]). Registrada aqui,
  mas **não** conta como confirmação independente.
- **H2 — Pressão da torcida (2020 sem público)**: a vantagem do mandante em
  cartões (mandante recebe menos) é menor em 2020, temporada inteira sem
  público, do que nas demais (desenho de Pettersson-Lidbom & Priks, 2010;
  Reade, Schreyer & Singleton, 2022). Registrada antes de ingerir 2018–2021.
- **H3 — Categoria sob pressão**: o viés de mandante em cartões é menor com
  árbitro FIFA. *Transparência*: estimativa pontual vista no diagnóstico
  (×1,06, p≈0,11, especificação com colinearidade, descartada) —
  registrada com a especificação nova.
- **H4 — VAR**: a vantagem do mandante em gols de pênalti é menor com VAR
  (2019+) do que sem (2018). Registrada antes de ingerir 2018.

### 9.5 Dado novo necessário (Fase 2)

- `MatchEvent.period` (1T/2T/AC1/AC2/INT/PJ) e minuto absoluto. Hoje a CBF
  manda acréscimo como `"45:003:00"` e o parser grava 45 — todo cartão de
  acréscimo, intervalo e pós-jogo vira "minuto 45" em qualquer tempo.
- `Referee.uf`; `Fixture.referee_category`; `Fixture.var_referee_id` +
  `var_category`; `Team.state` (UF do clube, do campo `clube` "Nome - UF").
- Ingestão de 2018–2021 (IDs já em `COMPETITION_IDS`).

### 9.6 Arquitetura (deploy alvo: Vercel + Neon)

- Cálculo **offline** (`scripts/compute_stats.py`, também chamado ao fim do
  scraping): numpy/scipy/pandas/statsmodels no grupo de dependências
  `analysis`, fora do caminho da request. Resultado gravado como JSON na
  tabela `stat_reports` (uma linha por temporada + "all").
- API (`GET /statistics`) só lê o JSON pronto — função serverless leve, sem
  numpy no pacote. Postgres (Neon) via SQLAlchemy, igual ao resto.

### 9.7 Fora de escopo agora

- Público por jogo (Boletim Financeiro em PDF) — dose-resposta de pressão
  da torcida fica para depois.
- Troca da aba Dashboard pelo método novo — depende da validação do
  usuário. (A aba Favorecimento antiga já foi trocada, ver 9.8.)

### 9.8 Emendas (datadas)

- **2026-09-14, antes de rodar o código de produção**: H1 tem 4 medidas
  (cartões e pontos × árbitro da região do clube / do adversário) — o
  veredito usa Bonferroni dentro da hipótese (α = 0,0125 por medida). H3 fica
  sem o termo principal `fifa` (colinear com o efeito de cada árbitro); só
  a interação mandante × FIFA entra.
- **2026-09-14, dado de 2018**: a CBF não publica a escala de árbitro das
  rodadas 1–32 de 2018 (o JSON vem com `arbitros: []`; só a súmula em PDF
  tem). 2018 entra inteiro no que não depende do árbitro (linha de base, H2,
  H4) e com só 60 jogos no que depende. VAR aparece em 0 jogos de 2018 e em
  todos de 2019 — bate com a adoção do VAR na Série A em 2019.
- **2026-09-14, esperado dos pares (A1–A3)**: o teste com cenário
  sintético mostrou que ajustar o esperado com os jogos do próprio par
  apaga o sinal (par plantado com 2,8× os cartões saiu com z = 2,7) e cria
  resíduo espelhado em pares inocentes — o excesso vira "rigor geral" do
  árbitro e "estilo" do clube. Correção, antes de rodar em dado real: o
  esperado de cada par vem de um ajuste **sem os jogos do par** (jackknife),
  a variância inclui a incerteza desse esperado (método delta nos pontos) e
  pares com sinal forte saem da régua dos demais até o conjunto estabilizar
  (busca progressiva, Atkinson & Riani, 2000). A primeira versão disso ainda
  gerava falso sinal em cascata no cenário sintético: tirar pares da régua
  deixava árbitro com 2–3 jogos restantes e rigor extremo. Correção: o
  efeito de cada árbitro entra encolhido para a média (efeito aleatório via
  Bayes empírico; a força do encolhimento é a variação real entre árbitros
  na temporada) — árbitro sem nenhum outro jogo vira o "árbitro médio", com
  a variância entre árbitros como incerteza.
- **2026-09-15, calibração — antes de rodar em dado real**: ligas simuladas
  **sem nenhum efeito** (nulo global; 8 e 20 clubes; começo, meio e fim de
  temporada — `backend/scripts/calibrate_stats.py`). Problemas achados e
  corrigidos, em ordem: (1) liga pequena / começo de temporada explodia
  numericamente (clube sem cartão nos jogos restantes → coeficiente −∞) →
  prior fraca (DP 1 na escala log) nos efeitos de clube e adversário, todos
  centrados na média; (2) a interação de um par sinalizado entrava na
  previsão do próprio par (variância 511 em vez de 33) → removida; (3) a
  aproximação normal de contagem pequena gerava "sinal forte" falso em até
  33% das ligas → teste exato de Poisson / binomial negativa para cartões e
  distribuição exata da soma de pontos (convolução jogo a jogo), com p exato
  convencional (não mid-p — conservador de propósito). Resultado final, ligas
  com algum "sinal forte" falso (cartões / adversário / pontos / escala):
  tamanho real 0/16, 1/16, 0/16, 0/16; meio de temporada 3/30, 3/30, 1/30,
  2/30; começo 1/20, 0/20, 3/20, 3/20 — dentro dos ~10% prometidos pela
  régua (BH q ≤ 0,10 sob nulo global); cauda |z| > 3 ≤ 0,31% (normal: 0,27%).
  Os efeitos plantados (árbitro 2,6× mais duro com um clube; árbitro sempre
  nos jogos fáceis de outro) continuam sendo achados (`tests/test_analysis.py`).
- **2026-09-14, nomes de clube**: 2018–2021 vinham com razão social ou sem
  acento ("America", "Botafogo de Futebol E Regatas", "Cruzeiro Esporte
  Clube", "Esporte Clube Bahia", "Csa", "Parana") e viravam clubes
  duplicados — mapeados em `TEAM_NAME_ALIASES`.
- **2026-09-21, retirada do Índice de Favorecimento (seção 6)**: decisão do
  usuário após o diagnóstico de 2026-09-14 (confiabilidade split-half ~0,20;
  permutação: 3 destaques contra 2,5 esperados por acaso; nenhum par passa
  Benjamini-Hochberg; o top-10 de 2022–24 não se repete em 2025–26). A aba
  antiga e o endpoint `/favoritism` saem do produto; o campo `index` sai das
  células do `/dashboard`. A aba "Dados estatísticos" (esta seção) passa a
  se chamar **Favorecimento**. O método desta seção não muda. O código do
  índice antigo continua no histórico do git.
