# Auditoria técnica independente — LotoFácil IA

**Data:** 25/08/2026  
**Repositório:** `petrickmsilva-alt/lotofacil_system`  
**Commit-base:** `f0590499383434d210ee20dd45db6a61e7098ddb`  
**Branch auditada:** `arena/01a03a0d-lotofacil-system`  
**Escopo:** segurança, correção funcional, matemática, dados, dependências, testes, arquitetura, operação e documentação.

> Esta é uma reauditoria independente do estado atual. O arquivo `AUDITORIA.md`
> contém o histórico das fases anteriores, mas não substitui este diagnóstico.
> Nesta etapa não foram alterados algoritmos nem dados de produção; o objetivo foi
> preservar as evidências e entregar um plano de correção priorizado.

> **Nota posterior:** a Fase 7 foi implementada após esta fotografia e resolveu
> os bloqueadores de ciclo, indexação, BLOB, lotes, dependências, debug e
> persistência descritos abaixo. Consulte `AUDITORIA.md` §§24–27 e o README para
> o estado atualizado da Inteligência Magna v9.0. Os achados permanecem aqui como
> evidência e histórico de origem das correções.

---

## 1. Parecer executivo

### Veredito

**Não aprovado para exposição em rede, uso financeiro confiável ou operação autônoma.**

O núcleo combinatório de wheeling é a parte mais sólida do projeto e a suíte atual
passa integralmente. Porém, foram confirmadas falhas bloqueantes fora dessa área:

1. o servidor inicia em `0.0.0.0` com o depurador Flask habilitado e não possui
   autenticação nem proteção CSRF;
2. 50 das 66 cartelas persistidas têm dezenas em BLOB e o conversor usado na
   conferência transforma esses números em zero;
3. o ciclo autônomo chama `_aprender()` com uma quantidade errada de argumentos e
   interrompe sempre nessa etapa;
4. mesmo corrigindo a chamada, `_aprender()` compara índices 0–24 com dezenas
   1–25, aprendendo pesos a partir de acertos incorretos;
5. o estado global do Cérebro é mutado por requisições e threads concorrentes sem
   qualquer trava;
6. há oito alertas de vulnerabilidade de dependências em quatro pacotes;
7. a página de “Auditoria” é, na prática, uma fachada sem telemetria: os métodos
   de escrita do `IAMonitor` não são chamados pelo fluxo principal.

### Classificação por área

| Área | Nota | Situação |
|---|---:|---|
| Segurança de aplicação | 2/10 | Bloqueante para rede |
| Integridade de dados/financeiro | 3/10 | Bloqueante |
| Ciclo autônomo/aprendizado | 2/10 | Quebrado |
| Matemática combinatória | 8/10 | Boa, com ressalvas pontuais |
| Testes | 5/10 | Passam, mas não cobrem fluxos críticos |
| Manutenibilidade | 3/10 | Monólitos, estado global e muitas exceções cegas |
| Observabilidade/auditoria | 2/10 | Desconectada |
| Prontidão de implantação | 2/10 | Apenas laboratório local após correções P0 |

### Pontos positivos confirmados

- `37/37` testes passam em Python 3.11.
- Todo o código Python compila.
- `PRAGMA integrity_check` do SQLite retorna `ok`.
- Os 3.767 resultados formam uma série contínua de concursos 1–3767, sem dezenas
  fora de 1–25 e sem divergência entre dezenas e métricas derivadas.
- Não foram encontrados segredos versionados, `eval`, `exec`, shell injection ou
  SQL injection evidente; as consultas com entrada de usuário usam parâmetros na
  maior parte dos casos.
- Os testes do wheeling verificam construções e probabilidades exatas; cobertura
  de linhas medida: `core/wheeling.py` 88% e `core/heavyweight_engine.py` 93%.
- O próprio produto apresenta corretamente a ressalva central: um algoritmo não
  torna um sorteio independente previsível nem muda a probabilidade marginal de
  uma cartela fixa.

---

## 2. Metodologia e evidências executadas

| Verificação | Resultado |
|---|---|
| `python -m compileall` | sucesso |
| `pytest -q` | **37 passed** em ~14 s |
| `coverage` | **51%** global em 4.031 statements |
| `pip-audit -r requirements.txt` | **8 alertas em 4 pacotes** |
| `bandit` | 1 alta, 1 média e 13 baixas |
| `ruff check` | **453 ocorrências**, 97 `except Exception` |
| SQLite `integrity_check` | `ok` |
| Validação dos resultados | 3.767/3.767 concursos contínuos; métricas consistentes |
| Busca de segredos | nenhum segredo aparente encontrado |
| Inspeção de rotas | 53 rotas de aplicação, sem controle de acesso |
| Inspeção de modelos | ~138 MB no diretório `database/`, quase todos sem referência no código |

Cobertura dos fluxos mais sensíveis:

| Arquivo | Cobertura |
|---|---:|
| `app.py` | 31% |
| `core/conferencia.py` | 17% |
| `core/data_loader.py` | 20% |
| `core/financeiro.py` | 40% |
| `core/ia_monitor.py` | 34% |
| `core/singularidade.py` | 14% |
| `core/cerebro_ia.py` | 70% |
| `core/wheeling.py` | 88% |

A suíte passa, mas os arquivos menos cobertos são justamente os que fazem rede,
persistência, conferência, finanças, segurança web e auditoria.

---

## 3. Achados bloqueantes e altos

### AUD-001 — Depurador remoto + servidor em todas as interfaces

**Severidade:** Crítica quando acessível por rede  
**Evidência:** `app.py:1445`

```python
app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
```

O Bandit classificou `debug=True` como alta severidade (`B201`). O depurador
Werkzeug não deve ser usado fora de desenvolvimento e pode levar à execução de
código. O risco é agravado porque:

- não existe autenticação;
- não existe autorização por ação;
- não existe CSRF;
- endpoints apagam dados, iniciam threads, alteram pesos, atualizam o banco e
  executam cálculos de milhões de combinações;
- o bind padrão é público (`0.0.0.0`).

**Impacto:** qualquer cliente com acesso ao serviço pode modificar/apagar dados,
disparar tarefas caras e, em cenários de erro, alcançar o depurador.

**Correção P0:** usar `debug=False`, tornar host/porta configuráveis, adotar
servidor WSGI, autenticação, autorização, CSRF, limites de requisição e proxy TLS.
Para uso estritamente pessoal, o padrão deve ser `127.0.0.1`.

---

### AUD-002 — Conferência converte 50 cartelas válidas em quinze zeros

**Severidade:** Crítica para dados e financeiro  
**Evidência:** `core/conferencia.py:13-31`

A função `_safe_int()` tenta `int(blob)` e depois `int(blob.decode('utf-8'))`.
Entretanto, as dezenas antigas foram gravadas como inteiros NumPy binários, por
exemplo:

```text
b'\x01\x00\x00\x00\x00\x00\x00\x00'  -> _safe_int(...) = 0
                                                   valor real = 1
```

Estado do banco auditado:

- cartelas totais: **66**;
- cartelas com dezenas SQLite `BLOB`: **50**;
- cartelas com dezenas `INTEGER`: **16**;
- cartelas que a conversão atual torna inválidas/duplicadas: **50**.

Impacto já materializado:

| Concurso | Distribuição gravada | Distribuição real após decodificar little-endian |
|---|---|---|
| 3765 | 9 cartelas com 0; 1 com 10 | 4×8, 2×9, 4×10 |
| 3766 | 41 com 0; 2×8, 7×9, 6×10 | 13×8, 31×9, 11×10, **1×11** |

