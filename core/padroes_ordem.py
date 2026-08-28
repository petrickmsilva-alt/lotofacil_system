"""
============================================================
MOTOR DE PADRÕES DA ORDEM DE SORTEIO (v11.3 — ORDEM REAL)
============================================================
O banco histórico guardava somente as dezenas ORDENADAS (d1<d2<...<d15).
A "ordem de sorteio" real (1ª bola, 2ª bola, ...) nunca foi armazenada —
e é exatamente dela que nasce a lógica popular:

    "01, 02, 03 são as que mais saem no início do sorteio;
     se a mesma dezena repete no início, a chance de repetir
     de novo cai; veja o máximo de vezes que saiu seguidas."

Esta lógica do usuário foi IMPLEMENTADA AQUI e é avaliada com
honestidade matemática contra o histórico real:

    R1 — Frequência por posição (1ª bola, janela inicial de k bolas);
    R2 — Sequências (streaks): atual, máxima histórica, distribuição;
    R3 — Repetição condicional: P(repetir | já repetiu 1×, 2×, 3×);
    R4 — Regra de exclusão: excluir a 1ª bola anterior e escolher entre
         as demais (avaliada walk-forward contra a taxa do acaso 4%).

HONESTIDADE MATEMÁTICA (a regra da casa):
    Sob sorteio independente, P(1ª bola = d) = 1/25 = 4% para QUALQUER
    dezena d, sem memória do que saiu antes. Repetições duplas da 1ª
    bola acontecem em ~4% das transições (~151 vezes em 3.770 concursos)
    e triplas ~6 vezes — não são raridade, são acaso esperado.
    O motor MEDE o lift real (walk-forward, sem vazamento) e publica
    o veredito REAL/RUÍDO com p-valor binomial. O consenso da Magna
    usa o vetor com fator de confiança proporcional ao lift medido;
    nada aqui altera garantias combinatórias nem probabilidade marginal
    de uma cartela.

Dados: tabela `ordem_sorteio` (concurso, b1..b15). Preenchida por:
    - `python backfill_ordem.py`            (histórico completo, local)
    - sincronização do histórico            (concursos novos, automático)
    - POST /api/magna/ordem/ingestao        (manual, upsert idempotente)
"""
from __future__ import annotations

import os
import sqlite3
import threading
from collections import Counter
from math import comb
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from scipy.stats import binomtest

    def _binom_p(k: int, n: int, p: float) -> float:
        if n <= 0:
            return 1.0
        return float(binomtest(k, n, p).pvalue)
except Exception:  # pragma: no cover — fallback sem scipy
    from math import comb

    def _binom_p(k: int, n: int, p: float) -> float:
        if n <= 0:
            return 1.0
        # bicaudal exato via soma da PMF binomial
        def pmf(i):
            return comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
        esquerda = sum(pmf(i) for i in range(0, k + 1))
        direita = sum(pmf(i) for i in range(k, n + 1))
        return float(min(1.0, esquerda + direita))


TOTAL = 25
TAM_ORDEM = 15
TIO_INICIAL = (1, 2, 3)          # o trio popular citado na lógica do usuário
P_ACASO_PRIMEIRA = 1.0 / TOTAL   # 4% — taxa do acaso para qualquer dezena


def _validar_ordem(ordem: Sequence[int]) -> Tuple[int, ...]:
    """Exige exatamente 15 dezenas únicas no intervalo 1–25."""
    try:
        vals = tuple(int(d) for d in ordem)
    except (TypeError, ValueError):
        raise ValueError("ordem deve conter 15 inteiros 1–25")
    if len(vals) != TAM_ORDEM or len(set(vals)) != TAM_ORDEM or \
            any(d < 1 or d > TOTAL for d in vals):
        raise ValueError(
            "ordem inválida: preciso de 15 dezenas únicas 1–25, recebi {}"
            .format(list(vals)))
    return vals


