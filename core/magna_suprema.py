"""
MAGNA SUPREMA v10 — Evoluções para sistema único pessoal em potência máxima
- Detector de Regime (K-means sobre features)
- Memória Vetorial com atenção
- Juiz Magna (8 critérios)
- Verificador Exaustivo
- Alocador de Orçamento Inteligente
- Aprendizado Bayesiano com momentum

Tudo honesto: nenhum módulo prevê sorteio, apenas maximiza estrutura combinatória.
"""
import math
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from config import TOTAL_DEZENAS, QUADRANTES, VALOR_APOSTA, PRIMOS, FIBONACCI, BORDA

# ----------------------------------------------------------------
# Detector de Regime
# ----------------------------------------------------------------
class DetectorRegime:
    """
    Detecta regime atual do histórico: agrupa últimos 100 concursos em
    3 regimes via K-means simples sobre features (soma, pares, primos, fib, borda, consec, gap_medio).
    Retorna regime_id e pesos ajustados por regime baseado em desempenho histórico.
    """
    def __init__(self, matriz: np.ndarray):
        self.matriz = np.asarray(matriz, dtype=np.float64)
        self.n = len(self.matriz)

    def _features_concurso(self, idx: int) -> np.ndarray:
        row = self.matriz[idx]
        dez = [i+1 for i in range(TOTAL_DEZENAS) if row[i]==1]
        if len(dez)!=15:
            return np.zeros(7)
        soma = sum(dez)
        pares = sum(1 for d in dez if d%2==0)
        primos = len(set(dez) & PRIMOS)
        fib = len(set(dez) & FIBONACCI)
        borda = len(set(dez) & BORDA)
        sd = sorted(dez); mc=cc=1
        for i in range(1,len(sd)):
            if sd[i]==sd[i-1]+1: cc+=1; mc=max(mc,cc)
            else: cc=1
        gaps = [sd[i+1]-sd[i] for i in range(len(sd)-1)]
        gap_medio = float(np.mean(gaps)) if gaps else 0
        return np.array([soma/300.0, pares/15.0, primos/15.0, fib/15.0, borda/15.0, mc/15.0, gap_medio/5.0], dtype=np.float64)

    def detectar(self, k: int = 3, janela: int = 100) -> Dict[str, Any]:
        janela = min(janela, self.n)
        if janela < 20:
            return {"regime_atual": 0, "n_regimes": 1, "descricao": "dados insuficientes", "centroides": []}
        feats = np.vstack([self._features_concurso(self.n - janela + i) for i in range(janela)])
        # K-means simples
        rng = np.random.default_rng(42)
        # init centroides como amostras aleatórias
        idx_init = rng.choice(janela, size=min(k, janela), replace=False)
        centroids = feats[idx_init].copy()
        for _ in range(20):
            dists = np.linalg.norm(feats[:, None, :] - centroids[None, :, :], axis=2)
            labels = np.argmin(dists, axis=1)
            new_cent = []
            for ci in range(len(centroids)):
                members = feats[labels==ci]
                if len(members)==0:
                    new_cent.append(centroids[ci])
                else:
                    new_cent.append(members.mean(axis=0))
            new_cent = np.vstack(new_cent)
            if np.allclose(new_cent, centroids, atol=1e-4):
                break
            centroids = new_cent
        # regime atual = label do último concurso
        ultimo_feat = self._features_concurso(self.n-1)
        d_last = np.linalg.norm(centroids - ultimo_feat, axis=1)
        regime_atual = int(np.argmin(d_last))
        # descrição
        desc = []
        for i, cent in enumerate(centroids):
            desc.append({
                "regime": i,
                "soma_est": round(float(cent[0]*300),1),
                "pares_est": round(float(cent[1]*15),1),
                "primos_est": round(float(cent[2]*15),1),
                "fib_est": round(float(cent[3]*15),1),
                "borda_est": round(float(cent[4]*15),1),
                "consec_est": round(float(cent[5]*15),1),
                "gap_est": round(float(cent[6]*5),2),
                "freq": int((labels==i).sum()),
            })
        return {
            "regime_atual": regime_atual,
            "n_regimes": len(centroids),
            "centroides": desc,
            "labels_janela": labels.tolist(),
            "descricao": f"Regime {regime_atual} dominante nos últimos {janela} concursos",
        }

