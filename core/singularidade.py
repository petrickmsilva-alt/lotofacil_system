"""
====================================================================
NÚCLEO DE SINGULARIDADE — MOTORES NÃO-CONVENCIONAIS v1.0
====================================================================
Complemento do Cérebro IA com métodos de alta complexidade
matemática/estatística/física que NÃO fazem parte do repertório
comum de análise de loterias (que se resume a "frequência + soma +
paridade"). Aqui entram:

  1. Teoria da Informação  — entropia de permutação, entropia de
     transferência, informação mútua entre dezenas.
  2. Análise Espectral     — FFT, entropia espectral e expoente de
     Hurst (R/S) para detectar dependência de longo alcance.
  3. Dependência Multivariada — copula de co-ocorrência, dependência
     de cauda e distância de Mahalanobis sobre o vetor de features.
  4. Filtros Avançados     — plausibilidade de gaps, entropia
     condicional e densidade de co-ocorrência.
  5. Cobertura Combinatória — limites de Schönheim para designs
     C(25,15,13/14/15) com contagem HONESTA de cartelas necessárias.
  6. Gestão de Banca       — valor esperado exato, critério de Kelly
     e probabilidade de ruína.
  7. Validador Fora-da-Amostra — walk-forward com baseline aleatória
     e significância estatística (permutação).

FILOSOFIA: este módulo é deliberadamente cético. Ele mede cada
hipótese contra o ACASO. Qualquer "padrão" que não supere uma
seleção aleatória fora-da-amostra é descartado como ruído — isso é o
que diferencia ciência de superstição.
====================================================================
"""

import numpy as np
from math import comb, log, factorial
from typing import List, Dict, Tuple
from scipy import stats
from scipy.fft import rfft

from config import (
    TOTAL_DEZENAS, DEZENAS_POR_JOGO, VALOR_APOSTA,
    PRIMOS, FIBONACCI, BORDA,
    PREMIOS_FIXOS, PREMIOS_RATEADOS_MEDIA,
)

N = TOTAL_DEZENAS           # 25
K = DEZENAS_POR_JOGO        # 15
UNIVERSO = comb(N, K)       # 3.268.760


# =====================================================================
# 0. PROBABILIDADES EXATAS (hipergeométrica) — a verdade irredutível
# =====================================================================
def probabilidade_acertos(k: int) -> float:
    """P(acertar exatamente k dezenas) numa cartela de 15 vs sorteio de 15 em 25."""
    if k < 0 or k > K:
        return 0.0
    return comb(K, k) * comb(N - K, K - k) / UNIVERSO


def distribuicao_exata() -> Dict[int, float]:
    """Distribuição completa P(0..15)."""
    return {k: probabilidade_acertos(k) for k in range(K + 1)}


def probabilidade_13_mais() -> float:
    """P(13, 14 ou 15 pontos)."""
    return sum(probabilidade_acertos(k) for k in (13, 14, 15))


