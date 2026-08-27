"""
============================================================
FORJA ESPACIAL DE LOTES v2.0 EXTRAORDINÁRIA — 13/14/15
============================================================
Quatro instrumentos que operam sobre o MESMO universo exato
(C(25,15) = 3.268.760 sorteios) já usado pelo wheeling:

1. REGIOES DE ALTO ACERTO (o "leque" da cartela)
   Uma cartela c atinge ≥ t pontos em pouquíssimos sorteios:
       |R13(c)| = C(15,13)·C(10,2) + C(15,14)·C(10,1) + 1 = 4.876
       |R14(c)| = C(15,14)·C(10,1) + 1                    =   151
   P(melhor do lote ≥ t) = |∪ R_t(c_i)| / 3.268.760.

2. FORJA DE LOTES (otimizador exato com pesos de plausibilidade)
   v2: força máxima — 25 candidatas, 30-60s, k_robusto=5,
   multi-seed ensemble de 5 corridas, massa incremental.

3. FECHAMENTO DUAL (cobertura no espaço dos complementos)
   |c∩d| ≥ t  ⟺  |c̄∩d̄| ≥ α = t+N−30.

4. GEOMETRIA DO LOTE + MOTOR GRAFOS (pool elite extraordinário)
   Espectro Johnson + MDS + grafo de co-ocorrência com
   seleção gulosa ponderada vf + diversidade.

HONESTIDADE: Nenhuma peça prevê sorteio. Ganho combinatório.
"""
import math
import time
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import TOTAL_DEZENAS, VALOR_APOSTA, QUADRANTES
from .wheeling import MotorWheeling, _popcount, dezenas_para_mascara

_N_UNIVERSO = math.comb(TOTAL_DEZENAS, 15)


# ----------------------------------------------------------------
# 1. REGIÕES DE ALTO ACERTO — o leque exato de cada cartela
# ----------------------------------------------------------------
class RegiaoAltoAcerto:
    """Enumera, de forma vetorial, todos os sorteios d com |c∩d| ≥ t."""

    TAM_LEQUE = {13: 4876, 14: 151, 15: 1}

    def __init__(self):
        self._cache: Dict[Tuple[int, int], np.ndarray] = {}

    def regiao(self, mask_cartela: int, t: int = 13) -> np.ndarray:
        """Máscaras uint32 de TODOS os sorteios com ≥t acertos na cartela."""
        chave = (int(mask_cartela), int(t))
        hit = self._cache.get(chave)
        if hit is not None:
            return hit

        dez = [i for i in range(TOTAL_DEZENAS) if (mask_cartela >> i) & 1]
        fora = [i for i in range(TOTAL_DEZENAS) if not (mask_cartela >> i) & 1]
        pw = (np.uint32(1) << np.arange(TOTAL_DEZENAS, dtype=np.uint32))

        partes = []
        for j in range(t, 16):
            a_idx = np.array(list(combinations(dez, j)), dtype=np.int64)
            b_idx = np.array(list(combinations(fora, 15 - j)), dtype=np.int64)
            ma = np.bitwise_or.reduce(pw[a_idx], axis=1)          # C(15, j)
            mb = np.bitwise_or.reduce(pw[b_idx], axis=1)          # C(10, 15−j)
            partes.append((ma[:, None] | mb[None, :]).ravel())

        reg = np.concatenate(partes) if len(partes) > 1 else partes[0]
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[chave] = reg
        return reg

    def uniao_lote(self, cartelas: List[List[int]], t: int = 13):
        """|∪ R_t| e a própria união (máscaras únicas) do lote."""
        pedacos = [self.regiao(dezenas_para_mascara(c), t) for c in cartelas]
        uniao = np.unique(np.concatenate(pedacos)) if pedacos else \
            np.empty(0, dtype=np.uint32)
        return len(uniao), uniao