class MotorOrdemSorteio:
    """Análise, previsão e auto-auditoria da ordem real das bolas.

    Pode operar sobre a tabela `ordem_sorteio` do banco (padrão) ou sobre
    uma lista em memória de tuplas (concurso, ordem) — usada nos testes.
    """

    def __init__(self, db_path: Optional[str] = None,
                 ordens: Optional[Sequence[Tuple[int, Sequence[int]]]] = None):
        self._lock = threading.RLock()
        self.db_path = db_path
        if ordens is not None:
            self.ordens: List[Tuple[int, Tuple[int, ...]]] = sorted(
                (int(c), _validar_ordem(o)) for c, o in ordens)
        else:
            self.ordens = self._carregar(db_path)
        self._b: List[int] = [o[1][0] for o in self.ordens]  # 1ª bola por concurso

    # ------------------------------------------------------------
    # Carga / persistência
    # ------------------------------------------------------------
    @staticmethod
    def _carregar(db_path: Optional[str]) -> List[Tuple[int, Tuple[int, ...]]]:
        if not db_path or not os.path.exists(db_path):
            return []
        try:
            conn = sqlite3.connect(db_path)
            cols = ", ".join("b{}".format(i) for i in range(1, TAM_ORDEM + 1))
            rows = conn.execute(
                "SELECT concurso, {} FROM ordem_sorteio "
                "ORDER BY concurso".format(cols)).fetchall()
            conn.close()
        except sqlite3.Error:
            return []
        return [(int(r[0]), tuple(int(x) for x in r[1:])) for r in rows]

    @property
    def n_registros(self) -> int:
        return len(self.ordens)

    def aprender(self, concurso: int, ordem: Sequence[int]) -> Dict[str, Any]:
        """Upsert idempotente de um sorteio (memória + banco)."""
        vals = _validar_ordem(ordem)
        concurso = int(concurso)
        if concurso < 1:
            raise ValueError("concurso inválido")
        with self._lock:
            existente = dict(self.ordens)
            ja_igual = existente.get(concurso) == vals
            existente[concurso] = vals
            self.ordens = sorted(existente.items())
            self._b = [o[1][0] for o in self.ordens]
            gravado = False
            if self.db_path:
                gravado = self._salvar_db(concurso, vals)
            return {
                "status": "ok",
                "concurso": concurso,
                "idempotente": ja_igual,
                "persistido": gravado,
                "n_registros": self.n_registros,
            }

    def _salvar_db(self, concurso: int, vals: Tuple[int, ...]) -> bool:
        if not self.db_path:
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            cols = ", ".join("b{}".format(i) for i in range(1, TAM_ORDEM + 1))
            ph = ", ".join("?" for _ in range(TAM_ORDEM + 1))
            conn.execute(
                "INSERT OR REPLACE INTO ordem_sorteio (concurso, {}) "
                "VALUES ({})".format(cols, ph),
                (concurso, *vals))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False

    # ------------------------------------------------------------
    # R1 — Frequências por posição
    # ------------------------------------------------------------
    def frequencia_posicao(self, posicao: int = 1) -> Dict[int, int]:
        if posicao < 1 or posicao > TAM_ORDEM:
            raise ValueError("posição 1–15")
        cnt = Counter(o[1][posicao - 1] for o in self.ordens)
        return {d: int(cnt.get(d, 0)) for d in range(1, TOTAL + 1)}

    def frequencia_janela_inicial(self, k: int = 3) -> Dict[int, int]:
        """Dezenas que aparecem dentro das k primeiras bolas (ex.: o trio 01/02/03)."""
        if k < 1 or k > TAM_ORDEM:
            raise ValueError("janela 1–15")
        cnt: Counter = Counter()
        for _, o in self.ordens:
            cnt.update(o[:k])
        return {d: int(cnt.get(d, 0)) for d in range(1, TOTAL + 1)}

    # ------------------------------------------------------------
    # R2 — Sequências (streaks) da 1ª bola
    # ------------------------------------------------------------
    def streaks_primeira_bola(self) -> Dict[int, Dict[str, Any]]:
        """Por dezena: streak atual, máxima histórica, última 1ª bola e lacuna."""
        info = {d: {"atual": 0, "maximo": 0, "ultimo_concurso": None,
                    "concursos_desde_ultima": None} for d in range(1, TOTAL + 1)}
        corrente_d, corrente_n = None, 0
        for idx, (concurso, _) in enumerate(self.ordens):
            d = self._b[idx]
            if d == corrente_d:
                corrente_n += 1
            else:
                corrente_d, corrente_n = d, 1
            registro = info[d]
            registro["maximo"] = max(registro["maximo"], corrente_n)
            registro["atual"] = corrente_n
            registro["ultimo_concurso"] = concurso
            for outro in range(1, TOTAL + 1):
                if outro != d:
                    info[outro]["atual"] = 0
                    if info[outro]["concursos_desde_ultima"] is not None:
                        info[outro]["concursos_desde_ultima"] += 1
            info[d]["concursos_desde_ultima"] = 0
        return info

    def max_streak_historico(self) -> Dict[str, Any]:
        """A maior sequência de repetição da 1ª bola em todo o histórico."""
        info = self.streaks_primeira_bola()
        d_max = max(range(1, TOTAL + 1), key=lambda d: info[d]["maximo"])
        return {
            "dezena": d_max,
            "comprimento": info[d_max]["maximo"],
            "por_dezena": {d: info[d]["maximo"] for d in range(1, TOTAL + 1)},
        }

    def distribuicao_streaks(self) -> Dict[int, int]:
        """Quantas vezes uma sequência de 1ª bola terminou com cada comprimento."""
        fim: Counter = Counter()
        corrente_d, corrente_n = None, 0
        for d in self._b:
            if d == corrente_d:
                corrente_n += 1
            else:
                if corrente_d is not None:
                    fim[corrente_n] += 1
                corrente_d, corrente_n = d, 1
        if corrente_d is not None:
            fim[corrente_n] += 1
        return {int(k): int(v) for k, v in sorted(fim.items())}

    # ------------------------------------------------------------
    # R3 — Repetição condicional
    # ------------------------------------------------------------
    def taxa_repeticao(self) -> Dict[str, Any]:
        """P(1ª bola t = 1ª bola t−1), global e condicional ao streak atual.

        Responde diretamente a lógica do usuário: "se repetiu 2×,
        a chance de repetir de novo é muito pequena?" — medida, não
        presumida. Sob acaso puro, TODAS ficam em 4%.
        """
        b = self._b
        n = len(b) - 1
        if n <= 0:
            return {"aplicavel": False, "n": 0}
        global_reps = sum(1 for i in range(1, len(b)) if b[i] == b[i - 1])
        cond: Dict[str, Dict[str, Any]] = {}
        for rotulo, run in (("apos_1", 1), ("apos_2", 2), ("apos_3_mais", 3)):
            # transição i → i+1, condicionada ao streak ATÉ i
            tot = rep = 0
            corrente = 1
            for i in range(1, len(b)):
                streak_antes = corrente
                repetiu = (b[i] == b[i - 1])
                pertence = (
                    (run == 3 and streak_antes >= 3) or
                    (run != 3 and streak_antes == run)
                )
                if pertence:
                    tot += 1
                    if repetiu:
                        rep += 1
                corrente = corrente + 1 if repetiu else 1
            cond[rotulo] = {
                "n": tot, "repeticoes": rep,
                "taxa": round(rep / tot, 4) if tot else None,
                "taxa_acaso": round(P_ACASO_PRIMEIRA, 4),
            }
        return {
            "aplicavel": True,
            "n_transicoes": n,
            "global": {
                "repeticoes": global_reps,
                "taxa": round(global_reps / n, 4),
                "taxa_acaso": round(P_ACASO_PRIMEIRA, 4),
                "p_valor": round(_binom_p(global_reps, n, P_ACASO_PRIMEIRA), 4),
            },
            "condicional": cond,
        }

    # ------------------------------------------------------------
    # R4 — Regra do usuário (exclusão da 1ª bola anterior)
    # ------------------------------------------------------------
    def placar_regra_exclusao(self) -> Dict[str, Any]:
        """Walk-forward da regra: 'a que acabou de sair no início não repete'.

        Mede com que frequência a 1ª bola excluída APESAR disso voltou.
        Se o sorteio é independente, a taxa observada ≈ 4% e a exclusão
        não tem valor preditivo (custa 1 dezena de busca, não ganha nada).
        """
        b = self._b
        n = len(b) - 1
        if n <= 0:
            return {"aplicavel": False, "n": 0}
        voltou = sum(1 for i in range(1, len(b)) if b[i] == b[i - 1])
        taxa = voltou / n
        p = _binom_p(voltou, n, P_ACASO_PRIMEIRA)
        if p < 0.05 and taxa < P_ACASO_PRIMEIRA:
            veredito = "SUPORTADO — exclusão reduz frequência real"
        else:
            veredito = "RUÍDO — a dezena excluída volta na taxa do acaso"
        return {
            "aplicavel": True,
            "n_transicoes": n,
            "voltou": voltou,
            "taxa_real": round(taxa, 4),
            "taxa_acaso": round(P_ACASO_PRIMEIRA, 4),
            "p_valor": round(p, 4),
            "veredito": veredito,
        }

    # ------------------------------------------------------------
    # Matriz de transição (qual das outras vai sair?)
    # ------------------------------------------------------------
    def matriz_transicao(self, suavizar: bool = True) -> np.ndarray:
        """P(prox 1ª bola = j | 1ª bola atual = i), 25×25, linha soma 1."""
        m = np.ones((TOTAL, TOTAL)) * (1.0 if suavizar else 0.0)  # prior Dirichlet(1)
        for i in range(1, len(self._b)):
            m[self._b[i - 1] - 1, self._b[i] - 1] += 1.0
        return m / m.sum(axis=1, keepdims=True)

    # ------------------------------------------------------------
    # Previsão (posterior bayesiana, sem vazamento)
    # ------------------------------------------------------------
    def previsao_primeira_bola(self) -> Dict[str, Any]:
        """Posterior Dirichlet(1)+frequências para a 1ª bola do próximo concurso.

        Inclui o painel do trio 01/02/03 e a leitura da regra do usuário:
        se a última 1ª bola é do trio, a recomendação ordena as DUAS
        restantes do trio pela posterior — com a taxa real de repetição
        ao lado, para decisão informada.
        """
        n = len(self._b)
        if n == 0:
            probs = {d: 1.0 / TOTAL for d in range(1, TOTAL + 1)}
        else:
            cnt = Counter(self._b)
            probs = {d: (cnt.get(d, 0) + 1.0) / (n + TOTAL)
                     for d in range(1, TOTAL + 1)}
        top5 = sorted(probs, key=lambda d: probs[d], reverse=True)[:5]
        ultima = self._b[-1] if self._b else None
        streaks = self.streaks_primeira_bola()
        trio = {d: {
            "prob_primeira_bola": round(probs[d], 5),
            "streak_atual": streaks[d]["atual"],
            "maximo_historico": streaks[d]["maximo"],
        } for d in TIO_INICIAL}
        candidatas = [d for d in sorted(TIO_INICIAL,
                                        key=lambda x: probs[x], reverse=True)
                      if d != ultima]
        return {
            "n_registros": n,
            "ultima_primeira_bola": ultima,
            "top5": [{"dezena": d, "prob": round(probs[d], 5)} for d in top5],
            "trio_01_02_03": trio,
            "regra_do_usuario": {
                "descricao": (
                    "Excluir a última 1ª bola e ordenar as restantes do "
                    "trio 01/02/03 pela posterior bayesiana"),
                "excluida": ultima,
                "candidatas_restantes": candidatas[:2],
                "prob_repetir_a_ultima": round(
                    probs[ultima], 5) if ultima else None,
                "nota_honesta": (
                    "Sob independência, repetir ou não repete a taxa de 4% — "
                    "veja taxa_repeticao() e placar_regra_exclusao()"),
            },
            "probabilidades": {str(d): round(p, 5) for d, p in probs.items()},
        }

    def vetor_preferencia(self) -> np.ndarray:
        """Vetor 25-dim (soma 1) para a fonte 'ordem' da Magna: posterior
        atenuada pela auto-auditoria walk-forward (nunca mais que o lift
        medido justifique)."""
        probs = self.previsao_primeira_bola()["probabilidades"]
        v = np.array([probs[str(d)] for d in range(1, TOTAL + 1)], dtype=float)
        fator = float(self.auto_ponderacao().get("fator_confianca", 0.5))
        uniforme = np.ones(TOTAL, dtype=float) / TOTAL
        atenuado = (1.0 - fator) * uniforme + fator * v
        s = atenuado.sum()
        return atenuado / s if s > 0 else uniforme

    # ------------------------------------------------------------
    # Auto-auditoria walk-forward (o detector de ilusão)
    # ------------------------------------------------------------
    def auto_ponderacao(self, min_registros: int = 30) -> Dict[str, Any]:
        """Um-passo-à-frente: o top-5 posterior acerta mais que 20% (acaso)?

        Sem vazamento: em cada passo t usa somente contagens até t−1.
        REAL exige p < 0.05 E lift > 1. fator_confianca ∈ [0.5, 1.0].
        """
        b = self._b
        n = len(b)
        if n < min_registros + 1:
            return {"aplicavel": False, "motivo": "dados insuficientes",
                    "n_registros": n, "fator_confianca": 0.5}
        acertos = 0
        cnt: Counter = Counter()
        for t in range(n - 1):
            probs = {d: (cnt.get(d, 0) + 1.0) / (t + TOTAL)
                     for d in range(1, TOTAL + 1)}
            top5 = set(sorted(probs, key=lambda d: probs[d],
                              reverse=True)[:5])
            if b[t + 1] in top5:
                acertos += 1
            cnt[b[t]] += 1
        provas = n - 1
        taxa = acertos / provas
        base = 5.0 / TOTAL
        lift = taxa / base
        p = _binom_p(acertos, provas, base)
        real = (p < 0.05) and (lift > 1.0)
        fator = 0.5 + 0.5 * max(0.0, min(1.0, (lift - 1.0) / 1.5))
        if not real:
            fator = 0.5  # máxima desconfiança, fonte nunca zerada
        return {
            "aplicavel": True,
            "n_provas": provas,
            "acertos_top5": acertos,
            "taxa_top5": round(taxa, 4),
            "taxa_acaso": round(base, 4),
            "lift": round(lift, 4),
            "p_valor": round(p, 4),
            "veredito": "REAL" if real else "RUÍDO",
            "fator_confianca": round(float(fator), 4),
        }

    # ------------------------------------------------------------
    # Relatório completo (API /api/magna/ordem)
    # ------------------------------------------------------------
    def relatorio(self) -> Dict[str, Any]:
        streaks = self.max_streak_historico()
        return {
            "status": "ok",
            "identidade": "Motor de Padrões da Ordem de Sorteio v11.3",
            "n_registros": self.n_registros,
            "dados_suficientes": self.n_registros >= 30,
            "frequencia_primeira_bola": self.frequencia_posicao(1),
            "frequencia_janela_inicial_3": self.frequencia_janela_inicial(3),
            "streak_maximo_historico": {
                "dezena": streaks["dezena"],
                "comprimento": streaks["comprimento"],
            },
            "distribuicao_streaks": self.distribuicao_streaks(),
            "taxa_repeticao": self.taxa_repeticao(),
            "placar_regra_exclusao": self.placar_regra_exclusao(),
            "previsao": self.previsao_primeira_bola(),
            "auto_auditoria": self.auto_ponderacao(),
            "honestidade": (
                "A ordem real das bolas é aleatória e independente entre "
                "concursos. Este motor mede cada regra popular contra o "
                "histórico e publica o placar; o peso na Magna é proporcional "
                "ao lift comprovado walk-forward."),
        }


