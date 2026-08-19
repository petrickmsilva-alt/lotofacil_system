"""
============================================================
SISTEMA LOTOFÁCIL — SERVIDOR PRINCIPAL FLASK
Cérebro IA v6.0 — Módulo único de decisão autônoma
============================================================
MAPA DE ROTAS:
  GET  /                          → index
  GET  /historico                 → historico
  GET  /gerar          POST       → gerar
  GET  /conferencia               → conferencia_page
  GET  /financeiro_page           → financeiro_page
  GET  /analise                   → analise
  GET  /premios                   → premios
  GET  /ia_auditoria              → ia_auditoria
  GET  /cerebro                   → cerebro_page

  POST /api/carregar_dados        → api_carregar_dados
  POST /api/atualizar_dados       → api_atualizar_dados
  POST /api/treinar_ia            → api_treinar_ia
  GET  /api/status                → api_status
  GET  /api/status_base           → api_status_base
  POST /api/conferir              → api_conferir
  POST /api/conferir_concurso     → api_conferir_concurso
  GET  /api/cartelas_concurso/<n> → api_cartelas_concurso
  POST /api/apagar_cartelas       → api_apagar_cartelas
  POST /api/apagar_cartelas_concurso → api_apagar_cartelas_concurso
  POST /api/adicionar_cartelas_concurso → api_adicionar_cartelas_concurso
  GET  /api/premios/<n>           → api_premios_concurso
  GET  /api/ia_sessao/<n>         → api_ia_sessao
  GET  /api/ia_log_tempo_real     → api_ia_log_tempo_real
  GET  /api/cerebro/status        → api_cerebro_status
  POST /api/cerebro/treinar       → api_cerebro_treinar
  POST /api/cerebro/gerar         → api_cerebro_gerar
  POST /api/cerebro/ciclo         → api_cerebro_ciclo
  POST /api/cerebro/loop/iniciar  → api_cerebro_loop_iniciar
  POST /api/cerebro/loop/parar    → api_cerebro_loop_parar
  POST /api/cerebro/loop/pausar   → api_cerebro_loop_pausar
  POST /api/cerebro/loop/retomar  → api_cerebro_loop_retomar
  GET  /api/cerebro/fila/<n>      → api_cerebro_fila
  GET  /api/cerebro/historico     → api_cerebro_historico
  POST /api/cerebro/backtesting   → api_cerebro_backtesting
  GET  /api/cerebro/log           → api_cerebro_log
============================================================
"""

# ── Imports padrão ────────────────────────────────────────────
import os
import time
import traceback
import threading
import json
from datetime import datetime

import numpy as np

# ── Migração do banco ANTES de tudo ──────────────────────────
try:
    from database.migrar import migrar
    migrar()
except Exception as _e:
    print("[AVISO] Migração: {}".format(_e))

# ── Flask ─────────────────────────────────────────────────────
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ── Módulos do sistema ────────────────────────────────────────
from config import VALOR_APOSTA
from database.db_manager  import DBManager
from core.data_loader     import DataLoader
from core.bitmatrix       import BitMatrix
from core.conferencia     import Conferencia
from core.financeiro      import Financeiro
from core.ia_monitor      import IAMonitor
from core.cerebro_ia      import CerebroIA        # ← PROTAGONISTA ÚNICO

# ── Instâncias globais ────────────────────────────────────────
db          = DBManager()
data_loader = DataLoader()
bitmatrix   = BitMatrix()
conferencia = Conferencia()
financeiro  = Financeiro()
monitor     = IAMonitor()
cerebro     = CerebroIA(n_cartelas=10)            # ← ÚNICA INSTÂNCIA DE IA

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
# HELPERS INTERNOS
# ============================================================

