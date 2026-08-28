# 📋 Relatório — o que a Inteligência Magna oferece hoje

**Data:** 28/08/2026 (America/São Paulo) · **Versão declarada:** `11.0-Magna-Suprema-Unica-Pessoal-Evoluida`, linha evolutiva **v11.4** (acervo nativo)
**Banco lido:** `database/lotofacil.db` — 3.773 concursos, próximo concurso **3774**
**Referência de código:** `core/cerebro_ia.py` (5.764 linhas, 17 classes) · `core/magna_suprema.py` (1.080 linhas, 22 instrumentos) · `app.py` (78 rotas)
**Estado do tree:** PR #14 aberto (`arena/01a048de-lotofacil-system` → `main`), `pytest -q` = **121 passed**, bandit medium+ = **0** nos arquivos alterados

Este documento é inventário, não propaganda. Cada número abaixo vem do código, do
banco ou de medição feita nesta sessão. O que o sistema **não** faz está dito na
seção 12.

---

## 1. O que é a Magna hoje

Uma única inteligência com **uma memória, uma análise e uma decisão**. Não existe
segundo gerador, segundo painel decisório nem módulo paralelo: os antigos painéis
(gerar, Cartela do Dia, wheeling, análise, singularidade, auditoria, física,
avaliação, padrões de abertura) foram **absorvidos** e hoje são fontes de
evidência, instrumentos e seções de tela dentro dela.

| Papel | Quem executa | Onde |
|---|---|---|
| **Aprender** | `treinar()`, `assimilar_acervo()`, `calibrar_pesos_walkforward()`, `aprender_resultado_magna()`, `aprender_ordem_sorteio()`, `aprender_abertura_medida()` | `core/cerebro_ia.py` |
| **Memorizar** | `magna_decisoes`, `magna_aprendizado`, `magna_estado`, `magna_episodios`, `magna_checkpoint`, `magna_conhecimento`, `magna_memoria` | `_criar_tabelas_ciclo()` |
| **Interpretar / analisar** | 14 motores + 15 oráculos + espectro + teoria da informação + física + clima + **acervo de abertura** | `_fontes_assimiladas_magna()` |
| **Decidir** | `decidir_e_gerar()`, `decidir_suprema()`, `decidir_ancoradas_01_02_03()`, `pipeline_wheeling()`, `alocar_orcamento_inteligente()` | `core/cerebro_ia.py` |
| **Criar cartelas** | `gerar_otimas()`, `_selecionar_elite_extraordinaria()`, MCTS pool, Forja Espacial, `MotorExaustaoUniverso` (3.268.760 jogos) | `core/forja_lotes.py`, `core/heavyweight_engine.py` |
| **Julgar** | `julgar_lote()` → `JuizMagna` (9 critérios) + `JuizAdversarial` + `TesteNIST` + `PValueRandom` + `VerificadorMagno` | `core/magna_suprema.py` |
| **Conferir e fechar ciclo** | `executar_ciclo()`, `ciclo_pos_sorteio_caixa()`, `iniciar_loop()` (Caixa) + `core/conferencia.py` | `core/cerebro_ia.py` |
| **Explicar** | `ExplainabilityMagna`, `ChatMagna` ("por que 22?") | `/api/magna/chat` |

Superfície: **41 métodos públicos** no `CerebroIA` + **33** no `AcervoAberturaMagna`.

## 2. O ciclo (é isto que roda, nesta ordem)

```text
1  base histórica (resultados + ordem_sorteio + clima + física)
       ↓  __init__ monta o acervo (~0,4 s p/ 3.773 concursos) e a fonte de abertura
2  treinar() → 14 módulos + Oráculo Convergente (15 teorias) + espectro/informação
       ↓
3  _garantir_acervo() → reassimila se a base mudou (carimbo em magna_conhecimento)
       ↓
4  _fontes_assimiladas_magna() → 8 fontes → pesos (magna_estado) → vetor combinado
       ↓
5  rota: exaustão única · exaustão diversa · wheeling-garantia-13/14/15 · suprema-forja
       ↓
6  juiz 9 critérios + adversarial + NIST + p-value  →  regenera se reprovar
       ↓
7  fingerprint SHA256 · bloqueio de combinação que já deu 15 · backtest 50 ·
   verificação exaustiva do lote · utilidade esperada por perfil de risco
       ↓
8  decisão persistida (com digest do acervo e o palpite de abertura registrado)
       ↓
9  sorteio sai → conferência → aprende (pesos por fonte) → JULGA o próprio palpite
   → reassimila o acervo → checkpoint/rollback se a média de 10 cair
```

