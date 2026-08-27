# AUDITORIA COMPLETA — SISTEMA LOTOFÁCIL / INTELIGÊNCIA MAGNA v9.2 EXTRAORDINÁRIA

Data: 2026-08-27
Branch: arena/01a04387-lotofacil-system
Versão Magna: 9.2-Magna-Extraordinaria-Forca-Maxima
Repositório: https://github.com/petrickmsilva-alt/lotofacil_system.git

## 1. ARQUITETURA GERAL

- **Stack**: Python 3, Flask, SQLite, NumPy, itertools, threading
- **Entrada única**: `/cerebro` → `InteligenciaMagna.decidir_e_gerar()` (única porta de criação)
- **Compatibilidade**: `app.py` mantém `cerebro = magna` alias, mas toda rota legada (`/gerar`, `/api/cerebro/gerar`, `/api/cerebro/wheeling`, `/cartela_do_dia`, `/wheeling`, etc.) redireciona 303 ou delega para `decidir_e_gerar`
- **Persistência atômica**: `_salvar_cartelas_banco()` valida dezenas, converte BLOB, cria lote_id com UUID e comita cabeçalho + cartelas em uma única transação (evita lotes órfãos)
- **Sincronização**: `data_loader` + `caixa_client` busca incremental da Caixa; `_iniciar_sincronizacao_historico` com `historico_lock` e flag `carregando` para evitar corrida; pós-sorteio chama `ciclo_pos_sorteio_caixa()` que retreina, confere e aprende idempotentemente
- **Loop autônomo**: `iniciar_loop(intervalo)` thread daemon monitora Caixa a cada 1800s

## 2. MÓDULOS CORE

### 2.1 `core/cerebro_ia.py` — Inteligência Magna (protagonista única)
- **14 motores analíticos**:
  - Frequência global/recente, Reversão à média, Anti-Lógica (saturação/atraso/FFT/correlação), Markov, Quantum (caminhada quântica), Verlet (simulação física com ruído nanosegundo), Estatística (Chi²/Bayes/KL), Gaussiano (filtros soma/pares/primos/fib/borda + taxa aprovação histórica p1-p99), Genético (4 ilhas), Cobertura, Stacking
- **Oráculo Convergente** (`oraculo_convergente.py`): 15 teorias independentes + entropia nanosegundo, quorum, votos por dezena, `gerar_cartela_do_dia(cartelas_ja_geradas)` garante inéditas
- **Física do Sorteio** (`fisica_sorteio.py`): perfil bolas (massa, diâmetro, cor, rugosidade, coef restituição) + ambiente (temp, pressão, umidade, rotação) → score físico integrado como fonte
- **Singularidade** (`singularidade.py`): EspectroTemporal (Hurst), TeoriaDaInformação (entropia permutação), FiltrosAvancados (gaps, entropia condicional, coocorrência, Mahalanobis), GestaoDeBanca (EV, Kelly), CoberturaSteiner (cotas), ValidadorForaDaAmostra (backtest honesto)
- **Wheeling** (`wheeling.py`): universo exato C(25,15)=3.268.760, família exata α=1 `⌈16/(N−15)⌉`, greedy Johnson para α≥2, verificação exata + probabilística
- **Forja** (`forja_lotes.py`): ver seção 6

### 2.2 Outros cores
- `bitmatrix.py`: conversão dezenas ↔ bitmask int (popcount para interseções)
- `caixa_client.py`: HTTP Caixa com headers Referer, parsing listaDezenas, listaRateioPremio
- `data_loader.py`: carga completa, atualização diária, status base
- `conferencia.py`: confere cartelas vs resultados, lotes, prêmios
- `financeiro.py`: registra lucro/prejuízo pós-conferência (hook `_registrar_financeiro`)
- `heavyweight_engine.py`: avalia universo completo pontuando por vetor vf (3.268.760 combos)
- `oraculo_convergente.py`: 15 oráculos, consenso, anti-repetição

## 3. FLUXOS

