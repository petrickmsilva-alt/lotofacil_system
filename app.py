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
    """O Dashboard foi absorvido: a entrada do sistema é a Inteligência Magna."""
    return redirect(url_for("cerebro_page"), code=303)


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
    from core.fisica_sorteio import CORES_RGB
    status_sistema["ultimo_concurso"] = db.get_ultimo_concurso() or 0
    status_sistema["total_concursos"] = db.get_total_concursos() or 0
    status_sistema["dados_carregados"] = status_sistema["ultimo_concurso"] > 0
    status_sistema["ia_treinada"] = magna.treinado
    
    # Calcular estatísticas de avaliação
    historico = magna.get_historico_magna(50)
    conferidas = [d for d in historico if d.get('status') == 'conferida']
    media_acertos = sum(d.get('media_acertos', 0) for d in conferidas) / len(conferidas) if conferidas else 0
    melhor_acertos = max((d.get('melhor_acertos', 0) for d in conferidas), default=0)
    
    return render_template(
        "cerebro.html",
        status=status_sistema,
        magna_status=magna.get_status(),
        historico_magna=historico,
        valor_aposta=VALOR_APOSTA,
        pesos=magna.pesos_fontes_magna,
        bolas=magna.fisica.get_bolas(),
        cores_rgb=CORES_RGB,
        media_acertos=round(media_acertos, 1),
        melhor_acertos=melhor_acertos,
        retencao=magna.get_retencao(8),
    )


@app.route("/cerebro/central", methods=["GET", "POST"])
def cerebro_central():
    """Compatibilidade: a antiga cabine foi absorvida pela Inteligência Magna."""
    return redirect(url_for("cerebro_page"), code=303)


def _responder_decisao_magna(dados):
    quantidade = int(dados.get("quantidade", dados.get("n", 1)))
    salvar = bool(dados.get("salvar", True))
    orcamento = dados.get("orcamento")
    alvo = dados.get("alvo")
    if alvo not in (None, "", 13, 14, 15, "13", "14", "15"):
        raise ValueError("alvo deve ser 13, 14 ou 15 (ou ausente)")
    alvo = int(alvo) if alvo not in (None, "") else None
    modo = dados.get("modo")
    if modo not in (None, "", "auto", "forja", "suprema"):
        raise ValueError("modo deve ser 'auto', 'forja' ou 'suprema'")
    modo = modo or None
    # Suprema é a via pessoal em potência máxima
    if modo == "suprema":
        resultado = magna.decidir_suprema(
            quantidade=quantidade,
            orcamento=float(orcamento or 100.0),
            alvo=int(alvo or 13),
            modo="suprema",
            registrar=salvar,
        )
    else:
        resultado = magna.decidir_e_gerar(
            quantidade=quantidade,
            orcamento=orcamento,
            registrar=salvar,
            alvo=alvo,
            modo=modo,
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
    """Única porta pública de análise, interpretação e criação de cartelas.

    v12.0 — a Magna é autônoma: o usuário só informa o limite (quantidade e,
    opcionalmente, orçamento). Ela mesma, sem comandos manuais:
      • retém a base histórica inteira e reassimila o próprio acervo;
      • calibra os pesos das fontes em walk-forward (no boot e após cada
        sorteio, via calibração autônoma);
      • percebe o ambiente do sorteio (telemetria INMET do local + registro
        do ambiente físico + condições de clima) — o antigo "Registrar
        Ambiente" e a "Forja automática" são passos internos;
      • decide SOZINHA se forja espacialmente (lotes grandes) ou se usa a
        escada de captura nativa / exaustão (lotes pequenos).

    Campos opcionais do corpo:
      alvo: 13 | 14 | 15 — escada de captura condicional;
      modo: reservado/compatibilidade — quando ausente, a própria Magna
            escolhe entre forja espacial e estratégia nativa.
    """
    try:
        return jsonify(_responder_decisao_magna(request.get_json() or {}))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/pre-cartelas", methods=["GET"])
def api_magna_pre_cartelas():
    """Relatório de TUDO que a Inteligência Magna processa ANTES de gerar.

    v12.1 — roda o pipeline de pré-processamento completo (treino, acervo
    de abertura e cores, percepção de ambiente INMET/clima/física, regime,
    fontes assimiladas, consenso do vetor, memória episódica, anti-
    popularidade e rota extraordinária) SEM gerar nenhuma cartela e devolve
    a trilha auditável, etapa por etapa, com duração e detalhes.

    Query opcional: ?quantidade=1&alvo=13|14|15&modo=auto|forja&orcamento=50
    """
    try:
        args = request.args
        quantidade = int(args.get("quantidade", 1))
        alvo = args.get("alvo") or None
        if alvo not in (None, "", 13, 14, 15, "13", "14", "15"):
            return jsonify({"status": "erro",
                            "msg": "alvo deve ser 13, 14 ou 15"}), 400
        alvo = int(alvo) if alvo not in (None, "") else None
        modo = args.get("modo") or None
        if modo not in (None, "", "auto", "forja"):
            return jsonify({"status": "erro",
                            "msg": "modo deve ser 'auto' ou 'forja'"}), 400
        orcamento = args.get("orcamento")
        orcamento = float(orcamento) if orcamento not in (None, "") else None
        concurso = args.get("concurso")
        concurso = int(concurso) if concurso not in (None, "") else None
        relatorio = magna.relatorio_pre_cartelas(
            quantidade=quantidade, orcamento=orcamento, alvo=alvo,
            modo=modo, concurso_alvo=concurso)
        return jsonify({"status": "ok", "relatorio": relatorio,
                        "markdown": relatorio.get("markdown", "")})
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/suprema", methods=["POST"])
def api_magna_suprema():
    """MAGNA SUPREMA v11 — Sistema único pessoal em potência máxima, sem erros.

    Evoluções completas:
    - EWC continual, meta por regime, clustering adaptativo, balança 0.001g
    - Perfil risco pessoal, MCTS pool, multi-rota 60/30/10, utilidade esperada prêmios reais
    - Juiz 9 critérios + adversarial + NIST + p-value + juiz que aprende
    - Explainability LLM, fingerprint SHA256, backtest 50, binomial, curva

    Único gerador Magna para decisão única e 3 âncoras.
    """
    try:
        dados = request.get_json() or {}
        quantidade = int(dados.get("quantidade", dados.get("n", 8)))
        orcamento = float(dados.get("orcamento", 100.0))
        alvo = int(dados.get("alvo", 13))
        modo = dados.get("modo", "suprema")
        perfil = dados.get("perfil", "equilibrado")
        segundos = float(dados.get("segundos_forja", dados.get("segundos", 30.0)))
        salvar = bool(dados.get("salvar", True))
        resultado = magna.decidir_suprema(
            quantidade=quantidade,
            orcamento=orcamento,
            alvo=alvo,
            modo=modo,
            perfil=perfil,
            segundos_forja=segundos,
            usar_mcts=bool(dados.get("usar_mcts", True)),
            usar_multi_rota=bool(dados.get("usar_multi_rota", False)),
            tentativas_juiz=int(dados.get("tentativas_juiz", 2)),
            registrar=salvar,
        )
        salvos = 0
        if salvar and resultado["n_cartelas"] > 0:
            salvos = _salvar_cartelas_banco(
                resultado["cartelas"], resultado["concurso_alvo"],
                tipo="magna_suprema", modo=resultado["estrategia"],
                grupo_elite=resultado["pool_elite"],
                cobertura=resultado["analise"]["p_melhor_14_mais"],
            )
        return jsonify({
            "status": "ok",
            "resultado": resultado,
            "salvas": salvos,
            "concurso": resultado["concurso_alvo"],
        })
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/regime")
def api_magna_regime():
    """Detecta regime atual K-means adaptativo."""
    try:
        # tenta adaptativo
        try:
            from core.magna_suprema import DetectorRegime
            det = DetectorRegime(magna.matriz)
            regime = det.detectar_adaptativo(janela=100)
        except Exception:
            regime = magna.detectar_regime_atual()
        return jsonify({"status": "ok", "regime": regime})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/verificar", methods=["POST"])
def api_magna_verificar():
    """Verificação exaustiva + backtest + binomial + curva."""
    try:
        dados = request.get_json() or {}
        cartelas = [c.get("dezenas") if isinstance(c, dict) else c for c in dados.get("cartelas", [])]
        pool = dados.get("pool_elite") or dados.get("pool") or []
        if not cartelas:
            return jsonify({"status": "erro", "msg": "cartelas vazias"}), 400
        ver = magna.verificar_lote_exaustivo(cartelas, pool or list(range(1,18)))
        # backtest opcional
        backtest = {}
        try:
            from core.magna_suprema import BacktestLote, CurvaAprendizado, TesteNIST, PValueRandom, JuizAdversarial
            backtest = BacktestLote().testar(cartelas, magna.matriz, janela=50)
            nist = TesteNIST().testar(cartelas)
            pval = PValueRandom().calcular(ver.get("p13_exata",0), len(cartelas), alvo=13)
            adv = JuizAdversarial().julgar(cartelas, pool or list(range(1,18)))
            curva = CurvaAprendizado(magna.get_historico_magna(50)).curva()
        except Exception as e:
            nist = {"erro": str(e)}
            pval = {}
            adv = {}
            curva = {}
        return jsonify({
            "status": "ok",
            "verificacao": ver,
            "backtest": backtest,
            "nist": nist,
            "p_value": pval,
            "adversarial": adv,
            "curva": curva,
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/chat", methods=["POST"])
def api_magna_chat():
    """Explainability LLM + Chat — responde 'por que 22?' etc."""
    try:
        dados = request.get_json() or {}
        pergunta = dados.get("pergunta", dados.get("mensagem", ""))
        if not pergunta:
            return jsonify({"status": "erro", "msg": "pergunta vazia"}), 400
        # contexto: último resultado ou pega do body
        contexto = dados.get("contexto", {})
        # se não tem contexto, usa vetor atual
        if not contexto:
            try:
                fontes, consulta, espectro, informacao, entropias = magna._fontes_assimiladas_magna()
                pesos = dict(magna.pesos_fontes_magna)
                vetor = np.zeros(25, dtype=float)
                for nome, v in fontes.items():
                    vetor += v * pesos[nome]
                vetor = magna._normalizar_vetor(vetor)
                contexto = {
                    "vf": vetor,
                    "fontes": fontes,
                    "votos": np.asarray(consulta["votos"], dtype=int),
                    "cartelas": [],
                    "pool": [],
                    "analise": {},
                    "regime": magna.detectar_regime_atual(),
                }
            except Exception as e:
                contexto = {"erro": str(e)}
        # chat
        try:
            from core.magna_suprema import ExplainabilityMagna, ChatMagna
            exp = ExplainabilityMagna()
            chat = ChatMagna(exp)
            resposta = chat.responder(pergunta, contexto)
        except Exception as e:
            resposta = f"Erro no chat: {e}"
        return jsonify({"status": "ok", "pergunta": pergunta, "resposta": resposta})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/fingerprint")
def api_magna_fingerprint():
    """Fingerprint pessoal SHA256."""
    try:
        from core.magna_suprema import FingerprintPessoal
        fp = FingerprintPessoal(magna.db)
        fp.carregar_historico()
        return jsonify({"status": "ok", "fingerprint": fp.relatorio(), "total_hashes": len(fp.cache)})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/perfil", methods=["POST"])
def api_magna_perfil():
    """Perfil risco pessoal + utilidade esperada."""
    try:
        dados = request.get_json() or {}
        perfil = dados.get("perfil", "equilibrado")
        from core.magna_suprema import PerfilRiscoPessoal, AlocadorMultiRota
        p = PerfilRiscoPessoal(perfil)
        aloc = AlocadorMultiRota().alocar(
            orcamento=float(dados.get("orcamento", 100.0)),
            quantidade=int(dados.get("quantidade", 8)),
            perfil=perfil
        )
        return jsonify({"status": "ok", "perfil": p.relatorio(), "alocacao_multi_rota": aloc})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/forja/menu")
def api_magna_forja_menu():
    """Menu exato da escada de captura 13 × 14 × 15 com rotas extraordinárias e suprema."""
    try:
        from core.forja_lotes import menu_captura, melhor_rota_por_orcamento
        orc = request.args.get("orcamento", None)
        try:
            orc_val = float(orc) if orc not in (None, "") else None
        except Exception:
            orc_val = None
        menu = menu_captura(orcamento=orc_val)
        rotas_extra = None
        try:
            if orc_val:
                vf = magna._vetor_combinado() if magna.treinado else None
                if vf is not None:
                    rotas_extra = melhor_rota_por_orcamento(
                        vf=vf, orcamento=orc_val, quantidade=8)
        except Exception:
            rotas_extra = None
        return jsonify({
            "status": "ok",
            "versao": "10.0-Magna-Suprema-Potencia-Maxima-Pessoal",
            "menu": menu,
            "rota_extraordinaria": rotas_extra,
            "extraordinaria": {
                "pool_metodo": "MotorGrafos pool_extraordinario vf+diversidade euclidiana lambda 0.38 + jitter",
                "forja_metodo": "forjar_com_forca_maxima 25 candidatas, 5 seeds, k=5 robusto, 30s, massa incremental",
                "fechamento_metodo": "FechamentoDual fechar_com_forca_maxima tabu + ensemble 3 tentativas",
                "14_exato": "forjar_14_exato greedy 151 leque máximo",
            },
            "suprema_v10": {
                "detector_regime": "K-means 3 regimes sobre soma/pares/primos/fib/borda/consec/gap últimos 100 concursos",
                "memoria_vetorial": "Embedding 25D + atenção cosseno sobre episódios prototipo/repulsao top_k=25",
                "juiz_magna": "9 critérios: diversidade_pool, cobertura_13, novidade_15, "
                              "quadrantes, johnson_z, ev, calibracao_vf, "
                              "filtros_soma, cobertura_abertura (acervo)",
                "verificador": "RegiaoAltoAcerto união exata |R13|=4876 |R14|=151 sobre 3.268.760",
                "alocador": "Knapsack maximiza P≥13 dentro orçamento",
                "forja_suprema": "60s, 25 candidatas, 7 seeds, k_robusto=7, mapa MDS",
                "aprendizado": "Dirichlet posterior Bayesiano + momentum 0.65 lr 0.18",
            },
            "verdade_honesta": (
                "A garantia é condicional: só vale se o pool capturar as 15 "
                "dezenas sorteadas. A rota extraordinária maximiza P(lote≥alvo) "
                "dentro do orçamento: pool diversificado + forja força máxima. "
                "Suprema v10 adiciona regime, memória vetorial, juiz e verificação exaustiva — ganho combinatório, nunca preditivo."
            ),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


# ============================================================
# API — TELEMETRIA INMET POR LOCAL DO SORTEIO (v11.7)
# ============================================================

def _forja_auto_instance():
    from core.forja_auto import ForjaAutomatica
    return ForjaAutomatica(magna=magna, db_path=getattr(db, "db_path", None))


@app.route("/api/magna/inmet")
def api_magna_inmet():
    """Estado da telemetria INMET: local do sorteio + última consulta."""
    try:
        auto = _forja_auto_instance()
        local = auto.local_do_sorteio(usar_rede=False)
        return jsonify({
            "status": "ok",
            "versao": "11.7-telemetria-inmet",
            "local_do_sorteio": local,
            "telemetria_banco": auto.telemetria.resumo(),
            "historico": auto.telemetria.historico(10),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/inmet/atualizar", methods=["POST"])
def api_magna_inmet_atualizar():
    """Busca a telemetria INMET do local do sorteio e persiste."""
    try:
        dados = request.get_json() or {}
        auto = _forja_auto_instance()
        local = auto.local_do_sorteio(usar_rede=True)
        parcela = auto.coletar_telemetria(
            local_dados=local,
            concurso=(int(dados["concurso"])
                      if dados.get("concurso") is not None else None),
            salvar=bool(dados.get("salvar", True)),
        )
        return jsonify({
            "status": "ok",
            "versao": "11.7-telemetria-inmet",
            "local_do_sorteio": local,
            "fonte": parcela.get("fonte"),
            "telemetria": parcela.get("telemetria"),
            "condicoes_clima": parcela.get("condicoes_clima"),
            "registrada": bool(dados.get("salvar", True)),
        })
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/forja-auto", methods=["POST"])
def api_magna_forja_auto():
    """Forja automática: local do sorteio → telemetria INMET → forja suprema."""
    try:
        dados = request.get_json() or {}
        auto = _forja_auto_instance()
        resultado = auto.executar(
            quantidade=int(dados.get("quantidade", 8)),
            orcamento=float(dados.get("orcamento", 100.0)),
            alvo=int(dados.get("alvo", 13)),
            perfil=dados.get("perfil", "equilibrado"),
            segundos_forja=float(dados.get("segundos_forja",
                                           dados.get("segundos", 30.0))),
            salvar=bool(dados.get("salvar", True)),
            usar_inmet=bool(dados.get("usar_inmet", True)),
            persistir_telemetria=bool(dados.get("persistir_telemetria", True)),
        )
        if resultado.get("status") != "ok":
            return jsonify(resultado), 502
        decisao = resultado.get("decisao") or {}
        salvos = 0
        if dados.get("salvar", True) and decisao.get("n_cartelas", 0) > 0:
            salvos = _salvar_cartelas_banco(
                decisao["cartelas"], decisao.get("concurso_alvo"),
                tipo="magna_forja_auto", modo=decisao.get("estrategia"),
                grupo_elite=decisao.get("pool_elite"),
                cobertura=(decisao.get("analise") or {}).get(
                    "p_melhor_14_mais", 0),
            )
        return jsonify({
            "status": "ok",
            "versao": "11.7-forja-auto-inmet",
            "local_do_sorteio": resultado.get("local"),
            "telemetria": resultado.get("telemetria"),
            "decisao": decisao,
            "salvas": salvos,
            "concurso": decisao.get("concurso_alvo"),
        })
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


@app.route("/api/magna/clima")
def api_magna_clima():
    """Estado completo da fonte de clima: previsão, vetores,
    auto-auditoria e resumo dos 3 testes físicos."""
    try:
        rel = magna.clima.relatorio()
        return jsonify(rel)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/clima/testes")
def api_magna_clima_testes():
    """Os 3 testes matemáticos (ímpares×pressão, soma×umidade,
    frequência×temperatura) com z-scores e vereditos."""
    try:
        return jsonify(magna.clima.testes_fisicos())
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/clima/ingestao", methods=["POST"])
def api_magna_clima_ingestao():
    """Ingestão de um sorteio com clima (aprendizado contínuo).

    Corpo: {concurso, data?, temperatura_c, pressao_atm, umidade_pct,
    dezenas?} — upsert por concurso; o motor recalibra os testes.
    """
    try:
        dados = request.get_json() or {}
        concurso = int(dados.get("concurso"))
        temp = float(dados.get("temperatura_c"))
        pressao = float(dados.get("pressao_atm"))
        umidade = float(dados.get("umidade_pct"))
        dezenas = dados.get("dezenas")
        if dezenas:
            dezenas = [int(d) for d in str(dezenas).replace(",", " ").split()]
        resultado = magna.clima.aprender(
            concurso=concurso,
            temp=temp,
            pressao=pressao,
            umidade=umidade,
            data=str(dados.get("data", "")),
            dezenas=dezenas,
        )
        if dados.get("aprender") and dezenas:
            # fecha o ciclo: a Magna aprende o resultado com o clima
            try:
                resultado["magna"] = magna.aprender_resultado_magna(
                    concurso, dezenas)
            except Exception as e2:
                resultado["magna"] = {"status": "erro", "msg": str(e2)}
        return jsonify({"status": "ok", **resultado})
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro",
                        "msg": f"dados inválidos: {exc}"}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/ordem")
def ordem_page():
    """v11.4 — o painel de padrões de abertura deixou de ser uma página à parte:
    o conhecimento mora na Inteligência Magna e é mostrado no /cerebro."""
    return redirect(url_for("cerebro_page"), code=303)


@app.route("/api/magna/ordem")
def api_magna_ordem():
    """v11.4 — removido: o antigo motor de ordem virou o ACERVO da Magna.

    Mantém a URL viva por um tempo, mas responde 410 apontando o novo caminho,
    para que qualquer atalho antigo deixe claro que não existe mais módulo.
    """
    return jsonify({"status": "removido",
                    "msg": "v11.4: os padrões de abertura foram absorvidos pela "
                           "Inteligência Magna. Use /api/magna/conhecimento "
                           "(o acervo) e /api/magna/abertura (leitura + "
                           "placar walk-forward); v11.8 — as cores das bolas "
                           "ficam em /api/magna/cor.",
                    "novo_endereco": ["/api/magna/conhecimento",
                                      "/api/magna/conhecimento/assimilar",
                                      "/api/magna/abertura",
                                      "/api/magna/ordem/ingestao",
                                      "/api/magna/cor"]}), 410


@app.route("/api/magna/popularidade")
def api_magna_popularidade():
    """Medição do efeito de RATEIO (edge real, não preditivo).

    Calibra no histórico oficial quantos ganhadores de 13/14 pontos cada perfil
    de cartela costuma atrair. Perfis menos disputados têm o MESMO custo e a
    MESMA P(acerto), mas prêmio esperado condicional maior.
    """
    try:
        if getattr(magna, "antipopularidade", None) is None:
            return jsonify({
                "status": "indisponivel",
                "msg": "anti-popularidade não inicializada",
            })
        return jsonify({
            "status": "ok",
            "anti_popularidade": magna.antipopularidade.relatorio(),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/captura")
def api_magna_captura():
    """Panorama 13 · 14 · 15: probabilidades exatas, custo e EV honesto.

    A escada de captura mostra quantas cartelas a combinatoria garante dado um
    pool de N dezenas. A garantia é CONDICIONAL (exige que o pool contenha as
    15 sorteadas). O EV usa prêmios médios reais e o bônus de rateio estimado.
    """
    try:
        from core.forja_lotes import menu_captura
        from core.wheeling import MotorWheeling
        menus = menu_captura()
        premios = db.get_media_premios()
        media_13 = float(premios["media_13"] or 35.0)
        media_14 = float(premios["media_14"] or 0.0)
        media_15 = float(premios["media_15"] or 0.0)
        ap = getattr(magna, "antipopularidade", None)
        bonus = 1.0
        if ap is not None and ap.n_concursos >= 30:
            rel = ap.relatorio()
            raz = ((rel.get("auto_auditoria") or {}).get(
                "razao_menos_popular_vs_popular"))
            if raz:
                bonus = float(np.clip(1.0 / max(float(raz), 1e-3), 1.0, 3.0))
            else:
                # fallback: cartela representativa da região mais impopular
                bonus = float(ap.analisar_cartela(
                    [7, 8, 9, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25]
                ).get("bonus_rateio_estimado_x", 1.0))
        for linha in menus:
            alvo = linha["alvo"]
            if alvo == 13:
                premio_medio = media_13 * bonus
            elif alvo == 14:
                premio_medio = media_14 * bonus
            else:
                premio_medio = media_15 * bonus
            custo = linha.get("custo_teorico") or 0.0
            p_cap = linha["p_captura"]
            ev = p_cap * premio_medio - custo
            linha["premio_medio_oficial"] = round(premio_medio, 2)
            linha["ev_esperado_lote"] = round(float(ev), 2)
            linha["retorno_esperado_pct"] = (
                round(100 * float(ev) / custo, 2) if custo > 0 else 0.0
            )
            linha["nota_honesta"] = (
                "EV negativo é esperado: a garantia só vale se o pool capturar "
                "o sorteio; prêmio maior (por rateio) é o único ajuste real."
            )
        return jsonify({
            "status": "ok",
            "concursos_na_base": db.get_total_concursos(),
            "universo": MotorWheeling.universo().size,
            "bonus_rateio_medio_x": round(float(bonus), 3),
            "escala": menus,
            "honestidade": (
                "Nenhuma rota altera a probabilidade de acertar 13/14/15. A "
                "escada troca pontos garantidos por probabilidade de captura; "
                "a anti-popularidade troca prêmio disputado por prêmio menos "
                "dividido. Ambos são estrutura, não previsão."
            ),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


# ============================================================
# FECHAMENTOS VERIFICADOS (prova exaustiva no espaço dual)
# ============================================================
@app.route("/api/fechamentos/tabela")
def api_fechamentos_tabela():
    """Escada de fechamentos com garantia PROVADA POR VERIFICAÇÃO EXAUSTIVA."""
    try:
        from core.forja_lotes import menu_captura
        return jsonify({
            "status": "ok",
            "valor_aposta": 3.50,
            "escada": menu_captura(),
            "nota": (
                "Cada fechamento verificado garante a pontuação indicada SE "
                "as 15 sorteadas estiverem no pool (n=25 = incondicional). "
                "A prova enumera TODOS os sorteios possíveis dentro do pool; "
                "não há verificação por amostragem. A fração hipergeométrica "
                "por cartela (1/692, 1/21.792, 1/3.268.760) não muda."
            ),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/fechamentos/construir", methods=["POST"])
def api_fechamentos_construir():
    """Constrói (ou busca do cache) um fechamento verificado.
    Body: {"n_pool": 20, "garantia": 13, "pool": [dezenas...], "tempo": 60}"""
    try:
        from core import cobertura as cov
        dados = request.get_json() or {}
        n = int(dados["n_pool"])
        t = int(dados["garantia"])
        tempo = float(dados.get("tempo", 60))
        res = cov.fechamento_verificado(n, t, tempo_max=tempo, sementes=2)
        if not res.get("garantia_verificada"):
            return jsonify({
                "status": "parcial",
                "msg": "fechamento não concluído no tempo concedido",
                "cota_inferior": cov.cota_inferior(n, t),
            }), 202
        pool = dados.get("pool") or list(range(1, n + 1))
        pool = sorted(int(d) for d in pool)
        if len(pool) != n:
            raise ValueError(f"pool precisa ter {n} dezenas")
        cartelas = cov.blocos_para_cartelas(res["blocos"], pool)
        p_cap = cov.prob_captura(n) if n < 25 else 1.0
        return jsonify({
            "status": "ok",
            "n_pool": n, "garantia": t,
            "cartelas": cartelas,
            "n_cartelas": len(cartelas),
            "custo": round(len(cartelas) * 3.50, 2),
            "cota_inferior": res["cota_inferior"],
            "tipo": "incondicional" if n == 25 else "condicional",
            "p_captura_pool": p_cap,
            "um_em_captura": round(1 / p_cap, 1) if n < 25 else 1,
            "alvos_verificados": res["total_alvos"],
            "do_cache": bool(res.get("do_cache")),
        })
    except (TypeError, ValueError, KeyError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/fechamentos/reverificar", methods=["POST"])
def api_fechamentos_reverificar():
    """Reexecuta a prova exaustiva de todos os fechamentos em cache."""
    try:
        from core import cobertura as cov
        laudo = cov.reverificar_todo_cache()
        return jsonify({
            "status": "ok",
            "laudo": laudo,
            "todos_provados": all(l["verificado"] for l in laudo),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/odds/reais")
def api_odds_reais():
    """Probabilidades exatas por cartela, escada por orçamento e EV real."""
    try:
        from core import odds_reais as odds
        premios = db.get_media_premios()
        media_14 = float(premios["media_14"] or 1763.0)
        media_15 = float(premios["media_15"] or 2_500_000.0)
        return jsonify({
            "status": "ok",
            "concursos_na_base": db.get_total_concursos(),
            "por_cartela": odds.tabela_cartela(),
            "ev_cartela": odds.ev_cartela(media_14 or 1763.0,
                                          media_15 or 2_500_000.0),
            "escada_orcamento": {
                "13": odds.escada_orcamento(13),
                "14": odds.escada_orcamento(14),
                "15": odds.escada_orcamento(15),
            },
            "verdade": (
                "As frações 1/692, 1/21.792 e 1/3.268.760 são fixas por "
                "cartela. Comprar mais cartelas aumenta a chance linearmente "
                "(P≈m/3.268.760 para o 15); o EV permanece negativo. Não "
                "existe método, na web ou em qualquer lugar, que altere a "
                "hipergeométrica de um sorteio independente."
            ),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/lab")
def api_magna_lab():
    """Estado do laboratório dinâmico: placar persistido, quarentena, pesos."""
    try:
        return jsonify(magna.lab_relatorio())
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/lab/benchmark", methods=["POST"])
def api_magna_lab_benchmark():
    """Roda o benchmark walk-forward de todas as estratégias e recalcula pesos."""
    try:
        dados = request.get_json() or {}
        n_testes = int(dados.get("n_testes", 40))
        janela = int(dados.get("janela", 50))
        n_aleatorio = int(dados.get("n_aleatorio", 120))
        if not 5 <= n_testes <= 200:
            raise ValueError("n_testes deve estar entre 5 e 200")
        if not 10 <= janela <= 300:
            raise ValueError("janela deve estar entre 10 e 300")
        return jsonify(magna.lab_benchmark(
            n_testes=n_testes, janela=janela, n_aleatorio=n_aleatorio,
        ))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/lab/explorar", methods=["POST"])
def api_magna_lab_explorar():
    """Explora mutações de janele/transformações e devolve as melhores."""
    try:
        dados = request.get_json() or {}
        ensaios = dados.get("ensaios") or []
        if not isinstance(ensaios, list) or not ensaios:
            raise ValueError("envie `ensaios` (janela/pesos/transformacao)")
        n_testes = int(dados.get("n_testes", 20))
        return jsonify(magna.lab_explorar(ensaios=ensaios, n_testes=n_testes))
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/lab/auditar", methods=["POST"])
def api_magna_lab_auditar():
    """Audita cartelas (repetição histórica, filtros, riscos, P exata)."""
    try:
        dados = request.get_json() or {}
        cartelas = dados.get("cartelas") or []
        if not isinstance(cartelas, list) or not cartelas:
            raise ValueError("envie `cartelas` — lista de listas de 15 dezenas")
        for c in cartelas:
            if not isinstance(c, list) or len(c) != 15:
                raise ValueError("cada cartela deve ter 15 dezenas")
        vetor = dados.get("vetor")
        vetor_final = (np.asarray(vetor, dtype=float)
                       if vetor is not None and len(vetor) == 25 else None)
        score_modelos = dados.get("score_modelos")
        res = magna.auditor_cartelas(
            cartelas, score_modelos=score_modelos,
            vetor_final=vetor_final)
        return jsonify(res)
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro", "msg": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/lab/jogos-ruins")
def api_magna_lab_jogos_ruins():
    """Investiga o histórico procurando jogos repetidos/quase repetidos."""
    try:
        lab = getattr(magna, "laboratorio", None)
        if lab is None:
            return jsonify({"status": "erro", "msg": "laboratório indisponível"})
        return jsonify(lab.jogos_ruins(persistir=True))
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/abertura")
def api_magna_abertura():
    """O que a Magna sabe sobre a abertura do próximo concurso.

    É a mesma evidência que entra no consenso das fontes, que o Juiz usa e que
    a conferência vai julgar — leitura + placar walk-forward + palpite.
    """
    try:
        return jsonify(magna.evidencia_abertura())
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/cor")
def api_magna_cor():
    """v11.8 — o que a Magna sabe sobre as CORES das bolas.

    Domínio de conhecimento derivado da tabela oficial (MazuSoft — a cor de
    cada bola é o último dígito) e reaprendido da base histórica a cada
    assimilação: ranking de cores (P de aparecer), cor forte (2+ bolas),
    streaks da cor dominante, placar walk-forward, auto-auditoria e palpite
    — a mesma evidência que entra no consenso e que a conferência julga.
    """
    try:
        return jsonify(magna.evidencia_cor())
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/cor/tabela")
def api_magna_cor_tabela():
    """v11.8 — a tabela de cores por concurso (como a do MazuSoft).

    Derivada das dezenas oficiais da base (a cor é determinística pelo último
    dígito), com a cor dominante, o perfil completo e as cores ausentes de
    cada sorteio. Parâmetros: `desde`, `ate` e `limite` (padrão 30, máx 200).
    """
    try:
        desde = request.args.get("desde", type=int)
        ate = request.args.get("ate", type=int)
        limite = request.args.get("limite", 30, type=int)
        return jsonify({
            "status": "ok",
            "fonte": "https://www.mazusoft.com.br/lotofacil/tabela-cor.php",
            "regra": "a cor de cada bola é o último dígito: Grupo 1 "
                     "(3 dezenas) vermelha/amarela/verde/marrom/azul; Grupo 2 "
                     "(2 dezenas) rosa/preta/cinza/laranja/branca",
            "linhas": magna.tabela_cores(desde=desde, ate=ate, limite=limite),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/conhecimento")
def api_magna_conhecimento():
    """Inventário do acervo da Magna: base lida, fontes do consenso, pesos,
    abertura aprendida, memória de decisões conferidas e leitura honesta."""
    try:
        detalhes = request.args.get("detalhes", "1") != "0"
        dominio = (request.args.get("dominio") or "").strip()
        if dominio:
            return jsonify(magna.conhecimento(dominio=dominio,
                                               detalhes=True))
        return jsonify(magna.conhecimento(detalhes=detalhes))
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/conhecimento/assimilar", methods=["POST"])
def api_magna_conhecimento_assimilar():
    """Manda a Magna reler a base histórica inteira (e, se pedido, recalibrar
    o peso de cada fonte em walk-forward). É o 'aprender' manual do ciclo."""
    try:
        dados = request.get_json(silent=True) or {}
        limite = float(dados.get("limite_segundos", 60.0))
        resultado = magna.assimilar_acervo(
            forcar=bool(dados.get("forcar", True)),
            calibrar_fontes=bool(dados.get("calibrar_fontes",
                                           dados.get("calibrar", False))),
            limite_segundos=limite)
        return jsonify(resultado)
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro",
                        "msg": f"dados inválidos: {exc}"}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


@app.route("/api/magna/ordem/ingestao", methods=["POST"])
def api_magna_ordem_ingestao():
    """v11.4 — ingestão da ORDEM REAL das bolas de um concurso, dentro da Magna.

    Corpo: {concurso, ordem: [b1..b15 na ordem de extração]} — upsert
    idempotente no banco e no acervo: alimenta a série da 1ª bola (canal
    `real`), o placar walk-forward e o peso da fonte `abertura`.
    Alternativa mais leve: {concurso, abertura: N} quando só se sabe qual bola
    saiu primeiro.
    """
    try:
        dados = request.get_json() or {}
        concurso = int(dados.get("concurso"))
        ordem = dados.get("ordem")
        if ordem:
            if isinstance(ordem, str):
                ordem = [int(d) for d in ordem.replace(",", " ").split()]
            ordem = [int(d) for d in ordem]
            resultado = magna.aprender_ordem_sorteio(concurso, ordem)
        elif dados.get("abertura") is not None:
            resultado = magna.aprender_abertura_medida(
                concurso, int(dados["abertura"]), origem="ingestao")
        else:
            return jsonify({"status": "erro",
                            "msg": "informe 'ordem' (15 bolas) ou 'abertura' "
                                   "(a 1ª bola)"}), 400
        return jsonify(resultado)
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "erro",
                        "msg": f"dados inválidos: {exc}"}), 400
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


@app.route("/api/financeiro/limpar", methods=["POST"])
def api_financeiro_limpar():
    """Botão Clear do módulo financeiro: apaga os resultados registrados."""
    try:
        removidos = financeiro.limpar()
        return jsonify({
            "status": "ok",
            "removidos": removidos,
            "resumo": financeiro.get_resumo_geral(),
        })
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


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


@app.route("/fisica")
def fisica_page():
    """A física do sorteio foi integrada na Inteligência Magna."""
    return redirect(url_for("cerebro_page"), code=303)


@app.route("/avaliacao")
def avaliacao_page():
    """A avaliação foi integrada na Inteligência Magna."""
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
            if resultado.get("novos") or resultado.get("recuperados"):
                try:
                    status_sistema["treinando"] = True
                    status_sistema["progresso"] = (
                        "Inteligência Magna assimilando o sorteio da Caixa..."
                    )
                    pos = magna.ciclo_pos_sorteio_caixa()
                    status_sistema["ia_treinada"] = magna.treinado
                    status_sistema["progresso"] = pos.get(
                        "msg", "Ciclo Magna pós-sorteio concluído")
                except Exception as exc_ciclo:
                    traceback.print_exc()
                    status_sistema["progresso"] = (
                        "Sincronizado; ciclo Magna: {}".format(exc_ciclo)
                    )
                finally:
                    status_sistema["treinando"] = False

                # v12.0 — CALIBRAÇÃO AUTÔNOMA: depois de cada sorteio novo a
                # Magna relê a base inteira e recalibra SOZINHA o peso das
                # fontes em walk-forward (o antigo botão "Calibrar pesos").
                # Roda em thread própria com orçamento de tempo para não
                # segurar a interface; o lock dela serializa com as decisões.
                def _calibrar_sozinha():
                    try:
                        print("[MAGNA] Calibração autônoma pós-sorteio "
                              "iniciada (walk-forward da base)...")
                        with magna._magna_lock:
                            cal = magna.assimilar_acervo(
                                forcar=False, calibrar_fontes=True,
                                limite_segundos=60.0)
                        print("[MAGNA] Calibração autônoma: {}".format(
                            cal.get("status")))
                    except Exception as exc_cal:
                        print("[AVISO] calibração autônoma: {}".format(exc_cal))

                threading.Thread(target=_calibrar_sozinha, daemon=True,
                                 name="magna-calibracao-auto").start()
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


@app.route("/api/magna/aprendizado")
def api_magna_aprendizado():
    """Diagnóstico constante: o que a Magna aprendeu e o que falta."""
    try:
        return jsonify({"status": "ok", **magna.diagnostico_aprendizado()})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"status": "erro", "msg": str(exc)}), 500


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
║  LOTOFÁCIL — INTELIGÊNCIA MAGNA SUPREMA v11.4       ║
║  Sistema único pessoal em potência máxima           ║
║  Aprende, decide, julga, verifica, atua — um só     ║
║  Acervo de conhecimento nativo (base inteira)       ║
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

    # ── v11.4 — PRÉ-CARGA DE CONHECIMENTO (parte do boot, não um passo manual) ──
    # A Magna já nasce tendo lido a base histórica inteira; aqui ela também
    # CALIBRA o peso de cada fonte do consenso em walk-forward antes de o
    # usuário pedir qualquer coisa — para que a decisão do concurso 3774 já
    # saia com todo o conhecimento que existe no sistema. Roda em thread para
    # não segurar o servidor; a UI mostra o estado em /cerebro e em
    # /api/magna/conhecimento. Desligue com LOTOFACIL_ACERVO_BOOT=0.
    if os.getenv("LOTOFACIL_ACERVO_BOOT", "1") != "0":
        def _precarregar_acervo():
            try:
                print("[ACERVO] A Magna está calibrando o próprio conhecimento "
                      "sobre a base histórica (tudo o que existe nela)...")
                res = magna.assimilar_acervo(
                    forcar=True, calibrar_fontes=True, limite_segundos=90.0)
                print("[ACERVO] {}: {}".format(
                    res.get("status"),
                    res.get("leitura")
                    or "pesos do consenso calibrados em walk-forward"))
                cal = res.get("calibracao") or {}
                if cal:
                    print("[ACERVO] calibração: {} provas fora-da-amostra em {}s{}"
                          " · pesos {}".format(
                              cal.get("provas"), cal.get("tempo_seg"),
                              " (parcial: o orçamento cortou)"
                              if cal.get("parcial") else "",
                              " · ".join("{} {:.3f}".format(n, p) for n, p
                                         in (cal.get("pesos_calibrados") or
                                            {}).items())))
            except Exception as exc:
                print("[AVISO] pré-carga de acervo: {}".format(exc))

        threading.Thread(target=_precarregar_acervo, daemon=True,
                         name="acervo-boot").start()

    # Monitora a Caixa em segundo plano: novo sorteio → treino + aprendizado.
    try:
        cerebro.iniciar_loop(int(os.getenv("LOTOFACIL_LOOP_SEG", "1800")))
        print("[MAGNA] Loop autônomo de monitoramento da Caixa iniciado")
    except Exception as exc:
        print("[AVISO] Loop Magna: {}".format(exc))

    host = os.getenv("LOTOFACIL_HOST", "127.0.0.1")
    port = int(os.getenv("LOTOFACIL_PORT", "5000"))
    debug = os.getenv("LOTOFACIL_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug, use_reloader=False)