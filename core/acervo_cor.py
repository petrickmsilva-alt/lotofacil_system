"""
============================================================================
ACERVO DE CORES DA MAGNA (v11.8) — órgão da Inteligência Magna
============================================================================
Fonte do conhecimento: tabela oficial de cores das bolas da Lotofácil
(MazuSoft — https://www.mazusoft.com.br/lotofacil/tabela-cor.php).

A cor de cada bola é definida pelo ÚLTIMO dígito do número (regra oficial,
documentada na própria tabela):

    Grupo 1 (3 dezenas por cor):
        Vermelha · 01, 11, 21      Amarela · 02, 12, 22
        Verde    · 03, 13, 23      Marrom  · 04, 14, 24
        Azul     · 05, 15, 25

    Grupo 2 (2 dezenas por cor):
        Rosa    · 06, 16           Preta   · 07, 17
        Cinza   · 08, 18           Laranja · 09, 19
        Branca  · 10, 20

Como a cor é uma função DETERMINÍSTICA do número, a tabela por concurso é
derivada das 15 dezenas oficiais que a base `resultados` já guarda — a Magna
não precisa de download: ela REAPRENDE o domínio inteiro a cada assimilação
e memoriza o que aprendeu em `magna_conhecimento`/`magna_memoria`.

O que este órgão mede (sempre com a disciplina de honestidade da casa):

  - distribuição de cores por sorteio real × teórica hipergeométrica
    P(k bolas da cor c) = C(n_c, k)·C(25−n_c, 15−k) / C(25,15);
  - streaks da cor dominante (a que mais aparece no sorteio);
  - repetição da dominância (regra popular) com margem teórica por simulação;
  - placar walk-forward sem vazamento + auto-auditoria com p-valor binomial;
  - posterior do próximo sorteio por cor → vetor 25-dim para o consenso;
  - afinidade estrutural de cada cartela com o perfil de cores aprendido.

HONESTIDADE (regra da casa): nenhum padrão de cor muda a probabilidade
hipergeométrica de uma cartela. O acervo mede, memoriza, publica o placar e
atenuia a própria influência quando o placar não supera a margem — exatamente
como o acervo de abertura (AcervoAberturaMagna) e as fontes de clima/INMET.
============================================================================
"""
import hashlib
import math
import threading
from collections import Counter
from math import comb
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from config import TOTAL_DEZENAS, DEZENAS_POR_JOGO

# ---------------------------------------------------------------------------
# TABELA OFICIAL DE CORES (MazuSoft — último dígito de cada bola)
# ---------------------------------------------------------------------------
CORES_GRUPO1 = ("vermelha", "amarela", "verde", "marrom", "azul")
CORES_GRUPO2 = ("rosa", "preta", "cinza", "laranja", "branca")
CORES = CORES_GRUPO1 + CORES_GRUPO2

DEZENAS_COR: Dict[str, Tuple[int, ...]] = {
    "vermelha": (1, 11, 21),
    "amarela": (2, 12, 22),
    "verde": (3, 13, 23),
    "marrom": (4, 14, 24),
    "azul": (5, 15, 25),
    "rosa": (6, 16),
    "preta": (7, 17),
    "cinza": (8, 18),
    "laranja": (9, 19),
    "branca": (10, 20),
}

COR_DEZENA: Dict[int, str] = {
    d: cor for cor, dezenas in DEZENAS_COR.items() for d in dezenas
}

GRUPO_COR: Dict[str, int] = {
    cor: (1 if cor in CORES_GRUPO1 else 2) for cor in CORES
}

# Nome de exibição (pt-BR, capitalizado) — usado em leituras e relatórios.
CORES_EXIBICAO: Dict[str, str] = {c: c.capitalize() for c in CORES}

_MARGEM_MISTURA = 200.0      # concursos p/ a frequência medida pesar metade
_BASELINE_DOMINANCIA_CACHE: Optional[Dict[str, Any]] = None


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