## 3. As 8 fontes do consenso (com os pesos medidos hoje)

| Fonte | O que traz | Default | Medido em walk-forward (48 passos, base inteira) |
|---|---|---|---|
| `motores` | 14 motores: freq global/recente, reversão, anti-lógica, Markov, quantum (Lorenz), Verlet, χ², Bayes, KL, gaussiano, genético, cobertura, stacking | 0,36 | **0,363** |
| `oraculos` | 15 oráculos convergentes (termodinâmico, quântico, físico, bayesiano, markov, caótico, fractal, gravitacional, neural, genético, estatístico, fourier, topológico, relativista, anti-comunidade) + entropia de nanossegundo | 0,18 | **0,182** |
| `espectral` | Espectro temporal (Potter, Hurst, entropia de permutação, variância residual, multifractal) | 0,10 | **0,105** |
| `informacao` | Teoria da informação (mutua, transferência, não-linearidade) | 0,10 | **0,097** |
| `recente` | leitura dos últimos concursos / regime | 0,09 | **0,096** |
| `fisica` | perfil físico das bolas + ambiente (Verlet, balanço 0,001 g) | 0,08 | **0,077** |
| `clima` | temperatura × pressão × umidade, 3 testes físicos, shrinkage, teto ±10% | 0,05 | **0,053** |
| `abertura` | **acervo v11.4**: quem abre o sorteio | 0,04 | **0,027** |

A calibração **derrubou** `abertura` abaixo do default: foi o medidor trabalhando,
não um defeito. Peso algum é prometido — todos são pagos com prova fora-da-amostra.

## 4. Ferramentas combinatórias e de busca

- **Exaustão do universo:** `MotorExaustaoUniverso` avalia os **3.268.760**
  jogos em ~0,3 s e devolve a cartela ótima por score (com rank no universo);
- **Escada de captura** (`GET /api/magna/forja/menu`, valores exatos, não simulados):

| Alvo | Pool | Cartelas | Custo | Garantia | P(captura) | 1 em |
|---|---|---|---|---|---|---|
| 15 | 16 | 16 | R$ 56,00 | 15 | 4,89e-06 | 204.298 |
| 14 | 17 | 8 | R$ 28,00 | 14 | 4,16e-05 | 24.035 |
| 13 | 18 | 6 | R$ 21,00 | 13 | 2,50e-04 | 4.006 |
| 13 | 19 | 13 | R$ 45,50 | 13 | 1,19e-03 | 843 |
| 13 | 20 | 20 | R$ 70,00 | 13 | 4,74e-03 | 211 |
| 13 | 21 | 30 | R$ 105,00 | 13 | 1,66e-02 | 60 |

- **Forja Espacial** (`core/forja_lotes.py`): leques exatos por alvo, fechamento
  dual no espaço dos complementos, `GeometriaJohnson` (interseções), `MotorGrafos`
  (diversidade do pool), `MapaInformacional` (MDS 25×2 desenhado na UI);
- **Wheeling** (`pipeline_wheeling`): desdobramento com garantia condicional N+1,
  backtest walk-forward da taxa real de captura (`/api/cerebro/wheeling/backtest`);
- **MCTS pool** (`MCTSPool`, UCT) + **forja suprema** (60 s, 7 seeds, k=7,
  25 candidatas) + **multi-rota** 60/30/10 + **alocador de orçamento** por teto;
- **Anti-repetição pessoal:** `FingerprintPessoal` (SHA256 do histórico pessoal) e
  bloqueio de qualquer combinação que **já saiu com 15 pontos** no histórico oficial.

## 5. Julgamento (9 critérios + três juízes auxiliares)

`JuizMagna.julgar(...)`: `diversidade_pool`, `cobertura_13`, `novidade_15`,
`quadrantes`, `johnson_z`, `ev`, `calibracao_vf`, `filtros_soma` e — desde a
v11.4 — **`cobertura_abertura`**, que mede quanta da massa de abertura aprendida
o lote cobre. É opt-in (só entra quando a Magna passa `abertura=`), pesa 0,6 e
**não** vira cota para lote pequeno: uma cartela só pode abrir de um jeito.
Se o lote reprova, a Magna regenera (`tentativas_juiz` até 3) e registra o
resultado com `nota`, `utilidade` e `reprovados`.

Acompanham: `JuizAdversarial` (ponto único de falha, interseção média, pool
pequeno), `TesteNIST` (χ² de aleatoriedade do lote), `PValueRandom` (lote vs
baseline aleatória), `VerificadorMagno` (união exata dos leques do lote),
`BacktestLote` (50 concursos), `TesteBinomial`, `CurvaAprendizado`.

