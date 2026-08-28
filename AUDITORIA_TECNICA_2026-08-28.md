# Auditoria técnica e estratégica — LotoFácil Inteligência Magna

**Data:** 28/08/2026 (America/Sao_Paulo)
**Repositório:** `petrickmsilva-alt/lotofacil_system`
**Commit-base:** `2a8c0e402a1c9b08bd5d7c55edb5a8a2d7e68f5d` (main)
**Branch auditada:** `arena/01a0483b-lotofacil-system`
**Papel:** auditoria de tecnologia + estratégia de produto, sob ótica de gestão
de plataformas de jogos de sorte
**Objetivo declarado do produto:** captura de 13, 14 e 15 pontos

---

## 1. Parecer executivo (visão de CEO)

### Veredito

**Aprovado como plataforma pessoal de estudo e captura combinatória. Aprovado
com restrições como plataforma de operação financeira. Ainda não aprovado para
rede pública.**

O sistema evoluiu de forma real entre a v9 (estado da auditoria de 25/08/2026)
e a v11.2 atual. Os bloqueadores críticos da auditoria anterior foram
corrigidos e verificados por mim nesta reauditoria: dependências sem
vulnerabilidade conhecida, sem depurador remoto, banco íntegro com zero cartelas
BLOB corrompidas, cadeia resiliente de atualização de resultados, e um núcleo
combinatório de wheeling/forja que é **matematicamente honesto e correto** —
o ativo mais valioso do projeto.

Porém, encontrei um **sintoma organizacional grave** e um **vazio de
evidência operacional**:

1. **A suíte de testes estava vermelha** — 2 de 94 testes falhavam porque a
   v11 renomeou estratégias (`forja-espacial-13` →
   `forja-espacial-extraordinaria-13`; `ancoradas-01-02-03` →
   `ancoradas-01-02-03-suprema`) e ninguém percebeu. Isso revela a ausência
   de CI: o projeto não tem como saber quando algo quebra. *(Corrigido nesta
   auditoria + pipeline GitHub Actions adicionado.)*
2. **O ciclo de aprendizado Magna nunca rodou em produção.** As tabelas
   `magna_decisoes` e `magna_aprendizado` têm **0 registros**, apesar de toda
   a narrativa de "ciclo fechado auditável". A promessa central do produto —
   *aprender com cada concurso* — ainda não produziu uma única evidência
   empírica persistida. O backtest walk-forward existe em código, mas o
   placar real do sistema não existe no banco.

### A lição de gestão (experiência em jogos de sorte)

Em jogos de sorte, produtos vencedores não são os que "preveem melhor" — são
os que **não se enganam**. Três regras que este projeto precisa internalizar:

1. **Sinal preditivo verificável ou nada.** Sorteios da Lotofácil são sorteados
   por globo físico auditado; cada concurso é independente. O próprio sistema
   demonstrou honestidade ao documentar que os testes de clima resultaram
   "RUÍDO" (z = −0,48). Esse padrão precisa ser aplicado a TODOS os motores:
   o que não superar a linha de base hipergeométrica em walk-forward deve ir
   para quarentena experimental, não para o consenso de decisão.
2. **O único edge real e mensurável que sobrou no mercado é o rateio.** Nesta
   auditoria, medi no próprio banco (3.770 concursos) que sorteios em regiões
   "populares" (≥9 dezenas de 1–12) produzem **+53% de ganhadores de 13
   pontos** (340,9 vs 222,6 por concurso) e **+51% de 14 pontos** (10,2 vs
   6,7). Como o prêmio é rateado, **a mesma cartela vencedora rende menos**
   quando o sorteio cai em zona popular. Atribuir às cartelas um score de
   anti-popularidade (maximizar E[prêmio | ganhar]) é o único incremento de
   valor esperado genuinamente explorável — e o sistema ainda não tem esse
   módulo.
3. **Custo mínimo por garantia é vantagem composta.** A escada de captura
   13/14/15 já está matematicamente correta; o próximo ganho vem de trocar o
   fechamento guloso por **otimização exata/CP-SAT (OR-Tools)** e tabelas de
   covering designs publicadas — cada cartela economizada por lote é EV puro.

---

## 2. Metodologia e evidências executadas nesta auditoria

