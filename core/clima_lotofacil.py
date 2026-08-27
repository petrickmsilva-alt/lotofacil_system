"""
============================================================
CLIMA DO SORTEIO — Motor de Análise Física-Estatística
============================================================
Fonte de evidência da Inteligência Magna (v11.2).

Consome o histórico (concurso, data, temperatura, pressão
atmosférica, umidade, dezenas) e executa três testes
matemáticos de física do ambiente:

  T1 — Média de Ímpares × Pressão atmosférica
       (ar menos denso ⇔ arrasto menor ⇔ hipótese: ímpares sobem)
  T2 — Soma das Dezenas × Faixas de Umidade
       (baixa <45% | média 45-50% | alta >50%)
  T3 — Frequência Individual das 25 Dezenas × Temperatura
       (frio/quente dividido pela mediana)

PRINCÍPIOS (honestidade antes de promessa):
  1. Cada teste devolve z-score, erro padrão e veredito
     (SINAL / FRONTEIRA / RUÍDO). Nada vira garantia.
  2. SHRINKAGE: o vetor de clima é misturado 50/50 com o
     uniforme e limitado a ±10% por dezena. O clima inclina,
     nunca dita.
  3. APRENDIZADO CONTÍNUO: aprender() incorpora cada novo
     sorteio com clima e recalibra os três testes na hora.
  4. AUTO-AUDITORIA: auto_ponderacao() roda backtest
     walk-forward do próprio vetor de clima e devolve um
     fator de confiança (0.5-1.0) que a Magna multiplica no
     peso da fonte — a fonte só é ouvida na medida em que
     o passado justifica.

AVISO: sorteio de loteria é um processo aleatório controlado.
Estes testes medem correlação, não causa. A Magna usa o clima
como física leve (dilatação, arrasto, estática) com peso
restrito e reavaliado a cada ciclo.
============================================================
"""
import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from config import TOTAL_DEZENAS

try:
    from scipy import stats as _sp
except Exception:  # pragma: no cover
    _sp = None

# Arquivo padrão do histórico climático
CSV_PADRAO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "historico_clima_lotofacil.csv"
)

# Limiar de significância usado nos vereditos
Z_SINAL = 1.96    # 95% — sinal
Z_FRONTEIRA = 1.0  # ~68% — fronteira (vale registrar, não confiar)

# Coeficientes máximos de inclinação (shrinkage dura)
TILT_T1_MAX = 0.05   # ±5% máx. por paridade (pressão)
TILT_T2_MAX = 0.03   # ±3% máx. por rampa de soma (umidade)
TILT_T3_MAX = 0.04   # ±4% máx. por dezena (temperatura)
FAIXA_PERMITIDA = 0.10  # vetor final: ±10% em torno do uniforme


