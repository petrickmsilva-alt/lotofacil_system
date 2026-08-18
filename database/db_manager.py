"""
============================================================
GERENCIADOR DE BANCO DE DADOS
Tabela de resultados com prêmios REAIS da Caixa
============================================================
"""
import sqlite3
import os
from config import DATABASE_PATH


class DBManager:

    def __init__(self):
        self.db_path = DATABASE_PATH
        self.criar_tabelas()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def criar_tabelas(self):
        conn   = self.get_conn()
        cursor = conn.cursor()

        # ── Resultados com prêmios reais ──────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resultados (
                concurso        INTEGER PRIMARY KEY,
                data            TEXT,
                d1  INTEGER, d2  INTEGER, d3  INTEGER,
                d4  INTEGER, d5  INTEGER, d6  INTEGER,
                d7  INTEGER, d8  INTEGER, d9  INTEGER,
                d10 INTEGER, d11 INTEGER, d12 INTEGER,
                d13 INTEGER, d14 INTEGER, d15 INTEGER,
                bitmask         INTEGER,
                soma            INTEGER,
                pares           INTEGER,
                impares         INTEGER,
                primos_count    INTEGER,
                fibonacci_count INTEGER,
                borda_count     INTEGER,
                consecutivos_max INTEGER,
                -- Prêmios reais por faixa
                premio_11       REAL DEFAULT 0,
                premio_12       REAL DEFAULT 0,
                premio_13       REAL DEFAULT 0,
                premio_14       REAL DEFAULT 0,
                premio_15       REAL DEFAULT 0,
                -- Número de ganhadores por faixa
                ganhadores_11   INTEGER DEFAULT 0,
                ganhadores_12   INTEGER DEFAULT 0,
                ganhadores_13   INTEGER DEFAULT 0,
                ganhadores_14   INTEGER DEFAULT 0,
                ganhadores_15   INTEGER DEFAULT 0,
                -- Arrecadação total
                arrecadacao     REAL DEFAULT 0
            )
        """)

        # ── Migração: adicionar colunas se não existirem ──────
        colunas_novas = [
            ("premio_11",       "REAL DEFAULT 0"),
            ("premio_12",       "REAL DEFAULT 0"),
            ("premio_13",       "REAL DEFAULT 0"),
            ("premio_14",       "REAL DEFAULT 0"),
            ("premio_15",       "REAL DEFAULT 0"),
            ("ganhadores_11",   "INTEGER DEFAULT 0"),
            ("ganhadores_12",   "INTEGER DEFAULT 0"),
            ("ganhadores_13",   "INTEGER DEFAULT 0"),
            ("ganhadores_14",   "INTEGER DEFAULT 0"),
            ("ganhadores_15",   "INTEGER DEFAULT 0"),
            ("arrecadacao",     "REAL DEFAULT 0"),
        ]
        cursor.execute("PRAGMA table_info(resultados)")
        colunas_existentes = {row[1] for row in cursor.fetchall()}

        for col_nome, col_tipo in colunas_novas:
            if col_nome not in colunas_existentes:
                cursor.execute(
                    f"ALTER TABLE resultados ADD COLUMN {col_nome} {col_tipo}"
                )

        # ── Cartelas geradas ──────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cartelas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                data_geracao    TEXT,
                concurso_alvo   INTEGER,
                d1  INTEGER, d2  INTEGER, d3  INTEGER,
                d4  INTEGER, d5  INTEGER, d6  INTEGER,
                d7  INTEGER, d8  INTEGER, d9  INTEGER,
                d10 INTEGER, d11 INTEGER, d12 INTEGER,
                d13 INTEGER, d14 INTEGER, d15 INTEGER,
                bitmask         INTEGER,
                score_ia        REAL DEFAULT 0,
                score_markov    REAL DEFAULT 0,
                score_fisico    REAL DEFAULT 0,
                score_entropia  REAL DEFAULT 0,
                score_total     REAL DEFAULT 0,
                conferida       INTEGER DEFAULT 0,
                acertos         INTEGER DEFAULT 0,
                premio_ganho    REAL DEFAULT 0,
                status          TEXT DEFAULT 'pendente'
            )
        """)

        # ── Previsões da IA ───────────────────────────────────
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
                parametros_usados TEXT,
                FOREIGN KEY (cartela_id) REFERENCES cartelas(id)
            )
        """)

        # ── Financeiro ────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financeiro (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso        INTEGER,
                data            TEXT,
                qtd_cartelas    INTEGER,
                custo_total     REAL,
                acertos_11      INTEGER DEFAULT 0,
                acertos_12      INTEGER DEFAULT 0,
                acertos_13      INTEGER DEFAULT 0,
                acertos_14      INTEGER DEFAULT 0,
                acertos_15      INTEGER DEFAULT 0,
                premio_11       REAL DEFAULT 0,
                premio_12       REAL DEFAULT 0,
                premio_13       REAL DEFAULT 0,
                premio_14       REAL DEFAULT 0,
                premio_15       REAL DEFAULT 0,
                premio_total    REAL DEFAULT 0,
                lucro_liquido   REAL DEFAULT 0
            )
        """)

        # ── Aprendizado da IA ─────────────────────────────────
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

        # ── Índices ───────────────────────────────────────────
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_resultados_concurso "
            "ON resultados(concurso)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cartelas_concurso "
            "ON cartelas(concurso_alvo)"
        )

        conn.commit()
        conn.close()

    # =========================================================
    # RESULTADOS
    # =========================================================

    def inserir_resultado(self, dados):
        conn   = self.get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO resultados (
                    concurso, data,
                    d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,
                    bitmask, soma, pares, impares,
                    primos_count, fibonacci_count, borda_count,
                    consecutivos_max,
                    premio_11, premio_12, premio_13, premio_14, premio_15,
                    ganhadores_11, ganhadores_12, ganhadores_13,
                    ganhadores_14, ganhadores_15,
                    arrecadacao
                ) VALUES (
                    ?,?,
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,
                    ?,?,?,?,
                    ?,?,?,?,?,
                    ?,?,?,?,?,
                    ?
                )
            """, dados)
            conn.commit()
        except Exception as e:
            print(f"[DB] Erro inserir resultado: {e}")
        finally:
            conn.close()

    def get_todos_resultados(self):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resultados ORDER BY concurso ASC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_ultimo_concurso(self):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(concurso) FROM resultados")
        result = cursor.fetchone()[0]
        conn.close()
        return result or 0

    def get_resultado_concurso(self, concurso):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM resultados WHERE concurso = ?", (concurso,)
        )
        row = cursor.fetchone()
        conn.close()
        return row

    def get_premios_concurso(self, concurso):
        """Retorna prêmios reais de um concurso"""
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                premio_11, premio_12, premio_13, premio_14, premio_15,
                ganhadores_11, ganhadores_12, ganhadores_13,
                ganhadores_14, ganhadores_15
            FROM resultados WHERE concurso = ?
        """, (concurso,))
        row = cursor.fetchone()
        conn.close()
        return row

    def get_media_premios(self):
        """Calcula média histórica dos prêmios por faixa"""
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                AVG(CASE WHEN premio_11 > 0 THEN premio_11 END) as media_11,
                AVG(CASE WHEN premio_12 > 0 THEN premio_12 END) as media_12,
                AVG(CASE WHEN premio_13 > 0 THEN premio_13 END) as media_13,
                AVG(CASE WHEN premio_14 > 0 THEN premio_14 END) as media_14,
                AVG(CASE WHEN premio_15 > 0 THEN premio_15 END) as media_15,
                MIN(CASE WHEN premio_15 > 0 THEN premio_15 END) as min_15,
                MAX(CASE WHEN premio_15 > 0 THEN premio_15 END) as max_15
            FROM resultados
        """)
        row = cursor.fetchone()
        conn.close()
        return row

    def get_ultimos_premios(self, n=10):
        """Últimos N concursos com prêmios"""
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT concurso, data,
                   premio_11, premio_12, premio_13, premio_14, premio_15,
                   ganhadores_11, ganhadores_12, ganhadores_13,
                   ganhadores_14, ganhadores_15
            FROM resultados
            ORDER BY concurso DESC
            LIMIT ?
        """, (n,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_total_concursos(self):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM resultados")
        total = cursor.fetchone()[0]
        conn.close()
        return total

    # =========================================================
    # CARTELAS
    # =========================================================

    def inserir_cartela(self, dados):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cartelas (
                data_geracao, concurso_alvo,
                d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,
                bitmask, score_ia, score_markov,
                score_fisico, score_entropia, score_total
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, dados)
        conn.commit()
        cartela_id = cursor.lastrowid
        conn.close()
        return cartela_id

    def get_cartelas_por_concurso(self, concurso):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM cartelas WHERE concurso_alvo = ? "
            "ORDER BY score_total DESC",
            (concurso,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_cartelas_pendentes(self):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM cartelas WHERE conferida = 0 "
            "ORDER BY concurso_alvo"
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def atualizar_conferencia(self, cartela_id, acertos, premio, status):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cartelas
            SET conferida = 1, acertos = ?, premio_ganho = ?, status = ?
            WHERE id = ?
        """, (acertos, premio, status, cartela_id))
        conn.commit()
        conn.close()

    # =========================================================
    # FINANCEIRO
    # =========================================================

    def inserir_financeiro(self, dados):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO financeiro (
                concurso, data, qtd_cartelas, custo_total,
                acertos_11, acertos_12, acertos_13, acertos_14, acertos_15,
                premio_11, premio_12, premio_13, premio_14, premio_15,
                premio_total, lucro_liquido
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, dados)
        conn.commit()
        conn.close()

    def get_financeiro_total(self):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COALESCE(SUM(custo_total),  0) as total_investido,
                COALESCE(SUM(premio_total), 0) as total_ganho,
                COALESCE(SUM(lucro_liquido),0) as lucro_total,
                COALESCE(SUM(acertos_11),   0) as total_11,
                COALESCE(SUM(acertos_12),   0) as total_12,
                COALESCE(SUM(acertos_13),   0) as total_13,
                COALESCE(SUM(acertos_14),   0) as total_14,
                COALESCE(SUM(acertos_15),   0) as total_15
            FROM financeiro
        """)
        result = cursor.fetchone()
        conn.close()
        return result

    # =========================================================
    # IA
    # =========================================================

    def inserir_aprendizado(self, dados):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ia_aprendizado (
                epoca, data, acuracia_media, erro_medio, melhor_score,
                total_cartelas_testadas, taxa_13_pontos, taxa_14_pontos,
                taxa_15_pontos, parametros_otimizados
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """, dados)
        conn.commit()
        conn.close()

    def get_historico_aprendizado(self):
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM ia_aprendizado ORDER BY epoca DESC LIMIT 50"
        )
        rows = cursor.fetchall()
        conn.close()
        return rows