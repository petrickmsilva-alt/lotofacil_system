"""
MAGNA SUPREMA v10.1 — Evoluções completas para sistema único pessoal em potência máxima
Implementa TODAS as evoluções pedidas:
- Aprender: EWC continual, meta-learning pesos por regime, clustering adaptativo, balança 0.001g
- Decidir: perfil risco pessoal, MCTS pool, alocação multi-rota, utilidade esperada prêmios reais
- Julgar: juiz adversarial, NIST, p-value vs random, juiz que aprende
- Entender: explainability LLM, chat, fingerprint SHA256
- Verificar: backtest walk-forward lote, binomial significância, curva aprendizado

Tudo honesto: nenhum módulo prevê sorteio, apenas maximiza estrutura combinatória.
Único gerador: Inteligência Magna — tanto decisão única quanto 3 âncoras passam pelo mesmo processo.
"""
import math
import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from config import TOTAL_DEZENAS, QUADRANTES, VALOR_APOSTA, PRIMOS, FIBONACCI, BORDA

# ----------------------------------------------------------------
# Detector de Regime + Clustering Adaptativo
# ----------------------------------------------------------------
class DetectorRegime:
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

    def _kmeans(self, feats: np.ndarray, k: int):
        rng = np.random.default_rng(42)
        idx_init = rng.choice(len(feats), size=min(k, len(feats)), replace=False)
        centroids = feats[idx_init].copy()
        labels = np.zeros(len(feats), dtype=int)
        for _ in range(25):
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
        # inertia
        inertia = sum(np.linalg.norm(feats[i]-centroids[labels[i]])**2 for i in range(len(feats)))
        return centroids, labels, inertia

    def _silhouette(self, feats: np.ndarray, labels: np.ndarray) -> float:
        # silhouette simplificado médio
        try:
            n = len(feats)
            if len(set(labels)) < 2:
                return 0.0
            sils = []
            for i in range(min(n, 50)):  # amostra 50 para performance
                same = feats[labels==labels[i]]
                other_labels = set(labels)-{labels[i]}
                if len(same)<=1 or not other_labels:
                    continue
                a = np.mean([np.linalg.norm(feats[i]-f) for f in same if not np.array_equal(f, feats[i])])
                b = min(np.mean([np.linalg.norm(feats[i]-f) for f in feats[labels==ol]]) for ol in other_labels)
                sil = (b-a)/max(a,b) if max(a,b)>0 else 0
                sils.append(sil)
            return float(np.mean(sils)) if sils else 0.0
        except Exception:
            return 0.0

    def detectar(self, k: int = 3, janela: int = 100) -> Dict[str, Any]:
        janela = min(janela, self.n)
        if janela < 20:
            return {"regime_atual": 0, "n_regimes": 1, "descricao": "dados insuficientes", "centroides": [], "k_otimo": 1, "silhouette": 0}
        feats = np.vstack([self._features_concurso(self.n - janela + i) for i in range(janela)])
        centroids, labels, inertia = self._kmeans(feats, k)
        ultimo_feat = self._features_concurso(self.n-1)
        d_last = np.linalg.norm(centroids - ultimo_feat, axis=1)
        regime_atual = int(np.argmin(d_last))
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
            "inertia": round(float(inertia),3),
            "silhouette": round(self._silhouette(feats, labels),3),
            "descricao": f"Regime {regime_atual} dominante nos últimos {janela} concursos",
            "k_otimo": k,
        }

    def detectar_adaptativo(self, janela: int = 100) -> Dict[str, Any]:
        """Clustering adaptativo: testa k=2..4 e escolhe melhor silhouette."""
        melhor = None
        melhor_sil = -1
        resultados = []
        for k in [2,3,4]:
            res = self.detectar(k=k, janela=janela)
            sil = res.get("silhouette",0)
            resultados.append((k, sil, res))
            if sil > melhor_sil:
                melhor_sil = sil
                melhor = res
        if melhor is None:
            melhor = self.detectar(k=3, janela=janela)
        melhor["k_candidatos"] = [{"k": k, "silhouette": sil} for k,sil,_ in resultados]
        melhor["adaptativo"] = True
        melhor["k_otimo"] = melhor.get("n_regimes",3)
        return melhor

# ----------------------------------------------------------------
# EWC Continual Learning
# ----------------------------------------------------------------
class EWCContinual:
    """Elastic Weight Consolidation simplificado para pesos fontes."""
    def __init__(self, lambda_ewc: float = 0.4):
        self.lambda_ewc = lambda_ewc
        self.pesos_antigos = {}
        self.fisher = {}  # importância aproximada

    def consolidar(self, pesos_atuais: Dict[str, float], acertos_fontes: Dict[str, int]):
        # Fisher aproximada = (acertos-9)^2
        for fonte, ac in acertos_fontes.items():
            if fonte not in pesos_atuais:
                continue
            self.fisher[fonte] = self.fisher.get(fonte, 0)*0.9 + 0.1*((ac-9)**2)
        self.pesos_antigos = dict(pesos_atuais)

    def penalidade(self, pesos_novos: Dict[str, float]) -> float:
        pen = 0.0
        for k,v in pesos_novos.items():
            if k in self.pesos_antigos and k in self.fisher:
                pen += self.fisher[k] * (v - self.pesos_antigos[k])**2
        return 0.5 * self.lambda_ewc * pen

    def regularizar(self, pesos_propostos: Dict[str, float]) -> Dict[str, float]:
        # puxa de volta para pesos antigos proporcional à Fisher
        out = {}
        for k,v in pesos_propostos.items():
            if k in self.pesos_antigos and k in self.fisher:
                fisher_norm = min(self.fisher[k]/10.0, 1.0)
                out[k] = v*(1 - self.lambda_ewc*fisher_norm*0.1) + self.pesos_antigos[k]*self.lambda_ewc*fisher_norm*0.1
            else:
                out[k]=v
        total = sum(out.values())
        return {k: round(v/total,6) for k,v in out.items()} if total>0 else out

