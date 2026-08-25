# 🔬 Auditoria Técnica — Sistema LotoFácil IA

**Data:** 2026-08-21 · **Base:** 3.767 concursos (concurso 1 → 3767) · **Branch:** `arena/01a02463-lotofacil-system`

---

## 1. Resumo executivo

O sistema é **elaborado e funcional** — carrega o histórico completo, treina 14 motores + 15 oráculos, gera cartelas, confere contra a API da Caixa e mantém lotes. Porém, a auditoria encontrou:

| Categoria | Quantidade | Severidade |
|---|---|---|
| Código morto / módulos nunca chamados | 6 módulos | Alta |
| Funcionalidades "fantasma" (stubs) | 2 (backtesting, finanças) | Alta |
| Bugs de lógica de aprendizado | 1 (reforço perverso) | Alta |
| Métricas enganosas | 2 (cobertura, score) | Média |
| Violações de boas práticas (seed global, etc.) | 3 | Baixa |

E a conclusão mais importante, de natureza **matemática**, está na Seção 3: **nenhum dos módulos atuais consegue — e nenhum módulo futuro conseguirá — "prever" 13/14/15 pontos com vantagem sobre o acaso**. Isso não é uma limitação do código: é uma propriedade do sorteio.

---

## 2. Arquitetura atual

```
app.py ───────────────────── Flask (rotas + API)
 ├─ core/cerebro_ia.py ───── CérebroIA (14 motores + oráculo + ciclo autônomo)
 ├─ core/oraculo_convergente.py ─ 15 oráculos que votam (consenso)
 ├─ core/conferencia.py ──── conferência contra API da Caixa
 ├─ core/bitmatrix.py ────── bitmasks (AND/OR/XOR)
 ├─ core/data_loader.py ──── ingestão do histórico
 ├─ core/financeiro.py ───── finanças (NÃO integrado)
 ├─ core/ia_monitor.py ───── auditoria/transparência (NÃO integrado)
 └─ [módulos órfãos]
     ├─ core/markov_engine.py      — nunca importado pelo Cérebro
     ├─ core/fisica_quantica.py    — nunca importado pelo Cérebro
     ├─ core/filtros_gaussianos.py — duplicado pelo MotorGaussiano interno
     ├─ core/heavyweight_engine.py — MotorExaustaoUniverso nunca instanciado
     ├─ core/covering_designs.py   — CoveringDesigns nunca instanciado
     └─ core/singularidade.py      — arquivo VAZIO (0 bytes)
```

**Base de dados:** `resultados` (3.767), `cartelas` (70), `lotes_cartelas` (3), `cartela_do_dia` (22).
Tabelas `financeiro`, `ia_sessoes`, `ia_previsao_vs_real` **vazias** (0 registros) — os módulos que deveriam alimentá-las não são invocados pelo fluxo principal.

---

## 3. A verdade irredutível (matemática, não opinião)

Cada sorteio da Lotofácil escolhe 15 dezenas de um universo de 25, de forma **independente e uniforme**. O número de acertos de uma cartela segue a distribuição **hipergeométrica**:

```
P(k acertos) = C(15,k) · C(10,15−k) / C(25,15)
```

Valores exatos (calculados a partir do próprio banco):

| Faixa | Probabilidade exata | 1 em ... |
|---|---|---|
| 11 pontos | 8,769 % | 1 em 11 |
| 12 pontos | 1,670 % | 1 em 60 |
| **13 pontos** | **0,1446 %** | **1 em 691** |
| **14 pontos** | **0,00459 %** | **1 em ~21.800** |
| **15 pontos** | **0,0000306 %** | **1 em 3.268.760** |

**Consequências inescapáveis:**

1. **Valor esperado negativo.** Com prêmios fixos (11=R$7, 12=R$14, 13=R$35) e médias de rateio, cada cartela tem EV ≈ **−R$1,75** (retorno de ~50%). O critério de Kelly retorna fração **negativa** — a resposta matemática correta é "não apostar por expectativa de lucro".

2. **Nenhuma "assinatura" é preditiva.** Média de acertos de *qualquer* método é ~9 (o sorteio tem 9 acertos em média). Soma (média 195, σ 17,8), paridade, primos, Fibonacci, borda, gaps — todos são **descritivos**, não **preditivos**. Ajustar um filtro à faixa histórica apenas descreve o passado.

