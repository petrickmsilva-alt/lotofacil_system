"""
============================================================
SISTEMA LOTOFÁCIL — CÉREBRO IA v7.0
14 Motores + Oráculo Convergente + Sistema de LOTES
============================================================
"""

# ── Imports padrão ────────────────────────────────────────────
import os
import time
import traceback
import threading
import json
import uuid
from datetime import datetime

import numpy as np

# ── Migração do banco ─────────────────────────────────────────
try:
    from database.migrar import migrar
    migrar()
except Exception as _e:
    print("[AVISO] Migração: {}".format(_e))

# ── Flask ─────────────────────────────────────────────────────
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# ============================================================
# CONVERSOR JSON UNIVERSAL — Trata NumPy, Bytes e Tipos Especiais
# ============================================================
import numpy as np
from flask.json.provider import DefaultJSONProvider


class NumpyJSONProvider(DefaultJSONProvider):
    """JSON provider universal para Flask"""

    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, (bytes, bytearray)):
            try:
                return int(obj)
            except Exception:
                try:
                    return obj.decode('utf-8')
                except Exception:
                    return str(obj)
        return super().default(obj)


app.json = NumpyJSONProvider(app)

# ── Módulos ───────────────────────────────────────────────────
from config import VALOR_APOSTA
from database.db_manager import DBManager
from core.data_loader    import DataLoader
from core.bitmatrix      import BitMatrix
from core.conferencia    import Conferencia
from core.financeiro     import Financeiro
from core.ia_monitor     import IAMonitor
from core.cerebro_ia     import CerebroIA

# ── Instâncias globais ────────────────────────────────────────
db          = DBManager()
data_loader = DataLoader()
bitmatrix   = BitMatrix()
conferencia = Conferencia()
financeiro  = Financeiro()
monitor     = IAMonitor()
cerebro     = CerebroIA(n_cartelas=10)

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
# HELPER: Salvar cartelas em LOTE
# ============================================================

def _salvar_cartelas_banco(cartelas, concurso_alvo, tipo="multiplas",
                             modo="hibrido", grupo_elite=None, cobertura=0):
    if not cartelas:
        return 0

    def to_safe_int(val):
        if hasattr(val, 'item'):
            val = val.item()
        if isinstance(val, (bytes, bytearray)):
            try:
                val = int(val)
            except Exception:
                val = int(val.decode('utf-8'))
        return int(val)

    grupo_elite_limpo = []
    if grupo_elite:
        for g in grupo_elite:
            grupo_elite_limpo.append(to_safe_int(g))

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    lote_id = "{}_{}_{}_{}".format(
        tipo, concurso_alvo, ts, str(uuid.uuid4())[:8]
    )
    custo   = len(cartelas) * VALOR_APOSTA

    try:
        conn   = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lotes_cartelas
            (lote_id, data_criacao, concurso_alvo, tipo_geracao,
             quantidade, custo_total, modo, grupo_elite, cobertura_13)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            lote_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            to_safe_int(concurso_alvo),
            str(tipo),
            len(cartelas),
            float(custo),
            str(modo),
            json.dumps(grupo_elite_limpo),
            float(cobertura),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[LOTE] {}".format(e))

    salvos = 0
    for c in cartelas:
        try:
            dez = c.get("dezenas", [])
            dez_int = [to_safe_int(d) for d in dez]

            if len(dez_int) != 15:
                continue

            conn   = db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cartelas
                (data_geracao, concurso_alvo,
                 d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
                 d11,d12,d13,d14,d15,
                 bitmask, score_ia, score_markov,
                 score_fisico, score_entropia, score_total,
                 lote_id, tipo_geracao)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?,?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                to_safe_int(concurso_alvo),
                dez_int[0],  dez_int[1],  dez_int[2],  dez_int[3],  dez_int[4],
                dez_int[5],  dez_int[6],  dez_int[7],  dez_int[8],  dez_int[9],
                dez_int[10], dez_int[11], dez_int[12], dez_int[13], dez_int[14],
                int(c.get("bitmask", 0)),
                float(c.get("score_total", 0)),
                float(c.get("scores", {}).get("markov",  0)),
                float(c.get("scores", {}).get("verlet",  0)),
                float(c.get("scores", {}).get("ev_prob", 0)),
                float(c.get("score_total", 0)),
                lote_id,
                str(tipo),
            ))
            conn.commit()
            conn.close()
            salvos += 1
        except Exception as e:
            print("[SALVAR] Erro: {}".format(e))

    print("[LOTE] {} cartelas salvas no lote {}".format(salvos, lote_id))
    return salvos