O concurso 3766 foi registrado no financeiro com prêmio R$ 0 e lucro **−R$ 196**.
Pelos próprios dados persistidos, havia uma cartela de 11 pontos; usando o prêmio
fixo de R$ 7, o valor correto seria prêmio R$ 7 e lucro **−R$ 189**.

**Correção P0:**

1. fazer backup do banco;
2. decodificar BLOBs binários com `int.from_bytes(..., byteorder='little',
   signed=True)` após distinguir bytes ASCII de bytes binários;
3. migrar `d1..d15` e bitmasks para `INTEGER` em uma transação;
4. reconferir todas as cartelas e reconstruir o financeiro;
5. adicionar teste com `np.int64` persistido como BLOB e restrições `CHECK`.

---

### AUD-003 — Ciclo autônomo quebra na chamada de aprendizado

**Severidade:** Crítica funcional  
**Evidência:** `core/cerebro_ia.py:1704` e `1795`

A assinatura aceita três argumentos posicionais após `self`:

```python
def _aprender(self, concurso, conf, dezenas_reais):
```

O ciclo envia quatro:

```python
self._aprender(concurso, conf, dezenas_reais, [])
```

Resultado inevitável: `TypeError`. Como o erro é capturado pelo `except` geral, o
ciclo apenas muda para `status="erro"`. A conferência da fila já pode ter sido
commitada antes da falha, mas o aprendizado e a geração para o próximo concurso
não acontecem: há efeito parcial sem rollback.

O teste existente (`test_ciclo_confere_concurso_certo`) inspeciona texto-fonte e
ordem de chamadas, mas nunca executa o ciclo; por isso os 37 testes passam.

**Correção P0:** corrigir a chamada e criar teste de integração com API falsa,
banco temporário e asserções sobre conferência, aprendizado, fila seguinte e
rollback em erro.

---

### AUD-004 — Aprendizado compara índices 0–24 com dezenas 1–25

**Severidade:** Alta  
**Evidência:** `core/cerebro_ia.py:1804-1815`

```python
real = set(dezenas_reais)                    # 1..25
top15 = set(np.argsort(v)[::-1][:15].tolist())  # 0..24
acertos = len(top15 & real)
```

Falta somar 1 ao ranking. Assim, mesmo depois de resolver AUD-003, os pesos dos
módulos seriam aumentados ou reduzidos com base em uma medição deslocada.

**Correção P0:** converter o ranking para 1–25 e testar casos de fronteira com as
dezenas 1 e 25.

---

### AUD-005 — Estado global não é seguro para concorrência

**Severidade:** Alta  
**Evidência:** instância global `cerebro` em `app.py:80`, threads em
`app.py:990`, `1029`, `1081` e mutações em `CerebroIA.treinar()`.

Treino, geração, backtest, loop e atualização usam a mesma instância e alteram:

- `matriz`, `raw`, `n`;
- `_motores`, `_vetores`, `_gaussiano`, `_oraculo`;
- `pesos`, `_rng_vetor`, `estado` e métricas.

`backtest_captura()` retreina temporariamente o objeto global em várias janelas e
só restaura no final, sem `try/finally`. Uma geração concorrente pode usar uma
janela histórica truncada. Uma exceção pode deixar permanentemente o Cérebro no
estado da janela de teste.

As flags `carregando` e `treinando` também são verificadas antes de serem ligadas
dentro da thread; duas requisições rápidas podem iniciar dois trabalhos.

**Correção P0/P1:** lock por operação, flag ligada antes de iniciar thread,
`try/finally`, backtests em instância isolada e fila de tarefas com estado
persistente. Não usar o servidor de desenvolvimento como executor de jobs.

---

### AUD-006 — API administrativa completamente aberta e sujeita a abuso

**Severidade:** Alta  
**Evidência:** todas as rotas de `app.py`.

Exemplos sem autenticação:

- apagar lote/cartelas;
- alterar banco com atualização externa;
- iniciar/parar o loop autônomo;
- iniciar treino/ciclo;
- persistir cartelas;
- executar exaustão dos 3.268.760 jogos;
- executar backtests e wheeling.

