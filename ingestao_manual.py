"""
Ingestão manual de resultados oficiais (API da Caixa) quando o
ambiente está sem rede direta — os JSON foram obtidos de
servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/<concurso>
e passam pela MESMA normalização e validação da sincronização normal.

Uso:
    python ingestao_manual.py                # insere os concursos abaixo
    python ingestao_manual.py --verificar    # só mostra o status da base
"""
import argparse
import sys

from core.caixa_client import CaixaClient
from core.data_loader import DataLoader

# ----------------------------------------------------------------
# JSON brutos oficiais (forma idêntica à da API da Caixa), capturados
# em 31/08/2026.
# ----------------------------------------------------------------
CONCURSOS = [
    {
        "numero": 3774,
        "dataApuracao": "28/08/2026",
        "listaDezenas": ["01", "03", "04", "05", "06", "07", "09", "12",
                         "14", "15", "16", "18", "19", "23", "24"],
        "dezenasSorteadasOrdemSorteio": ["04", "14", "12", "09", "06", "01",
                                         "05", "15", "16", "07", "03", "19",
                                         "24", "23", "18"],
        "valorArrecadado": 19968543.0,
        "listaRateioPremio": [
            {"faixa": 1, "descricaoFaixa": "15 acertos",
             "numeroDeGanhadores": 0, "valorPremio": 0.0},
            {"faixa": 2, "descricaoFaixa": "14 acertos",
             "numeroDeGanhadores": 281, "valorPremio": 1784.10},
            {"faixa": 3, "descricaoFaixa": "13 acertos",
             "numeroDeGanhadores": 8219, "valorPremio": 35.0},
            {"faixa": 4, "descricaoFaixa": "12 acertos",
             "numeroDeGanhadores": 91426, "valorPremio": 14.0},
            {"faixa": 5, "descricaoFaixa": "11 acertos",
             "numeroDeGanhadores": 474312, "valorPremio": 7.0},
        ],
    },
    {
        "numero": 3775,
        "dataApuracao": "30/08/2026",
        "listaDezenas": ["01", "04", "05", "06", "08", "10", "11", "12",
                         "13", "15", "17", "18", "19", "23", "25"],
        "dezenasSorteadasOrdemSorteio": ["17", "15", "04", "13", "05", "18",
                                         "06", "12", "23", "19", "25", "11",
                                         "10", "01", "08"],
        "valorArrecadado": 31360451.5,
        "listaRateioPremio": [
            {"faixa": 1, "descricaoFaixa": "15 acertos",
             "numeroDeGanhadores": 3, "valorPremio": 1268987.02},
            {"faixa": 2, "descricaoFaixa": "14 acertos",
             "numeroDeGanhadores": 412, "valorPremio": 1550.97},
            {"faixa": 3, "descricaoFaixa": "13 acertos",
             "numeroDeGanhadores": 14511, "valorPremio": 35.0},
            {"faixa": 4, "descricaoFaixa": "12 acertos",
             "numeroDeGanhadores": 166726, "valorPremio": 14.0},
            {"faixa": 5, "descricaoFaixa": "11 acertos",
             "numeroDeGanhadores": 853615, "valorPremio": 7.0},
        ],
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verificar", action="store_true")
    args = ap.parse_args()

    loader = DataLoader()

    if args.verificar:
        total = loader.db.get_total_concursos()
        ultimo = loader.db.get_ultimo_concurso()
        print(f"Base: {total} concursos; último = {ultimo}")
        return 0

    ok_total = 0
    for bruto in CONCURSOS:
        normalizado = CaixaClient.normalizar(bruto, "caixa_oficial_manual")
        gravou = loader.processar_e_salvar(normalizado)
        print(f"Concurso {normalizado['numero']} "
              f"({normalizado['dataApuracao']}): "
              f"{'GRAVADO' if gravou else 'rejeitado/já existente'}")
        ok_total += int(gravou)

    total = loader.db.get_total_concursos()
    ultimo = loader.db.get_ultimo_concurso()
    print(f"\nBase agora: {total} concursos; último = {ultimo}")
    return 0 if ok_total >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
