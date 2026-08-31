# 🧠 MAGNA v11.4 — Acervo de Conhecimento (órgão da própria Magna)

**Data:** 28/08/2026 (America/São Paulo)
**Onde mora:** `core/cerebro_ia.py` — classe `AcervoAberturaMagna`, montada em
`CerebroIA.__init__` como `self.acervo` · Fonte do consenso: `abertura`
**Não é módulo paralelo.** Não existe `core/padroes_ordem.py` nem página
`/ordem`: a leitura de abertura é memória, julgamento e peso dentro da
Inteligência Magna — ela aprende, memoriza, decide, julga e se confere sozinha.

---

## 1. Por que isso existe

A v11.3 entregou a leitura de abertura como **módulo novo com painel próprio**.
Isso era exatamente o que não devia ser: a Magna é uma só — ela decide, julga,
aprende, cria, molda, interpreta, analisa e memoriza. A v11.4 absorve essa
capacidade:

| Antes (v11.3) | Agora (v11.4) |
|---|---|
| `core/padroes_ordem.py` (motor separado) | `AcervoAberturaMagna` dentro de `core/cerebro_ia.py` |
| `magna.ordem_motor` / `magna.minimo_motor` | `magna.acervo` (um órgão, dois canais) |
| fonte `ordem` no consenso | fonte `abertura` no consenso |
| página `/ordem` + `ordem.js` | seção **"Acervo nativo"** em `/cerebro` |
| `GET /api/magna/ordem` | `GET /api/magna/abertura` + `GET /api/magna/conhecimento` |
| backfill como pré-requisito do aprendizado | a base histórica inteira (`resultados`) já basta |

**Concurso 3774 em diante não há cold start:** o conhecimento é lido da base no
nascimento da Magna (`__init__`, ~0,4 s para 3.773 concursos), reassimilado antes
de **cada** decisão (`_garantir_acervo`) e calibrado de ponta a ponta na pré-carga
do `python app.py`.

## 2. O que o acervo sabe (dois canais, um órgão)

| Canal | O que é | Base |
|---|---|---|
| `minima` | a **menor dezena** do sorteio — a que abre a lista ordenada | `resultados.d1` (todos os concursos) |
| `real` | a **1ª bola fisicamente extraída** | `ordem_sorteio` (o que o backfill/sync capturaram) |

Por canal, medido na base inteira:

- **frequências** reais × teórica — `P(menor = k) = C(25−k,14)/C(25,15)`, ou
  seja **01 → 60,0%**, 02 → 25,0%, 03 → 9,8%, 04 → 3,6%, 05+ → 1,6%;
- **streaks**: sequência atual, recorde histórico, distribuição de comprimentos;
- **repetição por dezena** (`repeticao_apos_streak`) — nunca agregada: agregar é
  a armadilha que faz "P(repetir | streak longo)" parecer 58% quando é só o 01
  repetindo os 60% de sempre;
- **taxa de repetição** global e condicional (após 1, 2 e 3+);
- **matriz de transição** P(abre j | abriu i) e **posterior do próximo início**
  (contagens suavizadas, misturadas à margem com peso `n/(n+200)`);
- **placar walk-forward** sem vazamento: para cada concurso *t*, prevê *t+1* só
  com o que existia antes de *t*;
- **auto-auditoria**: lift sobre a margem + p-valor binomial → veredito
  `REAL`/`RUÍDO` → `fator_confianca` ∈ [0,5; 1,0].

## 3. Como esse conhecimento entra na criação das cartelas

O acervo não gera cartela nenhuma. Ele **participa do mesmo processo** que gera:

1. **fonte `abertura` do consenso** — `_fontes_assimiladas_magna()` entrega o
   vetor da abertura já atenuado:
   `(1 − fator) · uniforme + fator · posterior`, com peso default **4%**
   (`_FONTES_MAGNA_DEFAULT["abertura"]`), renormalizado com as outras 7 fontes e
   reajustado pelo aprendizado bayesiano a cada sorteio;
2. **interpretação de cada cartela** — `interpretacao_magna["abertura"]` traz a
   abertura da própria cartela, a probabilidade dela no conhecimento, a
   afinidade e se cobre o palpite da Magna;