### 3.1 Fluxo único de decisão (Magna)
1. `decidir_e_gerar(quantidade, orcamento, alvo, modo, registrar)`
   - lock ` _magna_lock`
   - treina se necessário (14 motores)
   - `_fontes_assimiladas_magna()` → 6 fontes: motores, oráculos, espectral, informação, recente, física
   - pesos fontes carregados de `magna_estado` (pesos_fontes) → vetor final = Σ fonte_i * peso_i → `_aplicar_memoria_episodica` (reforça protótipos ≥12, repele ≤9)
   - `_planejar_rota_extraordinaria()` → `melhor_rota_por_orcamento` escolhe rota que maximiza P(lote≥alvo) dentro do orçamento
   - `gerar_otimas(vetor_override=vetor_final, alvo, modo)` → estratégia:
     - n=1: exaustão universo melhor cartela
     - 2-7: exaustão diversa (≤13 em comum)
     - ≥8: wheeling garantia 14 (8 cartelas) + exaustão diversa excedente
     - alvo=15 + n≥16: pool 16 → 16 cartelas garante 15 se capturar (1:204.297)
     - alvo=13 + n≥6: pool 18 família exata 6 cartelas (1:4.006) ou pool 19 dual 13 cartelas (1:843) — agora estendido até pool 21
     - modo=forja: forja espacial extraordinária
   - Singularidade interpreta cada cartela (filtros avançados + contribuições fontes)
   - registra em `magna_decisoes` + retorna JSON seguro

### 3.2 Pós-sorteio
`ciclo_pos_sorteio_caixa()` → recarrega matriz, treina, confere `magna_decisoes` aguardando, `aprender_resultado_magna` ajusta pesos fontes (±2% por fonte baseado em top15 vs real), registra episódios, checkpoint/rollback se média cair, ajusta pesos módulos via mediana acertos fora amostra

## 4. APIs

- `POST /api/magna/decidir` → única porta: {quantidade, orcamento, alvo 13/14/15, modo auto/forja, salvar}
- `GET /api/magna/forja/menu?orcamento=` → menu captura + rota_extraordinaria + métodos extraordinários
- `POST /api/magna/ancoras-123` → 3 cartelas âncora 01/02/03 exclusivas
- `GET /api/magna/fisica`, `POST /api/magna/fisica/bola`, `POST /api/magna/fisica/ambiente` → fonte física
- `GET /api/magna/aprendizado` → diagnóstico o que aprende/como/falta
- Legados: `/api/cerebro/otimas`, `/api/cerebro/gerar`, `/api/cerebro/wheeling` → delegam para Magna; `/api/cartela_do_dia`, `/api/adicionar_cartelas_concurso` → 410 com nova_rota
- `POST /api/treinar_ia`, `/api/cerebro/treinar` → treino background
- `GET /api/cerebro/status`, `/api/status`, `/api/status_base`
- `POST /api/cerebro/ciclo`, `/api/cerebro/loop/*`, `/api/cerebro/fila/<concurso>`, `/api/cerebro/historico`, `/api/cerebro/backtesting`
- `GET /api/singularidade/analise`, `POST /api/singularidade/backtest`, `POST /api/cerebro/wheeling/backtest` (walk-forward captura)
- Conferência: `POST /api/conferir`, `POST /api/conferir_concurso`, `GET /api/cartelas_concurso/<c>`, `GET /api/lotes`, `GET /api/lote/<id>`, `POST /api/apagar_lote`, `POST /api/conferir_lote`
- Prêmios: `GET /api/premios/<c>`, `POST /api/atualizar_premios_todos`
- Dados: `POST /api/carregar_dados`, `POST /api/atualizar_dados`

## 5. BANCO (SQLite)

