"""Testes da telemetria INMET por local do sorteio (core/inmet.py).

Cobertura:
- resolução de território (cidade/UF → geocódigo IBGE + coordenadas);
- extração do local do resultado oficial da Caixa;
- client com prioridade INMET oficial → Open-Meteo → neutro (sem rede);
- persistência por concurso e consultas (por_concurso/ultima/historico);
- vetor de evidência da Magna: uniforme sem dados, tilt leve com dados;
- condições para o MotorClima (integração v11.7).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.inmet import (
    LOCAL_PADRAO, InmetClient, TelemetriaInmet, TerritorioInmet,
    extrair_local, _normalizar_cidade_uf,
)

LINHA_INMET = {
    "DT_DATA": "2026-08-30",
    "TEMP_MEDIA": 21.3,
    "UMIDADE_RELATIVA_MEDIA": 52.0,
    "PRESSAO_ATMOSFERICA_NIVEL_ESTACAO_MEDIA": 913.0,
    "VENTO_VELOCIDADE_MEDIA": 2.4,
}


def getter_inmet(url):
    if "/estacao/proxima/" in url:
        return [{"codigo": "A001", "nome": "BRASILIA (A001)"}]
    if "/estacao/diaria/" in url:
        return [dict(LINHA_INMET)]
    return None


def getter_open_meteo(url):
    if "/estacao/proxima/" in url or "/estacao/diaria/" in url:
        raise RuntimeError("INMET indisponível")
    return {
        "daily": {
            "temperature_2m_mean": [19.0, 20.0, 21.0, None, None],
            "relative_humidity_2m_mean": [48.0, 50.0, 52.0, None, None],
            "pressure_msl_mean": [912.0, 913.0, 914.0, None, None],
        }
    }


def getter_mudo(url):
    return None


# ============================================================
# 1. Território / local do sorteio
# ============================================================
@pytest.mark.parametrize("texto,esperado", [
    ("São Paulo/SP", "São Paulo/SP"),
    ("SÃO PAULO, SP", "São Paulo/SP"),
    ("Sao Paulo - SP", "São Paulo/SP"),
    ("Espaço da Sorte", "São Paulo/SP"),
    ("GO", "Goiânia/GO"),
    ("Brasilia-DF", "Brasília/DF"),
])
def test_normalizar_cidade_uf_aceita_formatos(texto, esperado):
    assert _normalizar_cidade_uf(texto) == esperado


def test_normalizar_cidade_uf_desconhecida_devolve_none():
    assert _normalizar_cidade_uf("Atlântida/XX") is None
    assert _normalizar_cidade_uf(None) is None


def test_extrair_local_do_resultado_caixa():
    bruto = {"local": "ESPAÇO DA SORTE", "cidadeUF": "São Paulo/SP",
             "numero": 3773}
    local = extrair_local(bruto)
    assert local["local"] == "ESPAÇO DA SORTE"
    assert local["cidade_uf"] == "São Paulo/SP"
    # sem local nenhum → None (cascata decide o padrão)
    assert extrair_local({"numero": 3773}) is None
    assert extrair_local(None) is None


def test_territorio_fora_da_tabela_usa_capital_da_uf():
    t = TerritorioInmet().resolver("Campinas", "Campinas/SP")
    assert t["uf"] == "SP"
    assert t["fonte_territorio"] == "uf_capital"
    assert t["geocodigo"] == "3550308"
    # sem nada → padrão São Paulo/SP
    p = TerritorioInmet().resolver(None, None)
    assert p["uf"] == LOCAL_PADRAO["uf"]
    assert p["fonte_territorio"] == "padrao"


def test_local_sorteio_sem_cidade_uf_cai_no_alias():
    """Caixa pode trazer só `local` (ex.: 'ESPAÇO DA SORTE') sem cidadeUF."""
    local = extrair_local({"local": "ESPAÇO DA SORTE", "numero": 3773})
    assert local["cidade_uf"] == "São Paulo/SP"
    t = TerritorioInmet().resolver(local["local"], local["cidade_uf"])
    assert t["uf"] == "SP"
    assert t["geocodigo"] == "3550308"


# ============================================================
# 2. Cliente: INMET oficial → Open-Meteo → neutro
# ============================================================
def test_telemetria_inmet_oficial_por_local_do_sorteio():
    client = InmetClient(getter=getter_inmet)
    dados = client.telemetria("ESPAÇO DA SORTE", "São Paulo/SP")
    assert dados["status"] == "ok"
    assert dados["fonte"] == "inmet_oficial"
    assert dados["cidade"] == "São Paulo"
    assert dados["geocodigo"] == "3550308"
    assert dados["estacao"]["codigo"] == "A001"
    assert dados["temperatura"] == pytest.approx(21.3)
    assert dados["pressao"] == pytest.approx(913.0 / 1013.25, abs=1e-3)
    assert dados["umidade"] == pytest.approx(52.0)
    assert dados["vento"] == pytest.approx(2.4)
    assert dados["erro"] is None


def test_telemetria_contingencia_open_meteo():
    client = InmetClient(getter=getter_open_meteo)
    dados = client.telemetria("ESPAÇO DA SORTE", "São Paulo/SP")
    assert dados["status"] == "contingencia"
    assert dados["fonte"] == "open_meteo"
    assert dados["temperatura"] is not None
    assert dados["pressao"] is not None
    assert dados["diagnostico"]["inmet"]["status"] == "erro"


def test_telemetria_neutra_sem_rede():
    client = InmetClient(getter=getter_mudo)
    dados = client.telemetria("ESPAÇO DA SORTE", "São Paulo/SP")
    assert dados["status"] == "neutro"
    assert dados["fonte"] == "padrao"
    assert dados["temperatura"] is None
    assert dados["erro"] is not None
    # contrato uniforme entre os três ramos: local do sorteio preservado
    assert dados["local"] == "ESPAÇO DA SORTE"
    assert dados["cidade_uf"] == "São Paulo/SP"
    assert dados["n_observacoes"] == 0
    # nunca fabrica medição: os valores ficam vazios, não padrões fictícios
    assert all(dados[k] is None for k in
               ("temperatura", "pressao", "umidade", "vento"))


# ============================================================
# 3. Persistência
# ============================================================
def test_telemetria_persiste_por_concurso_e_recupera(tmp_path):
    tel = TelemetriaInmet(str(tmp_path / "inmet.db"))
    dados = InmetClient(getter=getter_inmet).telemetria(
        "ESPAÇO DA SORTE", "Goiânia/GO")
    ident = tel.registrar(dados, concurso=3774)
    assert ident is not None

    reg = tel.por_concurso(3774)
    assert reg["concurso"] == 3774
    assert reg["cidade_uf"] == "Goiânia/GO"
    assert reg["fonte"] == "inmet_oficial"
    assert reg["temperatura"] == pytest.approx(21.3)

    ult = tel.ultima()
    assert ult["id"] == ident
    assert tel.historico(5)[0]["id"] == ident

    resumo = tel.resumo()
    assert resumo["n_registros"] == 1
    assert resumo["fontes"] == {"inmet_oficial": 1}
    assert resumo["ultima"]["cidade_uf"] == "Goiânia/GO"


def test_condicoes_para_clima_vem_da_telemetria(tmp_path):
    tel = TelemetriaInmet(str(tmp_path / "inmet2.db"))
    assert tel.condicoes_para_clima() is None
    cliente = InmetClient(getter=getter_inmet)
    dados = cliente.telemetria("ESPAÇO DA SORTE", "São Paulo/SP")
    tel.registrar(dados, concurso=3775)
    cond = tel.condicoes_para_clima()
    assert cond["temperatura"] == pytest.approx(21.3)
    assert cond["pressao"] is not None
    assert cond["fonte"].startswith("inmet-")


# ============================================================
# 4. Vetor de evidência para o consenso
# ============================================================
def test_vetor_inmet_uniforme_sem_telemetria(tmp_path):
    tel = TelemetriaInmet(str(tmp_path / "inmet3.db"))
    v = tel.vetor_inmet()
    assert abs(float(v.sum()) - 25.0) < 1e-9
    assert np.allclose(v, np.ones(25))


def test_vetor_inmet_tilt_leve_respeita_teto_10(tmp_path):
    tel = TelemetriaInmet(str(tmp_path / "inmet4.db"))
    cliente = InmetClient(getter=getter_inmet)
    dados = cliente.telemetria("ESPAÇO DA SORTE", "São Paulo/SP")
    # força pressão baixa (ar menos denso) sem passar pelo cliente
    dados["pressao"] = 0.88
    tel.registrar(dados, concurso=3776)
    v = tel.vetor_inmet()
    assert abs(float(v.sum()) - 25.0) < 1e-9
    # teto ±10% (antes da renormalização o clip já limita a 1.10/0.90)
    assert v.max() <= 1.10 * 1.0001
    assert v.min() >= 0.90 * 0.9999
    # dezenas ímpares levemente acima das pares (tilt honesto, não previsão)
    impares = [v[d - 1] for d in range(1, 26, 2)]
    pares = [v[d - 1] for d in range(2, 26, 2)]
    assert sum(impares) > sum(pares)
