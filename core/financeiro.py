"""
============================================================
MÓDULO FINANCEIRO
Calcula custos, prêmios e lucros
============================================================
"""
from config import VALOR_APOSTA, PREMIOS_FIXOS
from database.db_manager import DBManager
from datetime import datetime


class Financeiro:

    def __init__(self):
        self.db = DBManager()

    def calcular_custo(self, n_cartelas):
        """Calcula custo total das apostas"""
        return n_cartelas * VALOR_APOSTA

    def calcular_premio(self, acertos, valor_rateio_14=None, valor_rateio_15=None):
        """Calcula prêmio por faixa de acerto"""
        if acertos in PREMIOS_FIXOS:
            return PREMIOS_FIXOS[acertos]
        elif acertos == 14:
            # Financeiro realizado não pode transformar média em prêmio real.
            return float(valor_rateio_14 or 0.0)
        elif acertos == 15:
            return float(valor_rateio_15 or 0.0)
        return 0

    def registrar_resultado_financeiro(self, concurso, cartelas_conferidas,
                                        valor_14=None, valor_15=None):
        """Registra resultado financeiro de um concurso"""
        n_cartelas = len(cartelas_conferidas)
        custo = self.calcular_custo(n_cartelas)

        acertos_por_faixa = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}
        premios_por_faixa = {11: 0, 12: 0, 13: 0, 14: 0, 15: 0}

        for cart in cartelas_conferidas:
            acertos = cart.get('acertos', 0)
            if acertos >= 11:
                acertos_por_faixa[acertos] = acertos_por_faixa.get(acertos, 0) + 1
                premio = self.calcular_premio(acertos, valor_14, valor_15)
                premios_por_faixa[acertos] = premios_por_faixa.get(acertos, 0) + premio

        premio_total = sum(premios_por_faixa.values())
        lucro = premio_total - custo

        dados = (
            concurso, datetime.now().strftime('%Y-%m-%d'),
            n_cartelas, custo,
            acertos_por_faixa[11], acertos_por_faixa[12],
            acertos_por_faixa[13], acertos_por_faixa[14],
            acertos_por_faixa[15],
            premios_por_faixa[11], premios_por_faixa[12],
            premios_por_faixa[13], premios_por_faixa[14],
            premios_por_faixa[15],
            premio_total, lucro
        )

        # Reconciliação idempotente: uma nova conferência substitui o resumo
        # do concurso inteiro. Assim, cartelas adicionadas depois e migrações de
        # BLOB não deixam o financeiro congelado no primeiro cálculo.
        conn = self.db.get_conn()
        try:
            conn.execute("DELETE FROM financeiro WHERE concurso = ?", (concurso,))
            conn.execute("""
                INSERT INTO financeiro (
                    concurso, data, qtd_cartelas, custo_total,
                    acertos_11, acertos_12, acertos_13, acertos_14, acertos_15,
                    premio_11, premio_12, premio_13, premio_14, premio_15,
                    premio_total, lucro_liquido
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, dados)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return {
            'concurso': concurso,
            'n_cartelas': n_cartelas,
            'custo': custo,
            'acertos': acertos_por_faixa,
            'premios': premios_por_faixa,
            'premio_total': premio_total,
            'lucro': lucro,
        }

    def get_resumo_geral(self):
        """Retorna resumo financeiro geral"""
        dados = self.db.get_financeiro_total()
        if not dados:
            return {
                'total_investido': 0,
                'total_ganho': 0,
                'lucro_total': 0,
                'roi': 0,
                'total_11': 0, 'total_12': 0,
                'total_13': 0, 'total_14': 0, 'total_15': 0,
            }

        total_investido = dados['total_investido']
        total_ganho = dados['total_ganho']
        roi = ((total_ganho - total_investido) / total_investido * 100) \
            if total_investido > 0 else 0

        return {
            'total_investido': total_investido,
            'total_ganho': total_ganho,
            'lucro_total': dados['lucro_total'],
            'roi': round(roi, 2),
            'total_11': dados['total_11'],
            'total_12': dados['total_12'],
            'total_13': dados['total_13'],
            'total_14': dados['total_14'],
            'total_15': dados['total_15'],
        }