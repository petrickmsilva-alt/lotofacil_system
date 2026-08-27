# 🌡️ MAGNA SUPREMA v11.2 — Clima Físico do Sorteio

Evolução do sistema único pessoal: a Inteligência Magna agora **assimila as
condições do ambiente de sorteio (temperatura × pressão × umidade)** como
fonte de evidência, com os três testes matemáticos de física, auto-auditoria
walk-forward e aprendizado contínuo.

> **Princípio norteador:** correlação ≠ causa. Sorteios são processos
> aleatórios controlados. O clima entra como *física leve* (dilatação,
> arrasto, estática), com shrinkage, teto de influência e reavaliação
> contínua. A fonte **inclina** o vetor; o consenso **decide**.

---

## O que mudou

| Item | v11.0 | v11.2 |
|---|---|---|
| Fontes assimiladas | 6 (motores, oraculos, espectral, informacao, recente, fisica) | **7** (+ `clima` 6%) |
| Dados | histórico Caixa + perfis físicos | **+ 100 concursos com clima** (3200–3299) |
| Testes físicos | — | **3 testes** com z-score e veredito 95%/68% |
| Previsão do ambiente | — | **Open-Meteo (São Paulo)** + fallback média 14 |
| Auto-auditoria | — | **walk-forward 40 concursos** → fator 0.5–1.0× |
| Aprendizado | pesos por sorteio | **+ upsert contínuo de clima** por concurso |

---

## Arquivos

- `core/clima_lotofacil.py` — **MotorClima**: carga, 3 testes, vetor,
  previsão, aprendizado e auto-auditoria.
- `data/historico_clima_lotofacil.csv` — histórico de 100 concursos
  (concurso, data, temperatura, pressão, umidade, dezenas).
- `core/cerebro_ia.py` — fonte `clima` no consenso, status e aprendizado.
- `app.py` — 3 novos endpoints (abaixo).
- `gerar_pessoal.py` — flags `--temp --pressao --umidade`.
- `tests/test_clima.py` — 14 testes que travam os valores validados.

## API

```http
GET  /api/magna/clima              # previsão, top5, auto-auditoria, resumo
GET  /api/magna/clima/testes       # os 3 testes com z e vereditos
POST /api/magna/clima/ingestao     # {concurso, temperatura_c, pressao_atm,
                                   #  umidade_pct, data?, dezenas?}
```

A ingestão é **upsert por concurso** e byte-idempotente: reenviar o mesmo
registro não altera o arquivo. Com `dezenas` + `aprender: true`, o ciclo de
aprendizado da Magna fecha no mesmo concurso.

---

## Os 3 testes matemáticos — resultado REAL (validado 2×)

Valores calculados sobre o CSV entregue e **revalidados por cálculo
independente** (caminho de código separado), 2026-08-27.

### T1 — Média de Ímpares × Pressão (limiar 0.917 atm)

| Grupo | n | Média de ímpares | EP |
|---|---|---|---|
| Pressão **baixa** (<0.917) | 74 | **7.797** | 0.131 |
| Pressão **alta** (≥0.917) | 26 | **7.923** | 0.228 |

- Diferença: **−0.126** (sob pressão baixa há *menos* ímpares, não mais).
- z = **−0.48** → veredito **RUÍDO** (muito abaixo de 1.96).
- **Honestidade:** a hipótese "ar menos denso ⇔ ímpares sobem" **não se
  confirma**. A oscilação é ~0.12 ímpares — dentro do ruído de 100 concursos.
- ⚠️ O relato externo (7.66 × 7.94) tem a **direção invertida** e valores que
  **não se reproduzem** neste CSV. A direção real observada é a oposta.

### T2 — Soma das Dezenas × Faixas de Umidade

| Faixa | n | Soma média | EP |
|---|---|---|---|
| Baixa (<45%) | 23 | **192.83** | 3.20 |
| **Média (45–50%)** | 39 | **198.46** | 3.35 |
| Alta (>50%) | 38 | **192.42** | 2.88 |

- Média global: **194.87** (esperada teórica: 195.0).
- A faixa do **meio** concentra as somas maiores (+3.59 vs global).
- z da faixa destaque = **1.48** → veredito **FRONTEIRA** (68%, não 95%).
- ⚠️ O relato externo (198.71 / 194.00 / 193.88) **não corresponde** a este
  CSV: aqui a faixa que sobe é a **média (45–50%)**, não a baixa.

### T3 — Frequência Individual × Temperatura (mediana 21.35 °C)

