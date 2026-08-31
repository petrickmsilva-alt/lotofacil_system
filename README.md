# 🧠 LotoFácil — Inteligência Magna v11.5

Sistema unificado de estudo estatístico e combinatório da Lotofácil.

A aplicação possui **uma única inteligência, uma única memória e uma única porta
de criação de cartelas**. Os antigos painéis de geração, Cartela do Dia, wheeling,
análise, singularidade e auditoria não tomam mais decisões separadas: todo o
conhecimento foi assimilado pela Inteligência Magna.

## Como a decisão funciona

```text
Histórico completo  →  ACERVO DA MAGNA (abertura: base inteira, memorizada)
      ↓
Síntese analítica + consenso + espectro + informação + leitura recente
      ↓
Filtros avançados + risco/EV + cobertura combinatória + juiz 9 critérios
      ↓
UMA decisão da Inteligência Magna
      ↓
Cartelas → conferência → julga o palpite → aprendizado auditável → novos pesos
```

A quantidade solicitada é apenas um limite. A estratégia é escolhida pela Magna:

- **1 cartela:** decisão única por avaliação do universo completo;
- **2–7 cartelas:** seleção integrada com diversidade;
- **8 ou mais:** fechamento de pool com garantia condicional quando aplicável.

> A garantia do wheeling é condicional: ela só vale se o pool contiver as 15
> dezenas sorteadas. Nenhuma análise altera as probabilidades hipergeométricas
> de um sorteio independente ou torna o valor esperado positivo.

## Executar

```bash
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Acesse `http://127.0.0.1:5000/cerebro`.

No primeiro boot a Magna calibra o próprio acervo (pesos das 8 fontes em
walk-forward sobre a base inteira) em segundo plano — ~90 s sem travar a
interface; depois disso o conhecimento é reaproveitado do banco e a leitura é
reassegurada antes de cada decisão. Desligue com `LOTOFACIL_ACERVO_BOOT=0`.

O servidor usa `127.0.0.1` e debug desligado por padrão. Configurações opcionais:

```bash
LOTOFACIL_HOST=127.0.0.1
LOTOFACIL_PORT=5000
LOTOFACIL_DEBUG=0
```

## API única de decisão

```http
POST /api/magna/decidir
Content-Type: application/json

{
  "quantidade": 8,
  "orcamento": 50.00,
  "salvar": true
}
```

A resposta contém a estratégia escolhida, cartelas, interpretação, contribuição
das fontes, probabilidades exatas e ID da auditoria. As rotas antigas de geração
delegam para essa mesma API ou redirecionam para `/cerebro`.

## Clima do sorteio (v11.2)

A Magna assimila as condições do ambiente (temperatura × pressão × umidade)
como fonte de evidência com shrinkage, teto ±10% e auto-auditoria
walk-forward — ver `MAGNA_SUPREMA_v11_2_CLIMA_FISICO.md`.

```http
GET  /api/magna/clima              # previsão + top5 + auto-auditoria + resumo
GET  /api/magna/clima/testes       # 3 testes físicos (z e vereditos 95%/68%)
POST /api/magna/clima/ingestao     # {concurso, temperatura_c, pressao_atm,
                                   #  umidade_pct, data?, dezenas?}
```

CLI: `python gerar_pessoal.py --qtd 8 --temp 19.5 --pressao 0.912 --umidade 42`.
O histórico fica em `data/historico_clima_lotofacil.csv` (upsert idempotente).

## Acervo de conhecimento (v11.4) — dentro da Magna, não ao lado dela

A leitura das **aberturas** (quem abre a lista ordenada e qual foi a 1ª bola
física extraída) deixou de ser um módulo ou uma página paralela. Ela é agora o
**acervo de conhecimento da própria Inteligência Magna**: `AcervoAberturaMagna`,
definido em `core/cerebro_ia.py`, montado no `__init__` da Magna e alimentado
por ela mesma.

```text
base histórica (resultados + ordem_sorteio)
        ↓  a Magna lê TUDO no boot (~0,4 s para 3.773 concursos)
acervo  →  frequências · streaks · recorde · repetição por dezena
        →  posterior do próximo início · placar walk-forward · p-valor
        ↓
fonte `abertura` do consenso (peso default 4%, atenuada pelo veredito)
        ↓
decisão · interpretação por cartela · 9º critério do Juiz · âncoras 01/02/03
        ↓
conferência → o palpite de abertura é julgado → pesos e memória reajustados
```

O que isso muda na prática:

- **nada de cold start.** Ao subir (`python app.py`), um thread de pré-carga
  manda a Magna reler a base inteira e calibrar o peso de cada fonte em
  walk-forward. A decisão do concurso **3774 já nasce com o conhecimento
  acumulado**; se a pré-carga ainda não terminou, `_garantir_acervo()` reassimila
  antes de cada decisão (custo ~0 quando a base não mudou).
- **o aprendizado é contínuo e auditável.** Cada conferência grava em
  `magna_memoria` se o palpite de abertura acertou (top1/top2/top3) e
  `magna_conhecimento` guarda o snapshot com `digest` — a decisão registra o
  digest do conhecimento que a produziu, e a auditoria compara os dois.
