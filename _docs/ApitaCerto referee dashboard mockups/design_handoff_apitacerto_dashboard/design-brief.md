# Brief de redesign — ApitaCerto

Prompt pra colar no Claude Design (skill `design`). Gerado em 14/09/2026 a
partir do dado real do banco. Ver `specs.md` pro produto, `AGENTS.md` pra stack.

---

## Prompt

Você vai redesenhar o **ApitaCerto**, um dashboard que analisa o Campeonato
Brasileiro Série A segmentado por árbitro, procurando sinais de favorecimento.
Hoje ele é funcional e feio: quatro abas cinzas, tabelas HTML cruas, zero
hierarquia visual. Preciso de um canvas com a direção nova e um design system
que eu consiga implementar depois.

### Produto

Cinco temporadas (2022-2026), 1900 partidas, 59 árbitros, 20 clubes por ano.
O usuário é torcedor e jornalista esportivo — não é analista de dados. Ele
chega querendo responder "esse árbitro prejudica meu time?" e precisa sair
entendendo que a resposta é estatística, não acusação.

O produto tem uma tensão editorial que o design precisa carregar: ele sinaliza
**padrão**, nunca **manipulação**. Um número alto é convite pra investigar, não
veredito. Se o design fizer isso parecer denúncia, está errado.

### Direção visual

Light mode. Cruzamento de duas referências:

- **Dashboard de produto moderno** — sidebar de navegação, cards com elevação
  sutil, microanimação na entrada e no hover, espaçamento generoso, tipografia
  com escala clara.
- **Portal esportivo** (ge.globo, ESPN) — tabela de classificação densa e
  escaneável, escudo do clube em cada linha, badges de forma recente (V/E/D em
  círculos coloridos), números que dominam visualmente.

O resultado deve parecer um produto editorial esportivo, não um painel de BI.

### Navegação (sidebar)

- **Dashboard** — visão da temporada, KPIs, destaques
- **Classificação** — tabela completa estilo portal
- **Árbitros** — lista + perfil individual
- **Clubes** — lista + perfil individual
- **Confrontos** — matriz clube × árbitro (índice de favorecimento)

Seletor de temporada global, sempre visível. Na tela de Confrontos ele tem uma
opção extra "Todas", porque o índice acumula entre anos.

### Telas (artboards)

1. **Dashboard** — KPIs da temporada, destaques de árbitro, prévia da tabela
2. **Classificação** — tabela completa, 20 clubes, densa
3. **Árbitros (lista)** — ranking por rigor, ordenável
4. **Perfil do árbitro** — KPIs dele, clubes que mais apitou, distribuição
5. **Confrontos** — matriz clube × árbitro com escala divergente
6. **Estado vazio / amostra insuficiente** — crítico, ver abaixo

### Dado real (use estes números, não invente)

Classificação 2026, parcial na rodada 27:

```
1  Flamengo              57 pts  27j  17V  6E  4D  53gp  22gc  +31  53CA  6CV
2  Palmeiras             56 pts  27j  16V  8E  3D  47gp  21gc  +26  56CA  6CV
3  Athletico Paranaense  46 pts  27j  13V  7E  7D  41gp  31gc  +10  61CA  2CV
4  Fluminense            45 pts  27j  12V  9E  6D  41gp  35gc   +6  78CA  4CV
5  Bahia                 43 pts  26j  11V 10E  5D  40gp  32gc   +8  67CA  4CV
8  Coritiba              38 pts  27j  10V  8E  9D  37gp  38gc   -1  49CA 10CV
12 Vitória               33 pts  27j   9V  6E 12D  27gp  39gc  -12  66CA  3CV
```

Árbitros que mais punem em 2026 (cartões por jogo):

```
Davi De Oliveira Lacerda        6,95  (19 jogos)
Paulo Cesar Zanovelli da Silva  6,58  (12 jogos)
Felipe Fernandes de Lima        6,50  (14 jogos)
Flavio Rodrigues de Souza       6,46  (13 jogos)
Bruno Arleu de Araujo           6,07  (15 jogos)
```

Viés de mandante — cartões a mais para o time da casa, por jogo. Todos
negativos: o visitante leva mais cartão com todo mundo.

```
Savio Pereira Sampaio  -1,27   Anderson Daronco  -1,00
Davi De Oliveira Lacerda -1,05  Ramon Abatti Abel -1,00
```