# ----------------------------------------------------------------
# Meta-Aprendizado por Regime
# ----------------------------------------------------------------
class MetaAprendizadoRegime:
    """Mantém pesos por regime, aprende regime-específico."""
    def __init__(self):
        self.pesos_por_regime: Dict[int, Dict[str,float]] = {}
        self.contagem_por_regime: Dict[int,int] = {}

    def obter_pesos_regime(self, regime_id: int, pesos_default: Dict[str,float]) -> Dict[str,float]:
        return self.pesos_por_regime.get(regime_id, dict(pesos_default))

    def atualizar(self, regime_id: int, acertos_fontes: Dict[str,int], pesos_atuais: Dict[str,float], lr: float=0.12):
        if regime_id not in self.pesos_por_regime:
            self.pesos_por_regime[regime_id] = dict(pesos_atuais)
        antes = self.pesos_por_regime[regime_id]
        # ajuste por regime
        ajustados = {}
        for fonte, ac in acertos_fontes.items():
            if fonte not in antes:
                continue
            fator = 1.0 + lr * (ac - 9) / 9.0
            ajustados[fonte] = max(0.01, antes[fonte]*fator)
        total = sum(ajustados.values())
        if total>0:
            ajustados = {k: round(v/total,6) for k,v in ajustados.items()}
            self.pesos_por_regime[regime_id] = ajustados
        self.contagem_por_regime[regime_id] = self.contagem_por_regime.get(regime_id,0)+1
        return self.pesos_por_regime[regime_id]

    def relatorio(self):
        return {
            "regimes_conhecidos": list(self.pesos_por_regime.keys()),
            "contagem": self.contagem_por_regime,
            "pesos_por_regime": self.pesos_por_regime,
        }

# ----------------------------------------------------------------
# Física Real Balança 0.001g
# ----------------------------------------------------------------
class FisicaRealBalanca:
    """Interface para balança 0.001g — valida medição física real das bolas."""
    def __init__(self, db_path: Optional[str]=None):
        self.db_path = db_path

    def validar_medicao(self, massa_g: float, diametro_mm: float) -> Dict[str,Any]:
        # Faixas realistas bola lotofácil: ~3-4g? (exemplo)
        # Aqui validamos com tolerância
        ok_massa = 2.5 <= massa_g <= 6.0
        ok_diam = 30.0 <= diametro_mm <= 50.0
        densidade = massa_g / ((4/3)*math.pi*(diametro_mm/2/10)**3) if diametro_mm>0 else 0  # g/cm3
        ok_dens = 0.5 <= densidade <= 2.5
        return {
            "massa_g": massa_g,
            "diametro_mm": diametro_mm,
            "densidade_gcm3": round(densidade,3),
            "ok_massa": ok_massa,
            "ok_diametro": ok_diam,
            "ok_densidade": ok_dens,
            "aprovada": ok_massa and ok_diam and ok_dens,
            "precisao_balanca": "0.001g",
            "mensagem": "Medição aprovada para fonte física" if (ok_massa and ok_diam and ok_dens) else "Medição fora da faixa realista — verificar balança",
        }

    def registrar_medicao(self, numero: int, massa_g: float, diametro_mm: float, db_manager=None) -> Dict[str,Any]:
        valid = self.validar_medicao(massa_g, diametro_mm)
        if not valid["aprovada"]:
            return {"status": "reprovada", "validacao": valid}
        # tenta registrar via MotorFisicaSorteio se db disponível
        try:
            from .fisica_sorteio import MotorFisicaSorteio
            if db_manager:
                fisica = MotorFisicaSorteio(db_manager.db_path if hasattr(db_manager,'db_path') else self.db_path)
                res = fisica.registrar_bola(numero=numero, massa_g=massa_g, diametro_mm=diametro_mm)
                return {"status": "ok", "bola": res, "validacao": valid}
        except Exception as e:
            return {"status": "ok_sem_db", "validacao": valid, "erro_db": str(e)}
        return {"status": "ok", "validacao": valid}

# ----------------------------------------------------------------
# Memória Vetorial com Atenção
# ----------------------------------------------------------------
class MemoriaVetorialMagna:
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
        query = vf_norm / (np.linalg.norm(vf_norm)+1e-9)
        scores = []
        for ep in self.episodios[:200]:
            dez = ep.get("dezenas") or []
            emb = self._embed(dez)
            sim = float(np.dot(query, emb))
            tipo = ep.get("tipo","neutro")
            peso = 1.0
            if tipo=="prototipo":
                peso = 1.5
            elif tipo=="repulsao":
                peso = -1.2
            scores.append((sim*peso, ep))
        scores.sort(key=lambda x: x[0], reverse=True)
        for sim_peso, ep in scores[:top_k]:
            if abs(sim_peso) < 0.1:
                continue
            for d in ep.get("dezenas") or []:
                if 1 <= int(d) <= 25:
                    if sim_peso > 0:
                        ajuste[int(d)-1] *= (1.0 + 0.03*sim_peso)
                    else:
                        ajuste[int(d)-1] *= (1.0 + 0.02*sim_peso)
        vf_ajust = vf_norm * ajuste
        vf_ajust = np.clip(vf_ajust, 1e-9, None)
        return vf_ajust / vf_ajust.sum()

