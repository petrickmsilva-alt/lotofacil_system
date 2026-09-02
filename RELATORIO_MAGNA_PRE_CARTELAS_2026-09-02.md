# RELATÓRIO — VERIFICAÇÃO, ANÁLISE E CORREÇÃO DA INTELIGÊNCIA MAGNA
## "A Magna faz todos os processos que o sistema oferece?" + Relatório pré-cartelas

**Data:** 2026-09-02 · **Branch:** `arena/01a0622f-lotofacil-system` · **Versão resultante:** v12.1
**Suíte:** 198 testes (193 pré-existentes + 5 novos) — todos passando

---

## 1. Objetivo

1. **Verificar e analisar** se a Inteligência Magna (`core/cerebro_ia.py` — a única
   inteligência, única memória e única porta de criação de cartelas) executa,
   antes de gerar as cartelas, **todos os processos que o sistema oferece**.
2. **Corrigir** as lacunas encontradas.
3. **Entregar um relatório** de tudo que ela processa antes de gerar as cartelas
   para o sorteio — dentro da própria decisão, consultável sozinho e na interface.

---

## 2. Metodologia da verificação

Mapeamento módulo a módulo (`core/*.py`) × pontos de uso no fluxo decisório
(`_decidir_e_gerar_sem_lock` → `gerar_otimas`), leitura do README/contratos
(documentação promete "juiz 9 critérios" no fluxo), execução real de decisões
com banco de 3.775 concursos e a suíte automatizada.

| Módulo do sistema | Processo que oferece | Era executado ANTES das cartelas? |
|---|---|---|
| `data_loader` + `caixa_client` | ingestão/atualização da base | ✅ (no boot e no treino) |
| `oraculo_convergente` | 15 teorias + entropia | ✅ fonte `oraculos` |
| 14 motores (`treinar`) + SPSA + stacking | memória única treinada | ✅ etapa de treino |
| `singularidade` (Espectro/Informação/Filtros/Banca/Steiner) | análise temporal, entropia, filtros, EV/Kelly | ✅ fontes `espectral`/`informacao` + interpretação |
| `acervo_cor` | cores oficiais das bolas | ✅ fonte `cor` |
| `fisica_sorteio` | perfil físico das bolas + ambiente | ✅ fonte `fisica` + registro do ambiente |
| `clima_lotofacil` | temperatura × pressão × umidade | ✅ fonte `clima` (shrinkage) |
| `inmet` | telemetria do local do sorteio | ✅ fonte `inmet` + percepção autônoma |
| `forja_auto` | local + telemetria automáticos | ✅ passo interno (v12.0) |
| `antipopularidade` | edge de rateio | ✅ desempate do vetor |
| `wheeling` | escada de captura 13/14/15 | ✅ estratégia garantida |
| `forja_lotes` | forja espacial (recocido) | ✅ lote 8+ |
| `heavyweight_engine` | exaustão das 3.268.760 combinações | ✅ estratégias 1–7 |
| `bitmatrix` | operações de bitmask | ✅ trilha interna |
| `cobertura` | motor de cobertura | ✅ vetor do treino |
| `laboratorio_magna` | auditoria estrutural por cartela | ✅ interpretação por cartela |
| `financeiro` | gestão de banca/EV | ✅ via `GestaoDeBanca` no diagnóstico |
| `odds_reais` | probabilidades exatas (informativo) | ⚙️ por design fica no endpoint `/api/odds/reais` (não é fonte de evidência) |
| `conferencia` | conferência/aprendizado pós-sorteio | ✅ ciclo pós-sorteio (não é etapa pré-cartela) |
| **`magna_suprema` — JuizMagna 9 critérios** | julgar o lote antes de entregar | ❌ **NUNCA chamado no fluxo principal** (só na Suprema) |
| **`magna_suprema` — JuizAdversarial** | caçar fraquezas do lote | ❌ só na Suprema |
| **`magna_suprema` — TesteNIST** | teste de aleatoriedade do lote | ❌ só na Suprema |
| **`magna_suprema` — PValueRandom** | significância vs. aleatório | ❌ só na Suprema |
| **`magna_suprema` — FingerprintPessoal** | nunca repetir cartela do usuário | ❌ só na Suprema |
| **`magna_suprema` — BacktestLote/CurvaAprendizado** | honestidade walk-forward | ❌ só na Suprema |
| **`magna_suprema` — UtilidadeEsperada** | EV com prêmios reais médios | ❌ só na Suprema |
| **`magna_suprema` — DetectorRegime** | regime atual da base | ❌ só na Suprema |
| **bloqueio de 15 já sorteados** (`_substituir_cartelas_ja_sorteadas_15`) | nunca reemitir combinação que já fez 15 | ❌ **código morto** — método existia, testado isoladamente, mas nenhum fluxo o chamava |
| **relatório do pré-processamento** | trilha auditável do "antes" | ❌ não existia |

