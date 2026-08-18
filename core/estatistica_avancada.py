"""
============================================================
ESTATÍSTICA AVANÇADA
- Teste Chi-Quadrado (χ²)
- Teorema de Bayes + Bernoulli Condicional
- Divergência de Kullback-Leibler (KL)
============================================================
"""
import numpy as np
from scipy import stats
from scipy.special import rel_entr
from config import TOTAL_DEZENAS, DEZENAS_POR_JOGO


class EstatisticaAvancada:

    def __init__(self):
        self.freq_esperada  = np.ones(TOTAL_DEZENAS) * \
                              (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        self.freq_observada = np.ones(TOTAL_DEZENAS) * \
                              (DEZENAS_POR_JOGO / TOTAL_DEZENAS)
        self.matriz_bayes   = np.ones((TOTAL_DEZENAS, TOTAL_DEZENAS)) / \
                              TOTAL_DEZENAS
        self.prior_bernoulli = np.ones(TOTAL_DEZENAS) * 0.5
        self.treinado       = False

    # =========================================================
    # CHI-QUADRADO
    # =========================================================

    def calcular_chi2(self, resultados, janela=None):
        """
        Teste χ² para medir uniformidade dos sorteios.
        H0: distribuição é uniforme (loteria honesta)
        Retorna estatística χ², p-valor e scores por dezena.

        Princípio da Honestidade: separa ganho matemático
        real do ruído aleatório.
        """
        if janela:
            resultados = resultados[-janela:]

        n = len(resultados)
        if n == 0:
            return {}, np.ones(TOTAL_DEZENAS) * 0.5

        # Contagem observada
        obs = np.zeros(TOTAL_DEZENAS)
        for r in resultados:
            for i in range(1, 16):
                d = r[f"d{i}"]
                if 1 <= d <= 25:
                    obs[d - 1] += 1

        # Esperado: distribuição uniforme
        esp = np.ones(TOTAL_DEZENAS) * \
              (n * DEZENAS_POR_JOGO / TOTAL_DEZENAS)

        # Estatística χ²
        chi2_stat, p_valor = stats.chisquare(obs, esp)

        # Chi2 por dezena (resíduo padronizado)
        residuos = (obs - esp) / np.sqrt(esp + 1e-9)

        # Score: dezenas com resíduo positivo (mais que esperado)
        # são favorecidas, negativo são evitadas
        scores_chi2 = np.clip(residuos, -3, 3)
        scores_chi2 = (scores_chi2 - scores_chi2.min()) / \
                      (scores_chi2.max() - scores_chi2.min() + 1e-9)

        self.freq_observada = obs / (obs.sum() + 1e-9)

        return {
            "chi2_stat":  float(chi2_stat),
            "p_valor":    float(p_valor),
            "uniforme":   p_valor > 0.05,
            "residuos":   residuos.tolist(),
        }, scores_chi2

    def chi2_score_jogo(self, dezenas, scores_chi2):
        """Score Chi² de um jogo"""
        return float(np.mean([scores_chi2[d - 1] for d in dezenas]))

    # =========================================================
    # BAYES + BERNOULLI
    # =========================================================

    def treinar_bayes(self, resultados):
        """
        Treina filtro Bayesiano com priori de Bernoulli.

        P(dezena_j no próximo | dezenas_i no atual) usando
        Bayes com atualização incremental.
        """
        N = TOTAL_DEZENAS
        # Contagem de co-ocorrências com suavização de Laplace
        contagem = np.ones((N, N))       # prior uniforme
        total    = np.ones(N) * N        # denominador

        n = len(resultados)
        for i in range(n - 1):
            try:
                dez_atual = set(
                    resultados[i][f"d{j}"] for j in range(1, 16)
                )
                dez_prox  = set(
                    resultados[i + 1][f"d{j}"] for j in range(1, 16)
                )

                for da in dez_atual:
                    total[da - 1] += 1
                    for dp in dez_prox:
                        contagem[da - 1][dp - 1] += 1

            except Exception:
                continue

        # P(dp | da) = contagem / total (Bayes Naive com Laplace)
        self.matriz_bayes = contagem / total[:, np.newaxis]

        # Prior Bernoulli: P(dezena aparece) = freq histórica
        freq = np.zeros(N)
        for r in resultados:
            for i in range(1, 16):
                d = r[f"d{i}"]
                if 1 <= d <= 25:
                    freq[d - 1] += 1

        self.prior_bernoulli = (freq + 1) / (n + N)   # Laplace

    def posterior_bayes(self, dezenas_anteriores):
        """
        P(dezena_j | dezenas_anteriores) via Bayes.
        Combina evidências de múltiplas dezenas anteriores.
        """
        N        = TOTAL_DEZENAS
        log_post = np.log(self.prior_bernoulli + 1e-9)

        for d in dezenas_anteriores:
            if 1 <= d <= 25:
                likelihood = self.matriz_bayes[d - 1]
                log_post  += np.log(likelihood + 1e-9)

        # Normalizar (log-sum-exp para estabilidade numérica)
        log_post -= log_post.max()
        post      = np.exp(log_post)
        post     /= post.sum() + 1e-9

        return post

    def bernoulli_condicional(self, dezenas, dezenas_anteriores):
        """
        P(jogo | histórico) = produto de Bernoullis condicionais.
        Score de um jogo baseado em probabilidade bayesiana.
        """
        post = self.posterior_bayes(dezenas_anteriores)
        return float(np.mean([post[d - 1] for d in dezenas]))

    def score_bayes_jogo(self, dezenas, ultimo_resultado):
        """Score Bayesiano de um jogo"""
        try:
            dez_ant = [ultimo_resultado[f"d{i}"] for i in range(1, 16)]
            return self.bernoulli_condicional(dezenas, dez_ant)
        except Exception:
            return 0.5

    # =========================================================
    # KULLBACK-LEIBLER DIVERGENCE
    # =========================================================

    def calcular_kl(self, dist_jogo, dist_referencia=None):
        """
        Divergência KL: D_KL(P || Q)
        Mede quão diferente um jogo é da distribuição histórica.

        Guardião de Entropia:
        - KL baixa = jogo alinhado com padrão histórico ✅
        - KL alta  = jogo diverge do padrão (ruído/anomalia) ❌
        """
        if dist_referencia is None:
            dist_referencia = self.freq_observada

        # Garantir que são distribuições válidas
        p = np.array(dist_jogo,       dtype=float) + 1e-9
        q = np.array(dist_referencia, dtype=float) + 1e-9

        p /= p.sum()
        q /= q.sum()

        # KL(P || Q) = Σ p(i) * log(p(i) / q(i))
        kl = float(np.sum(rel_entr(p, q)))

        return kl

    def dist_jogo(self, dezenas):
        """Converte jogo em distribuição de probabilidade"""
        dist = np.zeros(TOTAL_DEZENAS)
        for d in dezenas:
            if 1 <= d <= 25:
                dist[d - 1] = 1.0
        dist /= dist.sum()
        return dist

    def score_kl_jogo(self, dezenas):
        """
        Score KL de um jogo (1 - KL normalizada).
        Score alto = jogo com baixa divergência = mais alinhado.
        """
        dist = self.dist_jogo(dezenas)
        kl   = self.calcular_kl(dist)

        # KL máxima teórica para nosso espaço
        kl_max = np.log(TOTAL_DEZENAS)

        # Inverter: score alto = KL baixa
        score = 1.0 - min(kl / (kl_max + 1e-9), 1.0)

        return float(score)

    def filtrar_por_kl(self, lista_jogos, threshold=0.7):
        """
        Filtra jogos com KL score abaixo do threshold.
        Mantém apenas jogos alinhados com a distribuição histórica.
        """
        filtrados = []
        for jogo in lista_jogos:
            score = self.score_kl_jogo(jogo)
            if score >= threshold:
                filtrados.append(jogo)
        return filtrados

    # =========================================================
    # TREINAMENTO GERAL
    # =========================================================

    def treinar(self, resultados, callback=None):
        """Treina todos os módulos estatísticos"""
        if callback:
            callback("Estatística Avançada: treinando...")

        # Chi-Quadrado
        if callback:
            callback("Calculando Chi-Quadrado...")
        self.resultado_chi2, self.scores_chi2 = \
            self.calcular_chi2(resultados)

        # Chi-Quadrado recente (últimos 50)
        _, self.scores_chi2_recente = \
            self.calcular_chi2(resultados, janela=50)

        # Bayes + Bernoulli
        if callback:
            callback("Treinando filtro Bayesiano...")
        self.treinar_bayes(resultados)

        self.treinado = True

        if callback:
            callback("Estatística Avançada: concluído!")

    def score_completo(self, dezenas, ultimo_resultado):
        """Score combinado de todos os módulos estatísticos"""
        if not self.treinado:
            return 0.5

        try:
            s_chi2  = self.chi2_score_jogo(dezenas, self.scores_chi2)
            s_chi2r = self.chi2_score_jogo(dezenas, self.scores_chi2_recente)
            s_bayes = self.score_bayes_jogo(dezenas, ultimo_resultado)
            s_kl    = self.score_kl_jogo(dezenas)

            return float(
                s_chi2  * 0.25 +
                s_chi2r * 0.25 +
                s_bayes * 0.30 +
                s_kl    * 0.20
            )
        except Exception:
            return 0.5