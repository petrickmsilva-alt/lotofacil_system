"""
Testes da evolução v11.3 — Padrões da Ordem Real de Sorteio
===========================================================
Trava as estatísticas (streaks, repetição condicional, regra de
exclusão), a auto-auditoria walk-forward, a persistência idempotente
e a integração da fonte 'ordem' no consenso da Magna.

Os casos sintéticos usam sequências FABRICADAS de 1ª bola com streaks
conhecidos — servem para provar que os cálculos estão corretos. Os
cenários reais (histórico completo) tendem a dar veredito RUÍDO, o que
é o comportamento honesto esperado sob independência.
"""
import os
import shutil
import sqlite3
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.padroes_ordem import (  # noqa: E402
    MotorOrdemSorteio, TOTAL, _validar_ordem,
)
from config import DATABASE_PATH  # noqa: E402


def _ordem_com_primeira(primeira, rng):
    resto = [d for d in range(1, TOTAL + 1) if d != primeira]
    rng.shuffle(resto)
    return [primeira] + resto[:14]


@pytest.fixture(scope="module")
def motor_sintetico():
    """Sequência fabricada: dezena 2 como 1ª bola 5× seguidas, depois
    padrões com repetições conhecidas (9,7 alternando; 5 duas vezes;
    3 três vezes)."""
    rng = np.random.default_rng(42)
    primeiras = [2, 2, 2, 2, 2, 9, 7, 9, 7, 5, 5, 1, 25, 13, 3, 3, 3,
                 11, 11, 4]
    ordens = [(1000 + i, _ordem_com_primeira(b, rng))
              for i, b in enumerate(primeiras)]
    return MotorOrdemSorteio(ordens=ordens)


# ------------------------------------------------------------
# Validação e persistência
# ------------------------------------------------------------
def test_validar_ordem_rejeita_invalidas():
    with pytest.raises(ValueError):
        _validar_ordem([1] * 15)                    # duplicadas
    with pytest.raises(ValueError):
        _validar_ordem([0] + list(range(2, 16)))    # zero é inválido
    with pytest.raises(ValueError):
        _validar_ordem([26] + list(range(2, 16)))   # 26 fora da faixa
    with pytest.raises(ValueError):
        _validar_ordem([1, 2, 3])                   # incompleta
    with pytest.raises(ValueError):
        _validar_ordem("01 02 03")                  # não iterável de ints
    assert _validar_ordem(list(range(1, 16))) == tuple(range(1, 16))


def test_persistencia_upsert_idempotente(tmp_path):
    caminho = tmp_path / "ordem.db"
    shutil.copy2(DATABASE_PATH, caminho)
    m = MotorOrdemSorteio(db_path=str(caminho))
    base = m.n_registros
    ordem = [9, 4, 25, 5, 2, 21, 16, 11, 24, 1, 23, 10, 3, 17, 15]
    r1 = m.aprender(999001, ordem)
    assert r1["status"] == "ok" and r1["persistido"] is True
    r2 = m.aprender(999001, ordem)  # reenvio idempotente
    assert r2["idempotente"] is True
    assert m.n_registros == base + 1
    conn = sqlite3.connect(str(caminho))
    n_db = conn.execute(
        "SELECT COUNT(*) FROM ordem_sorteio WHERE concurso=999001").fetchone()[0]
    conn.close()
    assert n_db == 1
    with pytest.raises(ValueError):
        m.aprender(999002, [1, 2, 3])               # inválida é rejeitada


def test_tabela_tem_check_e_rejeita_fora_da_faixa(tmp_path):
    caminho = tmp_path / "ordem.db"
    shutil.copy2(DATABASE_PATH, caminho)
    db_path = str(caminho)
    # motor já cria a tabela; gravar ordem com dezena 26 deve falhar
    conn = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO ordem_sorteio (concurso, b1,b2,b3,b4,b5,b6,b7,b8,"
            "b9,b10,b11,b12,b13,b14,b15) VALUES (999003, 26,2,3,4,5,6,7,8,"
            "9,10,11,12,13,14,15)")
    conn.close()


# ------------------------------------------------------------
# Estatísticas de streak e repetição (casos conhecidos)
# ------------------------------------------------------------
def test_max_streak_sintetico(motor_sintetico):
    mx = motor_sintetico.max_streak_historico()
    assert mx["dezena"] == 2
    assert mx["comprimento"] == 5
    info = motor_sintetico.streaks_primeira_bola()
    assert info[3]["maximo"] == 3
    assert info[5]["maximo"] == 2
    assert info[2]["atual"] == 0           # a sequência terminou no passado
    assert info[4]["ultimo_concurso"] == 1019  # última 1ª bola da série


def test_distribuicao_streaks(motor_sintetico):
    dist = motor_sintetico.distribuicao_streaks()
    # runs: [5×2][1×9][1×7][1×9][1×7][2×5][1×1][1×25][1×13][3×3][2×11][1×4]
    assert dist[5] == 1 and dist[3] == 1 and dist[2] == 2
    assert sum(dist.values()) == 12


def test_taxa_repeticao_global_sintetica(motor_sintetico):
    t = motor_sintetico.taxa_repeticao()
    assert t["aplicavel"] is True
    # repetições: 2-2,2-2,2-2,2-2 (4) + 5-5 (1) + 3-3,3-3 (2) + 11-11 (1) = 8
    assert t["global"]["repeticoes"] == 8
    assert t["n_transicoes"] == 19
    assert abs(t["global"]["taxa"] - 8 / 19) < 1e-4


