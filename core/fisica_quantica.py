"""
============================================================
SIMULAÇÃO DE FÍSICA QUÂNTICA DAS BOLAS
Modelo de colisão, dinâmica do globo, micro-desgastes
============================================================
"""
import numpy as np
from config import (
    MASSA_BOLA_KG, DIAMETRO_BOLA_M, RAIO_BOLA_M,
    COEF_RESTITUICAO, TEMPERATURA_K, PRESSAO_ATM,
    DENSIDADE_AR, UMIDADE_RELATIVA, GRAVIDADE,
    TOTAL_DEZENAS
)


class FisicaQuantica:

    def __init__(self):
        self.k_boltzmann = 1.380649e-23  # Constante de Boltzmann
        self.energia_termica = self._calcular_energia_termica()
        self.velocidade_rms = self._calcular_velocidade_rms()
        self.scores_fisicos = np.zeros(TOTAL_DEZENAS)
        self.treinado = False

    def _calcular_energia_termica(self):
        """
        Energia térmica média: E = (3/2) * k * T
        Influencia a agitação das bolas no globo
        """
        return 1.5 * self.k_boltzmann * TEMPERATURA_K

    def _calcular_velocidade_rms(self):
        """
        Velocidade RMS das bolas: v_rms = sqrt(3kT/m)
        Velocidade quadrática média no sistema
        """
        return np.sqrt(3 * self.k_boltzmann * TEMPERATURA_K / MASSA_BOLA_KG)

    def _coeficiente_arrasto(self, velocidade):
        """
        Calcula coeficiente de arrasto da bola no ar.
        Cd = f(Reynolds)
        Re = ρvd/μ
        """
        viscosidade_ar = 1.81e-5  # Pa·s a ~20°C
        reynolds = (DENSIDADE_AR * velocidade * DIAMETRO_BOLA_M) / viscosidade_ar

        if reynolds < 1:
            cd = 24 / max(reynolds, 0.01)
        elif reynolds < 1000:
            cd = 24 / reynolds * (1 + 0.15 * reynolds ** 0.687)
        else:
            cd = 0.44

        return cd

    def _forca_arrasto(self, velocidade):
        """
        Força de arrasto: Fd = 0.5 * ρ * v² * Cd * A
        Área frontal: A = π * r²
        """
        area = np.pi * RAIO_BOLA_M ** 2
        cd = self._coeficiente_arrasto(velocidade)
        return 0.5 * DENSIDADE_AR * velocidade ** 2 * cd * area

    def _modelo_colisao(self, v1, v2):
        """
        Modelo de colisão elástica parcial entre duas bolas.
        v1_final = (m1*v1 + m2*v2 + m2*e*(v2-v1)) / (m1+m2)
        Onde e = coeficiente de restituição
        """
        m = MASSA_BOLA_KG
        e = COEF_RESTITUICAO
        v1_final = (m * v1 + m * v2 + m * e * (v2 - v1)) / (2 * m)
        v2_final = (m * v1 + m * v2 + m * e * (v1 - v2)) / (2 * m)
        return v1_final, v2_final

    def _simular_globo(self, n_iteracoes=1000):
        """
        Simula a dinâmica das 25 bolas dentro do globo.
        Retorna a frequência de cada bola atingir a zona de saída.
        """
        np.random.seed(None)

        # Posições e velocidades iniciais aleatórias
        posicoes = np.random.uniform(-0.15, 0.15, (TOTAL_DEZENAS, 3))
        velocidades = np.random.normal(0, 0.5, (TOTAL_DEZENAS, 3))

        # Zona de saída (topo do globo)
        zona_saida = np.array([0, 0, 0.15])
        raio_zona = 0.03

        contagem_zona = np.zeros(TOTAL_DEZENAS)

        dt = 0.001  # step temporal

        for _ in range(n_iteracoes):
            for i in range(TOTAL_DEZENAS):
                # Força gravitacional
                forca_grav = np.array([0, 0, -MASSA_BOLA_KG * GRAVIDADE])

                # Arrasto
                v_mag = np.linalg.norm(velocidades[i])
                if v_mag > 0:
                    fd_mag = self._forca_arrasto(v_mag)
                    direcao = -velocidades[i] / v_mag
                    forca_arrasto = fd_mag * direcao
                else:
                    forca_arrasto = np.zeros(3)

                # Flutuação térmica (ruído quântico)
                flutuacao = np.random.normal(0, self.energia_termica * 1e20, 3)

                # Efeito da umidade (eletricidade estática)
                fator_umidade = 1 - (UMIDADE_RELATIVA * 0.1)
                flutuacao *= fator_umidade

                # Atualizar velocidade
                aceleracao = (forca_grav + forca_arrasto + flutuacao) / MASSA_BOLA_KG
                velocidades[i] += aceleracao * dt

                # Atualizar posição
                posicoes[i] += velocidades[i] * dt

                # Colisão com paredes do globo (raio ~0.15m)
                dist_centro = np.linalg.norm(posicoes[i])
                if dist_centro > 0.15:
                    normal = posicoes[i] / dist_centro
                    velocidades[i] -= 2 * np.dot(velocidades[i], normal) * normal
                    velocidades[i] *= COEF_RESTITUICAO
                    posicoes[i] = normal * 0.149

                # Verificar proximidade da zona de saída
                dist_saida = np.linalg.norm(posicoes[i] - zona_saida)
                if dist_saida < raio_zona:
                    contagem_zona[i] += 1

            # Colisões entre bolas
            for i in range(TOTAL_DEZENAS):
                for j in range(i + 1, TOTAL_DEZENAS):
                    dist = np.linalg.norm(posicoes[i] - posicoes[j])
                    if dist < DIAMETRO_BOLA_M:
                        v1, v2 = velocidades[i].copy(), velocidades[j].copy()
                        for k in range(3):
                            velocidades[i][k], velocidades[j][k] = \
                                self._modelo_colisao(v1[k], v2[k])

        return contagem_zona

    def treinar(self, resultados, n_simulacoes=10):
        """
        Executa múltiplas simulações e cruza com dados históricos
        para calibrar os scores físicos.
        """
        # Frequência histórica real
        freq_real = np.zeros(TOTAL_DEZENAS)
        for r in resultados:
            for i in range(1, 16):
                d = r[f'd{i}']
                freq_real[d - 1] += 1
        freq_real /= len(resultados)

        # Simulações do globo
        freq_simulada = np.zeros(TOTAL_DEZENAS)
        for _ in range(n_simulacoes):
            contagem = self._simular_globo(500)
            freq_simulada += contagem

        freq_simulada /= (n_simulacoes * 500)

        # Normalizar
        if freq_simulada.max() > 0:
            freq_simulada /= freq_simulada.max()
        freq_real_norm = freq_real / freq_real.max() if freq_real.max() > 0 else freq_real

        # Score combinado: 70% histórico real + 30% simulação física
        self.scores_fisicos = freq_real_norm * 0.7 + freq_simulada * 0.3

        # Normalizar para 0-1
        if self.scores_fisicos.max() > 0:
            self.scores_fisicos /= self.scores_fisicos.max()

        self.treinado = True

    def score_fisico_jogo(self, dezenas):
        """Score físico de um jogo (0 a 1)"""
        if not self.treinado:
            return 0.5

        score = 0
        for d in dezenas:
            score += self.scores_fisicos[d - 1]
        return score / 15

    def get_dezenas_favorecidas(self, top_n=20):
        """Retorna dezenas com maior score físico"""
        if not self.treinado:
            return list(range(1, top_n + 1))

        ranking = np.argsort(self.scores_fisicos)[::-1]
        return [r + 1 for r in ranking[:top_n]]

    def get_mapa_energia(self):
        """Retorna mapa de energia para heatmap"""
        return {i + 1: float(self.scores_fisicos[i]) for i in range(TOTAL_DEZENAS)}