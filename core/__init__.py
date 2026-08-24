"""
============================================================
CORE — Módulos do Sistema Lotofácil
Cérebro IA v6.0 é o protagonista único
============================================================
"""

# ── Protagonista único ────────────────────────────────────────
from .cerebro_ia         import CerebroIA

# ── Módulos de suporte ────────────────────────────────────────
from .bitmatrix          import BitMatrix
from .data_loader        import DataLoader
from .conferencia        import Conferencia
from .financeiro         import Financeiro
from .ia_monitor         import IAMonitor
from .wheeling           import MotorWheeling
from .heavyweight_engine import MotorExaustaoUniverso

# Fase 3 (2026-08-24): filtros_gaussianos, markov_engine,
# fisica_quantica e covering_designs foram REMOVIDOS — eram órfãos
# nunca instanciados, duplicados pelos motores internos do CerebroIA
# (MotorGaussiano/MotorMarkov/MotorQuantum) e pelo core/wheeling.py.