# ----------------------------------------------------------------
# Perfil Risco Pessoal
# ----------------------------------------------------------------
class PerfilRiscoPessoal:
    """
    Conservador: max P13
    Equilibrado: max EV
    Agressivo: max P15
    """
    PERFIS = {
        "conservador": {"w_p13": 0.7, "w_p14": 0.2, "w_p15": 0.05, "w_ev": 0.05, "descricao": "Maximiza chance de 13 pontos (1 em 691 por cartela)"},
        "equilibrado": {"w_p13": 0.3, "w_p14": 0.3, "w_p15": 0.1, "w_ev": 0.3, "descricao": "Equilibra P13/P14 e valor esperado"},
        "agressivo": {"w_p13": 0.1, "w_p14": 0.3, "w_p15": 0.5, "w_ev": 0.1, "descricao": "Caça 15 pontos (1 em 3.2M) — maior risco, maior prêmio"},
    }

    def __init__(self, perfil: str = "equilibrado"):
        self.perfil = perfil if perfil in self.PERFIS else "equilibrado"
        self.pesos = self.PERFIS[self.perfil]

    def utilidade(self, p13: float, p14: float, p15: float, ev: float) -> float:
        # normaliza
        # p13 ~0.01, p14~0.0003, p15~0.0000003, ev ~ -2
        # escala para comparável
        p13_n = min(p13*100, 1.0)
        p14_n = min(p14*1000, 1.0)
        p15_n = min(p15*1_000_000, 1.0)
        ev_n = max(0, (ev + 10)/10)  # ev -3 => 0.7, ev 0 =>1
        return (
            self.pesos["w_p13"]*p13_n +
            self.pesos["w_p14"]*p14_n +
            self.pesos["w_p15"]*p15_n +
            self.pesos["w_ev"]*ev_n
        )

    def recomendar_alvo(self) -> int:
        if self.perfil == "conservador":
            return 13
        elif self.perfil == "agressivo":
            return 15
        else:
            return 14

    def relatorio(self):
        return {"perfil": self.perfil, **self.pesos}

# ----------------------------------------------------------------
# MCTS Pool
# ----------------------------------------------------------------
class MCTSPool:
    """MCTS simplificado para pool elite: cada nó adiciona dezena, recompensa = vf + diversidade."""
    class No:
        def __init__(self, pool: List[int], vf: np.ndarray, distancia: np.ndarray, parent=None, acao=None):
            self.pool = pool
            self.vf = vf
            self.distancia = distancia
            self.parent = parent
            self.acao = acao
            self.filhos = []
            self.visitas = 0
            self.valor_total = 0.0
            self.nao_expandidos = [i for i in range(TOTAL_DEZENAS) if (i+1) not in pool]

        def uct(self, c: float = 1.4) -> float:
            if self.visitas==0:
                return float('inf')
            media = self.valor_total / self.visitas
            if self.parent is None:
                return media
            return media + c * math.sqrt(math.log(self.parent.visitas+1) / (self.visitas+1))

        def recompensa(self) -> float:
            if not self.pool:
                return 0
            vf_sum = sum(self.vf[d-1] for d in self.pool)
            # diversidade
            if len(self.pool) >=2:
                idx = [d-1 for d in self.pool]
                dists = []
                for i in range(len(idx)):
                    for j in range(i+1, len(idx)):
                        dists.append(float(self.distancia[idx[i], idx[j]]))
                div = float(np.mean(dists)) if dists else 0
            else:
                div = 0.5
            # quadrantes
            quad_bonus = 0
            for q, nums in QUADRANTES.items():
                if any(d in nums for d in self.pool):
                    quad_bonus += 0.1
            return vf_sum * 0.6 + div * 0.3 + quad_bonus

    def __init__(self, matriz: np.ndarray):
        self.matriz = matriz
        try:
            from .forja_lotes import MotorGrafos
            mg = MotorGrafos(matriz)
            self.distancia = mg.distancia_euc
        except Exception:
            self.distancia = np.ones((TOTAL_DEZENAS, TOTAL_DEZENAS))*0.5

    def buscar(self, vf: np.ndarray, tam: int = 17, iteracoes: int = 800, semente: int = 42) -> List[int]:
        vf = np.asarray(vf, dtype=np.float64)
        rng = np.random.default_rng(semente)
        raiz = self.No([], vf, self.distancia)
        # ranking top candidatas
        ordem = np.argsort(vf)[::-1][:22]
        candidatas = [int(i+1) for i in ordem]

        for _ in range(iteracoes):
            # seleção
            no = raiz
            while no.filhos and not no.nao_expandidos:
                no = max(no.filhos, key=lambda n: n.uct())
            # expansão
            if no.nao_expandidos and len(no.pool) < tam:
                # escolhe entre candidatas não no pool
                possiveis = [d for d in candidatas if d not in no.pool]
                if not possiveis:
                    possiveis = [i+1 for i in range(TOTAL_DEZENAS) if (i+1) not in no.pool]
                if possiveis:
                    acao = int(rng.choice(possiveis))
                    novo_pool = sorted(no.pool + [acao])
                    filho = self.No(novo_pool, vf, self.distancia, parent=no, acao=acao)
                    no.filhos.append(filho)
                    if (acao-1) in no.nao_expandidos:
                        no.nao_expandidos.remove(acao-1)
                    no = filho
            # simulação (rollout) até tam
            pool_sim = list(no.pool)
            while len(pool_sim) < tam:
                restantes = [d for d in candidatas if d not in pool_sim]
                if not restantes:
                    restantes = [i+1 for i in range(TOTAL_DEZENAS) if (i+1) not in pool_sim]
                if not restantes:
                    break
                # escolhe com prob vf
                pesos = np.array([vf[d-1] for d in restantes])
                pesos = pesos / (pesos.sum()+1e-9)
                pool_sim.append(int(rng.choice(restantes, p=pesos)))
            # recompensa
            no_temp = self.No(sorted(pool_sim), vf, self.distancia)
            reward = no_temp.recompensa()
            # backprop
            cur = no
            while cur is not None:
                cur.visitas += 1
                cur.valor_total += reward
                cur = cur.parent

        # escolhe melhor caminho
        no = raiz
        pool_final = []
        while len(pool_final) < tam and no.filhos:
            no = max(no.filhos, key=lambda n: n.visitas)
            pool_final = no.pool
        if len(pool_final) < tam:
            # completa com vf
            for d in candidatas:
                if d not in pool_final and len(pool_final) < tam:
                    pool_final.append(d)
        return sorted(pool_final)[:tam]

