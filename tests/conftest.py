"""Configuração compartilhada da suíte.

`LOTOFACIL_ACERVO_AUTO=0` mantém o acervo de conhecimento da Magna em modo
somente-leitura durante os testes: a instância lê a base histórica (o
conhecimento está lá e é usado nas decisões), mas nenhuma gravação ou
calibração fundante é disparada por iniciativa própria. Sem isso, cada
`CerebroIA(...)` novo pagaria a recalibração walk-forward da base inteira ou
escreveria no banco do repositório.

Os testes que querem exercitar a persistência chamam explicitamente
`assimilar_acervo(forcar=True)` — caminho manual, que o ambiente não bloqueia.
"""
import os
import sys

os.environ.setdefault("LOTOFACIL_ACERVO_AUTO", "0")
os.environ.setdefault("LOTOFACIL_ACERVO_BOOT", "0")
os.environ.setdefault("LOTOFACIL_LOOP_SEG", "0")

# garante que `import core...`/`import config` funcionem sem instalar o pacote
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