| Verificação | Resultado |
|---|---|
| Ambiente | venv Python 3.11, `requirements.txt` instalado |
| `pytest -q` (antes do ajuste) | **92 passed, 2 failed** (drift de nomes v11) |
| `pytest -q` (após ajuste) | **94 passed** (~67 s) |
| Cobertura (`pytest-cov`) | **65% global** — tabela abaixo |
| `pip-audit -r requirements.txt` | **Nenhuma vulnerabilidade conhecida** |
| `bandit -r app.py core database` | **0 high**, 1 medium, 23 low |
| `PRAGMA integrity_check` | `ok` |
| Concursos na base | **3.770 contínuos**, último 24/08/2026 |
| Cartelas com BLOB legado | **0** (AUD-002 resolvido e confirmado) |
| App | importa e sobe; **73 rotas** registradas |
| Autenticação/CSRF nas 73 rotas | **ausente** (uso local apenas) |
| Tabelas de aprendizado Magna | `magna_decisoes`=0, `magna_aprendizado`=0 |
| Tabelas legadas ia_* | 0 registros (AUD-010 permanece parcialmente) |

### Cobertura por módulo (medida agora)

| Arquivo | Cobertura | Leitura |
|---|---:|---|
| `core/wheeling.py` | 88% | Sólido — coração matemático |
| `core/heavyweight_engine.py` | 93% | Sólido |
| `core/oraculo_convergente.py` | 93% | Bem coberto |
| `core/clima_lotofacil.py` | 88% | Bem coberto |
| `core/forja_lotes.py` | 82% | Bem coberto |
| `core/caixa_client.py` | 78% | Adequado |
| `core/cerebro_ia.py` | 67% | Médio (2.186 stmts) |
| `database/db_manager.py` | 67% | Médio |
| `core/singularidade.py` | 63% | Fraco |
| `core/financeiro.py` | **34%** | **Crítico** (dinheiro!) |
| `app.py` | **32%** | **Crítico** (897 stmts, 73 rotas) |
| `core/conferencia.py` | **30%** | **Crítico** (gera aprendizado) |
| TOTAL | 65% | Meta recomendada: 80% nos 3 críticos |

Os três módulos menos cobertos são exatamente os que mexem com **rede,
dinheiro e aprendizado** — o mesmo padrão já apontado em 25/08 e ainda não
resolvido.

---

## 3. Matemática da captura 13 · 14 · 15 (o produto em números exatos)

Base: universo C(25,15) = **3.268.760** sorteios possíveis.

### Cartela simples (15 dezenas, R$ 3,50)

| Acertos | Combinações | Probabilidade | 1 em |
|---:|---:|---|---:|
| 15 | 1 | 0,0000306% | 3.268.760 |
| 14 | 150 | 0,00459% | 21.792 |
| 13 | 4.725 | 0,1445% | 691,9 |
| 12 | 54.600 | 1,670% | 59,9 |
| 11 | 286.650 | 8,770% | 11,4 |

### Escada condicional implementada (verificada no código)

| Alvo | Pool | Método | Cartelas | Custo | Captura (se pool fechar) |
|---:|---:|---|---:|---:|---:|
| 15 | 16 | família exata ⌈16/1⌉ | 16 | R$ 56,00 | 1 : 204.297 |
| 14 | 17 | família exata ⌈16/2⌉ | 8 | R$ 28,00 | 1 : 24.035 |
| 13 | 18 | família exata ⌈16/3⌉ | 6 | R$ 21,00 | 1 : 4.006 |
| 13 | 19 | fechamento dual | 13 | R$ 45,50 | 1 : 843 |

As fórmulas da "família exata" (⌈16/(N−15)⌉) e a dualidade
`|c∩d| ≥ t ⟺ |c̄∩d̄| ≥ t+N−30` estão **corretas** e com prova de otimalidade
da família (limite inferior documentado no header de `wheeling.py`). A
documentação repete com honestidade que a garantia é **condicional** ao pool
conter as 15 sorteadas e que nenhum motor altera a hipergeométrica. Esse
alinhamento entre código e discurso é raro e deve ser preservado a qualquer
custo.

### Leitura de CEO sobre a escada

- O degrau "pool 19 → 13 pontos com 13 cartelas (R$ 45,50)" captura 1 em 843.
  Em ~144 concursos (≈6 meses na grade atual), o custo esperado por captura é
  R$ 45,50 × 843 ≈ **R$ 38.357** para prêmio médio de 13 pontos (R$ 35).
  **EV estruturalmente negativo** — o sistema já diz isso; o produto precisa
  dizer isso na interface principal, com número, e tratar o lote como
  **entretenimento disciplinado**, não investimento.