Também faltam limites consistentes. `n_testes` e `n_random` do backtest não têm
limite de servidor; `max_cartelas`, `limite_segundos`, orçamento e intervalo do
loop aceitam valores perigosos. Um orçamento negativo pode produzir slicing
negativo em `core/wheeling.py:364-369`, em vez de rejeição.

`GET /api/cartela_do_dia` e `GET /cartela_do_dia?fragmento=1` têm efeito de
escrita, violando a semântica segura de GET e permitindo acionamento por navegação.

**Correção P0:** autenticar, autorizar, proteger CSRF, limitar taxa e payload,
validar intervalos no servidor e mover qualquer escrita de GET para POST.

---

### AUD-007 — Dependências com vulnerabilidades conhecidas

**Severidade:** Alta  
**Ferramenta:** `pip-audit 2.10.1`

| Pacote fixado | Alertas | Correção mínima indicada pelo auditor |
|---|---|---|
| Flask 3.0.0 | `PYSEC-2026-2151` | 3.1.3 |
| requests 2.31.0 | `PYSEC-2026-1873`, `-1872`, `-2275` | 2.33.0 para cobrir todos |
| scikit-learn 1.3.2 | `PYSEC-2024-110` (reportado duas vezes) | 1.5.0 |
| lxml 4.9.3 | `PYSEC-2026-87` (reportado duas vezes) | 6.1.0 |

Além disso, `scikit-learn`, `pandas`, `beautifulsoup4`, `lxml` e `joblib` não são
importados pelo código atual. Dependências não usadas aumentam superfície de
ataque, tempo de instalação e conflitos.

**Correção P0:** remover dependências sem uso, atualizar Flask/requests, gerar
lock reproduzível e executar testes + `pip-audit` em CI.

---

### AUD-008 — Persistência de lotes não é atômica e o banco já está órfão

**Severidade:** Alta  
**Evidência:** `app.py:108-201`

O cabeçalho do lote é commitado primeiro. Cada cartela abre outra conexão e faz
outro commit. Se uma cartela falhar, o lote mantém quantidade/custo originais e o
método apenas imprime o erro.

Estado observado:

- `lotes_cartelas`: **0** linhas;
- cartelas com `lote_id` não nulo: **43**;
- IDs de lote órfãos distintos: **5**;
- cartelas sem lote: **23**.

A interface baseada em `lotes_cartelas` não consegue listar essas 43 cartelas.
Não existem FKs efetivas (`PRAGMA foreign_keys = 0`) nem exclusão em cascata.

**Correção P0/P1:** validar todas as cartelas antes da escrita e salvar cabeçalho
+ itens em uma transação. Habilitar FKs em toda conexão, adicionar relação com
`ON DELETE CASCADE`, reconciliar os cinco lotes e atualizar os endpoints de
exclusão para não criar órfãos.

---

### AUD-009 — Financeiro perde atualizações e pode inventar prêmios

**Severidade:** Alta  
**Evidência:** `app.py:1152-1187`, `core/conferencia.py:127-140`.

Problemas:

1. o hook considera um concurso já processado se existir qualquer linha em
   `financeiro`; cartelas adicionadas ou conferidas depois nunca entram no total;
2. `conferir_lote()` chama `conferir_concurso()` e confere todas as cartelas do
   concurso, não somente o lote solicitado;
3. na ausência do rateio oficial, `get_premio()` usa R$ 1.800/R$ 2.500.000 como
   se fossem valores ganhos reais para 14/15 pontos;
4. o banco auditado só possui prêmio preenchido em 102 concursos para 11–14 e em
   73 para 15; a ausência de dado é comum e não deve virar ganho estimado;
5. não há reconciliação entre `cartelas`, `financeiro` e exclusões posteriores.