def _gerar_sem_cerebro(n_cartelas: int):
    """
    Fallback estatístico simples quando o Cérebro ainda
    não foi treinado. Usa frequência histórica + filtros básicos.
    """
    resultados = db.get_todos_resultados()
    freq       = np.zeros(25)

    for r in list(resultados)[-200:]:
        for i in range(1, 16):
            d = r["d{}".format(i)]
            if 1 <= d <= 25:
                freq[d - 1] += 1

    s = freq.sum()
    freq = freq / s if s > 0 else np.ones(25) / 25.0

    cartelas = []
    bm       = BitMatrix()

    for i in range(n_cartelas * 8):
        if len(cartelas) >= n_cartelas:
            break
        try:
            np.random.seed(i + int(time.time()) % 100000)
            idx  = np.random.choice(25, size=15, replace=False, p=freq)
            dez  = sorted([int(j + 1) for j in idx])
            soma = sum(dez)
            par  = sum(1 for d in dez if d % 2 == 0)
            if soma < 170 or soma > 235:
                continue
            if par < 5 or par > 10:
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
                "score_total":     round(
                    float(np.mean([freq[d - 1] for d in dez])), 4
                ),
                "scores": {},
            })
        except Exception:
            continue

    # Completar se necessário
    while len(cartelas) < n_cartelas:
        np.random.seed(len(cartelas) + 88888)
        idx  = np.random.choice(25, size=15, replace=False)
        dez  = sorted([int(j + 1) for j in idx])
        mask = BitMatrix().dezenas_para_bitmask(dez)
        cartelas.append({
            "dezenas":         dez,
            "bitmask":         mask,
            "score_ia":        0.50,
            "score_markov":    0.50,
            "score_fisico":    0.50,
            "score_gaussiano": 0.50,
            "score_entropia":  0.50,
            "score_total":     0.50,
            "scores": {},
        })

    return cartelas[:n_cartelas]


def _salvar_cartelas_banco(cartelas, concurso_alvo):
    """Salva lista de cartelas no banco. Retorna quantidade salva."""
    salvos = 0
    for c in cartelas:
        try:
            dez = c.get("dezenas", [])
            if len(dez) != 15:
                continue
            dados = (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                concurso_alvo,
                dez[0],  dez[1],  dez[2],  dez[3],  dez[4],
                dez[5],  dez[6],  dez[7],  dez[8],  dez[9],
                dez[10], dez[11], dez[12], dez[13], dez[14],
                int(c.get("bitmask", 0)),
                float(c.get("score_total", 0)),
                float(c.get("scores", {}).get("markov",   0)),
                float(c.get("scores", {}).get("verlet",   0)),
                float(c.get("scores", {}).get("ev_prob",  0)),
                float(c.get("score_total", 0)),
            )
            db.inserir_cartela(dados)
            salvos += 1
        except Exception as e:
            print("[SALVAR_CARTELA] {}".format(e))
    return salvos


# ============================================================
# ROTAS PRINCIPAIS — PÁGINAS
# ============================================================

@app.route("/")
def index():
    """Dashboard principal"""
    status_sistema["ultimo_concurso"]  = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"]  = db.get_total_concursos() or 0
    status_sistema["dados_carregados"] = status_sistema["ultimo_concurso"] > 0
    status_sistema["ia_treinada"]      = cerebro.treinado

    resumo_fin  = financeiro.get_resumo_geral()
    resumo_conf = conferencia.resumo_conferencia()

    # Status do Cérebro IA formatado para o template
    cerebro_status = cerebro.get_status()
    ia_status = {
        "versao":           cerebro_status.get("versao",          "6.0"),
        "treinado":         cerebro_status.get("treinado",         False),
        "concursos_treino": cerebro_status.get("total_concursos",     0),
        "modelos_dezena":   0,
        "stacking_treinado": False,
        "modulos_ativos":   14,
        # Compatibilidade com o template antigo que usa ia_status.pesos
        "pesos": cerebro_status.get("pesos_modulos", {
            "markov":     0.11,
            "fisico":     0.07,
            "gaussiano":  0.05,
            "ml":         0.07,
            "verlet":     0.07,
            "quantum":    0.08,
            "chi2":       0.07,
            "bayes":      0.08,
            "kl":         0.05,
            "stacking":   0.06,
            "anti_logica":0.11,
            "reversao":   0.09,
            "cobertura":  0.04,
            "genetico":   0.05,
        }),
    }

    conf_simples = {}
    for pts, dados in resumo_conf.items():
        conf_simples[pts] = dados.get("qtd", 0) \
            if isinstance(dados, dict) else dados

    return render_template(
        "index.html",
        status       = status_sistema,
        financeiro   = resumo_fin,
        conferencia  = conf_simples,
        ia_status    = ia_status,
        valor_aposta = VALOR_APOSTA,
    )


