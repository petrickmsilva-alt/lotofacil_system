"""
============================================================
SISTEMA LOTOFÁCIL — INTELIGÊNCIA MAGNA v9.0
Uma memória + uma análise + uma decisão auditável
============================================================
"""

# ── Imports padrão ────────────────────────────────────────────
import os
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
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
)

app = Flask(__name__)

# ============================================================
# CONVERSOR JSON UNIVERSAL — Trata NumPy, Bytes e Tipos Especiais
# ============================================================
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
from core.cerebro_ia     import InteligenciaMagna
from core.caixa_client    import CaixaClient

# ── Instâncias globais ────────────────────────────────────────
db           = DBManager()
caixa_client = CaixaClient()
data_loader  = DataLoader(client=caixa_client)
bitmatrix    = BitMatrix()
conferencia  = Conferencia(client=caixa_client)
financeiro   = Financeiro()
magna        = InteligenciaMagna(n_cartelas=10, client=caixa_client)
# Compatibilidade interna temporária: rotas legadas passam a delegar à mesma
# instância. Nenhum segundo cérebro é criado.
cerebro     = magna

# ── Status global ─────────────────────────────────────────────
status_sistema = {
    "dados_carregados": False,
    "ia_treinada":      False,
    "ultimo_concurso":  0,
    "total_concursos":  0,
    "progresso":        "",
    "carregando":       False,
    "treinando":        False,
    "ultima_atualizacao": None,
    "erro_atualizacao": None,
}
historico_lock = threading.Lock()


@app.context_processor
def inject_status():
    """Disponibiliza `status` em TODOS os templates, inclusive nas páginas
    que antes não o passavam (wheeling, singularidade, avaliacao etc.),
    evitando que o indicador da sidebar mostrasse 'IA: Offline / 0 concursos'
    só porque a rota esqueceu de passar a variável."""
    return {"status": status_sistema}


# ============================================================
# HELPER: Salvar cartelas em LOTE
# ============================================================

