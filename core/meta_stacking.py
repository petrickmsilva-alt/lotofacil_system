"""
============================================================
META-CLASSIFICADOR STACKING
Aprende inteligentemente com erros e acertos de todos
os motores. Combina previsões de múltiplos modelos base.
============================================================
"""
import numpy as np
import json
import os
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from config import TOTAL_DEZENAS, MODELS_PATH


class MetaStacking:

    def __init__(self):
        # Meta-learner: combina saídas dos modelos base
        self.meta_learner   = Ridge(alpha=1.0)
        self.scaler_meta    = StandardScaler()
        self.treinado       = False

        # Pesos aprendidos por motor
        self.pesos_motores = {
            "markov":     0.20,
            "fisico":     0.10,
            "gaussiano":  0.15,
            "ml":         0.20,
            "verlet":     0.10,
            "quantum":    0.10,
            "chi2":       0.05,
            "bayes":      0.05,
            "kl":         0.05,
        }

        # Histórico de predições vs real
        self.historico_pred  = []   # lista de dicts
        self.erros_por_motor = {k: [] for k in self.pesos_motores}

    # =========================================================
    # REGISTRAR PREDIÇÃO
    # =========================================================

    def registrar_predicao(self, concurso, scores_motores, acertos_real):
        """
        Registra a predição de cada motor e o resultado real.
        Usado para treinar o meta-learner.

        scores_motores: dict {motor: score_do_jogo}
        acertos_real: int (11-15)
        """
        entrada = {
            "concurso":      concurso,
            "scores":        scores_motores.copy(),
            "acertos_reais": acertos_real,
        }
        self.historico_pred.append(entrada)

        # Registrar erro por motor
        for motor, score in scores_motores.items():
            if motor in self.erros_por_motor:
                # Quanto o score previu vs resultado normalizado
                alvo  = (acertos_real - 11) / 4.0   # normalizar 11-15 → 0-1
                erro  = abs(score - alvo)
                self.erros_por_motor[motor].append(erro)

    # =========================================================
    # TREINAR META-LEARNER
    # =========================================================

    def treinar(self, callback=None):
        """
        Treina o meta-learner com histórico de predições.
        X = scores de cada motor
        y = acertos reais normalizados
        """
        if len(self.historico_pred) < 10:
            if callback:
                callback("Stacking: histórico insuficiente (mín 10)")
            return False

        if callback:
            callback("Stacking: treinando meta-learner...")

        motores = list(self.pesos_motores.keys())
        X, y    = [], []

        for pred in self.historico_pred:
            linha = [pred["scores"].get(m, 0.5) for m in motores]
            X.append(linha)
            # Target: acertos normalizados (0=11pts, 1=15pts)
            alvo = (pred["acertos_reais"] - 11) / 4.0
            y.append(alvo)

        X = np.array(X)
        y = np.array(y)

        # Normalizar
        self.scaler_meta.fit(X)
        X_sc = self.scaler_meta.transform(X)

        # Treinar meta-learner
        self.meta_learner.fit(X_sc, y)

        # Atualizar pesos baseado nos coeficientes
        coefs = self.meta_learner.coef_
        coefs_pos = np.clip(coefs, 0.01, None)

        total = coefs_pos.sum()
        if total > 0:
            for i, motor in enumerate(motores):
                self.pesos_motores[motor] = float(coefs_pos[i] / total)

        self.treinado = True

        if callback:
            callback(
                f"Stacking: treinado com {len(self.historico_pred)} predições"
            )

        return True

    # =========================================================
    # PREDIÇÃO COMBINADA
    # =========================================================

    def combinar_scores(self, scores_motores):
        """
        Combina scores de múltiplos motores usando pesos aprendidos.
        Retorna score final ponderado.
        """
        if self.treinado:
            try:
                motores = list(self.pesos_motores.keys())
                linha   = [scores_motores.get(m, 0.5) for m in motores]
                X       = np.array(linha).reshape(1, -1)
                X_sc    = self.scaler_meta.transform(X)
                pred    = float(self.meta_learner.predict(X_sc)[0])
                return np.clip(pred, 0, 1)
            except Exception as e:
                print(f"[Stacking] predict erro: {e}")

        # Fallback: média ponderada simples
        total_peso = sum(self.pesos_motores.values())
        score      = 0.0
        for motor, peso in self.pesos_motores.items():
            score += scores_motores.get(motor, 0.5) * peso
        return score / (total_peso + 1e-9)

    def combinar_vetores(self, vetores_motores):
        """
        Combina vetores de probabilidade (tamanho 25) de cada motor.
        Retorna vetor combinado ponderado.
        """
        resultado = np.zeros(TOTAL_DEZENAS)

        for motor, vetor in vetores_motores.items():
            peso = self.pesos_motores.get(motor, 0.1)
            arr  = np.array(vetor, dtype=float)
            if arr.max() > 0:
                arr /= arr.max()
            resultado += arr * peso

        if resultado.max() > 0:
            resultado /= resultado.max()

        return resultado

    # =========================================================
    # ANÁLISE DE ERROS
    # =========================================================

    def relatorio_erros(self):
        """Relatório de performance de cada motor"""
        relatorio = {}
        for motor, erros in self.erros_por_motor.items():
            if erros:
                relatorio[motor] = {
                    "erro_medio":  round(float(np.mean(erros)),  4),
                    "erro_min":    round(float(np.min(erros)),   4),
                    "erro_max":    round(float(np.max(erros)),   4),
                    "n_amostras":  len(erros),
                    "peso_atual":  round(self.pesos_motores[motor], 4),
                }
        return relatorio

    def get_melhor_motor(self):
        """Retorna o motor com menor erro médio"""
        melhor      = None
        menor_erro  = float("inf")

        for motor, erros in self.erros_por_motor.items():
            if erros:
                media = float(np.mean(erros))
                if media < menor_erro:
                    menor_erro = media
                    melhor     = motor

        return melhor, menor_erro

    # =========================================================
    # SALVAR / CARREGAR
    # =========================================================

    def salvar(self):
        try:
            os.makedirs(MODELS_PATH, exist_ok=True)

            joblib.dump(
                self.meta_learner,
                os.path.join(MODELS_PATH, "meta_stacking.pkl")
            )
            joblib.dump(
                self.scaler_meta,
                os.path.join(MODELS_PATH, "meta_scaler.pkl")
            )
            with open(
                os.path.join(MODELS_PATH, "meta_pesos.json"), "w"
            ) as f:
                json.dump({
                    "pesos":    self.pesos_motores,
                    "historico": self.historico_pred[-50:],
                }, f, indent=2)

            print("[Stacking] Modelos salvos")
        except Exception as e:
            print(f"[Stacking] Erro ao salvar: {e}")

    def carregar(self):
        try:
            path_ml = os.path.join(MODELS_PATH, "meta_stacking.pkl")
            if not os.path.exists(path_ml):
                return False

            self.meta_learner = joblib.load(path_ml)
            self.scaler_meta  = joblib.load(
                os.path.join(MODELS_PATH, "meta_scaler.pkl")
            )

            path_json = os.path.join(MODELS_PATH, "meta_pesos.json")
            if os.path.exists(path_json):
                with open(path_json) as f:
                    dados = json.load(f)
                self.pesos_motores = dados.get("pesos", self.pesos_motores)
                self.historico_pred = dados.get("historico", [])

            self.treinado = True
            return True
        except Exception as e:
            print(f"[Stacking] Erro ao carregar: {e}")
            return False