# =====================================================================
# 1. TEORIA DA INFORMAÇÃO
# =====================================================================
class TeoriaDaInformacao:
    """Entropia, entropia de permutação, transferência de entropia e MI."""

    def __init__(self, matriz: np.ndarray):
        self.matriz = np.asarray(matriz, dtype=float)
        self.n = self.matriz.shape[0]

    def entropia_shannon_serie(self, serie: np.ndarray) -> float:
        p = float(np.mean(serie))
        if p <= 0 or p >= 1:
            return 0.0
        return -(p * log(p, 2) + (1 - p) * log(1 - p, 2))

    def entropia_permutacao(self, serie: np.ndarray, ordem: int = 3) -> float:
        """Entropia de permutação (Bandt & Pompe) — mede ordem temporal."""
        s = np.asarray(serie, dtype=float)
        if len(s) < ordem:
            return 0.0
        janela = s[-400:] if len(s) > 400 else s
        if len(janela) < ordem:
            return 0.0
        contagem: Dict[tuple, int] = {}
        for i in range(len(janela) - ordem + 1):
            seg = janela[i:i + ordem]
            # ranking relativo (trata empates)
            perm = tuple(np.argsort(np.argsort(seg)))
            contagem[perm] = contagem.get(perm, 0) + 1
        total = sum(contagem.values())
        ent = 0.0
        for c in contagem.values():
            p = c / total
            ent -= p * log(p, 2)
        return ent / log(factorial(ordem), 2)  # normalizado 0..1

    def transferencia_entropia(self, origem: np.ndarray, destino: np.ndarray,
                               lag: int = 1) -> float:
        """
        Transferência de entropia TE(origem -> destino) para séries binárias.
        Quantifica quanto o passado de `origem` reduz a incerteza de `destino`
        além do que o próprio passado de `destino` já explica.
        """
        o = np.asarray(origem, dtype=int)
        d = np.asarray(destino, dtype=int)
        n = len(d)
        if n < 30:
            return 0.0
        # conta transições conjuntas (lag=1, binarizado)
        def _h2(a, b):
            # entropia conjunta de (a_t-1, b_t)
            cnt = {}
            for t in range(1, n):
                key = (a[t - 1], b[t])
                cnt[key] = cnt.get(key, 0) + 1
            tot = sum(cnt.values())
            return -sum((c / tot) * log(c / tot, 2) for c in cnt.values())

        def _h3(a, b, c):
            cnt = {}
            for t in range(1, n):
                key = (a[t - 1], b[t - 1], c[t])
                cnt[key] = cnt.get(key, 0) + 1
            tot = sum(cnt.values())
            return -sum((c / tot) * log(c / tot, 2) for c in cnt.values())

        # TE = H(destino_t | destino_t-1) - H(destino_t | destino_t-1, origem_t-1)
        h_d_own = _h2(d, d)      # H(d_t | d_t-1) ≈ H(d_t-1, d_t) - H(d_t-1)
        h_d_all = _h3(o, d, d)   # H(d_t | d_t-1, o_t-1)
        # aproximação entrópica (sem marginal completa — suficiente p/ ranking)
        te = h_d_own - h_d_all
        return max(0.0, te)

    def matriz_informacao_mutua(self) -> np.ndarray:
        """Informação mútua pontual entre pares de dezenas (normalizada)."""
        M = self.matriz
        mi = np.zeros((N, N))
        for i in range(N):
            for j in range(N):
                if i == j:
                    continue
                a = M[:, i].astype(int)
                b = M[:, j].astype(int)
                # tabela de contingência 2x2
                p11 = float(np.mean(a & b))
                p10 = float(np.mean(a & (1 - b)))
                p01 = float(np.mean((1 - a) & b))
                p00 = float(np.mean((1 - a) & (1 - b)))
                pa = p11 + p10
                pb = p11 + p01
                def _term(p, q):
                    if p <= 0 or q <= 0:
                        return 0.0
                    return p * log(p / q, 2)
                mi[i, j] = (_term(p11, pa * pb) + _term(p10, pa * (1 - pb))
                            + _term(p01, (1 - pa) * pb) + _term(p00, (1 - pa) * (1 - pb)))
        return mi