def _salvar_cartelas_banco(cartelas, concurso_alvo, tipo="magna",
                             modo="decisao_unica", grupo_elite=None,
                             cobertura=0):
    """Persiste um lote completo de forma atômica.

    A Inteligência Magna entrega uma única decisão; portanto o cabeçalho e todas
    as cartelas dessa decisão devem existir juntos. O fluxo antigo commitava o
    lote e depois cada cartela em conexões diferentes, criando lotes parciais ou
    órfãos quando qualquer INSERT falhava.
    """
    if not cartelas:
        return 0

    def to_safe_int(val):
        if hasattr(val, "item"):
            val = val.item()
        if isinstance(val, (bytes, bytearray, memoryview)):
            raw = bytes(val)
            try:
                return int(raw.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                if len(raw) in (1, 2, 4, 8):
                    return int.from_bytes(raw, "little", signed=True)
                raise ValueError("BLOB inteiro inválido")
        return int(val)

    # Valida tudo antes de abrir a transação. Nenhuma dezena NumPy/BLOB volta a
    # ser persistida como binário e nenhuma cartela inválida entra no lote.
    cartelas_limpas = []
    for cartela in cartelas:
        try:
            dezenas = sorted(to_safe_int(d) for d in cartela.get("dezenas", []))
            if (len(dezenas) != 15 or len(set(dezenas)) != 15 or
                    any(d < 1 or d > 25 for d in dezenas)):
                continue
            cartelas_limpas.append((cartela, dezenas))
        except (TypeError, ValueError, OverflowError):
            continue

    if not cartelas_limpas:
        return 0

    grupo_elite_limpo = sorted({
        to_safe_int(g) for g in (grupo_elite or [])
        if 1 <= to_safe_int(g) <= 25
    })
    agora = datetime.now()
    ts = agora.strftime("%Y%m%d_%H%M%S")
    criado_em = agora.strftime("%Y-%m-%d %H:%M:%S")
    lote_id = "{}_{}_{}_{}".format(
        tipo, concurso_alvo, ts, str(uuid.uuid4())[:8]
    )
    custo = len(cartelas_limpas) * VALOR_APOSTA

    conn = db.get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lotes_cartelas
            (lote_id, data_criacao, concurso_alvo, tipo_geracao,
             quantidade, custo_total, modo, grupo_elite, cobertura_13)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            lote_id, criado_em, to_safe_int(concurso_alvo), str(tipo),
            len(cartelas_limpas), float(custo), str(modo),
            json.dumps(grupo_elite_limpo), float(cobertura),
        ))

        for cartela, dezenas in cartelas_limpas:
            scores = cartela.get("scores") or {}
            bitmask_cartela = int(cartela.get("bitmask") or
                                  bitmatrix.dezenas_para_bitmask(dezenas))
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
                criado_em, to_safe_int(concurso_alvo), *dezenas,
                bitmask_cartela,
                float(cartela.get("score_total", 0)),
                float(scores.get("markov", 0)),
                float(scores.get("verlet", 0)),
                float(scores.get("ev_prob", 0)),
                float(cartela.get("score_total", 0)),
                lote_id, str(tipo),
            ))

        conn.commit()
        salvos = len(cartelas_limpas)
        print("[MAGNA] {} cartelas salvas atomicamente no lote {}".format(
            salvos, lote_id))
        return salvos
    except Exception as exc:
        conn.rollback()
        print("[MAGNA] Falha ao salvar lote (rollback): {}".format(exc))
        return 0
    finally:
        conn.close()


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
        "versao":           cerebro_status.get("versao", "9.0"),
        "treinado":         cerebro_status.get("treinado", False),
        "concursos_treino": cerebro_status.get("total_concursos", 0),
        "fontes_assimiladas": len(magna.pesos_fontes_magna),
        "pesos": dict(magna.pesos_fontes_magna),
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
    return render_template(
        "historico.html", resultados=lista,
        status_base=data_loader.get_status_base(),
    )


@app.route("/cerebro")
def cerebro_page():
    """Painel único da Inteligência Magna.

    Não há mais submódulos ou abas que tomam decisões próprias. Todos os
    instrumentos analíticos são assimilados por `decidir_e_gerar()` e a página
    exibe somente a conclusão unificada e sua memória auditável.
    """
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0
    status_sistema["dados_carregados"] = status_sistema["ultimo_concurso"] > 0
    status_sistema["ia_treinada"] = magna.treinado
    return render_template(
        "cerebro.html",
        status=status_sistema,
        magna_status=magna.get_status(),
        historico_magna=magna.get_historico_magna(12),
        valor_aposta=VALOR_APOSTA,
    )


@app.route("/cerebro/central", methods=["GET", "POST"])
def cerebro_central():
    """Compatibilidade: a antiga cabine foi absorvida pela Inteligência Magna."""
    return redirect(url_for("cerebro_page"), code=303)


def _responder_decisao_magna(dados):
    quantidade = int(dados.get("quantidade", dados.get("n", 1)))
    salvar = bool(dados.get("salvar", True))
    orcamento = dados.get("orcamento")
    resultado = magna.decidir_e_gerar(
        quantidade=quantidade,
        orcamento=orcamento,
        registrar=salvar,
    )
    salvos = 0
    if salvar and resultado["n_cartelas"] > 0:
        salvos = _salvar_cartelas_banco(
            resultado["cartelas"], resultado["concurso_alvo"],
            tipo="inteligencia_magna", modo=resultado["estrategia"],
            grupo_elite=resultado["pool_elite"],
            cobertura=resultado["analise"]["p_melhor_14_mais"],
        )
    return {
        "status": "ok",
        "resultado": resultado,
        "salvas": salvos,
        "concurso": resultado["concurso_alvo"],
    }