Tabelas principais:
- `resultados` (concurso, data, d1..d15, soma, pares, premio_11..15, ganhadores_15)
- `cartelas` (id, data_geracao, concurso_alvo, d1..d15, bitmask, scores, lote_id, tipo_geracao, acertos, premio)
- `lotes_cartelas` (lote_id, data_criacao, concurso_alvo, tipo_geracao, quantidade, custo_total, modo, grupo_elite JSON, cobertura_13)
- `fila_conferencia` (concurso_alvo, dezenas JSON, timestamp_geracao, scores_modulos JSON, score_total, status, acertos, premio_ganho, dezenas_acertadas, erro_previsao)
- `historico_ciclos` (concurso, timestamp_inicio/fim, status, n_cartelas, melhor_acertos, media_acertos, total_ganho, pesos_antes/depois JSON)
- `memoria_erros` (concurso, modulo, erro, impacto)
- `desempenho_modulos` (concurso, modulo, correlacao, peso_antes/depois)
- `cartela_do_dia` (concurso_alvo, dezenas JSON, quorum_usado, confianca, consenso_forca, score_cerebro, aprovado_filtros, votos_json, acertos, premio, conferida)
- **Magna**:
  - `magna_estado` (chave=pesos_fontes, valor JSON, atualizado_em)
  - `magna_decisoes` (concurso_alvo, timestamp, quantidade, estrategia, cartelas_json, analise_json, justificativa, status aguardando/conferida, resultado_json, melhor_acertos, media_acertos)
  - `magna_aprendizado` (decisao_id, concurso, fonte, acertos, peso_antes/depois)
  - `magna_episodios` (concurso, dezenas JSON, acertos, faltaram JSON, tipo prototipo/repulsao/neutro)
  - `magna_checkpoint` (timestamp, pesos_json, media_acertos, n_amostra)
  - `memoria_cartelas_aprendidas` (criada via migrar.py — não no snapshot atual mas via criar_tabelas)
- `avaliacao_desdobramento` (concurso, grupo JSON, v, t, acertou_grupo, dezenas_escaparam, dezenas_fora JSON, melhor_acerto)
- `financeiro` (via financeiro.py)
- Física: `fisica_bolas`, `fisica_ambientes` (via fisica_sorteio.py)

## 6. GARANTIAS MATEMÁTICAS

- **Universo exato**: C(25,15)=3.268.760 (MotorWheeling.universo() gera todas máscaras uint32)
- **Probabilidades por cartela (imutáveis)**: 13=1/691, 14=1/21.800, 15=1/3.268.760 (hipergeométrica)
- **Wheeling família exata α=1**: para N=16,17,18 garante t=31−N com ⌈16/(N−15)⌉ cartelas (provado, verificação exata percorre todos complementos)
- **Greedy Johnson α≥2**: cota esfera inferior `C(N,s)/bola`, verificação exata para N≤19 ou probabilística (10k amostras) para N≥20
- **Fechamento Dual**: |c∩d|≥t ↔ |c̄∩d̄|≥α=t+N−30, cobertura no espaço dos complementos com força máxima (tabu + ensemble)
- **Análise lote exata**: `wheeling.analisar_lote` calcula sobre universo completo P(melhor≥13/14/15), EV, distribuição hipergeométrica
- **Backtest captura**: walk-forward honesto — treina sem concurso alvo, seleciona pool, verifica interseção; baseline teórico P(captura)=C(N,15)/C(25,15), E[interseção]=15·N/25

## 7. INTELIGÊNCIA MAGNA — DETALHAMENTO EXTRAORDINÁRIO

### 7.1 Fontes assimiladas (6)
- **motores** 0.40: vetor combinado 14 motores com ruído caótico 3% (dinamismo diário, RNG local)
- **oraculos** 0.22: 15 teorias, votos + pesos_acumulados (0.55 pesos +0.45 votos)
- **espectral** 0.10: EspectroTemporal score espectral por dezena (Hurst)
- **informacao** 0.10: TeoriaDaInformacao entropia permutação por dezena
- **recente** 0.10: janela 50 concursos
- **fisica** 0.08: MotorFisicaSorteio score físico (massa, diâmetro, etc.)
- Pesos salvos em `magna_estado`, ajustados pós-sorteio: `peso *= (1+0.02*(acertos_fonte-9))`, normalizado, min 0.01

### 7.2 Decisão única
- **Serialização**: `_magna_lock` RLock, `decidir_e_gerar` é única função pública que cria cartelas; todas rotas passam por ela
- **Idempotência cartela_do_dia**: `gerar_cartela_do_dia(reaproveitar=True)` verifica se já existe cartela para próximo concurso, reaproveita com re-análise oráculos
- **Repulsão vetorial**: `MotorRepulsaoVetorial` bloqueia duplicatas exatas (15 iguais), penaliza 14/13/12 iguais; 2 passagens: estrita (≥0.5) + relaxada (≥0.1) reaproveita relaxáveis ordenadas por score
- **Bloqueio 15 oficial**: `_mascaras_sorteios_15()` cache bitmasks de todos resultados oficiais; `_cartela_ja_foi_15` e `_substituir_cartelas_ja_sorteadas_15` garantem nunca reemitir combinação que já foi 15 pontos

