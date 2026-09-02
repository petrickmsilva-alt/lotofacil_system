"""v12.1 — Relatório pré-cartelas + juízo completo em TODA decisão.

Verifica que a Inteligência Magna, no fluxo principal (`decidir_e_gerar`):
  1. registra a trilha auditável de tudo que processa ANTES de gerar
     (`relatorio_pre_cartelas`), em ordem, com duração e sem erros;
  2. executa os processos que antes só existiam na Suprema: Juiz 9
     critérios, adversarial, NIST, p-value, backtest, curva, utilidade
     esperada e fingerprint pessoal;
  3. aplica o bloqueio de combinações já sorteadas com 15 pontos no
     `gerar_otimas` (antes era código morto no fluxo principal);
  4. produz o relatório SOZINHO, sem gerar nenhuma cartela.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from config import DATABASE_PATH
from core.cerebro_ia import InteligenciaMagna

# ordem esperada das etapas do pré-processamento (subconjunto verificável)
ETAPAS_EM_ORDEM = [
    "validacao_entrada",
    "treinamento_memoria_unica",
    "acervo_conhecimento",
    "evidencia_acervo",
    "percepcao_ambiente",
    "regime_atual",
    "fontes_assimiladas",
    "pesos_fontes",
    "consenso_vetor_final",
    "memoria_episodica",
    "rota_extraordinaria",
    "fingerprint_pessoal",
    "geracao_cartelas",
    "juizo_lote_magna",
    "verificacoes_honestidade",
]


@pytest.fixture
def magna_tmp(tmp_path):
    caminho = tmp_path / "magna_precart.db"
    shutil.copy2(DATABASE_PATH, caminho)
    m = InteligenciaMagna(db_path=str(caminho), n_cartelas=10)
    # isola rede: a percepção de ambiente não deve depender de INMET aqui
    m.perceber_ambiente_autonomo = (
        lambda *a, **k: {"status": "neutro", "concurso": 0,
                         "ambiente_registrado": False,
                         "telemetria": None, "clima": None,
                         "local": None, "fonte": "neutro",
                         "leitura": "teste isolado"})
    yield m


def test_decisao_traz_relatorio_pre_cartelas_em_ordem(magna_tmp):
    res = magna_tmp.decidir_e_gerar(quantidade=2, registrar=False,
                                    tentativas_juiz=1)
    rel = res["relatorio_pre_cartelas"]
    nomes = [et["nome"] for et in rel["etapas"]]
    for nome in ETAPAS_EM_ORDEM:
        assert nome in nomes, "etapa ausente do relatório: {}".format(nome)
    indices = [nomes.index(n) for n in ETAPAS_EM_ORDEM]
    assert indices == sorted(indices), "etapas fora da ordem do pipeline"
    for et in rel["etapas"]:
        assert et["status"] in ("ok", "neutro", "aviso", "ignorado")
        assert et["duracao_ms"] >= 0.0
    resumo = rel["resumo"]
    assert resumo["total_etapas"] == len(rel["etapas"])
    assert resumo["erros"] == []


def test_decisao_executa_juizo_e_honestidade(magna_tmp):
    res = magna_tmp.decidir_e_gerar(quantidade=1, registrar=False,
                                    tentativas_juiz=1)
    # juiz de 9 critérios — antes só na Suprema, agora em toda decisão
    julg = res["julgamento_magna"]
    assert julg.get("veredito") in ("APROVADO", "REPROVADO")
    assert "nota" in julg
    # diagnósticos de honestidade anexados à resposta
    assert "teste_nist" in res
    assert "p_value_random" in res
    assert "julgamento_adversarial" in res
    assert "backtest_lote" in res
    assert "curva_aprendizado" in res
    assert "verificacao_exaustiva" in res
    assert "utilidade_esperada" in res
    # fingerprint pessoal registrou o lote entregue
    assert res["fingerprint"].get("total_hashes", 0) >= res["n_cartelas"]
    # regime detectado e anexado
    assert "regime_atual" in res


def test_relatorio_sozinho_nao_gera_cartelas(magna_tmp):
    rel = magna_tmp.relatorio_pre_cartelas(quantidade=1)
    nomes = [et["nome"] for et in rel["etapas"]]
    assert "geracao_cartelas" not in nomes
    assert "consenso_vetor_final" in nomes
    estado = rel["estado_final"]
    assert len(estado["top15_magna"]) == 15
    assert estado["pesos_fontes"]
    assert "# Relatório pré-cartelas" in rel["markdown"]
    # a consulta não cria cartela nenhuma (contagem do banco não muda)
    conn = magna_tmp.db.get_conn()
    antes = conn.execute("SELECT COUNT(*) FROM cartelas").fetchone()[0]
    conn.close()
    magna_tmp.relatorio_pre_cartelas(quantidade=1)
    conn = magna_tmp.db.get_conn()
    depois = conn.execute("SELECT COUNT(*) FROM cartelas").fetchone()[0]
    conn.close()
    assert antes == depois


def test_bloqueio_15_ligado_ao_gerar_otimas(magna_tmp, monkeypatch):
    magna_tmp.treinar()
    vf = magna_tmp._vetor_combinado()
    chamou = {"vezes": 0}
    original = magna_tmp._substituir_cartelas_ja_sorteadas_15

    def espiada(cartelas, vetor):
        chamou["vezes"] += 1
        return original(cartelas, vetor)

    monkeypatch.setattr(magna_tmp,
                        "_substituir_cartelas_ja_sorteadas_15", espiada)
    res = magna_tmp.gerar_otimas(n_cartelas=2, vetor_override=vf)
    assert res["estrategia"] == "exaustao-diversa"
    assert chamou["vezes"] == 1, "bloqueio-15 não executado na rota de exaustão"
    # e nenhuma cartela entregue é combinação oficial já sorteada
    for c in res["cartelas"]:
        assert magna_tmp._cartela_ja_foi_15(c["dezenas"]) is False


def test_fingerprint_substitui_repetidas(magna_tmp):
    magna_tmp.treinar()
    vf = magna_tmp._vetor_combinado()

    class _FPFalso:
        def __init__(self):
            self.cache = set()

        def ja_foi_gerada(self, dezenas):
            return tuple(dezenas) in self.cache

        def registrar(self, dezenas):
            self.cache.add(tuple(dezenas))

    fp = _FPFalso()
    cartelas = magna_tmp.gerar_otimas(
        n_cartelas=1, vetor_override=vf)["cartelas"]
    dez = cartelas[0]["dezenas"]
    fp.registrar(dez)
    novas, trocadas = magna_tmp._substituir_cartelas_ja_geradas(
        [dez], vf, fp)
    assert trocadas == 1
    assert novas[0] != dez
    assert tuple(novas[0]) in fp.cache
