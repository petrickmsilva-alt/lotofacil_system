"""Testes da forja automática com telemetria INMET (core/forja_auto.py).

Cobertura:
- cascata do local do sorteio (Caixa → banco → padrão);
- telemetria injetável sem rede (getter) e persistência;
- integração com o MotorClima da Magna (definir_condicoes);
- forja suprema chamada com os parâmetros do pipeline automático;
- falhas de rede nunca quebram a forja (clima neutro).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.forja_auto import ForjaAutomatica
from core.inmet import InmetClient


def getter_inmet(url):
    if "/estacao/proxima/" in url:
        return [{"codigo": "A001", "nome": "BRASILIA (A001)"}]
    if "/estacao/diaria/" in url:
        return [{"DT_DATA": "2026-08-30", "TEMP_MEDIA": 21.3,
                 "UMIDADE_RELATIVA_MEDIA": 52.0,
                 "PRESSAO_ATMOSFERICA_NIVEL_ESTACAO_MEDIA": 913.0,
                 "VENTO_VELOCIDADE_MEDIA": 2.4}]
    return None


class FakeClima:
    def __init__(self):
        self.definidas = []

    def definir_condicoes(self, **kw):
        self.definidas.append(kw)
        return {"status": "ok"}


class FakeMagna:
    def __init__(self, falhar=False):
        self.clima = FakeClima()
        self.treinado = True
        self.chamadas = []
        self.falhar = falhar

    def decidir_suprema(self, **kw):
        if self.falhar:
            raise RuntimeError("forja indisponível")
        self.chamadas.append(kw)
        return {
            "status": "ok",
            "n_cartelas": 4,
            "cartelas": [{"dezenas": list(range(1, 16))}],
            "concurso_alvo": 3774,
            "pool_elite": list(range(1, 18)),
            "estrategia": "suprema-v11-inmet-auto",
            "custo": 14.0,
            "analise": {"p_melhor_14_mais": 0.000123},
        }


@pytest.fixture()
def auto(tmp_path):
    auto_obj = ForjaAutomatica(
        magna=None,
        client=InmetClient(getter=getter_inmet),
        db_path=str(tmp_path / "auto.db"),
    )
    return auto_obj


# ============================================================
# 1. Local do sorteio (cascata)
# ============================================================
def test_local_do_sorteio_vem_do_resultado_caixa(auto):
    local = auto.local_do_sorteio(
        usar_rede=False,
        resultado_caixa={"local": "ESPAÇO DA SORTE",
                         "cidadeUF": "Goiânia/GO", "numero": 3773})
    assert local["cidade"] == "Goiânia"
    assert local["uf"] == "GO"
    assert local["fonte"] == "caixa_remota"


def test_local_do_sorteio_cai_no_banco_e_depois_no_padrao(auto):
    assert auto.local_do_sorteio(usar_rede=False)["fonte"] == "padrao"
    # registra uma telemetria anterior de outro local → banco vira fonte
    dados = InmetClient(getter=getter_inmet).telemetria(
        "ESPAÇO DA SORTE", "Goiânia/GO")
    auto.telemetria.registrar(dados, concurso=3772)
    local = auto.local_do_sorteio(usar_rede=False)
    assert local["fonte"] == "banco_local"
    assert local["uf"] == "GO"


# ============================================================
# 2. Telemetria + integração com o MotorClima
# ============================================================
def test_coletar_telemetria_persiste_e_entrega_condicoes(auto):
    local = auto.local_do_sorteio(usar_rede=False)
    parcela = auto.coletar_telemetria(local, concurso=3773, salvar=True)
    assert parcela["status"] == "ok"
    assert parcela["fonte"] == "inmet_oficial"
    assert parcela["condicoes_clima"]["temperatura"] == pytest.approx(21.3)
    assert auto.telemetria.resumo()["n_registros"] == 1


def test_executar_forja_auto_usa_telemetria_no_clima(auto):
    magna = FakeMagna()
    auto.magna = magna
    resumo = auto.executar(quantidade=4, orcamento=50.0, alvo=13,
                           perfil="conservador", segundos_forja=10.0,
                           salvar=False, usar_inmet=True)
    assert resumo["status"] == "ok"
    assert resumo["local"]["fonte"] == "padrao"  # sem Caixa nem banco
    assert resumo["telemetria"]["fonte"] == "inmet_oficial"
    # clima da Magna recebeu as condições do INMET do local
    assert len(magna.clima.definidas) == 1
    cond = magna.clima.definidas[0]
    assert cond["temperatura"] == pytest.approx(21.3)
    # forja suprema chamada com os parâmetros do pipeline automático
    assert len(magna.chamadas) == 1
    chamada = magna.chamadas[0]
    assert chamada["quantidade"] == 4
    assert chamada["perfil"] == "conservador"
    assert chamada["registrar"] is False
    assert resumo["decisao"]["estrategia"] == "suprema-v11-inmet-auto"
    assert resumo["telemetria"]["telemetria"]["_registro_id"] is not None


def test_executar_sem_inmet_nao_consulta_cliente(auto):
    magna = FakeMagna()
    auto.magna = magna
    resumo = auto.executar(quantidade=2, alvo=14, salvar=False,
                           usar_inmet=False)
    assert resumo["status"] == "ok"
    assert resumo["telemetria"]["status"] == "neutro"
    # sem condições, o MotorClima não é tocado
    assert magna.clima.definidas == []
    assert auto.telemetria.resumo()["n_registros"] == 0


def test_persistir_telemetria_e_independente_das_cartelas(auto):
    magna = FakeMagna()
    auto.magna = magna
    # cartelas NÃO salvas, mas telemetria auditável SIM (contrato v11.7)
    resumo = auto.executar(quantidade=2, alvo=13, salvar=False,
                           usar_inmet=True, persistir_telemetria=True)
    assert resumo["status"] == "ok"
    assert auto.telemetria.resumo()["n_registros"] == 1
    assert auto.telemetria.ultima()["local"] == "Espaço da Sorte (padrão)"
    assert auto.telemetria.ultima()["cidade_uf"] == "São Paulo/SP"
    # e pode ser desligada explicitamente
    resumo2 = auto.executar(quantidade=2, alvo=13, salvar=True,
                            usar_inmet=True, persistir_telemetria=False)
    assert resumo2["status"] == "ok"
    assert auto.telemetria.resumo()["n_registros"] == 1


def test_executar_falha_na_forja_devolve_erro_sem_levantar(auto):
    auto.magna = FakeMagna(falhar=True)
    resumo = auto.executar(quantidade=2, alvo=13, salvar=False,
                           usar_inmet=True)
    assert resumo["status"] == "erro"
    assert "forja indisponível" in resumo["msg"]