@app.route("/historico")
def historico():
    """Histórico dos últimos 100 concursos"""
    resultados = db.get_todos_resultados()
    lista = []
    for r in list(resultados)[-100:]:
        lista.append({
            "concurso": r["concurso"],
            "data":     r["data"],
            "dezenas":  [r["d{}".format(i)] for i in range(1, 16)],
            "soma":     r["soma"],
            "pares":    r["pares"],
        })
    lista.reverse()
    return render_template("historico.html", resultados=lista)


# ============================================================
# ROTA UNIFICADA — CÉREBRO IA + GERAR CARTELAS
# ============================================================

@app.route("/cerebro", methods=["GET", "POST"])
def cerebro_page():
    """
    Página única do Cérebro IA:
    - Painel de controle e status
    - Treinamento dos 14 módulos
    - Geração de cartelas
    - Ciclo autônomo fechado
    - Histórico e aprendizado
    """
    cartelas = []
    msg      = ""
    metricas = {}

    if request.method == "POST":
        acao = request.form.get("acao", "gerar")

        # ── AÇÃO: GERAR CARTELAS ──────────────────────────────
        if acao == "gerar":
            n_cartelas = int(request.form.get("n_cartelas", 10))
            modo       = request.form.get("modo", "hibrido")
            t0         = time.time()

            try:
                if cerebro.n < 50:
                    msg = "Poucos dados no banco ({}). Carregue o histórico primeiro.".format(
                        cerebro.n
                    )
                else:
                    proximo = (db.get_ultimo_concurso() or 0) + 1
                    print("[CEREBRO] Gerando {} cartelas | modo={}".format(
                        n_cartelas, modo
                    ))

                    cartelas_geradas = cerebro.gerar_cartelas(
                        quantidade=n_cartelas,
                        modo=modo,
                    )

                    if cartelas_geradas:
                        salvos   = _salvar_cartelas_banco(cartelas_geradas, proximo)
                        cartelas = cartelas_geradas
                        custo    = salvos * VALOR_APOSTA
                        tempo    = time.time() - t0

                        metricas = {
                            "tempo":         round(tempo, 2),
                            "modo":          modo,
                            "grupo_elite":   cerebro.decisoes.get("grupo_elite", []),
                            "cobertura_13":  cerebro.metricas.get("cobertura_13", 0),
                            "concurso_alvo": proximo,
                            "salvos":        salvos,
                            "custo":         custo,
                        }

                        msg = "OK Cérebro IA gerou {} cartelas para concurso {} em {:.1f}s | Custo: R$ {:.2f}".format(
                            salvos, proximo, tempo, custo
                        )
                    else:
                        msg = "Cérebro não conseguiu gerar cartelas."

            except Exception as e:
                msg = "Erro no Cérebro: {}".format(str(e))
                traceback.print_exc()

    # Dados para renderização
    status    = cerebro.get_status()
    historico = cerebro.get_historico_ciclos(10)
    modulos   = cerebro.get_desempenho_modulos()
    erros     = cerebro.get_memoria_erros()

    return render_template(
        "cerebro.html",
        status    = status,
        historico = historico,
        modulos   = modulos,
        erros     = erros,
        cartelas  = cartelas,
        msg       = msg,
        metricas  = metricas,
    )


