"""
============================================================
SIMULADOR VERLET 3D
Trata o sorteio como fenômeno mecânico real.
Simula cinemática e colisões de 25 esferas dentro de um
globo tridimensional usando integração de Verlet.
============================================================
"""
import numpy as np
from config import (
    MASSA_BOLA_KG, RAIO_BOLA_M, COEF_RESTITUICAO,
    DENSIDADE_AR, GRAVIDADE, TEMPERATURA_K,
    TOTAL_DEZENAS
)


class VerletSimulator3D:

    # Raio do globo (em metros)
    RAIO_GLOBO = 0.20

    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)
        self.scores_verlet = np.zeros(TOTAL_DEZENAS)
        self.treinado      = False

    # =========================================================
    # FÍSICA BÁSICA
    # =========================================================

    def _viscosidade_ar(self):
        """Viscosidade dinâmica do ar ~ Sutherland"""
        T0, mu0, C = 291.15, 1.827e-5, 120.0
        return mu0 * (T0 + C) / (TEMPERATURA_K + C) * \
               (TEMPERATURA_K / T0) ** 1.5

    def _arrasto(self, vel):
        """Força de arrasto (vetor)"""
        speed = np.linalg.norm(vel)
        if speed < 1e-9:
            return np.zeros(3)
        mu  = self._viscosidade_ar()
        Re  = DENSIDADE_AR * speed * 2 * RAIO_BOLA_M / mu
        Cd  = 24/Re + 6/(1 + np.sqrt(Re)) + 0.4 if Re > 0 else 0.4
        A   = np.pi * RAIO_BOLA_M ** 2
        Fd  = 0.5 * DENSIDADE_AR * speed ** 2 * Cd * A
        return -Fd * vel / speed

    def _forca_magnus(self, vel, omega):
        """Força de Magnus (efeito de rotação)"""
        rho = DENSIDADE_AR
        r   = RAIO_BOLA_M
        return np.pi * rho * r ** 3 * np.cross(omega, vel)

    # =========================================================
    # INTEGRAÇÃO DE VERLET
    # =========================================================

    def _inicializar_estado(self, n_bolas):
        """Posições e velocidades iniciais aleatórias dentro do globo"""
        pos = np.zeros((n_bolas, 3))
        vel = np.zeros((n_bolas, 3))
        ang = np.zeros((n_bolas, 3))   # velocidade angular

        for i in range(n_bolas):
            while True:
                p = self.rng.uniform(-self.RAIO_GLOBO * 0.8,
                                      self.RAIO_GLOBO * 0.8, 3)
                if np.linalg.norm(p) < self.RAIO_GLOBO * 0.8:
                    pos[i] = p
                    break
            vel[i] = self.rng.normal(0, 1.5, 3)
            ang[i] = self.rng.normal(0, 5.0, 3)

        return pos, vel, ang

    def _calcular_aceleracoes(self, pos, vel, ang):
        """Calcula aceleração de cada bola"""
        n   = len(pos)
        acc = np.zeros((n, 3))

        g_vec = np.array([0.0, 0.0, -GRAVIDADE])

        for i in range(n):
            # Gravidade
            f = MASSA_BOLA_KG * g_vec

            # Arrasto
            f += self._arrasto(vel[i])

            # Magnus
            f += self._forca_magnus(vel[i], ang[i])

            # Turbulência (fluxo de ar do motor)
            f += self.rng.normal(0, 0.002, 3)

            acc[i] = f / MASSA_BOLA_KG

        return acc

    def _resolver_colisoes_bolas(self, pos, vel):
        """Colisões elásticas parciais entre pares de bolas"""
        n = len(pos)
        d = 2 * RAIO_BOLA_M   # diâmetro

        for i in range(n):
            for j in range(i + 1, n):
                delta = pos[j] - pos[i]
                dist  = np.linalg.norm(delta)

                if dist < d and dist > 1e-9:
                    # Normal de colisão
                    n_hat = delta / dist

                    # Sobreposição
                    overlap = d - dist
                    pos[i] -= n_hat * overlap * 0.5
                    pos[j] += n_hat * overlap * 0.5

                    # Velocidades relativas
                    v_rel = vel[j] - vel[i]
                    v_n   = np.dot(v_rel, n_hat)

                    if v_n < 0:
                        j_imp = -(1 + COEF_RESTITUICAO) * v_n / 2
                        vel[i] -= j_imp * n_hat
                        vel[j] += j_imp * n_hat

        return pos, vel

    def _resolver_colisao_globo(self, pos, vel):
        """Colisão de cada bola com a parede esférica do globo"""
        n = len(pos)
        for i in range(n):
            dist = np.linalg.norm(pos[i])
            lim  = self.RAIO_GLOBO - RAIO_BOLA_M

            if dist > lim and dist > 1e-9:
                n_hat   = pos[i] / dist
                pos[i]  = n_hat * lim
                v_n     = np.dot(vel[i], n_hat)
                if v_n > 0:
                    vel[i] -= (1 + COEF_RESTITUICAO) * v_n * n_hat

        return pos, vel

    # =========================================================
    # SIMULAÇÃO PRINCIPAL
    # =========================================================

    def simular(self, n_passos=2000, dt=5e-4):
        """
        Executa simulação Verlet 3D completa.
        Retorna contagem de visitas à zona de saída por bola.
        """
        n_bolas = TOTAL_DEZENAS
        pos, vel, ang = self._inicializar_estado(n_bolas)

        # Aceleração anterior (Verlet)
        acc_ant = self._calcular_aceleracoes(pos, vel, ang)

        # Zona de saída: topo do globo
        zona_saida  = np.array([0.0, 0.0, self.RAIO_GLOBO * 0.85])
        raio_saida  = RAIO_BOLA_M * 2.5
        contagem    = np.zeros(n_bolas)

        for passo in range(n_passos):
            # ── Verlet position update ────────────────────────
            pos_nova = pos + vel * dt + 0.5 * acc_ant * dt ** 2

            # ── Nova aceleração ───────────────────────────────
            acc_nova = self._calcular_aceleracoes(pos_nova, vel, ang)

            # ── Verlet velocity update ────────────────────────
            vel += 0.5 * (acc_ant + acc_nova) * dt

            # ── Rotação das bolas ─────────────────────────────
            ang *= 0.999   # amortecimento angular

            # ── Colisões ──────────────────────────────────────
            pos_nova, vel = self._resolver_colisoes_bolas(pos_nova, vel)
            pos_nova, vel = self._resolver_colisao_globo(pos_nova, vel)

            pos     = pos_nova
            acc_ant = acc_nova

            # ── Verificar zona de saída ───────────────────────
            if passo > n_passos * 0.3:   # ignorar fase inicial
                for i in range(n_bolas):
                    if np.linalg.norm(pos[i] - zona_saida) < raio_saida:
                        contagem[i] += 1

        return contagem

    # =========================================================
    # TREINO COM HISTÓRICO
    # =========================================================

    def treinar(self, resultados, n_simulacoes=8, callback=None):
        """
        Roda N simulações e calibra scores com histórico real.
        """
        if callback:
            callback("Verlet 3D: iniciando simulações...")

        # Frequência histórica real
        freq_real = np.zeros(TOTAL_DEZENAS)
        for r in resultados:
            for i in range(1, 16):
                d = r[f"d{i}"]
                if 1 <= d <= 25:
                    freq_real[d - 1] += 1

        n_res = len(resultados)
        if n_res > 0:
            freq_real /= n_res

        # Simulações
        freq_sim = np.zeros(TOTAL_DEZENAS)
        for s in range(n_simulacoes):
            sim = VerletSimulator3D(seed=s * 137 + 42)
            cnt = sim.simular(n_passos=1500, dt=5e-4)
            freq_sim += cnt
            if callback:
                callback(f"Verlet 3D: simulação {s+1}/{n_simulacoes}")

        # Normalizar simulação
        if freq_sim.max() > 0:
            freq_sim /= freq_sim.max()
        if freq_real.max() > 0:
            freq_real /= freq_real.max()

        # Combinar: 60% histórico real + 40% física simulada
        self.scores_verlet = freq_real * 0.60 + freq_sim * 0.40

        if self.scores_verlet.max() > 0:
            self.scores_verlet /= self.scores_verlet.max()

        self.treinado = True

        if callback:
            callback("Verlet 3D: treinamento concluído!")

        return self.scores_verlet.copy()

    def score_jogo(self, dezenas):
        """Score Verlet para um jogo"""
        if not self.treinado:
            return 0.5
        return float(np.mean([self.scores_verlet[d - 1] for d in dezenas]))

    def get_scores(self):
        return {i + 1: float(self.scores_verlet[i])
                for i in range(TOTAL_DEZENAS)}