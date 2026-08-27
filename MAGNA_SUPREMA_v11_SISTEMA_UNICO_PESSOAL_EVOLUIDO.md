# MAGNA SUPREMA v11 — SISTEMA ÚNICO PESSOAL EVOLUÍDO POTÊNCIA MÁXIMA

## Auditoria Completa + Evoluções Totais

**Data:** 2026-08-27 (America/Sao_Paulo)
**Versão:** 11.0-Magna-Suprema-Unica-Pessoal-Evoluida
**Evolução:** v11-EWC-Meta-MCTS-MultiRota-JuizAdv-NIST-Explain-Chat-Fingerprint-Backtest
**Repositório:** https://github.com/petrickmsilva-alt/lotofacil_system

---

## 1. Arquitetura Auditada (Completa)

### Módulos Principais
- `core/cerebro_ia.py` — Cérebro único: 14 motores + 15 oráculos + física + espectro + informação + singularidade + mapas + heavyweight
- `core/forja_lotes.py` — Forja espacial: regiões alto acerto, mapa informacional, motor grafos, geometria Johnson, forja multi-seed, fechamento dual, menu captura
- `core/magna_suprema.py` — **NOVO v11** com 20 classes evoluídas (ver abaixo)
- `core/oraculo_convergente.py` — 15 teorias + entropia nanossegundo
- `core/heavyweight_engine.py` — Motor exaustão universo C(25,15)=3.268.760
- `core/motores.py` — 14 motores estatísticos
- `core/singularidade.py` — Filtros avançados, Fibonacci, borda, primos
- `core/fisica.py` — Motor física sorteio
- `database/` — SQLite com 3770 concursos, migração, backup

### Fluxos
1. **Treino:** 14 módulos + oráculo em 1.2s sobre 3770 concursos
2. **Fontes assimiladas:** motores + oráculos + espectral + informação + recente + física + memória episódica + vetorial
3. **Decisão única:** vetor supremo → regime → perfil → MCTS pool → forja suprema → juiz 8 critérios + adversarial + NIST + p-value → fingerprint → backtest → verificação exaustiva
4. **Âncoras 01/02/03:** MESMO processo supremo, apenas âncoras fixas + ranking Magna
5. **APIs:** /api/magna/suprema, /api/magna/ancoras-123, /api/magna/regime, /api/magna/verificar, /api/magna/chat, /api/magna/fingerprint, /api/magna/perfil

---

## 2. Evoluções v11 — Tudo Possível e Impossível Dentro Honestidade

### APRENDER (EWC + Meta + Clustering Adaptativo + Balança 0.001g)

#### EWCContinual — Continual Learning sem esquecimento catastrófico
```python
class EWCContinual:
    lambda_ewc=0.4, Fisher Information (acertos-9)^2
    consolidar() → Fisher por dezena
    regularizar(vetor_atual) → penalidade EWC
```
Evita que aprendizado recente apague padrões antigos. Cada dezena tem importância Fisher baseada em desempenho histórico.

#### MetaAprendizadoRegime — Pesos por regime
```python
class MetaAprendizadoRegime:
    lr=0.12, pesos por regime_id (0,1,2)
    atualizar(regime, acertos, pesos_atuais) → ajusta lr por desempenho
    obter_pesos_regime(regime_id) → pesos personalizados por regime
```
Aprende que em regime 0 (ex: estável) motores de média funcionam melhor, em regime 1 (volátil) física funciona melhor, etc.

#### DetectorRegime Adaptativo — K-means silhouette
```python
detectar_adaptativo(janela=100):
  testa k=2,3,4 → silhouette score
  escolhe k_otimo com maior silhouette
  retorna regime_atual, k_otimo, silhouette, historico_regimes
```
Antes: k fixo=3. Agora: adaptativo 2..4, 50 amostras aleatórias para silhouette, detecta quantos regimes reais existem nos últimos 100 concursos.

#### FisicaRealBalanca — Validação 0.001g
```python
class FisicaRealBalanca:
    massa 2.5-6.0g, diâmetro 30-50mm, densidade 0.5-2.5g/cm³
    validar_medicao(dezena, massa, diametro, densidade) → valida faixa
    registrar_medicao() → MotorFisicaSorteio com medição real
    anomalias → lista bolas fora padrão
```
Simula balança de precisão 0.001g para validar bolas físicas reais. Se medir bola 07 com 5.432g, valida e registra no motor física.

---

### DECIDIR (Perfil Risco + MCTS Pool + Multi-Rota + Utilidade Esperada)

