"""
============================================================
MÓDULO DE CONFERÊNCIA COMPLETO
Com sistema de LOTES, prêmios reais, conferência por concurso
============================================================
"""
import requests
import json
from database.db_manager import DBManager
from .bitmatrix import BitMatrix
from config import VALOR_APOSTA
from datetime import datetime


class Conferencia:

    PREMIOS_FIXOS_OFICIAIS = {
        11: 7.00,
        12: 14.00,
        13: 35.00,
    }

    URL_API = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"

    def __init__(self):
        self.db        = DBManager()
        self.bitmatrix = BitMatrix()

    # =========================================================
    # BUSCAR PRÊMIOS DA CAIXA
    # =========================================================

    def buscar_premios_caixa(self, concurso):
        """
        Busca prêmios reais da Caixa.
        A API retorna FAIXAS (1-5), não quantidade de acertos.
        Faixa 1 = 15 acertos, Faixa 2 = 14, Faixa 3 = 13, etc.
        """
        # Mapeamento FAIXA → ACERTOS
        MAPA_FAIXA_ACERTOS = {
            1: 15,   # Faixa 1 = Jackpot (15 acertos)
            2: 14,
            3: 13,
            4: 12,
            5: 11,
        }

        try:
            url  = self.URL_API.format(concurso)
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer":    "https://loterias.caixa.gov.br/",
            })

            if resp.status_code != 200:
                print("[CONF] HTTP {} para concurso {}".format(
                    resp.status_code, concurso
                ))
                return None

            data         = resp.json()
            lista_rateio = data.get("listaRateioPremio", [])

            premios = {
                11: self.PREMIOS_FIXOS_OFICIAIS[11],
                12: self.PREMIOS_FIXOS_OFICIAIS[12],
                13: self.PREMIOS_FIXOS_OFICIAIS[13],
                14: 0.0,
                15: 0.0,
            }
            ganhadores = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}

            for item in lista_rateio:
                # A API retorna FAIXA, não acertos!
                faixa = item.get("faixa") or item.get("numeroAcertos") or 0

                try:
                    faixa = int(faixa)
                except Exception:
                    continue

                # Converter FAIXA → ACERTOS REAIS
                acertos = MAPA_FAIXA_ACERTOS.get(faixa)
                if acertos is None:
                    continue

                # Valor do prêmio
                valor = item.get("valorPremio", 0)
                if isinstance(valor, str):
                    valor = valor.replace("R$", "").replace(".", "")
                    valor = valor.replace(",", ".").strip()
                    try:
                        valor = float(valor)
                    except Exception:
                        valor = 0.0

                try:
                    valor = float(valor)
                except Exception:
                    valor = 0.0

                # Número de ganhadores
                qtd = item.get("numeroDeGanhadores", 0)
                try:
                    qtd = int(qtd)
                except Exception:
                    qtd = 0

                # Debug
                print("[CONF]   Faixa {} = {} acertos: R$ {:.2f} - {} ganhadores".format(
                    faixa, acertos, valor, qtd
                ))

                # Salvar nos dicionários
                if acertos in (11, 12, 13):
                    if valor > 0:
                        premios[acertos] = valor
                else:
                    # 14 e 15 sempre atualiza (pode ser 0 se acumulou)
                    premios[acertos] = valor

                ganhadores[acertos] = qtd

            return {
                "premios":    premios,
                "ganhadores": ganhadores,
                "concurso":   concurso,
            }

        except Exception as e:
            print("[CONF] buscar_premios_caixa erro concurso {}: {}".format(
                concurso, e
            ))
            return None
    def get_premio(self, acertos, concurso=None):
        if acertos in self.PREMIOS_FIXOS_OFICIAIS:
            return self.PREMIOS_FIXOS_OFICIAIS[acertos]

        if concurso:
            row = self.db.get_premios_concurso(concurso)
            if row:
                if acertos == 14:
                    v = row["premio_14"]
                    return float(v) if v and v > 0 else 1800.0
                if acertos == 15:
                    v = row["premio_15"]
                    return float(v) if v and v > 0 else 2500000.0

        return 0.0

    # =========================================================
    # CONFERÊNCIA
    # =========================================================

    def conferir_cartela(self, cartela_dezenas, resultado_dezenas):
        set_cartela   = set(cartela_dezenas)
        set_resultado = set(resultado_dezenas)
        acertadas     = sorted(set_cartela & set_resultado)
        erradas       = sorted(set_cartela - set_resultado)
        acertos       = len(acertadas)

        return {
            "acertos":           acertos,
            "dezenas_acertadas": acertadas,
            "dezenas_erradas":   erradas,
            "premiado":          acertos >= 11,
        }

    def conferir_concurso(self, concurso):
        resultado = self.db.get_resultado_concurso(concurso)

        if not resultado:
            try:
                url  = self.URL_API.format(concurso)
                resp = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer":    "https://loterias.caixa.gov.br/",
                })
                if resp.status_code != 200:
                    return {
                        "status":         "erro",
                        "msg":            "Concurso {} não disponível.".format(concurso),
                        "cartelas":       [],
                        "total_cartelas":  0,
                        "total_premiadas": 0,
                    }

                data_json     = resp.json()
                dezenas_json  = data_json.get("listaDezenas", [])
                dez_resultado = sorted([int(d) for d in dezenas_json])

                if len(dez_resultado) != 15:
                    return {
                        "status":         "erro",
                        "msg":            "Resultado inválido.",
                        "cartelas":       [],
                        "total_cartelas":  0,
                        "total_premiadas": 0,
                    }

                dados_caixa = self.buscar_premios_caixa(concurso)
                self._salvar_resultado_no_banco(
                    concurso, data_json, dez_resultado, dados_caixa
                )

            except Exception as e:
                return {
                    "status":         "erro",
                    "msg":            "Erro: {}".format(str(e)),
                    "cartelas":       [],
                    "total_cartelas":  0,
                    "total_premiadas": 0,
                }
        else:
            dez_resultado = [
                resultado["d{}".format(i)] for i in range(1, 16)
            ]

        cartelas = self.db.get_cartelas_por_concurso(concurso)
        if not cartelas:
            return {
                "status":         "vazio",
                "msg":            "Nenhuma cartela para concurso {}.".format(concurso),
                "cartelas":       [],
                "resultado":      dez_resultado,
                "total_cartelas":  0,
                "total_premiadas": 0,
            }

        premios_caixa = self.buscar_premios_caixa(concurso)
        premios_reais = {}
        if premios_caixa:
            premios_reais = premios_caixa.get("premios", {})
            self._atualizar_premios_banco(concurso, premios_caixa)

        resultados_conf = []
        for cartela in cartelas:
            try:
                dez_cartela = [
                    cartela["d{}".format(i)] for i in range(1, 16)
                ]
                conf    = self.conferir_cartela(dez_cartela, dez_resultado)
                acertos = conf["acertos"]

                premio = 0.0
                if acertos >= 11:
                    if acertos in (11, 12, 13):
                        premio = self.PREMIOS_FIXOS_OFICIAIS[acertos]
                        if premios_reais.get(acertos, 0) > 0:
                            premio = premios_reais[acertos]
                    else:
                        if premios_reais.get(acertos, 0) > 0:
                            premio = premios_reais[acertos]
                        else:
                            premio = self.get_premio(acertos, concurso)

                status = self._definir_status(acertos)

                self.db.atualizar_conferencia(
                    cartela["id"], acertos, premio, status
                )

                resultados_conf.append({
                    "cartela_id":        cartela["id"],
                    "dezenas_cartela":   dez_cartela,
                    "dezenas_resultado": dez_resultado,
                    "acertos":           acertos,
                    "dezenas_acertadas": conf["dezenas_acertadas"],
                    "dezenas_erradas":   conf["dezenas_erradas"],
                    "premio":            premio,
                    "status":            status,
                    "premiado":          acertos >= 11,
                })

            except Exception as e:
                print("[CONF] Erro cartela {}: {}".format(
                    cartela.get("id"), e
                ))
                continue

        return {
            "status":          "ok",
            "concurso":        concurso,
            "resultado":       dez_resultado,
            "cartelas":        resultados_conf,
            "premios_oficiais": premios_reais or self.PREMIOS_FIXOS_OFICIAIS,
            "total_cartelas":  len(resultados_conf),
            "total_premiadas": sum(1 for r in resultados_conf if r["premiado"]),
        }

    def conferir_todas_pendentes(self):
        cartelas    = self.db.get_cartelas_pendentes()
        resultados  = []
        processados = set()

        for cartela in cartelas:
            concurso = cartela["concurso_alvo"]
            if concurso in processados:
                continue

            resultado = self.db.get_resultado_concurso(concurso)
            if not resultado:
                continue

            processados.add(concurso)
            conf = self.conferir_concurso(concurso)

            if conf["status"] == "ok":
                resultados.extend(conf["cartelas"])

        return resultados

    def _definir_status(self, acertos):
        mapa = {
            15: "premio_15",
            14: "premio_14",
            13: "premio_13",
            12: "premio_12",
            11: "premio_11",
        }
        return mapa.get(acertos, "sem_premio")

    def _atualizar_premios_banco(self, concurso, dados_caixa):
        try:
            premios    = dados_caixa.get("premios", {})
            ganhadores = dados_caixa.get("ganhadores", {})

            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE resultados SET
                    premio_11     = ?,
                    premio_12     = ?,
                    premio_13     = ?,
                    premio_14     = ?,
                    premio_15     = ?,
                    ganhadores_11 = ?,
                    ganhadores_12 = ?,
                    ganhadores_13 = ?,
                    ganhadores_14 = ?,
                    ganhadores_15 = ?
                WHERE concurso = ?
            """, (
                float(premios.get(11, 7.0)),
                float(premios.get(12, 14.0)),
                float(premios.get(13, 35.0)),
                float(premios.get(14, 0.0)),
                float(premios.get(15, 0.0)),
                int(ganhadores.get(11, 0)),
                int(ganhadores.get(12, 0)),
                int(ganhadores.get(13, 0)),
                int(ganhadores.get(14, 0)),
                int(ganhadores.get(15, 0)),
                concurso,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print("[CONF] Erro atualizar prêmios: {}".format(e))

    def _salvar_resultado_no_banco(self, concurso, data_json,
                                     dezenas, dados_caixa):
        try:
            from core.bitmatrix import BitMatrix
            from config import PRIMOS, FIBONACCI, BORDA
            bm = BitMatrix()

            ds       = set(dezenas)
            soma     = sum(dezenas)
            pares    = sum(1 for d in dezenas if d % 2 == 0)
            primos_c = len(ds & PRIMOS)
            fib_c    = len(ds & FIBONACCI)
            borda_c  = len(ds & BORDA)

            sd = sorted(dezenas)
            mc = 1
            cc = 1
            for i in range(1, len(sd)):
                if sd[i] == sd[i - 1] + 1:
                    cc += 1
                    mc = max(mc, cc)
                else:
                    cc = 1

            bitmask  = bm.dezenas_para_bitmask(dezenas)
            data_str = data_json.get("dataApuracao", "")
            try:
                data_str = datetime.strptime(
                    data_str, "%d/%m/%Y"
                ).strftime("%Y-%m-%d")
            except Exception:
                pass

            premios    = {}
            ganhadores = {}
            if dados_caixa:
                premios    = dados_caixa.get("premios", {})
                ganhadores = dados_caixa.get("ganhadores", {})

            dados = (
                concurso, data_str, *dezenas,
                bitmask, soma, pares, 15 - pares,
                primos_c, fib_c, borda_c, mc,
                float(premios.get(11, 7.0)),
                float(premios.get(12, 14.0)),
                float(premios.get(13, 35.0)),
                float(premios.get(14, 0.0)),
                float(premios.get(15, 0.0)),
                int(ganhadores.get(11, 0)),
                int(ganhadores.get(12, 0)),
                int(ganhadores.get(13, 0)),
                int(ganhadores.get(14, 0)),
                int(ganhadores.get(15, 0)),
                0.0,
            )
            self.db.inserir_resultado(dados)
        except Exception as e:
            print("[CONF] Erro salvar resultado: {}".format(e))

    # =========================================================
    # RESUMOS
    # =========================================================

    def resumo_conferencia(self, concurso=None):
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        if concurso:
            cursor.execute("""
                SELECT acertos, COUNT(*) as qtd,
                       SUM(premio_ganho) as total_premio
                FROM cartelas
                WHERE concurso_alvo = ? AND conferida = 1
                GROUP BY acertos
                ORDER BY acertos DESC
            """, (concurso,))
        else:
            cursor.execute("""
                SELECT acertos, COUNT(*) as qtd,
                       SUM(premio_ganho) as total_premio
                FROM cartelas
                WHERE conferida = 1
                GROUP BY acertos
                ORDER BY acertos DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        resumo = {}
        for row in rows:
            resumo[row["acertos"]] = {
                "qtd":          row["qtd"],
                "total_premio": round(float(row["total_premio"] or 0), 2),
            }
        return resumo

    def get_cartelas_do_concurso(self, concurso):
        cartelas  = self.db.get_cartelas_por_concurso(concurso)
        resultado = []
        for c in cartelas:
            resultado.append({
                "id":          c["id"],
                "dezenas":     [c["d{}".format(i)] for i in range(1, 16)],
                "conferida":   bool(c["conferida"]),
                "acertos":     c["acertos"] or 0,
                "premio":      float(c["premio_ganho"] or 0),
                "status":      c["status"] or "pendente",
                "score_total": float(c["score_total"] or 0),
            })
        return resultado

    def get_concursos_com_cartelas(self):
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                concurso_alvo,
                COUNT(*) as total_cartelas,
                SUM(CASE WHEN conferida = 1 THEN 1 ELSE 0 END) as conferidas,
                SUM(CASE WHEN acertos >= 11 THEN 1 ELSE 0 END) as premiadas,
                SUM(premio_ganho) as total_ganho
            FROM cartelas
            GROUP BY concurso_alvo
            ORDER BY concurso_alvo DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        lista = []
        for r in rows:
            lista.append({
                "concurso":       r["concurso_alvo"],
                "total_cartelas": r["total_cartelas"],
                "conferidas":     r["conferidas"] or 0,
                "premiadas":      r["premiadas"]  or 0,
                "total_ganho":    round(float(r["total_ganho"] or 0), 2),
                "pendentes":      r["total_cartelas"] - (r["conferidas"] or 0),
            })
        return lista

    # =========================================================
    # LOTES
    # =========================================================

    def get_todos_lotes(self):
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.*,
                       r.d1, r.d2, r.d3, r.d4, r.d5,
                       r.d6, r.d7, r.d8, r.d9, r.d10,
                       r.d11, r.d12, r.d13, r.d14, r.d15,
                       r.data as data_sorteio,
                       r.ganhadores_15
                FROM lotes_cartelas l
                LEFT JOIN resultados r ON l.concurso_alvo = r.concurso
                ORDER BY l.data_criacao DESC
            """)
            rows = cursor.fetchall()

            lotes = []
            for r in rows:
                d = dict(r)

                if d.get("d1") is not None:
                    d["resultado_sorteio"] = [
                        d["d{}".format(i)] for i in range(1, 16)
                    ]
                else:
                    d["resultado_sorteio"] = None

                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN conferida = 1 THEN 1 ELSE 0 END) as conferidas,
                        SUM(CASE WHEN acertos >= 11 THEN 1 ELSE 0 END) as premiadas,
                        SUM(premio_ganho) as total_ganho
                    FROM cartelas WHERE lote_id = ?
                """, (d["lote_id"],))
                cnt = cursor.fetchone()

                d["total_cartelas"] = cnt["total"]      or 0
                d["conferidas"]     = cnt["conferidas"] or 0
                d["premiadas"]      = cnt["premiadas"]  or 0
                d["total_ganho"]    = float(cnt["total_ganho"] or 0)
                d["pendentes"]      = d["total_cartelas"] - d["conferidas"]
                lotes.append(d)

            conn.close()
            return lotes

        except Exception as e:
            print("[CONF] get_todos_lotes: {}".format(e))
            return []

    def get_cartelas_do_lote(self, lote_id):
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cartelas
                WHERE lote_id = ?
                ORDER BY id ASC
            """, (lote_id,))
            rows = cursor.fetchall()
            conn.close()

            resultado = []
            for c in rows:
                resultado.append({
                    "id":          c["id"],
                    "dezenas":     [c["d{}".format(i)] for i in range(1, 16)],
                    "conferida":   bool(c["conferida"]),
                    "acertos":     c["acertos"]     or 0,
                    "premio":      float(c["premio_ganho"] or 0),
                    "status":      c["status"]      or "pendente",
                    "score_total": float(c["score_total"] or 0),
                    "lote_id":     c["lote_id"],
                })
            return resultado

        except Exception as e:
            print("[CONF] get_cartelas_do_lote: {}".format(e))
            return []

    def apagar_lote(self, lote_id):
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM cartelas WHERE lote_id = ?", (lote_id,)
            )
            n_cart = cursor.rowcount

            cursor.execute(
                "DELETE FROM lotes_cartelas WHERE lote_id = ?", (lote_id,)
            )

            conn.commit()
            conn.close()

            return {"status": "ok", "cartelas_apagadas": n_cart}

        except Exception as e:
            return {"status": "erro", "msg": str(e)}

    def conferir_lote(self, lote_id):
        try:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT concurso_alvo FROM cartelas
                WHERE lote_id = ?
            """, (lote_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return {"status": "erro", "msg": "Lote não encontrado"}

            return self.conferir_concurso(row["concurso_alvo"])

        except Exception as e:
            return {"status": "erro", "msg": str(e)}