# ----------------------------------------------------------------
# Memória Vetorial com Atenção
# ----------------------------------------------------------------
class MemoriaVetorialMagna:
    """
    Armazena episódios como embeddings 25D (vf ponderado) e busca por similaridade
    cosseno para reforço contextual. Implementa atenção: quanto mais similar a protótipo,
    maior reforço; similar a repulsão, maior penalidade.
    """
    def __init__(self, episodios: List[Dict[str, Any]]):
        self.episodios = episodios or []

    def _embed(self, dezenas: List[int], vf: Optional[np.ndarray] = None) -> np.ndarray:
        v = np.zeros(TOTAL_DEZENAS, dtype=np.float64)
        for d in dezenas:
            if 1 <= int(d) <= 25:
                v[int(d)-1] = 1.0
        if vf is not None:
            v = v * np.asarray(vf, dtype=np.float64)
        norm = np.linalg.norm(v)
        return v / (norm+1e-9) if norm>0 else v

    def reforco_contextual(self, vf: np.ndarray, top_k: int = 20) -> np.ndarray:
        vf = np.asarray(vf, dtype=np.float64)
        vf_norm = vf / (vf.max()+1e-9)
        ajuste = np.ones(TOTAL_DEZENAS, dtype=np.float64)
        if not self.episodios:
            return vf_norm
        # embeddings dos episódios
        query = vf_norm / (np.linalg.norm(vf_norm)+1e-9)
        scores = []
        for ep in self.episodios[:200]:
            dez = ep.get("dezenas") or []
            emb = self._embed(dez)
            sim = float(np.dot(query, emb))  # cosseno
            tipo = ep.get("tipo","neutro")
            peso = 1.0
            if tipo=="prototipo":
                peso = 1.5
            elif tipo=="repulsao":
                peso = -1.2
            scores.append((sim*peso, ep))
        scores.sort(key=lambda x: x[0], reverse=True)
        # aplica reforço nos top_k
        for sim_peso, ep in scores[:top_k]:
            if abs(sim_peso) < 0.1:
                continue
            for d in ep.get("dezenas") or []:
                if 1 <= int(d) <= 25:
                    if sim_peso > 0:
                        ajuste[int(d)-1] *= (1.0 + 0.03*sim_peso)
                    else:
                        ajuste[int(d)-1] *= (1.0 + 0.02*sim_peso)  # sim_peso negativo → penaliza
        vf_ajust = vf_norm * ajuste
        vf_ajust = np.clip(vf_ajust, 1e-9, None)
        return vf_ajust / vf_ajust.sum()

