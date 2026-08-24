"""
Validação da Fase 3 (auditoria de módulos, filtros e navegação).
Roda com:  python3 tests/test_fase3.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

ok_contagem = {"pass": 0, "fail": 0}


def check(nome, cond):
    print("  {} {}".format("✅" if cond else "❌", nome))
    ok_contagem["pass" if cond else "fail"] += 1


print("== 1. Todos os módulos core importam ==")
import pkgutil
import core
falhas = []
for mod in sorted(pkgutil.iter_modules(core.__path__)):
    try:
        __import__("core." + mod.name)
    except Exception as e:
        falhas.append((mod.name, str(e)))
check("10 módulos importam sem erro (falhas: {})".format(falhas or "nenhuma"),
      not falhas)

print("== 2. Órfãos removidos ==")
removidos = ["filtros_gaussianos", "markov_engine", "fisica_quantica",
             "covering_designs"]
check("nenhum módulo órfão sobrou",
      all(m.name not in removidos
          for m in pkgutil.iter_modules(core.__path__)))

print("== 3. Filtro recalibrado aprova >90% dos sorteios reais ==")
from core.cerebro_ia import IngestorDados, MotorGaussiano
matriz, _ = IngestorDados("database/lotofacil.db").carregar_matriz()
g = MotorGaussiano(matriz)
aprov = sum(1 for i in range(len(matriz))
            if g.filtrar([int(x) + 1 for x in np.where(matriz[i] == 1)[0]])[0])
taxa = aprov / len(matriz)
check("taxa de aprovação = {:.1%} (antes 66,3%)".format(taxa), taxa > 0.90)
check("métrica exposta: taxa_aprovacao_historica = {}".format(
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
# vetor crescente → top deve ser exatamente as 15 maiores dezenas (11-25)
check("ranking é exato (top = dezenas 11–25)",
      top[0]["dezenas"] == list(range(11, 26)))

print("== 5. Config recalibrado ==")
from config import SOMA_MIN, SOMA_MAX, PRIMOS_MIN, PRIMOS_MAX
check("soma {}–{} cobre p1–p99 reais".format(SOMA_MIN, SOMA_MAX),
      SOMA_MIN <= 155 and SOMA_MAX >= 235)
check("primos {}–{}".format(PRIMOS_MIN, PRIMOS_MAX),
      PRIMOS_MIN <= 3 and PRIMOS_MAX >= 8)

print()
print("RESULTADO: {} passaram, {} falharam".format(
    ok_contagem["pass"], ok_contagem["fail"]))
sys.exit(1 if ok_contagem["fail"] else 0)