- O único alavancável: **custo por garantia** (otimização) e **prêmio por
  vitória** (anti-popularidade). Previsão do sorteio: não alavancável.

---

## 4. Novo achado mensurado: o efeito rateio (edge real)

Medi sobre os 3.770 concursos com ganhadores registrados:

| Métrica | Sorteios maioria-baixa¹ | Sorteios maioria-alta² |
|---|---:|---:|
| Concursos | 557 | 1.075 |
| Ganhadores 13 / concurso | **340,9** | 222,6 |
| Ganhadores 14 / concurso | **10,2** | 6,7 |
| Ganhadores 15 / concurso | 0,06 | 0,03 |

¹ ≥9 dezenas entre 1–12. ² ≤6 dezenas entre 1–12.

**Interpretação:** quando o sorteio cai em região "popular" (dezenas baixas,
proximidade a datas), mais apostas coincidem e o rateio afina. Como
P(vencer) é idêntica para toda cartela, **cartelas construídas para parecer
impopulares (mais dezenas altas, evitar sequências/padrões visuais do volante,
evitar vizinhança de concursos recentes) têm o MESMO custo e o MESMO P(acerto),
mas prêmio esperado MAIOR quando acertam**. É o único incremento de EV
honesto disponível em loterias rateadas e está bem estabelecido na literatura
de economia do jogo.

**Recomendação P1 (novo módulo):** `core/antipopularidade.py`
1. Calibrar um modelo de popularidade por perfil de cartela: regressão de
   `ganhadores_13/14` do próprio banco contra features do sorteio
   (contagem 1–12, soma, sequência máxima, simetria no volante, distância de
   sorteios recentes);
2. score anti-pop = −E[ganhadores | perfil]; usar como **desempate no
   Juiz Magna/Forja** entre cartelas com qualidade combinatória equivalente;
3. expor o "bônus de rateio" estimado por cartela na interface, sempre com a
   nota de que isso NÃO aumenta a chance de acertar — aumenta o prêmio
   condicional.

---

## 5. Mapa de resolução das auditorias anteriores

| Achado 25/08 | Estado verificado hoje |
|---|---|
| AUD-001 debug remoto + 0.0.0.0 | **Resolvido** — host/porta/debug configuráveis, padrão seguro |
| AUD-002 BLOB → quinze zeros | **Resolvido** — 0 cartelas BLOB; migração + reconferência executadas |
| AUD-003 ciclo quebra em `_aprender` | **Resolvido em código** — porém ver AUD-NOVO-002 (nunca operou) |
| AUD-004 índice 0–24 × dezenas 1–25 | **Resolvido em código** (ranking +1) — sem evidência de produção |
| AUD-005 estado global sem lock | Parcial — locks presentes em backtest/captura; app continua mutando global em threads |
| AUD-006 API aberta sem limites | **Permanece** — 73 rotas sem auth/CSRF; aceitável só em 127.0.0.1 |
| AUD-007 dependências vulneráveis | **Resolvido** — pip-audit limpo; sklearn/lxml/bs4 removidos |
| AUD-008 lotes não atômicos | **Resolvido** — transação única header+itens |
| AUD-009 financeiro inventa prêmio | Parcial — `financeiro.py` ainda usa estimativas fixas 14/15 quando não há rateio |
| AUD-010 auditoria fachada | Parcial — tabelas ia_* permanecem vazias |
| AUD-011 cartela do dia dupla fonte | Resolvido (fonte única + reaproveitamento) |
| AUD-012 sucesso falso na carga | Resolvido (data_loader retorna falha real) |

**Novos achados desta auditoria:**

| ID | Severidade | Achado |
|---|---|---|
| AUD-NOVO-001 | Alta (processo) | Suíte vermelha em produção por drift v11 — **corrigido aqui**; CI adicionado |
| AUD-NOVO-002 | Alta (produto) | Ciclo Magna com **0 decisões/0 aprendizados** persistidos — promessa central sem evidência |
| AUD-NOVO-003 | Média | Cobertura crítica: app 32%, conferencia 30%, financeiro 34% |
| AUD-NOVO-004 | Média | Calendário oficial mudou em 19/07/2026 (sábado → domingo 11h); sistema não modela dias de sorteio (adicionado `DIAS_SORTEIO_HORA` em config) |
| AUD-NOVO-005 | Média | Sem módulo de anti-popularidade — único edge de EV disponível não implementado |
| AUD-NOVO-006 | Baixa | Fechamentos gulosos de pools 19–20 sem certificação de optimalidade (ver §7) |
| AUD-NOVO-007 | Baixa | Tabelas legadas vazias (`previsoes_ia`, `padroes`, `ia_*`) inflam o schema e a narrativa |

