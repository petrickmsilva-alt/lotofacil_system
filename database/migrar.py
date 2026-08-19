"""
============================================================
MIGRAÇÃO DO BANCO DE DADOS
Adiciona colunas e tabelas que faltam sem perder dados
============================================================
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH


def migrar():
    print("[MIGRAÇÃO] Banco: {}".format(DATABASE_PATH))

    if not os.path.exists(DATABASE_PATH):
        print("[MIGRAÇÃO] Banco não encontrado. Será criado automaticamente.")
        return

    conn   = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    def add_col(tabela, coluna, tipo):
        try:
            cursor.execute("PRAGMA table_info({})".format(tabela))
            cols = {r[1] for r in cursor.fetchall()}
            if coluna not in cols:
                cursor.execute(
                    "ALTER TABLE {} ADD COLUMN {} {}".format(
                        tabela, coluna, tipo
                    )
                )
                print("  [+] {}.{}".format(tabela, coluna))
        except Exception:
            pass

    # ── Colunas da tabela resultados ──────────────────────────
    add_col("resultados", "impares",         "INTEGER DEFAULT 0")
    add_col("resultados", "primos_count",    "INTEGER DEFAULT 0")
    add_col("resultados", "fibonacci_count", "INTEGER DEFAULT 0")
    add_col("resultados", "borda_count",     "INTEGER DEFAULT 0")
    add_col("resultados", "consecutivos_max","INTEGER DEFAULT 0")
    add_col("resultados", "premio_11",       "REAL DEFAULT 0")
    add_col("resultados", "premio_12",       "REAL DEFAULT 0")
    add_col("resultados", "premio_13",       "REAL DEFAULT 0")
    add_col("resultados", "premio_14",       "REAL DEFAULT 0")
    add_col("resultados", "premio_15",       "REAL DEFAULT 0")
    add_col("resultados", "ganhadores_11",   "INTEGER DEFAULT 0")
    add_col("resultados", "ganhadores_12",   "INTEGER DEFAULT 0")
    add_col("resultados", "ganhadores_13",   "INTEGER DEFAULT 0")
    add_col("resultados", "ganhadores_14",   "INTEGER DEFAULT 0")
    add_col("resultados", "ganhadores_15",   "INTEGER DEFAULT 0")
    add_col("resultados", "arrecadacao",     "REAL DEFAULT 0")

    # ── Colunas da tabela cartelas ────────────────────────────
    add_col("cartelas", "score_ia",       "REAL DEFAULT 0")
    add_col("cartelas", "score_markov",   "REAL DEFAULT 0")
    add_col("cartelas", "score_fisico",   "REAL DEFAULT 0")
    add_col("cartelas", "score_entropia", "REAL DEFAULT 0")
    add_col("cartelas", "score_total",    "REAL DEFAULT 0")
    add_col("cartelas", "conferida",      "INTEGER DEFAULT 0")
    add_col("cartelas", "acertos",        "INTEGER DEFAULT 0")
    add_col("cartelas", "premio_ganho",   "REAL DEFAULT 0")
    add_col("cartelas", "status",         "TEXT DEFAULT 'pendente'")
    add_col("cartelas", "lote_id",        "TEXT DEFAULT NULL")
    add_col("cartelas", "tipo_geracao",   "TEXT DEFAULT 'multiplas'")

    # ── Colunas do financeiro ─────────────────────────────────
    add_col("financeiro", "premio_11",     "REAL DEFAULT 0")
    add_col("financeiro", "premio_12",     "REAL DEFAULT 0")
    add_col("financeiro", "premio_13",     "REAL DEFAULT 0")
    add_col("financeiro", "premio_14",     "REAL DEFAULT 0")
    add_col("financeiro", "premio_15",     "REAL DEFAULT 0")
    add_col("financeiro", "premio_total",  "REAL DEFAULT 0")
    add_col("financeiro", "lucro_liquido", "REAL DEFAULT 0")

    # ── Tabelas que podem faltar ──────────────────────────────
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
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo              TEXT,
            descricao         TEXT,
            frequencia        REAL,
            ultima_ocorrencia INTEGER,
            peso              REAL,
            ativo             INTEGER DEFAULT 1
        )
    """)

    # ── Tabela de LOTES ───────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes_cartelas (
            lote_id       TEXT PRIMARY KEY,
            data_criacao  TEXT,
            concurso_alvo INTEGER,
            tipo_geracao  TEXT,
            quantidade    INTEGER,
            custo_total   REAL,
            modo          TEXT,
            grupo_elite   TEXT,
            cobertura_13  REAL,
            observacao    TEXT
        )
    """)

    # ── Tabelas do Cérebro IA ─────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fila_conferencia (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso_alvo         INTEGER,
            dezenas               TEXT,
            timestamp_geracao     TEXT,
            scores_modulos        TEXT,
            score_total           REAL,
            status                TEXT DEFAULT 'aguardando',
            acertos               INTEGER DEFAULT 0,
            premio_ganho          REAL DEFAULT 0,
            dezenas_acertadas     TEXT,
            timestamp_conferencia TEXT,
            erro_previsao         REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_ciclos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso         INTEGER,
            timestamp_inicio TEXT,
            timestamp_fim    TEXT,
            status           TEXT,
            n_cartelas       INTEGER DEFAULT 0,
            melhor_acertos   INTEGER DEFAULT 0,
            media_acertos    REAL DEFAULT 0,
            total_ganho      REAL DEFAULT 0,
            pesos_antes      TEXT,
            pesos_depois     TEXT,
            log_ciclo        TEXT,
            erro_medio       REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memoria_erros (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso    INTEGER,
            timestamp   TEXT,
            modulo      TEXT,
            erro        REAL,
            impacto     REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS desempenho_modulos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso    INTEGER,
            timestamp   TEXT,
            modulo      TEXT,
            correlacao  REAL,
            peso_antes  REAL,
            peso_depois REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cartela_do_dia (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso_alvo      INTEGER,
            timestamp          TEXT,
            dezenas            TEXT,
            quorum_usado       INTEGER,
            confianca          TEXT,
            consenso_forca     REAL,
            score_cerebro      REAL,
            aprovado_filtros   INTEGER,
            votos_json         TEXT,
            acertos            INTEGER DEFAULT 0,
            premio             REAL DEFAULT 0,
            conferida          INTEGER DEFAULT 0
        )
    """)

    # ── Tabelas de auditoria da IA ────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ia_sessoes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo         TEXT,
            inicio       TEXT,
            fim          TEXT,
            duracao_seg  REAL,
            status       TEXT,
            resumo       TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ia_modulos_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sessao_id    INTEGER,
            modulo       TEXT,
            acao         TEXT,
            score_medio  REAL,
            top3_dezenas TEXT,
            detalhes     TEXT,
            timestamp    TEXT,
            duracao_ms   REAL,
            status       TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ia_decisoes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sessao_id       INTEGER,
            cartela_id      INTEGER,
            dezenas         TEXT,
            score_total     REAL,
            score_markov    REAL,
            score_fisico    REAL,
            score_gaussiano REAL,
            score_ml        REAL,
            score_verlet    REAL,
            score_quantum   REAL,
            score_chi2      REAL,
            score_bayes     REAL,
            score_kl        REAL,
            score_stacking  REAL,
            modulo_dominante TEXT,
            justificativa   TEXT,
            timestamp       TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ia_evolucao_pesos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            concurso    INTEGER,
            acertos_real INTEGER,
            peso_markov    REAL,
            peso_fisico    REAL,
            peso_gaussiano REAL,
            peso_ml        REAL,
            peso_verlet    REAL,
            peso_quantum   REAL,
            peso_chi2      REAL,
            peso_bayes     REAL,
            peso_kl        REAL,
            peso_stacking  REAL,
            evento      TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ia_previsao_vs_real (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            concurso        INTEGER,
            timestamp       TEXT,
            dezenas_previstas TEXT,
            dezenas_reais     TEXT,
            acertos           INTEGER,
            percentual        REAL,
            modulo_mais_certo TEXT,
            modulo_mais_errou TEXT,
            aprendizado       TEXT
        )
    """)

    # ── Índices ───────────────────────────────────────────────
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_res_concurso "
            "ON resultados(concurso)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cart_concurso "
            "ON cartelas(concurso_alvo)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cart_conferida "
            "ON cartelas(conferida)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cart_lote "
            "ON cartelas(lote_id)"
        )
    except Exception:
        pass

    conn.commit()
    conn.close()

    print("[MIGRAÇÃO] ✅ Concluída com sucesso!")


if __name__ == "__main__":
    migrar()