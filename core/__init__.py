"""
Núcleo do Sistema Lotofácil.

A única inteligência pública é `InteligenciaMagna`. As classes auxiliares são
instrumentos internos de cálculo; nenhuma delas decide ou gera cartelas fora do
fluxo unificado.
"""

from .cerebro_ia import CerebroIA, InteligenciaMagna
from .bitmatrix import BitMatrix
from .data_loader import DataLoader
from .conferencia import Conferencia
from .financeiro import Financeiro
from .wheeling import MotorWheeling
from .heavyweight_engine import MotorExaustaoUniverso

__all__ = [
    "InteligenciaMagna",
    "CerebroIA",  # alias de compatibilidade para integrações antigas
    "BitMatrix",
    "DataLoader",
    "Conferencia",
    "Financeiro",
    "MotorWheeling",
    "MotorExaustaoUniverso",
]
