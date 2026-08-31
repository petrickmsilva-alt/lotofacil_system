"""
Testes do motor de fechamentos VERIFICADOS (core/cobertura.py).

O princípio destes testes é o da PROVA EXAUSTIVA: nenhum fechamento
é aceito por amostragem — todos os C(n,s) alvos do espaço dual são
enumerados e checados.
"""
import math

import pytest

from core import cobertura as cov


# ----------------------------------------------------------------
# 1. Matemática básica
# ----------------------------------------------------------------
def test_perfil_cartela_bate_hipergeometrica_oficial():
    from core.odds_reais import tabela_cartela, TOTAL_COMB
    perf = {l["acertos"]: l for l in tabela_cartela()}
    assert TOTAL_COMB == 3_268_760
    # frações oficiais divulgadas pela Caixa
    assert round(perf[13]["um_em"], 0) == 692
    assert round(perf[14]["um_em"], 0) == 21_792
    assert perf[15]["um_em"] == 3_268_760
    assert perf[11]["combinacoes"] == math.comb(15, 11) * math.comb(10, 4)


def test_cota_inferior_e_piso_combinatorio():
    # α=1: família ótima provada ceil(16/s)
    assert cov.cota_inferior(16, 15) == 16
    assert cov.cota_inferior(17, 14) == 8
    assert cov.cota_inferior(18, 13) == 6
    assert cov.cota_inferior(19, 12) == 4
    assert cov.cota_inferior(20, 11) == 4
    # o caso que a escada antiga errava: 21/13 não pode ter 30 cartelas
    assert cov.cota_inferior(21, 13) == 33


def test_tamanho_esfera_contagem_direta():
    # α=1: esfera = todos os s-subconjuntos com interseção ≥1 com o bloco
    # = C(n,s) − C(n−s, s)
    n, s, alpha = 18, 3, 1
    assert cov.tamanho_esfera(n, s, alpha) == math.comb(n, s) - math.comb(n - s, s)
    # α=s: só o próprio bloco (interseção plena)
    assert cov.tamanho_esfera(n, s, s) == 1
    # caso α=2 do 19/13: esfera 691 = C(4,2)C(15,2)+C(4,3)C(15,1)+1
    assert cov.tamanho_esfera(19, 4, 2) == 6*105 + 4*15 + 1


# ----------------------------------------------------------------
# 2. Verificação exata — o coração do motor
# ----------------------------------------------------------------
@pytest.mark.parametrize("n,t,cartelas_max", [
    (16, 15, 16),
    (17, 14, 8),
    (18, 13, 6),
    (19, 13, 25),
    (20, 12, 8),
    (21, 12, 30),
])
def test_fechamento_construido_e_provado_exaustivamente(n, t, cartelas_max):
    res = cov.fechamento_verificado(n, t, tempo_max=60, sementes=2)
    assert res["garantia_verificada"] is True
    assert res["alvos_cobertos"] == res["total_alvos"] == math.comb(
        n, n - 15)
    assert res["cartelas"] <= cartelas_max
    assert res["cartelas"] >= res["cota_inferior"]
    # cada cartela tem 15 dezenas dentro de um pool canônico
    pool = list(range(1, n + 1))
    cartelas = cov.blocos_para_cartelas(res["blocos"], pool)
    for c in cartelas:
        assert len(c) == 15 and len(set(c)) == 15
        assert set(c) <= set(pool)


def test_verificador_recusa_cobertura_falsa():
    # um único bloco NÃO cobre o caso 21/13: o verificador precisa dizer não
    n, t = 21, 13
    s = n - 15
    alvos = cov.mascaras_subconjuntos(n, s)
    falso = [alvos[0]]  # 1 bloco só
    ok, cobertos, total = cov.verificar_blocos(falso, n, s, t + n - 30,
                                               alvos=alvos)
    assert ok is False
    assert cobertos < total


def test_cache_reverificado_em_carga():
    laudo = cov.reverificar_todo_cache()
    # todo fechamento gravado tem de sobreviver à prova exaustiva
    for linha in laudo:
        assert linha["verificado"] is True, linha
        assert linha["alvos_cobertos"] == linha["total_alvos"], linha


# ----------------------------------------------------------------
# 3. Garantia incondicional (n=25): qualquer sorteio do volante
# ----------------------------------------------------------------
def test_fechamento_incondicional_25_11():
    res = cov.fechamento_verificado(25, 11, tempo_max=120, sementes=2)
    assert res["garantia_verificada"] is True
    assert res["cartelas"] >= res["cota_inferior"]
    # prova independente: cada uma das 3.268.760 apostas do universo
    # oficial (15 dezenas) é coberta por ≥11 acertos em alguma cartela
    from core.wheeling import MotorWheeling
    universo = MotorWheeling.universo()
    pool = list(range(1, 26))
    cartelas = cov.blocos_para_cartelas(res["blocos"], pool)
    import numpy as np
    masks = np.array(
        [int(np.bitwise_or.reduce(
            np.uint32(1) << np.array([d - 1 for d in c], dtype=np.uint32)))
         for c in cartelas], dtype=np.uint32)
    pior = 15
    CHUNK = 400_000
    for i in range(0, len(universo), CHUNK):
        parte = universo[i:i + CHUNK]
        melhor = np.zeros(len(parte), dtype=np.int32)
        for m in masks:
            np.maximum(melhor, cov.popcount(parte & m), out=melhor)
        pior = min(pior, int(melhor.min()))
    assert pior >= 11


# ----------------------------------------------------------------
# 4. Integração com a antiga interface (FechamentoDual / menu)
# ----------------------------------------------------------------
def test_fechamento_dual_interface_antiga_provado():
    from core.forja_lotes import FechamentoDual
    pool = list(range(1, 20))
    res = FechamentoDual().fechar(pool, t=13, limite_segundos=60)
    assert res["garantia_verificada"] is True
    assert res["verificacao_exata"] is True
    assert 6 <= len(res["cartelas"]) <= 25
    for c in res["cartelas"]:
        assert set(c) <= set(pool)


def test_menu_captura_so_vende_garantia_provada():
    from core.forja_lotes import menu_captura
    menu = menu_captura()
    achou_21_13 = False
    for linha in menu:
        if linha["n_pool"] < 25:
            p = math.comb(linha["n_pool"], 15) / math.comb(25, 15)
            assert abs(linha["p_captura"] - p) < 5e-9
        else:
            assert linha["tipo"] == "incondicional"
            assert linha["p_captura"] == 1.0
        if linha["garantia_verificada"]:
            assert linha["cartelas_verificadas"] >= linha["cota_inferior"]
        if linha["n_pool"] == 21 and linha["garantia"] == 13:
            achou_21_13 = True
    # a mentira antiga (21/13 com 30) sumiu: ou está verificada com ≥33,
    # ou aparece honestamente como não construída (sem número inventado)
    assert achou_21_13
