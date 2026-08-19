"""
Script independente para atualizar prêmios da Caixa.
Rode: python atualizar_premios.py
"""
import time
from database.db_manager import DBManager
from core.conferencia import Conferencia


def atualizar_todos():
    db          = DBManager()
    conferencia = Conferencia()

    conn   = db.get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT concurso FROM resultados
        ORDER BY concurso DESC LIMIT 100
    """)
    concursos = [r[0] for r in cursor.fetchall()]
    conn.close()

    print("Atualizando {} concursos...".format(len(concursos)))

    atualizados = 0
    erros       = 0

    for i, c in enumerate(concursos, 1):
        try:
            print("[{}/{}] Concurso {}...".format(
                i, len(concursos), c
            ))

            dados_caixa = conferencia.buscar_premios_caixa(c)
            if dados_caixa:
                conferencia._atualizar_premios_banco(c, dados_caixa)
                atualizados += 1
                premios = dados_caixa.get("premios", {})
                print("  OK: 15pts=R${:.2f} | Ganhadores={}".format(
                    premios.get(15, 0),
                    dados_caixa.get("ganhadores", {}).get(15, 0)
                ))
            else:
                erros += 1
                print("  ERRO: sem resposta")

            time.sleep(0.3)

        except Exception as e:
            print("  ERRO: {}".format(e))
            erros += 1

    print("\n" + "="*50)
    print("CONCLUÍDO!")
    print("Atualizados: {}".format(atualizados))
    print("Erros:       {}".format(erros))
    print("Total:       {}".format(len(concursos)))
    print("="*50)


if __name__ == "__main__":
    atualizar_todos()