---
titulo: Achados do ApitaCerto para posts
versao: 1
gerado_em: 2026-09-24
dados_ate: "Brasileirão 2018–2026 (2026 até a rodada 27)"
fonte: "Súmulas e escalas oficiais da CBF, gravadas no banco do ApitaCerto"
site: https://147-15-76-139.sslip.io
repositorio: https://github.com/soutes/apitacerto
total_achados: 37
---

# Achados do ApitaCerto para posts

Arquivo pensado para ser lido por uma automação de postagens (criação de
imagem, legenda e agendamento). Cada achado é uma seção `##` com um bloco
YAML de campos fixos (esquema abaixo). O texto fora dos blocos é para
humanos.

## Regras editoriais (valem para todo post)

1. **A manchete tem que ser verdadeira sozinha**, sem depender da legenda.
2. **Arredondou para cima, escreve "quase"** (ex.: 1,93 → "quase 2").
3. **Nunca afirmar ou insinuar desonestidade de árbitro.** Nome de árbitro só
   aparece com fato de estilo (rigor) ou de escala (CBF), nunca como suspeito.
4. **`risco: medio` ou `risco: alto` → a `ressalva` entra obrigatoriamente na
   legenda**, com o mesmo sentido (pode reescrever, não pode cortar).
5. **Achados com `atualizacao: dinamico` mudam toda semana**: recalcular antes
   de publicar (ver `reproduzir`). Os números aqui são o retrato de
   `gerado_em`.
6. **Imagem**: sem escudo, sem logo de clube, de patrocinador ou da CBF, sem
   rosto reconhecível.
7. **"Nunca"** nos achados de clubes quer dizer "nunca desde 2018" (8
   temporadas completas).

## Esquema dos blocos

```yaml
id: slug-unico                 # estável; use como chave na automação
categoria: casa-fora | placar | var-tendencia | mando-viagem | grandes-regioes | arbitros | pessoas | flamengo | clubes
manchetes:                     # 1ª = versão em %/número; 2ª = versão em proporção simples
  - "..."
calculo: "..."                 # a conta que sustenta a manchete, em pt-BR
numeros: {}                    # valores brutos, ponto decimal, para gráfico/checagem
periodo: "..."
significancia: "..."           # teste estatístico, ou null quando é contagem direta
risco: baixo | medio | alto
ressalva: "..."                # obrigatória na legenda se risco != baixo; null se baixo
atualizacao: estatico | dinamico
reproduzir: "..."              # de onde recalcular (endpoint da API ou tabela do banco)
destaque: true | false         # aposta de maior alcance
```

---

## F1 · Adversários do Flamengo são expulsos 93% mais vezes

```yaml
id: flamengo-expulsoes-93pct
categoria: flamengo
manchetes:
  - "Adversários do Flamengo são expulsos 93% mais vezes"
calculo: "87 expulsões dos adversários contra 45 do Flamengo: 87 é 93,3% maior que 45"
numeros: {adversarios: 87, flamengo: 45, razao: 1.933, variacao_pct: 93.3, jogos: 331}
periodo: "2018–2026"
significancia: "p = 0,009 isolado; q = 0,22 corrigido entre 26 clubes (para acompanhar, não sinal forte)"
risco: alto
ressalva: "É o maior desequilíbrio da liga, mas comparando 26 clubes algum sempre fica no topo por sorte: pela régua do projeto o número fica em 'para acompanhar', não em 'sinal forte'. Não prova favorecimento."
atualizacao: dinamico
reproduzir: "match_events tipo RED_CARD por lado nos jogos do Flamengo; teste binomial contra a proporção de amarelos do mesmo clube"
destaque: true
```

## F2 · Para cada 1 expulsão do Flamengo, quase 2 dos adversários

```yaml
id: flamengo-expulsoes-2x1
categoria: flamengo
manchetes:
  - "Para cada 1 expulsão do Flamengo, quase 2 dos adversários"
  - "Quase 2 expulsões dos adversários para cada 1 do Flamengo"
calculo: "87 ÷ 45 = 1,93 para 1 (por isso 'quase 2')"
numeros: {adversarios: 87, flamengo: 45, razao: 1.933}
periodo: "2018–2026"
significancia: "p = 0,009 isolado; q = 0,22 corrigido entre 26 clubes (para acompanhar)"
risco: alto
ressalva: "Maior desequilíbrio da liga, mas pode ser acaso entre 26 clubes; não prova favorecimento. Palmeiras, que domina tanto quanto, tem 66 × 61."
atualizacao: dinamico
reproduzir: "igual a flamengo-expulsoes-93pct"
destaque: true
```

