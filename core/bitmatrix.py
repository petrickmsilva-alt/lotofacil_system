"""
============================================================
MATRIZ DE BITS - BITMASKING ENGINE
Converte dezenas em inteiros de 25 bits para operações
ultrarrápidas AND, OR, XOR
============================================================
"""
import numpy as np
from config import TOTAL_DEZENAS


class BitMatrix:

    def dezenas_para_bitmask(self, dezenas):
        """
        Converte lista de dezenas em bitmask de 25 bits.
        Dezena 1 = bit 0, Dezena 25 = bit 24
        Ex: [1,3,5] = ...10101 = 21
        """
        mask = 0
        for d in dezenas:
            mask |= (1 << (d - 1))
        return mask

    def bitmask_para_dezenas(self, mask):
        """Converte bitmask de volta para lista de dezenas"""
        dezenas = []
        for i in range(TOTAL_DEZENAS):
            if mask & (1 << i):
                dezenas.append(i + 1)
        return dezenas

    def contar_acertos(self, mask1, mask2):
        """
        Conta interseção entre dois bitmasks usando AND.
        Equivale a contar dezenas em comum.
        """
        intersecao = mask1 & mask2
        return bin(intersecao).count('1')

    def xor_diferenca(self, mask1, mask2):
        """Retorna as dezenas que diferem entre dois jogos"""
        diff = mask1 ^ mask2
        return bin(diff).count('1')

    def or_uniao(self, mask1, mask2):
        """Retorna a união de dois jogos"""
        return mask1 | mask2

    def cobertura_percentual(self, mask_jogo, mask_resultado):
        """
        Calcula % de cobertura do resultado pelo jogo.
        86.6% = 13 acertos (13/15)
        """
        acertos = self.contar_acertos(mask_jogo, mask_resultado)
        return (acertos / 15) * 100

    def string_binaria(self, mask):
        """Retorna string de 25 bits para visualização"""
        return format(mask, '025b')

    def matriz_historico(self, resultados):
        """
        Converte histórico completo em matriz numpy binária.
        Cada linha = concurso, cada coluna = dezena (1-25)
        """
        n = len(resultados)
        matriz = np.zeros((n, TOTAL_DEZENAS), dtype=np.int8)

        for i, r in enumerate(resultados):
            for j in range(TOTAL_DEZENAS):
                if r['bitmask'] & (1 << j):
                    matriz[i, j] = 1

        return matriz

    def cruzamento_massivo(self, jogo_mask, historico_masks):
        """
        Cruza um jogo contra todo o histórico usando operações de bits.
        Retorna distribuição de acertos.
        """
        distribuicao = {i: 0 for i in range(16)}
        for h_mask in historico_masks:
            acertos = self.contar_acertos(jogo_mask, h_mask)
            distribuicao[acertos] += 1
        return distribuicao

    def heatmap_frequencia(self, resultados, janela=None):
        """
        Gera mapa de calor de frequência das dezenas.
        janela: se definido, usa apenas os últimos N concursos
        """
        if janela:
            resultados = resultados[-janela:]

        freq = np.zeros(TOTAL_DEZENAS)
        for r in resultados:
            for i in range(TOTAL_DEZENAS):
                if r['bitmask'] & (1 << i):
                    freq[i] += 1

        # Normalizar para porcentagem
        total = len(resultados)
        if total > 0:
            freq = (freq / total) * 100

        return freq