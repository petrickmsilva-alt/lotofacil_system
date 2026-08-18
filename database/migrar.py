"""
============================================================
MIGRAÇÃO DO BANCO DE DADOS
Adiciona colunas que faltam sem perder dados
============================================================
"""
import sqlite3
import os
import sys

# Adicionar pasta raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH


def migrar():
    print(f"[MIGRAÇÃO] Banco: {DATABASE_PATH}")

    if not os.path.exists(DATABASE_PATH):
        print("[MIGRAÇÃO] Banco não encontrado. Será criado automaticamente.")
        return

    conn   = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # ── Colunas que devem existir em cada tabela ──────────────

    migracoes_cartelas = [
        ("premio_ganho",   "REAL    DEFAULT 0"),
        ("score_ia",       "REAL    DEFAULT 0"),
        ("score_markov",   "REAL    DEFAULT 0"),
        ("score_fisico",   "REAL    DEFAULT 0"),
        ("score_entropia", "REAL    DEFAULT 0"),
        ("score_total",    "REAL    DEFAULT 0"),
        ("conferida",      "INTEGER DEFAULT 0"),
        ("acertos",        "INTEGER DEFAULT 0"),
        ("status",         "TEXT    DEFAULT 'pendente'"),
    ]

    migracoes_resultados = [
        ("premio_11",       "REAL    DEFAULT 0"),
        ("premio_12",       "REAL    DEFAULT 0"),
        ("premio_13",       "REAL    DEFAULT 0"),
        ("premio_14",       "REAL    DEFAULT 0"),
        ("premio_15",       "REAL    DEFAULT 0"),
        ("ganhadores_11",   "INTEGER DEFAULT 0"),
        ("ganhadores_12",   "INTEGER DEFAULT 0"),
        ("ganhadores_13",   "INTEGER DEFAULT 0"),
        ("ganhadores_14",   "INTEGER DEFAULT 0"),
        ("ganhadores_15",   "INTEGER DEFAULT 0"),
        ("arrecadacao",     "REAL    DEFAULT 0"),
        ("impares",         "INTEGER DEFAULT 0"),
        ("primos_count",    "INTEGER DEFAULT 0"),
        ("fibonacci_count", "INTEGER DEFAULT 0"),
        ("borda_count",     "INTEGER DEFAULT 0"),
        ("consecutivos_max","INTEGER DEFAULT 0"),
    ]

    migracoes_financeiro = [
        ("premio_11",     "REAL    DEFAULT 0"),
        ("premio_12",     "REAL    DEFAULT 0"),
        ("premio_13",     "REAL    DEFAULT 0"),
        ("premio_14",     "REAL    DEFAULT 0"),
        ("premio_15",     "REAL    DEFAULT 0"),
        ("premio_total",  "REAL    DEFAULT 0"),
        ("lucro_liquido", "REAL    DEFAULT 0"),
    ]

    def adicionar_colunas(tabela, migracoes):
        # Verificar colunas existentes
        cursor.execute(f"PRAGMA table_info({tabela})")
        existentes = {row[1] for row in cursor.fetchall()}

        adicionadas = 0
        for col_nome, col_tipo in migracoes:
            if col_nome not in existentes:
                try:
                    cursor.execute(
                        f"ALTER TABLE {tabela} ADD COLUMN {col_nome} {col_tipo}"
                    )
                    print(f"  [+] {tabela}.{col_nome} adicionada")
                    adicionadas += 1
                except Exception as e:
                    print(f"  [!] {tabela}.{col_nome}: {e}")

        if adicionadas == 0:
            print(f"  [OK] {tabela} já está atualizada")

        return adicionadas

    # ── Verificar se tabelas existem ─────────────────────────
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tabelas_existentes = {row[0] for row in cursor.fetchall()}

    print("\n[MIGRAÇÃO] Verificando tabela: cartelas")
    if "cartelas" in tabelas_existentes:
        adicionar_colunas("cartelas", migracoes_cartelas)
    else:
        print("  [!] Tabela cartelas não existe ainda")

    print("\n[MIGRAÇÃO] Verificando tabela: resultados")
    if "resultados" in tabelas_existentes:
        adicionar_colunas("resultados", migracoes_resultados)
    else:
        print("  [!] Tabela resultados não existe ainda")

    print("\n[MIGRAÇÃO] Verificando tabela: financeiro")
    if "financeiro" in tabelas_existentes:
        adicionar_colunas("financeiro", migracoes_financeiro)
    else:
        print("  [!] Tabela financeiro não existe ainda")

    # ── Criar tabelas faltantes ───────────────────────────────
    print("\n[MIGRAÇÃO] Criando tabelas faltantes...")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS previsoes_ia (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso_alvo     INTEGER,
            cartela_id        INTEGER,
            acertos_previstos REAL,
            acertos_reais     INTEGER,
            erro              REAL,
            data_previsao     TEXT,
            data_conferencia  TEXT,
            modelo_versao     TEXT,
            parametros_usados TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ia_aprendizado (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            epoca                   INTEGER,
            data                    TEXT,
            acuracia_media          REAL,
            erro_medio              REAL,
            melhor_score            REAL,
            total_cartelas_testadas INTEGER,
            taxa_13_pontos          REAL,
            taxa_14_pontos          REAL,
            taxa_15_pontos          REAL,
            parametros_otimizados   TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS padroes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo             TEXT,
            descricao        TEXT,
            frequencia       REAL,
            ultima_ocorrencia INTEGER,
            peso             REAL,
            ativo            INTEGER DEFAULT 1
        )
    """)

    # ── Índices ───────────────────────────────────────────────
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_res_concurso "
        "ON resultados(concurso)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cart_concurso "
        "ON cartelas(concurso_alvo)"
    )

    conn.commit()
    conn.close()

    print("\n[MIGRAÇÃO] ✅ Concluída com sucesso!")


if __name__ == "__main__":
    migrar()