# Redirecionar /gerar para /cerebro
@app.route("/gerar", methods=["GET", "POST"])
def gerar():
    """Redireciona para o Cérebro IA (único módulo de geração)"""
    from flask import redirect, url_for
    if request.method == "POST":
        # Reencaminhar POST para /cerebro
        return cerebro_page()
    return redirect(url_for("cerebro_page"))


@app.route("/conferencia")
def conferencia_page():
    """Painel de conferência de jogos"""
    concursos  = conferencia.get_concursos_com_cartelas()
    resumo_raw = conferencia.resumo_conferencia()
    resumo = {}
    for pts, dados in resumo_raw.items():
        resumo[pts] = dados if isinstance(dados, dict) \
                      else {"qtd": dados, "total_premio": 0}
    return render_template(
        "conferencia.html",
        concursos = concursos,
        resumo    = resumo,
    )


@app.route("/financeiro_page")
def financeiro_page():
    """Painel financeiro"""
    return render_template(
        "financeiro.html",
        resumo = financeiro.get_resumo_geral()
    )


@app.route("/analise")
def analise():
    """Heatmaps e análises estatísticas"""
    resultados  = db.get_todos_resultados()
    freq        = bitmatrix.heatmap_frequencia(resultados)
    freq_rec    = bitmatrix.heatmap_frequencia(resultados, janela=50)
    heatmap     = {
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
    """Prêmios reais da Caixa"""
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
            "media_11": round(float(medias["media_11"] or 7),    2),
            "media_12": round(float(medias["media_12"] or 14),   2),
            "media_13": round(float(medias["media_13"] or 35),   2),
            "media_14": round(float(medias["media_14"] or 1800), 2),
            "media_15": round(float(medias["media_15"] or 0),    2),
            "min_15":   round(float(medias["min_15"]   or 0),    2),
            "max_15":   round(float(medias["max_15"]   or 0),    2),
        }

    return render_template(
        "premios.html",
        premios    = premios_lista,
        medias     = medias_dict,
        estimativa = estimativa,
    )


@app.route("/ia_auditoria")
def ia_auditoria():
    """Auditoria completa da IA"""
    return render_template(
        "ia_auditoria.html",
        stats           = monitor.get_dashboard_stats(),
        ranking_modulos = monitor.get_ranking_modulos(),
        sessoes         = monitor.get_ultimas_sessoes(10),
        evolucao_pesos  = monitor.get_evolucao_pesos(20),
    )

# ============================================================
# API — DADOS E STATUS
# ============================================================

@app.route("/api/status")
def api_status():
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["ia_treinada"]     = cerebro.treinado
    return jsonify(status_sistema)


@app.route("/api/status_base")
def api_status_base():
    return jsonify(data_loader.get_status_base())


@app.route("/api/carregar_dados", methods=["POST"])
def api_carregar_dados():
    """Baixa histórico completo da Caixa em background"""
    if status_sistema["carregando"]:
        return jsonify({"status": "info", "msg": "Já está carregando..."})

    def _carregar():
        status_sistema["carregando"] = True

        def cb(concurso, carregados, total, msg):
            status_sistema["progresso"] = msg

        resultado = data_loader.carregar_historico_completo(cb)
        status_sistema["carregando"]       = False
        status_sistema["dados_carregados"] = True
        status_sistema["ultimo_concurso"]  = db.get_ultimo_concurso()
        status_sistema["progresso"] = "✅ Completo! {} concursos carregados.".format(
            resultado.get("total_carregados", 0)
        )

        # Recarregar dados no Cérebro
        cerebro.matriz, cerebro.raw = cerebro._ingestor.carregar_matriz()
        cerebro.n = len(cerebro.matriz)

    threading.Thread(target=_carregar, daemon=True).start()
    return jsonify({"status": "ok", "msg": "Carregamento iniciado..."})


@app.route("/api/atualizar_dados", methods=["POST"])
def api_atualizar_dados():
    """Atualiza apenas concursos novos"""
    resultado = data_loader.atualizar_diario()
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso()

    # Recarregar no Cérebro
    cerebro.matriz, cerebro.raw = cerebro._ingestor.carregar_matriz()
    cerebro.n = len(cerebro.matriz)

    return jsonify(resultado)


# ============================================================
# API — CÉREBRO IA (ÚNICO MOTOR DE GERAÇÃO)
# ============================================================

@app.route("/api/treinar_ia", methods=["POST"])
def api_treinar_ia():
    """
    Treina o Cérebro IA com todos os 14 módulos.
    Substitui o antigo /api/treinar_ia.
    """
    if status_sistema["treinando"]:
        return jsonify({"status": "info", "msg": "Já está treinando..."})

    def _treinar():
        status_sistema["treinando"] = True
        try:
            def cb(msg):
                status_sistema["progresso"] = msg

            resultado = cerebro.treinar(callback=cb)
            status_sistema["ia_treinada"] = True
            status_sistema["progresso"]   = \
                "✅ Cérebro treinado! 14 módulos ativos."

        except Exception as e:
            status_sistema["progresso"] = "❌ Erro: {}".format(str(e))
            traceback.print_exc()

        status_sistema["treinando"] = False

    threading.Thread(target=_treinar, daemon=True).start()
    return jsonify({"status": "ok", "msg": "Treinamento do Cérebro iniciado..."})


@app.route("/api/cerebro/status")
def api_cerebro_status():
    return jsonify(cerebro.get_status())


@app.route("/api/cerebro/treinar", methods=["POST"])
def api_cerebro_treinar():
    """Alias direto para treinar o Cérebro"""
    return api_treinar_ia()


@app.route("/api/cerebro/gerar", methods=["POST"])
def api_cerebro_gerar():
    """Gera cartelas via Cérebro IA e salva no banco"""
    try:
        dados      = request.get_json() or {}
        quantidade = int(dados.get("quantidade", cerebro.n_cartelas))
        modo       = dados.get("modo", "hibrido")
        concurso   = int(dados.get("concurso", 0))

        if quantidade < 1 or quantidade > 50:
            return jsonify({"status": "erro", "msg": "Quantidade inválida (1-50)"})

        if concurso < 1:
            concurso = (db.get_ultimo_concurso() or 0) + 1

        cartelas = cerebro.gerar_cartelas(quantidade=quantidade, modo=modo)
        salvos   = _salvar_cartelas_banco(cartelas, concurso)

        return jsonify({
            "status":   "ok",
            "cartelas": cartelas,
            "salvas":   salvos,
            "concurso": concurso,
            "custo":    round(salvos * VALOR_APOSTA, 2),
            "metricas": cerebro.metricas,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/ciclo", methods=["POST"])
def api_cerebro_ciclo():
    """Executa um ciclo completo (Geração → Conferência → Aprendizado)"""
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})

        def _rodar():
            cerebro.executar_ciclo(concurso)

        threading.Thread(target=_rodar, daemon=True).start()
        return jsonify({
            "status":   "iniciado",
            "concurso": concurso,
            "msg":      "Ciclo iniciado em background",
        })
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/loop/iniciar", methods=["POST"])
def api_cerebro_loop_iniciar():
    """Inicia o loop automático do Cérebro"""
    dados      = request.get_json() or {}
    intervalo  = int(dados.get("intervalo",  3600))
    n_cartelas = int(dados.get("n_cartelas", cerebro.n_cartelas))
    if 1 <= n_cartelas <= 50:
        cerebro.n_cartelas = n_cartelas
    return jsonify(cerebro.iniciar_loop(intervalo))


@app.route("/api/cerebro/loop/parar", methods=["POST"])
def api_cerebro_loop_parar():
    return jsonify(cerebro.parar_loop())


@app.route("/api/cerebro/loop/pausar", methods=["POST"])
def api_cerebro_loop_pausar():
    return jsonify(cerebro.pausar_loop())


@app.route("/api/cerebro/loop/retomar", methods=["POST"])
def api_cerebro_loop_retomar():
    return jsonify(cerebro.retomar_loop())