3. **pontuação** — `_score_cartela()` inclui `afinidade_abertura · 0,05`: peso de
   coerência estrutural (desempate), pequeno por construção;
4. **nono critério do Juiz Magna** — `cobertura_abertura`: o lote é julgado pela
   massa de abertura que cobre. Uma cartela só pode abrir de um jeito, então o
   critério nunca vira cota para lote pequeno: ou alguma cartela abre pela dezena
   mais provável do conhecimento, ou (lote ≥ 3) a união das aberturas cobre
   ≥ 85% da massa;
5. **fonte INMET (v11.7)** — a telemetria por local do sorteio entrou como
   fonte leve do consenso (`peso 0.03`), pré-alimentada pela forja automática;
   **âncoras 01/02/03 foram removidas** nesta versão;
6. **palpite registrado** — cada decisão grava em `magna_decisoes.analise_json`
   o `memoria.palpite_abertura` (ranking + probabilidades + `digest` do
   conhecimento usado) antes de existir qualquer resultado.

## 4. Memória: onde o conhecimento fica gravado

| Tabela | Papel |
|---|---|
| `magna_conhecimento` | snapshot por domínio (`base`, `abertura`, `fontes`, `memoria`) com `versao`, `concurso_ate`, `n_provas`, `veredito`, `fator_confianca`, `origem` (`fundante`/`incremental`/`online`) e `snapshot_json` |
| `magna_memoria` | trilha de eventos: `assimilado` (leitura da base), `calibrado` (pesos em walk-forward), `aprendido` (abertura real de um concurso), `palpite` (o palpite julgado na conferência) |
| `magna_estado` | `pesos_fontes` (com migração automática da chave antiga `ordem` → `abertura`) |
| `magna_decisoes` / `magna_aprendizado` | decisão + ajuste de peso por fonte, vinculados por ID |

O **`digest`** (SHA256 truncado das séries memorizadas) é a impressão digital do
conhecimento: a decisão registra qual digest a produziu, e a auditoria compara o
digest da decisão com o vigente — se divergem, a decisão foi tomada com memória
velha.

### Reaprendizado

- **a cada sorteio** (ciclo `executar_ciclo` / `ciclo_pos_sorteio_caixa`):
  treino → aprendizado dos pesos → `aprender_ordem_sorteio` (se a Caixa trouxe a
  ordem real) → `_garantir_acervo` → plano;
- **na conferência** (`aprender_resultado_magna`): o `palpite_abertura` de cada
  decisão do concurso é julgado (top1/top2/top3), a abertura real entra na série
  viva, o conhecimento é repersistido e o evento vai para `magna_memoria`;
- **sob pedido**: `POST /api/magna/conhecimento/assimilar`, CLI `--assimilar`,
  botão da UI, ou `magna.assimilar_acervo(forcar=True, calibrar_fontes=True)`.

`_garantir_acervo()` é barato quando o carimbo bate (`max(base, acervo)`); quando
a base cresceu, relê tudo. Com `LOTOFACIL_ACERVO_AUTO=0` ele fica em modo
**somente-leitura**: usa o conhecimento, não grava nem recalibra por conta própria
(é o modo da suíte de testes).

## 5. Calibração fundante dos pesos (a parte cara, uma vez só)

`calibrar_pesos_walkforward(limite_segundos=…)` percorre a base em checkpoints,
treina a Magna **só com o prefixo** de cada um, mede quantas das 15 dezenas do
top-15 de cada fonte caíram no sorteio seguinte e entrega o resultado ao
`AprendizadoBayesianoMagno` — o mesmo instrumento que aprende online, com prior
Dirichlet já calibrado para o número de provas. Resultado: peso por fonte,
medido fora-da-amostra, com orçamento de tempo (quando o orçamento corta, o
snapshot é marcado como **parcial** — nada é fingido como completo).

Medido na base atual (3.773 concursos, 31–35 passos):

```text
motores 0.371 · oraculos 0.190 · espectral 0.113 · informacao 0.085
recente 0.102 · fisica 0.075  · clima 0.052  · abertura  0.013
```