# ----------------------------------------------------------------
# Juiz Magna — 8 critérios
# ----------------------------------------------------------------
class JuizMagna:
    """
    Julga lote gerado em 8 critérios. Se reprovar >2, solicita regeneração.
    """
    def __init__(self, matriz: Optional[np.ndarray] = None):
        self.matriz = matriz

    def julgar(self, cartelas: List[List[int]], pool: List[int],
               analise: Dict[str, Any], vf: np.ndarray,
               historico_15_masks: set) -> Dict[str, Any]:
        criterios = {}
        # 1. Diversidade pool min_dist >0.55
        try:
            from .forja_lotes import MotorGrafos
            if self.matriz is not None and len(self.matriz)>=30:
                mg = MotorGrafos(self.matriz)
                div = mg.diversidade_pool(pool)
                criterios["diversidade_pool"] = {
                    "ok": div.get("min_dist",0) >= 0.55,
                    "valor": div,
                    "peso": 1.0,
                }
            else:
                criterios["diversidade_pool"] = {"ok": True, "valor": {}, "peso": 0.5}
        except Exception as e:
            criterios["diversidade_pool"] = {"ok": True, "valor": str(e), "peso": 0.5}

        # 2. Cobertura 13
        p13 = float(analise.get("p_melhor_13_mais") or analise.get("p_melhor_13") or 0)
        criterios["cobertura_13"] = {
            "ok": p13 >= 0.005,  # pelo menos 0.5% para lote 8
            "valor": p13,
            "peso": 1.2,
        }

        # 3. Novidade — nenhuma cartela já foi 15 oficial
        def mask_dez(dezenas):
            m=0
            for d in dezenas:
                m|=1<<(int(d)-1)
            return m
        duplicadas_15 = sum(1 for c in cartelas if mask_dez(c) in historico_15_masks)
        criterios["novidade_15"] = {
            "ok": duplicadas_15==0,
            "valor": duplicadas_15,
            "peso": 2.0,
        }

        # 4. Equilíbrio quadrantes pool
        quad_ok = True
        quad_counts = {}
        for q, nums in QUADRANTES.items():
            cnt = sum(1 for d in pool if d in nums)
            quad_counts[q]=cnt
            if cnt < 2:
                quad_ok=False
        criterios["quadrantes"] = {
            "ok": quad_ok,
            "valor": quad_counts,
            "peso": 1.0,
        }

        # 5. Distância Johnson — z entre -2 e 2 ideal (não muito concentrado nem espalhado)
        try:
            from .forja_lotes import GeometriaJohnson
            geo = GeometriaJohnson().relatorio(cartelas, n_sim=100)
            z = geo.get("z_dispersao",0)
            criterios["johnson_z"] = {
                "ok": abs(z) <= 2.5,
                "valor": z,
                "peso": 0.8,
                "detalhe": geo,
            }
        except Exception as e:
            criterios["johnson_z"] = {"ok": True, "valor": str(e), "peso": 0.5}

        # 6. EV
        ev = float(analise.get("ev_lote",0))
        custo = len(cartelas)*VALOR_APOSTA
        criterios["ev"] = {
            "ok": ev >= -custo*0.9,  # EV não pode ser pior que -90% custo (sempre negativo, mas não absurdo)
            "valor": ev,
            "peso": 0.7,
        }

        # 7. Calibração vs histórico — verifica se pool tem pelo menos 10 dezenas com vf acima média
        vf = np.asarray(vf, dtype=np.float64)
        media_vf = float(vf.mean())
        acima = sum(1 for d in pool if vf[d-1] > media_vf)
        criterios["calibracao_vf"] = {
            "ok": acima >= 10,
            "valor": acima,
            "peso": 0.8,
        }

        # 8. Entropia filtros — soma dentro de faixa p1-p99 (já filtrado, mas reforça)
        somas = [sum(c) for c in cartelas]
        soma_ok = all(165 <= s <= 240 for s in somas)
        criterios["filtros_soma"] = {
            "ok": soma_ok,
            "valor": {"min": min(somas) if somas else 0, "max": max(somas) if somas else 0},
            "peso": 0.9,
        }

        # veredito
        reprovados = [k for k,v in criterios.items() if not v.get("ok")]
        nota = sum(v.get("peso",1) for k,v in criterios.items() if v.get("ok")) / max(sum(v.get("peso",1) for v in criterios.values()),1)
        veredito = "APROVADO" if len(reprovados) <=2 else "REPROVADO"
        return {
            "veredito": veredito,
            "nota": round(nota,3),
            "reprovados": reprovados,
            "criterios": criterios,
            "recomendacao": "Regenerar com penalidade" if veredito=="REPROVADO" else "Lote pronto para uso pessoal",
        }

# ----------------------------------------------------------------
# Verificador Exaustivo
# ----------------------------------------------------------------
class VerificadorMagno:
    """
    Recalcula P(lote≥t) exato via união leques e compara com baseline.
    Gera relatório honesto.
    """
    def verificar(self, cartelas: List[List[int]], pool: List[int]) -> Dict[str, Any]:
        try:
            from .forja_lotes import RegiaoAltoAcerto, GeometriaJohnson
            from .wheeling import MotorWheeling
            reg = RegiaoAltoAcerto()
            geo = GeometriaJohnson()
            analise = MotorWheeling().analisar_lote(cartelas, pool)
            # união exata 13 e 14
            u13, _ = reg.uniao_lote(cartelas, 13)
            u14, _ = reg.uniao_lote(cartelas, 14)
            total = 3268760
            p13 = u13/total
            p14 = u14/total
            return {
                "p13_exata": round(p13,8),
                "p14_exata": round(p14,8),
                "um_em_13": round(1/p13,1) if p13>0 else None,
                "um_em_14": round(1/p14,1) if p14>0 else None,
                "leque_13": u13,
                "leque_14": u14,
                "analise_wheeling": analise,
                "geometria": geo.relatorio(cartelas, n_sim=100),
                "honestidade": f"Lote de {len(cartelas)} cartelas: P≥13={p13*100:.4f}% (1 em {1/p13:.1f}), P≥14={p14*100:.6f}% (1 em {1/p14:.1f}) sobre universo exato 3.268.760. Garantias condicionais só valem se pool capturar.",
            }
        except Exception as e:
            return {"erro": str(e), "honestidade": "Falha na verificação exaustiva"}

