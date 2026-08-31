"""Testes do Laboratório Magna (aprendizado dinâmico + auditoria + exploração)."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from config import DATABASE_PATH
from core.laboratorio_magna import LaboratorioMagna


@pytest.fixture(scope="module")
def lab(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("lab") / "lab.db"
    shutil.copy2(DATABASE_PATH, caminho)
    return LaboratorioMagna(db_path=str(caminho))


def test_laboratorio_inicializa_lendo_a_base(lab):
    assert lab.n >= 3000
    assert lab.matriz.shape[1] == 25
    assert len(lab.historico) == lab.n


def test_auditor_audita_cartela_valida(lab):
    cartela = [1, 2, 3, 5, 8, 11, 13, 16, 17, 19, 20, 22, 23, 24, 25]
    r = lab.auditor.auditar(cartela)
    assert r["validado"] is True if "validado" in r else True
    assert r["valida"] is True
    assert r["dezenas"] == sorted(cartela)
    assert "prob_acertos_exatas" in r
    assert r["prob_acertos_exatas"]["13"] > 0


def test_auditor_audita_lote(lab):
    lote = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 22, 23, 24, 25, 2],
    ]
    r = lab.auditor.auditar_lote(lote)
    assert r["n_cartelas"] == 2
    assert r["n_aceitaveis"] >= 1   # ao menos uma não é classificada como RUIM
    assert "veredito_geral" in r


def test_auditor_reconhece_jogo_repetido_historico(lab):
    # pega o último sorteio e audita: ele deve aparecer como "já saiu 15"
    ultima = lab.historico[-1]
    r = lab.auditor.auditar(ultima)
    assert r["jogo_ja_saiu_15"] is True
    assert r["veredito"] in ("RUIM", "OBSERVACAO", "ACEITA")


def test_laboratorio_benchmark_walk_forward(lab):
    r = lab.rodar_benchmark(n_testes=12, janela=30, n_aleatorio=20,
                            persistir=False)
    assert r["status"] == "ok"
    assert r["n_testes"] == 12
    assert r["baseline_aleatoria"] > 0
    for nome, linha in r["estimativas"].items():
        assert linha["media_acertos"] > 0
        assert "veredito" in linha
        assert "quarentena" in linha
    # baseline "uniforme" nunca entra em quarentena
    assert r["estimativas"]["uniforme"]["quarentena"] is False


def test_laboratorio_jogos_ruins(lab):
    r = lab.jogos_ruins(persistir=False)
    if r["n"] == 0:
        # em uma base bem espalhada isso é aceitável; o contrato é ter lista vazia
        assert "jogos" in r
    else:
        for j in r["jogos"]:
            assert len(j["dezenas"]) == 15
            assert j["repetido_15"] >= 0


def test_magna_expoe_auditoria_na_decisao():
    from core.cerebro_ia import InteligenciaMagna
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        dbf = os.path.join(td, "m.db")
        shutil.copy2(DATABASE_PATH, dbf)
        m = InteligenciaMagna(db_path=dbf, n_cartelas=1)
        r = m.decidir_e_gerar(quantidade=1, registrar=False, alvo=None)
        assert r["status"] == "ok"
        cart = r["cartelas"][0]
        assert "auditoria" in cart["interpretacao_magna"]
        assert "auditoria_cartelas_magna" in r
        assert r["auditoria_cartelas_magna"]["disponivel"] is True


@pytest.fixture()
def app_module():
    import app as app_mod
    app_mod.app.config["TESTING"] = True
    return app_mod


@pytest.fixture()
def client(app_module):
    with app_module.app.test_client() as tc:
        yield tc


def test_endpoint_lab_estado(client):
    r = client.get("/api/magna/lab")
    assert r.status_code == 200
    d = r.get_json()
    assert d is not None
    assert d.get("status") != "erro"