class MotorPadroesMinimo:
    """Padrões da MENOR dezena do concurso — a lógica do 'início' na lista
    ordenada (a que os sites exibem).

    A lógica do usuário, formalizada e medida:
        "a 04 saiu no início pela última vez no 3676; depois o 01 saiu 6×
         seguidas; no 3683 o 02 assumiu; agora o 03 saiu 2× seguidas —
         a chance de repetir de novo é muito pequena; prever entre as outras"

    Diferença crucial para a 1ª bola física: a menor dezena NÃO é uniforme.
    P(menor = k) = C(25−k, 14) / C(25, 15):
        01 → 60,0% · 02 → 25,0% · 03 → 9,8% · 04 → 3,6% · 05+ → 1,6%
    Logo "prever o próximo início" É um problema preditivo real (top-1
    acerta ~60%, top-2 ~85%) — mas sob independência o melhor preditor
    possível é exatamente essa margem; streaks não adicionam nada.

    ARMADILHA DE COMPOSIÇÃO (o módulo evita):
        P(repetir | streak longo) AGREGADA cresce com o streak — não por
        causa, mas porque streaks longos são quase sempre do 01 (que
        repete 60% por natureza). A medição honesta é POR DEZENA:
        P(3º 03 | 03 duas vezes) = 4/42 ≈ 9,5% ≈ a margem de sempre 9,8%.
    """

    def __init__(self, db_path: Optional[str] = None,
                 serie: Optional[Sequence[Tuple[int, int]]] = None):
        self._lock = threading.RLock()
        if serie is not None:
            self.serie = sorted((int(c), int(m)) for c, m in serie)
        else:
            self.serie = self._carregar(db_path)

    @staticmethod
    def _carregar(db_path: Optional[str]) -> List[Tuple[int, int]]:
        if not db_path or not os.path.exists(db_path):
            return []
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT concurso, d1 FROM resultados ORDER BY concurso"
            ).fetchall()
            conn.close()
        except sqlite3.Error:
            return []
        return [(int(c), int(m)) for c, m in rows if 1 <= int(m) <= TOTAL]

    @property
    def n_registros(self) -> int:
        return len(self.serie)

    # ------------------------------------------------------------
    # Distribuição marginal (o melhor preditor sob independência)
    # ------------------------------------------------------------
    @staticmethod
    def p_menor_teorica(k: int) -> float:
        if k < 1 or k > TOTAL - 14:
            return 0.0
        return comb(25 - k, 14) / comb(25, 15)

    def frequencias_minimo(self) -> Dict[str, Any]:
        cnt = Counter(m for _, m in self.serie)
        n = self.n_registros
        tabela = []
        for k in range(1, 12):
            real = int(cnt.get(k, 0))
            teor = self.p_menor_teorica(k)
            tabela.append({
                "dezena": k, "vezes": real,
                "frequencia": round(real / n, 4) if n else 0.0,
                "teorico": round(teor, 4),
                "ultimo_concurso": max(
                    (c for c, m in self.serie if m == k), default=None),
            })
        return {"n": n, "tabela": tabela}

    # ------------------------------------------------------------
    # Streaks (sequências do mesmo 'início')
    # ------------------------------------------------------------
    def _runs(self) -> List[Dict[str, Any]]:
        """Runs consecutivos: [{dezena, inicio, fim, comprimento}]."""
        runs = []
        for concurso, dezena in self.serie:
            if runs and runs[-1]["dezena"] == dezena:
                runs[-1]["fim"] = concurso
                runs[-1]["comprimento"] += 1
            else:
                runs.append({"dezena": dezena, "inicio": concurso,
                             "fim": concurso, "comprimento": 1})
        return runs

    def streaks_minimo(self) -> Dict[str, Any]:
        runs = self._runs()
        por_dezena = {d: {"atual": 0, "maximo": 0, "maximo_inicio": None,
                          "maximo_fim": None, "ultimo_concurso": None}
                      for d in range(1, 12)}
        for r in runs:
            d = r["dezena"]
            info = por_dezena.get(d)
            if info is None:
                continue
            if r["comprimento"] > info["maximo"]:
                info["maximo"] = r["comprimento"]
                info["maximo_inicio"] = r["inicio"]
                info["maximo_fim"] = r["fim"]
            info["ultimo_concurso"] = r["fim"]
        if self.serie:
            ultimo_run = runs[-1]
            por_dezena[ultimo_run["dezena"]]["atual"] = \
                ultimo_run["comprimento"]
        maior = max(runs, key=lambda r: r["comprimento"]) if runs else None
        return {
            "run_atual": ({'dezena': ultimo_run['dezena'],
                           'comprimento': ultimo_run['comprimento'],
                           'inicio': ultimo_run['inicio']}
                          if self.serie else None),
            "streak_maximo_historico": (
                {"dezena": maior["dezena"], "comprimento": maior["comprimento"],
                 "inicio": maior["inicio"], "fim": maior["fim"]}
                if maior else None),
            "por_dezena": por_dezena,
        }

    # ------------------------------------------------------------
    # Repetição condicional — GLOBAL (sujeita à armadilha) e POR DEZENA
    # ------------------------------------------------------------
    def taxa_repeticao_minimo(self) -> Dict[str, Any]:
        m = [x[1] for x in self.serie]
        n = len(m) - 1
        if n <= 0:
            return {"aplicavel": False}
        reps = sum(1 for i in range(1, len(m)) if m[i] == m[i - 1])
        esperado = sum(self.p_menor_teorica(k) ** 2 for k in range(1, 26))
        por_dezena = {}
        for d in range(1, 8):
            transicoes = sum(1 for i in range(1, len(m))
                             if m[i - 1] == d)
            repetiu = sum(1 for i in range(1, len(m))
                          if m[i - 1] == d and m[i] == d)
            p_d = self.p_menor_teorica(d)
            if transicoes:
                por_dezena[str(d)] = {
                    "transicoes": transicoes, "repetiu": repetiu,
                    "taxa_real": round(repetiu / transicoes, 4),
                    "taxa_teorica": round(p_d, 4),
                }
        return {
            "aplicavel": True,
            "n_transicoes": n,
            "global": {
                "taxa_real": round(reps / n, 4),
                "taxa_esperada_soma_p2": round(esperado, 4),
            },
            "por_dezena": por_dezena,
        }

    def repeticao_apos_streak(self, dezena: int, streak_min: int = 2
                              ) -> Dict[str, Any]:
        """P(o mesmo início vir de novo | já veio `streak_min`× seguidas)
        medido APENAS na dezena pedida (sem mistura de composição)."""
        m = [x[1] for x in self.serie]
        tot = rep = 0
        corrente = 1
        for i in range(1, len(m)):
            repetiu = m[i] == m[i - 1]
            if m[i - 1] == dezena and corrente >= streak_min:
                tot += 1
                if repetiu:
                    rep += 1
            corrente = corrente + 1 if repetiu else 1
        p_d = self.p_menor_teorica(dezena)
        return {
            "dezena": dezena, "streak_min": streak_min,
            "provas": tot, "repetiu": rep,
            "taxa_real": round(rep / tot, 4) if tot else None,
            "taxa_teorica": round(p_d, 4),
            "leitura": (
                "A repetição segue a margem de sempre — streak não altera a "
                "probabilidade" if tot and abs(rep / tot - p_d) < 0.03
                else ("amostra pequena; taxa real observada" if tot else
                      "sem provas no histórico")),
        }

    # ------------------------------------------------------------
    # Previsão do próximo 'início' (a pergunta do usuário)
    # ------------------------------------------------------------
    def previsao_proximo_minimo(self) -> Dict[str, Any]:
        n = len(self.serie)
        cnt = Counter(m for _, m in self.serie)
        probs = {d: (cnt.get(d, 0) + 1.0) / (n + 11)
                 for d in range(1, 12)}
        top = sorted(probs, key=lambda d: probs[d], reverse=True)
        run_atual = self.streaks_minimo()["run_atual"]
        atual = run_atual["dezena"] if run_atual else None
        tam_atual = run_atual["comprimento"] if run_atual else 0
        candidatas = [d for d in top if d != atual]
        p_teorica_atual = self.p_menor_teorica(atual) if atual else None
        medida = (self.repeticao_apos_streak(atual, tam_atual)
                  if atual and tam_atual >= 2 else None)
        return {
            "n_registros": n,
            "run_atual": run_atual,
            "probabilidades": {str(d): round(probs[d], 4)
                               for d in range(1, 12)},
            "top3_proximo_inicio": top[:3],
            "regra_do_usuario": {
                "descricao": (
                    "excluir o início atual (streak {}) e ranquear os "
                    "demais pela posterior".format(tam_atual)),
                "excluida": atual,
                "streak_atual": tam_atual,
                "p_repetir_o_atual": {
                    "teorica": round(p_teorica_atual, 4)
                    if p_teorica_atual else None,
                    "medida_historica": medida,
                },
                "candidatas_restantes_top2": candidatas[:2],
            },
        }

    # ------------------------------------------------------------
    # Placar walk-forward das regras (sem vazamento)
    # ------------------------------------------------------------
    def placar_regras_walkforward(self) -> Dict[str, Any]:
        """Um-passo-à-frente em todo o histórico, usando somente o passado:
            R1 sempre-01 · R2 top-2 · R3 usuário (excluir atual se streak≥2)
        Contra os tetos teóricos da margem (60,0% / 85,3%)."""
        m = [x[1] for x in self.serie]
        if len(m) < 50:
            return {"aplicavel": False, "motivo": "dados insuficientes"}
        posterior: Counter = Counter()
        r1 = r2 = r3 = 0
        provas = 0
        corrente_d, corrente_n = None, 0
        for i in range(len(m) - 1):
            atual = m[i]
            proximo = m[i + 1]
            if posterior:
                n_passado = sum(posterior.values())
                probs = {d: (posterior.get(d, 0) + 1.0) / (n_passado + 11)
                         for d in range(1, 12)}
                melhor = max(probs, key=lambda d: probs[d])
                if melhor == proximo:
                    r1 += 1
                top2 = set(sorted(probs, key=lambda d: probs[d],
                                  reverse=True)[:2])
                if proximo in top2:
                    r2 += 1
                # regra do usuário: exclui o atual se streak ≥ 2
                if corrente_n >= 2:
                    cand = max((d for d in probs if d != atual),
                               key=lambda d: probs[d])
                else:
                    cand = melhor
                if cand == proximo:
                    r3 += 1
                provas += 1
            if atual == corrente_d:
                corrente_n += 1
            else:
                corrente_d, corrente_n = atual, 1
            posterior[atual] += 1
        t1 = self.p_menor_teorica(1)
        t2 = self.p_menor_teorica(1) + self.p_menor_teorica(2)
        return {
            "aplicavel": True,
            "n_provas": provas,
            "sempre_01": {"acertos": r1,
                          "taxa": round(r1 / provas, 4),
                          "teto_teorico": round(t1, 4)},
            "top2": {"acertos": r2,
                     "taxa": round(r2 / provas, 4),
                     "teto_teorico": round(t2, 4)},
            "regra_usuario": {"acertos": r3,
                              "taxa": round(r3 / provas, 4)},
            "leitura": (
                "Sob independência as três regras convergem ao teto da "
                "margem; streak não adiciona ganho mensurável."),
        }

    # ------------------------------------------------------------
    # Vetor de preferência para a fonte 'ordem' da Magna
    # ------------------------------------------------------------
    def vetor_preferencia_minimo(self) -> np.ndarray:
        n = len(self.serie)
        cnt = Counter(m for _, m in self.serie)
        probs = np.array(
            [(cnt.get(d, 0) + 1.0) / (n + 11) if d <= 11 else 0.0
             for d in range(1, TOTAL + 1)], dtype=float)
        # piso uniforme: nenhuma dezena zerada, simetria preservada nas altas
        probs = probs + (1.0 / TOTAL)
        s = probs.sum()
        probs /= s
        # fator de confiança: lift do preditor marginal vs teto (≈1 → 0.5)
        fator = 0.5
        uniforme = np.ones(TOTAL, dtype=float) / TOTAL
        atenuado = (1.0 - fator) * uniforme + fator * probs
        return atenuado / atenuado.sum()

    def auto_ponderacao(self, min_registros: int = 50) -> Dict[str, Any]:
        """O posterior um-passo-à-frente acerta o próximo 'início' perto do
        teto da margem (60%)? Aqui o teto JÁ É o melhor possível sob
        independência — lift mede se há algo ALÉM da margem."""
        m = [x[1] for x in self.serie]
        if len(m) < min_registros + 1:
            return {"aplicavel": False, "n_registros": len(m),
                    "fator_confianca": 0.5}
        posterior: Counter = Counter()
        acertos = provas = 0
        for i in range(len(m) - 1):
            if posterior:
                n_passado = sum(posterior.values())
                probs = {d: (posterior.get(d, 0) + 1.0) / (n_passado + 11)
                         for d in range(1, 12)}
                melhor = max(probs, key=lambda d: probs[d])
                if melhor == m[i + 1]:
                    acertos += 1
                provas += 1
            posterior[m[i]] += 1
        taxa = acertos / provas if provas else 0.0
        teto = self.p_menor_teorica(1)
        lift = taxa / teto if teto else 1.0
        p = _binom_p(acertos, provas, teto)
        real = (p < 0.05) and (lift > 1.02)
        return {
            "aplicavel": True, "n_provas": provas,
            "acertos": acertos, "taxa": round(taxa, 4),
            "teto_teorico": round(teto, 4), "lift": round(lift, 4),
            "p_valor": round(p, 4),
            "veredito": "REAL" if real else "RUÍDO",
            "fator_confianca": 0.75 if real else 0.5,
        }

    # ------------------------------------------------------------
    # Relatório
    # ------------------------------------------------------------
    def relatorio_minimo(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "identidade": "Padrões da Menor Dezena (início do concurso) v11.3",
            "n_registros": self.n_registros,
            "frequencias": self.frequencias_minimo(),
            "streaks": self.streaks_minimo(),
            "taxa_repeticao": self.taxa_repeticao_minimo(),
            "previsao": self.previsao_proximo_minimo(),
            "placar_walkforward": self.placar_regras_walkforward(),
            "auto_auditoria": self.auto_ponderacao(),
            "honestidade": (
                "A distribuição do 'início' é fortemente enviesada "
                "(01=60%, 02=25%, 03=9,8%) — prever o próximo início é um "
                "problema real que o sistema resolve com a margem. Streaks "
                "não alteram probabilidades: o placar walk-forward publica "
                "a medição a cada consulta."),
        }
