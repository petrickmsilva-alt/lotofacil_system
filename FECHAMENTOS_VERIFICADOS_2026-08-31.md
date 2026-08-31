# Fechamentos verificados, probabilidades reais e a correção da escada — 31/08/2026

> Sessão: branch `arena/01a058ee-lotofacil-system`. Pedido: *"fazer as
> previsões diminuírem drasticamente, vasculhar tudo, trazer dados reais,
> criar o PR"*. Este documento registra **o que é possível de verdade**,
> com prova matemática, e o que foi corrigido no sistema.

---

## 0. A verdade que precisa vir primeiro

As probabilidades da Lotofácil são **fixas por lei combinatória**
(hipergeométrica sobre `C(25,15) = 3.268.760`):

| Faixa | Combinações | Probabilidade por cartela |
|---|---:|---:|
| 11 acertos | 286.650 | **1 em 11,4** |
| 12 acertos | 54.600 | **1 em 59,9** |
| 13 acertos | 4.725 | **1 em 691,8** |
| 14 acertos | 150 | **1 em 21.791,7** |
| 15 acertos | 1 | **1 em 3.268.760** |

Vasculhei o sistema inteiro e a web — **não existe método, segredo,
"deep web", IA, física de bolas ou mapa de clima que altere essas
frações**. Os sorteios são independentes, auditados (Pricewaterhouse e
próprios fiscais da Caixa), e as bolas/esferas são trocadas
periodicamente. Qualquer pessoa que venda "redução de probabilidade de
15 pontos" está vendendo fraude. O que existe de comprovável na internet
(e que o sistema agora faz **com prova exaustiva**) é isto:

1. **Fechamentos (covering designs):** a mesma garantia condicional do
   desdobramento oficial por uma fração do preço — menos cartelas para a
   mesma garantia. **Não muda a fração por cartela; muda o custo da
   garantia.**
2. **Comprar mais cartelas (ou bolão):** a chance sobe linearmente
   (`P ≈ m/3.268.760` para o 15). O EV permanece negativo.
3. **Anti-popularidade:** não muda a chance; muda com quantas pessoas o
   prêmio é dividido quando você acerta.

---

## 1. Bug grave encontrado e corrigido: a escada vendia garantia falsa

A escada antiga (`core/forja_lotes.py: menu_captura`) anunciava:

> **21 dezenas / 30 cartelas → garantia de 13 pontos** (R$ 105, "1 em 60")

Isso é **matematicamente impossível**. A cota inferior por empacotamento
de esferas de Johnson prova que são necessárias **pelo menos 33**
blocos; o motor antigo (guloso com timeout de 20 s) devolvia uma
cobertura parcial e a "verificação" usava uma **amostra de 30 mil
sorteios** — que nunca prova nada para N > 20 (existem `C(21,15)` =
54.264 sorteios possíveis só dentro do pool).

Achados relacionados da auditoria:

- `FechamentoDual.cota_esfera()` retornava o **tamanho da esfera**
  (691) em vez do número mínimo de blocos (6) — fórmula errada.
- `melhor_rota_por_orcamento` inventava `p_forja_13 ≈ 1,8×` como
  "aproximação conservadora" — ficção. Removida.

### O motor novo: `core/cobertura.py`

Covering design no **espaço dual** (`|c∩d| ≥ t ⟺ |c̄∩d̄| ≥ α`,
α = t+N−30), com:

- **verificação EXAUSTIVA de TODOS os `C(N,s)` alvos** — nunca por
  amostragem. Para N=25 são enumerados todos os 3.268.760 casos;
- popcount por tabela de bytes (ordens de magnitude mais rápido);
- greedy set cover em dois estágios (pré-rank por amostra, ganho exato
  nos finalistas), poda de blocos redundantes, multi-restart;
- resultados bons em cache
  (`database/modelos/fechamentos_verificados.json`), **reverificados a
  cada carga** e por `python fechamentos_cli.py reverificar`.