---

## 01 · O visitante leva 735 cartões a mais

```yaml
id: visitante-735-cartoes
categoria: casa-fora
manchetes:
  - "O time visitante leva 735 cartões a mais que o dono da casa"
  - "Para cada 100 cartões do mandante, o visitante leva 109"
calculo: "9.270 cartões do visitante contra 8.535 do mandante: 8,6% a mais"
numeros: {visitante: 9270, mandante: 8535, diferenca: 735, variacao_pct: 8.6}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "match_events YELLOW_CARD + RED_CARD por lado (mandante/visitante)"
destaque: false
```

## 02 · O visitante é expulso 21% mais vezes

```yaml
id: visitante-expulsoes-21pct
categoria: casa-fora
manchetes:
  - "O visitante é expulso 21% mais vezes"
  - "Para cada 5 expulsões do time da casa, 6 do visitante"
calculo: "622 vermelhos do visitante contra 513 do mandante: 622 ÷ 513 = 1,21"
numeros: {visitante: 622, mandante: 513, razao: 1.212}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "match_events RED_CARD por lado"
destaque: false
```

## 03 · Sem torcida, até o time da casa passou a levar mais amarelo

```yaml
id: 2020-sem-torcida-amarelos
categoria: casa-fora
manchetes:
  - "Sem torcida, até o time da casa passou a levar mais amarelo"
  - "2020 foi o único ano em que o mandante levou mais cartão que o visitante"
calculo: "Em 2020 (sem público): 892 amarelos do mandante contra 874 do visitante. Nas outras 8 temporadas, o visitante levou mais. Em temporada normal, são cerca de 95 cartões a mais para o visitante."
numeros: {amarelos_mandante_2020: 892, amarelos_visitante_2020: 874, diferenca_media_temporada_normal: 95}
periodo: "2018–2026"
significancia: "Hipótese H2, registrada antes de ver os dados: confirmada (p = 0,018)"
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "match_events YELLOW_CARD por lado e por temporada; hipótese H2 em GET /statistics"
destaque: true
```

## 04 · Depois do apito final, o visitante leva 45% mais cartões

```yaml
id: pos-jogo-visitante
categoria: casa-fora
manchetes:
  - "Depois do apito final, o visitante leva 45% mais cartões"
  - "Para cada 2 cartões pós-jogo do mandante, quase 3 do visitante"
calculo: "113 cartões do visitante contra 78 do mandante depois do fim do jogo: 113 ÷ 78 = 1,45 (191 no total, 85 vermelhos)"
numeros: {visitante: 113, mandante: 78, total: 191, vermelhos: 85, razao: 1.449}
periodo: "2018–2026"
significancia: "p = 0,05 (no limite)"
risco: medio
ressalva: "Diferença no limite estatístico: chama atenção, não é prova."
atualizacao: dinamico
reproduzir: "match_events com period = 'PJ' (pós-jogo), por lado"
destaque: false
```

## 05 · Quem está perdendo é expulso 55% mais

```yaml
id: placar-perdendo-expulso
categoria: placar
manchetes:
  - "Quem está perdendo é expulso 55% mais do que quem está ganhando"
  - "Para cada 2 expulsões de quem ganha, 3 de quem perde"
calculo: "Modelo que compara o mesmo minuto de jogo: perdendo, +21% de expulsões em relação ao empate; ganhando, −22%. 1,21 ÷ 0,78 = 1,55"
numeros: {perdendo_vs_empate: 1.209, ganhando_vs_empate: 0.782, razao: 1.546}
periodo: "2018–2026"
significancia: "perdendo p = 0,01; ganhando p = 0,003 (regressão de Poisson com minuto do jogo)"
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "match_events: placar reconstruído pelos gols a cada cartão; Poisson de expulsões por situação do placar e faixa de minuto, com exposição em minutos"
destaque: true
```