@app.route("/api/cerebro/fila/<int:concurso>")
def api_cerebro_fila(concurso):
    return jsonify({
        "status": "ok",
        "fila":   cerebro.get_fila_concurso(concurso),
    })


@app.route("/api/cerebro/historico")
def api_cerebro_historico():
    return jsonify({
        "status":   "ok",
        "historico": cerebro.get_historico_ciclos(30),
    })


@app.route("/api/cerebro/backtesting", methods=["POST"])
def api_cerebro_backtesting():
    try:
        dados     = request.get_json() or {}
        n_testes  = int(dados.get("n_testes",   20))
        n_cart    = int(dados.get("n_cartelas",  5))
        resultado = cerebro.backtesting(n_testes, n_cart)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/log")
def api_cerebro_log():
    return jsonify({"log": cerebro.log[-50:]})


# ============================================================
# API — CONFERÊNCIA
# ============================================================

@app.route("/api/conferir", methods=["POST"])
def api_conferir():
    """Confere todas as cartelas pendentes"""
    try:
        resultados = conferencia.conferir_todas_pendentes()
        return jsonify({"status": "ok", "conferidas": len(resultados)})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/conferir_concurso", methods=["POST"])
def api_conferir_concurso():
    """Confere cartelas de um concurso específico"""
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})
        return jsonify(conferencia.conferir_concurso(concurso))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cartelas_concurso/<int:concurso>")
def api_cartelas_concurso(concurso):
    try:
        return jsonify({
            "status":   "ok",
            "cartelas": conferencia.get_cartelas_do_concurso(concurso),
        })
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
            cursor.execute("DELETE FROM cartelas WHERE id = ?", (int(cid),))
            apagadas += cursor.rowcount
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "apagadas": apagadas})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/adicionar_cartelas_concurso", methods=["POST"])
def api_adicionar_cartelas_concurso():
    """Adiciona mais cartelas a um concurso existente via Cérebro"""
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso",   0))
        qtd      = int(dados.get("quantidade", 5))

        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})
        if not (1 <= qtd <= 50):
            return jsonify({"status": "erro", "msg": "Quantidade inválida"})

        cartelas_novas = cerebro.gerar_cartelas(quantidade=qtd)
        adicionadas    = _salvar_cartelas_banco(cartelas_novas, concurso)

        return jsonify({
            "status":     "ok",
            "adicionadas": adicionadas,
            "concurso":   concurso,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# API — PRÊMIOS E AUDITORIA
# ============================================================

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


@app.route("/api/ia_sessao/<int:sessao_id>")
def api_ia_sessao(sessao_id):
    return jsonify(monitor.get_relatorio_sessao(sessao_id))


@app.route("/api/ia_log_tempo_real")
def api_ia_log_tempo_real():
    sessoes = monitor.get_ultimas_sessoes(1)
    if not sessoes:
        return jsonify({"logs": []})
    rel = monitor.get_relatorio_sessao(sessoes[0]["id"])
    return jsonify({"logs": rel.get("modulos", [])})


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║   SISTEMA LOTOFÁCIL — CÉREBRO IA v6.0              ║
║   14 Módulos Analíticos Unificados                  ║
║   Ciclo Autônomo: Geração → Conferência → Aprend.  ║
║   Acesse: http://localhost:5000                      ║
╚══════════════════════════════════════════════════════╝
    """)

    # Status inicial do banco
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0

    if status_sistema["ultimo_concurso"] > 0:
        status_sistema["dados_carregados"] = True
        print("[OK] {} concursos no banco".format(
            status_sistema["ultimo_concurso"]
        ))

    # Cérebro verifica se pode iniciar treinamento automático
    if cerebro.n >= 50:
        print("[CÉREBRO] {} concursos disponíveis para treino".format(
            cerebro.n
        ))
        print("[CÉREBRO] Acesse /cerebro para treinar e gerar cartelas")
    else:
        print("[AVISO] Poucos dados. Carregue o histórico primeiro.")

    status_sistema["ia_treinada"] = cerebro.treinado

    app.run(debug=True, port=5000)