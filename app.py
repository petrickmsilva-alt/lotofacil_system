"""
============================================================
SISTEMA LOTOFÁCIL - SERVIDOR PRINCIPAL FLASK
IA Autônoma v3.0 — Física Quântica + Machine Learning
============================================================
"""

# ── Migração automática do banco ──────────────────────────────
import os
import sys
import traceback
import threading
import json
from datetime import datetime

import numpy as np  # ← ESTE ERA O QUE FALTAVA

# ── Migrar banco antes de tudo ────────────────────────────────
try:
    from database.migrar import migrar
    migrar()
except Exception as _e:
    print("[AVISO] Migração: {}".format(_e))

# ── Flask ─────────────────────────────────────────────────────
from flask import (
    Flask, render_template, request,
    jsonify, redirect, url_for
)

# ── Módulos do sistema ────────────────────────────────────────
from config import VALOR_APOSTA
from database.db_manager import DBManager
from core.data_loader        import DataLoader
from core.bitmatrix          import BitMatrix
from core.filtros_gaussianos import FiltrosGaussianos
from core.markov_engine      import MarkovEngine
from core.fisica_quantica    import FisicaQuantica
from core.covering_designs   import CoveringDesigns
from core.ia_autonoma        import IAAutonoma
from core.conferencia        import Conferencia
from core.financeiro         import Financeiro
from core.ia_monitor         import IAMonitor

# ── Instâncias globais ────────────────────────────────────────
app         = Flask(__name__)
db          = DBManager()
data_loader = DataLoader()
bitmatrix   = BitMatrix()
ia          = IAAutonoma()
conferencia = Conferencia()
financeiro  = Financeiro()
monitor     = IAMonitor()

# ── Status global ─────────────────────────────────────────────
status_sistema = {
    "dados_carregados": False,
    "ia_treinada":      False,
    "ultimo_concurso":  0,
    "total_concursos":  0,
    "progresso":        "",
    "carregando":       False,
    "treinando":        False,
}


# ============================================================
# ROTAS PRINCIPAIS
# ============================================================

@app.route("/")
def index():
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0
    status_sistema["dados_carregados"] = status_sistema["ultimo_concurso"] > 0

    resumo_fin  = financeiro.get_resumo_geral()
    resumo_conf = conferencia.resumo_conferencia()
    ia_status   = ia.get_status()

    # Converter resumo_conf para formato simples {pontos: qtd}
    conf_simples = {}
    for pts, dados in resumo_conf.items():
        if isinstance(dados, dict):
            conf_simples[pts] = dados.get("qtd", 0)
        else:
            conf_simples[pts] = dados

    return render_template(
        "index.html",
        status      = status_sistema,
        financeiro  = resumo_fin,
        conferencia = conf_simples,
        ia_status   = ia_status,
        valor_aposta = VALOR_APOSTA,
    )


@app.route("/historico")
def historico():
    resultados = db.get_todos_resultados()
    lista = []
    for r in list(resultados)[-100:]:
        lista.append({
            "concurso": r["concurso"],
            "data":     r["data"],
            "dezenas":  [r[f"d{i}"] for i in range(1, 16)],
            "soma":     r["soma"],
            "pares":    r["pares"],
        })
    lista.reverse()
    return render_template("historico.html", resultados=lista)