## 06 · A cera tem preço

```yaml
id: placar-ganhando-cera
categoria: placar
manchetes:
  - "A cera tem preço: quem está ganhando leva 9% mais cartão"
calculo: "Mesmo modelo: time na frente do placar contra time empatando, no mesmo minuto de jogo"
numeros: {ganhando_vs_empate: 1.093}
periodo: "2018–2026"
significancia: "p < 0,001"
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "igual a placar-perdendo-expulso, com todos os cartões"
destaque: false
```

## 07 · Com o VAR, as expulsões aumentaram 33%

```yaml
id: var-expulsoes
categoria: var-tendencia
manchetes:
  - "Com o VAR, as expulsões aumentaram 33%"
  - "A cada 3 expulsões antes do VAR, 4 depois"
calculo: "0,27 vermelho por jogo em 2018 (sem VAR) contra 0,35 de 2019 em diante (com VAR)"
numeros: {sem_var: 0.266, com_var: 0.353, razao: 1.327}
periodo: "2018 × 2019–2026"
significancia: "p = 0,005"
risco: medio
ressalva: "Só existe um ano sem VAR na base (2018)."
atualizacao: estatico
reproduzir: "match_events RED_CARD por jogo, 2018 contra 2019+"
destaque: false
```

## 08 · Os árbitros tiram mais cartão hoje

```yaml
id: tendencia-cartoes
categoria: var-tendencia
manchetes:
  - "Os árbitros tiram mais cartão hoje: 5,7 por jogo nos últimos 4 anos, contra 5,0 nos 4 anteriores"
  - "As expulsões subiram 21%: eram 3 a cada 10 jogos, agora são quase 4"
calculo: "Média de 2022 a 2025 contra média de 2018 a 2021 (temporadas completas): cartões 5,73 contra 5,05 por jogo (+14%); vermelhos 0,370 contra 0,307 por jogo (+21%). Não compara com um ano só para não escolher o pico (2024 teve 6,01)."
numeros: {cartoes_jogo_2018_2021: 5.05, cartoes_jogo_2022_2025: 5.73, variacao_cartoes_pct: 13.6, vermelhos_jogo_2018_2021: 0.307, vermelhos_jogo_2022_2025: 0.370, variacao_vermelhos_pct: 20.8, cartoes_jogo_2026_parcial: 5.33, vermelhos_jogo_2026_parcial: 0.398}
periodo: "2018–2021 × 2022–2025 (2026 fora: temporada incompleta)"
significancia: null
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "match_events cartões por jogo e por temporada"
destaque: false
```

## 09 · Na última rodada, o árbitro guarda o cartão

```yaml
id: ultima-rodada-menos-cartoes
categoria: var-tendencia
manchetes:
  - "Na última rodada, o árbitro guarda o cartão: 20% a menos"
  - "1 cartão a menos por jogo na rodada final"
calculo: "4,36 cartões por jogo na rodada 38 contra 5,42 nas outras rodadas"
numeros: {rodada_38: 4.36, demais: 5.42, variacao_pct: -19.6}
periodo: "2018–2025"
significancia: "p = 0,001"
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "fixtures.round = 38 contra as demais, cartões por jogo"
destaque: false
```

## 10 · Vender o mando custa caro

```yaml
id: mando-vendido
categoria: mando-viagem
manchetes:
  - "Vender o mando custa caro: o visitante vence o dobro de vezes"
  - "Longe de casa, o 'mandante' vence menos da metade do normal"
calculo: "Em 35 jogos com mando fora do estado (quase todos em Brasília): visitante vence 51% (normal: 25%); mandante vence 23% (normal: 48%)"
numeros: {jogos: 35, mandante_vence_pct: 22.9, visitante_vence_pct: 51.4, normal_mandante_pct: 47.8, normal_visitante_pct: 24.6}
periodo: "2018–2026"
significancia: "p = 0,0035"
risco: medio
ressalva: "Amostra pequena (35 jogos)."
atualizacao: dinamico
reproduzir: "fixtures com venue_state diferente do estado do mandante"
destaque: true
```

## 11 · Viajar 3 mil km não muda nada