**Correção P0/P1:** financeiro derivado/upsert por concurso, transação e
reconciliação; separar `premio_oficial` de `estimativa`; jamais contabilizar
estimativa como ganho realizado; conferir lote por `lote_id` ou renomear a ação.

---

### AUD-010 — “Auditoria total” não registra o fluxo principal

**Severidade:** Alta de transparência/observabilidade  
**Evidência:** `app.py` apenas instancia e lê `IAMonitor`; não chama seus métodos
de escrita.

Métodos sem integração:

- `iniciar_sessao` / `finalizar_sessao`;
- `log_modulo`;
- `log_decisao_cartela`;
- `log_aprendizado`;
- `log_previsao_vs_real`.

As tabelas `ia_sessoes`, `ia_modulos_log`, `ia_decisoes`,
`ia_evolucao_pesos` e `ia_previsao_vs_real` têm **zero registros**. A página de
auditoria apresenta uma estrutura vazia, não transparência operacional.

**Correção P1:** integrar eventos transacionais e IDs de correlação em todos os
fluxos ou remover a alegação de auditoria até a funcionalidade existir.

---

### AUD-011 — Cartela do Dia possui duas fontes de verdade inconsistentes

**Severidade:** Alta funcional  
**Evidência:** `app.py:484-531`, `1139-1141` e
`core/cerebro_ia.py:923-1071`.

A função do Cérebro grava em `cartela_do_dia`. A rota de página grava novamente a
mesma combinação em `cartelas`, para que seja conferida. Já a rota
`GET /api/cartela_do_dia` só executa a primeira parte. Se a API gerar antes da
página, a visita posterior detecta “reaproveitada” e não cria a cartela
conferível.

Estado do banco:

- `cartela_do_dia`: **24** linhas;
- conferidas nessa tabela: **0**;
- alvos duplicados: 3766 (12), 3767 (8), 3768 (4);
- no alvo 3766, as 12 linhas representam a mesma combinação;
- somente as 12 linhas do alvo 3766 têm combinação correspondente em `cartelas`.

Não há `UNIQUE(concurso_alvo)`, então o padrão SELECT-antes-de-INSERT ainda aceita
duplicata em corrida. Ao reaproveitar, o sistema recalcula votos aleatórios atuais
e os apresenta como metadados da cartela antiga, embora não sejam os votos
persistidos que originaram a decisão.

**Correção P1:** uma única tabela/fonte de verdade, `UNIQUE(concurso_alvo)`, UPSERT
atômico, geração em POST e persistência dos metadados originais sem recomputá-los.

---

### AUD-012 — O carregador pode reportar sucesso quando a gravação falhou

**Severidade:** Alta de confiabilidade  
**Evidência:** `database/db_manager.py:183-212` e
`core/data_loader.py:162-239`.

`DBManager.inserir_resultado()` captura a exceção, imprime e não retorna falha.
`DataLoader.processar_e_salvar()` então retorna `True` mesmo se o INSERT não
ocorreu. A carga histórica incrementa “carregados” indevidamente.

Na thread de carga (`app.py:976-988`) também não existe `try/finally`: uma exceção
pode deixar `carregando=True` para sempre. Mesmo quando o loader devolve
`status="erro"`, a thread marca `dados_carregados=True` e exibe “Completo”.

**Correção P1:** deixar erro de persistência propagar ou retornar resultado
explícito; usar transações, `try/finally` e status de erro real.

---

## 4. Achados médios

### AUD-013 — “14 motores independentes” não corresponde aos sinais efetivos

**Severidade:** Média/Alta de integridade do produto

No treino atual:

- `genetico` recebe uma cópia de `anti_logica`;
- `cobertura` recebe uma cópia de `freq_global`;
- `stacking` começa uniforme e seu histórico é apenas em memória;
- `chi2`, `bayes` e `kl` vêm da mesma classe estatística;
- frequência global e recente são duas saídas da mesma classe.

Medição no banco atual:

- `freq_global`, `reversao` e `cobertura`: vetores exatamente iguais;
- `anti_logica` e `genetico`: vetores exatamente iguais;
- correlação de ranking entre frequência e Markov: 0,993;
- correlação entre frequência e Verlet: 0,965;
- nos oráculos, `bayesiano` e `markov` são exatamente iguais no estado medido.

Logo, 14/15 é contagem de nomes, não de evidências independentes. Muitos motores
são transformações altamente correlacionadas do mesmo histórico.

**Recomendação:** publicar matriz de correlação/ablação, contar sinais efetivos e
remover aliases. Um módulo só deve ganhar nome próprio se produzir sinal distinto
e tiver validação fora da amostra.

---

### AUD-014 — Quórum mínimo do Oráculo não é aplicado

**Severidade:** Média de correção/transparência  
**Evidência:** `core/oraculo_convergente.py:28-30`, `433-500`.

`QUORUM_MINIMO = 10`, mas a escolha apenas ordena `votos + pesos*2` e pega o melhor
combo dentro do top-19. Não há condição exigindo dez votos.

Em uma execução auditada, as 15 dezenas selecionadas pelo ranking tinham votos:

```text
15, 14, 13, 13, 13, 12, 11, 11, 11, 10, 9, 9, 9, 8, 8
```

Cinco dezenas ficaram abaixo do suposto quórum. A frase “apenas dezenas com
consenso” e o nome `quorum_usado` (que é apenas média truncada) são enganosos.

---

### AUD-015 — Backtest não testa a estratégia realmente entregue

**Severidade:** Média

`ValidadorForaDaAmostra` avalia os 15 oráculos e a soma de seus vetores. Não
avalia o pipeline de produção dos “14 motores”, SPSA, filtro, repulsão,
exaustão-diversa, Cartela do Dia final ou wheeling com seleção de pool.

O endpoint também aceita valores não limitados de `n_testes`/`n_random`. O teste t
sobre poucas observações discretas deve ser apresentado como exploratório, não
como certificação.

**Recomendação:** backtest walk-forward do artefato final, baseline pareada com as
mesmas quantidades/orçamento, intervalos de confiança e protocolo pré-registrado.

---

### AUD-016 — Custo da cobertura C(25,15,t) é calculado com outra quantidade

**Severidade:** Média matemática  
**Evidência:** `core/singularidade.py:442-455`.

A UI mostra a cota de Schönheim como número de cartelas, mas calcula custo usando
a razão ingênua `C(25,t)/C(15,t)`, que pode ser menor que a própria cota.

Para 13 pontos:

- cartelas exibidas: **58.887**;
- base usada no custo: **49.527**;
- custo exibido: **R$ 173.343,33**;
- custo mínimo coerente com 58.887 e R$ 3,50: **R$ 206.104,50**.

A descrição “cota inferior” também não equivale a uma construção que efetivamente
garanta cobertura; é somente um limite mínimo.

---

### AUD-017 — Métrica “retorno esperado” exibe ROI líquido com nome ambíguo

**Severidade:** Média/baixa  
**Evidência:** `core/singularidade.py:547-550`.

O cálculo usa `EV líquido / custo`, resultando cerca de **−50,12%**, mas o campo se
chama `retorno_esperado_pct`. O retorno bruto é cerca de **49,88%**; o ROI líquido
é −50,12%. Ambos podem ser mostrados, com nomes explícitos.

O EV exato com as premissas do projeto foi confirmado: pagamento esperado
R$ 1,7457 por cartela de R$ 3,50 e EV líquido R$ −1,7543.

---

### AUD-018 — Banco sem restrições de domínio e unicidade

**Severidade:** Média

Não há `CHECK` para dezenas 1–25, 15 dezenas distintas, valores não negativos ou
status válidos. Faltam unicidades úteis, por exemplo:

- `financeiro(concurso)`;
- `cartela_do_dia(concurso_alvo)`;
- combinação/lote quando duplicatas não são permitidas.