Média da liga, 5 temporadas: 5,74 cartões/jogo (varia de 4,43 a 7,15 entre
árbitros), 47,2% de vitória do mandante, 2,46 gols por jogo.

### Restrições reais do dado (o design tem que aguentar)

1. **Nome de árbitro chega a 50 caracteres.** "Fernando Antonio Mendes de
   Salles Nascimento Filho" existe e precisa caber. Defina a regra: trunca,
   abrevia o meio, quebra em duas linhas? Mostre o caso extremo no artboard,
   não só nome curto.
2. **Nome de clube vai a 23 caracteres** ("Fortaleza Esporte Clube").
3. **84% das células da matriz não têm amostra suficiente** (menos de 5 jogos
   do par clube × árbitro). A matriz é majoritariamente vazia — esse é o estado
   normal, não a exceção. Desenhe o vazio como cidadão de primeira classe.
4. **Escudos** vêm de `conteudo.cbf.com.br/clubes/{id}/escudo.jpg`, quadrados,
   fundo branco, qualidade irregular. Assuma que alguns vão falhar e defina o
   fallback.
5. **A temporada corrente é parcial** — em 2026 alguns times têm 26 jogos e
   outros 27. A interface precisa comunicar "em andamento" sem poluir.

### Design system

Entregue junto com os artboards:

- Tokens de cor, com a escala divergente do índice de favorecimento resolvida
  (vermelho = favorecido, azul = prejudicado, neutro = sem sinal) — precisa
  passar em contraste AA e continuar legível para daltonismo vermelho-verde,
  que é justamente onde essa escala costuma falhar
- Escala tipográfica e a fonte tabular pros números
- Espaçamento, raio, elevação
- Componentes: card de KPI, linha de tabela, badge de forma, célula de matriz,
  item de sidebar, seletor de temporada, estado vazio
- Especificação de movimento: o que anima, duração, easing, e o
  comportamento sob `prefers-reduced-motion`

### Stack de destino

React 19 + Vite, CSS puro com variáveis (o projeto não usa Tailwind nem
biblioteca de componentes, e não quero adicionar). Charts hoje são SVG à mão.
Mantenha o sistema implementável nesse contexto — sem depender de framework de
UI.
```

---

## Caminho sugerido

**Fase 1 — direção.** Cole o prompt acima no Claude Design. Peça primeiro
2 artboards (Dashboard e Classificação) pra validar a direção antes de
desenhar as outras cinco telas. Errar cedo é barato.

**Fase 2 — cobertura.** Aprovada a direção, peça o resto: Árbitros, Perfil,
Confrontos e os estados vazios. Insista nos casos extremos (nome de 50 chars,
matriz vazia) — é onde mockup bonito costuma quebrar.

**Fase 3 — sistema.** Peça os tokens e a especificação de componentes. Sem
isso a implementação vira adivinhação.

**Fase 4 — crítica.** Antes de implementar, rode a skill `design:design-critique`
e a `design:accessibility-review` sobre o resultado. A escala divergente do
índice é o ponto mais provável de falha de acessibilidade.

**Fase 5 — implementação.** Volta pra cá. Antes de qualquer código, o backend
precisa de dois ajustes:
- `Team` ganha campo de escudo (o `clube_id` já vem no payload da CBF, só não
  é gravado)
- os KPIs de árbitro (cartões/jogo, z-score, viés de mandante) não existem em
  `queries.py` ainda — hoje só existe o índice de favorecimento por par

## Skills e agentes

| Quando | O quê | Por quê |
|---|---|---|
| Fase 1-2 | skill `design` | Cria o canvas multi-artboard. É o ponto de entrada |
| Fase 1-2 | skill `dataviz` | Escala divergente, matriz, densidade de tabela. Traz validador de paleta |
| Fase 2 | skill `motion-design` | "Cards animados" com timing e easing que não viram enfeite |
| Fase 3 | skill `design:design-system` | Estrutura de tokens e componentes |
| Fase 3 | skill `responsive-design` | Container queries e tipografia fluida — a matriz é o caso difícil |
| Fase 4 | skill `design:accessibility-review` | Contraste e daltonismo na escala divergente |
| Fase 4 | skill `design:design-critique` | Crítica antes de virar código |
| Fase 5 | agente `ai-team-dev` | Implementação do React seguindo os tokens |