@app.route("/gerar", methods=["GET", "POST"])
def gerar():
    import time
    cartelas = []
    msg      = ""

    if request.method == "POST":
        n_cartelas = int(request.form.get("n_cartelas", 10))
        t_inicio   = time.time()

        try:
            resultados = db.get_todos_resultados()

            if not resultados:
                msg = "Carregue os dados primeiro."
                return render_template("gerar.html",
                                       cartelas=cartelas, msg=msg)

            ultimo   = resultados[-1]
            proximo  = ultimo["concurso"] + 1

            print("[GERAR] Iniciando geração de {} cartelas...".format(
                n_cartelas
            ))

            # Gerar cartelas
            # Se IA treinada, usar IA. Senão, usar fallback inteligente.
            if ia.treinado:
                cartelas_geradas = ia.gerar_cartelas(ultimo, n_cartelas)
            else:
                print("[GERAR] IA não treinada, usando geração estatística")
                cartelas_geradas = _gerar_sem_ia(
                    resultados, n_cartelas
                )

            # Garantir que temos cartelas
            if not cartelas_geradas:
                cartelas_geradas = ia._gerar_fallback(n_cartelas)

            # Salvar no banco
            salvos = 0
            for c in cartelas_geradas:
                try:
                    dez = c.get("dezenas", [])
                    if len(dez) != 15:
                        continue

                    dados = (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        proximo,
                        dez[0],  dez[1],  dez[2],  dez[3],  dez[4],
                        dez[5],  dez[6],  dez[7],  dez[8],  dez[9],
                        dez[10], dez[11], dez[12], dez[13], dez[14],
                        c.get("bitmask",       0),
                        c.get("score_ia",      0),
                        c.get("score_markov",  0),
                        c.get("score_fisico",  0),
                        c.get("score_entropia",0),
                        c.get("score_total",   0),
                    )
                    db.inserir_cartela(dados)
                    salvos += 1
                except Exception as e:
                    print("[GERAR] Erro salvar cartela: {}".format(e))

            cartelas = cartelas_geradas
            custo    = salvos * VALOR_APOSTA
            tempo    = time.time() - t_inicio

            msg = (
                "{} cartelas geradas para o concurso {} "
                "em {:.1f}s. Custo: R$ {:.2f}"
            ).format(salvos, proximo, tempo, custo)

            print("[GERAR] " + msg)

        except Exception as e:
            msg = "Erro ao gerar: {}".format(str(e))
            traceback.print_exc()

    return render_template("gerar.html", cartelas=cartelas, msg=msg)


def _gerar_sem_ia(resultados, n_cartelas):
    """
    Gera cartelas estatísticas sem IA treinada.
    Usa frequência histórica + filtros básicos.
    """
    # Calcular frequência das dezenas
    freq = np.zeros(25)
    for r in resultados[-200:]:
        for i in range(1, 16):
            d = r["d{}".format(i)]
            if 1 <= d <= 25:
                freq[d - 1] += 1

    if freq.sum() > 0:
        freq /= freq.sum()
    else:
        freq = np.ones(25) / 25

    cartelas = []
    bm       = BitMatrix()

    for i in range(n_cartelas * 5):
        if len(cartelas) >= n_cartelas:
            break
        try:
            np.random.seed(i + int(datetime.now().timestamp()))
            idx = np.random.choice(25, size=15, replace=False, p=freq)
            dez = sorted([int(j + 1) for j in idx])

            # Filtros básicos
            soma  = sum(dez)
            pares = sum(1 for d in dez if d % 2 == 0)
            if soma < 170 or soma > 235:
                continue
            if pares < 5 or pares > 10:
                continue

            mask = bm.dezenas_para_bitmask(dez)
            cartelas.append({
                "dezenas":         dez,
                "bitmask":         mask,
                "score_ia":        0.50,
                "score_markov":    0.50,
                "score_fisico":    0.50,
                "score_gaussiano": 0.50,
                "score_entropia":  0.50,
                "score_total":     round(float(np.mean([freq[d-1] for d in dez])), 4),
            })
        except Exception:
            continue

    # Completar se necessário
    while len(cartelas) < n_cartelas:
        np.random.seed(len(cartelas) + 9999)
        idx = np.random.choice(25, size=15, replace=False)
        dez = sorted([int(j + 1) for j in idx])
        mask = BitMatrix().dezenas_para_bitmask(dez)
        cartelas.append({
            "dezenas":     dez,
            "bitmask":     mask,
            "score_ia":    0.50,
            "score_markov":0.50,
            "score_fisico":0.50,
            "score_gaussiano":0.50,
            "score_entropia":0.50,
            "score_total": 0.50,
        })

    return cartelas[:n_cartelas]


# ============================================================
# ROTAS DE CONFERÊNCIA — bloco único, sem duplicatas
# ============================================================

@app.route("/conferencia")
def conferencia_page():
    concursos  = conferencia.get_concursos_com_cartelas()
    resumo_raw = conferencia.resumo_conferencia()

    resumo = {}
    for pts, dados in resumo_raw.items():
        if isinstance(dados, dict):
            resumo[pts] = dados
        else:
            resumo[pts] = {"qtd": dados, "total_premio": 0}

    return render_template(
        "conferencia.html",
        concursos = concursos,
        resumo    = resumo,
    )