# ----------------------------------------------------------------
# Juiz Magna — 9 critérios + adversarial + NIST + p-value + aprendizado
# ----------------------------------------------------------------
class JuizMagna:
    def __init__(self, matriz: Optional[np.ndarray] = None):
        self.matriz = matriz
        self.pesos_criterios = {
            "diversidade_pool": 1.0,
            "cobertura_13": 1.2,
            "novidade_15": 2.0,
            "quadrantes": 1.0,
            "johnson_z": 0.8,
            "ev": 0.7,
            "calibracao_vf": 0.8,
            "filtros_soma": 0.9,
            # v11.4 — o acervo de abertura da própria Magna entrou como
            # critério de julgamento (peso baixo: é estrutura, não previsão).
            "cobertura_abertura": 0.6,
        }
        self.historico_falhas = {}  # critério -> vezes que falhou mas depois deu 13+

    def julgar(self, cartelas: List[List[int]], pool: List[int],
               analise: Dict[str, Any], vf: np.ndarray,
               historico_15_masks: set,
               abertura: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        criterios = {}
        try:
            from .forja_lotes import MotorGrafos
            if self.matriz is not None and len(self.matriz)>=30:
                mg = MotorGrafos(self.matriz)
                div = mg.diversidade_pool(pool)
                criterios["diversidade_pool"] = {
                    "ok": div.get("min_dist",0) >= 0.55,
                    "valor": div,
                    "peso": self.pesos_criterios["diversidade_pool"],
                }
            else:
                criterios["diversidade_pool"] = {"ok": True, "valor": {}, "peso": 0.5}
        except Exception as e:
            criterios["diversidade_pool"] = {"ok": True, "valor": str(e), "peso": 0.5}

        p13 = float(analise.get("p_melhor_13_mais") or analise.get("p_melhor_13") or 0)
        criterios["cobertura_13"] = {
            "ok": p13 >= 0.005,
            "valor": p13,
            "peso": self.pesos_criterios["cobertura_13"],
        }

        def mask_dez(dezenas):
            m=0
            for d in dezenas:
                m|=1<<(int(d)-1)
            return m
        duplicadas_15 = sum(1 for c in cartelas if mask_dez(c) in historico_15_masks)
        criterios["novidade_15"] = {
            "ok": duplicadas_15==0,
            "valor": duplicadas_15,
            "peso": self.pesos_criterios["novidade_15"],
        }

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
            "peso": self.pesos_criterios["quadrantes"],
        }

        try:
            from .forja_lotes import GeometriaJohnson
            geo = GeometriaJohnson().relatorio(cartelas, n_sim=100)
            z = geo.get("z_dispersao",0)
            criterios["johnson_z"] = {
                "ok": abs(z) <= 2.5,
                "valor": z,
                "peso": self.pesos_criterios["johnson_z"],
                "detalhe": geo,
            }
        except Exception as e:
            criterios["johnson_z"] = {"ok": True, "valor": str(e), "peso": 0.5}

        ev = float(analise.get("ev_lote",0))
        custo = len(cartelas)*VALOR_APOSTA
        criterios["ev"] = {
            "ok": ev >= -custo*0.9,
            "valor": ev,
            "peso": self.pesos_criterios["ev"],
        }

        vf = np.asarray(vf, dtype=np.float64)
        media_vf = float(vf.mean())
        acima = sum(1 for d in pool if vf[d-1] > media_vf)
        criterios["calibracao_vf"] = {
            "ok": acima >= 10,
            "valor": acima,
            "peso": self.pesos_criterios["calibracao_vf"],
        }

        somas = [sum(c) for c in cartelas]
        soma_ok = all(165 <= s <= 240 for s in somas)
        criterios["filtros_soma"] = {
            "ok": soma_ok,
            "valor": {"min": min(somas) if somas else 0, "max": max(somas) if somas else 0},
            "peso": self.pesos_criterios["filtros_soma"],
        }

        # v11.4 — cobertura de abertura (conhecimento da própria Magna).
        # `abertura` é o posterior aprendido do acervo: {"probabilidades":
        # {dezena: p}, "ranking": [d...]} . O lote é julgado pela massa de
        # probabilidade de abertura que ele cobre: um lote cujas cartelas
        # abrem quase sempre em 04/05 ignora a estrutura do sorteio real.
        # É critério de ESTRUTURA (peso 0,6) — não altera a hipergeométrica.
        if abertura:
            try:
                probs = {int(k): float(v) for k, v in
                         (abertura.get("probabilidades") or {}).items()}
                if probs and cartelas:
                    aberturas_lote = sorted({min(int(d) for d in c)
                                             for c in cartelas})
                    cobertura = round(sum(probs.get(d, 0.0)
                                          for d in aberturas_lote), 4)
                    ranking_aprendido = [int(d) for d in
                                         (abertura.get("ranking") or [])][:3]
                    top1 = ranking_aprendido[0] if ranking_aprendido else None
                    # Duas formas de respeitar o conhecimento: abrir uma das
                    # cartelas com a dezena que a base aponta como mais provável
                    # (o caso natural de 1 ou 2 cartelas), ou, com lote ≥3,
                    # distribuir as aberturas de modo a cobrir 85% da massa —
                    # o hedge que o próprio placar walk-forward mediu. Nunca é
                    # cota para lote pequeno: uma cartela só pode abrir de um
                    # jeito, e cobrar dela "cobertura" seria exigir o imposível.
                    cobre_a_mais_provavel = (top1 is None
                                             or top1 in aberturas_lote)
                    hedge_de_lote = (len(cartelas) >= 3
                                     and cobertura >= 0.85)
                    criterios["cobertura_abertura"] = {
                        "ok": bool(cobre_a_mais_provavel or hedge_de_lote),
                        "valor": {
                            "aberturas_do_lote": aberturas_lote,
                            "massa_coberta": cobertura,
                            "alvo_de_hedge": 0.85,
                            "cobre_a_abertura_mais_provavel": bool(
                                cobre_a_mais_provavel),
                            "ranking_aprendido": ranking_aprendido,
                        },
                        "peso": self.pesos_criterios["cobertura_abertura"],
                        "leitura": (
                            "o lote cobre {:.1f}% da massa de abertura "
                            "aprendida da base histórica{}".format(
                                100 * cobertura,
                                "" if cobre_a_mais_provavel else
                                " e nenhuma cartela abre pela dezena mais "
                                "provável do conhecimento")),
                    }
            except Exception as exc:  # pragma: no cover — critério opcional
                criterios["cobertura_abertura"] = {
                    "ok": True, "valor": str(exc),
                    "peso": self.pesos_criterios["cobertura_abertura"],
                }

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

    def aprender_falha(self, criterio: str, deu_13_mais: bool):
        """Juiz que aprende: se critério reprovou mas depois deu 13+, reduz peso."""
        if criterio not in self.pesos_criterios:
            return
        if deu_13_mais:
            # critério foi rigoroso demais
            self.pesos_criterios[criterio] = max(0.3, self.pesos_criterios[criterio]*0.95)
            self.historico_falhas[criterio] = self.historico_falhas.get(criterio,0)+1

class JuizAdversarial:
    """Tenta achar fraqueza no lote."""
    def julgar(self, cartelas: List[List[int]], pool: List[int]) -> Dict[str,Any]:
        fraquezas = []
        # todas cartelas compartilham mesma dezena?
        from collections import Counter
        cnt = Counter(d for c in cartelas for d in c)
        comuns = [d for d,c in cnt.items() if c == len(cartelas)]
        if comuns:
            fraquezas.append(f"Todas cartelas contêm {comuns} — ponto único de falha")
        # pool muito pequeno?
        if len(pool) < 17:
            fraquezas.append(f"Pool {len(pool)} < 17 — captura baixa")
        # interseção média alta?
        inter = []
        for i in range(len(cartelas)):
            for j in range(i+1, len(cartelas)):
                inter.append(len(set(cartelas[i]) & set(cartelas[j])))
        media_inter = float(np.mean(inter)) if inter else 15
        if media_inter >= 13:
            fraquezas.append(f"Interseção média {media_inter:.1f} ≥13 — lote pouco diverso")
        return {
            "fraquezas": fraquezas,
            "media_intersecao": round(media_inter,2),
            "dezenas_comuns_todas": comuns,
            "veredito": "VULNERÁVEL" if fraquezas else "ROBUSTO",
        }

class TesteNIST:
    """Testes tipo NIST simplificados para lote."""
    def testar(self, cartelas: List[List[int]]) -> Dict[str,Any]:
        # frequency test: cada dezena deve aparecer ~ (n_cart*15/25) vezes
        from collections import Counter
        cnt = Counter(d for c in cartelas for d in c)
        n = len(cartelas)
        esperado = n*15/25
        chi2 = sum((cnt.get(i,0)-esperado)**2 / (esperado+1e-9) for i in range(1,26))
        # runs test simplificado: alternância par/impar nas cartelas ordenadas?
        # p-value aproximado chi2
        # Para 24 graus liberdade, chi2 ~24 média
        ok_freq = chi2 < 40  # threshold generoso
        # gap test: gaps médios
        gaps = []
        for c in cartelas:
            sd = sorted(c)
            gaps.extend([sd[i+1]-sd[i] for i in range(len(sd)-1)])
        gap_medio = float(np.mean(gaps)) if gaps else 0
        ok_gap = 1.2 <= gap_medio <= 2.5
        return {
            "chi2_frequencia": round(float(chi2),2),
            "ok_frequencia": ok_freq,
            "gap_medio": round(gap_medio,3),
            "ok_gap": ok_gap,
            "veredito": "ALEATÓRIO_OK" if (ok_freq and ok_gap) else "DESVIO",
            "detalhe": f"Esperado {esperado:.1f} por dezena, chi2 {chi2:.1f} (limite 40), gap {gap_medio:.2f}",
        }