A regra agora é dura: **o sistema só anuncia "garantia verificada"
depois da prova total**. Caso não construído aparece como
"não construído (cota inferior exibida)" — número nenhum é inventado.

---

## 2. A escada VERIFICADA (dados reais, preços de 2026 — R$ 3,50/cartela)

| Pool | Garante | Cartelas **provadas** | Cota inf. | Custo | Captura do pool | Tipo |
|---:|---:|---:|---:|---:|---:|---|
| 16 | 15 | 16 | 16 | R$ 56,00 | 1 em 204.297 | condicional |
| 17 | 14 | 8 | 8 | R$ 28,00 | 1 em 24.035 | condicional |
| 18 | 13 | 6 | 6 | **R$ 21,00** | 1 em 4.006 | condicional |
| 19 | 13 | 13 | 6 | R$ 45,50 | 1 em 843 | condicional |
| 20 | 13 | 42 | 14 | R$ 147,00 | 1 em 211 | condicional |
| 21 | 13 | **113** (não 30!) | 33 | R$ 395,50 | 1 em 60 | condicional |
| 18 | 14 | 24 | 18 | R$ 84,00 | 1 em 4.006 | condicional |
| 19 | 14 | 142 | 64 | R$ 497,00 | 1 em 843 | condicional |
| 19 | 12 | 4 | 4 | **R$ 14,00** | 1 em 843 | condicional |
| 20 | 12 | 4 | 3 | **R$ 14,00** | 1 em 211 | condicional |
| 21 | 12 | 18 | 6 | R$ 63,00 | 1 em 60 | condicional |
| 22 | 12 | 37 | 10 | R$ 129,50 | 1 em 19,2 | condicional |
| 23 | 12 | 81 | 18 | R$ 283,50 | 1 em 6,7 | condicional |
| 20 | 11 | 4 | 4 | **R$ 14,00** | 1 em 211 | condicional |
| 21 | 11 | 4 | 2 | **R$ 14,00** | 1 em 60 | condicional |
| 22 | 11 | 6 | 3 | **R$ 21,00** | 1 em 19,2 | condicional |
| **25** | **11** | **52** | 10 | **R$ 182,00** | **qualquer sorteio** | **INCONDICIONAL** |
| 25 | 12 | em construção | 55 | — | qualquer sorteio | incondicional |

Os melhores produtos novos (baratos e com captura alta):

- **R$ 14,00 / 4 cartelas / pool 21 → garante 11 pontos se fechar,
  captura 1 em 60.**
- **R$ 21,00 / 6 cartelas / pool 22 → garante 11 se fechar, captura
  1 em 19,2.**
- **R$ 182,00 / 52 cartelas → garante ≥11 pontos em QUALQUER sorteio**
  (sem nenhuma premissa sobre as 15 sorteadas — prova sobre os
  3.268.760 resultados possíveis).

Comparação com o desdobramento oficial (que cobre todas as `C(N,15)`
cartelas): um desdobramento de 20 dezenas custa **R$ 54.264** e garante
15 *se o pool fechar*; o fechamento verificado entrega **12 pontos
garantidos no mesmo evento por R$ 14,00** (99,97% menos). O que se
compra é o nível de garantia — a chance de o pool fechar é a mesma
(`C(N,15)/3.268.760`) nas duas modalidades.

---

## 3. Quanto custa "comprar chance" (a única alavanca real da fração)

Com `m` cartelas distintas, `P(pelo menos um prêmio) = 1−(1−p)^m`:

| Chance desejada | 13 pontos | 14 pontos | 15 pontos |
|---|---|---|---|
| 1% | 7 cartelas (R$ 24,50) | 220 (R$ 770) | 32.853 (R$ 114.985) |
| 10% | 73 (R$ 255,50) | 2.296 (R$ 8.036) | 344.399 (R$ 1,2 mi) |
| 50% | 480 (R$ 1.680) | 15.105 (R$ 52.867) | 2,27 mi (R$ 7,9 mi) |
| 90% | 1.592 (R$ 5.572) | 50.177 (R$ 175.620) | 7,53 mi (R$ 26,3 mi) |