```yaml
id: distancia-nao-pesa
categoria: mando-viagem
manchetes:
  - "Viajar 3 mil km não muda nada: o visitante pontua igual"
calculo: "Visitante faz 1,04 ponto por jogo vindo de outra região e 1,07 vindo do mesmo estado (3% de diferença)"
numeros: {outra_regiao: 1.042, mesmo_estado: 1.073, mesma_regiao: 0.951}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "fixtures: pontos do visitante por par de estados/regiões dos clubes"
destaque: false
```

## 12 · Os grandes não ganham mais pênaltis

```yaml
id: grandes-penaltis
categoria: grandes-regioes
manchetes:
  - "Os grandes NÃO ganham mais pênaltis"
  - "Contra os pequenos, os grandes fazem 60% dos gols, mas só 56% dos gols de pênalti"
calculo: "Nos jogos grande × pequeno: 2.230 contra 1.497 gols de bola rolando (60%); 235 contra 182 gols de pênalti (56%)"
numeros: {gols_bola_rolando_grandes: 2230, gols_bola_rolando_pequenos: 1497, gols_penalti_grandes: 235, gols_penalti_pequenos: 182}
periodo: "2018–2026"
significancia: "p = 0,15 (não há excesso)"
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "12 grandes (FLA, PAL, COR, SAO, SAN, VAS, FLU, BOT, GRE, INT, CAM, CRU); gols por detail em match_events"
destaque: true
```

## 13 · Na casa do grande, o pequeno leva mais amarelo

```yaml
id: grandes-em-casa-amarelos
categoria: grandes-regioes
manchetes:
  - "Na casa de um time grande, o time pequeno leva 23% mais cartão amarelo. Quando o grande é quem visita, os dois levam quase o mesmo"
  - "No estádio do grande: para cada 10 amarelos do grande, 12 do pequeno. No estádio do pequeno: 10 a 10"
  - "O que pesa é jogar fora de casa, não enfrentar um time grande"
calculo: "Jogos grande × pequeno. No estádio do grande: 2.184 amarelos do pequeno contra 1.780 do grande (1,23 para 1). No estádio do pequeno: 2.143 amarelos do pequeno contra 2.097 do grande (1,02 para 1)"
numeros: {grande_casa_pequeno: 2184, grande_casa_grande: 1780, grande_fora_pequeno: 2143, grande_fora_grande: 2097}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "igual a grandes-penaltis, separado por mando"
destaque: true
```

## 14 · Nordeste e os pênaltis

```yaml
id: nordeste-sudeste-penaltis
categoria: grandes-regioes
manchetes:
  - "O Nordeste faz 30% menos gols que o Sudeste, mas o mesmo número de gols de pênalti"
calculo: "Nos confrontos Nordeste × Sudeste: 562 contra 812 gols de bola rolando; 71 contra 71 gols de pênalti"
numeros: {gols_ne: 562, gols_se: 812, penaltis_ne: 71, penaltis_se: 71}
periodo: "2018–2026"
significancia: "p = 0,033 sem correção; não sobrevive à correção para 6 testes regionais"
risco: medio
ressalva: "Não sobrevive à correção de múltiplas comparações: é 'para acompanhar', não conclusão."
atualizacao: estatico
reproduzir: "fixtures por região dos clubes; gols por detail"
destaque: false
```

## 15 · Pênalti por árbitro: o número engana

```yaml
id: arbitro-penaltis-acaso
categoria: arbitros
manchetes:
  - "O 'árbitro do pênalti' não existe. Com um, sai gol de pênalti a cada 3 jogos. Com outro, a cada 8. Somando 26 árbitros, essa diferença é do tamanho que a sorte sozinha produz."
  - "Com um árbitro, 2,7 vezes mais gol de pênalti do que com outro. A sorte sozinha já daria essa diferença."
  - "Seu time pegou o 'árbitro do pênalti'? Ele não existe. Um apita gol de pênalti a cada 3 jogos, outro a cada 8, e os números de 26 árbitros mostram que isso é variação normal."
calculo: "0,337 contra 0,125 gol de pênalti por jogo entre árbitros com 40+ jogos: 0,337 ÷ 0,125 = 2,7. A variação entre os 26 árbitros cabe no acaso"
numeros: {maximo_por_jogo: 0.337, minimo_por_jogo: 0.125, razao: 2.7, arbitros: 26}
periodo: "2018–2026"
significancia: "Dispersão compatível com o acaso (p = 0,19)"
risco: medio
ressalva: "Não citar nomes como 'árbitro do pênalti': a variação é a que o acaso produz."
atualizacao: estatico
reproduzir: "gols de pênalti por jogo por árbitro (40+ jogos); qui-quadrado de dispersão"
destaque: true
```

