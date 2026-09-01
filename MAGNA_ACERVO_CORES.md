# 🎨 MAGNA v11.8 — Acervo de Cores das Bolas (tabela oficial MazuSoft)

**Data:** 31/08/2026 (America/São Paulo)
**Onde mora:** `core/acervo_cor.py` — classe `AcervoCorMagna`, montada em
`CerebroIA.__init__` como `self.acervo_cor` · Fonte do consenso: `cor`
**Fonte do conhecimento:** tabela oficial de cores das bolas da Lotofácil —
https://www.mazusoft.com.br/lotofacil/tabela-cor.php

---

## 1. O que a tabela oficial diz

As bolas da Lotofácil são coloridas para facilitar a identificação no sorteio.
**O que define a cor é sempre o último número de cada bola:**

| Grupo | Cor | Dezenas | Bolas por cor |
|---|---|---|---|
| 1 | Vermelha | 01, 11, 21 | 3 |
| 1 | Amarela | 02, 12, 22 | 3 |
| 1 | Verde | 03, 13, 23 | 3 |
| 1 | Marrom | 04, 14, 24 | 3 |
| 1 | Azul | 05, 15, 25 | 3 |
| 2 | Rosa | 06, 16 | 2 |
| 2 | Preta | 07, 17 | 2 |
| 2 | Cinza | 08, 18 | 2 |
| 2 | Laranja | 09, 19 | 2 |
| 2 | Branca | 10, 20 | 2 |

> **Atenção (regra da própria MazuSoft):** o Grupo 1 sempre terá mais
> ocorrências que o Grupo 2 — por isso as análises devem ser
> **proporcionais** a essa distribuição (margem hipergeométrica), nunca
> absolutas.

## 2. Por que a Magna não precisa baixar a tabela

A cor é uma função **determinística** do número (último dígito). A base
`resultados` já guarda as 15 dezenas de todos os 3.775 concursos — então a
tabela de cores por concurso é **derivada** das dezenas oficiais a cada
assimilação:

```text
resultados.d1..d15 (base oficial)
        ↓  regra MazuSoft (último dígito)
perfil de cores por concurso (10 cores × 0..3 bolas)
        ↓  aprendido no nascimento e reassimilado a cada sorteio
acervo → distribuições × margem exata · streaks da cor dominante
       → repetição da dominância · placar walk-forward · auto-auditoria
       → posterior do próximo perfil → vetor 25-dim → consenso da Magna
        ↓
decisão · interpretação por cartela · critério do Juiz (cobertura_cor)
        ↓
conferência → palpite de cores julgado → memória `cor` reajustada
```

Ou seja: **aprender, decidir, atualizar e memorizar a cada sorteio** é
exatamente o ciclo que este acervo implementa, no mesmo padrão do acervo de
abertura (v11.4) — o site entra como **fonte canônica da regra** (registrada
no código, no relatório e na API), e o dado por concurso vem da própria base.

## 3. O que o acervo mede (com honestidade da casa)

- **distribuição por cor** real × teórica exata:
  `P(k bolas da cor c) = C(n_c, k)·C(25−n_c, 15−k)/C(25,15)`
  - Grupo 1 (3 bolas): k=0 → 5,22% · k=1 → 29,35% · k=2 → 45,65% · k=3 → 19,78%
  - Grupo 2 (2 bolas): k=0 → 15,00% · k=1 → 50,00% · k=2 → 35,00%
  - P(aparecer): Grupo 1 → 94,78% · Grupo 2 → 85,00%
  - P(2+ bolas): Grupo 1 → 65,43% · Grupo 2 → 35,00%
- **cor dominante** por sorteio (a cor com mais bolas; empate desfeito pela
  ordem fixa da tabela oficial — determinístico e igual na simulação);
- **streaks** da dominância: sequência atual, recorde histórico, por cor;
- **repetição da dominância** (regra popular "repetir a cor do sorteio
  anterior") com margem teórica **por simulação** (40.000 sorteios, semente
  fixa): `Σ_c P(dom=c)²`;
- **placar walk-forward** sem vazamento (prevê t+1 só com dados < t);
- **auto-auditoria** com p-valor binomial → veredito `REAL`/`RUÍDO` →
  `fator_confianca` ∈ [0,5; 1,0];
- **posterior do próximo perfil** com shrinkage `n/(n+200)` para a margem.

## 4. Como entra na decisão

1. **fonte `cor` do consenso** — `_fontes_assimiladas_magna()` entrega o
   vetor já atenuado `(1 − fator)·uniforme + fator·posterior`, peso default
   **3%** (`_FONTES_MAGNA_DEFAULT["cor"]`), renormalizado com as outras 9
   fontes e reajustado pelo aprendizado bayesiano a cada sorteio. Sob a
   margem pura o vetor é **exatamente uniforme** (E[G1]/3 = E[G2]/2 = 0,6) —
   ele só inclina quando a base mostra desvio real de cores;
2. **interpretação de cada cartela** — `interpretacao_magna["cores"]` traz o
   perfil de cores da cartela, a cor dominante dela, a probabilidade do
   perfil sob o conhecimento e a afinidade estrutural;
3. **pontuação** — `_score_cartela()` inclui `afinidade_cores · 0,03`
   (desempate estrutural pequeno);
4. **critério do Juiz Magna** — `cobertura_cor` (peso 0,4): o lote deve
   cobrir a cor que o conhecimento aponta como mais provável de aparecer;
5. **palpite registrado** — cada decisão grava em
   `magna_decisoes.analise_json` o `memoria.palpite_cor` (ranking de cores,
   ranking de cor forte, probabilidades, `digest` do conhecimento usado)
   **antes** de existir qualquer resultado.

## 5. Aprender, atualizar e memorizar a cada sorteio

- **boot/pré-decisão:** `_garantir_acervo()` → `assimilar_acervo(auto=True)`
  reassegura o domínio `cor` no mesmo ciclo do domínio `abertura` (custo ~0
  quando a base não mudou; relê e repersiste quando o carimbo avançou);
- **conferência:** `_aprender_resultado_magna_sem_lock` julga o palpite de
  cores (`dominio='cor'`, evento `palpite`), aprende o concurso real em
  `acervo_cor.aprender` + `_cores_vivas` e grava o evento `aprendido` no
  mesmo commit;
- **memória:** domínio `cor` em `magna_conhecimento` (snapshot com digest) e
  diário em `magna_memoria`; o placar do que a Magna previu fica em
  `placar_cor_memoria()`.

## 6. API

```http
GET  /api/magna/cor                    # evidência completa (ranking, placar,
                                       # auto-auditoria, palpite, leitura)
GET  /api/magna/cor/tabela?desde=&ate=&limite=30   # tabela de cores por
                                       # concurso (fonte MazuSoft + data)
GET  /api/magna/conhecimento?dominio=cor           # snapshot memorizado
GET  /api/magna/conhecimento           # inclui `cor`, `placar_cor`,
                                       # `cor_relatorio`
```

CLI: `python gerar_pessoal.py --assimilar` rele a base inteira (abertura +
cores) e `--conhecimento` consulta.

## 7. Honestidade

Nenhum padrão de cor muda a probabilidade hipergeométrica de uma cartela.
O acervo **mede** a estrutura real de cores, **memoriza** com carimbo
auditável, **publica** o placar walk-forward fora-da-amostra e **atenua** a
própria influência quando o placar não supera a margem — a mesma disciplina
das fontes de abertura, clima e INMET. O teste
`tests/test_acervo_cor.py` prova com série sintética que, sob aleatoriedade,
o veredito é `RUÍDO` e o fator fica em 0,5 (vetor atenuado).