A fonte `abertura` **cai** abaixo do default porque o medidor fez o trabalho
dele: no canal que ela enxerga (a menor dezena), o top-15 dela não supera a
margem. Ela continua no consenso, com peso menor e veredito publicado.

## 6. Interface

```http
GET  /api/magna/abertura                    # evidência do próximo início (leitura,
                                            # ranking, probabilidades, placar, digest)
GET  /api/magna/conhecimento                # acervo completo + dominios + memória
GET  /api/magna/conhecimento?dominio=abertura
POST /api/magna/conhecimento/assimilar     # {forcar, calibrar_fontes, limite_segundos}
POST /api/magna/ordem/ingestao             # {concurso, ordem:[15 bolas]} |
                                            # {concurso, abertura:N}
GET  /api/magna/ordem                       # 410 — aponta o caminho novo
GET  /ordem                                 # 303 — /cerebro
```

CLI:

```bash
python gerar_pessoal.py --assimilar --calibrar-pesos --limite-calibracao 90
python gerar_pessoal.py --conhecimento
python gerar_pessoal.py --memorizar-abertura "3774:07"
python gerar_pessoal.py --memorizar-abertura "3774:07 01 22 03 14 05 19 11 02 25 08 13 17 04 10"
python backfill_ordem.py                    # opcional: enche o canal `real`
```

Python:

```python
magna = InteligenciaMagna()                 # já nasce com o acervo lido
magna.assimilar_acervo(forcar=True, calibrar_fontes=True)
magna.evidencia_abertura()                  # o que entra na decisão e no Juiz
magna.acervo.proximas_aberturas(3)         # top 3 aberturas da base
magna.conhecimento(detalhes=True)            # inventário + memória + pesos
magna.placar_abertura_memoria()              # palpite × conferência
magna.diagnostico_aprendizado()              # o que ela aprendeu, sem retoque
```

Flags: `LOTOFACIL_ACERVO_AUTO` (`0` = somente-leitura),
`LOTOFACIL_ACERVO_BOOT` (`0` = não calibrar na pré-carga),
`LOTOFACIL_DB` (outro arquivo .db — valide numa cópia antes de mexer na base real).

## 7. Honestidade (continua valendo)

- A abertura é enviesada **por construção combinatória**, não por previsão: saber
  que 01 abre 60% não muda em nada a probabilidade hipergeométrica de qualquer
  cartela (`1/3.268.760` para a quadra cheia, `≈1/692` para 13 pontos).
- O placar walk-forward sobre 3.771 provas sem vazamento diz: prever sempre a
  abertura nº 1 do ranking → **60,6%** (teto 60,0%); cobrir as duas primeiras →
  **85,3%** (teto 85,0%); excluir a abertura em sequência (a regra popular) →
  **51,7%** — perde 8,9 pontos porcentuais. **Streak não muda probabilidade.**
- Veredito atual: `RUÍDO` (lift ≈ 1,01, p ≈ 0,43) → vetor atenuado por 0,5.
- Dezenas baixas são as mais jogadas pela multidão: cartelas que abrem em
  01/02/03 tendem a **piorar o rateio** quando há prêmio. A afinidade de abertura
  é critério de coerência, não de ganho; o desempate anti-popularidade continua
  sendo trabalho do Juiz e da Forja.
- Nada aqui altera as garantias do fechamento, que continuam condicionais: só
  valem se o pool contiver as 15 dezenas sorteadas.

## 8. Testes

`tests/test_magna_acervo.py` (27) cobre: margem exata, validação da ordem,
idempotência do aprendizado, streaks, repetição por dezena, posterior,
walk-forward sem vazamento, veredito `REAL` em série com sinal e `RUÍDO` sob
independência, digest, `afinidade_cartela`, `avaliar_palpite`, os 8 nomes de
fonte do consenso, persistência em `magna_conhecimento`/`magna_memoria`,
presença do acervo na decisão única/suprema/forja-auto, julgamento do palpite na
conferência, ingestão da ordem real e a migração dos pesos gravados com a chave
antiga `ordem`. `tests/conftest.py` roda tudo em modo somente-leitura.

```bash
/home/user/.venv/bin/python -m pytest -q     # 118 passed
```
