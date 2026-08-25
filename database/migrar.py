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
from config import DATABASE_PATH, VALOR_APOSTA


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

    # ── Reparação de inteiros NumPy gravados como BLOB ────────
    # Builds antigos enviavam np.int64 diretamente ao sqlite3. O driver
    # persistia oito bytes little-endian e a conferência os lia como zero.
    # A migração é idempotente: só toca linhas que ainda contêm BLOB.
    concursos_reparados = set()
    try:
        rows_blob = cursor.execute("""
            SELECT id, concurso_alvo,
                   d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15
            FROM cartelas
            WHERE typeof(d1)='blob' OR typeof(d2)='blob' OR
                  typeof(d3)='blob' OR typeof(d4)='blob' OR
                  typeof(d5)='blob' OR typeof(d6)='blob' OR
                  typeof(d7)='blob' OR typeof(d8)='blob' OR
                  typeof(d9)='blob' OR typeof(d10)='blob' OR
                  typeof(d11)='blob' OR typeof(d12)='blob' OR
                  typeof(d13)='blob' OR typeof(d14)='blob' OR
                  typeof(d15)='blob'
        """).fetchall()

        def blob_para_int(valor):
            if isinstance(valor, (bytes, bytearray, memoryview)):
                raw = bytes(valor)
                try:
                    return int(raw.decode("ascii"))
                except (UnicodeDecodeError, ValueError):
                    return int.from_bytes(raw, "little", signed=True)
            return int(valor)

        for row in rows_blob:
            cartela_id, concurso_alvo = int(row[0]), int(row[1])
            dezenas = [blob_para_int(v) for v in row[2:17]]
            if (len(set(dezenas)) != 15 or
                    any(d < 1 or d > 25 for d in dezenas)):
                print("  [!] Cartela {} com BLOB inválido; não migrada".format(
                    cartela_id))
                continue
            bitmask = sum(1 << (d - 1) for d in dezenas)
            resultado = cursor.execute(
                "SELECT * FROM resultados WHERE concurso=?", (concurso_alvo,)
            ).fetchone()
            acertos = 0
            premio = 0.0
            conferida = 0
            status_cartela = "pendente"
            if resultado:
                nomes = [d[0] for d in cursor.description]
                # `cursor.description` agora pertence ao SELECT resultados.
                res = dict(zip(nomes, resultado))
                sorteadas = {int(res["d{}".format(i)]) for i in range(1, 16)}
                acertos = len(set(dezenas) & sorteadas)
                conferida = 1
                status_cartela = (
                    "premio_15" if acertos == 15 else
                    "premio_14" if acertos == 14 else
                    "premio_13" if acertos == 13 else
                    "premio_12" if acertos == 12 else
                    "premio_11" if acertos == 11 else "sem_premio"
                )
                if acertos in (11, 12, 13):
                    premio = float(res.get("premio_{}".format(acertos)) or
                                   {11: 7.0, 12: 14.0, 13: 35.0}[acertos])
                elif acertos in (14, 15):
                    premio = float(res.get("premio_{}".format(acertos)) or 0.0)

            cursor.execute("""
                UPDATE cartelas SET
                    d1=?,d2=?,d3=?,d4=?,d5=?,d6=?,d7=?,d8=?,d9=?,d10=?,
                    d11=?,d12=?,d13=?,d14=?,d15=?, bitmask=?,
                    conferida=?, acertos=?, premio_ganho=?, status=?
                WHERE id=?
            """, (*dezenas, bitmask, conferida, acertos, premio,
                  status_cartela, cartela_id))
            concursos_reparados.add(concurso_alvo)

        # Reconstrói os resumos financeiros dos concursos afetados usando todas
        # as cartelas, agora corretamente conferidas.
        for concurso in sorted(concursos_reparados):
            resumo = cursor.execute("""
                SELECT COUNT(*) qtd,
                       SUM(CASE WHEN acertos=11 THEN 1 ELSE 0 END) a11,
                       SUM(CASE WHEN acertos=12 THEN 1 ELSE 0 END) a12,
                       SUM(CASE WHEN acertos=13 THEN 1 ELSE 0 END) a13,
                       SUM(CASE WHEN acertos=14 THEN 1 ELSE 0 END) a14,
                       SUM(CASE WHEN acertos=15 THEN 1 ELSE 0 END) a15,
                       SUM(CASE WHEN acertos=11 THEN premio_ganho ELSE 0 END) p11,
                       SUM(CASE WHEN acertos=12 THEN premio_ganho ELSE 0 END) p12,
                       SUM(CASE WHEN acertos=13 THEN premio_ganho ELSE 0 END) p13,
                       SUM(CASE WHEN acertos=14 THEN premio_ganho ELSE 0 END) p14,
                       SUM(CASE WHEN acertos=15 THEN premio_ganho ELSE 0 END) p15,
                       SUM(premio_ganho) total
                FROM cartelas WHERE concurso_alvo=?
            """, (concurso,)).fetchone()
            qtd = int(resumo[0] or 0)
            custo = qtd * VALOR_APOSTA
            total_premio = float(resumo[11] or 0.0)
            cursor.execute("DELETE FROM financeiro WHERE concurso=?", (concurso,))
            cursor.execute("""
                INSERT INTO financeiro
                (concurso,data,qtd_cartelas,custo_total,
                 acertos_11,acertos_12,acertos_13,acertos_14,acertos_15,
                 premio_11,premio_12,premio_13,premio_14,premio_15,
                 premio_total,lucro_liquido)
                VALUES (?,date('now'),?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                concurso, qtd, custo,
                int(resumo[1] or 0), int(resumo[2] or 0), int(resumo[3] or 0),
                int(resumo[4] or 0), int(resumo[5] or 0),
                float(resumo[6] or 0), float(resumo[7] or 0),
                float(resumo[8] or 0), float(resumo[9] or 0),
                float(resumo[10] or 0), total_premio, total_premio - custo,
            ))
        if rows_blob:
            print("  [✓] {} cartelas BLOB reparadas".format(len(rows_blob)))
    except (sqlite3.Error, ValueError, TypeError) as exc:
        print("  [!] Reparação BLOB: {}".format(exc))

    # Recria cabeçalhos ausentes para lotes legados, preservando a capacidade
    # de conferi-los e apagá-los pela interface.
    try:
        lotes_orfaos = cursor.execute("""
            SELECT c.lote_id, MIN(c.data_geracao), c.concurso_alvo,
                   COALESCE(c.tipo_geracao,'migrado'), COUNT(*)
            FROM cartelas c
            LEFT JOIN lotes_cartelas l ON l.lote_id=c.lote_id
            WHERE c.lote_id IS NOT NULL AND l.lote_id IS NULL
            GROUP BY c.lote_id, c.concurso_alvo, c.tipo_geracao
        """).fetchall()
        for lote_id, data_criacao, concurso, tipo, qtd in lotes_orfaos:
            cursor.execute("""
                INSERT INTO lotes_cartelas
                (lote_id,data_criacao,concurso_alvo,tipo_geracao,quantidade,
                 custo_total,modo,grupo_elite,cobertura_13,observacao)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                lote_id, data_criacao, concurso, tipo, qtd,
                int(qtd) * VALOR_APOSTA, "migrado", "[]", 0.0,
                "Cabeçalho reconstruído pela migração de integridade",
            ))
        if lotes_orfaos:
            print("  [✓] {} cabeçalhos de lote reconstruídos".format(
                len(lotes_orfaos)))
    except sqlite3.Error as exc:
        print("  [!] Reparação de lotes: {}".format(exc))

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