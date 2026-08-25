"""
============================================================
MÓDULO DE CONFERÊNCIA COMPLETO
Protegido contra conversões de tipo (bytes/numpy/null)
============================================================
"""
from database.db_manager import DBManager
from .bitmatrix import BitMatrix
from .caixa_client import CaixaClient
from datetime import datetime


def _safe_int(val):
    """Converte inteiros Python/NumPy e BLOBs SQLite legados.

    Versões antigas gravaram `numpy.int64` diretamente no SQLite, produzindo
    oito bytes little-endian (por exemplo, 1 = ``01 00 00 ...``). Tentar
    ``int(blob)`` transforma esse dado válido em erro e, no código anterior,
    silenciosamente em zero — corrompendo a conferência e o financeiro.
    """
    if val is None:
        return 0
    if hasattr(val, "item"):
        val = val.item()
    if isinstance(val, (bytes, bytearray, memoryview)):
        raw = bytes(val)
        try:
            # Mantém compatibilidade com BLOB textual, como b"15".
            return int(raw.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            if len(raw) in (1, 2, 4, 8):
                return int.from_bytes(raw, byteorder="little", signed=True)
            return 0
    try:
        return int(val)
    except (TypeError, ValueError, OverflowError):
        return 0


class Conferencia:

    PREMIOS_FIXOS_OFICIAIS = {
        11: 7.00,
        12: 14.00,
        13: 35.00,
    }

    URL_API = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"

    def __init__(self, db_path=None, client=None):
        self.db = DBManager(db_path)
        self.bitmatrix = BitMatrix()
        self.client = client or CaixaClient()

    # =========================================================
    # BUSCAR PRÊMIOS DA CAIXA
    # =========================================================

    def buscar_premios_caixa(self, concurso):
        """Obtém rateio validado; contingência sem prêmios nunca zera o banco."""
        data = self.client.buscar_concurso(concurso)
        if not data or not data.get("_premios_disponiveis"):
            return None
        premios = dict(self.PREMIOS_FIXOS_OFICIAIS)
        premios.update({14: 0.0, 15: 0.0})
        ganhadores = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        for item in data.get("listaRateioPremio", []):
            acertos = _safe_int(item.get("numeroAcertos"))
            if acertos not in premios:
                continue
            try:
                valor = float(item.get("valorPremio", 0) or 0)
            except (TypeError, ValueError):
                valor = 0.0
            if valor > 0 or acertos in (14, 15):
                premios[acertos] = valor
            ganhadores[acertos] = _safe_int(item.get("numeroDeGanhadores"))
        return {
            "premios": premios, "ganhadores": ganhadores,
            "concurso": int(concurso), "fonte": data.get("_fonte"),
        }

    def atualizar_premios_concursos(self, concursos):
        """Atualiza rateios sem apagar valores quando a fonte não os possui."""
        atualizados = 0
        falhas = []
        fontes = set()
        for concurso in concursos:
            try:
                dados = self.buscar_premios_caixa(int(concurso))
                if not dados:
                    falhas.append({
                        "concurso": int(concurso),
                        "diagnostico": self.client.diagnostico(),
                    })
                    continue
                self._atualizar_premios_banco(int(concurso), dados)
                fontes.add(dados.get("fonte"))
                atualizados += 1
            except Exception as exc:
                falhas.append({
                    "concurso": int(concurso), "erro": str(exc),
                })
        total = len(concursos)
        return {
            "status": ("ok" if not falhas else
                       "parcial" if atualizados else "erro"),
            "atualizados": atualizados,
            "erros": len(falhas),
            "total": total,
            "fontes": sorted(f for f in fontes if f),
            "falhas": falhas[:20],
        }

    def get_premio(self, acertos, concurso=None):
        if acertos in self.PREMIOS_FIXOS_OFICIAIS:
            return self.PREMIOS_FIXOS_OFICIAIS[acertos]

        if concurso:
            row = self.db.get_premios_concurso(concurso)
            if row:
                if acertos == 14:
                    v = row["premio_14"]
                    return float(v) if v and float(v) > 0 else 0.0
                if acertos == 15:
                    v = row["premio_15"]
                    return float(v) if v and float(v) > 0 else 0.0

        return 0.0

    # =========================================================
    # CONFERÊNCIA
    # =========================================================

    def conferir_cartela(self, cartela_dezenas, resultado_dezenas):
        set_cartela   = set([_safe_int(d) for d in cartela_dezenas])
        set_resultado = set([_safe_int(d) for d in resultado_dezenas])
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
        concurso  = _safe_int(concurso)
        resultado = self.db.get_resultado_concurso(concurso)

        if not resultado:
            try:
                data_json = self.client.buscar_concurso(concurso)
                if not data_json:
                    return {
                        "status": "erro",
                        "msg": "Concurso {} indisponível. {}".format(
                            concurso, self.client.diagnostico()),
                        "cartelas": [], "total_cartelas": 0,
                        "total_premiadas": 0,
                    }
                dez_resultado = sorted(
                    _safe_int(d) for d in data_json.get("listaDezenas", []))
                if (len(dez_resultado) != 15 or
                        len(set(dez_resultado)) != 15 or
                        any(d < 1 or d > 25 for d in dez_resultado)):
                    return {
                        "status": "erro", "msg": "Resultado inválido.",
                        "cartelas": [], "total_cartelas": 0,
                        "total_premiadas": 0,
                    }
                dados_caixa = self.buscar_premios_caixa(concurso)
                self._salvar_resultado_no_banco(
                    concurso, data_json, dez_resultado, dados_caixa)
            except Exception as e:
                return {
                    "status": "erro", "msg": "Erro: {}".format(str(e)),
                    "cartelas": [], "total_cartelas": 0,
                    "total_premiadas": 0,
                }
        else:
            dez_resultado = [
                _safe_int(resultado["d{}".format(i)]) for i in range(1, 16)
            ]

        cartelas = self.db.get_cartelas_por_concurso(concurso)
        if not cartelas:
            return {
                "status":         "vazio",
                "msg":            "Nenhuma cartela para o concurso {}.".format(concurso),
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
                    _safe_int(cartela["d{}".format(i)]) for i in range(1, 16)
                ]
                conf    = self.conferir_cartela(dez_cartela, dez_resultado)
                acertos = conf["acertos"]

                premio = 0.0
                if acertos >= 11:
                    if acertos in (11, 12, 13):
                        premio = self.PREMIOS_FIXOS_OFICIAIS[acertos]
                        if premios_reais.get(acertos, 0) > 0:
                            premio = float(premios_reais[acertos])
                    else:
                        if premios_reais.get(acertos, 0) > 0:
                            premio = float(premios_reais[acertos])
                        else:
                            premio = float(self.get_premio(acertos, concurso))

                status = self._definir_status(acertos)

                self.db.atualizar_conferencia(
                    _safe_int(cartela["id"]), acertos, premio, status
                )

                resultados_conf.append({
                    "cartela_id":        _safe_int(cartela["id"]),
                    "dezenas_cartela":   [_safe_int(x) for x in dez_cartela],
                    "dezenas_resultado": [_safe_int(x) for x in dez_resultado],
                    "acertos":           acertos,
                    "dezenas_acertadas": [_safe_int(x) for x in conf["dezenas_acertadas"]],
                    "dezenas_erradas":   [_safe_int(x) for x in conf["dezenas_erradas"]],
                    "premio":            float(premio),
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
            "resultado":       [_safe_int(x) for x in dez_resultado],
            "cartelas":        resultados_conf,
            "premios_oficiais": {
                int(k): float(v) for k, v in (premios_reais or self.PREMIOS_FIXOS_OFICIAIS).items()
            },
            "total_cartelas":  len(resultados_conf),
            "total_premiadas": sum(1 for r in resultados_conf if r["premiado"]),
        }

    def conferir_todas_pendentes(self):
        """Confere, concurso a concurso, todas as cartelas ainda pendentes
        cujo resultado já está no banco.

        Retorna uma lista de resultados por concurso (cada um com
        status/concurso/cartelas), no mesmo formato de conferir_concurso —
        assim a camada app consegue alimentar o módulo financeiro.
        Antes retornava uma lista achatada de cartelas, o que impedia o
        registro financeiro (o hook procurava status='ok' em cada cartela).
        """
        cartelas    = self.db.get_cartelas_pendentes()
        resultados  = []
        processados = set()

        for cartela in cartelas:
            concurso = _safe_int(cartela["concurso_alvo"])
            if concurso in processados:
                continue

            resultado = self.db.get_resultado_concurso(concurso)
            if not resultado:
                continue

            processados.add(concurso)
            conf = self.conferir_concurso(concurso)

            if conf.get("status") == "ok":
                resultados.append(conf)

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
        premios = dados_caixa.get("premios", {})
        ganhadores = dados_caixa.get("ganhadores", {})
        conn = self.db.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE resultados SET
                    premio_11=?, premio_12=?, premio_13=?,
                    premio_14=?, premio_15=?,
                    ganhadores_11=?, ganhadores_12=?, ganhadores_13=?,
                    ganhadores_14=?, ganhadores_15=?
                WHERE concurso=?
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
                _safe_int(concurso),
            ))
            if cursor.rowcount != 1:
                raise ValueError("concurso {} não existe no banco".format(concurso))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _salvar_resultado_no_banco(self, concurso, data_json,
                                     dezenas, dados_caixa):
        try:
            from core.bitmatrix import BitMatrix
            from config import PRIMOS, FIBONACCI, BORDA
            bm = BitMatrix()

            dezenas_clean = [_safe_int(d) for d in dezenas]
            ds       = set(dezenas_clean)
            soma     = sum(dezenas_clean)
            pares    = sum(1 for d in dezenas_clean if d % 2 == 0)
            primos_c = len(ds & PRIMOS)
            fib_c    = len(ds & FIBONACCI)
            borda_c  = len(ds & BORDA)

            sd = sorted(dezenas_clean)
            mc = 1
            cc = 1
            for i in range(1, len(sd)):
                if sd[i] == sd[i - 1] + 1:
                    cc += 1
                    mc = max(mc, cc)
                else:
                    cc = 1

            bitmask  = bm.dezenas_para_bitmask(dezenas_clean)
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
                _safe_int(concurso), data_str, *dezenas_clean,
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
            """, (_safe_int(concurso),))
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
            resumo[_safe_int(row["acertos"])] = {
                "qtd":          _safe_int(row["qtd"]),
                "total_premio": round(float(row["total_premio"] or 0), 2),
            }
        return resumo

    def get_cartelas_do_concurso(self, concurso):
        cartelas  = self.db.get_cartelas_por_concurso(_safe_int(concurso))
        resultado = []
        for c in cartelas:
            resultado.append({
                "id":          _safe_int(c["id"]),
                "dezenas":     [_safe_int(c["d{}".format(i)]) for i in range(1, 16)],
                "conferida":   bool(c["conferida"]),
                "acertos":     _safe_int(c["acertos"]),
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
            tot  = _safe_int(r["total_cartelas"])
            conf = _safe_int(r["conferidas"])
            lista.append({
                "concurso":       _safe_int(r["concurso_alvo"]),
                "total_cartelas": tot,
                "conferidas":     conf,
                "premiadas":      _safe_int(r["premiadas"]),
                "total_ganho":    round(float(r["total_ganho"] or 0), 2),
                "pendentes":      tot - conf,
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
                        _safe_int(d["d{}".format(i)]) for i in range(1, 16)
                    ]
                else:
                    d["resultado_sorteio"] = None

                d["concurso_alvo"]  = _safe_int(d.get("concurso_alvo"))
                d["ganhadores_15"]   = _safe_int(d.get("ganhadores_15"))
                d["custo_total"]    = float(d.get("custo_total") or 0)
                d["cobertura_13"]   = float(d.get("cobertura_13") or 0)

                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN conferida = 1 THEN 1 ELSE 0 END) as conferidas,
                        SUM(CASE WHEN acertos >= 11 THEN 1 ELSE 0 END) as premiadas,
                        SUM(premio_ganho) as total_ganho
                    FROM cartelas WHERE lote_id = ?
                """, (d["lote_id"],))
                cnt = cursor.fetchone()

                tot  = _safe_int(cnt["total"])
                conf = _safe_int(cnt["conferidas"])

                d["total_cartelas"] = tot
                d["conferidas"]     = conf
                d["premiadas"]      = _safe_int(cnt["premiadas"])
                d["total_ganho"]    = float(cnt["total_ganho"] or 0)
                d["pendentes"]      = tot - conf
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
            """, (str(lote_id),))
            rows = cursor.fetchall()
            conn.close()

            resultado = []
            for c in rows:
                resultado.append({
                    "id":          _safe_int(c["id"]),
                    "dezenas":     [_safe_int(c["d{}".format(i)]) for i in range(1, 16)],
                    "conferida":   bool(c["conferida"]),
                    "acertos":     _safe_int(c["acertos"]),
                    "premio":      float(c["premio_ganho"] or 0),
                    "status":      c["status"] or "pendente",
                    "score_total": float(c["score_total"] or 0),
                    "lote_id":     str(c["lote_id"]),
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
                "DELETE FROM cartelas WHERE lote_id = ?", (str(lote_id),)
            )
            n_cart = cursor.rowcount

            cursor.execute(
                "DELETE FROM lotes_cartelas WHERE lote_id = ?", (str(lote_id),)
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
            """, (str(lote_id),))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return {"status": "erro", "msg": "Lote não encontrado"}

            return self.conferir_concurso(_safe_int(row["concurso_alvo"]))

        except Exception as e:
            return {"status": "erro", "msg": str(e)}