## 6. O acervo nativo (v11.4) — o que a Magna sabe sobre a abertura

Um órgão interno (`AcervoAberturaMagna`), dois canais: **`minima`** (a menor
dezena da lista ordenada — base: todos os concursos) e **`real`** (a 1ª bola
física — base: `ordem_sorteio`).

Estado medido hoje, na base real:

```text
aprendido até: concurso 3773 · 3.773 concursos memorizados · 3 com ordem real
palpite: 01 (60,5%) · 02 (24,6%) · 03 (9,8%)   [margem teórica: 60,0 / 25,0 / 9,8]
abertura atual: 03 no 2º concurso seguido · recorde 01: 17 concursos (1750–1766)
P(repetir 03 | streak 2) = 9,5% em 42 provas  →  igual aos 9,8% de sempre
placar walk-forward (3.771 provas sem vazamento):
   prever sempre nº 1 do ranking → 60,6% (teto 60,0%)
   cobrir as 2 primeiras         → 85,3% (teto 85,0%)
   excluir a abertura em sequência → 51,7% (−8,9 p.p.)
auto-auditoria: RUÍDO · lift 1,0108 · p 0,425 → fator de confiança 0,5
digest: sha256:0bba3f2807ea054c
```

Onde o acervo entra: fonte `abertura` do consenso; `interpretacao_magna["abertura"]`
por cartela; `scores["afinidade_abertura"]` e `afinidade·0,05` na pontuação; 9º
critério do juiz; `ancoras_do_acervo(3)`; `memoria_magna.palpite_abertura`
(julgável na conferência); `get_status()["acervo"]`; `diagnostico_aprendizado()`;
seção "Acervo nativo" no `/cerebro`.

## 7. Autonomia (roda sozinha, sem você pedir)

- `iniciar_loop(LOTOFACIL_LOOP_SEG=1800)` monitora a Caixa: sorteio novo →
  ingere (com cadeia de contingência de `CaixaClient`, incluindo
  `dezenasSorteadasOrdemSorteio`) → treina → confere → aprende → reassimila o
  acervo → planeja o próximo (`ciclo_pos_sorteio_caixa`);
- boot: `LOTOFACIL_ACERVO_BOOT=1` (default) dispara em thread a **calibração
  fundante** (pesos das 8 fontes na base inteira) antes do primeiro pedido;
- fila de conferência (`fila_conferencia`), histórico de ciclos, log por nível,
  `pausar_loop`/`retomar_loop`/`parar_loop`;
- `metricas_vs_acaso()`: média de acertos das decisões conferidas vs baseline
  de 9,0 dezenas por cartela — a Magna se compara ao acaso, não a si mesma;
- checkpoint/rollback: a cada 10 conferidas, se a média cair, os pesos voltam.

## 8. Física e clima (duas fontes que aceitam dado do mundo real)

- **Física:** `fisica_bolas` (25 perfis — massa 66 g, Ø 50 mm, restituição 0,82),
  `fisica_ambientes`; simulação Verlet (`MotorVerlet`), `FisicaRealBalanca` para
  entrada de medição real em 0,001 g; `POST /api/magna/fisica/bola|ambiente`;
- **Clima:** `core/clima_lotofacil.py` — previsão de temperatura/pressão/umidade
  do próximo sorteio, 3 testes (ímpares×pressão, soma×umidade, frequência×
  temperatura), shrinkage 50/50, teto ±10%, auto-auditoria walk-forward que
  escala o fator da fonte; ingestão `POST /api/magna/clima/ingestao`;
  100 registros hoje.

## 9. Interpretabilidade

- `ExplicabilityMagna`: explicação por dezena e por cartela (contribuição de cada
  fonte, votos dos oráculos, convergência média, filtros avançados, **abertura**);
- `ChatMagna` (`POST /api/magna/chat`): "por que a 22?" com a memória da decisão;
- `justificativa_magna` de toda decisão cita estratégia, pesos, juiz, backtest,
  verificação exaustiva e **o veredito do acervo com digest**;
- `diagnostico_aprendizado()`: `o_que_aprende`, `como_aprende`, `o_que_falta`
  (computado, não decorado), `retencao`, `acervo`.

## 10. Interface

**Painel único `/cerebro`** com: comando de decisão (quantidade/orçamento/alvo/
perfil/forja/salvar), **Acervo nativo** (leitura, previsão, placar, pesos,
reler base, calibrar, ingestão da ordem real), resultado com cartelas e
interpretação, forja (menu da escada, mapa MDS, espectro), história de decisões,
física/ambiente e avaliação. As demais páginas viraram âncoras/redirecionamentos
do mesmo cérebro (`/gerar`, `/wheeling`, `/analise`, `/singularidade`,
`/ia_auditoria`, `/fisica`, `/avaliacao`, `/cartela_do_dia`, `/ordem`).

