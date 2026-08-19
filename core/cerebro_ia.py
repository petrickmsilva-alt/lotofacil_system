"""
============================================================
CÉREBRO IA v6.0 — MÓDULO ÚNICO E COMPLETO
Unificação de: agente_autonomo.py + ciclo_autonomo.py + ia_autonoma.py
A IA é o protagonista absoluto:
  → Lê dados sozinha
  → Treina 14 módulos internamente
  → Opera em ciclo fechado (Geração → Conferência → Aprendizado)
  → Gera as melhores cartelas de forma 100% autônoma
============================================================
"""
import os
import sqlite3
import numpy as np
import json
import time
import threading
import itertools
import requests
import joblib
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from config import (
    DATABASE_PATH, TOTAL_DEZENAS, DEZENAS_POR_JOGO,
    PRIMOS, FIBONACCI, BORDA, QUADRANTES,
    VALOR_APOSTA, MODELS_PATH,
)
from database.db_manager import DBManager


# ============================================================
# BLOCO 1 — INGESTÃO DE DADOS (Alimentador Quântico)
# ============================================================
class IngestorDados:
    """
    A IA se alimenta sozinha.
    Lê o banco, converte em matriz binária de 25 bits,
    e busca novos resultados da Caixa automaticamente.
    """
    URL_BASE      = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    URL_CONCURSO  = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"
    HEADERS       = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer":    "https://loterias.caixa.gov.br/",
        "Accept":     "application/json",
    }

    def __init__(self, db_path: str):
        self.db_path = db_path

    def carregar_matriz(self) -> Tuple[np.ndarray, list]:
        """
        Lê o banco e retorna:
        - matriz binária N×25 (1 = dezena sorteada)
        - lista raw dos registros
        """
        if not os.path.exists(self.db_path):
            return np.zeros((1, 25), dtype=np.float32), []

        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                       d11,d12,d13,d14,d15
                FROM resultados ORDER BY concurso ASC
            """)
            rows   = cursor.fetchall()
            cursor.execute("SELECT * FROM resultados ORDER BY concurso ASC")
            raw    = cursor.fetchall()
            conn.close()

            if not rows:
                return np.zeros((1, 25), dtype=np.float32), []

            matriz = np.zeros((len(rows), 25), dtype=np.float32)
            for i, linha in enumerate(rows):
                for d in linha:
                    v = int(d)
                    if 1 <= v <= 25:
                        matriz[i][v - 1] = 1.0

            return matriz, raw

        except Exception as e:
            print("[INGESTOR] Erro: {}".format(e))
            return np.zeros((1, 25), dtype=np.float32), []

    def buscar_ultimo_caixa(self) -> Optional[Dict]:
        try:
            r = requests.get(self.URL_BASE, headers=self.HEADERS, timeout=15)
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    def buscar_concurso_caixa(self, numero: int) -> Optional[Dict]:
        try:
            r = requests.get(
                self.URL_CONCURSO.format(numero),
                headers=self.HEADERS, timeout=15
            )
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    def extrair_dezenas(self, data: Dict) -> List[int]:
        try:
            return sorted([int(d) for d in data.get("listaDezenas", [])])
        except Exception:
            return []

    def extrair_premios(self, data: Dict) -> Dict[int, float]:
        p = {11: 7.0, 12: 14.0, 13: 35.0, 14: 0.0, 15: 0.0}
        try:
            for item in data.get("listaRateioPremio", []):
                ac  = int(item.get("numeroAcertos", 0))
                val = item.get("valorPremio", 0)
                if isinstance(val, str):
                    val = float(
                        val.replace("R$","").replace(".","")
                           .replace(",",".").strip()
                    )
                if ac in p and float(val) > 0:
                    p[ac] = float(val)
        except Exception:
            pass
        return p


# ============================================================
# BLOCO 2 — 14 MOTORES ANALÍTICOS INTERNOS
# ============================================================

class _Motor:
    """Base dos motores analíticos"""
    def score_vetor(self) -> np.ndarray:
        return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


class MotorFrequencia(_Motor):
    """Módulos 1 e 2 — Frequência global e recente"""
    def __init__(self, matriz: np.ndarray):
        n = len(matriz)
        freq_g        = np.sum(matriz, axis=0)
        self._global  = freq_g / (freq_g.sum() + 1e-9)
        jan           = min(30, n)
        freq_r        = np.sum(matriz[-jan:], axis=0)
        self._recente = freq_r / (freq_r.sum() + 1e-9)

    def score_global(self)  -> np.ndarray: return self._global.copy()
    def score_recente(self) -> np.ndarray: return self._recente.copy()


class MotorReversao(_Motor):
    """Módulo 3 — Reversão à média estocástica"""
    def __init__(self, matriz: np.ndarray):
        n     = len(matriz)
        jan   = min(30, n)
        fg    = np.sum(matriz, axis=0) / max(n, 1)
        fr    = np.sum(matriz[-jan:], axis=0)
        esp   = jan * (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        v     = np.zeros(TOTAL_DEZENAS)
        for i in range(TOTAL_DEZENAS):
            if   fr[i] > esp * 1.5: v[i] = fg[i] * 0.60
            elif fr[i] < esp * 0.6: v[i] = fg[i] * 1.50
            else:                    v[i] = fg[i]
        s = v.sum()
        self._v = v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_vetor(self) -> np.ndarray: return self._v.copy()


class MotorAntiLogica(_Motor):
    """
    Módulo 4 — Anti-Lógica
    Saturação + Atraso + FFT + Correlação de pares
    """
    def __init__(self, matriz: np.ndarray):
        self._matriz = matriz
        self._n      = len(matriz)

    def _saturacao(self, janela: int = 20) -> np.ndarray:
        if self._n < janela:
            return np.zeros(TOTAL_DEZENAS)
        r   = self._matriz[-janela:]
        fr  = np.sum(r, axis=0)
        esp = janela * (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        return (fr - esp) / (esp + 1e-9)

    def _atraso(self) -> np.ndarray:
        a = np.zeros(TOTAL_DEZENAS)
        for d in range(TOTAL_DEZENAS):
            for i in range(self._n - 1, -1, -1):
                if self._matriz[i][d] == 1:
                    a[d] = (self._n - 1) - i
                    break
            else:
                a[d] = self._n
        m = a.max()
        return a / m if m > 0 else a

    def _fft(self, periodo: int = 60) -> np.ndarray:
        sc = np.zeros(TOTAL_DEZENAS)
        for d in range(TOTAL_DEZENAS):
            s = self._matriz[-periodo:, d].astype(float)
            if len(s) < 10: continue
            f = np.abs(np.fft.rfft(s))
            if f.max() > 0: sc[d] = float(f[1:].max() / f.max())
        return sc

    def _correlacao_isolamento(self) -> np.ndarray:
        if self._n < 20:
            return np.zeros(TOTAL_DEZENAS)
        try:
            c = np.nan_to_num(np.corrcoef(self._matriz.T), nan=0.0)
            con = np.abs(c).mean(axis=1)
            m   = con.max()
            return 1.0 - (con / m if m > 0 else con)
        except Exception:
            return np.zeros(TOTAL_DEZENAS)

    def score_vetor(self, base: np.ndarray) -> np.ndarray:
        sat  = self._saturacao(20)
        atr  = self._atraso()
        fft  = self._fft(60)
        isol = self._correlacao_isolamento()
        p    = base.copy()
        for i in range(TOTAL_DEZENAS):
            if sat[i]  > 0.40: p[i] *= 0.65
            if atr[i]  > 0.60: p[i] *= 1.45
            if fft[i]  > 0.50: p[i] *= 1.25
            p[i] *= (1.0 + isol[i] * 0.15)
        s = p.sum()
        return p / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


class MotorMarkov(_Motor):
    """Módulo 5 — Cadeias de Markov modificadas"""
    def __init__(self, matriz: np.ndarray):
        N     = TOTAL_DEZENAS
        trans = np.ones((N, N))
        n     = len(matriz)
        for i in range(1, n):
            ant = np.where(matriz[i - 1] == 1)[0]
            atu = np.where(matriz[i]     == 1)[0]
            for a in ant:
                for b in atu:
                    trans[a][b] += 1
        ls = trans.sum(axis=1, keepdims=True)
        ls[ls == 0] = 1
        self._trans  = trans / ls
        self._ultimo = matriz[-1] if n > 0 else np.zeros(N)

    def score_vetor(self) -> np.ndarray:
        ant  = np.where(self._ultimo == 1)[0]
        prob = np.zeros(TOTAL_DEZENAS)
        for d in ant:
            prob += self._trans[d]
        s = prob.sum()
        return prob / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_jogo(self, dezenas: List[int]) -> float:
        prob = self.score_vetor()
        return float(np.mean([prob[d - 1] for d in dezenas]))


class MotorQuantum(_Motor):
    """Módulo 6 — Passeios Quânticos"""
    def __init__(self, matriz: np.ndarray):
        self._prob = self._treinar(matriz)

    def _passo(self, au, ad):
        s  = 1.0 / np.sqrt(2)
        nu = s * au + s * ad
        nd = s * au - s * ad
        return np.roll(nu, 1), np.roll(nd, -1)

    def _caminhada(self, dezenas: List[int], passos: int = 120) -> np.ndarray:
        N  = TOTAL_DEZENAS
        au = np.zeros(N, dtype=complex)
        ad = np.zeros(N, dtype=complex)
        for d in dezenas:
            if 1 <= d <= N:
                au[d - 1] = 1.0 / np.sqrt(2)
                ad[d - 1] = 1.0j / np.sqrt(2)
        for _ in range(passos):
            au, ad = self._passo(au, ad)
        prob = np.abs(au) ** 2 + np.abs(ad) ** 2
        s    = prob.sum()
        return prob / s if s > 0 else np.ones(N) / N

    def _treinar(self, matriz: np.ndarray) -> np.ndarray:
        n   = len(matriz)
        acc = np.zeros(TOTAL_DEZENAS)
        jan = min(n - 1, 80)
        for i in range(n - jan, n - 1):
            dez = list(np.where(matriz[i] == 1)[0] + 1)
            acc += self._caminhada(dez, passos=80)
        s = acc.sum()
        return acc / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_vetor(self) -> np.ndarray: return self._prob.copy()


class MotorVerlet(_Motor):
    """Módulo 7 — Simulador Verlet 3D das bolas físicas"""
    RAIO_G = 0.20; RAIO_B = 0.025; MASSA = 0.066
    COEF   = 0.82; GRAV   = 9.78;  DENS  = 1.20

    def __init__(self, freq_hist: np.ndarray, n_sims: int = 2):
        self._scores = self._treinar(freq_hist, n_sims)

    def _simular(self, n_passos: int = 600) -> np.ndarray:
        N   = TOTAL_DEZENAS
        rng = np.random.default_rng(int(time.time()) % 10000)
        pos = np.zeros((N, 3)); vel = np.zeros((N, 3))
        for i in range(N):
            while True:
                p = rng.uniform(-0.15, 0.15, 3)
                if np.linalg.norm(p) < 0.15: pos[i] = p; break
            vel[i] = rng.normal(0, 0.8, 3)
        zona = np.array([0.0, 0.0, self.RAIO_G * 0.85])
        cnt  = np.zeros(N)
        gv   = np.array([0.0, 0.0, -self.GRAV])
        dt   = 5e-4
        for passo in range(n_passos):
            acc = np.zeros((N, 3))
            for i in range(N):
                sp = np.linalg.norm(vel[i])
                fd = np.zeros(3)
                if sp > 1e-6:
                    fd = -0.5 * self.DENS * sp**2 * 0.47 * \
                         np.pi * self.RAIO_B**2 * vel[i] / sp
                acc[i] = gv + fd / self.MASSA + rng.normal(0, 0.001, 3)
            vel += acc * dt; pos += vel * dt
            for i in range(N):
                d = np.linalg.norm(pos[i])
                lim = self.RAIO_G - self.RAIO_B
                if d > lim and d > 1e-9:
                    nh = pos[i] / d
                    vn = np.dot(vel[i], nh)
                    if vn > 0: vel[i] -= (1 + self.COEF) * vn * nh
                    pos[i] = nh * lim
            if passo > n_passos * 0.3:
                for i in range(N):
                    if np.linalg.norm(pos[i] - zona) < self.RAIO_B * 2.5:
                        cnt[i] += 1
        s = cnt.sum()
        return cnt / s if s > 0 else np.ones(N) / N

    def _treinar(self, freq: np.ndarray, n: int) -> np.ndarray:
        acc = np.zeros(TOTAL_DEZENAS)
        for _ in range(n): acc += self._simular(500)
        acc /= n
        fh  = freq.copy()
        if fh.max()  > 0: fh  /= fh.max()
        if acc.max() > 0: acc /= acc.max()
        v = fh * 0.65 + acc * 0.35
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_vetor(self) -> np.ndarray: return self._scores.copy()
    def score_jogo(self, dez: List[int]) -> float:
        return float(np.mean([self._scores[d - 1] for d in dez]))


class MotorEstatistica(_Motor):
    """
    Módulos 8, 9, 10 — Chi², Bayes+Bernoulli, KL Divergência
    """
    def __init__(self, matriz: np.ndarray):
        self._matriz      = matriz
        self._n           = len(matriz)
        self.freq_obs     = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.scores_chi2  = np.ones(TOTAL_DEZENAS) * 0.5
        self.prior_bayes  = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.mat_bayes    = np.ones((TOTAL_DEZENAS, TOTAL_DEZENAS)) / \
                            TOTAL_DEZENAS
        self._calcular_chi2()
        self._calcular_bayes()

    def _calcular_chi2(self):
        obs = np.sum(self._matriz, axis=0)
        esp = np.ones(TOTAL_DEZENAS) * \
              (self._n * DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        res = (obs - esp) / np.sqrt(esp + 1e-9)
        res = np.clip(res, -3, 3)
        mn  = res.min(); mx = res.max()
        self.scores_chi2 = (res - mn) / (mx - mn + 1e-9)
        self.freq_obs    = obs / (obs.sum() + 1e-9)

    def _calcular_bayes(self):
        N   = TOTAL_DEZENAS
        cnt = np.ones((N, N))
        tot = np.ones(N) * N
        for i in range(self._n - 1):
            ant = set(np.where(self._matriz[i]     == 1)[0])
            prx = set(np.where(self._matriz[i + 1] == 1)[0])
            for a in ant:
                tot[a] += 1
                for b in prx: cnt[a][b] += 1
        self.mat_bayes   = cnt / tot[:, np.newaxis]
        freq = np.sum(self._matriz, axis=0)
        self.prior_bayes = (freq + 1) / (self._n + N)

    def posterior_bayes(self, dezenas_ant: List[int]) -> np.ndarray:
        lp = np.log(self.prior_bayes + 1e-9)
        for d in dezenas_ant:
            if 1 <= d <= TOTAL_DEZENAS:
                lp += np.log(self.mat_bayes[d - 1] + 1e-9)
        lp -= lp.max()
        p   = np.exp(lp)
        s   = p.sum()
        return p / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_kl(self, dezenas: List[int]) -> float:
        dist = np.zeros(TOTAL_DEZENAS)
        for d in dezenas:
            if 1 <= d <= TOTAL_DEZENAS: dist[d - 1] = 1.0
        dist /= (dist.sum() + 1e-9)
        q = self.freq_obs + 1e-9
        p = dist + 1e-9
        kl = float(np.sum(p * np.log(p / q)))
        return max(0.0, 1.0 - kl / np.log(TOTAL_DEZENAS))

    def score_vetor(self) -> np.ndarray: return self.scores_chi2.copy()


class MotorGaussiano(_Motor):
    """Módulo 11 — Filtros Gaussianos calibrados pelo histórico"""
    def __init__(self, matriz: np.ndarray):
        self._calibrar(matriz)

    def _calibrar(self, matriz: np.ndarray):
        somas = pares_l = primos_l = fib_l = borda_l = None
        somas   = []
        pares_l = []
        primos_l = []
        fib_l   = []
        borda_l = []
        for i in range(len(matriz)):
            dez = list(np.where(matriz[i] == 1)[0] + 1)
            if len(dez) != 15: continue
            somas.append(sum(dez))
            pares_l.append(sum(1 for d in dez if d % 2 == 0))
            primos_l.append(len(set(dez) & PRIMOS))
            fib_l.append(len(set(dez) & FIBONACCI))
            borda_l.append(len(set(dez) & BORDA))

        def pct(arr, lo=3, hi=97):
            a = sorted(arr) if arr else [0, 25]
            n = len(a)
            return (a[max(0, int(n*lo/100))],
                    a[min(n-1, int(n*hi/100))])

        self.SOMA_MIN,   self.SOMA_MAX   = pct(somas)    if somas   else (175, 230)
        self.PARES_MIN,  self.PARES_MAX  = pct(pares_l)  if pares_l else (6,   9)
        self.PRIMOS_MIN, self.PRIMOS_MAX = pct(primos_l) if primos_l else (3,   7)
        self.FIB_MIN,    self.FIB_MAX    = pct(fib_l)    if fib_l   else (2,   6)
        self.BORDA_MIN,  self.BORDA_MAX  = pct(borda_l)  if borda_l else (7,  11)
        self.CONSEC_MAX  = 5

    def filtrar(self, dez: List[int]) -> Tuple[bool, Dict]:
        ds   = set(dez); soma = sum(dez)
        pares = sum(1 for d in dez if d % 2 == 0)
        sd   = sorted(dez); mc = cc = 1
        for i in range(1, len(sd)):
            if sd[i] == sd[i-1] + 1: cc += 1; mc = max(mc, cc)
            else: cc = 1
        pc = len(ds & PRIMOS); fc = len(ds & FIBONACCI); bc = len(ds & BORDA)
        det = {"soma": soma, "pares": pares, "primos": pc,
               "fibonacci": fc, "borda": bc, "consec": mc}
        ok = (self.SOMA_MIN  <= soma  <= self.SOMA_MAX  and
              self.PARES_MIN <= pares <= self.PARES_MAX and
              mc <= self.CONSEC_MAX and
              self.PRIMOS_MIN <= pc  <= self.PRIMOS_MAX and
              self.FIB_MIN   <= fc  <= self.FIB_MAX    and
              self.BORDA_MIN <= bc  <= self.BORDA_MAX)
        return ok, det

    def score_vetor(self) -> np.ndarray:
        v = np.zeros(TOTAL_DEZENAS)
        for i in range(TOTAL_DEZENAS):
            d = i + 1
            s = 0.5
            if d in PRIMOS:    s += 0.05
            if d in FIBONACCI: s += 0.05
            if d in BORDA:     s += 0.03
            v[i] = s
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


class MotorGenetico(_Motor):
    """Módulo 12 — Algoritmo Genético de Ilhas"""
    def __init__(self, n_ilhas=4, tam=50, geracoes=60):
        self.n_ilhas  = n_ilhas
        self.tam      = tam
        self.geracoes = geracoes

    def _ind(self, rng, cands: List[int]) -> List[int]:
        return sorted(rng.choice(cands, size=min(15, len(cands)),
                                  replace=False).tolist())

    def _cross(self, p1, p2, rng) -> List[int]:
        u = list(set(p1) | set(p2))
        if len(u) < 15:
            ext = [d for d in range(1, 26) if d not in u]
            u  += list(rng.choice(ext, size=15-len(u), replace=False))
        cnt = {}
        for d in p1 + p2: cnt[d] = cnt.get(d, 0) + 1
        u.sort(key=lambda x: -cnt.get(x, 0))
        return sorted(u[:15])

    def _mut(self, ind, rng, taxa=0.05) -> List[int]:
        ind = list(ind)
        for i in range(len(ind)):
            if rng.random() < taxa:
                disp = [d for d in range(1, 26) if d not in ind]
                if disp: ind[i] = int(rng.choice(disp))
        uniq = sorted(set(ind))
        while len(uniq) < 15:
            disp = [d for d in range(1, 26) if d not in uniq]
            if disp: uniq.append(int(rng.choice(disp)))
        return sorted(uniq[:15])

    def evoluir(
        self, fn_fitness, cands: List[int], timeout: float = 15.0
    ) -> List[Tuple[List[int], float]]:
        t0   = time.time()
        rngs = [np.random.default_rng(i * 37 + 13)
                for i in range(self.n_ilhas)]
        ilhas = [[self._ind(rngs[k], cands) for _ in range(self.tam)]
                 for k in range(self.n_ilhas)]
        fits  = [[fn_fitness(ind) for ind in ilha] for ilha in ilhas]
        melhor_f = -np.inf; melhor_i = []
        for g in range(self.geracoes):
            if time.time() - t0 > timeout: break
            for k in range(self.n_ilhas):
                nova = []
                idx_e = sorted(range(len(fits[k])),
                                key=lambda x: fits[k][x], reverse=True)[:3]
                for ie in idx_e: nova.append(list(ilhas[k][ie]))
                while len(nova) < self.tam:
                    try:
                        i1 = int(rngs[k].integers(0, len(ilhas[k])))
                        i2 = int(rngs[k].integers(0, len(ilhas[k])))
                        f  = self._cross(ilhas[k][i1], ilhas[k][i2], rngs[k])
                        f  = self._mut(f, rngs[k],
                                        taxa=0.05*(1-g/self.geracoes))
                        if len(f) == 15: nova.append(f)
                    except Exception: continue
                ilhas[k] = nova[:self.tam]
                fits[k]  = [fn_fitness(ind) for ind in ilhas[k]]
                idx_m    = int(np.argmax(fits[k]))
                if fits[k][idx_m] > melhor_f:
                    melhor_f = fits[k][idx_m]; melhor_i = list(ilhas[k][idx_m])
            if (g+1) % 10 == 0:
                for i in range(self.n_ilhas):
                    prox = (i+1) % self.n_ilhas
                    top  = sorted(range(len(fits[i])),
                                   key=lambda x: fits[i][x],
                                   reverse=True)[:3]
                    bot  = sorted(range(len(fits[prox])),
                                   key=lambda x: fits[prox][x])[:3]
                    for j in range(3):
                        ilhas[prox][bot[j]] = list(ilhas[i][top[j]])
        todos = []
        for ilha, fit in zip(ilhas, fits):
            for ind, f in zip(ilha, fit):
                todos.append((list(ind), float(f)))
        todos.sort(key=lambda x: x[1], reverse=True)
        vistos = set(); unicos = []
        for ind, f in todos:
            k = tuple(sorted(ind))
            if k not in vistos: vistos.add(k); unicos.append((ind, f))
        return unicos[:50]


class MotorCobertura(_Motor):
    """Módulo 13 — Covering Designs matemáticos"""
    def calcular(
        self, cartelas: List[List[int]],
        universo: List[int], pontos: int = 13
    ) -> Dict[str, Any]:
        uni = sorted(universo)[:min(len(universo), 19)]
        total = cobertos = 0
        for res in itertools.combinations(uni, 15):
            sr = set(res); total += 1
            for c in cartelas:
                if len(set(c) & sr) >= pontos:
                    cobertos += 1; break
        cob = cobertos / total if total > 0 else 0.0
        return {"cobertura": round(cob, 4), "cobertos": cobertos,
                "total": total, "pontos": pontos}


class MotorStacking(_Motor):
    """Módulo 14 — Meta-aprendizado (Stacking)"""
    def __init__(self):
        self._historico: List[Dict] = []

    def registrar(self, pesos: Dict, acertos: int):
        self._historico.append({"pesos": dict(pesos), "acertos": acertos})
        if len(self._historico) > 200:
            self._historico = self._historico[-200:]

    def score_vetor(
        self, vetores: Dict[str, np.ndarray]
    ) -> np.ndarray:
        if not self._historico:
            return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        v = np.zeros(TOTAL_DEZENAS)
        for entrada in self._historico[-50:]:
            ac = entrada["acertos"]
            ps = entrada["pesos"]
            for mod, peso in ps.items():
                if mod in vetores:
                    v += vetores[mod] * peso * (ac / 15.0)
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


# ============================================================
# BLOCO 3 — OTIMIZADOR SPSA
# ============================================================
class OtimizadorSPSA:
    """Calibra automaticamente os pesos dos 14 módulos"""
    def __init__(self, n_iter: int = 25):
        self.n_iter = n_iter

    def otimizar(
        self,
        fn_perda,
        pesos_iniciais: Dict[str, float],
    ) -> Dict[str, float]:
        nomes = list(pesos_iniciais.keys())
        theta = np.array([pesos_iniciais[k] for k in nomes], dtype=float)
        rng   = np.random.default_rng(42)
        melhor_theta = theta.copy()
        melhor_loss  = fn_perda(dict(zip(nomes, theta.tolist())))

        for k in range(self.n_iter):
            ak    = 0.15 / (k + 1 + 10) ** 0.602
            ck    = 0.05 / (k + 1) ** 0.101
            delta = rng.choice([-1.0, 1.0], size=len(theta))
            tp    = np.clip(theta + ck * delta, 0.01, 0.5)
            tn    = np.clip(theta - ck * delta, 0.01, 0.5)
            lp    = fn_perda(dict(zip(nomes, (tp/tp.sum()).tolist())))
            ln    = fn_perda(dict(zip(nomes, (tn/tn.sum()).tolist())))
            ghat  = (lp - ln) / (2 * ck * delta + 1e-9)
            theta -= ak * ghat
            theta  = np.clip(theta, 0.01, 0.5)
            lc     = fn_perda(dict(zip(nomes, (theta/theta.sum()).tolist())))
            if lc < melhor_loss:
                melhor_loss  = lc
                melhor_theta = theta.copy()

        melhor_theta = np.clip(melhor_theta, 0.01, None)
        melhor_theta /= melhor_theta.sum()
        return {nomes[i]: round(float(melhor_theta[i]), 4)
                for i in range(len(nomes))}


# ============================================================
# BLOCO 4 — CÉREBRO IA (PROTAGONISTA ÚNICO)
# ============================================================
class CerebroIA:
    """
    A IA que assume a cabine de comando.
    Único módulo responsável por TUDO:
    - Leitura de dados
    - Treinamento dos 14 motores
    - Geração das cartelas
    - Ciclo fechado (Geração → Conferência → Aprendizado)
    - Persistência e memória de erros
    """

    # Pesos iniciais dos 14 módulos
    _PESOS_DEFAULT = {
        "freq_global":  0.07,
        "freq_recente": 0.07,
        "reversao":     0.09,
        "anti_logica":  0.11,
        "markov":       0.11,
        "quantum":      0.08,
        "verlet":       0.07,
        "chi2":         0.07,
        "bayes":        0.08,
        "kl":           0.05,
        "gaussiano":    0.05,
        "genetico":     0.05,
        "cobertura":    0.04,
        "stacking":     0.06,
    }

    URL_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    HEADERS  = {
        "User-Agent": "Mozilla/5.0",
        "Referer":    "https://loterias.caixa.gov.br/",
        "Accept":     "application/json",
    }

    def __init__(self, db_path: str = None, n_cartelas: int = 10):
        self.db_path     = db_path or DATABASE_PATH
        self.db          = DBManager()
        self.n_cartelas  = n_cartelas
        self.pesos       = dict(self._PESOS_DEFAULT)
        self.log: List[Dict] = []
        self.estado      = "inicializando"
        self.metricas    = {}
        self.decisoes    = {}
        self.ultima_exec = None
        self.treinado    = False

        # Ciclo autônomo
        self._rodando    = False
        self._pausado    = False
        self._thread     = None
        self._ciclos_ok  = 0
        self._ciclos_err = 0
        self._ultimo_processado = 0
        self.proximo_sorteio    = None

        # Carregar dados
        self._ingestor = IngestorDados(self.db_path)
        self.matriz, self.raw = self._ingestor.carregar_matriz()
        self.n = len(self.matriz)
        self._log("INIT", "{} concursos carregados".format(self.n))

        # Motores (instanciados no treino)
        self._motores: Dict[str, Any] = {}
        self._vetores: Dict[str, np.ndarray] = {
            k: np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
            for k in self.pesos
        }

        # Motor cobertura e stacking sempre presentes
        self._cobertura = MotorCobertura()
        self._stacking  = MotorStacking()
        self._genetico  = MotorGenetico(n_ilhas=4, tam=50, geracoes=60)
        self._spsa      = OtimizadorSPSA(n_iter=25)
        self._gaussiano = MotorGaussiano(self.matriz)

        # Criar tabelas extras do ciclo
        self._criar_tabelas_ciclo()
        self._ultimo_processado = self._get_ultimo_processado()
        self.estado = "pronto"

    # =========================================================
    # BANCO DE DADOS DO CICLO
    # =========================================================
    def _criar_tabelas_ciclo(self):
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fila_conferencia (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso_alvo         INTEGER,
                dezenas               TEXT,
                timestamp_geracao     TEXT,
                scores_modulos        TEXT,
                score_total           REAL,
                status                TEXT DEFAULT 'aguardando',
                acertos               INTEGER DEFAULT 0,
                premio_ganho          REAL DEFAULT 0,
                dezenas_acertadas     TEXT,
                timestamp_conferencia TEXT,
                erro_previsao         REAL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_ciclos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso         INTEGER,
                timestamp_inicio TEXT,
                timestamp_fim    TEXT,
                status           TEXT,
                n_cartelas       INTEGER DEFAULT 0,
                melhor_acertos   INTEGER DEFAULT 0,
                media_acertos    REAL DEFAULT 0,
                total_ganho      REAL DEFAULT 0,
                pesos_antes      TEXT,
                pesos_depois     TEXT,
                log_ciclo        TEXT,
                erro_medio       REAL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memoria_erros (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso    INTEGER,
                timestamp   TEXT,
                modulo      TEXT,
                erro        REAL,
                impacto     REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS desempenho_modulos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso    INTEGER,
                timestamp   TEXT,
                modulo      TEXT,
                correlacao  REAL,
                peso_antes  REAL,
                peso_depois REAL
            )
        """)
        conn.commit()
        conn.close()

    def _get_ultimo_processado(self) -> int:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(concurso) FROM historico_ciclos
                WHERE status = 'completo'
            """)
            r = cursor.fetchone()[0]
            conn.close()
            return r or 0
        except Exception:
            return 0

    # =========================================================
    # TREINO DOS 14 MÓDULOS
    # =========================================================
    def treinar(self, callback=None) -> Dict:
        """Treina todos os 14 módulos internamente"""
        self.estado = "treinando"
        t0 = time.time()

        # Recarregar dados atualizados
        self.matriz, self.raw = self._ingestor.carregar_matriz()
        self.n = len(self.matriz)

        def cb(msg):
            self._log("TREINO", msg)
            if callback: callback(msg)

        cb("Treinando 14 módulos com {} concursos...".format(self.n))

        freq_g = np.sum(self.matriz, axis=0)
        freq_g_norm = freq_g / (freq_g.sum() + 1e-9)

        # 1. Frequência Global
        cb("1/14 Frequência Global")
        m1 = MotorFrequencia(self.matriz)
        self._vetores["freq_global"]  = m1.score_global()
        self._vetores["freq_recente"] = m1.score_recente()
        self._motores["frequencia"]   = m1

        # 2. Frequência Recente (já feito acima)
        cb("2/14 Frequência Recente")

        # 3. Reversão à Média
        cb("3/14 Reversão à Média Estocástica")
        m3 = MotorReversao(self.matriz)
        self._vetores["reversao"] = m3.score_vetor()
        self._motores["reversao"] = m3

        # 4. Anti-Lógica
        cb("4/14 Anti-Lógica (Saturação + Atraso + FFT)")
        m4 = MotorAntiLogica(self.matriz)
        self._vetores["anti_logica"] = m4.score_vetor(
            self._vetores["reversao"]
        )
        self._motores["anti_logica"] = m4

        # 5. Markov
        cb("5/14 Markov Engine")
        m5 = MotorMarkov(self.matriz)
        self._vetores["markov"] = m5.score_vetor()
        self._motores["markov"] = m5

        # 6. Quantum Walk
        cb("6/14 Quantum Walk")
        m6 = MotorQuantum(self.matriz)
        self._vetores["quantum"] = m6.score_vetor()
        self._motores["quantum"] = m6

        # 7. Verlet 3D
        cb("7/14 Simulador Verlet 3D")
        m7 = MotorVerlet(freq_g_norm, n_sims=2)
        self._vetores["verlet"] = m7.score_vetor()
        self._motores["verlet"] = m7

        # 8, 9, 10. Estatística (Chi², Bayes, KL)
        cb("8/14 Chi-Quadrado | 9/14 Bayes | 10/14 KL")
        m8 = MotorEstatistica(self.matriz)
        self._vetores["chi2"]  = m8.score_vetor()
        ult_dez = list(np.where(self.matriz[-1] == 1)[0] + 1) \
                  if self.n > 0 else list(range(1, 16))
        self._vetores["bayes"] = m8.posterior_bayes(ult_dez)
        kl_v = np.array([m8.score_kl([i + 1])
                          for i in range(TOTAL_DEZENAS)])
        s = kl_v.sum()
        self._vetores["kl"] = kl_v / s if s > 0 else \
                               np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self._motores["estatistica"] = m8

        # 11. Gaussiano
        cb("11/14 Filtros Gaussianos")
        self._gaussiano = MotorGaussiano(self.matriz)
        self._vetores["gaussiano"] = self._gaussiano.score_vetor()

        # 12. Genético (vetor = anti_logica como base)
        cb("12/14 Algoritmo Genético de Ilhas")
        self._vetores["genetico"] = self._vetores["anti_logica"].copy()

        # 13. Cobertura
        cb("13/14 Cobertura Matemática")
        self._vetores["cobertura"] = freq_g_norm.copy()

        # 14. Stacking
        cb("14/14 Meta-Aprendizado (Stacking)")
        self._vetores["stacking"] = self._stacking.score_vetor(
            self._vetores
        )

        # SPSA — Calibrar pesos
        cb("SPSA: Calibrando pesos...")
        self._calibrar_spsa()

        self.treinado    = True
        self.estado      = "pronto"
        self.ultima_exec = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tempo = time.time() - t0
        self.metricas["tempo_treino"] = round(tempo, 2)
        cb("✅ 14 módulos treinados em {:.1f}s".format(tempo))
        return {"status": "ok", "modulos": 14, "tempo": round(tempo, 2)}

    def _calibrar_spsa(self):
        def perda(pesos_dict):
            v = np.zeros(TOTAL_DEZENAS)
            for k, p in pesos_dict.items():
                v += self._vetores.get(k, np.ones(TOTAL_DEZENAS)/TOTAL_DEZENAS) * p
            s = v.sum()
            v = v / s if s > 0 else v
            ent = -np.sum(v * np.log(v + 1e-9))
            return float(-ent)
        self.pesos = self._spsa.otimizar(perda, self.pesos)
        self._log("SPSA", "Pesos calibrados: {}".format(
            {k: round(v, 3) for k, v in self.pesos.items()}
        ))

    # =========================================================
    # VETOR FINAL COMBINADO
    # =========================================================
    def _vetor_combinado(self) -> np.ndarray:
        v = np.zeros(TOTAL_DEZENAS)
        for k, p in self.pesos.items():
            v += self._vetores.get(
                k, np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
            ) * p
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    # =========================================================
    # SCORE COMPLETO DE UMA CARTELA
    # =========================================================
    def _score_cartela(
        self,
        dez: List[int],
        vf: np.ndarray,
        outras: List[List[int]],
    ) -> float:
        ev    = float(sum(vf[d - 1] for d in dez))
        div   = len(set(dez) - set(d2 for o in outras for d2 in o)) / 15.0 \
                if outras else 1.0
        m_est = self._motores.get("estatistica")
        kl    = m_est.score_kl(dez) if m_est else 0.5
        m_mk  = self._motores.get("markov")
        mk    = m_mk.score_jogo(dez) if m_mk else 0.5
        m_vl  = self._motores.get("verlet")
        vl    = m_vl.score_jogo(dez) if m_vl else 0.5
        _, det = self._gaussiano.filtrar(dez)
        soma   = det.get("soma", 200)
        centro = (self._gaussiano.SOMA_MIN + self._gaussiano.SOMA_MAX) / 2
        denom  = max(centro - self._gaussiano.SOMA_MIN, 1)
        sg     = max(0.0, 1.0 - abs(soma - centro) / denom)
        return (ev*0.25 + div*0.20 + kl*0.12 + mk*0.15 +
                vl*0.10 + sg*0.06 + 0.12)

    # =========================================================
    # GERADOR PRINCIPAL DE CARTELAS
    # =========================================================
    def gerar_cartelas(
        self,
        quantidade: int = None,
        modo: str = "hibrido",
        callback=None,
    ) -> List[Dict[str, Any]]:
        """
        ÚNICO método de geração de cartelas do sistema.
        Pipeline completo dos 14 módulos.
        """
        qtd = quantidade or self.n_cartelas
        self.estado = "gerando"
        t0 = time.time()

        def cb(msg):
            self._log("GERAR", msg)
            if callback: callback(msg)

        cb("Pipeline iniciado | qtd={} modo={}".format(qtd, modo))

        # Treinar se necessário
        if not self.treinado:
            cb("Treinando módulos antes de gerar...")
            self.treinar(callback=callback)

        # Vetor final
        vf   = self._vetor_combinado()
        top5 = list(np.argsort(vf)[::-1][:5] + 1)
        self._log("VETOR", "Top 5: {}".format(top5))

        # Grupo elite
        tam_elite   = min(19, 15 + qtd // 2)
        grupo_elite = self._selecionar_elite(vf, tam_elite)
        self.decisoes["grupo_elite"] = sorted(grupo_elite)
        cb("Grupo elite: {}".format(sorted(grupo_elite)))

        # Algoritmo Genético
        cb("Algoritmo Genético de Ilhas...")
        cands_ag = []
        try:
            def fitness(dez):
                ok, _ = self._gaussiano.filtrar(dez)
                ev    = float(sum(vf[d - 1] for d in dez))
                return ev * (1.5 if ok else 0.5)
            top_ag   = self._genetico.evoluir(fitness, grupo_elite, 15.0)
            cands_ag = [i for i, _ in top_ag[:qtd * 3]]
            cb("AG: {} candidatas".format(len(cands_ag)))
        except Exception as e:
            self._log("AVISO", "AG: {}".format(e))

        # Monte Carlo
        cb("Monte Carlo ponderado...")
        cands_mc = self._monte_carlo(grupo_elite, vf, qtd * 4)

        # Combinatório
        cb("Combinatório...")
        cands_cb = self._combinatorio(grupo_elite, vf, qtd * 2)

        todas = cands_ag + cands_mc + cands_cb
        cb("Total candidatas: {}".format(len(todas)))

        # Filtrar e rankear
        cb("Aplicando 14 filtros e calculando scores...")
        aprovadas = []; reprov = 0; vistas = set(); outras = []
        for cand in todas:
            key = tuple(sorted(cand))
            if key in vistas: continue
            vistas.add(key)
            ok, det = self._gaussiano.filtrar(cand)
            if ok:
                sc = self._score_cartela(cand, vf, outras)
                outras.append(cand)
                aprovadas.append({
                    "dezenas":    sorted(cand),
                    "score_total": round(sc, 6),
                    "soma":       det["soma"],
                    "pares":      det["pares"],
                    "primos":     det["primos"],
                    "fibonacci":  det["fibonacci"],
                    "borda":      det["borda"],
                    "scores": {
                        "ev_prob":   round(float(sum(vf[d-1] for d in cand)), 4),
                        "markov":    round(
                            self._motores["markov"].score_jogo(cand)
                            if "markov" in self._motores else 0.5, 4),
                        "verlet":    round(
                            self._motores["verlet"].score_jogo(cand)
                            if "verlet" in self._motores else 0.5, 4),
                        "gaussiano": round(
                            max(0.0, 1.0 - abs(det["soma"] - 200) / 50), 4),
                    },
                })
            else:
                reprov += 1

        # Fallback
        if len(aprovadas) < qtd:
            extras = self._fallback(vf, grupo_elite, qtd - len(aprovadas))
            for e in extras:
                _, det = self._gaussiano.filtrar(e)
                sc = self._score_cartela(e, vf, outras)
                aprovadas.append({
                    "dezenas":    sorted(e),
                    "score_total": round(sc, 6),
                    "soma":       det.get("soma", 0),
                    "pares":      det.get("pares", 0),
                    "primos":     det.get("primos", 0),
                    "fibonacci":  det.get("fibonacci", 0),
                    "borda":      det.get("borda", 0),
                    "scores":     {},
                })

        aprovadas.sort(key=lambda x: x["score_total"], reverse=True)
        resultado = aprovadas[:qtd]

        # Cobertura matemática
        if resultado:
            try:
                listas = [c["dezenas"] for c in resultado]
                cob    = self._cobertura.calcular(listas, grupo_elite, 13)
                for c in resultado:
                    c["cobertura_13"] = cob["cobertura"]
                self.metricas["cobertura_13"] = cob["cobertura"]
                cb("Cobertura 13pts: {:.1%}".format(cob["cobertura"]))
            except Exception as e:
                self._log("AVISO", "Cobertura: {}".format(e))

        # Metadados
        tempo = time.time() - t0
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for i, c in enumerate(resultado):
            c.update({
                "id_geracao":  i + 1,
                "timestamp":   ts,
                "modo":        modo,
                "grupo_elite": sorted(grupo_elite),
                "n_modulos":   14,
                "pesos_usados": dict(self.pesos),
            })

        self.metricas.update({
            "total_geradas":    len(resultado),
            "candidatas_total": len(todas),
            "reprovadas":       reprov,
            "tempo_seg":        round(tempo, 2),
        })

        self.estado      = "pronto"
        self.ultima_exec = ts
        cb("✅ {} cartelas em {:.1f}s | reprovadas: {}".format(
            len(resultado), tempo, reprov
        ))
        return resultado

    # =========================================================
    # GERADORES AUXILIARES
    # =========================================================
    def _selecionar_elite(self, v: np.ndarray, tam: int) -> List[int]:
        ranking = list(np.argsort(v)[::-1] + 1)
        grupo   = []
        for d in ranking:
            if len(grupo) >= tam: break
            if len(grupo) >= 10:
                dist = {q: 0 for q in QUADRANTES}
                for dz in grupo + [d]:
                    for q, nums in QUADRANTES.items():
                        if dz in nums: dist[q] += 1; break
                if any(val == 0 for val in dist.values()): continue
            grupo.append(d)
        for d in ranking:
            if len(grupo) >= tam: break
            if d not in grupo: grupo.append(d)
        return grupo[:tam]

    def _monte_carlo(self, cands, v, n) -> List[List[int]]:
        pesos = np.array([float(v[d-1]) for d in cands])
        pesos = np.clip(pesos, 0.001, None) / pesos.sum()
        res   = []
        for _ in range(n * 6):
            if len(res) >= n: break
            try:
                idx  = np.random.choice(len(cands), 15, replace=False, p=pesos)
                cand = sorted([cands[i] for i in idx])
                res.append(cand)
            except Exception: continue
        return res[:n]

    def _combinatorio(self, cands, v, n) -> List[List[int]]:
        c = sorted(cands)[:19]
        combos = sorted(
            list(itertools.combinations(c, 15)),
            key=lambda x: sum(v[d-1] for d in x), reverse=True
        )
        return [list(co) for co in combos[:n]]

    def _fallback(self, v, elite, n) -> List[List[int]]:
        res   = []
        pesos = np.array([float(v[d-1]) for d in elite])
        pesos = np.clip(pesos, 0.001, None) / pesos.sum()
        for _ in range(n * 30):
            if len(res) >= n: break
            try:
                idx  = np.random.choice(len(elite), 15, replace=False, p=pesos)
                cand = sorted([elite[i] for i in idx])
                soma = sum(cand)
                par  = sum(1 for d in cand if d % 2 == 0)
                if 165 <= soma <= 240 and 4 <= par <= 11:
                    res.append(cand)
            except Exception: continue
        return res[:n]

    # =========================================================
    # CICLO FECHADO — GERAÇÃO → CONFERÊNCIA → APRENDIZADO
    # =========================================================
    def executar_ciclo(self, concurso: int) -> Dict:
        """Ciclo completo autônomo para um concurso"""
        t0 = time.time()
        self._log("CICLO", "=== CICLO {} ===".format(concurso))
        pesos_antes = dict(self.pesos)

        # Registrar início
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO historico_ciclos
            (concurso, timestamp_inicio, status, pesos_antes)
            VALUES (?,?,?,?)
        """, (concurso,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "em_andamento",
              json.dumps(pesos_antes)))
        ciclo_id = cursor.lastrowid
        conn.commit()
        conn.close()

        resultado = {
            "ciclo_id": ciclo_id, "concurso": concurso,
            "status": "erro", "geracao": {}, "conferencia": {},
            "aprendizado": {}
        }

        try:
            # FASE 1: GERAÇÃO
            proximo    = concurso + 1
            cartelas   = self.gerar_cartelas(self.n_cartelas)
            self._salvar_fila(proximo, cartelas)
            resultado["geracao"] = {"n_cartelas": len(cartelas), "concurso_alvo": proximo}

            # Buscar resultado
            data_json = self._ingestor.buscar_concurso_caixa(concurso)
            if not data_json:
                raise Exception("Resultado {} não disponível".format(concurso))

            dezenas_reais = self._ingestor.extrair_dezenas(data_json)
            premios_reais = self._ingestor.extrair_premios(data_json)
            if len(dezenas_reais) != 15:
                raise Exception("Dezenas inválidas: {}".format(dezenas_reais))

            self._salvar_resultado_banco(concurso, data_json,
                                          dezenas_reais, premios_reais)

            # FASE 2: CONFERÊNCIA
            conf = self._conferir(proximo, dezenas_reais, premios_reais)
            resultado["conferencia"] = conf

            # FASE 3: APRENDIZADO
            aprd = self._aprender(concurso, conf, dezenas_reais, cartelas)
            resultado["aprendizado"] = aprd
            resultado["status"]      = "completo"
            self._ciclos_ok         += 1
            self._ultimo_processado  = concurso

        except Exception as e:
            self._log("ERRO", "Ciclo {}: {}".format(concurso, e))
            resultado["erro"]    = str(e)
            resultado["status"]  = "erro"
            self._ciclos_err    += 1

        # Finalizar
        tempo = time.time() - t0
        conn  = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historico_ciclos SET
                timestamp_fim   = ?,
                status          = ?,
                n_cartelas      = ?,
                melhor_acertos  = ?,
                media_acertos   = ?,
                total_ganho     = ?,
                pesos_depois    = ?,
                log_ciclo       = ?
            WHERE id = ?
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            resultado["status"],
            resultado.get("geracao", {}).get("n_cartelas", 0),
            resultado.get("conferencia", {}).get("melhor_acertos", 0),
            resultado.get("conferencia", {}).get("media_acertos",  0),
            resultado.get("conferencia", {}).get("total_ganho",    0),
            json.dumps(dict(self.pesos)),
            "Ciclo em {:.1f}s".format(tempo),
            ciclo_id,
        ))
        conn.commit()
        conn.close()

        self._log("CICLO", "=== FIM {} | {:.1f}s ===".format(
            concurso, tempo
        ))
        return resultado

    def _salvar_fila(self, concurso: int, cartelas: List[Dict]):
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        for c in cartelas:
            try:
                cursor.execute("""
                    INSERT INTO fila_conferencia
                    (concurso_alvo, dezenas, timestamp_geracao,
                     scores_modulos, score_total, status)
                    VALUES (?,?,?,?,?,?)
                """, (
                    concurso,
                    json.dumps(c["dezenas"]),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    json.dumps(c.get("scores", {})),
                    float(c.get("score_total", 0)),
                    "aguardando",
                ))
                dez = c["dezenas"]
                if len(dez) == 15:
                    cursor.execute("""
                        INSERT INTO cartelas
                        (data_geracao, concurso_alvo,
                         d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                         d11,d12,d13,d14,d15,
                         bitmask,score_ia,score_markov,
                         score_fisico,score_entropia,score_total)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                                ?,?,?,?,?,?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        concurso, *dez, 0,
                        float(c.get("score_total", 0)),
                        float(c.get("scores",{}).get("markov", 0)),
                        float(c.get("scores",{}).get("verlet", 0)),
                        float(c.get("scores",{}).get("ev_prob",0)),
                        float(c.get("score_total", 0)),
                    ))
            except Exception as e:
                self._log("AVISO", "Fila: {}".format(e))
        conn.commit()
        conn.close()

    def _conferir(
        self,
        concurso: int,
        dezenas_reais: List[int],
        premios: Dict[int, float],
    ) -> Dict:
        set_real = set(dezenas_reais)
        conn     = self.db.get_conn()
        cursor   = conn.cursor()
        cursor.execute("""
            SELECT id, dezenas, scores_modulos, score_total
            FROM fila_conferencia
            WHERE concurso_alvo = ? AND status = 'aguardando'
        """, (concurso,))
        fila = cursor.fetchall()

        resultados = []; total_g = 0.0; dist = {i: 0 for i in range(16)}
        for item in fila:
            fid   = item["id"]
            dez   = json.loads(item["dezenas"])
            sc_d  = {}
            try: sc_d = json.loads(item["scores_modulos"] or "{}")
            except Exception: pass

            acertos   = len(set(dez) & set_real)
            acertadas = sorted(set(dez) & set_real)
            premio    = premios.get(acertos, 0.0) if acertos >= 11 else 0.0
            total_g  += premio

            if   acertos >= 15: st = "premio_15"
            elif acertos >= 14: st = "premio_14"
            elif acertos >= 13: st = "premio_13"
            elif acertos >= 12: st = "premio_12"
            elif acertos >= 11: st = "premio_11"
            else:               st = "sem_premio"

            err = abs(float(item["score_total"] or 0) - acertos / 15.0)
            cursor.execute("""
                UPDATE fila_conferencia SET
                    status=?, acertos=?, premio_ganho=?,
                    dezenas_acertadas=?, timestamp_conferencia=?,
                    erro_previsao=?
                WHERE id=?
            """, (st, acertos, premio,
                  json.dumps(acertadas),
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  round(err, 4), fid))
            cursor.execute("""
                UPDATE cartelas SET conferida=1, acertos=?,
                    premio_ganho=?, status=?
                WHERE concurso_alvo=?
                  AND d1=? AND d2=? AND d3=? AND d4=? AND d5=?
                  AND d6=? AND d7=? AND d8=? AND d9=? AND d10=?
                  AND d11=? AND d12=? AND d13=? AND d14=? AND d15=?
            """, (acertos, premio, st, concurso, *dez))

            dist[acertos] += 1
            resultados.append({
                "fila_id": fid, "dezenas": dez, "acertos": acertos,
                "dezenas_acertadas": acertadas,
                "premio": premio, "status": st, "erro": round(err, 4),
                "scores_modulos": sc_d,
            })

            # Memória de erros
            for mod, sc in sc_d.items():
                try:
                    cursor.execute("""
                        INSERT INTO memoria_erros
                        (concurso,timestamp,modulo,erro,impacto)
                        VALUES (?,?,?,?,?)
                    """, (concurso,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          mod, abs(float(sc) - acertos/15.0),
                          abs(float(sc)-acertos/15.0) * \
                          float(self.pesos.get(mod, 0.1))))
                except Exception: pass

        conn.commit()
        conn.close()

        melhor = max((r["acertos"] for r in resultados), default=0)
        media  = sum(r["acertos"] for r in resultados) / max(len(resultados), 1)

        self._log("CONF", "melhor={}pts | ganho=R${:.2f}".format(
            melhor, total_g
        ))
        return {
            "status": "ok", "concurso": concurso,
            "dezenas_reais": dezenas_reais,
            "conferidas": len(resultados), "distribuicao": dist,
            "melhor_acertos": melhor, "media_acertos": round(media, 2),
            "total_ganho": round(total_g, 2),
            "custo": round(len(resultados) * VALOR_APOSTA, 2),
            "lucro": round(total_g - len(resultados) * VALOR_APOSTA, 2),
            "resultados": resultados,
        }

    def _aprender(
        self,
        concurso: int,
        conf: Dict,
        dezenas_reais: List[int],
        cartelas: List[Dict],
    ) -> Dict:
        pesos_antes = dict(self.pesos)
        melhor = conf.get("melhor_acertos", 0)
        fator  = 0.03

        # Ajustar pesos
        if   melhor >= 14:
            for k in self.pesos: self.pesos[k] *= (1 + fator)
        elif melhor >= 13:
            self.pesos["anti_logica"] *= (1 + fator * 2)
            self.pesos["markov"]      *= (1 + fator)
        elif melhor >= 11:
            self.pesos["gaussiano"]   *= (1 + fator)
            self.pesos["quantum"]     *= (1 + fator)
        else:
            self.pesos["anti_logica"] *= (1 + fator * 3)
            for k in ["freq_global","freq_recente"]:
                self.pesos[k] *= 0.97

        # Normalizar
        total = sum(self.pesos.values())
        for k in self.pesos:
            self.pesos[k] = round(self.pesos[k] / total, 4)

        # Registrar no stacking
        self._stacking.registrar(self.pesos, melhor)

        # Salvar desempenho
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        for mod in pesos_antes:
            try:
                cursor.execute("""
                    INSERT INTO desempenho_modulos
                    (concurso,timestamp,modulo,correlacao,
                     peso_antes,peso_depois)
                    VALUES (?,?,?,?,?,?)
                """, (concurso,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      mod,
                      round(1 - abs(
                          pesos_antes[mod] - self.pesos.get(mod, 0)
                      ), 4),
                      pesos_antes[mod], self.pesos.get(mod, 0)))
            except Exception: pass
        conn.commit()
        conn.close()

        mudancas = []
        for k in pesos_antes:
            d = self.pesos.get(k, 0) - pesos_antes[k]
            if abs(d) > 0.0005:
                mudancas.append("{}: {:.4f}{:+.4f}".format(
                    k, pesos_antes[k], d
                ))

        self._log("APRENDER", "melhor={} | {}".format(
            melhor, " | ".join(mudancas) or "sem mudanças"
        ))
        return {
            "status": "ok", "melhor": melhor,
            "pesos_novos": dict(self.pesos), "mudancas": mudancas,
        }

    def _salvar_resultado_banco(
        self,
        concurso: int,
        data_json: Dict,
        dezenas: List[int],
        premios: Dict[int, float],
    ):
        try:
            ds    = set(dezenas)
            soma  = sum(dezenas)
            pares = sum(1 for d in dezenas if d % 2 == 0)
            pc    = len(ds & PRIMOS)
            fc    = len(ds & FIBONACCI)
            bc    = len(ds & BORDA)
            sd    = sorted(dezenas); mc = cc = 1
            for i in range(1, len(sd)):
                if sd[i] == sd[i-1] + 1: cc += 1; mc = max(mc, cc)
                else: cc = 1
            dt_str = data_json.get("dataApuracao", "")
            try:
                from datetime import datetime as DT
                dt_str = DT.strptime(dt_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except Exception: pass
            from core.bitmatrix import BitMatrix
            bm = BitMatrix()
            dados = (concurso, dt_str, *dezenas,
                     bm.dezenas_para_bitmask(dezenas),
                     soma, pares, 15-pares, pc, fc, bc, mc,
                     premios.get(11,7.0), premios.get(12,14.0),
                     premios.get(13,35.0), premios.get(14,0.0),
                     premios.get(15,0.0),
                     0, 0, 0, 0, 0, 0.0)
            self.db.inserir_resultado(dados)
        except Exception as e:
            self._log("AVISO", "Salvar resultado: {}".format(e))

    # =========================================================
    # LOOP AUTOMÁTICO
    # =========================================================
    def iniciar_loop(self, intervalo: int = 3600) -> Dict:
        if self._rodando:
            return {"status": "ja_rodando"}
        self._rodando = True
        self.estado   = "monitorando"

        def _loop():
            self._log("LOOP", "Loop automático iniciado")
            while self._rodando:
                try:
                    if self._pausado:
                        time.sleep(30); continue
                    data = self._ingestor.buscar_ultimo_caixa()
                    if not data:
                        time.sleep(intervalo); continue
                    atual = int(data.get("numero", 0))
                    self.proximo_sorteio = data.get("dataProximoConcurso")
                    if atual <= self._ultimo_processado:
                        self._log("LOOP", "Sem novo. Último={}".format(atual))
                        time.sleep(intervalo); continue
                    self._log("LOOP", "Novo concurso: {}".format(atual))
                    self.executar_ciclo(atual)
                except Exception as e:
                    self._log("ERRO", "Loop: {}".format(e))
                    time.sleep(300)
            self.estado = "parado"
            self._log("LOOP", "Loop encerrado")

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        return {"status": "iniciado", "intervalo": intervalo}

    def parar_loop(self)  -> Dict: self._rodando = False; return {"status": "parando"}
    def pausar_loop(self) -> Dict: self._pausado = True;  self.estado = "pausado"; return {"status": "pausado"}
    def retomar_loop(self)-> Dict: self._pausado = False; self.estado = "monitorando"; return {"status": "retomado"}

    # =========================================================
    # BACKTESTING
    # =========================================================
    def backtesting(self, n_testes: int = 20, n_cart: int = 5) -> Dict:
        n = self.n
        if n < 100:
            return {"status": "insuficiente"}
        dist  = {i: 0 for i in range(16)}
        total = 0
        inicio = max(80, n - n_testes)
        for i in range(inicio, min(inicio + n_testes, n - 1)):
            try:
                cerebro_tmp = CerebroIA.__new__(CerebroIA)
                cerebro_tmp.db_path    = self.db_path
                cerebro_tmp.db         = self.db
                cerebro_tmp.n_cartelas = n_cart
                cerebro_tmp.pesos      = dict(self.pesos)
                cerebro_tmp.log        = []
                cerebro_tmp.estado     = "temp"
                cerebro_tmp.metricas   = {}
                cerebro_tmp.decisoes   = {}
                cerebro_tmp.ultima_exec = None
                cerebro_tmp.treinado   = False
                cerebro_tmp.matriz     = self.matriz[:i]
                cerebro_tmp.raw        = self.raw[:i]
                cerebro_tmp.n          = i
                cerebro_tmp._ingestor  = self._ingestor
                cerebro_tmp._motores   = {}
                cerebro_tmp._vetores   = {k: np.ones(TOTAL_DEZENAS)/TOTAL_DEZENAS
                                           for k in self.pesos}
                cerebro_tmp._cobertura = MotorCobertura()
                cerebro_tmp._stacking  = MotorStacking()
                cerebro_tmp._genetico  = MotorGenetico(2, 20, 20)
                cerebro_tmp._spsa      = OtimizadorSPSA(10)
                cerebro_tmp._gaussiano = MotorGaussiano(self.matriz[:i])
                cerebro_tmp._rodando   = False
                cerebro_tmp._pausado   = False
                cerebro_tmp._thread    = None
                cerebro_tmp._ciclos_ok  = 0
                cerebro_tmp._ciclos_err = 0
                cerebro_tmp._ultimo_processado = 0
                cerebro_tmp.proximo_sorteio    = None

                cartelas = cerebro_tmp.gerar_cartelas(n_cart, "monte_carlo")
                real = set(np.where(self.matriz[i+1] == 1)[0] + 1)
                if len(real) != 15: continue
                for c in cartelas:
                    ac = len(set(c["dezenas"]) & real)
                    dist[ac] += 1; total += 1
            except Exception as e:
                self._log("BT", "iter {}: {}".format(i, e)); continue

        return {
            "status": "ok",
            "total_testes":   n_testes,
            "total_cartelas": total,
            "distribuicao":   dist,
            "taxa_13": round(dist.get(13,0)/max(total,1), 4),
            "taxa_14": round(dist.get(14,0)/max(total,1), 4),
            "taxa_15": round(dist.get(15,0)/max(total,1), 4),
        }

    # =========================================================
    # STATUS E LOG
    # =========================================================
    def _log(self, tipo: str, msg: str):
        e = {"ts": datetime.now().strftime("%H:%M:%S"), "tipo": tipo, "msg": msg}
        self.log.append(e)
        if len(self.log) > 500: self.log = self.log[-500:]
        print("[CÉREBRO IA][{}] {}".format(tipo, msg))

    def get_status(self) -> Dict:
        return {
            "versao":           "6.0",
            "estado":           self.estado,
            "treinado":         self.treinado,
            "total_concursos":  self.n,
            "ultima_exec":      self.ultima_exec,
            "metricas":         self.metricas,
            "pesos_modulos":    self.pesos,
            "filtros": {
                "soma":      [self._gaussiano.SOMA_MIN,   self._gaussiano.SOMA_MAX],
                "pares":     [self._gaussiano.PARES_MIN,  self._gaussiano.PARES_MAX],
                "primos":    [self._gaussiano.PRIMOS_MIN, self._gaussiano.PRIMOS_MAX],
                "fibonacci": [self._gaussiano.FIB_MIN,    self._gaussiano.FIB_MAX],
                "borda":     [self._gaussiano.BORDA_MIN,  self._gaussiano.BORDA_MAX],
            },
            "ciclo": {
                "rodando":          self._rodando,
                "pausado":          self._pausado,
                "ciclos_ok":        self._ciclos_ok,
                "ciclos_erro":      self._ciclos_err,
                "ultimo_processado": self._ultimo_processado,
                "proximo_sorteio":  self.proximo_sorteio,
            },
            "log_recente": self.log[-20:],
        }

    def get_fila_concurso(self, concurso: int) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fila_conferencia
                WHERE concurso_alvo = ?
                ORDER BY score_total DESC
            """, (concurso,))
            rows = cursor.fetchall()
            conn.close()
            result = []
            for r in rows:
                d = dict(r)
                try:    d["dezenas"] = json.loads(d.get("dezenas","[]"))
                except: d["dezenas"] = []
                try:    d["dezenas_acertadas"] = json.loads(d.get("dezenas_acertadas","[]") or "[]")
                except: d["dezenas_acertadas"] = []
                result.append(d)
            return result
        except Exception: return []

    def get_historico_ciclos(self, limit: int = 20) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM historico_ciclos ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    def get_memoria_erros(self) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT modulo, AVG(erro) as erro_medio,
                       COUNT(*) as ocorrencias, AVG(impacto) as impacto_medio
                FROM memoria_erros GROUP BY modulo ORDER BY erro_medio DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    def get_desempenho_modulos(self) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT modulo, AVG(correlacao) as corr_media,
                       AVG(peso_depois) as peso_atual, COUNT(*) as n_ciclos
                FROM desempenho_modulos GROUP BY modulo ORDER BY corr_media DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []