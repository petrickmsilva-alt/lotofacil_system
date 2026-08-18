"""
============================================================
QUANTUM WALKS — PASSEIOS QUÂNTICOS
Modela transição de estados dos números usando
caminhadas quânticas para mapear superposições de tendências.
============================================================
"""
import numpy as np
from config import TOTAL_DEZENAS


class QuantumWalk:

    def __init__(self):
        self.amplitudes     = np.ones(TOTAL_DEZENAS, dtype=complex) / \
                              np.sqrt(TOTAL_DEZENAS)
        self.probabilidades = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS
        self.historico_prob = []
        self.treinado       = False

    # =========================================================
    # OPERADORES QUÂNTICOS
    # =========================================================

    def _hadamard_coin(self):
        """Moeda de Hadamard 2x2"""
        return np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

    def _operador_shift(self, amp, direcao):
        """
        Operador de deslocamento no grafo circular de N nós.
        +1 ou -1 no círculo de 25 dezenas.
        """
        if direcao > 0:
            return np.roll(amp, 1)
        else:
            return np.roll(amp, -1)

    def _grover_coin(self, n):
        """
        Moeda de Grover para N dimensões.
        Amplifica estados de alta probabilidade.
        """
        G = (2.0 / n) * np.ones((n, n), dtype=complex) - \
            np.eye(n, dtype=complex)
        return G

    def _passo_quantico(self, amp_up, amp_down):
        """
        Um passo da caminhada quântica com moeda de Hadamard.
        amp_up   = amplitude "spin up"
        amp_down = amplitude "spin down"
        """
        H = self._hadamard_coin()

        # Aplicar moeda
        amp_up_new   =  H[0, 0] * amp_up + H[0, 1] * amp_down
        amp_down_new =  H[1, 0] * amp_up + H[1, 1] * amp_down

        # Deslocamento
        amp_up_new   = self._operador_shift(amp_up_new,   +1)
        amp_down_new = self._operador_shift(amp_down_new, -1)

        return amp_up_new, amp_down_new

    # =========================================================
    # CAMINHADA PRINCIPAL
    # =========================================================

    def executar_caminhada(self, n_passos=500, posicao_inicial=None):
        """
        Executa caminhada quântica no espaço de 25 dezenas.
        Retorna distribuição de probabilidade final.
        """
        N = TOTAL_DEZENAS

        # Inicializar amplitudes
        if posicao_inicial is not None and 1 <= posicao_inicial <= N:
            amp_up   = np.zeros(N, dtype=complex)
            amp_down = np.zeros(N, dtype=complex)
            idx      = posicao_inicial - 1
            amp_up[idx]   = 1.0 / np.sqrt(2)
            amp_down[idx] = 1.0j / np.sqrt(2)
        else:
            # Superposição uniforme
            amp_up   = np.ones(N, dtype=complex) / np.sqrt(2 * N)
            amp_down = np.ones(N, dtype=complex) * 1.0j / np.sqrt(2 * N)

        # Executar passos
        for _ in range(n_passos):
            amp_up, amp_down = self._passo_quantico(amp_up, amp_down)

        # Distribuição de probabilidade = |amp|²
        prob = np.abs(amp_up) ** 2 + np.abs(amp_down) ** 2

        # Normalizar
        total = prob.sum()
        if total > 0:
            prob /= total

        return prob

    def caminhada_com_oraculo(self, dezenas_recentes, n_passos=300):
        """
        Caminhada quântica com oráculo que amplifica dezenas recentes.
        Simula memória quântica do sistema.
        """
        N    = TOTAL_DEZENAS
        prob = np.zeros(N)

        # Iniciar de cada dezena recente
        for d in dezenas_recentes:
            p = self.executar_caminhada(n_passos, posicao_inicial=d)
            prob += p

        # Média
        if len(dezenas_recentes) > 0:
            prob /= len(dezenas_recentes)

        # Aplicar moeda de Grover para amplificação
        G    = self._grover_coin(N)
        amp  = np.sqrt(prob).astype(complex)
        amp2 = G @ amp

        prob_grover = np.abs(amp2) ** 2
        total       = prob_grover.sum()
        if total > 0:
            prob_grover /= total

        # Combinar: 70% Grover + 30% caminhada pura
        prob_final = 0.70 * prob_grover + 0.30 * prob

        return prob_final

    # =========================================================
    # TREINAMENTO
    # =========================================================

    def treinar(self, resultados, callback=None):
        """
        Treina o modelo quântico com histórico completo.
        Constrói mapa de transições quânticas entre concursos.
        """
        if callback:
            callback("Quantum Walk: construindo mapa de transições...")

        N    = TOTAL_DEZENAS
        prob_acumulada = np.zeros(N)

        n = len(resultados)
        if n < 2:
            self.treinado = True
            return self.probabilidades

        # Para cada concurso, executar caminhada a partir
        # das dezenas do concurso anterior
        janela = min(n, 200)   # usar últimos 200 para eficiência

        for i in range(n - janela, n - 1):
            try:
                dezenas_ant = [resultados[i][f"d{j}"]
                               for j in range(1, 16)]

                prob = self.caminhada_com_oraculo(
                    dezenas_ant, n_passos=200
                )
                prob_acumulada += prob

            except Exception as e:
                continue

        # Normalizar
        if prob_acumulada.sum() > 0:
            prob_acumulada /= prob_acumulada.sum()

        # Suavizar com distribuição uniforme (evitar zeros)
        prob_suave = 0.95 * prob_acumulada + 0.05 / N

        self.probabilidades = prob_suave
        self.treinado       = True

        if callback:
            callback("Quantum Walk: treinamento concluído!")

        return self.probabilidades.copy()

    def prever_proximo(self, ultimo_resultado, n_passos=400):
        """
        Prevê probabilidades do próximo concurso.
        """
        try:
            dezenas = [ultimo_resultado[f"d{i}"] for i in range(1, 16)]
        except Exception:
            dezenas = list(range(1, 16))

        prob = self.caminhada_com_oraculo(dezenas, n_passos)

        # Combinar com modelo treinado
        if self.treinado:
            prob = 0.6 * prob + 0.4 * self.probabilidades

        return prob

    def score_jogo(self, dezenas, ultimo_resultado=None):
        """Score quântico de um jogo"""
        if ultimo_resultado is not None:
            prob = self.prever_proximo(ultimo_resultado)
        else:
            prob = self.probabilidades

        return float(np.mean([prob[d - 1] for d in dezenas]))

    def get_probabilidades(self):
        return {i + 1: float(self.probabilidades[i])
                for i in range(TOTAL_DEZENAS)}