- **a regra popular é medida, não obedecida.** Excluir a abertura que veio 2×
  seguidas fica em 51,7% contra 60,6% de simplesmente prever a mais provável: o
  sistema publica o placar e **não** exclui ninguém.

```bash
python backfill_ordem.py                                   # 1ª bola física (opcional)
python gerar_pessoal.py --assimilar --calibrar-pesos       # reler + calibrar (CLI)
python gerar_pessoal.py --conhecimento                     # só consulta
python gerar_pessoal.py --memorizar-abertura "3774:07"     # alimenta um concurso
```

```http
GET  /api/magna/abertura               # o que a Magna sabe do próximo início
GET  /api/magna/conhecimento           # acervo completo: base, fontes, pesos,
                                       # dominios, memória recente, placar
GET  /api/magna/conhecimento?dominio=abertura
POST /api/magna/conhecimento/assimilar # {forcar, calibrar_fontes, limite_segundos}
POST /api/magna/ordem/ingestao         # {concurso, ordem:[b1..b15]} ou
                                       # {concurso, abertura:N}
GET  /api/magna/ordem                  # 410 — a URL antiga aponta o novo caminho
GET  /ordem                            # 303 → /cerebro (o painel virou seção)
```

Flags: `LOTOFACIL_ACERVO_AUTO=0` deixa o acervo em modo somente-leitura (lê e
usa, não grava nem recalibra sozinho — é o modo da suíte de testes);
`LOTOFACIL_ACERVO_BOOT=0` desliga a pré-carga do `python app.py`;
`LOTOFACIL_DB=/caminho.db` troca o banco (útil para validar numa cópia).
Painel: **`/cerebro` → seção "Acervo nativo"**. Documentação completa em
[`MAGNA_ACERVO_CONHECIMENTO.md`](MAGNA_ACERVO_CONHECIMENTO.md); a medição
estatística detalhada continua em [`MAGNA_ORDEM_SORTEIO.md`](MAGNA_ORDEM_SORTEIO.md).

## Memória e aprendizado

Cada decisão é registrada em `magna_decisoes`. Depois da conferência oficial:

1. a Magna compara o top-15 de cada fonte com o resultado real;
2. ajusta suavemente os pesos em `magna_estado`;
3. grava cada mudança em `magna_aprendizado`;
4. mantém a decisão, o resultado e os pesos vinculados pelo mesmo ID;
5. julga o que havia previsto sobre a **abertura** e reassimila o acervo
   (`magna_conhecimento` + `magna_memoria`) — a memória do concurso vira o
   conhecimento do próximo.

Não existe aprendizado oculto nem outro gerador paralelo.

Combinações que **já saíram com 15 pontos** no histórico oficial nunca são
reemitidas (a chance de o mesmo jogo sair duas vezes é desprezível). Após a
conferência, cada cartela entra em `memoria_cartelas_aprendidas`; apagar o lote
tira da tela, mas a memória de aprendizado permanece. Diagnóstico contínuo:
`GET /api/magna/aprendizado`.

## Testes e segurança

```bash
pip install pytest pip-audit bandit
pytest -q                         # 135 testes
pip-audit -r requirements.txt    # nenhuma vulnerabilidade conhecida
bandit -q -r app.py core database -x tests
python auditar_sistema.py         # auditoria contínua (sem alterar o banco)
```

A migração corrige automaticamente dezenas NumPy antigas armazenadas como BLOB,
recalcula suas conferências/finanças e reconstrói cabeçalhos de lote órfãos.

### Sincronização do histórico

O botão **Histórico → Verificar e atualizar** usa uma cadeia resiliente:

1. API da Caixa (fonte primária);
2. API de contingência brasileira;
3. snapshot JSON diário no GitHub.

Todo resultado passa por validação de concurso, data, 15 dezenas únicas e faixa
1–25. Uma fonte atrasada ou divergente nunca sobrescreve a base local. Rateios já
gravados são preservados quando a contingência fornece somente as dezenas. Cada
execução fica auditada em `historico_atualizacoes`, com fonte, concursos antes e
depois, recuperações e erros detalhados.

## Escada de captura 13 · 14 · 15 e Forja Espacial

A Magna decide agora também pelo **alvo de prêmio** (`alvo`: 13, 14 ou 15)
e pelo **modo de construção** (`modo: "forja"`):

| Alvo | Pool | Método | Cartelas | Custo | Captura (condição da garantia) |
|------|------|--------|----------|-------|-------------------------------|
| 15 | 16 | família exata | 16 | R$ 56,00 | 1 em 204.297 |
| 14 | 17 | família exata | 8 | R$ 28,00 | 1 em 24.035 |
| 13 | 18 | família exata | 6 | R$ 21,00 | 1 em 4.006 |
| 13 | 19 | fechamento dual | 13 | R$ 45,50 | 1 em 843 |

