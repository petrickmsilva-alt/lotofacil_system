"""
============================================================
MONITOR DE TRANSPARÊNCIA DA IA
Registra, audita e explica TUDO que a IA faz.
Você vê exatamente o que cada módulo decidiu e por quê.
============================================================
"""
import numpy as np
import json
import os
from datetime import datetime
from database.db_manager import DBManager
from config import DATABASE_PATH, TOTAL_DEZENAS


class IAMonitor:

    def __init__(self):
        self.db          = DBManager()
        self.sessao_atual = None
        self.log_sessao  = []
        self._criar_tabelas_monitor()

    # =========================================================
    # BANCO DE DADOS DO MONITOR
    # =========================================================

    def _criar_tabelas_monitor(self):
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        # Sessões de treinamento/geração
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

        # Log de cada módulo em cada sessão
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
                status       TEXT,
                FOREIGN KEY (sessao_id) REFERENCES ia_sessoes(id)
            )
        """)

        # Decisões da IA por cartela gerada
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

        # Histórico de aprendizado (como os pesos evoluem)
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

        # Comparação: o que a IA previu vs o que saiu
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

        conn.commit()
        conn.close()

    # =========================================================
    # SESSÃO
    # =========================================================

    def iniciar_sessao(self, tipo="treinamento"):
        """Inicia uma nova sessão de IA"""
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ia_sessoes (tipo, inicio, status)
            VALUES (?, ?, 'em_andamento')
        """, (tipo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        self.sessao_atual = cursor.lastrowid
        conn.close()
        self.log_sessao   = []
        self._inicio_sessao = datetime.now()
        print(f"\n{'='*60}")
        print(f"  IA MONITOR — Sessão #{self.sessao_atual} [{tipo.upper()}]")
        print(f"  Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"{'='*60}")
        return self.sessao_atual

    def finalizar_sessao(self, status="concluido", resumo=""):
        """Finaliza a sessão atual"""
        if not self.sessao_atual:
            return
        duracao = (datetime.now() - self._inicio_sessao).total_seconds()
        conn    = self.db.get_conn()
        cursor  = conn.cursor()
        cursor.execute("""
            UPDATE ia_sessoes
            SET fim = ?, duracao_seg = ?, status = ?, resumo = ?
            WHERE id = ?
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duracao, status, resumo, self.sessao_atual
        ))
        conn.commit()
        conn.close()
        print(f"\n{'='*60}")
        print(f"  Sessão #{self.sessao_atual} finalizada em {duracao:.1f}s")
        print(f"  Status: {status.upper()}")
        print(f"  {resumo}")
        print(f"{'='*60}\n")

    # =========================================================
    # LOG DE MÓDULO
    # =========================================================

    def log_modulo(self, modulo, acao, scores=None,
                   detalhes=None, duracao_ms=0, status="ok"):
        """
        Registra o que um módulo fez e decidiu.
        """
        # Calcular top 3 dezenas do módulo
        top3 = []
        score_medio = 0.0

        if scores is not None:
            arr = np.array(scores)
            if arr.max() > 0:
                arr_norm = arr / arr.max()
                top3_idx = np.argsort(arr_norm)[::-1][:3]
                top3     = [int(i + 1) for i in top3_idx]
                score_medio = float(np.mean(arr_norm))

        top3_str    = json.dumps(top3)
        detalhes_str = json.dumps(detalhes) if detalhes else "{}"

        # Salvar no banco
        if self.sessao_atual:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ia_modulos_log
                (sessao_id, modulo, acao, score_medio, top3_dezenas,
                 detalhes, timestamp, duracao_ms, status)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                self.sessao_atual, modulo, acao, score_medio,
                top3_str, detalhes_str,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                duracao_ms, status
            ))
            conn.commit()
            conn.close()

        # Print colorido no terminal
        icon  = "✅" if status == "ok" else "❌"
        top3_fmt = ", ".join([f"{d:02d}" for d in top3]) if top3 else "—"

        print(f"\n  [{modulo.upper():20s}] {icon} {acao}")
        print(f"    Score médio : {score_medio:.4f}")
        print(f"    Top 3 dezenas favorecidas: [{top3_fmt}]")

        if detalhes:
            for k, v in detalhes.items():
                if isinstance(v, float):
                    print(f"    {k:20s}: {v:.4f}")
                else:
                    print(f"    {k:20s}: {v}")

        entry = {
            "modulo":     modulo,
            "acao":       acao,
            "score":      score_medio,
            "top3":       top3,
            "status":     status,
            "duracao_ms": duracao_ms,
        }
        self.log_sessao.append(entry)

    # =========================================================
    # DECISÃO DE CARTELA
    # =========================================================

    def log_decisao_cartela(self, dezenas, scores_motores,
                             score_total, justificativa=""):
        """
        Registra a decisão final sobre uma cartela.
        Mostra qual módulo foi mais influente.
        """
        # Módulo dominante = maior score
        modulo_dom = max(scores_motores, key=scores_motores.get) \
            if scores_motores else "N/A"

        if self.sessao_atual:
            conn   = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ia_decisoes
                (sessao_id, dezenas, score_total,
                 score_markov, score_fisico, score_gaussiano,
                 score_ml, score_verlet, score_quantum,
                 score_chi2, score_bayes, score_kl, score_stacking,
                 modulo_dominante, justificativa, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                self.sessao_atual,
                json.dumps(dezenas),
                score_total,
                scores_motores.get("markov",    0),
                scores_motores.get("fisico",    0),
                scores_motores.get("gaussiano", 0),
                scores_motores.get("ml",        0),
                scores_motores.get("verlet",    0),
                scores_motores.get("quantum",   0),
                scores_motores.get("chi2",      0),
                scores_motores.get("bayes",     0),
                scores_motores.get("kl",        0),
                scores_motores.get("stacking",  0),
                modulo_dom,
                justificativa,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            conn.commit()
            conn.close()

        dez_fmt = " ".join([f"{d:02d}" for d in dezenas])
        print(f"\n  📋 CARTELA GERADA: [{dez_fmt}]")
        print(f"     Score Total   : {score_total:.4f}")
        print(f"     Módulo líder  : {modulo_dom.upper()}")
        print(f"     Justificativa : {justificativa}")

        # Barra visual dos scores
        print(f"\n     📊 CONTRIBUIÇÃO DE CADA MÓDULO:")
        for modulo, score in sorted(scores_motores.items(),
                                     key=lambda x: x[1], reverse=True):
            barra = "█" * int(score * 20)
            print(f"     {modulo:12s} [{barra:<20s}] {score:.4f}")

    # =========================================================
    # APRENDIZADO
    # =========================================================

    def log_aprendizado(self, concurso, acertos_real,
                        pesos_antes, pesos_depois,
                        modulo_mais_certo, modulo_mais_errou):
        """
        Registra como a IA aprendeu com o resultado real.
        """
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ia_evolucao_pesos
            (timestamp, concurso, acertos_real,
             peso_markov, peso_fisico, peso_gaussiano,
             peso_ml, peso_verlet, peso_quantum,
             peso_chi2, peso_bayes, peso_kl, peso_stacking, evento)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            concurso, acertos_real,
            pesos_depois.get("markov",     0),
            pesos_depois.get("fisico",     0),
            pesos_depois.get("gaussiano",  0),
            pesos_depois.get("ml",         0),
            pesos_depois.get("verlet",     0),
            pesos_depois.get("quantum",    0),
            pesos_depois.get("chi2",       0),
            pesos_depois.get("bayes",      0),
            pesos_depois.get("kl",         0),
            pesos_depois.get("stacking",   0),
            f"acertos={acertos_real} | "
            f"melhor={modulo_mais_certo} | "
            f"pior={modulo_mais_errou}",
        ))
        conn.commit()
        conn.close()

        print(f"\n{'='*60}")
        print(f"  🧠 IA APRENDENDO — Concurso {concurso}")
        print(f"{'='*60}")
        print(f"  Acertos reais   : {acertos_real} pontos")
        print(f"  Módulo mais certo: {modulo_mais_certo}")
        print(f"  Módulo mais errou: {modulo_mais_errou}")
        print(f"\n  AJUSTE DE PESOS:")

        for modulo in pesos_antes:
            antes  = pesos_antes.get(modulo,  0)
            depois = pesos_depois.get(modulo, 0)
            diff   = depois - antes
            sinal  = "↑" if diff > 0 else "↓" if diff < 0 else "="
            print(f"  {modulo:12s}: {antes:.4f} → {depois:.4f} "
                  f"{sinal} ({diff:+.4f})")

    # =========================================================
    # PREVISÃO vs REAL
    # =========================================================

    def log_previsao_vs_real(self, concurso, dezenas_previstas,
                              dezenas_reais, scores_por_modulo):
        """
        Registra e analisa: o que cada módulo previu vs
        o que realmente saiu no sorteio.
        """
        dez_prev = set(dezenas_previstas)
        dez_real = set(dezenas_reais)
        acertos  = len(dez_prev & dez_real)
        pct      = acertos / 15 * 100

        # Qual módulo acertou mais?
        acertos_por_modulo = {}
        for modulo, scores in scores_por_modulo.items():
            if scores is None:
                continue
            arr     = np.array(scores)
            top15   = set(np.argsort(arr)[::-1][:15] + 1)
            ac_mod  = len(top15 & dez_real)
            acertos_por_modulo[modulo] = ac_mod

        melhor_mod = max(acertos_por_modulo,
                         key=acertos_por_modulo.get) \
            if acertos_por_modulo else "N/A"
        pior_mod   = min(acertos_por_modulo,
                         key=acertos_por_modulo.get) \
            if acertos_por_modulo else "N/A"

        aprendizado = (
            f"Módulo {melhor_mod} acertou "
            f"{acertos_por_modulo.get(melhor_mod, 0)} dezenas. "
            f"Peso será aumentado."
        )

        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ia_previsao_vs_real
            (concurso, timestamp, dezenas_previstas, dezenas_reais,
             acertos, percentual, modulo_mais_certo,
             modulo_mais_errou, aprendizado)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            concurso,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(list(dezenas_previstas)),
            json.dumps(list(dezenas_reais)),
            acertos, pct, melhor_mod, pior_mod, aprendizado,
        ))
        conn.commit()
        conn.close()

        print(f"\n{'='*60}")
        print(f"  🎯 ANÁLISE: Previsto vs Real — Concurso {concurso}")
        print(f"{'='*60}")
        print(f"  Dezenas previstas: "
              f"{sorted(list(dez_prev))}")
        print(f"  Dezenas sorteadas: "
              f"{sorted(list(dez_real))}")
        print(f"  Acertos em comum : {acertos}/15 ({pct:.1f}%)")

        print(f"\n  🏆 RANKING DOS MÓDULOS (dezenas acertadas):")
        ranking = sorted(acertos_por_modulo.items(),
                         key=lambda x: x[1], reverse=True)
        for i, (mod, ac) in enumerate(ranking):
            medal = ["🥇","🥈","🥉"][i] if i < 3 else f"  {i+1}."
            barra = "█" * ac + "░" * (15 - ac)
            print(f"  {medal} {mod:12s} [{barra}] {ac:2d}/15")

        return {
            "acertos":         acertos,
            "melhor_modulo":   melhor_mod,
            "pior_modulo":     pior_mod,
            "acertos_modulos": acertos_por_modulo,
        }

    # =========================================================
    # RELATÓRIOS
    # =========================================================

    def get_relatorio_sessao(self, sessao_id=None):
        """Retorna relatório completo de uma sessão"""
        sid    = sessao_id or self.sessao_atual
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM ia_sessoes WHERE id = ?", (sid,)
        )
        sessao = cursor.fetchone()

        cursor.execute("""
            SELECT modulo, acao, score_medio, top3_dezenas,
                   duracao_ms, status
            FROM ia_modulos_log
            WHERE sessao_id = ?
            ORDER BY id ASC
        """, (sid,))
        modulos = cursor.fetchall()

        cursor.execute("""
            SELECT dezenas, score_total, modulo_dominante,
                   score_markov, score_fisico, score_gaussiano,
                   score_ml, score_verlet, score_quantum,
                   score_chi2, score_bayes, score_kl
            FROM ia_decisoes
            WHERE sessao_id = ?
            ORDER BY score_total DESC
        """, (sid,))
        decisoes = cursor.fetchall()

        conn.close()
        return {
            "sessao":   dict(sessao) if sessao else {},
            "modulos":  [dict(m) for m in modulos],
            "decisoes": [dict(d) for d in decisoes],
        }

    def get_evolucao_pesos(self, limit=30):
        """Histórico de como os pesos evoluíram"""
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM ia_evolucao_pesos
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_ranking_modulos(self):
        """
        Ranking geral de qual módulo acerta mais.
        """
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT modulo_mais_certo,
                   COUNT(*) as vezes_melhor,
                   AVG(acertos) as media_acertos
            FROM ia_previsao_vs_real
            GROUP BY modulo_mais_certo
            ORDER BY vezes_melhor DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_ultimas_sessoes(self, limit=10):
        conn   = self.db.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tipo, inicio, fim, duracao_seg,
                   status, resumo
            FROM ia_sessoes
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_dashboard_stats(self):
        """Estatísticas gerais para o dashboard"""
        conn   = self.db.get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM ia_sessoes")
        total_sessoes = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM ia_sessoes WHERE status='concluido'"
        )
        sessoes_ok = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ia_decisoes")
        total_decisoes = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(acertos), MAX(acertos) FROM ia_previsao_vs_real"
        )
        row = cursor.fetchone()
        media_ac = round(float(row[0] or 0), 2)
        max_ac   = int(row[1] or 0)

        cursor.execute("""
            SELECT modulo_mais_certo, COUNT(*) as c
            FROM ia_previsao_vs_real
            GROUP BY modulo_mais_certo
            ORDER BY c DESC LIMIT 1
        """)
        row2    = cursor.fetchone()
        melhor  = row2[0] if row2 else "N/A"

        conn.close()

        return {
            "total_sessoes":   total_sessoes,
            "sessoes_ok":      sessoes_ok,
            "total_decisoes":  total_decisoes,
            "media_acertos":   media_ac,
            "max_acertos":     max_ac,
            "melhor_modulo":   melhor,
        }