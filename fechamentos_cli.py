"""
CLI de fechamentos VERIFICADOS + probabilidades reais da Lotofácil.

Exemplos:
    python fechamentos_cli.py tabela                 # escada completa provada
    python fechamentos_cli.py fechar 20 13           # fechamento verificado
    python fechamentos_cli.py fechar 20 13 --pool 1 2 3 ... (20 dezenas)
    python fechamentos_cli.py odds                   # frações exatas por cartela
    python fechamentos_cli.py chance 15 0.10         # cartelas p/ 10% de 15 pts
    python fechamentos_cli.py ev                     # valor esperado real
    python fechamentos_cli.py reverificar            # prova exaustiva do cache
"""
import argparse
import math
import sys

from core import cobertura as cov
from core import odds_reais as odds


def _pool(n, args):
    if args.pool:
        pool = sorted(set(int(x) for x in args.pool))
        if len(pool) != n or any(d < 1 or d > 25 for d in pool):
            print(f"ERRO: --pool precisa ter {n} dezenas distintas entre 1 e 25")
            sys.exit(1)
        return pool
    return list(range(1, n + 1))


def cmd_tabela(args):
    from core.forja_lotes import menu_captura
    print(f"{'n':>3} {'gar':>3} | {'cartelas':>8} {'cotaInf':>7} | "
          f"{'custo':>9} | {'captura':>12} | tipo")
    print("-" * 72)
    for l in menu_captura():
        cap = ("incondicional" if l["tipo"] == "incondicional"
               else f"1 em {l['um_em_captura']:,.0f}")
        cart = str(l["cartelas_verificadas"]) if l["garantia_verificada"] else "—"
        custo = (f"R$ {l['custo_teorico']:,.2f}"
                 if l["custo_teorico"] else "—")
        print(f"{l['n_pool']:>3} {l['garantia']:>3} | {cart:>8} "
              f"{l['cota_inferior']:>7} | {custo:>9} | {cap:>12} | "
              f"{l['tipo']}")
    print("\nLegenda: gar = pontos garantidos SE o pool capturar as 15 "
          "sorteadas\n(para n=25 a garantia é incondicional). 'cotaInf' é "
          "o piso matemático\nde cartelas; nenhum fechamento pode ter menos.")


def cmd_fechar(args):
    n, t = args.n_pool, args.garantia
    res = cov.fechamento_verificado(
        n, t, tempo_max=args.tempo, sementes=args.sementes, verboso=False)
    if not res.get("garantia_verificada"):
        print(f"Não foi possível construir/provar o fechamento {n}/{t} "
              f"no tempo dado. Cota inferior: {cov.cota_inferior(n, t)}.")
        sys.exit(2)
    pool = _pool(n, args)
    cartelas = cov.blocos_para_cartelas(res["blocos"], pool)
    p_cap = cov.prob_captura(n) if n < 25 else 1.0
    print(f"FECHAMENTO {n} dezenas → garantia {t} "
          f"({'INCONDICIONAL' if n == 25 else f'captura 1 em {1/p_cap:,.0f}'})")
    print(f"  {res['cartelas']} cartelas · R$ {res['cartelas']*3.5:,.2f} · "
          f"cota inferior {res['cota_inferior']} · "
          f"prova exaustiva de {res['total_alvos']:,} alvos"
          f"{' (cache)' if res.get('do_cache') else ''}")
    for i, c in enumerate(cartelas, 1):
        print(f"  {i:2d}: " + " ".join(f"{d:02d}" for d in c))


def cmd_odds(args):
    print("Probabilidades EXATAS por cartela (hipergeométrica, C(25,15)=3.268.760):")
    for l in odds.tabela_cartela():
        print(f"  {l['acertos']} acertos: 1 em {l['um_em']:>12,.1f}  "
              f"({l['combinacoes']:>7,} combinações)  prêmio {l['tipo']}: "
              f"R$ {l['premio']:,.2f}")


def cmd_chance(args):
    m = odds.cartelas_para_chance(args.alvo, args.chance)
    print(f"Para {args.chance:.0%} de chance de pelo menos UM "
          f"{args.alvo}-acertos:")
    print(f"  {m:,} cartelas distintas = R$ {m*3.5:,.2f}")
    print("  (sorteios independentes; EV continua negativo — isto é "
          "compra de chance, não vantagem.)")


def cmd_ev(args):
    r = odds.ev_cartela(args.p14, args.p15)
    print(f"EV por cartela (R$ 3,50):")
    print(f"  retorno bruto esperado : R$ {r['ev_por_cartela']:.3f}")
    print(f"  resultado líquido      : R$ {r['ev_liquido']:.3f}")
    print(f"  taxa de retorno        : {r['retorno_pct']}%")
    for k, d in r["detalhe"].items():
        print(f"    {k} pts: P=1/{1/d['prob']:,.0f} prêmio R$ {d['premio']:,.2f}"
              f"  → contribui R$ {d['contribuicao']:.3f}")


def cmd_reverificar(args):
    laudo = cov.reverificar_todo_cache()
    falhas = [l for l in laudo if not l["verificado"]]
    for l in laudo:
        status = "OK " if l["verificado"] else "FALHOU"
        print(f"  [{status}] {l['caso']:>6}: {l['cartelas']:>4} cartelas "
              f"(cota {l['cota_inferior']:>4}) — {l['alvos_cobertos']:,}/"
              f"{l['total_alvos']:,} alvos")
    print(f"\n{len(laudo) - len(falhas)}/{len(laudo)} fechamentos provados.")
    sys.exit(1 if falhas else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tabela", help="escada de fechamentos verificados").set_defaults(func=cmd_tabela)

    p = sub.add_parser("fechar", help="constrói um fechamento verificado")
    p.add_argument("n_pool", type=int)
    p.add_argument("garantia", type=int)
    p.add_argument("--pool", nargs="*", type=int, default=None)
    p.add_argument("--tempo", type=float, default=60)
    p.add_argument("--sementes", type=int, default=3)
    p.set_defaults(func=cmd_fechar)

    sub.add_parser("odds", help="probabilidades exatas por cartela").set_defaults(func=cmd_odds)
    p = sub.add_parser("chance")
    p.add_argument("alvo", type=int, choices=(11, 12, 13, 14, 15))
    p.add_argument("chance", type=float)
    p.set_defaults(func=cmd_chance)
    p = sub.add_parser("ev")
    p.add_argument("--p14", type=float, default=1763.0)
    p.add_argument("--p15", type=float, default=2_500_000.0)
    p.set_defaults(func=cmd_ev)
    sub.add_parser("reverificar").set_defaults(func=cmd_reverificar)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
