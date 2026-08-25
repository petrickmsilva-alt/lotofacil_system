"""
============================================================
ALIMENTADOR QUÂNTICO - DATA INGESTION COMPLETO
Busca TODOS os resultados desde o concurso 1 até hoje
Busca valores de prêmios REAIS da Caixa Econômica Federal
API Oficial: servicebus2.caixa.gov.br
============================================================
"""
import requests
import time
from datetime import datetime
from config import PRIMOS, FIBONACCI, BORDA
from database.db_manager import DBManager
from .bitmatrix import BitMatrix


class DataLoader:

    # URL oficial da API da Caixa
    URL_BASE      = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    URL_RESULTADO = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{}"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Origin":          "https://loterias.caixa.gov.br",
        "Referer":         "https://loterias.caixa.gov.br/",
    }

    def __init__(self):
        self.db         = DBManager()
        self.bitmatrix  = BitMatrix()
        self.session    = requests.Session()
        self.session.headers.update(self.HEADERS)

    # =========================================================
    # BUSCA DE RESULTADOS
    # =========================================================

    def buscar_ultimo_resultado(self):
        """Busca o resultado mais recente (sem número = último)"""
        try:
            resp = self.session.get(self.URL_BASE, timeout=20)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[ERRO] Último resultado: {e}")
        return None

    def buscar_concurso(self, numero):
        """Busca resultado de um concurso específico"""
        try:
            url  = self.URL_RESULTADO.format(numero)
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[ERRO] Concurso {numero}: {e}")
        return None

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
        """Processa JSON da Caixa e salva no banco completo"""
        try:
            concurso     = int(data_json.get("numero", 0))
            data_sorteio = data_json.get("dataApuracao", "")

            # Normalizar data
            try:
                dt = datetime.strptime(data_sorteio, "%d/%m/%Y")
                data_sorteio = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

            # Dezenas
            dezenas_str = data_json.get("listaDezenas", [])
            dezenas     = sorted([int(d) for d in dezenas_str])

            if len(dezenas) != 15:
                return False

            # Bitmask
            bitmask = self.bitmatrix.dezenas_para_bitmask(dezenas)

            # Métricas
            soma, pares, impares, primos_c, fib_c, borda_c, max_cons = \
                self.calcular_metricas(dezenas)

            # Prêmios REAIS
            premios    = self.extrair_premios(data_json)
            ganhadores = self.extrair_ganhadores(data_json)

            # Acumulado
            acumulado = data_json.get("valorArrecadado", 0) or 0
            if isinstance(acumulado, str):
                try:
                    acumulado = float(
                        acumulado.replace("R$","")
                                 .replace(".","")
                                 .replace(",",".")
                                 .strip()
                    )
                except Exception:
                    acumulado = 0.0

            dados = (
                concurso,
                data_sorteio,
                *dezenas,                    # d1..d15
                bitmask,
                soma,
                pares,
                impares,
                primos_c,
                fib_c,
                borda_c,
                max_cons,
                # Prêmios reais
                float(premios[11]),
                float(premios[12]),
                float(premios[13]),
                float(premios[14]),
                float(premios[15]),
                # Ganhadores
                int(ganhadores[11]),
                int(ganhadores[12]),
                int(ganhadores[13]),
                int(ganhadores[14]),
                int(ganhadores[15]),
                # Arrecadação
                float(acumulado),
            )

            self.db.inserir_resultado(dados)
            return True

        except Exception as e:
            print(f"[ERRO] Processar concurso: {e}")
            return False

    # =========================================================
    # CARGA HISTÓRICA COMPLETA
    # =========================================================

    def carregar_historico_completo(self, callback=None):
        """
        Carrega TODOS os resultados desde o concurso 1.
        Usa busca binária para localizar o primeiro concurso.
        """

        if callback:
            callback(0, 0, 1, "Buscando último concurso...")

        # Buscar último concurso
        ultimo_data = self.buscar_ultimo_resultado()
        if not ultimo_data:
            return {
                "status": "erro",
                "msg": "Não foi possível acessar a API da Caixa"
            }

        ultimo_concurso = int(ultimo_data.get("numero", 0))
        self.processar_e_salvar(ultimo_data)

        if callback:
            callback(ultimo_concurso, 1, ultimo_concurso,
                     f"Último concurso: {ultimo_concurso}")

        # Descobrir quais concursos faltam
        concursos_faltantes = self._descobrir_faltantes(ultimo_concurso)

        total      = len(concursos_faltantes)
        carregados = 0
        erros      = 0

        if callback:
            callback(0, 0, total,
                     f"Baixando {total} concursos faltantes...")

        for idx, concurso in enumerate(concursos_faltantes):
            try:
                data = self.buscar_concurso(concurso)
                if data:
                    ok = self.processar_e_salvar(data)
                    if ok:
                        carregados += 1
                    else:
                        erros += 1
                else:
                    erros += 1

                # Respeitar rate limit da Caixa
                time.sleep(0.25)

                if callback and (idx % 10 == 0 or idx == total - 1):
                    callback(
                        concurso, carregados, total,
                        f"Concurso {concurso} ({carregados}/{total})"
                    )

            except Exception as e:
                erros += 1
                print(f"[ERRO] Concurso {concurso}: {e}")

        return {
            "status":          "ok",
            "ultimo_concurso": ultimo_concurso,
            "total_carregados": carregados,
            "erros":           erros,
            "total_no_banco":  self.db.get_ultimo_concurso(),
        }

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
        """
        Atualização diária automática.
        Verifica se há novos concursos e baixa apenas os novos.
        Também atualiza os prêmios do último concurso (rateio).
        """
        ultimo_no_banco = self.db.get_ultimo_concurso() or 0

        # Buscar último da Caixa
        ultimo_data = self.buscar_ultimo_resultado()
        if not ultimo_data:
            return {
                "status": "erro",
                "msg":    "Sem conexão com a Caixa"
            }

        ultimo_caixa = int(ultimo_data.get("numero", 0))

        # Sempre re-salvar o último (pode ter rateio atualizado)
        self.processar_e_salvar(ultimo_data)

        novos = 0
        if ultimo_caixa > ultimo_no_banco:
            for c in range(ultimo_no_banco + 1, ultimo_caixa + 1):
                data = self.buscar_concurso(c)
                if data:
                    self.processar_e_salvar(data)
                    novos += 1
                time.sleep(0.3)

        # Verificar faltantes antigos
        faltantes = self._descobrir_faltantes(ultimo_caixa)
        recuperados = 0
        for c in faltantes[:20]:   # no máximo 20 por vez
            data = self.buscar_concurso(c)
            if data:
                self.processar_e_salvar(data)
                recuperados += 1
            time.sleep(0.3)

        return {
            "status":          "ok",
            "ultimo_caixa":    ultimo_caixa,
            "ultimo_banco":    ultimo_no_banco,
            "novos":           novos,
            "recuperados":     recuperados,
            "msg": (
                f"Atualizado até concurso {ultimo_caixa}. "
                f"{novos} novos, {recuperados} recuperados."
            ),
        }

    # =========================================================
    # BUSCAR PRÊMIOS AO VIVO DO PRÓXIMO SORTEIO
    # =========================================================

    def buscar_estimativa_premio(self):
        """
        Busca estimativa de prêmio para o próximo concurso.
        """
        try:
            ultimo = self.buscar_ultimo_resultado()
            if not ultimo:
                return None

            proximo   = int(ultimo.get("proximoConcurso", 0))
            estimativa = ultimo.get("valorEstimadoProximoConcurso", 0)

            if isinstance(estimativa, str):
                estimativa = float(
                    estimativa.replace("R$","")
                              .replace(".","")
                              .replace(",",".")
                              .strip()
                )

            data_prox = ultimo.get("dataProximoConcurso", "")

            return {
                "proximo_concurso": proximo,
                "estimativa_15":    float(estimativa or 0),
                "data_proximo":     data_prox,
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
        """Status completo da base de dados"""
        ultimo = self.db.get_ultimo_concurso() or 0
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM resultados")
        total = cursor.fetchone()[0]
        conn.close()

        return {
            "ultimo_concurso": ultimo,
            "total_concursos": total,
            "cobertura":       f"{total}/{ultimo}" if ultimo else "0/0",
            "atualizado_em":   datetime.now().strftime("%d/%m/%Y %H:%M"),
        }