## 16 · Nenhum árbitro é "caseiro"

```yaml
id: arbitro-caseiro-acaso
categoria: arbitros
manchetes:
  - "Com um árbitro, o mandante vence 1 em cada 3 jogos; com outro, mais da metade. E também é acaso"
calculo: "33% a 56% de vitórias do mandante entre os 26 árbitros com 40+ jogos"
numeros: {minimo_pct: 32.6, maximo_pct: 56.0, arbitros: 26}
periodo: "2018–2026"
significancia: "Dispersão compatível com o acaso (p = 0,32)"
risco: medio
ressalva: "A variação é a que o acaso produz; não chamar árbitro de caseiro."
atualizacao: estatico
reproduzir: "vitória do mandante por árbitro (40+ jogos); qui-quadrado de dispersão"
destaque: false
```

## 17 · A loteria do apito

```yaml
id: loteria-do-apito
categoria: arbitros
manchetes:
  - "O árbitro escalado muda em até 51% os cartões do seu jogo"
  - "O mais rigoroso dá 3 cartões para cada 2 do mais leve"
calculo: "Rigor de +20% contra −20% em relação ao esperado para os mesmos jogos: 1,20 ÷ 0,80 = 1,5 (cerca de 2,2 cartões por jogo)"
numeros: {rigor_max: 1.201, rigor_min: 0.797, razao: 1.51, cartoes_por_jogo: 2.2}
periodo: "2018–2026"
significancia: "13 dos 42 árbitros com 15+ jogos têm rigor claramente diferente da média"
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "GET /statistics → refereeStrictness (rigor encolhido)"
destaque: false
```

## 18 · Santa Catarina apita muito

```yaml
id: arbitros-sc
categoria: arbitros
manchetes:
  - "Árbitros de Santa Catarina apitam 1 em cada 8 jogos; clubes catarinenses ocupam 1 em cada 27 vagas"
calculo: "12,9% dos jogos com árbitro catarinense contra 3,7% das participações de clubes catarinenses: 3,5 vezes"
numeros: {jogos_arbitro_sc_pct: 12.9, vagas_clubes_sc_pct: 3.7, sp_pct: 17.0, rs_pct: 14.1, rj_pct: 11.0}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: "Efeito da regra que evita árbitro do mesmo estado dos clubes."
atualizacao: estatico
reproduzir: "referees.uf dos jogos contra teams.state das participações"
destaque: false
```

## 19 · Árbitro FIFA não muda nada

```yaml
id: arbitro-fifa-igual
categoria: arbitros
manchetes:
  - "Árbitro FIFA não é mais rigoroso nem mais caseiro"
calculo: "Cartões 5,37 contra 5,47 por jogo; vermelhos 0,35 contra 0,36; vitória do mandante 46% contra 48%"
numeros: {cartoes_fifa: 5.37, cartoes_outros: 5.47, mandante_fifa_pct: 46.4, mandante_outros_pct: 47.5}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: estatico
reproduzir: "fixtures.referee_category contendo FIFA contra as demais"
destaque: false
```

## 20 · O mais expulso não é jogador

```yaml
id: mais-expulso-auxiliar
categoria: pessoas
manchetes:
  - "O mais expulso do Brasileirão desde 2018 não é jogador: é um auxiliar técnico"
calculo: "Charles Hembert, auxiliar de Rogério Ceni: 9 vermelhos. O jogador mais expulso, Gabigol, tem 7"
numeros: {charles_hembert: 9, gaston_liendo: 7, joao_martins: 7, gabigol: 7, abel_ferreira: 6}
periodo: "2018–2026"
significancia: null
risco: medio
ressalva: "Fato público sobre pessoas nomeadas: manter o tom informativo."
atualizacao: dinamico
reproduzir: "match_events RED_CARD por player_name (a súmula inclui a comissão técnica)"
destaque: true
```

