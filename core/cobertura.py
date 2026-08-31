"""
============================================================
FECHAMENTOS VERIFICADOS — COVERING DESIGNS NO ESPAÇO DUAL
============================================================

O que isto faz (e o que NÃO faz)
--------------------------------
Dado um POOL de `n` dezenas (16 ≤ n ≤ 25), encontra o menor
conjunto de cartelas (15 dezenas cada) que GARANTE pelo menos
`t` acertos SE o sorteio de 15 dezenas cair dentro do pool.

Para n = 25 a garantia é **incondicional** (o pool é o volante
inteiro): nenhuma premissa sobre o sorteio.

A MATEMÁTICA (exata)
--------------------
Seja s = n − 15. Toda cartela dentro do pool tem um complemento
(bloco) de s dezenas; todo sorteio dentro do pool também. Para
cartela c e sorteio d:

    |c ∩ d| = 30 − n + |c̄ ∩ d̄|

logo

    |c ∩ d| ≥ t  ⟺  |c̄ ∩ d̄| ≥ α,   α = t + n − 30.

O problema vira, então: escolher o mínimo de s-subconjuntos
(blocos) do conjunto de n pontos tal que TODO s-subconjunto
(alvo) tenha interseção ≥ α com algum bloco escolhido. Isto é
um **covering code no grafo de Johnson J(n, s)**, raio s − α.

A VERIFICAÇÃO É EXAUSTIVA, NUNCA POR AMOSTRA
--------------------------------------------
Para n ≤ 25 enumeramos TODOS os C(n, s) alvos (no pior caso
C(25,10) = 3.268.760) e checamos cada um contra cada bloco.
`garantia_verificada=True` significa prova matemática total;
não há "99,9%". Resultados bons são gravados em cache e
reverificados a cada carga.

HONESTIDADE
-----------
Isto não muda a chance de acertar (hipergeométrica). O que muda
é o NÚMERO DE CARTELAS NECESSÁRIAS para uma garantia: o
desdobramento oficial (todas as C(n,15) cartelas) entrega a
mesma garantia por um preço muito maior. O fechamento remove
cartelas redundantes e é contabilizado com a probabilidade
exata de captura do pool.
"""
from __future__ import annotations

import json
import math
import os
import time
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from config import (
    TOTAL_DEZENAS,
    DEZENAS_POR_JOGO,
    VALOR_APOSTA,
    MODELS_PATH,
)

_ARQ_CACHE = os.path.join(MODELS_PATH, "fechamentos_verificados.json")

# ----------------------------------------------------------------
# Popcount rápido via tabela de bytes (4 lookups por uint32)
# ----------------------------------------------------------------
_TAB_BYTE = np.array([bin(i).count("1") for i in range(256)], dtype=np.int16)


def popcount(x: np.ndarray) -> np.ndarray:
    """Número de bits 1 por elemento de array uint32 (qualquer shape)."""
    x = np.asarray(x, dtype=np.uint32)
    x = np.broadcast_to(x, x.shape)
    return (_TAB_BYTE[(x & np.uint32(0xFF)).astype(np.int64)]
            + _TAB_BYTE[((x >> np.uint32(8)) & np.uint32(0xFF)).astype(np.int64)]
            + _TAB_BYTE[((x >> np.uint32(16)) & np.uint32(0xFF)).astype(np.int64)]
            + _TAB_BYTE[((x >> np.uint32(24)) & np.uint32(0xFF)).astype(np.int64)])


# ----------------------------------------------------------------
# Máscaras de subconjuntos (cache em memória por (n, k))
# ----------------------------------------------------------------
_cache_mascaras: Dict[Tuple[int, int], np.ndarray] = {}


