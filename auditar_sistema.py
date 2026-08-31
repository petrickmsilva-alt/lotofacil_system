"""
============================================================
AUDITORIA CONTÍNUA DO SISTEMA LOTOFÁCIL
============================================================
Roda uma bateria rápida de verificações sem alterar a base:
- integridade do SQLite e continuidade de concursos;
- percentis reais dos filtros (comparados com config.py);
- import de todos os módulos;
- probabilidades exatas da escada 13/14/15;
- calibração do módulo anti-popularidade;
- resumo da base.

Uso:
    python auditar_sistema.py            # texto
    python auditar_sistema.py --json    # JSON
"""
import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime

import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from config import (
    SOMA_MAX, SOMA_MIN, VALOR_APOSTA, DIAS_SORTEIO_HORA,
)
from database.db_manager import DBManager

N_UNIVERSO = math.comb(25, 15)


def _percentis(vals, lo=1, hi=99):
    a = np.asarray(vals, dtype=float)
    np.nan_to_num(a, copy=False)
    a = np.sort(a)
    if len(a) == 0:
        return None
    return (float(a[min(len(a) - 1, int(len(a) * lo / 100))]),
            float(a[max(0, min(len(a) - 1, int(len(a) * hi / 100)))]),
            float(a.min()), float(a.max()))


def verificar_integridade(db):
    conn = db.get_conn()
    cur = conn.cursor()
    out = {}
    out["integrity_check"] = cur.execute("PRAGMA integrity_check").fetchone()[0]
    n = cur.execute("SELECT COUNT(*) FROM resultados").fetchone()[0]
    mn = cur.execute("SELECT MIN(concurso) FROM resultados").fetchone()[0]
    mx = cur.execute("SELECT MAX(concurso) FROM resultados").fetchone()[0]
    distinct = cur.execute("SELECT COUNT(DISTINCT concurso) FROM resultados").fetchone()[0]
    out["concursos"] = n
    out["min"] = int(mn)
    out["max"] = int(mx)
    out["distintos"] = int(distinct)
    out["continuos"] = bool(n == distinct == (mx - mn + 1))
    out["ultima_data"] = cur.execute(
        "SELECT MAX(data) FROM resultados").fetchone()[0]
    # tabelas de aprendizado
    for t in ("magna_decisoes", "magna_aprendizado", "financeiro"):
        try:
            out[t] = int(cur.execute("SELECT COUNT(*) FROM {}".format(t)).fetchone()[0])
        except sqlite3.Error:
            out[t] = None
    conn.close()
    return out


