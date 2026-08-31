"""
====================================================================
TELEMETRIA INMET POR LOCAL DO SORTEIO (v11.7)
====================================================================
Fonte de evidência meteorológica para a Inteligência Magna.

O sorteio da Lotofácil acontece num local físico (o campo `local` /
`cidadeUF` do resultado oficial da Caixa). A telemetria resolve esse
local para um território brasileiro (cidade + UF + geocódigo IBGE +
coordenadas) e busca as condições atmosféricas no Instituto Nacional
de Meteorologia (INMET), usando apenas fontes públicas:

  1. INMET oficial (previsão/estações mais próxima + dados diários);
  2. Open-Meteo como contingência (mesmas coordenadas do local);
  3. neutro/padrão — nunca inventa medição, nunca bloqueia a Magna.

HONESTIDADE:
- Telemetria é evidência do AMBIENTE, não previsão de dezenas. O vetor
  que ela produz é inclinado com teto de ±10% e otimismo controlado.
- Correlação ≠ causa. A auto-auditoria walk-forward do clima (v11.2)
  continua valendo: a fonte só é ouvida pelo consenso na medida do que
  o passado justificar.
- Se a rede falhar, a resposta é `status=neutro` com padrão climatizado
  da UF — nunca um dado fabricado.
====================================================================
"""
import json
import re
import sqlite3
import unicodedata
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from config import DATABASE_PATH, TOTAL_DEZENAS

try:
    from scipy import stats as _sp  # noqa: F401 (usado pelos testes de z)
except Exception:  # pragma: no cover
    _sp = None

# ============================================================
# TERRITÓRIOS — capitais brasileiras conhecidas (geocódigo IBGE
# e coordenadas aproximadas do centro). Fontes públicas.
# ============================================================
CAPITAIS: Dict[str, Dict[str, Any]] = {
    "AC": {"cidade": "Rio Branco", "geocodigo": "1200401", "lat": -9.97475, "lon": -67.80790},
    "AL": {"cidade": "Maceió", "geocodigo": "2700402", "lat": -9.66599, "lon": -35.73500},
    "AP": {"cidade": "Macapá", "geocodigo": "1600303", "lat": 0.03493, "lon": -51.06940},
    "AM": {"cidade": "Manaus", "geocodigo": "1302603", "lat": -3.11903, "lon": -60.02173},
    "BA": {"cidade": "Salvador", "geocodigo": "2927408", "lat": -12.97775, "lon": -38.50163},
    "CE": {"cidade": "Fortaleza", "geocodigo": "2304400", "lat": -3.73186, "lon": -38.52667},
    "DF": {"cidade": "Brasília", "geocodigo": "5300108", "lat": -15.78014, "lon": -47.92917},
    "ES": {"cidade": "Vitória", "geocodigo": "3205309", "lat": -20.31547, "lon": -40.31280},
    "GO": {"cidade": "Goiânia", "geocodigo": "5208707", "lat": -16.68689, "lon": -49.26479},
    "MA": {"cidade": "São Luís", "geocodigo": "2111300", "lat": -2.53073, "lon": -44.30675},
    "MT": {"cidade": "Cuiabá", "geocodigo": "5103403", "lat": -15.60141, "lon": -56.09788},
    "MS": {"cidade": "Campo Grande", "geocodigo": "5002704", "lat": -20.44278, "lon": -54.64639},
    "MG": {"cidade": "Belo Horizonte", "geocodigo": "3106200", "lat": -19.91668, "lon": -43.93449},
    "PA": {"cidade": "Belém", "geocodigo": "1501402", "lat": -1.45583, "lon": -48.49036},
    "PB": {"cidade": "João Pessoa", "geocodigo": "2507507", "lat": -7.11950, "lon": -34.84500},
    "PR": {"cidade": "Curitiba", "geocodigo": "4106902", "lat": -25.42836, "lon": -49.27325},
    "PE": {"cidade": "Recife", "geocodigo": "2611606", "lat": -8.04756, "lon": -34.87700},
    "PI": {"cidade": "Teresina", "geocodigo": "2211001", "lat": -5.08964, "lon": -42.80155},
    "RJ": {"cidade": "Rio de Janeiro", "geocodigo": "3304557", "lat": -22.90685, "lon": -43.17290},
    "RN": {"cidade": "Natal", "geocodigo": "2408102", "lat": -5.79448, "lon": -35.21100},
    "RS": {"cidade": "Porto Alegre", "geocodigo": "4314902", "lat": -30.03465, "lon": -51.21766},
    "RO": {"cidade": "Porto Velho", "geocodigo": "1100205", "lat": -8.76116, "lon": -63.90043},
    "RR": {"cidade": "Boa Vista", "geocodigo": "1400100", "lat": 2.81972, "lon": -60.67342},
    "SC": {"cidade": "Florianópolis", "geocodigo": "4205407", "lat": -27.59487, "lon": -48.54822},
    "SP": {"cidade": "São Paulo", "geocodigo": "3550308", "lat": -23.54750, "lon": -46.63610},
    "SE": {"cidade": "Aracaju", "geocodigo": "2800308", "lat": -10.91106, "lon": -37.07165},
    "TO": {"cidade": "Palmas", "geocodigo": "1721000", "lat": -10.18432, "lon": -48.33361},
}