---

## 4. Valor esperado REAL (dados oficiais)

Prêmios fixos de 2026: R$ 7 (11), R$ 14 (12), R$ 35 (13). Rateios
médios na base local (107 concursos com rateio): **14 ≈ R$ 1.763**;
15 ≈ R$ 1,53 mi (média enviesada para baixo — inclui apenas concursos
com ganhadores; estimativa de referência R$ 2,5 mi).

| Cenário | EV bruto/cartela | Taxa de retorno |
|---|---:|---:|
| Médias reais da base | R$ 1,45 | 41,3% |
| 14 ≈ R$ 1.800 / 15 ≈ R$ 2,5 mi | R$ 1,74 | 49,8% |
| 15 acumulado ≈ R$ 6 mi | R$ 2,83 | 80,7% |

**O EV é sempre negativo.** A Lotofácil devolve em prêmios cerca de
43–45% da arrecadação (dado conferido no concurso 3775: R$ 13,05 mi de
prêmios sobre R$ 31,36 mi arrecadados = 41,6%). Fechamentos não mudam
isso: eles concentram retorno garantido nos eventos de captura.

---

## 5. Dados reais novos na base

A rede direta do sandbox está bloqueada (SSL), mas as APIs oficiais
foram consultadas e os resultados inseridos pela validação normal
(`ingestao_manual.py`):

- **Concurso 3.774 — 28/08/2026 (sexta):** 01 03 04 05 06 07 09 12 14
  15 16 18 19 23 24. Sem ganhador de 15 (acumulou); 281 ganhadores de 14
  (R$ 1.784,10); arrecadação R$ 19,97 mi.
- **Concurso 3.775 — 30/08/2026 (domingo):** 01 04 05 06 08 10 11 12 13
  15 17 18 19 23 25. Três ganhadores de 15 (Piripiri-PI, Teresópolis-RJ,
  São Paulo-SP) com R$ 1.268.987,02 cada; 412 de 14 (R$ 1.550,97);
  arrecadação R$ 31,36 mi.

Base agora: **3.775 concursos, íntegra e contínua (1–3775)**, com
ordem física de sorteio das duas extrações.

---

## 6. O que foi entregue em código

| Arquivo | Conteúdo |
|---|---|
| `core/cobertura.py` | Covering designs no espaço dual + verificação exaustiva + cache provado |
| `core/odds_reais.py` | Frações exatas por cartela, escada por orçamento, EV real |
| `core/forja_lotes.py` | `FechamentoDual.fechar` delega ao motor verificado; `cota_esfera` corrigida; `menu_captura` gerado do cache provado; rota forja sem número inventado |
| `app.py` | APIs `/api/fechamentos/tabela`, `/api/fechamentos/construir`, `/api/fechamentos/reverificar`, `/api/odds/reais` |
| `construir_fechamentos.py` | Pré-computa a tabela offline (multi-seed) |
| `fechamentos_cli.py` | CLI: `tabela`, `fechar N T`, `odds`, `chance`, `ev`, `reverificar` |
| `ingestao_manual.py` | Ingestão de resultados oficiais com validação total |
| `auditar_sistema.py` | Escada agora **reprova exaustivamente** cada fechamento anunciado |
| `tests/test_cobertura.py` (+ adaptações em `test_forja_lotes.py`) | **176 testes** (era 135) |

---

## 7. Honestidade final, em uma frase

A única forma de "diminuir drasticamente" os números 1/692, 1/21.792 e
1/3.268.760 é **comprar mais cartelas**; a forma inteligente de fazer
isso é **pagar o mínimo possível por garantia verificada** — que é o que
os fechamentos provados desta sessão entregam, sem mentir uma única
probabilidade.
