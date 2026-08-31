"""
============================================================
PROBABILIDADES E VALOR ESPERADO REAIS DA LOTOFÁCIL
============================================================

Tudo aqui é matemática exata (hipergeométrica) sobre as regras
oficiais de 2026: volante de 25 dezenas, cartela de 15,
aposta mínima R$ 3,50.

VERDADES QUE NENHUM SISTEMA MUDA
--------------------------------
* Por cartela: P(13) = 1/691,9 · P(14) = 1/21.792 ·
  P(15) = 1/3.268.760. São exatas e fixas por lei combinatória.
* Cada sorteio é independente: frequência histórica, física das
  bolas, clima e "IA" não alteram essas frações — não existe
  informação na deep web nem em lugar nenhum que mude isto; o
  sorteio é auditado e as bolas são trocadas periodicamente.
* O que É possível otimizar de verdade:
    1.  NÚMERO DE CARTELAS para uma GARANTIA (fechamentos
        verificados — ver core/cobertura.py): a mesma garantia
        condicional do desdobramento oficial por uma fração do
        preço. Isto reduz o custo por garantia, não a fração
        hipergeométrica por cartela.
    2.  CHANCE POR ORÇAMENTO: com m cartelas distintas,
        P(pelo menos um 15) ≈ m/3.268.760. Só apostar mais
        (ou bolão) aumenta a chance — e o EV continua negativo.
    3.  VALOR QUANDO GANHA: evitar dezenas populares reduz a
        divisão do rateio (core/antipopularidade.py).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from config import (
    TOTAL_DEZENAS as N_UNI,
    DEZENAS_POR_JOGO as K_JOGO,
    VALOR_APOSTA,
    PREMIOS_FIXOS,
)

TOTAL_COMB = math.comb(N_UNI, K_JOGO)  # 3.268.760


# ----------------------------------------------------------------
# Probabilidades exatas por cartela (hipergeométrica)
# ----------------------------------------------------------------
def combinacoes_com_k_acertos(k: int) -> int:
    """Cartelas de 15 que acertam exatamente k das 15 sorteadas:
    C(15,k) · C(10, 15−k)."""
    if k < 5 or k > 15:
        return 0
    return math.comb(15, k) * math.comb(10, 15 - k)


def prob_pelo_menos_k(k: int) -> float:
    return sum(combinacoes_com_k_acertos(j)
               for j in range(k, 16)) / TOTAL_COMB


def tabela_cartela() -> List[Dict]:
    linhas = []
    for k in range(11, 16):
        comb = combinacoes_com_k_acertos(k)
        p = comb / TOTAL_COMB
        linhas.append({
            "acertos": k,
            "combinacoes": comb,
            "probabilidade": p,
            "um_em": round(TOTAL_COMB / comb, 1),
            "premio": float(PREMIOS_FIXOS.get(k, 0.0)),
            "tipo": "fixo" if k in PREMIOS_FIXOS else "rateado",
        })
    return linhas


# ----------------------------------------------------------------
# M cartelas distintas: probabilidade de PELO MENOS UM evento
# (independência aproximada — exata para cartelas sem sobreposição
# de efeito; para a Lotofácil a correlação é desprezível em m pequeno)
# ----------------------------------------------------------------
def prob_pelo_menos_um(k_alvo: int, m_cartelas: int) -> float:
    p = combinacoes_com_k_acertos(k_alvo) / TOTAL_COMB
    return 1.0 - (1.0 - p) ** m_cartelas


def escada_orcamento(k_alvo: int = 15,
                     marcadores=(1, 10, 50, 100, 500, 1000, 5000,
                                 10000, 32687, 100000, 326876)) -> List[Dict]:
    """Quantas cartelas (e quanto custa) para cada chance '1 em X'."""
    p1 = combinacoes_com_k_acertos(k_alvo) / TOTAL_COMB
    linhas = []
    for m in marcadores:
        p = prob_pelo_menos_um(k_alvo, m)
        linhas.append({
            "cartelas": m,
            "custo": round(m * VALOR_APOSTA, 2),
            "prob_pelo_menos_um": p,
            "um_em": round(1 / p, 1) if p > 0 else None,
        })
    return linhas


def cartelas_para_chance(k_alvo: int, chance: float) -> int:
    """Menor m tal que P(pelo menos um k_alvo) ≥ chance."""
    p1 = combinacoes_com_k_acertos(k_alvo) / TOTAL_COMB
    if chance <= 0 or chance >= 1:
        raise ValueError("chance deve estar em (0, 1)")
    return math.ceil(math.log(1 - chance) / math.log(1 - p1))


# ----------------------------------------------------------------
# Desdobramento oficial (preço de tabela 2026, fonte Caixa)
# ----------------------------------------------------------------
PRECO_DESDOBRAMENTO = {
    15: 1 * VALOR_APOSTA,
    16: 56.00,
    17: 476.00,
    18: 2_856.00,
    19: 13_566.00,
    20: 54_264.00,
}


def probabilidade_pool(n_pool: int) -> float:
    """P(as 15 sorteadas estarem dentro de um pool fixo de n_pool)."""
    return math.comb(n_pool, 15) / TOTAL_COMB


# ----------------------------------------------------------------
# Valor esperado da cartela (premiação real)
# ----------------------------------------------------------------
def ev_cartela(premio_14: float = 1800.0, premio_15: float = 2_500_000.0) -> Dict:
    """EV exato por cartela usando prêmio fixo (11/12/13) e estimativa
    média dos rateios (14/15). Retorna também a taxa de retorno."""
    tabela = {l["acertos"]: l for l in tabela_cartela()}
    premios = {
        11: PREMIOS_FIXOS[11], 12: PREMIOS_FIXOS[12], 13: PREMIOS_FIXOS[13],
        14: float(premio_14), 15: float(premio_15),
    }
    ev = 0.0
    detalhe = {}
    for k in range(11, 16):
        p = tabela[k]["probabilidade"]
        detalhe[k] = {"prob": p, "premio": premios[k],
                      "contribuicao": round(p * premios[k], 4)}
        ev += p * premios[k]
    return {
        "ev_por_cartela": round(ev, 4),
        "custo_cartela": VALOR_APOSTA,
        "ev_liquido": round(ev - VALOR_APOSTA, 4),
        "retorno_pct": round(100 * ev / VALOR_APOSTA, 1),
        "detalhe": detalhe,
    }


def premio_medio_rateado(media_14: float, media_15: float) -> Dict:
    return {"premio_14_medio": media_14, "premio_15_medio": media_15}
