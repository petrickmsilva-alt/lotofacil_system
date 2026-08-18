"""
============================================================
MOTOR DE CADEIAS DE MARKOV MODIFICADAS
Operador Ψ(Ht) — Memória de Curto e Longo Prazo
Frequência de transição e mapeamento de clusters
============================================================
"""
import numpy as np
from config import TOTAL_DEZENAS, QUADRANTES, REPETICAO_MIN, REPETICAO_MAX


class MarkovEngine:

    def __init__(self):
        self.matriz_transicao = np.zeros((TOTAL_DEZENAS, TOTAL_DEZENAS))
        self.frequencia_global = np.zeros(TOTAL_DEZENAS)
        self.frequencia_recente = np.zeros(TOTAL_DEZENAS)
        self.atraso = np.zeros(TOTAL_DEZENAS)
        self.ultimo_resultado = None
        self.treinado = False

    def treinar(self, resultados):
        """
        Constrói a matriz de transição de Markov.
        Se dezena X saiu no concurso anterior, qual a probabilidade
        da dezena Y sair no próximo?
        """
        n = len(resultados)
        if n < 2:
            return

        # Frequência global
        for r in resultados:
            dezenas = self._extrair_dezenas(r)
            for d in dezenas:
                self.frequencia_global[d - 1] += 1

        # Normalizar
        self.frequencia_global /= n

        # Frequência recente (últimos 50 concursos)
        recentes = resultados[-50:]
        for r in recentes:
            dezenas = self._extrair_dezenas(r)
            for d in dezenas:
                self.frequencia_recente[d - 1] += 1
        self.frequencia_recente /= len(recentes)

        # Matriz de transição
        for i in range(1, n):
            dezenas_anterior = set(self._extrair_dezenas(resultados[i - 1]))
            dezenas_atual = set(self._extrair_dezenas(resultados[i]))

            for da in dezenas_anterior:
                for dc in dezenas_atual:
                    self.matriz_transicao[da - 1][dc - 1] += 1

        # Normalizar linhas
        somas_linhas = self.matriz_transicao.sum(axis=1, keepdims=True)
        somas_linhas[somas_linhas == 0] = 1
        self.matriz_transicao /= somas_linhas

        # Calcular atrasos
        ultimo = resultados[-1]
        dezenas_ultimo = set(self._extrair_dezenas(ultimo))
        self.ultimo_resultado = dezenas_ultimo

        for d in range(1, TOTAL_DEZENAS + 1):
            atraso = 0
            for r in reversed(resultados):
                dezenas_r = set(self._extrair_dezenas(r))
                if d in dezenas_r:
                    break
                atraso += 1
            self.atraso[d - 1] = atraso

        self.treinado = True

    def _extrair_dezenas(self, resultado):
        """Extrai dezenas de um resultado do banco"""
        return [resultado[f'd{i}'] for i in range(1, 16)]

    def probabilidade_transicao(self, dezena_anterior, dezena_proxima):
        """P(dezena_proxima | dezena_anterior)"""
        return self.matriz_transicao[dezena_anterior - 1][dezena_proxima - 1]

    def score_markov_jogo(self, dezenas):
        """
        Calcula score de Markov para um jogo completo.
        Considera transição do último resultado + frequência + atraso
        """
        if not self.treinado or not self.ultimo_resultado:
            return 0.5

        score = 0.0

        # 1. Score de transição
        for d in dezenas:
            prob_trans = 0
            for d_ant in self.ultimo_resultado:
                prob_trans += self.probabilidade_transicao(d_ant, d)
            prob_trans /= len(self.ultimo_resultado)
            score += prob_trans

        score_transicao = score / 15

        # 2. Score de repetição (8-10 dezenas repetem do anterior)
        repeticoes = len(set(dezenas) & self.ultimo_resultado)
        if REPETICAO_MIN <= repeticoes <= REPETICAO_MAX:
            score_repeticao = 1.0
        else:
            dist = min(abs(repeticoes - REPETICAO_MIN),
                       abs(repeticoes - REPETICAO_MAX))
            score_repeticao = max(0, 1 - (dist * 0.2))

        # 3. Score de frequência
        score_freq = 0
        for d in dezenas:
            peso_global = self.frequencia_global[d - 1]
            peso_recente = self.frequencia_recente[d - 1]
            score_freq += (peso_global * 0.3 + peso_recente * 0.7)
        score_freq /= 15

        # 4. Score de atraso (dezenas com atraso médio são boas candidatas)
        score_atraso = 0
        atraso_medio = np.mean(self.atraso)
        for d in dezenas:
            a = self.atraso[d - 1]
            if 0 <= a <= atraso_medio * 1.5:
                score_atraso += 1
        score_atraso /= 15

        # Score combinado
        score_total = (
                score_transicao * 0.35 +
                score_repeticao * 0.25 +
                score_freq * 0.25 +
                score_atraso * 0.15
        )

        return min(1.0, score_total)

    def dezenas_mais_provaveis(self, top_n=20):
        """
        Retorna as N dezenas com maior probabilidade de sair
        baseado na cadeia de Markov
        """
        if not self.treinado or not self.ultimo_resultado:
            return list(range(1, top_n + 1))

        scores = np.zeros(TOTAL_DEZENAS)
        for d_ant in self.ultimo_resultado:
            scores += self.matriz_transicao[d_ant - 1]

        # Ponderar com frequência recente e atraso
        for i in range(TOTAL_DEZENAS):
            scores[i] *= (1 + self.frequencia_recente[i])
            # Bônus para dezenas com atraso moderado
            if 1 <= self.atraso[i] <= 3:
                scores[i] *= 1.2

        # Ranking
        ranking = np.argsort(scores)[::-1]
        return [r + 1 for r in ranking[:top_n]]

    def analise_quadrantes(self, resultados):
        """
        Analisa distribuição de quadrantes ao longo do histórico.
        Identifica padrão de onda (3 cheios + 2 semicheios)
        """
        if not resultados:
            return {}

        ultimos = resultados[-20:]
        dist_quad = {q: [] for q in QUADRANTES}

        for r in ultimos:
            dezenas = set(self._extrair_dezenas(r))
            for q, nums in QUADRANTES.items():
                count = len(dezenas & set(nums))
                dist_quad[q].append(count)

        analise = {}
        for q, counts in dist_quad.items():
            analise[q] = {
                'media': np.mean(counts),
                'tendencia': 'subindo' if counts[-1] > np.mean(counts) else 'descendo',
                'ultimo': counts[-1],
                'previsao': round(np.mean(counts[-5:]))
            }

        return analise