3. **Física/quântica são "teatro matemático".** Verlet, caminhada quântica, atrator de Lorenz, relatividade, fractais — são transformações determinísticas do **mesmo passado** que não carregam informação sobre um sorteio fisicamente independente. Soam impressionantes, mas o sorteio não obedece a essas dinâmicas.

4. **Cobertura exata de 13 pontos é inviável.** Um design de cobertura C(25,15,13) exige **≥ 58.887 cartelas** (cota de Schönheim); para 14 → ~297.000; para 15 → 3.268.760. Custo: **R$ 173 mil** só para "garantir" 13 dentro de um grupo fechado — e o prêmio de 13 é R$ 35.

> **Isto não torna o sistema inútil.** Torna-o o que ele realmente pode ser: uma ferramenta de **exploração estatística, estudo combinatório e gestão de risco** — não um oráculo de previsão.

---

## 4. Achados detalhados

### A. Bugs e código morto

| # | Arquivo | Problema | Severidade |
|---|---|---|---|
| 1 | `core/cerebro_ia.py` | `MotorRepulsaoVetorial.calcular_forca_repulsao` definido **duas vezes** — a 1ª é código morto sobrescrito pela 2ª | Média |
| 2 | `core/cerebro_ia.py` | `_aprender()` reforçava `anti_logica` em caso de **fracasso** (loop perverso: quanto mais erra, mais confia no módulo "contrário") | **Alta** ✅ corrigido |
| 3 | `core/cerebro_ia.py` | `backtesting()` era um **stub** (`return {"status":"ok","msg":"Backtesting integrado"}`) sem nenhuma medição | **Alta** ✅ corrigido |
| 4 | `core/singularidade.py` | Arquivo **vazio** (0 bytes) | Alta ✅ implementado |
| 5 | `core/heavyweight_engine.py` | `MotorExaustaoUniverso` (3,26M combinações em RAM, 326 MB) **nunca é instanciado** | Média |
| 6 | `core/fisica_quantica.py` | Classe `FisicaQuantica` nunca usada; física com flutuação `* 1e20` arbitrária | Média |
| 7 | `core/markov_engine.py` | `MarkovEngine` duplicado do `MotorMarkov` interno, nunca usado | Média |
| 8 | `core/covering_designs.py` | `CoveringDesigns` nunca usado; não há cotas honestas de custo | Média |
| 9 | `core/financeiro.py` | `registrar_resultado_financeiro` **nunca chamado** → tabela `financeiro` vazia | **Alta** |
| 10 | `core/ia_monitor.py` | `iniciar_sessao`/`log_modulo`/`log_decisao` **nunca chamados** → `ia_sessoes` vazia | **Alta** |
| 11 | `core/filtros_gaussianos.py` | Usa constantes fixas (`SOMA 185–220`) desatualizadas em relação à distribuição real (133–257) | Baixa |

### B. Métricas enganosas

- **"Cobertura 13"** (`MotorCobertura.calcular`) calcula cobertura **dentro do grupo elite de 19 dezenas**, não no espaço real de 3,26M. O número reportado na UI sugere garantia que não existe.
- **`score_total`** mistura unidades incompatíveis (probabilidades + entropia + divisores arbitrários) e não é comparável entre cartelas de concursos diferentes.

### C. Boas práticas violadas

- `oraculo_convergente.consultar_todos()` faz `np.random.seed(...)` **global**, afetando a aleatoriedade de outros módulos.
- Módulos usam `time.time_ns()` como seed — fonte de "não-reprodutibilidade" que não agrega previsibilidade.
- Sem separação treino/teste em lugar nenhum: o oráculo "aprende" com o histórico **inteiro**, incluindo o alvo que tenta prever (vazamento/overfit).

---

## 5. Backtesting real (fora-da-amostra)

Implementamos um validador *walk-forward*: para cada um dos últimos N sorteios, os 15 oráculos são treinados **apenas** com o passado e avaliados no sorteio seguinte. Resultado (15 concursos de teste):