def _z_dois_media(a: np.ndarray, b: np.ndarray) -> float:
    """z de Welch entre duas amostras (sem scipy)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    va, vb = a.var(ddof=1), b.var(ddof=1)
    denom = np.sqrt(va / len(a) + vb / len(b))
    if denom < 1e-12:
        return 0.0
    return float((a.mean() - b.mean()) / denom)


def _z_proporcao(k1: int, n1: int, k2: int, n2: int) -> float:
    """z de duas proporções (pooled)."""
    if n1 == 0 or n2 == 0:
        return 0.0
    p = (k1 + k2) / (n1 + n2)
    denom = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if denom < 1e-12:
        return 0.0
    return float((k1 / n1 - k2 / n2) / denom)


def _veredito(z: float) -> str:
    az = abs(z)
    if az >= Z_SINAL:
        return "SINAL"
    if az >= Z_FRONTEIRA:
        return "FRONTEIRA"
    return "RUÍDO"


class MotorClima:
    """Análise físico-estatística do clima do sorteio.

    Fonte neutra quando não há dados: vetor uniforme, testes
    vazios, previsão por média histórica — a Magna a ouve
    apenas pelo peso que o auto-aprendizado atribuir.
    """

    def __init__(self, csv_path: str = None, usar_web: bool = True):
        self.csv_path = csv_path or CSV_PADRAO
        self.usar_web = usar_web
        self._condicoes_override: Optional[Dict[str, Any]] = None
        self._registros: List[Dict[str, Any]] = []
        self._carregar()

    def definir_condicoes(self, temperatura: float = None,
                          pressao: float = None,
                          umidade: float = None) -> Dict[str, Any]:
        """Força as condições do próximo sorteio (ex.: boletim do dia).

        Substitui a previsão automática até que novo valor venha.
        """
        if all(v is None for v in (temperatura, pressao, umidade)):
            self._condicoes_override = None
            return {"status": "ok", "condicoes": None}
        base = (self._condicoes_override
                or self.clima_previsto(usar_web=False))
        self._condicoes_override = {
            "temperatura": (float(temperatura)
                            if temperatura is not None
                            else base.get("temperatura", 21.5)),
            "pressao": (float(pressao) if pressao is not None
                        else base.get("pressao", 0.915)),
            "umidade": (float(umidade) if umidade is not None
                        else base.get("umidade", 50.0)),
            "fonte": "definida_manualmente",
            "detalhe": "condições informadas pelo operador",
        }
        return {"status": "ok", "condicoes": dict(self._condicoes_override)}

    # ------------------------------------------------------------
    # Carga / persistência
    # ------------------------------------------------------------
    def _carregar(self) -> None:
        self._registros = []
        if not os.path.exists(self.csv_path):
            return
        try:
            with open(self.csv_path, newline="", encoding="utf-8") as f:
                linhas = f.readlines()
            header = linhas[0] if linhas else ""
            for row_raw in linhas[1:]:
                if not row_raw.strip():
                    continue
                row = next(csv.DictReader([header, row_raw]))
                r = self._parse_rowa(row)
                if r:
                    r["_raw"] = row_raw.rstrip("\r\n")
                    self._registros.append(r)
            self._registros.sort(key=lambda r: r["concurso"])
        except Exception:
            self._registros = []

    @staticmethod
    def _parse_rowa(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            concurso = int(str(row["Concurso"]).strip())
            temp = float(str(row["Temperatura_C"]).strip().replace(",", "."))
            pressao = float(str(row["Pressao_atm"]).strip().replace(",", "."))
            umidade = float(str(row["Umidade_pct"]).strip().replace(",", "."))
            dezenas = sorted(
                int(x) for x in str(row.get("Dezenas", "")).split() if x
            )
        except (ValueError, KeyError, AttributeError):
            return None
        if not 1 <= concurso <= 9999:
            return None
        if not (-20.0 <= temp <= 60.0 and 0.7 <= pressao <= 1.3
                and 0.0 <= umidade <= 100.0):
            return None
        if len(dezenas) not in (0, 15) or (
                dezenas and (len(set(dezenas)) != 15
                             or any(not 1 <= d <= 25 for d in dezenas))):
            return None
        return {
            "concurso": concurso,
            "data": str(row.get("Data", "")).strip(),
            "temperatura": temp,
            "pressao": pressao,
            "umidade": umidade,
            "dezenas": dezenas,
        }

    def _gravar(self) -> None:
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        linhas = [
            "Concurso,Data,Temperatura_C,Pressao_atm,Umidade_pct,Dezenas"
        ]
        for r in self._registros:
            # linhas originais preservam o formato exato (idempotência);
            # linhas novas são formatadas aqui
            if r.get("_raw"):
                linhas.append(r["_raw"])
            else:
                dz = " ".join(f"{d:02d}" for d in r["dezenas"])
                linhas.append(",".join([
                    str(r["concurso"]), r["data"],
                    f"{r['temperatura']:g}", f"{r['pressao']:g}",
                    f"{r['umidade']:g}", dz,
                ]))
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")

    def aprender(self, concurso: int, temp: float, pressao: float,
                 umidade: float, data: str = "",
                 dezenas: Optional[List[int]] = None) -> Dict[str, Any]:
        """Incorpora um sorteio (com clima) ao aprendizado.

        Upsert por concurso: se o concurso já existe, atualiza;
        se não, acrescenta. Recalibrar() é implícito — os testes
        são sempre recomputados a partir do dataset atual.
        """
        concurso = int(concurso)
        nova = {
            "concurso": concurso,
            "data": str(data or "").strip(),
            "temperatura": float(temp),
            "pressao": float(pressao),
            "umidade": float(umidade),
            "dezenas": sorted(int(d) for d in (dezenas or [])),
        }
        if nova["dezenas"] and (
                len(set(nova["dezenas"])) != 15
                or any(not 1 <= d <= 25 for d in nova["dezenas"])):
            nova["dezenas"] = []
        atualizado = False
        for i, r in enumerate(self._registros):
            if r["concurso"] == concurso:
                if not nova["dezenas"]:
                    nova["dezenas"] = self._registros[i]["dezenas"]
                sem_mudancas = (
                    r["temperatura"] == nova["temperatura"]
                    and r["pressao"] == nova["pressao"]
                    and r["umidade"] == nova["umidade"]
                    and r["data"] == nova["data"]
                    and r["dezenas"] == nova["dezenas"]
                )
                if sem_mudancas and r.get("_raw"):
                    nova["_raw"] = r["_raw"]
                self._registros[i] = nova
                atualizado = True
                break
        if not atualizado:
            self._registros.append(nova)
            self._registros.sort(key=lambda r: r["concurso"])
        self._gravar()
        return {
            "status": "ok",
            "concurso": concurso,
            "novo": not atualizado,
            "n_registros": len(self._registros),
        }

    # ------------------------------------------------------------
    # Acessores
    # ------------------------------------------------------------
    @property
    def registros(self) -> List[Dict[str, Any]]:
        return list(self._registros)

    @property
    def n_registros(self) -> int:
        return len(self._registros)

    def _com_dezenas(self) -> List[Dict[str, Any]]:
        return [r for r in self._registros if len(r["dezenas"]) == 15]

    def _limiar_pressao(self) -> float:
        p = np.array([r["pressao"] for r in self._registros])
        return float(np.median(p)) if len(p) else 0.916

    def _limiar_temperatura(self) -> float:
        t = np.array([r["temperatura"] for r in self._registros])
        return float(np.median(t)) if len(t) else 21.5

    def _media_umidade(self) -> float:
        u = np.array([r["umidade"] for r in self._registros])
        return float(np.mean(u)) if len(u) else 50.0

    # ------------------------------------------------------------
    # T1 — Ímpares × Pressão
    # ------------------------------------------------------------
    def teste_impares_pressao(self, limiar: float = None) -> Dict[str, Any]:
        rows = self._com_dezenas()
        lim = float(limiar if limiar is not None else self._limiar_pressao())
        if len(rows) < 10:
            return {"aplicavel": False, "limiar": lim,
                    "motivo": "amostra insuficiente (<10)"}
        baixo = [r for r in rows if r["pressao"] < lim]
        alto = [r for r in rows if r["pressao"] >= lim]

        def impar_stats(g):
            if not g:
                return {"n": 0, "media": None, "ep": None}
            vals = np.array([
                sum(1 for d in r["dezenas"] if d % 2 == 1) for r in g
            ], dtype=float)
            return {
                "n": int(len(vals)),
                "media": round(float(vals.mean()), 4),
                "ep": round(float(vals.std(ddof=1) / np.sqrt(len(vals))), 4),
            }

        sb, sa = impar_stats(baixo), impar_stats(alto)
        z = _z_dois_media(
            [sum(1 for d in r["dezenas"] if d % 2 == 1) for r in baixo],
            [sum(1 for d in r["dezenas"] if d % 2 == 1) for r in alto],
        )
        return {
            "aplicavel": True,
            "limiar": round(lim, 4),
            "pressao_baixa": sb,
            "pressao_alta": sa,
            "diferenca": round(sb["media"] - sa["media"], 4)
            if sb["media"] is not None and sa["media"] is not None else None,
            "z": round(z, 4),
            "veredito": _veredito(z),
            "leitura": (
                "Ímpares tendem a ser MAIORES sob pressão baixa"
                if (sb["media"] or 0) > (sa["media"] or 0)
                else "Ímpares tendem a ser MENORES sob pressão baixa"
            ),
            "teorico_lotofacil": "média teórica 8 ímpares (15/25)",
        }

    # ------------------------------------------------------------
    # T2 — Soma × Umidade
    # ------------------------------------------------------------
    def teste_soma_umidade(self) -> Dict[str, Any]:
        rows = self._com_dezenas()
        if len(rows) < 10:
            return {"aplicavel": False,
                    "motivo": "amostra insuficiente (<10)"}
        faixas = {
            "baixa_lt_45": [r for r in rows if r["umidade"] < 45.0],
            "media_45_50": [
                r for r in rows if 45.0 <= r["umidade"] <= 50.0
            ],
            "alta_gt_50": [r for r in rows if r["umidade"] > 50.0],
        }
        soma = {
            nome: (
                {"n": 0, "media": None, "ep": None} if not g else {
                    "n": len(g),
                    "media": round(float(np.mean(
                        [sum(r["dezenas"]) for r in g])), 4),
                    "ep": round(float(np.std(
                        [sum(r["dezenas"]) for r in g], ddof=1)
                        / np.sqrt(len(g))), 4),
                }
            )
            for nome, g in faixas.items()
        }
        todas = np.array([sum(r["dezenas"]) for r in rows], dtype=float)
        global_media = round(float(todas.mean()), 4)

        # z da faixa mais discrepante vs o restante
        melhor_nome, melhor_z, melhor_dif = None, 0.0, 0.0
        for nome, g in faixas.items():
            if len(g) < 3:
                continue
            resto = [sum(r["dezenas"]) for r in rows if r not in g]
            z = _z_dois_media(
                [sum(r["dezenas"]) for r in g], resto)
            if abs(z) > abs(melhor_z):
                melhor_z = z
                melhor_nome = nome
                melhor_dif = (
                    soma[nome]["media"] - global_media
                    if soma[nome]["media"] is not None else 0.0)
        return {
            "aplicavel": True,
            "faixas": soma,
            "soma_media_global": global_media,
            "soma_esperada_lotofacil": 195.0,
            "faixa_destaque": melhor_nome,
            "z_faixa_destaque": round(melhor_z, 4),
            "diferenca_destaque_vs_global": round(melhor_dif, 4),
            "veredito": _veredito(melhor_z),
            "leitura": (
                "Umidade baixa ⇔ somas levemente maiores (dezenas altas); "
                "umidade alta ⇔ somas recuam à média"
                if (melhor_nome == "baixa_lt_45" and melhor_dif > 0)
                else "Nenhuma faixa domina com força estatística"
            ),
        }

    # ------------------------------------------------------------
    # T3 — Frequência individual × Temperatura
    # ------------------------------------------------------------
    def teste_frequencia_temperatura(self) -> Dict[str, Any]:
        rows = self._com_dezenas()
        lim = self._limiar_temperatura()
        if len(rows) < 20:
            return {"aplicavel": False, "limiar": round(lim, 2),
                    "motivo": "amostra insuficiente (<20)"}
        frio = [r for r in rows if r["temperatura"] < lim]
        quente = [r for r in rows if r["temperatura"] >= lim]
        n_f, n_q = len(frio), len(quente)

        det = []
        for d in range(1, TOTAL_DEZENAS + 1):
            k_f = sum(1 for r in frio if d in r["dezenas"])
            k_q = sum(1 for r in quente if d in r["dezenas"])
            z = _z_proporcao(k_f, n_f, k_q, n_q)
            det.append({
                "dezena": d,
                "frio": k_f,
                "quente": k_q,
                "diferenca": k_f - k_q,
                "z": round(z, 4),
                "veredito": _veredito(z),
            })
        top_diff = sorted(det, key=lambda x: abs(x["diferenca"]),
                          reverse=True)[:5]
        top_z = sorted(
            [x for x in det if abs(x["z"]) >= Z_FRONTEIRA],
            key=lambda x: abs(x["z"]), reverse=True)[:5]
        return {
            "aplicavel": True,
            "limiar_temperatura": round(lim, 2),
            "n_frio": n_f,
            "n_quente": n_q,
            "top_diferencia": top_diff,
            "top_z": top_z,
            "leitura": (
                "Discrepâncias máximas: " +
                ", ".join(f"{x['dezena']:02d} "
                          f"(frio {x['frio']} × quente {x['quente']})"
                          for x in top_diff[:3])
            ),
        }

    # ------------------------------------------------------------
    # Relatório completo (os 3 testes)
    # ------------------------------------------------------------
    def testes_fisicos(self) -> Dict[str, Any]:
        t1 = self.teste_impares_pressao()
        t2 = self.teste_soma_umidade()
        t3 = self.teste_frequencia_temperatura()
        aplicaveis = [t for t in (t1, t2, t3) if t.get("aplicavel")]
        n_sinais = sum(1 for t in aplicaveis if t.get("veredito") == "SINAL")
        n_fronteiras = sum(
            1 for t in aplicaveis if t.get("veredito") == "FRONTEIRA")
        return {
            "n_registros": self.n_registros,
            "n_com_dezenas": len(self._com_dezenas()),
            "T1_impares_pressao": t1,
            "T2_soma_umidade": t2,
            "T3_frequencia_temperatura": t3,
            "honestidade": {
                "sinais_95": n_sinais,
                "fronteiras": n_fronteiras,
                "resumo": (
                    f"{n_sinais}/3 testes com sinal em 95%; "
                    f"{n_fronteiras} em fronteira. Correlação não é causa: "
                    "o clima entra como física leve com shrinkage e "
                    "auto-auditoria."
                ),
            },
        }

    # ------------------------------------------------------------
    # Previsão do clima do próximo sorteio
    # ------------------------------------------------------------
    def clima_previsto(self, usar_web: bool = None) -> Dict[str, Any]:
        """Prevê o clima do próximo sorteio.

        1º: Open-Meteo (grátis, sem chave) — média dos próximos
        dias para São Paulo (Espaço da Sorte, Av. Paulista).
        2º: fallback — mediana dos 14 registros mais recentes
        suavizada com a média histórica.

        usar_web=None usa o padrão da instância; True/False força.
        """
        if self._condicoes_override:
            return dict(self._condicoes_override)
        web = self.usar_web if usar_web is None else bool(usar_web)
        if web:
            try:
                return self._clima_open_meteo()
            except Exception:
                pass
        return self._clima_media_recente()

    def _clima_open_meteo(self) -> Dict[str, Any]:
        import urllib.request
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=-23.5475&longitude=-46.6361"
            "&daily=temperature_2m_mean,relative_humidity_2m_mean,"
            "pressure_msl_mean"
            "&forecast_days=5&timezone=America/Sao_Paulo"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "MagnaClima/1.1"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            payload = resp.read().decode("utf-8")
        import json as _json
        daily = _json.loads(payload)["daily"]
        temps = [t for t in daily["temperature_2m_mean"] if t is not None]
        hums = [h for h in daily["relative_humidity_2m_mean"]
                if h is not None]
        press = [p for p in daily["pressure_msl_mean"] if p is not None]
        if not temps or not hums or not press:
            raise ValueError("open-meteo sem dados")
        # próximo sorteio: média dos próximos 3 dias
        temp = float(np.mean(temps[:3]))
        um = float(np.mean(hums[:3]))
        press_atm = float(np.mean(press[:3])) / 1013.25
        return {
            "temperatura": round(temp, 2),
            "pressao": round(press_atm, 4),
            "umidade": round(um, 2),
            "fonte": "open-meteo-sao_paulo",
            "detalhe": "média dos próximos 3 dias (Espaço da Sorte, SP)",
        }

    def _clima_media_recente(self) -> Dict[str, Any]:
        if not self._registros:
            return {
                "temperatura": 21.5, "pressao": 0.915, "umidade": 50.0,
                "fonte": "padrao_sao_paulo",
                "detalhe": "sem histórico — padrão climatizado de SP",
            }
        ult = self._registros[-14:]
        med = {
            "temperatura": float(np.median([r["temperatura"] for r in ult])),
            "pressao": float(np.median([r["pressao"] for r in ult])),
            "umidade": float(np.median([r["umidade"] for r in ult])),
        }
        hist = {
            "temperatura": float(np.mean(
                [r["temperatura"] for r in self._registros])),
            "pressao": float(np.mean([r["pressao"] for r in self._registros])),
            "umidade": float(np.mean([r["umidade"] for r in self._registros])),
        }
        return {
            "temperatura": round(0.7 * med["temperatura"]
                                 + 0.3 * hist["temperatura"], 2),
            "pressao": round(0.7 * med["pressao"]
                             + 0.3 * hist["pressao"], 4),
            "umidade": round(0.7 * med["umidade"]
                             + 0.3 * hist["umidade"], 2),
            "fonte": "media_recente_14",
            "detalhe": "mediana dos 14 registros recentes + média histórica",
        }

    # ------------------------------------------------------------
    # Vetor de clima (1..25) — a fonte assimilada pela Magna
    # ------------------------------------------------------------
    def vetor_clima(self, temperatura: float = None,
                    pressao: float = None,
                    umidade: float = None,
                    usar_web: bool = None) -> np.ndarray:
        """Vetor 1..25 ajustado pelo clima previsto/medido.

        Regras (todas com shrinkage e teto ±10%):
          T1: pressão abaixo do limiar inclina pares/ímpares na
              direção observada, força proporcional a |z|/1.96.
          T2: a faixa de umidade do dia inclina o volante para
              somas maiores/menores (rampa linear 1→25).
          T3: regime frio/quente fortalece as 3 dezenas com
              maior z observada naquele regime (z>=1.2).
        """
        uniforme = np.ones(TOTAL_DEZENAS)
        if self.n_registros < 10:
            return uniforme
        if temperatura is None or pressao is None or umidade is None:
            prev = self.clima_previsto(usar_web=usar_web)
            temperatura = temperatura if temperatura is not None \
                else prev["temperatura"]
            pressao = pressao if pressao is not None else prev["pressao"]
            umidade = umidade if umidade is not None else prev["umidade"]
        raw = np.ones(TOTAL_DEZENAS)

        # T1 — pressão × paridade
        t1 = self.teste_impares_pressao()
        if t1.get("aplicavel") and t1.get("diferenca") is not None:
            conf = min(1.0, abs(t1["z"]) / Z_SINAL)
            tilt = t1["diferenca"] / 2.0 * conf * TILT_T1_MAX
            # diferença +0.28 significa ~0.28 ímpares a mais sob pressão
            # baixa; convertemos em fração de inclinação (0..±1)
            inclinacao = float(np.clip(tilt, -1.0, 1.0))
            if pressao < self._limiar_pressao():
                raw[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 1] *= \
                    (1.0 + inclinacao)
                raw[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 0] *= \
                    (1.0 - inclinacao)
            else:
                raw[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 1] *= \
                    (1.0 - inclinacao)
                raw[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 0] *= \
                    (1.0 + inclinacao)

        # T2 — umidade × soma (rampa do volante)
        t2 = self.teste_soma_umidade()
        if t2.get("aplicavel") and t2.get("faixa_destaque"):
            faixas = t2["faixas"]
            if umidade < 45.0:
                nome = "baixa_lt_45"
            elif umidade <= 50.0:
                nome = "media_45_50"
            else:
                nome = "alta_gt_50"
            f = faixas.get(nome)
            if f and f.get("media") is not None and f["n"] >= 5:
                dif = f["media"] - t2["soma_media_global"]
                # 15 dezenas × média ~13 → soma 195; desvio de ~5 pontos
                # no total ⇔ deslocar o centro do volante ~1/3 de casa
                conf = min(1.0, abs(dif) / 10.0)
                tilt = np.clip(dif / 15.0, -1.0, 1.0) * conf * TILT_T2_MAX
                rampa = (np.arange(1, TOTAL_DEZENAS + 1)
                         - (TOTAL_DEZENAS + 1) / 2.0) / (TOTAL_DEZENAS / 2.0)
                raw *= (1.0 + tilt * rampa)

        # T3 — temperatura × dezenas individuais
        t3 = self.teste_frequencia_temperatura()
        if t3.get("aplicavel") and t3.get("top_z"):
            regime = "frio" if temperatura < t3["limiar_temperatura"] \
                else "quente"
            outros = "quente" if regime == "frio" else "frio"
            fortes = [
                x for x in t3["top_z"]
                if (regime == "frio" and x["frio"] >= x["quente"]
                    and x["z"] >= Z_FRONTEIRA * 1.2)
                or (regime == "quente" and x["quente"] >= x["frio"]
                    and x["z"] <= -Z_FRONTEIRA * 1.2)
            ][:3]
            for x in fortes:
                conf = min(1.0, abs(x["z"]) / (Z_SINAL * 1.5))
                raw[x["dezena"] - 1] *= (1.0 + conf * TILT_T3_MAX)

        # Shrinkage 50/50 + teto ±10% em torno do uniforme
        raw = 0.5 * uniforme + 0.5 * raw
        raw = np.clip(raw, 1.0 - FAIXA_PERMITIDA, 1.0 + FAIXA_PERMITIDA)
        return raw / raw.mean()

    def top5_clima(self, temperatura: float = None,
                   pressao: float = None,
                   umidade: float = None,
                   usar_web: bool = None) -> List[int]:
        v = self.vetor_clima(temperatura, pressao, umidade,
                             usar_web=usar_web)
        return [int(x) for x in np.argsort(v)[::-1][:5] + 1]

    # ------------------------------------------------------------
    # Auto-auditoria — quanto o clima realmente acerta?
    # ------------------------------------------------------------
    def auto_ponderacao(self, janela: int = 40) -> Dict[str, Any]:
        """Walk-forward: o vetor de clima, avaliado só com o passado,
        acertaria mais que o aleatório (9.0 em 15)?

        Devolve fator de confiança 0.5-1.0 para o peso da fonte.
        """
        rows = self._com_dezenas()
        if len(rows) < 20:
            return {"aplicavel": False,
                    "motivo": "amostra insuficiente para walk-forward"}
        inicio = max(10, len(rows) - janela)
        acertos = []
        for i in range(inicio, len(rows)):
            sub = rows[:i]
            if len(sub) < 15:
                continue
            r = rows[i]
            med_t = float(np.median([x["temperatura"] for x in sub]))
            med_p = float(np.median([x["pressao"] for x in sub]))
            v = np.ones(TOTAL_DEZENAS)
            # T1 simplificado sobre o subconjunto
            imp_b = [sum(1 for d in x["dezenas"] if d % 2 == 1)
                     for x in sub if x["pressao"] < med_p]
            imp_a = [sum(1 for d in x["dezenas"] if d % 2 == 1)
                     for x in sub if x["pressao"] >= med_p]
            z1 = _z_dois_media(imp_b, imp_a) if imp_b and imp_a else 0.0
            inclinacao = np.clip(
                (np.mean(imp_b or [8]) - np.mean(imp_a or [8])) / 2.0,
                -1.0, 1.0) * min(1.0, abs(z1) / Z_SINAL) * TILT_T1_MAX
            if r["pressao"] < med_p:
                v[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 1] *= \
                    (1.0 + inclinacao)
                v[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 0] *= \
                    (1.0 - inclinacao)
            else:
                v[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 1] *= \
                    (1.0 - inclinacao)
                v[np.arange(1, TOTAL_DEZENAS + 1) % 2 == 0] *= \
                    (1.0 + inclinacao)
            # T3 simplificado
            frio = [x for x in sub if x["temperatura"] < med_t]
            quente = [x for x in sub if x["temperatura"] >= med_t]
            if frio and quente:
                regime_frio = r["temperatura"] < med_t
                refs = frio if regime_frio else quente
                out = quente if regime_frio else frio
                cands = []
                for d in range(1, TOTAL_DEZENAS + 1):
                    kf = sum(1 for x in refs if d in x["dezenas"])
                    ko = sum(1 for x in out if d in x["dezenas"])
                    z = _z_proporcao(kf, len(refs), ko, len(out))
                    if (regime_frio and z >= Z_FRONTEIRA * 1.2) or (
                            not regime_frio and z <= -Z_FRONTEIRA * 1.2):
                        cands.append((abs(z), d))
                for _, d in sorted(cands, reverse=True)[:3]:
                    v[d - 1] *= (1.0 + TILT_T3_MAX)
            v = 0.5 * np.ones(TOTAL_DEZENAS) + 0.5 * v
            top15 = set(int(x) for x in np.argsort(v)[::-1][:15] + 1)
            acertos.append(len(top15 & set(r["dezenas"])))
        if not acertos:
            return {"aplicavel": False, "motivo": "sem avaliações válidas"}
        media = float(np.mean(acertos))
        vantagem = media - 9.0
        fator = float(np.clip(0.5 + 0.5 * max(0.0, vantagem) / 1.0, 0.5, 1.0))
        return {
            "aplicavel": True,
            "n_avaliados": len(acertos),
            "media_acertos_clima": round(media, 4),
            "baseline_aleatorio": 9.0,
            "vantagem": round(vantagem, 4),
            "melhor": max(acertos),
            "pior": min(acertos),
            "fator_confianca": round(fator, 4),
            "leitura": (
                "Clima acima do aleatório — fonte mantida em confiança "
                "plena." if vantagem > 0.15 else
                "Clima no nível do aleatório — fonte operando com "
                "confiança reduzida (0.5-1.0×). É esperado: o objetivo "
                "é não piorar, e a auto-auditoria protege o consenso."
                if vantagem > -0.15 else
                "Clima abaixo do aleatório nesta janela — a Magna corta "
                "o peso da fonte pela metade até novos dados reabilitá-la."
            ),
        }

    # ------------------------------------------------------------
    # Relatório para a API / Magna
    # ------------------------------------------------------------
    def relatorio(self) -> Dict[str, Any]:
        prev = self.clima_previsto()
        return {
            "status": "ok",
            "motor": "MotorClima v11.2",
            "n_registros": self.n_registros,
            "concurso_min": self._registros[0]["concurso"]
            if self._registros else None,
            "concurso_max": self._registros[-1]["concurso"]
            if self._registros else None,
            "medias": (
                {
                    "temperatura": round(float(np.mean(
                        [r["temperatura"] for r in self._registros])), 2),
                    "pressao": round(float(np.mean(
                        [r["pressao"] for r in self._registros])), 4),
                    "umidade": round(self._media_umidade(), 2),
                    "limiar_pressao": round(self._limiar_pressao(), 4),
                    "limiar_temperatura": round(
                        self._limiar_temperatura(), 2),
                } if self._registros else None
            ),
            "clima_previsto": prev,
            "top5_clima_previsto": (
                self.top5_clima() if self._registros else list(range(1, 6))),
            "auto_ponderacao": self.auto_ponderacao(),
            "testes_fisicos": self.testes_fisicos(),
            "principios": [
                "Correlação ≠ causa: vereditos em 95%/68% (z 1.96/1.0)",
                "Shrinkage 50/50 + teto ±10% por dezena",
                "Auto-auditoria walk-forward escala o peso da fonte",
            ],
        }