# Alias de locais que aparecem no resultado oficial da Caixa.
ALIASES_LOCAL: Dict[str, str] = {
    "espaço da sorte": "São Paulo/SP",
    "espaço caixa loterias - são paulo/sp": "São Paulo/SP",
    "espaço loterias": "São Paulo/SP",
    "sede": "São Paulo/SP",
}

LOCAL_PADRAO: Dict[str, Any] = {
    "local": "Espaço da Sorte (padrão)",
    "cidade_uf": "São Paulo/SP",
    "cidade": "São Paulo",
    "uf": "SP",
    "geocodigo": "3550308",
    "lat": -23.54750,
    "lon": -46.63610,
    "fonte_territorio": "padrao",
}

# Limite de inclinação do vetor de telemetria (±10%, como a v11.2)
TETO_INMET = 0.10
TILT_PARIDADE = 0.04  # ±4% por dezena via pressão (leve, nunca dita)


def _limpar(texto) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def _sem_acento(texto) -> str:
    """Desacentua e normaliza caixa para comparação de nomes de cidade."""
    nfkd = unicodedata.normalize("NFKD", _limpar(texto))
    return re.sub(r"[^A-Za-z0-9]", "", "".join(
        c for c in nfkd if not unicodedata.combining(c))).lower()


def _normalizar_cidade_uf(texto) -> Optional[str]:
    """Devolve 'Cidade/UF' a partir de qualquer grafia comum.

    Aceita: 'SÃO PAULO/SP', 'São Paulo, SP', 'SAO PAULO - SP',
    'São Paulo' (sem UF) e 'Espaço da Sorte'.
    """
    if texto is None:
        return None
    t = _limpar(texto)
    if not t:
        return None

    chave = re.sub(r"[^\w\s]", " ", t.lower())
    chave = re.sub(r"\s+", " ", chave).strip()
    if chave in ALIASES_LOCAL:
        t = ALIASES_LOCAL[chave]

    m = re.match(r"^(.+?)\s*[,/\-–]\s*([A-Za-zÀ-ÿ]{2})$", t)
    if m:
        cidade, uf = _limpar(m.group(1)), m.group(2).upper()
        if uf in CAPITAIS:
            # canonicaliza a grafia usando a tabela de capitais (SP ⇔ São Paulo)
            cap = CAPITAIS[uf]
            if _sem_acento(cidade) == _sem_acento(cap["cidade"]):
                cidade = cap["cidade"]
            return "{}/{}".format(cidade, uf)

    # Sem UF explícita: tenta bater com uma capital conhecida.
    t_norm = re.sub(r"[^\w]", "", t.lower())
    for uf, cap in CAPITAIS.items():
        cap_norm = re.sub(r"[^\w]", "", cap["cidade"].lower())
        if t_norm == cap_norm:
            return "{}/{}".format(cap["cidade"], uf)

    # Sobrou UF sozinha: 'SP' → capital da UF.
    if t.upper() in CAPITAIS:
        cap = CAPITAIS[t.upper()]
        return "{}/{}".format(cap["cidade"], t.upper())
    return None


