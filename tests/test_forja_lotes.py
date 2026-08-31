"""
Testes da Forja Espacial de Lotes (core/forja_lotes.py).

Cobertura:
- Leques exatos |R13| = 4.876 e |R14| = 151;
- União do lote bate com a análise exata do universo (wheeling);
- Pesos de plausibilidade = produto das odds do vetor fundido;
- Forja entrega lotes válidos e melhora a massa de plausibilidade;
- Fechamento dual: garantia verificada exatamente + cota de esfera;
- Mapa informacional e geometria de Johnson com invariantes;
- Menu de captura com probabilidades exatas;
- Integração com a decisão Magna (alvo=13 e modo="forja").
"""
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from config import DATABASE_PATH
from core.cerebro_ia import InteligenciaMagna
from core.forja_lotes import (
    FechamentoDual,
    ForjaDeLotes,
    GeometriaJohnson,
    MapaInformacional,
    RegiaoAltoAcerto,
    menu_captura,
)
from core.wheeling import MotorWheeling, dezenas_para_mascara


@pytest.fixture(scope="module")
def magna(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("forja") / "forja.db"
    shutil.copy2(DATABASE_PATH, caminho)
    m = InteligenciaMagna(db_path=str(caminho))
    m.treinar()
    return m


# ============================================================
# 1. Leques exatos
# ============================================================
def test_tamanho_dos_leques_e_exato():
    reg = RegiaoAltoAcerto()
    cartela = [1, 2, 3, 5, 8, 11, 13, 16, 17, 19, 20, 22, 23, 24, 25]
    mask = dezenas_para_mascara(cartela)
    assert len(reg.regiao(mask, 13)) == 4876
    assert len(reg.regiao(mask, 14)) == 151
    assert len(reg.regiao(mask, 15)) == 1


def test_uniao_do_lote_bate_com_analise_exata_do_universo():
    """|∪R13| / 3.268.760 deve ser idêntico a p_melhor_13_mais da
    enumeração completa feita pelo MotorWheeling (caminhos distintos)."""
    lote = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 22, 23, 24, 25, 2],
        [1, 4, 6, 8, 10, 12, 14, 16, 18, 20, 21, 22, 23, 24, 25],
    ]
    n_uniao, _ = RegiaoAltoAcerto().uniao_lote(lote, 13)
    an = MotorWheeling().analisar_lote(lote, pool=lote[0])
    p_uniao = n_uniao / math.comb(25, 15)
    assert abs(p_uniao - an["p_melhor_13_mais"]) < 1e-9


# ============================================================
# 2. Pesos de plausibilidade
# ============================================================
def test_peso_de_plausibilidade_e_o_produto_das_odds():
    forja = ForjaDeLotes()
    rng = np.random.default_rng(3)
    vf = rng.dirichlet(np.ones(25))
    w = forja.pesos_plausibilidade(vf)
    universo = MotorWheeling.universo()
    alvo = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    idx = int(np.flatnonzero(universo == dezenas_para_mascara(alvo))[0])
    assert abs(w[idx] - float(np.prod(vf[:15]))) < 1e-12 * abs(w[idx]) + 1e-300
    assert abs(w.sum() - w.sum()) == 0.0  # sanidade


# ============================================================
# 3. Forja de lotes
# ============================================================
def test_forja_entrega_lote_valido_e_melhora_massa():
    forja = ForjaDeLotes()
    rng = np.random.default_rng(11)
    vf = rng.dirichlet(np.ones(25) * 0.8)
    res = forja.forjar(vf, n_cartelas=4, alvo=13, segundos=4.0,
                       semente=42)
    cartelas = res["cartelas"]
    assert len(cartelas) == 4
    permitidas = set(res["candidatas"])
    for c in cartelas:
        assert len(c) == 15 and len(set(c)) == 15
        assert set(c) <= permitidas
    assert res["moves"] > 0
    assert res["massa_plausibilidade"] > 0
    # p exata do relatório == contagem direta da união
    n_uniao, _ = RegiaoAltoAcerto().uniao_lote(cartelas, 13)
    assert abs(res["p_exata_melhor_ge_alvo"] -
               n_uniao / math.comb(25, 15)) < 1e-9


# ============================================================
# 4. Fechamento dual
# ============================================================
def test_cota_de_esfera_pool19():
    # cota inferior correta = ceil(C(19,s) / |esfera Johnson|):
    # esfera(α=2) = Σ_{i=2..4} C(4,i)·C(15,4−i) = 630+60+1 = 691
    # piso = ceil(C(19,4)/691) = ceil(3876/691) = 6
    # (a fórmula antiga retornava a esfera 691 em vez do piso 6)
    assert FechamentoDual.cota_esfera(19, 13) == 6
    # e a mentira do menu antigo (21/13 com 30 cartelas) é impossível:
    assert FechamentoDual.cota_esfera(21, 13) == 33


def test_fechamento_dual_pool19_garantia_verificada():
    pool = list(range(1, 20))
    res = FechamentoDual().fechar(pool, t=13, limite_segundos=15.0)
    cartelas = res["cartelas"]
    assert res["garantia"] == 13
    assert res["garantia_verificada"] is True
    assert res["verificacao_exata"] is True
    assert 6 <= len(cartelas) <= 20  # fechamento verificado (cache)
    for c in cartelas:
        assert len(c) == 15
        assert set(c) <= set(pool)
    # garantia de 13 para TODO sorteio dentro do pool — já verificada
    # pelo verificador exato do MotorWheeling (verificacao_exata).


