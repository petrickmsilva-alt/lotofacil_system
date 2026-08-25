"""
Regressão do hub unificado do Cérebro IA (Fase 6).

Garante que:
- /cerebro é o hub com abas e layout completo;
- cada aba é carregável como fragmento (?fragmento=1) SEM a sidebar;
- todas as rotas de geração/análise unificadas respondem 200.

Roda como:
    pytest tests/test_hub_unificado.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture()
def client():
    # import tardio para já ter o sys.path configurado
    import app as A
    A.app.config["TESTING"] = True
    with A.app.test_client() as c:
        yield c


ABAS = [
    "/cerebro/central?fragmento=1",
    "/gerar?fragmento=1",
    "/cartela_do_dia?fragmento=1",
    "/wheeling?fragmento=1",
    "/analise?fragmento=1",
    "/singularidade?fragmento=1",
    "/ia_auditoria?fragmento=1",
]


def test_hub_tem_layout_completo_e_abas(client):
    r = client.get("/cerebro")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert 'class="sidebar"' in body
    assert 'id="cerebro-tabs"' in body
    # todas as abas declaradas
    for aba in ["central", "gerar", "cartela_do_dia", "wheeling",
                "analise", "singularidade", "auditoria"]:
        assert 'data-aba="{}"'.format(aba) in body


@pytest.mark.parametrize("rota", ABAS)
def test_fragmentos_das_abas_sem_sidebar(client, rota):
    r = client.get(rota)
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    # fragmento é só conteúdo: não pode vir com a navegação lateral do app.
    # (Evitamos o termo solto "sidebar", que aparece em classes de cartelas.)
    assert 'class="sidebar"' not in body
    assert "<!DOCTYPE html>" not in body


def test_menus_independentes_ainda_existem(client):
    """Conferência, Financeiro, Histórico e Prêmios continuam no menu."""
    for rota in ["/conferencia", "/financeiro_page", "/historico",
                 "/premios", "/", "/avaliacao"]:
        r = client.get(rota)
        assert r.status_code == 200, rota


@pytest.mark.parametrize("rota,aba", [
    ("/gerar", "aba-gerar"),
    ("/cartela_do_dia", "aba-cartela_do_dia"),
    ("/wheeling", "aba-wheeling"),
    ("/analise", "aba-analise"),
    ("/singularidade", "aba-singularidade"),
    ("/ia_auditoria", "aba-auditoria"),
])
def test_rotas_legadas_redirecionam_para_hub(client, rota, aba):
    """Acessar as rotas legadas SEM ?fragmento=1 redireciona para a aba do
    hub /cerebro; com ?fragmento=1 devolvem o miolo (200 sem sidebar)."""
    r = client.get(rota)
    assert r.status_code in (301, 302, 308), rota
    assert aba in r.headers.get("Location", "")
    frag = client.get(rota + "?fragmento=1")
    assert frag.status_code == 200
    assert 'class="sidebar"' not in frag.data.decode("utf-8")