# =====================================================================
# 2. ANÁLISE ESPECTRAL E DE LONGO ALCANCE
# =====================================================================
class EspectroTemporal:
    """FFT, entropia espectral e expoente de Hurst (R/S)."""

    def __init__(self, matriz: np.ndarray):
        self.matriz = np.asarray(matriz, dtype=float)

    def entropia_espectral(self, serie: np.ndarray) -> float:
        s = np.asarray(serie, dtype=float)
        if len(s) < 8:
            return 0.0
        f = np.abs(rfft(s - s.mean())) ** 2
        f = f / (f.sum() + 1e-12)
        ent = -np.sum(f[f > 0] * np.log(f[f > 0]))
        return float(ent / log(len(f), 2))

    def expoente_hurst(self, serie: np.ndarray) -> float:
        """
        Expoente de Hurst via análise R/S.
        H ≈ 0.5 => série sem memória (o esperado num sorteio justo).
        H > 0.5 => tendência persistente; H < 0.5 => anti-persistente.
        """
        s = np.asarray(serie, dtype=float)
        n = len(s)
        if n < 40:
            return 0.5
        escalas = [10, 20, 40, 80, 160, 320, 640]
        escalas = [e for e in escalas if e * 4 <= n]
        if not escalas:
            return 0.5
        rs_vals, tamanhos = [], []
        for esc in escalas:
            blocos = n // esc
            rs = []
            for b in range(blocos):
                bloco = s[b * esc:(b + 1) * esc]
                media = bloco.mean()
                desvios = np.cumsum(bloco - media)
                R = desvios.max() - desvios.min()
                S = bloco.std()
                if S > 0:
                    rs.append(R / S)
            if rs:
                rs_vals.append(np.mean(rs))
                tamanhos.append(esc)
        if len(rs_vals) < 3:
            return 0.5
        log_esc = np.log(tamanhos)
        log_rs = np.log(rs_vals)
        slope, *_ = np.polyfit(log_esc, log_rs, 1)
        return float(slope)

    def score_espectral_por_dezena(self) -> np.ndarray:
        """Combina entropia espectral + distância de Hurst de 0.5 (menos memória)."""
        scores = np.zeros(N)
        for d in range(N):
            s = self.matriz[:, d]
            he = self.entropia_espectral(s)
            hu = self.expoente_hurst(s)
            # favorece séries com ALTA entropia (sem periodicidade espúria)
            # e Hurst próximo de 0.5 (sem memória — comportamento de sorteio justo)
            scores[d] = he * (1.0 - abs(hu - 0.5))
        s = scores.sum()
        return scores / s if s > 0 else np.ones(N) / N


# =====================================================================
# 3. DEPENDÊNCIA MULTIVARIADA
# =====================================================================
class DependenciaMultivariada:
    """Co-ocorrência, dependência de cauda e plausibilidade de Mahalanobis."""

    def __init__(self, matriz: np.ndarray):
        self.matriz = np.asarray(matriz, dtype=float)
        self._calibrar()

    def _features_historico(self) -> np.ndarray:
        M = self.matriz
        linhas = []
        for i in range(M.shape[0]):
            dez = np.where(M[i] == 1)[0] + 1
            if len(dez) != K:
                continue
            soma = dez.sum()
            pares = int((dez % 2 == 0).sum())
            primos = len(set(dez.tolist()) & PRIMOS)
            fib = len(set(dez.tolist()) & FIBONACCI)
            borda = len(set(dez.tolist()) & BORDA)
            gaps = np.diff(np.sort(dez))
            gaps_mean = gaps.mean()
            spread = int(dez.max() - dez.min())
            consec = self._max_consecutivos(dez)
            linhas.append([soma, pares, primos, fib, borda, gaps_mean, spread, consec])
        return np.array(linhas)

    @staticmethod
    def _max_consecutivos(dez) -> int:
        sd = np.sort(dez)
        mc = cc = 1
        for i in range(1, len(sd)):
            if sd[i] == sd[i - 1] + 1:
                cc += 1
                mc = max(mc, cc)
            else:
                cc = 1
        return mc

    def _calibrar(self):
        self.features = self._features_historico()
        self.media = self.features.mean(axis=0)
        cov = np.cov(self.features.T)
        cov = cov + np.eye(cov.shape[0]) * 1e-6
        try:
            self.inv_cov = np.linalg.inv(cov)
            self.cov_ok = True
        except np.linalg.LinAlgError:
            self.inv_cov = np.eye(cov.shape[0])
            self.cov_ok = False

    def mahalanobis(self, dezenas: List[int]) -> Tuple[float, float]:
        """Distância de Mahalanobis do vetor de features + p-valor (chi²)."""
        dez = np.array(sorted(dezenas), dtype=int)
        soma = dez.sum()
        pares = int((dez % 2 == 0).sum())
        primos = len(set(dezenas) & PRIMOS)
        fib = len(set(dezenas) & FIBONACCI)
        borda = len(set(dezenas) & BORDA)
        gaps = np.diff(dez)
        gaps_mean = gaps.mean()
        spread = int(dez.max() - dez.min())
        consec = self._max_consecutivos(dez)
        x = np.array([soma, pares, primos, fib, borda, gaps_mean, spread, consec])
        delta = x - self.media
        md2 = float(delta @ self.inv_cov @ delta)
        pval = float(1 - stats.chi2.cdf(md2, df=len(x)))
        return md2, pval

    def dependencia_cauda(self, a: int, b: int) -> float:
        """Co-ocorrência conjunta em relação ao esperado (independência)."""
        Ma = self.matriz[:, a] > 0.5
        Mb = self.matriz[:, b] > 0.5
        pa = Ma.mean()
        pb = Mb.mean()
        p_obs = (Ma & Mb).mean()
        p_esp = pa * pb
        if p_esp <= 0:
            return 0.0
        return float((p_obs - p_esp) / p_esp)  # excesso relativo de co-ocorrência