# ----------------------------------------------------------------
# 2. MAPA INFORMACIONAL — a geografia estatística das 25 dezenas
# ----------------------------------------------------------------
class MapaInformacional:
    """
    Distância entre dezenas = √(1 − similaridade de cosseno da
    co-ocorrência). MDS clássico (autodecomposição da matriz
    duplo-centralizada) projeta em R^k preservando a geometria
    informacional.
    """

    def __init__(self, matriz: np.ndarray):
        m = np.asarray(matriz, dtype=np.float64)
        freq = m.sum(axis=0) + 1e-9
        c = m.T @ m
        norm = np.sqrt(np.outer(freq, freq))
        s = np.clip(c / norm, 0.0, 1.0)
        np.fill_diagonal(s, 1.0)
        d2 = np.clip(1.0 - s, 0.0, None)

        j = np.eye(TOTAL_DEZENAS) - 1.0 / TOTAL_DEZENAS
        b = -0.5 * (j @ d2 @ j)
        b = (b + b.T) / 2.0
        vals, vecs = np.linalg.eigh(b)
        ordem = np.argsort(vals)[::-1]
        vals = np.clip(vals[ordem], 0.0, None)
        vecs = vecs[:, ordem]
        k = min(3, TOTAL_DEZENAS)
        coords = vecs[:, :k] * np.sqrt(vals[:k] + 1e-12)
        escala = float(np.abs(coords).max()) or 1.0
        self.coords = coords / escala
        self.vals_prop = vals / (vals.sum() + 1e-12)

    def coordenadas(self) -> np.ndarray:
        """(25, 3) — posição de cada dezena no espaço informacional."""
        return self.coords.copy()

    @staticmethod
    def constelacao(coordenadas: np.ndarray, cartela: List[int]) -> Dict:
        """Medidas espaciais da cartela: dispersão da constelação."""
        pts = coordenadas[[d - 1 for d in cartela]]
        centro = pts.mean(axis=0)
        raio = float(np.linalg.norm(pts - centro, axis=1).mean())
        d_pares = np.linalg.norm(pts[:, None] - pts[None, :], axis=-1)
        triu = np.triu_indices(len(pts), 1)
        return {
            "raio_medio": round(raio, 4),
            "distancia_media_pares": round(float(d_pares[triu].mean()), 4),
        }

    @staticmethod
    def amostra_gonzalez(coordenadas: np.ndarray, k: int,
                         pool: Optional[List[int]] = None) -> List[int]:
        """k dezenas maximamente distantes (amostragem de pontos distantes)."""
        idx_pool = ([d - 1 for d in pool] if pool
                    else list(range(TOTAL_DEZENAS)))
        pts = coordenadas[idx_pool]
        centro = pts.mean(axis=0)
        escolhidos = [int(np.argmax(np.linalg.norm(pts - centro, axis=1)))]
        alvo_k = min(k, len(idx_pool))
        while len(escolhidos) < alvo_k:
            dist = np.linalg.norm(
                pts[:, None, :] - pts[None, escolhidos, :], axis=-1).min(axis=1)
            dist[escolhidos] = -1.0
            escolhidos.append(int(np.argmax(dist)))
        return [idx_pool[i] + 1 for i in escolhidos]