class TerritorioInmet:
    """Resolve local do sorteio → território com geocódigo e coordenadas."""

    def __init__(self, capitais: Optional[Dict[str, Dict[str, Any]]] = None):
        self.capitais = capitais or CAPITAIS

    def resolver(self, local: Any = None, cidade_uf: Any = None) -> Dict[str, Any]:
        """Monta o território de um sorteio sem nunca levantar exceção."""
        padrao = dict(LOCAL_PADRAO)
        cidade_uf_norm = _normalizar_cidade_uf(cidade_uf) or \
            _normalizar_cidade_uf(local)
        if not cidade_uf_norm:
            padrao["fonte_territorio"] = "padrao"
            padrao["detalhe"] = (
                "local do sorteio desconhecido — usando padrão climatizado "
                "de São Paulo/SP"
            )
            return padrao

        cidade, uf = cidade_uf_norm.split("/", 1)
        cap = self.capitais.get(uf.upper())
        if not cap:
            padrao["cidade_uf"] = cidade_uf_norm
            padrao["uf"] = uf.upper()
            padrao["detalhe"] = (
                "UF sem referência de capital — usando padrão de São Paulo/SP"
            )
            return padrao

        anyway = {
            "local": _limpar(local) or cidade_uf_norm,
            "cidade_uf": cidade_uf_norm,
            "cidade": _limpar(cidade),
            "uf": uf.upper(),
            "geocodigo": cap["geocodigo"],
            "lat": cap["lat"],
            "lon": cap["lon"],
            "fonte_territorio": "cidade_uf",
            "detalhe": "cidade/UF informada pelo resultado oficial da Caixa",
        }
        if _normalizar_cidade_uf(cidade) is None:
            anyway["fonte_territorio"] = "uf_capital"
            anyway["detalhe"] = (
                "cidade fora da tabela de capitais — usando a capital da UF "
                "como referência geográfica"
            )
        return anyway