# =====================================================================
# 4. FILTROS AVANÇADOS (não-triviais)
# =====================================================================
class FiltrosAvancados:
    """Filtros que vão além de soma/paridade/primos — estrutura de gaps,
    entropia condicional e densidade de co-ocorrência."""

    def __init__(self, matriz: np.ndarray):
        self.matriz = np.asarray(matriz, dtype=float)
        self.n = self.matriz.shape[0]
        self.dep = DependenciaMultivariada(self.matriz)
        self._gap_stats()

    def _gap_stats(self):
        """Calibra distribuição empírica dos gaps entre dezenas sorteadas."""
        gaps_total = []
        for i in range(self.n):
            dez = np.where(self.matriz[i] == 1)[0]
            if len(dez) == K:
                gaps_total.extend(np.diff(dez).tolist())
        gaps_total = np.array(gaps_total)
        self.gap_mean = gaps_total.mean()
        self.gap_std = gaps_total.std()

    def filtro_gaps(self, dezenas: List[int], n_sigmas: float = 2.0) -> Tuple[bool, float]:
        """Rejeita cartelas cujo gap médio é implausível (fora de n sigmas)."""
        dez = sorted(dezenas)
        gaps = np.diff(dez)
        gm = gaps.mean()
        z = (gm - self.gap_mean) / (self.gap_std + 1e-9)
        return bool(abs(z) <= n_sigmas), float(z)

    def filtro_entropia_condicional(self, dezenas: List[int],
                                    janela: int = 100) -> Tuple[bool, float]:
        """
        Entropia da cartela contra a distribuição condicional recente.
        Uma cartela deve ter entropia 'plausível' — nem colapsada (todas
        quentes) nem maximal (todas frias) em relação ao histórico recente.
        """
        recente = self.matriz[-janela:]
        freq = recente.sum(axis=0) / max(len(recente), 1)
        freq = np.clip(freq, 1e-6, 1 - 1e-6)
        idx = [d - 1 for d in dezenas]
        ent = -np.mean(np.log2(freq[idx]) * freq[idx] +
                       np.log2(1 - freq[idx]) * (1 - freq[idx]))
        # faixa plausível de entropia média por dezena
        ok = 0.4 <= ent <= 1.0
        return bool(ok), float(ent)

    def filtro_coocorrencia(self, dezenas: List[int],
                            max_excesso: float = 0.25) -> Tuple[bool, float]:
        """Rejeita cartelas com excesso de pares 'super-coincidentes' (não-independência)."""
        excessos = []
        for i in range(len(dezenas)):
            for j in range(i + 1, len(dezenas)):
                excessos.append(self.dep.dependencia_cauda(dezenas[i] - 1, dezenas[j] - 1))
        ex_medio = float(np.mean(np.abs(excessos)))
        return bool(ex_medio <= max_excesso), ex_medio

    def filtro_mahalanobis(self, dezenas: List[int], p_min: float = 0.01) -> Tuple[bool, float]:
        """Rejeita cartelas cujo vetor de features é outlier multivariado (p < p_min)."""
        _, pval = self.dep.mahalanobis(dezenas)
        return bool(pval >= p_min), float(pval)

    def score_avancado(self, dezenas: List[int]) -> float:
        """Score 0..1 combinando os filtros avançados (quanto maior, mais 'plausível')."""
        ok_gap, z = self.filtro_gaps(dezenas)
        ok_ent, ent = self.filtro_entropia_condicional(dezenas)
        ok_coo, coo = self.filtro_coocorrencia(dezenas)
        ok_mah, pval = self.filtro_mahalanobis(dezenas)
        s = 0.0
        s += 0.25 * (1.0 - min(abs(z) / 3.0, 1.0))
        s += 0.25 * (1.0 if ok_ent else 0.4)
        s += 0.25 * (1.0 - min(coo / 0.5, 1.0))
        s += 0.25 * (1.0 if ok_mah else 0.4)
        return float(s)

    def relatorio(self, dezenas: List[int]) -> Dict:
        return {
            "gaps": {"ok": self.filtro_gaps(dezenas)[0], "z": round(self.filtro_gaps(dezenas)[1], 3)},
            "entropia_condicional": {"ok": self.filtro_entropia_condicional(dezenas)[0]},
            "coocorrencia": {"ok": self.filtro_coocorrencia(dezenas)[0]},
            "mahalanobis": {"ok": self.filtro_mahalanobis(dezenas)[0]},
            "score_avancado": round(self.score_avancado(dezenas), 4),
        }


