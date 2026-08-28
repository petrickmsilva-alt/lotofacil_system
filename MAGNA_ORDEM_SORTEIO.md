# 🎯 MAGNA v11.3 — Padrões da Ordem Real de Sorteio

**Data:** 28/08/2026 (America/Sao_Paulo)
**Módulo:** `core/padroes_ordem.py` · Fonte Magna: `ordem` (peso default 4%)

---

## 1. A lógica que você pediu — implementada

A hipótese era:

> "01, 02, 03 são as que mais saem no início do sorteio. Se a 03 saiu de
> início duas vezes seguidas, a chance dela sair de novo é muito pequena.
> Verifique no histórico o máximo de vezes que uma dessas saiu seguidas e
> preveja qual das outras duas vai sair."

**Implementamos cada peça dessa lógica como estatística mensurável:**

| Regra | Onde | Como é medida |
|---|---|---|
| R1 — "01/02/03 saem mais no início" | `frequencia_posicao(1)`, `frequencia_janela_inicial(3)` | contagem real da 1ª bola e das 3 primeiras bolas por dezena |
| R2 — "máximo de vezes seguidas" | `max_streak_historico()`, `distribuicao_streaks()` | maior sequência de repetição da 1ª bola em todo o histórico, por dezena |
| R3 — "repetiu 2×, não repete de novo" | `taxa_repeticao()` | P(repetir) global e condicional após streak de 1, 2 e 3+ — comparada à taxa do acaso (4%) |
| R4 — "qual das outras duas vai sair?" | `previsao_primeira_bola()` | posterior bayesiana (Dirichlet) + exclusão da última 1ª bola + ordenação das restantes do trio |

## 2. A descoberta da auditoria: você estava lendo a lista ORDENADA

O banco só guardava as dezenas **ordenadas** (d1<d2<...<d15) — a "ordem de
sorteio" real nunca tinha sido armazenada. Consultamos a API oficial da
Caixa (campo `dezenasSorteadasOrdemSorteio`) e o quadro mudou:

| Concurso | Você observou | 1ª bola REAL | Onde a citada saiu |
|---|---|---|---|
| 3770 | "03 saiu de início (2ª vez)" | **01** | 03 nem saiu neste concurso |
| 3769 | "03 saiu de início" | **09** | 03 foi a **13ª** bola |
| 3676 | "última vez da 04 no início" | **25** | 04 foi a **15ª** (última) bola |

A sensação de "01, 02, 03 no começo" vem dos sites exibirem a lista em
ordem crescente — 01/02/03 sempre "aparecem no topo". Não é a ordem das
bolas. **Agora o sistema armazena e analisa a ordem REAL.**

## 3. O que a matemática diz (e o placar confirmará com o histórico cheio)

Sob sorteio independente e auditado:

- **P(qualquer dezena ser a 1ª bola) = 1/25 = 4%**, sem memória do sorteio
  anterior. Repetir ou não repetir: sempre 4%.
- Repetições duplas da 1ª bola acontecem em **~4% das transições** — em
  3.770 concursos são **~151 repetições**. Não é sinal, é volume.
- Triplas: esperadas **~6 vezes** no histórico. Se você viu a 02 repetir
  3×, está dentro do esperado pelo acaso — não é padrão explorável.
- O "máximo de vezes seguidas" histórico (a ser confirmado no seu banco
  após o backfill) deve ficar entre 3 e 5 — exatamente o que o acaso
  produz em séries desse tamanho.

O motor **não presume** isso: ele **mede** (`taxa_repeticao`,
`placar_regra_exclusao`, `auto_ponderacao`) e publica o veredito
REAL/RUÍDO com p-valor binomial. Se algum dia o lift real superar o
acaso com significância, o peso da fonte sobe automaticamente; enquanto
isso, o vetor entra atenuado (fator 0,5 — quase uniforme) e as garantias
combinatórias permanecem intactas.

## 4. Como operar

### 4.1 Preencher o histórico (uma vez, na sua máquina local)

```bash
python backfill_ordem.py            # histórico completo (retomável)
python backfill_ordem.py --limite 300   # em fatias, se preferir
```

A API da Caixa entrega a ordem real; concursos novos passam a ser
capturados automaticamente pela sincronização do histórico e pelo ciclo
autônomo. Já semeamos com as ordens reais verificadas dos concursos
3676, 3769 e 3770.

### 4.2 Painel e API

```http
GET  /api/magna/ordem               # relatório completo
POST /api/magna/ordem/ingestao      # {concurso, ordem: [b1..b15]}
```

Exemplo de resposta (com o histórico cheio):

```json
{
  "frequencia_primeira_bola": {"1": 178, "2": 165, ...},
  "streak_maximo_historico": {"dezena": 2, "comprimento": 4},
  "taxa_repeticao": {
    "global": {"taxa": 0.0398, "taxa_acaso": 0.04, "p_valor": 0.91},
    "condicional": {"apos_2": {"n": 6, "taxa": 0.0, "taxa_acaso": 0.04}}
  },
  "previsao": {
    "regra_do_usuario": {
      "excluida": 1,
      "candidatas_restantes": [2, 3],
      "prob_repetir_a_ultima": 0.0398
    }
  },
  "auto_auditoria": {"veredito": "RUÍDO", "lift": 0.98, "fator_confianca": 0.5}
}
```

### 4.3 Na Magna

A fonte `ordem` entrou no consenso com peso default 4% (renormalizado
entre as 8 fontes). O `vetor_preferencia()` é atenuado pela
auto-auditoria walk-forward — com lift ~1 (acaso), o vetor é quase
uniforme e não distorce a decisão; as cartelas seguem nascendo da
estrutura combinatória, agora também informada pela ordem real.

## 5. Arquivos

- `core/padroes_ordem.py` — motor completo (estatísticas, previsão, placar)
- `backfill_ordem.py` — preenchimento retomável do histórico
- `database/db_manager.py` — tabela `ordem_sorteio` (CHECK 1–25, upsert)
- `core/caixa_client.py` — captura de `dezenasSorteadasOrdemSorteio` com validação
- `core/data_loader.py` / ciclo autônomo — captura automática dos novos concursos
- `tests/test_padroes_ordem.py` — 17 testes travando o comportamento
