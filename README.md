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

## Memória e aprendizado

Cada decisão é registrada em `magna_decisoes`. Depois da conferência oficial:

1. a Magna compara o top-15 de cada fonte com o resultado real;
2. ajusta suavemente os pesos em `magna_estado`;
3. grava cada mudança em `magna_aprendizado`;
4. mantém a decisão, o resultado e os pesos vinculados pelo mesmo ID.

Não existe aprendizado oculto nem outro gerador paralelo.

## Testes e segurança

```bash
pip install pytest pip-audit bandit
pytest -q                         # 41 testes
pip-audit -r requirements.txt    # nenhuma vulnerabilidade conhecida
bandit -q -r app.py core database -x tests
```

A migração corrige automaticamente dezenas NumPy antigas armazenadas como BLOB,
recalcula suas conferências/finanças e reconstrói cabeçalhos de lote órfãos.

## Áreas do sistema

- **Inteligência Magna:** análise, decisão, geração e aprendizado unificados;
- **Conferência:** compara cartelas com resultados oficiais;
- **Financeiro:** reconcilia custo, prêmio realizado e resultado líquido;
- **Histórico e Prêmios:** consulta da base oficial;
- **Avaliação:** acompanhamento dos pools usados.

O relatório técnico está em
[`AUDITORIA_TECNICA_2026-08-25.md`](AUDITORIA_TECNICA_2026-08-25.md).