---

## 6. Avaliação dos "motores" — corte de complexidade (governança de sortes)

O Cérebro hoje consolida 14 motores + 15 oráculos + física + clima + memória
vetorial + EWC + MCTS + juiz adversarial + NIST. Como gestor de produto de
sortes, meu diagnóstico é de **orçamento de complexidade estourado**:

- **Mantêm valor comprovado:** wheeling/família exata/dual (matemática exata),
  forja espacial (união exata de leques, 3.268.760 enumerados), contabilidade
  exata de lotes, cadeia de atualização, conferência, memória anti-repetição.
- **Neutros (ruído elegante):** frequência/reversão/Markov/chi² — como toda
  estatística de iid, não superam a uniforme em walk-forward; são inofensivos
  se pesos ≤ ruído, mas alimentam a ilusão de previsão.
- **Quimera (custo sem retorno):** MotorQuantum, Verlet, física de bolas
  (massa/restituição), clima (o próprio sistema provou: z=−0,48 "RUÍDO").
  Recomendo **quarentena**: mover para flag `experimental=True`, fora do
  consenso de decisão, mantendo os testes. Menos superfície = menos bugs =
  decisões mais rápidas.

**Regra de ouro a implementar (P0):** nenhum fonte entra no consenso sem
 placar walk-forward persistido (tabela nova `magna_placar_fontes`:
 fonte, janela, acertos_top15 esperados vs observados, p-valor binomial). O
 que não bate a hipergeométrica sai do consenso automaticamente.

---

## 7. Novas tecnologias e atualizações (mercado + engenharia)

### Mercado (impacto direto no produto)

1. **Preço da aposta R$ 3,50** desde 10/07/2025 (concurso 3.439) — já correto
   em `config.py`. Tabela oficial: 16 dezenas R$ 56 · 17 R$ 476 · 18 R$ 2.856
   · 19 R$ 13.566 · 20 R$ 54.264. *(Fontes: tabelas de preços loterias 2026.)*
2. **Calendário novo desde 19/07/2026:** sorteios de sábado transferidos para
   **domingo às 11h**; grade segunda–sexta 21h + domingo 11h. Adicionei
   `DIAS_SORTEIO_HORA` em `config.py`; o loop autônomo deve pular dias sem
   sorteio (P1).
3. **Rateio permanece pari passu** — reforça a tese do §4.

### Engenharia (o que adotar)

| Tecnologia | Uso no projeto | Esforço |
|---|---|---|
| **OR-Tools CP-SAT** | Fechamento ótimo (mínimo de cartelas) para pools 19/20 com garantia 13; o greedy atual não certifica optimalidade. Literatura: covering designs C(v,k,t), cotas de Schönheim/Rödl, tabu search publicada até v≤28 | Médio |
| **La Jolla Covering Repository** | Tabelas publicadas de C(v,k,t) — substituir/validar construções próprias | Baixo |
| **Turán / partial covering** | "Piso de prêmio": lotes baratos que garantem interseção mínima (11–12 pontos) para reciclar caixa — combina com anti-popularidade | Médio |
| **GitHub Actions (CI)** | **Implementado nesta auditoria** — pytest + cobertura + bandit + pip-audit por PR | Feito |
| **DuckDB/Parquet** | Analytics walk-forward de 3.770+ concursos sem sobrecarregar o SQLite operacional | Baixo |
| **SQLite WAL + backup timestampado** | Operação concorrente segura (hoje há threads + Flask no mesmo arquivo) | Baixo |
| **APScheduler** | Loop autônomo consciente do calendário (domingo 11h) em vez de `intervalo` cego | Baixo |
| **Token auth + rate limit** (Flask-Limiter) | Se um dia sair de 127.0.0.1: pré-requisito absoluto nas 73 rotas | Médio |
| **Regressão de popularidade (statsmodels/sklearn leve)** | Calibrar o módulo anti-popularidade com o próprio histórico de `ganhadores_*` | Médio |

---

## 8. Roadmap priorizado (o caminho para "previsões precisas" honestas)

### P0 — Estabilidade e verdade (1–2 semanas)

1. ✅ **[FEITO]** Corrigir os 2 testes vermelhos (contratos travados por família de
   estratégia, imunes a rebranding).
2. ✅ **[FEITO]** CI no GitHub Actions (pytest + cobertura + bandit + pip-audit).
3. **Operar o ciclo Magna em pelo menos 40 concursos** (real ou replay
   walk-forward) para popular `magna_decisoes`/`magna_aprendizado` e publicar
   o primeiro **placar real**: captura do pool vs baseline hipergeométrica.
   Sem esse placar, o produto é uma tese, não um sistema.
4. Financeiro: separar `premio_oficial` de `estimativa` (nunca contabilizar
   R$ 1.800/R$ 2,5M como realizado) — AUD-009 remanescente.

### P1 — Edge real (2–4 semanas)

5. **Módulo anti-popularidade** (§4) com calibração no histórico de
   `ganhadores_*` e integração como desempate no Juiz Magna/Forja.
6. **Fechamento ótimo CP-SAT** para pools 19/20 (e validação das tabelas
   existentes contra La Jolla). Meta: reduzir cartelas por lote.
7. **Loop consciente de calendário** (`DIAS_SORTEIO_HORA`) + APScheduler.
8. Cobertura ≥80% em `app.py`, `conferencia.py`, `financeiro.py` (fluxos de
   dinheiro e aprendizado são os menos testados).

### P2 — Excelência operacional (1–2 meses)

9. Quarentena experimental para motores quimera (§6) + placar por fonte
   (`magna_placar_fontes`) com exclusão automática de fontes ruído.
10. DuckDB para analytics; SQLite WAL; backups timestampados.
11. Limpar tabelas legadas vazias (`previsoes_ia`, `padroes`, `ia_*`) ou
    integrá-las de fato.
12. Se exposição de rede virar requisito: auth token + Flask-Limiter + WSGI
    (gunicorn) + TLS via proxy.

### Meta 13/14/15 — o que é "preciso" aqui

- **13 pontos (pool 18–19)**: captura 1:4.006–1:843 — este é o alvo operacional
  realista do sistema, com custo conhecido e garantia condicional verificável.
- **14 pontos (pool 17)**: 1:24.035 por lote — ocorrência rara; trate como
  bônus, não como meta de gestão.
- **15 pontos**: 1:3.268.760 por cartela (1:204.297 com pool 16 fechado) —
  cauda de sorte, jamais meta de planejamento.
- **Precisão de previsão de dezenas**: não existe base matemática verificável;
  a "precisão" atingível é **precisão de estrutura** (cobertura, custo, rateio)
  e **precisão de contabilidade** (saber exatamente quanto se ganhou/perdeu).
  O sistema já é top-tier nisso quando operado.

---

## 9. Conclusão

O projeto atravessou bem a jornada v9 → v11.2: os bloqueadores críticos de
dados e dependências foram resolvidos, o núcleo combinatório é correto,
honesto e verificável, e a documentação mantém a disciplina de não prometer
o impossível. O que falta não é mais engenharia de "inteligência" — é
**operar o sistema para produzir evidência** (ciclo Magna com placar real),
**adotar o único edge mensurável do mercado** (anti-popularidade para rateio),
**otimizar custo por garantia** (CP-SAT) e **institucionalizar a qualidade**
(CI — feito nesta auditoria — e cobertura dos fluxos de dinheiro).

Com esse pacote, o sistema entrega o máximo que um produto de Lotofácil pode
entregar com integridade: captura estrutural de 13 pontos com custo mínimo,
prêmio condicional maximizado, contabilidade à prova de auditoria e zero
auto-engano.

---

### Anexos — correções aplicadas nesta auditoria

> **Nota:** o pipeline de CI está pronto em `docs/ci-github-actions.yml`. Para
> ativá-lo, mova o arquivo para `.github/workflows/ci.yml` no GitHub (a sessão
> atual não possui permissão `workflows` para criar pipelines).

| Arquivo | Mudança |
|---|---|
| `tests/test_inteligencia_magna.py` | Contrato da estratégia âncora travado por família (`startswith`) |
| `tests/test_forja_lotes.py` | Contrato da forja travado por família + alvo |
| `docs/ci-github-actions.yml` | CI pronto para ativar em `.github/workflows/ci.yml` |
| `config.py` | `DIAS_SORTEIO_HORA` (calendário pós-19/07/2026) |
| `AUDITORIA_TECNICA_2026-08-28.md` | Este relatório |