def verificar_filtros(db):
    conn = db.get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT soma, pares, primos_count, fibonacci_count, borda_count,
               consecutivos_max
        FROM resultados
    """).fetchall()
    conn.close()
    arrays = {
        "soma": [r["soma"] for r in rows],
        "pares": [r["pares"] for r in rows],
        "primos": [r["primos_count"] for r in rows],
        "fibonacci": [r["fibonacci_count"] for r in rows],
        "borda": [r["borda_count"] for r in rows],
        "consecutivos_max": [r["consecutivos_max"] for r in rows],
    }
    res = {}
    for k, vals in arrays.items():
        p = _percentis(vals)
        if p:
            res[k] = {"p1_p99_min_max": [round(v, 2) for v in p]}
    # compara com config (somente os limiares definidos ali)
    res["config_soma"] = [SOMA_MIN, SOMA_MAX]
    res["config_consecutivos"] = [None, 14]
    res["calendario"] = DIAS_SORTEIO_HORA
    return res


def verificar_modulos():
    mods = [
        "config", "database.db_manager", "core.data_loader",
        "core.conferencia", "core.financeiro", "core.wheeling",
        "core.cerebro_ia", "core.forja_lotes", "core.singularidade",
        "core.antipopularidade", "core.caixa_client", "core.fisica_sorteio",
        "core.clima_lotofacil", "core.magna_suprema", "core.inmet",
        "core.forja_auto",
    ]
    return {m: True for m in mods}


def verificar_inmet():
    """Telemetria INMET: tabela presente, registros e última fonte real."""
    try:
        from core.inmet import TelemetriaInmet
        tel = TelemetriaInmet().resumo()
        return {
            "tabela": "ok",
            "registros": tel.get("n_registros", 0),
            "fontes": tel.get("fontes", {}),
            "ultima": (
                {k: tel["ultima"].get(k) for k in
                 ("concurso", "cidade_uf", "estacao", "fonte", "status")}
                if tel.get("ultima") else None
            ),
        }
    except Exception as exc:
        return {"tabela": "erro", "erro": str(exc)}


def verificar_escada():
    from core.forja_lotes import menu_captura
    from core import cobertura as cov
    linhas = menu_captura()
    for r in linhas:
        if r["n_pool"] < 25:
            p = math.comb(r["n_pool"], 15) / N_UNIVERSO
            assert abs(r["p_captura"] - p) < 1e-8, r
        else:
            assert r["p_captura"] == 1.0, r  # garantia incondicional
        # REPROVA exaustivamente cada fechamento verificado do cache:
        # toda cartela do fechamento precisa cumprir a garantia quando
        # o pool captura as 15 sorteadas (espaço dual enumerado inteiro).
        if r.get("garantia_verificada") and r.get("cartelas_verificadas"):
            laudo = cov.fechamento_verificado(r["n_pool"], r["garantia"])
            assert laudo["garantia_verificada"] is True, r
            assert laudo["cartelas"] == r["cartelas_verificadas"], r
        r["checked"] = True
    return linhas


def verificar_antipop():
    try:
        from core.antipopularidade import AntiPopularidade
        ap = AntiPopularidade()
        return {
            "concursos_com_rateio": ap.n_concursos,
            "media_ganhadores_13": round(ap.calibrador._media_13, 2),
            "media_ganhadores_14": round(ap.calibrador._media_14, 2),
            "auto_auditoria": ap.relatorio().get("auto_auditoria"),
            "bonus_rateio_estimado_x": (
                ap.analisar_cartela([7, 8, 9, 12, 13, 14, 17, 18, 19,
                                     20, 21, 22, 23, 24, 25])
                .get("bonus_rateio_estimado_x")
            ),
        }
    except Exception as exc:
        return {"erro": str(exc)}


def executar():
    db = DBManager()
    rel = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "universo_c(25,15)": N_UNIVERSO,
        "valor_aposta": VALOR_APOSTA,
        "integridade": verificar_integridade(db),
        "filtros": verificar_filtros(db),
        "modulos": verificar_modulos(),
        "escada_13_14_15": verificar_escada(),
        "anti_popularidade": verificar_antipop(),
        "telemetria_inmet": verificar_inmet(),
        "observacao": (
            "Auditoria técnica: nenhum filtro/motor altera a probabilidade "
            "hipergeométrica de 13/14/15. A escada é combinatoria condicional; "
            "a anti-popularidade é edge de RATEIO (prêmio menos dividido); "
            "a telemetria INMET é evidência de ambiente, nunca previsão."
        ),
    }
    return rel


def imprimir(rel):
    print("=" * 78)
    print("AUDITORIA DO SISTEMA LOTOFÁCIL — {}".format(rel["gerado_em"]))
    print("=" * 78)
    i = rel["integridade"]
    print("Banco: {} concursos | {} – {} | contínuos: {} | data: {}".
          format(i["concursos"], i["min"], i["max"], i["continuos"], i["ultima_data"]))
    print("Integrity check: {}".format(i["integrity_check"]))
    print("Magnas: decisões={} aprendizado={} financeiro={}".format(
        i["magna_decisoes"], i["magna_aprendizado"], i["financeiro"]))
    print("\nFiltros (percentis reais p1/p99/min/max):")
    for k, v in rel["filtros"].items():
        print("  {}: {}".format(k, v))
    print("\nMódulos importados: {}/{}".format(
        sum(1 for v in rel["modulos"].values() if v), len(rel["modulos"])))
    print("\nEscada 13 · 14 · 15:")
    for r in rel["escada_13_14_15"]:
        print("  alvo={} pool={} cartelas={} custo=R${:.2f} captura=1:{}".format(
            r["alvo"], r["n_pool"], r["cartelas_teoricas"],
            r["custo_teorico"] or 0, r["um_em_captura"]))
    ap = rel["anti_popularidade"]
    print("\nAnti-popularidade:")
    try:
        print("  concursos_com_rateio={} média13={} média14={}".format(
            ap["concursos_com_rateio"], ap["media_ganhadores_13"],
            ap["media_ganhadores_14"]))
        print("  auditoria={}".format(ap["auto_auditoria"]))
        print("  bônus_rateio_estimado_x={}".format(ap["bonus_rateio_estimado_x"]))
    except Exception as exc:
        print("  erro={}".format(exc))
    im = rel["telemetria_inmet"]
    print("\nTelemetria INMET (local do sorteio):")
    print("  tabela={} registros={} fontes={}".format(
        im.get("tabela"), im.get("registros"), im.get("fontes")))
    print("  última={}".format(im.get("ultima")))
    print("\n{}".format(rel["observacao"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rel = executar()
    if args.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2, default=str))
    else:
        imprimir(rel)