---

## 3. Achados (verificação + análise)

### 3.1 A verificação de qualidade existia — mas só na porta "Suprema"
`decidir_suprema()` julga o lote (Juiz 9 critérios + adversarial + NIST +
p-value, com regeneração). Porém a porta principal — `/api/magna/decidir`,
usada pelo painel `/cerebro` e pelos aliases legados — entregava o lote
**sem nenhum juízo**: `julgar_lote()` (o método que encapsula o Juiz) tinha
zero chamadas no fluxo. O README promete "juiz 9 critérios" no fluxo da
decisão; o código não cumpria o contrato.

### 3.2 Bloqueio de 15 já sorteados era código morto
`_substituir_cartelas_ja_sorteadas_15()` — documentado como "Nunca reemite
uma combinação que já foi contemplada com 15 pontos" e coberto por teste
próprio (`test_bloqueio_15_memoria.py`) — **não era chamado por nenhum fluxo
de geração**. A Suprema filtrava `_cartela_ja_foi_15`, o fluxo principal não.

### 3.3 Processos de honestidade/utilidade ausentes da resposta principal
Backtest 50, curva de aprendizado, verificação exaustiva e utilidade esperada
com prêmios reais só existiam na Suprema ou em endpoints avulsos.

### 3.4 Nenhuma trilha auditável do pré-processamento
A decisão carregava pedaços (`acervo_magna`, `diagnostico_magna`…), mas não
existia o relatório pedido: **a lista ordenada, cronometrada e detalhada de
tudo que a Magna processa antes de gerar as cartelas**.

### 3.5 Regeneração por adversarial era desperdício (achado de análise)
No piloto, `JuizAdversarial` marca quase todo lote de exaustão como
"VULNERÁVEL" (dezenas de topo aparecem em todas as cartelas — é o esperado
do consenso). Usá-lo como gatilho de regeneração, como na Suprema, dobra o
custo com resultado idêntico (lote determinístico). **Correção de projeto:**
a regeneração responde apenas ao veredito do Juiz de 9 critérios;
adversarial/NIST/p-value ficam como diagnóstico na resposta.

---

## 4. Correções aplicadas (v12.1)

| # | Correção | Onde |
|---|---|---|
| 1 | **Juiz 9 critérios em TODA decisão** — `julgar_lote()` com até `tentativas_juiz` tentativas (regenera se REPROVADO) | `core/cerebro_ia.py` · `_decidir_e_gerar_sem_lock` |
| 2 | **Adversarial + NIST + p-value** anexados a toda resposta (`julgamento_adversarial`, `teste_nist`, `p_value_random`) | idem |
| 3 | **Fingerprint pessoal ativo** — carrega memória (500 últimas cartelas), substitui repetidas por jogos inéditos do topo do universo e registra o lote entregue | `core/cerebro_ia.py` · `_substituir_cartelas_ja_geradas` (novo) + decisão |
| 4 | **Bloqueio-15 ligado ao `gerar_otimas`** — rotas de exaustão/forja substituem combinação oficial já sorteada; rotas de garantia (wheeling) preservam a garantia e reportam | `core/cerebro_ia.py` · `gerar_otimas` |
| 5 | **Backtest 50 + curva + verificação exaustiva + utilidade esperada** em toda decisão | idem |
| 6 | **Detector de regime** agora alimenta toda decisão (`regime_atual` no resultado e no relatório) | idem |
| 7 | **Relatório pré-cartelas** — `core/relatorio_pre_cartelas.py` (novo): `GravadorEtapas` cronometra e documenta cada etapa; anexado como `relatorio_pre_cartelas` e persistido em `magna_decisoes.analise_json` | módulo novo + decisão |
| 8 | **Consulta sem gerar cartela** — `InteligenciaMagna.relatorio_pre_cartelas()` roda só o pré-processamento | `core/cerebro_ia.py` (novo método) |
| 9 | **API pública** — `GET /api/magna/pre-cartelas` (JSON + markdown) | `app.py` |
| 10 | **Painel** — seção "Relatório pré-cartelas" em `/cerebro` (renderiza o relatório da decisão e consulta sozinho) | `templates/cerebro.html`, `static/css/style.css` |
| 11 | Refatoração sem duplicação — pré-processamento extraído para `_pipeline_pre_cartelas()`, usado pela decisão e pela consulta | `core/cerebro_ia.py` |