### 7.3 Aprendizado
- **O que aprende**: pesos 6 fontes via top15 vs real, pesos 14 módulos via mediana acertos fora amostra, episódios protótipo (≥12) e repulsão (≤9), checkpoint/rollback se média 10 decisões cair, combinações 15 bloqueadas, cartelas conferidas em memoria
- **Como**: após conferência oficial, fecha `magna_decisoes`, grava `magna_aprendizado`, episódios, ajusta pesos suavemente, persiste `magna_checkpoint`
- **Memória episódica**: `_aplicar_memoria_episodica` reforça dezenas de protótipos *1.04 e faltaram *1.02, repele repulsão *0.99
- **Checkpoint**: a cada 10 conferidas, se média recente < anterior, restaura pesos do último checkpoint
- **Métricas vs acaso**: `metricas_vs_acaso` → média acertos, baseline 9.0, taxa lote ≥13, protótipos/repulsoes

### 7.4 Escada de captura 13/14/15 (força máxima)
- **15 pontos**: pool 16 → 16 cartelas garante 15 se pool capturar (1:204.297) — máxima garantia combinatória
- **14 pontos**: pool 17 → 8 cartelas garante 14 se capturar (1:24.035) — ótimo provado
- **13 pontos**: pool 18 família exata 6 cartelas (1:4.006, ~6× pool-17), pool 19 dual 13 cartelas (1:843, ~28×), pool 20 dual 20 cartelas (1:210), pool 21 dual 30 cartelas (1:50) — escada troca pontos garantidos por probabilidade
- **Menu**: `menu_captura(orcamento)` retorna para cada degrau: alvo, n_pool, metodo, cartelas_teoricas, custo_teorico (cartelas*3.5), p_captura, um_em_captura, dentro_do_orcamento
- **Melhor rota por orçamento**: `melhor_rota_por_orcamento(vf, orcamento, quantidade, alvo_desejado)` avalia todas rotas do menu que cabem no orçamento + rota forja-extraordinária (pool 22, 8 cartelas R$28, P≈1.5× wheeling), escolhe max score = p_captura*(1+alvo/10)
- Exemplo real: orçamento R$100, quantidade 8, alvo 13 → rota escolhida pool 22 forja-extraordinária R$28, captura N/A (forja maximiza leque)

### 7.5 Forja espacial extraordinária (P0)
- **Regiões alto acerto**: RegiaoAltoAcerto enumera leques exatos: |R13|=4.876, |R14|=151, |R15|=1; `uniao_lote` calcula |∪R_t| → P(melhor≥t)=|∪|/3.268.760
- **MotorGrafos — pool elite extraordinário** (NOVO v9.2):
  - Similaridade cosseno co-ocorrência: s = (MᵀM)/√(freq·freq), distância euclidiana = √(1−s)
  - `pool_extraordinario(vf, tam, lambda_div=0.38, candidatas_top=22)`: score = (1−λ)*vf_norm + λ*(0.6*min_dist+0.4*mean_dist) com jitter 0.5% para escapar ótimo local, garantia quadrantes
  - `diversidade_pool`: média/min/max distância par a par
  - Magna usa exclusivamente este método: `_selecionar_elite` delega para `_selecionar_elite_extraordinaria` (todas chamadas migradas)
- **Mapa Informacional**: MDS clássico (duplo-centralizada, autodecomposição) projeta 25 dezenas em R³, `constelacao` raio médio, distância média pares, `amostra_gonzalez` k dezenas maximamente distantes
- **Geometria Johnson**: espectro interseções J(25,15), z-dispersão vs 200 lotes aleatórios, leque total vs primeira cartela, amplificação
- **ForjaDeLotes v2 extraordinária**:
  - `forjar`: SA single-run, 20 candidatas, k_robusto=3, massa plausibilidade incremental (Dirichlet concentração 900)
  - `forjar_com_forca_maxima`: ensemble 5 seeds (1000,1137,1274,1411,1548), 25 candidatas, k=5 robusto, 30s total (6s por seed), tracking melhor_p, historico_seeds, tempo_total, candidatas_extraordinarias, k_robusto_extraordinario
  - `forjar_14_exato`: greedy exato para alvo 14 (leque 151), top 22 dezenas → C(22,15)=170k combos, avalia top 5000 por vf, greedy maximiza ganho massa plausibilidade (w = pesos plausibilidade universo)
  - FechamentoDual `fechar`: cobertura dual com tabu list 100, varredura blocos 512, jitter; `fechar_com_forca_maxima`: ensemble 3 tentativas, melhor cobertura
