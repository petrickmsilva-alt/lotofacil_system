# Relatório de Alterações — 2026-08-31

**Sistema Lotofácil · Inteligência Magna v11.7**

## Resumo

Implementação da feature **"telemetria INMET por local do sorteio + forja auto + remoção das âncoras"**
na branch `arena/01a0583f-lotofacil-system` (base: `45e4826` — PR #15, já mergeado no `main`).

## O que foi feito

### 1. Telemetria INMET por local do sorteio (`core/inmet.py` — novo)

- **Local do sorteio**: o resultado oficial da Caixa traz `local` + `cidadeUF`;
  `CaixaClient.normalizar()` agora os expõe sempre (`normalizado["local"]` /
  `normalizado["cidadeUF"]`).
- **Território**: `TerritorioInmet` resolve cidade/UF → geocódigo IBGE + coordenadas
  (tabela das 27 capitais, com canonicalização de grafia e aceitação de formatos
  `São Paulo/SP`, `SAO PAULO - SP`, `Espaço da Sorte`, `GO`…).
- **Cliente** (`InmetClient`), com cascata honesta e **sem** dados fabricados:
  1. INMET oficial — estação mais próxima por geocódigo + dados diários;
  2. Open-Meteo (contingência nas mesmas coordenadas);
  3. **neutro** sem rede (valores vazios, nunca inventados).
- **Persistência** (`TelemetriaInmet`): tabela `inmet_telemetria` (criada em
  `db_manager.criar_tabelas` e em `database/migrar.py` para bases existentes),
  consultas por concurso/última/histórico + resumo para auditoria.
- **Integração Magna**: fonte `inmet` no consenso (`peso 0.03`, somatório default
  continua 1.0; novos pesos: motores 0.33 · oráculos 0.18 · espectral 0.10 ·
  informação 0.10 · recente 0.09 · física 0.08 · clima 0.05 · abertura 0.04 ·
  **inmet 0.03**) com vetor de tilt leve (±10%) e uniforme quando sem telemetria
  (fonte neutra — a Magna a ignora). `get_status()` expõe o bloco `inmet`.

### 2. Forja automática (`core/forja_auto.py` — novo)

Pipeline único em modo automático:

```
local do sorteio (Caixa → banco → padrão SP)
   → telemetria INMET (oficial → Open-Meteo → neutro)
   → condições no MotorClima da Magna (peso restrito + auto-auditoria)
   → forja suprema v11 (mesmo processo da decisão única)
   → lote + telemetria + local auditáveis
```

- `ForjaAutomatica.executar()` nunca levanta exceção por falha de rede.
- **CLI:** `python gerar_pessoal.py --auto` (e `--sem-inmet` para clima neutro).
- **APIs novas:**
  - `GET /api/magna/inmet` — estado da telemetria + local do sorteio;
  - `POST /api/magna/inmet/atualizar` — busca e persiste a telemetria do local;
  - `POST /api/magna/forja-auto` — pipeline completo com salvamento do lote.
- `auditar_sistema.py` ganhou `verificar_inmet()` (tabela, registros, fontes).

### 3. Remoção das âncoras

- `CerebroIA.decidir_ancoradas_01_02_03()` e `ancoras_do_acervo()` removidos;
- rota `POST /api/magna/ancoras-123` removida;
- flag `--ancoras` do CLI removida;
- referências em docstrings, comentários, README e docs da Magna atualizadas
  (o acervo de abertura continua: ranking/palpite/Juiz, sem o trio chumbado);
- testes de âncoras substituídos por testes da telemetria/forja automática.

## Qualidade

- **162 testes passando** (`pytest -q -W error::ResourceWarning`) — 135 da base
  + 27 novos/substituídos (`test_inmet.py`, `test_forja_auto.py`, hub de APIs).
- Cobertura nova: normalização de formatos, cliente com 3 estratégias
  (mock HTTP injetável), persistência, vetor de consenso, integração com o
  MotorClima, cascata do local do sorteio, contratos das 3 APIs.
- `python -m compileall` limpo; `ruff` (E9/F63/F7/F82/F811/F841/F401/F541/E722)
  sem pendências; **0 ResourceWarnings**; encoding UTF-8 validado (73 arquivos).
- Banco local íntegro: 3.773 concursos contínuos (auditoria em cópia).

## Auditoria pós-PR#16 — correções de codificação (2026-08-31)

Auditoria minuciosa com análise estática + suíte + smoke test real do servidor
(87 rotas, GET/POST, CLI `--auto`, API com `salvar=True`). Correções:

1. **Bug crítico (CLI/API com salvar=True):** `_registrar_decisao_magna`
   acessava `resultado["diagnostico_magna"]` incondicionalmente, mas
   `decidir_suprema` não montava essa chave → `KeyError: 'diagnostico_magna'`
   no `gerar_pessoal.py --auto --salvar` e no `POST /api/magna/forja-auto`
   com `salvar=True`. Corrigido:
   - `decidir_suprema` agora expõe `diagnostico_magna` (mesmo contrato da
     decisão única — o painel `/cerebro` lê `hurst/entropia/filtro/kelly`);
   - `_registrar_decisao_magna` usa acesso defensivo (`get()` com fallback).
   - Teste de regressão: `test_decidir_suprema_registra_sem_keyerror`.
2. **Contrato INMET no ramo neutro:** `InmetClient._neutro()` omitia a chave
   `local` (+ `n_observacoes`/`periodo`), inconsistente com os ramos
   `ok`/`contingencia` — a telemetria persistida perdia o local do sorteio.
   Corrigido + teste (`test_telemetria_neutra_sem_rede`).
3. **Painel /cerebro:** o JS da forja automática referenciava
   `id="magna-telemetria"` inexistente (o status nunca era exibido).
   Elemento adicionado + teste de regressão do painel.
4. **Contrato do orquestrador:** `persistir_telemetria` separado de `salvar`
   (cartelas) — telemetria auditável independente do lote + docs.
5. **Qualidade estática:** 9 variáveis não usadas, 22 imports não usados,
   2 `except:` genéricos, 2 f-strings sem placeholder e 3 `ResourceWarning`
   de arquivos abertos em testes — todos corrigidos.
6. Verificações estruturais: 87 rotas sem duplicação problemática, todas as
   rotas do front-end existem no app, todas as páginas respondem 200 e as
   legadas redirecionam (303/410), CLI `--auto` e `--auto --salvar` completam
   com exit 0.

## Honestidade

- Nenhum código altera a probabilidade de 13/14/15. A telemetria é evidência de
  **ambiente** (peso 0.03, teto ±10%, auto-auditoria walk-forward do clima) —
  inclina, nunca dita.
- Sem rede, a resposta é `status=neutro` — nunca um dado inventado.
- Sem `.github/` neste commit (não há pipeline; a conta não tem permissão
  `workflows` para criá-lo automaticamente).
