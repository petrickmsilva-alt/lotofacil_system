"""
Validação de gerar_otimas() — o Cérebro como motor único.

Roda como:
    pytest tests/test_otimas.py
    python tests/test_otimas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.cerebro_ia import CerebroIA


@pytest.fixture(scope="module")
def cerebro():
    c = CerebroIA()
    c.treinar()
    return c


def test_n1_exaustao_unica(cerebro):
    r = cerebro.gerar_otimas(1)
    assert r["estrategia"] == "exaustao-unica"
    assert r["n_cartelas"] == 1
    assert len(set(r["cartelas"][0]["dezenas"])) == 15
    a = r["analise"]
    assert abs(a["p_melhor_15"] - 1 / 3_268_760) < 1e-12
    assert abs(a["p_melhor_14_mais"] - 151 / 3_268_760) < 1e-12


def test_n3_exaustao_diversa(cerebro):
    r = cerebro.gerar_otimas(3)
    assert r["estrategia"] == "exaustao-diversa"
    cs = [set(x["dezenas"]) for x in r["cartelas"]]
    overs = [len(cs[i] & cs[j])
             for i in range(len(cs)) for j in range(i + 1, len(cs))]
    assert len(cs) == 3
    assert all(o <= 13 for o in overs)


def test_n8_wheeling_garantia14(cerebro):
    r = cerebro.gerar_otimas(8)
    assert r["estrategia"] == "wheeling-garantia-14"
    assert r["n_cartelas"] == 8
    assert r["garantia"] == 14
    assert r["custo"] == 28.0
    assert r["analise"].get("cond_min_acertos") == 14


def test_n12_wheeling_mais_excedente(cerebro):
    r = cerebro.gerar_otimas(12)
    assert r["n_cartelas"] == 12


def test_verdade_honesta_presente(cerebro):
    r = cerebro.gerar_otimas(1)
    assert "3.268.760" in r["verdade_honesta"]
    assert "21.800" in r["verdade_honesta"]


# ----------------------------------------------------------------------
# Modo script legado
# ----------------------------------------------------------------------
def _rodar_script():
    ok_contagem = {"pass": 0, "fail": 0}

    def check(nome, cond):
        print("  {} {}".format("✅" if cond else "❌", nome))
        ok_contagem["pass" if cond else "fail"] += 1

    c = CerebroIA()
    c.treinar()

    print("== 1. n=1 → exaustão única ==")
    r1 = c.gerar_otimas(1)
    check("estratégia exaustao-unica", r1["estrategia"] == "exaustao-unica")
    check("1 cartela com 15 dezenas únicas",
          r1["n_cartelas"] == 1
          and len(set(r1["cartelas"][0]["dezenas"])) == 15)
    a1 = r1["analise"]
    check("P(15) = 1/3.268.760",
          abs(a1["p_melhor_15"] - 1 / 3_268_760) < 1e-12)
    check("P(≥14) = 151/3.268.760",
          abs(a1["p_melhor_14_mais"] - 151 / 3_268_760) < 1e-12)

    print("== 2. n=3 → exaustão diversa ==")
    r3 = c.gerar_otimas(3)
    cs = [set(x["dezenas"]) for x in r3["cartelas"]]
    overs = [len(cs[i] & cs[j])
             for i in range(len(cs)) for j in range(i + 1, len(cs))]
    check("3 cartelas diversificadas (sobreposições {} ≤ 13)".format(overs),
          len(cs) == 3 and all(o <= 13 for o in overs))

    print("== 3. n=8 → wheeling garantia 14 ==")
    r8 = c.gerar_otimas(8)
    check("estratégia wheeling-garantia-14",
          r8["estrategia"] == "wheeling-garantia-14")
    check("8 cartelas · garantia 14 · R$ 28,00",
          r8["n_cartelas"] == 8 and r8["garantia"] == 14
          and r8["custo"] == 28.0)
    check("mínimo garantido = 14 (condicional à captura)",
          r8["analise"].get("cond_min_acertos") == 14)

    print("== 4. n=12 → wheeling + excedente ==")
    r12 = c.gerar_otimas(12)
    check("12 cartelas (8 wheeling + 4 exaustão)", r12["n_cartelas"] == 12)

    print("== 5. Verdade honesta ==")
    check("probabilidades imutáveis presentes",
          "3.268.760" in r1["verdade_honesta"]
          and "21.800" in r1["verdade_honesta"])

    print()
    print("RESULTADO: {} passaram, {} falharam".format(
        ok_contagem["pass"], ok_contagem["fail"]))
    return ok_contagem["fail"]


if __name__ == "__main__":
    sys.exit(1 if _rodar_script() else 0)