@app.route("/api/conferir_concurso", methods=["POST"])
def api_conferir_concurso():
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))

        if concurso < 1:
            return jsonify({
                "status": "erro",
                "msg":    "Número de concurso inválido."
            })

        resultado = conferencia.conferir_concurso(concurso)
        return jsonify(resultado)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cartelas_concurso/<int:concurso>")
def api_cartelas_concurso(concurso):
    try:
        cartelas = conferencia.get_cartelas_do_concurso(concurso)
        return jsonify({"status": "ok", "cartelas": cartelas})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})

@app.route("/api/apagar_cartelas_concurso", methods=["POST"])
def api_apagar_cartelas_concurso():
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})

        conn   = db.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM cartelas WHERE concurso_alvo = ?", (concurso,)
        )
        apagadas = cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({"status": "ok", "apagadas": apagadas})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/apagar_cartelas", methods=["POST"])
def api_apagar_cartelas():
    try:
        dados = request.get_json() or {}
        ids   = dados.get("ids", [])
        if not ids:
            return jsonify({"status": "erro", "msg": "Nenhum ID informado"})

        conn   = db.get_conn()
        cursor = conn.cursor()
        apagadas = 0
        for cid in ids:
            cursor.execute(
                "DELETE FROM cartelas WHERE id = ?", (int(cid),)
            )
            apagadas += cursor.rowcount
        conn.commit()
        conn.close()

        return jsonify({"status": "ok", "apagadas": apagadas})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/adicionar_cartelas_concurso", methods=["POST"])
def api_adicionar_cartelas_concurso():
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        qtd      = int(dados.get("quantidade", 5))

        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})
        if qtd < 1 or qtd > 50:
            return jsonify({"status": "erro", "msg": "Quantidade inválida"})

        resultados = db.get_todos_resultados()
        if not resultados:
            return jsonify({"status": "erro", "msg": "Sem dados históricos"})

        # Encontrar resultado mais próximo ao concurso alvo
        ultimo = resultados[-1]
        for r in reversed(resultados):
            if r["concurso"] < concurso:
                ultimo = r
                break

        # Gerar cartelas
        if ia.treinado:
            cartelas_novas = ia.gerar_cartelas(ultimo, qtd)
        else:
            cartelas_novas = _gerar_sem_ia(resultados, qtd)

        adicionadas = 0
        for c in cartelas_novas:
            try:
                dez = c.get("dezenas", [])
                if len(dez) != 15:
                    continue
                dados_ins = (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    concurso,
                    dez[0],  dez[1],  dez[2],  dez[3],  dez[4],
                    dez[5],  dez[6],  dez[7],  dez[8],  dez[9],
                    dez[10], dez[11], dez[12], dez[13], dez[14],
                    c.get("bitmask",        0),
                    c.get("score_ia",       0),
                    c.get("score_markov",   0),
                    c.get("score_fisico",   0),
                    c.get("score_entropia", 0),
                    c.get("score_total",    0),
                )
                db.inserir_cartela(dados_ins)
                adicionadas += 1
            except Exception as e:
                print("[ADD] erro: {}".format(e))

        return jsonify({
            "status":     "ok",
            "adicionadas": adicionadas,
            "concurso":   concurso,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})

@app.route("/financeiro_page")
def financeiro_page():
    resumo = financeiro.get_resumo_geral()
    return render_template("financeiro.html", resumo=resumo)


@app.route("/ia_painel")
def ia_painel():
    ia_status   = ia.get_status()
    aprendizado = db.get_historico_aprendizado()
    return render_template(
        "ia_painel.html",
        status      = ia_status,
        aprendizado = aprendizado,
    )


@app.route("/analise")
def analise():
    resultados  = db.get_todos_resultados()
    freq        = bitmatrix.heatmap_frequencia(resultados)
    freq_rec    = bitmatrix.heatmap_frequencia(resultados, janela=50)

    heatmap = {
        i + 1: {
            "total":   round(float(freq[i]),     2),
            "recente": round(float(freq_rec[i]), 2),
        }
        for i in range(25)
    }

    return render_template(
        "analise.html",
        heatmap         = heatmap,
        total_concursos = len(resultados),
    )