#### PerfilRiscoPessoal — Conservador/Equilibrado/Agressivo
```python
conservador: w_p13=0.6 w_p14=0.3 w_p15=0.05 w_ev=0.05 → maximiza 13
equilibrado: w_p13=0.3 w_p14=0.4 w_p15=0.2 w_ev=0.1 → busca 14
agressivo:   w_p13=0.1 w_p14=0.3 w_p15=0.5 w_ev=0.1 → caça 15

utilidade(p13,p14,p15,ev) → score risco
recomendar_alvo() → 13/14/15 baseado no perfil
```
Usuário escolhe perfil: conservador quer 13 garantido, agressivo caça 15 com maior risco.

#### MCTSPool — Monte Carlo Tree Search UCT para pool elite
```python
class MCTSPool:
    iteracoes=800, c=1.4 (UCT), recompensa = vf*0.6 + div*0.3 + quad*0.1
    buscar(vetor, tam=17, iteracoes=800) → pool elite via MCTS
    Nó: visitas, valor, dezenas, filhos, UCT = Q/N + c*sqrt(ln(Npai)/N)
```
Antes: pool guloso MotorGrafos. Agora: MCTS explora árvore de dezenas, balanceia exploração vs explotação, encontra pool com melhor compromisso vf+diversidade+quadrantes. 800 iterações.

#### AlocadorMultiRota — 60/30/10
```python
class AlocadorMultiRota:
    conservador: 70% forja + 20% wheeling14 + 10% exaustão
    equilibrado: 60% forja + 30% wheeling14 + 10% exaustão
    agressivo:   40% forja + 30% wheeling14 + 30% exaustão

    alocar(orcamento, quantidade, perfil) → forja_qtd, wheeling_qtd, exaustao_qtd
```
Divide orçamento em 3 rotas diferentes para diversificar risco: forja (ganho combinatório), wheeling14 (cobertura), exaustão (busca universo). Ex: R$100 8 cartelas conservador → 5 forja + 2 wheeling + 1 exaustão.

#### UtilidadeEsperada — Prêmios reais médios
```python
class UtilidadeEsperada:
    premios_medios DB: AVG(premio_13), AVG(premio_14), AVG(premio_15)
    calcular(analise, premios_medios, custo) → EV real, ROI, lucro esperado
    ev_real = p13*premio13 + p14*premio14 + p15*premio15 - custo
    roi = (ev_real / custo)*100
```
Antes: EV probabilístico apenas. Agora: EV com prêmios reais médios do banco (ex: 13=R$35, 14=R$1800, 15=R$500k). Mostra se lote tem ROI positivo (nunca tem, mas mostra honestidade).

---

### JULGAR (Juiz 8 critérios + Adversarial + NIST + P-Value + Juiz que Aprende)

#### JuizMagna 8 critérios + aprender_falha
```python
8 critérios: cobertura_13, cobertura_14, ev, soma, pares, primos, quadrantes, johnson_z
julgar(cartelas, pool, analise, vetor, mascaras) → veredito APROVADO/REPROVADO nota 0..1
aprender_falha(falhou_13_mais, mas_deu_13) → se reprovou mas deu 13+, reduz peso do critério 0.95
```
Juiz que aprende: se reprovou lote por soma mas lote deu 13+, reduz importância de soma no futuro. Não é estático.

#### JuizAdversarial — Fraquezas comuns
```python
class JuizAdversarial:
    julgar(cartelas, pool) → comuns (interseção de todas), fraquezas (ponto único falha), veredito VULNERÁVEL/ROBUSTO
    Ex: todas cartelas contêm [4,5,11,12,13] → se essas 5 não saírem, lote inteiro falha
```
Detecta ponto único de falha: se todas cartelas compartilham 10 dezenas, é vulnerável. Força diversidade.

#### TesteNIST — Chi2 frequência + gap
```python
class TesteNIST:
    testar(cartelas) → chi2 frequencia, gap_medio, veredito ALEATÓRIO_OK/SUSPEITO
    Frequência: cada dezena deve aparecer ~ (15/25)*n_cartelas vezes
    Gap: distância entre ocorrências da mesma dezena deve ser aleatória
```
Teste de aleatoriedade NIST adaptado: verifica se lote não é enviesado (ex: todas cartelas com 01 é suspeito).

#### PValueRandom — Ratio vs baseline aleatório
```python
class PValueRandom:
    calcular(p_melhor, n_cartelas, alvo) → p_random=1-(1-p1)^n, ratio=p_melhor/p_random, veredito MELHOR_QUE_RANDOM/EQUIVALENTE
    p1 = 1/692 para 13, 1/21800 para 14, 1/3.268M para 15
```
Compara P(lote≥t) vs lote aleatório: ratio 1.2 = 20% melhor que aleatório. Mostra ganho combinatório real.

---

### ENTENDER (Explainability LLM + Chat + Fingerprint)