class AcervoCorMagna:
    """Conhecimento memorizado da Magna sobre as CORES das bolas.

    Um único canal, medido na base histórica inteira (`resultados.d1..d15`):

      `perfil` — para cada uma das 10 cores, a distribuição de quantas bolas
      daquela cor saíram por sorteio (0..3 no Grupo 1, 0..2 no Grupo 2),
      confrontada com a margem hipergeométrica exata; mais a série da COR
      DOMINANTE (a cor com mais bolas no sorteio, empate desfeito pela ordem
      fixa da tabela oficial), seus streaks e a taxa de repetição da
      dominância com margem teórica estimada por simulação.

    O acervo mede: frequências reais × teóricas, streaks, repetição da
    dominância (regra popular) com p-valor, placar walk-forward, auto-
    auditoria e a posterior do próximo sorteio — que vira o vetor 25-dim
    entregue ao consenso da Magna (atenuado pelo fator de confiança).
    """

    TOTAL = TOTAL_DEZENAS
    TAM_ORDEM = DEZENAS_POR_JOGO
    CORES = CORES
    CORES_GRUPO1 = CORES_GRUPO1
    CORES_GRUPO2 = CORES_GRUPO2
    DEZENAS_COR = DEZENAS_COR
    COR_DEZENA = COR_DEZENA
    GRUPO_COR = GRUPO_COR
    MARGEM_MISTURA = _MARGEM_MISTURA

    # ------------------------------------------------------------
    # construção e ingestão
    # ------------------------------------------------------------
    def __init__(self, serie: Optional[Sequence[Tuple[int, Sequence[int]]]] = None,
                 alpha: float = 1.0):
        self._lock = threading.RLock()
        self.alpha = float(alpha)
        self.serie: List[Tuple[int, Tuple[int, ...]]] = sorted(
            (int(c), self.validar_dezenas(d)) for c, d in (serie or []))
        self._memo: Dict[Any, Any] = {}

    @classmethod
    def validar_dezenas(cls, dezenas: Sequence[int]) -> Tuple[int, ...]:
        """Exige exatamente 15 dezenas únicas em 1-25 (perfil de um sorteio)."""
        try:
            vals = tuple(sorted(int(d) for d in dezenas))
        except (TypeError, ValueError):
            raise ValueError("dezenas devem ser 15 inteiros 1-25")
        if (len(vals) != cls.TAM_ORDEM or len(set(vals)) != cls.TAM_ORDEM
                or any(d < 1 or d > cls.TOTAL for d in vals)):
            raise ValueError(
                "perfil inválido: 15 dezenas únicas 1-25 obrigatórias, "
                "recebi {}".format(list(vals)))
        return vals

    def aprender(self, concurso: int, dezenas: Sequence[int]) -> Dict[str, Any]:
        """Upsert idempotente de um sorteio na memória viva (por concurso)."""
        vals = self.validar_dezenas(dezenas)
        concurso = int(concurso)
        if concurso < 1:
            raise ValueError("concurso inválido")
        with self._lock:
            atual = dict(self.serie)
            igual = atual.get(concurso) == vals
            atual[concurso] = vals
            self.serie = sorted(atual.items())
            self._memo.clear()
            perfil = self.perfil_dezenas(vals)
            return {"status": "ok", "concurso": concurso,
                    "idempotente": bool(igual),
                    "n_registros": len(self.serie),
                    "perfil": perfil,
                    "dominante": self.dominante_de(perfil)}

    # ------------------------------------------------------------
    # perfil de cores (determinístico a partir das dezenas)
    # ------------------------------------------------------------
    @classmethod
    def perfil_dezenas(cls, dezenas: Sequence[int]) -> Dict[str, int]:
        """Contagem de bolas por cor para um conjunto de dezenas (ordem fixa)."""
        perfil = {c: 0 for c in cls.CORES}
        for d in dezenas:
            cor = cls.COR_DEZENA.get(int(d))
            if cor is not None:
                perfil[cor] += 1
        return perfil

    @classmethod
    def dominante_de(cls, perfil: Dict[str, int]) -> str:
        """A cor com mais bolas no perfil; empate desfeito pela ordem fixa da
        tabela oficial (determinístico — mesma regra usada na simulação)."""
        melhor, maior = None, -1
        for c in cls.CORES:
            q = int(perfil.get(c, 0))
            if q > maior:
                maior, melhor = q, c
        return melhor

    @classmethod
    def n_bolas(cls, cor: str) -> int:
        if cor not in cls.DEZENAS_COR:
            raise ValueError("cor desconhecida: {}".format(cor))
        return len(cls.DEZENAS_COR[cor])

    # ------------------------------------------------------------
    # teoria: a margem hipergeométrica exata
    # ------------------------------------------------------------
    @classmethod
    def p_teorica(cls, cor: str, k: int) -> float:
        """P(exatamente k bolas da cor c num sorteio de 15 entre 25).

        P(k) = C(n_c, k) · C(25−n_c, 15−k) / C(25, 15)
        Grupo 1 (n_c=3): 0,0522 · 0,2935 · 0,4565 · 0,1978 (k=0..3)
        Grupo 2 (n_c=2): 0,1500 · 0,5000 · 0,3500       (k=0..2)
        """
        n_c = cls.n_bolas(cor)
        if k < 0 or k > n_c:
            return 0.0
        return (comb(n_c, k) * comb(cls.TOTAL - n_c,
                                    cls.TAM_ORDEM - k)
                / comb(cls.TOTAL, cls.TAM_ORDEM))

    @classmethod
    def p_aparecer_teorica(cls, cor: str) -> float:
        """P(a cor c aparecer ao menos uma vez) sob sorteio independente."""
        return 1.0 - cls.p_teorica(cor, 0)

    @classmethod
    def p_forte_teorica(cls, cor: str) -> float:
        """P(a cor c vir com 2+ bolas) sob sorteio independente."""
        return sum(cls.p_teorica(cor, k) for k in range(2, cls.n_bolas(cor) + 1))

    @classmethod
    def esperado_teorico(cls, cor: str) -> float:
        """E[bolas da cor c] = 15·n_c/25 (1,8 no Grupo 1; 1,2 no Grupo 2)."""
        return cls.TAM_ORDEM * cls.n_bolas(cor) / cls.TOTAL

    # ------------------------------------------------------------
    # leitura da memória
    # ------------------------------------------------------------
    def n(self) -> int:
        return len(self.serie)

    def ultimo(self) -> Optional[int]:
        return int(self.serie[-1][0]) if self.serie else None

    def _chave_memo(self, nome: str, canal: str):
        return (nome, canal, self.n())

    def _contagens(self) -> Dict[str, List[int]]:
        """cnt[cor][k] = nº de sorteios em que a cor veio exatamente k vezes."""
        chave = self._chave_memo("cnt", "todos")
        if chave in self._memo:
            return self._memo[chave]
        cnt = {c: [0] * (self.n_bolas(c) + 1) for c in self.CORES}
        for _, dezenas in self.serie:
            perfil = self.perfil_dezenas(dezenas)
            for c, q in perfil.items():
                cnt[c][q] += 1
        self._memo[chave] = cnt
        return cnt

    def frequencias(self) -> Dict[str, Any]:
        """Distribuição real × teórica por cor, com razão e última ocorrência."""
        chave = self._chave_memo("freq", "todos")
        if chave in self._memo:
            return self._memo[chave]
        cnt = self._contagens()
        n = self.n()
        tabelas = {}
        for c in self.CORES:
            n_c = self.n_bolas(c)
            linhas = []
            for k in range(n_c + 1):
                real = int(cnt[c][k])
                teor = self.p_teorica(c, k)
                linhas.append({
                    "k": k, "vezes": real,
                    "frequencia": round(real / n, 4) if n else 0.0,
                    "teorico": round(teor, 4),
                    "razao": round((real / n) / teor, 3) if n and teor else None,
                })
            apareceu = n - int(cnt[c][0])
            tabelas[c] = {
                "grupo": GRUPO_COR[c],
                "n_bolas": n_c,
                "dezenas": list(DEZENAS_COR[c]),
                "tabela": linhas,
                "esperado": round(self.esperado_teorico(c), 4),
                "aparecer_real": round(apareceu / n, 4) if n else 0.0,
                "aparecer_teorico": round(self.p_aparecer_teorica(c), 4),
                "forte_real": round((n - int(cnt[c][0]) - int(cnt[c][1])) / n, 4)
                              if n else 0.0,
                "forte_teorico": round(self.p_forte_teorica(c), 4),
                "ultimo_concurso": (max((co for co, dz in self.serie
                                         if self.perfil_dezenas(dz).get(c, 0) > 0),
                                        default=None) if n else None),
            }
        res = {"n": n, "por_cor": tabelas}
        self._memo[chave] = res
        return res

    def _dominantes(self) -> List[Tuple[int, str]]:
        """Série (concurso, cor dominante) com a regra de desempate oficial."""
        chave = self._chave_memo("dom", "todos")
        if chave in self._memo:
            return self._memo[chave]
        res = [(int(c), self.dominante_de(self.perfil_dezenas(dz)))
               for c, dz in self.serie]
        self._memo[chave] = res
        return res

    def streaks(self) -> Dict[str, Any]:
        """Streaks da cor dominante: sequência atual, recorde, por cor."""
        chave = self._chave_memo("streaks", "todos")
        if chave in self._memo:
            return self._memo[chave]
        doms = self._dominantes()
        runs: List[Dict[str, Any]] = []
        for concurso, cor in doms:
            if runs and runs[-1]["cor"] == cor:
                runs[-1]["fim"] = concurso
                runs[-1]["comprimento"] += 1
            else:
                runs.append({"cor": cor, "inicio": concurso, "fim": concurso,
                             "comprimento": 1})
        por = {c: {"atual": 0, "maximo": 0, "maximo_inicio": None,
                   "maximo_fim": None, "ultimo_concurso": None,
                   "concursos_desde_ultima": None}
               for c in self.CORES}
        for r in runs:
            info = por.get(r["cor"])
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
            por[atual["cor"]]["atual"] = atual["comprimento"]
            indice = {c: i for i, (c, _) in enumerate(doms)}
            fim = len(doms) - 1
            for info in por.values():
                pos = indice.get(info["ultimo_concurso"])
                if pos is not None:
                    info["concursos_desde_ultima"] = fim - pos
            maior = max(runs, key=lambda r: r["comprimento"])
        res = {
            "rotulo": "cor dominante do sorteio (mais bolas; empate pela ordem oficial)",
            "n_registros": len(doms),
            "run_atual": ({"cor": atual["cor"],
                           "comprimento": atual["comprimento"],
                           "inicio": atual["inicio"]} if atual else None),
            "recorde_historico": ({"cor": maior["cor"],
                                   "comprimento": maior["comprimento"],
                                   "inicio": maior["inicio"],
                                   "fim": maior["fim"]} if maior else None),
            "distribuicao_streaks": {str(int(k)): int(v) for k, v in
                                     Counter(r["comprimento"]
                                             for r in runs).items()},
            "por_cor": por,
        }
        self._memo[chave] = res
        return res

    @classmethod
    def baseline_dominancia(cls) -> Dict[str, Any]:
        """Margem teórica da regra 'repetir a cor dominante', por simulação.

        Simula 40.000 sorteios independentes de 15 bolas entre 25 (semente
        fixa, regra de desempate idêntica à série real) e mede a distribuição
        da cor dominante. Sob independência, P(dominante repete) = Σ_c p_c².
        """
        global _BASELINE_DOMINANCIA_CACHE
        if _BASELINE_DOMINANCIA_CACHE is None:
            rng = np.random.default_rng(20260831)
            n_sim = 40000
            amostras = (rng.random((n_sim, cls.TOTAL)).argsort(axis=1)[:, :cls.TAM_ORDEM]
                        + 1)
            idx_cores = np.array([cls.CORES.index(cls.COR_DEZENA[d])
                                  for d in range(1, cls.TOTAL + 1)], dtype=np.int16)
            dominantes = np.empty(n_sim, dtype=np.int8)
            for i in range(n_sim):
                cnt = np.bincount(idx_cores[amostras[i] - 1],
                                  minlength=len(cls.CORES))
                dominantes[i] = int(np.argmax(cnt))  # 1ª ocorrência = ordem oficial
            dist = np.bincount(dominantes, minlength=len(cls.CORES)) / n_sim
            _BASELINE_DOMINANCIA_CACHE = {
                "n_sim": n_sim, "semente": 20260831,
                "distribuicao": {cls.CORES[i]: round(float(dist[i]), 5)
                                 for i in range(len(cls.CORES))},
                "repeticao_teorica": round(float(np.sum(dist * dist)), 5),
            }
        return _BASELINE_DOMINANCIA_CACHE

    def taxa_repeticao_dominancia(self) -> Dict[str, Any]:
        """P(dominante de t+1 = dominante de t) medida × margem simulada."""
        chave = self._chave_memo("repeticao", "todos")
        if chave in self._memo:
            return self._memo[chave]
        doms = [c for _, c in self._dominantes()]
        n = len(doms) - 1
        if n <= 0:
            res = {"aplicavel": False, "n": 0}
            self._memo[chave] = res
            return res
        reps = sum(1 for i in range(1, len(doms)) if doms[i] == doms[i - 1])
        base = self.baseline_dominancia()["repeticao_teorica"]
        por_cor = {}
        for c in self.CORES[:6]:
            trans = sum(1 for i in range(1, len(doms)) if doms[i - 1] == c)
            repet = sum(1 for i in range(1, len(doms))
                        if doms[i - 1] == c and doms[i] == c)
            if trans:
                por_cor[c] = {"transicoes": trans, "repetiu": repet,
                              "taxa_real": round(repet / trans, 4)}
        res = {
            "aplicavel": True, "n_transicoes": n,
            "global": {"repeticoes": int(reps), "taxa": round(reps / n, 4),
                       "taxa_esperada": round(base, 4),
                       "p_valor": round(_binom_p(reps, n, base), 4)},
            "por_cor": por_cor,
            "leitura": ("a repetição da cor dominante coincide com a margem: "
                        "sequência não altera probabilidade"
                        if abs(reps / n - base) < 0.03 else
                        "desvio da margem na amostra — sem efeito operacional "
                        "sem significância"),
        }
        self._memo[chave] = res
        return res

    def repeticao_apos_streak(self, cor: str, streak_min: int = 2) -> Dict[str, Any]:
        """P(essa cor dominar de novo | ela dominou `streak_min`x seguidas)."""
        doms = [c for _, c in self._dominantes()]
        cor = str(cor)
        streak_min = int(streak_min)
        tot = rep = 0
        corrente = 1
        for i in range(1, len(doms)):
            repetiu = doms[i] == doms[i - 1]
            if doms[i - 1] == cor and corrente >= streak_min:
                tot += 1
                if repetiu:
                    rep += 1
            corrente = corrente + 1 if repetiu else 1
        base = self.baseline_dominancia()["repeticao_teorica"]
        taxa = rep / tot if tot else None
        if tot and taxa is not None and abs(taxa - base) < 0.03:
            leitura = ("a repetição seguiu a margem — streak não altera "
                       "probabilidade")
        elif tot:
            leitura = "amostra pequena: vale a taxa da margem"
        else:
            leitura = "sem provas no histórico: vale a taxa da margem"
        return {"cor": cor, "streak_min": streak_min, "provas": tot,
                "repetiu": rep,
                "taxa_real": round(taxa, 4) if tot else None,
                "taxa_esperada": round(base, 4), "leitura": leitura}

    # ------------------------------------------------------------
    # posterior do próximo sorteio (margem + o que a base mostrou)
    # ------------------------------------------------------------
    def posterior_contagem(self, cor: str) -> Dict[int, float]:
        """Posterior da contagem k da cor no próximo sorteio, com shrinkage.

        w = n/(n+200); post = w·empírica + (1−w)·hipergeométrica exata.
        """
        cnt = self._contagens()[cor]
        n = self.n()
        k_max = len(cnt) - 1
        teor = [self.p_teorica(cor, k) for k in range(k_max + 1)]
        w = n / (n + self.MARGEM_MISTURA) if n else 0.0
        return {k: w * (cnt[k] / n if n else 0.0) + (1.0 - w) * teor[k]
                for k in range(k_max + 1)}

    def esperado(self, cor: str) -> float:
        """E[bolas da cor no próximo sorteio] sob a posterior aprendida."""
        return float(sum(k * p for k, p in self.posterior_contagem(cor).items()))

    def ranking_cores(self) -> List[Dict[str, Any]]:
        """Cores mais prováveis de APARECER no próximo sorteio (P(k≥1))."""
        cnt = self._contagens()
        n = self.n()
        probs = {c: 1.0 - self.posterior_contagem(c).get(0, 0.0)
                 for c in self.CORES}
        ordem = sorted(self.CORES, key=lambda c: probs[c], reverse=True)
        out = []
        for pos, c in enumerate(ordem[:5], 1):
            out.append({"posicao": pos, "cor": c,
                        "nome": CORES_EXIBICAO[c],
                        "grupo": GRUPO_COR[c],
                        "prob": round(probs[c], 5),
                        "prob_teorica": round(self.p_aparecer_teorica(c), 5),
                        "vezes_na_base": int(n - cnt[c][0])})
        return out

    def ranking_fortes(self) -> List[Dict[str, Any]]:
        """Cores mais prováveis de vir FORTES (2+ bolas) no próximo sorteio."""
        probs = {c: sum(p for k, p in self.posterior_contagem(c).items()
                        if k >= 2) for c in self.CORES}
        ordem = sorted(self.CORES, key=lambda c: probs[c], reverse=True)
        out = []
        for pos, c in enumerate(ordem[:5], 1):
            out.append({"posicao": pos, "cor": c,
                        "nome": CORES_EXIBICAO[c],
                        "grupo": GRUPO_COR[c],
                        "prob": round(probs[c], 5),
                        "prob_teorica": round(self.p_forte_teorica(c), 5)})
        return out

    def palpite(self) -> Dict[str, Any]:
        """Palpite de cores para o próximo concurso + pergunta decisiva."""
        probs = {c: 1.0 - self.posterior_contagem(c).get(0, 0.0)
                 for c in self.CORES}
        fortes = {c: sum(p for k, p in self.posterior_contagem(c).items()
                         if k >= 2) for c in self.CORES}
        ranking = sorted(self.CORES, key=lambda c: probs[c], reverse=True)
        ranking_fortes = sorted(self.CORES, key=lambda c: fortes[c],
                                reverse=True)
        st = self.streaks()
        run = st["run_atual"]
        atual = run["cor"] if run else None
        tam = run["comprimento"] if run else 0
        medida = (self.repeticao_apos_streak(atual, tam)
                  if atual is not None and tam >= 2 else None)
        cnt = self._contagens()
        n = self.n()
        return {
            "n_registros": n,
            "probabilidades": {c: round(p, 5) for c, p in probs.items()},
            "probabilidades_fortes": {c: round(p, 5) for c, p in fortes.items()},
            "ranking": self.ranking_cores(),
            "ranking_fortes": self.ranking_fortes(),
            "proximo_palpite_top3": list(ranking[:3]),
            "proximo_palpite_forte_top3": list(ranking_fortes[:3]),
            "dominante_atual": ({"cor": atual, "streak": tam,
                                 "desde_o_concurso": run["inicio"]}
                                if run else None),
            "pergunta_decisiva": {
                "descricao": (("a cor dominante {} veio {}x seguidas: vale "
                              "excluí-la e apostar nas outras?").format(
                                  CORES_EXIBICAO.get(atual, atual), tam)
                              if atual is not None else
                              "sem streak de dominância ativo"),
                "excluida": atual,
                "candidatas_sem_excluir": list(ranking[:3]),
                "candidatas_se_excluir": [c for c in ranking if c != atual][:2],
                "p_repetir_a_atual": (round(probs.get(atual, 0.0), 5)
                                      if atual is not None else None),
                "medicao_no_historico": medida,
                "veredito_operacional": (
                    "NAO EXCLUIR: a repetição medida coincide com a margem e "
                    "o placar walk-forward mostra perda ao excluir"
                    if medida else
                    "streak inativo: seguir o ranking da margem"),
            },
        }

    # ------------------------------------------------------------
    # placar walk-forward (sem vazamento) e auto-auditoria
    # ------------------------------------------------------------
    def _walkforward(self) -> Dict[str, Any]:
        """Prevê t+1 só com o que existia antes de t (cores, sem vazamento)."""
        chave = self._chave_memo("wf", "todos")
        if chave in self._memo:
            return self._memo[chave]
        s = self.serie
        n = len(s)
        cnt = {c: [0] * (self.n_bolas(c) + 1) for c in self.CORES}
        doms = [c for _, c in self._dominantes()]
        r_top = r_forte = r_dom = provas = 0
        for i in range(n - 1):
            if i > 0:  # já existe passado antes de t
                probs = {c: 1.0 - self._posterior_de(cnt[c], c).get(0, 0.0)
                         for c in self.CORES}
                fortes = {c: sum(p for k, p in
                                 self._posterior_de(cnt[c], c).items()
                                 if k >= 2) for c in self.CORES}
                ranking = sorted(self.CORES, key=lambda c: probs[c],
                                 reverse=True)
                rk_forte = sorted(self.CORES, key=lambda c: fortes[c],
                                  reverse=True)
                perfil = self.perfil_dezenas(s[i + 1][1])
                presentes = [c for c, q in perfil.items() if q > 0]
                fortes_real = [c for c, q in perfil.items() if q >= 2]
                if ranking[0] in presentes:
                    r_top += 1
                if rk_forte[0] in fortes_real:
                    r_forte += 1
                if doms[i + 1] == doms[i]:
                    r_dom += 1
                provas += 1
            # aprende o concurso i para o futuro
            perfil = self.perfil_dezenas(s[i][1])
            for c, q in perfil.items():
                cnt[c][q] += 1
        res = {"n_provas": provas, "acertos_top1": r_top,
               "acertos_forte": r_forte, "acertos_repeticao_dominante": r_dom}
        self._memo[chave] = res
        return res

    def _posterior_de(self, cnt: List[int], cor: str) -> Dict[int, float]:
        """Posterior a partir de contagens acumuladas parciais (walk-forward)."""
        n_parcial = sum(cnt)
        k_max = len(cnt) - 1
        teor = [self.p_teorica(cor, k) for k in range(k_max + 1)]
        w = n_parcial / (n_parcial + self.MARGEM_MISTURA) if n_parcial else 0.0
        return {k: w * (cnt[k] / n_parcial if n_parcial else 0.0)
                + (1.0 - w) * teor[k] for k in range(k_max + 1)}

    def placar_walkforward(self) -> Dict[str, Any]:
        """Placar fora-da-amostra das três regras de cor vs margens teóricas."""
        if self.n() < 50:
            return {"aplicavel": False, "motivo": "dados insuficientes",
                    "n_registros": self.n()}
        wf = self._walkforward()
        provas = wf["n_provas"]
        teto1 = max(self.p_aparecer_teorica(c) for c in self.CORES)
        teto_forte = max(self.p_forte_teorica(c) for c in self.CORES)
        teto_dom = self.baseline_dominancia()["repeticao_teorica"]
        r_top, r_forte, r_dom = (wf["acertos_top1"], wf["acertos_forte"],
                                 wf["acertos_repeticao_dominante"])
        return {
            "aplicavel": True, "n_provas": provas,
            "margem_da_magna_top1": {
                "acertos": r_top, "taxa": round(r_top / provas, 4),
                "teto_teorico": round(teto1, 4),
                "leitura": "P(a cor mais provável aparecer) já é 94,8% por "
                           "construção: o teto é a própria margem"},
            "cor_forte_top1": {
                "acertos": r_forte, "taxa": round(r_forte / provas, 4),
                "teto_teorico": round(teto_forte, 4),
                "leitura": "cor forte (2+ bolas): teto teórico 65,4%"},
            "regra_popular_da_repeticao": {
                "acertos": r_dom, "taxa": round(r_dom / provas, 4),
                "teto_teorico": round(teto_dom, 4),
                "leitura": "repetir a cor dominante do sorteio anterior: "
                           "margem estimada por simulação (semente fixa)"},
            "leitura": ("{} provas fora-da-amostra: a Magna acerta {}% da cor "
                        "mais provável (teto {}%); a cor forte fica em {}% "
                        "(teto {}%); repetir a dominante fica em {}% "
                        "(margem {}%)".format(
                            provas, round(100 * r_top / provas, 1),
                            round(100 * teto1, 1),
                            round(100 * r_forte / provas, 1),
                            round(100 * teto_forte, 1),
                            round(100 * r_dom / provas, 1),
                            round(100 * teto_dom, 1))),
        }

    def auto_auditoria(self, min_registros: int = 30) -> Dict[str, Any]:
        """Existe algo ALÉM da margem nas cores? Medido fora-da-amostra."""
        chave = self._chave_memo("auto", "todos")
        if chave in self._memo:
            return self._memo[chave]
        if self.n() < min_registros + 1:
            res = {"aplicavel": False, "motivo": "dados insuficientes",
                   "n_registros": self.n(), "fator_confianca": 0.5,
                   "veredito": "SEM AMOSTRA"}
            self._memo[chave] = res
            return res
        wf = self._walkforward()
        provas = wf["n_provas"]
        acertos = wf["acertos_top1"]
        base = max(self.p_aparecer_teorica(c) for c in self.CORES)
        taxa = acertos / provas if provas else 0.0
        lift = taxa / base if base else 1.0
        p = round(_binom_p(acertos, provas, base), 4) if provas else 1.0
        real = bool(provas >= 50 and p < 0.05 and lift > 1.02)
        fator = (round(0.75 + 0.25 * min(1.0, max(0.0, (lift - 1.0) / 0.10)), 4)
                 if real else 0.5)
        res = {
            "aplicavel": True, "palpite_top_m": 1,
            "n_provas": provas, "acertos": int(acertos),
            "taxa": round(taxa, 4), "linha_de_base": round(base, 4),
            "lift": round(lift, 4), "p_valor": p,
            "veredito": "REAL" if real else "RUÍDO",
            "fator_confianca": fator,
            "leitura": ("a distribuição de cores superou a margem "
                        "hipergeométrica fora-da-amostra: entra com confiança "
                        "alta no consenso" if real else
                        "nenhum padrão de cor superou a margem hipergeométrica: "
                        "o vetor entra atenuado (0,5) e a leitura é publicada "
                        "como conhecimento, não como promessa"),
        }
        self._memo[chave] = res
        return res

    # ------------------------------------------------------------
    # entrega ao consenso da Magna
    # ------------------------------------------------------------
    def vetor_bruto(self) -> np.ndarray:
        """Vetor 25-dim (soma 1): cada dezena pesa E[bolas da sua cor]/n_cor.

        Sob a margem teórica pura, E[G1]/3 = 1,8/3 = 0,6 e E[G2]/2 = 1,2/2 =
        0,6 → o vetor é EXATAMENTE uniforme. Ele só inclina quando a base
        mostra desvio real de cores — e a auto-auditoria decide o quanto
        confiar nesse desvio.
        """
        v = np.zeros(self.TOTAL, dtype=float)
        for d in range(1, self.TOTAL + 1):
            c = self.COR_DEZENA[d]
            v[d - 1] = self.esperado(c) / self.n_bolas(c)
        v = v + 1.0 / self.TOTAL          # piso: nenhuma dezena zerada
        return v / v.sum()

    def pesos_de_evidencia(self) -> Dict[str, float]:
        """Peso da evidência medida (proporcional ao que o órgão já viu)."""
        n_provas = max(0, self.n() - 1)
        peso = n_provas / (n_provas + 150.0) if n_provas else 0.0
        return {"perfil": round(peso, 4) or 0.5}

    def fator_confianca(self) -> float:
        return float(self.auto_auditoria().get("fator_confianca", 0.5))

    def vetor_evidencia(self) -> np.ndarray:
        """Vetor de cores para o consenso (canal único: o perfil medido).

        Quem mistura com o uniforme é a Magna, usando `fator_confianca()` —
        a mesma disciplina aplicada à abertura, clima e INMET.
        """
        return self.vetor_bruto()

    # ------------------------------------------------------------
    # julgamento do próprio palpite (memória do que a Magna previu)
    # ------------------------------------------------------------
    @staticmethod
    def avaliar_palpite(ranking: Sequence[str],
                        perfil: Dict[str, int],
                        ranking_fortes: Optional[Sequence[str]] = None
                        ) -> Dict[str, Any]:
        """Como o palpite de cores se saiu contra o perfil real do sorteio.

        acerto_top1: a cor mais provável de aparecer apareceu;
        acerto_top2/top3: ao menos uma das top 2/3 apareceu;
        acerto_forte: a cor mais provável de vir forte veio com 2+ bolas;
        posicao_no_ranking: onde caiu a cor dominante real.
        """
        ordem = [str(c) for c in ranking]
        presentes = [c for c, q in (perfil or {}).items() if q > 0]
        dominante = AcervoCorMagna.dominante_de(perfil or {})
        pos = ordem.index(dominante) + 1 if dominante in ordem else None
        acerto_forte = None
        if ranking_fortes:
            acerto_forte = bool(str(ranking_fortes[0]) in
                                [c for c, q in (perfil or {}).items() if q >= 2])
        return {"dominante_real": dominante, "posicao_no_ranking": pos,
                "acerto_top1": bool(ordem and ordem[0] in presentes),
                "acerto_top2": bool(len(ordem) >= 2 and
                                    (ordem[0] in presentes or
                                     ordem[1] in presentes)),
                "acerto_top3": bool(ordem and
                                    any(c in presentes for c in ordem[:3])),
                "acerto_forte": acerto_forte}

    def afinidade_cartela(self, dezenas: Sequence[int]) -> Dict[str, Any]:
        """Quão coerente com o perfil de cores aprendido esta cartela é.

        A cartela tem 15 dezenas → um perfil de cores válido. Sob o
        conhecimento memorizado, cartelas cujo perfil é típico (perto do
        modal) são estruturalmente plausíveis. É critério de PLAUSIBILIDADE
        ESTRUTURAL (desempate), nunca preditivo: a chance de 13/14/15 pontos
        não muda.
        """
        perfil = self.perfil_dezenas(dezenas)
        score = 0.0
        modal = 0.0
        for c in self.CORES:
            post = self.posterior_contagem(c)
            k = int(perfil.get(c, 0))
            score += math.log(post.get(k, 1e-9) + 1e-12)
            km = max(post, key=post.get)
            modal += math.log(post.get(km, 1e-9) + 1e-12)
        afin = math.exp(score - modal) if modal else 0.0
        palpite = self.palpite()
        return {
            "perfil_da_cartela": perfil,
            "cor_dominante_da_cartela": self.dominante_de(perfil),
            "probabilidade_do_perfil": round(math.exp(score), 8),
            "afinidade": round(min(1.0, float(afin)), 4),
            "cobre_palpite_da_magna": (self.dominante_de(perfil) in
                                       palpite["proximo_palpite_top3"]),
        }

    # ------------------------------------------------------------
    # sínteses
    # ------------------------------------------------------------
    def veredito(self) -> str:
        auto = self.auto_auditoria()
        if not auto.get("aplicavel"):
            return "SEM AMOSTRA"
        return "REAL" if auto.get("veredito") == "REAL" else "RUÍDO"

    def digest(self) -> str:
        """Hash do que foi aprendido — cada decisão cita exatamente o acervo."""
        chave = self._chave_memo("digest", "todos")
        if chave in self._memo:
            return self._memo[chave]
        h = hashlib.sha256()
        s = self.serie
        h.update("cor|{}|".format(len(s)).encode())
        if s:
            h.update("{}:{}|".format(s[0][0], s[-1][0]).encode())
            cnt = self._contagens()
            h.update(str({c: tuple(cnt[c]) for c in self.CORES}).encode())
        res = "sha256:" + h.hexdigest()[:16]
        self._memo[chave] = res
        return res

    def estado(self) -> Dict[str, Any]:
        """Resumo barato para status, log e cabeçalho da decisão."""
        st = self.streaks()
        run = st["run_atual"]
        return {
            "concursos_da_base": self.n(),
            "aprendido_ate_concurso": self.ultimo(),
            "dominante_atual": (run["cor"] if run else None),
            "streak_dominante_atual": (run["comprimento"] if run else 0),
            "palpite_top3": self.palpite()["proximo_palpite_top3"],
            "palpite_forte_top3": self.palpite()["proximo_palpite_forte_top3"],
            "veredito": self.veredito(),
            "fator_confianca": self.fator_confianca(),
            "digest": self.digest(),
        }

    def leitura(self) -> str:
        """A Magna interpretando o acervo de cores em uma frase operacional."""
        prev = self.palpite()
        auto = self.auto_auditoria()
        topo = prev.get("ranking") or []
        quem = " · ".join("{} ({:.1f}%)".format(
            CORES_EXIBICAO.get(t["cor"], t["cor"]), 100 * t["prob"])
            for t in topo[:3]) or "sem dados"
        st = self.streaks()
        run = st.get("run_atual")
        partes = [
            "cores mais prováveis de aparecer no próximo concurso: {} — "
            "medidas em {} concursos memorizados".format(quem, self.n()),
        ]
        if run:
            med = self.repeticao_apos_streak(run["cor"], run["comprimento"])
            frase = "cor dominante atual {} no {}º concurso seguido".format(
                CORES_EXIBICAO.get(run["cor"], run["cor"]),
                run["comprimento"])
            if med["provas"] and med["taxa_real"] is not None:
                frase += ("; P(repetir | streak {}) = {:.1%} em {} provas vs "
                          "{:.1%} da margem".format(
                              run["comprimento"], med["taxa_real"],
                              med["provas"], med["taxa_esperada"]))
            partes.append(frase)
        partes.append("auto-auditoria walk-forward {} (lift {} em {} provas) "
                      "→ fator de confiança {}".format(
                          auto.get("veredito"), auto.get("lift"),
                          auto.get("n_provas"), self.fator_confianca()))
        return ("A Magna leu as cores das bolas (tabela oficial — último "
                "dígito): " + "; ".join(partes) +
                ". Leitura estrutural: não muda a chance de nenhuma cartela.")

    def tabela(self, desde: Optional[int] = None, ate: Optional[int] = None,
               limite: int = 30) -> List[Dict[str, Any]]:
        """A tabela de cores por concurso (como a do MazuSoft), derivada das
        dezenas oficiais — últimas `limite` linhas do intervalo pedido."""
        linhas = []
        for concurso, dezenas in self.serie:
            if desde is not None and concurso < int(desde):
                continue
            if ate is not None and concurso > int(ate):
                continue
            perfil = self.perfil_dezenas(dezenas)
            linhas.append({
                "concurso": int(concurso),
                "dominante": self.dominante_de(perfil),
                "perfil": perfil,
                "ausentes": [c for c, q in perfil.items() if q == 0],
            })
        return linhas[-max(1, min(int(limite), 200)):]

    def relatorio(self) -> Dict[str, Any]:
        """Relatório completo do domínio de cores (memória + placar + leitura)."""
        freq = self.frequencias()
        st = self.streaks()
        rep = self.taxa_repeticao_dominancia()
        prev = self.palpite()
        return {
            "status": "ok",
            "identidade": ("Acervo de Cores das Bolas — órgão da "
                           "Inteligência Magna v11.8 (tabela oficial "
                           "MazuSoft)"),
            "fonte": "https://www.mazusoft.com.br/lotofacil/tabela-cor.php",
            "regra": ("a cor de cada bola é definida pelo último dígito: "
                      "Grupo 1 (3 dezenas) vermelha/amarela/verde/marrom/azul; "
                      "Grupo 2 (2 dezenas) rosa/preta/cinza/laranja/branca"),
            "n_registros": self.n(),
            "digest": self.digest(),
            "pesos_de_evidencia": self.pesos_de_evidencia(),
            "fator_confianca": self.fator_confianca(),
            "veredito": self.veredito(),
            "distribuicoes": freq["por_cor"],
            "baseline_dominancia": self.baseline_dominancia(),
            "streaks": st,
            "taxa_repeticao_dominancia": rep,
            "placar_walkforward": self.placar_walkforward(),
            "auto_auditoria": self.auto_auditoria(),
            "palpite": prev,
            "leitura": self.leitura(),
            "honestidade": (
                "As cores são uma propriedade determinística das dezenas "
                "(último dígito): a tabela por concurso é derivada da base "
                "oficial, não prevista. A distribuição de cores é enviesada "
                "por construção (Grupo 1 tem 3 bolas por cor, Grupo 2 tem 2) "
                "— por isso todas as análises são proporcionais à margem "
                "hipergeométrica. O acervo publica o placar walk-forward e "
                "atenua o próprio vetor quando o padrão não supera a margem "
                "fora-da-amostra; nenhuma garantia combinatória é tocada."),
        }