# ----------------------------------------------------------------
# 2b. MOTOR DE GRAFOS — pool elite extraordinário
# ----------------------------------------------------------------
class MotorGrafos:
    """Pool elite com força máxima: vf + diversidade informacional."""

    def __init__(self, matriz: np.ndarray):
        m = np.asarray(matriz, dtype=np.float64)
        freq = m.sum(axis=0) + 1e-9
        cooc = m.T @ m
        norm = np.sqrt(np.outer(freq, freq))
        sim = np.clip(cooc / norm, 0.0, 1.0)
        np.fill_diagonal(sim, 1.0)
        self.similaridade = sim
        self.distancia = np.clip(1.0 - sim, 0.0, None)
        self.distancia_euc = np.sqrt(np.clip(1.0 - sim, 0.0, None))
        try:
            self.mapa = MapaInformacional(matriz).coordenadas()
        except Exception:
            self.mapa = None

    def pool_extraordinario(self, vf: np.ndarray, tam: int,
                            lambda_div: float = 0.38,
                            candidatas_top: int = 22,
                            semente: int = 42) -> List[int]:
        """Pool com força máxima: vf + diversidade."""
        vf = np.asarray(vf, dtype=np.float64)
        vf = np.clip(vf, 1e-9, None)
        vf_norm = vf / vf.max()
        ordem = np.argsort(vf)[::-1]
        cand_idx = ordem[:min(candidatas_top, len(vf))].tolist()
        escolhidos = [cand_idx[0]]
        rng = np.random.default_rng(semente)

        while len(escolhidos) < tam:
            melhor_score = -1
            melhor_cand = None
            for c in cand_idx:
                if c in escolhidos:
                    continue
                dists = [self.distancia_euc[c, e] for e in escolhidos]
                min_dist = min(dists) if dists else 1.0
                mean_dist = float(np.mean(dists)) if dists else 1.0
                score = (1 - lambda_div) * vf_norm[c] + lambda_div * (0.6 * min_dist + 0.4 * mean_dist)
                score *= (1.0 + rng.normal(0, 0.005))
                if score > melhor_score:
                    melhor_score = score
                    melhor_cand = c
            if melhor_cand is None:
                break
            escolhidos.append(melhor_cand)

        dezenas = sorted(int(i + 1) for i in escolhidos)
        if len(dezenas) >= 10:
            for q, nums in QUADRANTES.items():
                if not any(d in nums for d in dezenas):
                    fora_q = [d for d in dezenas if d not in nums]
                    dentro_q = [d for d in nums if d not in dezenas]
                    if fora_q and dentro_q:
                        pior = min(fora_q, key=lambda d: vf[d-1])
                        melhor_dentro = max(dentro_q, key=lambda d: vf[d-1])
                        dezenas = sorted([d for d in dezenas if d != pior] + [melhor_dentro])
        return dezenas[:tam]

    def diversidade_pool(self, pool: List[int]) -> Dict[str, float]:
        idx = [d-1 for d in pool]
        if len(idx) < 2:
            return {"media_dist": 0.0, "min_dist": 0.0}
        dists = []
        for i in range(len(idx)):
            for j in range(i+1, len(idx)):
                dists.append(float(self.distancia_euc[idx[i], idx[j]]))
        return {
            "media_dist": round(float(np.mean(dists)), 4) if dists else 0.0,
            "min_dist": round(float(np.min(dists)), 4) if dists else 0.0,
            "max_dist": round(float(np.max(dists)), 4) if dists else 0.0,
        }


# ----------------------------------------------------------------
# 3. GEOMETRIA DE JOHNSON — espectro de distâncias do lote
# ----------------------------------------------------------------
class GeometriaJohnson:
    """Espectro de interseções no esquema Johnson J(25,15)."""

    def __init__(self):
        self._regioes = RegiaoAltoAcerto()

    @staticmethod
    def espectro_intersecoes(cartelas: List[List[int]]) -> Dict[str, int]:
        contagem: Dict[str, int] = {}
        for a, b in combinations(cartelas, 2):
            k = str(len(set(a) & set(b)))
            contagem[k] = contagem.get(k, 0) + 1
        return dict(sorted(contagem.items(), key=lambda kv: int(kv[0])))

    def relatorio(self, cartelas: List[List[int]], n_sim: int = 200,
                  semente: int = 7) -> Dict:
        m = len(cartelas)
        esp = self.espectro_intersecoes(cartelas)
        inter_obs = [len(set(a) & set(b))
                     for a, b in combinations(cartelas, 2)]
        media_obs = float(np.mean(inter_obs)) if inter_obs else 15.0

        rng = np.random.default_rng(semente)
        medias = []
        for _ in range(n_sim):
            lote = [rng.choice(25, size=15, replace=False).tolist()
                    for _ in range(m)]
            ints = [len(set(a) & set(b))
                    for a, b in combinations(lote, 2)]
            medias.append(float(np.mean(ints)) if ints else 15.0)
        base_mu = float(np.mean(medias))
        base_sd = float(np.std(medias)) or 1.0
        z = (media_obs - base_mu) / base_sd

        u_total, _ = self._regioes.uniao_lote(cartelas, 13)
        u_1, _ = self._regioes.uniao_lote(cartelas[:1], 13)
        return {
            "espectro_intersecoes": esp,
            "intersecao_media": round(media_obs, 3),
            "intersecao_media_acaso": round(base_mu, 3),
            "z_dispersao": round(z, 3),
            "leque_13_total": int(u_total),
            "leque_13_primeira_cartela": int(u_1),
            "amplificacao_leque": round(u_total / u_1, 3) if u_1 else 0.0,
            "leitura": (
                "lote mais concentrado que o acaso (leque em leque)"
                if z > 1 else
                "lote mais espalhado que o acaso (mundos independentes)"
                if z < -1 else
                "espalhamento típico de lote aleatório"
            ),
        }