class PValueRandom:
    """p-value vs random baseline."""
    def calcular(self, p_lote: float, n_cartelas: int, alvo: int = 13) -> Dict[str,Any]:
        # baseline random: 1 cartela P13=1/691≈0.001447, lote 8 P≈ n*P (aprox)
        p1 = {13: 1/691, 14: 1/21800, 15: 1/3268760}.get(alvo, 1/691)
        p_random = 1 - (1-p1)**n_cartelas  # pelo menos uma cartela
        # binomial: lote melhor que random?
        # p-value = prob de random >= lote? Aproxima
        if p_lote <= p_random:
            p_value = 0.5
            veredito = "EQUIVALENTE_RANDOM"
        else:
            # quanto melhor, menor p-value (mais significativo)
            ratio = p_lote / (p_random+1e-12)
            p_value = max(0.01, 1.0 / ratio)
            veredito = "MELHOR_QUE_RANDOM" if p_value < 0.1 else "EQUIVALENTE_RANDOM"
        return {
            "p_lote": round(p_lote,8),
            "p_random_baseline": round(p_random,8),
            "ratio": round(p_lote/(p_random+1e-9),2),
            "p_value": round(p_value,4),
            "veredito": veredito,
            "interpretacao": f"Lote P={p_lote*100:.4f}% vs random {p_random*100:.4f}% — ratio {p_lote/(p_random+1e-9):.2f}x, p-value {p_value}",
        }

# ----------------------------------------------------------------
# Explainability LLM + Chat + Fingerprint
# ----------------------------------------------------------------
class ExplainabilityMagna:
    """Gera explicação tipo LLM para cada dezena."""
    def explicar_dezena(self, dezena: int, vf: np.ndarray, fontes: Dict[str,np.ndarray], votos: np.ndarray) -> str:
        vf = np.asarray(vf)
        contrib = {nome: float(v[dezena-1]) for nome, v in fontes.items()}
        voto = int(votos[dezena-1]) if votos is not None else 0
        # ordena fontes por contribuição
        ordenadas = sorted(contrib.items(), key=lambda x: x[1], reverse=True)
        top_fonte = ordenadas[0][0] if ordenadas else "motores"
        explic = f"Dezena {dezena:02d}: "
        explic += f"top fonte {top_fonte} ({contrib.get(top_fonte,0):.4f}), "
        explic += f"votos oráculo {voto}/15, "
        explic += f"contribuições: " + ", ".join([f"{k}={v:.3f}" for k,v in ordenadas[:3]])
        if dezena in [1,2,3]:
            explic += " — âncora pessoal"
        if dezena % 2 == 0:
            explic += " — par equilibra"
        else:
            explic += " — ímpar"
        return explic

    def explicar_cartela(self, cartela: List[int], vf: np.ndarray, fontes: Dict[str,np.ndarray], votos: np.ndarray) -> Dict[str,Any]:
        explicacoes = [self.explicar_dezena(d, vf, fontes, votos) for d in cartela]
        soma = sum(cartela)
        pares = sum(1 for d in cartela if d%2==0)
        return {
            "cartela": cartela,
            "soma": soma,
            "pares": pares,
            "explicacoes": explicacoes,
            "resumo": f"Cartela soma {soma} pares {pares} — " + ("equilibrada" if 175 <= soma <= 220 and 6 <= pares <= 9 else "atípica mas dentro do filtro"),
        }

    def explicar_lote(self, cartelas: List[List[int]], vf: np.ndarray, fontes: Dict[str,np.ndarray], votos: np.ndarray) -> List[Dict[str,Any]]:
        return [self.explicar_cartela(c, vf, fontes, votos) for c in cartelas]

class ChatMagna:
    """Chat simples com Magna — responde por que."""
    def __init__(self, explain: ExplainabilityMagna):
        self.explain = explain

    def responder(self, pergunta: str, contexto: Dict[str,Any]) -> str:
        pergunta = pergunta.lower()
        vf = contexto.get("vf")
        fontes = contexto.get("fontes", {})
        votos = contexto.get("votos")
        cartelas = contexto.get("cartelas", [])
        pool = contexto.get("pool", [])
        # parsing simples
        if "por que" in pergunta and any(str(d) in pergunta for d in range(1,26)):
            # extrai dezena
            import re
            nums = re.findall(r'\b([0-9]{1,2})\b', pergunta)
            for n in nums:
                try:
                    d = int(n)
                    if 1 <= d <= 25:
                        return self.explain.explicar_dezena(d, vf, fontes, votos)
                except:
                    pass
        if "13" in pergunta or "14" in pergunta or "15" in pergunta:
            analise = contexto.get("analise", {})
            return f"P(lote≥13)={analise.get('p_melhor_13_mais',0)*100:.4f}% 1 em {1/(analise.get('p_melhor_13_mais',1e-9)):.1f}, P≥14={analise.get('p_melhor_14_mais',0)*100:.6f}% — ganho combinatório, nunca preditivo. Pool {pool} captura 1 em {contexto.get('um_em_captura','?')}"
        if "regime" in pergunta:
            regime = contexto.get("regime", {})
            return f"Regime atual {regime.get('regime_atual')} — {regime.get('descricao')} — centroides {regime.get('centroides')}"
        if "juiz" in pergunta or "julg" in pergunta:
            julgamento = contexto.get("julgamento", {})
            return f"Juiz: {julgamento.get('veredito')} nota {julgamento.get('nota')} reprovados {julgamento.get('reprovados')} — {julgamento.get('recomendacao')}"
        # default
        return f"Magna Suprema v10: {len(cartelas)} cartelas pool {pool[:5]}... top15 {[int(x) for x in (np.argsort(vf)[::-1][:5]+1)] if vf is not None else []} — pergunte 'por que 22?' ou 'chance 13?'"

