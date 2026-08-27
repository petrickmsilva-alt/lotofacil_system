"""Bloqueio de combinações já sorteadas com 15 pontos e memória pós-exclusão."""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_PATH
from core.cerebro_ia import InteligenciaMagna
from core.conferencia import Conferencia
from database.db_manager import DBManager


def test_cartela_oficial_e_detectada_como_15(tmp_path):
    caminho = tmp_path / "b15.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho))
    row = magna.db.get_todos_resultados()[0]
    dez = [int(row["d{}".format(i)]) for i in range(1, 16)]
    assert magna._cartela_ja_foi_15(dez) is True
    assert magna._cartela_ja_foi_15(list(range(1, 16))) in (True, False)


def test_substituicao_remove_sorteio_oficial(tmp_path):
    caminho = tmp_path / "sub.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho))
    magna.treinar()
    row = magna.db.get_todos_resultados()[10]
    oficial = [int(row["d{}".format(i)]) for i in range(1, 16)]
    vf = magna._vetor_combinado()
    out = magna._substituir_cartelas_ja_sorteadas_15([oficial], vf)
    assert out
    assert not magna._cartela_ja_foi_15(out[0])


def test_apagar_lote_arquiva_memoria(tmp_path):
    caminho = tmp_path / "mem.db"
    shutil.copy2(DATABASE_PATH, caminho)
    db = DBManager(str(caminho))
    db.criar_tabelas()
    conf = Conferencia(db_path=str(caminho))
    conn = db.get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lotes_cartelas (
            lote_id TEXT PRIMARY KEY,
            data_criacao TEXT,
            concurso_alvo INTEGER,
            tipo_geracao TEXT,
            quantidade INTEGER,
            custo_total REAL,
            modo TEXT,
            grupo_elite TEXT,
            cobertura_13 REAL
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO lotes_cartelas "
        "(lote_id, data_criacao, concurso_alvo, tipo_geracao, quantidade, "
        "custo_total, modo, grupo_elite, cobertura_13) "
        "VALUES ('lote-x','2026-01-01',1,'t',1,3.5,'m','[]',0)"
    )
    # garantir coluna lote_id
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cartelas)").fetchall()}
    if "lote_id" not in cols:
        conn.execute("ALTER TABLE cartelas ADD COLUMN lote_id TEXT")
    if "tipo_geracao" not in cols:
        conn.execute("ALTER TABLE cartelas ADD COLUMN tipo_geracao TEXT")
    conn.execute("""
        INSERT INTO cartelas
        (data_geracao, concurso_alvo, d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,
         d11,d12,d13,d14,d15, bitmask, score_total, lote_id, conferida, acertos)
        VALUES ('t', 1, 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15, 0, 0.1, 'lote-x', 1, 11)
    """)
    conn.commit()
    conn.close()
    res = conf.apagar_lote("lote-x")
    assert res["status"] == "ok"
    assert res["cartelas_apagadas"] >= 1
    conn = db.get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM memoria_cartelas_aprendidas"
    ).fetchone()[0]
    visiveis = conn.execute(
        "SELECT COUNT(*) FROM cartelas WHERE lote_id='lote-x'"
    ).fetchone()[0]
    conn.close()
    assert n >= 1
    assert visiveis == 0


def test_diagnostico_aprendizado(tmp_path):
    caminho = tmp_path / "diag.db"
    shutil.copy2(DATABASE_PATH, caminho)
    magna = InteligenciaMagna(db_path=str(caminho))
    d = magna.diagnostico_aprendizado()
    assert d["n_sorteios_15_bloqueados"] == magna.n
    assert "pesos_fontes" in d
    assert d["o_que_aprende"]