def test_taxa_repeticao_condicional_estrutura(motor_sintetico):
    cond = motor_sintetico.taxa_repeticao()["condicional"]
    for chave in ("apos_1", "apos_2", "apos_3_mais"):
        assert chave in cond
        assert "taxa" in cond[chave] and "taxa_acaso" in cond[chave]
    # após streak 1 há muitas provas; após 3+ as transições saídas de
    # streaks ≥3: duas 2→2 (streaks 3 e 4), a saída do 5º "2" e a saída
    # do trio "3" — 4 provas, 2 repetições
    assert cond["apos_1"]["n"] > 0
    assert cond["apos_3_mais"]["n"] == 4
    assert cond["apos_3_mais"]["repeticoes"] == 2


def test_regra_exclusao_veredito_honesto(motor_sintetico):
    p = motor_sintetico.placar_regra_exclusao()
    assert p["aplicavel"] is True
    assert p["voltou"] == 8 and p["n_transicoes"] == 19
    # veredito RUÍDO é o rótulo correto quando a taxa NÃO é menor que o acaso
    assert "RUÍDO" in p["veredito"] or p["p_valor"] < 0.05


def test_regra_exclusao_dados_reais_sempre_comparados_ao_acaso():
    m = MotorOrdemSorteio(db_path=DATABASE_PATH)
    if m.n_registros < 2:
        pytest.skip("sem dados de ordem no banco de produção")
    p = m.placar_regra_exclusao()
    assert p["taxa_acaso"] == 0.04
    assert p["veredito"] in (
        "SUPORTADO — exclusão reduz frequência real",
        "RUÍDO — a dezena excluída volta na taxa do acaso")


# ------------------------------------------------------------
# Matriz, previsão e vetor de preferência
# ------------------------------------------------------------
def test_matriz_transicao_linhas_somam_1(motor_sintetico):
    m = motor_sintetico.matriz_transicao()
    assert m.shape == (25, 25)
    assert np.allclose(m.sum(axis=1), 1.0, atol=1e-9)
    # com prior Dirichlet(1), transições nunca são zero
    assert (m > 0).all()


def test_previsao_estrutura_e_trio(motor_sintetico):
    prev = motor_sintetico.previsao_primeira_bola()
    assert prev["n_registros"] == 20
    assert prev["ultima_primeira_bola"] == 4
    assert abs(sum(prev["probabilidades"].values()) - 1.0) < 1e-3
    trio = prev["trio_01_02_03"]
    assert set(trio) == {1, 2, 3}
    # dezena 2 teve 5 ocorrências — posterior maior que 1 e 3
    assert trio[2]["prob_primeira_bola"] > trio[1]["prob_primeira_bola"]
    regra = prev["regra_do_usuario"]
    assert 4 not in regra["candidatas_restantes"]
    assert len(regra["candidatas_restantes"]) == 2


def test_vetor_preferencia_normalizado(motor_sintetico):
    v = motor_sintetico.vetor_preferencia()
    assert v.shape == (25,)
    assert abs(float(v.sum()) - 1.0) < 1e-6
    assert (v > 0).all()


def test_auto_ponderacao_sem_dados_e_desconfiada():
    m_vazio = MotorOrdemSorteio(ordens=[])
    a = m_vazio.auto_ponderacao()
    assert a["aplicavel"] is False
    assert a["fator_confianca"] == 0.5
    m3 = MotorOrdemSorteio(db_path=DATABASE_PATH)
    if m3.n_registros < 31:
        a3 = m3.auto_ponderacao()
        assert a3["aplicavel"] is False  # honestidade: sem amostra, sem tese


def test_auto_ponderacao_com_dados_suficientes():
    rng = np.random.default_rng(7)
    primeiras = rng.integers(1, 26, size=120)  # acaso puro
    ordens = [(2000 + i, _ordem_com_primeira(int(b), rng))
              for i, b in enumerate(primeiras)]
    m = MotorOrdemSorteio(ordens=ordens)
    a = m.auto_ponderacao()
    assert a["aplicavel"] is True
    # sob acaso puro, lift ~1 e veredito RUÍDO com fator mínimo
    assert a["veredito"] == "RUÍDO"
    assert a["fator_confianca"] == 0.5
    assert 0.0 <= a["p_valor"] <= 1.0


def test_relatorio_completo(motor_sintetico):
    rel = motor_sintetico.relatorio()
    for chave in ("n_registros", "frequencia_primeira_bola",
                  "streak_maximo_historico", "distribuicao_streaks",
                  "taxa_repeticao", "placar_regra_exclusao",
                  "previsao", "auto_auditoria", "honestidade"):
        assert chave in rel


# ------------------------------------------------------------
# Integração com a Magna (fonte 'ordem' no consenso)
# ------------------------------------------------------------
def test_magna_fontes_incluem_ordem():
    from core.cerebro_ia import InteligenciaMagna
    m = InteligenciaMagna(n_cartelas=1)
    assert "ordem" in m._FONTES_MAGNA_DEFAULT
    assert abs(sum(m._FONTES_MAGNA_DEFAULT.values()) - 1.0) < 1e-9
    fontes, *_ = m._fontes_assimiladas_magna()
    assert "ordem" in fontes
    v = fontes["ordem"]
    assert v.shape == (25,)
    # vetor atenuado nunca é degenerado: todas as dezenas têm massa
    assert (v > 0).all()
    assert abs(float(np.asarray(v, dtype=float).sum()) - 1.0) < 1e-6


def test_magna_ordem_motor_carrega_banco():
    from core.cerebro_ia import InteligenciaMagna
    m = InteligenciaMagna(n_cartelas=1)
    assert m.ordem_motor.n_registros >= 3  # seed real 3676/3769/3770


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
