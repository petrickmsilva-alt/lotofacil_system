"""
Validação do MotorWheeling — matemática exata, sem fé cega.

Roda como:
    pytest tests/test_wheeling.py        # suíte pytest
    python tests/test_wheeling.py        # script legado (sys.exit)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from core.wheeling import MotorWheeling


w = MotorWheeling()


def test_familia_exata_construcao_verificacao_exaustiva():
    """N ≤ 20: construção ⌈16/(N−15)⌉ e verificação exaustiva da garantia."""
    for n in range(16, 21):
        pool = list(range(1, n + 1))
        esperado_t = 31 - n
        esperado_q = math.ceil(16 / (n - 15))
        res = w.fechamento_exato(pool)
        ok, exato = w.verificar(res["cartelas"], pool, esperado_t)
        assert ok and exato, "N={}: garantia não verificada".format(n)
        assert len(res["cartelas"]) == esperado_q, \
            "N={}: esperado {} cartelas, obtido {}".format(
                n, esperado_q, len(res["cartelas"]))


def test_otimo_provado_n17_sete_cartelas_falham():
    """7 complementos-pares cobrem ≤ 14 dezenas → 7 cartelas NÃO garantem 14."""
    pool17 = list(range(1, 18))
    sete = [sorted(set(pool17) - set(pool17[2 * i:2 * i + 2])) for i in range(7)]
    ok7, _ = w.verificar(sete, pool17, 14)
    assert not ok7, "7 cartelas não deveriam garantir 14 em pool 17"


def test_greedy_n18_garantia14():
    """Greedy Johnson: 14 pontos em pool de 18 (α=2, verificado exaustivamente)."""
    pool18 = list(range(1, 19))
    res = w.fechamento_guloso(pool18, 14, max_cartelas=40, limite_segundos=60)
    ok, exato = w.verificar(res["cartelas"], pool18, 14)
    assert ok and exato, "greedy não atingiu garantia 14 em N=18"
    lb = math.ceil(math.comb(18, 15) / (1 + 15 * 3))
    assert lb <= len(res["cartelas"]) <= lb * 2.5


def test_analise_marginal_igual_hipergeometrica():
    """P(15) de uma cartela qualquer = 1/C(25,15)."""
    cartela = list(range(1, 16))
    an = w.analisar_lote([cartela], list(range(1, 18)))
    p15 = an["dist_melhor_acertos"].get("15", 0) / an["universo"]
    assert abs(p15 - 1 / math.comb(25, 15)) < 1e-12


def test_prob_captura_hipergeometrica():
    n = 17
    p = w.prob_captura(n)
    p_hip = math.comb(n, 15) * math.comb(25 - n, 0) / math.comb(25, 15)
    assert abs(p - p_hip) < 1e-15


def test_menu_exato_consistente():
    menu = w.menu_exato()
    assert len(menu) >= 7
    for linha in menu:
        assert 16 <= linha["n_pool"] <= 25
        assert linha["garantia"] == 31 - linha["n_pool"]
        assert linha["cartelas"] == math.ceil(16 / (linha["n_pool"] - 15))


# ----------------------------------------------------------------------
# Modo script legado (mesmo relatório impresso de antes)
# ----------------------------------------------------------------------
def _rodar_script():
    ok_contagem = {"pass": 0, "fail": 0}

    def check(nome, cond):
        print("  {} {}".format("✅" if cond else "❌", nome))
        ok_contagem["pass" if cond else "fail"] += 1

    print("== 1. Família exata α=1: construção e verificação exaustiva ==")
    for n in range(16, 21):
        pool = list(range(1, n + 1))
        esperado_t = 31 - n
        esperado_q = math.ceil(16 / (n - 15))
        res = w.fechamento_exato(pool)
        ok, exato = w.verificar(res["cartelas"], pool, esperado_t)
        check("N={}: {} cartelas (esperado {}), garantia {} verificada exaustiva={}"
              .format(n, len(res["cartelas"]), esperado_q, esperado_t, ok and exato),
              ok and exato and len(res["cartelas"]) == esperado_q)

    print("== 2. Ótimo provado: N=17 com 7 cartelas NÃO garante 14 ==")
    pool17 = list(range(1, 18))
    sete = [sorted(set(pool17) - set(pool17[2 * i:2 * i + 2])) for i in range(7)]
    ok7, _ = w.verificar(sete, pool17, 14)
    check("7 cartelas falham a garantia (confirma que 8 é mínimo)", not ok7)

    print("== 3. Greedy: 14 pontos em pool de 18 (α=2, exato) ==")
    pool18 = list(range(1, 19))
    res = w.fechamento_guloso(pool18, 14, max_cartelas=40, limite_segundos=60)
    ok, exato = w.verificar(res["cartelas"], pool18, 14)
    print("     → {} cartelas, cobertura {:.1f}%".format(
        len(res["cartelas"]), res["cobertura_pct"]))
    check("garantia 14 verificada exaustivamente em N=18", ok and exato)

    print("== 4. Análise exata: marginal de 1 cartela = hipergeométrica ==")
    cartela = list(range(1, 16))
    an = w.analisar_lote([cartela], list(range(1, 18)))
    p15 = an["dist_melhor_acertos"].get("15", 0) / an["universo"]
    check("P(15) exata = 1/C(25,15) ({:.2e})".format(p15),
          abs(p15 - 1 / math.comb(25, 15)) < 1e-12)

    print("== 5. Probabilidade de captura bate com hipergeométrica ==")
    n = 17
    p = w.prob_captura(n)
    p_hip = math.comb(n, 15) / math.comb(25, 15)
    check("P(pool 17 ⊇ sorteio) = {:.6f}%".format(p * 100), abs(p - p_hip) < 1e-15)

    print("== 6. Menu da família exata ==")
    for linha in w.menu_exato():
        print("     pool {:>2} → garantia {:>2} com {:>2} cartelas "
              "(R$ {:>6.2f}) | captura 1 em {:>9,.0f}"
              .format(linha["n_pool"], linha["garantia"], linha["cartelas"],
                      linha["custo"], linha["um_em"]))
    check("menu consistente", len(w.menu_exato()) >= 7)

    print()
    print("RESULTADO: {} passaram, {} falharam".format(
        ok_contagem["pass"], ok_contagem["fail"]))
    return ok_contagem["fail"]


if __name__ == "__main__":
    sys.exit(1 if _rodar_script() else 0)
