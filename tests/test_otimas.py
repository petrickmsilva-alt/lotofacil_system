"""
Validação de gerar_otimas() — o Cérebro como motor único.
Roda com:  python3 tests/test_otimas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math

ok_contagem = {"pass": 0, "fail": 0}


def check(nome, cond):
    print("  {} {}".format("✅" if cond else "❌", nome))
    ok_contagem["pass" if cond else "fail"] += 1


from core.cerebro_ia import CerebroIA

c = CerebroIA()
c.treinar()

print("== 1. n=1 → exaustão única: A cartela ótima do universo ==")
r1 = c.gerar_otimas(1)
check("estratégia exaustao-unica", r1["estrategia"] == "exaustao-unica")
check("exatamente 1 cartela com 15 dezenas únicas",
      r1["n_cartelas"] == 1
      and len(set(r1["cartelas"][0]["dezenas"])) == 15)
a1 = r1["analise"]
check("P(15) da cartela única = 1/3.268.760 (exato, hipergeométrica)",
      abs(a1["p_melhor_15"] - 1 / 3_268_760) < 1e-12)
check("P(≥14) = 151/3.268.760 (exato, hipergeométrica)",
      abs(a1["p_melhor_14_mais"]
          - 151 / 3_268_760) < 1e-12)

print("== 2. n=3 → exaustão diversa (sobreposição ≤ 13) ==")
r3 = c.gerar_otimas(3)
cs = [set(x["dezenas"]) for x in r3["cartelas"]]
overs = [len(cs[i] & cs[j]) for i in range(len(cs)) for j in range(i + 1, len(cs))]
check("3 cartelas diversificadas (sobreposições {} ≤ 13)".format(overs),
      len(cs) == 3 and all(o <= 13 for o in overs))

print("== 3. n=8 → wheeling com garantia 14 condicional ==")
r8 = c.gerar_otimas(8)
check("estratégia wheeling-garantia-14",
      r8["estrategia"] == "wheeling-garantia-14")
check("8 cartelas · garantia 14 · custo R$ 28,00",
      r8["n_cartelas"] == 8 and r8["garantia"] == 14
      and r8["custo"] == 28.0)
a8 = r8["analise"]
check("condicional à captura: mínimo garantido = 14",
      a8.get("cond_min_acertos") == 14)

print("== 4. n=12 → wheeling + excedente por exaustão ==")
r12 = c.gerar_otimas(12)
check("12 cartelas (8 wheeling + 4 exaustão)", r12["n_cartelas"] == 12)

print("== 5. Verdade honesta sempre presente ==")
check("campo verdade_honesta com probabilidades imutáveis",
      "3.268.760" in r1["verdade_honesta"] and "21.800" in r1["verdade_honesta"])

print()
print("RESULTADO: {} passaram, {} falharam".format(
    ok_contagem["pass"], ok_contagem["fail"]))
sys.exit(1 if ok_contagem["fail"] else 0)