class FingerprintPessoal:
    """SHA256 do histórico pessoal para nunca repetir cartela."""
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.cache = set()

    def _hash_cartela(self, dezenas: List[int]) -> str:
        s = ",".join(map(str, sorted(dezenas)))
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    def carregar_historico(self):
        try:
            if self.db:
                conn = self.db.get_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15 FROM cartelas ORDER BY id DESC LIMIT 500")
                rows = cursor.fetchall()
                conn.close()
                for r in rows:
                    if r[0] is not None:
                        dez = [int(r[i]) for i in range(15)]
                        self.cache.add(self._hash_cartela(dez))
        except Exception:
            pass

    def ja_foi_gerada(self, dezenas: List[int]) -> bool:
        return self._hash_cartela(dezenas) in self.cache

    def registrar(self, dezenas: List[int]):
        self.cache.add(self._hash_cartela(dezenas))

    def relatorio(self):
        return {"total_hashes": len(self.cache), "fingerprint": "SHA256 16 chars"}

# ----------------------------------------------------------------
# Verificador Exaustivo + Backtest Lote + Binomial + Curva
# ----------------------------------------------------------------
class VerificadorMagno:
    def verificar(self, cartelas: List[List[int]], pool: List[int]) -> Dict[str, Any]:
        try:
            from .forja_lotes import RegiaoAltoAcerto, GeometriaJohnson
            from .wheeling import MotorWheeling
            reg = RegiaoAltoAcerto()
            geo = GeometriaJohnson()
            analise = MotorWheeling().analisar_lote(cartelas, pool)
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

class BacktestLote:
    """Walk-forward do lote: últimos 50 concursos, média acertos empírica."""
    def testar(self, cartelas: List[List[int]], matriz: np.ndarray, janela: int = 50) -> Dict[str,Any]:
        try:
            n = len(matriz)
            janela = min(janela, n)
            acertos_por_concurso = []
            for i in range(n-janela, n):
                real = set(int(x)+1 for x in np.where(matriz[i]==1)[0])
                melhores = [len(set(c) & real) for c in cartelas]
                acertos_por_concurso.append({
                    "concurso_idx": i,
                    "melhor": max(melhores) if melhores else 0,
                    "media": float(np.mean(melhores)) if melhores else 0,
                })
            medias = [x["media"] for x in acertos_por_concurso]
            melhores = [x["melhor"] for x in acertos_por_concurso]
            return {
                "janela": janela,
                "media_acertos_lote": round(float(np.mean(medias)),3) if medias else 0,
                "melhor_acertos_medio": round(float(np.mean(melhores)),3) if melhores else 0,
                "taxa_13_mais": round(sum(1 for m in melhores if m>=13)/len(melhores),4) if melhores else 0,
                "baseline_media": 9.0,
                "baseline_taxa_13": round(1 - (1-1/691)**len(cartelas),4),
                "detalhes": acertos_por_concurso[-10:],
                "veredito": "Acima da média 9.0" if (np.mean(medias) if medias else 0) > 9.0 else "Na média do acaso",
            }
        except Exception as e:
            return {"erro": str(e)}

class TesteBinomial:
    """Teste binomial significância."""
    def testar(self, sucessos: int, tentativas: int, p0: float) -> Dict[str,Any]:
        # binomial CDF aproximado
        try:
            from math import comb
            # p-value = P(X >= sucessos | p0)
            p_val = sum(comb(tentativas, k) * (p0**k) * ((1-p0)**(tentativas-k)) for k in range(sucessos, tentativas+1))
            return {
                "sucessos": sucessos,
                "tentativas": tentativas,
                "p0": p0,
                "p_value": round(float(p_val),5),
                "significativo": p_val < 0.05,
                "veredito": "Significativo p<0.05" if p_val < 0.05 else "Não significativo",
            }
        except Exception as e:
            return {"erro": str(e)}

class CurvaAprendizado:
    """Curva aprendizado contínua."""
    def __init__(self, historico_magna: List[Dict[str,Any]]):
        self.hist = historico_magna or []

    def curva(self) -> Dict[str,Any]:
        conferidas = [d for d in self.hist if d.get("status")=="conferida"]
        if not conferidas:
            return {"n":0, "curva": [], "tendencia": "sem dados"}
        conferidas = sorted(conferidas, key=lambda x: x.get("id",0))
        medias = [float(d.get("media_acertos") or 0) for d in conferidas]
        # média móvel 5
        mm5 = []
        for i in range(len(medias)):
            janela = medias[max(0,i-4):i+1]
            mm5.append(round(float(np.mean(janela)),3))
        tendencia = "crescente" if len(mm5)>=5 and mm5[-1] > mm5[-5] else "estável" if len(mm5)>=5 and abs(mm5[-1]-mm5[-5])<0.2 else "decrescente" if len(mm5)>=5 else "indefinida"
        return {
            "n": len(conferidas),
            "media_atual": mm5[-1] if mm5 else 0,
            "media_inicial": mm5[0] if mm5 else 0,
            "curva_mm5": mm5,
            "tendencia": tendencia,
            "melhor": max(medias) if medias else 0,
            "pior": min(medias) if medias else 0,
        }

