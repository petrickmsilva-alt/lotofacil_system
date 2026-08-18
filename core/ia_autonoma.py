"""
============================================================
IA AUTÔNOMA v3.0 — ORQUESTRADOR COMPLETO
Controla, aprende e decide usando todos os 14 módulos
============================================================
"""
import numpy as np
import json
import os
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
import joblib

from config import (
    TOTAL_DEZENAS, DEZENAS_POR_JOGO, MODELS_PATH,
    PRIMOS, FIBONACCI, BORDA, QUADRANTES
)
from .bitmatrix       import BitMatrix
from .filtros_gaussianos import FiltrosGaussianos
from .markov_engine   import MarkovEngine
from .fisica_quantica import FisicaQuantica
from .covering_designs import CoveringDesigns
from .verlet_3d       import VerletSimulator3D
from .quantum_walk    import QuantumWalk
from .estatistica_avancada import EstatisticaAvancada
from .algoritmo_genetico   import AlgoritmoGeneticoIlhas
from .spsa_optimizer  import SPSAOptimizer
from .meta_stacking   import MetaStacking


class IAAutonoma:

    def __init__(self):
        # ── Módulos base ──────────────────────────────────────
        self.bitmatrix   = BitMatrix()
        self.filtros     = FiltrosGaussianos()
        self.markov      = MarkovEngine()
        self.fisica      = FisicaQuantica()
        self.covering    = CoveringDesigns()

        # ── Novos módulos ─────────────────────────────────────
        self.verlet      = VerletSimulator3D(seed=42)
        self.quantum     = QuantumWalk()
        self.estatistica = EstatisticaAvancada()
        self.genetico    = AlgoritmoGeneticoIlhas(
            n_ilhas=4, tamanho_ilha=60,
            n_geracoes=80, taxa_mutacao=0.06,
        )
        self.spsa        = SPSAOptimizer(n_iteracoes=100)
        self.stacking    = MetaStacking()

        # ── Modelos ML ────────────────────────────────────────
        self.scaler      = StandardScaler()
        self._init_modelos()
        self.modelos_por_dezena = {}

        # ── Estado ────────────────────────────────────────────
        self.versao      = "3.0.0"
        self.treinado    = False
        self.historico   = []

        # ── Pesos (serão otimizados pelo SPSA) ───────────────
        self.pesos = {
            "markov":     0.15,
            "fisico":     0.08,
            "gaussiano":  0.12,
            "ml":         0.15,
            "verlet":     0.10,
            "quantum":    0.10,
            "chi2":       0.08,
            "bayes":      0.10,
            "kl":         0.07,
            "stacking":   0.05,
        }

    def _init_modelos(self):
        self.modelo_rf = RandomForestClassifier(
            n_estimators=200, max_depth=15,
            min_samples_split=5, random_state=42, n_jobs=-1
        )
        self.modelo_gb = GradientBoostingClassifier(
            n_estimators=150, max_depth=8,
            learning_rate=0.1, random_state=42
        )
        self.modelo_nn = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu", max_iter=500, random_state=42
        )

    # =========================================================
    # TREINAMENTO COMPLETO
    # =========================================================

    def treinar(self, resultados, callback=None):
        """
        Treina todos os módulos.
        Cada etapa tem timeout e fallback.
        """
        import time
        self.historico = resultados
        n = len(resultados)

        if n < 50:
            return {"status": "erro", "msg": "Minimo 50 concursos"}

        def cb(msg):
            if callback:
                callback(msg)
            print("[IA] {}".format(msg))

        def executar_com_timeout(nome, func, timeout_seg=30):
            """Executa função com aviso se demorar"""
            import threading
            resultado = [None]
            erro      = [None]
            concluido = [False]

            def run():
                try:
                    resultado[0] = func()
                    concluido[0] = True
                except Exception as e:
                    erro[0]      = str(e)
                    concluido[0] = True

            t = threading.Thread(target=run, daemon=True)
            t.start()
            t.join(timeout=timeout_seg)

            if not concluido[0]:
                print("[IA] AVISO: {} excedeu {}s — continuando".format(
                    nome, timeout_seg
                ))
                return False
            if erro[0]:
                print("[IA] {} erro: {}".format(nome, erro[0]))
                return False
            return True

        t_inicio = time.time()
        cb("Iniciando treino com {} concursos...".format(n))

        # 1. Markov (rapido ~2s)
        cb("1/10 Markov Engine...")
        executar_com_timeout("Markov", lambda: self.markov.treinar(resultados), 30)
        cb("    Markov: {:.1f}s".format(time.time() - t_inicio))

        # 2. Fisica (rapido ~3s)
        t2 = time.time()
        cb("2/10 Fisica das Bolas...")
        executar_com_timeout("Fisica",
            lambda: self.fisica.treinar(resultados, n_simulacoes=2), 30)
        cb("    Fisica: {:.1f}s".format(time.time() - t2))

        # 3. Filtros Gaussianos (rapido ~1s)
        t3 = time.time()
        cb("3/10 Filtros Gaussianos...")
        try:
            self.filtros = FiltrosGaussianos(resultados)
            cb("    Filtros: {:.1f}s".format(time.time() - t3))
        except Exception as e:
            print("[IA] Filtros erro: {}".format(e))

        # 4. Verlet 3D (medio ~15s com 4 sims)
        t4 = time.time()
        cb("4/10 Verlet 3D (4 simulacoes)...")
        self.verlet = VerletSimulator3D(seed=42)
        executar_com_timeout("Verlet",
            lambda: self.verlet.treinar(resultados, n_simulacoes=4, callback=cb),
            60)
        cb("    Verlet: {:.1f}s".format(time.time() - t4))

        # 5. Quantum Walk (medio ~10s)
        t5 = time.time()
        cb("5/10 Quantum Walks...")
        executar_com_timeout("Quantum",
            lambda: self.quantum.treinar(resultados, callback=cb), 45)
        cb("    Quantum: {:.1f}s".format(time.time() - t5))

        # 6. Estatistica Avancada (rapido ~3s)
        t6 = time.time()
        cb("6/10 Estatistica (Chi2 + Bayes + KL)...")
        executar_com_timeout("Estatistica",
            lambda: self.estatistica.treinar(resultados, callback=cb), 30)
        cb("    Estatistica: {:.1f}s".format(time.time() - t6))

        # 7. Machine Learning (medio ~20s)
        t7 = time.time()
        cb("7/10 Machine Learning (RF + GB + NN)...")
        try:
            X, y = self.preparar_dados_treino(resultados)
            if len(X) >= 30:
                self.scaler.fit(X)
                X_sc      = self.scaler.transform(X)
                y_score   = np.mean(y, axis=1)
                y_binario = self._criar_target_binario(y_score)

                try:
                    self.modelo_rf.fit(X_sc, y_binario)
                    cb("    RF: OK")
                except Exception as e:
                    print("[IA] RF: {}".format(e))

                try:
                    if self._tem_duas_classes(y_binario):
                        self.modelo_gb.fit(X_sc, y_binario)
                        cb("    GB: OK")
                except Exception as e:
                    print("[IA] GB: {}".format(e))

                try:
                    if self._tem_duas_classes(y_binario):
                        self.modelo_nn.fit(X_sc, y_binario)
                        cb("    NN: OK")
                except Exception as e:
                    print("[IA] NN: {}".format(e))

                # Modelos por dezena
                self.modelos_por_dezena = {}
                for d in range(25):
                    try:
                        y_d = y[:, d]
                        if len(np.unique(y_d)) < 2:
                            continue
                        if np.min(np.bincount(y_d)) < 3:
                            continue
                        rf_d = RandomForestClassifier(
                            n_estimators=50,
                            max_depth=8,
                            random_state=42,
                            n_jobs=-1,
                        )
                        rf_d.fit(X_sc, y_d)
                        self.modelos_por_dezena[d] = rf_d
                    except Exception:
                        pass

                cb("    Modelos/dezena: {}/25".format(
                    len(self.modelos_por_dezena)
                ))

        except Exception as e:
            print("[IA] ML erro: {}".format(e))

        cb("    ML total: {:.1f}s".format(time.time() - t7))

        # 8. SPSA (rapido ~5s com nova versao)
        t8 = time.time()
        cb("8/10 SPSA (calibracao rapida)...")
        executar_com_timeout("SPSA",
            lambda: self._calibrar_pesos_spsa(resultados, cb),
            60)   # max 60s
        cb("    SPSA: {:.1f}s".format(time.time() - t8))

        # 9. Meta Stacking
        t9 = time.time()
        cb("9/10 Meta Stacking...")
        try:
            if len(self.stacking.historico_pred) >= 10:
                self.stacking.treinar(callback=cb)
            else:
                cb("    Stacking: aguardando mais dados")
        except Exception as e:
            print("[IA] Stacking: {}".format(e))
        cb("    Stacking: {:.1f}s".format(time.time() - t9))

        # 10. Salvar
        cb("10/10 Salvando modelos...")
        self._salvar_modelos()
        try:
            self.stacking.salvar()
        except Exception:
            pass

        self.treinado   = True
        tempo_total     = time.time() - t_inicio

        msg = "Treinamento concluido em {:.1f}s | {} concursos | {}/25 modelos".format(
            tempo_total, n, len(self.modelos_por_dezena)
        )
        cb(msg)

        return {
            "status":         "ok",
            "concursos":      n,
            "tempo_seg":      round(tempo_total, 1),
            "modelos_dezena": len(self.modelos_por_dezena),
        }

    # =========================================================
    # CALIBRAÇÃO SPSA
    # =========================================================

    def _calibrar_pesos_spsa(self, resultados, callback=None):
        """
        VERSÃO RÁPIDA do SPSA.
        Usa amostra pequena e função de perda leve.
        Tempo máximo: ~10 segundos.
        """
        if len(resultados) < 50:
            if callback:
                callback("SPSA: pulado (histórico insuficiente)")
            return

        if callback:
            callback("SPSA: iniciando calibração rápida...")

        # Usar apenas os últimos 30 concursos como referência
        amostra = resultados[-30:]
        n_ref   = min(5, len(amostra))   # testar contra apenas 5

        # Cache de frequência histórica (cálculo único)
        freq_hist = np.zeros(25)
        for r in resultados[-200:]:
            for i in range(1, 16):
                d = r["d{}".format(i)]
                if 1 <= d <= 25:
                    freq_hist[d - 1] += 1
        if freq_hist.max() > 0:
            freq_hist /= freq_hist.max()

        # Função de perda LEVE (sem gerar cartelas)
        def funcao_perda_rapida(pesos_lista):
            """
            Avalia os pesos usando score estatístico simples.
            Não gera cartelas — apenas calcula scores.
            """
            try:
                nomes = list(self.pesos.keys())
                pesos_dict = {}
                for idx in range(min(len(nomes), len(pesos_lista))):
                    pesos_dict[nomes[idx]] = float(pesos_lista[idx])

                # Score baseado em frequência histórica
                # Quanto maior a correlação com o histórico, menor a perda
                score_total = 0.0
                n_calc = 0

                for r_ref in amostra[-n_ref:]:
                    dez_real = set()
                    for i in range(1, 16):
                        dez_real.add(r_ref["d{}".format(i)])

                    # Score simples: frequência das dezenas reais
                    freq_media = 0.0
                    for d in dez_real:
                        freq_media += freq_hist[d - 1]
                    freq_media /= 15.0

                    # Penalizar pesos muito desbalanceados
                    p_vals = list(pesos_dict.values())
                    variancia = float(np.var(p_vals))
                    penalidade = variancia * 2.0

                    score_total += freq_media - penalidade
                    n_calc += 1

                if n_calc == 0:
                    return 1.0

                score_medio = score_total / n_calc
                # Perda = 1 - score (queremos maximizar score)
                perda = 1.0 - min(max(score_medio, 0.0), 1.0)
                return float(perda)

            except Exception as e:
                print("[SPSA] Erro perda: {}".format(e))
                return 1.0

        # Executar SPSA com poucos parâmetros e iterações
        nomes_pesos    = list(self.pesos.keys())
        valores_atuais = [self.pesos[k] for k in nomes_pesos]
        bounds         = [(0.03, 0.40)] * len(valores_atuais)

        # SPSA rápido: 30 iterações
        spsa_rapido = SPSAOptimizer(n_iteracoes=30)

        try:
            pesos_otim, loss = spsa_rapido.otimizar_pesos(
                funcao_perda_rapida,
                valores_atuais,
                bounds=bounds,
                callback=callback,
            )

            # Aplicar pesos otimizados
            for idx in range(len(nomes_pesos)):
                if idx < len(pesos_otim):
                    self.pesos[nomes_pesos[idx]] = round(
                        float(pesos_otim[idx]), 4
                    )

            spsa_rapido.salvar(pesos_otim)

            if callback:
                callback(
                    "SPSA: concluido! loss={:.4f}".format(loss)
                )

        except Exception as e:
            print("[SPSA] Erro otimizacao: {}".format(e))
            if callback:
                callback("SPSA: erro, mantendo pesos anteriores")

    # =========================================================
    # PREVISÃO COMPLETA
    # =========================================================

    def prever_dezenas(self, resultado_atual):
        """
        Orquestra todos os módulos para prever dezenas.
        Retorna top 20 dezenas e vetor de scores.
        """
        vetores = {}

        # Markov
        try:
            dez_markov = self.markov.dezenas_mais_provaveis(TOTAL_DEZENAS)
            v = np.zeros(TOTAL_DEZENAS)
            for rank, d in enumerate(dez_markov):
                v[d - 1] = 1.0 - rank / TOTAL_DEZENAS
            vetores["markov"] = v
        except Exception:
            vetores["markov"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Físico
        try:
            v = self.fisica.scores_fisicos.copy()
            vetores["fisico"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["fisico"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Gaussiano (frequência histórica)
        try:
            v = self.bitmatrix.heatmap_frequencia(self.historico)
            vetores["gaussiano"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["gaussiano"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # ML por dezena
        try:
            feat   = self.extrair_features(resultado_atual)
            feat_sc = self.scaler.transform(feat.reshape(1, -1))
            v = np.zeros(TOTAL_DEZENAS)
            for d, modelo in self.modelos_por_dezena.items():
                try:
                    p = modelo.predict_proba(feat_sc)
                    v[d] = p[0][1] if p.shape[1] > 1 else p[0][0]
                except Exception:
                    v[d] = 0.5
            vetores["ml"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["ml"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Verlet 3D
        try:
            v = self.verlet.scores_verlet.copy()
            vetores["verlet"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["verlet"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Quantum Walk
        try:
            v = self.quantum.prever_proximo(resultado_atual)
            vetores["quantum"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["quantum"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Chi²
        try:
            v = self.estatistica.scores_chi2.copy()
            vetores["chi2"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["chi2"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # Bayes
        try:
            dez_ant = [resultado_atual[f"d{i}"] for i in range(1, 16)]
            v = self.estatistica.posterior_bayes(dez_ant)
            vetores["bayes"] = v / (v.max() + 1e-9)
        except Exception:
            vetores["bayes"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # KL (inverso — dezenas com baixa divergência)
        try:
            v_kl = np.zeros(TOTAL_DEZENAS)
            for i in range(TOTAL_DEZENAS):
                dist_i = np.zeros(TOTAL_DEZENAS)
                dist_i[i] = 1.0
                v_kl[i] = 1.0 - min(
                    self.estatistica.calcular_kl(dist_i), 1.0
                )
            vetores["kl"] = v_kl / (v_kl.max() + 1e-9)
        except Exception:
            vetores["kl"] = np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        # ── Combinar via Meta-Stacking ────────────────────────
        scores_combinados = self.stacking.combinar_vetores(vetores)

        # Somar com pesos manuais como fallback
        scores_ponderados = np.zeros(TOTAL_DEZENAS)
        for motor, vetor in vetores.items():
            peso = self.pesos.get(motor, 0.1)
            scores_ponderados += np.array(vetor) * peso

        # Média entre stacking e ponderação manual
        scores_finais = (scores_combinados * 0.5 +
                         scores_ponderados * 0.5)

        if scores_finais.max() > 0:
            scores_finais /= scores_finais.max()

        ranking = np.argsort(scores_finais)[::-1]
        top_20  = [int(r + 1) for r in ranking[:20]]

        return top_20, scores_finais

    # =========================================================
    # GERAR CARTELAS (com AG de Ilhas)
    # =========================================================

    def gerar_cartelas(self, resultado_atual, n_cartelas=10):
        """
        Pipeline de geração SEM algoritmo genético no caminho crítico.
        AG roda apenas se tiver tempo disponível.
        """
        import time
        t_inicio = time.time()
        TIMEOUT  = 30  # segundos máximo para gerar

        if not self.historico:
            print("[GERAR] Sem histórico, usando fallback")
            return self._gerar_fallback(n_cartelas)

        # Fase 1: Dezenas candidatas (rápido)
        try:
            top_candidatas, scores = self.prever_dezenas(resultado_atual)
        except Exception as e:
            print("[GERAR] prever erro: {}".format(e))
            top_candidatas = list(range(1, 21))
            scores         = np.ones(25) * 0.5

        todas_cartelas = []

        # Fase 2: Monte Carlo (rápido ~1s)
        try:
            mc = self._monte_carlo_simples(top_candidatas, scores, n_cartelas * 3)
            todas_cartelas.extend(mc)
            print("[GERAR] Monte Carlo: {} cartelas".format(len(mc)))
        except Exception as e:
            print("[GERAR] MC erro: {}".format(e))

        # Fase 3: Covering Designs (rápido ~2s)
        if time.time() - t_inicio < TIMEOUT:
            try:
                cov = self.covering.gerar_cobertura_minima(
                    top_candidatas[:18],
                    min_acertos=13,
                    max_cartelas=min(n_cartelas, 10),
                )
                todas_cartelas.extend(cov)
                print("[GERAR] Covering: {} cartelas".format(len(cov)))
            except Exception as e:
                print("[GERAR] Covering erro: {}".format(e))

        # Fase 4: Verificar se já temos suficiente
        if len(todas_cartelas) < n_cartelas:
            extras = self._gerar_por_filtros(
                top_candidatas, n_cartelas - len(todas_cartelas)
            )
            todas_cartelas.extend(extras)

        # Fase 5: Rankear (rápido)
        rankeadas = self._rankear_cartelas(
            todas_cartelas, resultado_atual, scores
        )

        # Resultado final
        resultado = rankeadas[:n_cartelas]

        # Completar se necessário
        while len(resultado) < n_cartelas:
            resultado.extend(self._gerar_fallback(1))

        tempo = time.time() - t_inicio
        print("[GERAR] Concluido em {:.1f}s — {} cartelas".format(
            tempo, len(resultado)
        ))

        return resultado[:n_cartelas]


    def _monte_carlo_simples(self, candidatas, scores, n):
        """Monte Carlo rápido e simples"""
        cartelas = []
        todas    = list(range(1, 26))

        # Pesos para as candidatas
        pesos = np.zeros(25)
        for d in candidatas:
            if 1 <= d <= 25:
                pesos[d - 1] = float(scores[d - 1])

        # Dezenas fora do top também têm chance pequena
        for i in range(25):
            if pesos[i] == 0:
                pesos[i] = 0.01

        pesos = pesos / pesos.sum()

        tentativas = 0
        max_tent   = n * 10

        while len(cartelas) < n and tentativas < max_tent:
            tentativas += 1
            try:
                idx    = np.random.choice(25, size=15, replace=False, p=pesos)
                dezenas = sorted([int(i + 1) for i in idx])
                cartelas.append(dezenas)
            except Exception:
                # Fallback sem pesos
                idx     = np.random.choice(25, size=15, replace=False)
                dezenas = sorted([int(i + 1) for i in idx])
                cartelas.append(dezenas)

        return cartelas[:n]


    def _gerar_por_filtros(self, candidatas, n):
        """
        Gera cartelas respeitando os filtros estatísticos.
        Mais determinístico que Monte Carlo.
        """
        cartelas = []
        candidatas_ord = list(candidatas)

        # Estratégia 1: Top 15 direto
        if len(candidatas_ord) >= 15:
            c1 = sorted(candidatas_ord[:15])
            cartelas.append(c1)

        # Estratégia 2: Rotação das candidatas
        n_cand = len(candidatas_ord)
        for i in range(min(n * 3, 50)):
            if len(cartelas) >= n:
                break
            try:
                np.random.seed(i + 42)
                # Pegar 15 com deslocamento
                inicio = i % max(1, n_cand - 15)
                dez    = sorted(candidatas_ord[inicio:inicio + 15])

                if len(dez) < 15:
                    # Completar com outros
                    resto = [d for d in range(1, 26)
                             if d not in dez]
                    np.random.shuffle(resto)
                    dez = sorted(dez + resto[:15 - len(dez)])

                if len(dez) == 15:
                    cartelas.append(dez)

            except Exception:
                continue

        # Completar com aleatório se necessário
        while len(cartelas) < n:
            np.random.seed(len(cartelas) + 777)
            idx = np.random.choice(25, size=15, replace=False)
            cartelas.append(sorted([int(i + 1) for i in idx]))

        return cartelas[:n]


    def _rankear_cartelas(self, lista_cartelas, resultado_atual, scores):
        """
        Rankeia cartelas por score. Versão rápida.
        """
        rankeadas = []
        vistas    = set()

        for cartela in lista_cartelas:
            try:
                # Garantir formato correto
                if isinstance(cartela, dict):
                    dez = cartela.get("dezenas", [])
                else:
                    dez = list(cartela)

                dez = sorted([int(d) for d in dez])

                if len(dez) != 15:
                    continue

                # Evitar duplicatas
                key = tuple(dez)
                if key in vistas:
                    continue
                vistas.add(key)

                # Score rápido
                score_markov = 0.5
                score_fisico = 0.5
                score_gauss  = 0.5
                score_ml     = 0.5

                try:
                    score_markov = float(
                        self.markov.score_markov_jogo(dez)
                    )
                except Exception:
                    pass

                try:
                    score_fisico = float(
                        self.fisica.score_fisico_jogo(dez)
                    )
                except Exception:
                    pass

                try:
                    score_gauss = float(
                        self.filtros.calcular_score_gaussiano(dez)
                    )
                except Exception:
                    pass

                try:
                    score_ml = float(
                        np.mean([scores[d - 1] for d in dez])
                    )
                except Exception:
                    pass

                score_total = (
                    score_markov * 0.30 +
                    score_fisico * 0.15 +
                    score_gauss  * 0.30 +
                    score_ml     * 0.25
                )

                mask = self.bitmatrix.dezenas_para_bitmask(dez)

                rankeadas.append({
                    "dezenas":         dez,
                    "bitmask":         mask,
                    "score_ia":        round(score_ml,     4),
                    "score_markov":    round(score_markov, 4),
                    "score_fisico":    round(score_fisico, 4),
                    "score_gaussiano": round(score_gauss,  4),
                    "score_entropia":  round(score_ml,     4),
                    "score_total":     round(score_total,  4),
                })

            except Exception as e:
                print("[RANK] Erro: {}".format(e))
                continue

        # Ordenar pelo score total
        rankeadas.sort(key=lambda x: x["score_total"], reverse=True)

        return rankeadas
    # =========================================================
    # SCORE COMPLETO DE UM JOGO
    # =========================================================

    def _score_completo(self, dezenas, resultado_atual, scores_globais):
        """Calcula score usando TODOS os módulos"""
        scores_motores = {}

        try:
            scores_motores["markov"] = self.markov.score_markov_jogo(dezenas)
        except Exception:
            scores_motores["markov"] = 0.5

        try:
            scores_motores["fisico"] = self.fisica.score_fisico_jogo(dezenas)
        except Exception:
            scores_motores["fisico"] = 0.5

        try:
            scores_motores["gaussiano"] = \
                self.filtros.calcular_score_gaussiano(dezenas)
        except Exception:
            scores_motores["gaussiano"] = 0.5

        try:
            scores_motores["ml"] = float(
                np.mean([scores_globais[d - 1] for d in dezenas])
            )
        except Exception:
            scores_motores["ml"] = 0.5

        try:
            scores_motores["verlet"] = self.verlet.score_jogo(dezenas)
        except Exception:
            scores_motores["verlet"] = 0.5

        try:
            scores_motores["quantum"] = self.quantum.score_jogo(
                dezenas, resultado_atual
            )
        except Exception:
            scores_motores["quantum"] = 0.5

        try:
            scores_motores["chi2"] = self.estatistica.chi2_score_jogo(
                dezenas, self.estatistica.scores_chi2
            )
        except Exception:
            scores_motores["chi2"] = 0.5

        try:
            scores_motores["bayes"] = self.estatistica.score_bayes_jogo(
                dezenas, resultado_atual
            )
        except Exception:
            scores_motores["bayes"] = 0.5

        try:
            scores_motores["kl"] = self.estatistica.score_kl_jogo(dezenas)
        except Exception:
            scores_motores["kl"] = 0.5

        # Meta-Stacking combina tudo
        score_final = self.stacking.combinar_scores(scores_motores)

        return float(score_final)

    # ── Métodos auxiliares (manter os existentes) ─────────────

    def extrair_features(self, resultado):
        try:
            dezenas     = [resultado[f"d{i}"] for i in range(1, 16)]
            dezenas_set = set(dezenas)
        except Exception:
            dezenas     = list(range(1, 16))
            dezenas_set = set(dezenas)

        features = []
        for i in range(1, TOTAL_DEZENAS + 1):
            features.append(1 if i in dezenas_set else 0)
        features.append(sum(dezenas))
        pares = sum(1 for d in dezenas if d % 2 == 0)
        features.append(pares)
        features.append(15 - pares)
        features.append(len(dezenas_set & PRIMOS))
        features.append(len(dezenas_set & FIBONACCI))
        features.append(len(dezenas_set & BORDA))
        for q, nums in QUADRANTES.items():
            features.append(len(dezenas_set & set(nums)))
        sorted_d   = sorted(dezenas)
        max_c = 1; curr = 1
        for i in range(1, len(sorted_d)):
            if sorted_d[i] == sorted_d[i-1] + 1:
                curr += 1; max_c = max(max_c, curr)
            else:
                curr = 1
        features.append(max_c)
        features.append(sorted_d[-1] - sorted_d[0])
        features.append(float(np.mean(dezenas)))
        features.append(float(np.std(dezenas)))
        baixas = sum(1 for d in dezenas if d <= 12)
        features.append(baixas)
        features.append(15 - baixas)
        return np.array(features, dtype=float)

    def preparar_dados_treino(self, resultados):
        X, y = [], []
        for i in range(len(resultados) - 1):
            try:
                feat = self.extrair_features(resultados[i])
                X.append(feat)
                dez_prox = set(resultados[i+1][f"d{j}"] for j in range(1,16))
                target   = [1 if d in dez_prox else 0 for d in range(1, 26)]
                y.append(target)
            except Exception:
                continue
        return np.array(X, dtype=float), np.array(y, dtype=int)

    def _criar_target_binario(self, y_score):
        n = len(y_score)
        for func in [np.median, np.mean]:
            ref   = func(y_score)
            y_bin = (y_score > ref).astype(int)
            if len(np.unique(y_bin)) >= 2:
                return y_bin
        idx   = np.argsort(y_score)
        y_bin = np.zeros(n, dtype=int)
        y_bin[idx[n//2:]] = 1
        if len(np.unique(y_bin)) >= 2:
            return y_bin
        y_bin[::2] = 1
        return y_bin

    def _tem_duas_classes(self, y):
        return len(np.unique(y)) >= 2

    def _monte_carlo(self, candidatas, scores, n):
        cartelas = []
        pesos = np.array([float(scores[d-1]) for d in candidatas])
        pesos = np.clip(pesos, 0.01, None) / pesos.sum()
        for _ in range(n * 15):
            try:
                idx = np.random.choice(len(candidatas), size=DEZENAS_POR_JOGO,
                                        replace=False, p=pesos)
                c = sorted([candidatas[i] for i in idx])
                if len(c) == DEZENAS_POR_JOGO:
                    cartelas.append(c)
                if len(cartelas) >= n:
                    break
            except Exception:
                continue
        return cartelas

    def _gerar_fallback(self, n):
        cartelas = []
        for i in range(n):
            np.random.seed(i + 9999)
            dez  = sorted(np.random.choice(25, size=15, replace=False) + 1)
            mask = self.bitmatrix.dezenas_para_bitmask(dez)
            cartelas.append({
                "dezenas": dez, "bitmask": mask,
                "score_ia": 0.5, "score_markov": 0.5,
                "score_fisico": 0.5, "score_gaussiano": 0.5,
                "score_entropia": 0.5, "score_total": 0.5,
            })
        return cartelas

    def aprender_com_erro(self, cartela, resultado_real, acertos):
        self.stacking.registrar_predicao(0, {}, acertos)
        fator = 0.02
        if acertos >= 14:
            for k in self.pesos:
                self.pesos[k] *= (1 + fator)
        elif acertos >= 11:
            self.pesos["gaussiano"] *= (1 + fator)
        else:
            self.pesos["stacking"] *= (1 + fator * 2)
        total = sum(self.pesos.values())
        for k in self.pesos:
            self.pesos[k] = round(self.pesos[k] / total, 4)

    def backtesting(self, resultados, n_cartelas=5, janela=100):
        if len(resultados) < janela + 10:
            return {"status": "erro", "msg": "Histórico insuficiente"}
        acertos_total  = {11:0, 12:0, 13:0, 14:0, 15:0}
        total_testes   = 0
        total_cartelas = 0
        inicio = max(janela, len(resultados) - 20)
        for i in range(inicio, min(inicio+15, len(resultados)-1)):
            try:
                self.markov.treinar(resultados[:i])
                cartelas  = self.gerar_cartelas(resultados[i-1], n_cartelas)
                mask_real = self.bitmatrix.dezenas_para_bitmask(
                    [resultados[i+1][f"d{j}"] for j in range(1,16)]
                )
                for c in cartelas:
                    acertos = self.bitmatrix.contar_acertos(
                        self.bitmatrix.dezenas_para_bitmask(c["dezenas"]),
                        mask_real
                    )
                    if acertos >= 11:
                        acertos_total[min(acertos,15)] += 1
                    total_cartelas += 1
                total_testes += 1
            except Exception as e:
                print(f"[BT] {e}")
        return {
            "status": "ok",
            "total_testes":   total_testes,
            "total_cartelas": total_cartelas,
            "acertos":        acertos_total,
            "taxa_13": round(acertos_total.get(13,0)/max(total_cartelas,1),4),
            "taxa_14": round(acertos_total.get(14,0)/max(total_cartelas,1),4),
            "taxa_15": round(acertos_total.get(15,0)/max(total_cartelas,1),4),
        }

    def _salvar_modelos(self):
        try:
            os.makedirs(MODELS_PATH, exist_ok=True)
            joblib.dump(self.modelo_rf, os.path.join(MODELS_PATH,"rf.pkl"))
            joblib.dump(self.scaler,    os.path.join(MODELS_PATH,"scaler.pkl"))
            if self.modelos_por_dezena:
                joblib.dump(self.modelos_por_dezena,
                            os.path.join(MODELS_PATH,"dezena.pkl"))
            with open(os.path.join(MODELS_PATH,"pesos.json"),"w") as f:
                json.dump(self.pesos, f, indent=2)
            print("[IA] Modelos salvos")
        except Exception as e:
            print(f"[IA] Erro salvar: {e}")

    def _carregar_modelos(self):
        try:
            p = os.path.join(MODELS_PATH,"rf.pkl")
            if not os.path.exists(p):
                return False
            self.modelo_rf = joblib.load(p)
            self.scaler    = joblib.load(os.path.join(MODELS_PATH,"scaler.pkl"))
            dp = os.path.join(MODELS_PATH,"dezena.pkl")
            if os.path.exists(dp):
                self.modelos_por_dezena = joblib.load(dp)
            pp = os.path.join(MODELS_PATH,"pesos.json")
            if os.path.exists(pp):
                with open(pp) as f:
                    self.pesos = json.load(f)
            self.stacking.carregar()
            self.treinado = True
            return True
        except Exception as e:
            print(f"[IA] Erro carregar: {e}")
            return False

    def get_status(self):
        return {
            "versao":           self.versao,
            "treinado":         self.treinado,
            "pesos":            self.pesos,
            "concursos_treino": len(self.historico),
            "modelos_dezena":   len(self.modelos_por_dezena),
            "stacking_treinado": self.stacking.treinado,
            "modulos_ativos":   10,
        }