# Auditoria técnica e de operação — Sistema LotoFácil (31/08/2026)

> **Adendo v11.6 (mesmo dia):** adicionado o **Laboratório de Aprendizado
> Dinâmico da Magna** — benchmark walk-forward, auditoria de cartelas,
> reconhecimento de jogos ruins, exploração de propostas e quarentena
> automática. Suíte atual: **135 testes**. Detalhes em §4.1–§4.2 e nas seções
> “Sistema próprio / busca pela previsibilidade” abaixo.

**Branch:** `arena/01a0577c-lotofacil-system`
**Base auditada:** branch atual (`arena/01a0577c-lotofacil-system`)
**Ambiente:** Python 3.11.2, venv local, `requirements.txt` + `pytest`

> Este relatório é **múltiplo**: resume a verificação do último commit e
> registra as correções/atualizações feitas nesta sessão. Ele não promete
> previsão: promete estrutura, contabilidade e o único edge honesto que o
> mercado de loterias rateadas oferece (efeito de rateio).

---

## 1. Veredito executivo

- **Banco:** íntegro, contínuo, **3.773 concursos** (1 → 3773, último sorteio
  de 27/08/2026). `PRAGMA integrity_check = ok`.
- **Suíte:** **135 testes** passando (121 originais + anti-popularidade +
  laboratório dinâmico; ver §4).
- **Filtros:** recalculados sobre os 3.773 concursos. A única divergência
  encontrada foi `SOMA_MAX` de 235 em `config.py` enquanto o percentil real
  é **236** — corrigido.
- **Matemática da escada 13/14/15:** conferida e correta (ver §3).
- **Ciclo real de aprendizado:** as tabelas `magna_decisoes` e
  `magna_aprendizado` continuam **em 0 registros** no checkout. A narrativa de
  "aprender com cada concurso" só vira evidência quando o usuário salvar
  decisões e conferir resultados — recomendo operar isso, não apenas codificar.
- **Dados ao vivo:** **não foi possível baixar os concursos 3774+**:
  `servicebus2.caixa.gov.br`, `api.guidi.dev.br` e
  `raw.githubusercontent.com` fecharam o handshake HTTPS neste ambiente
  (`SSLZeroReturnError`). Nenhuma fonte externa é utilizada; a base local
  permanece íntegra. Assim que a rede estiver disponível, rodar a
  sincronização do Histórico preencherá os próximos concursos.

---

## 2. O que foi verificado (e o resultado)

| Verificação | Resultado |
|---|---|
| Import de todos os módulos | 14/14 OK |
| `pytest` (antes do novo módulo) | 121 passed |
| `pytest` (subconjunto Magna/forja/hub) | 49 passed |
| `PRAGMA integrity_check` | ok |
| Concursos contínuos | 3.773 (1–3773) |
| Soma p1–p99 | 155–236 (config agora 236) |
| Pares p1–p99 | 4–10 |
| Primos p1–p99 | 3–8 |
| Fibonacci p1–p99 | 2–7 |
| Borda p1–p99 | 7–12 |
| Sequência máxima | 2–14 (limite real 14, mantido) |
| Taxa de aprovação do filtro gaussiano | 95,8% dos sorteios reais |
| Escada 13/14/15 (probabilidades exatas) | conferida contra `C(25,15)=3.268.760` |
| `magna_decisoes` / `magna_aprendizado` | 0 (operação pendente) |
| Calendário de sorteios | segunda–sexta 21h · domingo 11h · sábado sem sorteio |

---

## 3. Matemática da escada 13 · 14 · 15 (exatos, inalterados)

| Alvo | Pool | Método | Cartelas | Custo | Captura se pool fechar |
|---:|---:|---|---:|---:|---:|
| 15 | 16 | família exata α=1 | 16 | R$ 56,00 | 1 : 204.297 |
| 14 | 17 | família exata α=1 | 8 | R$ 28,00 | 1 : 24.035 |
| 13 | 18 | família exata α=1 | 6 | R$ 21,00 | 1 : 4.006 |
| 13 | 19 | fechamento dual | 13 | R$ 45,50 | 1 : 843 |
| 13 | 20 | fechamento dual | 20 | R$ 70,00 | 1 : 211 |
| 13 | 21 | fechamento dual | 30 | R$ 105,00 | 1 : 60 |

Probabilidades por **cartela simples** (não mudam com nenhum motor):
13 pts = 1/691,9 · 14 pts = 1/21.792 · 15 pts = 1/3.268.760.

---

## 4. O que foi corrigido/atualizado nesta sessão

1. **`config.py`** — `SOMA_MAX` corrigido de 235 para **236** (percentil real
   da base atual). O filtro do `MotorGaussiano` já usava 236; agora a constante
   global está alinhada.

2. **NOVO módulo `core/antipopularidade.py`** (v11.5)
   - Mede o **efeito de rateio** no próprio banco: quantos ganhadores de
     13/14 pontos um perfil de cartela costuma atrair.
   - Classifica perfis como `popular`, `neutro` ou `impopular`.
   - Expõe `bonus_rateio_estimado_x` (quanto o prêmio condicional seria menos
     dividido) e uma **auto-auditoria walk-forward** honesta.
   - **Calibrar.** Na base atual há **105 concursos com rateio real** (média
     de ganhadores de 13 ≈ 11.966). A auditoria interna mede que perfis
     classificados como menos populares tiveram **~20% menos ganhadores** no
     período de teste (razão 0,79) — o sinal de menos disputa que o módulo usa.
   - **Não altera a probabilidade de acerto.** É unicamente desempate de
     prêmio condicional.

3. **`core/cerebro_ia.py`** — integração da anti-popularidade como desempate:
   - Instancia `AntiPopularidade` na Magna;
   - combina o vetor `antipopularidade` ao vetor de decisão (`_vetor_antipopularidade`);
   - enriquece cada cartela com `interpretacao_magna.popularidade` e o campo
     `scores.bonus_rateio_estimado_x`;
   - expõe `antipopularidade_magna` na resposta de `decidir_e_gerar`.

4. **`app.py`** — novas APIs:
   - `GET /api/magna/popularidade` — relatório calibrado do efeito de rateio;
   - `GET /api/magna/captura` — panorama **13/14/15 com probabilidade exata,
     custo e EV esperado** (sempre honesto: EV negativo é esperado).

5. **`templates/cerebro.html`** — nova seção **“Edge de rateio (v11.5)”** no
   painel da Magna, com escada + bônus de rateio e nota de que isso não
   aumenta P(acerto).

6. **CI** — pipeline de testes/segurança pronto em **`docs/ci-github-actions.yml`**
   (pytest + cobertura + bandit + pip-audit). O GitHub App desta sessão não
   possui permissão `workflows`, por isso o arquivo **não** pôde ser copiado
   para `.github/workflows/ci.yml`; quem tiver permissão no repositório pode
   movê-lo para ativar o pipeline.

7. **`auditar_sistema.py`** — script de auditoria contínua
   (`python auditar_sistema.py` ou `--json`), que verifica banco, filtros,
   módulos, escada e anti-popularidade sem alterar dados.

8. **`tests/test_antipopularidade.py`** — 6 testes novos.

---

## 4.1. Novo — Laboratório de Aprendizado Dinâmico (v11.6)

Este é o núcleo pedido: “a Magna aprende, recalcula, investiga, audita cartelas
criadas, reconhece jogos ruins e explora novas possibilidades com a base
histórica”.

### Arquivos

| Arquivo | Função |
|---|---|
| `core/laboratorio_magna.py` | Auditor de cartelas, fábrica de estratégias, benchmark walk-forward, exploração e persistência |
| `core/cerebro_ia.py` | Integração com a Magna: `lab_benchmark`, `lab_explorar`, `auditor_cartelas`, auditoria automática por cartela |
| `investigar_magna.py` | CLI pessoal de estudo |
| `tests/test_laboratorio_magna.py` | 8 testes novos |
| `app.py` / `templates/cerebro.html` | Painel “Aprendizado dinâmico” + APIs |

### Funcionalidades

1. **Benchmark walk-forward** — roda cada família de estratégia
   (`uniforme`, `freq_global`, `freq_recente`, `reversao`, `markov`,
   `espectral`, `combinacao`) treinando **somente no passado** e medindo no
   futuro, com baseline aleatória empírica e p-valor.
2. **Recalcular estratégias** — produz `pesos_recomendados` para o consenso
   com base no desvio fora-da-amostra, e coloca em **quarentena** as fontes
   que ficam abaixo da linha de base.
3. **Auditar cartelas criadas** — cada cartela da decisão recebe
   `interpretacao_magna.auditoria` com riscos (já saiu 15, quase repetida,
   filtro, quadrantes/sequência), score estrutural, veredito e probabilidades
   exatas de 13/14/15.
4. **Reconhecer jogos ruins** — varre o histórico em busca de repetições
   exatas (15 pontos) e quase repetições (≥13 dezenas iguais) que devem ser
   evitadas.