- **Integração Magna**: `gerar_otimas` modo=forja → alvo 13/14, 30s força máxima, 25 candidatas, 5 seeds, k=5; se alvo 14 e n≤15 usa `forjar_14_exato` + completa com forja max; relatório forja inclui moves, aceites, um_em_exata, massa, historico_seeds
- **Exemplo real testado**: 8 cartelas, orçamento R$100, alvo 13, modo forja → 937 movimentos, P(melhor≥13)=1 em 85.6, custo R$28, EV -14.03, pool elite extraordinário [1,2,3,4,5,6,9,12,13,14,15,17,20,22,25]

## 8. FRONTEND

- `templates/cerebro.html`: painel único Magna, forja-grid (menu captura tabela, mapa MDS canvas, espectro Johnson), controles quantidade/orçamento/alvo/modo forja, decisão única botão, histórico Magna, retencao protótipos, métricas
- `templates/base.html`: sidebar status IA online/offline, total concursos
- Outros templates redirecionam para cerebro (gerar, wheeling, analise, etc.)

## 9. VERDADES HONESTAS (auditoria)

- Probabilidade por cartela imutável: 14=1:21.800, 15=1:3.268.760
- Garantias wheeling condicionais: só valem se pool capturar as 15
- Forja maximiza estrutura lote sob modelo plausibilidade Magna — ganho combinatório, nunca preditivo
- Backtest captura consistente com acaso (§3 AUDITORIA.md) — pool não captura além baseline de forma consistente
- Hurst médio ≈0.5 → sem memória (sorteio justo), entropia permutação alta → aleatório

## 10. O QUE FOI ENTREGUE NESTA SESSÃO (P0 extraordinária)

- `core/forja_lotes.py` v2.0 reescrito: MotorGrafos pool_extraordinario vf+diversidade euclidiana λ0.38+jitter+garantia quadrantes, ForjaDeLotes.forjar_com_forca_maxima multi-seed 5 corridas 30-60s n_candidatas=25 k_robusto=5, forjar_14_exato greedy 151 leque, FechamentoDual fechar_com_forca_maxima ensemble, menu_captura estendido até pool 21, melhor_rota_por_orcamento
- `core/cerebro_ia.py` v9.2: import MotorGrafos/melhor_rota_por_orcamento, VERSAO_MAGNA 9.2, _selecionar_elite delega para _selecionar_elite_extraordinaria, _selecionar_elite_extraordinaria com log diversidade, _planejar_rota_extraordinaria, gerar_otimas pool elite extraordinário + forja força máxima, decidir_e_gerar planejamento rota log, get_status versão 9.2
- `app.py`: api_magna_forja_menu retorna versao 9.2, menu, rota_extraordinaria, extraordinaria métodos, orcamento query param
- Testes runtime: pool extraordinário [1,2,3,4,5,9,10,11,12,13,14,15,20,21,22,24,25] div média 0.64, forja 8 cartelas 937 moves P=1/85.6, rota orçamento R$100 → pool 22 forja R$28

## 11. COMO USAR (exemplos)

- `POST /api/magna/decidir {"quantidade":8,"orcamento":100,"alvo":13,"modo":"forja","salvar":true}` → lote extraordinário 8 cartelas R$28
- `POST /api/magna/decidir {"quantidade":8,"orcamento":100,"alvo":13}` → escada 13 pool 18 família exata 6 cartelas R$21 (ou 13 cartelas se quantidade≥13)
- `GET /api/magna/forja/menu?orcamento=100` → menu completo + melhor rota
- `python -c "from core.cerebro_ia import CerebroIA; c=CerebroIA(); print(c.decidir_e_gerar(8,100,13,'forja',False))"`

Fim da auditoria.