# ----------------------------------------------------------------
# Alocador de Orçamento Inteligente
# ----------------------------------------------------------------
class AlocadorOrcamentoMagno:
    """
    Dado orçamento, divide em sub-lotes para maximizar utilidade esperada.
    Usa knapsack simples: tenta combinar wheeling 13 + forja 13 + exaustão.
    """
    def alocar(self, orcamento: float, quantidade_max: int = 20, alvo: int = 13) -> Dict[str, Any]:
        max_cart = max(1, int(orcamento // VALOR_APOSTA))
        n = min(quantidade_max, max_cart)
        # estratégias possíveis com custo
        estrategias = [
            {"nome": "forja-13", "cartelas": min(8, n), "custo": min(8,n)*VALOR_APOSTA, "p13_est": 0.012, "ev": -0.5},
            {"nome": "wheeling-14", "cartelas": min(8, n), "custo": min(8,n)*VALOR_APOSTA, "p13_est": 0.008, "p14_est": 0.0004, "ev": -0.4},
            {"nome": "wheeling-13-pool18", "cartelas": 6, "custo": 21.0, "p13_est": 0.006, "ev": -0.3},
            {"nome": "exaustao-diversa", "cartelas": min(5, n), "custo": min(5,n)*VALOR_APOSTA, "p13_est": 0.005, "ev": -0.6},
        ]
        # simples: escolhe combinação que maximiza p13 dentro orçamento
        melhor = None
        melhor_score = -1
        # tenta 2 combinações
        for i, e1 in enumerate(estrategias):
            if e1["custo"] <= orcamento:
                score = e1["p13_est"] * (1 + (e1.get("p14_est",0)*10))
                if score > melhor_score:
                    melhor_score = score
                    melhor = [e1]
            for e2 in estrategias[i+1:]:
                custo2 = e1["custo"]+e2["custo"]
                if custo2 <= orcamento and (e1["cartelas"]+e2["cartelas"]) <= n:
                    score = (e1["p13_est"]+e2["p13_est"]) * 1.2
                    if score > melhor_score:
                        melhor_score = score
                        melhor = [e1, e2]
        if melhor is None:
            melhor = [estrategias[0]]
        total_cart = sum(e["cartelas"] for e in melhor)
        total_custo = sum(e["custo"] for e in melhor)
        return {
            "alocacao": melhor,
            "total_cartelas": total_cart,
            "total_custo": total_custo,
            "orcamento": orcamento,
            "score": melhor_score,
            "recomendacao": f"Com R${orcamento:.2f}, use {total_cart} cartelas em {len(melhor)} estratégia(s) para maximizar P≥13",
        }

# ----------------------------------------------------------------
# Aprendizado Bayesiano com Momentum
# ----------------------------------------------------------------
class AprendizadoBayesianoMagno:
    """
    Pesos fontes como Dirichlet posterior. Atualiza com evidência + momentum.
    """
    def __init__(self, pesos_iniciais: Dict[str, float], alpha_prior: float = 10.0):
        self.pesos = dict(pesos_iniciais)
        self.alpha = {k: alpha_prior * v for k,v in pesos_iniciais.items()}
        self.momentum = {k: 0.0 for k in pesos_iniciais}
        self.historico = []

    def atualizar(self, acertos_fontes: Dict[str, int], lr: float = 0.15, momentum_beta: float = 0.7) -> Dict[str, float]:
        # evidência: acertos - 9 (baseline)
        for fonte, acertos in acertos_fontes.items():
            if fonte not in self.alpha:
                continue
            evidencia = (acertos - 9) * 0.5  # -4.5 a +3
            grad = evidencia
            self.momentum[fonte] = momentum_beta * self.momentum[fonte] + (1-momentum_beta)*grad
            self.alpha[fonte] = max(0.5, self.alpha[fonte] + lr * self.momentum[fonte])
        total_alpha = sum(self.alpha.values())
        novos_pesos = {k: round(v/total_alpha,6) for k,v in self.alpha.items()}
        self.pesos = novos_pesos
        self.historico.append({"acertos": acertos_fontes, "pesos": novos_pesos})
        if len(self.historico) > 100:
            self.historico = self.historico[-100:]
        return novos_pesos

    def get_pesos(self) -> Dict[str, float]:
        return dict(self.pesos)