**Garantias preservadas:** nenhuma garantia combinatória do wheeling é
quebrada pelo bloqueio/fingerprint (rotas de garantia não trocam cartela);
nenhuma fração hipergeométrica muda; o relatório descreve o processo —
não valida previsibilidade.

---

## 5. Como consultar o relatório pré-cartelas

```http
GET /api/magna/pre-cartelas?quantidade=1&alvo=13&orcamento=50
```
— roda SÓ o pré-processamento (nada é gerado) e devolve `relatorio.etapas`,
`resumo`, `estado_final` e `markdown`.

`POST /api/magna/decidir` — a resposta passa a trazer
`resultado.relatorio_pre_cartelas` (a trilha daquela decisão específica).

Painel `/cerebro` → seção **"Relatório pré-cartelas"** (e o selo
`DECISÃO AUDITÁVEL` mostra o veredito do Juiz).

---

## 6. RELATÓRIO REAL (capturado em execução — 3.775 concursos, sem telemetria INMET no ambiente de teste)

# Relatório pré-cartelas — Inteligência Magna

- Início: `2026-09-02 13:13:30`
- Etapas processadas: **14**
- Tempo total: `6990.7 ms`
- Status: 1 aviso, 13 ok

## 1. ✅ validacao_entrada — `0.0 ms` [ok]
Parâmetros normalizados para o ciclo decisório

| campo | valor |
|---|---|
| quantidade | `1` |
| orcamento | `None` |
| alvo | `auto` |
| modo | `auto` |
| concurso_alvo | `próximo` |

## 2. ✅ treinamento_memoria_unica — `1416.4 ms` [ok]
14 motores + Oráculo Convergente + SPSA sobre a base histórica inteira

| campo | valor |
|---|---|
| concursos | `3775` |
| modulos | `14` |
| oraculos | `15` |
| tempo_s | `1.42` |

## 3. ✅ acervo_conhecimento — `468.1 ms` [ok]
Relê a base histórica (abertura + cores) e reassigura o conhecimento

## 4. ✅ evidencia_acervo — `0.0 ms` [ok]
Síntese do que o acervo ensina — usada no vetor, no Juiz e na conferência

| campo | valor |
|---|---|
| abertura_digest | `sha256:6fac6122d006d4ae` |
| abertura_aprendido_ate | `3775` |
| abertura_veredito | `RUÍDO` |
| abertura_fator_confianca | `0.5` |
| abertura_palpite_top3 | `[1, 2, 3]` |
| cores_digest | `sha256:5e5d8420ba79e0c3` |
| cores_veredito | `RUÍDO` |
| cores_fator_confianca | `0.5` |
| cores_dominante_atual | `azul` |

## 5. ⚠️ percepcao_ambiente — `3704.0 ms` [aviso]
Local do sorteio + telemetria INMET + clima (shrinkage) + registro físico do ambiente
- ⚠️ sem telemetria completa: fontes climáticas neutras

| campo | valor |
|---|---|
| status_ambiente | `neutro` |
| local | `São Paulo/SP` |
| telemetria | `{}` |
| clima | `None` |
| ambiente_registrado | `False` |

## 6. ✅ regime_atual — `0.0 ms` [ok]
Detector de regime (K-means adaptativo sobre a janela recente)

