"""
============================================================
MOTOR HEAVYWEIGHT v11.0 — EXAUSÇÃO TOTAL DO ESPAÇO AMOSTRAL
============================================================
Avalia TODAS as 3.268.760 combinações da Lotofácil contra um
vetor de scores das 25 dezenas — sem amostragem, sem heurística.

v11 (auditoria Fase 3):
- Corrige bug de import (Tuple/List indefinidos) — módulo nem importava
- Não constrói mais uma matriz própria de 82 MB: reaproveita o cache
  de máscaras uint32 do core.wheeling (13 MB) e pontua via bits
- Sem dependência de torch: o caminho numpy com máscaras é rápido o
  suficiente (~1-2 s para ordenar o universo inteiro)

HONESTIDADE: ordenar o universo pelo vetor dos motores apenas ranqueia
uma opinião subjetiva sobre dezenas — as 3.268.760 combinações seguem
todas exatamente a mesma distribuição hipergeométrica de acertos.
"""
import time
from typing import List, Tuple

import numpy as np

from config import TOTAL_DEZENAS, DEZENAS_POR_JOGO
from .wheeling import MotorWheeling


class MotorExaustaoUniverso:
    """Avaliação exaustiva do universo C(25,15) via máscaras de bits."""

    def __init__(self):
        self.universo = MotorWheeling.universo()  # 3.268.760 máscaras uint32

    def avaliar_universo_completo(
        self,
        vetor_probabilidades_25: np.ndarray,
        pesos_penalidade_duplicatas: np.ndarray = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Pontua cada uma das 3.268.760 combinações como a soma dos scores
        das 15 dezenas que a compõem.

        Retorna:
        - indices_ordenados: índices dos jogos, do melhor para o pior
        - scores_ordenados: os scores correspondentes, em ordem decrescente
        """
        t0 = time.time()
        v = np.asarray(vetor_probabilidades_25, dtype=np.float32)
        if v.shape[0] != TOTAL_DEZENAS:
            raise ValueError("vetor deve ter 25 posições")

        scores = np.zeros(len(self.universo), dtype=np.float32)
        for d in range(TOTAL_DEZENAS):
            bits = ((self.universo >> np.uint32(d)) & np.uint32(1)).astype(np.float32)
            scores += bits * v[d]

        if pesos_penalidade_duplicatas is not None:
            scores *= np.asarray(pesos_penalidade_duplicatas, dtype=np.float32)

        indices_res = np.argsort(scores)[::-1]
        scores_res = scores[indices_res]
        print("[HEAVYWEIGHT] 3.268.760 jogos avaliados exaustivamente em {:.3f}s"
              .format(time.time() - t0))
        return indices_res, scores_res

    def obter_dezenas_por_indice(self, idx) -> List[int]:
        """Converte o índice do universo de volta para as 15 dezenas."""
        mask = int(self.universo[int(idx)])
        return [d + 1 for d in range(TOTAL_DEZENAS) if (mask >> d) & 1]

    def top_n(self, vetor_probabilidades_25: np.ndarray, n: int = 10):
        """Atalho: top-N combinações pelo vetor de scores."""
        idx, sc = self.avaliar_universo_completo(vetor_probabilidades_25)
        n = min(n, len(idx))
        return [
            {"dezenas": self.obter_dezenas_por_indice(i), "score": float(s)}
            for i, s in zip(idx[:n], sc[:n])
        ]
