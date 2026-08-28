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