## 21 · A comissão do Palmeiras

```yaml
id: comissao-palmeiras
categoria: pessoas
manchetes:
  - "A comissão técnica do Palmeiras foi expulsa quase o dobro de vezes que o jogador mais expulso do país"
calculo: "Abel Ferreira (6) + João Martins (7) = 13, contra 7 do Gabigol: 13 ÷ 7 = 1,86"
numeros: {abel_ferreira: 6, joao_martins: 7, total: 13, gabigol: 7}
periodo: "2018–2026"
significancia: null
risco: medio
ressalva: "Fato público sobre pessoas nomeadas: manter o tom informativo."
atualizacao: dinamico
reproduzir: "igual a mais-expulso-auxiliar"
destaque: true
```

## 22 · Gabigol e os pênaltis

```yaml
id: gabigol-penaltis
categoria: pessoas
manchetes:
  - "1 em cada 4 gols do Gabigol foi de pênalti"
calculo: "26 de 105 gols (24,8%). É também o artilheiro do período e o 2º mais advertido (61 amarelos)"
numeros: {gols: 105, gols_penalti: 26, amarelos: 61, vermelhos: 7}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "match_events GOAL por player_name e detail"
destaque: false
```

## 23 · Kannemann e o mesmo árbitro

```yaml
id: kannemann-arbitro
categoria: pessoas
manchetes:
  - "Kannemann levou do mesmo árbitro mais que o dobro de cartões do esperado"
calculo: "13 cartões em 23 jogos do Grêmio apitados por Bruno Arleu, contra cerca de 6 esperados pelo ritmo do jogador. Nenhum desses jogos foi Gre-Nal. Em sorteios, algo assim aparece em 2% das simulações"
numeros: {cartoes: 13, jogos: 23, esperado: 5.7, simulacoes_pct: 2.25}
periodo: "2018–2026"
significancia: "Simulação com 532 jogadores de 10+ cartões: 13 ou mais em 2% dos sorteios"
risco: alto
ressalva: "Curiosidade, não prova de perseguição: entre milhares de combinações jogador × árbitro, alguma sempre se destaca."
atualizacao: estatico
reproduzir: "match_events cartões por player_name × árbitro; simulação distribuindo os cartões do jogador pelos jogos do clube"
destaque: false
```

## 24 · Recorde de cartões num jogo

```yaml
id: recorde-cartoes-jogo
categoria: pessoas
manchetes:
  - "Um único jogo teve 17 cartões"
calculo: "Corinthians × Atlético-MG, 2024"
numeros: {cartoes: 17, temporada: 2024}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "máximo de cartões por fixture"
destaque: false
```

## 25 · Flamengo e os pênaltis

```yaml
id: flamengo-penaltis
categoria: flamengo
manchetes:
  - "O Flamengo teve quase o dobro de gols de pênalti a favor. E o número engana"
calculo: "49 a favor contra 25 contra (1,96). É a mesma proporção dos gols de bola rolando do Flamengo: 66% contra 65%"
numeros: {a_favor: 49, contra: 25, razao: 1.96, share_penalti_pct: 66.2, share_gols_pct: 64.6}
periodo: "2018–2026"
significancia: "Proporção igual à dos gols de bola rolando (sem excesso)"
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "match_events GOAL detail = 'penalti' nos jogos do Flamengo"
destaque: false
```

## 26 · Flamengo leva pouco cartão

```yaml
id: flamengo-menos-cartao
categoria: flamengo
manchetes:
  - "O Flamengo é o grande que menos leva cartão"
calculo: "2,35 cartões por jogo. Só a Chapecoense leva menos (2,34)"
numeros: {flamengo: 2.35, chapecoense: 2.34}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "cartões próprios por jogo por clube (100+ jogos)"
destaque: false
```

---

## 27 · A linha do rebaixamento

