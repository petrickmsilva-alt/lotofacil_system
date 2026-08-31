"""
============================================================
INVESTIGAR MAGNA — LABORATÓRIO DE APRENDIZADO DINÂMICO (CLI)
============================================================
Ferramenta pessoal para estudar a base histórica, auditar cartelas,
medir estratégias fora-da-amostra, reconhecer jogos ruins e explorar
novas propostas.

Exemplos:
    python investigar_magna.py --benchmark                # walk-forward completo
    python investigar_magna.py --benchmark --testes 60 --janela 50
    python investigar_magna.py --auditar "01 02 03 ..."  # audita cartela
    python investigar_magna.py --historico-ruins         # jogos repetidos
    python investigar_magna.py --explorar                 # grid de janelas
    python investigar_magna.py --relatorio                # placar persistido
    python investigar_magna.py --dry-run                  # não grava no banco
"""
import argparse
import os
import sys
from datetime import datetime

import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

from database.db_manager import DBManager
from core.cerebro_ia import InteligenciaMagna


def _decodificar(dezenas: list) -> list:
    vals = []
    for d in dezenas:
        for token in d.replace(",", " ").split():
            try:
                vals.append(int(token))
            except ValueError:
                pass
    return sorted(int(v) for v in vals if 1 <= v <= 25)


def _formatar_bench(r: dict):
    print("RESULTADO DO BENCHMARK WALK-FORWARD")
    print("=" * 78)
    print("Concursos base: {} | testados: {} | janela: {} | baseline aleatória: {:.3f}".
          format(r["concursos_na_base"], r["n_testes"], r["janela"],
                 r["baseline_aleatoria"]))
    print("-" * 78)
    for nome, linha in r["estimativas"].items():
        print("{:>14} média={:6.3f} desvio={:+.3f} p={:.4f} => {}{}".
              format(nome, linha["media_acertos"],
                     linha.get("desvio_vs_aleatorio", 0),
                     linha["p_valor"], linha["veredito"],
                     " [quarentena]" if linha["quarentena"] else ""))
    print("-" * 78)
    print("Quarentena: {}".format(", ".join(r["quarentena"]) or "—"))
    print("Pesos recomendados: {}".format(
        ", ".join("{}={:.2f}".format(k, v)
                  for k, v in (r.get("pesos_recomendados") or {}).items()) or "—"))
    print("Veredito: {}".format(r["veredito_geral"]))
    print("Honestidade: {}".format(r["honestidade"]))


def _formatar_auditoria(r: dict):
    print("AUDITORIA DO LOTE")
    print("=" * 78)
    print("Veredito geral: {}".format(r.get("veredito_geral")))
    print("Cartelas: {} | aceitáveis: {} | ruins: {} | observação: {}".format(
        r["n_cartelas"], r.get("n_aceitaveis", r.get("n_aprovadas", 0)),
        r.get("n_ruins", 0), r.get("n_observacao", 0)))
    for i, c in enumerate(r["cartelas"], 1):
        print("  [{:02}] {} → {} · score {}".
              format(i, "-".join("{:02d}".format(d) for d in c["dezenas"]),
                     c["veredito"], c["score_estrutural"]))
        for risco in c["riscos"]:
            print("       riscos: {}".format(risco))
    print("Honestidade: {}".format(r.get("honestidade")))


def _formatar_ruins(r: dict):
    print("JOGOS RUINS / REPETIDOS DO HISTÓRICO")
    print("=" * 78)
    print("Total: {}".format(r["n"]))
    for j in r["jogos"][:30]:
        print("  {} → repetido_15={} quase_13+={} freq={:.6f} · {}".
              format("-".join("{:02d}".format(d) for d in j["dezenas"]),
                     j["repetido_15"], j["quase_repetido_13_mais"],
                     j["freq_na_janela"], j["motivo"]))


def _formatar_relatorio(r: dict):
    print("RELATÓRIO DO LABORATÓRIO")
    print("=" * 78)
    print("Versão: {} | concursos na base: {}".format(
        r["versao"], r["concursos_na_base"]))
    print("Placar persistido:")
    for p in r["placar_historico"]:
        print("  {:>14} média={:6.3f} taxa13={:.5f} p={:.4f} {} {}".format(
            p["fonte"], p["media_acertos"], p["taxa_13_mais"], p["p_valor"],
            p["veredito"], "[quarentena]" if p["quarentena"] else ""))
    print("Honestidade: {}".format(r["honestidade"]))


def executar(args):
    persistir = not args.dry_run
    if args.dry_run:
        print("[AVISO] --dry-run: nada será persistido no banco.\n")

    magna = InteligenciaMagna(n_cartelas=1)
    lab = magna.laboratorio

    if args.benchmark:
        r = magna.lab_benchmark(
            n_testes=args.testes, janela=args.janela,
            n_aleatorio=args.aleatorios)
        _formatar_bench(r)

    if args.auditar:
        cartelas = [_decodificar(args.auditar)]
        r = magna.auditor_cartelas(cartelas)
        _formatar_auditoria(r)

    if args.historico_ruins:
        r = lab.jogos_ruins(persistir=persistir)
        _formatar_ruins(r)

    if args.explorar:
        ensaios = [{"janela": j} for j in (30, 50, 80, 120, 200)]
        r = magna.lab_explorar(ensaios=ensaios, n_testes=min(args.testes, 30))
        print("EXPLORAÇÃO DE PROPOSTAS")
        print("=" * 78)
        for e in r["melhores_propostas"]:
            print("  janela={} média={} ganho={} => {}".format(
                e.get("janela"), e.get("media_acertos"),
                e.get("ganho_vs_base"), e.get("veredito")))
        print("Honestidade: {}".format(r["honestidade"]))

    if args.relatorio or not any([args.benchmark, args.auditar,
                                  args.historico_ruins, args.explorar]):
        _formatar_relatorio(magna.lab_relatorio())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--testes", type=int, default=40)
    parser.add_argument("--janela", type=int, default=50)
    parser.add_argument("--aleatorios", type=int, default=120)
    parser.add_argument("--auditar", nargs="+",
                        help="15 dezenas, ex: 01 02 03 ... 25")
    parser.add_argument("--historico-ruins", action="store_true")
    parser.add_argument("--explorar", action="store_true")
    parser.add_argument("--relatorio", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    executar(args)