Rotas da Magna (78 no total; as principais):

```http
POST /api/magna/decidir                 # ÚNICA porta de criação de cartelas
POST /api/magna/suprema                 # potência máxima (forja+MCTS+juiz+...)
POST /api/magna/ancoras-123             # 3 âncoras escolhidas pelo acervo
GET  /api/magna/forja/menu              # escada de captura exata 13/14/15
POST /api/magna/verificar               # verificação exaustiva + backtest + binomial
POST /api/magna/chat                    # explainability
GET  /api/magna/regime | /perfil | /fingerprint
GET  /api/magna/fisica | /clima | /clima/testes
POST /api/magna/fisica/bola|ambiente | /clima/ingestao
GET  /api/magna/abertura                # o que a Magna sabe do próximo início
GET  /api/magna/conhecimento[?dominio=] # acervo: base, fontes, pesos, memória
POST /api/magna/conhecimento/assimilar  # reler base (e, se quiser, calibrar)
POST /api/magna/ordem/ingestao          # 15 bolas ou só a abertura — pela Magna
GET  /api/magna/aprendizado             # diagnóstico contínuo
POST /api/cerebro/ciclo | /treinar | /loop/{iniciar,parar,pausar,retomar}
GET  /api/cerebro/status|historico|fila/<concurso>|log
POST /api/conferir | /api/conferir_lote | /api/avaliacao
```

**CLI** (`gerar_pessoal.py`): `--qtd --orcamento --alvo --perfil --modo --segundos
--tentativas --mcts --multi-rota --ancoras --salvar --chat --temp --pressao
--umidade` + v11.4: `--assimilar --calibrar-pesos --limite-calibracao
--conhecimento --memorizar-abertura "3774:07"`.

**Flags:** `LOTOFACIL_ACERVO_AUTO=0` (acervo somente-leitura — não grava nem
recalibra sozinho), `LOTOFACIL_ACERVO_BOOT=0` (sem pré-carga), `LOTOFACIL_DB`
(outro banco, para validar em cópia), `LOTOFACIL_LOOP_SEG`, `LOTOFACIL_HOST/PORT`,
`LOTOFACIL_DEBUG`.

## 11. Persistência

| Tabela | Conteúdo | Hoje |
|---|---|---|
| `resultados` | 15 dezenas + `d1`..`d15` + prêmios | 3.773 linhas |
| `ordem_sorteio` | 1ª→15ª bola física (CHECK 1–25, upsert) | 3 linhas |
| `magna_decisoes` | cada decisão: cartelas, análise, justificativa, status, média/melhor acertos | 0 |
| `magna_aprendizado` | ajuste de peso por fonte, por decisão conferida | 0 |
| `magna_estado` | pesos do consenso (com migração `ordem`→`abertura`) | 1 |
| `magna_episodios` | memória episódica (EWC / atenção) | 1 |
| `magna_checkpoint` | snapshot de pesos p/ rollback | 0 |
| **`magna_conhecimento`** | snapshots `base`/`abertura`/`fontes`/`memoria` com `digest`, veredito, fator, origem | novo na v11.4 |
| **`magna_memoria`** | eventos `assimilado`/`calibrado`/`aprendido`/`palpite` | novo na v11.4 |
| `memoria_cartelas_aprendidas` | cartelas conferidas arquivadas | 0 |
| `memoria_erros` | trilha de erros/avisos | 8 |
| `desempenho_modulos` | acerto por motor | 14 |

## 12. Honestidade matemática (parte do produto, não rodapé)

- **Nada aqui altera a probabilidade de uma cartela.** Cada jogo tem
  P(15)=1/3.268.760 · P(14)=1/21.792 · P(13)=1/692,2 · P(12)=1/60,4 ·
  P(11)=1/11,06 — hipergeométrica exata (`C(15,k)·C(10,15−k)/C(25,15)`),
  invariante a qualquer leitura de frequência, espectro, física, clima ou
  **abertura**;
- **EV negativo, publicado em toda decisão:** 1 cartela → EV ≈ **−R$ 1,75**;
  2 cartelas na rota suprema de hoje → **−R$ 6,07 (ROI −86,8%)**. Na rota
  pool 19/13 cartelas, o custo esperado até capturar um 13 é ≈ **R$ 38.357**
  para um prêmio de R$ 35: estrutura, não lucro;