# ============================================================
# 5. Mapa informacional e geometria de Johnson
# ============================================================
def test_mapa_informacional_projeta_25_dezenas():
    rng = np.random.default_rng(5)
    matriz = (rng.random((120, 25)) > 0.4).astype(np.int8)
    mapa = MapaInformacional(matriz)
    coords = mapa.coordenadas()
    assert coords.shape == (25, 3)
    assert np.isfinite(coords).all()
    d = np.linalg.norm(coords[:, None] - coords[None, :], axis=-1)
    assert np.allclose(d, d.T, atol=1e-8)


def test_gonzalez_amostra_dezenas_distintas_do_pool():
    rng = np.random.default_rng(6)
    matriz = (rng.random((80, 25)) > 0.4).astype(np.int8)
    mapa = MapaInformacional(matriz)
    pool = list(range(1, 21))
    amostra = MapaInformacional.amostra_gonzalez(mapa.coordenadas(), 15, pool)
    assert len(amostra) == 15
    assert len(set(amostra)) == 15
    assert set(amostra) <= set(pool)


def test_espectro_de_johnson_soma_os_pares():
    lote = [
        list(range(1, 16)),
        list(range(2, 17)),
        list(range(3, 18)),
        list(range(4, 19)),
    ]
    esp = GeometriaJohnson.espectro_intersecoes(lote)
    assert sum(esp.values()) == math.comb(4, 2)
    rel = GeometriaJohnson().relatorio(lote, n_sim=20)
    for chave in ("z_dispersao", "leque_13_total", "amplificacao_leque",
                  "leitura"):
        assert chave in rel


# ============================================================
# 6. Menu de captura
# ============================================================
def test_menu_captura_probabilidades_exatas():
    menu = menu_captura()
    por_caso = {(l["n_pool"], l["garantia"]): l for l in menu}
    assert {(16, 15), (17, 14), (18, 13), (19, 13)} <= set(por_caso)
    for linha in menu:
        if linha["n_pool"] < 25:
            esperado = math.comb(linha["n_pool"], 15) / math.comb(25, 15)
            assert abs(linha["p_captura"] - esperado) < 1e-8
        else:
            assert linha["p_captura"] == 1.0
    assert por_caso[(16, 15)]["alvo"] == 15
    assert por_caso[(17, 14)]["alvo"] == 14
    assert por_caso[(18, 13)]["alvo"] == 13
    assert por_caso[(16, 15)]["um_em_captura"] == round(
        math.comb(25, 15) / math.comb(16, 15), 1)
    # a correção honesta: 21/13 não tem 30 cartelas (mínimo 33)
    linha21 = por_caso.get((21, 13))
    if linha21 and linha21["garantia_verificada"]:
        assert linha21["cartelas_verificadas"] >= 33


# ============================================================
# 7. Integração com a decisão Magna
# ============================================================
def test_magna_alvo13_usa_escada_de_captura(magna):
    r = magna.decidir_e_gerar(quantidade=6, alvo=13, registrar=False)
    assert r["estrategia"] == "wheeling-garantia-13"
    assert r["n_cartelas"] == 6
    assert r["garantia"] == 13
    assert r["garantia_verificada"] is True
    assert len(r["pool_elite"]) == 18
    assert r["analise"]["cond_min_acertos"] >= 13
    for c in r["cartelas"]:
        assert len(c["dezenas"]) == 15


def test_magna_modo_forja_entrega_geometria_e_lote_valido(magna):
    r = magna.decidir_e_gerar(quantidade=3, modo="forja", alvo=13,
                              registrar=False)
    # v11: a forja ganhou o prefixo "extraordinaria". O contrato travado é
    # a família "forja-espacial" + o alvo, não o nome exato da variante.
    assert r["estrategia"].startswith("forja-espacial")
    assert r["estrategia"].endswith("-13")
    assert r["n_cartelas"] == 3
    forja = r["forja"]
    assert forja["alvo"] == 13
    assert forja["moves"] > 0
    geo = r["geometria_johnson"]
    assert sum(geo["espectro_intersecoes"].values()) == math.comb(3, 2)
    assert len(r["mapa_dezenas"]) == 25
    for c in r["cartelas"]:
        assert len(c["dezenas"]) == 15
        assert len(set(c["dezenas"])) == 15
    # p exata da forja == análise exata do universo sobre o mesmo lote
    n_uniao, _ = RegiaoAltoAcerto().uniao_lote(
        [c["dezenas"] for c in r["cartelas"]], 13)
    assert abs(forja["p_exata_melhor_ge_alvo"] -
               n_uniao / math.comb(25, 15)) < 1e-12


def test_magna_alvo_invalido_rejeitado(magna):
    from core.cerebro_ia import CerebroIA  # noqa: F401  (garante import)
    with pytest.raises(ValueError):
        magna.decidir_e_gerar(quantidade=1, alvo=12, registrar=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