def mascaras_subconjuntos(n: int, k: int) -> np.ndarray:
    """uint32 mask para cada k-subconjunto de [0..n-1], ordem lexicográfica."""
    chave = (n, k)
    if chave not in _cache_mascaras:
        pw = (np.uint32(1) << np.arange(n, dtype=np.uint32))
        total = math.comb(n, k)
        out = np.empty(total, dtype=np.uint32)
        for i, comb in enumerate(combinations(range(n), k)):
            out[i] = np.bitwise_or.reduce(pw[list(comb)])
        _cache_mascaras[chave] = out
    return _cache_mascaras[chave]


# ----------------------------------------------------------------
# Cota inferior (esfera de Johnson / fração de cobertura)
# ----------------------------------------------------------------
def tamanho_esfera(n: int, s: int, alpha: int) -> int:
    """Quantos s-subconjuntos um bloco fixo cobre (|interseção| ≥ α).

    Um bloco B (s pontos) cobre o alvo T (s pontos) quando T tem
    i ≥ α pontos dentro de B e s−i fora: C(s,i)·C(n−s, s−i).
    """
    # i = nº de pontos do alvo dentro do bloco; s−i fora.
    # C(s−i, n−s) é zero quando s−i > n−s, então somar i de α até s
    # já dá a contagem correta (os termos impossíveis contribuem zero).
    return int(sum(
        math.comb(s, i) * math.comb(n - s, s - i)
        for i in range(alpha, s + 1)
        if 0 <= s - i <= n - s
    ))


def cota_inferior(n: int, t: int) -> int:
    """Menor número de blocos que pode existir (cota por empacotamento
    de esferas). Um resultado com menos cartelas que isto é impossível."""
    s = n - DEZENAS_POR_JOGO
    alpha = t + n - 2 * DEZENAS_POR_JOGO
    if alpha <= 1:
        # família ótima provada: ⌈16/s⌉ blocos (união dos complementos
        # precisa cobrir 16 pontos do pool)
        return math.ceil(16.0 / s)
    esfera = tamanho_esfera(n, s, alpha)
    return math.ceil(math.comb(n, s) / esfera)


# ----------------------------------------------------------------
# Verificação EXATA (todos os alvos)
# ----------------------------------------------------------------
def verificar_blocos(blocos: Sequence[int], n: int, s: int, alpha: int,
                     alvos: Optional[np.ndarray] = None,
                     chunk: int = 2_000_000) -> Tuple[bool, int, int]:
    """Prova exaustiva: todo s-subconjunto de [0..n-1] encontra algum
    bloco com interseção ≥ α.

    Retorna (ok, n_alvos_cobertos, total_alvos)."""
    if not blocos:
        return False, 0, math.comb(n, s)
    if alvos is None:
        alvos = mascaras_subconjuntos(n, s)
    blocos_arr = np.asarray(sorted(set(int(b) for b in blocos)), dtype=np.uint32)
    total = len(alvos)
    cobertos = np.zeros(total, dtype=bool)
    for i in range(0, total, chunk):
        parte = alvos[i:i + chunk]
        for b in blocos_arr:
            cobertos[i:i + chunk] |= popcount(parte & b) >= alpha
    return bool(cobertos.all()), int(cobertos.sum()), total


# ----------------------------------------------------------------
# Construção gulosa no espaço dual (dois estágios) + poda
# ----------------------------------------------------------------
def _candidatos(alvos: np.ndarray, amostra_idx: np.ndarray,
                n: int, s: int, alpha: int, rng: np.random.Generator,
                max_ext: int = 24) -> np.ndarray:
    cand = set()
    for ai in amostra_idx:
        bits = [j for j in range(n) if (int(alvos[ai]) >> j) & 1]
        fora = [j for j in range(n) if not ((int(alvos[ai]) >> j) & 1)]
        for sub in combinations(bits, alpha):
            if len(fora) >= s - alpha:
                ext = list(combinations(fora, s - alpha))
                if len(ext) > max_ext:
                    idx = rng.choice(len(ext), size=max_ext, replace=False)
                    ext = [ext[k] for k in idx]
            else:
                ext = [()]
            for e in ext:
                m = 0
                for b in sub:
                    m |= 1 << b
                for b in e:
                    m |= 1 << b
                cand.add(m)
    return np.array(sorted(cand), dtype=np.uint32)