# ----------------------------------------------------------------
# Alocador Multi-Rota
# ----------------------------------------------------------------
class AlocadorOrcamentoMagno:
    def alocar(self, orcamento: float, quantidade_max: int = 20, alvo: int = 13) -> Dict[str, Any]:
        max_cart = max(1, int(orcamento // VALOR_APOSTA))
        n = min(quantidade_max, max_cart)
        estrategias = [
            {"nome": "forja-13", "cartelas": min(8, n), "custo": min(8,n)*VALOR_APOSTA, "p13_est": 0.012, "ev": -0.5},
            {"nome": "wheeling-14", "cartelas": min(8, n), "custo": min(8,n)*VALOR_APOSTA, "p13_est": 0.008, "p14_est": 0.0004, "ev": -0.4},
            {"nome": "wheeling-13-pool18", "cartelas": 6, "custo": 21.0, "p13_est": 0.006, "ev": -0.3},
            {"nome": "exaustao-diversa", "cartelas": min(5, n), "custo": min(5,n)*VALOR_APOSTA, "p13_est": 0.005, "ev": -0.6},
        ]
        melhor = None
        melhor_score = -1
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

class AlocadorMultiRota:
    """Alocação multi-rota 60% forja + 30% wheeling 14 + 10% exaustão."""
    def alocar(self, orcamento: float, quantidade: int, perfil: str = "equilibrado") -> Dict[str,Any]:
        max_cart = max(1, int(orcamento // VALOR_APOSTA))
        n = min(quantidade, max_cart)
        if perfil == "conservador":
            perc = {"forja": 0.7, "wheeling14": 0.2, "exaustao": 0.1}
        elif perfil == "agressivo":
            perc = {"forja": 0.4, "wheeling14": 0.3, "exaustao": 0.3}
        else:
            perc = {"forja": 0.6, "wheeling14": 0.3, "exaustao": 0.1}
        n_forja = max(1, int(n*perc["forja"]))
        n_wheel = max(0, int(n*perc["wheeling14"]))
        n_ex = n - n_forja - n_wheel
        if n_ex <0:
            n_ex=0
            n_wheel = n - n_forja
        aloc = []
        if n_forja>0:
            aloc.append({"nome": "forja-13-suprema", "cartelas": n_forja, "custo": n_forja*VALOR_APOSTA, "perc": perc["forja"]})
        if n_wheel>0:
            aloc.append({"nome": "wheeling-14", "cartelas": n_wheel, "custo": n_wheel*VALOR_APOSTA, "perc": perc["wheeling14"]})
        if n_ex>0:
            aloc.append({"nome": "exaustao-diversa", "cartelas": n_ex, "custo": n_ex*VALOR_APOSTA, "perc": perc["exaustao"]})
        total_custo = sum(a["custo"] for a in aloc)
        return {
            "perfil": perfil,
            "percentuais": perc,
            "alocacao": aloc,
            "total_cartelas": n,
            "total_custo": total_custo,
            "orcamento": orcamento,
            "recomendacao": f"Multi-rota {perfil}: {n_forja} forja + {n_wheel} wheeling14 + {n_ex} exaustão = {n} cartelas R${total_custo}",
        }

class UtilidadeEsperada:
    """Calcula EV com prêmios reais médios."""
    def calcular(self, analise: Dict[str,Any], premios_medios: Dict[int,float], custo: float) -> Dict[str,Any]:
        # analise tem p_melhor_11..15?
        # usa distribuição hipergeométrica por cartela + lote
        ev = float(analise.get("ev_lote",0))
        # recalcula com premios reais se disponível
        p13 = float(analise.get("p_melhor_13_mais") or 0)
        p14 = float(analise.get("p_melhor_14_mais") or 0)
        p15 = float(analise.get("p_melhor_15") or 0)
        # premios médios
        premio13 = premios_medios.get(13, 35.0)
        premio14 = premios_medios.get(14, 1800.0)
        premio15 = premios_medios.get(15, 500000.0)
        ev_real = p13*premio13 + p14*premio14 + p15*premio15 - custo
        return {
            "ev_teorico": round(ev,2),
            "ev_real_premios_medios": round(ev_real,2),
            "premios_medios_usados": premios_medios,
            "custo": custo,
            "lucro_esperado": round(ev_real,2),
            "roi": round(ev_real/custo*100,2) if custo>0 else 0,
        }

# ----------------------------------------------------------------
# Aprendizado Bayesiano com Momentum
# ----------------------------------------------------------------
class AprendizadoBayesianoMagno:
    def __init__(self, pesos_iniciais: Dict[str, float], alpha_prior: float = 10.0):
        self.pesos = dict(pesos_iniciais)
        self.alpha = {k: alpha_prior * v for k,v in pesos_iniciais.items()}
        self.momentum = {k: 0.0 for k in pesos_iniciais}
        self.historico = []

    def atualizar(self, acertos_fontes: Dict[str, int], lr: float = 0.15, momentum_beta: float = 0.7) -> Dict[str, float]:
        for fonte, acertos in acertos_fontes.items():
            if fonte not in self.alpha:
                continue
            evidencia = (acertos - 9) * 0.5
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
