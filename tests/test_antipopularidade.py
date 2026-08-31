"""Testes do módulo anti-popularidade (edge de RATEIO, não de acerto).

Objetivo:
- Perfil/características de cartela são invariantes (15 dezenas → comprimento fixo);
- Calibração a partir da base oficial (concursos com rateio) funciona;
- Cartela "impopular" (dezenas altas, pouca zona 1–12) recebe score MAIOR e
  estimativa de MENOS ganhadores que uma cartela "popular" (1–12 em massa);
- Vetor de impopularidade é normalizado;
- O resumo da Magna expõe a auditoria e o bônus médio estimado.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.antipopularidade import AntiPopularidade, caracteristicas
from core.cerebro_ia import InteligenciaMagna


@pytest.fixture()
def app_module():
    import app as app_mod
    app_mod.app.config["TESTING"] = True
    return app_mod


@pytest.fixture()
def client(app_module):
    with app_module.app.test_client() as test_client:
        yield test_client


def test_caracteristicas_tem_comprimento_fixo():
    cartela = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    car = caracteristicas(cartela)
    assert len(car) == 7
    assert all(isinstance(v, float) for v in car)
    assert car[0] >= 0.0  # zona 1–12
    assert len(caracteristicas([7, 8, 9, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25])) == 7


def test_calibracao_a_partir_do_banco():
    ap = AntiPopularidade()
    assert ap.n_concursos >= 60
    assert ap.calibrador._media_13 > 0
    assert ap.calibrador._media_14 > 0
    rel = ap.relatorio()
    assert rel["versao"] == "v1.0"
    assert "auto_auditoria" in rel
    assert "honestidade" in rel


def test_cartela_impopular_tem_menos_ganhadores_que_popular():
    ap = AntiPopularidade()
    popular = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    impopular = [7, 8, 9, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25]
    r_pop = ap.analisar_cartela(popular)
    r_imp = ap.analisar_cartela(impopular)
    assert r_pop["regiao"] == "popular"
    assert r_imp["regiao"] == "impopular"
    assert r_imp["score_antipopularidade"] > r_pop["score_antipopularidade"]
    assert r_imp["ganhadores_13_estimados"] < r_pop["ganhadores_13_estimados"]
    assert r_imp["bonus_rateio_estimado_x"] >= r_pop["bonus_rateio_estimado_x"]


def test_vetor_impopularidade_normalizado():
    ap = AntiPopularidade()
    v = ap.vetor_impopularidade()
    assert v.shape == (25,)
    assert np.all(np.isfinite(v))
    assert v.min() >= 0
    assert abs(float(v.sum()) - 1.0) < 1e-9


def test_magna_expoe_resumo_anti_popularidade():
    m = InteligenciaMagna(n_cartelas=1)
    cartelas = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [7, 8, 9, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25],
    ]
    res = m._resumo_antipopularidade(cartelas)
    assert res["disponivel"] is True
    assert "calibracao" in res
    assert "bonus_rateio_medio_x" in res
    assert "distribuicao_regioes" in res


def test_endpoints_de_popularidade_e_captura(client):
    r = client.get("/api/magna/popularidade")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "anti_popularidade" in data

    r2 = client.get("/api/magna/captura")
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2["status"] == "ok"
    assert "escala" in data2
    assert all("ev_esperado_lote" in c for c in data2["escala"])
