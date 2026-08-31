"""Regressões da interface unificada da Inteligência Magna v9."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture()
def app_module():
    import app as app_mod
    app_mod.app.config["TESTING"] = True
    return app_mod


@pytest.fixture()
def client(app_module):
    with app_module.app.test_client() as test_client:
        yield test_client


def test_hub_e_uma_interface_unica_sem_abas(client):
    response = client.get("/cerebro")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert 'id="magna-form"' in body
    assert 'id="magna-decidir"' in body
    assert "Uma memória. Uma análise. Uma decisão." in body
    assert 'id="cerebro-tabs"' not in body
    assert 'class="ctab' not in body


def test_menu_expoe_apenas_a_inteligencia_magna(client):
    body = client.get("/cerebro").data.decode("utf-8")
    assert "INTELIGÊNCIA ÚNICA" in body
    assert "Magna Unificada" in body
    # Os antigos recursos podem ser citados como conhecimentos assimilados,
    # mas não podem continuar como links/submenus independentes.
    for href in (
        "/cerebro#aba-gerar", "/cerebro#aba-cartela_do_dia",
        "/cerebro#aba-wheeling", "/cerebro#aba-analise",
        "/cerebro#aba-singularidade", "/cerebro#aba-auditoria",
    ):
        assert f'href="{href}"' not in body


@pytest.mark.parametrize("rota", [
    "/cerebro/central", "/gerar", "/cartela_do_dia", "/wheeling",
    "/analise", "/singularidade", "/ia_auditoria", "/fisica", "/avaliacao",
])
def test_paginas_antigas_redirecionam_para_magna(client, rota):
    response = client.get(rota)
    assert response.status_code in (301, 302, 303, 307, 308)
    assert response.headers["Location"].endswith("/cerebro")


def test_menus_do_sistema_continuam_independentes(client):
    for rota in (
        "/conferencia", "/financeiro_page", "/historico", "/premios",
    ):
        assert client.get(rota).status_code == 200, rota
    home = client.get("/")
    assert home.status_code in (301, 302, 303, 307, 308)
    assert home.headers["Location"].endswith("/cerebro")


def test_dashboard_saiu_do_menu(client):
    body = client.get("/cerebro").data.decode("utf-8")
    assert "> Dashboard<" not in body
    assert "Inteligência Magna" in body


def test_api_magna_e_a_unica_porta_de_decisao(client, app_module, monkeypatch):
    fake = {
        "status": "ok",
        "n_cartelas": 0,
        "cartelas": [],
        "concurso_alvo": 9999,
        "pool_elite": [],
        "estrategia": "exaustao-unica",
        "analise": {"p_melhor_14_mais": 0.0},
    }
    monkeypatch.setattr(app_module.magna, "decidir_e_gerar", lambda **_: fake)
    response = client.post("/api/magna/decidir", json={
        "quantidade": 1, "salvar": False,
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["resultado"]["concurso_alvo"] == 9999


def test_painel_tem_forja_auto_sem_ancoras(client):
    body = client.get("/cerebro").data.decode("utf-8")
    # v11.7 — forja automática com telemetria INMET substituiu as âncoras
    assert 'id="magna-inmet-auto"' in body
    assert 'id="magna-telemetria"' in body
    assert 'id="magna-ancoras"' not in body
    assert "/api/magna/ancoras-123" not in body
    assert "/api/magna/forja-auto" in body


def test_api_inmet_existe(client):
    """Telemetria INMET com janela de estado (sem rede: padrão São Paulo/SP)."""
    response = client.get("/api/magna/inmet")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["versao"] == "11.7-telemetria-inmet"
    assert data["local_do_sorteio"]["uf"] == "SP"
    assert data["local_do_sorteio"]["geocodigo"] == "3550308"
    assert "n_registros" in data["telemetria_banco"]


def test_api_forja_auto_existe(client, monkeypatch):
    """Contrato da rota: forja automática devolve local + telemetria + decisão."""
    import core.forja_auto as fa_mod

    class FakeAuto:
        def executar(self, **kw):
            return {
                "status": "ok",
                "local": {"cidade": "São Paulo", "uf": "SP",
                          "fonte": "padrao"},
                "telemetria": {"status": "neutro", "fonte": "padrao",
                               "telemetria": None, "condicoes_clima": None},
                "decisao": {
                    "status": "ok", "n_cartelas": 0, "cartelas": [],
                    "concurso_alvo": 9999, "pool_elite": [],
                    "estrategia": "suprema", "custo": 0.0,
                    "analise": {"p_melhor_14_mais": 0.0},
                },
            }

        def local_do_sorteio(self, **kw):
            return {"cidade": "São Paulo", "uf": "SP", "fonte": "padrao"}

    monkeypatch.setattr(fa_mod, "ForjaAutomatica", lambda **_: FakeAuto())
    response = client.post("/api/magna/forja-auto", json={
        "quantidade": 2, "salvar": False, "usar_inmet": False,
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["local_do_sorteio"]["uf"] == "SP"
    assert data["decisao"]["concurso_alvo"] == 9999


def test_cartela_do_dia_isolada_foi_desativada(client):
    response = client.get("/api/cartela_do_dia")
    assert response.status_code == 410
    assert response.get_json()["nova_rota"] == "/api/magna/decidir"


def test_financeiro_tem_botao_clear(client):
    body = client.get("/financeiro_page").data.decode("utf-8")
    assert 'id="btn-limpar-financeiro"' in body
    assert "/api/financeiro/limpar" in body


def test_api_financeiro_limpar_existe(client, app_module, monkeypatch):
    # Não toca no banco real: apenas valida contrato da rota.
    monkeypatch.setattr(app_module.financeiro, "limpar", lambda: 3)
    response = client.post("/api/financeiro/limpar")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["removidos"] == 3
    assert "resumo" in data
