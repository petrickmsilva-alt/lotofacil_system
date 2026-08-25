"""Regressões da busca, validação e sincronização do histórico Lotofácil."""
import threading
import time

import pytest

from core.caixa_client import CaixaClient, ErroFonteResultados
from core.data_loader import DataLoader
from database.db_manager import DBManager


def resultado(numero, dezenas=None, fonte="github_snapshot", premios=True):
    dezenas = dezenas or list(range(1, 16))
    rateio = ([
        {"faixa": 1, "numeroAcertos": 15,
         "numeroDeGanhadores": 1, "valorPremio": 1000000.0},
        {"faixa": 2, "numeroAcertos": 14,
         "numeroDeGanhadores": 10, "valorPremio": 1500.0},
        {"faixa": 3, "numeroAcertos": 13,
         "numeroDeGanhadores": 100, "valorPremio": 35.0},
        {"faixa": 4, "numeroAcertos": 12,
         "numeroDeGanhadores": 1000, "valorPremio": 14.0},
        {"faixa": 5, "numeroAcertos": 11,
         "numeroDeGanhadores": 10000, "valorPremio": 7.0},
    ] if premios else [])
    return {
        "numero": numero,
        "dataApuracao": "{:02d}/08/2026".format(min(numero, 28)),
        "listaDezenas": ["{:02d}".format(d) for d in dezenas],
        "listaRateioPremio": rateio,
        "valorArrecadado": 123456.0,
        "_fonte": fonte,
        "_premios_disponiveis": bool(rateio),
    }


class ClienteFalso:
    def __init__(self, resultados, ultimo=None):
        self.resultados = dict(resultados)
        self.ultimo = ultimo or max(self.resultados)
        self._diag = {"status": "ok", "fonte": "github_snapshot",
                      "tentativas": []}

    def buscar_ultimo(self):
        return self.resultados.get(self.ultimo)

    def buscar_concurso(self, numero):
        dado = self.resultados.get(int(numero))
        if dado is None:
            self._diag = {"status": "erro", "fonte": None,
                          "tentativas": [{"erro": "indisponível"}]}
        return dado

    def diagnostico(self):
        return dict(self._diag)


def test_normaliza_formatos_oficial_guidi_e_snapshot():
    oficial = CaixaClient.normalizar({
        "numero": 10, "dataApuracao": "10/08/2026",
        "listaDezenas": list(range(1, 16)),
        "listaRateioPremio": [{"faixa": 1, "numeroAcertos": 15,
                                "numeroDeGanhadores": 2,
                                "valorPremio": 123.45}],
    }, "caixa_oficial")
    assert oficial["numero"] == 10
    assert oficial["_premios_disponiveis"] is False  # rateio parcial não é confiável

    guidi = CaixaClient.normalizar({
        "concurso": 11, "data": "11/08/2026",
        "dezenas": list(range(1, 16)),
        "premiacoes": [{"faixa": 2, "acertos": "14 Pontos",
                         "ganhadores": "1.234", "premio": "R$ 1.500,25"}],
    }, "api_guidi")
    assert guidi["listaRateioPremio"][0]["numeroAcertos"] == 14
    assert guidi["listaRateioPremio"][0]["numeroDeGanhadores"] == 1234
    assert guidi["listaRateioPremio"][0]["valorPremio"] == 1500.25

    snapshot = CaixaClient.normalizar({
        "concurso": 12, "data": "12/08/2026",
        "resultado": list(range(1, 16)),
    }, "github_snapshot")
    assert snapshot["_premios_disponiveis"] is False
    assert snapshot["listaDezenas"][0] == "01"


def test_normalizador_rejeita_dezenas_repetidas():
    with pytest.raises(ErroFonteResultados):
        CaixaClient.normalizar({
            "concurso": 1, "data": "01/01/2026",
            "resultado": [1] * 15,
        }, "teste")


def test_sincronizacao_preenche_base_e_grava_auditoria(tmp_path):
    caminho = tmp_path / "historico.db"
    cliente = ClienteFalso({n: resultado(n) for n in range(1, 4)})
    loader = DataLoader(db_path=str(caminho), client=cliente)

    relatorio = loader.atualizar_diario()
    assert relatorio["status"] == "ok"
    assert relatorio["novos"] == 3
    assert relatorio["ultimo_banco_depois"] == 3
    assert loader._descobrir_faltantes(3) == []
    status = loader.get_status_base()
    assert status["base_integra"] is True
    assert status["ultima_atualizacao"]["fonte"] == "github_snapshot"


def test_falha_de_um_concurso_e_reportada_sem_falso_sucesso(tmp_path):
    caminho = tmp_path / "parcial.db"
    cliente = ClienteFalso({1: resultado(1), 3: resultado(3)}, ultimo=3)
    loader = DataLoader(db_path=str(caminho), client=cliente)

    relatorio = loader.atualizar_diario()
    assert relatorio["status"] == "parcial"
    assert relatorio["erros"] == 1
    assert relatorio["novos"] == 2
    assert relatorio["faltantes_restantes"] == [2]


