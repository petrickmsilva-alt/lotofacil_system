"""
============================================================
ALIMENTADOR QUÂNTICO - DATA INGESTION COMPLETO
Busca TODOS os resultados desde o concurso 1 até hoje
Busca valores de prêmios REAIS da Caixa Econômica Federal
API Oficial: servicebus2.caixa.gov.br
============================================================
"""
import json
import sqlite3
import time
from datetime import datetime
from config import PRIMOS, FIBONACCI, BORDA
from database.db_manager import DBManager
from .bitmatrix import BitMatrix
from .caixa_client import CaixaClient


class DataLoader:
    """Sincroniza e valida o histórico usado pela Inteligência Magna."""

    def __init__(self, db_path=None, client=None):
        self.db = DBManager(db_path)
        self.bitmatrix = BitMatrix()
        self.client = client or CaixaClient()

    # =========================================================
    # BUSCA DE RESULTADOS
    # =========================================================

    def buscar_ultimo_resultado(self):
        """Busca o último resultado com contingência e diagnóstico de fonte."""
        return self.client.buscar_ultimo()

    def buscar_concurso(self, numero):
        """Busca um concurso específico com a mesma política de fontes."""
        return self.client.buscar_concurso(numero)

    # =========================================================
    # EXTRAÇÃO DE PRÊMIOS REAIS
    # =========================================================

    def extrair_premios(self, data_json):
        """
        Extrai os valores REAIS de prêmio por faixa de acerto
        diretamente do JSON da Caixa.

        Estrutura do JSON da Caixa:
        {
          "listaRateioPremio": [
            {
              "numeroAcertos": 15,
              "descricaoFaixa": "15 acertos",
              "numeroDeGanhadores": 2,
              "valorPremio": 2500000.00
            },
            ...
          ]
        }
        """
        premios = {11: 0.0, 12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0}

        try:
            lista_rateio = data_json.get("listaRateioPremio", [])

            for item in lista_rateio:
                acertos = item.get("numeroAcertos", 0)
                valor   = item.get("valorPremio", 0.0)

                # Converter string para float se necessário
                if isinstance(valor, str):
                    valor = float(
                        valor.replace("R$", "")
                            .replace(".", "")
                            .replace(",", ".")
                            .strip()
                    )

                if acertos in premios:
                    premios[acertos] = float(valor)

        except Exception as e:
            print(f"[ERRO] Extrair prêmios: {e}")

        return premios

    def extrair_ganhadores(self, data_json):
        """Extrai número de ganhadores por faixa"""
        ganhadores = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}

        try:
            lista_rateio = data_json.get("listaRateioPremio", [])
            for item in lista_rateio:
                acertos = item.get("numeroAcertos", 0)
                qtd     = item.get("numeroDeGanhadores", 0)
                if acertos in ganhadores:
                    ganhadores[acertos] = int(qtd)
        except Exception as e:
            print(f"[ERRO] Extrair ganhadores: {e}")

        return ganhadores

    # =========================================================
    # MÉTRICAS DO JOGO
    # =========================================================

    def calcular_metricas(self, dezenas):
        """Calcula todas as métricas estatísticas de um jogo"""
        dezenas_set = set(dezenas)
        soma        = sum(dezenas)
        pares       = sum(1 for d in dezenas if d % 2 == 0)
        impares     = 15 - pares
        primos_c    = len(dezenas_set & PRIMOS)
        fib_c       = len(dezenas_set & FIBONACCI)
        borda_c     = len(dezenas_set & BORDA)

        # Consecutivos máximos
        sorted_d    = sorted(dezenas)
        max_consec  = 1
        curr        = 1
        for i in range(1, len(sorted_d)):
            if sorted_d[i] == sorted_d[i - 1] + 1:
                curr      += 1
                max_consec = max(max_consec, curr)
            else:
                curr = 1

        return soma, pares, impares, primos_c, fib_c, borda_c, max_consec

    # =========================================================
    # PROCESSAR E SALVAR
    # =========================================================

    def processar_e_salvar(self, data_json):
        """Valida integralmente um resultado e confirma a gravação no SQLite."""
        try:
            if not isinstance(data_json, dict):
                raise ValueError("resultado deve ser um objeto JSON")
            concurso = int(data_json.get("numero", 0))
            if concurso < 1:
                raise ValueError("número do concurso ausente ou inválido")

            data_sorteio = str(data_json.get("dataApuracao", "")).strip()
            data_normalizada = None
            for formato in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    data_normalizada = datetime.strptime(
                        data_sorteio, formato).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            if data_normalizada is None:
                raise ValueError("data de apuração inválida: {}".format(
                    data_sorteio))

            dezenas = sorted(int(d) for d in data_json.get("listaDezenas", []))
            if (len(dezenas) != 15 or len(set(dezenas)) != 15 or
                    any(d < 1 or d > 25 for d in dezenas)):
                raise ValueError("o resultado deve ter 15 dezenas únicas entre 1 e 25")

            existente = self.db.get_resultado_concurso(concurso)
            if existente is not None:
                dezenas_locais = sorted(
                    int(existente["d{}".format(i)]) for i in range(1, 16)
                )
                if dezenas_locais != dezenas:
                    raise ValueError(
                        "conflito no concurso {}: local={} fonte={}".format(
                            concurso, dezenas_locais, dezenas)
                    )

            bitmask = self.bitmatrix.dezenas_para_bitmask(dezenas)
            metricas = self.calcular_metricas(dezenas)
            soma, pares, impares, primos_c, fib_c, borda_c, max_cons = metricas
            premios = self.extrair_premios(data_json)
            ganhadores = self.extrair_ganhadores(data_json)

            arrecadacao = data_json.get("valorArrecadado", 0) or 0
            if isinstance(arrecadacao, str):
                arrecadacao = CaixaClient._valor_monetario(arrecadacao)

            dados = (
                concurso, data_normalizada, *dezenas,
                bitmask, soma, pares, impares, primos_c, fib_c, borda_c,
                max_cons,
                float(premios[11]), float(premios[12]),
                float(premios[13]), float(premios[14]),
                float(premios[15]),
                int(ganhadores[11]), int(ganhadores[12]),
                int(ganhadores[13]), int(ganhadores[14]),
                int(ganhadores[15]), float(arrecadacao),
            )
            preservar_premios = not bool(
                data_json.get("_premios_disponiveis", bool(
                    data_json.get("listaRateioPremio")))
            )
            self.db.inserir_resultado(
                dados, preservar_premios=preservar_premios)
            # v11.3 — captura a ordem real de sorteio quando a fonte traz
            # (campo oficial dezenasSorteadasOrdemSorteio). Falha aqui não
            # rejeita o concurso: a ordem pode ser completada depois.
            ordem = data_json.get("ordem_sorteio")
            if ordem:
                try:
                    self.db.salvar_ordem(concurso, ordem)
                except (ValueError, sqlite3.Error):
                    pass
            return True
        except (TypeError, ValueError, OverflowError, OSError, sqlite3.Error) as exc:
            print("[HISTÓRICO] Concurso rejeitado: {}".format(exc))
            return False

    # =========================================================
    # CARGA HISTÓRICA COMPLETA
    # =========================================================

    def carregar_historico_completo(self, callback=None):
        """Preenche todos os concursos ausentes até a última fonte disponível."""
        return self._sincronizar_historico(callback=callback, completo=True)

    def _registrar_sincronizacao(self, inicio, resultado):
        try:
            self.db.registrar_atualizacao_historico((
                inicio,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                resultado.get("status", "erro"),
                resultado.get("fonte"),
                int(resultado.get("ultimo_banco_antes", 0)),
                int(resultado.get("ultimo_remoto", 0)),
                int(resultado.get("ultimo_banco_depois", 0)),
                int(resultado.get("novos", 0)),
                int(resultado.get("recuperados", 0)),
                int(resultado.get("erros", 0)),
                json.dumps({
                    "msg": resultado.get("msg"),
                    "falhas": resultado.get("falhas", []),
                    "diagnostico": resultado.get("diagnostico", {}),
                }, ensure_ascii=False),
            ))
        except Exception as exc:
            print("[HISTÓRICO] Falha ao gravar auditoria: {}".format(exc))

    def _sincronizar_historico(self, callback=None, completo=False):
        inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ultimo_antes = self.db.get_ultimo_concurso() or 0
        resultado_base = {
            "status": "erro", "fonte": None,
            "ultimo_banco_antes": ultimo_antes,
            "ultimo_remoto": 0, "ultimo_banco_depois": ultimo_antes,
            "novos": 0, "recuperados": 0, "erros": 0, "falhas": [],
        }
        if callback:
            callback(0, 0, 1, "Consultando resultado mais recente...")

        ultimo_data = self.buscar_ultimo_resultado()
        diagnostico = self.client.diagnostico()
        resultado_base["diagnostico"] = diagnostico
        if not ultimo_data:
            resultado_base.update({
                "msg": "Nenhuma fonte de resultados respondeu. "
                       "Consulte o diagnóstico da atualização.",
                "erros": 1,
            })
            self._registrar_sincronizacao(inicio, resultado_base)
            return resultado_base

        try:
            ultimo_remoto = int(ultimo_data.get("numero", 0))
        except (TypeError, ValueError):
            ultimo_remoto = 0
        fonte = ultimo_data.get("_fonte") or diagnostico.get("fonte")
        resultado_base.update({"fonte": fonte, "ultimo_remoto": ultimo_remoto})
        if ultimo_remoto < 1:
            resultado_base.update({"msg": "Fonte retornou concurso inválido", "erros": 1})
            self._registrar_sincronizacao(inicio, resultado_base)
            return resultado_base

        if ultimo_remoto < ultimo_antes:
            resultado_base.update({
                "status": "aviso",
                "msg": (
                    "A fonte {} está atrás do banco local ({} < {}). "
                    "Nenhum dado foi sobrescrito."
                ).format(fonte, ultimo_remoto, ultimo_antes),
            })
            self._registrar_sincronizacao(inicio, resultado_base)
            return resultado_base

        faltantes = self._descobrir_faltantes(ultimo_remoto)
        # Atualiza rateio/metadados do último mesmo quando ele já existe.
        if ultimo_remoto not in faltantes:
            if not self.processar_e_salvar(ultimo_data):
                resultado_base["erros"] += 1
                resultado_base["falhas"].append({
                    "concurso": ultimo_remoto,
                    "erro": "último concurso não passou na validação",
                })

        alvos = faltantes if completo else faltantes
        total = len(alvos)
        if callback:
            callback(0, 0, total,
                     "Sincronizando {} concurso(s) ausente(s)...".format(total))

        for indice, concurso in enumerate(alvos, 1):
            dados = (ultimo_data if concurso == ultimo_remoto
                     else self.buscar_concurso(concurso))
            if not dados:
                resultado_base["erros"] += 1
                resultado_base["falhas"].append({
                    "concurso": concurso,
                    "erro": self.client.diagnostico(),
                })
            elif self.processar_e_salvar(dados):
                if concurso > ultimo_antes:
                    resultado_base["novos"] += 1
                else:
                    resultado_base["recuperados"] += 1
            else:
                resultado_base["erros"] += 1
                resultado_base["falhas"].append({
                    "concurso": concurso,
                    "erro": "resultado rejeitado pela validação",
                })

            if dados and dados.get("_fonte") != "github_snapshot":
                time.sleep(0.08)
            if callback and (indice == total or indice % 10 == 0):
                callback(concurso, indice - resultado_base["erros"], total,
                         "Concurso {} ({}/{})".format(concurso, indice, total))

        ultimo_depois = self.db.get_ultimo_concurso() or 0
        restantes = self._descobrir_faltantes(max(ultimo_remoto, ultimo_depois))
        resultado_base["ultimo_banco_depois"] = ultimo_depois
        resultado_base["faltantes_restantes"] = restantes[:100]
        if resultado_base["erros"]:
            resultado_base["status"] = "parcial" if ultimo_depois >= ultimo_antes else "erro"
        else:
            resultado_base["status"] = "ok"
        resultado_base["msg"] = (
            "Histórico sincronizado pela fonte {}: banco {} → {}; "
            "{} novo(s), {} recuperado(s), {} erro(s)."
        ).format(
            fonte, ultimo_antes, ultimo_depois,
            resultado_base["novos"], resultado_base["recuperados"],
            resultado_base["erros"],
        )
        self._registrar_sincronizacao(inicio, resultado_base)
        return resultado_base

    def _descobrir_faltantes(self, ultimo_concurso):
        """Descobre quais concursos não estão no banco"""
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT concurso FROM resultados ORDER BY concurso")
        no_banco = set(row[0] for row in cursor.fetchall())
        conn.close()

        faltantes = [
            c for c in range(1, ultimo_concurso + 1)
            if c not in no_banco
        ]
        return faltantes

    # =========================================================
    # ATUALIZAÇÃO DIÁRIA
    # =========================================================

    def atualizar_diario(self):
        """Sincronização incremental validada, com recuperação de lacunas."""
        return self._sincronizar_historico(callback=None, completo=False)

    # =========================================================
    # BUSCAR PRÊMIOS AO VIVO DO PRÓXIMO SORTEIO
    # =========================================================

    def buscar_estimativa_premio(self):
        """
        Busca estimativa de prêmio para o próximo concurso.

        Correção: as fontes de contingência (e alguns espelhos da fonte
        oficial) não informam `proximoConcurso`, então o painel de prêmios
        ficava eternamente zerado. Agora, quando a fonte externa não traz o
        dado, o próximo concurso é derivado do último resultado conhecido
        (número + 1) ou do banco local, e a estimativa cai para a média
        histórica de 15 pontos.
        """
        try:
            ultimo = None
            try:
                ultimo = self.buscar_ultimo_resultado()
            except Exception as exc:
                print(f"[AVISO] Estimativa sem fonte externa: {exc}")

            proximo = 0
            estimativa = 0.0
            data_prox = ""
            fonte = "indisponivel"

            if ultimo:
                try:
                    proximo = int(ultimo.get("proximoConcurso") or 0)
                except (TypeError, ValueError):
                    proximo = 0
                if proximo > 0:
                    fonte = "caixa"
                else:
                    # Fonte não informou: deriva do último sorteio apurado.
                    try:
                        numero = int(ultimo.get("numero") or 0)
                    except (TypeError, ValueError):
                        numero = 0
                    if numero > 0:
                        proximo = numero + 1
                        fonte = "derivado_ultimo_resultado"

                bruta = ultimo.get("valorEstimadoProximoConcurso", 0)
                if isinstance(bruta, str):
                    try:
                        bruta = float(
                            bruta.replace("R$", "")
                                 .replace(".", "")
                                 .replace(",", ".")
                                 .strip()
                        )
                    except ValueError:
                        bruta = 0
                estimativa = float(bruta or 0)
                data_prox = ultimo.get("dataProximoConcurso", "") or ""

            if proximo <= 0:
                # Último recurso: banco local (sempre disponível offline).
                ultimo_local = int(self.db.get_ultimo_concurso() or 0)
                if ultimo_local > 0:
                    proximo = ultimo_local + 1
                    fonte = "banco_local"

            if estimativa <= 0:
                # Sem valor oficial: usa a média histórica de 15 pontos.
                try:
                    medias = self.db.get_media_premios()
                    if medias and medias["media_15"]:
                        estimativa = round(float(medias["media_15"]), 2)
                except Exception:
                    pass

            return {
                "proximo_concurso": proximo,
                "estimativa_15":    float(estimativa or 0),
                "data_proximo":     data_prox,
                "fonte_estimativa": fonte,
            }
        except Exception as e:
            print(f"[ERRO] Estimativa: {e}")
            return None

    # =========================================================
    # GETTERS
    # =========================================================

    def get_historico_completo(self):
        return self.db.get_todos_resultados()

    def get_ultimo_resultado_local(self):
        """Retorna último resultado do banco local"""
        resultados = self.db.get_todos_resultados()
        return resultados[-1] if resultados else None

    def get_premios_concurso(self, concurso):
        """Retorna prêmios reais de um concurso específico"""
        return self.db.get_premios_concurso(concurso)

    def get_status_base(self):
        """Integridade local, última execução e diagnóstico das fontes."""
        ultimo = self.db.get_ultimo_concurso() or 0
        conn = self.db.get_conn()
        total = conn.execute("SELECT COUNT(*) FROM resultados").fetchone()[0]
        conn.close()
        ultima = self.db.get_ultima_atualizacao_historico()
        faltantes = self._descobrir_faltantes(ultimo) if ultimo else []
        return {
            "ultimo_concurso": ultimo,
            "total_concursos": total,
            "cobertura": f"{total}/{ultimo}" if ultimo else "0/0",
            "faltantes": faltantes,
            "base_integra": not faltantes and total == ultimo,
            "ultima_atualizacao": dict(ultima) if ultima else None,
            "diagnostico_fonte": self.client.diagnostico(),
            "consultado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
