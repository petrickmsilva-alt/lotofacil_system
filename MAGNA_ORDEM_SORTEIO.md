# 🎯 MAGNA — Padrões da Ordem Real de Sorteio (registro de medição)

**Data:** 28/08/2026 (America/São Paulo) · medição v11.3/v11.3b, base até 3773
**Onde isso vive hoje (v11.4):** `AcervoAberturaMagna` dentro de
`core/cerebro_ia.py` — **órgão da Inteligência Magna**, não módulo separado.
Fonte do consenso: `abertura` (peso default 4%, atenuada pelo veredito).
Doc da integração: [`MAGNA_ACERVO_CONHECIMENTO.md`](MAGNA_ACERVO_CONHECIMENTO.md).

> Este arquivo é o **registro das medições** (o que a base histórica mostrou e o
> que foi publicado como veredito). A arquitetura, as rotas e os pesos estão no
> documento do acervo acima — o módulo `core/padroes_ordem.py`, o painel `/ordem`
> e a fonte `ordem` deixaram de existir na v11.4.

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
| R1 — "01/02/03 saem mais no início" | `frequencias(canal)`, `janela_inicial(3)` | contagem real da 1ª bola e das 3 primeiras bolas por dezena |
| R2 — "máximo de vezes seguidas" | `streaks(canal)` | sequência atual, recorde histórico e distribuição de comprimentos, por dezena |
| R3 — "repetiu 2×, não repete de novo" | `taxa_repeticao(canal)`, `repeticao_apos_streak(d, k)` | P(repetir) global e condicional após streak de 1, 2 e 3+ — medido **por dezena**, nunca agregado |
| R4 — "qual das outras duas vai sair?" | `previsao(canal)`, `posterior(canal)` | posterior (contagens suavizadas + margem) + a pergunta decisiva com as candidatas com e sem exclusão |

*(nomes na v11.4; na v11.3 eram métodos do módulo separado `core/padroes_ordem.py`)*

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

### 4.2 Painel e API (v11.4)

```http
GET  /api/magna/abertura             # o que a Magna sabe do próximo início
GET  /api/magna/conhecimento          # acervo: base, fontes, pesos, memória
POST /api/magna/conhecimento/assimilar  # {forcar, calibrar_fontes, limite_segundos}
POST /api/magna/ordem/ingestao       # {concurso, ordem: [b1..b15]} — pela Magna
GET  /api/magna/ordem                # 410 (a URL antiga aponta o caminho novo)
```

O painel `ordem.html` foi absorvido pela seção **“Acervo nativo”** de
`/cerebro`; o `MotorPadroesMinimo`/`MotorOrdemSorteio` viraram os dois canais
(`minima`, `real`) do mesmo acervo.

Exemplo de resposta **da v11.3** (o formato atual é o de
`GET /api/magna/abertura`: `digest`, `aprendido_ate`, `veredito`,
`fator_confianca`, `ranking_completo`, `probabilidades`, `palpite_top3`,
`recorde`, `placar`, `auto_auditoria`, `pergunta_decisiva`, `leitura`):

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

A fonte passou a se chamar `abertura` e entrou no consenso com peso default 4%
(renormalizada entre as 8 fontes). O vetor é atenuado pela auto-auditoria
walk-forward — com lift ~1 (acaso), ele é quase uniforme e não distorce a
decisão; as cartelas seguem nascendo da estrutura combinatória, agora também
informada pela ordem real. A diferença da v11.4 é de posse: quem atenua, quem
pesa e quem julga é a própria Magna
(`vetor_abertura_para_consenso()`), e o palpite sai da decisão já registrado
para ser julgado na conferência.

## 5. A SUA LÓGICA, MEDIDA SOBRE O HISTÓRICO COMPLETO (v11.3b)

Você esclareceu: o "início do sorteio" é a **menor dezena da lista ordenada**
(a primeira que os sites exibem). Exemplos seus confirmados no banco:

- ✅ 3676 = última vez que a **04** abriu o concurso;
- ✅ em seguida o **01** abriu **6× seguidas** (3677–3682);
- ✅ no **3683** o **02** assumiu;
- ✅ 01/02/03 dominam as aberturas: **60,7% / 24,6% / 9,8%** (teórico:
  60,0% / 25,0% / 9,8% — `P(menor=k) = C(25−k,14)/C(25,15)`);
- ✅ o recorde de aberturas seguidas do 01 é **17 concursos** (1750–1766).

Medido no canal `minima` do acervo (o que era `MotorPadroesMinimo`), com o banco
atualizado até o concurso **3773** (seus dados: 3771 abriu 02, 3772 e 3773
abriram 03).

### A sua pergunta: "03 saiu 2×, a chance de repetir é muito pequena?"

| Medida (histórico completo) | Resultado |
|---|---|
| P(3º 03 depois de 03+03) | **4/42 = 9,5%** — igual aos 9,8% de sempre |
| 03 abriu 3× seguidas | **4 vezes** (concursos 419–421, 1972–1974, 2361–2363, 2544–2546) |
| P(abertura repetir em geral) | 43,4% observado vs 43,3% teórico |

**Conclusão honesta:** a chance do 03 abrir o 3774 é **9,8% — a mesma de
sempre**. "Muito pequena" em termos absolutos, sim; mas não POR ter
repetido. O placar walk-forward (3.771 provas sem vazamento) mostra:

| Regra | Acerto | Teto teórico |
|---|---|---|
| Sempre prever 01 | **60,6%** | 60,0% |
| Prever {01, 02} | **85,3%** | 85,0% |
| Excluir a atual quando streak ≥ 2 (sua regra) | **51,7%** | — |

A regra de exclusão **perde 9 pontos**: quando o 01 está em sequência
(o caso mais comum), excluir o 01 força prever o 02 (25%) em vez de
manter o 01 (60%). **Streak não altera probabilidade — e o placar prova.**

O que o sistema faz hoje: prevê o próximo "início" pela margem hipergeométrica
(o melhor preditor possível, validado fora-da-amostra), publica
streaks/recorde/pergunta-resposta na seção "Acervo nativo" de `/cerebro` e
alimenta a fonte **`abertura`** do consenso da Magna com essa posterior. No
3774, a leitura do sistema é: **01 (60%) > 02 (25%) > 03 (9,8%)** — sem
excluir ninguém.

> Armadilha evitada: agregando todas as dezenas, "P(repetir | streak
> longo)" parece subir (58% após 3+). É composição, não causa — streaks
> longos são quase sempre do 01, que repete 60% por natureza. A medição
> por dezena elimina a ilusão.

## 6. Arquivos (estado v11.4)

- `core/cerebro_ia.py` — `AcervoAberturaMagna` (estatística, previsão, placar,
  auditoria) + a integração no `CerebroIA` (`assimilar_acervo`,
  `evidencia_abertura`, `acervo.proximas_aberturas`, `aprender_ordem_sorteio`,
  `conhecimento`, `calibrar_pesos_walkforward`)
- `core/magna_suprema.py` — 9º critério do Juiz (`cobertura_abertura`)
- `database/db_manager.py` — tabela `ordem_sorteio` (CHECK 1–25, upsert) e
  `magna_conhecimento` / `magna_memoria` criados pela própria Magna
- `backfill_ordem.py` — preenchimento retomável do canal `real` (opcional)
- `core/caixa_client.py` — captura de `dezenasSorteadasOrdemSorteio` com validação
- `core/data_loader.py` / ciclo autônomo — captura automática dos novos concursos
- `templates/cerebro.html` — seção “Acervo nativo”
- `tests/test_magna_acervo.py` — 27 testes do acervo e da integração
- ~~`core/padroes_ordem.py`~~, ~~`templates/ordem.html`~~,
  ~~`static/js/ordem.js`~~, ~~`tests/test_padroes_ordem.py`~~ — absorvidos
