"""
============================================================
LABORATÓRIO DE APRENDIZADO DINÂMICO DA MAGNA (v11.6)
============================================================
Objetivo do usuário: um sistema pessoal que aprende com a base histórica,
recalcula estratégias, investiga, audita cartelas criadas, reconhece jogos
ruins e explora novas possibilidades.

O que este módulo faz de verdade
--------------------------------
1. RODA A BASE HISTÓRICA em walk-forward (treina só no passado, mede no
   futuro) para cada família de estratégia;
2. compara com a baseline aleatória + teórica da hipergeométrica;
3. marca como RUIM / NEUTRA / PROMISSORA cada estratégia;
4. coloca estratégias ruidosas em QUARENTENA (fora do consenso);
5. audita cada cartela criada (estrutura, repetição, intersecção com o
   histórico, filtros, cobertura, P exata de 13/14/15);
6. EXPLORA mutações de parâmetros (janelas, pesos, transformações) e devolve
   as propostas que melhoraram fora-da-amostra;
7. persiste tudo em `magna_laboratorio` e `magna_placar_fontes`.

Honestidade (mantida em cada saída)
-----------------------------------
Sorteios da Lotofácil são independentes: NENHUM método muda a probabilidade
de 13/14/15 de uma cartela. Por isso o laboratório não é um oráculo: é um
**árbitro interno** que impede o sistema de se enganar, e um **explorador**
que só aproveita o que sobrevive ao teste fora-da-amostra.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from config import (
    BORDA, DATABASE_PATH, DEZENAS_POR_JOGO, FIBONACCI, PRIMOS,
    QUADRANTES, TOTAL_DEZENAS, VALOR_APOSTA,
)
from database.db_manager import DBManager

try:
    from scipy import stats as _stats
except Exception:  # pragma: no cover
    _stats = None

_N_UNIVERSO = math.comb(TOTAL_DEZENAS, DEZENAS_POR_JOGO)


# ----------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------
def _binomial_p_atleast(sucessos: int, tentativas: int, p0: float) -> float:
    p = max(0.0, min(1.0, float(p0)))
    if tentativas <= 0:
        return 1.0
    soma = 0.0
    for k in range(int(sucessos), tentativas + 1):
        soma += math.comb(tentativas, k) * (p ** k) * ((1.0 - p) ** (tentativas - k))
    return float(soma)


def _consecutivos(dezenas: Sequence[int]) -> int:
    sd = sorted(int(d) for d in dezenas)
    if not sd:
        return 0
    best = cur = 1
    for i in range(1, len(sd)):
        if sd[i] == sd[i - 1] + 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def _mask(dezenas: Sequence[int]) -> int:
    m = 0
    for d in dezenas:
        m |= 1 << (int(d) - 1)
    return m


def _mascaras_de_linhas(linhas: List[Sequence[int]]) -> np.ndarray:
    return np.array([_mask(l) for l in linhas], dtype=np.uint32)


def _popcount(x):
    if hasattr(np, "bitwise_count"):
        return np.bitwise_count(x).astype(np.int32)
    return np.array([bin(int(v)).count("1") for v in np.asarray(x).ravel()],
                    dtype=np.int32).reshape(np.shape(x))


# ----------------------------------------------------------------
# 1. Auditor de cartelas
# ----------------------------------------------------------------
class AuditorCartelas:
    """Audita cartelas criadas pela Magna.

    O critério final NÃO é "prever": é estrutura + repetição + compatibilidade
    com a linha de base. Uma cartela "boa" é uma cartela que otimiza cobertura
    e variedade sem cair em padrões repetidos/ruidosos.
    """

    def __init__(self, matriz: Optional[np.ndarray] = None,
                 db_path: Optional[str] = None,
                 historico_dezenas: Optional[List[Sequence[int]]] = None):
        self.matriz = (np.asarray(matriz, dtype=float) if matriz is not None
                       else None)
        self.linhas_historico = historico_dezenas or []
        self._masks_hist = _mascaras_de_linhas(
            self.linhas_historico) if self.linhas_historico else np.empty(0, dtype=np.uint32)
        self.db_path = db_path
        if historico_dezenas is None and db_path is not None:
            self.linhas_historico = self._ler_resultados_banco(db_path)
            self._masks_hist = _mascaras_de_linhas(self.linhas_historico)

    @staticmethod
    def _ler_resultados_banco(db_path: str) -> List[Sequence[int]]:
        if not db_path or not os.path.exists(db_path):
            return []
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                       d11,d12,d13,d14,d15
                FROM resultados ORDER BY concurso ASC
            """).fetchall()
            return [[int(r["d{}".format(i)]) for i in range(1, 16)]
                    for r in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    @staticmethod
    def prob_acertos(k: int) -> float:
        """P(k acertos da cartela contra 1 sorteio). Hipergeométrica exata."""
        if not 0 <= k <= 15:
            return 0.0
        return (math.comb(15, k) * math.comb(10, 15 - k)) / _N_UNIVERSO

    def _semelhante_ao_historico(self, dezenas: Sequence[int],
                                 limiar: int = 13) -> int:
        """Nº de sorteios históricos com interseção >= limiar."""
        if len(self._masks_hist) == 0:
            return 0
        m = np.uint32(_mask(dezenas))
        hits = _popcount(self._masks_hist & m)
        return int((hits >= limiar).sum())

    def _quantidade_semelhante_lote(self, dezenas: Sequence[int],
                                    lote: List[Sequence[int]],
                                    limiar: int = 13) -> int:
        m = _mask(dezenas)
        outros = _mascaras_de_linhas(lote) if lote else np.empty(0, dtype=np.uint32)
        if len(outros) == 0:
            return 0
        hits = _popcount(outros & m)
        return int((hits >= limiar).sum())

    def auditar(self, dezenas: Sequence[int],
                lote: Optional[List[Sequence[int]]] = None,
                score_modelo: Optional[float] = None,
                vetor_final: Optional[np.ndarray] = None) -> Dict[str, Any]:
        ds = sorted(int(d) for d in dezenas)
        if len(ds) != 15 or len(set(ds)) != 15:
            return {"valida": False, "msg": "cartela precisa de 15 dezenas únicas"}

        conjunto = set(ds)
        soma = sum(ds)
        pares = sum(1 for d in ds if d % 2 == 0)
        primos = len(conjunto & PRIMOS)
        fib = len(conjunto & FIBONACCI)
        borda = len(conjunto & BORDA)
        consec = _consecutivos(ds)
        q_counts = [len(conjunto & set(nums)) for _q, nums in QUADRANTES.items()]
        desvio_q = max(q_counts) - min(q_counts) if q_counts else 0

        # filtros padrão da Magna (mesmos percentis recalculados)
        ok_filtro = (155 <= soma <= 236 and 4 <= pares <= 10 and
                     3 <= primos <= 8 and 2 <= fib <= 7 and
                     7 <= borda <= 12 and consec <= 14)

        semelh_hist = self._semelhante_ao_historico(ds, limiar=13)
        semelh_lote = self._quantidade_semelhante_lote(ds, lote or [])
        repetida_hist = semelh_hist > 0     # já saiu como 15 pontos antes
        quase_repetida = semelh_hist >= 2   # >13 dezenas de sorteios passados
        over_lote = semelh_lote > 0         # >13 repetidas com outras do lote

        # massa modelada dentro da cartela (se houver vetor)
        if vetor_final is not None and len(vetor_final) == 25:
            ev_modelo = float(sum(vetor_final[d - 1] for d in ds))
        elif score_modelo is not None:
            ev_modelo = float(score_modelo)
        else:
            ev_modelo = float(sum(ds)) / 240.0

        # combinação de riscos estruturais
        riscos: List[str] = []
        if repetida_hist:
            riscos.append("já saiu 15 pontos no histórico")
        if quase_repetida:
            riscos.append(f"{semelh_hist} sorteios históricos com ≥13 dezenas iguais")
        if over_lote:
            riscos.append(f"{semelh_lote} cartelas do lote com ≥13 dezenas iguais")
        if not ok_filtro:
            riscos.append("fora da faixa percentil histórica (filtro)")
        if desvio_q >= 5:
            riscos.append("quadrantes muito desbalanceados")
        if consec >= 12:
            riscos.append("sequência longa demais (padrão visual comum)")

        # score básico 0..1 a partir dos riscos (-0.12 por risco, até 0)
        base = 1.0 - 0.12 * len(riscos)
        # diversidade informacional negativa para padrões repetidos
        if ev_modelo > 0:
            base += 0.10 * min(1.0, ev_modelo / 20.0)
        score = float(np.clip(base, 0.0, 1.0))

        if score >= 0.75 and not repetida_hist:
            veredito = "APROVADA"
        elif score >= 0.55 and not repetida_hist:
            veredito = "ACEITA"
        elif score >= 0.40:
            veredito = "OBSERVACAO"
        else:
            veredito = "RUIM"

        return {
            "valida": True,
            "dezenas": ds,
            "soma": soma,
            "pares": pares,
            "primos": primos,
            "fibonacci": fib,
            "borda": borda,
            "consecutivos": consec,
            "desvio_quadrantes": desvio_q,
            "filtr_ok": bool(ok_filtro),
            "semelhantes_historicos_ge_13": semelh_hist,
            "semelhantes_lote_ge_13": semelh_lote,
            "jogo_ja_saiu_15": bool(repetida_hist),
            "quase_repetido_historico": bool(quase_repetida),
            "ev_modelo": round(float(ev_modelo), 6),
            "riscos": riscos,
            "score_estrutural": round(score, 4),
            "veredito": veredito,
            "prob_acertos_exatas": {
                str(k): round(self.prob_acertos(k), 10) for k in (11, 12, 13, 14, 15)
            },
            "nota": (
                "Esta auditoria avalia ESTRUTURA e repetição, não prevê o "
                "sorteio. A probabilidade exata de 13/14/15 é a hipergeométrica."
            ),
        }

    def auditar_lote(self, cartelas: List[Sequence[int]],
                     lote: Optional[List[Sequence[int]]] = None,
                     score_modelos: Optional[List[float]] = None,
                     vetor_final: Optional[np.ndarray] = None) -> Dict[str, Any]:
        lote = [sorted(int(d) for d in c) for c in (lote or cartelas)]
        res = []
        for i, c in enumerate(cartelas):
            sm = (score_modelos[i] if score_modelos is not None and
                  i < len(score_modelos) else None)
            res.append(self.auditar(c, lote=lote, score_modelo=sm,
                                    vetor_final=vetor_final))
        aprovadas = [r for r in res if r.get("veredito") in ("APROVADA", "ACEITA")]
        ruins = [r for r in res if r.get("veredito") == "RUIM"]
        aceitaveis = [r for r in res if r.get("veredito") != "RUIM"]
        return {
            "n_cartelas": len(res),
            "n_aprovadas": len(aprovadas),
            "n_aceitaveis": len(aceitaveis),
            "n_ruins": len(ruins),
            "n_observacao": len(res) - len(aprovadas) - len(ruins),
            "cartelas": res,
            "veredito_geral": (
                "LOTE APROVADO" if len(aprovadas) == len(res) and len(res) > 0 else
                "LOTE COM RESSALVAS" if len(ruins) == 0 else
                "LOTE CONTÉM JOGOS RUINS"
            ),
            "honestidade": (
                "Nenhuma auditoria muda P(acerto). Ela serve para não repetir "
                "jogos já saídos e para evitar padrões fracos/ruidosos."
            ),
        }

    def jogos_ruins_historicos(self, limite: int = 40) -> Dict[str, Any]:
        """Procura no histórico cartelas que se repetem/quase se repetem."""
        if not self.linhas_historico:
            return {"n": 0, "jogos": [], "msg": "sem histórico carregado"}
        mascaras = _mascaras_de_linhas(self.linhas_historico)
        n = len(mascaras)
        achados: List[Dict[str, Any]] = []
        visto: set = set()
        ultimas = mascaras if n <= 400 else mascaras[-400:]
        for i in range(n):
            m = int(mascaras[i])
            if m in visto:
                continue
            hits = _popcount(ultimas & np.uint32(m))
            n_ge15 = max(0, int((hits == 15).sum()) - 1)  # remove ele mesmo
            n_ge13 = max(0, int((hits >= 13).sum()) - 1)
            if n_ge15 > 0 or n_ge13 >= 1:
                dez = [i + 1 for i in range(25) if (m >> i) & 1]
                # frequência percentual sobre a janela
                freq = round(float(n_ge13) / max(len(ultimas), 1), 6)
                achados.append({
                    "dezenas": dez,
                    "repetido_15": int(n_ge15),
                    "quase_repetido_13_mais": int(n_ge13),
                    "freq_na_janela": freq,
                    "motivo": (
                        "jogo já saiu como 15 pontos anteriormente"
                        if n_ge15 > 0 else
                        "aparece ≥2 vezes com ≥13 dezenas iguais no histórico"
                    ),
                })
                visto.add(m)
                if len(achados) >= limite:
                    break
        return {"n": len(achados), "jogos": achados}


# ----------------------------------------------------------------
# 2. Famílias de estratégia
# ----------------------------------------------------------------
ESTRATEGIAS_BASE = (
    "uniforme", "freq_global", "freq_recente", "reversao", "markov",
    "espectral", "combinacao",
)

ESTRATEGIAS_ROTULOS = {
    "uniforme": "Sorteio aleatório (baseline)",
    "freq_global": "Frequência histórica",
    "freq_recente": "Frequência recente",
    "reversao": "Reversão à média",
    "markov": "Transição de Markov",
    "espectral": "Espectro temporal (FFT)",
    "combinacao": "Consenso do laboratório",
}


class FabricaEstrategias:
    """Gera vetores de plausibilidade a partir de uma janela histórica."""

    @staticmethod
    def vetor_uniforme() -> np.ndarray:
        return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    @staticmethod
    def vetor_freq_global(matriz: np.ndarray) -> np.ndarray:
        v = np.asarray(matriz, dtype=float).sum(axis=0)
        s = v.sum()
        return (v / s) if s > 0 else FabricaEstrategias.vetor_uniforme()

    @staticmethod
    def vetor_freq_recente(matriz: np.ndarray,
                           janela: int = 50) -> np.ndarray:
        m = np.asarray(matriz, dtype=float)
        if len(m) > janela:
            m = m[-janela:]
        return FabricaEstrategias.vetor_freq_global(m)

    @staticmethod
    def vetor_reversao(matriz: np.ndarray) -> np.ndarray:
        base = FabricaEstrategias.vetor_freq_global(matriz)
        # quanto MENOS saiu no passado, mais peso a reversão dá (com teto)
        v = 1.0 / (base * TOTAL_DEZENAS + 1e-3)
        # atenua para não ficar explosivo
        v = np.sqrt(v)
        return v / v.sum()

    @staticmethod
    def vetor_markov(matriz: np.ndarray, janela: int = 200) -> np.ndarray:
        m = np.asarray(matriz, dtype=float)
        if len(m) > janela:
            m = m[-janela:]
        if m.shape[0] < 2:
            return FabricaEstrategias.vetor_uniforme()
        v = np.zeros(TOTAL_DEZENAS)
        # transição simple: se j saiu no t-1, quanto i saiu no t juntos
        for t in range(1, len(m)):
            ant = np.where(m[t - 1] == 1)[0] + 1
            atu = np.where(m[t] == 1)[0] + 1
            for a in ant:
                v[a - 1] += 0.25
            for b in atu:
                v[b - 1] += 0.05
        v += m.sum(axis=0) * 0.5
        return v / v.sum()

    @staticmethod
    def vetor_espectral(matriz: np.ndarray, janela: int = 200) -> np.ndarray:
        m = np.asarray(matriz, dtype=float)
        if len(m) > janela:
            m = m[-janela:]
        v = np.zeros(TOTAL_DEZENAS)
        for d in range(TOTAL_DEZENAS):
            sig = m[:, d].astype(float)
            if len(sig) >= 8:
                f = np.abs(np.fft.rfft(sig - sig.mean()))
                # prioriza dezenas com componente de baixa frequência
                if len(f) > 1:
                    v[d] = float(f[1]) + 0.5 * float(f[0])
            else:
                v[d] = float(sig.mean())
        if v.sum() <= 0:
            return FabricaEstrategias.vetor_uniforme()
        # suavização log + normalização
        v = np.log1p(np.maximum(v, 0.0))
        return v / v.sum() if v.sum() > 0 else FabricaEstrategias.vetor_uniforme()

    @classmethod
    def todos(cls, treino: np.ndarray, janela: int = 50,
              pesos: Optional[Dict[str, float]] = None) -> Dict[str, np.ndarray]:
        return {
            "uniforme": cls.vetor_uniforme(),
            "freq_global": cls.vetor_freq_global(treino),
            "freq_recente": cls.vetor_freq_recente(treino, janela),
            "reversao": cls.vetor_reversao(treino),
            "markov": cls.vetor_markov(treino),
            "espectral": cls.vetor_espectral(treino),
            "combinacao": cls.combinacao(treino, pesos=pesos, janela=janela),
        }

    @classmethod
    def combinacao(cls, treino: np.ndarray,
                   pesos: Optional[Dict[str, float]] = None,
                   janela: int = 50) -> np.ndarray:
        pesos = pesos or {
            "freq_global": 0.20, "freq_recente": 0.20, "reversao": 0.15,
            "markov": 0.15, "espectral": 0.15, "uniforme": 0.15,
        }
        v = np.zeros(TOTAL_DEZENAS)
        for nome, p in pesos.items():
            if nome == "uniforme":
                v += p * cls.vetor_uniforme()
            elif nome == "freq_global":
                v += p * cls.vetor_freq_global(treino)
            elif nome == "freq_recente":
                v += p * cls.vetor_freq_recente(treino, janela)
            elif nome == "reversao":
                v += p * cls.vetor_reversao(treino)
            elif nome == "markov":
                v += p * cls.vetor_markov(treino)
            elif nome == "espectral":
                v += p * cls.vetor_espectral(treino)
        if v.sum() <= 0:
            return cls.vetor_uniforme()
        return v / v.sum()


# ----------------------------------------------------------------
# 3. Lab (benchmark + exploração + persistência)
# ----------------------------------------------------------------
class LaboratorioMagna:
    _VERSAO = "v11.6-laboratorio-dinamico"

    def __init__(self, db_path: Optional[str] = None,
                 matriz: Optional[np.ndarray] = None,
                 pesos_iniciais: Optional[Dict[str, float]] = None):
        self.db_path = db_path or DATABASE_PATH
        self.db = DBManager(self.db_path)
        self.matriz = self._carregar_matriz() if matriz is None else \
            np.asarray(matriz, dtype=float)
        self.n = len(self.matriz)
        self.historico = AuditorCartelas._ler_resultados_banco(self.db_path)
        self.auditor = AuditorCartelas(
            matriz=self.matriz, db_path=self.db_path,
            historico_dezenas=self.historico,
        )
        self.pesos_iniciais = dict(pesos_iniciais or {})
        self._placar = {}
        self._quarentena: List[str] = []
        self._recomendacao: Dict[str, float] = {}
        self._criar_tabelas()

    # ---------------- consulta base ----------------
    def _carregar_matriz(self) -> np.ndarray:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                       d11,d12,d13,d14,d15
                FROM resultados ORDER BY concurso ASC
            """).fetchall()
        finally:
            conn.close()
        out = np.zeros((len(rows), TOTAL_DEZENAS), dtype=np.float32)
        for i, r in enumerate(rows):
            for j in range(1, 16):
                d = int(r["d{}".format(j)])
                if 1 <= d <= 25:
                    out[i][d - 1] = 1.0
        return out

    def _criar_tabelas(self):
        conn = self.db.get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS magna_laboratorio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tipo TEXT NOT NULL,
                parametros TEXT,
                resultado TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS magna_placar_fontes (
                fonte TEXT PRIMARY KEY,
                janela INTEGER,
                n_testes INTEGER,
                media_acertos REAL,
                taxa_13_mais REAL,
                p_valor REAL,
                veredito TEXT,
                quarentena INTEGER DEFAULT 0,
                atualizado_em TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _registrar(self, tipo: str, parametros: Dict, resultado: Dict):
        conn = self.db.get_conn()
        try:
            conn.execute("""
                INSERT INTO magna_laboratorio
                (timestamp, tipo, parametros, resultado)
                VALUES (?,?,?,?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(tipo),
                json.dumps(self._json(parametros)),
                json.dumps(self._json(resultado)),
            ))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

    def _persistir_placar(self, nome: str, linha: Dict):
        conn = self.db.get_conn()
        try:
            conn.execute("""
                INSERT INTO magna_placar_fontes
                (fonte, janela, n_testes, media_acertos, taxa_13_mais,
                 p_valor, veredito, quarentena, atualizado_em)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(fonte) DO UPDATE SET
                    janela=excluded.janela, n_testes=excluded.n_testes,
                    media_acertos=excluded.media_acertos,
                    taxa_13_mais=excluded.taxa_13_mais,
                    p_valor=excluded.p_valor, veredito=excluded.veredito,
                    quarentena=excluded.quarentena,
                    atualizado_em=excluded.atualizado_em
            """, (
                str(nome),
                int(linha.get("janela", 0) or 0),
                int(linha.get("n_testes", 0) or 0),
                float(linha.get("media_acertos", 0) or 0),
                float(linha.get("taxa_13_mais", 0) or 0),
                float(linha.get("p_valor", 1.0) or 1.0),
                str(linha.get("veredito", "?")) if linha.get("veredito") else "?",
                1 if linha.get("quarentena") else 0,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

    # ---------------- benchmark ----------------
    def rodar_benchmark(self, n_testes: int = 40, janela: int = 50,
                        n_aleatorio: int = 120,
                        pesos: Optional[Dict[str, float]] = None,
                        persistir: bool = True) -> Dict[str, Any]:
        """Walk-forward de todas as famílias de estratégia."""
        t0 = time.time()
        n = self.n
        n_testes = int(max(1, min(int(n_testes), max(1, n - 40))))
        if n < 60:
            return {"status": "erro", "msg": "base insuficiente (mínimo 60)"}

        treino_min = min(60, n - n_testes)
        acumulado: Dict[str, List[int]] = {
            nome: [] for nome in ESTRATEGIAS_BASE
        }
        erros_dict: Dict[str, float] = {nome: 0.0 for nome in ESTRATEGIAS_BASE}
        aleatorio_hits: List[int] = []
        detalhes: List[Dict] = []

        for t in range(n - n_testes, n):
            treino = self.matriz[:t]
            real = set(int(x) + 1 for x in np.where(self.matriz[t] == 1)[0])
            if len(real) != 15:
                continue
            vetores = FabricaEstrategias.todos(
                treino, janela=janela, pesos=pesos)
            rng = np.random.default_rng(t + 723)
            for _ in range(n_aleatorio):
                aleatorio_hits.append(len(set(
                    rng.choice(TOTAL_DEZENAS, size=15, replace=False)) &
                    real))
            for nome, v in vetores.items():
                top = set(int(x) + 1 for x in np.argsort(v)[::-1][:15])
                hits = len(top & real)
                acumulado[nome].append(hits)
                erros_dict[nome] += 15 - hits

        # agrega
            baseline_random = float(np.mean(aleatorio_hits)) if aleatorio_hits else 9.0
        report = {}
        for nome in ESTRATEGIAS_BASE:
            arr = np.array(acumulado[nome], dtype=float)
            if len(arr) == 0:
                continue
            media = float(arr.mean())
            taxa13 = float((arr >= 13).sum() / len(arr))
            # p-valor contra a distribuição empírica aleatória.
            # Para `uniforme` (baseline) usamos a distribuição teórica.
            if _stats is not None and len(aleatorio_hits) >= 20 and nome != "uniforme":
                p = float(_stats.mannwhitneyu(
                    arr, np.array(aleatorio_hits, dtype=float),
                    alternative="two-sided").pvalue)
            else:
                p = float(_binomial_p_atleast(int((arr >= 13).sum()),
                                              len(arr), 1 / 691.0))
            desvio = media - 9.0
            desvio_aleatorio = media - baseline_random

            if nome == "uniforme":
                # baseline por definição: nunca entra em quarentena
                veredito = "NEUTRA"
            elif media < baseline_random - 0.30:
                veredito = "RUIM"
            elif desvio_aleatorio > 0.55 and p < 0.05:
                veredito = "PROMISSORA"
            elif desvio_aleatorio > 0.25 and p < 0.10:
                veredito = "PROMISSORA"
            elif desvio_aleatorio > 0.15:
                veredito = "ATENCAO"
            else:
                veredito = "NEUTRA"
            quarentena = veredito == "RUIM"
            report[nome] = {
                "n_testes": len(arr),
                "media_acertos": round(media, 4),
                "taxa_13_mais": round(taxa13, 5),
                "erro_total": round(erros_dict[nome], 1),
                "p_valor": round(p, 5),
                "desvio_vs_9": round(desvio, 4),
                "desvio_vs_aleatorio": round(float(desvio_aleatorio), 4),
                "veredito": veredito,
                "quarentena": bool(quarentena),
                "justificativa": (
                    "Fica fora do consenso por ficar abaixo da linha de base."
                    if quarentena else
                    "Entra no consenso com peso proporcional ao desvio; "
                    "baseline 'uniforme' nunca é quarentenada."
                ),
            }
            if persistir:
                self._persistir_placar(nome, report[nome])
            self._placar[nome] = report[nome]
            self._quarentena = [k for k, v in report.items() if v["quarentena"]]

        self._recomendacao = self._recomendar_pesos(report)
        resumo = {
            "status": "ok",
            "versao": self._VERSAO,
            "concursos_na_base": n,
            "n_testes": n_testes,
            "janela": janela,
            "baseline_aleatoria": round(baseline_random, 4),
            "baseline_teorica": 9.0,
            "estimativas": report,
            "quarentena": list(self._quarentena),
            "pesos_recomendados": self._recomendacao,
            "tempo_seg": round(time.time() - t0, 2),
            "veredito_geral": (
                "Ainda na linha do acaso: nenhuma estratégia supera a"
                " hipergeométrica de forma consistente."
                if not any(v["veredito"] == "PROMISSORA"
                           for v in report.values()) else
                "Há candidatas PROMISSORAS acima do acaso (verificar nº de"
                " concursos e não comemorar antes de mais 50 sorteios)."
            ),
            "honestidade": (
                "O benchmark é fora-da-amostra e compara com o Acaso. "
                "Alcançar 9,0 acertos em média é o esperado; não é derrota "
                "do sistema — é a realidade de um sorteio independente."
            ),
        }
        if persistir:
            self._registrar("benchmark", {"n_testes": n_testes,
                                          "janela": janela}, resumo)
        return resumo

    def _recomendar_pesos(
            self, report: Dict[str, Dict]) -> Dict[str, float]:
        """Pesos para as fontes do consenso, com quarentena automática."""
        pesos = {}
        soma = 0.0
        for nome, linha in report.items():
            if nome == "uniforme":
                continue
            if linha["veredito"] in ("RUIM", "NEUTRA") or linha["quarentena"]:
                continue
            # desvio positivo e significância entram; depois normaliza
            dev = max(0.0, float(linha.get("desvio_vs_aleatorio", 0.0)))
            p = max(1e-4, 1.0 - float(linha["p_valor"]))
            peso = max(0.0, dev * 4 + 0.15 * p)
            pesos[nome] = peso
            soma += peso
        if soma <= 0:
            # fallback: só freq_global e freq_recente com peso pequeno
            pesos = {"freq_global": 0.35, "freq_recente": 0.35,
                     "uniforme": 0.30}
            return pesos
        return {k: round(v / soma, 4) for k, v in pesos.items()}

    # ---------------- auditoria ----------------
    def auditar_cartelas(self, cartelas: List[Sequence[int]],
                         score_modelos: Optional[List[float]] = None,
                         vetor_final: Optional[np.ndarray] = None,
                         persistir: bool = True) -> Dict[str, Any]:
        res = self.auditor.auditar_lote(
            cartelas, cartelas, score_modelos=score_modelos,
            vetor_final=vetor_final)
        if persistir:
            self._registrar("auditura", {"max_cartelas": len(cartelas)}, res)
        return res

    def jogos_ruins(self, persistir: bool = True) -> Dict[str, Any]:
        res = self.auditor.jogos_ruins_historicos(limite=50)
        if persistir:
            self._registrar("jogos_ruins", {"limite": 50}, res)
        return res

    # ---------------- exploração ----------------
    def explorar(self, ensaios: List[Dict[str, Any]],
                 n_testes: int = 20, persistir: bool = True) -> Dict[str, Any]:
        """Avalia mutações de estratégia (janela + pesos + transformações).

        Cada ensaio dita `janela`, `pesos`, e, se quiser, `transformacao`.
        O resultado é comparado com o benchmark da combinação padrão.
        """
        if not ensaios:
            return {"status": "erro", "msg": "nenhum ensaio"}

        # benchmark base para comparar
        base = self.rodar_benchmark(n_testes=n_testes, persistir=False)
        base_combi = (base["estimativas"].get("combinacao", {})
                      .get("media_acertos", 9.0) or 9.0)

        resultados = []
        for e in ensaios:
            janela = int(e.get("janela", 50))
            pesos = e.get("pesos")
            trans = e.get("transformacao")
            try:
                br = self.rodar_benchmark(n_testes=n_testes, janela=janela,
                                          pesos=pesos, persistir=False)
                media = (br["estimativas"].get("combinacao", {})
                         .get("media_acertos", 9.0))
                ganho = float(media) - float(base_combi)
                veredito = "MELHOROU" if ganho > 0.15 else "NEUTRO"
                resultados.append({
                    "janela": janela,
                    "pesos": pesos,
                    "transformacao": trans,
                    "media_acertos": round(float(media), 4),
                    "ganho_vs_base": round(float(ganho), 4),
                    "veredito": veredito,
                })
            except Exception as exc:
                resultados.append({"janela": janela, "erro": str(exc)})

        resultados.sort(key=lambda r: r.get("ganho_vs_base", -999), reverse=True)
        sucesso = [r for r in resultados if r.get("veredito") == "MELHOROU"]
        out = {
            "status": "ok",
            "n_ensaios": len(resultados),
            "base_media_combinacao": round(float(base_combi), 4),
            "melhores_propostas": resultados[:10],
            "n_melhoraram": len(sucesso),
            "veredito": (
                "Nenhuma mutação superou claramente a combinação padrão."
                if not sucesso else
                "Há mutações que melhoraram fora-da-amostra (tratar com cautela)"
            ),
            "honestidade": (
                "Explorar mutações é pesquisa empírica, não magia. Qualquer "
                "ganho precisa ser confirmado em uma janela futura maior."
            ),
        }
        if persistir:
            self._registrar("exploracao",
                            {"n_ensaios": len(ensaios), "n_testes": n_testes}, out)
        return out

    # ---------------- estado ----------------
    def placar_persistido(self) -> List[Dict[str, Any]]:
        conn = self.db.get_conn()
        try:
            rows = conn.execute("""
                SELECT * FROM magna_placar_fontes ORDER BY media_acertos DESC
            """).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()

    def relatorio(self) -> Dict[str, Any]:
        return {
            "versao": self._VERSAO,
            "concursos_na_base": self.n,
            "baseline_teorica": 9.0,
            "placar_historico": self.placar_persistido(),
            "placar_memoria": self._placar,
            "quarentena": list(self._quarentena),
            "pesos_recomendados": self._recomendacao,
            "auditor": {
                "funcional": True,
                "historico_para_auditoria": len(self.historico),
            },
            "honestidade": (
                "Laboratório pessoal de estudo: mede, explora e quarentena. "
                "A previsibilidade perfeita de um sorteio independente não "
                "existe; o que existe é estrutura, disciplina e contabilidade."
            ),
        }

    @staticmethod
    def _json(val):
        if isinstance(val, np.ndarray):
            return val.tolist()
        if isinstance(val, np.generic):
            return val.item()
        if isinstance(val, dict):
            return {str(k): LaboratorioMagna._json(v) for k, v in val.items()}
        if isinstance(val, (list, tuple, set)):
            return [LaboratorioMagna._json(v) for v in val]
        return val