def extrair_local(resultado: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extrai o local do sorteio de um resultado normalizado da Caixa.

    O payload oficial traz `local` (ex.: 'ESPAÇO DA SORTE') e `cidadeUF`
    (ex.: 'São Paulo/SP'); espelhos históricos costumam manter as mesmas
    chaves. Devolve None quando não há informação de local.
    """
    if not isinstance(resultado, dict):
        return None
    local = resultado.get("local")
    cidade_uf = (
        resultado.get("cidadeUF")
        or resultado.get("cidade_uf")
        or resultado.get("cidadeUf")
    )
    cidade_uf_norm = _normalizar_cidade_uf(cidade_uf) or \
        _normalizar_cidade_uf(local)
    if not cidade_uf_norm and not local:
        return None
    return {
        "local": _limpar(local) or None,
        "cidade_uf": cidade_uf_norm or _limpar(cidade_uf) or None,
        "fonte_dados": "resultado_caixa",
    }


# ============================================================
# CLIENTE — INMET oficial + contingência Open-Meteo + neutro
# ============================================================
class InmetClient:
    """Busca telemetria atmosférica por local do sorteio.

    `getter` é injetável nos testes (url -> object/None/raise) e em
    produção usa `urllib` com timeout curto, como o MotorClima.
    """

    BASE_PREVISAO = "https://apiprevmet3.inmet.gov.br"
    BASE_DADOS = "https://apitempo.inmet.gov.br"
    BASE_CONTINGENCIA = "https://api.open-meteo.com/v1/forecast"
    USER_AGENT = "MagnaInmet/11.7"

    def __init__(self, getter: Optional[Callable[[str], Optional[Any]]] = None,
                 timeout: float = 6.0):
        self.getter = getter or self._get_http
        self.timeout = timeout

    def _get_http(self, url: str) -> Optional[Any]:
        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---------- resolução de território ----------------
    def _territorio(self, local: Any = None,
                    cidade_uf: Any = None) -> Dict[str, Any]:
        return TerritorioInmet().resolver(local, cidade_uf)

    # ---------- 1. INMET oficial -------------------------
    def _estacao_proxima(self, territorio: Dict[str, Any]) -> Dict[str, Any]:
        url = "{}/estacao/proxima/{}".format(
            self.BASE_PREVISAO, territorio["geocodigo"])
        bruto = self.getter(url)
        if bruto is None:
            raise ValueError("INMET sem resposta de estação próxima")
        if isinstance(bruto, list):
            bruto = bruto[0] if bruto else {}
        if not isinstance(bruto, dict):
            raise ValueError("resposta de estação INMET inválida")
        codigo = (bruto.get("codigo") or bruto.get("cod")
                  or bruto.get("id_estacao") or bruto.get("estacao_codigo"))
        nome = (bruto.get("estacao") or bruto.get("nome")
                or bruto.get("descricao"))
        if not codigo:
            raise ValueError("estação INMET sem código")
        return {
            "codigo": str(codigo),
            "nome": _limpar(nome) or None,
            "bruto": bruto,
        }

    @staticmethod
    def _num(valor) -> Optional[float]:
        try:
            if valor is None or str(valor).strip() in ("", "-", "NaN"):
                return None
            return float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalizar_linha_inmet(cls, row: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Mapeia os nomes de coluna dos dados diários do INMET."""
        def primeiro(*chaves):
            for k in chaves:
                if k in row and row[k] not in (None, "", "-"):
                    return row[k]
            return None

        temp = cls._num(primeiro(
            "TEMP_MEDIA", "temperatura", "TEMPERATURA_MEDIA",
            "TEMP_MEDIA_COMPENSADA", "TEMP_MEDIA_INSOLACAO"))
        umid = cls._num(primeiro(
            "UMIDADE_RELATIVA_MEDIA", "umidade", "UMIDADE_RELATIVA",
            "UMIDADE_RELATIVA_MEDIA_DIARIA"))
        press_hpa = cls._num(primeiro(
            "PRESSAO_ATMOSFERICA_NIVEL_ESTACAO_MEDIA",
            "PRESSAO_ATMOSFERICA_MEDIA", "pressao",
            "PRESSAO_ATMOSFERICA", "PRESSAO_ATMOSFERICA_NIVEL_MEDIO_MAR_MEDIA"))
        vento = cls._num(primeiro(
            "VENTO_VELOCIDADE_MEDIA", "vento", "VENTO_VELOCIDADE",
            "VENTO_VELOCIDADE_MEDIA_DIARIA"))
        pressao = (press_hpa / 1013.25) if press_hpa is not None else None
        return {
            "temperatura": round(temp, 2) if temp is not None else None,
            "pressao": round(pressao, 4) if pressao is not None else None,
            "umidade": round(umid, 2) if umid is not None else None,
            "vento": round(vento, 2) if vento is not None else None,
        }

    @classmethod
    def _agregar(cls, linhas: List[Dict[str, Any]]):
        """Média dos valores presentes em N linhas diárias."""
        chaves = ("temperatura", "pressao", "umidade", "vento")
        out = {}
        for ch in chaves:
            vals = [r[ch] for r in linhas if r.get(ch) is not None]
            out[ch] = round(float(np.mean(vals)), 4) if vals else None
        return out

    def _inmet_dados(self, estacao: Dict[str, Any],
                     data_inicio: date, data_fim: date) -> Dict[str, Any]:
        di = data_inicio.isoformat()
        df = data_fim.isoformat()
        url = "{}/estacao/diaria/{}/{}/{}".format(
            self.BASE_DADOS, di, df, estacao["codigo"])
        bruto = self.getter(url)
        if bruto is None:
            raise ValueError("INMET sem dados diários")
        if isinstance(bruto, dict):
            bruto = bruto.get("dados") or bruto.get("data") or \
                bruto.get("estacao") or bruto.get("lista") or []
        if not isinstance(bruto, list) or not bruto:
            raise ValueError("INMET sem observações no período")
        linhas = [self._normalizar_linha_inmet(r) for r in bruto
                  if isinstance(r, dict)]
        valores = self._agregar(linhas)
        return {
            "temperatura": valores["temperatura"],
            "pressao": valores["pressao"],
            "umidade": valores["umidade"],
            "vento": valores["vento"],
            "n_observacoes": len(linhas),
            "periodo": {"inicio": di, "fim": df},
        }

    # ---------- 2. Contingência Open-Meteo ---------------
    def _open_meteo(self, territorio: Dict[str, Any]) -> Dict[str, Any]:
        url = (
            "{base}?latitude={lat}&longitude={lon}"
            "&daily=temperature_2m_mean,relative_humidity_2m_mean,"
            "pressure_msl_mean&forecast_days=5&timezone=America/Sao_Paulo"
        ).format(base=self.BASE_CONTINGENCIA,
                 lat=territorio["lat"], lon=territorio["lon"])
        bruto = self.getter(url)
        if bruto is None:
            raise ValueError("Open-Meteo sem resposta")
        daily = (bruto.get("daily") or {}) if isinstance(bruto, dict) else {}
        temps = [t for t in daily.get("temperature_2m_mean", [])
                 if t is not None]
        hums = [h for h in daily.get("relative_humidity_2m_mean", [])
                if h is not None]
        press = [p for p in daily.get("pressure_msl_mean", [])
                 if p is not None]
        if not temps or not hums or not press:
            raise ValueError("Open-Meteo sem dados válidos")
        return {
            "temperatura": round(float(np.mean(temps[:3])), 2),
            "pressao": round(float(np.mean(press[:3])) / 1013.25, 4),
            "umidade": round(float(np.mean(hums[:3])), 2),
            "vento": None,
            "n_observacoes": min(3, len(temps)),
            "periodo": {"inicio": date.today().isoformat(),
                        "fim": (date.today() + timedelta(days=2)).isoformat()},
        }

    # ---------- 3. Neutro --------------------------------
    @staticmethod
    def _neutro(territorio: Dict[str, Any], motivo: str,
                diagnostico: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            "status": "neutro",
            "fonte": "padrao",
            "local": territorio.get("local"),
            "cidade": territorio.get("cidade"),
            "uf": territorio.get("uf"),
            "cidade_uf": territorio.get("cidade_uf"),
            "lat": territorio.get("lat"),
            "lon": territorio.get("lon"),
            "geocodigo": territorio.get("geocodigo"),
            "estacao": None,
            "temperatura": None,
            "pressao": None,
            "umidade": None,
            "vento": None,
            "n_observacoes": 0,
            "periodo": None,
            "detalhe": motivo,
            "diagnostico": diagnostico or {},
            "erro": motivo,
        }

    def telemetria(self, local: Any = None, cidade_uf: Any = None,
                   dias: int = 3, usar_contingencia: bool = True
                   ) -> Dict[str, Any]:
        """Telemetria completa por local do sorteio (nunca levanta exceção)."""
        territorio = self._territorio(local, cidade_uf)
        diagnostico: Dict[str, Any] = {"territorio": territorio}

        # 1. INMET oficial
        try:
            estacao = self._estacao_proxima(territorio)
            hoje = date.today()
            dados = self._inmet_dados(
                estacao, hoje, hoje + timedelta(days=max(1, int(dias)) - 1))
            diagnostico["inmet"] = {"status": "ok", "estacao": estacao}
            return {
                "status": "ok",
                "fonte": "inmet_oficial",
                "cidade": territorio.get("cidade"),
                "uf": territorio.get("uf"),
                "cidade_uf": territorio.get("cidade_uf"),
                "local": territorio.get("local"),
                "lat": territorio.get("lat"),
                "lon": territorio.get("lon"),
                "geocodigo": territorio.get("geocodigo"),
                "estacao": estacao,
                "temperatura": dados.get("temperatura"),
                "pressao": dados.get("pressao"),
                "umidade": dados.get("umidade"),
                "vento": dados.get("vento"),
                "n_observacoes": dados.get("n_observacoes"),
                "periodo": dados.get("periodo"),
                "detalhe": (
                    "INMET oficial — estação mais próxima de {}/{} "
                    "({})".format(territorio.get("cidade"),
                                  territorio.get("uf"),
                                  estacao.get("nome") or estacao.get("codigo"))
                ),
                "diagnostico": diagnostico,
                "erro": None,
            }
        except Exception as exc:
            diagnostico["inmet"] = {"status": "erro",
                                    "erro": "{}: {}".format(type(exc).__name__, exc)}

        # 2. Contingência Open-Meteo (mesmas coordenadas)
        if usar_contingencia:
            try:
                dados = self._open_meteo(territorio)
                diagnostico["contingencia"] = {"status": "ok"}
                return {
                    "status": "contingencia",
                    "fonte": "open_meteo",
                    "cidade": territorio.get("cidade"),
                    "uf": territorio.get("uf"),
                    "cidade_uf": territorio.get("cidade_uf"),
                    "local": territorio.get("local"),
                    "lat": territorio.get("lat"),
                    "lon": territorio.get("lon"),
                    "geocodigo": territorio.get("geocodigo"),
                    "estacao": None,
                    "temperatura": dados.get("temperatura"),
                    "pressao": dados.get("pressao"),
                    "umidade": dados.get("umidade"),
                    "vento": None,
                    "n_observacoes": dados.get("n_observacoes"),
                    "periodo": dados.get("periodo"),
                    "detalhe": (
                        "INMET indisponível — contingência Open-Meteo nas "
                        "coordenadas de {}/{}".format(territorio.get("cidade"),
                                                      territorio.get("uf"))
                    ),
                    "diagnostico": diagnostico,
                    "erro": None,
                }
            except Exception as exc:
                diagnostico["contingencia"] = {
                    "status": "erro",
                    "erro": "{}: {}".format(type(exc).__name__, exc)}

        return self._neutro(
            territorio,
            "rede indisponível — telemetria neutra, sem dados fabricados",
            diagnostico)


# ============================================================
# PERSISTÊNCIA — telemetria por concurso/local
# ============================================================
class TelemetriaInmet:
    """Guarda a telemetria consultada para cada sorteio e a reusa.

    A tabela é criada com `IF NOT EXISTS`, então funciona tanto em
    bancos novos quanto em bases já existentes (sem migração destrutiva).
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH
        self._criar_tabela()

    def _criar_tabela(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inmet_telemetria (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    concurso    INTEGER,
                    local       TEXT,
                    cidade_uf   TEXT,
                    cidade      TEXT,
                    uf          TEXT,
                    geocodigo   TEXT,
                    estacao     TEXT,
                    lat         REAL,
                    lon         REAL,
                    temperatura REAL,
                    pressao     REAL,
                    umidade     REAL,
                    vento       REAL,
                    fonte       TEXT,
                    status      TEXT,
                    bruto       TEXT,
                    criado_em   TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _bruto_json(dados: Dict[str, Any]) -> Optional[str]:
        try:
            return json.dumps(dados, ensure_ascii=False, default=str)
        except Exception:
            return None

    def registrar(self, dados: Dict[str, Any],
                  concurso: Optional[int] = None) -> Optional[int]:
        """Persiste uma consulta de telemetria; devolve o id (ou None)."""
        if not isinstance(dados, dict):
            return None
        estacao = dados.get("estacao")
        if isinstance(estacao, dict):
            estacao = estacao.get("codigo") or estacao.get("nome")
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute("""
                INSERT INTO inmet_telemetria (
                    concurso, local, cidade_uf, cidade, uf, geocodigo,
                    estacao, lat, lon, temperatura, pressao, umidade,
                    vento, fonte, status, bruto, criado_em
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                int(concurso) if concurso is not None else None,
                dados.get("local"), dados.get("cidade_uf"),
                dados.get("cidade"), dados.get("uf"), dados.get("geocodigo"),
                estacao, dados.get("lat"), dados.get("lon"),
                dados.get("temperatura"), dados.get("pressao"),
                dados.get("umidade"), dados.get("vento"),
                dados.get("fonte"), dados.get("status"),
                self._bruto_json(dados),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    @staticmethod
    def _linha_para_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if d.get("bruto"):
            try:
                d["bruto"] = json.loads(d["bruto"])
            except (TypeError, ValueError):
                pass
        return d

    def por_concurso(self, concurso: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM inmet_telemetria WHERE concurso = ? "
                "ORDER BY id DESC LIMIT 1", (int(concurso),)).fetchone()
            return self._linha_para_dict(row) if row else None
        finally:
            conn.close()

    def ultima(self) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM inmet_telemetria ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return self._linha_para_dict(row) if row else None
        finally:
            conn.close()

    def historico(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM inmet_telemetria ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),)).fetchall()
            return [self._linha_para_dict(r) for r in rows]
        finally:
            conn.close()

    def resumo(self, limit: int = 30) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM inmet_telemetria").fetchone()[0]
            if not n:
                return {"status": "neutro", "n_registros": 0,
                        "ultima": None, "fontes": {},
                        "medias": None}
            ultima = conn.execute(
                "SELECT * FROM inmet_telemetria ORDER BY id DESC LIMIT 1"
            ).fetchone()
            fontes = {r["fonte"]: r["n"] for r in conn.execute(
                "SELECT fonte, COUNT(*) AS n FROM inmet_telemetria "
                "GROUP BY fonte").fetchall()}
            medias = conn.execute("""
                SELECT AVG(temperatura) AS temperatura,
                       AVG(pressao) AS pressao,
                       AVG(umidade) AS umidade,
                       AVG(vento) AS vento
                FROM inmet_telemetria
                WHERE temperatura IS NOT NULL OR pressao IS NOT NULL
                   OR umidade IS NOT NULL
                LIMIT 1
            """).fetchone()
            return {
                "status": "ok",
                "n_registros": int(n),
                "ultima": self._linha_para_dict(ultima),
                "fontes": fontes,
                "medias": {
                    k: (round(v, 4) if v is not None else None)
                    for k, v in dict(medias).items()
                },
            }
        finally:
            conn.close()

    # ----------------------------------------------------------
    # VETOR DE EVIDÊNCIA (para o consenso da Magna)
    # ----------------------------------------------------------
    def condicoes_para_clima(self) -> Optional[Dict[str, Any]]:
        """Condições (temp/pressão/umidade) para o MotorClima, se houver."""
        ult = self.ultima()
        if not ult or ult.get("temperatura") is None:
            return None
        return {
            "temperatura": ult.get("temperatura"),
            "pressao": ult.get("pressao"),
            "umidade": ult.get("umidade"),
            "fonte": "inmet-{}".format(ult.get("fonte") or "desconhecida"),
            "detalhe": (
                "telemetria INMET por local do sorteio ({} — {})".format(
                    ult.get("cidade_uf"), ult.get("fonte"))
            ),
        }

    def vetor_inmet(self, teto: float = TETO_INMET) -> np.ndarray:
        """Vetor 25D leve a partir da última telemetria (uniforme se neutro).

        Apenas um tilt de paridade vinculado à pressão (a mesma hipótese
        física da v11.2: ar menos denso ⇔ arrasto menor) e clipes em
        ±10% em torno do uniforme. Não prevê dezena: inclina, nunca dita.
        """
        v = np.ones(TOTAL_DEZENAS, dtype=float)
        ult = self.ultima()
        if not ult or ult.get("pressao") is None:
            return v
        pressao = float(ult["pressao"])
        # normalizado em torno da pressão média de SP (0,915 atm)
        if pressao < 0.94:      # ar menos denso → ímpares levemente favorecidos
            fator = 1.0 + TILT_PARIDADE
        elif pressao > 1.07:    # ar mais denso → pares levemente favorecidos
            fator = 1.0 - TILT_PARIDADE
        else:
            fator = 1.0
        v[0::2] *= fator        # 01, 03, 05, ... (índices pares = dezenas ímpares)
        v[1::2] *= 2.0 - fator  # 02, 04, 06, ... (dezenas pares)
        v = np.clip(v, 1.0 - teto, 1.0 + teto)
        return v / v.sum() * TOTAL_DEZENAS
