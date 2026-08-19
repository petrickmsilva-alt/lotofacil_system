"""
============================================================
AGENTE AUTÔNOMO LOTOFÁCIL v5.0 — INTEGRAÇÃO TOTAL
Orquestra TODOS os 14 módulos + Anti-Lógica + Aprendizado
O agente decide, aprende, valida e entrega as melhores cartelas
============================================================
"""
import os
import sqlite3
import numpy as np
import json
import time
import itertools
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from config import (
    DATABASE_PATH, TOTAL_DEZENAS, DEZENAS_POR_JOGO,
    PRIMOS, FIBONACCI, BORDA, QUADRANTES, VALOR_APOSTA
)
from database.db_manager import DBManager


# ============================================================
# MÓDULO 1 — ANTI-LÓGICA ENGINE
# ============================================================
class AntiLogicEngine:
    """
    Detecta padrões óbvios e os inverte.
    Saturação, atraso, ciclos FFT, correlação de pares.
    """
    def __init__(self, matriz: np.ndarray):
        self.matriz = matriz
        self.n      = len(matriz)

    def detectar_saturacao(self, janela: int = 20) -> np.ndarray:
        if self.n < janela:
            return np.zeros(TOTAL_DEZENAS)
        recente  = self.matriz[-janela:]
        freq     = np.sum(recente, axis=0)
        esperado = janela * (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        desvio   = (freq - esperado) / (esperado + 1e-9)
        return desvio

    def detectar_atraso(self) -> np.ndarray:
        atraso = np.zeros(TOTAL_DEZENAS)
        for d in range(TOTAL_DEZENAS):
            for i in range(self.n - 1, -1, -1):
                if self.matriz[i][d] == 1:
                    atraso[d] = (self.n - 1) - i
                    break
            else:
                atraso[d] = self.n
        if atraso.max() > 0:
            atraso /= atraso.max()
        return atraso

    def detectar_ciclos_fft(self, periodo: int = 60) -> np.ndarray:
        scores = np.zeros(TOTAL_DEZENAS)
        for d in range(TOTAL_DEZENAS):
            serie = self.matriz[-periodo:, d].astype(float)
            if len(serie) < 10:
                continue
            fft_v = np.abs(np.fft.rfft(serie))
            if fft_v.max() > 0:
                scores[d] = float(fft_v[1:].max() / fft_v.max())
        return scores

    def calcular_correlacao(self) -> np.ndarray:
        if self.n < 20:
            return np.eye(TOTAL_DEZENAS)
        try:
            corr = np.corrcoef(self.matriz.T)
            return np.nan_to_num(corr, nan=0.0)
        except Exception:
            return np.eye(TOTAL_DEZENAS)

    def gerar_vetor_anti(self, probs_base: np.ndarray) -> np.ndarray:
        sat   = self.detectar_saturacao(20)
        atr   = self.detectar_atraso()
        ciclo = self.detectar_ciclos_fft(60)
        corr  = self.calcular_correlacao()
        conect = np.abs(corr).mean(axis=1)
        bonus_isol = 1.0 - (conect / (conect.max() + 1e-9))

        p = probs_base.copy()
        for i in range(TOTAL_DEZENAS):
            if sat[i]   > 0.40: p[i] *= 0.65
            if atr[i]   > 0.60: p[i] *= 1.45
            if ciclo[i] > 0.50: p[i] *= 1.25
            p[i] *= (1.0 + bonus_isol[i] * 0.15)

        s = p.sum()
        return p / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


# ============================================================
# MÓDULO 2 — MARKOV ENGINE INTERNO
# ============================================================
class MarkovInterno:
    def __init__(self, matriz: np.ndarray):
        self.matriz = matriz
        self.n      = len(matriz)
        self.trans  = np.ones((TOTAL_DEZENAS, TOTAL_DEZENAS))
        self._treinar()

    def _treinar(self):
        for i in range(1, self.n):
            ant = np.where(self.matriz[i - 1] == 1)[0]
            atu = np.where(self.matriz[i]     == 1)[0]
            for a in ant:
                for b in atu:
                    self.trans[a][b] += 1
        linha_sum = self.trans.sum(axis=1, keepdims=True)
        linha_sum[linha_sum == 0] = 1
        self.trans /= linha_sum

    def prever(self, ultimo_vetor: np.ndarray) -> np.ndarray:
        dezenas_ant = np.where(ultimo_vetor == 1)[0]
        prob        = np.zeros(TOTAL_DEZENAS)
        for d in dezenas_ant:
            prob += self.trans[d]
        s = prob.sum()
        return prob / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


# ============================================================
# MÓDULO 3 — QUANTUM WALK INTERNO
# ============================================================
class QuantumWalkInterno:
    def __init__(self):
        self.prob = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def passo(self, amp_u: np.ndarray, amp_d: np.ndarray):
        s = 1.0 / np.sqrt(2)
        au = s * amp_u + s * amp_d
        ad = s * amp_u - s * amp_d
        return np.roll(au, 1), np.roll(ad, -1)

    def executar(self, dezenas_init: List[int], passos: int = 150) -> np.ndarray:
        N   = TOTAL_DEZENAS
        au  = np.zeros(N, dtype=complex)
        ad  = np.zeros(N, dtype=complex)
        for d in dezenas_init:
            if 1 <= d <= N:
                au[d - 1] = 1.0 / np.sqrt(2)
                ad[d - 1] = 1.0j / np.sqrt(2)
        for _ in range(passos):
            au, ad = self.passo(au, ad)
        prob = np.abs(au) ** 2 + np.abs(ad) ** 2
        s    = prob.sum()
        return prob / s if s > 0 else np.ones(N) / N

    def treinar(self, matriz: np.ndarray) -> np.ndarray:
        n   = len(matriz)
        acc = np.zeros(TOTAL_DEZENAS)
        jan = min(n, 100)
        for i in range(n - jan, n - 1):
            dezenas = list(np.where(matriz[i] == 1)[0] + 1)
            acc    += self.executar(dezenas, passos=100)
        s = acc.sum()
        self.prob = acc / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        return self.prob


# ============================================================
# MÓDULO 4 — VERLET FÍSICO INTERNO
# ============================================================
class VerletInterno:
    RAIO_GLOBO = 0.20
    RAIO_BOLA  = 0.025
    MASSA      = 0.066
    COEF_REST  = 0.82
    GRAV       = 9.78
    DENS_AR    = 1.20

    def __init__(self):
        self.scores = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def simular(self, n_passos: int = 800) -> np.ndarray:
        N   = TOTAL_DEZENAS
        rng = np.random.default_rng(42)
        pos = np.zeros((N, 3))
        vel = np.zeros((N, 3))
        for i in range(N):
            while True:
                p = rng.uniform(-0.15, 0.15, 3)
                if np.linalg.norm(p) < 0.15:
                    pos[i] = p
                    break
            vel[i] = rng.normal(0, 0.8, 3)

        zona    = np.array([0.0, 0.0, self.RAIO_GLOBO * 0.85])
        contagem = np.zeros(N)
        g_vec   = np.array([0.0, 0.0, -self.GRAV])
        dt      = 5e-4

        for passo in range(n_passos):
            acc = np.zeros((N, 3))
            for i in range(N):
                speed = np.linalg.norm(vel[i])
                fd    = np.zeros(3)
                if speed > 1e-6:
                    cd = 0.47
                    A  = np.pi * self.RAIO_BOLA ** 2
                    fd = -0.5 * self.DENS_AR * speed ** 2 * cd * A * \
                         vel[i] / speed
                acc[i] = g_vec + fd / self.MASSA
                acc[i] += rng.normal(0, 0.001, 3)

            vel += acc * dt
            pos += vel * dt

            for i in range(N):
                d = np.linalg.norm(pos[i])
                lim = self.RAIO_GLOBO - self.RAIO_BOLA
                if d > lim and d > 1e-9:
                    n_hat  = pos[i] / d
                    vn     = np.dot(vel[i], n_hat)
                    if vn > 0:
                        vel[i] -= (1 + self.COEF_REST) * vn * n_hat
                    pos[i] = n_hat * lim

            if passo > n_passos * 0.3:
                for i in range(N):
                    if np.linalg.norm(pos[i] - zona) < self.RAIO_BOLA * 2.5:
                        contagem[i] += 1

        s = contagem.sum()
        return contagem / s if s > 0 else np.ones(N) / N

    def treinar(self, freq_hist: np.ndarray, n_sims: int = 3) -> np.ndarray:
        acc = np.zeros(TOTAL_DEZENAS)
        for _ in range(n_sims):
            acc += self.simular(600)
        acc /= n_sims
        if acc.max() > 0:
            acc /= acc.max()
        fh = freq_hist.copy()
        if fh.max() > 0:
            fh /= fh.max()
        self.scores = fh * 0.65 + acc * 0.35
        if self.scores.max() > 0:
            self.scores /= self.scores.max()
        return self.scores


# ============================================================
# MÓDULO 5 — ESTATÍSTICA AVANÇADA INTERNA
# ============================================================
class EstatisticaInterna:
    def __init__(self):
        self.freq_obs     = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.scores_chi2  = np.ones(TOTAL_DEZENAS) * 0.5
        self.prior_bayes  = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.matriz_bayes = np.ones((TOTAL_DEZENAS, TOTAL_DEZENAS)) / \
                            TOTAL_DEZENAS

    def calcular_chi2(self, matriz: np.ndarray) -> np.ndarray:
        n   = len(matriz)
        obs = np.sum(matriz, axis=0)
        esp = np.ones(TOTAL_DEZENAS) * (n * DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        res = (obs - esp) / np.sqrt(esp + 1e-9)
        res = np.clip(res, -3, 3)
        scores = (res - res.min()) / (res.max() - res.min() + 1e-9)
        self.scores_chi2 = scores
        self.freq_obs    = obs / (obs.sum() + 1e-9)
        return scores

    def treinar_bayes(self, matriz: np.ndarray):
        N   = TOTAL_DEZENAS
        cnt = np.ones((N, N))
        tot = np.ones(N) * N
        n   = len(matriz)
        for i in range(n - 1):
            ant = set(np.where(matriz[i]     == 1)[0])
            prx = set(np.where(matriz[i + 1] == 1)[0])
            for a in ant:
                tot[a] += 1
                for b in prx:
                    cnt[a][b] += 1
        self.matriz_bayes = cnt / tot[:, np.newaxis]
        freq = np.sum(matriz, axis=0)
        self.prior_bayes  = (freq + 1) / (n + N)

    def posterior(self, dezenas_ant: List[int]) -> np.ndarray:
        lp = np.log(self.prior_bayes + 1e-9)
        for d in dezenas_ant:
            if 1 <= d <= TOTAL_DEZENAS:
                lp += np.log(self.matriz_bayes[d - 1] + 1e-9)
        lp -= lp.max()
        p   = np.exp(lp)
        s   = p.sum()
        return p / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_kl(self, dezenas: List[int]) -> float:
        dist = np.zeros(TOTAL_DEZENAS)
        for d in dezenas:
            if 1 <= d <= TOTAL_DEZENAS:
                dist[d - 1] = 1.0
        dist /= (dist.sum() + 1e-9)
        q     = self.freq_obs + 1e-9
        p     = dist + 1e-9
        kl    = float(np.sum(p * np.log(p / q)))
        return max(0.0, 1.0 - kl / np.log(TOTAL_DEZENAS))

    def treinar(self, matriz: np.ndarray):
        self.calcular_chi2(matriz)
        self.treinar_bayes(matriz)


# ============================================================
# MÓDULO 6 — ALGORITMO GENÉTICO DE ILHAS INTERNO
# ============================================================
class GeneticoInterno:
    def __init__(self, n_ilhas: int = 4, tam: int = 40, geracoes: int = 50):
        self.n_ilhas  = n_ilhas
        self.tam      = tam
        self.geracoes = geracoes

    def _individuo(self, rng, candidatas: List[int]) -> List[int]:
        n = min(15, len(candidatas))
        return sorted(rng.choice(candidatas, size=n, replace=False).tolist())

    def _fitness(self, ind: List[int], fitness_fn) -> float:
        try:
            return float(fitness_fn(ind))
        except Exception:
            return 0.0

    def _crossover(self, p1: List[int], p2: List[int], rng) -> List[int]:
        uniao = list(set(p1) | set(p2))
        if len(uniao) < 15:
            extras = [d for d in range(1, 26) if d not in uniao]
            uniao += list(rng.choice(extras, size=15 - len(uniao),
                                      replace=False))
        cnt = {}
        for d in p1 + p2:
            cnt[d] = cnt.get(d, 0) + 1
        uniao.sort(key=lambda x: -cnt.get(x, 0))
        return sorted(uniao[:15])

    def _mutacao(self, ind: List[int], rng, taxa: float = 0.05) -> List[int]:
        ind = list(ind)
        for i in range(len(ind)):
            if rng.random() < taxa:
                disp = [d for d in range(1, 26) if d not in ind]
                if disp:
                    ind[i] = int(rng.choice(disp))
        uniq = sorted(set(ind))
        while len(uniq) < 15:
            disp = [d for d in range(1, 26) if d not in uniq]
            if disp:
                uniq.append(int(rng.choice(disp)))
        return sorted(uniq[:15])

    def evoluir(
        self,
        fitness_fn,
        candidatas: List[int],
        timeout: float = 20.0,
    ) -> List[Tuple[List[int], float]]:
        t0   = time.time()
        rngs = [np.random.default_rng(i * 31 + 7) for i in range(self.n_ilhas)]

        ilhas = [
            [self._individuo(rngs[ilha], candidatas)
             for _ in range(self.tam)]
            for ilha in range(self.n_ilhas)
        ]
        fits = [
            [self._fitness(ind, fitness_fn) for ind in ilha]
            for ilha in ilhas
        ]

        melhor_global = []
        melhor_fit    = -np.inf

        for g in range(self.geracoes):
            if time.time() - t0 > timeout:
                break

            for ilha in range(self.n_ilhas):
                pop = ilhas[ilha]
                fit = fits[ilha]
                nova = []

                # Elitismo top 3
                idx_e = sorted(range(len(fit)),
                                key=lambda x: fit[x], reverse=True)[:3]
                for ie in idx_e:
                    nova.append(list(pop[ie]))

                while len(nova) < self.tam:
                    try:
                        i1 = int(rngs[ilha].integers(0, len(pop)))
                        i2 = int(rngs[ilha].integers(0, len(pop)))
                        filho = self._crossover(pop[i1], pop[i2], rngs[ilha])
                        filho = self._mutacao(filho, rngs[ilha],
                                              taxa=0.05 * (1 - g/self.geracoes))
                        if len(filho) == 15:
                            nova.append(filho)
                    except Exception:
                        continue

                ilhas[ilha] = nova[:self.tam]
                fits[ilha]  = [self._fitness(ind, fitness_fn)
                                for ind in ilhas[ilha]]

                # Atualizar melhor
                idx_m = int(np.argmax(fits[ilha]))
                if fits[ilha][idx_m] > melhor_fit:
                    melhor_fit    = fits[ilha][idx_m]
                    melhor_global = list(ilhas[ilha][idx_m])

            # Migração a cada 10 gerações
            if (g + 1) % 10 == 0:
                for i in range(self.n_ilhas):
                    prox = (i + 1) % self.n_ilhas
                    idx_top = sorted(range(len(fits[i])),
                                     key=lambda x: fits[i][x],
                                     reverse=True)[:3]
                    idx_bot = sorted(range(len(fits[prox])),
                                     key=lambda x: fits[prox][x])[:3]
                    for k in range(3):
                        ilhas[prox][idx_bot[k]] = list(ilhas[i][idx_top[k]])

        # Coletar top soluções de todas as ilhas
        todos = []
        for ilha, fit in zip(ilhas, fits):
            for ind, f in zip(ilha, fit):
                todos.append((list(ind), float(f)))

        todos.sort(key=lambda x: x[1], reverse=True)

        # Deduplicar
        vistos, unicos = set(), []
        for ind, f in todos:
            key = tuple(sorted(ind))
            if key not in vistos:
                vistos.add(key)
                unicos.append((ind, f))

        return unicos[:50]


# ============================================================
# MÓDULO 7 — VALIDADOR DE COBERTURA
# ============================================================
class ValidadorCobertura:
    def calcular(
        self,
        cartelas: List[List[int]],
        universo: List[int],
        pontos: int = 13,
    ) -> Dict[str, Any]:
        uni   = sorted(universo)[:min(len(universo), 19)]
        total = cobertos = 0
        for res in itertools.combinations(uni, 15):
            set_r = set(res)
            total += 1
            for c in cartelas:
                if len(set(c) & set_r) >= pontos:
                    cobertos += 1
                    break
        cob = cobertos / total if total > 0 else 0.0
        return {
            "cobertura":   round(cob, 4),
            "cobertos":    cobertos,
            "total":       total,
            "pontos_alvo": pontos,
        }


# ============================================================
# AGENTE AUTÔNOMO v5.0 — INTEGRAÇÃO TOTAL DOS 14 MÓDULOS
# ============================================================
class AutonomousLotofacilAgent:
    """
    O agente único que:
    1.  Lê o banco de dados
    2.  Treina os 14 módulos internamente
    3.  Aplica anti-lógica
    4.  Executa algoritmo genético de ilhas
    5.  Aplica cobertura matemática
    6.  Entrega as melhores cartelas
    7.  Aprende com resultados reais
    """

    # Filtros (calibrados automaticamente)
    SOMA_MIN   = 175;  SOMA_MAX   = 230
    PARES_MIN  = 6;    PARES_MAX  = 9
    PRIMOS_MIN = 3;    PRIMOS_MAX = 7
    FIB_MIN    = 2;    FIB_MAX    = 6
    BORDA_MIN  = 7;    BORDA_MAX  = 11
    CONSEC_MAX = 5

    # Pesos dos 14 módulos (ajustados pelo SPSA interno)
    PESOS = {
        "freq_global":   0.08,
        "freq_recente":  0.08,
        "reversao":      0.10,
        "anti_logica":   0.12,
        "markov":        0.12,
        "quantum":       0.08,
        "verlet":        0.08,
        "chi2":          0.07,
        "bayes":         0.08,
        "kl":            0.05,
        "genetico":      0.05,
        "cobertura":     0.04,
        "gaussiano":     0.03,
        "stacking":      0.02,
    }

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        self.db      = DBManager()
        self.log     = []
        self.estado  = "inicializando"
        self.metricas = {}
        self.decisoes = {}
        self.ultima_exec = None
        self.historico_aprendizado = []

        # Carregar dados
        t0 = time.time()
        self.matriz, self.raw = self._carregar_banco()
        self.n = len(self.matriz)

        self._log("INIT", "{} concursos | {:.2f}s".format(
            self.n, time.time() - t0
        ))

        # Instanciar sub-módulos
        self.anti_logic  = AntiLogicEngine(self.matriz)
        self.markov_int  = MarkovInterno(self.matriz)
        self.quantum_int = QuantumWalkInterno()
        self.verlet_int  = VerletInterno()
        self.estat_int   = EstatisticaInterna()
        self.genetico    = GeneticoInterno(
            n_ilhas=4, tam=50, geracoes=60
        )
        self.validador   = ValidadorCobertura()

        # Vetores de score por módulo (inicializar uniforme)
        self.vetores: Dict[str, np.ndarray] = {
            k: np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
            for k in self.PESOS
        }

        self.estado = "pronto"
        self._calibrar_filtros_auto()

    # =========================================================
    # CARREGAR BANCO
    # =========================================================
    def _carregar_banco(self) -> Tuple[np.ndarray, list]:
        if not os.path.exists(self.db_path):
            self._log("AVISO", "Banco não encontrado.")
            return np.zeros((1, 25)), []
        try:
            conn   = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                       d11,d12,d13,d14,d15
                FROM resultados ORDER BY concurso ASC
            """)
            rows = cursor.fetchall()
            cursor.execute("SELECT * FROM resultados ORDER BY concurso ASC")
            raw  = cursor.fetchall()
            conn.close()

            if not rows:
                return np.zeros((1, 25)), []

            matriz = np.zeros((len(rows), 25), dtype=np.float32)
            for idx, linha in enumerate(rows):
                for d in linha:
                    v = int(d)
                    if 1 <= v <= 25:
                        matriz[idx][v - 1] = 1.0

            self._log("DADOS", "Matriz {}x25 carregada.".format(len(rows)))
            return matriz, raw
        except Exception as e:
            self._log("ERRO", "Banco: {}".format(str(e)))
            return np.zeros((1, 25)), []

    # =========================================================
    # TREINO COMPLETO DOS 14 MÓDULOS
    # =========================================================
    def treinar_todos_modulos(self, callback=None) -> Dict[str, Any]:
        """
        Treina TODOS os 14 módulos internamente.
        Chamado automaticamente antes de gerar cartelas.
        """
        self.estado = "treinando"
        t0 = time.time()

        def cb(msg):
            self._log("TREINO", msg)
            if callback:
                callback(msg)

        cb("Iniciando treino completo dos 14 módulos...")

        # ── Módulo 1: Frequência Global ───────────────────────
        cb("1/14 Frequência Global...")
        freq_g = np.sum(self.matriz, axis=0)
        freq_g_norm = freq_g / (freq_g.sum() + 1e-9)
        self.vetores["freq_global"] = freq_g_norm

        # ── Módulo 2: Frequência Recente ──────────────────────
        cb("2/14 Frequência Recente (30 concursos)...")
        jan = min(30, self.n)
        freq_r = np.sum(self.matriz[-jan:], axis=0)
        freq_r_norm = freq_r / (freq_r.sum() + 1e-9)
        self.vetores["freq_recente"] = freq_r_norm

        # ── Módulo 3: Reversão à Média ────────────────────────
        cb("3/14 Reversão à Média Estocástica...")
        rev = self._calcular_reversao(freq_g_norm, freq_r)
        self.vetores["reversao"] = rev

        # ── Módulo 4: Anti-Lógica ─────────────────────────────
        cb("4/14 Anti-Lógica (Saturação + Atraso + FFT)...")
        self.anti_logic = AntiLogicEngine(self.matriz)
        anti = self.anti_logic.gerar_vetor_anti(rev)
        self.vetores["anti_logica"] = anti

        # ── Módulo 5: Markov Engine ───────────────────────────
        cb("5/14 Markov Engine (Transições)...")
        try:
            self.markov_int = MarkovInterno(self.matriz)
            ult_vetor = self.matriz[-1] if self.n > 0 else \
                        np.zeros(TOTAL_DEZENAS)
            markov_v  = self.markov_int.prever(ult_vetor)
            self.vetores["markov"] = markov_v
        except Exception as e:
            self._log("AVISO", "Markov: {}".format(str(e)))

        # ── Módulo 6: Quantum Walk ────────────────────────────
        cb("6/14 Quantum Walk...")
        try:
            self.quantum_int = QuantumWalkInterno()
            q_v = self.quantum_int.treinar(self.matriz)
            self.vetores["quantum"] = q_v
        except Exception as e:
            self._log("AVISO", "Quantum: {}".format(str(e)))

        # ── Módulo 7: Verlet 3D ───────────────────────────────
        cb("7/14 Simulador Verlet 3D...")
        try:
            self.verlet_int = VerletInterno()
            v_v = self.verlet_int.treinar(freq_g_norm, n_sims=2)
            self.vetores["verlet"] = v_v
        except Exception as e:
            self._log("AVISO", "Verlet: {}".format(str(e)))

        # ── Módulo 8: Chi-Quadrado ────────────────────────────
        cb("8/14 Teste Chi-Quadrado (χ²)...")
        try:
            self.estat_int = EstatisticaInterna()
            chi2_v = self.estat_int.calcular_chi2(self.matriz)
            self.vetores["chi2"] = chi2_v
        except Exception as e:
            self._log("AVISO", "Chi2: {}".format(str(e)))

        # ── Módulo 9: Bayes + Bernoulli ───────────────────────
        cb("9/14 Bayes + Bernoulli Condicional...")
        try:
            self.estat_int.treinar_bayes(self.matriz)
            ult_dez = list(np.where(self.matriz[-1] == 1)[0] + 1) \
                      if self.n > 0 else list(range(1, 16))
            bayes_v = self.estat_int.posterior(ult_dez)
            self.vetores["bayes"] = bayes_v
        except Exception as e:
            self._log("AVISO", "Bayes: {}".format(str(e)))

        # ── Módulo 10: KL Divergência ─────────────────────────
        cb("10/14 Filtro KL Divergência...")
        try:
            kl_v = np.zeros(TOTAL_DEZENAS)
            for i in range(TOTAL_DEZENAS):
                dist_i    = np.zeros(TOTAL_DEZENAS)
                dist_i[i] = 1.0
                kl_v[i]   = self.estat_int.score_kl([i + 1])
            s = kl_v.sum()
            self.vetores["kl"] = kl_v / s if s > 0 else \
                                  np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        except Exception as e:
            self._log("AVISO", "KL: {}".format(str(e)))

        # ── Módulo 11: Filtro Gaussiano ───────────────────────
        cb("11/14 Filtros Gaussianos (Soma/Paridade)...")
        try:
            gauss_v = self._calcular_score_gaussiano_global()
            self.vetores["gaussiano"] = gauss_v
        except Exception as e:
            self._log("AVISO", "Gaussiano: {}".format(str(e)))

        # ── Módulo 12: Algoritmo Genético ─────────────────────
        cb("12/14 Algoritmo Genético (placeholder treino)...")
        # O AG é usado na geração, não no treino
        self.vetores["genetico"] = anti.copy()

        # ── Módulo 13: Cobertura Matemática ───────────────────
        cb("13/14 Cobertura Matemática...")
        self.vetores["cobertura"] = freq_g_norm.copy()

        # ── Módulo 14: Stacking / Meta-Aprendizado ────────────
        cb("14/14 Meta-Aprendizado (Stacking)...")
        stack_v = self._calcular_stacking()
        self.vetores["stacking"] = stack_v

        # ── Calibrar pesos via SPSA ───────────────────────────
        cb("Calibrando pesos com SPSA...")
        self._calibrar_pesos_spsa()

        tempo = time.time() - t0
        self.estado = "pronto"
        self.metricas["tempo_treino"] = round(tempo, 2)
        cb("14 módulos treinados em {:.1f}s".format(tempo))

        return {
            "status":  "ok",
            "modulos": 14,
            "tempo":   round(tempo, 2),
        }

    # =========================================================
    # HELPERS DE TREINO
    # =========================================================
    def _calcular_reversao(
        self,
        freq_g: np.ndarray,
        freq_r: np.ndarray,
    ) -> np.ndarray:
        jan      = min(30, self.n)
        esperado = jan * (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        v        = np.zeros(TOTAL_DEZENAS)
        for i in range(TOTAL_DEZENAS):
            if freq_r[i] > esperado * 1.5:
                v[i] = freq_g[i] * 0.60
            elif freq_r[i] < esperado * 0.6:
                v[i] = freq_g[i] * 1.50
            else:
                v[i] = freq_g[i]
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def _calcular_score_gaussiano_global(self) -> np.ndarray:
        v = np.zeros(TOTAL_DEZENAS)
        for i in range(TOTAL_DEZENAS):
            score = 0.5
            d     = i + 1
            if d in PRIMOS:     score += 0.05
            if d in FIBONACCI:  score += 0.05
            if d in BORDA:      score += 0.03
            v[i] = score
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def _calcular_stacking(self) -> np.ndarray:
        if not self.historico_aprendizado:
            return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Pesos baseados nos acertos históricos de cada módulo
        v = np.zeros(TOTAL_DEZENAS)
        for entrada in self.historico_aprendizado[-50:]:
            acertos = entrada.get("acertos", 0)
            pesos_u = entrada.get("pesos_usados", {})
            for mod, peso in pesos_u.items():
                vec = self.vetores.get(mod, np.zeros(TOTAL_DEZENAS))
                v  += vec * peso * (acertos / 15.0)

        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def _calibrar_pesos_spsa(self):
        """SPSA rápido para calibrar pesos dos módulos"""
        nomes  = list(self.PESOS.keys())
        theta  = np.array([self.PESOS[k] for k in nomes])
        rng    = np.random.default_rng(42)
        n_iter = 20

        def perda(p):
            p = np.clip(p, 0.01, None)
            p = p / p.sum()
            # Combinar vetores com esses pesos
            v = np.zeros(TOTAL_DEZENAS)
            for i_m, nome in enumerate(nomes):
                v += self.vetores[nome] * p[i_m]
            # Penalizar concentração excessiva
            entropia = -np.sum(v * np.log(v + 1e-9))
            return float(-entropia)

        melhor_theta = theta.copy()
        melhor_loss  = perda(theta)

        for k in range(n_iter):
            ak    = 0.15 / (k + 1 + 10) ** 0.602
            ck    = 0.05 / (k + 1) ** 0.101
            delta = rng.choice([-1.0, 1.0], size=len(theta))
            tp    = np.clip(theta + ck * delta, 0.01, 0.5)
            tn    = np.clip(theta - ck * delta, 0.01, 0.5)
            ghat  = (perda(tp) - perda(tn)) / (2 * ck * delta + 1e-9)
            theta -= ak * ghat
            theta  = np.clip(theta, 0.01, 0.5)
            lp     = perda(theta)
            if lp < melhor_loss:
                melhor_loss  = lp
                melhor_theta = theta.copy()

        melhor_theta = np.clip(melhor_theta, 0.01, None)
        melhor_theta /= melhor_theta.sum()
        for i_m, nome in enumerate(nomes):
            self.PESOS[nome] = round(float(melhor_theta[i_m]), 4)

        self._log("SPSA", "Pesos calibrados. Melhor loss={:.4f}".format(
            melhor_loss
        ))

    # =========================================================
    # VETOR FINAL COMBINADO
    # =========================================================
    def _combinar_vetores(self) -> np.ndarray:
        """Combina os 14 vetores com pesos otimizados pelo SPSA"""
        v = np.zeros(TOTAL_DEZENAS)
        for nome, peso in self.PESOS.items():
            vec = self.vetores.get(nome, np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS)
            v  += vec * peso
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    # =========================================================
    # FILTROS
    # =========================================================
    def _filtrar(
        self, dezenas: List[int]
    ) -> Tuple[bool, Dict[str, Any]]:
        d_set  = set(dezenas)
        soma   = sum(dezenas)
        pares  = sum(1 for d in dezenas if d % 2 == 0)
        sd     = sorted(dezenas)
        max_c  = curr = 1
        for i in range(1, len(sd)):
            if sd[i] == sd[i - 1] + 1:
                curr  += 1
                max_c  = max(max_c, curr)
            else:
                curr   = 1
        primos_c = len(d_set & PRIMOS)
        fib_c    = len(d_set & FIBONACCI)
        borda_c  = len(d_set & BORDA)
        det = {
            "soma": soma, "pares": pares, "primos": primos_c,
            "fibonacci": fib_c, "borda": borda_c, "consec": max_c,
        }
        ok = (
            self.SOMA_MIN  <= soma    <= self.SOMA_MAX   and
            self.PARES_MIN <= pares   <= self.PARES_MAX  and
            max_c          <= self.CONSEC_MAX            and
            self.PRIMOS_MIN <= primos_c <= self.PRIMOS_MAX and
            self.FIB_MIN   <= fib_c   <= self.FIB_MAX   and
            self.BORDA_MIN <= borda_c <= self.BORDA_MAX
        )
        return ok, det

    # =========================================================
    # SCORE COMPLETO DE UMA CARTELA
    # =========================================================
    def _score_cartela(
        self,
        dezenas: List[int],
        vetor_final: np.ndarray,
        outras: List[List[int]],
    ) -> Dict[str, float]:
        scores = {}

        # EV probabilístico
        scores["ev_prob"] = float(sum(
            vetor_final[d - 1] for d in dezenas
        ))

        # Diversidade em relação às outras
        if outras:
            uniao_outras = set()
            for o in outras:
                uniao_outras.update(o)
            scores["diversidade"] = len(set(dezenas) - uniao_outras) / 15.0
        else:
            scores["diversidade"] = 1.0

        # KL score
        scores["kl"] = self.estat_int.score_kl(dezenas)

        # Bayes score
        ult_dez = list(np.where(self.matriz[-1] == 1)[0] + 1) \
                  if self.n > 0 else list(range(1, 16))
        bayes_v = self.estat_int.posterior(ult_dez)
        scores["bayes"] = float(np.mean([bayes_v[d - 1] for d in dezenas]))

        # Verlet
        scores["verlet"] = float(np.mean([
            self.vetores["verlet"][d - 1] for d in dezenas
        ]))

        # Markov
        scores["markov"] = float(np.mean([
            self.vetores["markov"][d - 1] for d in dezenas
        ]))

        # Score gaussiano
        passou, det = self._filtrar(dezenas)
        soma   = det["soma"]
        centro = (self.SOMA_MIN + self.SOMA_MAX) / 2
        scores["gaussiano"] = max(
            0.0, 1.0 - abs(soma - centro) / (centro - self.SOMA_MIN)
        )

        # Score total ponderado
        scores["total"] = (
            scores["ev_prob"]    * 0.25 +
            scores["diversidade"] * 0.20 +
            scores["kl"]         * 0.12 +
            scores["bayes"]      * 0.15 +
            scores["verlet"]     * 0.10 +
            scores["markov"]     * 0.12 +
            scores["gaussiano"]  * 0.06
        )

        return scores

    # =========================================================
    # GERAR CARTELAS — PIPELINE COMPLETO
    # =========================================================
    def moldurar_cartelas_autonomas(
        self,
        quantidade: int = 10,
        modo: str = "hibrido",
        callback=None,
    ) -> List[Dict[str, Any]]:
        """
        Pipeline completo e autônomo:
        Fase 1  → Treinar os 14 módulos
        Fase 2  → Combinar vetores
        Fase 3  → Selecionar grupo elite
        Fase 4  → Algoritmo Genético de Ilhas
        Fase 5  → Monte Carlo + Combinatório
        Fase 6  → Filtros gaussianos
        Fase 7  → Score completo
        Fase 8  → Cobertura matemática
        Fase 9  → Aprendizado e entrega
        """
        self.estado = "gerando"
        t0 = time.time()

        def cb(msg):
            self._log("GERAR", msg)
            if callback:
                callback(msg)

        cb("Pipeline iniciado | qtd={} modo={}".format(quantidade, modo))

        # ── Fase 1: Treinar módulos ───────────────────────────
        cb("Fase 1/9: Treinando 14 módulos...")
        self.treinar_todos_modulos(callback=callback)

        # ── Fase 2: Vetor combinado ───────────────────────────
        cb("Fase 2/9: Combinando vetores dos 14 módulos...")
        vetor_final = self._combinar_vetores()

        top5 = list(np.argsort(vetor_final)[::-1][:5] + 1)
        self._log("VETOR", "Top 5 dezenas: {}".format(top5))
        self.metricas["top5"] = top5

        # ── Fase 3: Grupo Elite ───────────────────────────────
        cb("Fase 3/9: Selecionando grupo elite...")
        tam_elite   = min(19, 15 + quantidade // 2)
        grupo_elite = self._selecionar_elite(vetor_final, tam_elite)
        self.decisoes["grupo_elite"] = sorted(grupo_elite)
        self._log("ELITE", "Grupo: {}".format(sorted(grupo_elite)))

        # ── Fase 4: Algoritmo Genético de Ilhas ──────────────
        cb("Fase 4/9: Algoritmo Genético de Ilhas...")
        candidatas_ag = []
        try:
            def fitness_ag(dezenas):
                passou, _ = self._filtrar(dezenas)
                ev = float(sum(vetor_final[d - 1] for d in dezenas))
                return ev * (1.5 if passou else 0.5)

            top_ag = self.genetico.evoluir(
                fitness_ag, grupo_elite, timeout=15.0
            )
            candidatas_ag = [ind for ind, _ in top_ag[:quantidade * 3]]
            self._log("AG", "{} candidatas do AG".format(len(candidatas_ag)))
        except Exception as e:
            self._log("AVISO", "AG: {}".format(str(e)))

        # ── Fase 5: Monte Carlo + Combinatório ───────────────
        cb("Fase 5/9: Monte Carlo + Combinatório...")
        candidatas_mc  = self._monte_carlo(grupo_elite, vetor_final,
                                            quantidade * 4)
        candidatas_comb = self._combinatorio(grupo_elite, vetor_final,
                                              quantidade * 2)
        todas_candidatas = candidatas_ag + candidatas_mc + candidatas_comb
        self._log("CANDIDATAS",
                  "Total: {}".format(len(todas_candidatas)))

        # ── Fase 6: Filtros Gaussianos ────────────────────────
        cb("Fase 6/9: Aplicando filtros gaussianos...")
        aprovadas  = []
        reprovadas = 0
        for cand in todas_candidatas:
            passou, det = self._filtrar(cand)
            if passou:
                aprovadas.append((cand, det))
            else:
                reprovadas += 1

        self._log("FILTROS", "Aprovadas: {} | Reprovadas: {}".format(
            len(aprovadas), reprovadas
        ))

        # Fallback se filtros rejeitaram tudo
        if len(aprovadas) < quantidade:
            cb("Filtros muito restritivos, usando fallback...")
            extras = self._fallback(vetor_final, grupo_elite,
                                    quantidade - len(aprovadas))
            for e in extras:
                passou, det = self._filtrar(e)
                aprovadas.append((e, det))

        # ── Fase 7: Score completo ────────────────────────────
        cb("Fase 7/9: Calculando score completo...")
        rankeadas = []
        outras    = []
        vistas    = set()

        for cand, det in aprovadas:
            key = tuple(sorted(cand))
            if key in vistas:
                continue
            vistas.add(key)

            scores = self._score_cartela(cand, vetor_final, outras)
            outras.append(cand)

            rankeadas.append({
                "dezenas":     sorted(cand),
                "scores":      scores,
                "score_total": round(scores["total"], 6),
                "soma":        det["soma"],
                "pares":       det["pares"],
                "primos":      det["primos"],
                "fibonacci":   det["fibonacci"],
                "borda":       det["borda"],
                "consec_max":  det["consec"],
            })

        rankeadas.sort(key=lambda x: x["score_total"], reverse=True)
        resultado = rankeadas[:quantidade]

        # ── Fase 8: Cobertura matemática ──────────────────────
        cb("Fase 8/9: Validando cobertura 13+ pontos...")
        if resultado and len(grupo_elite) >= 15:
            listas = [c["dezenas"] for c in resultado]
            try:
                cob = self.validador.calcular(
                    listas, grupo_elite, pontos=13
                )
                for c in resultado:
                    c["cobertura_13"] = cob["cobertura"]
                self.metricas["cobertura_13"] = cob["cobertura"]
                self._log("COBERTURA", "13pts: {:.1%} ({}/{})".format(
                    cob["cobertura"], cob["cobertos"], cob["total"]
                ))
            except Exception as e:
                self._log("AVISO", "Cobertura: {}".format(str(e)))

        # ── Fase 9: Metadados e entrega ───────────────────────
        cb("Fase 9/9: Preparando entrega...")
        tempo = time.time() - t0
        for i, c in enumerate(resultado):
            c.update({
                "id_geracao":   i + 1,
                "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "modo":         modo,
                "grupo_elite":  sorted(grupo_elite),
                "tempo_seg":    round(tempo, 2),
                "n_modulos":    14,
                "pesos_usados": dict(self.PESOS),
            })

        self.metricas.update({
            "total_geradas":    len(resultado),
            "candidatas_total": len(todas_candidatas),
            "reprovadas":       reprovadas,
            "tempo_seg":        round(tempo, 2),
            "grupo_elite":      sorted(grupo_elite),
        })

        self.estado      = "pronto"
        self.ultima_exec = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cb("Concluído em {:.1f}s | {} cartelas entregues".format(
            tempo, len(resultado)
        ))

        return resultado

    # =========================================================
    # GERADORES AUXILIARES
    # =========================================================
    def _selecionar_elite(
        self, vetor: np.ndarray, tam: int
    ) -> List[int]:
        ranking = list(np.argsort(vetor)[::-1] + 1)
        grupo   = []
        for d in ranking:
            if len(grupo) >= tam:
                break
            # Verificar diversidade por quadrante
            g_test = grupo + [d]
            if len(g_test) >= 10:
                dist = {q: 0 for q in QUADRANTES}
                for dz in g_test:
                    for q, nums in QUADRANTES.items():
                        if dz in nums:
                            dist[q] += 1
                if any(v == 0 for v in dist.values()):
                    continue
            grupo.append(d)
        for d in ranking:
            if len(grupo) >= tam:
                break
            if d not in grupo:
                grupo.append(d)
        return grupo[:tam]

    def _monte_carlo(
        self,
        candidatas: List[int],
        probs: np.ndarray,
        n: int,
    ) -> List[List[int]]:
        pesos = np.array([float(probs[d - 1]) for d in candidatas])
        pesos = np.clip(pesos, 0.001, None)
        pesos /= pesos.sum()
        result = []
        for _ in range(n * 5):
            if len(result) >= n:
                break
            try:
                idx  = np.random.choice(len(candidatas), size=15,
                                         replace=False, p=pesos)
                cand = sorted([candidatas[i] for i in idx])
                result.append(cand)
            except Exception:
                continue
        return result[:n]

    def _combinatorio(
        self,
        candidatas: List[int],
        probs: np.ndarray,
        n: int,
    ) -> List[List[int]]:
        cands = sorted(candidatas)
        if len(cands) > 19:
            cands = cands[:19]
        result = []
        combos = list(itertools.combinations(cands, 15))
        scored = sorted(
            combos,
            key=lambda c: sum(probs[d - 1] for d in c),
            reverse=True,
        )
        for combo in scored[:n]:
            result.append(list(combo))
        return result

    def _fallback(
        self,
        probs: np.ndarray,
        elite: List[int],
        n: int,
    ) -> List[List[int]]:
        result = []
        pesos  = np.array([float(probs[d - 1]) for d in elite])
        pesos  = np.clip(pesos, 0.001, None) / pesos.sum()
        for _ in range(n * 20):
            if len(result) >= n:
                break
            try:
                idx  = np.random.choice(len(elite), size=15,
                                         replace=False, p=pesos)
                cand = sorted([elite[i] for i in idx])
                soma = sum(cand)
                par  = sum(1 for d in cand if d % 2 == 0)
                if 165 <= soma <= 240 and 4 <= par <= 11:
                    result.append(cand)
            except Exception:
                continue
        return result[:n]

    # =========================================================
    # APRENDIZADO COM RESULTADO REAL
    # =========================================================
    def aprender_com_resultado(
        self,
        concurso: int,
        dezenas_reais: List[int],
        cartelas_geradas: List[Dict],
    ) -> Dict[str, Any]:
        """
        Após o sorteio, o agente aprende:
        - Qual módulo acertou mais dezenas
        - Ajusta os pesos via feedback real
        - Registra para o stacking futuro
        """
        set_real = set(dezenas_reais)

        # Avaliar cada cartela
        melhor_acertos = 0
        total_acertos  = 0
        acertos_mod    = {k: 0.0 for k in self.PESOS}

        for cart in cartelas_geradas:
            dez = cart.get("dezenas", [])
            if not dez:
                continue
            acertos = len(set(dez) & set_real)
            melhor_acertos = max(melhor_acertos, acertos)
            total_acertos += acertos

            # Verificar qual módulo favorecia mais as dezenas acertadas
            acertadas = set(dez) & set_real
            for mod in self.PESOS:
                vec    = self.vetores.get(mod, np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS)
                score  = float(np.mean([vec[d - 1] for d in acertadas])) \
                         if acertadas else 0.0
                acertos_mod[mod] += score

        media_acertos = total_acertos / max(len(cartelas_geradas), 1)

        # Ajustar pesos
        pesos_antes = dict(self.PESOS)
        fator = 0.03

        if melhor_acertos >= 14:
            for k in self.PESOS:
                self.PESOS[k] *= (1 + fator)
        elif melhor_acertos >= 13:
            # Reforçar módulos que acertaram mais
            melhor_mod = max(acertos_mod, key=acertos_mod.get)
            self.PESOS[melhor_mod] *= (1 + fator * 2)
        elif melhor_acertos >= 11:
            self.PESOS["anti_logica"] *= (1 + fator)
        else:
            # Resultado ruim — rebalancear
            for k in self.PESOS:
                self.PESOS[k] = max(self.PESOS[k] * 0.98, 0.01)
            self.PESOS["anti_logica"] *= 1.10

        # Normalizar
        total = sum(self.PESOS.values())
        for k in self.PESOS:
            self.PESOS[k] = round(self.PESOS[k] / total, 4)

        # Registrar histórico de aprendizado
        entrada = {
            "concurso":     concurso,
            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "acertos_max":  melhor_acertos,
            "acertos_media": round(media_acertos, 2),
            "pesos_antes":  pesos_antes,
            "pesos_depois": dict(self.PESOS),
            "pesos_usados": dict(self.PESOS),
            "acertos_mod":  {k: round(v, 4)
                              for k, v in acertos_mod.items()},
        }
        self.historico_aprendizado.append(entrada)

        # Salvar no banco
        try:
            dados = (
                len(self.historico_aprendizado),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round(media_acertos / 15, 4),
                0.0,
                float(melhor_acertos),
                len(cartelas_geradas),
                float(melhor_acertos >= 13),
                float(melhor_acertos >= 14),
                float(melhor_acertos >= 15),
                json.dumps(self.PESOS),
            )
            self.db.inserir_aprendizado(dados)
        except Exception as e:
            self._log("AVISO", "Salvar aprendizado: {}".format(str(e)))

        self._log(
            "APRENDIZADO",
            "Concurso {} | melhor={} | média={:.1f}".format(
                concurso, melhor_acertos, media_acertos
            ),
        )

        return {
            "status":       "ok",
            "concurso":     concurso,
            "melhor":       melhor_acertos,
            "media":        round(media_acertos, 2),
            "pesos_novos":  dict(self.PESOS),
        }

    # =========================================================
    # CALIBRAÇÃO AUTÔNOMA DOS FILTROS
    # =========================================================
    def _calibrar_filtros_auto(self):
        if self.n < 50:
            return
        try:
            somas   = []
            pares_l = []
            primos_l = []
            fib_l   = []
            borda_l = []
            for i in range(self.n):
                dez = list(np.where(self.matriz[i] == 1)[0] + 1)
                if len(dez) != 15:
                    continue
                somas.append(sum(dez))
                pares_l.append(sum(1 for d in dez if d % 2 == 0))
                primos_l.append(len(set(dez) & PRIMOS))
                fib_l.append(len(set(dez) & FIBONACCI))
                borda_l.append(len(set(dez) & BORDA))

            def pct(arr, lo=3, hi=97):
                a = sorted(arr)
                n = len(a)
                return (
                    a[max(0, int(n * lo / 100))],
                    a[min(n - 1, int(n * hi / 100))]
                )

            self.SOMA_MIN,   self.SOMA_MAX   = pct(somas)
            self.PARES_MIN,  self.PARES_MAX  = pct(pares_l)
            self.PRIMOS_MIN, self.PRIMOS_MAX = pct(primos_l)
            self.FIB_MIN,    self.FIB_MAX    = pct(fib_l)
            self.BORDA_MIN,  self.BORDA_MAX  = pct(borda_l)

            self._log("CALIBRAÇÃO", "Filtros: soma={}-{} | pares={}-{}".format(
                self.SOMA_MIN, self.SOMA_MAX,
                self.PARES_MIN, self.PARES_MAX,
            ))
        except Exception as e:
            self._log("AVISO", "Calibração: {}".format(str(e)))

    def calibrar_filtros_autonomamente(self) -> Dict[str, Any]:
        self._calibrar_filtros_auto()
        return {
            "status":    "ok",
            "soma":      [self.SOMA_MIN,   self.SOMA_MAX],
            "pares":     [self.PARES_MIN,  self.PARES_MAX],
            "primos":    [self.PRIMOS_MIN, self.PRIMOS_MAX],
            "fibonacci": [self.FIB_MIN,    self.FIB_MAX],
            "borda":     [self.BORDA_MIN,  self.BORDA_MAX],
        }

    # =========================================================
    # BACKTESTING AUTÔNOMO
    # =========================================================
    def backtesting_autonomo(
        self, n_testes: int = 20, n_cart: int = 5
    ) -> Dict[str, Any]:
        n = self.n
        if n < 100:
            return {"status": "insuficiente"}

        dist   = {i: 0 for i in range(16)}
        total  = 0
        inicio = max(80, n - n_testes)

        for i in range(inicio, min(inicio + n_testes, n - 1)):
            try:
                # Agente temporário com dados até i
                ag_tmp = self._agente_temp(i)
                cartelas = ag_tmp.moldurar_cartelas_autonomas(
                    quantidade=n_cart, modo="monte_carlo"
                )
                real = set(np.where(self.matriz[i + 1] == 1)[0] + 1)
                if len(real) != 15:
                    continue
                for c in cartelas:
                    ac = len(set(c["dezenas"]) & real)
                    dist[ac] += 1
                    total    += 1
            except Exception as e:
                self._log("BT", "Erro iter {}: {}".format(i, str(e)))
                continue

        taxa_13 = dist.get(13, 0) / max(total, 1)
        taxa_14 = dist.get(14, 0) / max(total, 1)
        taxa_15 = dist.get(15, 0) / max(total, 1)

        return {
            "status":         "ok",
            "total_testes":   n_testes,
            "total_cartelas": total,
            "distribuicao":   dist,
            "taxa_13":        round(taxa_13, 4),
            "taxa_14":        round(taxa_14, 4),
            "taxa_15":        round(taxa_15, 4),
        }

    def _agente_temp(self, ate_indice: int) -> "AutonomousLotofacilAgent":
        ag = AutonomousLotofacilAgent.__new__(AutonomousLotofacilAgent)
        ag.db_path    = self.db_path
        ag.db         = self.db
        ag.log        = []
        ag.estado     = "temp"
        ag.metricas   = {}
        ag.decisoes   = {}
        ag.ultima_exec = None
        ag.historico_aprendizado = []
        ag.matriz     = self.matriz[:ate_indice]
        ag.raw        = self.raw[:ate_indice]
        ag.n          = ate_indice
        ag.PESOS      = dict(self.PESOS)
        ag.SOMA_MIN   = self.SOMA_MIN;  ag.SOMA_MAX   = self.SOMA_MAX
        ag.PARES_MIN  = self.PARES_MIN; ag.PARES_MAX  = self.PARES_MAX
        ag.PRIMOS_MIN = self.PRIMOS_MIN; ag.PRIMOS_MAX = self.PRIMOS_MAX
        ag.FIB_MIN    = self.FIB_MIN;   ag.FIB_MAX    = self.FIB_MAX
        ag.BORDA_MIN  = self.BORDA_MIN; ag.BORDA_MAX  = self.BORDA_MAX
        ag.CONSEC_MAX = self.CONSEC_MAX
        ag.anti_logic = AntiLogicEngine(ag.matriz)
        ag.markov_int = MarkovInterno(ag.matriz)
        ag.quantum_int = QuantumWalkInterno()
        ag.verlet_int  = VerletInterno()
        ag.estat_int   = EstatisticaInterna()
        ag.genetico    = GeneticoInterno(n_ilhas=2, tam=20, geracoes=20)
        ag.validador   = ValidadorCobertura()
        ag.vetores     = {
            k: np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
            for k in self.PESOS
        }
        return ag

    # =========================================================
    # STATUS E LOG
    # =========================================================
    def _log(self, tipo: str, msg: str):
        entrada = {
            "ts":   datetime.now().strftime("%H:%M:%S"),
            "tipo": tipo,
            "msg":  msg,
        }
        self.log.append(entrada)
        print("[AGENTE v5][{}] {}".format(tipo, msg))

    def get_status(self) -> Dict[str, Any]:
        return {
            "estado":          self.estado,
            "total_concursos": self.n,
            "ultima_exec":     self.ultima_exec,
            "metricas":        self.metricas,
            "pesos_modulos":   self.PESOS,
            "filtros": {
                "soma":      [self.SOMA_MIN,   self.SOMA_MAX],
                "pares":     [self.PARES_MIN,  self.PARES_MAX],
                "primos":    [self.PRIMOS_MIN, self.PRIMOS_MAX],
                "fibonacci": [self.FIB_MIN,    self.FIB_MAX],
                "borda":     [self.BORDA_MIN,  self.BORDA_MAX],
            },
            "historico_aprendizado": len(self.historico_aprendizado),
            "log_recente": self.log[-15:],
        }

    def get_log(self) -> List[Dict]:
        return self.log[-100:]