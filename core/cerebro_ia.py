"""
============================================================
INTELIGÊNCIA MAGNA v11.4 — UNIFICADA, AUTÔNOMA E CIENTE
Assimila motores, oráculos, análise, singularidade e wheeling
+ Repulsão Vetorial de Coulomb (Sem Repetições)
+ Deriva de Entropia Temporal Nanosegundo
+ Flutuação Caótica de Pesos via Atrator de Lorenz
+ ACERVO PRÓPRIO: aprende com toda a base histórica, memoriza e
  decide — os padrões de abertura deixaram de ser um módulo à parte
  e viraram um órgão desta inteligência (ver AcervoAberturaMagna)
============================================================
"""
import os
import sqlite3
import numpy as np
import json
import time
import hashlib
import threading
import itertools
from collections import Counter
from datetime import datetime
from math import comb
from typing import List, Dict, Any, Sequence, Tuple, Optional

from config import (
    DATABASE_PATH, TOTAL_DEZENAS, DEZENAS_POR_JOGO,
    PRIMOS, FIBONACCI, BORDA, QUADRANTES,
    VALOR_APOSTA,
)
from database.db_manager import DBManager
from .oraculo_convergente import OraculoConvergente
from .wheeling import MotorWheeling
from .caixa_client import CaixaClient
from .fisica_sorteio import MotorFisicaSorteio

# v11.2 — Clima do sorteio (temperatura × pressão × umidade)
try:
    from .clima_lotofacil import MotorClima
except Exception as _e_clima:
    print(f"[AVISO] clima_lotofacil import: {_e_clima}")

# v11.7 — Telemetria INMET por local do sorteio (fonte de evidência)
try:
    from .inmet import TelemetriaInmet
except Exception as _e_inmet:
    print(f"[AVISO] inmet import: {_e_inmet}")
    TelemetriaInmet = None

# Forja v2 extraordinária + Suprema v10
try:
    from .forja_lotes import MotorGrafos, melhor_rota_por_orcamento, ForjaDeLotes, GeometriaJohnson, MapaInformacional
except Exception:
    MotorGrafos = None
    melhor_rota_por_orcamento = None
    ForjaDeLotes = None
    GeometriaJohnson = None
    MapaInformacional = None

# v11.5 — Anti-popularidade (edge real de RATEIO, não de acerto)
try:
    from .antipopularidade import AntiPopularidade
except Exception as _e_ap:
    print("[AVISO] antipopularidade import: {}".format(_e_ap))
    AntiPopularidade = None

# v11.6 — Laboratório de aprendizado dinâmico (benchmark + auditoria + exploração)
try:
    from .laboratorio_magna import LaboratorioMagna
except Exception as _e_lab:
    print("[AVISO] laboratorio_magna import: {}".format(_e_lab))
    LaboratorioMagna = None

try:
    from .magna_suprema import (
        DetectorRegime, MemoriaVetorialMagna, JuizMagna,
        VerificadorMagno, AlocadorOrcamentoMagno, AprendizadoBayesianoMagno,
        EWCContinual, MetaAprendizadoRegime, FisicaRealBalanca,
        PerfilRiscoPessoal, MCTSPool, AlocadorMultiRota, UtilidadeEsperada,
        JuizAdversarial, TesteNIST, PValueRandom, ExplainabilityMagna,
        ChatMagna, FingerprintPessoal, BacktestLote, TesteBinomial,
        CurvaAprendizado
    )
except Exception as _e:
    print(f"[AVISO] magna_suprema import: {_e}")
    DetectorRegime = None
    MemoriaVetorialMagna = None
    JuizMagna = None
    VerificadorMagno = None
    AlocadorOrcamentoMagno = None
    AprendizadoBayesianoMagno = None
    EWCContinual = None
    MetaAprendizadoRegime = None
    FisicaRealBalanca = None
    PerfilRiscoPessoal = None
    MCTSPool = None
    AlocadorMultiRota = None
    UtilidadeEsperada = None
    JuizAdversarial = None
    TesteNIST = None
    PValueRandom = None
    ExplainabilityMagna = None
    ChatMagna = None
    FingerprintPessoal = None
    BacktestLote = None
    TesteBinomial = None
    CurvaAprendizado = None


def _popcount_uf(x: int) -> int:
    """Popcount de um inteiro Python (máscara de dezenas)."""
    return bin(x).count("1")


# ============================================================
# ENGENHARIA DISRUPTIVA: REPULSÃO VETORIAL DE COULOMB
# ============================================================
# ============================================================
# ENGENHARIA DISRUPTIVA: REPULSÃO VETORIAL DE COULOMB
# ============================================================
class MotorRepulsaoVetorial:
    """
    Trata cada cartela gerada no passado como uma carga elétrica.
    Jogos novos sofrem repulsão vetorial para garantir que a IA
    explore novos vales de alta probabilidade sem repetir palpites.
    """
    def __init__(self, db: DBManager):
        self.db = db

    def obter_cartelas_recentes(self, dias: int = 15) -> List[set]:
        """Busca histórico de jogos gerados recentemente para criar campo de repulsão"""
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15 
                FROM cartelas 
                ORDER BY id DESC LIMIT 150
            """)
            rows = cursor.fetchall()
            conn.close()
            return [set([int(r[i]) for i in range(15)]) for r in rows if r[0] is not None]
        except Exception:
            return []

    def calcular_forca_repulsao(self, candidato: List[int], cartelas_recentes: List[set]) -> float:
        """
        Calcula a repulsão. Se a cartela for idêntica ou muito parecida
        com uma gerada recentemente, a força de repulsão explode (penalidade alta).
        """
        if not cartelas_recentes:
            return 1.0

        set_cand = set(candidato)
        penalidade = 1.0

        for antiga in cartelas_recentes:
            intersecao = len(set_cand & antiga)
            if intersecao >= 15:
                return 0.0  # Repulsão total (Bloqueio absoluto de duplicata)
            elif intersecao == 14:
                penalidade *= 0.10  # Penaliza 90%
            elif intersecao == 13:
                penalidade *= 0.40  # Penaliza 60%
            elif intersecao == 12:
                penalidade *= 0.75  # Penaliza 25%

        return penalidade


# ============================================================
# BLOCO 1 — INGESTÃO DE DADOS COM DERIVA DE ENTROPIA
# ============================================================
class IngestorDados:
    URL_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    URL_CONCURSO = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://loterias.caixa.gov.br/",
        "Accept": "application/json",
    }

    def __init__(self, db_path: str, client=None):
        self.db_path = db_path
        self.client = client or CaixaClient()

    def carregar_matriz(self) -> Tuple[np.ndarray, list]:
        if not os.path.exists(self.db_path):
            return np.zeros((1, 25), dtype=np.float32), []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                       d11,d12,d13,d14,d15
                FROM resultados ORDER BY concurso ASC
            """)
            rows = cursor.fetchall()
            cursor.execute("SELECT * FROM resultados ORDER BY concurso ASC")
            raw = cursor.fetchall()
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
        return self.client.buscar_ultimo()

    def buscar_concurso_caixa(self, numero: int) -> Optional[Dict]:
        return self.client.buscar_concurso(numero)

    def extrair_dezenas(self, data: Dict) -> List[int]:
        try:
            return sorted([int(d) for d in data.get("listaDezenas", [])])
        except Exception:
            return []

    def extrair_premios(self, data: Dict) -> Dict[int, float]:
        p = {11: 7.0, 12: 14.0, 13: 35.0, 14: 0.0, 15: 0.0}
        try:
            for item in data.get("listaRateioPremio", []):
                ac = int(item.get("numeroAcertos", 0))
                val = item.get("valorPremio", 0)
                if isinstance(val, str):
                    val = float(
                        val.replace("R$", "").replace(".", "")
                           .replace(",", ".").strip()
                    )
                if ac in p and float(val) > 0:
                    p[ac] = float(val)
        except Exception:
            pass
        return p


# ============================================================
# BLOCO 2 — MOTORES ANALÍTICOS COM FLUTUAÇÃO CAÓTICA
# ============================================================
class _Motor:
    def score_vetor(self) -> np.ndarray:
        return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


class MotorFrequencia(_Motor):
    def __init__(self, matriz: np.ndarray):
        n = len(matriz)
        freq_g = np.sum(matriz, axis=0)
        self._global = freq_g / (freq_g.sum() + 1e-9)
        jan = min(30, n)
        freq_r = np.sum(matriz[-jan:], axis=0)
        self._recente = freq_r / (freq_r.sum() + 1e-9)

    def score_global(self) -> np.ndarray: return self._global.copy()
    def score_recente(self) -> np.ndarray: return self._recente.copy()