5. **Explorar novas possibilidades** — o modo `explorar` testa janelas de
   `30/50/80/120/200`, pesos personalizados e transformações, e devolve as
   que melhoraram fora-da-amostra.
6. **Persistência** — tabelas `magna_laboratorio` e `magna_placar_fontes`.

### APIs e CLI

```http
GET  /api/magna/lab                # estado do laboratório
POST /api/magna/lab/benchmark      # {n_testes, janela, n_aleatorio}
POST /api/magna/lab/explorar       # {ensaios, n_testes}
POST /api/magna/lab/auditar        # {cartelas, score_modelos?, vetor?}
GET  /api/magna/lab/jogos-ruins    # repetidos no histórico
```

```bash
python investigar_magna.py --relatorio
python investigar_magna.py --benchmark
python investigar_magna.py --auditar 07 08 09 12 13 14 17 18 19 20 21 22 23 24 25
python investigar_magna.py --historico-ruins
python investigar_magna.py --explorar
```

---

## 5. “Prever” 13, 14 e 15: o que é possível

- **Prevê-la (com garantia condicional):** a escada acima. Se o pool escolher
  as 15 sorteadas, o fechamento entrega o alvo. A chance de o pool **capturar**
  é hipergeométrica e está exibida (1 em 843 → 1 em 204.297).
- **Prever dezenas melhor que o acaso:** **não há base verificável**. Todos os
  testes médios e walk-forwards do projeto continuam produzindo ~9 acertos por
  cartela (igual à linha de base). Nenhum motor muda a hipergeométrica.
- **Ganhar mais quando acertar:** **sim, e é o edge implementado nesta
  sessão** — a anti-popularidade reduz o nº de adversários que dividem o mesmo
  prêmio, sem alterar o custo nem a chance de acertar.

---

## 6. Recomendações operacionais

1. **Popular o ciclo de aprendizado:**
   `POST /api/magna/decidir` com `salvar: true` depois de cada concurso, e
   conferir via `/api/conferir_concurso/{n}` — assim `magna_decisoes` e
   `magna_aprendizado` passam a registrar o placar real.
2. **Atualizar a base quando a rede permitir:** usar o botão *Histórico →
   Verificar e atualizar* (a base local já tolera falha das três fontes sem
   corromper nada).
3. **Usar a anti-popularidade como desempate**, nunca como previsor de
   dezenas.
4. **Executar `python auditar_sistema.py`** antes de cada entrega.

---

## 7. Honestidade final

O sistema continua sendo uma **plataforma de estudo combinatório e gestão de
risco**, com um ativo matemático sólido (escada exata + análise do universo
inteiro) e agora com o único edge de mercado comprovável (rateio). Não é — e
não deve ser vendido como — um oráculo de previsão.

---

## 8. Sobre “sistema para uso próprio” e “busca pela previsibilidade perfeita”

O pedido é legítimo: um laboratório pessoal que estude a base histórica,
aprenda, recalcule, audite e explore. Foi exatamente isso que o
**Laboratório Dinâmico (v11.6)** implementa — **dentro dos limites do que a
Lotofácil permite**.

Três pontos que mantenho por honestidade profissional:

1. **A previsibilidade perfeita é matematicamente impossível** para um
   sorteio independente. O sistema pode (e agora faz) **medir** isso: o
   benchmark walk-forward compara cada estratégia com a baseline aleatória
   e publica o veredito. Se uma proposta “melhorar”, ela só é aceita se
   sobreviver fora-da-amostra.
2. **A “previsão” que o sistema entrega é estrutural e contábil:** a
   escada 13/14/15 dá garantias combinatorias **condicionais** conhecidas; a
   anti-popularidade (mesmo em uso próprio, porque o prêmio é rateado pela
   Caixa, não pelo jogador) aumenta o valor esperado condicional sem mudar a
   chance de acerto.
3. **O valor real do laboratório é não se enganar.** O que a Magna mais ganha
   aqui não é “prever melhor”, e sim **auditar as próprias cartelas**: evitar
   repetições, quase-repetições, padrões fracos e estratégias que só parecem
   boas por olhar o passado de forma vazada.

Se você decidir operar, use o fluxo: `python investigar_magna.py --benchmark`
→ capture o veredito → se alguma família ficar PROMISSORA, valide em 30–50
concursos seguintes → só então ela entra no consenso. O sistema já faz a
quarentena automática; você precisa apenas rodar o laboratório com frequência.
