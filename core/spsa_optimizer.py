"""
============================================================
SPSA - Simultaneous Perturbation Stochastic Approximation
VERSÃO OTIMIZADA - rápida e eficiente
============================================================
"""
import numpy as np
import json
import os
from config import MODELS_PATH


class SPSAOptimizer:

    def __init__(
        self,
        n_iteracoes=30,   # Reduzido de 200 para 30
        a=0.15,
        c=0.05,
        A=10,
        alpha=0.602,
        gamma=0.101,
    ):
        self.n_iter  = n_iteracoes
        self.a       = a
        self.c       = c
        self.A       = A
        self.alpha   = alpha
        self.gamma   = gamma
        self.historico_loss = []

    def _ak(self, k):
        return self.a / (k + 1 + self.A) ** self.alpha

    def _ck(self, k):
        return self.c / (k + 1) ** self.gamma

    def _perturbacao(self, n_params, rng):
        return rng.choice([-1.0, 1.0], size=n_params)

    def _clipar(self, theta, bounds):
        for i in range(len(bounds)):
            lb = bounds[i][0]
            ub = bounds[i][1]
            if theta[i] < lb:
                theta[i] = lb
            if theta[i] > ub:
                theta[i] = ub
        return theta

    def _normalizar(self, theta):
        s = sum(theta)
        if s <= 0:
            return [1.0 / len(theta)] * len(theta)
        return [t / s for t in theta]

    def otimizar_pesos(
        self, funcao_perda, pesos_iniciais,
        bounds=None, callback=None
    ):
        rng   = np.random.default_rng(seed=42)
        n     = len(pesos_iniciais)
        theta = np.array(pesos_iniciais, dtype=float)

        if bounds is None:
            bounds = [(0.05, 0.60)] * n

        self.historico_loss = []
        melhor_theta = theta.copy()

        try:
            melhor_loss = funcao_perda(self._normalizar(theta.tolist()))
        except Exception:
            melhor_loss = 1.0

        for k in range(self.n_iter):
            ak = self._ak(k)
            ck = self._ck(k)

            delta     = self._perturbacao(n, rng)
            theta_pos = self._clipar((theta + ck * delta).copy(), bounds)
            theta_neg = self._clipar((theta - ck * delta).copy(), bounds)

            try:
                loss_pos = funcao_perda(
                    self._normalizar(theta_pos.tolist())
                )
            except Exception:
                loss_pos = melhor_loss

            try:
                loss_neg = funcao_perda(
                    self._normalizar(theta_neg.tolist())
                )
            except Exception:
                loss_neg = melhor_loss

            denom = 2.0 * ck * delta
            denom[denom == 0] = 1e-9
            g_hat = (loss_pos - loss_neg) / denom

            theta -= ak * g_hat
            theta  = self._clipar(theta, bounds)

            try:
                loss_atual = funcao_perda(
                    self._normalizar(theta.tolist())
                )
            except Exception:
                loss_atual = melhor_loss

            self.historico_loss.append(float(loss_atual))

            if loss_atual < melhor_loss:
                melhor_loss  = loss_atual
                melhor_theta = theta.copy()

            if callback and k % 10 == 0:
                callback(
                    "SPSA: iter {}/{} | loss={:.4f}".format(
                        k + 1, self.n_iter, loss_atual
                    )
                )

        pesos_finais = self._normalizar(melhor_theta.tolist())
        return pesos_finais, melhor_loss

    def otimizar_filtros(self, funcao_perda, params_iniciais,
                          bounds, callback=None):
        return self.otimizar_pesos(
            funcao_perda, params_iniciais, bounds, callback
        )

    def salvar(self, pesos, nome="spsa_pesos"):
        try:
            os.makedirs(MODELS_PATH, exist_ok=True)
            path = os.path.join(MODELS_PATH, nome + ".json")
            with open(path, "w") as f:
                json.dump({
                    "pesos": pesos,
                    "loss":  self.historico_loss[-5:]
                }, f)
        except Exception as e:
            print("[SPSA] Erro salvar: {}".format(e))

    def carregar(self, nome="spsa_pesos"):
        try:
            path = os.path.join(MODELS_PATH, nome + ".json")
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f).get("pesos")
        except Exception:
            pass
        return None