`PRAGMA foreign_keys` está desligado em novas conexões. Migrações são executadas
como efeito colateral ao importar `app.py`, com vários `except: pass`, sem tabela
de versão nem rollback controlado.

---

### AUD-019 — Tratamento de erro mascara falhas e APIs respondem 200

**Severidade:** Média

O Ruff encontrou 97 capturas cegas de `Exception`; há caminhos que retornam lista
vazia, zero ou “status erro” sem log estruturado. Quase todos os erros de API
continuam com HTTP 200, dificultando clientes, alertas e observabilidade.

**Recomendação:** exceções específicas, logger estruturado, handler global e
status 4xx/5xx coerentes.

---

### AUD-020 — Repositório contém ~136 MB de artefatos de modelo sem uso

**Severidade:** Média de supply chain/manutenção

Arquivos como `dezena_models.pkl` (~85 MB), `dezena.pkl` (~21 MB), `rf*.pkl`
(~32 MB) e `gb_model.pkl` (~1,9 MB) estão versionados, mas nenhum é referenciado
pelo código atual. Além de inflar clones, pickle é um formato de execução de
código se voltar a ser carregado sem verificação.

**Recomendação:** remover do Git em mudança própria, documentar regeneração,
armazenar artefatos externamente com hash/assinatura e nunca carregar pickle não
confiável.

---

### AUD-021 — Testes não são herméticos

**Severidade:** Média

Os testes usam `database/lotofacil.db` real e instanciam singletons. Um teste de
Cartela do Dia admite inserir uma linha no banco versionado. Não há fixture de DB
temporário nem injeção completa de caminho — `CerebroIA(db_path=...)` ainda cria
`DBManager()` apontando para o caminho global.

Isso torna a suíte dependente do snapshot de 3.767 concursos e permite efeito
colateral. Testes por inspeção de código-fonte deram falso positivo para o ciclo.

**Recomendação:** fábrica de aplicação, injeção de repositório/DB, `tmp_path`, API
Caixa mockada e cobertura mínima por módulo crítico.

---

### AUD-022 — Monólitos e responsabilidades duplicadas

**Severidade:** Média de manutenibilidade

- `app.py`: 1.445 linhas e 66 funções;
- `core/cerebro_ia.py`: 1.984 linhas, 16 classes e 100 funções;
- `database/migrar.py` e `DBManager.criar_tabelas()` duplicam DDL;
- três componentes diferentes acessam a API Caixa;
- conferência, finanças e ciclo mantêm filas/tabelas parcialmente paralelas.

A duplicação explica divergências como Cartela do Dia, prêmios e lotes.

---

### AUD-023 — Empacotamento e documentação estão desatualizados

**Severidade:** Média/baixa

- `criar_executavel.bat` usa `--icon static/icon.ico`, mas o arquivo não existe;
- PyInstaller não está nas dependências instaladas pelo script;
- README diz “22 testes”, enquanto a suíte tem 37;
- interface/README mostram v7.0, enquanto `CerebroIA.get_status()` retorna
  `8.0-Disruptiva`;
- repositório público não possui licença, política de segurança, CI ou instruções
  de implantação segura.

---

## 5. Avaliação matemática e de produto

### Confirmado

A distribuição por cartela é hipergeométrica:

```text
P(X=k) = C(15,k) * C(10,15-k) / C(25,15)
```

Resultados confirmados:

| Acertos exatos | Probabilidade | Aproximadamente 1 em |
|---:|---:|---:|
| 11 | 8,7694% | 11,4 |
| 12 | 1,6704% | 59,9 |
| 13 | 0,14455% | 691,8 |
| 14 | 0,0045889% | 21.791,7 |
| 15 | 0,00003059% | 3.268.760 |

A construção de wheeling para pool 17 com oito cartelas e garantia condicional de
14 pontos passou na verificação exaustiva. A condição é essencial: a garantia só
vale se as 15 sorteadas estiverem dentro do pool.

