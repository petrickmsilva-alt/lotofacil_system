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

- **158 testes passando** (`pytest -q`) — 135 da base + 23 novos/substituídos
  (`test_inmet.py`: 16 · `test_forja_auto.py`: 6 · hub de APIs: +1).
- Cobertura nova: normalização de formatos, cliente com 3 estratégias
  (mock HTTP injetável), persistência, vetor de consenso, integração com o
  MotorClima, cascata do local do sorteio, contratos das 3 APIs.
- `python -m compileall` limpo; banco local íntegro (3.773 concursos).

## Honestidade

- Nenhum código altera a probabilidade de 13/14/15. A telemetria é evidência de
  **ambiente** (peso 0.03, teto ±10%, auto-auditoria walk-forward do clima) —
  inclina, nunca dita.
- Sem rede, a resposta é `status=neutro` — nunca um dado inventado.
- Sem `.github/` neste commit (não há pipeline; a conta não tem permissão
  `workflows` para criá-lo automaticamente).
