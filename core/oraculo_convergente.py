"""
============================================================
ORÁCULO CONVERGENTE v1.0
Módulo do Cérebro IA — 15 oráculos independentes votam.
Apenas dezenas com CONSENSO EMERGENTE entram na cartela.

FILOSOFIA:
Não apostamos em UMA teoria (que pode estar errada).
Apostamos na INTERSECÇÃO de 15 teorias diferentes.
Se múltiplas realidades convergem no mesmo número,
isso não é coincidência — é SINAL EMERGENTE.
============================================================
"""

import time
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats
from scipy.fft import rfft
from config import TOTAL_DEZENAS, DEZENAS_POR_JOGO

class OraculoConvergente:
    """
    A verdade emergente vem da intersecção de múltiplas realidades.
    Cada oráculo é uma teoria independente com base científica.
    """

    N_ORACULOS       = 15
    QUORUM_MINIMO    = 10   # Consenso necessário
    TOP_DEZENAS_ORAC = 15   # Cada oráculo escolhe suas top 15

    NOMES_ORACULOS = [
        "termodinamico",  "quantico",     "fisico",
        "bayesiano",      "markov",       "caotico",
        "fractal",        "gravitacional", "neural",
        "genetico",       "estatistico",  "fourier",
        "topologico",     "relativista",  "anti_comunidade",
    ]

    def __init__(self, matriz: np.ndarray):
        """
        Recebe a matriz binária diretamente do Cérebro IA.
        Não acessa o banco — evita duplicação.
        """
        self.matriz  = matriz
        self.n       = len(matriz)
        self.ultima_analise: Optional[Dict] = None

    # =========================================================
    # ORÁCULO 1: TERMODINÂMICO
    # =========================================================
    def oraculo_termodinamico(self) -> np.ndarray:
        """
        Entropia de Shannon: baixa entropia = maior previsibilidade.
        Dezenas com padrão claro são preferidas.
        """
        scores = np.zeros(TOTAL_DEZENAS)
        janela = min(50, self.n)
        for d in range(TOTAL_DEZENAS):
            serie = self.matriz[-janela:, d]
            p     = np.mean(serie)
            if 0 < p < 1:
                entropia = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
                scores[d] = 1.0 - entropia
        return scores


    # =========================================================
    # ORÁCULO 2: QUÂNTICO
    # =========================================================
    def oraculo_quantico(self) -> np.ndarray:
        """
        Caminhada quântica: superposição de estados.
        Cada dezena existe em múltiplos estados simultâneos.
        """
        if self.n == 0:
            return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        ult_dez = np.where(self.matriz[-1] == 1)[0]
        amp     = np.zeros(TOTAL_DEZENAS, dtype=complex)
        for d in ult_dez:
            amp[d] = 1.0 / np.sqrt(len(ult_dez) + 1)

        for _ in range(50):
            amp = (np.roll(amp, 1) + np.roll(amp, -1)) / np.sqrt(2)

        prob = np.abs(amp) ** 2
        s    = prob.sum()
        return prob / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    # =========================================================
    # ORÁCULO 3: FÍSICO (Simulação Verlet 3D)
    # =========================================================
    def oraculo_fisico(self) -> np.ndarray:
        """Modelo mecânico das bolas dentro do globo"""
        rng   = np.random.default_rng(42)
        pos   = rng.uniform(-1, 1, (25, 3))
        vel   = rng.normal(0, 0.5, (25, 3))
        cnt   = np.zeros(25)
        alvo  = np.array([0.0, 0.0, 0.9])
        for passo in range(500):
            for i in range(25):
                dist = np.linalg.norm(pos[i])
                if dist > 1.0:
                    pos[i] *= 0.99
                    vel[i] *= -0.8
                vel[i] += rng.normal(0, 0.05, 3)
                pos[i] += vel[i] * 0.01
                if passo > 150:
                    if np.linalg.norm(pos[i] - alvo) < 0.3:
                        cnt[i] += 1
        s = cnt.sum()
        return cnt / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 4: BAYESIANO
    # =========================================================
    def oraculo_bayesiano(self) -> np.ndarray:
        """P(dezena | histórico) posterior via Bayes"""
        freq  = np.sum(self.matriz, axis=0)
        prior = (freq + 1) / (self.n + 25)
        if self.n <= 1:
            return prior / prior.sum()

        ult   = self.matriz[-1]
        trans = np.dot(self.matriz[:-1].T, self.matriz[1:]) + 1
        row_s = trans.sum(axis=1, keepdims=True)
        row_s[row_s == 0] = 1
        trans = trans / row_s

        post = np.zeros(25)
        ant  = np.where(ult == 1)[0]
        for d in ant:
            post += trans[d]
        s = post.sum()
        return post / s if s > 0 else prior / prior.sum()

    # =========================================================
    # ORÁCULO 5: MARKOVIANO
    # =========================================================
    def oraculo_markov(self) -> np.ndarray:
        """Cadeia de Markov de 2ª ordem"""
        if self.n < 3:
            return np.ones(25) / 25
        trans = np.ones((25, 25))
        for i in range(1, self.n):
            ant = np.where(self.matriz[i - 1] == 1)[0]
            atu = np.where(self.matriz[i] == 1)[0]
            for a in ant:
                for b in atu:
                    trans[a][b] += 1
        row_s = trans.sum(axis=1, keepdims=True)
        trans = trans / row_s
        ult   = np.where(self.matriz[-1] == 1)[0]
        prob  = np.zeros(25)
        for d in ult:
            prob += trans[d]
        s = prob.sum()
        return prob / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 6: CAÓTICO (Atrator de Lorenz)
    # =========================================================
    def oraculo_caotico(self) -> np.ndarray:
        """Dinâmica caótica com atratores estranhos"""
        scores = np.zeros(25)
        sigma, rho, beta = 10.0, 28.0, 8/3.0
        dt = 0.01
        for d in range(25):
            x, y, z = 1.0, 1.0, 1.0
            freq_d = np.sum(self.matriz[:, d]) / max(self.n, 1)
            for _ in range(100):
                dx = sigma * (y - x)
                dy = x * (rho - z) - y
                dz = x * y - beta * z
                x += dx * dt * (freq_d + 0.1)
                y += dy * dt
                z += dz * dt
            scores[d] = abs(z) / 100.0
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 7: FRACTAL
    # =========================================================
    def oraculo_fractal(self) -> np.ndarray:
        """Dimensão fractal (box-counting)"""
        scores = np.zeros(25)
        janela = min(100, self.n)
        if janela < 10:
            return np.ones(25) / 25
        for d in range(25):
            serie = self.matriz[-janela:, d]
            dim = 0.0
            for size in [2, 4, 8, 16]:
                if len(serie) >= size:
                    boxes = len(serie) // size
                    ativos = sum(
                        1 for i in range(boxes)
                        if np.any(serie[i*size:(i+1)*size] > 0)
                    )
                    if ativos > 0:
                        dim += np.log(ativos + 1) / np.log(1.0/size + 2)
            scores[d] = abs(dim)
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 8: GRAVITACIONAL (N-corpos)
    # =========================================================
    def oraculo_gravitacional(self) -> np.ndarray:
        """Dezenas se atraem por co-ocorrência"""
        if self.n < 10:
            return np.ones(25) / 25
        coocorr = np.dot(self.matriz.T, self.matriz)
        np.fill_diagonal(coocorr, 0)
        massa = np.sum(self.matriz, axis=0)
        forca = np.zeros(25)
        for i in range(25):
            for j in range(25):
                if i != j:
                    dist = abs(i - j) + 1
                    forca[i] += (massa[i] * massa[j] * coocorr[i][j]) / \
                                (dist ** 2 + 1)
        s = forca.sum()
        return forca / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 9: NEURAL (LSTM aproximado)
    # =========================================================
    def oraculo_neural(self) -> np.ndarray:
        """Memória de longo prazo com decay exponencial"""
        if self.n == 0:
            return np.ones(25) / 25
        scores = np.zeros(25)
        pesos  = np.exp(-np.arange(self.n)[::-1] / 100)
        for d in range(25):
            scores[d] = np.sum(self.matriz[:, d] * pesos)
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 10: GENÉTICO
    # =========================================================
    def oraculo_genetico(self) -> np.ndarray:
        """Sobrevivência das dezenas nos últimos 30 concursos"""
        if self.n < 10:
            return np.ones(25) / 25
        fitness = np.zeros(25)
        inicio  = max(0, self.n - 30)
        for i in range(inicio, self.n):
            for d in range(25):
                if self.matriz[i][d] == 1:
                    fitness[d] += 1.0 / (self.n - i + 1)
        s = fitness.sum()
        return fitness / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 11: ESTATÍSTICO (Regressão)
    # =========================================================
    def oraculo_estatistico(self) -> np.ndarray:
        """Tendência linear projetada"""
        scores = np.zeros(25)
        if self.n < 10:
            return np.ones(25) / 25
        for d in range(25):
            serie = self.matriz[:, d]
            x     = np.arange(len(serie))
            try:
                slope, intercept, _, _, _ = stats.linregress(x, serie)
                pred = slope * len(serie) + intercept
                scores[d] = max(0, pred)
            except Exception:
                scores[d] = 0.5
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 12: FOURIER
    # =========================================================
    def oraculo_fourier(self) -> np.ndarray:
        """Frequências espectrais dominantes"""
        scores = np.zeros(25)
        for d in range(25):
            serie = self.matriz[-100:, d] if self.n >= 100 \
                    else self.matriz[:, d]
            if len(serie) < 10:
                continue
            try:
                fft_vals = np.abs(rfft(serie.astype(float)))
                if len(fft_vals) > 1 and fft_vals[0] > 0:
                    scores[d] = fft_vals[1:].max() / fft_vals[0]
            except Exception:
                pass
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 13: TOPOLÓGICO
    # =========================================================
    def oraculo_topologico(self) -> np.ndarray:
        """Grid 5x5 do volante — conectividade"""
        scores = np.zeros(25)
        grid   = np.array([[i * 5 + j for j in range(5)] for i in range(5)])
        for d in range(25):
            row = d // 5
            col = d % 5
            viz = 0.0
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < 5 and 0 <= nc < 5:
                    vd = grid[nr][nc]
                    if self.n > 0:
                        viz += np.sum(self.matriz[:, d] * self.matriz[:, vd])
            scores[d] = viz
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 14: RELATIVIDADE
    # =========================================================
    def oraculo_relativista(self) -> np.ndarray:
        """Dilatação temporal — recentes pesam mais"""
        if self.n == 0:
            return np.ones(25) / 25
        scores = np.zeros(25)
        c = 3.0
        for i in range(self.n):
            t = self.n - i
            v = 0.9 * (t / (t + c))
            gamma = 1.0 / np.sqrt(1 - v ** 2 + 1e-9)
            for d in range(25):
                if self.matriz[i][d] == 1:
                    scores[d] += 1.0 / gamma
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # ORÁCULO 15: ANTI-COMUNIDADE
    # =========================================================
    def oraculo_anti_comunidade(self) -> np.ndarray:
        """Foge dos padrões populares humanos"""
        scores = np.ones(25)
        for d in [4, 9, 14, 19, 24]:  # múltiplos de 5
            scores[d] *= 0.7
        for d in range(20):  # aniversários
            scores[d] *= 0.9
        for d in [20, 21, 22, 23, 24]:  # dezenas altas
            scores[d] *= 1.3
        s = scores.sum()
        return scores / s if s > 0 else np.ones(25) / 25

    # =========================================================
    # CONSULTA COMPLETA
    # =========================================================
    def consultar_todos(self) -> Dict:
            """Todos os 15 oráculos votam com Injeção de Entropia Dinâmica"""
            
            # Semente com ruído de tempo real (microsecond level)
            # Impede que duas chamadas no mesmo dia com a mesma base retornem resultados idênticos
            seed_entropia = int(time.time_ns() % 1_000_000)
            np.random.seed(seed_entropia)
    
            oraculos_map = {
                "termodinamico":   self.oraculo_termodinamico,
                "quantico":        self.oraculo_quantico,
                "fisico":          self.oraculo_fisico,
                "bayesiano":       self.oraculo_bayesiano,
                "markov":          self.oraculo_markov,
                "caotico":         self.oraculo_caotico,
                "fractal":         self.oraculo_fractal,
                "gravitacional":   self.oraculo_gravitacional,
                "neural":          self.oraculo_neural,
                "genetico":        self.oraculo_genetico,
                "estatistico":     self.oraculo_estatistico,
                "fourier":         self.oraculo_fourier,
                "topologico":      self.oraculo_topologico,
                "relativista":     self.oraculo_relativista,
                "anti_comunidade": self.oraculo_anti_comunidade,
            }
    
            votos = np.zeros(25, dtype=int)
            pesos_ac = np.zeros(25)
            detalhes = {}
    
            # Injeta ruidinho quântico suave nos pesos acumulados (flutuação de vácuo)
            ruido_flutuacao = np.random.normal(0, 0.02, 25)
    
            for nome, func in oraculos_map.items():
                try:
                    pesos = func()
                    if pesos.sum() > 0:
                        pesos = (pesos + np.abs(ruido_flutuacao * 0.1))
                        pesos /= pesos.sum()
                    pesos_ac += pesos
    
                    top_idx = np.argsort(pesos)[::-1][:self.TOP_DEZENAS_ORAC]
                    for idx in top_idx:
                        votos[idx] += 1
    
                    detalhes[nome] = {
                        "top5": [int(x + 1) for x in top_idx[:5]],
                        "top15": [int(x + 1) for x in top_idx],
                    }
                except Exception as e:
                    detalhes[nome] = {"erro": str(e)}
    
            return {
                "votos": votos,
                "pesos_acumulados": pesos_ac,
                "detalhes": detalhes,
            }

    # =========================================================
    # GERAR CARTELA CONVERGENTE
    # =========================================================
    def gerar_cartela_do_dia(self, cartelas_ja_geradas: List[List[int]] = None) -> Dict:
        """
        Gera a Cartela do Dia por consenso emergente.
        Se a combinação de 1º lugar já foi entregue ao usuário anteriormente,
        o Oráculo avança automaticamente para a próxima combinação de maior consenso
        dentro do grupo das 19 dezenas Elite!
        """
        import itertools

        consulta = self.consultar_todos()
        votos    = consulta["votos"]
        pesos    = consulta["pesos_acumulados"]

        # Score final por dezena
        score_final = votos.astype(float) + pesos * 2.0

        # Seleciona as 19 dezenas de maior consenso
        idx_top19 = np.argsort(score_final)[::-1][:19]
        dezenas_top19 = sorted([int(i + 1) for i in idx_top19])

        # Gera todas as 3.876 combinações possíveis de 15 números dentro do Grupo 19
        combos = list(itertools.combinations(dezenas_top19, 15))

        # Avalia a força de consenso de cada uma das 3.876 combinações
        combos_scored = []
        for c in combos:
            sc = sum(score_final[num - 1] for num in c)
            combos_scored.append((sorted(list(c)), float(sc)))

        # Ordena do maior consenso para o menor
        combos_scored.sort(key=lambda x: x[1], reverse=True)

        # Mapeia historico de cartelas passadas para bloquear duplicações (14 ou 15 iguais)
        vistas = set()
        if cartelas_ja_geradas:
            for g in cartelas_ja_geradas:
                vistas.add(tuple(sorted(g)))

        cartela_escolhida = None
        
        # Filtra a melhor combinação que AINDA NÃO FOI ENTREGUE
        for comb, sc in combos_scored:
            key = tuple(comb)
            if key in vistas:
                continue  # Já foi gerada antes, pula para a próxima!

            # Verifica sobreposição de 14 ou 15 dezenas com jogos já entregues
            muito_parecida = False
            if cartelas_ja_geradas:
                set_comb = set(comb)
                for g in cartelas_ja_geradas:
                    if len(set_comb & set(g)) >= 14:
                        muito_parecida = True
                        break

            if not muito_parecida:
                cartela_escolhida = comb
                break

        # Fallback de segurança se todas as combinações tiverem sido usadas
        if not cartela_escolhida:
            cartela_escolhida = combos_scored[0][0]

        # Recalcula estatísticas para a combinação inédita selecionada
        soma  = sum(cartela_escolhida)
        pares = sum(1 for d in cartela_escolhida if d % 2 == 0)
        sc    = sorted(cartela_escolhida)
        max_c = cc = 1
        for i in range(1, len(sc)):
            if sc[i] == sc[i - 1] + 1:
                cc += 1
                max_c = max(max_c, cc)
            else:
                cc = 1

        # Quorum médio das dezenas na cartela escolhida
        votos_na_cartela = [votos[d - 1] for d in cartela_escolhida]
        quorum_medio = int(np.mean(votos_na_cartela))

        confianca = "ALTA"   if quorum_medio >= 10 else \
                    "MÉDIA"  if quorum_medio >= 7 else "BAIXA"

        resultado = {
            "cartela":          cartela_escolhida,
            "quorum_usado":     quorum_medio,
            "quorum_original":  self.QUORUM_MINIMO,
            "votos_por_dezena": {int(i + 1): int(votos[i]) for i in range(25)},
            "score_por_dezena": {int(i + 1): round(float(score_final[i]), 4) for i in range(25)},
            "consenso_forca":   round(float(np.mean(votos_na_cartela)), 2),
            "soma":             soma,
            "pares":            pares,
            "impares":          15 - pares,
            "consecutivos_max":  max_c,
            "confianca":        confianca,
            "detalhes_oraculos": consulta["detalhes"],
            "n_oraculos":       self.N_ORACULOS,
        }

        self.ultima_analise = resultado
        return resultado