50 concursos frios × 50 quentes. Top discrepâncias:

| Dezena | Frio | Quente | Dif | z | Veredito |
|---|---|---|---|---|---|
| **16** | 42 | 29 | +13 | **+2.86** | **SINAL 95%** |
| **22** | 23 | 37 | −14 | **−2.86** | **SINAL 95%** |
| **08** | 27 | 38 | −11 | −2.31 | SINAL 95% |
| **19** | 25 | 36 | −11 | −2.26 | SINAL 95% |
| 01 | 28 | 36 | −8 | −1.67 | FRONTEIRA |

- **16 sobe no frio; 22, 08 e 19 sobem no quente.**
- ⚠️ O relato externo citava **17 (30×21)**, **19 (frio 35×27)** e **22
  (quente 35×27)**. Sobre este CSV: **17 é plana (24×25)**; **19 tem a
  direção oposta (mais no quente)**; 22 tem direção certa (quente) mas 37×23.

> **Por que isso importa:** o motor **não confere relatos, confere dados.**
> Cada veredito vem do z-score do CSV real. O clima só move o vetor na
> direção que os dados suportam e na força que o z justifica.

---

## Como a fonte se protege (anti-sobreajuste)

1. **Shrinkage 50/50:** `vetor = 0.5×uniforme + 0.5×bruto` — o clima nunca
   dita, inclina.
2. **Teto ±10%:** nenhuma dezena sai de 10% do uniforme.
3. **Força ∝ evidência:** a inclinação é multiplicada por `min(1, |z|/1.96)` —
   teste em ruído ⇒ inclinação ≈ 0.
4. **Auto-auditoria walk-forward (40 concursos):** o vetor de clima, usando
   *só o passado*, acertou **9.125** vs **9.0** do aleatório →
   `fator_confianca = 0.5625`. A Magna aplica o vetor misturado com o
   uniforme nesse fator: **se o clima deixar de justificar, o peso cai
   sozinho**, sem intervenção.
5. **Aprendizado bayesiano por sorteio:** no pós-sorteio, o top-15 da fonte
   `clima` entra no mesmo ajuste de pesos de todas as outras fontes.

---

## Previsão do próximo sorteio

`clima_previsto()` resolve em cascata:

1. **Boletim manual** (`definir_condicoes` / `--temp --pressao --umidade`);
2. **Open-Meteo** — média dos próximos 3 dias para São Paulo
   (Espaço da Sorte, Av. Paulista), sem chave, timeout 6 s;
3. **Fallback** — mediana dos 14 registros recentes + média histórica.

Exemplo real desta build: `21.5 °C · 0.915 atm · 49.15% (média 14)` →
**top5 do clima: 22, 19, 8, 25, 23**.

Com boletim frio e seco (`--temp 19.5 --pressao 0.912 --umidade 42`), o top5
muda para **16, 2, 4, 6, 8** — exatamente o que T1/T3 preveem (16 forte no
frio, pares favorecidos sob pressão baixa).

## Cidade do sorteio (contexto da v11.1)

- Desde **2019** os sorteios da Lotofácil são fixos no **Espaço da Sorte,
  São Paulo/SP** (Av. Paulista, 750); antes, o Caminhão da Sorte era itinerante.
- Por isso o "clima do sorteio" é, na prática, **o clima de São Paulo** —
  por isso a previsão usa Open-Meteo de SP.
- A fonte de cidade tem **baixa variância** (≈100% SP) e serve mais a
  auditoria do que a predição; por isso v11.2 concentra a força no **clima
  medido**, não no nome da cidade.

## Como continuar a alimentar (autonomia)

A cada sorteio, registre o clima (uma linha):

```bash
curl -X POST http://127.0.0.1:5000/api/magna/clima/ingestao \
  -H 'Content-Type: application/json' \
  -d '{"concurso": 3300, "data": "28/08/2026",
       "temperatura_c": 20.5, "pressao_atm": 0.913, "umidade_pct": 52,
       "dezenas": "1 3 5 7 9 11 13 15 17 19 21 22 23 24 25"}'
```

O motor recalibra os 3 testes na hora e a auto-auditoria passa a ponderar a
nova amostra. **Quanto mais concursos com clima, mais as fontes de z deixam
de ser fronteira e mais a fonte ganha (ou perde) confiança — sempre pelo
número, nunca pela fé.**

## Testes

```bash
pytest tests/test_clima.py -q     # 14 testes
pytest -q                         # suíte completa (92 ok; 2 falhas pré-existentes em v11)
```
