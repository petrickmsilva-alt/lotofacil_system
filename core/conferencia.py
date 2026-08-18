"""
============================================================
MÓDULO DE CONFERÊNCIA COMPLETO
- Cartelas fixadas por concurso
- Escolha do concurso para conferência
- Valores reais da Caixa (atualizados 2024/2025)
- Busca valores ao vivo da API
============================================================
"""
import requests
from database.db_manager import DBManager
from .bitmatrix import BitMatrix
from config import VALOR_APOSTA
from datetime import datetime


class Conferencia:

    # =========================================================
    # VALORES FIXOS OFICIAIS DA CAIXA (atualizados 2025)
    # Fonte: loterias.caixa.gov.br
    # 11, 12, 13 pontos = prêmio fixo por ganhador
    # 14, 15 pontos     = rateio (varia por concurso)
    # =========================================================
    PREMIOS_FIXOS_OFICIAIS = {
        11: 7.00,     # R$ 7,00 fixo
        12: 14.00,    # R$ 14,00 fixo
        13: 35.00,    # R$ 35,00 fixo
    }

    URL_API = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"

    def __init__(self):
        self.db        = DBManager()
        self.bitmatrix = BitMatrix()

    # =========================================================
    # BUSCAR VALORES REAIS DA CAIXA
    # =========================================================

    def buscar_premios_caixa(self, concurso):
        """
        Busca valores REAIS de prêmio direto da API da Caixa.
        Retorna dict com prêmios por faixa de acerto.
        """
        try:
            url  = self.URL_API.format(concurso)
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer":    "https://loterias.caixa.gov.br/",
            })

            if resp.status_code != 200:
                return None

            data        = resp.json()
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
                acertos = int(item.get("numeroAcertos", 0))
                valor   = item.get("valorPremio", 0)
                qtd     = int(item.get("numeroDeGanhadores", 0))

                # Converter valor para float
                if isinstance(valor, str):
                    valor = valor.replace("R$", "").replace(".", "")
                    valor = valor.replace(",", ".").strip()
                    try:
                        valor = float(valor)
                    except Exception:
                        valor = 0.0

                valor = float(valor)

                if acertos in premios:
                    # 11, 12, 13 = fixo (não sobrescreve com 0)
                    if acertos in (11, 12, 13):
                        if valor > 0:
                            premios[acertos] = valor
                    else:
                        premios[acertos]    = valor
                    ganhadores[acertos]     = qtd

            return {
                "premios":    premios,
                "ganhadores": ganhadores,
                "concurso":   concurso,
            }

        except Exception as e:
            print("[CONF] buscar_premios_caixa erro: {}".format(e))
            return None

    def get_premio(self, acertos, concurso=None):
        """
        Retorna o valor do prêmio para uma faixa de acertos.
        Para 11, 12, 13: valor fixo oficial.
        Para 14, 15: busca no banco (vindo da Caixa).
        """
        # Fixos — não mudam
        if acertos in self.PREMIOS_FIXOS_OFICIAIS:
            return self.PREMIOS_FIXOS_OFICIAIS[acertos]

        # Rateados — buscar no banco
        if concurso:
            row = self.db.get_premios_concurso(concurso)
            if row:
                if acertos == 14:
                    v = row["premio_14"]
                    return float(v) if v and v > 0 else 1800.0
                if acertos == 15:
                    v = row["premio_15"]
                    return float(v) if v and v > 0 else 2500000.0

        # Médias históricas como fallback
        medias = self.db.get_media_premios()
        if medias:
            if acertos == 14:
                return float(medias["media_14"] or 1800.0)
            if acertos == 15:
                return float(medias["media_15"] or 2500000.0)

        return 0.0

    # =========================================================
    # CONFERÊNCIA
    # =========================================================

    def conferir_cartela(self, cartela_dezenas, resultado_dezenas):
        """Confere uma cartela contra um resultado"""
        set_cartela   = set(cartela_dezenas)
        set_resultado = set(resultado_dezenas)

        acertadas = sorted(set_cartela & set_resultado)
        erradas   = sorted(set_cartela - set_resultado)
        acertos   = len(acertadas)

        return {
            "acertos":           acertos,
            "dezenas_acertadas": acertadas,
            "dezenas_erradas":   erradas,
            "premiado":          acertos >= 11,
        }

    def conferir_concurso(self, concurso):
        """
        Confere TODAS as cartelas de um concurso específico.
        Busca resultado da Caixa se não tiver no banco.
        """
        resultado = self.db.get_resultado_concurso(concurso)

        if not resultado:
            # Tentar buscar da Caixa
            dados_caixa = self.buscar_premios_caixa(concurso)
            if not dados_caixa:
                return {
                    "status":  "erro",
                    "msg":     "Resultado do concurso {} não encontrado.".format(
                        concurso
                    ),
                    "cartelas": [],
                }

        dez_resultado = [resultado["d{}".format(i)] for i in range(1, 16)]

        # Buscar cartelas do concurso
        cartelas = self.db.get_cartelas_por_concurso(concurso)

        if not cartelas:
            return {
                "status":   "vazio",
                "msg":      "Nenhuma cartela encontrada para o concurso {}.".format(
                    concurso
                ),
                "cartelas": [],
            }

        # Buscar prêmios reais da Caixa para este concurso
        premios_caixa = self.buscar_premios_caixa(concurso)
        premios_reais = {}
        if premios_caixa:
            premios_reais = premios_caixa.get("premios", {})
            # Atualizar banco com valores reais
            self._atualizar_premios_banco(concurso, premios_caixa)

        resultados_conf = []
        for cartela in cartelas:
            dez_cartela = [cartela["d{}".format(i)] for i in range(1, 16)]
            conf        = self.conferir_cartela(dez_cartela, dez_resultado)
            acertos     = conf["acertos"]

            # Valor do prêmio
            premio = 0.0
            if acertos >= 11:
                if acertos in (11, 12, 13):
                    # Fixo oficial
                    premio = self.PREMIOS_FIXOS_OFICIAIS[acertos]
                    # Verificar se a Caixa tem valor diferente
                    if premios_reais.get(acertos, 0) > 0:
                        premio = premios_reais[acertos]
                else:
                    # Rateado — usar valor real se disponível
                    if premios_reais.get(acertos, 0) > 0:
                        premio = premios_reais[acertos]
                    else:
                        premio = self.get_premio(acertos, concurso)

            # Status
            status = self._definir_status(acertos)

            # Atualizar banco
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

        return {
            "status":          "ok",
            "concurso":        concurso,
            "resultado":       dez_resultado,
            "cartelas":        resultados_conf,
            "premios_oficiais": premios_reais or self.PREMIOS_FIXOS_OFICIAIS,
            "total_cartelas":  len(resultados_conf),
            "total_premiadas": sum(1 for r in resultados_conf
                                   if r["premiado"]),
        }

    def conferir_todas_pendentes(self):
        """Confere todas as cartelas pendentes automaticamente"""
        cartelas    = self.db.get_cartelas_pendentes()
        resultados  = []

        concursos_processados = set()

        for cartela in cartelas:
            concurso = cartela["concurso_alvo"]

            if concurso in concursos_processados:
                continue

            resultado = self.db.get_resultado_concurso(concurso)
            if not resultado:
                continue

            concursos_processados.add(concurso)
            conf = self.conferir_concurso(concurso)

            if conf["status"] == "ok":
                resultados.extend(conf["cartelas"])

        return resultados

    def _definir_status(self, acertos):
        """Define o status textual do resultado"""
        mapa = {
            15: "premio_15",
            14: "premio_14",
            13: "premio_13",
            12: "premio_12",
            11: "premio_11",
        }
        return mapa.get(acertos, "sem_premio")

    def _atualizar_premios_banco(self, concurso, dados_caixa):
        """Atualiza os prêmios no banco com valores reais"""
        try:
            premios    = dados_caixa.get("premios", {})
            ganhadores = dados_caixa.get("ganhadores", {})
            conn       = self.db.get_conn()
            cursor     = conn.cursor()
            cursor.execute("""
                UPDATE resultados SET
                    premio_11 = ?,
                    premio_12 = ?,
                    premio_13 = ?,
                    premio_14 = ?,
                    premio_15 = ?,
                    ganhadores_11 = ?,
                    ganhadores_12 = ?,
                    ganhadores_13 = ?,
                    ganhadores_14 = ?,
                    ganhadores_15 = ?
                WHERE concurso = ?
            """, (
                premios.get(11, 6.0),
                premios.get(12, 12.0),
                premios.get(13, 30.0),
                premios.get(14, 0.0),
                premios.get(15, 0.0),
                ganhadores.get(11, 0),
                ganhadores.get(12, 0),
                ganhadores.get(13, 0),
                ganhadores.get(14, 0),
                ganhadores.get(15, 0),
                concurso,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print("[CONF] Erro atualizar banco: {}".format(e))

    # =========================================================
    # RESUMOS
    # =========================================================

    def resumo_conferencia(self, concurso=None):
        """Resumo de acertos e prêmios"""
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        if concurso:
            cursor.execute("""
                SELECT acertos,
                       COUNT(*) as qtd,
                       SUM(premio_ganho) as total_premio
                FROM cartelas
                WHERE concurso_alvo = ? AND conferida = 1
                GROUP BY acertos
                ORDER BY acertos DESC
            """, (concurso,))
        else:
            cursor.execute("""
                SELECT acertos,
                       COUNT(*) as qtd,
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
        """Retorna todas as cartelas de um concurso com status"""
        cartelas = self.db.get_cartelas_por_concurso(concurso)
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
        """Lista todos os concursos que têm cartelas geradas"""
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