def _ganho_exato(cand: np.ndarray, livres: np.ndarray, alpha: int,
                 top_k: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Ganho exato de cada candidato sobre os alvos ainda livres.
    Para (alvo, candidato): popcount(and) >= alpha. Vetorizado em blocos."""
    ganhos = np.zeros(len(cand), dtype=np.int64)
    CHUNK_C, CHUNK_L = 2048, 60_000
    for i in range(0, len(cand), CHUNK_C):
        bloco_c = cand[i:i + CHUNK_C]
        g = np.zeros(len(bloco_c), dtype=np.int64)
        for j in range(0, len(livres), CHUNK_L):
            parte_l = livres[j:j + CHUNK_L]
            for k in range(0, len(bloco_c), 256):
                sub_c = bloco_c[k:k + 256]
                ands = parte_l[:, None] & sub_c[None, :]
                g[k:k + len(sub_c)] += (popcount(ands) >= alpha).sum(axis=0)
        ganhos[i:i + len(bloco_c)] = g
    if top_k is not None:
        k = min(top_k, len(cand))
        idx = np.argpartition(ganhos, -k)[-k:]
        return idx, ganhos[idx]
    return np.arange(len(cand)), ganhos


def construir(n: int, t: int,
              tempo_max: float = 60.0,
              sementes: int = 3,
              alvos: Optional[np.ndarray] = None,
              verboso: bool = False) -> Dict:
    """Constrói fechamento verificado para (pool n, garantia t).

    Estratégia: greedy set cover no espaço dual com triagem em dois
    estágios (amostra de alvos livres para pré-rankear candidatos;
    ganho exato só nos finalistas), seguida de poda de blocos
    redundantes. Repete com sementes diferentes e fica com o menor.
    """
    if not (DEZENAS_POR_JOGO + 1 <= n <= TOTAL_DEZENAS):
        raise ValueError(f"pool deve ter 16..25 dezenas (recebi {n})")
    s = n - DEZENAS_POR_JOGO
    alpha = t + n - 2 * DEZENAS_POR_JOGO
    if alpha < 1 or t > DEZENAS_POR_JOGO:
        raise ValueError(f"garantia {t} inválida para pool {n}")

    if alvos is None:
        alvos = mascaras_subconjuntos(n, s)
    total_alvos = len(alvos)

    melhor: Optional[List[int]] = None
    melhor_tempo = 0.0
    t0 = time.time()

    for seed in range(sementes):
        if time.time() - t0 > tempo_max and melhor is not None:
            break
        rng = np.random.default_rng(1000 + 7919 * seed)
        coberto = np.zeros(total_alvos, dtype=bool)
        blocos: List[int] = []
        while not coberto.all():
            if time.time() - t0 > tempo_max and melhor is not None:
                break
            livres_idx = np.flatnonzero(~coberto)
            am = rng.choice(livres_idx,
                            size=min(48, len(livres_idx)), replace=False)
            cand = _candidatos(alvos, am, n, s, alpha, rng)
            # remove candidatos já escolhidos
            cand = cand[~np.isin(cand, np.array(blocos, dtype=np.uint32))] \
                if blocos else cand
            if len(cand) == 0:
                break
            livres = alvos[~coberto]
            # estágio 1: pré-rank por amostra de alvos livres
            amostra_l = livres[rng.choice(len(livres),
                                          size=min(1500, len(livres)),
                                          replace=False)]
            idx_pre, g_pre = _ganho_exato(cand, amostra_l, alpha)
            k_final = min(64, len(cand))
            top = idx_pre[np.argpartition(g_pre, -min(k_final, len(g_pre)))[-k_final:]]
            # estágio 2: ganho exato dos finalistas sobre TODOS os livres
            _, g_exato = _ganho_exato(cand[top], livres, alpha)
            j = int(np.argmax(g_exato))
            if g_exato[j] <= 0:
                break
            escolhido = int(cand[top[j]])
            blocos.append(escolhido)
            coberto |= popcount(alvos & np.uint32(escolhido)) >= alpha

        if not coberto.all():
            continue

        # poda: remove blocos redundantes (reverificação exata após remoção)
        blocos = _podar(blocos, alvos, alpha)

        ok, nc, _ = verificar_blocos(blocos, n, s, alpha, alvos=alvos)
        if ok and (melhor is None or len(blocos) < len(melhor)):
            melhor = blocos
            melhor_tempo = round(time.time() - t0, 1)
        if verboso:
            print(f"  seed {seed}: {len(blocos)} blocos "
                  f"({round(time.time()-t0,1)}s)", flush=True)

    if melhor is None:
        return {
            "n_pool": n, "garantia": t, "s": s, "alpha": alpha,
            "blocos": [], "cartelas": 0,
            "garantia_verificada": False,
            "cota_inferior": cota_inferior(n, t),
            "tempo_s": round(time.time() - t0, 1),
        }

    ok, nc, tot = verificar_blocos(melhor, n, s, alpha, alvos=alvos)
    return {
        "n_pool": n,
        "garantia": t,
        "s": s,
        "alpha": alpha,
        "blocos": sorted(int(b) for b in melhor),
        "cartelas": len(melhor),
        "garantia_verificada": bool(ok),
        "alvos_cobertos": nc,
        "total_alvos": tot,
        "cota_inferior": cota_inferior(n, t),
        "custo": round(len(melhor) * VALOR_APOSTA, 2),
        "tempo_s": melhor_tempo,
    }


def _podar(blocos: List[int], alvos: np.ndarray, alpha: int) -> List[int]:
    """Remove blocos cuja retirada mantém a cobertura total (exato)."""
    blocos = list(blocos)
    mudou = True
    while mudou:
        mudou = False
        # conta cobertura por bloco; só pode sair bloco sem alvo exclusivo
        for b in list(blocos):
            resto = [x for x in blocos if x != b]
            ok, _, _ = verificar_blocos(resto, 0, 0, alpha, alvos=alvos)
            if ok:
                blocos.remove(b)
                mudou = True
    return blocos


# ----------------------------------------------------------------
# Família exata α = 1 (ótimo provado ⌈16/s⌉) — construção direta
# ----------------------------------------------------------------
def familia_exata(n: int) -> Dict:
    """Fechamento ótimo provado para a garantia t = 31 − n (α = 1):
    ⌈16/s⌉ blocos cujos complementos cobrem 16 pontos do pool."""
    s = n - DEZENAS_POR_JOGO
    m = math.ceil(16 / s)
    blocos = []
    usadas = 0
    for i in range(m):
        tam = min(s, 16 - usadas)
        bloco = list(range(usadas, usadas + tam))
        if tam < s:
            bloco += list(range(16, 16 + (s - tam)))
        blocos.append(sorted(set(bloco)))
        usadas += tam
    mascaras = [int(np.bitwise_or.reduce(np.uint32(1) << np.arange(n, dtype=np.uint32)[b]))
                for b in blocos]
    alvos = mascaras_subconjuntos(n, s)
    ok, nc, tot = verificar_blocos(mascaras, n, s, 1, alvos=alvos)
    return {
        "n_pool": n, "garantia": 31 - n, "s": s, "alpha": 1,
        "blocos": sorted(mascaras), "cartelas": m,
        "garantia_verificada": bool(ok),
        "alvos_cobertos": nc, "total_alvos": tot,
        "cota_inferior": math.ceil(16 / s),
        "custo": round(m * VALOR_APOSTA, 2),
        "tempo_s": 0.0, "metodo": "familia-exata-otima",
    }


# ----------------------------------------------------------------
# Conversão bloco (posições do pool) → cartela (dezenas reais)
# ----------------------------------------------------------------
def blocos_para_cartelas(blocos: Sequence[int], pool: Sequence[int]) -> List[List[int]]:
    pool = sorted(int(d) for d in pool)
    n = len(pool)
    cartelas = []
    for b in blocos:
        pos = {j for j in range(n) if (int(b) >> j) & 1}
        cartela = sorted(pool[j] for j in range(n) if j not in pos)
        assert len(cartela) == DEZENAS_POR_JOGO
        cartelas.append(cartela)
    return cartelas


# ----------------------------------------------------------------
# Probabilidade de captura do pool (hipergeométrica, exata)
# ----------------------------------------------------------------
def prob_captura(n_pool: int) -> float:
    return math.comb(n_pool, DEZENAS_POR_JOGO) / math.comb(
        TOTAL_DEZENAS, DEZENAS_POR_JOGO)


# ----------------------------------------------------------------
# Cache dos fechamentos verificados
# ----------------------------------------------------------------
def carregar_cache() -> Dict[str, Dict]:
    if not os.path.exists(_ARQ_CACHE):
        return {}
    with open(_ARQ_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_cache(cache: Dict[str, Dict]) -> None:
    os.makedirs(MODELS_PATH, exist_ok=True)
    with open(_ARQ_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1, sort_keys=True)


def _chave(n: int, t: int) -> str:
    return f"{n}:{t}"


def fechamento_verificado(n: int, t: int,
                          tempo_max: float = 45.0,
                          sementes: int = 3,
                          usar_cache: bool = True,
                          verboso: bool = False) -> Dict:
    """Devolve fechamento verificado para (n, t), usando cache quando
    disponível (e REVERIFICANDO o cache contra todos os alvos)."""
    alpha = t + n - 2 * DEZENAS_POR_JOGO
    if alpha == 1 and t == 31 - n:
        res = familia_exata(n)
        if res.get("garantia_verificada") and usar_cache:
            cache = carregar_cache()
            if _chave(n, t) not in cache:
                cache[_chave(n, t)] = {
                    k: v for k, v in res.items() if k != "metodo"}
                salvar_cache(cache)
        return res
    cache = carregar_cache() if usar_cache else {}
    ch = _chave(n, t)
    if ch in cache and cache[ch].get("garantia_verificada"):
        entrada = cache[ch]
        blocos = [int(b) for b in entrada["blocos"]]
        s = n - DEZENAS_POR_JOGO
        alvos = mascaras_subconjuntos(n, s)
        ok, nc, tot = verificar_blocos(blocos, n, s, alpha, alvos=alvos)
        if ok:
            entrada.update({
                "garantia_verificada": True, "alvos_cobertos": nc,
                "total_alvos": tot, "do_cache": True,
                "cota_inferior": cota_inferior(n, t),
                "custo": round(len(blocos) * VALOR_APOSTA, 2),
            })
            return entrada
    res = construir(n, t, tempo_max=tempo_max, sementes=sementes, verboso=verboso)
    if res.get("garantia_verificada") and usar_cache:
        cache = carregar_cache()
        cache[ch] = {k: v for k, v in res.items() if k != "do_cache"}
        salvar_cache(cache)
    return res


def reverificar_todo_cache() -> List[Dict]:
    """Reabre o cache e prova exaustivamente cada fechamento gravado."""
    cache = carregar_cache()
    laudo = []
    for ch, entrada in sorted(cache.items(), key=lambda kv: tuple(map(int, kv[0].split(":")))):
        n, t = map(int, ch.split(":"))
        s = n - DEZENAS_POR_JOGO
        alpha = t + n - 2 * DEZENAS_POR_JOGO
        blocos = [int(b) for b in entrada["blocos"]]
        ok, nc, tot = verificar_blocos(blocos, n, s, alpha)
        laudo.append({
            "caso": ch, "n_pool": n, "garantia": t,
            "cartelas": len(blocos),
            "cota_inferior": cota_inferior(n, t),
            "verificado": ok, "alvos_cobertos": nc, "total_alvos": tot,
        })
    return laudo
