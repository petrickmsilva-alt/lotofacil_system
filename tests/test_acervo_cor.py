"""Testes do ACERVO DE CORES da Magna (v11.8 — tabela oficial MazuSoft).

A cor de cada bola é o último dígito do número; o perfil por concurso é
derivado das 15 dezenas oficiais. Estes testes cobrem a tabela, a margem
hipergeométrica, o aprendizado/memorização, o placar walk-forward honesto e
a integração com a Inteligência Magna (fonte `cor` no consenso).
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
from math import comb

from config import DATABASE_PATH, TOTAL_DEZENAS
from core.acervo_cor import (
    AcervoCorMagna, CORES, CORES_GRUPO1, CORES_GRUPO2,
    COR_DEZENA, DEZENAS_COR, GRUPO_COR,
)
from core.cerebro_ia import InteligenciaMagna


# ---------------------------------------------------------------------------
# TABELA OFICIAL DE CORES (último dígito)
# ---------------------------------------------------------------------------
def test_tabela_cobre_as_25_dezenas_sem_duplicidade():
    assert sorted(COR_DEZENA) == list(range(1, 26))
    assert len(COR_DEZENA) == 25
    todas = [d for dezenas in DEZENAS_COR.values() for d in dezenas]
    assert sorted(todas) == list(range(1, 26))


def test_cores_por_ultimo_digito():
    # Grupo 1 — 3 dezenas por cor (terminadas em 1..5)
    assert DEZENAS_COR["vermelha"] == (1, 11, 21)
    assert DEZENAS_COR["amarela"] == (2, 12, 22)
    assert DEZENAS_COR["verde"] == (3, 13, 23)
    assert DEZENAS_COR["marrom"] == (4, 14, 24)
    assert DEZENAS_COR["azul"] == (5, 15, 25)
    # Grupo 2 — 2 dezenas por cor (terminadas em 6..0)
    assert DEZENAS_COR["rosa"] == (6, 16)
    assert DEZENAS_COR["preta"] == (7, 17)
    assert DEZENAS_COR["cinza"] == (8, 18)
    assert DEZENAS_COR["laranja"] == (9, 19)
    assert DEZENAS_COR["branca"] == (10, 20)
    # último dígito → cor
    assert COR_DEZENA[21] == "vermelha"
    assert COR_DEZENA[25] == "azul"
    assert COR_DEZENA[10] == "branca"
    assert COR_DEZENA[16] == "rosa"
    # grupos
    assert all(GRUPO_COR[c] == 1 for c in CORES_GRUPO1)
    assert all(GRUPO_COR[c] == 2 for c in CORES_GRUPO2)
    assert len(CORES) == 10


# ---------------------------------------------------------------------------
# MARGEM HIPERGEOMÉTRICA EXATA
# ---------------------------------------------------------------------------
def test_probabilidade_teorica_hipergeometrica():
    total = comb(25, 15)
    for cor in CORES_GRUPO1:  # 3 bolas
        for k in range(4):
            esperado = comb(3, k) * comb(22, 15 - k) / total
            assert AcervoCorMagna.p_teorica(cor, k) == pytest.approx(esperado)
        assert sum(AcervoCorMagna.p_teorica(cor, k) for k in range(4)) \
            == pytest.approx(1.0)
        # valores da tabela MazuSoft: P(aparecer) 94,78% · P(2+) 65,43%
        assert AcervoCorMagna.p_aparecer_teorica(cor) \
            == pytest.approx(0.947826, abs=1e-4)
        assert AcervoCorMagna.p_forte_teorica(cor) \
            == pytest.approx(0.654348, abs=1e-4)
        assert AcervoCorMagna.esperado_teorico(cor) == pytest.approx(1.8)
    for cor in CORES_GRUPO2:  # 2 bolas
        for k in range(3):
            esperado = comb(2, k) * comb(23, 15 - k) / total
            assert AcervoCorMagna.p_teorica(cor, k) == pytest.approx(esperado)
        assert AcervoCorMagna.p_aparecer_teorica(cor) \
            == pytest.approx(0.85, abs=1e-4)
        assert AcervoCorMagna.p_forte_teorica(cor) \
            == pytest.approx(0.35, abs=1e-4)
        assert AcervoCorMagna.esperado_teorico(cor) == pytest.approx(1.2)


def test_margem_teorica_do_vetor_de_cores_e_uniforme():
    """Sob a margem pura (acervo vazio), E[G1]/3 = E[G2]/2 = 0,6 → uniforme."""
    ac = AcervoCorMagna(serie=[])
    v = ac.vetor_bruto()
    assert v.shape == (25,)
    assert v.sum() == pytest.approx(1.0)
    assert np.allclose(v, np.ones(25) / 25, atol=1e-9)


# ---------------------------------------------------------------------------
# APRENDIZADO E MEMÓRIA
# ---------------------------------------------------------------------------
def test_perfil_e_dominante():
    dezenas = [1, 2, 3, 6, 7, 8, 11, 12, 13, 16, 17, 18, 21, 22, 23]
    perfil = AcervoCorMagna.perfil_dezenas(dezenas)
    assert perfil["vermelha"] == 3     # 1, 11, 21
    assert perfil["amarela"] == 3      # 2, 12, 22
    assert perfil["verde"] == 3        # 3, 13, 23
    assert perfil["rosa"] == 2         # 6, 16
    assert perfil["preta"] == 2        # 7, 17
    assert perfil["cinza"] == 2        # 8, 18
    assert sum(perfil.values()) == 15
    assert AcervoCorMagna.dominante_de(perfil) == "vermelha"  # empate → ordem oficial


def test_aprender_upsert_idempotente():
    ac = AcervoCorMagna(serie=[])
    res = ac.aprender(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    assert res["status"] == "ok"
    assert res["n_registros"] == 1
    assert res["dominante"] in CORES
    igual = ac.aprender(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    assert igual["idempotente"] is True
    assert ac.n() == 1
    with pytest.raises(ValueError):
        ac.aprender(2, [1, 2, 3])  # perfil incompleto
    with pytest.raises(ValueError):
        ac.aprender(2, list(range(1, 16)) + [16])  # 16 dezenas


def test_digest_estavel_e_sensivel():
    serie = [(1, tuple(range(1, 16))), (2, tuple(range(2, 17)))]
    a = AcervoCorMagna(serie=serie)
    b = AcervoCorMagna(serie=serie)
    assert a.digest() == b.digest()
    c = AcervoCorMagna(serie=[(1, tuple(range(1, 16))), (2, tuple(range(3, 18)))])
    assert a.digest() != c.digest()


# ---------------------------------------------------------------------------
# PLACAR WALK-FORWARD E AUTO-AUDITORIA (honestidade)
# ---------------------------------------------------------------------------
def test_walkforward_sem_vazamento_fica_na_margem():
    """Com uma série sintética balanceada, o placar não supera a margem:
    o veredito é RUÍDO e o fator de confiança 0,5 (vetor atenuado)."""
    rng = np.random.default_rng(7)
    serie = []
    for concurso in range(1, 201):
        dezenas = sorted(rng.choice(25, 15, replace=False) + 1)
        serie.append((concurso, tuple(int(d) for d in dezenas)))
    ac = AcervoCorMagna(serie=serie)
    placar = ac.placar_walkforward()
    assert placar["aplicavel"] is True
    assert placar["n_provas"] >= 100
    # a taxa da cor mais provável fica colada na margem teórica 94,78%
    assert abs(placar["margem_da_magna_top1"]["taxa"]
               - placar["margem_da_magna_top1"]["teto_teorico"]) < 0.05
    aud = ac.auto_auditoria()
    assert aud["veredito"] == "RUÍDO"
    assert aud["fator_confianca"] == 0.5
    assert ac.fator_confianca() == 0.5


def test_baseline_dominancia_por_simulacao():
    base = AcervoCorMagna.baseline_dominancia()
    assert base["n_sim"] == 40000
    dist = base["distribuicao"]
    assert abs(sum(dist.values()) - 1.0) < 1e-4
    # Grupo 1 domina com folga (3 bolas vs 2): soma das 5 primeiras > 70%
    g1 = sum(dist[c] for c in CORES_GRUPO1)
    assert g1 > 0.7
    # repetição teórica = Σ p² < 0,5
    assert 0.0 < base["repeticao_teorica"] < 0.5


def test_avaliar_palpite():
    ranking = ["vermelha", "amarela", "verde"]
    perfil = {"vermelha": 2, "amarela": 1, "verde": 1, "branca": 2,
              "preta": 2, "cinza": 2, "rosa": 2, "laranja": 1, "marrom": 1,
              "azul": 1}
    j = AcervoCorMagna.avaliar_palpite(ranking, perfil,
                                       ranking_fortes=["vermelha"])
    assert j["dominante_real"] == "vermelha"
    assert j["posicao_no_ranking"] == 1
    assert j["acerto_top1"] is True
    assert j["acerto_forte"] is True
    # perfil válido (15 bolas) sem nenhuma das cores previstas no top3
    perfil2 = {"marrom": 3, "azul": 2, "rosa": 2, "preta": 2,
               "cinza": 2, "laranja": 2, "branca": 2}
    assert sum(perfil2.values()) == 15
    j2 = AcervoCorMagna.avaliar_palpite(ranking, perfil2)
    assert j2["acerto_top1"] is False
    assert j2["dominante_real"] == "marrom"
    assert j2["posicao_no_ranking"] is None


def test_afinidade_cartela():
    ac = AcervoCorMagna(serie=[(1, tuple(range(1, 16)))])
    r = ac.afinidade_cartela(list(range(1, 16)))
    # 1..15 → G1 cores com 2 bolas (sem a 21/22/23/24/25), G2 com 1 bola
    assert r["perfil_da_cartela"]["vermelha"] == 2
    assert r["perfil_da_cartela"]["rosa"] == 1
    assert sum(r["perfil_da_cartela"].values()) == 15
    assert r["cor_dominante_da_cartela"] in CORES
    assert 0.0 <= r["afinidade"] <= 1.0
    assert isinstance(r["cobre_palpite_da_magna"], bool)


def test_tabela_cores_derivada():
    serie = [(1, tuple(range(1, 16))), (2, tuple(range(6, 21))),
             (3, tuple(range(11, 26)))]
    ac = AcervoCorMagna(serie=serie)
    linhas = ac.tabela(limite=2)
    assert len(linhas) == 2
    assert linhas[0]["concurso"] == 2
    assert set(linhas[0]["perfil"]) == set(CORES)
    assert sum(linhas[0]["perfil"].values()) == 15
    assert linhas[0]["dominante"] in CORES


# ---------------------------------------------------------------------------
# INTEGRAÇÃO COM A INTELIGÊNCIA MAGNA
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def magna_cores(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("magna_cor") / "magna.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho))
    return magna


def test_magna_tem_fonte_cor_no_consenso(magna_cores):
    m = magna_cores
    assert "cor" in m._FONTES_MAGNA_DEFAULT
    assert m._FONTES_MAGNA_DEFAULT["cor"] == pytest.approx(0.03)
    assert abs(sum(m._FONTES_MAGNA_DEFAULT.values()) - 1.0) < 1e-9
    fontes, *_ = m._fontes_assimiladas_magna()
    assert "cor" in fontes
    v = fontes["cor"]
    assert v.shape == (25,)
    assert v.sum() == pytest.approx(1.0)


def test_evidencia_cor_da_magna(magna_cores):
    ev = magna_cores.evidencia_cor()
    assert ev["concursos_da_base"] >= 3000
    assert ev["aprendido_ate"] >= 3000
    assert len(ev["ranking_completo"]) >= 5
    assert len(ev["palpite_top3"]) == 3
    assert all(c in CORES for c in ev["palpite_top3"])
    assert ev["placar"]["aplicavel"] is True
    assert ev["veredito"] in ("REAL", "RUÍDO")
    assert 0.5 <= ev["fator_confianca"] <= 1.0


def test_conhecimento_inclui_dominio_cor(magna_cores):
    kn = magna_cores.conhecimento(detalhes=True)
    assert "cor" in kn
    assert kn["cor"]["concursos_da_base"] >= 3000
    assert "placar_cor" in kn
    assert "cor_relatorio" in kn
    assert kn["cor_relatorio"]["n_registros"] >= 3000
    # o relatório cita a fonte oficial e a regra do último dígito
    assert "mazusoft" in kn["cor_relatorio"]["fonte"].lower()


def test_decisao_magna_cita_acervo_de_cores(magna_cores):
    m = magna_cores
    resultado = m.decidir_e_gerar(
        quantidade=1, registrar=False, concurso_alvo=9999)
    assert resultado["status"] == "ok"
    assert "acervo_cor_magna" in resultado
    assert resultado["acervo_cor_magna"]["digest"].startswith("sha256:")
    memoria = resultado["memoria_magna"]
    assert "cor" in memoria and "palpite_cor" in memoria
    palpite = memoria["palpite_cor"]
    assert len(palpite["ranking"]) >= 3
    cartela = resultado["cartelas"][0]
    assert "cores" in cartela["interpretacao_magna"]
    assert "afinidade_cores" in cartela["scores"]


def test_tabela_cores_do_magna_tem_data(magna_cores):
    linhas = magna_cores.tabela_cores(limite=5)
    assert len(linhas) == 5
    assert linhas[-1]["concurso"] >= 3700
    assert linhas[-1]["data"] is not None