```yaml
id: linha-rebaixamento-rodada
categoria: clubes
manchetes:
  - "Depois de 27 jogos, nenhum clube com menos de 25 pontos escapou da queda"
  - "E nenhum com mais de 35 caiu"
calculo: "Recorde de 8 temporadas completas (2018–2025). Em 2026, Remo e Chapecoense estão abaixo da linha"
numeros: {jogos: 27, menor_que_escapou: 25, maior_que_caiu: 35}
periodo: "2018–2025 (linha) · 2026 (clubes abaixo)"
significancia: null
risco: baixo
ressalva: "'Nunca' = desde 2018."
atualizacao: dinamico
reproduzir: "GET /club-insights → linha de corte depois de R jogos (aba Análises dos clubes)"
destaque: true
```

## 28 · Lanterna depois da 20ª rodada

```yaml
id: lanterna-rodada-20
categoria: clubes
manchetes:
  - "Lanterna depois da 20ª rodada: 8 em cada 8 caíram"
calculo: "100% das temporadas completas desde 2018"
numeros: {temporadas: 8, cairam: 8, a_partir_do_jogo: 20}
periodo: "2018–2025"
significancia: null
risco: baixo
ressalva: "'Nunca' = desde 2018."
atualizacao: dinamico
reproduzir: "GET /club-insights → lanterna por rodada contra destino final"
destaque: false
```

## 29 · A lenda dos 45 pontos

```yaml
id: lenda-45-pontos
categoria: clubes
manchetes:
  - "44 pontos sempre bastaram: a lenda dos 45 está errada"
calculo: "O rebaixado com mais pontos fez 43 (Grêmio 2021, Santos 2023, Ceará 2025). Já escapou quem fez 39 (Ceará 2019)"
numeros: {maior_rebaixado: 43, menor_salvo: 39}
periodo: "2018–2025"
significancia: null
risco: baixo
ressalva: "'Nunca' = desde 2018."
atualizacao: dinamico
reproduzir: "GET /club-insights → pontos finais do 16º e do 17º por temporada"
destaque: true
```

## 30 · O líder do turno

```yaml
id: lider-turno-campeao
categoria: clubes
manchetes:
  - "O líder do fim do turno foi campeão em 5 de cada 8 anos"
calculo: "62,5%. Depois de 34 rodadas, 7 em 8"
numeros: {turno: 5, rodada_34: 7, temporadas: 8}
periodo: "2018–2025"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "GET /club-insights → líder por rodada contra campeão"
destaque: false
```

## 31 · Quem sobe cai

```yaml
id: promovidos-caem
categoria: clubes
manchetes:
  - "1 em cada 3 clubes que sobem cai no mesmo ano"
calculo: "9 de 28 promovidos desde 2019. Dois foram ao G-6: Grêmio 2023 (2º) e Mirassol 2025 (4º, na estreia)"
numeros: {promovidos: 28, rebaixados: 9, g6: 2}
periodo: "2019–2025"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "GET /club-insights → teams[].promoted e fate"
destaque: false
```

## 32 · Quem marca primeiro

```yaml
id: primeiro-gol
categoria: clubes
manchetes:
  - "Quem marca primeiro vence quase 7 em cada 10 jogos"
  - "Virada só em 1 de cada 10"
calculo: "2.069 vitórias de quem abriu o placar em 3.019 jogos com gol (68,5%); quem marcou primeiro perdeu em 10,5%"
numeros: {jogos_com_gol: 3019, vitorias_de_quem_abriu: 2069, empates: 632, viradas_pct: 10.5}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "GET /club-insights → firstGoal"
destaque: false
```

## 33 · Sair na frente em casa e fora

```yaml
id: primeiro-gol-casa-fora
categoria: clubes
manchetes:
  - "O mandante que sai na frente vence 3 em cada 4; o visitante, 6 em cada 10"
calculo: "74,9% contra 58,4%"
numeros: {mandante_pct: 74.9, visitante_pct: 58.4}
periodo: "2018–2026"
significancia: null
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "GET /club-insights → firstGoal.homeFirstWins/homeFirst e awayFirstWins/awayFirst"
destaque: false
```

## 34 · O campeonato mudou

