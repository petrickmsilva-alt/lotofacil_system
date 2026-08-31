"""Cliente resiliente e centralizado para resultados da Lotofácil.

A Caixa continua sendo a fonte primária. Duas fontes de contingência são usadas
somente quando a origem oficial está indisponível, sempre com identificação da
procedência e validação estrutural antes de qualquer gravação.
"""
from __future__ import annotations

import copy
import os
import re
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ErroFonteResultados(RuntimeError):
    """Falha controlada ao consultar ou validar uma fonte de resultados."""


def _limpar(valor):
    """Normaliza texto livre (espaços múltiplos / None) sem levantar erro."""
    return re.sub(r"\s+", " ", str(valor or "")).strip()


class CaixaClient:
    OFICIAL_BASE = os.getenv(
        "LOTOFACIL_API_URL",
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil",
    ).rstrip("/")
    CONTINGENCIA_API_BASE = os.getenv(
        "LOTOFACIL_FALLBACK_API_URL",
        "https://api.guidi.dev.br/loteria/lotofacil",
    ).rstrip("/")
    CONTINGENCIA_HISTORICO = os.getenv(
        "LOTOFACIL_FALLBACK_HISTORY_URL",
        "https://raw.githubusercontent.com/eitchtee/loterias.json/"
        "main/data/lotofacil.json",
    )

    HEADERS = {
        "User-Agent": "LotoFacil-Inteligencia-Magna/9.0",
        "Accept": "application/json, text/plain;q=0.9, */*;q=0.1",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Origin": "https://loterias.caixa.gov.br",
        "Referer": "https://loterias.caixa.gov.br/",
        "Cache-Control": "no-cache",
    }

    def __init__(self, session=None, timeout=(5, 20), cache_segundos=900):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.cache_segundos = int(cache_segundos)
        self._lock = threading.RLock()
        self._historico_cache = None
        self._historico_cache_em = 0.0
        self._oficial_indisponivel_ate = 0.0
        self._contingencia_api_indisponivel_ate = 0.0
        self._ultimo_diagnostico = {
            "status": "nao_testado", "fonte": None, "tentativas": []
        }
        self.session.headers.update(self.HEADERS)
        if hasattr(self.session, "mount"):
            retry = Retry(
                total=2,
                connect=2,
                read=2,
                status=2,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                respect_retry_after_header=True,
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    @staticmethod
    def _valor_monetario(valor):
        if valor in (None, "", "-"):
            return 0.0
        if isinstance(valor, (int, float)):
            return float(valor)
        texto = str(valor).replace("R$", "").replace(" ", "").strip()
        if not texto or texto == "-":
            return 0.0
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        return float(texto)

    @staticmethod
    def _inteiro(valor, padrao=0):
        try:
            if isinstance(valor, str):
                valor = valor.replace(".", "").strip()
            return int(valor)
        except (TypeError, ValueError):
            return int(padrao)

    def _get_json(self, url, fonte):
        inicio = time.monotonic()
        try:
            resposta = self.session.get(url, timeout=self.timeout)
            duracao = round((time.monotonic() - inicio) * 1000)
            if resposta.status_code != 200:
                raise ErroFonteResultados(
                    "HTTP {} em {}".format(resposta.status_code, fonte)
                )
            try:
                conteudo = resposta.json()
            except ValueError as exc:
                raise ErroFonteResultados(
                    "resposta não é JSON válido em {}".format(fonte)
                ) from exc
            return conteudo, {
                "fonte": fonte, "url": url, "http": resposta.status_code,
                "duracao_ms": duracao, "status": "ok",
            }
        except (requests.RequestException, ErroFonteResultados) as exc:
            return None, {
                "fonte": fonte, "url": url, "status": "erro",
                "erro": "{}: {}".format(type(exc).__name__, exc),
            }

    @classmethod
    def _normalizar_rateio(cls, itens):
        rateio = []
        mapa_faixa = {1: 15, 2: 14, 3: 13, 4: 12, 5: 11}
        for item in itens or []:
            faixa = cls._inteiro(item.get("faixa"), 0)
            acertos_raw = item.get("numeroAcertos", item.get("acertos", 0))
            if isinstance(acertos_raw, str):
                encontrado = re.search(r"(1[1-5])", acertos_raw)
                acertos = int(encontrado.group(1)) if encontrado else 0
            else:
                acertos = cls._inteiro(acertos_raw, 0)
            if acertos not in range(11, 16):
                acertos = mapa_faixa.get(faixa, 0)
            if acertos not in range(11, 16):
                continue
            ganhadores = cls._inteiro(
                item.get("numeroDeGanhadores", item.get("ganhadores", 0)), 0
            )
            premio = cls._valor_monetario(
                item.get("valorPremio", item.get("premio", 0))
            )
            rateio.append({
                "faixa": faixa or 16 - acertos,
                "numeroAcertos": acertos,
                "numeroDeGanhadores": ganhadores,
                "valorPremio": premio,
            })
        return rateio

    @classmethod
    def normalizar(cls, bruto, fonte):
        if not isinstance(bruto, dict):
            raise ErroFonteResultados("objeto de resultado inválido")

        if "numero" in bruto or "listaDezenas" in bruto:
            concurso = cls._inteiro(bruto.get("numero"), 0)
            data = bruto.get("dataApuracao", "")
            dezenas = bruto.get("listaDezenas", [])
            rateio = cls._normalizar_rateio(bruto.get("listaRateioPremio", []))
            normalizado = dict(bruto)
            normalizado.update({
                "numero": concurso,
                "dataApuracao": data,
                "listaDezenas": dezenas,
                "listaRateioPremio": rateio,
                # Dados do próximo sorteio: alguns espelhos da fonte oficial
                # omitem essas chaves e o painel de prêmios ficava zerado.
                "proximoConcurso": cls._inteiro(
                    bruto.get("proximoConcurso",
                              bruto.get("numeroConcursoProximo", 0)), 0
                ),
                "dataProximoConcurso": bruto.get("dataProximoConcurso", ""),
                "valorEstimadoProximoConcurso": bruto.get(
                    "valorEstimadoProximoConcurso", 0
                ),
            })
        else:
            concurso = cls._inteiro(bruto.get("concurso"), 0)
            data = bruto.get("data", bruto.get("dataApuracao", ""))
            dezenas = bruto.get(
                "dezenas", bruto.get("resultado", bruto.get("listaDezenas", []))
            )
            rateio = cls._normalizar_rateio(
                bruto.get("premiacoes", bruto.get("listaRateioPremio", []))
            )
            normalizado = {
                "numero": concurso,
                "dataApuracao": data,
                "listaDezenas": dezenas,
                "listaRateioPremio": rateio,
                "valorArrecadado": bruto.get(
                    "valorArrecadado", bruto.get("arrecadacao", 0)
                ),
                "proximoConcurso": bruto.get(
                    "proximoConcurso", bruto.get("proxConcurso", 0)
                ),
                "dataProximoConcurso": bruto.get(
                    "dataProximoConcurso", bruto.get("dataProxConcurso", "")
                ),
                "valorEstimadoProximoConcurso": bruto.get(
                    "valorEstimadoProximoConcurso", 0
                ),
            }

        try:
            dezenas_int = sorted(int(d) for d in normalizado["listaDezenas"])
        except (TypeError, ValueError) as exc:
            raise ErroFonteResultados("dezenas não numéricas") from exc
        if (concurso < 1 or len(dezenas_int) != 15 or
                len(set(dezenas_int)) != 15 or
                any(d < 1 or d > 25 for d in dezenas_int)):
            raise ErroFonteResultados(
                "resultado inválido: concurso={}, dezenas={}".format(
                    concurso, dezenas_int)
            )
        if not isinstance(data, str) or not data.strip():
            raise ErroFonteResultados("data de apuração ausente")

        normalizado["listaDezenas"] = ["{:02d}".format(d) for d in dezenas_int]
        normalizado["_fonte"] = fonte
        # v11.7 — local físico do sorteio (para a telemetria INMET).
        # A Caixa traz `local` + `cidadeUF`; espelhos costumam manter as
        # mesmas chaves. Sempre normalizadas para strings vazias quando
        # ausentes, para o `extrair_local` decidir sem exceção.
        normalizado["local"] = _limpar(bruto.get("local")) \
            if bruto.get("local") is not None else ""
        normalizado["cidadeUF"] = _limpar(
            bruto.get("cidadeUF") or bruto.get("cidade_uf")) \
            if (bruto.get("cidadeUF") or bruto.get("cidade_uf")) else ""
        # v11.3 — ordem real de sorteio (1ª, 2ª, ... bola), se a fonte
        # fornecer (campo oficial `dezenasSorteadasOrdemSorteio`; espelhos
        # usam `listaDezenasOrdemSorteio`). Só é aceita se tiver 15
        # dezenas únicas 1–25 formando o MESMO conjunto de listaDezenas.
        ordem_bruta = (bruto.get("dezenasSorteadasOrdemSorteio") or
                       bruto.get("listaDezenasOrdemSorteio"))
        normalizado["ordem_sorteio"] = None
        if isinstance(ordem_bruta, (list, tuple)):
            try:
                ordem_int = [int(d) for d in ordem_bruta]
            except (TypeError, ValueError):
                ordem_int = []
            if (len(ordem_int) == 15 and len(set(ordem_int)) == 15 and
                    all(1 <= d <= 25 for d in ordem_int) and
                    set(ordem_int) == set(dezenas_int)):
                normalizado["ordem_sorteio"] = ordem_int
        faixas_rateio = {int(item["numeroAcertos"]) for item in rateio}
        normalizado["_premios_disponiveis"] = \
            faixas_rateio == {11, 12, 13, 14, 15}
        return normalizado

    def _historico_contingencia(self, forcar=False):
        with self._lock:
            agora = time.monotonic()
            if (not forcar and self._historico_cache is not None and
                    agora - self._historico_cache_em < self.cache_segundos):
                return self._historico_cache, {
                    "fonte": "github_snapshot", "status": "cache"
                }

            bruto, tentativa = self._get_json(
                self.CONTINGENCIA_HISTORICO, "github_snapshot"
            )
            if not isinstance(bruto, list) or not bruto:
                raise ErroFonteResultados(
                    tentativa.get("erro", "snapshot histórico inválido")
                )
            indice = {}
            for item in bruto:
                try:
                    normalizado = self.normalizar(item, "github_snapshot")
                    indice[int(normalizado["numero"])] = normalizado
                except ErroFonteResultados:
                    continue
            if not indice:
                raise ErroFonteResultados("snapshot sem concursos válidos")
            self._historico_cache = indice
            self._historico_cache_em = agora
            return indice, tentativa

    def _tentar_normalizar(self, url, fonte):
        bruto, tentativa = self._get_json(url, fonte)
        if bruto is None:
            return None, tentativa
        try:
            return self.normalizar(bruto, fonte), tentativa
        except ErroFonteResultados as exc:
            tentativa.update({"status": "erro", "erro": str(exc)})
            return None, tentativa

    def _consultar(self, concurso=None):
        tentativas = []
        agora = time.monotonic()

        if agora >= self._oficial_indisponivel_ate:
            url = (self.OFICIAL_BASE if concurso is None
                   else "{}/{}".format(self.OFICIAL_BASE, int(concurso)))
            resultado, tentativa = self._tentar_normalizar(url, "caixa_oficial")
            tentativas.append(tentativa)
            if resultado is not None:
                self._ultimo_diagnostico = {
                    "status": "ok", "fonte": "caixa_oficial",
                    "tentativas": tentativas,
                }
                return resultado
            # Evita repetir um handshake/timeout sabidamente quebrado em cada
            # concurso da mesma sincronização.
            self._oficial_indisponivel_ate = agora + 300

        if agora >= self._contingencia_api_indisponivel_ate:
            url_guidi = (
                "{}/ultimo".format(self.CONTINGENCIA_API_BASE)
                if concurso is None else
                "{}/{}".format(self.CONTINGENCIA_API_BASE, int(concurso))
            )
            resultado, tentativa = self._tentar_normalizar(
                url_guidi, "api_guidi")
            tentativas.append(tentativa)
            if resultado is not None:
                self._ultimo_diagnostico = {
                    "status": "contingencia", "fonte": "api_guidi",
                    "tentativas": tentativas,
                }
                return resultado
            self._contingencia_api_indisponivel_ate = agora + 300

        try:
            historico, tentativa_hist = self._historico_contingencia()
            tentativas.append(tentativa_hist)
            numero = max(historico) if concurso is None else int(concurso)
            resultado = copy.deepcopy(historico.get(numero))
            if resultado is not None:
                self._ultimo_diagnostico = {
                    "status": "contingencia", "fonte": "github_snapshot",
                    "tentativas": tentativas,
                }
                return resultado
        except ErroFonteResultados as exc:
            tentativas.append({
                "fonte": "github_snapshot", "status": "erro",
                "erro": str(exc),
            })

        self._ultimo_diagnostico = {
            "status": "erro", "fonte": None, "tentativas": tentativas,
        }
        return None

    def buscar_ultimo(self):
        return self._consultar(concurso=None)

    def buscar_concurso(self, concurso):
        numero = self._inteiro(concurso, 0)
        if numero < 1:
            self._ultimo_diagnostico = {
                "status": "erro", "fonte": None,
                "tentativas": [{"erro": "concurso inválido"}],
            }
            return None
        return self._consultar(concurso=numero)

    def diagnostico(self):
        return copy.deepcopy(self._ultimo_diagnostico)