@app.route("/api/magna/decidir", methods=["POST"])
def api_magna_decidir():
    """Única porta pública de análise, interpretação e criação de cartelas."""
    try:
        return jsonify(_responder_decisao_magna(request.get_json() or {}))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


# ============================================================
# API — FÍSICA DO SORTEIO (Perfil das Bolas + Ambiente)
# ============================================================

@app.route("/api/magna/fisica")
def api_magna_fisica():
    """Retorna o estado atual da fonte física da Magna."""
    try:
        return jsonify({
            "status": "ok",
            "fisica": magna.fisica.get_status(),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/fisica/bola", methods=["POST"])
def api_magna_fisica_bola():
    """Registra ou atualiza o perfil físico de uma bola."""
    try:
        dados = request.get_json() or {}
        numero = int(dados.get("numero", 0))
        if not 1 <= numero <= 25:
            return jsonify({"status": "erro", "msg": "numero deve estar entre 1 e 25"}), 400
        resultado = magna.fisica.registrar_bola(
            numero=numero,
            massa_g=dados.get("massa_g"),
            diametro_mm=dados.get("diametro_mm"),
            cor=dados.get("cor"),
            rugosidade=dados.get("rugosidade"),
            coef_restituicao=dados.get("coef_restituicao"),
            ciclos_uso=int(dados.get("ciclos_uso", 0)),
        )
        return jsonify({"status": "ok", "bola": resultado})
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/fisica/ambiente", methods=["POST"])
def api_magna_fisica_ambiente():
    """Registra as condições ambientais de um sorteio."""
    try:
        dados = request.get_json() or {}
        resultado = magna.fisica.registrar_ambiente(
            concurso=dados.get("concurso"),
            maquina=dados.get("maquina", "padrao"),
            conjunto_bolas=dados.get("conjunto_bolas", "A"),
            temperatura_K=dados.get("temperatura_K"),
            pressao_atm=dados.get("pressao_atm"),
            umidade=dados.get("umidade"),
            densidade_ar=dados.get("densidade_ar"),
            gravidade=dados.get("gravidade"),
            velocidade_rotacao=dados.get("velocidade_rotacao", 30.0),
            duracao_mistura=dados.get("duracao_mistura", 60.0),
            data_ultima_manutencao=dados.get("data_ultima_manutencao"),
        )
        return jsonify({"status": "ok", "ambiente": resultado})
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/cerebro/otimas", methods=["POST"])
def api_cerebro_otimas():
    """Alias legado: delega à mesma e única Inteligência Magna."""
    return api_magna_decidir()


@app.route("/gerar", methods=["GET", "POST"])
def gerar():
    """A geração separada foi absorvida pela Inteligência Magna."""
    return redirect(url_for("cerebro_page"), code=303)


@app.route("/cartela_do_dia")
def cartela_do_dia():
    """O consenso diário agora é uma fonte interna da decisão Magna."""
    return redirect(url_for("cerebro_page"), code=303)


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
    """Alias legado: exaustão também passa pela decisão integrada da Magna."""
    try:
        dados = request.get_json() or {}
        return jsonify(_responder_decisao_magna({
            "quantidade": max(1, min(int(dados.get("top_n", 1)), 7)),
            "salvar": False,
        }))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/analise")
def analise():
    """A análise histórica foi assimilada pela decisão Magna."""
    return redirect(url_for("cerebro_page"), code=303)


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
    """A auditoria agora acompanha cada decisão no painel único."""
    return redirect(url_for("cerebro_page"), code=303)


@app.route("/singularidade")
def singularidade_page():
    """A interpretação cética foi assimilada pela decisão Magna."""
    return redirect(url_for("cerebro_page"), code=303)


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
        return jsonify(cerebro.backtesting(
            n_testes=n_testes, n_random=n_random))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# PÁGINA + API — DESDOBRAMENTO COM COBERTURA GARANTIDA (WHEELING)
# ============================================================

@app.route("/wheeling")
def wheeling_page():
    """O fechamento é escolhido internamente pela Inteligência Magna."""
    return redirect(url_for("cerebro_page"), code=303)


@app.route("/api/cerebro/wheeling", methods=["POST"])
def api_cerebro_wheeling():
    """Alias legado: a Magna decide se o wheeling é a estratégia adequada."""
    try:
        dados = request.get_json() or {}
        dados["quantidade"] = int(dados.get("quantidade", 8))
        return jsonify(_responder_decisao_magna(dados))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/cerebro/wheeling/backtest", methods=["POST"])
def api_cerebro_wheeling_backtest():
    """Walk-forward honesto da taxa de captura do pool."""
    try:
        dados = request.get_json() or {}
        k = int(dados.get("k", 10))
        n_pool = int(dados.get("n_pool", 17))
        if not (1 <= k <= 25):
            return jsonify({"status": "erro", "msg": "k entre 1 e 25"})
        with magna._magna_lock:
            bt = magna.backtest_captura(k=k, n_pool=n_pool)
        return jsonify({"status": "ok", "backtest": bt})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# AVALIAÇÃO DO DESDOBRAMENTO (página própria da main, preservada)
# ============================================================

def _criar_tabela_avaliacao():
    conn = db.get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avaliacao_desdobramento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso INTEGER,
            data TEXT,
            grupo TEXT,
            v INTEGER,
            t INTEGER,
            acertou_grupo INTEGER DEFAULT 0,
            dezenas_escaparam INTEGER DEFAULT 0,
            dezenas_fora TEXT,
            melhor_acerto INTEGER DEFAULT 0,
            observacao TEXT
        )
    """)
    conn.commit()
    conn.close()


@app.route("/avaliacao")
def avaliacao_page():
    return render_template("avaliacao.html", status=status_sistema)


@app.route("/api/avaliacao", methods=["POST"])
def api_avaliacao_registrar():
    """
    Registra a avaliação de um desdobramento para um concurso.
    Busca o resultado real no banco e calcula automaticamente
    se o grupo acertou (as 15 dentro) e quantas dezenas escaparam.
    """
    try:
        _criar_tabela_avaliacao()
        dados = request.get_json() or {}
        concurso = int(dados.get("concurso", 0))
        grupo = sorted({int(x) for x in dados.get("grupo", []) if x not in (None, "")})
        t = int(dados.get("t", 13))
        observacao = str(dados.get("observacao", ""))

        if concurso < 1 or not grupo:
            return jsonify({"status": "erro",
                            "msg": "Informe o concurso e o grupo de dezenas."})

        res = db.get_resultado_concurso(concurso)
        if not res:
            return jsonify({"status": "erro",
                            "msg": "Concurso {} não está no banco. Atualize os dados primeiro."
                                   .format(concurso)})

        sorteadas = [int(res["d{}".format(i)]) for i in range(1, 16)]
        gset, sset = set(grupo), set(sorteadas)
        acertos = len(gset & sset)
        fora = sorted(sset - gset)
        escaparam = len(fora)
        acertou = 1 if escaparam == 0 else 0
        melhor_acerto = 15 - escaparam

        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO avaliacao_desdobramento
            (concurso, data, grupo, v, t, acertou_grupo, dezenas_escaparam,
             dezenas_fora, melhor_acerto, observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            concurso, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(grupo), len(grupo), t, acertou, escaparam,
            json.dumps(fora), melhor_acerto, observacao,
        ))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "ok",
            "registro": {
                "concurso": concurso, "grupo": grupo, "sorteadas": sorteadas,
                "acertos": acertos, "acertou_grupo": bool(acertou),
                "dezenas_escaparam": escaparam, "dezenas_fora": fora,
                "melhor_acerto": melhor_acerto,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/avaliacao", methods=["GET"])
def api_avaliacao_listar():
    """Lista as avaliações + estatísticas agregadas (taxa de acerto do grupo)."""
    try:
        _criar_tabela_avaliacao()
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM avaliacao_desdobramento "
                       "ORDER BY id DESC LIMIT 200")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        registros = []
        for r in rows:
            try:
                r["grupo"] = json.loads(r.get("grupo") or "[]")
            except Exception:
                r["grupo"] = []
            try:
                r["dezenas_fora"] = json.loads(r.get("dezenas_fora") or "[]")
            except Exception:
                r["dezenas_fora"] = []
            registros.append(r)

        total = len(registros)
        acertos = sum(1 for r in registros if r.get("acertou_grupo"))
        taxa = round(acertos / total * 100, 1) if total else 0.0
        escapadas = [r.get("dezenas_escaparam", 0) for r in registros]
        media_escap = round(float(np.mean(escapadas)), 2) if escapadas else 0.0

        return jsonify({
            "status": "ok",
            "registros": registros,
            "stats": {
                "total": total,
                "acertos_grupo": acertos,
                "taxa_acerto_pct": taxa,
                "media_dezenas_escaparam": media_escap,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(e)})


# ============================================================
# API — DADOS
# ============================================================

@app.route("/api/status")
def api_status():
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0
    status_sistema["ia_treinada"] = cerebro.treinado
    if status_sistema["ultima_atualizacao"] is None:
        status_sistema["ultima_atualizacao"] = (
            data_loader.get_status_base().get("ultima_atualizacao")
        )
    return jsonify(status_sistema)


@app.route("/api/status_base")
def api_status_base():
    return jsonify(data_loader.get_status_base())


def _iniciar_sincronizacao_historico(completo=False):
    with historico_lock:
        if status_sistema["carregando"]:
            return False
        # A flag é ligada antes da thread para impedir duas atualizações na
        # janela entre a resposta HTTP e o início do trabalho.
        status_sistema["carregando"] = True
        status_sistema["erro_atualizacao"] = None
        status_sistema["progresso"] = "Iniciando sincronização do histórico..."

    def executar():
        try:
            def callback(concurso, carregados, total, mensagem):
                status_sistema["progresso"] = mensagem

            resultado = (
                data_loader.carregar_historico_completo(callback)
                if completo else data_loader.atualizar_diario()
            )
            status_sistema["ultima_atualizacao"] = resultado
            status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
            status_sistema["total_concursos"] = db.get_total_concursos() or 0
            status_sistema["dados_carregados"] = (
                status_sistema["total_concursos"] > 0
            )
            status_sistema["progresso"] = resultado.get(
                "msg", "Sincronização concluída")
            if resultado.get("status") in ("erro", "parcial"):
                status_sistema["erro_atualizacao"] = resultado.get("msg")

            # Troca a matriz de forma atômica em relação às decisões. Novos
            # concursos invalidam o treino anterior e exigem nova assimilação.
            with magna._magna_lock:
                magna.matriz, magna.raw = magna._ingestor.carregar_matriz()
                magna.n = len(magna.matriz)
                if resultado.get("novos") or resultado.get("recuperados"):
                    magna.treinado = False
                    status_sistema["ia_treinada"] = False
        except Exception as exc:
            traceback.print_exc()
            status_sistema["erro_atualizacao"] = str(exc)
            status_sistema["progresso"] = "Erro ao atualizar: {}".format(exc)
            status_sistema["ultima_atualizacao"] = {
                "status": "erro", "msg": str(exc)
            }
        finally:
            with historico_lock:
                status_sistema["carregando"] = False

    threading.Thread(target=executar, daemon=True).start()
    return True


@app.route("/api/carregar_dados", methods=["POST"])
def api_carregar_dados():
    if not _iniciar_sincronizacao_historico(completo=True):
        return jsonify({"status": "info", "msg": "Sincronização já em andamento"}), 409
    return jsonify({
        "status": "iniciado", "msg": "Carga e reparação do histórico iniciadas"
    }), 202


@app.route("/api/atualizar_dados", methods=["POST"])
def api_atualizar_dados():
    if not _iniciar_sincronizacao_historico(completo=False):
        return jsonify({"status": "info", "msg": "Sincronização já em andamento"}), 409
    return jsonify({
        "status": "iniciado", "msg": "Busca incremental iniciada"
    }), 202


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

            with magna._magna_lock:
                magna.treinar(callback=cb)

            # Atualiza flags de estado
            status_sistema["ia_treinada"] = True
            status_sistema["progresso"]   = "✅ Memória da Inteligência Magna assimilada com sucesso!"
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
    """Alias legado da decisão única da Inteligência Magna."""
    try:
        dados = request.get_json() or {}
        dados["quantidade"] = int(dados.get("quantidade", magna.n_cartelas))
        return jsonify(_responder_decisao_magna(dados))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


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
        n_random = int(dados.get("n_random", 200))
        return jsonify(cerebro.backtesting(
            n_testes=n_testes, n_random=n_random))
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)})


@app.route("/api/cerebro/log")
def api_cerebro_log():
    return jsonify({"log": cerebro.log[-50:]})


@app.route("/api/cartela_do_dia")
def api_cartela_do_dia():
    """Endpoint removido: nenhuma fonte interna pode gerar isoladamente."""
    return jsonify({
        "status": "substituido",
        "msg": "Use POST /api/magna/decidir para a decisão única.",
        "nova_rota": "/api/magna/decidir",
    }), 410


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
        if concurso < 1:
            return None

        # O resultado fecha a memória única antes da contabilização financeira.
        # A operação é idempotente: apenas decisões `aguardando` são aprendidas.
        dezenas_reais = resultado_conf.get("resultado", [])
        if len(dezenas_reais) == 15:
            aprendizado = magna.aprender_resultado_magna(
                concurso, dezenas_reais)
            resultado_conf["aprendizado_magna"] = aprendizado

        if not cartelas:
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
        total_cartelas = 0
        for r in resultados:
            _registrar_financeiro(r)
            total_cartelas += len(r.get("cartelas", []))
        return jsonify({
            "status": "ok",
            "concursos": len(resultados),
            "conferidas": total_cartelas,
        })
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
    """Bloqueia geração paralela fora da memória única."""
    return jsonify({
        "status": "substituido",
        "msg": "Novas cartelas só podem ser decididas pela Inteligência Magna.",
        "nova_rota": "/api/magna/decidir",
    }), 410



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
    """Atualiza rateios recentes sem zerar dados quando só há contingência."""
    try:
        conn = db.get_conn()
        concursos = [r[0] for r in conn.execute("""
            SELECT concurso FROM resultados
            ORDER BY concurso DESC LIMIT 100
        """).fetchall()]
        conn.close()
        resultado = conferencia.atualizar_premios_concursos(concursos)
        codigo = 200 if resultado["status"] in ("ok", "parcial") else 503
        return jsonify(resultado), codigo
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


# ============================================================
# API — AUDITORIA
# ============================================================

@app.route("/api/ia_sessao/<int:sessao_id>")
def api_ia_sessao(sessao_id):
    return jsonify({
        "status": "substituido",
        "msg": "A auditoria agora pertence à decisão Magna.",
        "decisao_id": sessao_id,
    }), 410


@app.route("/api/ia_log_tempo_real")
def api_ia_log_tempo_real():
    return jsonify({
        "status": "substituido",
        "msg": "Consulte a memória única em /cerebro.",
        "logs": [],
    }), 410



# ============================================================
# INICIALIZAÇÃO DO SERVIDOR
# ============================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║   LOTOFÁCIL — INTELIGÊNCIA MAGNA v9.0              ║
║   Uma memória + uma análise + uma decisão           ║
║   Criação unificada e auditável                     ║
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

    host = os.getenv("LOTOFACIL_HOST", "127.0.0.1")
    port = int(os.getenv("LOTOFACIL_PORT", "5000"))
    debug = os.getenv("LOTOFACIL_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug, use_reloader=False)