- Todos os 15 oráculos e o consenso tiveram **média de ~9 acertos** (igual à baseline aleatória).
- **Nenhum** método atingiu 13+ pontos em 15 testes (esperado: 1 em ~691 por cartela).
- Nenhum método superou o acaso com significância estatística (após correção de Bonferroni).

Isso confirma, **empiricamente**, a Seção 3. A boa notícia: o sistema agora consegue **medir isso sozinho**, em vez de apenas afirmar confiança.

---

## 6. O que foi implementado nesta auditoria

Novo módulo **`core/singularidade.py`** (substitui o arquivo vazio), com métodos não-convencionais e **validação cética**:

| Componente | O que faz |
|---|---|
| `TeoriaDaInformacao` | Entropia de Shannon, entropia de permutação (Bandt–Pompe), transferência de entropia, matriz de informação mútua |
| `EspectroTemporal` | FFT, entropia espectral, expoente de **Hurst** (R/S) — detecta memória de longo alcance |
| `DependenciaMultivariada` | Co-ocorrência, dependência de cauda, distância de **Mahalanobis** sobre vetor de features |
| `FiltrosAvancados` | Filtros de **gaps**, **entropia condicional**, **co-ocorrência** e outlier multivariado |
| `CoberturaSteiner` | Cotas de **Schönheim** para C(25,15,13/14/15) com custo honesto |
| `GestaoDeBanca` | Valor esperado exato, critério de **Kelly**, risco de ruína |
| `ValidadorForaDaAmostra` | Backtest *walk-forward* com baseline aleatória e teste de significância (Bonferroni) |

**Correções no Cérebro:**

- `_aprender()` reescrito: agora ajusta pesos pelo **desempenho real** de cada módulo no sorteio (top-15 × resultado), e persiste em `desempenho_modulos` / `memoria_erros` (antes nunca gravadas).
- `backtesting()` reescrito: agora executa o validador fora-da-amostra real.

**Novos endpoints e página:**

- `GET /singularidade` — painel de auditoria cética (probabilidades exatas, banca/Kelly, cobertura, Hurst, entropia).
- `GET /api/singularidade/analise`
- `POST /api/singularidade/backtest`

---

## 7. Roadmap de evolução (sugestões)

**Valor real (recomendado):**

1. **Estudo combinatório sério** — designs de cobertura, sistemas de rodas reduzidos, análise de garantia condicional. É a única área onde há matemática "de verdade" aplicável, ainda que não rentável.
2. **Gestão de banca** — integrar `financeiro` e `ia_monitor` ao fluxo (hoje desconectados), para medir ROI real e risco.
3. **Auditoria de sorteio** — testes de aleatoriedade (chi² de frequência, gaps, runs, autocorrelação, Hurst≈0.5) para *monitorar* a Caixa, não para prever.
4. **Validação contínua** — rodar o backtest a cada concurso novo e registrar no banco (hoje é sob demanda).

**Exploração não-convencional (pedida pelo usuário, com ressalva honesta):**

5. *Entropia de transferência* e *causalidade de Granger* entre dezenas — para **detectar** dependência (o esperado é nenhuma).
6. *Copulas* (Gaussiana/t) sobre a estrutura de dependência conjunta das 25 séries.
7. *Processos de Hawkes* e *modelos de estados ocultos* (HMM) sobre frequências — novamente, para confirmar ausência de sinal.
8. *Algoritmos quânticos* reais (Grover/amplitude amplification) como exercício teórico — não mudam a expectativa, mas são didáticos.

**A evitar (pseudo-melhorias):** adicionar mais "oráculos" do mesmo tipo (mais transformações do passado) sem validação fora-da-amostra. Isso aumenta a complexidade sem aumentar a acurácia.

---

## 8. Conclusão

O sistema é um excelente **laboratório** de matemática aplicada e estatística, mas deve ser tratado como tal. A auditoria corrigiu os defeitos estruturais mais graves (aprendizado perverso, backtest fantasma, finanças/auditoria desconectadas) e adicionou uma camada de **medição honesta contra o acaso**.

**A recomendação central:** use o sistema para estudar, explorar e se divertir — nunca como fonte de vantagem financeira. Nenhuma técnica, lógica ou "não-lógica", muda o fato de que 13/14/15 pontos obedecem a probabilidades fixas que nenhum algoritmo supera.

---