# =====================================================================
# 5. COBERTURA COMBINATÓRIA (designs C(25,15,t))
# =====================================================================
class CoberturaSteiner:
    """
    Teoria de designs de cobertura (covering designs) — a matemática
    REAL por trás de 'garantir t pontos'. Um design C(v,k,t) é um
    conjunto de blocos de k elementos tal que todo subconjunto de t
    elementos está contido em ao menos um bloco.
    """

    def __init__(self, v: int = N, k: int = K):
        self.v = v
        self.k = k

    def limite_schonheim(self, t: int) -> int:
        """
        Limite inferior de Schönheim para o número de blocos de um
        C(v,k,t). Recursivo e EXATO como cota mínima.
        """
        v, k = self.v, self.k
        if t == 1:
            # cobrir todo elemento: ceil(v/k)
            return (v + k - 1) // k
        # Schönheim: C(v,k,t) >= ceil( (v/k) * C(v-1, k-1, t-1) )
        return ((v * self._schonheim_rec(v - 1, k - 1, t - 1)) + k - 1) // k

    def _schonheim_rec(self, v, k, t):
        if t == 1:
            return (v + k - 1) // k
        if v < k:
            return 0
        return (v * self._schonheim_rec(v - 1, k - 1, t - 1) + k - 1) // k

    def cota_total(self) -> Dict[int, Dict]:
        """Relatório de cotas para garantir 13, 14 e 15 pontos."""
        resultado = {}
        for t in (13, 14, 15):
            lb = self.limite_schonheim(t)
            # cobertura total ingênua = C(25,t)/C(15,t)
            total_t = comb(self.v, t)
            por_bloco = comb(self.k, t)
            ing = total_t / por_bloco
            resultado[t] = {
                "limite_inferior_schonheim": lb,
                "estimativa_ingenuo": round(ing),
                # O custo deve usar a mesma cota mostrada como quantidade.
                # Antes a UI exibia 58.887 cartelas, mas multiplicava uma razão
                # ingênua menor (49.527), produzindo um custo incoerente.
                "custo_estimado_R$": round(lb * VALOR_APOSTA, 2),
            }
        return resultado

    def cobertura_minima_gulosa(self, universo: List[int], t: int,
                                max_blocos: int = 200) -> List[List[int]]:
        """
        Greedy set-cover para o sub-universo fornecido (limitado por max_blocos).
        Apenas para demonstração — cobertura EXATA do espaço inteiro é inviável.
        """
        universos = sorted(universo)
        if len(universos) < K:
            return [universos[:K]]
        import itertools
        alvos = set()
        for sub in itertools.combinations(universos, t):
            alvos.add(sub)
        blocos = []
        cobertos = set()
        while len(cobertos) < len(alvos) and len(blocos) < max_blocos:
            melhor, melhor_cobre = None, set()
            for bloco in itertools.combinations(universos, K):
                bs = set(bloco)
                cobre = {a for a in alvos if a not in cobertos and set(a) <= bs}
                if len(cobre) > len(melhor_cobre):
                    melhor, melhor_cobre = bloco, cobre
            if melhor is None:
                break
            blocos.append(sorted(melhor))
            cobertos |= melhor_cobre
        return blocos