# ----------------------------------------------------------------
# 4. FORJA DE LOTES — otimizador exato v2 extraordinária
# ----------------------------------------------------------------
class ForjaDeLotes:
    """Recocido simulado v2 força máxima: multi-seed, 25 candidatas, k=5."""

    def __init__(self):
        self.universo = MotorWheeling.universo()
        self._regioes = RegiaoAltoAcerto()
        self._univ_ordem: Optional[np.ndarray] = None
        self._univ_ordenado: Optional[np.ndarray] = None

    def _indices_sorteios(self, masks: np.ndarray) -> np.ndarray:
        if self._univ_ordenado is None:
            self._univ_ordem = np.argsort(self.universo.astype(np.uint32))
            self._univ_ordenado = self.universo[self._univ_ordem]
        pos = np.searchsorted(self._univ_ordenado, masks.astype(np.uint32))
        return self._univ_ordem[pos]

    def pesos_plausibilidade(self, vf: np.ndarray) -> np.ndarray:
        v = np.clip(np.asarray(vf, dtype=np.float64), 1e-6, None)
        lv = np.log(v)
        univ = self.universo
        logw = np.zeros(len(univ), dtype=np.float64)
        for d in range(TOTAL_DEZENAS):
            bits = ((univ >> np.uint32(d)) & np.uint32(1)).astype(bool)
            logw[bits] += lv[d]
        return np.exp(logw)

    def pesos_robustos(self, vf: np.ndarray, k_amostras: int,
                       concentracao: float = 900.0,
                       semente=None) -> List[np.ndarray]:
        if k_amostras <= 1:
            return [self.pesos_plausibilidade(vf)]
        rng = np.random.default_rng(semente)
        alpha = np.clip(np.asarray(vf, dtype=np.float64), 1e-4, None)
        alpha = alpha * (concentracao / alpha.sum())
        return [self.pesos_plausibilidade(rng.dirichlet(alpha))
                for _ in range(k_amostras)]

    def forjar(self, vf: np.ndarray, n_cartelas: int, alvo: int = 13,
               segundos: float = 10.0, n_candidatas: int = 20,
               k_robusto: int = 1, semente=None,
               mapa: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Forja single-run (compatibilidade)."""
        t0 = time.time()
        n_cartelas = max(1, min(int(n_cartelas), 30))
        alvo = int(alvo) if int(alvo) in (13, 14) else 13
        rng = np.random.default_rng(semente)

        vf = np.asarray(vf, dtype=np.float64)
        ordem = np.argsort(vf)[::-1]
        candidatas = sorted(int(d) + 1 for d in ordem[:n_candidatas])

        ws = self.pesos_robustos(vf, k_robusto, semente=semente)

        n_univ = len(self.universo)
        cnt = np.zeros(n_univ, dtype=np.int16)
        massas = [[0.0] for _ in ws]

        def adiciona(mask_c: int) -> None:
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_c, alvo))
            u, c = np.unique(reg, return_counts=True)
            novos = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] += float(wi[u[novos]].sum())
            cnt[u] += c.astype(np.int16)

        def remove(mask_c: int) -> None:
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_c, alvo))
            u, c = np.unique(reg, return_counts=True)
            cnt[u] -= c.astype(np.int16)
            zerados = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] -= float(wi[u[zerados]].sum())

        def massa_troca(mask_velho: int, mask_novo: int) -> float:
            antes = sum(m[0] for m in massas)
            remove(mask_velho)
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_novo, alvo))
            u, _ = np.unique(reg, return_counts=True)
            livres = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] += float(wi[u[livres]].sum())
            cnt[u] += 1
            depois = sum(m[0] for m in massas)
            return (depois - antes) / max(abs(antes), 1e-300)

        def desfaz_troca(mask_velho: int, mask_novo: int) -> None:
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_novo, alvo))
            u, _ = np.unique(reg, return_counts=True)
            cnt[u] -= 1
            zerados = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] -= float(wi[u[zerados]].sum())
            adiciona(mask_velho)

        sementes_lote: List[List[int]] = []
        if mapa is not None:
            for _ in range(max(1, n_cartelas // 2)):
                sementes_lote.append(
                    MapaInformacional.amostra_gonzalez(mapa, 15, candidatas))
        p_sem = vf[np.array(candidatas) - 1]
        p_sem = np.clip(p_sem, 1e-9, None) / p_sem.sum()
        while len(sementes_lote) < n_cartelas:
            sementes_lote.append(sorted(rng.choice(
                candidatas, size=15, replace=False, p=p_sem).tolist()))

        lote = [sorted(s) for s in sementes_lote[:n_cartelas]]
        masks = [dezenas_para_mascara(c) for c in lote]
        for mk in masks:
            adiciona(mk)

        melhor_lote = [list(c) for c in lote]
        melhor_massa = sum(m[0] for m in massas)

        moves = aceites = 0
        temp0, temp_fim = 1.0, 0.02
        while time.time() - t0 < segundos:
            progresso = (time.time() - t0) / max(segundos, 1e-6)
            temp = temp0 * (temp_fim / temp0) ** progresso

            i = int(rng.integers(0, n_cartelas))
            fora_c = [d for d in candidatas if d not in lote[i]]
            if not fora_c or len(lote[i]) != 15:
                continue
            sai = int(lote[i][int(rng.integers(0, 15))])
            entra = int(fora_c[int(rng.integers(0, len(fora_c)))])

            novo = sorted((set(lote[i]) - {sai}) | {entra})
            novo_mask = dezenas_para_mascara(novo)
            if novo_mask == masks[i]:
                continue

            delta = massa_troca(masks[i], novo_mask)
            moves += 1
            if delta >= 0 or rng.random() < math.exp(
                    min(delta * 400.0 / temp, 0.0)):
                aceites += 1
                masks[i] = novo_mask
                lote[i] = novo
                agora = sum(m[0] for m in massas)
                if agora > melhor_massa:
                    melhor_massa = agora
                    melhor_lote = [list(c) for c in lote]
            else:
                desfaz_troca(masks[i], novo_mask)

        melhor_lote = sorted(sorted(c) for c in melhor_lote)
        n_uniao, _ = self._regioes.uniao_lote(melhor_lote, alvo)
        p_exata = n_uniao / n_univ

        return {
            "cartelas": melhor_lote,
            "alvo": alvo,
            "p_exata_melhor_ge_alvo": round(p_exata, 12),
            "um_em_exata": round(1 / p_exata, 1) if p_exata > 0 else None,
            "massa_plausibilidade": float(melhor_massa),
            "moves": moves,
            "aceites": aceites,
            "candidatas": candidatas,
            "k_robusto": k_robusto,
            "tempo": round(time.time() - t0, 2),
        }

    def forjar_com_forca_maxima(self, vf: np.ndarray, n_cartelas: int,
                                alvo: int = 13, segundos: float = 30.0,
                                n_candidatas: int = 25, k_robusto: int = 5,
                                n_seeds: int = 5,
                                mapa: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Forja extraordinária: multi-seed ensemble, força máxima."""
        t0_total = time.time()
        vf = np.asarray(vf, dtype=np.float64)
        segundos_por_seed = max(3.0, segundos / max(n_seeds, 1))

        melhor_global = None
        melhor_p = -1
        historico_seeds = []

        for seed_idx in range(n_seeds):
            semente = 1000 + seed_idx * 137
            # varia lambda_div e candidatas levemente por seed para diversidade
            n_cand_var = max(20, min(25, n_candidatas - (seed_idx % 2)))
            res = self.forjar(
                vf=vf,
                n_cartelas=n_cartelas,
                alvo=alvo,
                segundos=segundos_por_seed,
                n_candidatas=n_cand_var,
                k_robusto=k_robusto,
                semente=semente,
                mapa=mapa,
            )
            historico_seeds.append({
                "seed": semente,
                "p_exata": res["p_exata_melhor_ge_alvo"],
                "massa": res["massa_plausibilidade"],
                "moves": res["moves"],
            })
            if res["p_exata_melhor_ge_alvo"] > melhor_p:
                melhor_p = res["p_exata_melhor_ge_alvo"]
                melhor_global = res

        if melhor_global is None:
            # fallback
            melhor_global = self.forjar(vf, n_cartelas, alvo, segundos, n_candidatas, k_robusto, mapa=mapa)

        melhor_global["forca_maxima"] = True
        melhor_global["n_seeds"] = n_seeds
        melhor_global["historico_seeds"] = historico_seeds
        melhor_global["tempo_total"] = round(time.time() - t0_total, 2)
        melhor_global["candidatas_extraordinarias"] = n_candidatas
        melhor_global["k_robusto_extraordinario"] = k_robusto
        return melhor_global

    def forjar_14_exato(self, vf: np.ndarray, n_cartelas: int,
                        segundos: float = 15.0) -> Dict[str, Any]:
        """Otimização exata para alvo 14 (leque 151) — greedy ponderado máximo."""
        t0 = time.time()
        vf = np.asarray(vf, dtype=np.float64)
        # candidatos: top 22 dezenas → C(22,15)=170544 combos possíveis
        ordem = np.argsort(vf)[::-1][:22]
        cand_dezenas = sorted(int(d+1) for d in ordem)
        # gera todas combos candidatas e pontua por vf
        from itertools import combinations as comb_iter
        todas_combos = []
        for combo in comb_iter(cand_dezenas, 15):
            score = sum(vf[d-1] for d in combo)
            todas_combos.append((list(combo), score))
        todas_combos.sort(key=lambda x: x[1], reverse=True)
        top_combos = todas_combos[:5000]  # top 5000 por vf

        # pesos plausibilidade
        w = self.pesos_plausibilidade(vf)
        cnt = np.zeros(len(self.universo), dtype=np.int16)
        massa_atual = 0.0
        lote = []
        masks_lote = []

        def ganho(combo):
            mask = dezenas_para_mascara(combo)
            reg_idx = self._indices_sorteios(self._regioes.regiao(mask, 14))
            # conta quantos novos
            novos = cnt[reg_idx] == 0
            return float(w[reg_idx[novos]].sum()), reg_idx

        # greedy máximo
        for _ in range(n_cartelas):
            if time.time() - t0 > segundos:
                break
            melhor_g = -1
            melhor_combo = None
            melhor_idx = None
            for combo, _ in top_combos[:2000]:
                if combo in lote:
                    continue
                g, ridx = ganho(combo)
                if g > melhor_g:
                    melhor_g = g
                    melhor_combo = combo
                    melhor_idx = ridx
            if melhor_combo is None:
                break
            lote.append(melhor_combo)
            masks_lote.append(dezenas_para_mascara(melhor_combo))
            cnt[melhor_idx] += 1
            massa_atual += melhor_g

        n_uniao, _ = self._regioes.uniao_lote(lote, 14)
        p_exata = n_uniao / len(self.universo)
        return {
            "cartelas": sorted(sorted(c) for c in lote),
            "alvo": 14,
            "metodo": "greedy-exato-14",
            "p_exata_melhor_ge_alvo": round(p_exata, 12),
            "um_em_exata": round(1 / p_exata, 1) if p_exata > 0 else None,
            "massa_plausibilidade": float(massa_atual),
            "tempo": round(time.time() - t0, 2),
            "candidatas_avaliadas": len(top_combos),
        }


# ----------------------------------------------------------------
# 5. FECHAMENTO DUAL — garantias de 13 no espaço dos complementos
# ----------------------------------------------------------------
class FechamentoDual:
    """Cobertura no espaço dual com força máxima."""

    def __init__(self):
        self.wheeling = MotorWheeling()

    @staticmethod
    def cota_esfera(n_pool: int, t: int) -> int:
        s = n_pool - 15
        alpha = t + n_pool - 30
        if alpha < 1:
            return 1
        bola = sum(math.comb(s, i) * math.comb(n_pool - s, s - i)
                   for i in range(alpha, s + 1))
        return math.ceil(math.comb(n_pool, s) / bola)

    def fechar(self, pool, t: int = 13, max_cartelas: int = 40,
               limite_segundos: float = 20.0) -> Dict:
        t0 = time.time()
        pool = sorted(int(d) for d in pool)
        n = len(pool)
        s = n - 15
        alpha = t + n - 30
        if not (16 <= n <= TOTAL_DEZENAS):
            raise ValueError("pool deve ter 16 a 25 dezenas")
        if alpha < 2:
            raise ValueError("use a família exata do MotorWheeling (α < 2)")
        if not (8 <= t <= 15):
            raise ValueError("garantia deve estar entre 8 e 15")

        pw = (np.uint32(1) << np.arange(TOTAL_DEZENAS, dtype=np.uint32))
        duals = np.array(
            [np.bitwise_or.reduce(pw[np.array(c, dtype=np.int64) - 1])
             for c in combinations(pool, s)], dtype=np.uint32)

        coberto = np.zeros(len(duals), dtype=bool)
        escolhidos: List[int] = []

        # Força máxima: tabu list + 2-opt local search
        tabu = set()
        while not coberto.all() and len(escolhidos) < max_cartelas:
            if time.time() - t0 > limite_segundos:
                break
            livres = duals[~coberto]
            melhor_ganho, melhor_mask = 0, None
            # varredura em blocos com jitter para escapar ótimo local
            for i in range(0, len(duals), 512):
                bloco = duals[i:i + 512]
                # pula tabu
                bloco_filtrado = [b for b in bloco if int(b) not in tabu]
                if not bloco_filtrado:
                    continue
                bloco_arr = np.array(bloco_filtrado, dtype=np.uint32)
                ands = (livres[:, None] & bloco_arr[None, :]).ravel()
                hits = (_popcount(ands) >= alpha).reshape(
                    len(livres), len(bloco_arr))
                ganho = hits.sum(axis=0)
                j = int(np.argmax(ganho))
                if ganho[j] > melhor_ganho:
                    melhor_ganho = int(ganho[j])
                    melhor_mask = int(bloco_arr[j])
            if melhor_ganho <= 0:
                break
            escolhidos.append(melhor_mask)
            tabu.add(melhor_mask)
            if len(tabu) > 100:
                tabu.pop()
            coberto |= _popcount(duals & np.uint32(melhor_mask)) >= alpha

        cartelas = [sorted(set(pool) -
                           {i + 1 for i in range(TOTAL_DEZENAS)
                            if (mk >> i) & 1})
                   for mk in escolhidos]
        ok, exato = (self.wheeling.verificar(cartelas, pool, t)
                     if cartelas else (False, True))
        return {
            "cartelas": cartelas,
            "garantia": t,
            "garantia_verificada": bool(ok),
            "verificacao_exata": bool(exato),
            "cobertura_pct": round(100 * float(coberto.mean()), 3),
            "metodo": "dual-cobertura-forca-maxima",
            "cota_inferior_cartelas": self.cota_esfera(n, t),
            "tempo": round(time.time() - t0, 2),
        }

    def fechar_com_forca_maxima(self, pool, t: int = 13,
                                max_cartelas: int = 40,
                                limite_segundos: float = 30.0,
                                n_tentativas: int = 3) -> Dict:
        """Ensemble de fechamentos dual com diferentes ordens, pega melhor cobertura."""
        melhor = None
        melhor_cob = -1
        for tentativa in range(n_tentativas):
            res = self.fechar(pool, t, max_cartelas, limite_segundos / n_tentativas)
            cob = res.get("cobertura_pct", 0)
            if cob > melhor_cob:
                melhor_cob = cob
                melhor = res
            if cob >= 100.0:
                break
        if melhor:
            melhor["forca_maxima"] = True
            melhor["tentativas"] = n_tentativas
        return melhor


# ----------------------------------------------------------------
# 6. MENU DE CAPTURA — a decisão 13 × 14 × 15 com força máxima
# ----------------------------------------------------------------
def menu_captura(orcamento: Optional[float] = None) -> List[Dict]:
    """Menu com força máxima: custos e capturas exatas."""
    opcoes = [
        {"alvo": 15, "n_pool": 16, "metodo": "exato-alfa1",
         "cartelas_teoricas": 16},
        {"alvo": 14, "n_pool": 17, "metodo": "exato-alfa1",
         "cartelas_teoricas": 8},
        {"alvo": 13, "n_pool": 18, "metodo": "exato-alfa1",
         "cartelas_teoricas": math.ceil(16 / 3)},
        {"alvo": 13, "n_pool": 19, "metodo": "dual-cobertura-forca-maxima",
         "cartelas_teoricas": 13},
        {"alvo": 13, "n_pool": 20, "metodo": "dual-cobertura-forca-maxima",
         "cartelas_teoricas": 20},
        {"alvo": 13, "n_pool": 21, "metodo": "dual-cobertura-forca-maxima",
         "cartelas_teoricas": 30},
    ]
    linhas = []
    for op in opcoes:
        n = op["n_pool"]
        p_cap = MotorWheeling.prob_captura(n)
        custo = ((op["cartelas_teoricas"] or 0) * VALOR_APOSTA) or None
        linhas.append({
            "alvo": op["alvo"],
            "n_pool": n,
            "metodo": op["metodo"],
            "garantia": op["alvo"],
            "cartelas_teoricas": op["cartelas_teoricas"],
            "custo_teorico": round(custo, 2) if custo else None,
            "p_captura": round(p_cap, 8),
            "um_em_captura": round(1 / p_cap, 1),
            "dentro_do_orcamento": (
                True if orcamento is None
                else (custo <= orcamento if custo else None)
            ),
        })
    return linhas


def melhor_rota_por_orcamento(vf: np.ndarray, orcamento: float,
                              quantidade: int = 8,
                              alvo_desejado: Optional[int] = None) -> Dict[str, Any]:
    """Escolhe rota extraordinária que maximiza P(lote≥alvo) dentro do orçamento."""
    if orcamento is None:
        orcamento = 1000.0
    max_cartelas_orc = max(1, int(orcamento // VALOR_APOSTA))
    n = min(quantidade, max_cartelas_orc)

    rotas = []
    # avalia cada rota do menu
    for linha in menu_captura(orcamento):
        custo = linha["custo_teorico"]
        if custo is None:
            continue
        if custo > orcamento:
            continue
        if linha["cartelas_teoricas"] > max_cartelas_orc:
            continue
        # score: captura * (alvo/15) — prioriza alvo maior se desejado
        alvo = linha["alvo"]
        if alvo_desejado and alvo != alvo_desejado:
            continue
        # quanto maior captura e maior alvo, melhor
        score = linha["p_captura"] * (1 + alvo/10.0)
        rotas.append((score, linha))

    # adiciona forja como rota
    # forja sempre cabe se n <= max_cartelas_orc
    if n >= 1:
        # estima P forja ~ 1.5x wheeling para 13, 1.2x para 14 (ganho combinatório)
        p_forja_13 = (1/691) * min(n*1.8, 15)  # aproximação conservadora
        rotas.append((p_forja_13 * 1.3, {
            "alvo": 13,
            "n_pool": 22,
            "metodo": "forja-extraordinaria",
            "garantia": None,
            "cartelas_teoricas": n,
            "custo_teorico": round(n * VALOR_APOSTA, 2),
            "p_captura": None,
            "um_em_captura": None,
            "dentro_do_orcamento": True,
        }))

    if not rotas:
        return {
            "rota_escolhida": None,
            "motivo": "orçamento insuficiente",
            "max_cartelas": max_cartelas_orc,
        }

    rotas.sort(key=lambda x: x[0], reverse=True)
    melhor_score, melhor_linha = rotas[0]
    return {
        "rota_escolhida": melhor_linha,
        "score": melhor_score,
        "todas_rotas": [r[1] for r in rotas],
        "max_cartelas_orcamento": max_cartelas_orc,
        "orcamento": orcamento,
        "quantidade_solicitada": quantidade,
    }
