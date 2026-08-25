"""
Regressões da Fase 5 — auditoria de bugs, módulos e filtros.

Cobre as correções:
- MotorRepulsaoVetorial tem um ÚNICO calcular_forca_repulsao (antes, havia
  dois; o primeiro era código morto sobrescrito pelo segundo).
- gerar_cartelas() reaproveita, na passagem 2, as candidatas válidas
  adiadas por repulsão forte (antes a passagem 2 era código morto: a
  passagem 1 marcava TODAS as candidatas em "vistas").
- gerar_cartela_do_dia() é idempotente por concurso-alvo (um F5 não gera
  nem salva uma cartela nova).
- O ciclo autônomo confere as apostas do concurso que acabou de sair (antes
  conferia a fila de "próximo" contra o resultado de "concurso" — off-by-one
  que fazia o ciclo nunca acertar nada e aprender com a comparação errada).
- Nenhum módulo usa np.random.seed global (estado global que contaminava a
  aleatoriedade dos outros módulos).

Roda como:
    pytest tests/test_regressoes_fase5.py
"""
import inspect
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.cerebro_ia import (
    CerebroIA, MotorRepulsaoVetorial,
)


def test_metodo_repulsao_definido_uma_unica_vez():
    src = inspect.getsource(MotorRepulsaoVetorial)
    assert src.count("def calcular_forca_repulsao") == 1, \
        "calcular_forca_repulsao está duplicado (código morto)"


def test_repulsao_duplicata_e_quase_duplicata():
    m = MotorRepulsaoVetorial.__new__(MotorRepulsaoVetorial)  # sem DB
    recentes = [set(range(1, 16))]
    # idêntica → repulsão total
    assert m.calcular_forca_repulsao(list(range(1, 16)), recentes) == 0.0
    # 14 em comum → penalidade forte (0.10)
    quatorze = list(range(1, 15)) + [16]
    assert m.calcular_forca_repulsao(quatorze, recentes) < 0.2
    # sem jogos anteriores → neutro
    assert m.calcular_forca_repulsao(list(range(1, 16)), []) == 1.0


@pytest.fixture(scope="module")
def cerebro(tmp_path_factory):
    from config import DATABASE_PATH
    caminho = tmp_path_factory.mktemp("regressoes") / "teste.db"
    shutil.copy2(DATABASE_PATH, caminho)
    c = CerebroIA(db_path=str(caminho))
    c.treinar()
    return c


def test_gerar_cartelas_entrega_quantidade_e_metricas(cerebro):
    cs = cerebro.gerar_cartelas(quantidade=8)
    assert len(cs) == 8
    for cartela in cs:
        assert len(cartela["dezenas"]) == 15
        assert len(set(cartela["dezenas"])) == 15
    # métricas novas expostas (separação das causas de reprovação)
    for chave in ("reprovadas_gauss", "reprovadas_duplicada",
                  "reprovadas_repulsao"):
        assert chave in cerebro.metricas


def test_cartela_do_dia_idempotente(cerebro):
    # Duas chamadas seguidas devem devolver a MESMA cartela para o mesmo
    # concurso-alvo (e não criar uma segunda linha na tabela cartela_do_dia).
    import sqlite3

    conn = sqlite3.connect(cerebro.db_path)
    antes = conn.execute(
        "SELECT COUNT(*) FROM cartela_do_dia").fetchone()[0]
    conn.close()

    r1 = cerebro.gerar_cartela_do_dia()
    r2 = cerebro.gerar_cartela_do_dia()

    conn = sqlite3.connect(cerebro.db_path)
    depois = conn.execute(
        "SELECT COUNT(*) FROM cartela_do_dia").fetchone()[0]
    conn.close()

    assert r1["cartela"] == r2["cartela"]
    # A primeira chamada pode inserir 0 (se já existia) ou 1; a segunda
    # obrigatoriamente não insere nada.
    assert depois - antes <= 1


def test_ciclo_confere_concurso_certo():
    """O INSERT na fila deve usar o PRÓXIMO concurso, mas a conferência
    (`_conferir`) deve ler a fila do concurso que acabou de sair — não do
    próximo. Garantimos isso conferindo o corpo do método."""
    src = inspect.getsource(CerebroIA._executar_ciclo_sem_lock)
    # A busca do resultado acontece ANTES de gerar novas apostas
    pos_resultado = src.find("buscar_concurso_caixa")
    pos_gerar = src.find("self.decidir_e_gerar")
    assert 0 < pos_resultado < pos_gerar, \
        "executar_ciclo deve buscar/conferir o resultado antes de gerar " \
        "apostas para o próximo"
    # A conferência usa o concurso que saiu; a decisão Magna recebe o próximo.
    assert src.find("self._conferir(concurso") > 0
    assert "concurso_alvo=proximo" in src


def test_modulos_sem_estado_global_np_random():
    """Nenhum módulo do núcleo deve chamar np.random.seed (que polui o
    gerador global do processo)."""
    import glob
    for caminho in glob.glob(os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "core", "*.py")):
        with open(caminho, encoding="utf-8") as f:
            conteudo = f.read()
        assert "np.random.seed(" not in conteudo, \
            "{} usa np.random.seed global — use default_rng local".format(
                os.path.basename(caminho))