# =====================================================================
# 6. GESTÃO DE BANCA
# =====================================================================
class GestaoDeBanca:
    """Valor esperado exato, critério de Kelly e risco de ruína."""

    def __init__(self, premio_14: float = None, premio_15: float = None):
        self.premio_14 = premio_14 or PREMIOS_RATEADOS_MEDIA[14]
        self.premio_15 = premio_15 or PREMIOS_RATEADOS_MEDIA[15]

    def valor_esperado_cartela(self) -> float:
        """EV exato de UMA cartela (sem viés de padrão nenhum)."""
        ev = 0.0
        for k in range(11, 16):
            p = probabilidade_acertos(k)
            if k in PREMIOS_FIXOS:
                ev += p * PREMIOS_FIXOS[k]
            elif k == 14:
                ev += p * self.premio_14
            elif k == 15:
                ev += p * self.premio_15
        return ev - VALOR_APOSTA

    def fracao_kelly(self, edge: float = None, variancia: float = None) -> float:
        """
        Fração ótima de Kelly. Com EV negativo o resultado é <= 0
        (a resposta matemática correta: NÃO apostar por expectativa).
        """
        edge = self.valor_esperado_cartela() if edge is None else edge
        # variância aproximada de uma aposta (perde 3.5 ou ganha prêmio - 3.5)
        variancia = variancia or (self.premio_15 ** 2 * probabilidade_acertos(15)
                                  + self.premio_14 ** 2 * probabilidade_acertos(14)
                                  + PREMIOS_FIXOS[13] ** 2 * probabilidade_acertos(13))
        return float(edge / variancia) if variancia > 0 else 0.0

    def risco_ruina(self, banca: float, aposta: float, p_ganho: float,
                    n_apostas: int) -> float:
        """
        Probabilidade aproximada de ruína (perda total da banca)
        usando caminhada aleatória enviesada.
        """
        if aposta <= 0:
            return 0.0
        q = 1 - p_ganho
        if p_ganho <= 0:
            return 1.0
        r = q / p_ganho
        a = banca / aposta
        if r == 1:
            return 1.0 - a / n_apostas
        try:
            return float((r ** a - r ** n_apostas) / (1 - r ** n_apostas))
        except (OverflowError, ZeroDivisionError):
            return 1.0 if r > 1 else 0.0

    def relatorio(self, banca: float = 1000.0) -> Dict:
        ev = self.valor_esperado_cartela()
        kelly = self.fracao_kelly()
        p11mais = sum(probabilidade_acertos(k) for k in range(11, 16))
        return {
            "valor_esperado_por_cartela_R$": round(ev, 4),
            "retorno_esperado_pct": round(ev / VALOR_APOSTA * 100, 2),
            "fracao_kelly": round(kelly, 6),
            "conclusao_kelly": ("apostar" if kelly > 0 else "não apostar por EV"),
            "p_pelo_menos_11": round(p11mais, 4),
            "p_13_mais": round(probabilidade_13_mais(), 6),
            "cartelas_para_1_em_13_mais": int(round(1 / probabilidade_13_mais())),
        }


