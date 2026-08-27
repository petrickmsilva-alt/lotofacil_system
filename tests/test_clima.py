"""
Testes da evolução v11.2 — Clima Físico do Sorteio
====================================================
Trava os três testes matemáticos sobre o histórico
(data/historico_clima_lotofacil.csv, 100 concursos 3200-3299),
a shrinkage do vetor de clima, o aprendizado contínuo
(upsert idempotente) e a auto-auditoria walk-forward.

Valores de referência validados de forma independente
(cálculo manual separado do motor) em 2026-08-27.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clima_lotofacil import MotorClima  # noqa: E402

CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "historico_clima_lotofacil.csv"
)


@pytest.fixture(scope="module")
def motor():
    m = MotorClima(csv_path=CSV, usar_web=False)
    assert m.n_registros == 100
    return m


@pytest.fixture(scope="module")
def t1(motor):
    return motor.teste_impares_pressao(limiar=0.917)


@pytest.fixture(scope="module")
def t2(motor):
    return motor.teste_soma_umidade()


@pytest.fixture(scope="module")
def t3(motor):
    return motor.teste_frequencia_temperatura()


# ------------------------------------------------------------
# T1 — Ímpares × Pressão
# ------------------------------------------------------------
def test_t1_amostras(t1):
    assert t1["aplicavel"] is True
    # limiar 0.917: 74 concursos abaixo, 26 acima
    assert t1["pressao_baixa"]["n"] == 74
    assert t1["pressao_alta"]["n"] == 26


def test_t1_medias(t1):
    # validado independentemente sobre o CSV real
    assert abs(t1["pressao_baixa"]["media"] - 7.7973) < 0.01
    assert abs(t1["pressao_alta"]["media"] - 7.9231) < 0.01
    # direção: sob pressão baixa há MENOS ímpares (diferença ~-0.13)
    assert t1["diferenca"] < 0
    # z pequeno → veredito RUÍDO (honestidade)
    assert abs(t1["z"]) < 1.96
    assert t1["veredito"] == "RUÍDO"


# ------------------------------------------------------------
# T2 — Soma × Umidade
# ------------------------------------------------------------
def test_t2_faixas(t2):
    assert t2["aplicavel"] is True
    assert t2["faixas"]["baixa_lt_45"]["n"] == 23
    assert t2["faixas"]["media_45_50"]["n"] == 39
    assert t2["faixas"]["alta_gt_50"]["n"] == 38


def test_t2_medias(t2):
    # validado independentemente sobre o CSV real
    assert abs(t2["faixas"]["baixa_lt_45"]["media"] - 192.8261) < 0.01
    assert abs(t2["faixas"]["media_45_50"]["media"] - 198.4615) < 0.01
    assert abs(t2["faixas"]["alta_gt_50"]["media"] - 192.4211) < 0.01
    # a faixa do MEIO (45-50%) concentra as somas maiores
    assert t2["faixa_destaque"] == "media_45_50"
    # fronteira, não sinal (z < 1.96)
    assert t2["veredito"] in ("FRONTEIRA", "RUÍDO")


# ------------------------------------------------------------
# T3 — Frequência individual × Temperatura
# ------------------------------------------------------------
def test_t3_divisao(t3):
    assert t3["aplicavel"] is True
    assert t3["n_frio"] == 50
    assert t3["n_quente"] == 50
    assert abs(t3["limiar_temperatura"] - 21.35) < 0.01


def _todas_dezenas(m):
    """Detalhamento frio/quente completo (recalculado do dataset)."""
    lim = m._limiar_temperatura()
    rows = m._com_dezenas()
    frio = [r for r in rows if r["temperatura"] < lim]
    quente = [r for r in rows if r["temperatura"] >= lim]
    out = []
    for d in range(1, 26):
        kf = sum(1 for r in frio if d in r["dezenas"])
        kq = sum(1 for r in quente if d in r["dezenas"])
        out.append({"dezena": d, "frio": kf, "quente": kq,
                    "diferenca": kf - kq})
    return out


def test_t3_dezenas_validadas(t3, motor):
    mapa = {x["dezena"]: x for x in t3["top_diferencia"]}
    # dezena 22: mais no QUENTE (23 × 37) — SINAL z≈-2.86
    assert mapa[22]["frio"] == 23 and mapa[22]["quente"] == 37
    # dezena 16: mais no FRIO (42 × 29) — SINAL z≈+2.86
    assert mapa[16]["frio"] == 42 and mapa[16]["quente"] == 29
    # dezena 17: praticamente PLANA (24 × 25). A "descoberta" 30×21 do
    # relato externo NÃO se reproduz nos dados reais.
    det = {x["dezena"]: x for x in _todas_dezenas(motor)}
    assert (det[17]["frio"], det[17]["quente"]) == (24, 25)
    # dezena 19: mais no QUENTE (25 × 36) — direção OPosta à do relato
    assert (det[19]["frio"], det[19]["quente"]) == (25, 36)


# ------------------------------------------------------------
# Vetor de clima — shrinkage e limites
# ------------------------------------------------------------
def test_vetor_clima_shape_e_shrinkage(motor):
    v = motor.vetor_clima(usar_web=False)
    assert v.shape == (25,)
    assert abs(float(v.mean()) - 1.0) < 1e-9
    # teto: nenhuma dezena sai de ±10% do uniforme
    assert float(v.max()) <= 1.1000001
    assert float(v.min()) >= 0.8999999


def test_vetor_clima_sem_dados_neutro(tmp_path):
    m = MotorClima(csv_path=str(tmp_path / "nao_existe.csv"),
                   usar_web=False)
    v = m.vetor_clima(usar_web=False)
    assert np.allclose(v, 1.0)
    rep = m.testes_fisicos()
    assert not rep["T1_impares_pressao"]["aplicavel"]


def test_top5_clima(motor):
    top5 = motor.top5_clima(usar_web=False)
    assert len(top5) == 5
    assert all(1 <= d <= 25 for d in top5)
    # com os dados atuais o clima favorece 22/19/8
    assert top5[0] in (22, 16, 8, 19)


# ------------------------------------------------------------
# Aprendizado contínuo — upsert idempotente
# ------------------------------------------------------------
def test_aprender_novo_e_upsert(tmp_path):
    p = str(tmp_path / "clima.csv")
    m = MotorClima(csv_path=p, usar_web=False)
    r1 = m.aprender(4000, 20.0, 0.91, 55, data="01/09/2026",
                    dezenas=list(range(1, 16)))
    assert r1["novo"] is True and r1["n_registros"] == 1

    # re-ingestão idêntica → byte-idêntico, não duplica
    import hashlib
    h1 = hashlib.md5(open(p, "rb").read()).hexdigest()
    r2 = m.aprender(4000, 20.0, 0.91, 55, data="01/09/2026",
                    dezenas=list(range(1, 16)))
    h2 = hashlib.md5(open(p, "rb").read()).hexdigest()
    assert r2["novo"] is False and r2["n_registros"] == 1
    assert h1 == h2

    # atualização de valores → recalcula sem duplicar
    r3 = m.aprender(4000, 21.5, 0.92, 60, data="01/09/2026")
    m2 = MotorClima(csv_path=p, usar_web=False)
    assert m2.n_registros == 1
    assert m2.registros[0]["temperatura"] == 21.5

    # registro inválido (16 dezenas) → aceita clima, descarta dezenas
    r4 = m.aprender(4001, 22.0, 0.91, 40,
                    dezenas=list(range(1, 17)))
    m3 = MotorClima(csv_path=p, usar_web=False)
    assert m3.n_registros == 2
    assert m3.registros[1]["dezenas"] == []


# ------------------------------------------------------------
# Auto-auditoria walk-forward
# ------------------------------------------------------------
def test_auto_ponderacao(motor):
    auto = motor.auto_ponderacao()
    assert auto["aplicavel"] is True
    assert auto["n_avaliados"] == 40
    assert auto["baseline_aleatorio"] == 9.0
    assert 0.5 <= auto["fator_confianca"] <= 1.0
    # nos dados atuais: 9.125 de média (levemente acima do aleatório)
    assert abs(auto["media_acertos_clima"] - 9.125) < 0.05


# ------------------------------------------------------------
# Previsão — fallback sem web
# ------------------------------------------------------------
def test_clima_previsto_fallback(motor):
    prev = motor.clima_previsto(usar_web=False)
    assert prev["fonte"] in ("media_recente_14", "padrao_sao_paulo")
    assert 15.0 <= prev["temperatura"] <= 30.0
    assert 0.85 <= prev["pressao"] <= 0.98
    assert 20.0 <= prev["umidade"] <= 80.0


def test_definir_condicoes_manual(motor):
    motor.definir_condicoes(temperatura=18.0, pressao=0.905,
                            umidade=35.0)
    prev = motor.clima_previsto()
    assert prev["temperatura"] == 18.0
    assert prev["pressao"] == 0.905
    assert prev["umidade"] == 35.0
    assert prev["fonte"] == "definida_manualmente"
    motor.definir_condicoes()  # limpa
    assert motor.clima_previsto(usar_web=False)["fonte"] != \
        "definida_manualmente"


# ------------------------------------------------------------
# Integração — Magna assimilou a fonte
# ------------------------------------------------------------
def test_magna_fontes_incluem_clima():
    from core.cerebro_ia import InteligenciaMagna
    m = InteligenciaMagna(n_cartelas=1)
    try:
        assert "clima" in m._FONTES_MAGNA_DEFAULT
        assert abs(sum(m._FONTES_MAGNA_DEFAULT.values()) - 1.0) < 1e-9
        fontes, *_ = m._fontes_assimiladas_magna()
        assert "clima" in fontes
        v = fontes["clima"]
        assert v.shape == (25,)
        assert abs(float(v.sum()) - 1.0) < 1e-6
        status = m.get_status()
        assert status["clima"]["registros"] == 100
    finally:
        pass
