"""Testes do fluxo único de decisão, memória e aprendizado da Magna."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from config import DATABASE_PATH
from core.cerebro_ia import CerebroIA, InteligenciaMagna
from core.conferencia import _safe_int


@pytest.fixture(scope="module")
def magna_decisao(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("magna") / "magna.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho))
    resultado = magna.decidir_e_gerar(
        quantidade=1,
        registrar=True,
        concurso_alvo=9999,
    )
    return magna, resultado


def test_nome_publico_unico_preserva_compatibilidade():
    assert InteligenciaMagna is CerebroIA


def test_decisao_assimila_todos_os_conhecimentos(magna_decisao):
    _, resultado = magna_decisao
    assert resultado["status"] == "ok"
    assert resultado["identidade"] == "Inteligência Magna"
    assert resultado["decisao_unica"] is True
    assert resultado["n_cartelas"] == 1
    assert resultado["decisao_id"] is not None
    # v11.4 — o acervo de abertura (base histórica inteira) entrou como
    # conhecimento assimilado: são 7 fontes de leitura dentro da Magna.
    assert len(resultado["fontes_assimiladas"]) == 7
    assert any("acervo" in f for f in resultado["fontes_assimiladas"])
    # v11.2 — clima entrou no consenso; v11.4 — a fonte `ordem` (módulo
    # paralelo) virou `abertura`: órgão da própria Magna; v11.7 — telemetria
    # INMET por local do sorteio entrou como fonte leve.
    assert set(resultado["pesos_fontes"]) == {
        "motores", "oraculos", "espectral", "informacao", "recente",
        "fisica", "clima", "abertura", "inmet",
    }
    assert abs(sum(resultado["pesos_fontes"].values()) - 1.0) < 1e-5
    assert len(resultado["top15_magna"]) == 15
    assert all(1 <= d <= 25 for d in resultado["top15_magna"])


def test_cartela_final_tem_interpretacao_unificada(magna_decisao):
    _, resultado = magna_decisao
    cartela = resultado["cartelas"][0]
    assert len(cartela["dezenas"]) == 15
    assert len(set(cartela["dezenas"])) == 15
    interpretacao = cartela["interpretacao_magna"]
    assert set(interpretacao["contribuicoes_fontes"]) == set(
        resultado["pesos_fontes"])
    assert 0 <= interpretacao["convergencia_media"] <= 1
    assert 0 <= interpretacao["filtros_avancados"]["score_avancado"] <= 1


def test_decisao_e_persistida_em_uma_trilha(magna_decisao):
    magna, resultado = magna_decisao
    historico = magna.get_historico_magna(1)
    assert historico[0]["id"] == resultado["decisao_id"]
    assert historico[0]["concurso_alvo"] == 9999
    assert historico[0]["status"] == "aguardando"


def test_resultado_real_fecha_ciclo_e_aprende_uma_vez(magna_decisao):
    magna, resultado = magna_decisao
    antes = dict(magna.pesos_fontes_magna)
    aprendizagem = magna.aprender_resultado_magna(9999, list(range(1, 16)))
    assert len(aprendizagem["decisoes_aprendidas"]) == 1
    assert set(aprendizagem["decisoes_aprendidas"][0]["acertos_fontes"]) == set(antes)
    assert all(0 <= n <= 15 for n in
               aprendizagem["decisoes_aprendidas"][0]["acertos_fontes"].values())
    assert magna.get_historico_magna(1)[0]["status"] == "conferida"
    # Idempotência: uma nova conferência não duplica o aprendizado.
    repetida = magna.aprender_resultado_magna(9999, list(range(1, 16)))
    assert repetida["decisoes_aprendidas"] == []
    assert resultado["decisao_id"] is not None


def test_blob_numpy_legado_e_decodificado_corretamente():
    assert _safe_int(b"\x01\x00\x00\x00\x00\x00\x00\x00") == 1
    assert _safe_int(b"\x19\x00\x00\x00\x00\x00\x00\x00") == 25
    assert _safe_int(b"15") == 15


def test_ciclo_autonomo_chama_aprendizado_e_decisao_com_assinaturas_corretas(
        tmp_path, monkeypatch):
    caminho = tmp_path / "ciclo.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho), n_cartelas=1)
    chamadas = {}

    monkeypatch.setattr(
        magna._ingestor, "buscar_concurso_caixa", lambda concurso: {"numero": concurso})
    monkeypatch.setattr(
        magna._ingestor, "extrair_dezenas", lambda _: list(range(1, 16)))
    monkeypatch.setattr(
        magna._ingestor, "extrair_premios", lambda _: {11: 7.0, 12: 14.0, 13: 35.0})
    monkeypatch.setattr(
        magna, "_conferir", lambda concurso, dezenas, premios: {
            "status": "ok", "melhor_acertos": 9,
            "media_acertos": 9.0, "total_ganho": 0,
        })

    def aprender(concurso, conferencia, dezenas):
        chamadas["aprender"] = (concurso, len(dezenas))
        return {"status": "ok"}

    def decidir(**kwargs):
        chamadas["decidir"] = kwargs
        return {"cartelas": [{"dezenas": list(range(1, 16)), "scores": {}}]}

    monkeypatch.setattr(magna, "_aprender", aprender)
    monkeypatch.setattr(magna, "decidir_e_gerar", decidir)
    monkeypatch.setattr(
        magna, "_salvar_fila", lambda concurso, cartelas:
        chamadas.setdefault("fila", (concurso, len(cartelas))))

    resultado = magna.executar_ciclo(5000)
    assert resultado["status"] == "completo"
    assert chamadas["aprender"] == (5000, 15)
    assert chamadas["decidir"]["concurso_alvo"] == 5001
    assert chamadas["fila"] == (5001, 1)


def test_gerar_otimas_respeita_vetor_unificado_da_magna(tmp_path):
    caminho = tmp_path / "override.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho), n_cartelas=1)
    magna.treinar()
    vetor = np.zeros(25, dtype=float)
    # Força o ranking nas dezenas 11–25 para provar que o override entra.
    vetor[10:] = 1.0
    res = magna.gerar_otimas(n_cartelas=1, vetor_override=vetor)
    assert set(range(11, 26)).issubset(set(res["pool_elite"]))


def test_ciclo_pos_sorteio_assimila_e_planeja(tmp_path):
    caminho = tmp_path / "pos.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho), n_cartelas=8)
    out = magna.ciclo_pos_sorteio_caixa()
    assert out["status"] == "ok"
    assert magna.treinado is True
    assert out["plano"]["modo_recomendado"] == "wheeling-garantia-14"
    assert "autocritica" in out


def test_inmet_e_fonte_do_consenso(magna_decisao):
    magna, resultado = magna_decisao
    # v11.7 — telemetria INMET integrada à Magna como fonte leve (sem dados
    # o vetor é uniforme: fonte neutra, nunca inventa medição).
    assert "inmet" in magna._FONTES_MAGNA_DEFAULT
    assert "inmet" in resultado["pesos_fontes"]
    assert "inmet" in magna.get_status()["inteligencia_magna"]["pesos_fontes"]
    assert magna.get_status()["inmet"]["n_registros"] == 0
    fontes, *_ = magna._fontes_assimiladas_magna()
    vetor_inmet = fontes["inmet"]
    assert len(vetor_inmet) == 25
    # vetor normalizado para o consenso (soma = 1, uniforme sem telemetria)
    assert abs(float(vetor_inmet.sum()) - 1.0) < 1e-6
    assert np.allclose(vetor_inmet, np.ones(25) / 25.0, atol=1e-6)


def test_aprendizado_grava_episodio_de_retencao(magna_decisao):
    magna, _ = magna_decisao
    ret = magna.get_retencao()
    assert "metricas" in ret
    assert "prototipos" in ret


def test_estimativa_proximo_concurso_usa_fallback_do_banco(tmp_path, monkeypatch):
    """O box 'Próximo Concurso' não pode ficar zerado quando a fonte falha."""
    from core.data_loader import DataLoader
    caminho = tmp_path / "estimativa.db"
    shutil.copy2(DATABASE_PATH, caminho)
    loader = DataLoader(db_path=str(caminho))
    ultimo_local = loader.db.get_ultimo_concurso()
    assert ultimo_local > 0

    # Fonte externa totalmente indisponível → banco local responde.
    monkeypatch.setattr(loader, "buscar_ultimo_resultado", lambda: None)
    est = loader.buscar_estimativa_premio()
    assert est is not None
    assert est["proximo_concurso"] == ultimo_local + 1
    assert est["fonte_estimativa"] == "banco_local"

    # Fonte devolve resultado sem 'proximoConcurso' → deriva de numero + 1.
    monkeypatch.setattr(
        loader, "buscar_ultimo_resultado",
        lambda: {"numero": 4000, "listaDezenas": [], "proximoConcurso": 0},
    )
    est = loader.buscar_estimativa_premio()
    assert est["proximo_concurso"] == 4001
    assert est["fonte_estimativa"] == "derivado_ultimo_resultado"
