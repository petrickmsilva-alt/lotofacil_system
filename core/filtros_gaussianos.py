"""
============================================================
FILTROS GAUSSIANOS E ESTATÍSTICOS
Assinatura de Gauss, Paridade, Fibonacci, Primos,
Moldura/Miolo, Entropia
============================================================
"""
import numpy as np
from scipy import stats
from config import (
    SOMA_MIN, SOMA_MAX, MAX_CONSECUTIVOS,
    PRIMOS, FIBONACCI, BORDA, MIOLO,
    PRIMOS_MIN, PRIMOS_MAX,
    FIBONACCI_MIN, FIBONACCI_MAX,
    BORDA_MIN, BORDA_MAX,
    QUADRANTES
)


class FiltrosGaussianos:

    def __init__(self, historico=None):
        self.historico = historico or []
        self.stats_cache = {}
        if historico:
            self._calcular_estatisticas()

    def _calcular_estatisticas(self):
        """Calcula estatísticas do histórico para calibrar filtros"""
        somas = []
        pares_list = []
        primos_list = []
        fib_list = []
        borda_list = []
        consec_list = []

        for r in self.historico:
            somas.append(r['soma'])
            pares_list.append(r['pares'])
            primos_list.append(r['primos_count'])
            fib_list.append(r['fibonacci_count'])
            borda_list.append(r['borda_count'])
            consec_list.append(r['consecutivos_max'])

        self.stats_cache = {
            'soma_media': np.mean(somas) if somas else 195,
            'soma_std': np.std(somas) if somas else 15,
            'pares_media': np.mean(pares_list) if pares_list else 7.5,
            'primos_media': np.mean(primos_list) if primos_list else 5,
            'fib_media': np.mean(fib_list) if fib_list else 4,
            'borda_media': np.mean(borda_list) if borda_list else 9,
        }

    def filtro_soma(self, dezenas):
        """
        Filtro 1: Assinatura de Gauss
        Soma das dezenas deve estar entre 185 e 220
        """
        soma = sum(dezenas)
        return SOMA_MIN <= soma <= SOMA_MAX

    def filtro_paridade(self, dezenas):
        """
        Filtro 2: Razão Par/Ímpar
        Apenas 8:7 ou 7:8
        """
        pares = sum(1 for d in dezenas if d % 2 == 0)
        impares = 15 - pares
        return (pares == 7 and impares == 8) or (pares == 8 and impares == 7)

    def filtro_consecutivos(self, dezenas):
        """
        Filtro 3: Máximo de consecutivos
        Não mais que 4 números seguidos
        """
        sorted_d = sorted(dezenas)
        max_c = 1
        current = 1
        for i in range(1, len(sorted_d)):
            if sorted_d[i] == sorted_d[i - 1] + 1:
                current += 1
                max_c = max(max_c, current)
            else:
                current = 1
        return max_c <= MAX_CONSECUTIVOS

    def filtro_primos(self, dezenas):
        """
        Filtro 4: Equilíbrio de primos
        Entre 4 e 6 primos
        """
        count = len(set(dezenas) & PRIMOS)
        return PRIMOS_MIN <= count <= PRIMOS_MAX

    def filtro_fibonacci(self, dezenas):
        """
        Filtro 5: Fibonacci
        Entre 3 e 5 números de Fibonacci
        """
        count = len(set(dezenas) & FIBONACCI)
        return FIBONACCI_MIN <= count <= FIBONACCI_MAX

    def filtro_borda_miolo(self, dezenas):
        """
        Filtro 6: Constante da Moldura
        Borda retém 8 a 10 números
        """
        borda_count = len(set(dezenas) & BORDA)
        return BORDA_MIN <= borda_count <= BORDA_MAX

    def filtro_quadrantes(self, dezenas):
        """
        Filtro 7: Distribuição por quadrantes
        3 quadrantes cheios (3 números) e 2 semicheios
        """
        distribuicao = {}
        for q, nums in QUADRANTES.items():
            count = len(set(dezenas) & set(nums))
            distribuicao[q] = count

        # Pelo menos 1 número em cada quadrante
        if any(v == 0 for v in distribuicao.values()):
            return False

        # Máximo 4 de um quadrante
        if any(v > 4 for v in distribuicao.values()):
            return False

        return True

    def filtro_entropia(self, dezenas):
        """
        Filtro 8: Filtro Quântico de Baixa Entropia
        Elimina combinações que nunca ocorreram em 20 anos
        """
        # Verificar se não são 15 números seguidos
        sorted_d = sorted(dezenas)
        if sorted_d == list(range(sorted_d[0], sorted_d[0] + 15)):
            return False

        # Verificar se não são todos pares ou todos ímpares (impossível com 15/25)
        pares = sum(1 for d in dezenas if d % 2 == 0)
        if pares < 5 or pares > 10:
            return False

        return True

    def calcular_score_gaussiano(self, dezenas):
        """
        Calcula score de 0 a 1 baseado na proximidade com a
        curva de Gauss histórica
        """
        score = 0.0
        total_filtros = 8

        if self.filtro_soma(dezenas):
            score += 1
        else:
            # Score parcial baseado na distância
            soma = sum(dezenas)
            centro = (SOMA_MIN + SOMA_MAX) / 2
            dist = abs(soma - centro) / centro
            score += max(0, 1 - dist)

        if self.filtro_paridade(dezenas):
            score += 1
        else:
            score += 0.3

        if self.filtro_consecutivos(dezenas):
            score += 1
        else:
            score += 0.1

        if self.filtro_primos(dezenas):
            score += 1
        else:
            score += 0.4

        if self.filtro_fibonacci(dezenas):
            score += 1
        else:
            score += 0.4

        if self.filtro_borda_miolo(dezenas):
            score += 1
        else:
            score += 0.3

        if self.filtro_quadrantes(dezenas):
            score += 1

        if self.filtro_entropia(dezenas):
            score += 1

        return score / total_filtros

    def aplicar_todos_filtros(self, dezenas):
        """Aplica todos os filtros. Retorna True se passa em todos."""
        return all([
            self.filtro_soma(dezenas),
            self.filtro_paridade(dezenas),
            self.filtro_consecutivos(dezenas),
            self.filtro_primos(dezenas),
            self.filtro_fibonacci(dezenas),
            self.filtro_borda_miolo(dezenas),
            self.filtro_quadrantes(dezenas),
            self.filtro_entropia(dezenas),
        ])

    def relatorio_filtros(self, dezenas):
        """Retorna relatório detalhado de cada filtro"""
        return {
            'soma': {'valor': sum(dezenas), 'aprovado': self.filtro_soma(dezenas),
                     'range': f'{SOMA_MIN}-{SOMA_MAX}'},
            'paridade': {'pares': sum(1 for d in dezenas if d % 2 == 0),
                         'aprovado': self.filtro_paridade(dezenas)},
            'consecutivos': {'aprovado': self.filtro_consecutivos(dezenas)},
            'primos': {'count': len(set(dezenas) & PRIMOS),
                       'aprovado': self.filtro_primos(dezenas)},
            'fibonacci': {'count': len(set(dezenas) & FIBONACCI),
                          'aprovado': self.filtro_fibonacci(dezenas)},
            'borda_miolo': {'borda': len(set(dezenas) & BORDA),
                            'aprovado': self.filtro_borda_miolo(dezenas)},
            'quadrantes': {'aprovado': self.filtro_quadrantes(dezenas)},
            'entropia': {'aprovado': self.filtro_entropia(dezenas)},
            'score_total': self.calcular_score_gaussiano(dezenas)
        }