# ============================================================
# PÁGINAS
# ============================================================

@app.route("/")
def index():
    status_sistema["ultimo_concurso"]  = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"]  = db.get_total_concursos() or 0
    status_sistema["dados_carregados"] = status_sistema["ultimo_concurso"] > 0
    status_sistema["ia_treinada"]      = cerebro.treinado

    resumo_fin  = financeiro.get_resumo_geral()
    resumo_conf = conferencia.resumo_conferencia()

    cerebro_status = cerebro.get_status()
    ia_status = {
        "versao":           cerebro_status.get("versao", "7.0"),
        "treinado":         cerebro_status.get("treinado", False),
        "concursos_treino": cerebro_status.get("total_concursos", 0),
        "modulos_ativos":   14,
        "oraculos_ativos":  15,
        "pesos": cerebro_status.get("pesos_modulos", {}),
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
    resultados = db.get_todos_resultados()
    lista = []
    for r in list(resultados)[-100:]:
        try:
            premio_15     = r["premio_15"]     if "premio_15"     in r.keys() else 0
            ganhadores_15 = r["ganhadores_15"] if "ganhadores_15" in r.keys() else 0
        except Exception:
            premio_15     = 0
            ganhadores_15 = 0

        lista.append({
            "concurso":      r["concurso"],
            "data":          r["data"],
            "dezenas":       [r["d{}".format(i)] for i in range(1, 16)],
            "soma":          r["soma"],
            "pares":         r["pares"],
            "premio_15":     float(premio_15 or 0),
            "ganhadores_15": int(ganhadores_15 or 0),
        })
    lista.reverse()
    return render_template("historico.html", resultados=lista)


@app.route("/cerebro", methods=["GET", "POST"])
def cerebro_page():
    cartelas = []
    msg      = ""
    metricas = {}

    if request.method == "POST":
        acao = request.form.get("acao", "gerar")

        if acao == "gerar":
            n_cartelas = int(request.form.get("n_cartelas", 10))
            modo       = request.form.get("modo", "hibrido")
            t0         = time.time()

            try:
                if cerebro.n < 50:
                    msg = "Poucos dados ({}). Carregue o histórico.".format(
                        cerebro.n
                    )
                else:
                    proximo = (db.get_ultimo_concurso() or 0) + 1

                    print("[CEREBRO_PAGE] Gerando {} cartelas para {}...".format(
                        n_cartelas, proximo
                    ))

                    cartelas_geradas = cerebro.gerar_cartelas(
                        quantidade=n_cartelas, modo=modo,
                    )

                    print("[CEREBRO_PAGE] Cartelas geradas: {}".format(
                        len(cartelas_geradas) if cartelas_geradas else 0
                    ))

                    if cartelas_geradas:
                        # SALVAR EM LOTE (essa era a linha problemática)
                        grupo_e = cerebro.decisoes.get("grupo_elite", [])
                        # Converter numpy int64 para int puro
                        grupo_e = [int(x) for x in grupo_e] if grupo_e else []

                        cob = float(cerebro.metricas.get("cobertura_13", 0))

                        print("[CEREBRO_PAGE] Salvando em lote...")

                        salvos = _salvar_cartelas_banco(
                            cartelas_geradas,
                            proximo,
                            tipo="multiplas",
                            modo=modo,
                            grupo_elite=grupo_e,
                            cobertura=cob,
                        )

                        print("[CEREBRO_PAGE] Salvos: {}".format(salvos))

                        cartelas = cartelas_geradas
                        custo    = salvos * VALOR_APOSTA
                        tempo    = time.time() - t0

                        metricas = {
                            "tempo":         round(tempo, 2),
                            "modo":          modo,
                            "grupo_elite":   grupo_e,
                            "cobertura_13":  cob,
                            "concurso_alvo": proximo,
                            "salvos":        salvos,
                            "custo":         custo,
                        }

                        msg = "OK {} cartelas para concurso {} em {:.1f}s | R$ {:.2f}".format(
                            salvos, proximo, tempo, custo
                        )
                    else:
                        msg = "Cérebro não gerou cartelas."
            except Exception as e:
                msg = "Erro: {}".format(str(e))
                traceback.print_exc()

    status  = cerebro.get_status()
    hist    = cerebro.get_historico_ciclos(10)
    modulos = cerebro.get_desempenho_modulos()
    erros   = cerebro.get_memoria_erros()

    return render_template(
        "cerebro.html",
        status    = status,
        historico = hist,
        modulos   = modulos,
        erros     = erros,
        cartelas  = cartelas,
        msg       = msg,
        metricas  = metricas,
    )


@app.route("/api/cerebro/otimas", methods=["POST"])
def api_cerebro_otimas():
    """A DECISÃO do Cérebro: análise completa → estratégia automática →
    cartelas (1 = exaustão do universo; 2–7 = exaustão diversa;
    ≥8 = wheeling com garantia 14) + contabilidade exata do lote."""
    try:
        dados = request.get_json() or {}
        n = int(dados.get("n", 1))
        salvar = bool(dados.get("salvar", False))
        if not (1 <= n <= 100):
            return jsonify({"status": "erro", "msg": "n entre 1 e 100"})
        res = cerebro.gerar_otimas(n_cartelas=n)
        salvos = 0
        if salvar and res["n_cartelas"] > 0:
            concurso = (db.get_ultimo_concurso() or 0) + 1
            salvos = _salvar_cartelas_banco(
                res["cartelas"], concurso,
                tipo="cerebro_otimas", modo=res["estrategia"],
                grupo_elite=res["pool_elite"],
                cobertura=100.0 * res["analise"]["p_melhor_14_mais"],
            )
        return jsonify({"status": "ok", "resultado": res, "salvas": salvos})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/gerar", methods=["GET", "POST"])
def gerar():
    """Geração rápida de cartelas (página server-rendered, auditada Fase 3:
    antes era rota-fantasma que só redirecionava para /cerebro)."""
    if request.method == "POST":
        try:
            quantidade = int(request.form.get("quantidade", 10))
            modo = request.form.get("modo", "hibrido")
            quantidade = max(1, min(50, quantidade))
            t0 = time.time()
            if modo == "cerebro":
                # O CÉREBRO DECIDE: estratégia automática pela quantidade
                res = cerebro.gerar_otimas(n_cartelas=quantidade)
                concurso = (db.get_ultimo_concurso() or 0) + 1
                salvos = _salvar_cartelas_banco(
                    res["cartelas"], concurso,
                    tipo="cerebro_otimas", modo=res["estrategia"],
                    grupo_elite=res["pool_elite"],
                    cobertura=100.0 * res["analise"]["p_melhor_14_mais"],
                )
                a = res["analise"]
                extra = ""
                if res["estrategia"] == "wheeling-garantia-14":
                    extra = (" · garantia 14 se o pool capturar (1 em {:,})"
                             .format(int(res["um_em_captura"]))
                             .replace(",", "."))
                msg = ("✅ Estratégia {} · {} cartela(s) salva(s) para o "
                       "concurso {} · P(lote≥14) = {:.6f}%{} · EV R$ {:.2f}"
                       .format(res["estrategia"], salvos, concurso,
                               100 * a["p_melhor_14_mais"], extra,
                               a["ev_lote"]))
                metricas = {
                    "tempo": res["tempo"],
                    "salvos": salvos,
                    "cobertura_13": a["p_melhor_14_mais"],
                    "custo": res["custo"],
                    "grupo_elite": res["pool_elite"],
                }
                return render_template(
                    "gerar.html", metricas=metricas, cartelas=res["cartelas"],
                    msg=msg,
                )
            cartelas = cerebro.gerar_cartelas(quantidade=quantidade, modo=modo)
            concurso = (db.get_ultimo_concurso() or 0) + 1
            salvos = _salvar_cartelas_banco(
                cartelas, concurso, tipo="multiplas", modo=modo,
                grupo_elite=cerebro.decisoes.get("grupo_elite", []),
                cobertura=cerebro.metricas.get("cobertura_13", 0),
            )
            metricas = {
                "tempo": round(time.time() - t0, 1),
                "salvos": salvos,
                "cobertura_13": cerebro.metricas.get("cobertura_13", 0),
                "custo": round(salvos * VALOR_APOSTA, 2),
                "grupo_elite": cerebro.decisoes.get("grupo_elite", []),
            }
            return render_template(
                "gerar.html", metricas=metricas, cartelas=cartelas,
                msg="✅ {} cartela(s) gerada(s) e salva(s) para o concurso {}"
                    .format(salvos, concurso),
            )
        except Exception as e:
            traceback.print_exc()
            return render_template("gerar.html",
                                   msg="Erro ao gerar: {}".format(e))
    return render_template("gerar.html")


@app.route("/cartela_do_dia")
def cartela_do_dia():
    resultado = cerebro.gerar_cartela_do_dia()

    if resultado.get("status") != "erro":
        try:
            proximo = (db.get_ultimo_concurso() or 0) + 1
            dez     = resultado["cartela"]
            if len(dez) == 15:
                cartela_fmt = {
                    "dezenas":     dez,
                    "bitmask":     int(resultado.get("bitmask", 0)),
                    "score_total": float(resultado.get("consenso_forca", 0)),
                    "scores": {
                        "markov":  0,
                        "verlet":  0,
                        "ev_prob": float(resultado.get("score_cerebro", 0)),
                    },
                }
                _salvar_cartelas_banco(
                    [cartela_fmt],
                    proximo,
                    tipo="cartela_do_dia",
                    modo="oraculo_convergente",
                    grupo_elite=[],
                    cobertura=float(resultado.get("consenso_forca", 0)),
                )
                resultado["salvo_concurso"] = proximo
        except Exception as e:
            resultado["erro_salvar"] = str(e)
            traceback.print_exc()

    hist_cdd = cerebro.get_historico_cartelas_do_dia(10)

    return render_template(
        "cartela_do_dia.html",
        resultado    = resultado,
        historico_cdd = hist_cdd,
    )


@app.route("/conferencia")
def conferencia_page():
    lotes      = conferencia.get_todos_lotes()
    resumo_raw = conferencia.resumo_conferencia()
    resumo = {}
    for pts, dados in resumo_raw.items():
        resumo[pts] = dados if isinstance(dados, dict) \
                      else {"qtd": dados, "total_premio": 0}
    return render_template(
        "conferencia.html",
        lotes  = lotes,
        resumo = resumo,
    )


@app.route("/financeiro_page")
def financeiro_page():
    return render_template(
        "financeiro.html",
        resumo = financeiro.get_resumo_geral(),
    )


@app.route("/api/analise/exaustao", methods=["POST"])
def api_analise_exaustao():
    """Exaustão do universo: pontua TODAS as 3.268.760 combinações contra
    o vetor combinado dos motores (Motor Heavyweight revivido na Fase 3)."""
    try:
        from core.heavyweight_engine import MotorExaustaoUniverso
        dados = request.get_json() or {}
        top_n = max(1, min(int(dados.get("top_n", 10)), 100))
        if not cerebro.treinado:
            cerebro.treinar()
        vetor = cerebro._vetor_combinado()
        motor = MotorExaustaoUniverso()
        t0 = time.time()
        top = motor.top_n(vetor, top_n)
        return jsonify({
            "status": "ok",
            "total": len(motor.universo),
            "tempo": round(time.time() - t0, 2),
            "concursos": cerebro.n,
            "top": top,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/analise")
def analise():
    resultados = db.get_todos_resultados()
    freq       = bitmatrix.heatmap_frequencia(resultados)
    freq_rec   = bitmatrix.heatmap_frequencia(resultados, janela=50)
    heatmap    = {
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
    return render_template(
        "ia_auditoria.html",
        stats           = monitor.get_dashboard_stats(),
        ranking_modulos = monitor.get_ranking_modulos(),
        sessoes         = monitor.get_ultimas_sessoes(10),
        evolucao_pesos  = monitor.get_evolucao_pesos(20),
    )


@app.route("/singularidade")
def singularidade_page():
    return render_template("singularidade.html", status=status_sistema)


# ============================================================
# API — NÚCLEO DE SINGULARIDADE (auditoria cética + evolução)
# ============================================================

@app.route("/api/singularidade/analise")
def api_singularidade_analise():
    """Análise não-convencional completa (banca, cobertura, espectro, filtros)."""
    try:
        from core.singularidade import (
            GestaoDeBanca, CoberturaSteiner, EspectroTemporal,
            TeoriaDaInformacao, FiltrosAvancados, distribuicao_exata,
            probabilidade_13_mais,
        )
        matriz, _ = cerebro._ingestor.carregar_matriz()
        n = len(matriz)

        banca = GestaoDeBanca().relatorio()
        cobertura = CoberturaSteiner().cota_total()

        espectro = EspectroTemporal(matriz)
        hurst = [round(float(espectro.expoente_hurst(matriz[:, d])), 3) for d in range(25)]
        hurst_medio = round(float(np.mean(hurst)), 3)

        info = TeoriaDaInformacao(matriz)
        perm_ent = [round(float(info.entropia_permutacao(matriz[:, d])), 3) for d in range(25)]
        perm_medio = round(float(np.mean(perm_ent)), 3)

        filtros = FiltrosAvancados(matriz)
        ult_dez = [int(x + 1) for x in np.where(matriz[-1] == 1)[0]] if n else []
        rel_filtros = filtros.relatorio(ult_dez) if ult_dez else {}

        return jsonify({
            "status": "ok",
            "concursos": n,
            "probabilidades": {
                "distribuicao": {str(k): round(v, 8) for k, v in distribuicao_exata().items()},
                "p_13_mais": round(probabilidade_13_mais(), 6),
                "cartelas_para_1_em_13": int(round(1 / probabilidade_13_mais())),
            },
            "banca": banca,
            "cobertura_steiner": cobertura,
            "espectro": {
                "hurst_medio": hurst_medio,
                "interpretacao": ("sem memória (sorteio justo)" if abs(hurst_medio - 0.5) < 0.1
                                  else "tendência" if hurst_medio > 0.5 else "anti-persistente"),
                "hurst_por_dezena": hurst,
            },
            "informacao": {
                "entropia_permutacao_media": perm_medio,
                "interpretacao": ("alta ordem temporal (aleatório)" if perm_medio > 0.7
                                  else "alguma estrutura temporal" if perm_medio > 0.5 else "baixa entropia"),
                "entropia_por_dezena": perm_ent,
            },
            "filtros_avancados_ultimo_sorteio": {
                "dezenas": ult_dez,
                "relatorio": rel_filtros,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/singularidade/backtest", methods=["POST"])
def api_singularidade_backtest():
    """Backtesting walk-forward dos 15 oráculos vs baseline aleatória."""
    try:
        dados = request.get_json() or {}
        n_testes = int(dados.get("n_testes", 15))
        n_random = int(dados.get("n_random", 200))
        return jsonify(cerebro.backtesting(n_testes=n_testes, n_cart=5))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# PÁGINA + API — DESDOBRAMENTO COM COBERTURA GARANTIDA (WHEELING)
# ============================================================

@app.route("/wheeling")
def wheeling_page():
    from core.wheeling import MotorWheeling
    return render_template(
        "wheeling.html",
        status=status_sistema,
        menu=MotorWheeling.menu_exato(),
    )


@app.route("/api/cerebro/wheeling", methods=["POST"])
def api_cerebro_wheeling():
    """Pipeline completo: motores → pool → fechamento c/ garantia →
    análise exata. Corpo: {n_pool, garantia, max_cartelas, orcamento,
    salvar, limite_segundos}."""
    try:
        dados = request.get_json() or {}
        n_pool = int(dados.get("n_pool", 17))
        garantia = dados.get("garantia", None)
        max_cartelas = int(dados.get("max_cartelas", 40))
        salvar = bool(dados.get("salvar", False))
        limite = float(dados.get("limite_segundos", 25))

        res = cerebro.pipeline_wheeling(
            n_pool=n_pool, garantia=int(garantia) if garantia else None,
            max_cartelas=max_cartelas,
            orcamento=dados.get("orcamento", None),
            limite_segundos=limite,
        )

        salvos = 0
        lote_id = None
        if salvar and res["n_cartelas"] > 0:
            concurso = (db.get_ultimo_concurso() or 0) + 1
            salvos = _salvar_cartelas_banco(
                res["cartelas"], concurso,
                tipo="wheeling", modo=res["metodo"],
                grupo_elite=res["pool"],
                cobertura=100.0 * (res["analise"]["p_melhor_14_mais"]),
            )
            lote_id = "wheeling_{}".format(concurso)

        return jsonify({
            "status": "ok",
            "resultado": res,
            "salvas": salvos,
            "concurso": (db.get_ultimo_concurso() or 0) + 1,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/wheeling/backtest", methods=["POST"])
def api_cerebro_wheeling_backtest():
    """Walk-forward honesto da taxa de captura do pool."""
    try:
        dados = request.get_json() or {}
        k = int(dados.get("k", 10))
        n_pool = int(dados.get("n_pool", 17))
        if not (1 <= k <= 25):
            return jsonify({"status": "erro", "msg": "k entre 1 e 25"})
        bt = cerebro.backtest_captura(k=k, n_pool=n_pool)
        return jsonify({"status": "ok", "backtest": bt})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# API — DADOS
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
    if status_sistema["carregando"]:
        return jsonify({"status": "info", "msg": "Já carregando..."})

    def _carregar():
        status_sistema["carregando"] = True
        def cb(concurso, carregados, total, msg):
            status_sistema["progresso"] = msg
        resultado = data_loader.carregar_historico_completo(cb)
        status_sistema["carregando"]       = False
        status_sistema["dados_carregados"] = True
        status_sistema["ultimo_concurso"]  = db.get_ultimo_concurso()
        status_sistema["progresso"] = "Completo! {} concursos.".format(
            resultado.get("total_carregados", 0)
        )
        cerebro.matriz, cerebro.raw = cerebro._ingestor.carregar_matriz()
        cerebro.n = len(cerebro.matriz)

    threading.Thread(target=_carregar, daemon=True).start()
    return jsonify({"status": "ok", "msg": "Carregamento iniciado..."})


@app.route("/api/atualizar_dados", methods=["POST"])
def api_atualizar_dados():
    resultado = data_loader.atualizar_diario()
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso()
    cerebro.matriz, cerebro.raw = cerebro._ingestor.carregar_matriz()
    cerebro.n = len(cerebro.matriz)
    return jsonify(resultado)


# ============================================================
# API — CÉREBRO IA
# ============================================================

@app.route("/api/treinar_ia", methods=["POST"])
def api_treinar_ia():
    if status_sistema["treinando"]:
        return jsonify({"status": "info", "msg": "Já treinando..."})

    def _treinar():
        status_sistema["treinando"] = True
        try:
            def cb(msg):
                status_sistema["progresso"] = msg

            cerebro.treinar(callback=cb)
            
            # Atualiza flags de estado
            status_sistema["ia_treinada"] = True
            status_sistema["progresso"]   = "✅ Cérebro treinado com sucesso!"
        except Exception as e:
            status_sistema["progresso"] = "❌ Erro no treino: {}".format(str(e))
            traceback.print_exc()
        
        status_sistema["treinando"] = False

    threading.Thread(target=_treinar, daemon=True).start()
    return jsonify({"status": "ok", "msg": "Treinamento iniciado em background..."})


@app.route("/api/cerebro/status")
def api_cerebro_status():
    return jsonify(cerebro.get_status())


@app.route("/api/cerebro/treinar", methods=["POST"])
def api_cerebro_treinar():
    return api_treinar_ia()


@app.route("/api/cerebro/gerar", methods=["POST"])
def api_cerebro_gerar():
    try:
        dados      = request.get_json() or {}
        quantidade = int(dados.get("quantidade", cerebro.n_cartelas))
        modo       = dados.get("modo", "hibrido")
        concurso   = int(dados.get("concurso", 0))
        if quantidade < 1 or quantidade > 50:
            return jsonify({"status": "erro", "msg": "Quantidade 1-50"})
        if concurso < 1:
            concurso = (db.get_ultimo_concurso() or 0) + 1
        cartelas = cerebro.gerar_cartelas(quantidade=quantidade, modo=modo)
        salvos   = _salvar_cartelas_banco(
            cartelas, concurso,
            tipo="multiplas", modo=modo,
            grupo_elite=cerebro.decisoes.get("grupo_elite", []),
            cobertura=cerebro.metricas.get("cobertura_13", 0),
        )
        return jsonify({
            "status": "ok", "cartelas": cartelas,
            "salvas": salvos, "concurso": concurso,
            "custo": round(salvos * VALOR_APOSTA, 2),
            "metricas": cerebro.metricas,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/ciclo", methods=["POST"])
def api_cerebro_ciclo():
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})
        def _r():
            cerebro.executar_ciclo(concurso)
        threading.Thread(target=_r, daemon=True).start()
        return jsonify({"status": "iniciado", "concurso": concurso})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/loop/iniciar", methods=["POST"])
def api_cerebro_loop_iniciar():
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
    return jsonify({"status": "ok", "fila": cerebro.get_fila_concurso(concurso)})


@app.route("/api/cerebro/historico")
def api_cerebro_historico():
    return jsonify({"status": "ok", "historico": cerebro.get_historico_ciclos(30)})


@app.route("/api/cerebro/backtesting", methods=["POST"])
def api_cerebro_backtesting():
    try:
        dados    = request.get_json() or {}
        n_testes = int(dados.get("n_testes",  20))
        n_cart   = int(dados.get("n_cartelas", 5))
        return jsonify(cerebro.backtesting(n_testes, n_cart))
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/log")
def api_cerebro_log():
    return jsonify({"log": cerebro.log[-50:]})


@app.route("/api/cartela_do_dia")
def api_cartela_do_dia():
    return jsonify(cerebro.gerar_cartela_do_dia())


# ============================================================
# API — CONFERÊNCIA E LOTES
# ============================================================

# ============================================================
# HELPER: Hook financeiro pós-conferência (auditoria Fase 3)
# ============================================================

def _registrar_financeiro(resultado_conf):
    """Alimenta o módulo financeiro após uma conferência bem-sucedida.
    Antes da Fase 3 a tabela `financeiro` ficava eternamente vazia
    porque `registrar_resultado_financeiro` nunca era chamado."""
    try:
        if not isinstance(resultado_conf, dict):
            return None
        if resultado_conf.get("status") != "ok":
            return None
        cartelas = resultado_conf.get("cartelas", [])
        concurso = int(resultado_conf.get("concurso", 0))
        if not cartelas or concurso < 1:
            return None

        # evita duplicar registro no re-conferir do mesmo concurso
        conn = db.get_conn()
        ja_tem = conn.execute(
            "SELECT COUNT(*) FROM financeiro WHERE concurso = ?",
            (concurso,)
        ).fetchone()[0]
        conn.close()
        if ja_tem:
            return None

        premios = resultado_conf.get("premios_oficiais") or {}
        fin = financeiro.registrar_resultado_financeiro(
            concurso, cartelas,
            valor_14=float(premios.get(14) or 0) or None,
            valor_15=float(premios.get(15) or 0) or None,
        )
        print("[FINANCEIRO] concurso {} registrado: lucro R$ {:.2f}"
              .format(concurso, fin.get("lucro", 0)))
        return fin
    except Exception as e:
        print("[FINANCEIRO] erro: {}".format(e))
        return None


@app.route("/api/conferir", methods=["POST"])
def api_conferir():
    try:
        resultados = conferencia.conferir_todas_pendentes()
        for r in resultados:
            _registrar_financeiro(r)
        return jsonify({"status": "ok", "conferidas": len(resultados)})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/conferir_concurso", methods=["POST"])
def api_conferir_concurso():
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Concurso inválido"})
        res = conferencia.conferir_concurso(concurso)
        fin = _registrar_financeiro(res)
        if fin:
            res["financeiro"] = fin
        return jsonify(res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cartelas_concurso/<int:concurso>")
def api_cartelas_concurso(concurso):
    try:
        return jsonify({
            "status": "ok",
            "cartelas": conferencia.get_cartelas_do_concurso(concurso),
        })
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/lotes")
def api_lotes():
    return jsonify({
        "status": "ok",
        "lotes":  conferencia.get_todos_lotes(),
    })


@app.route("/api/lote/<string:lote_id>")
def api_lote(lote_id):
    return jsonify({
        "status":   "ok",
        "cartelas": conferencia.get_cartelas_do_lote(lote_id),
    })


@app.route("/api/apagar_lote", methods=["POST"])
def api_apagar_lote():
    dados   = request.get_json() or {}
    lote_id = dados.get("lote_id", "")
    if not lote_id:
        return jsonify({"status": "erro", "msg": "Lote ID inválido"})
    return jsonify(conferencia.apagar_lote(lote_id))


@app.route("/api/conferir_lote", methods=["POST"])
def api_conferir_lote():
    dados   = request.get_json() or {}
    lote_id = dados.get("lote_id", "")
    if not lote_id:
        return jsonify({"status": "erro", "msg": "Lote ID inválido"})
    res = conferencia.conferir_lote(lote_id)
    fin = _registrar_financeiro(res)
    if fin:
        res["financeiro"] = fin
    return jsonify(res)


@app.route("/api/apagar_cartelas_concurso", methods=["POST"])
def api_apagar_cartelas_concurso():
    try:
        dados    = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        if concurso < 1:
            return jsonify({"status": "erro", "msg": "Inválido"})
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
            return jsonify({"status": "erro", "msg": "Nenhum ID"})
        conn   = db.get_conn()
        cursor = conn.cursor()
        apagadas = 0
        for cid in ids:
            cursor.execute("DELETE FROM cartelas WHERE id=?", (int(cid),))
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
            return jsonify({"status": "erro", "msg": "Inválido"})
        if not (1 <= qtd <= 50):
            return jsonify({"status": "erro", "msg": "Qtd inválida"})
        novas       = cerebro.gerar_cartelas(quantidade=qtd)
        adicionadas = _salvar_cartelas_banco(
            novas, concurso,
            tipo="multiplas", modo="hibrido",
            grupo_elite=cerebro.decisoes.get("grupo_elite", []),
            cobertura=cerebro.metricas.get("cobertura_13", 0),
        )
        return jsonify({"status": "ok", "adicionadas": adicionadas,
                        "concurso": concurso})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# API — PRÊMIOS
# ============================================================

@app.route("/api/premios/<int:concurso>")
def api_premios_concurso(concurso):
    row = db.get_premios_concurso(concurso)
    if not row:
        return jsonify({"status": "erro", "msg": "Não encontrado"})
    return jsonify({
        "status": "ok", "concurso": concurso,
        "premio_11": row["premio_11"], "premio_12": row["premio_12"],
        "premio_13": row["premio_13"], "premio_14": row["premio_14"],
        "premio_15": row["premio_15"], "ganhadores_15": row["ganhadores_15"],
    })


@app.route("/api/atualizar_premios_todos", methods=["POST"])
def api_atualizar_premios_todos():
    """Busca prêmios reais dos últimos 100 concursos da Caixa"""
    try:
        conn   = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT concurso FROM resultados
            ORDER BY concurso DESC LIMIT 100
        """)
        concursos = [r[0] for r in cursor.fetchall()]
        conn.close()

        atualizados = 0
        erros       = 0

        for c in concursos:
            try:
                dados_caixa = conferencia.buscar_premios_caixa(c)
                if dados_caixa:
                    conferencia._atualizar_premios_banco(c, dados_caixa)
                    atualizados += 1
                    print("[PREMIOS] {} atualizado".format(c))
                else:
                    erros += 1
                time.sleep(0.3)
            except Exception as e:
                print("[PREMIOS] erro {}: {}".format(c, e))
                erros += 1

        return jsonify({
            "status":      "ok",
            "atualizados": atualizados,
            "erros":       erros,
            "total":       len(concursos),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# API — AUDITORIA
# ============================================================

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
# INICIALIZAÇÃO DO SERVIDOR
# ============================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║   SISTEMA LOTOFÁCIL — CÉREBRO IA v7.0              ║
║   14 Motores + 15 Oráculos Convergentes             ║
║   Sistema de LOTES independentes                    ║
║   Acesse: http://localhost:5000                      ║
╚══════════════════════════════════════════════════════╝
    """)

    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0

    if status_sistema["ultimo_concurso"] > 0:
        status_sistema["dados_carregados"] = True
        print("[OK] {} concursos no banco".format(
            status_sistema["ultimo_concurso"]
        ))

    if cerebro.n >= 50:
        print("[CÉREBRO] {} concursos disponíveis".format(cerebro.n))
        print("[ORÁCULO] 15 oráculos convergentes ativos")
    else:
        print("[AVISO] Carregue o histórico primeiro")

    status_sistema["ia_treinada"] = cerebro.treinado

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)