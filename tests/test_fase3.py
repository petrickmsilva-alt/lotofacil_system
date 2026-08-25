"""
Validação da Fase 3 (auditoria de módulos, filtros e navegação).

Roda como:
    pytest tests/test_fase3.py
    python tests/test_fase3.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pkgutil

import numpy as np
import pytest

import core
from core.cerebro_ia import IngestorDados, MotorGaussiano


MATRIZ, _ = IngestorDados(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "database", "lotofacil.db")
).carregar_matriz()


def test_todos_modulos_core_importam():
    falhas = []
    for mod in sorted(pkgutil.iter_modules(core.__path__)):
        try:
            __import__("core." + mod.name)
        except Exception as e:  # pragma: no cover
            falhas.append((mod.name, str(e)))
    assert not falhas, "módulos com erro de import: {}".format(falhas)


def test_orfaus_removidos():
    removidos = ["filtros_gaussianos", "markov_engine",
                 "fisica_quantica", "covering_designs"]
    existentes = {m.name for m in pkgutil.iter_modules(core.__path__)}
    for nome in removidos:
        assert nome not in existentes, \
            "módulo órfão {} ainda existe".format(nome)


@pytest.fixture(scope="module")
def gaussiano():
    return MotorGaussiano(MATRIZ)


def test_filtro_aprovacao_histórica(gaussiano):
    aprov = sum(
        1 for i in range(len(MATRIZ))
        if gaussiano.filtrar(
            [int(x) + 1 for x in np.where(MATRIZ[i] == 1)[0]])[0]
    )
    taxa = aprov / len(MATRIZ)
    assert taxa > 0.90, "taxa de aprovação {:.1%} ≤ 90%".format(taxa)
    assert abs(gaussiano.taxa_aprovacao_historica - taxa) < 1e-3


def test_heavyweight_avalia_universo():
    from core.heavyweight_engine import MotorExaustaoUniverso
    m = MotorExaustaoUniverso()
    assert len(m.universo) == 3_268_760
    v = np.linspace(0.01, 0.05, 25)
    top = m.top_n(v, 5)
    assert len(top) == 5
    assert all(len(t["dezenas"]) == 15 for t in top)
    # vetor crescente → top é o conjunto das 15 maiores dezenas (11–25)
    assert top[0]["dezenas"] == list(range(11, 26))


def test_config_recalibrado():
    from config import SOMA_MIN, SOMA_MAX, PRIMOS_MIN, PRIMOS_MAX
    assert SOMA_MIN <= 155 and SOMA_MAX >= 235
    assert PRIMOS_MIN <= 3 and PRIMOS_MAX >= 8


# ----------------------------------------------------------------------
# Modo script legado
# ----------------------------------------------------------------------
def _rodar_script():
    ok_contagem = {"pass": 0, "fail": 0}

    def check(nome, cond):
        print("  {} {}".format("✅" if cond else "❌", nome))
        ok_contagem["pass" if cond else "fail"] += 1

    print("== 1. Todos os módulos core importam ==")
    falhas = []
    for mod in sorted(pkgutil.iter_modules(core.__path__)):
        try:
            __import__("core." + mod.name)
        except Exception as e:
            falhas.append((mod.name, str(e)))
    check("módulos importam sem erro (falhas: {})".format(falhas or "nenhuma"),
          not falhas)

    print("== 2. Órfãos removidos ==")
    removidos = ["filtros_gaussianos", "markov_engine",
                 "fisica_quantica", "covering_designs"]
    check("nenhum módulo órfão sobrou",
          all(m.name not in removidos
              for m in pkgutil.iter_modules(core.__path__)))

    print("== 3. Filtro recalibrado aprova >90% dos sorteios reais ==")
    g = MotorGaussiano(MATRIZ)
    aprov = sum(
        1 for i in range(len(MATRIZ))
        if g.filtrar([int(x) + 1 for x in np.where(MATRIZ[i] == 1)[0]])[0]
    )
    taxa = aprov / len(MATRIZ)
    check("taxa de aprovação = {:.1%}".format(taxa), taxa > 0.90)
    check("métrica taxa_aprovacao_historica = {}".format(
        g.taxa_aprovacao_historica),
        abs(g.taxa_aprovacao_historica - taxa) < 1e-3)

    print("== 4. Heavyweight avalia o universo exato ==")
    from core.heavyweight_engine import MotorExaustaoUniverso
    m = MotorExaustaoUniverso()
    check("universo tem 3.268.760 combinações", len(m.universo) == 3_268_760)
    v = np.linspace(0.01, 0.05, 25)
    top = m.top_n(v, 5)
    check("top-5 retorna 5 cartelas de 15 dezenas",
          len(top) == 5 and all(len(t["dezenas"]) == 15 for t in top))
    check("ranking é exato (top = dezenas 11–25)",
          top[0]["dezenas"] == list(range(11, 26)))

    print("== 5. Config recalibrado ==")
    from config import SOMA_MIN, SOMA_MAX, PRIMOS_MIN, PRIMOS_MAX
    check("soma {}–{} cobre p1–p99".format(SOMA_MIN, SOMA_MAX),
          SOMA_MIN <= 155 and SOMA_MAX >= 235)
    check("primos {}–{}".format(PRIMOS_MIN, PRIMOS_MAX),
          PRIMOS_MIN <= 3 and PRIMOS_MAX >= 8)

    print()
    print("RESULTADO: {} passaram, {} falharam".format(
        ok_contagem["pass"], ok_contagem["fail"]))
    return ok_contagem["fail"]


if __name__ == "__main__":
    sys.exit(1 if _rodar_script() else 0)