```yaml
id: campeonato-mais-gols
categoria: clubes
manchetes:
  - "O Brasileirão ficou 22% mais goleador"
  - "O 0 a 0 caiu pela metade"
calculo: "Gols por jogo: 2,18 (2018) → 2,66 (2026). 0 a 0: 11,3% → 5,6% dos jogos"
numeros: {gols_jogo_2018: 2.18, gols_jogo_2026: 2.66, zero_zero_2018_pct: 11.3, zero_zero_2026_pct: 5.6}
periodo: "2018–2026 (2026 em andamento)"
significancia: null
risco: baixo
ressalva: "2026 ainda está em andamento."
atualizacao: dinamico
reproduzir: "GET /club-insights → seasons[].goalsPerGame e zeroZeroPct"
destaque: false
```

## 35 · "Time de returno" é mito

```yaml
id: time-de-returno-mito
categoria: clubes
manchetes:
  - "'Time de returno' é mito: nenhum clube repete o padrão"
calculo: "Nenhum clube melhora ou piora no returno de forma que o cara ou coroa não explique; o mais 'consistente' (Atlético-MG) foi pior em 5 de 8 anos"
numeros: {clubes_testados: 17, com_padrao: 0}
periodo: "2018–2025"
significancia: "Teste binomial por clube, nenhum com p < 0,05"
risco: baixo
ressalva: null
atualizacao: dinamico
reproduzir: "GET /club-insights → pontos do jogo 19 e do jogo 38 por clube e temporada"
destaque: false
```

---

## Modelo de imagem (estilo padrão: pôster em risografia)

Placeholders entre chaves. `{HERO}` é o número grande; `{FRASE_1}` a
`{FRASE_3}` são as linhas da manchete; `{DADO}` é a linha de proporção;
`{SELO}` é o texto do carimbo; `{RODAPE}` identifica período e fonte.

```text
Vertical social media poster, 4:5 (1080x1350), risograph print aesthetic — NOT a photo. Only three inks: fluorescent red (#FF3B30), black, and cream paper (#F3EBDD). Visible halftone dots, paper grain, slight ink misregistration between red and black layers, uneven ink coverage, tiny dust specks. Bold editorial Swiss grid, asymmetric, lots of cream negative space.

COMPOSITION: a gigantic "{HERO}" in fluorescent red ink, ultra-bold condensed grotesk, left-aligned and fully inside the canvas, occupying the left ~75% of the width. ALL CHARACTERS MUST BE FULLY VISIBLE: nothing overlaps the number. In the free right column, a cut-out paper collage with rough scissor edges and a soft drop shadow: {ILUSTRACAO}. A small circular rubber-stamp badge in black ink, tilted about -12 degrees, placed away from the digits.

TYPOGRAPHY (Portuguese, exact text, ultra-condensed bold grotesk like Anton / Druk, all caps unless noted):
top-left, black, stacked: "{FRASE_1} / {FRASE_2} / {FRASE_3}"
hero number, fluorescent red: "{HERO}"
stamp badge text, black: "{SELO}"
bottom-left, black, big: "{DADO}"
bottom strip, black bar with cream text: "{RODAPE}"
tiny bottom-right, black: "APITACERTO · DADOS"

No club crest, no club or sponsor logos, no CBF logo, no real faces, no watermark.
```

Sugestões de `{ILUSTRACAO}` (sempre recorte em retícula preta, sem rosto):
- cartões: "a black halftone duotone image of a referee's arm (arm and hand only) raising a red card, the card printed in fluorescent red";
- torcida: "a black halftone crowd in the stands, arms raised, no recognizable faces";
- estádio vazio: "black halftone empty stadium seats";
- placar: "a vintage split-flap stadium scoreboard printed in black ink";
- pênalti: "a black halftone football on the penalty spot".

**Negative prompt padrão:**

```text
photorealistic, photograph, 3D render, CGI, glossy, night stadium, rain, dark background, gradients, neon glow, club crest, logos, recognizable face, watermark, misspelled text, extra text, gibberish letters, more than three colors, number covered by illustration
```

## Modelo de legenda

```text
{FATO — a manchete com o número}
{CONTEXTO — a conta em uma frase}
{RESSALVA — obrigatória se risco != baixo}
Todos os números, jogo a jogo, no ApitaCerto: https://147-15-76-139.sslip.io
```
