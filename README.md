# 🧠 LotoFácil — Inteligência Magna v9.0

Sistema unificado de estudo estatístico e combinatório da Lotofácil.

A aplicação possui **uma única inteligência, uma única memória e uma única porta
de criação de cartelas**. Os antigos painéis de geração, Cartela do Dia, wheeling,
análise, singularidade e auditoria não tomam mais decisões separadas: todo o
conhecimento foi assimilado pela Inteligência Magna.

## Como a decisão funciona

```text
Histórico completo
      ↓
Síntese analítica + consenso + espectro + informação + leitura recente
      ↓
Filtros avançados + risco/EV + cobertura combinatória
      ↓
UMA decisão da Inteligência Magna
      ↓
Cartelas → conferência → aprendizado auditável → novos pesos
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

## Ordem real de sorteio (v11.3)

O sistema agora armazena e analisa a **ordem real das bolas** (1ª, 2ª, ...,
15ª) — campo oficial `dezenasSorteadasOrdemSorteio`. A lógica popular das
dezenas "do início" (repetições, sequências máximas, trio 01/02/03) foi
implementada em `core/padroes_ordem.py` e entra no consenso como fonte
`ordem` (4%), **sempre com placar walk-forward**: se a regra não superar o
acaso (4% por dezena), o veredito RUÍDO fica publicado e o vetor entra
atenuado — ver `MAGNA_ORDEM_SORTEIO.md`.

```bash
python backfill_ordem.py           # preenche o histórico (retomável, local)
```

```http
GET  /api/magna/ordem              # streaks, repetição condicional, trio,
                                   # regra de exclusão do usuário, auto-auditoria
POST /api/magna/ordem/ingestao     # {concurso, ordem: [b1..b15]}
```

## Memória e aprendizado

Cada decisão é registrada em `magna_decisoes`. Depois da conferência oficial:

1. a Magna compara o top-15 de cada fonte com o resultado real;
2. ajusta suavemente os pesos em `magna_estado`;
3. grava cada mudança em `magna_aprendizado`;
4. mantém a decisão, o resultado e os pesos vinculados pelo mesmo ID.

Não existe aprendizado oculto nem outro gerador paralelo.

Combinações que **já saíram com 15 pontos** no histórico oficial nunca são
reemitidas (a chance de o mesmo jogo sair duas vezes é desprezível). Após a
conferência, cada cartela entra em `memoria_cartelas_aprendidas`; apagar o lote
tira da tela, mas a memória de aprendizado permanece. Diagnóstico contínuo:
`GET /api/magna/aprendizado`.

## Testes e segurança

```bash
pip install pytest pip-audit bandit
pytest -q                         # 76 testes
pip-audit -r requirements.txt    # nenhuma vulnerabilidade conhecida
bandit -q -r app.py core database -x tests
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

## Áreas do sistema

- **Inteligência Magna:** análise, decisão, geração e aprendizado unificados;
- **Conferência:** compara cartelas com resultados oficiais;
- **Financeiro:** reconcilia custo, prêmio realizado e resultado líquido;
- **Histórico e Prêmios:** consulta da base oficial;
- **Avaliação:** acompanhamento dos pools usados.

O relatório técnico está em
[`AUDITORIA_TECNICA_2026-08-25.md`](AUDITORIA_TECNICA_2026-08-25.md).