- **Garantia condicional:** o N+1 do fechamento só vale se o pool contiver as 15
  sorteadas — por isso o menu mostra P(captura) do pool, não "garantia de 13";
- **Padrões de sequência não superam o acaso:** veredito RUÍDO → vetor atenuado
  0,5; a regra popular de excluir a abertura em sequência **perde 8,9 p.p.** e o
  sistema não a obedece;
- **Rateio:** dezenas baixas (01/02/03) são as mais jogadas pela multidão —
  cartelas que abrem nelas tendem a **piorar** o prêmio dividido. A afinidade de
  abertura é critério de coerência estrutural, e o desempate por antipopularidade
  ainda **não existe** (era a recomendação nº 3 da auditoria de 28/08);
- **Amostra de autoavaliação é zero:** `magna_decisoes` tem 0 linhas — o loop de
  aprendizado por conferência está ligado e testado, mas **nunca viu um sorteio
  real conferido desde que existe**. Toda a conhecimento acumulado hoje vem da
  base histórica, não de decisões próprias.

## 13. Cobertura de prova

| Arquivo | Testes |
|---|---|
| `tests/test_magna_acervo.py` | 27 |
| `tests/test_clima.py` | 14 |
| `tests/test_forja_lotes.py` | 13 |
| `tests/test_inteligencia_magna.py` | 12 |
| `tests/test_atualizacao_historico.py` | 11 |
| `tests/test_hub_unificado.py` | 10 |
| `tests/test_regressoes_fase5.py` | 6 |
| `tests/test_wheeling.py` | 6 |
| `tests/test_fase3.py` · `test_otimas.py` | 5 · 5 |
| `tests/test_bloqueio_15_memoria.py` | 4 |
| **total** | **121 passed** (~75 s) |

Validado ao vivo nesta sessão (banco em cópia): pré-carga do boot fechou
**48/48 checkpoints** de calibração e gravou `magna_conhecimento.fontes`
(`calibrado: true`); decisão para o 3774 e âncoras 01/02/03 saíram com
`acervo_magna`, `afinidade_abertura` e `cobertura_abertura` ativo; CLI
`--assimilar --calibrar-pesos --conhecimento` e `--memorizar-abertura "3774:07"`
ok; `/ordem` 303 e `/api/magna/ordem` 410 conforme projetado.

## 14. Lacunas conhecidas (e o que cada uma custa)

1. **`n=0` decisões conferidas** — sem histórico próprio, `metricas_vs_acaso`,
   `placar_abertura_memoria` e o ajuste fino de pesos ficam de amostra pequena.
   Custo: nenhum — basta conferir após o 3774 (o loop já faz isso sozinho).
2. **Canal `real` do acervo com 3 concursos** — a 1ª bola física não foi
   capturada para os outros 3.770. Custo: `python backfill_ordem.py` (20–40 min,
   onde há rede; aqui a API da Caixa estava inacessível).
3. **`core/antipopularidade.py` não existe** — a auditoria de 28/08 mostrou
   +53% em 13 pontos e +51% em 14 para cartelas populares, e recomendou o
   desempate anti-popularidade dentro do Juiz/Forja. É o item de maior EV
   positivo ainda não implementado.
4. **CI não roda** — o workflow está em `docs/ci-github-actions.yml`, fora de
   `.github/workflows/`; pytest/bandit/pip-audit precisam ser disparados à mão.
5. **README diz "Inteligência Magna v9.0"** no título — o código é v11.4.
6. **Física sem dado real** — os 25 perfis de bola são os nominalmente
   constantes; sem medição própria (`FisicaRealBalanca` aceita, mas nada foi
   medido), a fonte `fisica` é estrutural, não empírica.
7. **Conferência depende de rede** — em ambiente offline a fila de conferência
   acumula (hoje 2 pendências) e nada do ciclo pós-sorteio roda.

## 15. Como usar amanhã (concurso 3774)

```bash
python app.py                      # sobe, lê a base inteira e calibra os pesos sozinho
python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 13 --perfil equilibrado \
                       --modo suprema --mcts --salvar
python gerar_pessoal.py --conhecimento                 # o que a Magna sabe agora
python backfill_ordem.py                               # opcional: enche o canal `real`
# após o sorteio: conferir e aprender (a Magna faz isso no loop; manual:)
curl -X POST localhost:5000/api/conferir
curl -X POST localhost:5000/api/magna/conhecimento/assimilar -H 'Content-Type: application/json' \
     -d '{"forcar":true,"calibrar_fontes":true,"limite_segundos":120}'
```

Painel: **`/cerebro`** — decisão, acervo, forja, história, física, avaliação.
