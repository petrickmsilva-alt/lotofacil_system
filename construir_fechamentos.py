"""
Constrói (offline) a tabela de fechamentos VERIFICADOS por prova exaustiva.

Uso:
    python construir_fechamentos.py                # todos os casos da escada
    python construir_fechamentos.py --caso 20 13   # um caso só
    python construir_fechamentos.py --reverificar  # só reverifica o cache

Resultados em database/modelos/fechamentos_verificados.json.
Cada entrada é provada contra TODOS os C(n,s) alvos (nunca amostragem).
"""
import argparse
import json
import math
import time

from core import cobertura as cov
from core.cobertura import (
    cota_inferior, fechamento_verificado, prob_captura, reverificar_todo_cache,
)
from config import VALOR_APOSTA, MODELS_PATH
import os

# (n_pool, garantia, tempo_max, sementes)
CASOS = [
    # --- estrela da escada: garantia 13 condicional ---
    (18, 13, 10, 2),
    (19, 13, 60, 4),
    (20, 13, 240, 4),
    (21, 13, 300, 4),
    # --- garantia 14 condicional ---
    (17, 14, 10, 2),
    (18, 14, 60, 4),
    (19, 14, 180, 3),
    # --- garantia 12 condicional (barata, captura alta) ---
    (19, 12, 10, 2),
    (20, 12, 90, 4),
    (21, 12, 240, 4),
    (22, 12, 300, 3),
    (23, 12, 420, 3),
    # --- garantia 11 condicional ---
    (20, 11, 60, 3),
    (21, 11, 120, 3),
    (22, 11, 240, 3),
    # --- INCONDICIONAL (pool = volante inteiro) ---
    (25, 11, 600, 3),
    (25, 12, 900, 3),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caso", nargs=2, type=int, metavar=("N", "T"))
    ap.add_argument("--reverificar", action="store_true")
    ap.add_argument("--tempo", type=float, default=None)
    args = ap.parse_args()

    if args.reverificar:
        for linha in reverificar_todo_cache():
            print(linha)
        return

    casos = [tuple(args.caso + [args.tempo or 300, 4])] if args.caso else CASOS

    print(f"{'n':>3} {'t':>3} {'α':>2} | {'cotaInf':>7} | {'achado':>6} "
          f"{'verif':>5} | {'custo':>9} | {'1 em(captura)':>13} | tempo")
    for n, t, tmax, sem in casos:
        alpha = t + n - 30
        t0 = time.time()
        res = fechamento_verificado(n, t, tempo_max=tmax, sementes=sem, verboso=False)
        p = prob_captura(n)
        um_em = f"{1/p:,.0f}" if n < 25 else "1 (incond.)"
        print(f"{n:>3} {t:>3} {alpha:>2} | {cota_inferior(n, t):>7} | "
              f"{res.get('cartelas', '-'):>6} "
              f"{str(res.get('garantia_verificada')):>5} | "
              f"R${(res.get('cartelas',0)*VALOR_APOSTA):>8.2f} | "
              f"{um_em:>13} | {round(time.time()-t0,1)}s", flush=True)


if __name__ == "__main__":
    main()