# 🔁 FASE 2 (2026-08-24) — Motor de Desdobramento com Cobertura Garantida

Entrega o item 1 do roadmap (§7): **wheeling com garantia condicional exata + contabilidade exata do lote**, integrado ao Cérebro como orquestrador (`pipeline_wheeling`), com página própria (`/wheeling`) e backtest honesto de captura.

## 9. Teorema do fechamento condicional (novo resultado implementado)

Seja um **pool** de N dezenas (16 ≤ N ≤ 25). Uma cartela `c` e um sorteio `d` são 15-subconjuntos do pool; seus complementos `c̄, d̄` têm `s = N − 15` dezenas. Então:

```
|c ∩ d| = 30 − N + |c̄ ∩ d̄|
```

**Teorema (família α = 1).** O número mínimo de cartelas que garante **31 − N pontos** (se as 15 sorteadas estiverem no pool) é exatamente:

```
C(N, 15, 31−N) = ⌈16 / (N−15)⌉
```

*Prova.* ≥: com `m` cartelas, a união dos complementos tem ≤ `m·s` dezenas; se `m < 16/s` então ≤ 15 dezenas cobertas, e existe um complemento `d̄` de tamanho `s` disjunto de todos — aquele sorteio atinge apenas `30−N` pontos. ≤: particionando 16 dezenas do pool em `⌈16/s⌉` grupos de tamanho `s` (completando o último com dezenas extras), as cartelas `pool ∖ grupo` cobrem tudo: qualquer `d̄` precisa conter uma das 16 primeiras dezenas, que está em algum grupo. ∎

Menu resultante (verificado exaustivamente por código, `tests/test_wheeling.py`):

| Pool | Garantia | Cartelas | Custo | P(pool ⊇ sorteio) |
|---|---|---|---|---|
| 16 | **15** | 16 | R$ 56,00 | 1 em 204.298 |
| **17** | **14** | **8** | **R$ 28,00** | **1 em 24.035** |
| 18 | 13 | 6 | R$ 21,00 | 1 em 4.006 |
| 19 | 12 | 4 | R$ 14,00 | 1 em 843 |
| 20 | 11 | 4 | R$ 14,00 | 1 em 211 |
| 21 | 10 | 3 | R$ 10,50 | 1 em 60 |
| 22 | 9 | 3 | R$ 10,50 | 1 em 19 |
| 23 | 8 | 2 | R$ 7,00 | 1 em 6,7 |

Para garantias acima disso (α ≥ 2, ex.: 14 pontos em pool de 18): **greedy com vizinhanças de Johnson** + verificação exaustiva (N ≤ 20). Medido: pool 18 → garantia 14 com 24 cartelas (limite inferior teórico: 18).

## 10. Contabilidade exata do lote (sem Monte Carlo)

`analisar_lote()` enumera **todos os 3.268.760 sorteios possíveis** (máscaras uint32 + `np.bitwise_count`, universo em cache) e calcula com exatidão:

- distribuição do **melhor acerto do lote** → P(lote ≥ 14), P(15);
- **prêmio esperado e EV exatos** (fixos 11/12/13 + médias históricas de 14/15);
- distribuição **condicional à captura** do pool (mínimo garantido verificado).

Exemplo real (pool de 17 escolhido pelos motores, 8 cartelas, R$ 28,00): se o pool capturar → **mínimo 14 pontos garantido**, P(15 | captura) = 5,88%; incondicional → P(≥14) = 1 em 2.983; **EV do lote = −R$ 14,03** (retorno ~50%, como manda a casa).

## 11. Backtest honesto de captura

`/api/cerebro/wheeling/backtest`: walk-forward que re-treina os 14 motores sem cada concurso e mede a interseção pool×sorteio. Baselines teóricos: E[interseção] = 15·N/25 = 10,2 (pool 17) e P(captura) = 1 em 24.035. Resultado inicial (k=3): interseções 10–12, 0 capturas — **consistente com o acaso**, como estabelece a §3. O veredito é exibido ao usuário junto com os números.

## 12. O que mudou no código

