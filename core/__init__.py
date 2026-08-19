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

# ── Módulos auxiliares usados pelo CerebroIA ──────────────────
from .filtros_gaussianos import FiltrosGaussianos
from .markov_engine      import MarkovEngine
from .fisica_quantica    import FisicaQuantica
from .covering_designs   import CoveringDesigns