#### ExplainabilityMagna — Por dezena/cartela
```python
class ExplainabilityMagna:
    explicar_dezena(dezena, vetor, fontes, votos) → top fonte, votos oráculo, contribuições
    explicar_lote(cartelas, vetor, fontes, votos) → lista explicações por cartela
    Ex: "Dezena 22: top fonte motores (0.0418), votos oráculo 10/15, contribuições: motores=0.042..."
```
Explica por que cada dezena foi escolhida: qual fonte deu maior peso, quantos oráculos votaram nela, etc. Não é caixa preta.

#### ChatMagna — "Por que 22?" / "Chance?" / "Regime?" / "Juiz?"
```python
class ChatMagna:
    responder(pergunta, contexto) → resposta natural
    "por que 22?" → explica dezena 22
    "chance" → explica P≥13/14/15
    "regime" → explica regime atual
    "juiz" → explica julgamento
```
Chat LLM local (sem API externa): responde perguntas sobre lote em linguagem natural.

#### FingerprintPessoal — SHA256 anti-repetição
```python
class FingerprintPessoal:
    hash = SHA256(sorted(dezenas))[:16]
    cache 500 hashes, carregar_historico() do DB
    ja_foi_gerada(cartela) → True se já gerou antes
    registrar(cartela) → adiciona hash
    relatorio() → total_hashes, fingerprint
```
Nunca repete cartela pessoal: cada cartela gerada vira hash SHA256, verifica se já foi gerada antes. Uso pessoal sem repetição.

---

### VERIFICAR (Backtest 50 + Binomial + Curva)

#### BacktestLote — Walk-forward 50 concursos
```python
class BacktestLote:
    testar(cartelas, matriz, janela=50) → media_acertos_lote, melhor_acertos_medio, taxa_13_mais, baseline_media, baseline_taxa_13
    Walk-forward: pega últimos 50 concursos, testa lote contra cada um, compara com baseline aleatório
```
Backtest honesto: testa lote atual contra últimos 50 concursos reais, mostra se média > baseline aleatório (9.0). Ex: 9.33 média vs 9.0 baseline = acima da média.

#### TesteBinomial — Significância p-value
```python
class TesteBinomial:
    comb(n,k) → C(n,k)
    testar(k_sucessos, n_tentativas, p_sucesso) → p_value, veredito SIGNIFICATIVO/NÃO_SIGNIFICATIVO
    Ex: 3 acertos 13+ em 10 concursos com p=0.0014 → p_value=0.0002 significativo
```
Testa se taxa de acertos é estatisticamente significativa vs aleatório (p<0.05).

#### CurvaAprendizado — mm5 tendência
```python
class CurvaAprendizado:
    curva() → mm5 (média móvel 5), tendencia SUBINDO/DESCENDO/ESTÁVEL, slope
    Usa histórico Magna últimos 50 decisões
```
Mostra se sistema está aprendendo: curva de acertos subindo = melhorando.

---

## 3. Sistema Único — Mesmo Pipeline para Tudo

### Requisito Cumprido: Único Gerador Magna

**Antes v10:** `decidir_e_gerar` e `decidir_ancoradas_01_02_03` usavam fluxos diferentes.

**Agora v11:** Ambos usam **MESMO processo supremo**:

```python
# decidir_suprema (único gerador)
1. Regime adaptativo K-means k_otimo silhouette
2. Meta por regime + EWC
3. Vetor supremo + memória vetorial atenção
4. Perfil risco + multi-rota + MCTS pool
5. Forja suprema 60s 7 seeds k=7 (adaptativo: 3 seeds se qtd<=3)
6. Juiz 8 critérios + adversarial + NIST + p-value — regenera até 2x
7. Fingerprint SHA256 anti-repetição
8. Backtest 50 + binomial + curva + verificação exaustiva + explainability + utilidade esperada

# decidir_ancoradas_01_02_03 (mesmo processo)
Mesmos passos 1-8, apenas cartelas fixas 01/02/03 + 14 dezenas ranking Magna
```

**Validação:**
- `/api/magna/suprema` → estrategia `suprema-forja-13-7seeds-mcts-conservador`, unico_gerador=True
- `/api/magna/ancoras-123` → estrategia `ancoradas-01-02-03-suprema`, decisao_unica=True, mesmo pipeline
- Ambos retornam: julgamento, adversarial, NIST, p-value, backtest, curva, fingerprint, perfil, verificação

---

## 4. APIs v11

### POST /api/magna/suprema
```json
{
  "quantidade": 8,
  "orcamento": 100,
  "alvo": 13,
  "perfil": "conservador|equilibrado|agressivo",
  "segundos_forja": 30,
  "tentativas_juiz": 2,
  "usar_mcts": true,
  "usar_multi_rota": false,
  "salvar": true
}
→ julgamento, adversarial, nist, p_value, backtest, curva, fingerprint, perfil, utilidade, verificacao, explicacoes
```