Cada degrau acima multiplica a probabilidade de captura por ~8,4× e reduz
em 1 o número de pontos garantidos. A garantia permanece condicional: vale
somente se o pool contiver as 15 dezenas sorteadas.

A **Forja Espacial** (`core/forja_lotes.py`) é o novo instrumento para
lotes livres: como o leque de alto acerto de uma cartela é minúsculo
(4.876 sorteios para 13 pontos, 151 para 14), a união EXATA de todo o
lote é otimizável por recocido simulado com pesos de plausibilidade da
Magna — em três instrumentos:

1. **Leques exatos:** `P(melhor do lote ≥ t) = |∪ R_t| / 3.268.760`, sem simulação;
2. **Fechamento dual:** a cobertura no espaço dos complementos
   (`|c∩d| ≥ t ⟺ |c̄∩d̄| ≥ t+N−30`) viabiliza garantias de 13 com pool 19/20;
3. **Geometria:** espectro de Johnson (interseções par a par) e mapa
   informacional (MDS da co-ocorrência) com constelação do lote na interface.

Honestidade mantida: a forja maximiza a estrutura do lote sob o modelo da
Magna — ganho combinatório, nunca preditivo. A probabilidade exata
não-pesada acompanha sempre o relatório.

## Edge de rateio — anti-popularidade (v11.5)

A Lotofácil é **rateada**: quando o sorteio cai em região popular do volante,
mais apostas coincidem e **o mesmo prêmio é dividido por mais gente**. Isso
não altera a chance de acertar — altera o valor esperado **quando você
acerta**. O módulo `core/antipopularidade.py` calibra o efeito sobre o
histórico oficial e usa apenas como **desempate estrutural** na decisão da
Magna.

```http
GET /api/magna/popularidade   # calibração + auto-auditoria walk-forward
GET /api/magna/captura        # escada 13/14/15 com custo, P exata e EV honesto
```

Na base atual (105 concursos com rateio), perfis classificados como menos
populares tiveram **~20% menos ganhadores de 13 pontos** no período de teste.
A interface exibe o `bonus_rateio_estimado_x` por cartela e a nota explícita:
**anti-popularidade não prevê dezenas; reduz a disputa do prêmio.**

## Laboratório de aprendizagem dinâmica (v11.6)

A Magna agora tem um **árbitro interno** para estudar a base histórica sem
mentir para si mesma:

1. **Benchmark walk-forward** — treina apenas com o passado, mede no futuro,
   compara com a baseline aleatória/hipergeométrica;
2. **Auditoria de cartelas** — detecta jogos já saídos, quase-repetidos,
   padrões fracos, e reporta a probabilidade exata de 13/14/15;
3. **Reconhecimento de jogos ruins** — varre o histórico por repetições/quase
   repetições que devem ser evitadas;
4. **Exploração de propostas** — testa janelas e combinações de fontes e
   devolve as que melhoraram fora-da-amostra;
5. **Quarentena + pesos recomendados** — estratégias que não batem o acaso
   saem do consenso automaticamente e o placar fica persistido em
   `magna_placar_fontes` / `magna_laboratorio`.

```http
GET  /api/magna/lab                # placar, quarentena, pesos
POST /api/magna/lab/benchmark      # walk-forward completo
POST /api/magna/lab/explorar       # ensaios {janela, pesos, transformacao}
POST /api/magna/lab/auditar        # {cartelas: [[...15...], ...]}
GET  /api/magna/lab/jogos-ruins    # repetidos/quase repetidos históricos
```

```bash
python investigar_magna.py --benchmark
python investigar_magna.py --auditar 07 08 09 12 13 14 17 18 19 20 21 22 23 24 25
python investigar_magna.py --historico-ruins
python investigar_magna.py --explorar
python investigar_magna.py --relatorio
```

A honestidade permanece: **nenhum método muda a probabilidade de acertar
13/14/15**. O laboratório serve para **medir, auditar e não se enganar** —
a busca por “previsibilidade perfeita” é tratada como estudo de estrutura e
gestão de risco, não como promessa de previsão.

## Melhorias de engenharia

- **CI:** pipeline de testes/segurança pronto em `docs/ci-github-actions.yml`
  (pytest + cobertura + bandit + pip-audit). Nesta conta o GitHub App não possui
  permissão `workflows`, então o arquivo deve ser copiado para
  `.github/workflows/ci.yml` por quem tenha permissão no repositório.
- **Auditoria contínua:** `python auditar_sistema.py` verifica banco,
  filtros, módulos, escada e anti-popularidade sem alterar dados.

## Áreas do sistema

- **Inteligência Magna:** análise, decisão, geração e aprendizado unificados;
- **Conferência:** compara cartelas com resultados oficiais;
- **Financeiro:** reconcilia custo, prêmio realizado e resultado líquido;
- **Histórico e Prêmios:** consulta da base oficial;
- **Avaliação:** acompanhamento dos pools usados.

O relatório técnico está em
[`AUDITORIA_TECNICA_2026-08-25.md`](AUDITORIA_TECNICA_2026-08-25.md).