| Arquivo | Mudança |
|---|---|
| `core/wheeling.py` | **novo** — família exata α=1, greedy Johnson, verificação exaustiva, análise exata do universo, cache do universo 25/15 |
| `core/cerebro_ia.py` | `pipeline_wheeling()` (orquestração motores→pool→fechamento→análise), `backtest_captura()` (walk-forward), `treinar(matriz_override)` para janelas |
| `app.py` | página `/wheeling`, `POST /api/cerebro/wheeling` (gera e salva lote tipo `wheeling`), `POST /api/cerebro/wheeling/backtest` |
| `templates/wheeling.html`, `templates/base.html` | página com menu de fechamentos, gerador, cartelas, números exatos e backtest; item na navegação |
| `tests/test_wheeling.py` | 11 testes: construção exata N=16–20 verificada exaustivamente, prova de otimalidade N=17 (7 cartelas falham), greedy N=18/14, marginal = hipergeométrica, probabilidades de captura |

`core/covering_designs.py` (órfão, greedy O(C(N,15)²) sem verificação) fica **obsoleto**: `core/wheeling.py` o substitui com garantias verificadas e análise exata. Recomenda-se remoção futura.

**A mesma conclusão da §3 permanece de pé** — agora com números exatos por lote: o wheeling converte *acertar o pool* em *pontos garantidos*, mas não muda a probabilidade de capturar (hipergeométrica pura) nem torna o EV positivo. É a ferramenta certa para quem joga por diversão com orçamento definido: maximiza o que se extrai de cada real **se** o pool acertar, e diz com honestidade matemática o preço disso.

---

# 🔍 FASE 3 (2026-08-24) — Auditoria de módulos, filtros e navegação

Varredura de todos os módulos `core/`, dos filtros combinatórios e do menu/páginas, com correções aplicadas e validadas ao vivo.

## 13. Falhas encontradas e corrigidas

| # | Falha | Evidência | Correção |
|---|---|---|---|
| 1 | `core/heavyweight_engine.py` **nem importava** | `NameError: Tuple` — módulo morto desde a criação | Reescrito (v11): import corrigido, reaproveita o cache de máscaras do `wheeling` (13 MB em vez de matriz própria de 82 MB), sem torch. **3.268.760 combinações avaliadas em 0,46 s** |
| 2 | Filtro ativo (`MotorGaussiano`, p3–p97) rejeitava **33,7%** dos sorteios reais | 2.499/3.767 concursos históricos passavam | Recalibrado para p1–p99 + `CONSEC_MAX=8` → **93,9% de aprovação**; nova métrica `taxa_aprovacao_filtro` exposta após treino |
| 3 | Faixas estáticas do `config.py` rejeitavam **69,9%** dos sorteios reais | ex.: SOMA 185–220 vs. real 133–257 | Recalibradas para os p1–p99 medidos (soma 155–235, primos 3–8, fib 2–7, borda 7–12, repetição 6–12, consecutivos 14) |
| 4 | `/gerar` era rota-fantasma | GET redirecionava para `/cerebro`; `gerar.html` (169 linhas) nunca renderizado; sem item no menu | Página real server-rendered (form → geração → cartelas + métricas) e item **"Gerar Cartelas"** adicionado ao menu |
| 5 | Módulo financeiro desconectado | `registrar_resultado_financeiro()` nunca chamado; tabela com 0 linhas desde a criação | Hook `_registrar_financeiro` nas rotas de conferência (com guarda anti-duplicata e rateio real da Caixa). Primeiro registro real: concurso 3766 — 56 cartelas, custo R$ 196, **lucro −R$ 196** |
| 6 | 4 módulos órfãos exportados sem uso | `FiltrosGaussianos`, `MarkovEngine`, `FisicaQuantica`, `CoveringDesigns` nunca instanciados; duplicados por motores internos e pelo `wheeling` | Removidos (junto com as linhas de export no `core/__init__.py`) — superseded |
| 7 | `MotorExaustaoUniverso` nunca integrado à UI | classe morta | Endpoint `POST /api/analise/exaustao` + card "Exaustão do Universo" na página Análise (com aviso de honestidade) |

## 14. O que foi verificado e passou

