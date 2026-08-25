"""Atualiza os rateios dos 100 concursos mais recentes com diagnóstico."""
from core.conferencia import Conferencia
from database.db_manager import DBManager


def atualizar_todos():
    db = DBManager()
    conferencia = Conferencia()
    conn = db.get_conn()
    concursos = [r[0] for r in conn.execute("""
        SELECT concurso FROM resultados ORDER BY concurso DESC LIMIT 100
    """).fetchall()]
    conn.close()

    print("Atualizando rateios de {} concursos...".format(len(concursos)))
    resultado = conferencia.atualizar_premios_concursos(concursos)
    print("Status:       {}".format(resultado["status"]))
    print("Atualizados:  {}".format(resultado["atualizados"]))
    print("Erros:        {}".format(resultado["erros"]))
    print("Fontes:       {}".format(", ".join(resultado["fontes"]) or "nenhuma"))
    for falha in resultado["falhas"][:5]:
        print("  - concurso {}: {}".format(
            falha["concurso"], falha["diagnostico"]))
    return resultado


if __name__ == "__main__":
    atualizar_todos()