### O que o sistema não demonstrou

- vantagem preditiva fora da amostra do pipeline final;
- independência entre os 14 motores ou 15 oráculos;
- ROI positivo;
- confiabilidade operacional suficiente para automatizar apostas/finanças.

Termos como “quântico”, “relativista”, “fractal” e “físico” descrevem
transformações determinísticas/aleatórias sem ligação demonstrada com o mecanismo
físico do sorteio. Devem ser apresentados como experimentos didáticos, não como
fontes científicas de previsão.

---

## 6. Plano de correção priorizado

### P0 — antes de qualquer uso em rede ou confiança financeira

1. Desabilitar debug, restringir bind e implantar autenticação/autorização/CSRF.
2. Fazer backup e migrar os 50 registros BLOB; reconferir cartelas e financeiro.
3. Corrigir aridade de `_aprender()` e a indexação 0/1-based.
4. Criar teste de integração real do ciclo autônomo.
5. Atualizar/remover dependências vulneráveis.
6. Bloquear concorrência no Cérebro e isolar backtests.
7. Tornar lote + cartelas uma transação única.
8. Definir limites de servidor para toda operação cara.

### P1 — confiabilidade operacional

1. Unificar Cartela do Dia e adicionar unicidade/UPSERT.
2. Reconstruir os cinco lotes órfãos e habilitar FKs.
3. Refazer financeiro como projeção reconciliável; nunca lançar prêmio estimado
   como realizado.
4. Integrar de fato o `IAMonitor` ou remover a página/alegação até a integração.
5. Corrigir propagação de erro do loader e estados de background com `finally`.
6. Usar fila de jobs, lock distribuído/local e logs estruturados.
7. Retornar códigos HTTP adequados.

### P2 — qualidade e honestidade do produto

1. Remover sinais duplicados e publicar correlação/ablação.
2. Aplicar quórum real ou renomear a métrica.
3. Backtestar exatamente a estratégia entregue, com baseline pareada.
4. Corrigir custo Schönheim e nomenclatura ROI/retorno.
5. Separar `app.py`, domínio, repositórios, jobs e clientes externos.
6. Remover modelos/dependências órfãos.
7. Criar CI com `pytest`, cobertura, Ruff, Bandit e pip-audit.
8. Atualizar README, versão, licença, política de segurança e empacotamento.

---

## 7. Critérios objetivos para uma nova aprovação

- [ ] servidor nunca inicia com debug em configuração normal;
- [ ] toda rota mutável exige autenticação e proteção CSRF;
- [ ] zero dezenas BLOB e zero lotes órfãos;
- [ ] reconferência reproduz o financeiro esperado;
- [ ] teste de ciclo executa ponta a ponta sem inspeção de texto-fonte;
- [ ] treino/aprendizado usa a mesma base 1–25;
- [ ] backtest não altera o Cérebro usado por requisições;
- [ ] zero vulnerabilidades conhecidas de severidade alta nas dependências;
- [ ] `IAMonitor` recebe eventos reais ou a funcionalidade é removida;
- [ ] Cartela do Dia tem uma única fonte de verdade e unicidade por concurso;
- [ ] persistência de lote é atômica;
- [ ] cobertura mínima de 80% em conferência, finanças, loader e APIs críticas;
- [ ] CI bloqueia regressões de segurança e qualidade.

---

## 8. Conclusão

O projeto tem valor como laboratório estatístico e combinatório, especialmente no
wheeling e na exposição das probabilidades. Contudo, a camada operacional ainda
não sustenta as promessas de autonomia, auditoria total e controle financeiro.

A prioridade não deve ser adicionar novos oráculos. Deve ser corrigir segurança,
integridade de dados, ciclo autônomo, concorrência, persistência e testes. Somente
depois disso faz sentido avaliar evolução algorítmica — sempre contra uma baseline
aleatória e sem prometer vantagem financeira não demonstrada.