- **Imports**: 10/10 módulos `core/` importam limpo após a limpeza (antes: 11/12, com `heavyweight` quebrado).
- **Menu × rotas**: os 12 itens do menu apontam para rotas existentes; 12/12 páginas respondem 200 (`/gerar` agora incluída). Todos os endpoints chamados por `fetch` nos templates/JS existem.
- **Conferência**: fluxo `conferir_concurso`/`conferir_lote` validado com dados reais (56 cartelas do 3766, prêmios oficiais da Caixa, 0 premiadas — registrado com fidelidade).
- **Regressão**: suíte do wheeling 11/11 após todas as mudanças; pipeline wheeling e backtest de captura seguem operando.

## 15. Nota honesta sobre os filtros

Recalibrar filtros **não aumenta a probabilidade de acerto** — toda combinação de 15 dezenas tem a mesma distribuição hipergeométrica. O que a correção resolve: (a) o gerador não desperdiça ciclos nem cai no "fallback" por rejeição excessiva; (b) as cartelas geradas deixam de se concentrar num estereótipo atípico que excluía 1/3 dos sorteios reais; (c) a taxa de aprovação agora é medida e exibida em vez de implícita.

---

# 🧠 FASE 4 (2026-08-24) — O Cérebro IA como motor único do sistema

`CerebroIA.gerar_otimas(n)` — um único comando, o Cérebro faz TUDO: treina os 14 motores, combina os vetores, escolhe a estratégia e entrega as cartelas com contabilidade exata sobre o universo completo.

## 17. Estratégia automática por quantidade

| Pedido | Estratégia | O que o Cérebro faz |
|---|---|---|
| **1 cartela** | `exaustao-unica` | Pontua **todas as 3.268.760 combinações** contra o vetor combinado e entrega a melhor que existe (aprovada no filtro gaussiano) |
| 2–7 | `exaustao-diversa` | As n melhores com sobreposição ≤ 13 dezenas entre si (cobertura espalhada sem abandonar o critério dos motores) |
| **≥ 8** | `wheeling-garantia-14` | Pool elite de 17 fechado em 8 cartelas com **garantia 14 se capturar** (ótimo provado) + excedente por exaustão |

Integrações: `POST /api/cerebro/otimas` · página `/gerar` com modo **"🧠 O Cérebro Decide"** (padrão) · lote salvo como `cerebro_otimas`.

## 18. Números exatos por estratégia (medidos sobre o universo)

| n | Custo | P(lote ≥ 14) | Garantia condicional |
|---|---|---|---|
| 1 | R$ 3,50 | 1 em 21.647 | — |
| 3 | R$ 10,50 | 1 em 7.412 | — |
| 8 | R$ 28,00 | 1 em 2.983 | **14 se pool capturar (1 em 24.035)** |

Validação: 10/10 testes (`tests/test_otimas.py`) — probabilidades da cartela única conferem ao exato hipergeométrico (P(15) = 1/3.268.760), sobreposições ≤ 13 na diversa, garantia verificada na wheeling.

**A verdade continua a mesma e o sistema segue dizendo:** com uma cartela, 14 pontos é 1 em 21.647 e 15 pontos é 1 em 3.268.760 — qualquer que seja a análise. O que o Cérebro agora garante é que a escolha é a **melhor definível** pelos critérios dos motores (exaustiva, não amostral) e, quando você aceita jogar 8+, que **se** o pool de 17 capturar as sorteadas, **14 pontos são garantidos por construção matemática**.

---

# 🧠 FASE 6 (2026-08-25) — Unificação: o Cérebro IA como Inteligência Magna ÚNICA

Atendendo ao pedido para que o Cérebro IA seja o **único módulo a gerar
cartelas** e a única porta de entrada das áreas de geração/análise, todas
essas áreas foram unificadas em abas internas de `/cerebro`, sem perder
nenhum cálculo, fórmula, filtro ou template já construídos.

## 19. Arquitetura unificada

```
/cerebro  (HUB — Inteligência Magna)
 ├─ aba Cabine         → /cerebro/central?fragmento=1   (treino, loop, geração clássica, pesos, filtros, ciclos, log)
 ├─ aba Gerar Cartelas → /gerar?fragmento=1             (Cérebro decide: exaustão/diversa/wheeling + modos)
 ├─ aba Cartela do Dia→ /cartela_do_dia?fragmento=1     (15 oráculos, idempotente por concurso)
 ├─ aba Wheeling 14/15→ /wheeling?fragmento=1           (fechamentos com garantia + análise exata)
 ├─ aba Análise       → /analise?fragmento=1            (heatmap total/recente)
 ├─ aba Singularidade → /singularidade?fragmento=1      (banca/Kelly, Hurst, entropia, Steiner)
 └─ aba Auditoria     → /ia_auditoria?fragmento=1       (transparência dos módulos)

Continuam no menu (fora do hub, como pedido):
 /  Dashboard · /conferencia · /financeiro_page · /historico · /premios · /avaliacao
```

