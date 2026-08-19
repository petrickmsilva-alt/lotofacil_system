"""
============================================================
CICLO AUTÔNOMO FECHADO v1.0
Geração ➡️ Conferência ➡️ Aprendizado
A IA opera sozinha sem nenhuma intervenção humana.
============================================================
"""
import time
import json
import threading
import requests
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from config import DATABASE_PATH, VALOR_APOSTA
from database.db_manager import DBManager


class CicloAutonomo:
    """
    Motor de ciclo fechado que:
    1. Monitora a Caixa por novos resultados
    2. Gera cartelas automaticamente
    3. Confere contra resultado real
    4. Aprende com os erros
    5. Repete indefinidamente
    """

    URL_CAIXA    = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    URL_CONCURSO = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer":    "https://loterias.caixa.gov.br/",
        "Accept":     "application/json",
    }

    def __init__(self, agente, n_cartelas: int = 10):
        self.agente         = agente
        self.db             = DBManager()
        self.n_cartelas     = n_cartelas
        self.rodando        = False
        self.pausado        = False
        self.thread         = None
        self.log            = []
        self.ciclos_ok      = 0
        self.ciclos_erro    = 0
        self.ultimo_concurso_processado = 0
        self.proximo_sorteio = None
        self.estado         = "parado"
        self.historico_ciclos = []

        # Criar tabelas do ciclo
        self._criar_tabelas()

        # Carregar último concurso processado
        self.ultimo_concurso_processado = \
            self._get_ultimo_processado()

    # =========================================================
    # BANCO DE DADOS DO CICLO
    # =========================================================
    def _criar_tabelas(self):
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        # Fila de conferência
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fila_conferencia (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso_alvo   INTEGER NOT NULL,
                cartela_id      INTEGER,
                dezenas         TEXT NOT NULL,
                timestamp_geracao TEXT,
                scores_modulos  TEXT,
                score_total     REAL,
                status          TEXT DEFAULT 'aguardando',
                acertos         INTEGER DEFAULT 0,
                premio_ganho    REAL DEFAULT 0,
                dezenas_acertadas TEXT,
                timestamp_conferencia TEXT,
                erro_previsao   REAL DEFAULT 0
            )
        """)

        # Histórico de ciclos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_ciclos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso        INTEGER,
                timestamp_inicio TEXT,
                timestamp_fim   TEXT,
                fase            TEXT,
                status          TEXT,
                n_cartelas      INTEGER DEFAULT 0,
                melhor_acertos  INTEGER DEFAULT 0,
                media_acertos   REAL DEFAULT 0,
                total_ganho     REAL DEFAULT 0,
                pesos_antes     TEXT,
                pesos_depois    TEXT,
                log_ciclo       TEXT,
                erro_medio      REAL DEFAULT 0
            )
        """)

        # Memória de erros (para calibração futura)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memoria_erros (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso        INTEGER,
                timestamp       TEXT,
                filtro          TEXT,
                valor_esperado  REAL,
                valor_real      REAL,
                erro            REAL,
                peso_modulo     TEXT,
                impacto         REAL,
                correcao_aplicada TEXT
            )
        """)

        # Desempenho por filtro/módulo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS desempenho_modulos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso    INTEGER,
                timestamp   TEXT,
                modulo      TEXT,
                score_previsto REAL,
                acertos_real   INTEGER,
                correlacao     REAL,
                peso_atual     REAL,
                peso_ajustado  REAL
            )
        """)

        conn.commit()
        conn.close()

    def _get_ultimo_processado(self) -> int:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(concurso) FROM historico_ciclos
                WHERE status = 'completo'
            """)
            r = cursor.fetchone()[0]
            conn.close()
            return r or 0
        except Exception:
            return 0

    # =========================================================
    # MONITORAMENTO DA CAIXA
    # =========================================================
    def _buscar_ultimo_resultado(self) -> Optional[Dict]:
        try:
            resp = requests.get(
                self.URL_CAIXA,
                headers=self.HEADERS,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            self._log("ERRO", "Caixa API: {}".format(str(e)))
        return None

    def _buscar_concurso(self, numero: int) -> Optional[Dict]:
        try:
            resp = requests.get(
                self.URL_CONCURSO.format(numero),
                headers=self.HEADERS,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            self._log("ERRO", "Concurso {}: {}".format(numero, str(e)))
        return None

    def _extrair_dezenas(self, data_json: Dict) -> List[int]:
        try:
            return sorted([int(d) for d in data_json.get("listaDezenas", [])])
        except Exception:
            return []

    def _extrair_premios(self, data_json: Dict) -> Dict[int, float]:
        premios = {11: 7.0, 12: 14.0, 13: 35.0, 14: 0.0, 15: 0.0}
        try:
            for item in data_json.get("listaRateioPremio", []):
                ac  = int(item.get("numeroAcertos", 0))
                val = item.get("valorPremio", 0)
                if isinstance(val, str):
                    val = float(
                        val.replace("R$","").replace(".","")
                           .replace(",",".").strip()
                    )
                if ac in premios and float(val) > 0:
                    premios[ac] = float(val)
        except Exception:
            pass
        return premios

    def _calcular_data_proximo(self, data_json: Dict) -> Optional[str]:
        try:
            return data_json.get("dataProximoConcurso", None)
        except Exception:
            return None

    # =========================================================
    # FASE 1 — GERAÇÃO AUTÔNOMA
    # =========================================================
    def fase_geracao(self, concurso_alvo: int) -> List[Dict]:
        """
        A IA gera cartelas e as envia para a fila de conferência.
        """
        self._log("GERACAO", "Gerando {} cartelas para concurso {}".format(
            self.n_cartelas, concurso_alvo
        ))

        # Gerar com o agente autônomo (pipeline completo dos 14 módulos)
        cartelas = self.agente.moldurar_cartelas_autonomas(
            quantidade=self.n_cartelas,
            modo="hibrido",
        )

        if not cartelas:
            self._log("ERRO", "Agente não gerou cartelas.")
            return []

        # Salvar na fila de conferência
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        ids_fila = []

        for c in cartelas:
            try:
                cursor.execute("""
                    INSERT INTO fila_conferencia
                    (concurso_alvo, dezenas, timestamp_geracao,
                     scores_modulos, score_total, status)
                    VALUES (?,?,?,?,?,?)
                """, (
                    concurso_alvo,
                    json.dumps(c["dezenas"]),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    json.dumps(c.get("scores", {})),
                    float(c.get("score_total", 0)),
                    "aguardando",
                ))
                ids_fila.append(cursor.lastrowid)

                # Também salvar na tabela cartelas (para o frontend)
                dez = c["dezenas"]
                if len(dez) == 15:
                    cursor.execute("""
                        INSERT INTO cartelas
                        (data_geracao, concurso_alvo,
                         d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                         d11,d12,d13,d14,d15,
                         bitmask, score_ia, score_markov,
                         score_fisico, score_entropia, score_total)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                                ?,?,?,?,?,?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        concurso_alvo,
                        *dez,
                        0,
                        float(c.get("score_total", 0)),
                        float(c.get("scores", {}).get("markov",   0)),
                        float(c.get("scores", {}).get("verlet",   0)),
                        float(c.get("scores", {}).get("ev_prob",  0)),
                        float(c.get("score_total", 0)),
                    ))
            except Exception as e:
                self._log("AVISO", "Inserir fila: {}".format(str(e)))

        conn.commit()
        conn.close()

        self._log("GERACAO", "{} cartelas na fila de conferência".format(
            len(ids_fila)
        ))
        return cartelas

    # =========================================================
    # FASE 2 — CONFERÊNCIA AUTOMÁTICA
    # =========================================================
    def fase_conferencia(
        self,
        concurso: int,
        dezenas_reais: List[int],
        premios_reais: Dict[int, float],
    ) -> Dict[str, Any]:
        """
        Confere automaticamente todas as cartelas da fila
        contra o resultado real.
        """
        self._log("CONFERENCIA",
                  "Conferindo concurso {} | {}".format(
                      concurso, dezenas_reais
                  ))

        set_real = set(dezenas_reais)
        conn     = self.db.get_conn()
        cursor   = conn.cursor()

        # Buscar fila do concurso
        cursor.execute("""
            SELECT id, dezenas, scores_modulos, score_total
            FROM fila_conferencia
            WHERE concurso_alvo = ? AND status = 'aguardando'
        """, (concurso,))
        fila = cursor.fetchall()

        if not fila:
            conn.close()
            self._log("CONFERENCIA", "Fila vazia para concurso {}".format(
                concurso
            ))
            return {"status": "vazio", "conferidas": 0}

        resultados  = []
        acertos_dist = {i: 0 for i in range(16)}
        total_ganho  = 0.0

        for item in fila:
            fila_id     = item["id"]
            dez_cartela = json.loads(item["dezenas"])
            scores_mod  = {}
            try:
                scores_mod = json.loads(item["scores_modulos"] or "{}")
            except Exception:
                pass

            set_cartela = set(dez_cartela)
            acertos     = len(set_cartela & set_real)
            acertadas   = sorted(set_cartela & set_real)
            erradas     = sorted(set_cartela - set_real)

            # Prêmio
            premio = 0.0
            if acertos >= 11:
                premio = premios_reais.get(acertos, 0.0)

            # Erro de previsão
            score_prev  = float(item["score_total"] or 0)
            score_real  = acertos / 15.0
            erro_prev   = abs(score_prev - score_real)

            # Status
            if   acertos >= 15: status = "premio_15"
            elif acertos >= 14: status = "premio_14"
            elif acertos >= 13: status = "premio_13"
            elif acertos >= 12: status = "premio_12"
            elif acertos >= 11: status = "premio_11"
            else:               status = "sem_premio"

            # Atualizar fila
            cursor.execute("""
                UPDATE fila_conferencia SET
                    status                = ?,
                    acertos               = ?,
                    premio_ganho          = ?,
                    dezenas_acertadas     = ?,
                    timestamp_conferencia = ?,
                    erro_previsao         = ?
                WHERE id = ?
            """, (
                status,
                acertos,
                premio,
                json.dumps(acertadas),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round(erro_prev, 4),
                fila_id,
            ))

            # Atualizar tabela cartelas
            cursor.execute("""
                UPDATE cartelas SET
                    conferida    = 1,
                    acertos      = ?,
                    premio_ganho = ?,
                    status       = ?
                WHERE concurso_alvo = ?
                  AND d1  = ? AND d2  = ? AND d3  = ?
                  AND d4  = ? AND d5  = ? AND d6  = ?
                  AND d7  = ? AND d8  = ? AND d9  = ?
                  AND d10 = ? AND d11 = ? AND d12 = ?
                  AND d13 = ? AND d14 = ? AND d15 = ?
            """, (
                acertos, premio, status,
                concurso,
                *dez_cartela,
            ))

            acertos_dist[acertos] += 1
            total_ganho           += premio

            resultados.append({
                "fila_id":         fila_id,
                "dezenas":         dez_cartela,
                "acertos":         acertos,
                "dezenas_acertadas": acertadas,
                "dezenas_erradas":   erradas,
                "premio":          premio,
                "status":          status,
                "erro_previsao":   round(erro_prev, 4),
                "scores_modulos":  scores_mod,
            })

            # Salvar memória de erros por módulo
            for mod, score_m in scores_mod.items():
                try:
                    cursor.execute("""
                        INSERT INTO memoria_erros
                        (concurso, timestamp, filtro,
                         valor_esperado, valor_real, erro,
                         peso_modulo, impacto)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        concurso,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        mod,
                        float(score_m),
                        score_real,
                        abs(float(score_m) - score_real),
                        mod,
                        round(abs(float(score_m) - score_real) * \
                              float(self.agente.PESOS.get(mod, 0.1)), 4),
                    ))
                except Exception:
                    pass

        conn.commit()
        conn.close()

        melhor   = max((r["acertos"] for r in resultados), default=0)
        media    = sum(r["acertos"] for r in resultados) / max(len(resultados), 1)
        custo    = len(resultados) * VALOR_APOSTA
        lucro    = total_ganho - custo

        self._log("CONFERENCIA",
                  "Concurso {} | melhor={} | ganho=R${:.2f} | lucro=R${:.2f}".format(
                      concurso, melhor, total_ganho, lucro
                  ))

        return {
            "status":         "ok",
            "concurso":       concurso,
            "dezenas_reais":  dezenas_reais,
            "conferidas":     len(resultados),
            "distribuicao":   acertos_dist,
            "melhor_acertos": melhor,
            "media_acertos":  round(media, 2),
            "total_ganho":    round(total_ganho, 2),
            "custo":          round(custo, 2),
            "lucro":          round(lucro, 2),
            "resultados":     resultados,
        }

    # =========================================================
    # FASE 3 — APRENDIZADO E PERSISTÊNCIA
    # =========================================================
    def fase_aprendizado(
        self,
        concurso: int,
        resultado_conferencia: Dict,
        dezenas_reais: List[int],
    ) -> Dict[str, Any]:
        """
        Persiste o aprendizado e calibra pesos para o próximo ciclo.
        """
        self._log("APRENDIZADO",
                  "Aprendendo com concurso {}...".format(concurso))

        pesos_antes = dict(self.agente.PESOS)

        # Delegar ao agente
        cartelas_fmt = [
            {"dezenas": json.loads(r.get("dezenas", "[]"))
             if isinstance(r.get("dezenas"), str)
             else r.get("dezenas", [])}
            for r in resultado_conferencia.get("resultados", [])
        ]

        aprendizado = self.agente.aprender_com_resultado(
            concurso, dezenas_reais, cartelas_fmt
        )

        pesos_depois = dict(self.agente.PESOS)

        # Salvar desempenho por módulo
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        for mod, peso_atual in pesos_depois.items():
            # Buscar correlação média desse módulo com os acertos
            cursor.execute("""
                SELECT AVG(erro) FROM memoria_erros
                WHERE concurso = ? AND filtro = ?
            """, (concurso, mod))
            r = cursor.fetchone()
            erro_medio = float(r[0] or 0.5)

            cursor.execute("""
                INSERT INTO desempenho_modulos
                (concurso, timestamp, modulo,
                 score_previsto, acertos_real,
                 correlacao, peso_atual, peso_ajustado)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                concurso,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                mod,
                float(pesos_antes.get(mod, 0)),
                resultado_conferencia.get("melhor_acertos", 0),
                round(1 - erro_medio, 4),
                float(pesos_antes.get(mod, 0)),
                float(pesos_depois.get(mod, 0)),
            ))

        conn.commit()
        conn.close()

        # Log do que mudou
        mudancas = []
        for mod in pesos_antes:
            diff = pesos_depois.get(mod, 0) - pesos_antes.get(mod, 0)
            if abs(diff) > 0.0005:
                sinal = "↑" if diff > 0 else "↓"
                mudancas.append("{}: {:.4f} {} {:.4f}".format(
                    mod, pesos_antes[mod], sinal, pesos_depois[mod]
                ))

        if mudancas:
            self._log("PESOS", " | ".join(mudancas))

        return {
            "status":       "ok",
            "concurso":     concurso,
            "pesos_antes":  pesos_antes,
            "pesos_depois": pesos_depois,
            "mudancas":     mudancas,
        }

    # =========================================================
    # CICLO COMPLETO
    # =========================================================
    def executar_ciclo(self, concurso: int) -> Dict[str, Any]:
        """
        Executa um ciclo completo:
        Geração → Conferência → Aprendizado
        """
        t0     = time.time()
        log_ciclo = []

        self._log("CICLO", "=== INICIANDO CICLO {} ===".format(concurso))

        # Registrar início
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        pesos_inicio = json.dumps(dict(self.agente.PESOS))
        cursor.execute("""
            INSERT INTO historico_ciclos
            (concurso, timestamp_inicio, fase, status, pesos_antes)
            VALUES (?,?,?,?,?)
        """, (
            concurso,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iniciando",
            "em_andamento",
            pesos_inicio,
        ))
        ciclo_id = cursor.lastrowid
        conn.commit()
        conn.close()

        resultado_final = {
            "ciclo_id":  ciclo_id,
            "concurso":  concurso,
            "status":    "erro",
            "geracao":   {},
            "conferencia": {},
            "aprendizado": {},
        }

        try:
            # ── Fase 1: Geração ───────────────────────────────
            proximo = concurso + 1
            self._atualizar_ciclo(ciclo_id, "geracao", "em_andamento")
            cartelas = self.fase_geracao(proximo)
            log_ciclo.append("Geração: {} cartelas".format(len(cartelas)))

            if not cartelas:
                raise Exception("Geração falhou")

            resultado_final["geracao"] = {
                "n_cartelas":   len(cartelas),
                "concurso_alvo": proximo,
            }

            # ── Buscar resultado atual da Caixa ───────────────
            self._log("CICLO",
                      "Aguardando resultado do concurso {}...".format(concurso))

            data_json     = self._buscar_concurso(concurso)
            if not data_json:
                raise Exception("Resultado não disponível ainda")

            dezenas_reais = self._extrair_dezenas(data_json)
            premios_reais = self._extrair_premios(data_json)

            if len(dezenas_reais) != 15:
                raise Exception("Resultado inválido: {}".format(dezenas_reais))

            # Salvar resultado no banco
            self._salvar_resultado(concurso, data_json,
                                    dezenas_reais, premios_reais)

            # ── Fase 2: Conferência ───────────────────────────
            self._atualizar_ciclo(ciclo_id, "conferencia", "em_andamento")
            res_conf = self.fase_conferencia(
                proximo, dezenas_reais, premios_reais
            )
            log_ciclo.append("Conferência: melhor={}pts ganho=R${:.2f}".format(
                res_conf.get("melhor_acertos", 0),
                res_conf.get("total_ganho",    0),
            ))
            resultado_final["conferencia"] = res_conf

            # ── Fase 3: Aprendizado ───────────────────────────
            self._atualizar_ciclo(ciclo_id, "aprendizado", "em_andamento")
            res_aprd = self.fase_aprendizado(
                proximo, res_conf, dezenas_reais
            )
            log_ciclo.append("Aprendizado: {} módulos ajustados".format(
                len(res_aprd.get("mudancas", []))
            ))
            resultado_final["aprendizado"] = res_aprd

            # Sucesso
            resultado_final["status"] = "completo"
            self.ciclos_ok           += 1
            self.ultimo_concurso_processado = concurso

        except Exception as e:
            self._log("ERRO", "Ciclo {}: {}".format(concurso, str(e)))
            resultado_final["erro"]    = str(e)
            resultado_final["status"]  = "erro"
            self.ciclos_erro          += 1

        # Finalizar registro do ciclo
        tempo = time.time() - t0
        conn  = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE historico_ciclos SET
                timestamp_fim   = ?,
                fase            = ?,
                status          = ?,
                n_cartelas      = ?,
                melhor_acertos  = ?,
                media_acertos   = ?,
                total_ganho     = ?,
                pesos_depois    = ?,
                log_ciclo       = ?,
                erro_medio      = ?
            WHERE id = ?
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            resultado_final["status"],
            resultado_final["status"],
            resultado_final.get("geracao", {}).get("n_cartelas", 0),
            resultado_final.get("conferencia", {}).get("melhor_acertos", 0),
            resultado_final.get("conferencia", {}).get("media_acertos", 0),
            resultado_final.get("conferencia", {}).get("total_ganho", 0),
            json.dumps(dict(self.agente.PESOS)),
            "\n".join(log_ciclo),
            resultado_final.get("conferencia", {}).get(
                "media_acertos", 0
            ) / 15.0,
            ciclo_id,
        ))
        conn.commit()
        conn.close()

        self.historico_ciclos.append(resultado_final)
        self._log("CICLO",
                  "=== CICLO {} CONCLUÍDO em {:.1f}s ===".format(
                      concurso, tempo
                  ))
        return resultado_final

    # =========================================================
    # LOOP AUTOMÁTICO
    # =========================================================
    def iniciar_loop_automatico(
        self,
        intervalo_verificacao: int = 3600,
    ):
        """
        Inicia o loop automático em background.
        Verifica a Caixa a cada intervalo_verificacao segundos.
        """
        if self.rodando:
            return {"status": "ja_rodando"}

        self.rodando = True
        self.estado  = "monitorando"

        def _loop():
            self._log("LOOP", "Loop automático iniciado")
            while self.rodando:
                try:
                    if self.pausado:
                        time.sleep(30)
                        continue

                    # Verificar novo resultado
                    data = self._buscar_ultimo_resultado()
                    if not data:
                        self._log("LOOP", "Sem resposta da Caixa")
                        time.sleep(intervalo_verificacao)
                        continue

                    concurso_atual = int(data.get("numero", 0))
                    self.proximo_sorteio = self._calcular_data_proximo(data)

                    if concurso_atual <= self.ultimo_concurso_processado:
                        self._log("LOOP",
                                  "Sem novo concurso. Último: {}".format(
                                      concurso_atual
                                  ))
                        time.sleep(intervalo_verificacao)
                        continue

                    self._log("LOOP",
                              "Novo concurso detectado: {}".format(
                                  concurso_atual
                              ))

                    # Executar ciclo completo
                    self.executar_ciclo(concurso_atual)

                    # Aguardar próximo sorteio
                    time.sleep(intervalo_verificacao)

                except Exception as e:
                    self._log("ERRO", "Loop: {}".format(str(e)))
                    time.sleep(300)

            self.estado = "parado"
            self._log("LOOP", "Loop encerrado")

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()

        return {"status": "iniciado", "intervalo": intervalo_verificacao}

    def parar_loop(self):
        self.rodando = False
        self.estado  = "parando"
        return {"status": "parando"}

    def pausar(self):
        self.pausado = True
        self.estado  = "pausado"
        return {"status": "pausado"}

    def retomar(self):
        self.pausado = False
        self.estado  = "monitorando"
        return {"status": "retomado"}

    def executar_ciclo_manual(self, concurso: int) -> Dict:
        """Executa um ciclo manualmente para um concurso específico"""
        return self.executar_ciclo(concurso)

    # =========================================================
    # HELPERS
    # =========================================================
    def _salvar_resultado(
        self,
        concurso: int,
        data_json: Dict,
        dezenas: List[int],
        premios: Dict[int, float],
    ):
        try:
            from core.bitmatrix import BitMatrix
            from config import PRIMOS, FIBONACCI, BORDA
            bm = BitMatrix()

            dezenas_set  = set(dezenas)
            soma         = sum(dezenas)
            pares        = sum(1 for d in dezenas if d % 2 == 0)
            primos_c     = len(dezenas_set & PRIMOS)
            fib_c        = len(dezenas_set & FIBONACCI)
            borda_c      = len(dezenas_set & BORDA)

            sd = sorted(dezenas)
            mc = cc = 1
            for i in range(1, len(sd)):
                if sd[i] == sd[i - 1] + 1:
                    cc += 1; mc = max(mc, cc)
                else:
                    cc  = 1

            bitmask = bm.dezenas_para_bitmask(dezenas)
            data_str = data_json.get("dataApuracao", "")
            try:
                from datetime import datetime as dt
                data_str = dt.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except Exception:
                pass

            dados = (
                concurso, data_str,
                *dezenas,
                bitmask, soma, pares, 15 - pares,
                primos_c, fib_c, borda_c, mc,
                premios.get(11, 7.0),
                premios.get(12, 14.0),
                premios.get(13, 35.0),
                premios.get(14, 0.0),
                premios.get(15, 0.0),
                0, 0, 0, 0, 0,
                0.0,
            )
            self.db.inserir_resultado(dados)
        except Exception as e:
            self._log("AVISO", "Salvar resultado: {}".format(str(e)))

    def _atualizar_ciclo(self, ciclo_id: int, fase: str, status: str):
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE historico_ciclos SET fase = ?, status = ?
                WHERE id = ?
            """, (fase, status, ciclo_id))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _log(self, tipo: str, msg: str):
        entrada = {
            "ts":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo": tipo,
            "msg":  msg,
        }
        self.log.append(entrada)
        print("[CICLO][{}] {}".format(tipo, msg))

    # =========================================================
    # RELATÓRIOS
    # =========================================================
    def get_status(self) -> Dict[str, Any]:
        return {
            "estado":           self.estado,
            "rodando":          self.rodando,
            "pausado":          self.pausado,
            "ciclos_ok":        self.ciclos_ok,
            "ciclos_erro":      self.ciclos_erro,
            "ultimo_processado": self.ultimo_concurso_processado,
            "proximo_sorteio":  self.proximo_sorteio,
            "n_cartelas":       self.n_cartelas,
            "log_recente":      self.log[-20:],
        }

    def get_historico_ciclos(self, limit: int = 20) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM historico_ciclos
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_fila_concurso(self, concurso: int) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fila_conferencia
                WHERE concurso_alvo = ?
                ORDER BY score_total DESC
            """, (concurso,))
            rows = cursor.fetchall()
            conn.close()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["dezenas"] = json.loads(d.get("dezenas", "[]"))
                except Exception:
                    d["dezenas"] = []
                try:
                    d["dezenas_acertadas"] = json.loads(
                        d.get("dezenas_acertadas", "[]") or "[]"
                    )
                except Exception:
                    d["dezenas_acertadas"] = []
                result.append(d)
            return result
        except Exception:
            return []

    def get_memoria_erros(self, limit: int = 100) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT filtro, AVG(erro) as erro_medio,
                       COUNT(*) as ocorrencias,
                       AVG(impacto) as impacto_medio
                FROM memoria_erros
                GROUP BY filtro
                ORDER BY erro_medio DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_desempenho_modulos(self) -> List[Dict]:
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT modulo,
                       AVG(correlacao)   as corr_media,
                       AVG(peso_ajustado) as peso_atual,
                       COUNT(*)          as n_ciclos
                FROM desempenho_modulos
                GROUP BY modulo
                ORDER BY corr_media DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []