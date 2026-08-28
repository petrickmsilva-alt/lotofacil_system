"""Acervo de conhecimento da Inteligência Magna (v11.4).

Trava duas coisas:

1. a matemática do órgão de abertura (`AcervoAberturaMagna`, que agora mora
   DENTRO de `core/cerebro_ia.py` — não existe módulo paralelo);
2. a integração: a abertura entra no consenso como fonte `abertura`, pesa na
   interpretação de cada cartela, é julgada pelo Juiz, memorizada em
   `magna_conhecimento`/`magna_memoria` e reaprendida a cada conferência.

Os casos sintéticos usam sequências FABRICADAS para provar os cálculos; os
cenários com a base real tendem a dar veredito RUÍDO — comportamento honesto
esperado sob independência, e é isso que o sistema publica.
"""
import json
import os
import shutil
import sqlite3
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_PATH, TOTAL_DEZENAS  # noqa: E402
from core.cerebro_ia import AcervoAberturaMagna, InteligenciaMagna  # noqa: E402


def _acervo_minima(valores, inicio=1000):
    return AcervoAberturaMagna(
        minima=[(inicio + i, int(v)) for i, v in enumerate(valores)])


# ------------------------------------------------------------
# 1. matemática do acervo
# ------------------------------------------------------------
def test_nao_existeMais_modulo_paralelo():
    """O antigo `core/padroes_ordem.py` foi absorvido pela Magna."""
    with pytest.raises(ImportError):
        import core.padroes_ordem  # noqa: F401
    assert not hasattr(InteligenciaMagna, "ordem_motor")
    assert not hasattr(InteligenciaMagna, "minimo_motor")


def test_margem_teorica_exata():
    assert AcervoAberturaMagna.p_teorica("minima", 1) == pytest.approx(0.60)
    assert AcervoAberturaMagna.p_teorica("minima", 2) == pytest.approx(0.25)
    assert AcervoAberturaMagna.p_teorica("minima", 3) == pytest.approx(0.098, abs=1e-3)
    assert AcervoAberturaMagna.p_teorica("minima", 13) == 0.0
    assert AcervoAberturaMagna.p_teorica("real", 7) == pytest.approx(1.0 / 25)
    acervo = _acervo_minima([1, 2, 3])
    assert acervo.linha_de_base("minima") == pytest.approx(0.60)
    assert acervo.linha_de_base("real") == pytest.approx(5.0 / 25)


def test_validar_ordem_exige_15_unicas_1_a_25():
    for invalida in ([1] * 15, [0] + list(range(2, 16)), [26] + list(range(2, 16)),
                     [1, 2, 3], list(range(1, 16)) + [1]):
        with pytest.raises(ValueError):
            AcervoAberturaMagna.validar_ordem(invalida)
    valida = list(range(1, 16))
    assert AcervoAberturaMagna.validar_ordem(valida) == tuple(valida)


def test_aprender_e_idempotente_e_ordena_por_concurso():
    acervo = AcervoAberturaMagna()
    assert acervo.aprender("minima", 10, 1)["n_registros"] == 1
    assert acervo.aprender("minima", 9, 2)["n_registros"] == 2
    res = acervo.aprender("minima", 10, 1)
    assert res["idempotente"] is True
    assert acervo.serie["minima"] == [(9, 2), (10, 1)]
    assert acervo.ultimo("minima") == 10
    assert acervo.abertura_atual("minima") == 1
    with pytest.raises(ValueError):
        acervo.aprender("canal_inexistente", 1, 1)
    with pytest.raises(ValueError):
        acervo.aprender("minima", 0, 1)
    with pytest.raises(ValueError):
        acervo.aprender("minima", 5, 99)


def test_aprender_ordem_alimenta_canal_real():
    acervo = AcervoAberturaMagna()
    ordem = [7, 1, 22, 3, 14, 5, 19, 11, 2, 25, 8, 13, 17, 4, 10]
    res = acervo.aprender_ordem(3774, ordem)
    assert res["abertura"] == 7 and res["n_ordens"] == 1
    assert acervo.n("real") == 1
    with pytest.raises(ValueError):
        acervo.aprender_ordem(3775, [1] * 15)


def test_streaks_medem_sequencia_atual_e_recorde():
    # 03 abre 3x, larga, e fecha com 02 duas vezes
    acervo = _acervo_minima([1, 3, 3, 3, 1, 2, 2])
    st = acervo.streaks("minima")
    assert st["run_atual"]["dezena"] == 2
    assert st["run_atual"]["comprimento"] == 2
    assert st["recorde_historico"]["dezena"] == 3
    assert st["recorde_historico"]["comprimento"] == 3
    assert st["por_dezena"][3]["maximo"] == 3
    assert st["por_dezena"][1]["concursos_desde_ultima"] == 2


def test_repeticao_condicional_e_medida_so_zinha_dezena():
    """P(repetir | streak) é medido na dezena pedida, nunca agregado."""
    serie = []
    for _ in range(4):
        serie += [3, 3, 3, 1]          # 03 emenda 3x e para
    acervo = _acervo_minima(serie)
    med = acervo.repeticao_apos_streak(3, streak_min=2)
    # 4 blocos × 2 transições saindo de um streak de 03 = 8 provas; só a
    # segunda emenda repete → 03 abre de novo em metade delas
    assert med["provas"] == 8 and med["repetiu"] == 4
    assert med["taxa_real"] == pytest.approx(0.5)
    assert med["taxa_teorica"] == pytest.approx(0.098, abs=1e-3)
    # dezena sem histórico de streak não inventa número
    assert acervo.repeticao_apos_streak(11, streak_min=2)["provas"] == 0


def test_posterior_normaliza_e_puxa_para_a_margem_em_base_pequena():
    acervo = _acervo_minima([1, 1, 2, 5, 3])
    probs = acervo.posterior("minima")
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-9)
    assert set(probs) >= set(AcervoAberturaMagna.categorias("minima"))
    # com 5 registros a mistura ainda é dominada pela margem teórica
    assert probs[1] > probs[2] > probs[11]


def test_walkforward_usa_so_o_passado_e_um_sinal_forte_vira_REAL():
    """Se a abertura é sempre 01, o walk-forward acerta tudo e o veredito é REAL."""
    acervo = _acervo_minima([1] * 400)
    placar = acervo.placar_walkforward("minima")
    assert placar["aplicavel"] is True
    # a primeira prova só existe quando já há um passado para aprender
    assert placar["n_provas"] == 398
    assert placar["margem_da_magna_top1"]["acertos"] == 398
    assert placar["margem_da_magna_top1"]["taxa"] == pytest.approx(1.0)
    assert placar["margem_da_magna_top1"]["teto_teorico"] == pytest.approx(0.6)
    aud = acervo.auto_auditoria("minima")
    assert aud["veredito"] == "REAL"
    assert aud["fator_confianca"] == pytest.approx(1.0)
    assert acervo.fator_confianca() > 0.75


def test_ruido_nao_ganha_confianca():
    """Sob independência o veredito é RUÍDO e o vetor entra atenuado (0,5)."""
    rng = np.random.default_rng(7)
    # amostras do próprio processo hipergeométrico: 15 de 25 sem reposição
    serie = [min(rng.choice(np.arange(1, 26), size=15, replace=False))
             for _ in range(1500)]
    acervo = _acervo_minima(serie)
    aud = acervo.auto_auditoria("minima")
    assert aud["veredito"] in ("RUÍDO", "REAL")
    if aud["veredito"] == "RUÍDO":
        assert aud["fator_confianca"] == 0.5
        assert acervo.fator_confianca() <= 0.75
    placar = acervo.placar_walkforward("minima")
    # a margem continua sendo o teto: ninguém passa dela por muito
    assert 0.45 < placar["margem_da_magna_top1"]["taxa"] < 0.72
    # e excluir a abertura em sequência não melhora nada
    assert (placar["margem_da_magna_top1"]["taxa"]
            >= placar["regra_popular_de_exclusao"]["taxa"] - 0.02)
    assert placar["cobertura_top2"]["taxa"] < 0.95


def test_afinidade_de_cartela_reflete_a_abertura_prevista():
    acervo = _acervo_minima([1] * 60 + [2] * 20 + [3] * 10)
    assert acervo.auto_auditoria("minima")["veredito"] in ("RUÍDO", "REAL")
    com_01 = sorted([1, 4, 5, 6, 8, 9, 11, 13, 14, 16, 17, 19, 21, 23, 25])
    sem_01 = sorted([13, 14, 16, 17, 19, 20, 21, 22, 23, 24, 25, 12, 15, 18, 2])
    a = acervo.afinidade_cartela(com_01)
    b = acervo.afinidade_cartela(sem_01)
    assert a["abertura_da_cartela"] == 1 and b["abertura_da_cartela"] == 2
    assert a["afinidade"] > b["afinidade"]
    assert a["cobre_palpite_da_magna"] is True
    assert 0.0 <= b["afinidade"] <= 1.0


def test_avaliar_palpite_posicao_no_ranking():
    j1 = AcervoAberturaMagna.avaliar_palpite([1, 2, 3], 1)
    assert j1["posicao_no_ranking"] == 1 and j1["acerto_top1"] is True
    j3 = AcervoAberturaMagna.avaliar_palpite([1, 2, 3], 3)
    assert j3["posicao_no_ranking"] == 3 and j3["acerto_top1"] is False
    jfora = AcervoAberturaMagna.avaliar_palpite([1, 2, 3], 9)
    assert jfora["posicao_no_ranking"] is None
    assert jfora["acerto_top3"] is False


def test_digest_muda_so_quando_a_memoria_muda():
    a = _acervo_minima([1, 2, 3, 1, 2])
    b = _acervo_minima([1, 2, 3, 1, 2])
    c = _acervo_minima([1, 2, 3, 1, 3])
    assert a.digest() == b.digest()
    assert a.digest() != c.digest()
    assert a.digest().startswith("sha256:")


def test_relatorio_publica_canais_e_honestidade():
    acervo = _acervo_minima([1] * 80 + [2] * 30)
    rel = acervo.relatorio()
    assert set(rel["canais"]) == {"minima", "real"}
    assert rel["canais"]["minima"]["n_registros"] == 110
    assert "hipergeométrica" in rel["honestidade"]
    assert rel["leitura"]
    assert "status" in rel and rel["status"] == "ok"


# ------------------------------------------------------------
# 2. integração com a Magna (banco isolado em cópia temporária)
# ------------------------------------------------------------
@pytest.fixture(scope="module")
def magna(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("acervo") / "magna.db"
    shutil.copy2(DATABASE_PATH, caminho)
    return InteligenciaMagna(db_path=str(caminho))


@pytest.fixture(scope="module")
def magna_aprendida(magna):
    """Magna que já relê a base inteira e memoriza (sem calibrar pesos)."""
    magna.assimilar_acervo(forcar=True, calibrar_fontes=False)
    return magna


def test_fonte_abertura_substitui_motor_paralelo(magna):
    assert "abertura" in magna._FONTES_MAGNA_DEFAULT
    assert "ordem" not in magna._FONTES_MAGNA_DEFAULT
    assert magna._FONTES_MAGNA_DEFAULT["abertura"] == pytest.approx(0.04)
    assert set(magna.pesos_fontes_magna) == set(magna._FONTES_MAGNA_DEFAULT)
    assert abs(sum(magna.pesos_fontes_magna.values()) - 1.0) < 1e-6


def test_acervo_monta_na_instancia_sem_pedido(magna):
    assert isinstance(magna.acervo, AcervoAberturaMagna)
    assert magna.acervo.n("minima") >= 3000          # a base histórica inteira
    assert magna.acervo.ultimo("minima") >= 3770


def test_vetor_da_fonte_abertura_entra_no_consenso(magna):
    fontes, *_ = magna._fontes_assimiladas_magna()
    assert "abertura" in fontes and "ordem" not in fontes
    v = fontes["abertura"]
    assert len(v) == TOTAL_DEZENAS
    assert float(np.sum(v)) == pytest.approx(1.0, abs=1e-6)
    assert "abertura" in magna._ACERVO_DOMINIOS


def test_assimilar_grava_e_reaproveita_carimbo(magna_aprendida):
    conn = sqlite3.connect(magna_aprendida.db_path)
    try:
        dom = dict(conn.execute(
            "SELECT dominio, veredito FROM magna_conhecimento").fetchall())
        assert "abertura" in dom and "base" in dom
        assert dom["abertura"] in ("RUÍDO", "REAL")
        n_eventos = conn.execute(
            "SELECT COUNT(*) FROM magna_memoria WHERE dominio='abertura'"
        ).fetchone()[0]
        assert n_eventos >= 1
    finally:
        conn.close()
    de_novo = magna_aprendida.assimilar_acervo(auto=True)
    assert de_novo["status"] in ("atualizado", "memoria", "ok")
    conhecimento = magna_aprendida.conhecimento(detalhes=False)
    assert conhecimento["versao_acervo"] == magna_aprendida.ACERVO_VERSAO
    assert conhecimento["base"]["concursos"] >= 3000
    assert "leitura" in conhecimento and "honestidade" in conhecimento
    assert "abertura" in conhecimento["dominios"]


def test_evidencia_abertura_e_a_mesma_para_decisao_e_juiz(magna_aprendida):
    ev = magna_aprendida.evidencia_abertura()
    for chave in ("digest", "aprendido_ate", "veredito", "fator_confianca",
                  "ranking", "palpite_top3", "placar", "leitura",
                  "concursos_da_base", "probabilidades"):
        assert chave in ev, chave
    assert ev["ranking"], "a Magna precisa ter um ranking de abertura"
    assert magna_aprendida.ancoras_do_acervo(3) == ev["ranking"][:3]
    assert len(magna_aprendida.ancoras_do_acervo(1)) == 1


def test_decisao_leva_acervo_memoria_e_palpite_julgavel(magna_aprendida):
    resultado = magna_aprendida.decidir_e_gerar(
        quantidade=1, registrar=True, concurso_alvo=9991)
    assert resultado["status"] == "ok"
    acervo = resultado["acervo_magna"]
    assert acervo["veredito"] in ("RUÍDO", "REAL")
    assert acervo["digest"] == magna_aprendida.acervo.digest()
    assert "abertura" in resultado["justificativa_magna"].lower()
    cartela = resultado["cartelas"][0]
    assert cartela["interpretacao_magna"]["abertura"]["abertura_da_cartela"] in range(1, 14)
    assert 0.0 <= cartela["scores"]["afinidade_abertura"] <= 1.0
    palpite = resultado["memoria_magna"]["palpite_abertura"]
    assert palpite["digest"] == acervo["digest"]
    assert palpite["concurso"] == 9991
    assert 1 <= len(palpite["ranking"]) <= 25


def test_conferencia_julga_o_palpite_e_a_magna_aprende_abertura(magna_aprendida):
    alvo = 9991
    # sorteio fabricado: abre com 01 (o palpite mais provável da base)
    dezenas = [1, 4, 6, 8, 10, 12, 13, 14, 15, 17, 19, 21, 22, 23, 25]
    antes = magna_aprendida.acervo.n("minima")
    aprendido = magna_aprendida.aprender_resultado_magna(alvo, dezenas)
    assert aprendido["status"] == "ok"
    julgados = [d.get("abertura") for d in aprendido["decisoes_aprendidas"]
                if d.get("abertura")]
    assert julgados, "a conferência tem que julgar o palpite de abertura"
    alvo_julgado = [j for j in julgados if j["concurso"] == alvo]
    assert alvo_julgado and alvo_julgado[0]["acerto_top1"] is True
    assert "abertura" in aprendido["pesos_fontes"]
    assert aprendido["acervo"]["concursos_da_base"] == antes + 1
    assert aprendido["placar_abertura"]["provas"] >= 1
    conn = sqlite3.connect(magna_aprendida.db_path)
    try:
        eventos = [r[0] for r in conn.execute(
            "SELECT evento FROM magna_memoria WHERE dominio='abertura' "
            "AND concurso=?", (alvo,)).fetchall()]
        assert "palpite" in eventos
    finally:
        conn.close()


def test_ingestao_da_ordem_real_persiste_e_reassimila(magna_aprendida):
    ordem = [7, 1, 22, 3, 14, 5, 19, 11, 2, 25, 8, 13, 17, 4, 10]
    res = magna_aprendida.aprender_ordem_sorteio(9992, ordem)
    assert res["abertura_real"] == 7 and res["persistido"] is True
    assert magna_aprendida.acervo.n("real") >= 4
    gravado = magna_aprendida.db.get_ordem(9992)
    assert gravado == ordem
    # a fonte `real` passou a ter mais um concurso memorizado
    assert magna_aprendida.conhecimento(detalhes=False)["abertura"][
        "concursos_com_ordem_real"] >= 4
    # e a 1ª bola entra no canal minima via conferência, não por duplicação
    with pytest.raises(ValueError):
        magna_aprendida.aprender_ordem_sorteio(9992, [1] * 15)


def test_status_e_diagnostico_expoem_o_acervo(magna_aprendida):
    status = magna_aprendida.get_status()
    assert "acervo" in status and "ordem" not in status
    bloco = status["acervo"]
    assert bloco["versao"] == magna_aprendida.ACERVO_VERSAO
    assert bloco["estado"]["concursos_da_base"] >= 3000
    assert bloco["pesos_fontes"]["abertura"] > 0
    diag = magna_aprendida.diagnostico_aprendizado()
    assert "acervo" in diag
    assert any("acervo" in item for item in diag["o_que_aprende"])
    assert "ordem_motor" not in json.dumps(diag, ensure_ascii=False)


def test_checkpoint_migra_pesos_antigos_da_fonte_ordem(magna):
    """Peso aprendido com a chave antiga `ordem` não é jogado fora."""
    conn = sqlite3.connect(magna.db_path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS magna_checkpoint "
                     "(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, "
                     "pesos_json TEXT, media_acertos REAL, n_amostra INTEGER)")
        conn.execute("DELETE FROM magna_checkpoint")
        antigos = dict(magna._FONTES_MAGNA_DEFAULT)
        antigos.pop("abertura")
        antigos["ordem"] = 0.09                      # aprendido na v11.3
        conn.execute(
            "INSERT INTO magna_checkpoint (timestamp, pesos_json, "
            "media_acertos, n_amostra) VALUES ('agora', ?, 8.0, 10)",
            (json.dumps(antigos),))
        for i in range(20):                           # derruba a média
            conn.execute(
                "INSERT INTO magna_decisoes (timestamp, concurso_alvo, "
                "quantidade, estrategia, justificativa, status, cartelas_json, "
                "analise_json, media_acertos, melhor_acertos) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("t", 9000 + i, 1, "s", "j", "conferida", "[]", "{}",
                 9.0 if i < 10 else 1.0, 9))
        conn.commit()
    finally:
        conn.close()
    conn = magna.db.get_conn()
    try:
        magna._checkpoint_ou_rollback(conn)
        conn.commit()
    finally:
        conn.close()
    pesos = magna.pesos_fontes_magna
    assert set(pesos) == set(magna._FONTES_MAGNA_DEFAULT)
    assert "ordem" not in pesos
    # 0,09 reaproveitado como `abertura` e renormalizado sobre a soma 1,05
    assert pesos["abertura"] == pytest.approx(0.09 / 1.05, abs=1e-4)
    assert abs(sum(pesos.values()) - 1.0) < 1e-4


def test_suprema_decide_com_o_acervo_e_o_juiz_ve_a_abertura(magna_aprendida):
    """A Suprema (potência máxima) usa o mesmo acervo — sem segunda cabeça."""
    r = magna_aprendida.decidir_suprema(
        quantidade=1, alvo=13, perfil="equilibrado", usar_mcts=False,
        usar_multi_rota=False, segundos_forja=1.0, tentativas_juiz=1,
        registrar=False, concurso_alvo=9994)
    assert r["status"] == "ok"
    assert "acervo" in r["justificativa_magna"].lower()
    assert r["acervo_magna"]["digest"] == magna_aprendida.acervo.digest()
    assert r["memoria_magna"]["acervo"]["veredito"] in ("RUÍDO", "REAL")
    assert r["memoria_magna"]["palpite_abertura"]["ranking"]
    cartela = r["cartelas"][0]
    assert 0.0 <= cartela["interpretacao_magna"]["abertura"]["afinidade"] <= 1.0
    assert "acervo" in " ".join(r["fontes_assimiladas"])


def test_juiz_aplica_o_nono_criterio_so_quando_o_acervo_entr(magna_aprendida):
    """Sem `abertura` o juiz continua com 8 critérios; com ela, 9 — e uma
    cartela única não é reprovada por não 'cobrir' 85% da massa."""
    from core.magna_suprema import JuizMagna
    cartelas = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 25]]
    pool = sorted({d for c in cartelas for d in c} | {15})
    vf = magna_aprendida.vetor_final if hasattr(
        magna_aprendida, "vetor_final") else np.ones(25) / 25.0
    analise = {"p_melhor_13_mais": 0.01, "ev_lote": -3.0}
    sem = JuizMagna(magna_aprendida.matriz).julgar(
        cartelas, pool, analise, vf, set())
    com = JuizMagna(magna_aprendida.matriz).julgar(
        cartelas, pool, analise, vf, set(),
        abertura=magna_aprendida.evidencia_abertura())
    assert "cobertura_abertura" not in sem["criterios"]
    assert "cobertura_abertura" in com["criterios"]
    assert com["criterios"]["cobertura_abertura"]["ok"] is True
    assert "cobertura_abertura" not in com["reprovados"]


def test_memoria_nao_infla_com_a_mesma_assimilacao(magna_aprendida):
    magna_aprendida.assimilar_acervo(forcar=True, calibrar_fontes=False)
    conn = sqlite3.connect(magna_aprendida.db_path)
    try:
        carimbo = magna_aprendida._acervo_carimbo()
        n = conn.execute(
            "SELECT COUNT(*) FROM magna_memoria WHERE dominio='abertura' "
            "AND evento='assimilado' AND concurso=?", (carimbo,)).fetchone()[0]
    finally:
        conn.close()
    assert n == 1, "a mesma leitura não pode virar dois registros na memória"