# =====================================================================
# 7. VALIDADOR FORA-DA-AMOSTRA (walk-forward + baseline aleatória)
# =====================================================================
class ValidadorForaDaAmostra:
    """
    O árbitro da casa. Testa cada teoria (oráculo) SEM vazamento de dados:
    treina só no passado, avalia só no futuro. Compara contra a baseline
    aleatória e reporta significância.
    """

    def __init__(self, matriz: np.ndarray):
        self.matriz = np.asarray(matriz, dtype=float)

    def _acertos_top15(self, scores: np.ndarray, real: set) -> int:
        if scores is None or np.isnan(scores).any():
            return 0
        top = set(np.argsort(scores)[::-1][:K].tolist())
        return len(top & real)

    def backtest(self, n_testes: int = 20, n_random: int = 200,
                 callbacks: dict = None) -> Dict:
        """
        Walk-forward: para cada um dos últimos n_testes sorteios,
        treina os 15 oráculos apenas com os sorteios anteriores e mede
        acertos no sorteio de teste. Compara com a distribuição aleatória.
        """
        from .oraculo_convergente import OraculoConvergente

        n = self.matriz.shape[0]
        n_testes = min(n_testes, n - 40)
        if n_testes < 1:
            return {"status": "erro", "msg": "dados insuficientes"}

        nomes = OraculoConvergente.NOMES_ORACULOS
        acumulado = {nome: [] for nome in nomes}
        acumulado["consenso"] = []
        random_hits = []

        for i in range(n - n_testes, n):
            treino = self.matriz[:i]
            real = set(np.where(self.matriz[i] == 1)[0].tolist())
            oracle = OraculoConvergente(treino)

            map_metodos = {
                "termodinamico": oracle.oraculo_termodinamico,
                "quantico": oracle.oraculo_quantico,
                "fisico": oracle.oraculo_fisico,
                "bayesiano": oracle.oraculo_bayesiano,
                "markov": oracle.oraculo_markov,
                "caotico": oracle.oraculo_caotico,
                "fractal": oracle.oraculo_fractal,
                "gravitacional": oracle.oraculo_gravitacional,
                "neural": oracle.oraculo_neural,
                "genetico": oracle.oraculo_genetico,
                "estatistico": oracle.oraculo_estatistico,
                "fourier": oracle.oraculo_fourier,
                "topologico": oracle.oraculo_topologico,
                "relativista": oracle.oraculo_relativista,
                "anti_comunidade": oracle.oraculo_anti_comunidade,
            }

            votos = np.zeros(N)
            for nome, func in map_metodos.items():
                try:
                    sc = np.asarray(func(), dtype=float)
                    if sc.sum() > 0:
                        sc = sc / sc.sum()
                    acertos = self._acertos_top15(sc, real)
                    acumulado[nome].append(acertos)
                    votos += sc
                except Exception:
                    acumulado[nome].append(0)

            # consenso = soma dos votos (top15 por votos)
            ac_cons = self._acertos_top15(votos, real)
            acumulado["consenso"].append(ac_cons)

            # baseline aleatória empírica
            rng = np.random.default_rng(i)
            for _ in range(n_random):
                pick = rng.choice(N, size=K, replace=False)
                random_hits.append(len(set(pick.tolist()) & real))

        # agrega
        report = {}
        for nome in nomes + ["consenso"]:
            arr = np.array(acumulado[nome])
            report[nome] = {
                "media_acertos": round(float(arr.mean()), 3),
                "melhor": int(arr.max()),
                "n_13_ou_mais": int((arr >= 13).sum()),
                "n_14_ou_mais": int((arr >= 14).sum()),
                "n_15": int((arr == 15).sum()),
            }

        rand_arr = np.array(random_hits)
        report["baseline_aleatoria"] = {
            "media_acertos": round(float(rand_arr.mean()), 3),
            "n_13_ou_mais": int((rand_arr >= 13).sum()),
            "total_amostras": int(len(rand_arr)),
        }

        # significância: teste t de cada método vs baseline
        for nome in nomes + ["consenso"]:
            arr = np.array(acumulado[nome])
            # compara contra média teórica da hipergeométrica
            t_stat, p_val = stats.ttest_1samp(arr, 9.0)
            report[nome]["t_vs_esperado_9"] = round(float(t_stat), 3)
            report[nome]["p_valor"] = round(float(p_val), 4)

        # verdade teórica
        report["_teoria"] = {
            "esperado_media": 9.0,
            "p_13_mais": round(probabilidade_13_mais(), 6),
            "p_14": round(probabilidade_acertos(14), 7),
            "p_15": round(probabilidade_acertos(15), 9),
        }

        # conclusão: algum método supera significativamente o acaso?
        # Correção de Bonferroni (16 comparações) para evitar falsos positivos.
        alpha_bonf = 0.05 / (len(nomes) + 1)
        significativos = [
            nome for nome in nomes + ["consenso"]
            if report[nome]["p_valor"] < alpha_bonf and report[nome]["t_vs_esperado_9"] > 0
        ]
        report["_conclusao"] = {
            "alpha_bonferroni": round(alpha_bonf, 4),
            "metodos_significativos": significativos,
            "resumo": ("Nenhum método superou o acaso com significância estatística"
                       if not significativos else
                       f"Superaram o acaso (após Bonferroni): {significativos}"),
        }
        return report
