"""
============================================================
GERENCIADOR DE BANCO DE DADOS
Tabela de resultados com prêmios REAIS da Caixa
============================================================
"""
import sqlite3
from config import DATABASE_PATH


class DBManager:

    def __init__(self, db_path=None):
        """Cria o repositório SQLite.

        O caminho injetável mantém produção e testes separados. Antes, mesmo
        `CerebroIA(db_path=...)` continuava escrevendo no banco global porque o
        DBManager ignorava o caminho recebido pelo Cérebro.
        """
        self.db_path = db_path or DATABASE_PATH
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

        # ── Auditoria de sincronização do histórico ───────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_atualizacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inicio TEXT NOT NULL,
                fim TEXT NOT NULL,
                status TEXT NOT NULL,
                fonte TEXT,
                ultimo_local_antes INTEGER DEFAULT 0,
                ultimo_remoto INTEGER DEFAULT 0,
                ultimo_local_depois INTEGER DEFAULT 0,
                novos INTEGER DEFAULT 0,
                recuperados INTEGER DEFAULT 0,
                erros INTEGER DEFAULT 0,
                detalhes TEXT
            )
        """)

        # ── Física das Bolas ─────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fisica_bolas (
                numero INTEGER PRIMARY KEY,
                massa_g REAL,
                diametro_mm REAL,
                circunferencia_mm REAL,
                cor TEXT,
                material TEXT,
                rugosidade REAL,
                coef_restituicao REAL,
                ciclos_uso INTEGER DEFAULT 0,
                indice_desgaste REAL DEFAULT 0,
                atualizado_em TEXT
            )
        """)

        # ── Ambiente do Sorteio ─────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fisica_ambientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso INTEGER,
                maquina TEXT,
                conjunto_bolas TEXT,
                temperatura_K REAL,
                pressao_atm REAL,
                umidade REAL,
                densidade_ar REAL,
                gravidade REAL,
                velocidade_rotacao REAL,
                duracao_mistura REAL,
                data_ultima_manutencao TEXT,
                registrado_em TEXT
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memoria_cartelas_aprendidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cartela_origem_id INTEGER,
                concurso INTEGER,
                bitmask INTEGER,
                dezenas TEXT NOT NULL,
                acertos INTEGER DEFAULT 0,
                premio_ganho REAL DEFAULT 0,
                status TEXT,
                score_total REAL DEFAULT 0,
                timestamp TEXT,
                UNIQUE(concurso, bitmask)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memoria_bitmask "
            "ON memoria_cartelas_aprendidas(bitmask)"
        )

        # ── Ordem real de sorteio (1ª, 2ª, ... 15ª bola) ─────
        # v11.3 — fonte dos padrões de ordem (MotorOrdemSorteio).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordem_sorteio (
                concurso INTEGER PRIMARY KEY,
                b1  INTEGER NOT NULL, b2  INTEGER NOT NULL,
                b3  INTEGER NOT NULL, b4  INTEGER NOT NULL,
                b5  INTEGER NOT NULL, b6  INTEGER NOT NULL,
                b7  INTEGER NOT NULL, b8  INTEGER NOT NULL,
                b9  INTEGER NOT NULL, b10 INTEGER NOT NULL,
                b11 INTEGER NOT NULL, b12 INTEGER NOT NULL,
                b13 INTEGER NOT NULL, b14 INTEGER NOT NULL,
                b15 INTEGER NOT NULL,
                atualizado_em TEXT,
                CHECK (b1 BETWEEN 1 AND 25 AND b2 BETWEEN 1 AND 25
                   AND b3 BETWEEN 1 AND 25 AND b4 BETWEEN 1 AND 25
                   AND b5 BETWEEN 1 AND 25 AND b6 BETWEEN 1 AND 25
                   AND b7 BETWEEN 1 AND 25 AND b8 BETWEEN 1 AND 25
                   AND b9 BETWEEN 1 AND 25 AND b10 BETWEEN 1 AND 25
                   AND b11 BETWEEN 1 AND 25 AND b12 BETWEEN 1 AND 25
                   AND b13 BETWEEN 1 AND 25 AND b14 BETWEEN 1 AND 25
                   AND b15 BETWEEN 1 AND 25)
            )
        """)

        conn.commit()
        conn.close()

    # =========================================================
    # ORDEM DE SORTEIO (v11.3)
    # =========================================================

    def salvar_ordem(self, concurso, ordem):
        """Upsert idempotente da ordem real das 15 bolas de um concurso.

        `ordem`: sequência de 15 ints únicos 1–25, na ordem de extração.
        Retorna True se gravado; rejeita dados inválidos (validação dupla
        com a CHECK da tabela).
        """
        vals = [int(d) for d in ordem]
        if (len(vals) != 15 or len(set(vals)) != 15 or
                any(d < 1 or d > 25 for d in vals)):
            raise ValueError(
                "ordem inválida: 15 dezenas únicas 1–25 obrigatórias")
        conn = self.get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO ordem_sorteio (
                    concurso, b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,
                    b11,b12,b13,b14,b15)
                VALUES (?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (int(concurso), *vals))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_ordem(self, concurso):
        """Ordem (b1..b15) de um concurso ou None."""
        conn = self.get_conn()
        try:
            row = conn.execute(
                "SELECT b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,b11,b12,b13,b14,b15 "
                "FROM ordem_sorteio WHERE concurso=?",
                (int(concurso),)).fetchone()
            return list(row) if row else None
        finally:
            conn.close()

    def get_concursos_sem_ordem(self, limite=None):
        """Concursos do histórico oficial que ainda não têm ordem gravada."""
        conn = self.get_conn()
        try:
            sql = ("SELECT r.concurso FROM resultados r "
                   "LEFT JOIN ordem_sorteio o ON o.concurso = r.concurso "
                   "WHERE o.concurso IS NULL ORDER BY r.concurso DESC")
            if limite:
                sql += " LIMIT {}".format(int(limite))
            return [int(r[0]) for r in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    # =========================================================
    # RESULTADOS
    # =========================================================

    def inserir_resultado(self, dados, preservar_premios=False):
        """Insere/atualiza um concurso e propaga qualquer falha de persistência.

        Fontes de contingência podem não possuir rateio. Nesse caso, os campos
        financeiros já existentes são preservados em vez de serem zerados.
        """
        valores = list(dados)
        if len(valores) != 36:
            raise ValueError("resultado deve possuir 36 campos")

        conn = self.get_conn()
        try:
            cursor = conn.cursor()
            if preservar_premios:
                existente = cursor.execute(
                    "SELECT * FROM resultados WHERE concurso=?",
                    (int(valores[0]),),
                ).fetchone()
                if existente is not None:
                    for offset, acertos in enumerate(range(11, 16)):
                        valores[25 + offset] = float(
                            existente["premio_{}".format(acertos)] or 0)
                        valores[30 + offset] = int(
                            existente["ganhadores_{}".format(acertos)] or 0)
                    valores[35] = float(existente["arrecadacao"] or 0)

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
            """, tuple(valores))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
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

    def registrar_atualizacao_historico(self, dados):
        conn = self.get_conn()
        try:
            conn.execute("""
                INSERT INTO historico_atualizacoes
                (inicio,fim,status,fonte,ultimo_local_antes,ultimo_remoto,
                 ultimo_local_depois,novos,recuperados,erros,detalhes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, dados)
            conn.commit()
        finally:
            conn.close()

    def get_ultima_atualizacao_historico(self):
        conn = self.get_conn()
        try:
            return conn.execute("""
                SELECT * FROM historico_atualizacoes
                ORDER BY id DESC LIMIT 1
            """).fetchone()
        finally:
            conn.close()

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

    def limpar_financeiro(self):
        """Apaga todos os resultados financeiros registrados.

        Retorna a quantidade de registros removidos. Não toca em
        resultados, cartelas ou aprendizado — apenas o módulo financeiro.
        """
        conn   = self.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM financeiro")
        removidos = cursor.fetchone()[0]
        cursor.execute("DELETE FROM financeiro")
        conn.commit()
        conn.close()
        return removidos

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

    def arquivar_cartela_aprendida(self, dados):
        """Persiste cartela conferida na memória de longo prazo.

        `dados`: (cartela_origem_id, concurso, bitmask, dezenas_json,
                  acertos, premio, status, score_total, timestamp)
        Duplicatas (mesmo concurso+bitmask) são ignoradas.
        """
        conn = self.get_conn()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO memoria_cartelas_aprendidas
                (cartela_origem_id, concurso, bitmask, dezenas, acertos,
                 premio_ganho, status, score_total, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, dados)
            conn.commit()
        finally:
            conn.close()

    def get_bitmasks_15_oficiais(self):
        """Bitmasks de todos os sorteios oficiais (15 pontos já ocorreram)."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT bitmask FROM resultados WHERE bitmask IS NOT NULL"
            ).fetchall()
            return {int(r[0]) for r in rows if r[0] is not None}
        finally:
            conn.close()