@app.route("/premios")
def premios():
    ultimos    = db.get_ultimos_premios(20)
    medias     = db.get_media_premios()
    estimativa = data_loader.buscar_estimativa_premio()

    premios_lista = []
    for r in ultimos:
        premios_lista.append({
            "concurso":      r["concurso"],
            "data":          r["data"],
            "premio_11":     r["premio_11"]     or 0,
            "premio_12":     r["premio_12"]     or 0,
            "premio_13":     r["premio_13"]     or 0,
            "premio_14":     r["premio_14"]     or 0,
            "premio_15":     r["premio_15"]     or 0,
            "ganhadores_15": r["ganhadores_15"] or 0,
        })

    medias_dict = {}
    if medias:
        medias_dict = {
            "media_11": round(float(medias["media_11"] or 6),       2),
            "media_12": round(float(medias["media_12"] or 12),      2),
            "media_13": round(float(medias["media_13"] or 30),      2),
            "media_14": round(float(medias["media_14"] or 1800),    2),
            "media_15": round(float(medias["media_15"] or 0),       2),
            "min_15":   round(float(medias["min_15"]   or 0),       2),
            "max_15":   round(float(medias["max_15"]   or 0),       2),
        }

    return render_template(
        "premios.html",
        premios    = premios_lista,
        medias     = medias_dict,
        estimativa = estimativa,
    )

from core.ia_monitor import IAMonitor
monitor = IAMonitor()

@app.route("/ia_auditoria")
def ia_auditoria():
    stats          = monitor.get_dashboard_stats()
    ranking_modulos = monitor.get_ranking_modulos()
    sessoes        = monitor.get_ultimas_sessoes(10)
    evolucao_pesos = monitor.get_evolucao_pesos(20)

    return render_template(
        "ia_auditoria.html",
        stats           = stats,
        ranking_modulos = ranking_modulos,
        sessoes         = sessoes,
        evolucao_pesos  = evolucao_pesos,
    )

@app.route("/api/ia_sessao/<int:sessao_id>")
def api_ia_sessao(sessao_id):
    relatorio = monitor.get_relatorio_sessao(sessao_id)
    return jsonify(relatorio)

@app.route("/api/ia_log_tempo_real")
def api_ia_log_tempo_real():
    """Retorna os últimos logs para atualização em tempo real"""
    sessoes = monitor.get_ultimas_sessoes(1)
    if not sessoes:
        return jsonify({"logs": []})
    sid  = sessoes[0]["id"]
    rel  = monitor.get_relatorio_sessao(sid)
    return jsonify({"logs": rel.get("modulos", [])})

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route("/api/carregar_dados", methods=["POST"])
def api_carregar_dados():
    if status_sistema["carregando"]:
        return jsonify({"status": "info", "msg": "Já está carregando..."})

    def carregar():
        status_sistema["carregando"] = True

        def cb(concurso, carregados, total, msg):
            status_sistema["progresso"] = msg

        resultado = data_loader.carregar_historico_completo(cb)
        status_sistema["carregando"]      = False
        status_sistema["dados_carregados"] = True
        status_sistema["ultimo_concurso"] = db.get_ultimo_concurso()
        status_sistema["progresso"] = (
            f"✅ Completo! "
            f"{resultado.get('total_carregados', 0)} concursos carregados."
        )

    threading.Thread(target=carregar, daemon=True).start()
    return jsonify({"status": "ok", "msg": "Carregamento iniciado..."})


@app.route("/api/atualizar_dados", methods=["POST"])
def api_atualizar():
    resultado = data_loader.atualizar_diario()
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso()
    return jsonify(resultado)


@app.route("/api/atualizar_diario", methods=["POST"])
def api_atualizar_diario():
    resultado = data_loader.atualizar_diario()
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso()
    return jsonify(resultado)


@app.route("/api/treinar_ia", methods=["POST"])
def api_treinar_ia():
    if status_sistema["treinando"]:
        return jsonify({"status": "info", "msg": "Já está treinando..."})

    def treinar():
        status_sistema["treinando"] = True

        try:
            resultados = db.get_todos_resultados()
            if not resultados:
                status_sistema["progresso"] = "❌ Sem dados!"
                status_sistema["treinando"] = False
                return

            def cb(msg):
                status_sistema["progresso"] = msg

            ia.treinar(resultados, cb)
            status_sistema["ia_treinada"] = True
            status_sistema["progresso"] = (
                f"✅ IA treinada com {len(resultados)} concursos!"
            )

        except Exception as e:
            status_sistema["progresso"] = f"❌ Erro: {str(e)}"
            traceback.print_exc()

        status_sistema["treinando"] = False

    threading.Thread(target=treinar, daemon=True).start()
    return jsonify({"status": "ok", "msg": "Treinamento iniciado..."})