| campo | valor |
|---|---|
| regime | `{'regime_atual': 1, 'n_regimes': 3, 'centroides': [{'regime': 0, 'soma_est': 200.8, 'pares_est': 7.7, 'primos_est': 4.4, 'fib_est': 3.8, 'borda_est': 10.2, 'consec_est': 4.1, 'gap_est': 1.65, 'freq': 36}, {'regime': 1, 'soma_est': 190.7, 'pares_est': 6.3, 'primos_est': 6.3, 'fib_est': 4.9, 'borda_est': 9.5, 'consec_est': 4.0, 'gap_est': 1.65, 'freq': 41}, {'regime': 2, 'soma_est': 186.0, 'pares_est': 7.1, 'primos_est': 5.7, 'fib_est': 4.7, 'borda_est': 9.4, 'consec_est': 6.6, 'gap_est': 1.61, 'freq': 23}], 'labels_janela': [0, 0, 0, 1, 1, 0, 1, 2, 1, 0, 1, 0, 2, 2, 0, 1, 1, 0, 1, 1, 1, 1, 2, 0, 1, 0, 2, 1, 2, 0, 0, 2, 0, 0, 2, 0, 0, 2, 2, 0, 1, 0, 2, 0, 0, 0, 2, 0, 1, 1, 2, 1, 1, 2, 2, 1, 1, 1, 2, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 2, 0, 1, 1, 1, 1, 1, 2, 0, 1, 0, 1, 0, 1, 2, 0, 2, 2, 1, 2, 0, 1, 0, 2, 1, 1, 1, 1, 0, 0, 1], 'inertia': 2.466, 'silhouette': 0.176, 'descricao': 'Regime 1 dominante nos últimos 100 concursos', 'k_otimo': 3}` |

## 7. ✅ escolha_metodo_geracao — `0.0 ms` [ok]
A Magna escolhe sozinha entre exaustão, escada de captura e forja espacial

| campo | valor |
|---|---|
| modo_escolhido | `auto` |
| quantidade | `1` |
| alvo | `auto` |

## 8. ✅ fontes_assimiladas — `1370.1 ms` [ok]
Motores, oráculos, espectro, informação, janela recente, física, clima, abertura, cores e INMET

## 9. ✅ pesos_fontes — `0.0 ms` [ok]
Peso calibrado de cada fonte no consenso (aprendido em walk-forward/conferências)

| campo | valor |
|---|---|
| pesos | `{'motores': 0.3, 'oraculos': 0.18, 'espectral': 0.1, 'informacao': 0.1, 'recente': 0.09, 'fisica': 0.08, 'clima': 0.05, 'abertura': 0.04, 'cor': 0.03, 'inmet': 0.03}` |
| peso_total | `1.0` |

## 10. ✅ consenso_vetor_final — `0.2 ms` [ok]
Fusão ponderada das fontes no ÚNICO vetor autorizado a gerar

| campo | valor |
|---|---|
| top5_por_fonte | `{'motores': [25, 20, 11, 10, 2], 'oraculos': [15, 4, 11, 13, 3], 'espectral': [10, 13, 4, 7, 23], 'informacao': [12, 18, 3, 14, 20], 'recente': [5, 11, 2, 13, 3], 'fisica': [20, 19, 18, 5, 17], 'clima': [22, 19, 8, 25, 23], 'abertura': [1, 2, 3, 4, 5], 'cor': [20, 10, 25, 15, 5], 'inmet': [25, 24, 23, 22, 21]}` |
| top15_consenso | `[4, 2, 11, 1, 15, 13, 3, 25, 5, 14, 10, 23, 19, 20, 12]` |

## 11. ✅ memoria_episodica — `2.5 ms` [ok]
Reforço de quase-13/14, repulsão de clones fracos e memória vetorial com atenção

| campo | valor |
|---|---|
| episodios_prototipo | `0` |
| episodios_repulsao | `1` |

## 12. ✅ antipopularidade — `0.1 ms` [ok]
Prioriza perfis menos disputados no rateio (edge de prêmio, não de acerto)

## 13. ✅ rota_extraordinaria — `0.3 ms` [ok]
Planejamento extraordinário por orçamento (rota, pool e captura)

| campo | valor |
|---|---|
| rota_escolhida | `True` |
| resumo | `{'alvo': 11, 'n_pool': 25, 'metodo': 'cobertura-verificada', 'custo_teorico': 182.0, 'um_em_captura': 1}` |

## 14. ✅ pronto_para_gerar — `0.0 ms` [ok]
Estado final consolidado; a partir daqui a Magna geraria as cartelas

| campo | valor |
|---|---|
| vetor_top15 | `[4, 2, 1, 3, 11, 15, 13, 5, 25, 10, 14, 9, 23, 20, 19]` |
| metodo | `auto` |
| concursos_na_base | `3775` |