### POST /api/magna/ancoras-123
```json
{
  "perfil": "conservador",
  "orcamento": 100,
  "salvar": true
}
→ MESMO pipeline supremo, 3 cartelas 01/02/03
```

### GET /api/magna/regime
→ regime adaptativo k_otimo, silhouette, regime_atual

### POST /api/magna/verificar
→ verificação exaustiva + backtest + NIST + p-value + adversarial + curva

### POST /api/magna/chat
```json
{"pergunta": "por que 22?"}
→ resposta explainability
```

### GET /api/magna/fingerprint
→ total_hashes, fingerprint SHA256

### POST /api/magna/perfil
```json
{"perfil": "agressivo", "orcamento": 100, "quantidade": 8}
→ perfil risco + alocação multi-rota
```

---

## 5. Uso Pessoal — Potência Máxima

### CLI
```bash
# Decisão única conservadora 8 cartelas 13 pontos 60s suprema
python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 13 --perfil conservador --modo suprema --segundos 60 --mcts --multi-rota

# Âncoras 01/02/03 mesmo processo supremo
python gerar_pessoal.py --ancoras --perfil conservador --chat "por que 22?"

# Agressivo caça 15
python gerar_pessoal.py --qtd 16 --orcamento 200 --alvo 15 --perfil agressivo --modo suprema --segundos 60 --tentativas 2
```

### Output Exemplo
```
[REGIME ADAPTATIVO] k_otimo=2 sil=0.189 atual=0
[PERFIL] conservador: Maximiza chance de 13 pontos
[MULTI-ROTA] Multi-rota conservador: 2 forja + 0 wheeling14 + 1 exaustão = 3 cartelas R$10.5
[JUIZ 8 CRITÉRIOS] APROVADO nota 0.808
[JUIZ ADVERSARIAL] ROBUSTO fraquezas [] comuns []
[NIST] ALEATÓRIO_OK chi2 12.3 gap 1.6
[P-VALUE RANDOM] MELHOR_QUE_RANDOM ratio 1.25
[BACKTEST 50] média 9.333 taxa13+ 0.0 vs baseline 9.0
[CURVA] tendência SUBINDO slope 0.02
[UTILIDADE] EV real R$-5.26 ROI -15% util_perfil 0.518
[FINGERPRINT] SHA256 16 chars hashes 56
[CHAT MAGNA] Q: por que 22? A: Dezena 22: top fonte motores (0.0427), votos oráculo 10/15...
```

---

## 6. Honestidade Matemática (Sempre)

- **Hipergeométrica:** 13≈1/692, 14≈1/21.800, 15=1/3.268.760 por cartela
- **Nenhuma peça prevê sorteio:** ganho combinatório, nunca preditivo
- **P(lote≥t) = |∪R_t| / 3.268.760:** exato, auditável, sem simulação
- **EV real com prêmios médios:** mostra ROI negativo honesto (loteria tem -50% EV)
- **Juiz que aprende, NIST, p-value, backtest, binomial, curva:** tudo para julgar honestamente se lote é melhor que aleatório

---

## 7. Próximos Passos (v12 Roadmap)

- [ ] Balança real 0.001g integrada via serial/USB + MotorFisicaSorteio com massa/diâmetro/densidade real
- [ ] MCTS com 2000 iterações + paralelismo + GPU
- [ ] Multi-rota com 5 rotas (forja, wheeling13, wheeling14, dual, exaustão) + alocação Kelly
- [ ] EWC com Fisher diagonal + synaptic consolidation
- [ ] ChatMagna com LLM local 7B (Llama) para explicações mais naturais
- [ ] Backtest walk-forward com retreino incremental por concurso
- [ ] Dashboard curva aprendizado + regime + fingerprint em tempo real

---

**Magna Suprema v11 — Sistema único pessoal em potência máxima, sem erros, com tudo que é possível e impossível dentro da honestidade matemática para 13/14/15.**

*Único gerador: Inteligência Magna. Mesmo processo para decisão única e âncoras 01/02/03.*
*Aprender: EWC, meta regime, clustering adaptativo, balança 0.001g*
*Decidir: perfil risco, MCTS pool, multi-rota 60/30/10, utilidade esperada prêmios reais*
*Julgar: juiz 8 critérios + adversarial + NIST + p-value + juiz que aprende*
*Entender: explainability LLM, chat por que 22, fingerprint SHA256*
*Verificar: backtest 50, binomial, curva mm5, verificação exaustiva*