def test_fonte_atrasada_nao_regride_banco_local(tmp_path):
    caminho = tmp_path / "stale.db"
    loader_local = DataLoader(
        db_path=str(caminho),
        client=ClienteFalso({n: resultado(n) for n in range(1, 4)}),
    )
    assert loader_local.atualizar_diario()["ultimo_banco_depois"] == 3

    loader_stale = DataLoader(
        db_path=str(caminho),
        client=ClienteFalso({1: resultado(1), 2: resultado(2)}, ultimo=2),
    )
    relatorio = loader_stale.atualizar_diario()
    assert relatorio["status"] == "aviso"
    assert relatorio["ultimo_banco_depois"] == 3
    assert DBManager(str(caminho)).get_ultimo_concurso() == 3


def test_contingencia_sem_rateio_preserva_premios_existentes(tmp_path):
    caminho = tmp_path / "premios.db"
    loader = DataLoader(db_path=str(caminho), client=ClienteFalso({1: resultado(1)}))
    assert loader.processar_e_salvar(resultado(1, fonte="caixa_oficial"))
    antes = loader.db.get_premios_concurso(1)
    assert antes["premio_15"] == 1000000.0

    sem_premios = resultado(1, premios=False)
    assert loader.processar_e_salvar(sem_premios)
    depois = loader.db.get_premios_concurso(1)
    assert depois["premio_15"] == 1000000.0
    assert depois["ganhadores_15"] == 1



def test_conflito_com_resultado_local_e_rejeitado(tmp_path):
    caminho = tmp_path / "conflito.db"
    loader = DataLoader(db_path=str(caminho), client=ClienteFalso({1: resultado(1)}))
    assert loader.processar_e_salvar(resultado(1))
    conflitante = resultado(1, dezenas=list(range(2, 17)))
    assert loader.processar_e_salvar(conflitante) is False
    salvo = loader.db.get_resultado_concurso(1)
    assert [salvo["d{}".format(i)] for i in range(1, 16)] == list(range(1, 16))

def test_db_nao_engole_erro_de_persistencia(tmp_path):
    db = DBManager(str(tmp_path / "db.db"))
    with pytest.raises(ValueError):
        db.inserir_resultado((1, 2, 3))


def test_endpoint_impede_duas_atualizacoes_concorrentes(monkeypatch):
    import app as app_mod

    iniciou = threading.Event()
    liberar = threading.Event()

    def atualizacao_lenta():
        iniciou.set()
        liberar.wait(timeout=5)
        return {
            "status": "ok", "msg": "ok", "novos": 0,
            "recuperados": 0, "erros": 0,
        }

    monkeypatch.setattr(app_mod.data_loader, "atualizar_diario", atualizacao_lenta)
    app_mod.status_sistema["carregando"] = False
    app_mod.app.config["TESTING"] = True
    with app_mod.app.test_client() as client:
        primeira = client.post("/api/atualizar_dados")
        assert primeira.status_code == 202
        assert iniciou.wait(timeout=2)
        segunda = client.post("/api/atualizar_dados")
        assert segunda.status_code == 409
        liberar.set()
        limite = time.time() + 3
        while app_mod.status_sistema["carregando"] and time.time() < limite:
            time.sleep(0.02)
        assert app_mod.status_sistema["carregando"] is False


def test_javascript_do_historico_possui_funcao_de_atualizacao():
    conteudo = open("static/js/main.js", encoding="utf-8").read()
    assert "function atualizarDados()" in conteudo
    assert "'/api/atualizar_dados'" in conteudo

class RespostaFalsa:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = respostas
        self.headers = {}
        self.chamadas = []

    def mount(self, *_):
        return None

    def get(self, url, timeout=None):
        self.chamadas.append((url, timeout))
        return self.respostas[url]


def test_cliente_troca_para_contingencia_e_informa_fonte(monkeypatch):
    oficial = "https://oficial.test/lotofacil"
    guidi = "https://guidi.test/lotofacil"
    snapshot = "https://snapshot.test/lotofacil.json"
    sessao = SessaoFalsa({
        oficial: RespostaFalsa(503, {}),
        guidi + "/ultimo": RespostaFalsa(200, {
            "concurso": 20, "data": "20/08/2026",
            "dezenas": list(range(1, 16)),
        }),
    })
    monkeypatch.setattr(CaixaClient, "OFICIAL_BASE", oficial)
    monkeypatch.setattr(CaixaClient, "CONTINGENCIA_API_BASE", guidi)
    monkeypatch.setattr(CaixaClient, "CONTINGENCIA_HISTORICO", snapshot)
    client = CaixaClient(session=sessao)
    obtido = client.buscar_ultimo()
    assert obtido["numero"] == 20
    assert obtido["_fonte"] == "api_guidi"
    assert client.diagnostico()["status"] == "contingencia"
    assert [url for url, _ in sessao.chamadas] == [oficial, guidi + "/ultimo"]
