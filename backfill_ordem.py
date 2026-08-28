#!/usr/bin/env python3
"""
============================================================
BACKFILL DA ORDEM REAL DE SORTEIO (v11.3 — ferramenta de captura;
desde a v11.4 o destino é o acervo da Inteligência Magna)
============================================================
Preenche a tabela `ordem_sorteio` com a ordem REAL de extração
das bolas (1ª, 2ª, ..., 15ª) de todo o histórico que ainda não
a tem. A ordem vem do campo oficial `dezenasSorteadasOrdemSorteio`
da API da Caixa (com cadeia de contingência do CaixaClient).

Uso (rodar ONDE A REDE FUNCIONA — sua máquina local):

    python backfill_ordem.py                 # histórico completo
    python backfill_ordem.py --limite 300    # em fatias (recomeça depois)
    python backfill_ordem.py --pausa 0.5     # gentileza com a API
    python backfill_ordem.py --reconsultar 3770  # forçar concurso

O script é IDEMPOTENTE e RETOMÁVEL: concursos já gravados são
pulados; se interromper, rode de novo que continua de onde parou.

Rendimento esperado: ~2–4 concursos/segundo quando a Caixa responde;
histórico completo (3.770+) em 20–40 minutos. Após concluir:

    python gerar_pessoal.py --assimilar    # a Magna reassimila o acervo: o que
                                           # este script gravou vira o canal
                                           # `real` do conhecimento da Magna
    # consulta: GET /api/magna/conhecimento · painel: /cerebro (seção
    # "Acervo nativo"). A partir da v11.4 a ordem real não alimenta mais um
    # motor separado: alimenta a própria Magna.
"""
import argparse
import sys
import time

from core.caixa_client import CaixaClient, ErroFonteResultados
from config import DATABASE_PATH
from database.db_manager import DBManager


def main():
    parser = argparse.ArgumentParser(
        description="Preenche a ordem real de sorteio do histórico")
    parser.add_argument("--limite", type=int, default=None,
                        help="máximo de concursos nesta execução")
    parser.add_argument("--pausa", type=float, default=0.25,
                        help="pausa entre consultas (segundos)")
    parser.add_argument("--reconsultar", type=int, nargs="*", default=[],
                        help="concursos para gravar de novo")
    args = parser.parse_args()

    db = DBManager(DATABASE_PATH)
    client = CaixaClient()

    pendentes = db.get_concursos_sem_ordem()
    alvos = list(dict.fromkeys(
        list(args.reconsultar) + list(reversed(pendentes))))
    if args.limite:
        alvos = alvos[:args.limite]

    total = len(alvos)
    print("[ORDEM] Concursos a processar: {}".format(total))
    if total == 0:
        print("[ORDEM] Histórico já completo. Painel: /api/magna/ordem")
        return 0

    ok = falha = 0
    inicio = time.time()
    for i, concurso in enumerate(alvos, 1):
        try:
            dados = client.buscar_concurso(concurso)
            ordem = (dados or {}).get("ordem_sorteio")
            if not ordem:
                falha += 1
                print("[ORDEM] {:>5}: fonte sem ordem de sorteio".format(
                    concurso))
            else:
                db.salvar_ordem(concurso, ordem)
                ok += 1
                if ok % 50 == 0 or i == total:
                    ritmo = (time.time() - inicio) / max(ok, 1)
                    resta = (total - i) * ritmo
                    print("[ORDEM] {}/{} ok ({}) — 1ª bola de {}: {:02d} | "
                          "resta ~{:.0f} min".format(
                              i, total, ok, concurso, ordem[0], resta / 60))
        except (ErroFonteResultados, Exception) as exc:
            falha += 1
            print("[ORDEM] {:>5}: ERRO {}".format(concurso, str(exc)[:80]))
        time.sleep(args.pausa)

    print("[ORDEM] FIM: {} gravados, {} falhas. Reexecute para retomar."
          .format(ok, falha))
    print("[ORDEM] Painel: GET /api/magna/ordem")
    return 0


if __name__ == "__main__":
    sys.exit(main())
