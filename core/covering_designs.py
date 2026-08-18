"""
============================================================
MOTOR COMBINATÓRIO - COVERING DESIGNS
Matriz de Cobertura Mínima para garantir 13, 14 e 15 pontos
============================================================
"""
import numpy as np
from itertools import combinations
from config import DEZENAS_POR_JOGO, TOTAL_DEZENAS
from .bitmatrix import BitMatrix


class CoveringDesigns:

    def __init__(self):
        self.bitmatrix = BitMatrix()

    def gerar_cobertura_minima(self, dezenas_candidatas, min_acertos=13,
                               max_cartelas=20):
        """
        Dado um conjunto de dezenas candidatas (ex: 19-20 dezenas),
        gera o menor número de jogos de 15 que garantam
        min_acertos pontos se o resultado estiver dentro das candidatas.

        Algoritmo Greedy de Cobertura:
        1. Gera todas as combinações possíveis de 15 em N
        2. Seleciona iterativamente a que maximiza a cobertura
        """
        n = len(dezenas_candidatas)
        if n < DEZENAS_POR_JOGO:
            return [sorted(dezenas_candidatas[:DEZENAS_POR_JOGO])]

        if n > 22:
            # Para N muito grande, usar heurística
            return self._cobertura_heuristica(
                dezenas_candidatas, min_acertos, max_cartelas
            )

        # Gerar todas as combinações possíveis de 15 em N
        todas_combos = list(combinations(dezenas_candidatas, DEZENAS_POR_JOGO))

        # Converter para bitmasks
        masks_combos = []
        for combo in todas_combos:
            mask = self.bitmatrix.dezenas_para_bitmask(combo)
            masks_combos.append((combo, mask))

        # Gerar todos os possíveis resultados de 15 em N
        possiveis_resultados = list(combinations(dezenas_candidatas, DEZENAS_POR_JOGO))
        masks_resultados = []
        for res in possiveis_resultados:
            mask = self.bitmatrix.dezenas_para_bitmask(res)
            masks_resultados.append(mask)

        # Greedy: selecionar cartelas que maximizam cobertura
        cartelas_selecionadas = []
        resultados_cobertos = set()

        for _ in range(max_cartelas):
            melhor_combo = None
            melhor_cobertura = 0

            for combo, mask_combo in masks_combos:
                cobertura = 0
                for idx, mask_res in enumerate(masks_resultados):
                    if idx not in resultados_cobertos:
                        acertos = self.bitmatrix.contar_acertos(mask_combo, mask_res)
                        if acertos >= min_acertos:
                            cobertura += 1

                if cobertura > melhor_cobertura:
                    melhor_cobertura = cobertura
                    melhor_combo = combo

            if melhor_combo is None or melhor_cobertura == 0:
                break

            cartelas_selecionadas.append(sorted(melhor_combo))

            # Marcar resultados cobertos
            mask_sel = self.bitmatrix.dezenas_para_bitmask(melhor_combo)
            for idx, mask_res in enumerate(masks_resultados):
                acertos = self.bitmatrix.contar_acertos(mask_sel, mask_res)
                if acertos >= min_acertos:
                    resultados_cobertos.add(idx)

            if len(resultados_cobertos) == len(masks_resultados):
                break

        return cartelas_selecionadas

    def _cobertura_heuristica(self, dezenas_candidatas, min_acertos,
                               max_cartelas):
        """
        Para conjuntos grandes, usa heurística de espaçamento geométrico.
        """
        cartelas = []
        n = len(dezenas_candidatas)
        candidatas = sorted(dezenas_candidatas)

        # Estratégia: gerar cartelas com espaçamento controlado
        for i in range(max_cartelas):
            np.random.seed(i * 42 + 7)

            # Selecionar 15 dezenas com distribuição uniforme
            indices = np.linspace(0, n - 1, DEZENAS_POR_JOGO, dtype=int)

            # Adicionar ruído controlado
            ruido = np.random.randint(-1, 2, size=DEZENAS_POR_JOGO)
            indices = np.clip(indices + ruido, 0, n - 1)
            indices = np.unique(indices)

            while len(indices) < DEZENAS_POR_JOGO:
                faltam = DEZENAS_POR_JOGO - len(indices)
                extras = np.random.choice(
                    [j for j in range(n) if j not in indices],
                    size=min(faltam, n - len(indices)),
                    replace=False
                )
                indices = np.concatenate([indices, extras])

            indices = sorted(indices[:DEZENAS_POR_JOGO])
            cartela = [candidatas[int(j)] for j in indices]

            if len(cartela) == DEZENAS_POR_JOGO:
                cartelas.append(sorted(cartela))

        # Remover duplicatas
        cartelas_unicas = []
        seen = set()
        for c in cartelas:
            key = tuple(c)
            if key not in seen:
                seen.add(key)
                cartelas_unicas.append(c)

        return cartelas_unicas

    def validar_cobertura(self, cartelas, resultado_real):
        """
        Valida quantos acertos cada cartela tem contra o resultado real.
        """
        mask_real = self.bitmatrix.dezenas_para_bitmask(resultado_real)
        resultados = []

        for cartela in cartelas:
            mask_cartela = self.bitmatrix.dezenas_para_bitmask(cartela)
            acertos = self.bitmatrix.contar_acertos(mask_cartela, mask_real)
            resultados.append({
                'cartela': cartela,
                'acertos': acertos,
                'sucesso_13': acertos >= 13,
                'sucesso_14': acertos >= 14,
                'sucesso_15': acertos >= 15,
            })

        return resultados

    def calcular_cobertura_total(self, cartelas, dezenas_universo):
        """
        Calcula a cobertura total de um conjunto de cartelas
        sobre todos os possíveis resultados.
        """
        total_possiveis = 0
        cobertos_13 = 0
        cobertos_14 = 0
        cobertos_15 = 0

        for resultado in combinations(dezenas_universo, DEZENAS_POR_JOGO):
            total_possiveis += 1
            mask_res = self.bitmatrix.dezenas_para_bitmask(resultado)

            melhor_acerto = 0
            for cartela in cartelas:
                mask_cart = self.bitmatrix.dezenas_para_bitmask(cartela)
                acertos = self.bitmatrix.contar_acertos(mask_cart, mask_res)
                melhor_acerto = max(melhor_acerto, acertos)

            if melhor_acerto >= 13:
                cobertos_13 += 1
            if melhor_acerto >= 14:
                cobertos_14 += 1
            if melhor_acerto >= 15:
                cobertos_15 += 1

        return {
            'total_possiveis': total_possiveis,
            'cobertura_13': cobertos_13 / total_possiveis if total_possiveis else 0,
            'cobertura_14': cobertos_14 / total_possiveis if total_possiveis else 0,
            'cobertura_15': cobertos_15 / total_possiveis if total_possiveis else 0,
        }