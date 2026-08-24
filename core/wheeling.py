"""
====================================================================
MOTOR DE DESDOBRAMENTO COM COBERTURA GARANTIDA (LOTTERY WHEELING)
====================================================================
A via matematicamente viável para FORÇAR 13/14/15 pontos.

Princípio (covering design C(v,k,t)):
  Dado um grupo fechado de `v` dezenas (redução) que contém as 15
  sorteadas, um design de cobertura C(v,15,13) é um conjunto de jogos
  de 15 dezenas tal que QUALQUER subconjunto de 13 dezenas do grupo
  está contido em pelo menos um jogo. Logo, se as 15 sorteadas caírem
  dentro do grupo, é IMPOSSÍVEL não acertar 13 pontos.
====================================================================
"""

import itertools
import numpy as np
from math import comb
from config import (
    TOTAL_DEZENAS, DEZENAS_POR_JOGO, VALOR_APOSTA,
    PREMIOS_FIXOS, PREMIOS_RATEADOS_MEDIA,
)


class WheelEngine:
    """Design de cobertura C(v, k, t) sobre um grupo de dezenas."""

    def __init__(self, universo, k=DEZENAS_POR_JOGO, t=13):
        self.universo = sorted(int(d) for d in universo)
        self.v = len(self.universo)
        self.k = k
        self.t = t

    def gerar_cobertura(self, max_tickets=None, progresso=None):
        """
        Gera jogos de `k` dezenas cobrindo todos os C(v,t) subconjuntos.
        Retorna (tickets, cobertura_ratio, total_alvos).
        """
        v, k, t = self.v, self.k, self.t
        if v < k:
            return [self.universo[:k]], 0.0, 1

        alvos = list(itertools.combinations(self.universo, t))
        jogos = list(itertools.combinations(self.universo, k))

        alvo_idx = {a: i for i, a in enumerate(alvos)}

        jogos_alvos = []
        for j in jogos:
            jogos_alvos.append([alvo_idx[a] for a in itertools.combinations(j, t)])

        alvo_jogos = [[] for _ in range(len(alvos))]
        for ji, idxs in enumerate(jogos_alvos):
            for ai in idxs:
                alvo_jogos[ai].append(ji)

        coberto = [False] * len(alvos)
        uncovered_count = [len(idxs) for idxs in jogos_alvos]
        restante = len(alvos)
        selecionados = []

        while restante > 0:
            if max_tickets and len(selecionados) >= max_tickets:
                break

            melhor, melhor_c = -1, 0
            for ji in range(len(jogos)):
                if uncovered_count[ji] > melhor_c:
                    melhor_c = uncovered_count[ji]
                    melhor = ji
            if melhor < 0:
                break

            selecionados.append(list(jogos[melhor]))
            for ai in jogos_alvos[melhor]:
                if not coberto[ai]:
                    coberto[ai] = True
                    restante -= 1
                    for jj in alvo_jogos[ai]:
                        if jj != melhor and uncovered_count[jj] > 0:
                            uncovered_count[jj] -= 1
            uncovered_count[melhor] = 0

            if progresso and len(selecionados) % 50 == 0:
                progresso(len(selecionados), restante)

        cobertura = 1.0 - (restante / len(alvos)) if alvos else 1.0
        return selecionados, cobertura, len(alvos)

    def validar_garantia(self, tickets):
        """Confere se todo C(v,t) está contido em algum ticket."""
        t = self.t
        alvos = set(itertools.combinations(self.universo, t))
        cobertos = set()
        for tk in tickets:
            s = set(tk)
            for a in itertools.combinations(tk, t):
                cobertos.add(a)
        return len(cobertos & alvos) / len(alvos) if alvos else 0.0

    def avaliar_ev(self, tickets, n_sim=20000, seed=42):
        """
        Simula sorteios de 15 dentro do grupo e calcula o melhor acerto
        de cada sorteio contra os tickets. Retorna distribuição e EV.
        """
        rng = np.random.default_rng(seed)
        tickets_sets = [set(tk) for tk in tickets]
        hits = {i: 0 for i in range(16)}
        for _ in range(n_sim):
            sorteio = rng.choice(self.universo, size=15, replace=False)
            s = set(sorteio.tolist())
            melhor = max(len(tk & s) for tk in tickets_sets)
            hits[melhor] += 1

        premio_cond = 0.0
        for k, cnt in hits.items():
            if cnt == 0:
                continue
            p = cnt / n_sim
            if k in PREMIOS_FIXOS:
                premio_cond += p * PREMIOS_FIXOS[k]
            elif k == 14:
                premio_cond += p * PREMIOS_RATEADOS_MEDIA[14]
            elif k == 15:
                premio_cond += p * PREMIOS_RATEADOS_MEDIA[15]

        custo = len(tickets) * VALOR_APOSTA
        return {
            "n_sim": n_sim,
            "distribuicao": hits,
            "premio_esperado_condicional": round(premio_cond, 2),
            "custo_total": round(custo, 2),
            "ev_condicional": round(premio_cond - custo, 2),
        }

    def relatorio(self, max_tickets=None, n_sim=20000):
        tickets, cobertura, total_alvos = self.gerar_cobertura(max_tickets=max_tickets)

        p_reducao = comb(self.v, 15) / comb(TOTAL_DEZENAS, 15)
        premio_garantido = PREMIOS_FIXOS.get(self.t, 0) if self.t in PREMIOS_FIXOS else 0

        ev = self.avaliar_ev(tickets, n_sim=n_sim) if tickets else None

        custo = len(tickets) * VALOR_APOSTA
        ev_incond = 0.0
        if ev:
            ev_incond = p_reducao * ev["premio_esperado_condicional"] - custo

        return {
            "v": self.v,
            "k": self.k,
            "t": self.t,
            "universo": self.universo,
            "n_tickets": len(tickets),
            "tickets": tickets,
            "cobertura": round(cobertura, 6),
            "total_alvos": total_alvos,
            "garantia": (cobertura >= 1.0),
            "custo_total_R$": round(custo, 2),
            "premio_garantido_R$": premio_garantido,
            "p_reducao_certa": round(p_reducao, 6),
            "p_reducao_1_em": int(round(1 / p_reducao)) if p_reducao > 0 else None,
            "ev_condicional": ev["ev_condicional"] if ev else 0.0,
            "ev_incondicional_R$": round(ev_incond, 2),
            "distribuicao_acertos": ev["distribuicao"] if ev else None,
        }


def escolher_reducao(vetor_25, n_dezenas=18):
    """
    Monta a redução (grupo fechado) de N dezenas a partir de um vetor de
    pontuação de 25 posições (ex.: vetor combinado do Cérebro).
    """
    v = np.asarray(vetor_25, dtype=float)
    if v.shape[0] != 25:
        v = np.ones(25) / 25
    ranking = list(np.argsort(v)[::-1] + 1)
    return sorted(ranking[:n_dezenas])