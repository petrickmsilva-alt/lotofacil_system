"""
============================================================
CONFIGURAÇÕES GLOBAIS DO SISTEMA LOTOFÁCIL
============================================================
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "lotofacil.db")
MODELS_PATH = os.path.join(BASE_DIR, "database", "modelos")

# Garantir que pastas existam
os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)
os.makedirs(MODELS_PATH, exist_ok=True)

# ============================================================
# CONSTANTES DA LOTOFÁCIL
# ============================================================
TOTAL_DEZENAS = 25
DEZENAS_POR_JOGO = 15
VALOR_APOSTA = 3.50

# Prêmios fixos (valores médios para 11, 12, 13)
PREMIOS_FIXOS = {
    11: 7.00,
    12: 14.00,
    13: 35.00,
}

# 14 e 15 são rateados - valores médios históricos
PREMIOS_RATEADOS_MEDIA = {
    14: 1800.00,
    15: 2500000.00,
}

# ============================================================
# CONSTANTES FÍSICAS DAS BOLAS
# ============================================================
MASSA_BOLA_KG = 0.066        # 66g
DIAMETRO_BOLA_M = 0.050      # 50mm = 5cm
RAIO_BOLA_M = 0.025
COEF_RESTITUICAO = 0.82       # Borracha maciça
TEMPERATURA_K = 294.5          # ~21.5°C
PRESSAO_ATM = 0.92             # São Paulo
DENSIDADE_AR = 1.20            # kg/m³
UMIDADE_RELATIVA = 0.55        # 55%
GRAVIDADE = 9.78               # São Paulo

# ============================================================
# PARÂMETROS DOS FILTROS
# (Recalibrados na auditoria Fase 3 — 2026-08-24, 3.767 concursos:
#  faixas = percentis p1–p99 REAIS do histórico. As faixas antigas
#  rejeitavam ~70% dos sorteios reais.)
# ============================================================
SOMA_MIN = 155
SOMA_MAX = 235
MAX_CONSECUTIVOS = 14      # maior sequência real observada
PRIMOS_MIN = 3
PRIMOS_MAX = 8
FIBONACCI_MIN = 2
FIBONACCI_MAX = 7
BORDA_MIN = 7
BORDA_MAX = 12
REPETICAO_MIN = 6
REPETICAO_MAX = 12

# Quadrantes do volante
QUADRANTES = {
    1: [1, 2, 3, 4, 5],
    2: [6, 7, 8, 9, 10],
    3: [11, 12, 13, 14, 15],
    4: [16, 17, 18, 19, 20],
    5: [21, 22, 23, 24, 25],
}

# Números primos até 25
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

# Fibonacci até 25
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}

# Borda do volante (números das extremidades da grade 5x5)
BORDA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
MIOLO = {7, 8, 9, 12, 13, 14, 17, 18, 19}

# URL da Caixa
URL_RESULTADOS = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/"