## 20. Como foi feito (sem perder nada)

- **Helper `_render()`** em `app.py`: renderiza o template completo
  normalmente ou, quando a requisição traz `?fragmento=1`, usa a casca
  mínima `_fragmento.html` (só `{% block content %}` + `{% block scripts %}`).
  Cada template antigo passou a fazer
  `{% extends base_layout|default("base.html") %}` — sozinho, continua
  funcionando como página; no hub, vira fragmento.
- **Página `/cerebro` reescrita** como hub com abas; cada aba carrega seu
  fragmento via `fetch` e re-executa os `<script>` embutidos (necessário
  porque `innerHTML` não executa scripts injetados). O hash da URL
  (`#aba-...`) permite linkar e usar o botão voltar.
- **Novo `templates/_cerebro_central.html`**: conteúdo da antiga Cabine de
  Comando (treino, loop, geração clássica, pesos SPSA, filtros, ciclos,
  log em tempo real), agora servido por `/cerebro/central`.
- **Formulários do hub** postam para a própria rota com `?fragmento=1`
  (`/cerebro/central?fragmento=1`, `/gerar?fragmento=1`), mantendo o
  usuário dentro do hub.
- **Rotas legadas redirecionam** (302) para a aba correspondente quando
  acessadas sem `?fragmento=1`; com `?fragmento=1`, devolvem só o miolo.
- **Sidebar reorganizada** em dois grupos: **CÉREBRO IA** (hub + atalhos
  das abas) e **SISTEMA** (Dashboard, Conferência, Financeiro, Histórico,
  Prêmios, Avaliação).
- **`context_processor`** movido para depois da criação de
  `status_sistema` (corrige NameError em runtime).

## 21. Garantias preservadas

- Todos os **cálculos/fórmulas** seguem em `core/cerebro_ia.py` (14 motores
  + SPSA + genético + gaussiano + repulsão), `core/wheeling.py`
  (família exata α=1, greedy Johnson, análise exata do universo),
  `core/singularidade.py` (Kelly, Hurst, entropia, Steiner) e
  `core/oraculo_convergente.py` (15 oráculos).
- **Filtros** gaussianos e de repulsão continuam ativos em TODA geração.
- **Toda geração passa pelo `CerebroIA`**: `/gerar` chama
  `cerebro.gerar_otimas/gerar_cartelas`; wheeling chama
  `cerebro.pipeline_wheeling`; cartela do dia chama
  `cerebro.gerar_cartela_do_dia`. Nenhuma rota gera cartelas por fora.
- APIs de geração (`/api/cerebro/otimas`, `/api/cerebro/wheeling`,
  `/api/cerebro/gerar`, `/api/analise/exaustao`) seguem intactas para os
  JS das abas.

## 22. Testes

- 37/37 testes passam. Novos testes em `tests/test_hub_unificado.py`:
  - `/cerebro` tem layout completo + 7 abas declaradas;
  - cada aba carrega como fragmento **sem** a sidebar/`<!DOCTYPE>`;
  - rotas legadas redirecionam (302) para a âncora correta E continuam
    servindo o fragmento com `?fragmento=1`;
  - Conferência, Financeiro, Histórico e Prêmios seguem 200.
- Servidor verificado ao vivo: redirects 302 confirmados e os 7
  fragmentos retornam 200 sem a casca do app.

## 23. Nota honesta (mantida)

Unificar a interface não muda a matemática do sorteio: 13/14/15 pontos
continuam com as mesmas probabilidades hipergeométricas. O que a unificação
ganha é clareza: **um único cérebro analisa, decide, gera e aprende**, com
todos os instrumentos (filtros, wheeling, oráculos, auditoria cética)
organizados sob o mesmo teto.