@app.route("/api/status")
def api_status():
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    return jsonify(status_sistema)


@app.route("/api/status_base")
def api_status_base():
    return jsonify(data_loader.get_status_base())


@app.route("/api/conferir", methods=["POST"])
def api_conferir():
    try:
        resultados = conferencia.conferir_todas_pendentes()
        return jsonify({
            "status":    "ok",
            "conferidas": len(resultados),
        })
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/premios/<int:concurso>")
def api_premios_concurso(concurso):
    row = db.get_premios_concurso(concurso)
    if not row:
        return jsonify({"status": "erro", "msg": "Não encontrado"})
    return jsonify({
        "status":        "ok",
        "concurso":      concurso,
        "premio_11":     row["premio_11"],
        "premio_12":     row["premio_12"],
        "premio_13":     row["premio_13"],
        "premio_14":     row["premio_14"],
        "premio_15":     row["premio_15"],
        "ganhadores_15": row["ganhadores_15"],
    })


@app.route("/api/backtesting", methods=["POST"])
def api_backtesting():
    try:
        resultados = db.get_todos_resultados()
        if not resultados or len(resultados) < 200:
            return jsonify({"status": "erro", "msg": "Dados insuficientes"})
        resultado = ia.backtesting(resultados, n_cartelas=5, janela=150)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/gerar_rapido", methods=["POST"])
def api_gerar_rapido():
    try:
        data_req   = request.get_json() or {}
        n          = int(data_req.get("n_cartelas", 10))
        resultados = db.get_todos_resultados()

        if not resultados:
            return jsonify({"status": "erro", "msg": "Sem dados"})
        if not ia.treinado:
            return jsonify({"status": "erro", "msg": "IA não treinada"})

        cartelas = ia.gerar_cartelas(resultados[-1], n)
        return jsonify({
            "status":   "ok",
            "cartelas": [
                {
                    "dezenas":     c["dezenas"],
                    "score_total": round(c["score_total"], 4),
                }
                for c in cartelas
            ],
        })
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║   SISTEMA LOTOFÁCIL - IA AUTÔNOMA               ║
║   Física Quântica + Machine Learning             ║
║   Acesse: http://localhost:5000                  ║
╚══════════════════════════════════════════════════╝
    """)

    # Tentar carregar modelos salvos
    if ia._carregar_modelos():
        status_sistema["ia_treinada"] = True
        print("[OK] Modelos da IA carregados")

    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0

    if status_sistema["ultimo_concurso"] > 0:
        status_sistema["dados_carregados"] = True
        print(f"[OK] {status_sistema['ultimo_concurso']} concursos no banco")

    app.run(debug=True, port=5000)
# ============================================================
# MAPA DE TODAS AS ROTAS — verificar duplicatas
# ============================================================
#
# GET  /                          → index
# GET  /historico                 → historico
# GET  /gerar          POST       → gerar
# GET  /conferencia               → conferencia_page
# GET  /financeiro_page           → financeiro_page
# GET  /ia_painel                 → ia_painel
# GET  /analise                   → analise
# GET  /premios                   → premios
# GET  /ia_auditoria              → ia_auditoria
#
# POST /api/carregar_dados        → api_carregar_dados
# POST /api/atualizar_dados       → api_atualizar
# POST /api/atualizar_diario      → api_atualizar_diario
# POST /api/treinar_ia            → api_treinar_ia
# GET  /api/status                → api_status
# GET  /api/status_base           → api_status_base
# POST /api/conferir              → api_conferir
# POST /api/conferir_concurso     → api_conferir_concurso
# GET  /api/cartelas_concurso/<n> → api_cartelas_concurso
# GET  /api/premios/<n>           → api_premios_concurso
# POST /api/backtesting           → api_backtesting
# POST /api/gerar_rapido          → api_gerar_rapido
# GET  /api/ia_sessao/<n>         → api_ia_sessao
# GET  /api/ia_log_tempo_real     → api_ia_log_tempo_real