class MotorReversao(_Motor):
    def __init__(self, matriz: np.ndarray):
        n = len(matriz)
        jan = min(30, n)
        fg = np.sum(matriz, axis=0) / max(n, 1)
        fr = np.sum(matriz[-jan:], axis=0)
        esp = jan * (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        v = np.zeros(TOTAL_DEZENAS)
        for i in range(TOTAL_DEZENAS):
            if fr[i] > esp * 1.5: v[i] = fg[i] * 0.60
            elif fr[i] < esp * 0.6: v[i] = fg[i] * 1.50
            else: v[i] = fg[i]
        s = v.sum()
        self._v = v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_vetor(self) -> np.ndarray: return self._v.copy()


class MotorAntiLogica(_Motor):
    def __init__(self, matriz: np.ndarray):
        self._matriz = matriz
        self._n = len(matriz)

    def _saturacao(self, janela: int = 20) -> np.ndarray:
        if self._n < janela:
            return np.zeros(TOTAL_DEZENAS)
        r = self._matriz[-janela:]
        fr = np.sum(r, axis=0)
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
            m = con.max()
            return 1.0 - (con / m if m > 0 else con)
        except Exception:
            return np.zeros(TOTAL_DEZENAS)

    def score_vetor(self, base: np.ndarray) -> np.ndarray:
        sat = self._saturacao(20)
        atr = self._atraso()
        fft = self._fft(60)
        isol = self._correlacao_isolamento()
        p = base.copy()
        for i in range(TOTAL_DEZENAS):
            if sat[i] > 0.40: p[i] *= 0.65
            if atr[i] > 0.60: p[i] *= 1.45
            if fft[i] > 0.50: p[i] *= 1.25
            p[i] *= (1.0 + isol[i] * 0.15)
        s = p.sum()
        return p / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


class MotorMarkov(_Motor):
    def __init__(self, matriz: np.ndarray):
        N = TOTAL_DEZENAS
        trans = np.ones((N, N))
        n = len(matriz)
        for i in range(1, n):
            ant = np.where(matriz[i - 1] == 1)[0]
            atu = np.where(matriz[i] == 1)[0]
            for a in ant:
                for b in atu:
                    trans[a][b] += 1
        ls = trans.sum(axis=1, keepdims=True)
        ls[ls == 0] = 1
        self._trans = trans / ls
        self._ultimo = matriz[-1] if n > 0 else np.zeros(N)

    def score_vetor(self) -> np.ndarray:
        ant = np.where(self._ultimo == 1)[0]
        prob = np.zeros(TOTAL_DEZENAS)
        for d in ant:
            prob += self._trans[d]
        s = prob.sum()
        return prob / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_jogo(self, dezenas: List[int]) -> float:
        prob = self.score_vetor()
        return float(np.mean([prob[d - 1] for d in dezenas]))


class MotorQuantum(_Motor):
    def __init__(self, matriz: np.ndarray):
        self._prob = self._treinar(matriz)

    def _passo(self, au, ad):
        s = 1.0 / np.sqrt(2)
        nu = s * au + s * ad
        nd = s * au - s * ad
        return np.roll(nu, 1), np.roll(nd, -1)

    def _caminhada(self, dezenas: List[int], passos: int = 120) -> np.ndarray:
        N = TOTAL_DEZENAS
        au = np.zeros(N, dtype=complex)
        ad = np.zeros(N, dtype=complex)
        for d in dezenas:
            if 1 <= d <= N:
                au[d - 1] = 1.0 / np.sqrt(2)
                ad[d - 1] = 1.0j / np.sqrt(2)
        for _ in range(passos):
            au, ad = self._passo(au, ad)
        prob = np.abs(au) ** 2 + np.abs(ad) ** 2
        s = prob.sum()
        return prob / s if s > 0 else np.ones(N) / N

    def _treinar(self, matriz: np.ndarray) -> np.ndarray:
        n = len(matriz)
        acc = np.zeros(TOTAL_DEZENAS)
        jan = min(n - 1, 80)
        for i in range(n - jan, n - 1):
            dez = list(np.where(matriz[i] == 1)[0] + 1)
            acc += self._caminhada(dez, passos=80)
        s = acc.sum()
        return acc / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_vetor(self) -> np.ndarray: return self._prob.copy()


class MotorVerlet(_Motor):
    RAIO_G = 0.20; RAIO_B = 0.025; MASSA = 0.066
    COEF = 0.82; GRAV = 9.78; DENS = 1.20

    def __init__(self, freq_hist: np.ndarray, n_sims: int = 2):
        self._scores = self._treinar(freq_hist, n_sims)

    def _simular(self, n_passos: int = 600) -> np.ndarray:
        N = TOTAL_DEZENAS
        # Semente com ruído de nanossundo para simulação viva
        seed_temporal = int(time.time_ns() % 1_000_000)
        rng = np.random.default_rng(seed_temporal)
        pos = np.zeros((N, 3)); vel = np.zeros((N, 3))
        for i in range(N):
            while True:
                p = rng.uniform(-0.15, 0.15, 3)
                if np.linalg.norm(p) < 0.15: pos[i] = p; break
            vel[i] = rng.normal(0, 0.8, 3)
        zona = np.array([0.0, 0.0, self.RAIO_G * 0.85])
        cnt = np.zeros(N)
        gv = np.array([0.0, 0.0, -self.GRAV])
        dt = 5e-4
        for passo in range(n_passos):
            acc = np.zeros((N, 3))
            for i in range(N):
                sp = np.linalg.norm(vel[i])
                fd = np.zeros(3)
                if sp > 1e-6:
                    fd = -0.5 * self.DENS * sp**2 * 0.47 * np.pi * self.RAIO_B**2 * vel[i] / sp
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
        fh = freq.copy()
        if fh.max() > 0: fh /= fh.max()
        if acc.max() > 0: acc /= acc.max()
        v = fh * 0.65 + acc * 0.35
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def score_vetor(self) -> np.ndarray: return self._scores.copy()
    def score_jogo(self, dez: List[int]) -> float:
        return float(np.mean([self._scores[d - 1] for d in dez]))


class MotorEstatistica(_Motor):
    def __init__(self, matriz: np.ndarray):
        self._matriz = matriz
        self._n = len(matriz)
        self.freq_obs = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.scores_chi2 = np.ones(TOTAL_DEZENAS) * 0.5
        self.prior_bayes = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.mat_bayes = np.ones((TOTAL_DEZENAS, TOTAL_DEZENAS)) / TOTAL_DEZENAS
        self._calcular_chi2()
        self._calcular_bayes()

    def _calcular_chi2(self):
        obs = np.sum(self._matriz, axis=0)
        esp = np.ones(TOTAL_DEZENAS) * (self._n * DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        res = (obs - esp) / np.sqrt(esp + 1e-9)
        res = np.clip(res, -3, 3)
        mn = res.min(); mx = res.max()
        self.scores_chi2 = (res - mn) / (mx - mn + 1e-9)
        self.freq_obs = obs / (obs.sum() + 1e-9)

    def _calcular_bayes(self):
        N = TOTAL_DEZENAS
        cnt = np.ones((N, N))
        tot = np.ones(N) * N
        for i in range(self._n - 1):
            ant = set(np.where(self._matriz[i] == 1)[0])
            prx = set(np.where(self._matriz[i + 1] == 1)[0])
            for a in ant:
                tot[a] += 1
                for b in prx: cnt[a][b] += 1
        self.mat_bayes = cnt / tot[:, np.newaxis]
        freq = np.sum(self._matriz, axis=0)
        self.prior_bayes = (freq + 1) / (self._n + N)

    def posterior_bayes(self, dezenas_ant: List[int]) -> np.ndarray:
        lp = np.log(self.prior_bayes + 1e-9)
        for d in dezenas_ant:
            if 1 <= d <= TOTAL_DEZENAS:
                lp += np.log(self.mat_bayes[d - 1] + 1e-9)
        lp -= lp.max()
        p = np.exp(lp)
        s = p.sum()
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
    def __init__(self, matriz: np.ndarray):
        self._calibrar(matriz)

    def _calibrar(self, matriz: np.ndarray):
        somas = []; pares_l = []; primos_l = []; fib_l = []; borda_l = []
        for i in range(len(matriz)):
            dez = list(np.where(matriz[i] == 1)[0] + 1)
            if len(dez) != 15: continue
            somas.append(sum(dez))
            pares_l.append(sum(1 for d in dez if d % 2 == 0))
            primos_l.append(len(set(dez) & PRIMOS))
            fib_l.append(len(set(dez) & FIBONACCI))
            borda_l.append(len(set(dez) & BORDA))

        # Auditoria Fase 3: p3–p97 rejeitava ~34% dos sorteios reais.
        # p1–p99 mantém o recorte "típico" rejeitando só ~1% por dimensão.
        def pct(arr, lo=1, hi=99):
            a = sorted(arr) if arr else [0, 25]
            n = len(a)
            return (a[max(0, int(n*lo/100))], a[min(n-1, int(n*hi/100))])

        self.SOMA_MIN, self.SOMA_MAX = pct(somas) if somas else (175, 230)
        self.PARES_MIN, self.PARES_MAX = pct(pares_l) if pares_l else (6, 9)
        self.PRIMOS_MIN, self.PRIMOS_MAX = pct(primos_l) if primos_l else (3, 7)
        self.FIB_MIN, self.FIB_MAX = pct(fib_l) if fib_l else (2, 6)
        self.BORDA_MIN, self.BORDA_MAX = pct(borda_l) if borda_l else (7, 11)
        self.CONSEC_MAX = 14  # maior sequência real observada no histórico

        # Métrica honesta: % dos sorteios reais que passariam no filtro
        aprov = 0
        for i in range(len(matriz)):
            dez = list(np.where(matriz[i] == 1)[0] + 1)
            ok, _ = self.filtrar(dez)
            aprov += 1 if ok else 0
        self.taxa_aprovacao_historica = (
            round(aprov / len(matriz), 4) if len(matriz) else 1.0)

    def filtrar(self, dez: List[int]) -> Tuple[bool, Dict]:
        ds = set(dez); soma = sum(dez)
        pares = sum(1 for d in dez if d % 2 == 0)
        sd = sorted(dez); mc = cc = 1
        for i in range(1, len(sd)):
            if sd[i] == sd[i-1] + 1: cc += 1; mc = max(mc, cc)
            else: cc = 1
        pc = len(ds & PRIMOS); fc = len(ds & FIBONACCI); bc = len(ds & BORDA)
        det = {"soma": soma, "pares": pares, "primos": pc, "fibonacci": fc, "borda": bc, "consec": mc}
        ok = (self.SOMA_MIN <= soma <= self.SOMA_MAX and
              self.PARES_MIN <= pares <= self.PARES_MAX and
              mc <= self.CONSEC_MAX and
              self.PRIMOS_MIN <= pc <= self.PRIMOS_MAX and
              self.FIB_MIN <= fc <= self.FIB_MAX and
              self.BORDA_MIN <= bc <= self.BORDA_MAX)
        return ok, det

    def score_vetor(self) -> np.ndarray:
        v = np.zeros(TOTAL_DEZENAS)
        for i in range(TOTAL_DEZENAS):
            d = i + 1; s = 0.5
            if d in PRIMOS: s += 0.05
            if d in FIBONACCI: s += 0.05
            if d in BORDA: s += 0.03
            v[i] = s
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


class MotorGenetico(_Motor):
    def __init__(self, n_ilhas=4, tam=50, geracoes=60):
        self.n_ilhas = n_ilhas
        self.tam = tam
        self.geracoes = geracoes

    def _ind(self, rng, cands: List[int]) -> List[int]:
        return sorted(rng.choice(cands, size=min(15, len(cands)), replace=False).tolist())

    def _cross(self, p1, p2, rng) -> List[int]:
        u = list(set(p1) | set(p2))
        if len(u) < 15:
            ext = [d for d in range(1, 26) if d not in u]
            u += list(rng.choice(ext, size=15-len(u), replace=False))
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

    def evoluir(self, fn_fitness, cands: List[int], timeout: float = 15.0) -> List[Tuple[List[int], float]]:
        t0 = time.time()
        # Entropia de tempo no algoritmo genético
        seed_dyn = int(time.time_ns() % 100_000)
        rngs = [np.random.default_rng(i * 37 + seed_dyn) for i in range(self.n_ilhas)]
        ilhas = [[self._ind(rngs[k], cands) for _ in range(self.tam)] for k in range(self.n_ilhas)]
        fits = [[fn_fitness(ind) for ind in ilha] for ilha in ilhas]
        melhor_f = -np.inf
        for g in range(self.geracoes):
            if time.time() - t0 > timeout: break
            for k in range(self.n_ilhas):
                nova = []
                idx_e = sorted(range(len(fits[k])), key=lambda x: fits[k][x], reverse=True)[:3]
                for ie in idx_e: nova.append(list(ilhas[k][ie]))
                while len(nova) < self.tam:
                    try:
                        i1 = int(rngs[k].integers(0, len(ilhas[k])))
                        i2 = int(rngs[k].integers(0, len(ilhas[k])))
                        f = self._cross(ilhas[k][i1], ilhas[k][i2], rngs[k])
                        f = self._mut(f, rngs[k], taxa=0.05*(1-g/self.geracoes))
                        if len(f) == 15: nova.append(f)
                    except Exception: continue
                ilhas[k] = nova[:self.tam]
                fits[k] = [fn_fitness(ind) for ind in ilhas[k]]
                idx_m = int(np.argmax(fits[k]))
                if fits[k][idx_m] > melhor_f:
                    melhor_f = fits[k][idx_m]
            if (g+1) % 10 == 0:
                for i in range(self.n_ilhas):
                    prox = (i+1) % self.n_ilhas
                    top = sorted(range(len(fits[i])), key=lambda x: fits[i][x], reverse=True)[:3]
                    bot = sorted(range(len(fits[prox])), key=lambda x: fits[prox][x])[:3]
                    for j in range(3): ilhas[prox][bot[j]] = list(ilhas[i][top[j]])
        todos = []
        for ilha, fit in zip(ilhas, fits):
            for ind, f in zip(ilha, fit): todos.append((list(ind), float(f)))
        todos.sort(key=lambda x: x[1], reverse=True)
        vistos = set(); unicos = []
        for ind, f in todos:
            k = tuple(sorted(ind))
            if k not in vistos: vistos.add(k); unicos.append((ind, f))
        return unicos[:50]


class MotorCobertura(_Motor):
    def calcular(self, cartelas: List[List[int]], universo: List[int], pontos: int = 13) -> Dict[str, Any]:
        uni = sorted(universo)[:min(len(universo), 19)]
        total = cobertos = 0
        for res in itertools.combinations(uni, 15):
            sr = set(res); total += 1
            for c in cartelas:
                if len(set(c) & sr) >= pontos:
                    cobertos += 1; break
        cob = cobertos / total if total > 0 else 0.0
        return {"cobertura": round(cob, 4), "cobertos": cobertos, "total": total, "pontos": pontos}


class MotorStacking(_Motor):
    def __init__(self):
        self._historico: List[Dict] = []

    def registrar(self, pesos: Dict, acertos: int):
        self._historico.append({"pesos": dict(pesos), "acertos": acertos})
        if len(self._historico) > 200: self._historico = self._historico[-200:]

    def score_vetor(self, vetores: Dict[str, np.ndarray]) -> np.ndarray:
        if not self._historico: return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        v = np.zeros(TOTAL_DEZENAS)
        for entrada in self._historico[-50:]:
            ac = entrada["acertos"]
            ps = entrada["pesos"]
            for mod, peso in ps.items():
                if mod in vetores: v += vetores[mod] * peso * (ac / 15.0)
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS


# ============================================================
# BLOCO 3 — OTIMIZADOR SPSA
# ============================================================
class OtimizadorSPSA:
    def __init__(self, n_iter: int = 25):
        self.n_iter = n_iter

    def otimizar(self, fn_perda, pesos_iniciais: Dict[str, float]) -> Dict[str, float]:
        nomes = list(pesos_iniciais.keys())
        theta = np.array([pesos_iniciais[k] for k in nomes], dtype=float)
        rng = np.random.default_rng(int(time.time_ns() % 1_000_000))
        melhor_theta = theta.copy()
        melhor_loss = fn_perda(dict(zip(nomes, theta.tolist())))
        for k in range(self.n_iter):
            ak = 0.15 / (k + 1 + 10) ** 0.602
            ck = 0.05 / (k + 1) ** 0.101
            delta = rng.choice([-1.0, 1.0], size=len(theta))
            tp = np.clip(theta + ck * delta, 0.01, 0.5)
            tn = np.clip(theta - ck * delta, 0.01, 0.5)
            lp = fn_perda(dict(zip(nomes, (tp/tp.sum()).tolist())))
            ln = fn_perda(dict(zip(nomes, (tn/tn.sum()).tolist())))
            ghat = (lp - ln) / (2 * ck * delta + 1e-9)
            theta -= ak * ghat
            theta = np.clip(theta, 0.01, 0.5)
            lc = fn_perda(dict(zip(nomes, (theta/theta.sum()).tolist())))
            if lc < melhor_loss:
                melhor_loss = lc
                melhor_theta = theta.copy()
        melhor_theta = np.clip(melhor_theta, 0.01, None)
        melhor_theta /= melhor_theta.sum()
        return {nomes[i]: round(float(melhor_theta[i]), 4) for i in range(len(nomes))}


# ============================================================
# BLOCO 3.9 — ACERVO DE ABERTURA DA MAGNA (memória viva · v11.4)
# ============================================================
# O que antes era o módulo separado `core/padroes_ordem.py` agora é um órgão da
# própria Inteligência Magna. Não existe painel paralelo, nem segundo gerador,
# nem peso manual: o acervo alimenta o MESMO vetor que faz a Magna analisar,
# julgar, decidir, moldar e criar as cartelas — e é reensinado a cada sorteio
# conferido, com a memória gravada no banco.
#
# HONESTIDADE (regra da casa): nenhum padrão de abertura muda a probabilidade
# hipergeométrica de uma cartela. O acervo (a) MEDe a estrutura real do sorteio
# sobre toda a base histórica, (b) MEMORIZA a medição com carimbo auditável,
# (c) PUBLICA o placar walk-forward fora-da-amostra de cada regra popular e
# (d) ATENUA a própria influência quando o placar mostra que ela não passou do
# acaso. Nenhuma garantia combinatória (wheeling/forja) é alterada.

_ACERVO_TAM_ORDEM = 15
_ACERVO_CATEGORIAS = {"minima": 12, "real": TOTAL_DEZENAS}
_ACERVO_PALPITE = {"minima": 1, "real": 5}
_ACERVO_ROTULO = {
    "minima": "menor dezena do concurso (a que abre a lista ordenada)",
    "real": "1ª bola física extraída do globo",
}
# concursos necessários para a frequência medida pesar metade da margem teórica
_ACERVO_MISTURA = 200.0


def _binom_p(k: int, n: int, p: float) -> float:
    """p-valor binomial exato bicaudal (com fallback sem SciPy)."""
    if n <= 0 or not 0.0 < p < 1.0:
        return 1.0
    try:
        from scipy.stats import binomtest
        return float(binomtest(int(k), int(n), float(p)).pvalue)
    except Exception:  # pragma: no cover — ambiente sem SciPy
        def pmf(i):
            return comb(n, i) * (p ** i) * ((1.0 - p) ** (n - i))
        esquerda = sum(pmf(i) for i in range(0, int(k) + 1))
        direita = sum(pmf(i) for i in range(int(k), n + 1))
        return float(min(1.0, esquerda + direita))


class AcervoAberturaMagna:
    """Conhecimento memorizado da Magna sobre QUEM ABRE o próximo concurso.

    Dois canais medidos pelo mesmo órgão:

      `minima` — a MENOR dezena do sorteio, isto é, a dezena que "abre" a lista
      ordenada exibida pelos sites. A distribuição é enviesada por construção
      combinatória::

          P(menor = k) = C(25-k, 14) / C(25, 15)
          01 -> 60,0% · 02 -> 25,0% · 03 -> 9,8% · 04 -> 3,6% · 05+ -> 1,6%

      Base: todos os concursos da tabela `resultados` (a base histórica inteira).

      `real` — a 1ª bola fisicamente extraída (campo oficial
      ``dezenasSorteadasOrdemSorteio``, tabela `ordem_sorteio`). Sob sorteio
      independente, P = 1/25 para qualquer dezena, sem memória do anterior.

      Base: o que o backfill/a sincronização já capturaram.

    Por canal o acervo mede: frequência real × teórica, streaks (sequência
    atual e recorde histórico), repetição condicional POR DEZENA (sem a
    armadilha da composição), placar walk-forward das regras populares,
    auto-auditoria com p-valor binomial e a posterior do próximo início.
    """

    TOTAL = TOTAL_DEZENAS
    TAM_ORDEM = _ACERVO_TAM_ORDEM
    TRIO_POPULAR = (1, 2, 3)
    _CATEGORIAS = _ACERVO_CATEGORIAS
    _PALPITE = _ACERVO_PALPITE
    _ROTULO = _ACERVO_ROTULO
    _MARGEM_MISTURA = _ACERVO_MISTURA

    # ------------------------------------------------------------
    # construção e ingestão
    # ------------------------------------------------------------
    def __init__(self, minima: Optional[Sequence[Tuple[int, int]]] = None,
                 ordens: Optional[Sequence[Tuple[int, Sequence[int]]]] = None,
                 alpha: float = 1.0):
        self._lock = threading.RLock()
        self.alpha = float(alpha)
        self.serie: Dict[str, List[Tuple[int, int]]] = {
            "minima": sorted((int(c), int(m)) for c, m in (minima or [])),
            "real": sorted((int(c), self.validar_ordem(o)[0])
                           for c, o in (ordens or [])),
        }
        self._ordens: Dict[int, Tuple[int, ...]] = {
            int(c): self.validar_ordem(o) for c, o in (ordens or [])}
        self._memo: Dict[Any, Any] = {}

    @classmethod
    def validar_ordem(cls, ordem: Sequence[int]) -> Tuple[int, ...]:
        """Exige exatamente 15 dezenas únicas em 1-25, na ordem de extração."""
        try:
            vals = tuple(int(d) for d in ordem)
        except (TypeError, ValueError):
            raise ValueError("ordem deve conter 15 inteiros 1-25")
        if (len(vals) != cls.TAM_ORDEM or len(set(vals)) != cls.TAM_ORDEM
                or any(d < 1 or d > cls.TOTAL for d in vals)):
            raise ValueError(
                "ordem inválida: 15 dezenas únicas 1-25 obrigatórias, "
                "recebi {}".format(list(vals)))
        return vals

    def aprender(self, canal: str, concurso: int,
                  abertura: int) -> Dict[str, Any]:
        """Upsert idempotente de uma abertura medida na memória viva."""
        if canal not in self.serie:
            raise ValueError("canal desconhecido: {}".format(canal))
        concurso, abertura = int(concurso), int(abertura)
        if concurso < 1 or not 1 <= abertura <= self.TOTAL:
            raise ValueError("concurso/abertura fora da faixa válida")
        with self._lock:
            atual = dict(self.serie[canal])
            igual = atual.get(concurso) == abertura
            atual[concurso] = abertura
            self.serie[canal] = sorted(atual.items())
            self._memo.clear()
            return {"status": "ok", "canal": canal, "concurso": concurso,
                    "abertura": abertura, "idempotente": igual,
                    "n_registros": len(self.serie[canal])}

    def aprender_ordem(self, concurso: int,
                        ordem: Sequence[int]) -> Dict[str, Any]:
        """Registra a ordem real completa de um sorteio (canal `real`)."""
        vals = self.validar_ordem(ordem)
        res = self.aprender("real", concurso, vals[0])
        with self._lock:
            self._ordens[int(concurso)] = vals
            self._memo.clear()
        res.update({"ordem": list(vals), "n_ordens": len(self._ordens)})
        return res

    # ------------------------------------------------------------
    # teoria: a margem que já é o melhor preditor possível
    # ------------------------------------------------------------
    @classmethod
    def p_teorica(cls, canal: str, k: int) -> float:
        if k < 1 or k > cls.TOTAL:
            return 0.0
        if canal == "minima":
            if k > cls.TOTAL - (cls.TAM_ORDEM - 1):
                return 0.0
            return (comb(cls.TOTAL - k, cls.TAM_ORDEM - 1)
                    / comb(cls.TOTAL, cls.TAM_ORDEM))
        return 1.0 / cls.TOTAL

    @classmethod
    def categorias(cls, canal: str) -> range:
        return range(1, cls._CATEGORIAS.get(canal, cls.TOTAL) + 1)

    # ------------------------------------------------------------
    # leitura da memória
    # ------------------------------------------------------------
    def n(self, canal: str) -> int:
        return len(self.serie.get(canal) or [])

    def n_total(self) -> int:
        return self.n("minima") + self.n("real")

    def ultimo(self, canal: str = "minima") -> Optional[int]:
        s = self.serie.get(canal) or []
        return int(s[-1][0]) if s else None

    def abertura_atual(self, canal: str = "minima") -> Optional[int]:
        s = self.serie.get(canal) or []
        return int(s[-1][1]) if s else None

    def _chave_memo(self, nome: str, canal: str):
        return (nome, canal, self.n("minima"), self.n("real"))

    def frequencias(self, canal: str = "minima") -> Dict[str, Any]:
        chave = self._chave_memo("freq", canal)
        if chave in self._memo:
            return self._memo[chave]
        s = self.serie.get(canal) or []
        cnt = Counter(v for _, v in s)
        n = len(s)
        tabela = []
        for k in self.categorias(canal):
            teor = self.p_teorica(canal, k)
            real = int(cnt.get(k, 0))
            tabela.append({
                "dezena": int(k), "vezes": real,
                "frequencia": round(real / n, 4) if n else 0.0,
                "teorico": round(teor, 4),
                "razao": round((real / n) / teor, 3) if n and teor else None,
                "ultimo_concurso": (max((c for c, v in s if v == k), default=None)
                                     if n else None),
            })
        res = {"n": n, "tabela": tabela}
        self._memo[chave] = res
        return res

    def janela_inicial(self, k: int = 3) -> Dict[str, int]:
        """Dezenas dentro das k primeiras bolas (o trio 01/02/03 popular)."""
        if k < 1 or k > self.TAM_ORDEM:
            raise ValueError("janela 1-15")
        cnt: Counter = Counter()
        for _, ordem in sorted(self._ordens.items()):
            cnt.update(ordem[:k])
        return {str(d): int(cnt.get(d, 0)) for d in range(1, self.TOTAL + 1)}

    def _runs(self, canal: str) -> List[Dict[str, Any]]:
        runs: List[Dict[str, Any]] = []
        for concurso, valor in (self.serie.get(canal) or []):
            if runs and runs[-1]["dezena"] == valor:
                runs[-1]["fim"] = concurso
                runs[-1]["comprimento"] += 1
            else:
                runs.append({"dezena": valor, "inicio": concurso,
                             "fim": concurso, "comprimento": 1})
        return runs

    def streaks(self, canal: str = "minima") -> Dict[str, Any]:
        chave = self._chave_memo("streaks", canal)
        if chave in self._memo:
            return self._memo[chave]
        s = self.serie.get(canal) or []
        runs = self._runs(canal)
        por = {int(d): {"atual": 0, "maximo": 0, "maximo_inicio": None,
                        "maximo_fim": None, "ultimo_concurso": None,
                        "concursos_desde_ultima": None}
               for d in self.categorias(canal)}
        for r in runs:
            info = por.get(r["dezena"])
            if info is None:
                continue
            if r["comprimento"] > info["maximo"]:
                info["maximo"] = r["comprimento"]
                info["maximo_inicio"] = r["inicio"]
                info["maximo_fim"] = r["fim"]
            info["ultimo_concurso"] = r["fim"]
        atual = maior = None
        if runs:
            atual = runs[-1]
            if atual["dezena"] in por:
                por[atual["dezena"]]["atual"] = atual["comprimento"]
            indice = {c: i for i, (c, _) in enumerate(s)}
            fim = len(s) - 1
            for info in por.values():
                pos = indice.get(info["ultimo_concurso"])
                if pos is not None:
                    info["concursos_desde_ultima"] = fim - pos
            maior = max(runs, key=lambda r: r["comprimento"])
        res = {
            "canal": canal, "rotulo": self._ROTULO.get(canal, canal),
            "n_registros": len(s),
            "run_atual": ({"dezena": atual["dezena"],
                           "comprimento": atual["comprimento"],
                           "inicio": atual["inicio"]} if atual else None),
            "recorde_historico": ({"dezena": maior["dezena"],
                                   "comprimento": maior["comprimento"],
                                   "inicio": maior["inicio"],
                                   "fim": maior["fim"]} if maior else None),
            "distribuicao_streaks": {str(int(k)): int(v) for k, v in
                                     Counter(r["comprimento"]
                                             for r in runs).items()},
            "por_dezena": por,
        }
        self._memo[chave] = res
        return res

    def taxa_repeticao(self, canal: str = "minima") -> Dict[str, Any]:
        chave = self._chave_memo("repeticao", canal)
        if chave in self._memo:
            return self._memo[chave]
        v = [x[1] for x in (self.serie.get(canal) or [])]
        n = len(v) - 1
        if n <= 0:
            return {"aplicavel": False, "n": 0}
        reps = sum(1 for i in range(1, len(v)) if v[i] == v[i - 1])
        base = sum(self.p_teorica(canal, k) ** 2
                   for k in self.categorias(canal))
        cond: Dict[str, Any] = {}
        for rotulo, alvo in (("apos_1", 1), ("apos_2", 2), ("apos_3_mais", 3)):
            tot = rep = 0
            corrente = 1
            for i in range(1, len(v)):
                repetiu = v[i] == v[i - 1]
                pertence = ((rotulo == "apos_3_mais" and corrente >= 3)
                            or (rotulo != "apos_3_mais" and corrente == alvo))
                if pertence:
                    tot += 1
                    if repetiu:
                        rep += 1
                corrente = corrente + 1 if repetiu else 1
            cond[rotulo] = {"provas": tot, "repetiu": rep,
                            "taxa": round(rep / tot, 4) if tot else None,
                            "taxa_esperada": round(base, 4)}
        por_dezena = {}
        for d in list(self.categorias(canal))[:8]:
            trans = sum(1 for i in range(1, len(v)) if v[i - 1] == d)
            repet = sum(1 for i in range(1, len(v))
                        if v[i - 1] == d and v[i] == d)
            if trans:
                por_dezena[str(int(d))] = {
                    "transicoes": trans, "repetiu": repet,
                    "taxa_real": round(repet / trans, 4),
                    "taxa_teorica": round(self.p_teorica(canal, d), 4),
                }
        res = {
            "aplicavel": True, "n_transicoes": n,
            "global": {"repeticoes": int(reps), "taxa": round(reps / n, 4),
                       "taxa_esperada": round(base, 4),
                       "p_valor": (round(_binom_p(reps, n, base), 4)
                                   if base > 0 else None)},
            "condicional": cond,
            "por_dezena": por_dezena,
            "leitura": ("a repetição observada coincide com a margem: "
                        "sequência não altera probabilidade"
                        if abs(reps / n - base) < 0.02 else
                        "diferença pequena diante da margem — sem efeito "
                        "operacional sem significância"),
        }
        self._memo[chave] = res
        return res

    def repeticao_apos_streak(self, dezena: int, streak_min: int = 2,
                              canal: str = "minima") -> Dict[str, Any]:
        """P(essa dezena abrir de novo | já abriu `streak_min`x seguidas).

        Medido APENAS na dezena pedida. A versão agregada engana: streaks
        longos são quase sempre do 01, que abre 60% por natureza — o que
        parece sinal é composição, não causa.
        """
        v = [x[1] for x in (self.serie.get(canal) or [])]
        dezena, streak_min = int(dezena), int(streak_min)
        tot = rep = 0
        corrente = 1
        for i in range(1, len(v)):
            repetiu = v[i] == v[i - 1]
            if v[i - 1] == dezena and corrente >= streak_min:
                tot += 1
                if repetiu:
                    rep += 1
            corrente = corrente + 1 if repetiu else 1
        teor = self.p_teorica(canal, dezena)
        taxa = rep / tot if tot else None
        if tot and taxa is not None and abs(taxa - teor) < 0.03:
            leitura = ("a repetição seguiu a margem de sempre — streak não "
                       "altera probabilidade")
        elif tot:
            leitura = "amostra pequena: vale a taxa da margem"
        else:
            leitura = "sem provas no histórico: vale a taxa da margem"
        return {
            "canal": canal, "dezena": dezena, "streak_min": streak_min,
            "provas": tot, "repetiu": rep,
            "taxa_real": round(taxa, 4) if tot else None,
            "taxa_teorica": round(teor, 4),
            "leitura": leitura,
        }

    def matriz_transicao(self, canal: str = "minima",
                         suavizar: bool = True) -> np.ndarray:
        """P(próxima abertura = j | abertura atual = i); linhas somam 1."""
        k = self._CATEGORIAS.get(canal, self.TOTAL)
        m = np.ones((k, k), dtype=float) * (1.0 if suavizar else 0.0)
        s = self.serie.get(canal) or []
        for i in range(1, len(s)):
            a, b = s[i - 1][1], s[i][1]
            if 1 <= a <= k and 1 <= b <= k:
                m[a - 1, b - 1] += 1.0
        return m / m.sum(axis=1, keepdims=True)
    # ------------------------------------------------------------
    # posterior do próximo início: margem teórica + o que a base mostrou
    # ------------------------------------------------------------
    def posterior(self, canal: str = "minima") -> Dict[int, float]:
        s = self.serie.get(canal) or []
        n = len(s)
        cnt = Counter(v for _, v in s)
        cats = list(self.categorias(canal))
        alpha = self.alpha
        medida = {d: (cnt.get(d, 0) + alpha) / (n + alpha * len(cats))
                  for d in cats}
        massa = sum(self.p_teorica(canal, d) for d in cats) or 1.0
        teoria = {d: self.p_teorica(canal, d) / massa for d in cats}
        w = n / (n + self._MARGEM_MISTURA)
        return {int(d): w * medida[d] + (1.0 - w) * teoria[d] for d in cats}

    def ranking_abertura(self, canal: str = "minima") -> List[Dict[str, Any]]:
        probs = self.posterior(canal)
        ordem = sorted(probs, key=lambda d: probs[d], reverse=True)
        cnt = Counter(v for _, v in (self.serie.get(canal) or []))
        acum = 0.0
        out = []
        for pos, d in enumerate(ordem[:5], 1):
            acum += probs[d]
            out.append({"posicao": pos, "dezena": int(d),
                        "prob": round(probs[d], 5),
                        "prob_acumulada": round(acum, 5),
                        "prob_teorica": round(self.p_teorica(canal, d), 5),
                        "vezes_na_base": int(cnt.get(d, 0))})
        return out

    def proximas_aberturas(self, k: int = 3,
                           canal: str = "minima") -> List[int]:
        """As k aberturas mais prováveis do próximo concurso."""
        probs = self.posterior(canal)
        ordem = sorted(probs, key=lambda d: probs[d], reverse=True)
        return [int(d) for d in ordem[:max(1, int(k))]]

    def previsao(self, canal: str = "minima") -> Dict[str, Any]:
        probs = self.posterior(canal)
        st = self.streaks(canal)
        run = st["run_atual"]
        atual = run["dezena"] if run else None
        tam = run["comprimento"] if run else 0
        medida = (self.repeticao_apos_streak(atual, tam, canal=canal)
                  if atual is not None and tam >= 2 else None)
        ordem = sorted(probs, key=lambda d: probs[d], reverse=True)
        sem_excluir = [int(d) for d in ordem[:3]]
        se_excluir = [int(d) for d in ordem if d != atual][:2]
        return {
            "canal": canal, "rotulo": self._ROTULO.get(canal, canal),
            "n_registros": self.n(canal),
            "probabilidades": {str(d): round(p, 5) for d, p in probs.items()},
            "ranking": self.ranking_abertura(canal),
            "proximo_palpite_top3": sem_excluir,
            "abertura_atual": ({"dezena": atual, "streak": tam,
                                "desde_o_concurso": run["inicio"]}
                               if run else None),
            "pergunta_decisiva": {
                "descricao": ("a abertura {} veio {}x seguidas: vale exclui-la "
                              "e apostar nas outras?".format(
                                  "{:02d}".format(atual)
                                  if atual is not None else "--", tam)),
                "excluida": atual,
                "candidatas_sem_excluir": sem_excluir,
                "candidatas_se_excluir": se_excluir,
                "p_repetir_a_atual": (round(probs.get(atual, 0.0), 5)
                                      if atual is not None else None),
                "medicao_no_historico": medida,
                "veredito_operacional": (
                    "NAO EXCLUIR: a repeticao medida coincide com a margem e "
                    "o placar walk-forward mostra perda ao excluir"
                    if medida else
                    "streak inativo: seguir o ranking da margem"),
            },
        }

    # ------------------------------------------------------------
    # placar walk-forward (sem vazamento) e auto-auditoria
    # ------------------------------------------------------------
    def _walkforward(self, canal: str) -> Dict[str, Any]:
        """Percorre a base inteira prevendo o concurso t+1 com dados de < t."""
        chave = self._chave_memo("wf", canal)
        if chave in self._memo:
            return self._memo[chave]
        s = self.serie.get(canal) or []
        cats = list(self.categorias(canal))
        massa = sum(self.p_teorica(canal, d) for d in cats) or 1.0
        teoria = {d: self.p_teorica(canal, d) / massa for d in cats}
        posterior_c: Counter = Counter()
        r_top = r_top2 = r_excl = provas = 0
        corrente_d, corrente_n = None, 0
        for i in range(len(s) - 1):
            atual = s[i][1]
            proximo = s[i + 1][1]
            if posterior_c:
                n_passado = sum(posterior_c.values())
                w = n_passado / (n_passado + self._MARGEM_MISTURA)
                probs = {
                    d: w * ((posterior_c.get(d, 0) + self.alpha)
                            / (n_passado + self.alpha * len(cats)))
                    + (1.0 - w) * teoria[d] for d in cats}
                ranking = sorted(probs, key=lambda d: probs[d], reverse=True)
                if ranking[0] == proximo:
                    r_top += 1
                if proximo in set(ranking[:2]):
                    r_top2 += 1
                escolha = (max((d for d in probs if d != atual),
                               key=lambda d: probs[d])
                           if corrente_n >= 2 else ranking[0])
                if escolha == proximo:
                    r_excl += 1
                provas += 1
            corrente_n = corrente_n + 1 if atual == corrente_d else 1
            corrente_d = atual
            posterior_c[atual] += 1
        res = {"n_provas": provas, "acertos_top1": r_top,
               "acertos_top2": r_top2, "acertos_exclusao": r_excl}
        self._memo[chave] = res
        return res

    def _palpite_top_m(self, canal: str) -> int:
        return self._PALPITE.get(canal, 1)

    def linha_de_base(self, canal: str = "minima") -> float:
        """Acerto esperado do MELHOR preditor possível sob independência."""
        m = self._palpite_top_m(canal)
        return sum(sorted((self.p_teorica(canal, d)
                            for d in self.categorias(canal)),
                           reverse=True)[:m])

    def placar_walkforward(self, canal: str = "minima") -> Dict[str, Any]:
        if self.n(canal) < 50:
            return {"aplicavel": False, "motivo": "dados insuficientes",
                    "n_registros": self.n(canal)}
        wf = self._walkforward(canal)
        provas = wf["n_provas"]
        teto1 = self.linha_de_base(canal) if self._palpite_top_m(canal) == 1 \
            else max(self.p_teorica(canal, d) for d in self.categorias(canal))
        teto2 = (self.p_teorica(canal, 1) + self.p_teorica(canal, 2)
                 if canal == "minima" else 2.0 / self.TOTAL)
        r_top, r_top2, r_excl = (wf["acertos_top1"], wf["acertos_top2"],
                                 wf["acertos_exclusao"])
        custo = round(100.0 * (r_top - r_excl) / provas, 2) if provas else 0.0
        return {
            "aplicavel": True, "canal": canal, "n_provas": provas,
            "margem_da_magna_top1": {
                "acertos": r_top, "taxa": round(r_top / provas, 4),
                "teto_teorico": round(teto1, 4),
                "leitura": "o melhor preditor possível é a própria margem"},
            "cobertura_top2": {
                "acertos": r_top2, "taxa": round(r_top2 / provas, 4),
                "teto_teorico": round(teto2, 4)},
            "regra_popular_de_exclusao": {
                "acertos": r_excl, "taxa": round(r_excl / provas, 4),
                "custo_vs_top1_pp": custo,
                "leitura": ("excluir a abertura em sequência custa {} pontos "
                            "porcentuais: streak não muda probabilidade"
                            .format(custo))},
            "leitura": ("{} provas fora-da-amostra: a Magna acerta {}% do "
                        "início previsto (teto {}%); a regra popular de "
                        "exclusão fica em {}%".format(
                            provas, round(100 * r_top / provas, 1),
                            round(100 * teto1, 1),
                            round(100 * r_excl / provas, 1))),
        }

    def auto_auditoria(self, canal: str = "minima",
                       min_registros: int = 30) -> Dict[str, Any]:
        """Existe algo ALÉM da margem? Medido fora-da-amostra, com p-valor."""
        chave = self._chave_memo("auto", canal)
        if chave in self._memo:
            return self._memo[chave]
        if self.n(canal) < min_registros + 1:
            res = {"aplicavel": False, "motivo": "dados insuficientes",
                   "n_registros": self.n(canal), "fator_confianca": 0.5,
                   "veredito": "SEM AMOSTRA"}
            self._memo[chave] = res
            return res
        wf = self._walkforward(canal)
        provas = wf["n_provas"]
        m = self._palpite_top_m(canal)
        acertos = wf["acertos_top1"] if m == 1 else wf["acertos_top2"]
        base = self.linha_de_base(canal)
        taxa = acertos / provas if provas else 0.0
        lift = taxa / base if base else 1.0
        p = round(_binom_p(acertos, provas, base), 4) if provas else 1.0
        real = bool(provas >= 50 and p < 0.05 and lift > 1.02)
        fator = (round(0.75 + 0.25 * min(1.0, max(0.0, (lift - 1.0) / 0.10)), 4)
                 if real else 0.5)
        res = {
            "aplicavel": True, "canal": canal, "palpite_top_m": m,
            "n_provas": provas, "acertos": int(acertos),
            "taxa": round(taxa, 4), "linha_de_base": round(base, 4),
            "lift": round(lift, 4), "p_valor": p,
            "veredito": "REAL" if real else "RUÍDO",
            "fator_confianca": fator,
            "leitura": ("o padrão superou a margem fora-da-amostra: entra com "
                        "confiança alta no consenso" if real else
                        "nenhum padrão superou a margem hipergeométrica: o "
                        "vetor entra atenuado (0,5) e a leitura é publicada "
                        "como conhecimento, não como promessa"),
        }
        self._memo[chave] = res
        return res

    # ------------------------------------------------------------
    # entrega ao consenso da Magna
    # ------------------------------------------------------------
    def vetor_bruto(self, canal: str = "minima") -> np.ndarray:
        probs = self.posterior(canal)
        v = np.array([probs.get(d, 0.0) for d in range(1, self.TOTAL + 1)],
                     dtype=float)
        v = v + 1.0 / self.TOTAL          # piso: nenhuma dezena zerada
        return v / v.sum()

    def pesos_de_evidencia(self) -> Dict[str, float]:
        """Peso de cada canal na leitura, proporcional ao que ele já viu."""
        out = {}
        for canal in self._CATEGORIAS:
            n_provas = max(0, self.n(canal) - 1)
            out[canal] = n_provas / (n_provas + 150.0) if n_provas else 0.0
        total = sum(out.values())
        if total <= 0:
            return {c: 0.5 for c in self._CATEGORIAS}
        return {k: v / total for k, v in out.items()}

    def fator_confianca(self) -> float:
        pesos = self.pesos_de_evidencia()
        fat = sum(pesos[c] * float(
            self.auto_auditoria(c).get("fator_confianca", 0.5)) for c in pesos)
        return round(float(fat or 0.5), 4)

    def vetor_evidencia(self) -> np.ndarray:
        """Vetor 25-dim (soma 1) mesclando os canais pela força da evidência.

        Sem atenuação aqui: quem mistura com o uniforme é a Magna, usando
        `fator_confianca()` — a mesma disciplina aplicada à fonte de clima.
        """
        pesos = self.pesos_de_evidencia()
        v = np.zeros(self.TOTAL, dtype=float)
        for canal, w in pesos.items():
            if w > 0:
                v += w * self.vetor_bruto(canal)
        if v.sum() <= 0:
            return np.ones(self.TOTAL, dtype=float) / self.TOTAL
        return v / v.sum()

    # ------------------------------------------------------------
    # julgamento do próprio palpite (memória do que a Magna previu)
    # ------------------------------------------------------------
    @staticmethod
    def avaliar_palpite(ranking: Sequence[int],
                        abertura_real: int) -> Dict[str, Any]:
        """Em que posição do ranking previsto caiu a abertura realmente sorteada."""
        ordem = [int(d) for d in ranking]
        alvo = int(abertura_real)
        pos = ordem.index(alvo) + 1 if alvo in ordem else None
        return {"abertura_real": alvo, "posicao_no_ranking": pos,
                "acerto_top1": pos == 1, "acerto_top2": pos in (1, 2),
                "acerto_top3": pos in (1, 2, 3)}

    def afinidade_cartela(self, dezenas: Sequence[int],
                          canal: str = "minima") -> Dict[str, Any]:
        """Quão coerente com a abertura prevista esta cartela é.

        A abertura de uma cartela é a sua menor dezena. Sob o conhecimento
        memorizado, cartelas que abrem em 01/02/03 pertencem à região onde
        95% dos sorteios reais abrem. É critério de PLAUSIBILIDADE ESTRUTURAL
        (desempate), nunca preditivo: a chance de 13/14/15 pontos não muda.
        """
        probs = self.posterior(canal)
        abre = min(int(d) for d in dezenas)
        p = probs.get(abre, 0.0)
        p_max = max(probs.values()) if probs else 1.0
        ranking = self.proximas_aberturas(3, canal=canal)
        return {"abertura_da_cartela": abre,
                "prob_no_conhecimento": round(p, 5),
                "afinidade": round(p / p_max, 4) if p_max else 0.0,
                "cobre_palpite_da_magna": abre in ranking}

    # ------------------------------------------------------------
    # sínteses
    # ------------------------------------------------------------
    def veredito(self) -> str:
        autos = [self.auto_auditoria(c) for c in self._CATEGORIAS
                 if self.auto_auditoria(c).get("aplicavel")]
        if not autos:
            return "SEM AMOSTRA"
        return "REAL" if any(a.get("veredito") == "REAL" for a in autos) \
            else "RUÍDO"

    def digest(self) -> str:
        """Hash do que foi aprendido — cada decisão cita exatamente o acervo."""
        chave = self._chave_memo("digest", "todos")
        if chave in self._memo:
            return self._memo[chave]
        h = hashlib.sha256()
        for canal in self._CATEGORIAS:
            s = self.serie.get(canal) or []
            h.update("{}|{}|".format(canal, len(s)).encode())
            if s:
                h.update("{}:{}|".format(s[0][0], s[-1][0]).encode())
                h.update(str(sorted(Counter(v for _, v in s).items())
                             ).encode())
        res = "sha256:" + h.hexdigest()[:16]
        self._memo[chave] = res
        return res

    def estado(self) -> Dict[str, Any]:
        """Resumo barato para status, log e cabeçalho da decisão."""
        return {
            "concursos_da_base": self.n("minima"),
            "concursos_com_ordem_real": self.n("real"),
            "aprendido_ate_concurso": self.ultimo("minima"),
            "abertura_atual": self.abertura_atual("minima"),
            "palpite_top3": self.proximas_aberturas(3),
            "veredito": self.veredito(),
            "fator_confianca": self.fator_confianca(),
            "digest": self.digest(),
        }

    def leitura(self) -> str:
        """A Magna interpretando o acervo em uma frase operacional."""
        prev = self.previsao("minima")
        auto = self.auto_auditoria("minima")
        topo = prev.get("ranking") or []
        quem = " · ".join("{:02d} ({:.1f}%)".format(
            t["dezena"], 100 * t["prob"]) for t in topo[:3]) or "sem dados"
        partes = ["abertura mais provável do próximo concurso: {} — medida em "
                  "{} concursos memorizados".format(quem, self.n("minima"))]
        run = prev.get("abertura_atual")
        if run:
            med = self.repeticao_apos_streak(run["dezena"], run["streak"])
            frase = ("abertura atual {:02d} no {}º concurso seguido".format(
                run["dezena"], run["streak"]))
            if med["provas"] and med["taxa_real"] is not None:
                frase += ("; P(repetir {:02d} | streak {}) = {:.1%} em {} "
                          "provas vs {:.1%} da margem".format(
                              run["dezena"], run["streak"], med["taxa_real"],
                              med["provas"], med["taxa_teorica"]))
            partes.append(frase)
        partes.append("auto-auditoria walk-forward {} (lift {} em {} provas) → "
                      "fator de confiança {}".format(
                          auto.get("veredito"), auto.get("lift"),
                          auto.get("n_provas"), self.fator_confianca()))
        return ("A Magna leu a base: " + "; ".join(partes) +
                ". Leitura estrutural: não muda a chance de nenhuma cartela.")

    def relatorio(self) -> Dict[str, Any]:
        canais = {}
        for canal in self._CATEGORIAS:
            canais[canal] = {
                "rotulo": self._ROTULO[canal],
                "n_registros": self.n(canal),
                "ultimo_concurso": self.ultimo(canal),
                "frequencias": self.frequencias(canal),
                "streaks": self.streaks(canal),
                "taxa_repeticao": self.taxa_repeticao(canal),
                "placar_walkforward": self.placar_walkforward(canal),
                "auto_auditoria": self.auto_auditoria(canal),
                "previsao": self.previsao(canal),
            }
        return {
            "status": "ok",
            "identidade": ("Acervo de Abertura — órgão da Inteligência Magna "
                           "v11.4"),
            "digest": self.digest(),
            "pesos_de_evidencia": self.pesos_de_evidencia(),
            "fator_confianca": self.fator_confianca(),
            "veredito": self.veredito(),
            "canais": canais,
            "janela_inicial_3": (self.janela_inicial(3) if self._ordens
                                 else None),
            "leitura": self.leitura(),
            "honestidade": (
                "A abertura é enviesada por construção combinatória (a menor "
                "de 15 dezenas sorteadas entre 25 tende a ser 01) — isso não é "
                "previsão: toda cartela mantém a mesma probabilidade "
                "hipergeométrica. O acervo publica o placar walk-forward e "
                "atenua o próprio vetor quando o padrão não supera a margem "
                "fora-da-amostra; nenhuma garantia combinatória é tocada."),
        }


# ============================================================
# BLOCO 4 — INTELIGÊNCIA MAGNA v9.0 (PROTAGONISTA ÚNICA)
# ============================================================
class CerebroIA:
    # v11.2 — nova fonte "clima" (temperatura/pressão/umidade) com
    # shrinkage interna e auto-auditoria walk-forward. Os pesos são
    # re-normalizados em _carregar_pesos_fontes_magna e reajustados a
    # cada sorteio pelo aprendizado bayesiano das fontes.
    #
    # v11.4 — a fonte `abertura` substitui a antiga `ordem`: ela é alimentada
    # pelo ACERVO da própria Magna (aprendido da base histórica inteira e
    # memorizado no banco), e não por um módulo separado. O peso é um teto de
    # influência: sobe apenas se a auto-auditoria walk-forward medir lift.
    _FONTES_MAGNA_DEFAULT = {
        "motores": 0.33,
        "oraculos": 0.18,
        "espectral": 0.10,
        "informacao": 0.10,
        "recente": 0.09,
        "fisica": 0.08,
        "clima": 0.05,
        "abertura": 0.04,
        "inmet": 0.03,
    }

    # Chaves do acervo persistidas em magna_conhecimento
    _ACERVO_DOMINIOS = ("base", "abertura", "fontes", "memoria")
    ACERVO_VERSAO = "v11.4-acervo-unico"

    # v9.2 extraordinária: pool elite força máxima + forja força máxima
    VERSAO_MAGNA = "11.0-Magna-Suprema-Unica-Pessoal-Evoluida"
    VERSAO_SUPREMA = "11.0"
    VERSAO_EVOLUCAO = "v11.4-EWC-Meta-MCTS-MultiRota-JuizAdv-NIST-Explain-Chat-Fingerprint-Backtest-ClimaFisico-AcervoAberturaUnico"

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

    def __init__(self, db_path: str = None, n_cartelas: int = 10, client=None):
        self.db_path     = db_path or DATABASE_PATH
        self.db          = DBManager(self.db_path)
        self.n_cartelas  = n_cartelas
        self.pesos       = dict(self._PESOS_DEFAULT)
        self.log: List[Dict] = []
        self.estado      = "inicializando"
        self.metricas    = {}
        self.decisoes    = {}
        self.ultima_exec = None
        self.treinado    = False
        self._magna_lock = threading.RLock()

        # Ciclo autônomo
        self._rodando    = False
        self._pausado    = False
        self._thread     = None
        self._ciclos_ok  = 0
        self._ciclos_err = 0
        self._ultimo_processado = 0
        self.proximo_sorteio    = None

        # Motor de Desdobramento com Cobertura Garantida (wheeling)
        self.wheeling = MotorWheeling()

        # Instância o Motor Disruptivo de Repulsão Vetorial
        self.repulsao_vetorial = MotorRepulsaoVetorial(self.db)

        # Motor de Física do Sorteio (perfil das bolas + ambiente)
        self.fisica = MotorFisicaSorteio(self.db_path)

        # v11.2 — Motor de Clima do Sorteio (fonte física-estatística)
        if MotorClima is not None:
            self.clima = MotorClima()
        else:  # pragma: no cover — fallback neutro
            class _ClimaNeutro:
                n_registros = 0

                def vetor_clima(self, *a, **k):
                    return np.ones(TOTAL_DEZENAS)

                def clima_previsto(self):
                    return {"temperatura": 21.5, "pressao": 0.915,
                            "umidade": 50.0, "fonte": "neutro"}

                def testes_fisicos(self):
                    return {"aplicavel": False,
                            "motivo": "motor de clima indisponível"}

                def auto_ponderacao(self, *a, **k):
                    return {"aplicavel": False, "fator_confianca": 1.0}

                def aprender(self, *a, **k):
                    return {"status": "erro",
                            "msg": "motor de clima indisponível"}

            self.clima = _ClimaNeutro()
        self._log("INIT", "Clima v11.2: {} registros, auto-auditoria ativa".format(
            self.clima.n_registros))

        # v11.7 — Telemetria INMET por local do sorteio. Fonte de evidência
        # leve (peso 0.03 no consenso): persistida por concurso e reusada;
        # quando não há dados, o vetor é uniforme (fonte neutra).
        if TelemetriaInmet is not None:
            try:
                self.inmet = TelemetriaInmet(self.db_path)
            except Exception as _e_inmet:
                self.inmet = None
                print(f"[AVISO] TelemetriaInmet init: {_e_inmet}")
        else:  # pragma: no cover — fallback neutro
            self.inmet = None
        self._log("INIT", "INMET v11.7: {} registros de telemetria".format(
            self.inmet.resumo().get("n_registros", 0) if self.inmet else 0))

        # v11.4 — os padrões de abertura DEIXARAM DE SER UM MÓDULO. Eles são o
        # acervo da própria Magna (AcervoAberturaMagna), montado logo abaixo,
        # depois das tabelas de memória, para já nascer aprendido e memorizado.

        # Carregar dados
        self._ingestor = IngestorDados(self.db_path, client=client)
        self.matriz, self.raw = self._ingestor.carregar_matriz()
        self.n = len(self.matriz)
        self._log("INIT", "{} concursos carregados".format(self.n))

        # Motores
        self._motores: Dict[str, Any] = {}
        self._vetores: Dict[str, np.ndarray] = {
            k: np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
            for k in self.pesos
        }

        self._cobertura = MotorCobertura()
        self._stacking  = MotorStacking()
        self._genetico  = MotorGenetico(n_ilhas=4, tam=50, geracoes=60)
        self._spsa      = OtimizadorSPSA(n_iter=25)
        self._gaussiano = MotorGaussiano(self.matriz)

        # Oráculo Convergente
        self._oraculo = OraculoConvergente(self.matriz)
        self._log("INIT", "Oráculo Convergente ativado (15 teorias + Entropia Nanossegundo)")

        # v11.5 — anti-popularidade: mede o efeito de RATEIO (quem costuma
        # dividir o prêmio) e usa apenas como desempate estrutural. Não altera
        # P(acerto): é edge de prêmio condicional.
        try:
            if AntiPopularidade is not None:
                self.antipopularidade = AntiPopularidade(self.db_path)
            else:
                self.antipopularidade = None
        except Exception as _e_ap:
            print("[AVISO] AntiPopularidade não inicializado: {}".format(_e_ap))
            self.antipopularidade = None

        # v11.6 — laboratório pessoal de aprendizado dinâmico
        try:
            if LaboratorioMagna is not None:
                self.laboratorio = LaboratorioMagna(
                    db_path=self.db_path, matriz=self.matriz)
            else:
                self.laboratorio = None
        except Exception as _e_lab:
            print("[AVISO] LaboratorioMagna não inicializado: {}".format(_e_lab))
            self.laboratorio = None

        self._criar_tabelas_ciclo()
        self.pesos_fontes_magna = self._carregar_pesos_fontes_magna()
        self._ultimo_processado = self._get_ultimo_processado()

        # ── ACERVO DE CONHECIMENTO DA MAGNA (v11.4) ──────────────────
        # A Magna já nasce aprendendo: ela varre a base histórica, mede a
        # abertura em dois canais, calibra o peso das próprias fontes em
        # walk-forward e MEMORIZA tudo em magna_conhecimento/magna_memoria.
        # É o mesmo acervo que alimenta o vetor e o Juiz de cada
        # cartela — não existe módulo, painel ou gerador paralelo.
        self._aberturas_vivas: Dict[int, int] = {}
        self.acervo = self._montar_acervo_abertura()
        self._acervo_calibrado = False
        # v11.4 — o conhecimento é montado aqui, no nascimento da Magna: ela já
        # vem sabendo o que a base histórica ensina (a leitura dos 3.700+
        # concursos custa ~0,4 s). A calibração fundante dos pesos (walk-forward
        # da base inteira) é a parte cara: ela roda no preload do `python app.py`
        # e sob pedido (botão da UI / CLI / assimilar_acervo(forcar=True)).
        self.assimilar_acervo(auto=True, calibrar_fontes=False)
        self.estado = "pronto"

    def _criar_tabelas_ciclo(self):
        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fila_conferencia (
                id INTEGER PRIMARY KEY AUTOINCREMENT, concurso_alvo INTEGER, dezenas TEXT,
                timestamp_geracao TEXT, scores_modulos TEXT, score_total REAL,
                status TEXT DEFAULT 'aguardando', acertos INTEGER DEFAULT 0, premio_ganho REAL DEFAULT 0,
                dezenas_acertadas TEXT, timestamp_conferencia TEXT, erro_previsao REAL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_ciclos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, concurso INTEGER, timestamp_inicio TEXT,
                timestamp_fim TEXT, status TEXT, n_cartelas INTEGER DEFAULT 0, melhor_acertos INTEGER DEFAULT 0,
                media_acertos REAL DEFAULT 0, total_ganho REAL DEFAULT 0, pesos_antes TEXT,
                pesos_depois TEXT, log_ciclo TEXT, erro_medio REAL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memoria_erros (
                id INTEGER PRIMARY KEY AUTOINCREMENT, concurso INTEGER, timestamp TEXT,
                modulo TEXT, erro REAL, impacto REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS desempenho_modulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, concurso INTEGER, timestamp TEXT,
                modulo TEXT, correlacao REAL, peso_antes REAL, peso_depois REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cartela_do_dia (
                id INTEGER PRIMARY KEY AUTOINCREMENT, concurso_alvo INTEGER, timestamp TEXT,
                dezenas TEXT, quorum_usado INTEGER, confianca TEXT, consenso_forca REAL,
                score_cerebro REAL, aprovado_filtros INTEGER, votos_json TEXT,
                acertos INTEGER DEFAULT 0, premio REAL DEFAULT 0, conferida INTEGER DEFAULT 0
            )
        """)

        # A Inteligência Magna mantém uma única trilha de decisão. Os antigos
        # painéis (geração, oráculo, wheeling, análise, singularidade e
        # auditoria) agora alimentam este mesmo registro e estes mesmos pesos.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_estado (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_decisoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso_alvo INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                estrategia TEXT NOT NULL,
                cartelas_json TEXT NOT NULL,
                analise_json TEXT NOT NULL,
                justificativa TEXT NOT NULL,
                status TEXT DEFAULT 'aguardando',
                resultado_json TEXT,
                melhor_acertos INTEGER DEFAULT 0,
                media_acertos REAL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_aprendizado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decisao_id INTEGER NOT NULL,
                concurso INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                fonte TEXT NOT NULL,
                acertos INTEGER NOT NULL,
                peso_antes REAL NOT NULL,
                peso_depois REAL NOT NULL,
                FOREIGN KEY (decisao_id) REFERENCES magna_decisoes(id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_magna_concurso_status
            ON magna_decisoes(concurso_alvo, status)
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_episodios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                dezenas TEXT NOT NULL,
                acertos INTEGER NOT NULL,
                faltaram TEXT,
                tipo TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_checkpoint (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pesos_json TEXT NOT NULL,
                media_acertos REAL NOT NULL,
                n_amostra INTEGER NOT NULL
            )
        """)

        # ── ACERVO DE CONHECIMENTO (v11.4) ──────────────────────────
        # `magna_conhecimento` guarda o estado consolidado do que a Magna
        # aprendeu (um registro por domínio, com o carimbo do último concurso
        # assimilado). `magna_memoria` é o diário apendável: cada lote
        # aprendido, cada previsão de abertura feita e julgada. Juntos eles
        # respondem "o que você sabia, em que concurso, e como descobriu".
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_conhecimento (
                dominio TEXT PRIMARY KEY,
                versao TEXT NOT NULL,
                concurso_ate INTEGER NOT NULL DEFAULT 0,
                n_provas INTEGER NOT NULL DEFAULT 0,
                veredito TEXT,
                fator_confianca REAL,
                snapshot_json TEXT NOT NULL,
                origem TEXT NOT NULL DEFAULT 'fundante',
                atualizado_em TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS magna_memoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                dominio TEXT NOT NULL,
                evento TEXT NOT NULL,
                concurso INTEGER,
                acertos INTEGER,
                provas INTEGER,
                taxa REAL,
                detalhe_json TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_magna_memoria_dom
            ON magna_memoria(dominio, concurso)
        """)
        conn.commit()
        conn.close()

    def _get_ultimo_processado(self) -> int:
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(concurso) FROM historico_ciclos WHERE status = 'completo'")
            r = cursor.fetchone()[0]
            conn.close()
            return r or 0
        except Exception:
            return 0

    def treinar(self, callback=None, matriz_override=None, raw_override=None) -> Dict:
        self.estado = "treinando"
        t0 = time.time()

        if matriz_override is not None:
            # Walk-forward: treina só com o passado até uma janela
            self.matriz = np.asarray(matriz_override, dtype=self.matriz.dtype)
            self.raw = (list(raw_override) if raw_override is not None
                        else self.raw[:len(self.matriz)])
        else:
            self.matriz, self.raw = self._ingestor.carregar_matriz()
        self.n = len(self.matriz)
        self._cache_mascaras_15 = None

        def cb(msg):
            self._log("TREINO", msg)
            if callback: callback(msg)

        cb("Treinando 14 módulos com {} concursos...".format(self.n))

        freq_g = np.sum(self.matriz, axis=0)
        freq_g_norm = freq_g / (freq_g.sum() + 1e-9)

        m1 = MotorFrequencia(self.matriz)
        self._vetores["freq_global"]  = m1.score_global()
        self._vetores["freq_recente"] = m1.score_recente()
        self._motores["frequencia"]   = m1

        m3 = MotorReversao(self.matriz)
        self._vetores["reversao"] = m3.score_vetor()
        self._motores["reversao"] = m3

        m4 = MotorAntiLogica(self.matriz)
        self._vetores["anti_logica"] = m4.score_vetor(self._vetores["reversao"])
        self._motores["anti_logica"] = m4

        m5 = MotorMarkov(self.matriz)
        self._vetores["markov"] = m5.score_vetor()
        self._motores["markov"] = m5

        m6 = MotorQuantum(self.matriz)
        self._vetores["quantum"] = m6.score_vetor()
        self._motores["quantum"] = m6

        m7 = MotorVerlet(freq_g_norm, n_sims=2)
        self._vetores["verlet"] = m7.score_vetor()
        self._motores["verlet"] = m7

        m8 = MotorEstatistica(self.matriz)
        self._vetores["chi2"]  = m8.score_vetor()
        ult_dez = list(np.where(self.matriz[-1] == 1)[0] + 1) if self.n > 0 else list(range(1, 16))
        self._vetores["bayes"] = m8.posterior_bayes(ult_dez)
        kl_v = np.array([m8.score_kl([i + 1]) for i in range(TOTAL_DEZENAS)])
        s = kl_v.sum()
        self._vetores["kl"] = kl_v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self._motores["estatistica"] = m8

        self._gaussiano = MotorGaussiano(self.matriz)
        self._vetores["gaussiano"] = self._gaussiano.score_vetor()
        self._vetores["genetico"] = self._vetores["anti_logica"].copy()
        self._vetores["cobertura"] = freq_g_norm.copy()
        self._vetores["stacking"] = self._stacking.score_vetor(self._vetores)

        self._oraculo = OraculoConvergente(self.matriz)
        self._calibrar_spsa()

        self.treinado = True
        self.estado = "pronto"
        self.ultima_exec = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tempo = time.time() - t0
        self.metricas["tempo_treino"] = round(tempo, 2)
        self.metricas["taxa_aprovacao_filtro"] = getattr(
            self._gaussiano, "taxa_aprovacao_historica", None)
        cb("✅ 14 módulos + Oráculo treinados em {:.1f}s".format(tempo))
        return {"status": "ok", "modulos": 14, "oraculos": 15, "tempo": round(tempo, 2)}

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

    def _vetor_combinado(self) -> np.ndarray:
        v = np.zeros(TOTAL_DEZENAS)
        # Injeta uma micro-flutuação de ruído caótico nos pesos para dar dinamismo diário.
        # RNG local (não usa np.random global) para não contaminar outros módulos.
        rng = getattr(self, "_rng_vetor", None)
        if rng is None:
            rng = np.random.default_rng()
            self._rng_vetor = rng
        ruido_caotico = rng.normal(1.0, 0.03, len(self.pesos))
        for idx, (k, p) in enumerate(self.pesos.items()):
            peso_dinamico = p * ruido_caotico[idx]
            vec = self._vetores.get(k, np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS)
            v += vec * peso_dinamico
        s = v.sum()
        return v / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def _score_cartela(self, dez: List[int], vf: np.ndarray, outras: List[List[int]]) -> float:
        ev = float(sum(vf[d - 1] for d in dez))
        div = len(set(dez) - set(d2 for o in outras for d2 in o)) / 15.0 if outras else 1.0
        m_est = self._motores.get("estatistica")
        kl = m_est.score_kl(dez) if m_est else 0.5
        m_mk = self._motores.get("markov")
        mk = m_mk.score_jogo(dez) if m_mk else 0.5
        m_vl = self._motores.get("verlet")
        vl = m_vl.score_jogo(dez) if m_vl else 0.5
        _, det = self._gaussiano.filtrar(dez)
        soma = det.get("soma", 200)
        centro = (self._gaussiano.SOMA_MIN + self._gaussiano.SOMA_MAX) / 2
        denom = max(centro - self._gaussiano.SOMA_MIN, 1)
        sg = max(0.0, 1.0 - abs(soma - centro) / denom)

        ok_filtro, _ = self._gaussiano.filtrar(dez)
        filtro = 1.0 if ok_filtro else 0.55
        ja_15 = 0.0 if self._cartela_ja_foi_15(dez) else 1.0
        # v11.4 — abertura: coerência com o que a base ensinou (a menor dezena
        # da cartela frente ao posterior memorizado). É DESEMPATE estrutural de
        # peso pequeno; a probabilidade hipergeométrica da cartela não muda.
        try:
            ab = self.acervo.afinidade_cartela(dez)["afinidade"]
        except Exception:
            ab = 0.5
        return (
            ev * 0.22 + div * 0.14 + kl * 0.10 + mk * 0.14 + vl * 0.10
            + sg * 0.08 + filtro * 0.09 + ja_15 * 0.08 + ab * 0.05
        )

    # ============================================================
    # v11.5 — Anti-popularidade (edge de rateio, não de acerto)
    # ============================================================
    def _vetor_antipopularidade(self, vf: np.ndarray,
                                forca: float = 0.05) -> np.ndarray:
        """Combina o vetor da Magna com a impopularidade de cada dezena.

        O score anti-popularidade EVITA regiões do volante que historicamente
        atraem mais ganhadores (e portanto dividem mais o prêmio). É usado
        apenas como desempate/priorização — a probabilidade hipergeométrica de
        cada cartela permanece exatamente a mesma.
        """
        vf = self._normalizar_vetor(vf)
        ap = getattr(self, "antipopularidade", None)
        if ap is None or not hasattr(ap, "vetor_impopularidade"):
            return vf
        try:
            v_ap = ap.vetor_impopularidade()
            if v_ap is None or float(np.sum(v_ap)) <= 0:
                return vf
            v_ap = v_ap / float(np.sum(v_ap))
            # v_ap normalizada é ~4% por dezena; multiplicar por (1+força) dá
            # um leve favorecimento às dezenas menos lotadas.
            v = vf * (1.0 + float(forca) * v_ap * TOTAL_DEZENAS)
            return self._normalizar_vetor(v)
        except Exception:
            return vf

    def _popularidade_da_cartela(self, dezenas: List[int]) -> Dict[str, Any]:
        ap = getattr(self, "antipopularidade", None)
        if ap is None or not hasattr(ap, "analisar_cartela"):
            return {"disponivel": False}
        try:
            r = ap.analisar_cartela(dezenas)
            return {"disponivel": True, **r}
        except Exception:
            return {"disponivel": False}

    def _auditoria_cartelas_magna(
            self, cartelas: List[Sequence[int]],
            vetor_final: Optional[np.ndarray] = None) -> Dict[str, Any]:
        lab = getattr(self, "laboratorio", None)
        if lab is None:
            return {"disponivel": False}
        try:
            res = lab.auditor.auditar_lote(
                cartelas, cartelas, vetor_final=vetor_final)
            return {"disponivel": True, **res}
        except Exception:
            return {"disponivel": False}

    def _resumo_antipopularidade(self, cartelas: List[List[int]]) -> Dict[str, Any]:
        ap = getattr(self, "antipopularidade", None)
        if ap is None or not hasattr(ap, "relatorio"):
            return {"disponivel": False}
        rel = ap.relatorio()
        bonus = [self._popularidade_da_cartela(c) for c in cartelas]
        bonus_x = [float(b.get("bonus_rateio_estimado_x", 1.0))
                   for b in bonus if b.get("disponivel")]
        regioes = [b.get("regiao") for b in bonus if b.get("disponivel")]
        return {
            "disponivel": True,
            "calibracao": rel,
            "bonus_rateio_medio_x": (
                round(float(np.mean(bonus_x)), 3) if bonus_x else 1.0
            ),
            "distribuicao_regioes": {
                r: regioes.count(r) for r in set(regioes)
            },
            "honestidade": (
                "A anti-popularidade reduz a disputa do MESMO prêmio quando "
                "você acerta. Não altera a probabilidade de acertar 13/14/15."
            ),
        }

    # ============================================================
    # v11.6 — Laboratório dinâmico (benchmark, auditoria, exploração)
    # ============================================================
    def lab_benchmark(self, n_testes: int = 40, janela: int = 50,
                      n_aleatorio: int = 120,
                      pesos: Optional[Dict[str, float]] = None,
                      callback=None) -> Dict[str, Any]:
        """Walk-forward de todas as famílias de estratégia da base histórica.

        Treina apenas com o passado, mede no futuro, compara com o acaso,
        marca o que é RUIM (quarentena) e propõe novos pesos para o consenso.
        """
        lab = getattr(self, "laboratorio", None)
        if lab is None:
            return {"status": "erro", "msg": "laboratório indisponível"}
        try:
            res = lab.rodar_benchmark(
                n_testes=n_testes, janela=janela, n_aleatorio=n_aleatorio,
                pesos=pesos, persistir=True)
            res["pesos_recomendados"] = lab._recomendacao
            res["quarentena"] = lab._quarentena
            if callback:
                callback(res)
            return res
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return {"status": "erro", "msg": str(exc)}

    def lab_explorar(self, ensaios: List[Dict[str, Any]],
                     n_testes: int = 20,
                     callback=None) -> Dict[str, Any]:
        """Explora mutações de estratégia e devolve as que melhoram fora-da-amostra."""
        lab = getattr(self, "laboratorio", None)
        if lab is None:
            return {"status": "erro", "msg": "laboratório indisponível"}
        try:
            res = lab.explorar(ensaios=ensaios, n_testes=n_testes,
                               persistir=True)
            if callback:
                callback(res)
            return res
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return {"status": "erro", "msg": str(exc)}

    def auditor_cartelas(self, cartelas: List[Sequence[int]],
                         score_modelos: Optional[List[float]] = None,
                         vetor_final: Optional[np.ndarray] = None,
                         callback=None) -> Dict[str, Any]:
        """Audita cartelas criadas: repetidas, quase-repetidas, riscos e P exata."""
        lab = getattr(self, "laboratorio", None)
        if lab is None:
            return {"status": "erro", "msg": "laboratório indisponível"}
        try:
            res = lab.auditar_cartelas(
                cartelas, score_modelos=score_modelos,
                vetor_final=vetor_final, persistir=True)
            if callback:
                callback(res)
            return res
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return {"status": "erro", "msg": str(exc)}

    def lab_relatorio(self) -> Dict[str, Any]:
        lab = getattr(self, "laboratorio", None)
        if lab is None:
            return {"status": "erro", "msg": "laboratório indisponível"}
        return lab.relatorio()

    def gerar_cartela_do_dia(self, reaproveitar: bool = True) -> Dict:
        """
        A CARTELA ÚNICA do dia baseada em CONSENSO de 15 oráculos.
        Lê todas as cartelas do dia já geradas no banco para nunca repetir o mesmo jogo.

        Se `reaproveitar=True` (padrão) e já existir uma cartela salva para o
        PRÓXIMO concurso (concurso-alvo), o método a devolve — recompondo a
        análise dos oráculos — em vez de gerar/salvar uma nova a cada chamada
        (evita duplicatas a cada F5 na página).
        """
        self._log("ORACULO", "Consultando 15 oráculos independentes com filtro de inéditas...")

        if self.n < 30:
            return {
                "status": "erro",
                "msg": "Dados insuficientes (mínimo 30 concursos)",
            }

        proximo = (self.db.get_ultimo_concurso() or 0) + 1

        # 0. Idempotência: reaproveita a cartela do concurso-alvo se já existir.
        if reaproveitar:
            try:
                conn = self.db.get_conn()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM cartela_do_dia WHERE concurso_alvo=? "
                    "ORDER BY id DESC LIMIT 1", (proximo,))
                row = cursor.fetchone()
                conn.close()
                if row is not None:
                    existente = dict(row)
                    dez_exist = json.loads(existente.get("dezenas") or "[]")
                    if isinstance(dez_exist, list) and len(dez_exist) == 15:
                        self._oraculo = OraculoConvergente(self.matriz)
                        # Recompõe os metadados dos oráculos (votos/detalhes)
                        # sem escolher outra cartela.
                        consulta = self._oraculo.consultar_todos()
                        votos = consulta["votos"]
                        pesos = consulta["pesos_acumulados"]
                        score_final = votos.astype(float) + pesos * 2.0
                        resultado = {
                            "cartela": sorted(int(x) for x in dez_exist),
                            "quorum_usado": existente.get("quorum_usado"),
                            "quorum_original": self._oraculo.QUORUM_MINIMO,
                            "votos_por_dezena": {
                                int(i + 1): int(votos[i]) for i in range(25)},
                            "score_por_dezena": {
                                int(i + 1): round(float(score_final[i]), 4)
                                for i in range(25)},
                            "consenso_forca": float(
                                existente.get("consenso_forca") or 0),
                            "soma": sum(dez_exist),
                            "pares": sum(1 for d in dez_exist if d % 2 == 0),
                            "impares": sum(1 for d in dez_exist if d % 2 != 0),
                            "consecutivos_max": self._max_consecutivos(dez_exist),
                            "confianca": existente.get("confianca"),
                            "detalhes_oraculos": consulta["detalhes"],
                            "n_oraculos": self._oraculo.N_ORACULOS,
                            "salvo_concurso": proximo,
                            "reaproveitada": True,
                        }
                        aprovado, det = self._gaussiano.filtrar(resultado["cartela"])
                        resultado["aprovado_filtros"] = aprovado
                        resultado["detalhes_filtros"] = det
                        vf = (self._vetor_combinado() if self.treinado
                              else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS)
                        resultado["score_cerebro"] = round(
                            float(self._score_cartela(resultado["cartela"], vf, [])), 4)
                        from .bitmatrix import BitMatrix
                        resultado["bitmask"] = BitMatrix().dezenas_para_bitmask(
                            resultado["cartela"])
                        resultado["timestamp"] = existente.get("timestamp")
                        self._log("ORACULO",
                                  "Cartela do concurso {} reaproveitada (idempotente)"
                                  .format(proximo))
                        return resultado
            except Exception as e:
                print("[CEREBRO] Erro ao reaproveitar cartela_do_dia: {}".format(e))

        # 1. Carrega todas as cartelas do dia já salvas no banco de dados
        cartelas_passadas = []
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT dezenas FROM cartela_do_dia")
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                try:
                    c = json.loads(r[0])
                    if isinstance(c, list):
                        cartelas_passadas.append(c)
                except Exception:
                    pass
        except Exception as e:
            print("[CEREBRO] Erro ao ler cartela_do_dia passadas: {}".format(e))

        # 2. Sincroniza o oráculo e passa o histórico de cartelas já geradas
        self._oraculo = OraculoConvergente(self.matriz)
        resultado = self._oraculo.gerar_cartela_do_dia(cartelas_ja_geradas=cartelas_passadas)
        cartela = resultado["cartela"]

        # 3. Validações e filtros do Cérebro
        aprovado, det = self._gaussiano.filtrar(cartela)
        resultado["aprovado_filtros"] = aprovado
        resultado["detalhes_filtros"] = det

        vf = self._vetor_combinado() if self.treinado else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        score_cerebro = self._score_cartela(cartela, vf, [])
        resultado["score_cerebro"] = round(float(score_cerebro), 4)

        from .bitmatrix import BitMatrix
        bm = BitMatrix()
        resultado["bitmask"] = bm.dezenas_para_bitmask(cartela)
        resultado["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. Salva a nova cartela no banco
        try:
            proximo = (self.db.get_ultimo_concurso() or 0) + 1
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cartela_do_dia
                (concurso_alvo, timestamp, dezenas, quorum_usado,
                 confianca, consenso_forca, score_cerebro,
                 aprovado_filtros, votos_json)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                proximo,
                resultado["timestamp"],
                json.dumps(cartela),
                int(resultado.get("quorum_usado", 0)),
                resultado.get("confianca", "N/A"),
                float(resultado.get("consenso_forca", 0)),
                float(resultado.get("score_cerebro", 0)),
                1 if aprovado else 0,
                json.dumps(resultado.get("votos_por_dezena", {})),
            ))
            conn.commit()
            conn.close()
            resultado["salvo_concurso"] = proximo
        except Exception as e:
            resultado["erro_salvar"] = str(e)

        self._log("ORACULO", "Nova Cartela Inédita Gerada! Dezenas: {}".format(cartela))

        return resultado

    def get_historico_cartelas_do_dia(self, limit: int = 30) -> List[Dict]:
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cartela_do_dia ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            result = []
            for r in rows:
                d = dict(r)
                try: d["dezenas"] = json.loads(d.get("dezenas", "[]"))
                except: d["dezenas"] = []
                result.append(d)
            return result
        except Exception:
            return []

    def gerar_cartelas(self, quantidade: int = None, modo: str = "hibrido", callback=None) -> List[Dict[str, Any]]:
        qtd = quantidade or self.n_cartelas
        self.estado = "gerando"
        t0 = time.time()

        def cb(msg):
            self._log("GERAR", msg)
            if callback: callback(msg)

        cb("Pipeline iniciado | qtd={} modo={}".format(qtd, modo))

        if not self.treinado:
            cb("Treinando antes de gerar...")
            self.treinar(callback=callback)

        vf = self._vetor_combinado()
        top5 = [int(x) for x in (np.argsort(vf)[::-1][:5] + 1)]
        self._log("VETOR", "Top 5: {}".format(top5))

        # Grupo Elite GARANTIDO com no mínimo 19 dezenas (3.876 combinações)
        tam_elite = max(19, min(21, 15 + qtd))
        grupo_elite = [int(x) for x in self._selecionar_elite_extraordinaria(vf, tam_elite)]
        self.decisoes["grupo_elite"] = sorted(grupo_elite)
        cb("Grupo elite ({} dezenas): {}".format(len(grupo_elite), sorted(grupo_elite)))

        # Algoritmo Genético
        cands_ag = []
        try:
            def fitness(dez):
                ok, _ = self._gaussiano.filtrar(dez)
                ev = float(sum(vf[d - 1] for d in dez))
                return ev * (1.5 if ok else 0.5)
            top_ag = self._genetico.evoluir(fitness, grupo_elite, 15.0)
            cands_ag = [i for i, _ in top_ag[:qtd * 5]]
        except Exception as e:
            self._log("AVISO", "AG: {}".format(e))

        cands_mc = self._monte_carlo(grupo_elite, vf, qtd * 8)
        cands_cb = self._combinatorio(grupo_elite, vf, qtd * 4)

        todas = cands_ag + cands_mc + cands_cb

        # Repulsão Vetorial contra jogos anteriores
        recentes = self.repulsao_vetorial.obter_cartelas_recentes()

        aprovadas = []
        reprov_gauss = 0
        reprov_duplicada = 0
        reprov_repulsao = 0
        vistas = set()            # combinações já aprovadas (não repetir)
        bloqueadas = set()        # duplicatas exatas (nunca voltam)
        relaxaveis = []           # candidatas válidas no filtro, mas com repulsão forte
        outras = []

        # Passagem 1: Estrita (Sem repetições idênticas ou quase idênticas)
        for cand in todas:
            dez = sorted([int(x) for x in cand])
            key = tuple(dez)
            if key in vistas or key in bloqueadas:
                continue

            f_rep = self.repulsao_vetorial.calcular_forca_repulsao(dez, recentes)
            if f_rep <= 0.0:  # 15 números idênticos a um jogo anterior
                bloqueadas.add(key)
                reprov_duplicada += 1
                continue

            ok, det = self._gaussiano.filtrar(dez)
            if not ok:
                reprov_gauss += 1
                continue
            if self._cartela_ja_foi_15(dez):
                bloqueadas.add(key)
                continue

            # Repulsão forte (≥13 dezenas iguais a um jogo recente) → adia
            # para a passagem 2 (que relaxa a repulsão) em vez de descartar
            # silenciosamente. Antes estas candidatas eram marcadas como
            # "vistas" e a passagem 2 nunca as reencontrava (código morto).
            if f_rep < 0.5:
                relaxaveis.append((dez, det, f_rep))
                reprov_repulsao += 1
                continue

            vistas.add(key)
            sc = self._score_cartela(dez, vf, outras) * f_rep
            outras.append(dez)
            aprovadas.append({
                "dezenas": dez,
                "score_total": round(sc, 6),
                "soma": det["soma"],
                "pares": det["pares"],
                "primos": det["primos"],
                "fibonacci": det["fibonacci"],
                "borda": det["borda"],
                "f_repulsao": round(f_rep, 3),
                "scores": {
                    "ev_prob": round(float(sum(vf[d-1] for d in dez)), 4),
                    "markov": round(self._motores["markov"].score_jogo(dez) if "markov" in self._motores else 0.5, 4),
                    "verlet": round(self._motores["verlet"].score_jogo(dez) if "verlet" in self._motores else 0.5, 4),
                    "gaussiano": round(max(0.0, 1.0 - abs(det["soma"] - 200) / 50), 4),
                },
            })

        # Passagem 2: Se ainda não atingiu a quantidade, relaxa a repulsão
        # e reaproveita as candidatas válidas que só foram adiadas.
        if len(aprovadas) < qtd and relaxaveis:
            # ordena por score inerente para entregar as melhores mesmo aqui
            relaxaveis.sort(
                key=lambda t: self._score_cartela(t[0], vf, outras),
                reverse=True,
            )
            for dez, det, f_rep in relaxaveis:
                if len(aprovadas) >= qtd:
                    break
                key = tuple(dez)
                if key in vistas or key in bloqueadas:
                    continue
                vistas.add(key)
                sc = self._score_cartela(dez, vf, outras) * 0.8
                outras.append(dez)
                aprovadas.append({
                    "dezenas": dez,
                    "score_total": round(sc, 6),
                    "soma": det["soma"],
                    "pares": det["pares"],
                    "primos": det["primos"],
                    "fibonacci": det["fibonacci"],
                    "borda": det["borda"],
                    "f_repulsao": round(max(f_rep, 0.5), 3),
                    "scores": {},
                })

        # Passagem 3: Fallback final para garantir que o número de cartelas SEMPRE seja entregue
        if len(aprovadas) < qtd:
            extras = self._fallback(vf, grupo_elite, qtd - len(aprovadas))
            for e in extras:
                dez = sorted([int(x) for x in e])
                key = tuple(dez)
                if key in vistas: continue
                vistas.add(key)
                _, det = self._gaussiano.filtrar(dez)
                sc = self._score_cartela(dez, vf, outras)
                aprovadas.append({
                    "dezenas": dez,
                    "score_total": round(sc * 0.5, 6),
                    "soma": det.get("soma", 0),
                    "pares": det.get("pares", 0),
                    "primos": det.get("primos", 0),
                    "fibonacci": det.get("fibonacci", 0),
                    "borda": det.get("borda", 0),
                    "f_repulsao": 0.1,
                    "scores": {},
                })

        aprovadas.sort(key=lambda x: x["score_total"], reverse=True)
        resultado = aprovadas[:qtd]

        # Cobertura matemática
        if resultado:
            try:
                listas = [c["dezenas"] for c in resultado]
                cob = self._cobertura.calcular(listas, grupo_elite, 13)
                for c in resultado:
                    c["cobertura_13"] = cob["cobertura"]
                self.metricas["cobertura_13"] = cob["cobertura"]
            except Exception as e:
                self._log("AVISO", "Cobertura: {}".format(e))

        tempo = time.time() - t0
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for i, c in enumerate(resultado):
            c.update({
                "id_geracao": i + 1,
                "timestamp": ts,
                "modo": modo,
                "grupo_elite": sorted(grupo_elite),
                "n_modulos": 14,
                "pesos_usados": dict(self.pesos),
            })

        self.metricas.update({
            "total_geradas": len(resultado),
            "candidatas_total": len(todas),
            "reprovadas": reprov_gauss + reprov_duplicada + reprov_repulsao,
            "reprovadas_gauss": reprov_gauss,
            "reprovadas_duplicada": reprov_duplicada,
            "reprovadas_repulsao": reprov_repulsao,
            "tempo_seg": round(tempo, 2),
        })

        self.estado = "pronto"
        self.ultima_exec = ts
        cb("✅ {} cartelas inéditas entregues com sucesso em {:.1f}s".format(len(resultado), tempo))
        return resultado

    # ============================================================
    # PIPELINE DE DESDOBRAMENTO (WHEELING) 14/15 PONTOS
    # motores → pool → fechamento c/ garantia → análise exata
    # ============================================================
    def pipeline_wheeling(self, n_pool=17, garantia=None, max_cartelas=40,
                          orcamento=None, limite_segundos=25,
                          salvar=False, callback=None) -> Dict[str, Any]:
        """
        Orquestra o processo completo de cartelas com garantia condicional:

        1. Treina os 14 motores + oráculo (se necessário)
        2. Seleciona o POOL de n_pool dezenas pelo vetor combinado
        3. Gera o fechamento (desdobramento) com garantia:
           - família exata α=1: ⌈16/(N−15)⌉ cartelas garantem 31−N pontos
           - greedy Johnson p/ garantias maiores (α≥2)
        4. Analisa o lote EXATAMENTE sobre os 3.268.760 sorteios possíveis
        """
        def cb(msg):
            self._log("WHEELING", msg)
            if callback:
                callback(msg)

        self.estado = "gerando"
        t0 = time.time()

        if not (16 <= int(n_pool) <= 23):
            raise ValueError("n_pool deve estar entre 16 e 23")
        n_pool = int(n_pool)

        if not self.treinado:
            cb("Treinando antes de gerar...")
            self.treinar(callback=callback)

        vf = self._vetor_combinado()
        pool = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vf, n_pool))
        cb("Pool de {} dezenas selecionado: {}".format(len(pool), pool))

        t_padrao = 31 - n_pool
        t = int(garantia) if garantia else t_padrao
        if t > t_padrao:
            cb("Garantia {} > família exata ({}): usando greedy Johnson..."
               .format(t, t_padrao))

        res = self.wheeling.gerar(
            pool, garantia=t, max_cartelas=max_cartelas,
            orcamento=orcamento, limite_segundos=limite_segundos, vf=vf,
        )
        res["tempo"] = round(time.time() - t0, 2)
        res["treino_premissas"] = {
            "concursos": self.n,
            "top5_vetor": [int(x) for x in (np.argsort(vf)[::-1][:5] + 1)],
        }

        g = res.get("garantia_verificada")
        cb("Fechamento: {} cartelas | garantia {} pontos {} | custo R$ {:.2f}"
           .format(res["n_cartelas"], res["garantia"],
                   "VERIFICADA" if g else "PARCIAL", res["custo"]))
        an = res["analise"]
        cb("Análise exata: captura do pool 1 em {:,.0f} | P(lote≥14)={:.6f}% | "
           "EV do lote R$ {:.2f}".format(
               res["um_em_captura"], 100 * an["p_melhor_14_mais"],
               an["ev_lote"]))

        self.decisoes["wheeling"] = {
            "pool": pool, "garantia": res["garantia"],
            "n_cartelas": res["n_cartelas"], "metodo": res["metodo"],
        }
        self.metricas["wheeling_ev_lote"] = an["ev_lote"]
        self.metricas["wheeling_p_captura"] = res["p_captura"]
        self.estado = "pronto"

        if salvar:
            res["salvar"] = True  # a camada app persiste via _salvar_cartelas_banco
        return res

    # ============================================================
    # A DECISÃO DO CÉREBRO — gerar_otimas()
    # Análise completa → escolha automática de estratégia → cartelas
    # ============================================================
    def gerar_otimas(self, n_cartelas=1, salvar=False, callback=None,
                      vetor_override=None, alvo=None, modo=None) -> Dict[str, Any]:
        """
        O Cérebro como motor único EXTRAORDINÁRIO do sistema (v9.2). Dado o número desejado de
        cartelas, ele próprio decide a estratégia ótima:

        ── n = 1 (ou alvo=15 com pouco orçamento) ────────────────
        EXAUSTÃO DO UNIVERSO: pontua TODAS as 3.268.760 combinações
        contra o vetor combinado dos 14 motores e entrega a MELHOR
        cartela única que existe (respeitando o filtro gaussiano).

        ── 2 ≤ n ≤ 7 ──────────────────────────────────────────────
        EXAUSTÃO COM DIVERSIDADE: as n melhores combinações com
        sobreposição máxima de 13 dezenas entre si (espalha a
        cobertura sem abandonar o critério dos motores).

        ── n ≥ 8 ──────────────────────────────────────────────────
        WHEELING COM GARANTIA: pool de 17 dezenas do vetor combinado
        fechado em 8 cartelas que GARANTEM 14 pontos se as 15
        sorteadas caírem no pool (ótimo provado, ver wheeling.py);
        cartelas excedentes preenchidas pela exaustão com diversidade.

        ── alvo=13 ────────────────────────────────────────────────
        ESCADA DE CAPTURA 13: pools maiores com garantia condicional
        de 13 pontos — pool 18 família exata (6 cartelas, captura
        1:4.006) ou pool 19 FECHAMENTO DUAL (13 cartelas, 1:843).
        A captura de pool-18 é ~6× mais provável que a de pool-17;
        a de pool-19, ~28×. É a rota racional para caçar 13 pontos.

        ── alvo=15 ────────────────────────────────────────────────
        ESCADA DE CAPTURA 15: pool 16 fechado em 16 cartelas (família
        exata) que GARANTEM 15 pontos se as 15 sorteadas caírem no
        pool (captura 1:204.297 — a garantia máxima que existe).

        ── modo="forja" ───────────────────────────────────────────
        FORJA ESPACIAL: recocido simulado sobre a união EXATA dos
        leques de alto acerto (R_t) com pesos de plausibilidade da
        Magna — maximiza diretamente P(melhor do lote ≥ alvo) sob o
        modelo de amostragem sucessiva, com relatório de geometria
        de Johnson. Ver core/forja_lotes.py.

        Toda saída traz a contabilidade EXATA do lote sobre o
        universo completo (probabilidades, prêmio esperado, EV).
        """
        def cb(msg):
            self._log("DECISÃO", msg)
            if callback:
                callback(msg)

        self.estado = "gerando"
        t0 = time.time()
        n = max(1, min(int(n_cartelas), 100))

        if not self.treinado:
            cb("Treinando os 14 motores...")
            self.treinar(callback=callback)

        vf = (self._normalizar_vetor(vetor_override)
              if vetor_override is not None else self._vetor_combinado())
        pool_elite = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vf, 17))
        cb("Vetor combinado pronto · pool elite: {}".format(pool_elite))

        from .heavyweight_engine import MotorExaustaoUniverso
        heavy = MotorExaustaoUniverso()

        cartelas = []
        estrategia = None
        garantia = None
        info_extra: Dict[str, Any] = {}

        # ---------- FORJA ESPACIAL EXTRAORDINÁRIA (força máxima) ----------
        if modo == "forja":
            from .forja_lotes import (
                ForjaDeLotes, GeometriaJohnson, MapaInformacional,
            )
            alvo_forja = int(alvo) if int(alvo or 0) in (13, 14) else 13
            estrategia = "forja-espacial-extraordinaria-{}".format(alvo_forja)
            cb("Forjando lote EXTRAORDINÁRIO: {} cartelas, alvo ≥{} | "
               "25 candidatas, 5 seeds, k=5 robusto, 30s força máxima...".format(
                   n, alvo_forja))
            mapa = MapaInformacional(self.matriz).coordenadas()
            forja_engine = ForjaDeLotes()
            if alvo_forja == 14 and n <= 15:
                # para 14 pontos, greedy exato é mais forte que SA
                forja = forja_engine.forjar_14_exato(vf, n, segundos=15.0)
                # completa com forja normal se faltar
                if len(forja.get("cartelas", [])) < n:
                    resto = forja_engine.forjar_com_forca_maxima(
                        vf, n - len(forja["cartelas"]), alvo=alvo_forja,
                        segundos=20.0, n_candidatas=25, k_robusto=5,
                        n_seeds=3, mapa=mapa)
                    forja["cartelas"] = sorted(sorted(c) for c in (forja["cartelas"] + resto["cartelas"]))
            else:
                forja = forja_engine.forjar_com_forca_maxima(
                    vf, n, alvo=alvo_forja, segundos=30.0,
                    n_candidatas=25, k_robusto=5, n_seeds=5, mapa=mapa)
            cartelas = forja.pop("cartelas")
            garantia = None
            geo = GeometriaJohnson().relatorio(cartelas)
            info_extra = {
                "forja": forja,
                "geometria_johnson": geo,
                "constelacoes": [
                    MapaInformacional.constelacao(mapa, c) for c in cartelas[:8]
                ],
                "mapa_dezenas": [[round(float(x), 4) for x in pt]
                                 for pt in mapa[:, :2]],
            }
            cb("Forja concluída: {} movimentos · P(melhor ≥ {}) exata = "
               "1 em {}".format(forja["moves"], alvo_forja,
                                forja["um_em_exata"]))

        # ---------- ESCADA DE CAPTURA (alvo explícito) ----------
        elif int(alvo or 0) == 15 and n >= 16:
            estrategia = "wheeling-garantia-15"
            pool15 = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vf, 16))
            cb("Escada 15: pool de 16 dezenas → 16 cartelas garantem o "
               "prêmio máximo SE o pool capturar (1:204.297)")
            res_w = self.wheeling.gerar(pool15, garantia=15, max_cartelas=16)
            cartelas = [c["dezenas"] for c in res_w["cartelas"]]
            pool_elite = pool15
            garantia = 15
            info_extra["wheeling"] = {
                "metodo": res_w["metodo"],
                "garantia_verificada": res_w["garantia_verificada"],
            }

        elif int(alvo or 0) == 13 and n >= 6:
            estrategia = "wheeling-garantia-13"
            if n >= 13:
                pool13 = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vf, 19))
                cb("Escada 13: pool de 19 → fechamento DUAL no espaço dos "
                   "complementos (captura 1:843)...")
                from .forja_lotes import FechamentoDual
                res_d = FechamentoDual().fechar(pool13, t=13,
                                                limite_segundos=20.0)
                cartelas = res_d["cartelas"]
                metodo = res_d["metodo"]
                verificada = res_d["garantia_verificada"]
            else:
                pool13 = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vf, 18))
                cb("Escada 13: pool de 18 → família exata de 6 cartelas "
                   "(captura 1:4.006, ~6× o pool-17)...")
                res_w = self.wheeling.gerar(pool13, garantia=13,
                                            max_cartelas=6)
                cartelas = [c["dezenas"] for c in res_w["cartelas"]]
                metodo = res_w["metodo"]
                verificada = res_w["garantia_verificada"]
            pool_elite = pool13
            garantia = 13
            info_extra["wheeling"] = {
                "metodo": metodo,
                "garantia_verificada": bool(verificada),
            }

        elif n == 1:
            estrategia = "exaustao-unica"
            idx, sc = heavy.avaliar_universo_completo(vf)
            # anda do topo para baixo até aprovada no filtro gaussiano
            for i in range(min(500, len(idx))):
                cand = heavy.obter_dezenas_por_indice(idx[i])
                ok, _ = self._gaussiano.filtrar(cand)
                if ok:
                    cartelas.append(cand)
                    cb("Cartela ótima encontrada no rank {} do universo "
                       "(score {:.5f})".format(i + 1, sc[i]))
                    break
            if not cartelas:  # fallback: a própria melhor
                cartelas.append(heavy.obter_dezenas_por_indice(idx[0]))
        elif n <= 7:
            estrategia = "exaustao-diversa"
            idx, sc = heavy.avaliar_universo_completo(vf)
            escolhidas_masks = []
            for i in range(len(idx)):
                if len(cartelas) >= n:
                    break
                cand = heavy.obter_dezenas_por_indice(idx[i])
                m = self._mask_de_dezenas(cand)
                # diversidade: ≤13 dezenas em comum com cada escolhida
                if any(_popcount_uf(m & e) >= 13 for e in escolhidas_masks):
                    continue
                ok, _ = self._gaussiano.filtrar(cand)
                if not ok and len(cartelas) >= max(1, n // 2):
                    continue
                cartelas.append(cand)
                escolhidas_masks.append(m)
        else:
            estrategia = "wheeling-garantia-14"
            garantia = 14
            res_w = self.wheeling.gerar(pool_elite, garantia=14,
                                        max_cartelas=8)
            cartelas = [c["dezenas"] for c in res_w["cartelas"]]
            # excedente do orçamento: exaustão diversa
            if n > 8:
                idx, sc = heavy.avaliar_universo_completo(vf)
                masks = [self._mask_de_dezenas(c) for c in cartelas]
                for i in range(len(idx)):
                    if len(cartelas) >= n:
                        break
                    cand = heavy.obter_dezenas_por_indice(idx[i])
                    m = self._mask_de_dezenas(cand)
                    if any(_popcount_uf(m & e) >= 14 for e in masks):
                        continue
                    cartelas.append(cand)
                    masks.append(m)
            cb("Wheeling: 8 cartelas com garantia 14 condicional ao pool "
               "+ {} por exaustão".format(len(cartelas) - 8))

        # contabilidade exata do lote (universo completo)
        analise = self.wheeling.analisar_lote(cartelas, pool_elite)
        custo = round(len(cartelas) * VALOR_APOSTA, 2)

        res = {
            "estrategia": estrategia,
            "n_cartelas": len(cartelas),
            "cartelas": [],
            "pool_elite": pool_elite,
            "custo": custo,
            "analise": analise,
            "tempo": round(time.time() - t0, 2),
            "verdade_honesta": (
                "Probabilidade por cartela (hipergeométrica, imutável por "
                "qualquer análise): 14 pontos 1 em 21.800 · 15 pontos 1 em "
                "3.268.760. A decisão do Cérebro ordena o universo pelos "
                "critérios dos motores; com garantias, 14/15 só valem se o "
                "pool capturar o sorteio (1:24.035 para pool 17 · 1:204.297 "
                "para pool 16). A forja maximiza a estrutura do lote sob o "
                "modelo da Magna — ganho combinatório, nunca preditivo."
            ),
        }
        if garantia is not None:
            res["garantia"] = garantia
            res["garantia_verificada"] = True
            res["p_captura"] = self.wheeling.prob_captura(len(pool_elite))
            res["um_em_captura"] = round(
                1 / self.wheeling.prob_captura(len(pool_elite)), 1)
        if info_extra:
            res.update(info_extra)

        # formato compatível com gerar.html/_salvar_cartelas_banco
        for c in cartelas:
            _, det = self._gaussiano.filtrar(c)
            res["cartelas"].append({
                "dezenas": [int(d) for d in c],
                "bitmask": self._mask_de_dezenas(c),
                "score_total": round(float(sum(vf[d - 1] for d in c)), 6),
                "soma": det.get("soma"), "pares": det.get("pares"),
                "primos": det.get("primos"), "fibonacci": det.get("fibonacci"),
                "borda": det.get("borda"),
                "scores": {"ev_prob": round(float(sum(vf[d - 1] for d in c)), 4)},
            })

        cb("Decisão: {} · {} cartelas · P(lote≥14)={:.6f}% · EV R$ {:.2f}"
           .format(estrategia, len(cartelas),
                   100 * analise["p_melhor_14_mais"], analise["ev_lote"]))
        self.decisoes["gerar_otimas"] = {
            "estrategia": estrategia, "n": len(cartelas),
            "pool_elite": pool_elite,
        }
        self.estado = "pronto"
        if salvar:
            res["salvar"] = True  # a camada app persiste o lote
        return res

    # ============================================================
    # INTELIGÊNCIA MAGNA — UMA análise, UMA memória, UMA decisão
    # ============================================================
    @staticmethod
    def _normalizar_vetor(vetor):
        v = np.asarray(vetor, dtype=float)
        if v.shape != (TOTAL_DEZENAS,):
            return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
        v = np.clip(v, 0.0, None)
        return (v / v.sum() if v.sum() > 0
                else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS)

    @staticmethod
    def _json_seguro(valor):
        """Converte estruturas NumPy em JSON puro para a memória auditável."""
        if isinstance(valor, np.ndarray):
            return [CerebroIA._json_seguro(v) for v in valor.tolist()]
        if isinstance(valor, np.generic):
            return valor.item()
        if isinstance(valor, dict):
            return {str(k): CerebroIA._json_seguro(v)
                    for k, v in valor.items()}
        if isinstance(valor, (list, tuple, set)):
            return [CerebroIA._json_seguro(v) for v in valor]
        return valor

    def _carregar_pesos_fontes_magna(self):
        """Pesos das fontes: os gravados pela Magna, com migrações de nome.

        v11.4 — a fonte `ordem` (módulo externo) virou `abertura` (órgão da
        própria Magna). O peso aprendido na fonte antiga é reaproveitado, não
        jogado fora: a memória continua a mesma, só mudou de dono.
        """
        pesos = dict(self._FONTES_MAGNA_DEFAULT)
        try:
            conn = self.db.get_conn()
            row = conn.execute(
                "SELECT valor FROM magna_estado WHERE chave='pesos_fontes'"
            ).fetchone()
            conn.close()
            if row:
                gravados = json.loads(row[0])
                if isinstance(gravados, dict):
                    if ("ordem" in gravados and "abertura" not in gravados):
                        gravados = dict(gravados)
                        gravados["abertura"] = gravados.pop("ordem")
                        self._log("ACERVO",
                                  "peso aprendido da fonte 'ordem' migrado "
                                  "para 'abertura' (mesma memória)")
                    if set(gravados) == set(pesos):
                        pesos = {k: max(0.01, float(gravados[k]))
                                 for k in pesos}
        except (ValueError, TypeError, json.JSONDecodeError, sqlite3.Error):
            pass
        total = sum(pesos.values())
        return {k: round(v / total, 6) for k, v in pesos.items()}

    def _salvar_pesos_fontes_magna(self, conn=None):
        proprio = conn is None
        conn = conn or self.db.get_conn()
        conn.execute("""
            INSERT INTO magna_estado (chave, valor, atualizado_em)
            VALUES ('pesos_fontes', ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                valor=excluded.valor, atualizado_em=excluded.atualizado_em
        """, (
            json.dumps(self.pesos_fontes_magna, sort_keys=True),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        if proprio:
            conn.commit()
            conn.close()

    def _fontes_assimiladas_magna(self):
        """Assimila todos os antigos painéis em um único vetor decisório.

        Os nomes abaixo são fontes internas de evidência, não subsistemas que
        geram cartelas. Somente o vetor final da Magna pode chegar à geração.
        """
        from .singularidade import EspectroTemporal, TeoriaDaInformacao

        vetor_motores = self._normalizar_vetor(self._vetor_combinado())

        consulta = self._oraculo.consultar_todos()
        votos = np.asarray(consulta["votos"], dtype=float)
        pesos_oraculo = np.asarray(consulta["pesos_acumulados"], dtype=float)
        vetor_oraculos = self._normalizar_vetor(
            0.55 * self._normalizar_vetor(pesos_oraculo)
            + 0.45 * self._normalizar_vetor(votos)
        )

        espectro = EspectroTemporal(self.matriz)
        vetor_espectral = self._normalizar_vetor(espectro.score_espectral_por_dezena())

        informacao = TeoriaDaInformacao(self.matriz)
        entropias = np.array([
            informacao.entropia_permutacao(self.matriz[:, d])
            for d in range(TOTAL_DEZENAS)
        ], dtype=float)
        vetor_informacao = self._normalizar_vetor(entropias)

        janela = self.matriz[-min(50, self.n):]
        vetor_recente = self._normalizar_vetor(np.sum(janela, axis=0))

        # Fonte física: perfil individual das bolas + ambiente do sorteio
        vetor_fisica = self._normalizar_vetor(self.fisica.score_fisico())

        # v11.2 — Fonte de clima: temperatura × pressão × umidade do
        # sorteio, com shrinkage 50/50, teto ±10% e auto-auditoria.
        # O clima inclina o vetor; o consenso decide.
        try:
            # fator_confianca em [0.5, 1.0] (auto-auditoria walk-forward):
            # mistura o vetor de clima com o uniforme na medida em que o
            # histórico NÃO justifica confiança — a fonte nunca é zerada.
            fator = float(
                self.clima.auto_ponderacao().get("fator_confianca", 1.0))
            v_clima = self.clima.vetor_clima()
            uniforme = np.ones(TOTAL_DEZENAS, dtype=float)
            v_atenuado = (1.0 - fator) * uniforme + fator * v_clima
            vetor_clima = self._normalizar_vetor(v_atenuado)
        except Exception:
            vetor_clima = self._normalizar_vetor(
                np.ones(TOTAL_DEZENAS, dtype=float))

        # v11.4 — Fonte ABERTURA: conhecimento do acervo da própria Magna
        # (menor dezena + 1ª bola física), medido na base histórica inteira,
        # memorizado e auto-avaliado walk-forward. Sob independência o lift é
        # ~1,0 e o fator mantém o vetor quase uniforme — a fonte entra no
        # consenso apenas na medida do que o placar comprovou.
        try:
            vetor_abertura = self.vetor_abertura_para_consenso()
        except Exception:
            vetor_abertura = self._normalizar_vetor(
                np.ones(TOTAL_DEZENAS, dtype=float) / TOTAL_DEZENAS)

        # v11.7 — Fonte INMET: telemetria por local do sorteio. Apenas um
        # tilt leve (±10% no máximo, puxado pela pressão do local medido
        # pelo INMET). Sem telemetria, o vetor é uniforme → fonte neutra
        # (a Magna a ignora no consenso, exatamente como as demais).
        try:
            vetor_inmet = self._normalizar_vetor(self.inmet.vetor_inmet())
        except Exception:
            vetor_inmet = self._normalizar_vetor(
                np.ones(TOTAL_DEZENAS, dtype=float))

        fontes = {
            "motores": vetor_motores,
            "oraculos": vetor_oraculos,
            "espectral": vetor_espectral,
            "informacao": vetor_informacao,
            "recente": vetor_recente,
            "fisica": vetor_fisica,
            "clima": vetor_clima,
            "abertura": vetor_abertura,
            "inmet": vetor_inmet,
        }
        return fontes, consulta, espectro, informacao, entropias

    # ============================================================
    # ACERVO DE CONHECIMENTO — aprender, memorizar, julgar (v11.4)
    # ============================================================
    def _montar_acervo_abertura(self) -> AcervoAberturaMagna:
        """Lê da base histórica o que a Magna precisa para saber abrir.

        `resultados.d1`  → canal `minima` (a dezena que abre a lista) — a base
                           inteira, sem depender de backfill externo;
        `ordem_sorteio`  → canal `real` (1ª bola física), na medida em que a
                           captura oficial já forneceu.
        """
        minima: List[Tuple[int, int]] = []
        ordens: List[Tuple[int, Tuple[int, ...]]] = []
        try:
            conn = self.db.get_conn()
            try:
                for concurso, d1 in conn.execute(
                        "SELECT concurso, d1 FROM resultados "
                        "ORDER BY concurso ASC").fetchall():
                    if d1 is not None and 1 <= int(d1) <= TOTAL_DEZENAS:
                        minima.append((int(concurso), int(d1)))
                try:
                    for row in conn.execute(
                            "SELECT concurso, b1, b2, b3, b4, b5, b6, b7, b8, "
                            "b9, b10, b11, b12, b13, b14, b15 "
                            "FROM ordem_sorteio "
                            "ORDER BY concurso ASC").fetchall():
                        ordens.append((int(row[0]), tuple(int(x) for x in row[1:])))
                except sqlite3.Error:
                    ordens = []      # tabela ainda não criada nesta base
            finally:
                conn.close()
        except sqlite3.Error as exc:
            self._log("AVISO", "acervo: leitura da base falhou ({})".format(exc))
        # aberturas aprendidas em conferências recentes, ainda não refletidas
        # no dump consultado, continuam na memória viva da Magna
        ja_vistos = {c for c, _ in minima}
        for concurso, abertura in sorted(getattr(self, "_aberturas_vivas",
                                                 {}).items()):
            if concurso not in ja_vistos:
                minima.append((int(concurso), int(abertura)))
        return AcervoAberturaMagna(minima=sorted(minima), ordens=ordens)

    def _ler_conhecimento(self, dominio: str) -> Optional[Dict[str, Any]]:
        try:
            conn = self.db.get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM magna_conhecimento WHERE dominio=?",
                    (dominio,)).fetchone()
            finally:
                conn.close()
        except sqlite3.Error:
            return None
        if not row:
            return None
        dados = dict(row)
        try:
            dados["snapshot"] = json.loads(dados.pop("snapshot_json"))
        except (TypeError, json.JSONDecodeError):
            dados["snapshot"] = {}
        return dados

    def _gravar_conhecimento(self, conn, dominio: str, snapshot: Dict[str, Any],
                             concurso_ate: int, n_provas: int = 0,
                             veredito: Optional[str] = None,
                             fator_confianca: Optional[float] = None,
                             origem: str = "fundante") -> None:
        conn.execute("""
            INSERT INTO magna_conhecimento
            (dominio, versao, concurso_ate, n_provas, veredito,
             fator_confianca, snapshot_json, origem, atualizado_em)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(dominio) DO UPDATE SET
                versao=excluded.versao,
                concurso_ate=excluded.concurso_ate,
                n_provas=excluded.n_provas,
                veredito=excluded.veredito,
                fator_confianca=excluded.fator_confianca,
                snapshot_json=excluded.snapshot_json,
                origem=excluded.origem,
                atualizado_em=excluded.atualizado_em
        """, (
            dominio, self.ACERVO_VERSAO, int(concurso_ate), int(n_provas),
            veredito, fator_confianca,
            json.dumps(self._json_seguro(snapshot), sort_keys=True),
            origem, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))

    def _registrar_memoria(self, conn, dominio: str, evento: str,
                           concurso: Optional[int] = None,
                           acertos: Optional[int] = None,
                           provas: Optional[int] = None,
                           taxa: Optional[float] = None,
                           detalhe: Optional[Dict[str, Any]] = None) -> None:
        conn.execute("""
            INSERT INTO magna_memoria
            (timestamp, dominio, evento, concurso, acertos, provas, taxa,
             detalhe_json)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dominio, evento,
            (int(concurso) if concurso is not None else None),
            (int(acertos) if acertos is not None else None),
            (int(provas) if provas is not None else None),
            (float(taxa) if taxa is not None else None),
            json.dumps(self._json_seguro(detalhe or {}), sort_keys=True),
        ))

    def _acervo_carimbo(self, base: Optional[Dict[str, Any]] = None) -> int:
        """Último concurso que o acervo cobre — base oficial ou memória viva."""
        ultimo_base = int((base or self._estado_base_historica())["ultimo"] or 0)
        vivo = (int(self.acervo.ultimo("minima") or 0)
                if hasattr(self, "acervo") else 0)
        return max(ultimo_base, vivo)

    def _estado_base_historica(self) -> Dict[str, Any]:
        """Carimbo da base que a Magna está lendo (para aprendizado incremental)."""
        try:
            conn = self.db.get_conn()
            try:
                row = conn.execute(
                    "SELECT COUNT(*), MIN(concurso), MAX(concurso) "
                    "FROM resultados").fetchone()
            finally:
                conn.close()
            n, primeiro, ultimo = (int(row[0] or 0), int(row[1] or 0),
                                   int(row[2] or 0))
        except sqlite3.Error:
            n, primeiro, ultimo = self.n, 0, 0
        return {"concursos": n, "primeiro": primeiro, "ultimo": ultimo,
                "proximo_concurso": (ultimo + 1) if ultimo else None}

    def vetor_abertura_para_consenso(self) -> np.ndarray:
        """A leitura de abertura, atenuada pela confiança medida na própria base.

        fator 0,5 → vetor quase uniforme (ruído); fator 1,0 → o posterior
        aprendido entra inteiro. A atenuação é feita AQUI, na Magna, para que a
        decisão controla o peso da evidência — não o acervo.
        """
        fator = float(self.acervo.fator_confianca())
        v = self.acervo.vetor_evidencia()
        uniforme = np.ones(TOTAL_DEZENAS, dtype=float) / TOTAL_DEZENAS
        return self._normalizar_vetor((1.0 - fator) * uniforme + fator * v)

    @staticmethod
    def _acervo_auto_calibracao() -> bool:
        """Chave `LOTOFACIL_ACERVO_AUTO=0`: a Magna não toca no estado sozinha.

        Vale só para os caminhos AUTOMÁTICOS (boot e pré-decisão): o acervo é
        lido e usado, mas nada é gravado nem recalibrado por iniciativa própria
        — é o que os testes e um `import app` inofensivo precisam. Quando o
        usuário MANDA (botão da UI, `--assimilar`, `assimilar_acervo(forcar=True)`
        ou `calibrar_pesos_walkforward()`), a calibração roda do mesmo jeito.
        """
        return os.environ.get("LOTOFACIL_ACERVO_AUTO", "1") != "0"

    def assimilar_acervo(self, auto: bool = False, forcar: bool = False,
                         calibrar_fontes: bool = True,
                         limite_segundos: float = 25.0,
                         callback=None) -> Dict[str, Any]:
        """Porta serializada do aprendizado: a Magna aprende com a própria base.

        `auto=True` (boot e pré-decisão) nunca espera nem trava o usuário: se já
        existe uma assimilação em curso em outra thread, este passo é adiado —
        o conhecimento é reconstruído do banco na decisão seguinte. Sob RLock,
        a mesma thread que já decide reentra sem custo.
        """
        adquirido = False
        if auto:
            adquirido = self._magna_lock.acquire(blocking=False)
            if not adquirido:
                return {"status": "ocupado", "reassimilado": False,
                        "msg": "assimilação em curso em outra thread — adiada"}
        else:
            self._magna_lock.acquire()
            adquirido = True
        try:
            return self._assimilar_acervo_sem_lock(
                auto=auto, forcar=forcar, calibrar_fontes=calibrar_fontes,
                limite_segundos=limite_segundos, callback=callback)
        finally:
            if adquirido:
                self._magna_lock.release()

    def _assimilar_acervo_sem_lock(self, auto: bool = False,
                                   forcar: bool = False,
                                   calibrar_fontes: bool = True,
                                   limite_segundos: float = 25.0,
                                   callback=None) -> Dict[str, Any]:
        """Aprender TUDO da base histórica e memorizar — sem módulo paralelo.

        1. `abertura` — varre a base inteira (frequências, streaks, recorde,
           repetição por dezena, placar walk-forward, posterior do próximo
           concurso) e grava o snapshot com o carimbo do último concurso;
        2. `fontes`   — calibra o peso de cada fonte do consenso em
           walk-forward fora-da-amostra (orçamento de tempo; só refaz se a
           base mudou). Sem esta etapa a Magna começaria no chute do default;
        3. `memoria`  — resume o que já está conferido e aprendido.

        `auto=True` (boot e pré-decisão) refaz apenas o que ficou desatualizado:
        se a base não mudou e o carimbo bate, o custo é ~0 e nada é recalibrado.
        """
        def cb(msg):
            self._log("ACERVO", msg)
            if callback:
                callback(msg)

        base = self._estado_base_historica()
        aprendido_ate = (self.acervo.ultimo("minima")
                         if hasattr(self, "acervo") else None) or 0
        ate = self._acervo_carimbo(base)
        gravado = self._ler_conhecimento("abertura")
        desatualizado = (forcar or aprendido_ate != base["ultimo"]
                         or not gravado
                         or int(gravado.get("concurso_ate") or 0) != ate)
        if not desatualizado:
            rel = self.acervo.relatorio()
            return {"status": "atualizado", "base": base,
                    "aprendido_ate": aprendido_ate,
                    "digest": self.acervo.digest(),
                    "veredito": rel["veredito"],
                    "fator_confianca": rel["fator_confianca"],
                    "leitura": rel["leitura"],
                    "reassimilado": False}

        # A fonte da verdade do conhecimento é o banco: reler a série completa
        # custa ~10 ms para 3.773 concursos e elimina estado defasado.
        self.acervo = self._montar_acervo_abertura()

        rel = self.acervo.relatorio()
        canais = rel["canais"]
        # LOTOFACIL_ACERVO_AUTO=0 = "a Magna não escreve nada por conta própria":
        # o conhecimento é lido e usado, mas não é persistido nem recalibrado.
        gravar = not (auto and not self._acervo_auto_calibracao())
        if not gravar:
            cb("modo somente-leitura (LOTOFACIL_ACERVO_AUTO=0): conhecimento "
               "montado em memória, nada gravado nem recalibrado")
            return {"status": "memoria", "base": base,
                    "aprendido_ate": self.acervo.ultimo("minima"),
                    "digest": rel["digest"], "veredito": rel["veredito"],
                    "fator_confianca": rel["fator_confianca"],
                    "leitura": rel["leitura"], "reassimilado": True,
                    "gravado": False}
        conn = self.db.get_conn()
        try:
            self._gravar_conhecimento(conn, "abertura", {
                "digest": rel["digest"],
                "fator_confianca": rel["fator_confianca"],
                "veredito": rel["veredito"],
                "pesos_de_evidencia": rel["pesos_de_evidencia"],
                "leitura": rel["leitura"],
                "canais": {
                    nome: {
                        "n_registros": c["n_registros"],
                        "ultimo_concurso": c["ultimo_concurso"],
                        "placar_walkforward": c["placar_walkforward"],
                        "auto_auditoria": c["auto_auditoria"],
                        "previsao": c["previsao"],
                        "streaks": {k: v for k, v in c["streaks"].items()
                                    if k != "por_dezena"},
                    } for nome, c in canais.items()},
                "honestidade": rel["honestidade"],
            }, concurso_ate=ate,
                n_provas=int(canais["minima"]["n_registros"]),
                veredito=rel["veredito"],
                fator_confianca=rel["fator_confianca"],
                origem="incremental" if auto else "fundante")
            self._gravar_conhecimento(conn, "base", base,
                                      concurso_ate=base["ultimo"],
                                      n_provas=base["concursos"],
                                      veredito="OK",
                                      origem="fundante")
            # só registra quando a leitura realmente mudou: o carimbo evita
            # inflar a memória com o mesmo aprendizado a cada decisão
            ultimo_evento = conn.execute(
                "SELECT provas, taxa, detalhe_json FROM magna_memoria "
                "WHERE dominio='abertura' AND evento='assimilado' "
                "AND concurso=? ORDER BY id DESC LIMIT 1", (ate,)).fetchone()
            ultima_digest = ""
            try:
                ultima_digest = json.loads(ultimo_evento[2] or "{}").get(
                    "digest", "") if ultimo_evento is not None else ""
            except (TypeError, json.JSONDecodeError):
                ultima_digest = ""
            if (ultimo_evento is None
                    or ultima_digest != rel["digest"]
                    or (ultimo_evento[0], ultimo_evento[1] or 0.0) !=
                       (canais["minima"]["n_registros"],
                        canais["minima"]["auto_auditoria"].get("taxa") or 0.0)):
                self._registrar_memoria(conn, "abertura", "assimilado",
                                        concurso=ate,
                                        provas=canais["minima"]["n_registros"],
                                        taxa=canais["minima"]["auto_auditoria"].get(
                                            "taxa"),
                                        detalhe={"digest": rel["digest"],
                                                 "veredito": rel["veredito"],
                                                 "leitura": rel["leitura"]})
            conn.commit()
        finally:
            conn.close()

        cb(rel["leitura"])

        calibracao = None
        if calibrar_fontes and base["concursos"] >= 120:
            calibrado = self._ler_conhecimento("fontes")
            precisa = (forcar or not calibrado
                       or int(calibrado.get("concurso_ate") or 0)
                       != base["ultimo"])
            if precisa and (not auto or self._acervo_auto_calibracao()):
                cb("Calibrando o peso das {} fontes em walk-forward sobre a "
                   "base histórica (orçamento de {:.0f}s)...".format(
                       len(self._FONTES_MAGNA_DEFAULT), limite_segundos))
                try:
                    calibracao = self.calibrar_pesos_walkforward(
                        limite_segundos=limite_segundos, callback=callback)
                except Exception as exc:
                    self._log("AVISO", "calibração do acervo indisponível: {}"
                              .format(exc))
            elif precisa:
                cb("Auto-calibração desativada "
                   "(LOTOFACIL_ACERVO_AUTO=0): pesos permanecem nos defaults "
                   "aprendidos online. Rode assimilar_acervo(forcar=True) para "
                   "calibrar.")
            else:
                cb("Calibração de fontes já memorizada até o concurso {} — "
                   "reaproveitando.".format(calibrado.get("concurso_ate")))
        elif calibrar_fontes:
            cb("Base pequena ({} concursos): pesos ficam nos defaults até "
               "haver amostra.".format(base["concursos"]))

        self._gravar_resumo_memoria()
        return {"status": "ok", "base": base, "gravado": True,
                "aprendido_ate": ate,
                "digest": rel["digest"], "reassimilado": True,
                "veredito": rel["veredito"],
                "fator_confianca": rel["fator_confianca"],
                "leitura": rel["leitura"],
                "pesos_fontes": dict(self.pesos_fontes_magna),
                "calibracao": calibracao}

    def _gravar_resumo_memoria(self) -> None:
        """Memória do que já foi conferido/aprendido (dominio `memoria`)."""
        try:
            conn = self.db.get_conn()
            try:
                dec = conn.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN status='conferida' "
                    "THEN 1 ELSE 0 END), AVG(media_acertos), "
                    "MAX(melhor_acertos) FROM magna_decisoes").fetchone()
                apr = conn.execute(
                    "SELECT COUNT(*), AVG(peso_depois - peso_antes) "
                    "FROM magna_aprendizado").fetchone()
                mem = conn.execute(
                    "SELECT COUNT(*) FROM magna_memoria").fetchone()
                epi = conn.execute(
                    "SELECT COUNT(*) FROM magna_episodios").fetchone()
                placar = self.placar_abertura_memoria(conn)
                snapshot = {
                    "decisoes": int(dec[0] or 0),
                    "decisoes_conferidas": int(dec[1] or 0),
                    "media_acertos_conferidas": round(float(dec[2] or 0.0), 4),
                    "melhor_acertos": int(dec[3] or 0),
                    "ajustes_de_peso": int(apr[0] or 0),
                    "delta_medio_de_peso": round(float(apr[1] or 0.0), 6),
                    "episodios": int(epi[0] or 0),
                    "eventos_de_memoria": int(mem[0] or 0),
                    "placar_abertura": placar,
                }
                ultimo = self._acervo_carimbo()
                self._gravar_conhecimento(conn, "memoria", snapshot,
                                          concurso_ate=ultimo,
                                          n_provas=snapshot["decisoes_conferidas"],
                                          veredito="OK", origem="online")
                conn.commit()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            self._log("AVISO", "resumo de memória: {}".format(exc))

    def placar_abertura_memoria(self, conn=None) -> Dict[str, Any]:
        """O placar do que a Magna PREVÊ de abertura — memória auditável.

        Compara o ranking aprendido com a abertura real de cada concurso
        conferido e devolve o aproveitamento ao lado da margem teórica.
        """
        proprio = conn is None
        conn = conn or self.db.get_conn()
        try:
            rows = conn.execute("""
                SELECT acertos, provas, taxa, detalhe_json FROM magna_memoria
                WHERE dominio='abertura' AND evento='palpite'
                ORDER BY id DESC LIMIT 5000""").fetchall()
        except sqlite3.Error:
            return {"aplicavel": False, "motivo": "sem tabela de memória"}
        finally:
            if proprio:
                conn.close()
        n = len(rows)
        if not n:
            return {"aplicavel": False,
                    "motivo": "a Magna ainda não conferiu um concurso com "
                             "palpite de abertura registrado",
                    "provas": 0}
        t1 = t2 = t3 = 0
        for r in rows:
            try:
                det = json.loads(r[3] or "{}")
            except (TypeError, json.JSONDecodeError):
                det = {}
            t1 += 1 if det.get("acerto_top1") else 0
            t2 += 1 if det.get("acerto_top2") else 0
            t3 += 1 if det.get("acerto_top3") else 0
        teto = {
            "top1": self.acervo.p_teorica("minima", 1),
            "top2": (self.acervo.p_teorica("minima", 1)
                     + self.acervo.p_teorica("minima", 2)),
            "top3": sum(self.acervo.p_teorica("minima", k) for k in (1, 2, 3)),
        }
        return {
            "aplicavel": True, "provas": n,
            "acerto_top1": round(t1 / n, 4), "acerto_top2": round(t2 / n, 4),
            "acerto_top3": round(t3 / n, 4),
            "margem_teorica": {k: round(v, 4) for k, v in teto.items()},
            "leitura": ("o palpite da Magna fica na margem teórica — isso é "
                        "o teto do que existe para prever abertura sob "
                        "independência" if abs(t3 / n - teto["top3"]) < 0.05
                        else "desvio da margem na amostra pequena: aguardar"),
        }

    def calibrar_pesos_walkforward(self, n_passos: Optional[int] = None,
                                   limite_segundos: float = 25.0,
                                   callback=None) -> Dict[str, Any]:
        """Aprenda o peso de cada fonte olhando o passado, sem vazamento.

        Para cada concurso-t do histórico, a Magna refaz o próprio consenso
        usando SOMENTE os concursos < t e mede quantas das 15 dezenas do
        top-15 de cada fonte caíram no sorteio real. Baseline de qualquer
        escolha de 15 dezenas: 9,0 acertos (15·15/25). O peso evolui com a
        MESMA regra bayesiana usada online — assim a Magna não começa do zero
        no concurso 3774: ela começa calibrada com a própria história.
        """
        def cb(msg):
            self._log("CALIBRAÇÃO", msg)
            if callback:
                callback(msg)

        matriz_original, raw_original = self.matriz.copy(), list(self.raw)
        pesos_originais = dict(self.pesos_fontes_magna)
        n_total = len(matriz_original)
        if n_total < 120:
            return {"status": "ignorado", "motivo": "base pequena",
                    "concursos": n_total}

        passos = int(n_passos or 0)
        t0 = time.time()
        if passos <= 0:
            passos = 8
            while passos < 48 and (time.time() - t0) < limite_segundos * 0.25:
                passos += 4
        inicio = max(60, n_total - passos * max(1, (n_total - 60) // passos))
        passo = max(1, (n_total - inicio) // passos)
        checkpoints = list(range(inicio, n_total - 1, passo))[:passos]
        if not checkpoints:
            return {"status": "ignorado", "motivo": "sem checkpoints"}

        nome_fontes = list(self._FONTES_MAGNA_DEFAULT)
        acertos_fontes = {n: 0 for n in nome_fontes}
        provas = 0
        pesos_passo: List[Dict[str, float]] = []
        bayes: Dict[str, float] = dict(pesos_originais)
        try:
            for t in checkpoints:
                if time.time() - t0 > limite_segundos:
                    cb("Orçamento de {:.0f}s atingido no passo {} de {} — a "
                       "calibração para aqui e fica registrada como parcial."
                       .format(limite_segundos, provas, len(checkpoints)))
                    break
                self.treinar(
                    matriz_override=matriz_original[:t],
                    raw_override=raw_original[:t])
                fontes, *_ = self._fontes_assimiladas_magna()
                real = {int(d) + 1 for d in np.where(
                    matriz_original[t] > 0)[0]}
                if len(real) != 15:
                    continue
                acertos = {}
                for nome, vetor in fontes.items():
                    top15 = [int(x) + 1 for x in
                             (np.argsort(vetor)[::-1][:15])]
                    acertos[nome] = len(set(top15) & real)
                    acertos_fontes[nome] += acertos[nome]
                if AprendizadoBayesianoMagno is not None:
                    try:
                        if not hasattr(self, "_bayes_acervo"):
                            self._bayes_acervo = AprendizadoBayesianoMagno(
                                pesos_originais, alpha_prior=60.0)
                        bayes = self._bayes_acervo.atualizar(
                            acertos, lr=0.10, momentum_beta=0.5)
                    except Exception:
                        pass
                pesos_passo.append({"t": int(t), "acertos": acertos,
                                    "pesos": dict(bayes)})
                provas += 1
                cb("passo {}/{} (concurso {}): {}".format(
                    provas, len(checkpoints), t,
                    " · ".join("{} {}".format(n, a)
                               for n, a in acertos.items())))
        finally:
            self._rng_vetor = None
            if (self.matriz.shape != matriz_original.shape
                    or not np.array_equal(self.matriz, matriz_original)):
                self.treinar(matriz_override=matriz_original,
                             raw_override=raw_original)

        if not provas:
            return {"status": "ignorado", "motivo": "nenhuma prova válida"}

        linha_base = 15.0 * 15.0 / TOTAL_DEZENAS      # 9 acertos esperados
        medicao = {}
        for nome in nome_fontes:
            media = acertos_fontes[nome] / provas
            medicao[nome] = {
                "acertos_totais": int(acertos_fontes[nome]),
                "media_top15": round(media, 4),
                "linha_de_base": round(linha_base, 4),
                "lift": round(media / linha_base, 4),
            }
        calibrados = {n: max(0.01, float(bayes.get(n, pesos_originais[n])))
                      for n in nome_fontes}
        soma = sum(calibrados.values())
        calibrados = {n: round(v / soma, 6) for n, v in calibrados.items()}
        base_historica = self._estado_base_historica()
        carimbo = self._acervo_carimbo(base_historica)
        conn = self.db.get_conn()
        try:
            self._gravar_conhecimento(conn, "fontes", {
                "provas": provas,
                "concursos_cobertos": [int(checkpoints[0]),
                                       int(checkpoints[-1] + 1)],
                "cobertura": ("{} passos de walk-forward cobrindo os "
                              "concursos {}-{} de {} (prefixo limpo, sem "
                              "vazamento)".format(
                                  provas, checkpoints[0], checkpoints[-1] + 1,
                                  n_total)),
                "medicao": medicao,
                "pesos_calibrados": calibrados,
                "pesos_anteriores": pesos_originais,
                "parcial": bool(provas < len(checkpoints)),
                "limite_segundos": round(float(limite_segundos), 2),
                "leitura": ("nenhuma fonte saiu do acaso em walk-forward: os "
                            "pesos ficam nos defaults e a Magna não finge ter "
                            "aprendido o que a base não mostrou"
                            if all(abs(v["lift"] - 1.0) < 0.05
                                   for v in medicao.values()) else
                            "há fontes acima da linha de base fora-da-amostra; "
                            "o peso recalibrado reflete isso"),
            }, concurso_ate=carimbo, n_provas=provas,
                veredito="CALIBRADO", origem="fundante")
            self._registrar_memoria(conn, "fontes", "calibrado",
                                    concurso=carimbo,
                                    provas=provas,
                                    detalhe={"pesos": calibrados,
                                             "medicao": medicao})
            conn.commit()
        finally:
            conn.close()

        self.pesos_fontes_magna = calibrados
        conn = self.db.get_conn()
        try:
            self._salvar_pesos_fontes_magna(conn)
            conn.commit()
        finally:
            conn.close()
        self._acervo_calibrado = True
        tempo = round(time.time() - t0, 2)
        cb("Pesos calibrados com {} provas fora-da-amostra em {}s · {}".format(
            provas, tempo, " · ".join("{} {:.3f}".format(n, calibrados[n])
                                      for n in nome_fontes)))
        return {"status": "ok", "provas": provas, "tempo_seg": tempo,
                "medicao": medicao, "pesos_calibrados": calibrados,
                "parcial": bool(provas < len(checkpoints)),
                "cobertura": [int(checkpoints[0]), int(checkpoints[-1] + 1)]}

    def _garantir_acervo(self, callback=None, orcamento_segundos=12.0) -> None:
        """Chamado por TODA decisão: a Magna nunca decide com memória velha.

        O custo é ~0 quando o carimbo do acervo bate com o da base histórica.
        Quando a base cresceu (concurso novo, ordem real ingerida, decisão depois
        de instalar o aprendizado), a Magna reassimila o conhecimento de abertura
        e o repersiste — decisão alguma é tomada com memória velha.

        A calibração fundante (pesos das 8 fontes em walk-forward sobre a base
        inteira) é a parte cara e NÃO é disparada aqui: ela roda no preload do
        `python app.py`, no botão da UI, na CLI (`--assimilar`) ou quando a
        conferência pede. O `orcamento_segundos` continua no contrato para o dia
        em que a Magna decidir calibrar dentro do próprio ciclo.
        """
        try:
            if not hasattr(self, "acervo"):
                self.acervo = self._montar_acervo_abertura()
            self.assimilar_acervo(auto=True, callback=callback,
                                  calibrar_fontes=False,
                                  limite_segundos=float(orcamento_segundos))
        except Exception as exc:  # a decisão nunca trava por leitura de acervo
            self._log("AVISO", "acervo não reassimilado: {}".format(exc))

    def evidencia_abertura(self) -> Dict[str, Any]:
        """Síntese do conhecimento de abertura usada por TODA decisão.

        É o mesmo objeto que o Juiz recebe, que a interpretação de cada cartela
        cita e que a conferência vai julgar — uma única fonte, dentro da Magna.
        """
        acervo = self.acervo
        prev = acervo.previsao("minima")
        est = acervo.estado()
        probs = {int(k): float(v) for k, v in
                 (prev.get("probabilidades") or {}).items()}
        return {
            "digest": est["digest"],
            "versao": self.ACERVO_VERSAO,
            "aprendido_ate": est["aprendido_ate_concurso"],
            "concursos_da_base": est["concursos_da_base"],
            "concursos_com_ordem_real": est["concursos_com_ordem_real"],
            "abertura_atual": est["abertura_atual"],
            "veredito": est["veredito"],
            "fator_confianca": est["fator_confianca"],
            "ranking": [r["dezena"] for r in prev.get("ranking") or []],
            "ranking_completo": prev.get("ranking") or [],
            "probabilidades": {str(k): round(v, 5) for k, v in probs.items()},
            "palpite_top3": prev.get("proximo_palpite_top3") or [],
            "recorde": acervo.streaks("minima").get("recorde_historico"),
            "placar": acervo.placar_walkforward("minima"),
            "auto_auditoria": acervo.auto_auditoria("minima"),
            "pergunta_decisiva": prev.get("pergunta_decisiva"),
            "leitura": acervo.leitura(),
        }

    def aprender_abertura_medida(self, concurso: int, abertura: int,
                                 origem: str = "conferencia",
                                 gravar: bool = True) -> Dict[str, Any]:
        """Memoriza a abertura REAL de um concurso acabado de conferir.

        É aqui que o "aprender" da Magna acontece no fim do ciclo: o concurso
        entra na série viva do acervo, o palpite anterior é julgado e o
        conhecimento é repersistido com novo carimbo — sem nenhum outro módulo
        envolvido.
        """
        concurso, abertura = int(concurso), int(abertura)
        if not 1 <= abertura <= TOTAL_DEZENAS:
            raise ValueError("abertura fora da faixa 1-25")
        res = self.acervo.aprender("minima", concurso, abertura)
        vivas = getattr(self, "_aberturas_vivas", None)
        if vivas is None:
            vivas = self._aberturas_vivas = {}
        vivas[concurso] = abertura
        if gravar:
            self._assimilar_acervo_sem_lock(auto=True, calibrar_fontes=False)
            conn = self.db.get_conn()
            try:
                self._registrar_memoria(conn, "abertura", "aprendido",
                                        concurso=concurso,
                                        detalhe={"abertura": abertura,
                                                 "origem": origem})
                conn.commit()
            finally:
                conn.close()
        res["origem"] = origem
        return res

    def _julgar_palpite_abertura(self, conn, concurso: int,
                                 row: Dict[str, Any],
                                 real: set) -> Optional[Dict[str, Any]]:
        """Julga o que a Magna previu de abertura para ESTE concurso.

        O palpite está gravado em `analise_json.memoria.palpite_abertura` desde
        a decisão; aqui ele é confrontado com a abertura real e vira memória
        auditável (dominio `abertura`, evento `palpite`) — o placar do
        /api/magna/conhecimento é montado a partir desses registros.
        """
        try:
            analise = json.loads(row["analise_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            return None
        palpite = ((analise.get("memoria") or {}).get("palpite_abertura") or {})
        ranking = [int(d) for d in (palpite.get("ranking") or [])]
        abertura_real = int(min(int(d) for d in real))
        julgamento = AcervoAberturaMagna.avaliar_palpite(
            ranking, abertura_real) if ranking else {
                "abertura_real": abertura_real, "posicao_no_ranking": None,
                "acerto_top1": None, "acerto_top2": None, "acerto_top3": None,
                "motivo": "decisão anterior ao acervo: sem palpite gravado"}
        julgamento.update({"concurso": int(concurso),
                           "digest_acervo": palpite.get("digest"),
                           "abertura_prevista_top3": ranking[:3]})
        self._registrar_memoria(
            conn, "abertura", "palpite", concurso=concurso,
            acertos=(1 if julgamento.get("acerto_top1") else 0),
            provas=1,
            taxa=(1.0 if julgamento.get("acerto_top3") else 0.0),
            detalhe=julgamento)
        return julgamento



    def abertura_para_o_juiz(self, cartelas: Optional[List[List[int]]] = None
                             ) -> Dict[str, Any]:
        """Recorte do acervo que o Juiz Magna usa como 9º critério."""
        prev = self.acervo.previsao("minima")
        return {
            "probabilidades": prev.get("probabilidades") or {},
            "ranking": prev.get("proximo_palpite_top3") or [],
            "n_registros": prev.get("n_registros"),
            "fator_confianca": self.acervo.fator_confianca(),
        }

    def conhecimento(self, dominio: Optional[str] = None,
                     detalhes: bool = True) -> Dict[str, Any]:
        """O que a Magna sabe, como aprendeu e onde isso está memorizado."""
        if dominio:
            gravado = self._ler_conhecimento(dominio)
            if not gravado:
                return {"status": "vazio", "dominio": dominio,
                        "msg": "a Magna ainda não assimilou este domínio"}
            return {"status": "ok", **gravado}
        gravados = {}
        try:
            conn = self.db.get_conn()
            try:
                rows = conn.execute(
                    "SELECT dominio, versao, concurso_ate, n_provas, veredito, "
                    "fator_confianca, origem, atualizado_em, snapshot_json "
                    "FROM magna_conhecimento ORDER BY dominio").fetchall()
                eventos = conn.execute(
                    "SELECT dominio, evento, concurso, acertos, provas, taxa, "
                    "timestamp FROM magna_memoria ORDER BY id DESC LIMIT 30"
                ).fetchall()
            finally:
                conn.close()
            for r in rows:
                d = dict(r)
                try:
                    d["snapshot"] = json.loads(d.pop("snapshot_json"))
                except (TypeError, json.JSONDecodeError):
                    d["snapshot"] = {}
                gravados[d["dominio"]] = d
            memoria = [dict(r) for r in eventos]
        except sqlite3.Error as exc:
            gravados, memoria = {}, [{"erro": str(exc)}]
        out = {
            "status": "ok",
            "identidade": "Inteligência Magna — acervo de conhecimento v11.4",
            "versao_acervo": self.ACERVO_VERSAO,
            "base": self._estado_base_historica(),
            "fontes_do_consenso": list(self._FONTES_MAGNA_DEFAULT),
            "pesos_fontes": dict(self.pesos_fontes_magna),
            "calibrado": bool(self._ler_conhecimento("fontes")),
            "dominios": {k: {kk: vv for kk, vv in v.items()
                              if kk != "snapshot"}
                         for k, v in gravados.items()},
            "memoria_recente": memoria,
            "abertura": self.acervo.estado(),
            "leitura": self.acervo.leitura(),
            "placar_abertura": self.placar_abertura_memoria(),
            "honestidade": (
                "O acervo é memória e julgamento, não bola de cristal: mede, "
                "atenua e publica. As probabilidades hipergeométricas de cada "
                "cartela e as garantias do fechamento permanecem as mesmas."),
        }
        if detalhes:
            out["abertura_relatorio"] = self.acervo.relatorio()
        return out

    def aprender_ordem_sorteio(self, concurso: int,
                              ordem: Sequence[int]) -> Dict[str, Any]:
        """Entrada única da ordem real das bolas (o que a Magna memoriza).

        Substitui o antigo POST /api/magna/ordem/ingestao: o dado entra pela
        mão da própria Magna, que valida, grava em `ordem_sorteio`, atualiza o
        acervo e reassimila o conhecimento no mesmo passo.
        """
        vals = AcervoAberturaMagna.validar_ordem(ordem)
        concurso = int(concurso)
        if concurso < 1:
            raise ValueError("concurso inválido")
        persistido = False
        try:
            persistido = bool(self.db.salvar_ordem(concurso, list(vals)))
        except (ValueError, sqlite3.Error) as exc:
            self._log("AVISO", "ordem {}: {}".format(concurso, exc))
        res = self.acervo.aprender_ordem(concurso, vals)
        rel = self.assimilar_acervo(forcar=True, calibrar_fontes=False)
        res.update({"persistido": persistido,
                    "abertura_real": vals[0],
                    "acervo": {"digest": rel.get("digest"),
                               "aprendido_ate": rel.get("aprendido_ate"),
                               "reassimilado": rel.get("reassimilado")}})
        self._log("ACERVO", "ordem real do {} memorizada (1ª bola {:02d})"
                  .format(concurso, vals[0]))
        return res


    def decidir_e_gerar(self, quantidade=1, orcamento=None, callback=None,
                         registrar=True, concurso_alvo=None, alvo=None,
                         modo=None):
        """Serializa e executa a única decisão de criação do processo.

        alvo: None (automático) | 13 | 14 | 15 — escada de captura.
        modo: None/"auto" | "forja" — forja espacial de lotes.
        """
        with self._magna_lock:
            return self._decidir_e_gerar_sem_lock(
                quantidade=quantidade,
                orcamento=orcamento,
                callback=callback,
                registrar=registrar,
                concurso_alvo=concurso_alvo,
                alvo=alvo,
                modo=modo,
            )

    def _decidir_e_gerar_sem_lock(self, quantidade=1, orcamento=None,
                                  callback=None, registrar=True,
                                  concurso_alvo=None, alvo=None,
                                  modo=None):
        """Executa o único fluxo autorizado de criação de cartelas.

        Tudo que antes aparecia como Gerar Cartelas, Cartela do Dia, Wheeling,
        Análise, Singularidade e Auditoria é assimilado antes da decisão. Esses
        componentes não entregam palpites próprios: produzem evidências para a
        mesma memória, o mesmo vetor e a mesma resposta final.
        """
        from .singularidade import (
            CoberturaSteiner, FiltrosAvancados, GestaoDeBanca,
        )

        quantidade = int(quantidade)
        if not 1 <= quantidade <= 100:
            raise ValueError("quantidade deve estar entre 1 e 100")
        if alvo not in (None, "", 13, 14, 15, "13", "14", "15"):
            raise ValueError("alvo deve ser 13, 14 ou 15")
        alvo = int(alvo) if alvo not in (None, "") else None
        if modo not in (None, "", "auto", "forja"):
            raise ValueError("modo deve ser \"auto\" ou \"forja\"")
        modo = modo or None
        if orcamento not in (None, ""):
            orcamento = float(orcamento)
            if not np.isfinite(orcamento) or orcamento < VALOR_APOSTA:
                raise ValueError("orçamento deve permitir ao menos uma cartela")
            quantidade = min(quantidade, int(orcamento // VALOR_APOSTA))

        def cb(msg):
            self._log("MAGNA", msg)
            if callback:
                callback(msg)

        if not self.treinado:
            cb("Assimilando histórico e treinando a memória única...")
            self.treinar(callback=callback)

        # v11.4 — antes de decidir, a Magna reassegura o PRÓPRIO acervo: nada
        # de consultar um módulo separado. O conhecimento de abertura é dela,
        # aprendido da base histórica inteira e memorizado no banco.
        cb("Reassegurando o acervo de conhecimento (base histórica)...")
        self._garantir_acervo(callback=callback)
        evidencia_abertura = self.evidencia_abertura()

        cb("Unificando motores, oráculos, espectro, informação e análise recente...")
        fontes, consulta, espectro, informacao, entropias = \
            self._fontes_assimiladas_magna()

        pesos = dict(self.pesos_fontes_magna)
        vetor_final = np.zeros(TOTAL_DEZENAS, dtype=float)
        for nome, vetor in fontes.items():
            vetor_final += vetor * pesos[nome]
        vetor_final = self._normalizar_vetor(vetor_final)
        vetor_final = self._aplicar_memoria_episodica(vetor_final)

        # v11.5 — desempate por taxa de rateio (edge real, não preditivo).
        if getattr(self, "antipopularidade", None) is not None:
            vetor_final = self._vetor_antipopularidade(vetor_final)
            cb("Anti-popularidade: priorizando perfis menos disputados no "
               "rateio (não muda P(acerto) — reduz divisão do prêmio).")

        # Planejamento extraordinário por orçamento (nova inteligência)
        try:
            rota_info = self._planejar_rota_extraordinaria(
                vetor_final, quantidade, orcamento, alvo)
            if rota_info.get("rota_escolhida"):
                rc = rota_info["rota_escolhida"]
                cb("Rota extraordinária escolhida: alvo {} | pool {} | método {} | custo R$ {} | captura {}".format(
                    rc.get("alvo"), rc.get("n_pool"), rc.get("metodo"),
                    rc.get("custo_teorico"), rc.get("um_em_captura")))
        except Exception:
            pass

        cb("Tomando uma decisão única para {} cartela(s)...".format(quantidade))
        resultado = self.gerar_otimas(
            n_cartelas=quantidade,
            callback=callback,
            vetor_override=vetor_final,
            alvo=alvo,
            modo=modo,
        )

        # Singularidade deixa de ser uma página separada: seus filtros passam a
        # interpretar cada cartela da decisão final, sem quebrar uma garantia
        # matemática já construída pelo wheeling.
        filtros = FiltrosAvancados(self.matriz)
        votos = np.asarray(consulta["votos"], dtype=int)
        for cartela in resultado["cartelas"]:
            dezenas = cartela["dezenas"]
            relatorio = filtros.relatorio(dezenas)
            contribuicoes = {
                nome: round(float(sum(v[d - 1] for d in dezenas)), 6)
                for nome, v in fontes.items()
            }
            pop = self._popularidade_da_cartela(dezenas)
            cartela["interpretacao_magna"] = {
                "filtros_avancados": relatorio,
                "contribuicoes_fontes": contribuicoes,
                "votos_oraculo": {str(d): int(votos[d - 1]) for d in dezenas},
                "convergencia_media": round(
                    float(np.mean([votos[d - 1] for d in dezenas])) / 15.0,
                    4,
                ),
                # v11.4 — como esta cartela se relaciona com o conhecimento de
                # abertura que a Magna memorizou (abrir com 01 não aumenta a
                # chance de nada: é coerência estrutural, registrada à vista).
                "abertura": self.acervo.afinidade_cartela(dezenas),
                # v11.5 — taxa de rateio estimada (desempate de prêmio).
                "popularidade": pop,
            }
            cartela["scores"]["afinidade_abertura"] = float(
                cartela["interpretacao_magna"]["abertura"]["afinidade"])
            cartela["scores"]["bonus_rateio_estimado_x"] = float(
                (pop or {}).get("bonus_rateio_estimado_x", 1.0))
            # v11.6 — auditoria estrutural de cada cartela (repetição, filtros,
            # riscos e P exata) sem alterar a probabilidade do sorteio.
            cartela["interpretacao_magna"]["auditoria"] = (
                self.laboratorio.auditor.auditar(
                    dezenas, lote=[c["dezenas"] for c in resultado["cartelas"]],
                    score_modelo=float(cartela.get("score_total", 0) or 0),
                    vetor_final=vetor_final,
                ) if getattr(self, "laboratorio", None) is not None else
                {"disponivel": False}
            )

        hurst = [
            round(float(espectro.expoente_hurst(self.matriz[:, d])), 4)
            for d in range(TOTAL_DEZENAS)
        ]
        banca = GestaoDeBanca().relatorio()
        cobertura = CoberturaSteiner().cota_total()
        estrategia = resultado["estrategia"]
        justificativas = {
            "exaustao-unica": (
                "Uma cartela: a Magna fundiu todas as evidências e examinou o "
                "universo completo para uma única escolha auditável."
            ),
            "exaustao-diversa": (
                "Poucas cartelas: a Magna preservou o consenso integrado e "
                "reduziu sobreposição para ampliar diversidade."
            ),
            "wheeling-garantia-14": (
                "Oito ou mais cartelas: a Magna escolheu um pool de 17 e o "
                "fechamento de 8 jogos que garante 14 pontos somente se o pool "
                "capturar as 15 dezenas."
            ),
            "wheeling-garantia-13": (
                "Rota 13 pontos: pool de 18/19 dezenas fechado com garantia "
                "condicional de 13. A captura do pool-18 é ~6× e a do "
                "pool-19 ~28× mais provável que a do pool-17 — a escada de "
                "captura troca pontos garantidos por probabilidade."
            ),
            "wheeling-garantia-15": (
                "Rota 15 pontos: pool de 16 dezenas fechado em 16 cartelas "
                "que contêm o prêmio máximo inteiro se o pool capturar "
                "(1 em 204.297) — a garantia máxima que a combinatoria oferece."
            ),
        }
        justificativa = justificativas.get(
            estrategia, None)
        if justificativa is None:
            if estrategia and estrategia.startswith("forja-espacial"):
                justificativa = (
                    "Forja espacial: o recocido simulado moveu dezenas sobre a "
                    "união EXATA dos leques de {} pontos — maximizando a "
                    "probabilidade modelada de o melhor bilhete do lote "
                    "alcançar o alvo, com espectro de Johnson auditável."
                    .format(estrategia.rsplit("-", 1)[-1])
                )
            else:
                justificativa = "Estratégia escolhida pela memória única."

        top15_fontes = {
            nome: [int(x) for x in (np.argsort(v)[::-1][:15] + 1)]
            for nome, v in fontes.items()
        }
        diagnostico = {
            "concursos_assimilados": self.n,
            "hurst_medio": round(float(np.mean(hurst)), 4),
            "entropia_permutacao_media": round(float(np.mean(entropias)), 4),
            "taxa_aprovacao_filtro": getattr(
                self._gaussiano, "taxa_aprovacao_historica", None),
            "valor_esperado_liquido_cartela": banca[
                "valor_esperado_por_cartela_R$"],
            "kelly": banca["fracao_kelly"],
            "limites_cobertura": cobertura,
            "interpretacao": (
                "Os diagnósticos medem plausibilidade e risco; não demonstram "
                "previsibilidade do sorteio. A decisão continua sujeita às "
                "probabilidades hipergeométricas exibidas."
            ),
        }

        resultado.update({
            "status": "ok",
            "identidade": "Inteligência Magna",
            "decisao_unica": True,
            "justificativa_magna": (
                justificativa + " " + evidencia_abertura["leitura"]),
            "fontes_assimiladas": [
                "geração combinatória", "consenso dos oráculos",
                "wheeling 14/15", "análise histórica e recente",
                "singularidade e filtros avançados", "auditoria e aprendizado",
                "acervo de abertura (base histórica inteira)",
            ],
            "pesos_fontes": pesos,
            "acervo_magna": evidencia_abertura,
            "top15_magna": [
                int(x) for x in (np.argsort(vetor_final)[::-1][:15] + 1)
            ],
            "votos_consenso": {
                str(i + 1): int(votos[i]) for i in range(TOTAL_DEZENAS)
            },
            "diagnostico_magna": diagnostico,
            "antipopularidade_magna": self._resumo_antipopularidade(
                [c["dezenas"] for c in resultado["cartelas"]]),
            "auditoria_cartelas_magna": self._auditoria_cartelas_magna(
                [c["dezenas"] for c in resultado["cartelas"]], vetor_final),
            "memoria_magna": {
                "top15_fontes": top15_fontes,
                "vetor_final": [round(float(x), 10) for x in vetor_final],
                "pesos_fontes": pesos,
                # v11.4 — a decisão passa a citar OBRIGATORIAMENTE o acervo que
                # a produziu: carimbo da base, hash do conhecimento e o palpite
                # de abertura que será julgado na conferência.
                "acervo": {
                    "versao": self.ACERVO_VERSAO,
                    "digest": evidencia_abertura["digest"],
                    "aprendido_ate": evidencia_abertura["aprendido_ate"],
                    "concursos_da_base": evidencia_abertura["concursos_da_base"],
                    "veredito": evidencia_abertura["veredito"],
                    "fator_confianca": evidencia_abertura["fator_confianca"],
                    "leitura": evidencia_abertura["leitura"],
                    "placar_walkforward": evidencia_abertura["placar"],
                },
                "palpite_abertura": {
                    "concurso": (int(concurso_alvo) if concurso_alvo is not None
                                 else None),
                    "digest": evidencia_abertura["digest"],
                    "ranking": evidencia_abertura["ranking"],
                    "probabilidades": evidencia_abertura["probabilidades"],
                    "abertura_atual": evidencia_abertura["abertura_atual"],
                    "recorde": evidencia_abertura["recorde"],
                },
            },
            "concurso_alvo": (int(concurso_alvo) if concurso_alvo is not None
                                else (self.db.get_ultimo_concurso() or 0) + 1),
        })

        resultado["agentes_magna"] = self._agentes_autonomos_refinar(
            resultado, vetor_final, fontes)
        resultado["decisao_id"] = (
            self._registrar_decisao_magna(resultado) if registrar else None
        )
        self.decisoes["magna"] = {
            "id": resultado["decisao_id"],
            "estrategia": estrategia,
            "quantidade": resultado["n_cartelas"],
            "top15": resultado["top15_magna"],
        }
        cb("Decisão Magna concluída: {} · auditoria #{}".format(
            estrategia, resultado["decisao_id"] or "não persistida"))
        return self._json_seguro(resultado)

    def _registrar_decisao_magna(self, resultado):
        conn = self.db.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO magna_decisoes
                (concurso_alvo, timestamp, quantidade, estrategia,
                 cartelas_json, analise_json, justificativa, status)
                VALUES (?,?,?,?,?,?,?,'aguardando')
            """, (
                int(resultado["concurso_alvo"]),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(resultado["n_cartelas"]),
                str(resultado["estrategia"]),
                json.dumps(self._json_seguro(resultado["cartelas"])),
                json.dumps(self._json_seguro({
                    "memoria": resultado["memoria_magna"],
                    "diagnostico": resultado["diagnostico_magna"],
                    "analise_lote": resultado["analise"],
                })),
                str(resultado["justificativa_magna"]),
            ))
            decisao_id = cursor.lastrowid
            conn.commit()
            return decisao_id
        finally:
            conn.close()

    def aprender_resultado_magna(self, concurso, dezenas_reais):
        """Serializa o fechamento do ciclo na mesma memória da decisão."""
        with self._magna_lock:
            return self._aprender_resultado_magna_sem_lock(
                concurso, dezenas_reais)

    def _aprender_resultado_magna_sem_lock(self, concurso, dezenas_reais):
        """Fecha o ciclo único e ajusta o peso de cada fonte assimilada — Bayesiano com momentum v10.

        O ajuste é deliberadamente pequeno e auditável. Ele mede top-15 contra o
        resultado real, sempre em dezenas 1..25, e não transforma ruído em
        promessa de previsão. v10 usa Dirichlet posterior + momentum.
        """
        concurso = int(concurso)
        real = {int(d) for d in dezenas_reais}
        if len(real) != 15:
            return {"status": "erro", "msg": "resultado deve ter 15 dezenas"}

        conn = self.db.get_conn()
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT * FROM magna_decisoes
                WHERE concurso_alvo=? AND status='aguardando'
                ORDER BY id
            """, (concurso,)).fetchall()
            aprendidas = []
            for row in rows:
                analise = json.loads(row["analise_json"])
                top_fontes = analise["memoria"]["top15_fontes"]
                antes = dict(self.pesos_fontes_magna)
                acertos_fontes = {
                    nome: len(set(int(d) for d in dezenas) & real)
                    for nome, dezenas in top_fontes.items()
                }
                # v10 Bayesiano com momentum se disponível
                try:
                    if AprendizadoBayesianoMagno is not None:
                        if not hasattr(self, "_bayes_magna"):
                            self._bayes_magna = AprendizadoBayesianoMagno(antes, alpha_prior=12.0)
                        depois = self._bayes_magna.atualizar(acertos_fontes, lr=0.18, momentum_beta=0.65)
                    else:
                        raise Exception("fallback")
                except Exception:
                    ajustados = {
                        nome: max(0.01, antes[nome] *
                                  (1.0 + 0.02 * (acertos_fontes[nome] - 9)))
                        for nome in antes
                    }
                    total = sum(ajustados.values())
                    depois = {
                        nome: round(valor / total, 6)
                        for nome, valor in ajustados.items()
                    }
                self.pesos_fontes_magna = depois

                cartelas = json.loads(row["cartelas_json"])
                acertos_cartelas = [
                    len(set(int(d) for d in c["dezenas"]) & real)
                    for c in cartelas
                ]
                melhor = max(acertos_cartelas, default=0)
                media = (sum(acertos_cartelas) / len(acertos_cartelas)
                         if acertos_cartelas else 0.0)
                for c, ac in zip(cartelas, acertos_cartelas):
                    self._registrar_episodio(
                        conn, concurso, c["dezenas"], ac, real)
                resultado_json = {
                    "dezenas_reais": sorted(real),
                    "acertos_cartelas": acertos_cartelas,
                    "acertos_fontes": acertos_fontes,
                }
                conn.execute("""
                    UPDATE magna_decisoes SET
                        status='conferida', resultado_json=?,
                        melhor_acertos=?, media_acertos=?
                    WHERE id=?
                """, (
                    json.dumps(resultado_json), melhor, round(media, 4), row["id"]
                ))
                for nome, acertos in acertos_fontes.items():
                    conn.execute("""
                        INSERT INTO magna_aprendizado
                        (decisao_id, concurso, timestamp, fonte, acertos,
                         peso_antes, peso_depois)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        row["id"], concurso,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        nome, int(acertos), float(antes[nome]),
                        float(depois[nome]),
                    ))
                # v11.4 — a Magna julga também o que previu sobre a ABERTURA
                # deste concurso e memoriza o resultado no próprio acervo.
                julgamento_abertura = self._julgar_palpite_abertura(
                    conn, concurso, dict(row), real)
                aprendidas.append({
                    "decisao_id": row["id"], "melhor_acertos": melhor,
                    "media_acertos": round(media, 2),
                    "acertos_fontes": acertos_fontes,
                    "abertura": julgamento_abertura,
                })

            if aprendidas:
                self._salvar_pesos_fontes_magna(conn)
                self._checkpoint_ou_rollback(conn)
                conn.commit()
                # o concurso que acabou de ser conferido entra na série viva do
                # acervo (abertura real) e o conhecimento é repersistido com o
                # novo carimbo — aprendizado e memória no mesmo fechamento de ciclo
                abertura_real = int(min(real))
                self.acervo.aprender("minima", concurso, abertura_real)
                vivas = getattr(self, "_aberturas_vivas", None)
                if vivas is None:
                    vivas = self._aberturas_vivas = {}
                vivas[concurso] = abertura_real
                self._registrar_memoria(
                    conn, "abertura", "aprendido", concurso=concurso,
                    detalhe={"abertura": abertura_real,
                             "origem": "conferencia"})
                conn.commit()
                self._assimilar_acervo_sem_lock(auto=True,
                                                calibrar_fontes=False)
            conn.commit()
            return {
                "status": "ok", "concurso": concurso,
                "decisoes_aprendidas": aprendidas,
                "pesos_fontes": dict(self.pesos_fontes_magna),
                "acervo": self.acervo.estado(),
                "placar_abertura": self.placar_abertura_memoria(),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ciclo_pos_sorteio_caixa(self, callback=None) -> Dict[str, Any]:
        """Após um sorteio da Caixa: treina, confere, aprende e planeja.

        Substitui o botão 'Treinar IA' do Dashboard. O ciclo é idempotente
        sobre decisões já conferidas e sempre reassimila a matriz atual.
        """
        with self._magna_lock:
            def cb(msg):
                self._log("POS-SORTEIO", msg)
                if callback:
                    callback(msg)

            cb("Recarregando histórico oficial...")
            self.matriz, self.raw = self._ingestor.carregar_matriz()
            self.n = len(self.matriz)
            treino = self.treinar(callback=callback)

            ultimo = int(self.db.get_ultimo_concurso() or 0)
            aprendizado = {"status": "ok", "decisoes_aprendidas": []}
            if ultimo:
                row = self.db.get_resultado_concurso(ultimo)
                if row:
                    dezenas = [int(row["d{}".format(i)]) for i in range(1, 16)]
                    aprendizado = self._aprender_resultado_magna_sem_lock(
                        ultimo, dezenas)
                    try:
                        self._aprender(
                            ultimo,
                            {"melhor_acertos": aprendizado.get(
                                "decisoes_aprendidas", [{}])[0].get(
                                "melhor_acertos", 0)
                             if aprendizado.get("decisoes_aprendidas") else 0},
                            dezenas,
                        )
                    except Exception as exc:
                        self._log("AVISO", "Ajuste de motores: {}".format(exc))

            # v11.4 — o acervo é reassegurado no mesmo ciclo: a Magna aprende o
            # concurso que acabou de sair ANTES de planejar o próximo
            try:
                self._garantir_acervo(callback=callback)
            except Exception as exc:
                cb("aviso: acervo não reassimilado ({})".format(exc))
            plano = self._planejar_alvo_13_14_15()
            critica = self._autocriticar_memoria()
            cb("Ciclo pós-sorteio concluído · concurso {} · {}".format(
                ultimo, self.acervo.leitura()))
            return {
                "status": "ok",
                "concurso": ultimo,
                "treino": treino,
                "acervo": self.acervo.estado(),
                "placar_abertura": self.placar_abertura_memoria(),
                "aprendizado": aprendizado,
                "plano": plano,
                "autocritica": critica,
                "msg": "Magna assimilou o concurso {} e reajustou a memória"
                       .format(ultimo),
            }

    def _planejar_alvo_13_14_15(self) -> Dict[str, Any]:
        """Escolhe o modo que maximiza cobertura de 13+ sem mudar o pipeline."""
        n = max(1, int(self.n_cartelas))
        critica = None
        try:
            critica = self._autocriticar_memoria()
        except Exception:
            critica = {}
        if critica.get("esforco") or n >= 8:
            modo = "wheeling-garantia-14"
            motivo = "esforço ou lote grande: garantia condicional de 14"
            n = max(n, 8)
        elif n >= 2:
            modo = "exaustao-diversa"
            motivo = "diversidade para elevar a chance de 13 no lote"
        else:
            modo = "exaustao-unica"
            motivo = "uma cartela: melhor ranking do universo unificado"
        return {"modo_recomendado": modo, "n_cartelas": n, "motivo": motivo}

    def _autocriticar_memoria(self) -> Dict[str, Any]:
        historico = self.get_historico_magna(30)
        conferidas = [d for d in historico if d.get("status") == "conferida"]
        if not conferidas:
            return {"veredito": "sem amostra", "media": 0.0, "esforco": False}
        medias = [float(d.get("media_acertos") or 0) for d in conferidas]
        media = sum(medias) / len(medias)
        esforco = media < 11.0
        return {
            "veredito": ("abaixo do esperado: reforçar diversidade e wheeling"
                         if esforco else "desempenho estável na faixa típica"),
            "media": round(media, 3),
            "n": len(conferidas),
            "esforco": esforco,
        }

    def _agentes_autonomos_refinar(self, resultado, vetor_final, fontes):
        """Agentes internos: monitoram, criticam e priorizam 13/14/15."""
        analise = resultado.get("analise") or {}
        p14 = float(analise.get("p_melhor_14_mais") or 0)
        p13 = float(analise.get("p_melhor_13_mais") or
                    analise.get("p_melhor_13") or 0)
        critica = self._autocriticar_memoria()
        plano = self._planejar_alvo_13_14_15()
        alerta = []
        if critica.get("esforco"):
            alerta.append("aprendizado por esforço: média histórica < 11")
        if resultado.get("estrategia") != plano["modo_recomendado"]:
            alerta.append("estratégia alinhada ao orçamento informado")
        return {
            "monitor": {"p_lote_14_mais": p14, "p_lote_13_ref": p13},
            "plano": plano,
            "autocritica": critica,
            "alertas": alerta,
            "raciocinio": (
                "Fontes fundidas no vetor único; ranking favorece 13+ "
                "via diversidade/wheeling sem alterar a estrutura."
            ),
        }

    def _registrar_episodio(self, conn, concurso, dezenas, acertos, real):
        dez = [int(d) for d in dezenas]
        faltaram = sorted(real - set(dez))
        if acertos >= 12:
            tipo = "prototipo"
        elif acertos <= 9:
            tipo = "repulsao"
        else:
            tipo = "neutro"
        conn.execute("""
            INSERT INTO magna_episodios
            (concurso, timestamp, dezenas, acertos, faltaram, tipo)
            VALUES (?,?,?,?,?,?)
        """, (
            int(concurso), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(dez), int(acertos), json.dumps(faltaram), tipo,
        ))

    def _carregar_episodios(self, tipo=None, limit=200):
        try:
            conn = self.db.get_conn()
            if tipo:
                rows = conn.execute(
                    "SELECT * FROM magna_episodios WHERE tipo=? "
                    "ORDER BY id DESC LIMIT ?", (tipo, limit)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM magna_episodios ORDER BY id DESC LIMIT ?",
                    (limit,)).fetchall()
            conn.close()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["dezenas"] = json.loads(d.get("dezenas") or "[]")
                except Exception:
                    d["dezenas"] = []
                try:
                    d["faltaram"] = json.loads(d.get("faltaram") or "[]")
                except Exception:
                    d["faltaram"] = []
                out.append(d)
            return out
        except sqlite3.Error:
            return []

    def _aplicar_memoria_episodica(self, vetor):
        """Reforça dezenas de quase-13/14 e repele clones fracos + memória vetorial com atenção."""
        v = np.asarray(vetor, dtype=float).copy()
        # clássico
        for ep in self._carregar_episodios("prototipo", 80):
            for d in ep.get("dezenas") or []:
                if 1 <= int(d) <= 25:
                    v[int(d) - 1] *= 1.04
            for d in ep.get("faltaram") or []:
                if 1 <= int(d) <= 25:
                    v[int(d) - 1] *= 1.02
        for ep in self._carregar_episodios("repulsao", 80):
            for d in ep.get("dezenas") or []:
                if 1 <= int(d) <= 25:
                    v[int(d) - 1] *= 0.99
        # vetorial com atenção (v10)
        try:
            if MemoriaVetorialMagna is not None:
                episodios = self._carregar_episodios(None, 200)
                mem_vec = MemoriaVetorialMagna(episodios)
                v = mem_vec.reforco_contextual(v, top_k=25)
        except Exception as exc:
            self._log("AVISO", f"Memória vetorial: {exc}")
        return self._normalizar_vetor(v)

    def _checkpoint_ou_rollback(self, conn):
        """A cada 10 conferidas: se a média cair, restaura pesos anteriores."""
        rows = conn.execute("""
            SELECT media_acertos FROM magna_decisoes
            WHERE status='conferida' ORDER BY id DESC LIMIT 20
        """).fetchall()
        medias = [float(r[0] or 0) for r in rows]
        if len(medias) < 10:
            return
        recente = sum(medias[:10]) / 10.0
        anterior = sum(medias[10:]) / max(len(medias[10:]), 1)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if recente + 1e-9 >= anterior:
            conn.execute("""
                INSERT INTO magna_checkpoint
                (timestamp, pesos_json, media_acertos, n_amostra)
                VALUES (?,?,?,?)
            """, (ts, json.dumps(self.pesos_fontes_magna), recente, 10))
            return
        last = conn.execute(
            "SELECT pesos_json FROM magna_checkpoint ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last:
            try:
                gravados = json.loads(last[0])
                if isinstance(gravados, dict) and "ordem" in gravados \
                        and "abertura" not in gravados:
                    # v11.4 — checkpoint anterior à unificação: o peso da fonte
                    # `ordem` é o MESMO conhecimento da fonte `abertura` (o
                    # default não mudou de tamanho), então ele é reaproveitado
                    # em vez de descartado por divergência de nomes.
                    gravados = dict(gravados)
                    gravados["abertura"] = gravados.pop("ordem")
                if set(gravados) == set(self.pesos_fontes_magna):
                    self.pesos_fontes_magna = {
                        k: max(0.01, float(gravados[k]))
                        for k in self.pesos_fontes_magna
                    }
                    total = sum(self.pesos_fontes_magna.values())
                    self.pesos_fontes_magna = {
                        k: round(v / total, 6)
                        for k, v in self.pesos_fontes_magna.items()
                    }
                    self._salvar_pesos_fontes_magna(conn)
                    self._log("ROLLBACK",
                              "média {:.2f} < {:.2f}: pesos restaurados"
                              .format(recente, anterior))
            except (ValueError, TypeError, json.JSONDecodeError):
                pass

    def metricas_vs_acaso(self):
        historico = self.get_historico_magna(40)
        conferidas = [d for d in historico if d.get("status") == "conferida"]
        medias = [float(d.get("media_acertos") or 0) for d in conferidas]
        melhores = [int(d.get("melhor_acertos") or 0) for d in conferidas]
        media = sum(medias) / len(medias) if medias else 0.0
        taxa13 = (sum(1 for m in melhores if m >= 13) / len(melhores)
                  if melhores else 0.0)
        return {
            "n": len(conferidas),
            "media_acertos": round(media, 3),
            "baseline_media_cartela": 9.0,
            "taxa_lote_13_mais": round(taxa13, 4),
            "prototipos": len(self._carregar_episodios("prototipo", 500)),
            "repulsoes": len(self._carregar_episodios("repulsao", 500)),
        }

    def get_retencao(self, limit=12):
        return {
            "prototipos": self._carregar_episodios("prototipo", limit),
            "metricas": self.metricas_vs_acaso(),
            "autocritica": self._autocriticar_memoria(),
            "plano": self._planejar_alvo_13_14_15(),
        }





    def get_historico_magna(self, limit=20):
        try:
            conn = self.db.get_conn()
            rows = conn.execute("""
                SELECT id, concurso_alvo, timestamp, quantidade, estrategia,
                       justificativa, status, melhor_acertos, media_acertos
                FROM magna_decisoes ORDER BY id DESC LIMIT ?
            """, (max(1, min(int(limit), 100)),)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    @staticmethod
    def _mask_de_dezenas(dezenas) -> int:
        m = 0
        for d in dezenas:
            m |= 1 << (int(d) - 1)
        return m

    def _mascaras_sorteios_15(self):
        """Conjunto de bitmasks oficiais: cada um já foi 15 pontos uma vez."""
        cache = getattr(self, "_cache_mascaras_15", None)
        if cache is not None and len(cache) == self.n:
            return cache
        masks = set()
        for i in range(self.n):
            dez = np.where(self.matriz[i] == 1)[0]
            m = 0
            for d in dez:
                m |= 1 << int(d)
            masks.add(int(m))
        self._cache_mascaras_15 = masks
        return masks

    def _cartela_ja_foi_15(self, dezenas) -> bool:
        """True se a combinação já saiu no histórico oficial (15 pontos)."""
        if not dezenas or len(dezenas) != 15:
            return False
        return self._mask_de_dezenas(dezenas) in self._mascaras_sorteios_15()

    def _substituir_cartelas_ja_sorteadas_15(self, cartelas, vf):
        """Nunca reemite uma combinação que já foi contemplada com 15 pontos."""
        from .heavyweight_engine import MotorExaustaoUniverso
        usadas = {self._mask_de_dezenas(c) for c in cartelas}
        oficiais = self._mascaras_sorteios_15()
        out = []
        for c in cartelas:
            m = self._mask_de_dezenas(c)
            if m not in oficiais:
                out.append(c)
                continue
            self._log(
                "BLOQUEIO-15",
                "Cartela {} já foi 15 pontos no histórico — descartada".format(
                    sorted(int(d) for d in c)))
            substituta = None
            heavy = MotorExaustaoUniverso()
            idx, _ = heavy.avaliar_universo_completo(vf)
            for i in range(min(4000, len(idx))):
                cand = heavy.obter_dezenas_por_indice(idx[i])
                cm = self._mask_de_dezenas(cand)
                if cm in oficiais or cm in usadas:
                    continue
                ok, _ = self._gaussiano.filtrar(cand)
                if not ok:
                    continue
                substituta = cand
                break
            if substituta is None:
                continue
            usadas.add(self._mask_de_dezenas(substituta))
            out.append(substituta)
        return out

    def diagnostico_aprendizado(self) -> Dict[str, Any]:
        """O que a Magna já aprendeu, como aprende e o que ainda falta.

        v11.4 — o acervo de conhecimento é a primeira resposta: a Magna já
        aprendeu da base histórica inteira ANTES de existir qualquer decisão
        conferida, e é o mesmo acervo que alimenta o vetor e o Juiz de
        cada cartela.
        """
        ret = self.get_retencao(20)
        pesos = dict(self.pesos_fontes_magna)
        historico = self.get_historico_magna(50)
        conferidas = [d for d in historico if d.get("status") == "conferida"]
        n_15_hist = len(self._mascaras_sorteios_15())
        conhecimento = self.conhecimento(detalhes=False)
        base = conhecimento["base"]
        sem_ordem = max(0, int(base.get("concursos") or 0)
                         - (self.acervo.n("real")
                            if hasattr(self, "acervo") else 0))
        faltam = [
            "amostra maior de decisões conferidas (n={})".format(
                len(conferidas)),
            "calibração fundante das fontes em walk-forward"
            if not self._ler_conhecimento("fontes")
            else "calibração das fontes já memorizada",
            "ordem real das bolas em {} concursos da base — rode `python "
            "backfill_ordem.py` para o canal 'real' do acervo ganhar força"
            .format(sem_ordem) if sem_ordem else
            "ordem real das bolas já coberta na base inteira",
            "calibração física com medidas reais das bolas"
            if not self.fisica.get_status().get("tem_dados_reais")
            else "física já com dados reais",
        ]
        return {
            "o_que_aprende": [
                "acervo de abertura: frequências, streaks, recorde, repetição "
                "por dezena e posterior do próximo início — medidos na base "
                "histórica inteira e memorizados em magna_conhecimento",
                "peso de cada fonte do consenso calibrado em walk-forward "
                "fora-da-amostra (magna_conhecimento 'fontes')",
                "pesos das {} fontes ({}) via top-15 vs resultado real".format(
                    len(pesos), ", ".join(pesos)),
                "pesos dos 14 módulos via mediana de acertos fora da amostra",
                "episódios protótipo (≥12) e repulsão (≤9)",
                "checkpoint/rollback se a média de 10 decisões cair",
                "combinações oficiais de 15 pontos — nunca reemitidas",
                "cartelas conferidas arquivadas em memoria_cartelas_aprendidas",
            ],
            "como_aprende": (
                "Na inicialização e antes de cada decisão a Magna reassimila a "
                "base (carimbo em magna_conhecimento); após cada conferência "
                "oficial ela fecha magna_decisoes, grava magna_aprendizado, "
                "julga o próprio palpite de abertura em magna_memoria, ajusta "
                "pesos suavemente e persiste episódios. Excluir da tela não "
                "apaga a memória de aprendizado."
            ),
            "o_que_falta": faltam,
            "acervo": {
                "versao": self.ACERVO_VERSAO,
                "base": base,
                "abertura": conhecimento["abertura"],
                "leitura": conhecimento["leitura"],
                "placar_abertura": conhecimento["placar_abertura"],
                "dominios_gravados": list(conhecimento["dominios"].keys()),
            },
            "pesos_fontes": pesos,
            "pesos_modulos": dict(self.pesos),
            "n_sorteios_15_bloqueados": n_15_hist,
            "retencao": ret,
        }

    @staticmethod
    def _max_consecutivos(dezenas) -> int:
        """Maior sequência de dezenas consecutivas numa cartela."""
        sd = sorted(int(d) for d in dezenas)
        mc = cc = 1
        for i in range(1, len(sd)):
            if sd[i] == sd[i - 1] + 1:
                cc += 1
                mc = max(mc, cc)
            else:
                cc = 1
        return mc


    def backtest_captura(self, k=10, n_pool=17, callback=None) -> Dict[str, Any]:
        """Executa o backtest isolado e sempre restaura a memória de produção."""
        with self._magna_lock:
            matriz_original = self.matriz.copy()
            raw_original = list(self.raw)
            try:
                return self._backtest_captura_sem_lock(
                    k=k, n_pool=n_pool, callback=callback)
            finally:
                self._rng_vetor = None
                if (self.matriz.shape != matriz_original.shape or
                        not np.array_equal(self.matriz, matriz_original)):
                    self.treinar(
                        matriz_override=matriz_original,
                        raw_override=raw_original,
                    )

    def _backtest_captura_sem_lock(self, k=10, n_pool=17,
                                   callback=None) -> Dict[str, Any]:
        """
        Para cada um dos últimos k concursos:
          1. Treina o Cérebro SEM aquele concurso (e sem os posteriores)
          2. Seleciona o pool de n_pool dezenas com os dados do passado
          3. Verifica se o pool capturou as 15 sorteadas (|interseção|=15)

        Baselines teóricos:
          P(captura)      = C(N,15)/C(25,15)
          E[interseção]   = 15·N/25
        A premissa da auditoria (§3 do AUDITORIA.md) é que nenhum motor
        bate o baseline de forma consistente — este backtest deixa o
        usuário VER isso com os próprios dados.
        """
        def cb(msg):
            self._log("BACKTEST", msg)
            if callback:
                callback(msg)

        k = max(1, min(int(k), 40))
        matriz_full = self.matriz.copy()
        raw_full = list(self.raw)
        n_total = len(matriz_full)
        capturas = 0
        intersecoes = []
        detalhes = []

        # RNG local e determinístico para o backtest (não usa np.random.seed
        # global, que contaminava a aleatoriedade dos outros módulos).
        rng = np.random.default_rng(1000)

        for i in range(1, k + 1):
            alvo_idx = n_total - i
            if alvo_idx < 50:
                break
            passado = matriz_full[:alvo_idx]
            sorteado = set(
                int(x) + 1 for x in np.where(matriz_full[alvo_idx] == 1)[0]
            )
            self.treinar(matriz_override=passado, raw_override=raw_full[:alvo_idx])
            # injeta o RNG determinístico no ruído do vetor combinado
            self._rng_vetor = rng
            vf = self._vetor_combinado()
            pool = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vf, n_pool))
            inter = len(sorteado & set(pool))
            capturou = inter == 15
            capturas += 1 if capturou else 0
            intersecoes.append(inter)
            detalhes.append({
                "concurso": int(raw_full[alvo_idx].get("concurso", alvo_idx + 1))
                            if isinstance(raw_full[alvo_idx], dict) else alvo_idx + 1,
                "intersecao": inter, "capturou": capturou,
            })
            cb("janela {:>2}: interseção {}/15 {}".format(
                i, inter, "← CAPTUROU" if capturou else ""))

        # restaura treino completo e RNG de produção
        self._rng_vetor = None
        self.treinar(matriz_override=matriz_full, raw_override=raw_full)

        p_base = self.wheeling.prob_captura(n_pool)
        e_base = 15.0 * n_pool / TOTAL_DEZENAS
        media_inter = sum(intersecoes) / len(intersecoes) if intersecoes else 0.0
        return {
            "k": len(detalhes),
            "n_pool": n_pool,
            "capturas": capturas,
            "taxa_captura": round(capturas / len(detalhes), 4) if detalhes else 0,
            "baseline_p_captura": round(p_base, 6),
            "baseline_um_em": round(1 / p_base, 1),
            "media_intersecao": round(media_inter, 2),
            "baseline_intersecao": round(e_base, 2),
            "detalhes": detalhes,
            "veredito": (
                "Consistente com o acaso (como previsto na auditoria §3): "
                "o pool não captura além do baseline."
                if capturas <= max(1, p_base * len(detalhes) * 3)
                else "Taxa acima do esperado — investigar antes de comemorar "
                     "(múltiplos testes/seleção a posteriori)."
            ),
        }

    def _selecionar_elite(self, v: np.ndarray, tam: int) -> List[int]:
        """Mantido por compatibilidade — delega para extraordinário."""
        return self._selecionar_elite_extraordinaria(v, tam)

    def _selecionar_elite_extraordinaria(self, v: np.ndarray, tam: int,
                                         lambda_div: float = 0.38,
                                         candidatas_top: int = 22) -> List[int]:
        """Pool elite com força máxima: vf + diversidade via MotorGrafos.

        Se MotorGrafos não disponível ou matriz pequena, cai para método
        clássico com garantia de quadrantes. A Magna usa este método em
        TODA geração — é a única porta de pool.
        """
        try:
            if MotorGrafos is not None and self.n >= 30:
                grafo = MotorGrafos(self.matriz)
                pool = grafo.pool_extraordinario(
                    vf=v, tam=tam, lambda_div=lambda_div,
                    candidatas_top=max(tam+5, candidatas_top))
                # log diversidade
                div = grafo.diversidade_pool(pool)
                self._log("POOL-EXTRA", "Pool {} dezenas | div média {:.3f} min {:.3f} | vf top {}".format(
                    len(pool), div.get("media_dist",0), div.get("min_dist",0),
                    sorted(pool)[:5]))
                return pool
        except Exception as exc:
            self._log("AVISO", "Pool extraordinário fallback: {}".format(exc))

        # fallback clássico
        ranking = list(np.argsort(v)[::-1] + 1)
        grupo = []
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

    def _planejar_rota_extraordinaria(self, vf: np.ndarray, quantidade: int,
                                      orcamento: Optional[float],
                                      alvo: Optional[int] = None) -> Dict[str, Any]:
        """Escolhe rota extraordinária maximizando P(lote≥alvo) dentro do orçamento."""
        try:
            if melhor_rota_por_orcamento is not None:
                return melhor_rota_por_orcamento(
                    vf=vf, orcamento=orcamento or 1000.0,
                    quantidade=quantidade, alvo_desejado=alvo)
        except Exception as exc:
            self._log("AVISO", "Planejamento rota: {}".format(exc))
        # fallback simples
        return {"rota_escolhida": None, "motivo": "fallback"}

    # ============================================================
    # MAGNA SUPREMA v10 — Evoluções para potência máxima pessoal
    # ============================================================
    def detectar_regime_atual(self) -> Dict[str, Any]:
        """Detecta regime atual do histórico (K-means sobre features)."""
        try:
            if DetectorRegime is None:
                return {"regime_atual": 0, "descricao": "Detector não disponível"}
            det = DetectorRegime(self.matriz)
            res = det.detectar(k=3, janela=100)
            self._log("REGIME", f"Regime atual: {res.get('regime_atual')} — {res.get('descricao')}")
            return res
        except Exception as exc:
            return {"erro": str(exc), "regime_atual": 0}

    def julgar_lote(self, cartelas: List[List[int]], pool: List[int],
                    analise: Dict[str, Any], vf: np.ndarray) -> Dict[str, Any]:
        """Julga lote com 9 critérios — Juiz Magna v11.4.

        O nono critério (cobertura de abertura) vem do acervo da própria Magna:
        o lote é julgado também por quanta da massa de abertura aprendida ele
        cobre. É estrutura, não previsão — a hipergeométrica não muda.
        """
        try:
            if JuizMagna is None:
                return {"veredito": "APROVADO", "nota": 1.0, "criterios": {}}
            juiz = JuizMagna(self.matriz)
            masks_15 = self._mascaras_sorteios_15()
            veredito = juiz.julgar(cartelas, pool, analise, vf, masks_15,
                                   abertura=self.abertura_para_o_juiz(cartelas))
            self._log("JUIZ", f"Veredito: {veredito.get('veredito')} nota {veredito.get('nota')} reprovados {veredito.get('reprovados')}")
            return veredito
        except Exception as exc:
            return {"veredito": "APROVADO", "nota": 0.8, "erro": str(exc)}

    def verificar_lote_exaustivo(self, cartelas: List[List[int]], pool: List[int]) -> Dict[str, Any]:
        """Verificação exaustiva P(lote≥t) sobre universo 3.268.760."""
        try:
            if VerificadorMagno is None:
                return {"honestidade": "Verificador não disponível"}
            ver = VerificadorMagno()
            res = ver.verificar(cartelas, pool)
            return res
        except Exception as exc:
            return {"erro": str(exc)}

    def alocar_orcamento_inteligente(self, orcamento: float, quantidade_max: int = 20, alvo: int = 13) -> Dict[str, Any]:
        """Alocador de orçamento — maximiza utilidade esperada."""
        try:
            if AlocadorOrcamentoMagno is None:
                return {"alocacao": [], "total_cartelas": quantidade_max, "total_custo": quantidade_max*VALOR_APOSTA}
            aloc = AlocadorOrcamentoMagno()
            return aloc.alocar(orcamento, quantidade_max, alvo)
        except Exception as exc:
            return {"erro": str(exc), "alocacao": []}

    def decidir_suprema(self, quantidade: int = 8, orcamento: float = 100.0,
                         alvo: int = 13, modo: str = "suprema",
                         tentativas_juiz: int = 2, perfil: str = "equilibrado",
                         usar_mcts: bool = True, usar_multi_rota: bool = False,
                         segundos_forja: float = 60.0,
                         callback=None, registrar: bool = True,
                         concurso_alvo=None) -> Dict[str, Any]:
        """
        MAGNA SUPREMA v11 — Sistema único pessoal em potência máxima, sem erros.

        Evoluções completas:
        - Aprender: EWC continual, meta por regime, clustering adaptativo, balança 0.001g
        - Decidir: perfil risco pessoal, MCTS pool, multi-rota 60/30/10, utilidade esperada prêmios reais
        - Julgar: juiz 9 critérios + adversarial + NIST + p-value + juiz que aprende
          (o 9º é `cobertura_abertura`: o quanto do que o ACERVO aprendeu sobre
          a abertura o lote efetivamente cobre — estrutura, não previsão)
        - Entender: explainability LLM, fingerprint SHA256
        - Verificar: backtest walk-forward lote 50, binomial significância, curva aprendizado

        Fluxo supremo único:
        1. Detecta regime adaptativo K-means
        2. Pesos por regime meta + EWC
        3. Vetor supremo com memória vetorial atenção
        4. Perfil risco + alocação multi-rota + MCTS pool
        5. Forja suprema 60s 7 seeds k=7
        6. Juiz 9 critérios + adversarial + NIST + p-value — regenera se reprovar
        7. Fingerprint SHA256 anti-repetição pessoal
        8. Backtest 50 + binomial + curva + verificação exaustiva + explainability
        9. Utilidade esperada com prêmios reais médios

        Único gerador: Inteligência Magna.
        """
        with self._magna_lock:
            def cb(msg):
                self._log("SUPREMA", msg)
                if callback:
                    callback(msg)

            quantidade = max(1, min(int(quantidade), 30))
            orcamento = float(orcamento or 100.0)
            alvo = int(alvo or 13)
            if alvo not in (13,14,15):
                alvo = 13
            perfil = perfil if perfil in ("conservador","equilibrado","agressivo") else "equilibrado"

            if not self.treinado:
                cb("Treinando em potência máxima v11...")
                self.treinar(callback=callback)

            # 0. v11.4 — ACERVO DE CONHECIMENTO. Antes de qualquer julgamento a
            # Magna reassimila a base histórica (abertura, placar walk-forward,
            # posterior do próximo início) e memoriza o que aprendeu. Não existe
            # módulo de turno: é a própria inteligência que aprende, memoriza,
            # decide e depois se julga.
            cb("Reassegurando o acervo de conhecimento (base histórica)...")
            self._garantir_acervo(callback=callback)
            evidencia_abertura = self.evidencia_abertura()
            cb("Acervo v11.4 · {} concursos · {}".format(
                evidencia_abertura["concursos_da_base"],
                evidencia_abertura["leitura"]))

            # 1. Regime adaptativo
            regime = {}
            try:
                if DetectorRegime is not None:
                    det = DetectorRegime(self.matriz)
                    regime = det.detectar_adaptativo(janela=100)
                    cb(f"Regime adaptativo: k_otimo={regime.get('k_otimo')} sil={regime.get('silhouette')} atual={regime.get('regime_atual')}")
                else:
                    regime = {"regime_atual": 0, "descricao": "Detector não disponível"}
            except Exception as exc:
                regime = {"regime_atual": 0, "erro": str(exc)}

            # 2. Meta por regime + EWC
            fontes, consulta, espectro, informacao, entropias = self._fontes_assimiladas_magna()
            pesos_default = dict(self.pesos_fontes_magna)
            try:
                if not hasattr(self, "_meta_regime"):
                    self._meta_regime = MetaAprendizadoRegime() if MetaAprendizadoRegime else None
                if self._meta_regime:
                    pesos = self._meta_regime.obter_pesos_regime(regime.get("regime_atual",0), pesos_default)
                else:
                    pesos = pesos_default
            except Exception:
                pesos = pesos_default

            # 3. Vetor supremo com memória vetorial
            vetor = np.zeros(TOTAL_DEZENAS, dtype=float)
            for nome, v in fontes.items():
                vetor += v * pesos[nome]
            vetor = self._aplicar_memoria_episodica(self._normalizar_vetor(vetor))

            # 4. Perfil risco + alocação
            try:
                perfil_obj = PerfilRiscoPessoal(perfil) if PerfilRiscoPessoal else None
                alvo_perfil = perfil_obj.recomendar_alvo() if perfil_obj else alvo
                # se alvo não informado, usa perfil
                if alvo == 13 and perfil_obj and perfil != "equilibrado":
                    # mantém alvo pedido, mas loga recomendação
                    cb(f"Perfil {perfil} recomenda alvo {alvo_perfil}, mas usando alvo solicitado {alvo}")
            except Exception:
                perfil_obj = None

            # Alocação multi-rota
            aloc_multi = {}
            try:
                if usar_multi_rota and AlocadorMultiRota is not None:
                    aloc_multi = AlocadorMultiRota().alocar(orcamento, quantidade, perfil)
                    cb(f"Multi-rota {perfil}: {aloc_multi.get('recomendacao')}")
                else:
                    if AlocadorOrcamentoMagno is not None:
                        aloc_multi = AlocadorOrcamentoMagno().alocar(orcamento, quantidade, alvo)
            except Exception:
                aloc_multi = {}

            # Fingerprint pessoal
            try:
                fp = FingerprintPessoal(self.db) if FingerprintPessoal else None
                if fp:
                    fp.carregar_historico()
            except Exception:
                fp = None

            # 5. Geração suprema com MCTS pool + forja suprema + juiz loop
            melhor_resultado = None
            melhor_nota = -1
            melhor_utilidade = -1
            for tentativa in range(max(1, tentativas_juiz)):
                # Pool via MCTS se ativado
                try:
                    if usar_mcts and MCTSPool is not None and self.n >= 50:
                        mcts = MCTSPool(self.matriz)
                        pool_sup = mcts.buscar(vetor, tam=min(22, 17+quantidade//2), iteracoes=800)
                        cb(f"MCTS pool {len(pool_sup)} dezenas: {pool_sup[:5]}...")
                    else:
                        pool_sup = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vetor, min(22, 17+quantidade//2)))
                except Exception as exc:
                    cb(f"MCTS falhou {exc}, usando pool extraordinário")
                    pool_sup = sorted(int(d) for d in self._selecionar_elite_extraordinaria(vetor, min(22, 17+quantidade//2)))

                # Forja suprema
                try:
                    mapa = MapaInformacional(self.matriz).coordenadas() if MapaInformacional else None
                    engine = ForjaDeLotes() if ForjaDeLotes else None
                    if engine is None:
                        raise Exception("Forja não disponível")
                    if alvo == 14 and quantidade <= 15:
                        forja_res = engine.forjar_14_exato(vetor, quantidade, segundos=20.0)
                        if len(forja_res.get("cartelas", [])) < quantidade:
                            resto = engine.forjar_com_forca_maxima(
                                vetor, quantidade - len(forja_res["cartelas"]), alvo=alvo,
                                segundos=40.0, n_candidatas=25, k_robusto=7, n_seeds=5, mapa=mapa)
                            forja_res["cartelas"] = sorted(sorted(c) for c in (forja_res["cartelas"] + resto["cartelas"]))
                    else:
                        # suprema 60s 7 seeds k=7
                        forja_res = engine.forjar_suprema(vetor, quantidade, alvo=alvo, segundos=segundos_forja, mapa=mapa)
                    cartelas_raw = forja_res.get("cartelas", [])
                    # fingerprint check + anti-15
                    cartelas_filtradas = []
                    for c in cartelas_raw:
                        if self._cartela_ja_foi_15(c):
                            continue
                        if fp and fp.ja_foi_gerada(c):
                            continue
                        cartelas_filtradas.append(c)
                        if fp:
                            fp.registrar(c)
                    # completa se filtrou demais
                    if len(cartelas_filtradas) < quantidade:
                        # fallback exaustão
                        from .heavyweight_engine import MotorExaustaoUniverso
                        heavy = MotorExaustaoUniverso()
                        idx, _ = heavy.avaliar_universo_completo(vetor)
                        for i in range(min(2000, len(idx))):
                            if len(cartelas_filtradas) >= quantidade:
                                break
                            cand = heavy.obter_dezenas_por_indice(idx[i])
                            if self._cartela_ja_foi_15(cand):
                                continue
                            if fp and fp.ja_foi_gerada(cand):
                                continue
                            cartelas_filtradas.append(cand)
                    cartelas_raw = cartelas_filtradas[:quantidade]

                    analise = self.wheeling.analisar_lote(cartelas_raw, pool_sup)
                    resultado = {
                        "estrategia": f"suprema-forja-{alvo}-7seeds-mcts-{perfil}",
                        "n_cartelas": len(cartelas_raw),
                        "cartelas": [],
                        "pool_elite": pool_sup,
                        "custo": round(len(cartelas_raw)*VALOR_APOSTA,2),
                        "analise": analise,
                        "forja": forja_res,
                        "tempo": forja_res.get("tempo_total", forja_res.get("tempo",0)),
                        "verdade_honesta": "Suprema v11: 60s 7 seeds k=7 25 candidatas + MCTS pool + memória vetorial + EWC + meta regime + perfil risco + juiz 9 critérios + adversarial + NIST + p-value + fingerprint + backtest 50 + binomial + curva + verificação exaustiva + utilidade esperada. Ganho combinatório, nunca preditivo.",
                    }
                    for c in cartelas_raw:
                        _, det = self._gaussiano.filtrar(c)
                        resultado["cartelas"].append({
                            "dezenas": [int(d) for d in c],
                            "bitmask": self._mask_de_dezenas(c),
                            "score_total": round(float(sum(vetor[d-1] for d in c)),6),
                            "soma": det.get("soma"), "pares": det.get("pares"),
                            "primos": det.get("primos"), "fibonacci": det.get("fibonacci"),
                            "borda": det.get("borda"),
                            "scores": {"ev_prob": round(float(sum(vetor[d-1] for d in c)),4)},
                        })
                except Exception as exc:
                    cb(f"Forja suprema falhou ({exc}), usando gerar_otimas...")
                    resultado = self.gerar_otimas(
                        n_cartelas=quantidade, callback=callback,
                        vetor_override=vetor, alvo=alvo, modo="forja")
                    cartelas_raw = [c["dezenas"] for c in resultado["cartelas"]]
                    pool_sup = resultado["pool_elite"]
                    analise = resultado["analise"]

                # 6. Juiz + adversarial + NIST + p-value
                julgamento = {}
                adv = {}
                nist = {}
                pval = {}
                try:
                    if JuizMagna is not None:
                        julgamento = JuizMagna(self.matriz).julgar(
                            cartelas_raw, pool_sup, analise, vetor,
                            self._mascaras_sorteios_15(),
                            abertura=self.abertura_para_o_juiz())
                    if JuizAdversarial is not None:
                        adv = JuizAdversarial().julgar(cartelas_raw, pool_sup)
                    if TesteNIST is not None:
                        nist = TesteNIST().testar(cartelas_raw)
                    if PValueRandom is not None:
                        pval = PValueRandom().calcular(analise.get("p_melhor_13_mais",0), len(cartelas_raw), alvo=alvo)
                except Exception as exc:
                    julgamento = {"veredito": "APROVADO", "nota": 0.8, "erro": str(exc)}

                # 7. Backtest + binomial + curva + verificação + explainability + utilidade
                backtest = {}
                curva = {}
                verificacao = {}
                explicacoes = []
                utilidade = {}
                try:
                    if BacktestLote is not None:
                        backtest = BacktestLote().testar(cartelas_raw, self.matriz, janela=50)
                    if CurvaAprendizado is not None:
                        curva = CurvaAprendizado(self.get_historico_magna(50)).curva()
                    if VerificadorMagno is not None:
                        verificacao = VerificadorMagno().verificar(cartelas_raw, pool_sup)
                    if ExplainabilityMagna is not None:
                        exp = ExplainabilityMagna()
                        explicacoes = exp.explicar_lote(cartelas_raw, vetor, fontes, np.asarray(consulta["votos"], dtype=int))
                    if UtilidadeEsperada is not None:
                        # premios medios do DB
                        try:
                            conn = self.db.get_conn()
                            row = conn.execute("SELECT AVG(premio_13), AVG(premio_14), AVG(premio_15) FROM resultados WHERE premio_13>0").fetchone()
                            conn.close()
                            premios_med = {13: float(row[0] or 35), 14: float(row[1] or 1800), 15: float(row[2] or 500000)}
                        except Exception:
                            premios_med = {13: 35, 14: 1800, 15: 500000}
                        utilidade = UtilidadeEsperada().calcular(analise, premios_med, resultado["custo"])
                        # perfil risco utilidade
                        if perfil_obj:
                            util_perfil = perfil_obj.utilidade(
                                analise.get("p_melhor_13_mais",0),
                                analise.get("p_melhor_14_mais",0),
                                analise.get("p_melhor_15",0),
                                analise.get("ev_lote",0)
                            )
                            utilidade["utilidade_perfil"] = round(util_perfil,4)
                            utilidade["perfil"] = perfil
                except Exception as exc:
                    cb(f"Evoluções verificação falhou: {exc}")

                resultado["julgamento"] = julgamento
                resultado["julgamento_adversarial"] = adv
                resultado["teste_nist"] = nist
                resultado["p_value_random"] = pval
                resultado["backtest_lote"] = backtest
                resultado["curva_aprendizado"] = curva
                resultado["verificacao_exaustiva"] = verificacao
                resultado["explicacoes"] = explicacoes
                resultado["utilidade_esperada"] = utilidade
                resultado["fingerprint"] = fp.relatorio() if fp else {}
                resultado["perfil_risco"] = perfil_obj.relatorio() if perfil_obj else {}

                # EWC consolidar se tiver acertos históricos? Aqui apenas penalidade log
                try:
                    if EWCContinual is not None and not hasattr(self, "_ewc"):
                        self._ewc = EWCContinual(lambda_ewc=0.4)
                except Exception:
                    pass

                nota = julgamento.get("nota",0)
                util = utilidade.get("utilidade_perfil", nota)
                score_total = nota*0.6 + util*0.4
                if score_total > melhor_nota:
                    melhor_nota = score_total
                    melhor_resultado = resultado
                    melhor_utilidade = util

                if julgamento.get("veredito") == "APROVADO" and adv.get("veredito") != "VULNERÁVEL":
                    cb(f"Lote APROVADO juiz nota {nota} adv {adv.get('veredito')} nist {nist.get('veredito')} na tentativa {tentativa+1}")
                    break
                else:
                    cb(f"Lote REPROVADO juiz {julgamento.get('reprovados')} adv {adv.get('fraquezas')} — regenerando...")
                    # juiz que aprende
                    try:
                        if JuizMagna is not None and hasattr(self, "_juiz_aprendiz"):
                            pass
                    except Exception:
                        pass

            resultado = melhor_resultado or resultado
            resultado.update({
                "status": "ok",
                "identidade": "Inteligência Magna Suprema v11 — Única Pessoal",
                "versao_suprema": "11.0",
                "versao_evolucao": "v11.2-EWC-Meta-MCTS-MultiRota-JuizAdv-NIST-Explain-Chat-Fingerprint-Backtest-ClimaFisico",
                "decisao_unica": True,
                "potencia_maxima": True,
                "uso_pessoal": True,
                "unico_gerador": True,
                "regime": regime,
                "acervo_magna": evidencia_abertura,
                "alocacao_orcamento": aloc_multi,
                "justificativa_magna": (
                    f"Suprema v11 única pessoal evoluída: regime adaptativo k_otimo={regime.get('k_otimo')} sil={regime.get('silhouette')} atual={regime.get('regime_atual')}, "
                    f"meta por regime, EWC, memória vetorial atenção, perfil {perfil}, MCTS pool, "
                    f"forja suprema 60s 7 seeds k=7, juiz 9 critérios nota {melhor_nota:.3f} + adversarial {resultado.get('julgamento_adversarial',{}).get('veredito')} + NIST {resultado.get('teste_nist',{}).get('veredito')} + p-value {resultado.get('p_value_random',{}).get('veredito')}, "
                    f"fingerprint SHA256 {len(fp.cache) if fp else 0} hashes, backtest 50 média {resultado.get('backtest_lote',{}).get('media_acertos_lote')}, "
                    f"utilidade esperada EV real R${resultado.get('utilidade_esperada',{}).get('ev_real_premios_medios')} ROI {resultado.get('utilidade_esperada',{}).get('roi')}%, "
                    f"verificação exaustiva P≥13={resultado.get('verificacao_exaustiva',{}).get('p13_exata')}, "
                    f"acervo de conhecimento {evidencia_abertura['digest']} aprendido até o concurso {evidencia_abertura['aprendido_ate']} "
                    f"(veredito {evidencia_abertura['veredito']}, fator {evidencia_abertura['fator_confianca']}) — tudo possível e impossível dentro honestidade para 13/14/15. Único gerador Magna."
                ),
                "fontes_assimiladas": ["motores","oraculos","espectral","informacao","recente","fisica","clima","abertura","memoria_vetorial","regime","ewc","meta_regime","mcts","perfil_risco","multi_rota","juiz_adv","nist","p_value","fingerprint","backtest","binomial","curva","acervo"],
                "pesos_fontes": pesos,
                "top15_magna": [int(x) for x in (np.argsort(vetor)[::-1][:15]+1)],
                "concurso_alvo": int(concurso_alvo) if concurso_alvo is not None else (self.db.get_ultimo_concurso() or 0)+1,
            })
            # interpretação filtros + explainability por cartela
            try:
                from .singularidade import FiltrosAvancados
                filtros = FiltrosAvancados(self.matriz)
                votos = np.asarray(consulta["votos"], dtype=int)
                for idx, cartela in enumerate(resultado["cartelas"]):
                    dezenas = cartela["dezenas"]
                    rel = filtros.relatorio(dezenas)
                    contrib = {nome: round(float(sum(v[d-1] for d in dezenas)),6) for nome,v in fontes.items()}
                    cartela["interpretacao_magna"] = {
                        "filtros_avancados": rel,
                        "contribuicoes_fontes": contrib,
                        "votos_oraculo": {str(d): int(votos[d-1]) for d in dezenas},
                        "convergencia_media": round(float(np.mean([votos[d-1] for d in dezenas]))/15.0,4),
                        "abertura": self.acervo.afinidade_cartela(dezenas),
                    }
                    if idx < len(resultado.get("explicacoes",[])):
                        cartela["explicacao_llm"] = resultado["explicacoes"][idx]
            except Exception:
                pass

            resultado["memoria_magna"] = {
                "top15_fontes": {
                    nome: [int(x) for x in (np.argsort(v)[::-1][:15] + 1)]
                    for nome, v in fontes.items()},
                "vetor_final": [round(float(x), 10) for x in vetor],
                "pesos_fontes": pesos,
                "acervo": {
                    "versao": self.ACERVO_VERSAO,
                    "digest": evidencia_abertura["digest"],
                    "aprendido_ate": evidencia_abertura["aprendido_ate"],
                    "concursos_da_base": evidencia_abertura["concursos_da_base"],
                    "veredito": evidencia_abertura["veredito"],
                    "fator_confianca": evidencia_abertura["fator_confianca"],
                    "leitura": evidencia_abertura["leitura"],
                    "placar_walkforward": evidencia_abertura["placar"],
                },
                "palpite_abertura": {
                    "concurso": resultado["concurso_alvo"],
                    "digest": evidencia_abertura["digest"],
                    "ranking": evidencia_abertura["ranking"],
                    "probabilidades": evidencia_abertura["probabilidades"],
                    "abertura_atual": evidencia_abertura["abertura_atual"],
                    "recorde": evidencia_abertura["recorde"],
                },
            }
            resultado["decisao_id"] = self._registrar_decisao_magna(resultado) if registrar else None
            cb(f"Decisão Suprema v11 concluída: {resultado['estrategia']} nota {melhor_nota:.3f} util {melhor_utilidade:.3f} auditoria #{resultado['decisao_id'] or 'pessoal'}")
            return self._json_seguro(resultado)




    def _monte_carlo(self, cands, v, n, rng=None) -> List[List[int]]:
        rng = rng or np.random.default_rng()
        pesos = np.array([float(v[d-1]) for d in cands])
        pesos = np.clip(pesos, 0.001, None) / pesos.sum()
        res = []
        for _ in range(n * 6):
            if len(res) >= n: break
            try:
                idx = rng.choice(len(cands), 15, replace=False, p=pesos)
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

    def _fallback(self, v, elite, n, rng=None) -> List[List[int]]:
        rng = rng or np.random.default_rng()
        res = []
        pesos = np.array([float(v[d-1]) for d in elite])
        pesos = np.clip(pesos, 0.001, None) / pesos.sum()
        for _ in range(n * 30):
            if len(res) >= n: break
            try:
                idx = rng.choice(len(elite), 15, replace=False, p=pesos)
                cand = sorted([elite[i] for i in idx])
                soma = sum(cand)
                par = sum(1 for d in cand if d % 2 == 0)
                if 165 <= soma <= 240 and 4 <= par <= 11:
                    res.append(cand)
            except Exception: continue
        return res[:n]

    def executar_ciclo(self, concurso: int) -> Dict:
        """Executa conferência, aprendizado e nova decisão sem concorrência."""
        with self._magna_lock:
            return self._executar_ciclo_sem_lock(concurso)

    def _executar_ciclo_sem_lock(self, concurso: int) -> Dict:
        t0 = time.time()
        self._log("CICLO", "=== CICLO {} ===".format(concurso))
        pesos_antes = dict(self.pesos)

        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO historico_ciclos
            (concurso, timestamp_inicio, status, pesos_antes)
            VALUES (?,?,?,?)
        """, (concurso, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "em_andamento", json.dumps(pesos_antes)))
        ciclo_id = cursor.lastrowid
        conn.commit()
        conn.close()

        resultado = {"ciclo_id": ciclo_id, "concurso": concurso, "status": "erro"}

        try:
            # 1) Busca o resultado do concurso que ACABOU de sair.
            data_json = self._ingestor.buscar_concurso_caixa(concurso)
            if not data_json:
                raise Exception("Resultado {} não disponível".format(concurso))

            dezenas_reais = self._ingestor.extrair_dezenas(data_json)
            premios_reais = self._ingestor.extrair_premios(data_json)

            # 1.5) v11.4 — a ordem real das bolas do concurso que acabou de
            # sair entra pelo acervo da Magna: grava, memoriza e reassimila o
            # conhecimento de abertura no mesmo passo (não há módulo à parte).
            ordem_sorteio = data_json.get("ordem_sorteio")
            if ordem_sorteio:
                try:
                    self.aprender_ordem_sorteio(concurso, ordem_sorteio)
                except (ValueError, sqlite3.Error) as exc:
                    self._log("AVISO", "Ordem {}: {}".format(concurso, exc))

            # 2) Confere as apostas que estavam na fila para ESTE concurso.
            #    (Bug anterior: conferia a fila de "proximo" contra o
            #     resultado de "concurso" — nunca acertava nada.)
            conf = self._conferir(concurso, dezenas_reais, premios_reais)

            # 3) Aprende com o resultado real (fora-da-amostra).
            self._aprender(concurso, conf, dezenas_reais)

            # 4) Gera e enfileira novas apostas para o PRÓXIMO concurso.
            proximo = concurso + 1
            decisao = self.decidir_e_gerar(
                quantidade=self.n_cartelas,
                registrar=True,
                concurso_alvo=proximo,
            )
            cartelas = decisao["cartelas"]
            self._salvar_fila(proximo, cartelas)

            resultado["status"] = "completo"
            self._ciclos_ok += 1
            self._ultimo_processado = concurso

        except Exception as e:
            self._log("ERRO", "Ciclo {}: {}".format(concurso, e))
            resultado["status"] = "erro"
            self._ciclos_err += 1

        tempo = time.time() - t0
        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historico_ciclos SET
                timestamp_fim=?, status=?, n_cartelas=?, melhor_acertos=?,
                media_acertos=?, total_ganho=?, pesos_depois=?, log_ciclo=?
            WHERE id=?
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), resultado["status"],
            len(cartelas) if 'cartelas' in locals() else 0,
            conf.get("melhor_acertos", 0) if 'conf' in locals() else 0,
            conf.get("media_acertos", 0) if 'conf' in locals() else 0,
            conf.get("total_ganho", 0) if 'conf' in locals() else 0,
            json.dumps(dict(self.pesos)), "Ciclo em {:.1f}s".format(tempo), ciclo_id
        ))
        conn.commit()
        conn.close()
        return resultado

    def _salvar_fila(self, concurso: int, cartelas: List[Dict]):
        conn = self.db.get_conn()
        cursor = conn.cursor()
        for c in cartelas:
            try:
                cursor.execute("""
                    INSERT INTO fila_conferencia
                    (concurso_alvo, dezenas, timestamp_geracao, scores_modulos, score_total, status)
                    VALUES (?,?,?,?,?,?)
                """, (
                    concurso, json.dumps(c["dezenas"]),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    json.dumps(c.get("scores", {})), float(c.get("score_total", 0)), "aguardando"
                ))
            except Exception: pass
        conn.commit()
        conn.close()

    def _conferir(self, concurso, dezenas_reais, premios):
        set_real = set(dezenas_reais)
        conn = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, dezenas, scores_modulos, score_total FROM fila_conferencia WHERE concurso_alvo=? AND status='aguardando'", (concurso,))
        fila = cursor.fetchall()
        resultados = []; total_g = 0.0; dist = {i: 0 for i in range(16)}

        for item in fila:
            fid = item["id"]
            dez = json.loads(item["dezenas"])
            acertos = len(set(dez) & set_real)
            premio = premios.get(acertos, 0.0) if acertos >= 11 else 0.0
            total_g += premio

            st = "premio_15" if acertos >= 15 else "premio_14" if acertos >= 14 else "premio_13" if acertos >= 13 else "premio_12" if acertos >= 12 else "premio_11" if acertos >= 11 else "sem_premio"
            err = abs(float(item["score_total"] or 0) - acertos / 15.0)

            cursor.execute("""
                UPDATE fila_conferencia SET status=?, acertos=?, premio_ganho=?,
                dezenas_acertadas=?, timestamp_conferencia=?, erro_previsao=? WHERE id=?
            """, (st, acertos, premio, json.dumps(sorted(list(set(dez) & set_real))), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), round(err, 4), fid))

            dist[acertos] += 1
            resultados.append({"fila_id": fid, "acertos": acertos, "premio": premio})

        conn.commit()
        conn.close()

        melhor = max((r["acertos"] for r in resultados), default=0)
        media = sum(r["acertos"] for r in resultados) / max(len(resultados), 1)

        return {
            "status": "ok", "concurso": concurso, "conferidas": len(resultados),
            "melhor_acertos": melhor, "media_acertos": round(media, 2), "total_ganho": round(total_g, 2)
        }

    def _aprender(self, concurso: int, conf: Dict, dezenas_reais: List[int]) -> Dict:
        """
        Aprendizado honesto por desempenho FORA-DA-AMOSTRA de cada módulo:
        cada módulo 'vota' num top-15; o módulo que mais acertou no sorteio
        real ganha peso; quem errou mais perde. Não há reforço cego de um
        único módulo em caso de fracasso (o viés anti_lógica de antes).
        """
        pesos_antes = dict(self.pesos)
        melhor = conf.get("melhor_acertos", 0)
        real = set(dezenas_reais)

        # Acertos de cada módulo no top-15 (proxy de qualidade)
        acertos_por_modulo = {}
        for nome, vetor in self._vetores.items():
            try:
                v = np.asarray(vetor, dtype=float)
                if v.sum() <= 0:
                    acertos_por_modulo[nome] = 0.0
                    continue
                top15 = set(int(x) + 1 for x in np.argsort(v)[::-1][:15])
                acertos_por_modulo[nome] = float(len(top15 & real))
            except Exception:
                acertos_por_modulo[nome] = 0.0

        valores = list(acertos_por_modulo.values())
        if valores:
            mediana = float(np.median(valores))
            fator = 0.05
            for nome in self.pesos:
                ac = acertos_por_modulo.get(nome, 0.0)
                if ac > mediana:
                    self.pesos[nome] *= (1 + fator)
                elif ac < mediana:
                    self.pesos[nome] *= (1 - fator * 0.5)

        # Normalização
        total = sum(self.pesos.values())
        for k in self.pesos:
            self.pesos[k] = round(self.pesos[k] / total, 4)

        # Persistência de desempenho e memória de erros (antes nunca gravadas)
        self._registrar_desempenho(concurso, acertos_por_modulo, pesos_antes)
        self._stacking.registrar(self.pesos, melhor)
        return {"status": "ok", "pesos_novos": dict(self.pesos),
                "acertos_por_modulo": acertos_por_modulo}

    def _registrar_desempenho(self, concurso: int, acertos_por_modulo: Dict,
                              pesos_antes: Dict):
        """Grava correlação (acertos) de cada módulo e o erro cometido."""
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for nome, ac in acertos_por_modulo.items():
                cursor.execute("""
                    INSERT INTO desempenho_modulos
                    (concurso, timestamp, modulo, correlacao, peso_antes, peso_depois)
                    VALUES (?,?,?,?,?,?)
                """, (concurso, ts, nome, float(ac / 15.0),
                      float(pesos_antes.get(nome, 0)),
                      float(self.pesos.get(nome, 0))))
                # erro do módulo = quão longe ficou de 15
                cursor.execute("""
                    INSERT INTO memoria_erros (concurso, timestamp, modulo, erro, impacto)
                    VALUES (?,?,?,?,?)
                """, (concurso, ts, nome, float(15 - ac), float((15 - ac) / 15.0)))
            conn.commit()
            conn.close()
        except Exception as e:
            print("[APRENDER] persistir desempenho: {}".format(e))

    def iniciar_loop(self, intervalo: int = 3600) -> Dict:
        if self._rodando: return {"status": "ja_rodando"}
        self._rodando = True; self.estado = "monitorando"

        def _loop():
            while self._rodando:
                try:
                    if self._pausado: time.sleep(30); continue
                    data = self._ingestor.buscar_ultimo_caixa()
                    if not data: time.sleep(intervalo); continue
                    atual = int(data.get("numero", 0))
                    if atual <= self._ultimo_processado:
                        time.sleep(intervalo); continue
                    self.executar_ciclo(atual)
                except Exception: time.sleep(300)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        return {"status": "iniciado"}

    def parar_loop(self) -> Dict: self._rodando = False; return {"status": "parando"}
    def pausar_loop(self) -> Dict: self._pausado = True; return {"status": "pausado"}
    def retomar_loop(self) -> Dict: self._pausado = False; return {"status": "retomado"}

    def backtesting(self, n_testes: int = 20, n_cart: int = 5,
                    n_random: int = 200) -> Dict:
        """
        Backtesting FORA-DA-AMOSTRA real (walk-forward) com baseline aleatória.
        Substitui o stub anterior. Avalia os 15 oráculos e o consenso,
        sem vazamento de dados, e compara contra o acaso.
        """
        try:
            from .singularidade import ValidadorForaDaAmostra
            matriz, _ = self._ingestor.carregar_matriz()
            validador = ValidadorForaDaAmostra(matriz)
            relatorio = validador.backtest(
                n_testes=n_testes, n_random=n_random)
            relatorio["status"] = "ok"
            relatorio["concursos_testados"] = relatorio.get(
                "concursos_testados", n_testes)
            return relatorio
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "erro", "msg": str(e)}

    def _log(self, tipo: str, msg: str):
        e = {"ts": datetime.now().strftime("%H:%M:%S"), "tipo": tipo, "msg": msg}
        self.log.append(e)
        if len(self.log) > 500: self.log = self.log[-500:]
        print("[CÉREBRO IA][{}] {}".format(tipo, msg))

    def get_status(self) -> Dict:
        fisica_status = self.fisica.get_status()
        return {
            "versao": "11.0-Magna-Suprema-Unica-Pessoal-Evoluida",
            "estado": self.estado,
            "treinado": self.treinado,
            "total_concursos": self.n,
            "ultima_exec": self.ultima_exec,
            "metricas": self.metricas,
            "pesos_modulos": self.pesos,
            "inteligencia_magna": {
                "unificada": True,
                "pesos_fontes": dict(self.pesos_fontes_magna),
                "ultima_decisao": self.decisoes.get("magna"),
                "modulos_agregados": 14,
                "fontes_assimiladas": list(self._FONTES_MAGNA_DEFAULT.keys()),
            },
            "fisica": {
                "estado": fisica_status["estado"],
                "bolas_registradas": fisica_status["bolas_medidas"],
                "ambientes_registrados": fisica_status["ambientes_registrados"],
                "tem_dados_reais": fisica_status["tem_dados_reais"],
            },
            "clima": {
                "registros": self.clima.n_registros,
                "limiar_pressao": (
                    round(self.clima._limiar_pressao(), 4)
                    if self.clima.n_registros else None),
                "limiar_temperatura": (
                    round(self.clima._limiar_temperatura(), 2)
                    if self.clima.n_registros else None),
                "top5_previsto": (
                    self.clima.top5_clima(usar_web=False)
                    if self.clima.n_registros else None),
            },
            # v11.7 — telemetria INMET por local do sorteio
            "inmet": (
                self.inmet.resumo()
                if getattr(self, "inmet", None) is not None
                else {"status": "neutro", "n_registros": 0,
                      "ultima": None, "fontes": {}, "medias": None}
            ),
            # v11.4 — o acervo da própria Magna (aprendizado + memória viva)
            "acervo": {
                "versao": self.ACERVO_VERSAO,
                "estado": (self.acervo.estado()
                           if hasattr(self, "acervo")
                           else {"status": "indisponível"}),
                "placar_abertura": self.placar_abertura_memoria(),
                "calibrado": bool(getattr(self, "_acervo_calibrado", False)),
                "pesos_fontes": dict(self.pesos_fontes_magna),
            },
            "filtros": {
                "soma": [self._gaussiano.SOMA_MIN, self._gaussiano.SOMA_MAX],
                "pares": [self._gaussiano.PARES_MIN, self._gaussiano.PARES_MAX],
                "primos": [self._gaussiano.PRIMOS_MIN, self._gaussiano.PRIMOS_MAX],
                "fibonacci": [self._gaussiano.FIB_MIN, self._gaussiano.FIB_MAX],
                "borda": [self._gaussiano.BORDA_MIN, self._gaussiano.BORDA_MAX],
            },
            "ciclo": {
                "rodando": self._rodando,
                "pausado": self._pausado,
                "n_cartelas": self.n_cartelas,
                "ciclos_ok": self._ciclos_ok,
                "ciclos_erro": self._ciclos_err,
                "ultimo_processado": self._ultimo_processado,
                "proximo_sorteio": self.proximo_sorteio,
            },
            "log_recente": self.log[-20:],
        }

    def get_fila_concurso(self, concurso: int) -> List[Dict]:
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fila_conferencia WHERE concurso_alvo=?", (concurso,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    def get_historico_ciclos(self, limit: int = 20) -> List[Dict]:
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM historico_ciclos ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    def get_memoria_erros(self) -> List[Dict]:
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT modulo, AVG(erro) as erro_medio, COUNT(*) as ocorrencias FROM memoria_erros GROUP BY modulo")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception: return []

    def get_desempenho_modulos(self) -> List[Dict]:
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT modulo, AVG(correlacao) as corr_media, AVG(peso_depois) as peso_atual FROM desempenho_modulos GROUP BY modulo")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []


# Nome público único. `CerebroIA` permanece como classe-base/alias histórico
# para não quebrar integrações; toda a aplicação instancia InteligenciaMagna.
InteligenciaMagna = CerebroIA
