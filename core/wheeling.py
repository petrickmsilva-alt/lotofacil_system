"""
============================================================
MOTOR DE DESDOBRAMENTO COM COBERTURA GARANTIDA (WHEELING)
============================================================
Desdobramento condicional: dado um POOL de N dezenas escolhidas
pelos motores do Cérebro, gera o menor conjunto de cartelas que
GARANTE t pontos SE as 15 dezenas sorteadas estiverem dentro do pool.

A MATEMÁTICA (exata, verificável)
---------------------------------
Seja s = N − 15 (tamanho do complemento de uma cartela dentro do pool).
Para uma cartela c e um sorteio d (ambos 15-subconjuntos do pool):

    |c ∩ d| = 30 − N + |c̄ ∩ d̄|

onde c̄ e d̄ são os complementos (s-subconjuntos). Logo:

    |c ∩ d| ≥ t  ⟺  |c̄ ∩ d̄| ≥ t + N − 30  (= α)

FAMÍLIA EXATA (α = 1, garantia t = 31 − N):
    Precisamos que todo s-subconjunto d̄ partilhe ≥1 elemento com algum
    c̄ escolhido. Se a união dos c̄ escolhidos cobrir ≥ 16 dezenas,
    nenhum d̄ (de tamanho s = N−15 ≤ 10 quando N ≤ 25) cabe fora da
    união — resta intersecção não vazia. Como cada c̄ tem s elementos:

        C(N, 15, 31−N) = ⌈16 / (N−15)⌉  (cartelas — ÓTIMO PROVADO)

    E o limite inferior: com m cartelas, a união dos complementos tem
    ≤ m·s elementos; para m < 16/s existem ≤ 15 elementos cobertos e
    um d̄ disjunto de todos os c̄ escapa com apenas 30−N pontos.

    Ex.: pool 17 dezenas → 8 cartelas garantem 14 pontos
         (se as 15 sorteadas estiverem entre as 17).

GREEDY EXATO (garantias maiores, α ≥ 2):
    Cobertura de conjunto gulosa sobre o espaço de C(N,15) sorteios
    possíveis dentro do pool, com vizinhanças de Johnson e verificação
    exata ao final (N ≤ 20 → verificação exaustiva).

ANÁLISE EXATA DO LOTE:
    Nenhuma simulação: todos os 3.268.760 sorteios possíveis do
    universo 25/15 são enumerados (via np.bitwise_count) para calcular
    a distribuição EXATA de acertos do lote, prêmio esperado, EV e
    probabilidades incondicionais — incluindo o que acontece quando o
    pool NÃO captura o sorteio.

HONESTIDADE:
    Nada aqui prevê sorteio. O wheeling converte "acertar um pool" em
    "acertos garantidos". A probabilidade de o pool capturar as 15
    dezenas é hipergeométrica: C(N,15)/C(25,15) — e nenhum motor muda
    esse número de forma verificável (ver AUDITORIA.md §3).
"""
import math
import os
import time
from itertools import combinations

import numpy as np

from config import (
    TOTAL_DEZENAS,
    DEZENAS_POR_JOGO,
    VALOR_APOSTA,
    PREMIOS_FIXOS,
    PREMIOS_RATEADOS_MEDIA,
    MODELS_PATH,
)

# ----------------------------------------------------------------
# Popcount (numpy >= 2.0 tem bitwise_count; fallback para versões antigas)
# ----------------------------------------------------------------
if hasattr(np, "bitwise_count"):
    def _popcount(x):
        return np.bitwise_count(x).astype(np.int32)
else:  # pragma: no cover
    _TABELA_BYTE = np.array([bin(i).count("1") for i in range(256)], dtype=np.int32)

    def _popcount(x):
        x = np.asarray(x, dtype=np.uint32)
        return (_TABELA_BYTE[(x & 0xFF).astype(np.int64)]
                + _TABELA_BYTE[((x >> 8) & 0xFF).astype(np.int64)]
                + _TABELA_BYTE[((x >> 16) & 0xFF).astype(np.int64)]
                + _TABELA_BYTE[((x >> 24) & 0xFF).astype(np.int64)])


def dezenas_para_mascara(dezenas):
    m = 0
    for d in dezenas:
        m |= 1 << (int(d) - 1)
    return m


def mascara_para_dezenas(mask):
    return [i + 1 for i in range(TOTAL_DEZENAS) if (mask >> i) & 1]


class MotorWheeling:
    """Desdobramento com garantia condicional + contabilidade exata."""

    # Limite para greedy exato (espaço de sorteios enumerável)
    LIMITE_EXATO = 15504          # C(20,15)
    LIMITE_VERIFICACAO = 15504    # acima disso, verificação por amostra
    CHUNK = 400_000               # chunk da análise do universo

    # ------------------------------------------------------------
    # Universo 25/15 (3.268.760 máscaras) com cache em disco
    # ------------------------------------------------------------
    _ARQ_UNIVERSO = os.path.join(MODELS_PATH, "universo_25_15.npy")

    @classmethod
    def universo(cls):
        if not hasattr(cls, "_universo"):
            if os.path.exists(cls._ARQ_UNIVERSO):
                cls._universo = np.load(cls._ARQ_UNIVERSO)
            else:
                masks = np.fromiter(
                    (dezenas_para_mascara(c)
                     for c in combinations(range(1, TOTAL_DEZENAS + 1),
                                           DEZENAS_POR_JOGO)),
                    dtype=np.uint32,
                    count=math.comb(TOTAL_DEZENAS, DEZENAS_POR_JOGO),
                )
                cls._universo = masks
                try:
                    np.save(cls._ARQ_UNIVERSO, masks)
                except OSError:
                    pass
        return cls._universo

    # ------------------------------------------------------------
    # Probabilidades do pool
    # ------------------------------------------------------------
    @staticmethod
    def prob_captura(n_pool):
        """P(um pool fixo de n_pool conter as 15 sorteadas). Exata."""
        return math.comb(n_pool, 15) / math.comb(TOTAL_DEZENAS, 15)

    @staticmethod
    def premio_por_acertos(k):
        if k in PREMIOS_FIXOS:
            return float(PREMIOS_FIXOS[k])
        if k in PREMIOS_RATEADOS_MEDIA:
            return float(PREMIOS_RATEADOS_MEDIA[k])
        return 0.0

    # ------------------------------------------------------------
    # Menu da família exata: garantia t = 31 − N com ⌈16/(N−15)⌉ cartelas
    # ------------------------------------------------------------
    @classmethod
    def menu_exato(cls):
        linhas = []
        for n in range(16, TOTAL_DEZENAS + 1):
            t = 31 - n
            if t < 8:
                break
            qtd = math.ceil(16 / (n - 15))
            p = cls.prob_captura(n)
            linhas.append({
                "n_pool": n,
                "garantia": t,
                "cartelas": qtd,
                "custo": round(qtd * VALOR_APOSTA, 2),
                "p_captura": p,
                "um_em": round(1.0 / p, 1) if p > 0 else float("inf"),
            })
        return linhas

    # ------------------------------------------------------------
    # Construção exata da família α=1 (ótima provada)
    # ------------------------------------------------------------
    def fechamento_exato(self, pool):
        """⌈16/(N−15)⌉ cartelas garantindo 31−N pontos se o sorteio
        cair dentro do pool. Construção direta, sem busca."""
        pool = sorted(int(d) for d in pool)
        n = len(pool)
        if n < 16 or n > TOTAL_DEZENAS:
            raise ValueError("Pool deve ter entre 16 e 25 dezenas")

        s = n - 15
        m = math.ceil(16 / s)

        # Particiona as 16 primeiras dezenas em m grupos de tamanho s;
        # o último grupo pode ser menor → completa com dezenas do resto
        # do pool para fechar tamanho exatamente s.
        grupos = []
        usadas = 0
        for i in range(m):
            tam = min(s, 16 - usadas)
            if tam < s:
                # completa com dezenas fora das 16 primeiras
                extra = pool[16:16 + (s - tam)]
                grupo = pool[usadas:usadas + tam] + list(extra)
            else:
                grupo = pool[usadas:usadas + tam]
            grupos.append(sorted(set(grupo)))
            usadas += tam

        # cartela_i = pool ∖ grupo_i  →  complemento c̄_i = grupo_i
        cartelas = []
        pool_set = set(pool)
        for g in grupos:
            cartela = sorted(pool_set - set(g))
            assert len(cartela) == 15, "cartela deve ter 15 dezenas"
            cartelas.append(cartela)

        garantia = 31 - n
        ok, exato = self.verificar(cartelas, pool, garantia)
        return {
            "cartelas": cartelas,
            "garantia": garantia,
            "garantia_verificada": bool(ok),
            "verificacao_exata": bool(exato),
            "metodo": "exato-alfa1",
            "cartelas_teoricas": m,
        }

    # ------------------------------------------------------------
    # Verificação exata da garantia
    # ------------------------------------------------------------
    def verificar(self, cartelas, pool, garantia):
        """True sse TODO sorteio possível dentro do pool atinge
        `garantia` em alguma cartela. Exaustivo p/ N ≤ 20;
        amostral (30k, semente fixa) acima disso."""
        pool = sorted(int(d) for d in pool)
        n = len(pool)
        masks_c = np.array([dezenas_para_mascara(c) for c in cartelas],
                           dtype=np.uint32)
        if math.comb(n, 15) <= self.LIMITE_VERIFICACAO:
            masks_d = np.array(
                [dezenas_para_mascara(d) for d in combinations(pool, 15)],
                dtype=np.uint32)
            exato = True
        else:
            rng = np.random.default_rng(42)
            universe = self.universo()
            masks_d = rng.choice(universe, size=30_000, replace=False)
            masks_d = masks_d[_popcount(masks_d & dezenas_para_mascara(pool)) == 15]
            exato = False

        melhor = np.zeros(len(masks_d), dtype=np.int32)
        for mc in masks_c:
            hits = _popcount(masks_d & mc)
            np.maximum(melhor, hits, out=melhor)
        return bool((melhor >= garantia).all()), exato

    # ------------------------------------------------------------
    # Greedy (α ≥ 2): garantias maiores que a família exata
    # ------------------------------------------------------------
    def fechamento_guloso(self, pool, garantia, max_cartelas=40,
                          limite_segundos=25, vf=None):
        pool = sorted(int(d) for d in pool)
        n = len(pool)
        t = int(garantia)
        alpha = t + n - 30
        if alpha < 2:
            raise ValueError(
                "Para garantia {} use fechamento_exato (N={})".format(t, n))

        combs = list(combinations(pool, 15))
        total = len(combs)
        masks_d = np.array([dezenas_para_mascara(d) for d in combs],
                           dtype=np.uint32)
        coberto = np.zeros(total, dtype=bool)

        # Vizinhança de Johnson de um sorteio d: cartelas a ≤ (15−t+1)
        # trocas de d. Candidatos úteis vivem na vizinhança dos não cobertos.
        trocas = 15 - t + 1  # nº máx. de elementos de d substituídos

        def vizinhas(d_idx):
            d = set(combs[d_idx])
            fora = [x for x in pool if x not in d]
            cand = {tuple(sorted(d))}
            fronteira = {tuple(sorted(d))}
            for _ in range(trocas):
                nova = set()
                for base in fronteira:
                    b = set(base)
                    for sai in b:
                        for entra in fora:
                            c = tuple(sorted((b - {sai}) | {entra}))
                            if c not in cand:
                                nova.add(c)
                cand |= nova
                fronteira = nova
            return cand

        t0 = time.time()
        escolhidas = []
        rng = np.random.default_rng(7)

        while not coberto.all() and len(escolhidas) < max_cartelas:
            if time.time() - t0 > limite_segundos:
                break
            idx_livres = np.flatnonzero(~coberto)
            # candidatos: vizinhança de uma amostra de sorteios não cobertos
            amostra = rng.choice(idx_livres,
                                 size=min(len(idx_livres), 60),
                                 replace=False)
            cands = set()
            for i in amostra:
                cands |= vizinhas(int(i))
                if len(cands) > 60_000:
                    break
            if not cands:
                break
            cand_list = sorted(cands)
            masks_c = np.array([dezenas_para_mascara(c) for c in cand_list],
                               dtype=np.uint32)

            livres = masks_d[~coberto]
            melhor_gain, melhor_mask, melhor_c = -1, None, None
            for i in range(0, len(masks_c), 2048):
                bloco = masks_c[i:i + 2048]
                hits = _popcount(livres[:, None] & bloco[None, :]) >= t
                ganho = hits.sum(axis=0)
                j = int(np.argmax(ganho))
                if ganho[j] > melhor_gain:
                    melhor_gain = int(ganho[j])
                    melhor_mask = int(bloco[j])
                    melhor_c = cand_list[i + j]

            if melhor_gain <= 0:
                break

            escolhidas.append(list(melhor_c))
            hits_todas = _popcount(masks_d & np.uint32(melhor_mask)) >= t
            coberto |= hits_todas

        pct = float(coberto.mean())
        ok, exato = self.verificar(escolhidas, pool, t) if escolhidas else (False, True)
        return {
            "cartelas": escolhidas,
            "garantia": t,
            "garantia_verificada": ok and pct >= 1.0,
            "cobertura_pct": round(pct * 100, 3),
            "verificacao_exata": exato,
            "metodo": "guloso-johnson",
        }

    # ------------------------------------------------------------
    # Orquestrador
    # ------------------------------------------------------------
    def gerar(self, pool, garantia=None, max_cartelas=40, orcamento=None,
              limite_segundos=25, vf=None):
        pool = sorted(int(d) for d in set(int(d) for d in pool))
        n = len(pool)
        if not (16 <= n <= TOTAL_DEZENAS):
            raise ValueError("Pool deve ter 16 a 25 dezenas (recebi {})".format(n))

        t = int(garantia) if garantia else (31 - n)
        if t < 8 or t > 15:
            raise ValueError("Garantia deve estar entre 8 e 15")

        # 1) Família exata se a garantia pedida for a ótima fechada 31−N
        if t == 31 - n:
            res = self.fechamento_exato(pool)
        else:
            res = self.fechamento_guloso(
                pool, t, max_cartelas=max_cartelas,
                limite_segundos=limite_segundos, vf=vf)

        cartelas = res["cartelas"]
        if orcamento is not None:
            cabem = int(math.floor(float(orcamento) / VALOR_APOSTA))
            if len(cartelas) > cabem:
                cartelas = cartelas[:cabem]
                res["truncado_orcamento"] = True
                res["garantia_verificada"] = False

        # 2) Contabilidade exata
        res["analise"] = self.analisar_lote(cartelas, pool, vf=vf)
        res["pool"] = pool
        res["p_captura"] = self.prob_captura(n)
        res["um_em_captura"] = round(1.0 / self.prob_captura(n), 1)
        res["custo"] = round(len(cartelas) * VALOR_APOSTA, 2)

        # 3) Formato compatível com _salvar_cartelas_banco
        cartelas_fmt = []
        for c in cartelas:
            sc = float(sum(vf[d - 1] for d in c)) if vf is not None else 0.0
            cartelas_fmt.append({
                "dezenas": [int(d) for d in c],
                "bitmask": dezenas_para_mascara(c),
                "score_total": round(sc, 6),
                "scores": {"ev_prob": round(sc, 4)},
            })
        res["cartelas"] = cartelas_fmt
        res["n_cartelas"] = len(cartelas_fmt)
        return res

    # ------------------------------------------------------------
    # Análise EXATA do lote sobre os 3.268.760 sorteios possíveis
    # ------------------------------------------------------------
    def analisar_lote(self, cartelas, pool, vf=None):
        universo = self.universo()
        total = len(universo)  # 3.268.760
        masks_c = np.array([dezenas_para_mascara(c) for c in cartelas],
                           dtype=np.uint32)
        pool_mask = (np.uint32(dezenas_para_mascara(pool))
                     if pool is not None else None)

        premios = np.array([self.premio_por_acertos(k) for k in range(16)],
                           dtype=np.float64)

        # distribuição do MELHOR acerto do lote + prêmio esperado exato
        dist_melhor = np.zeros(16, dtype=np.int64)
        premio_total = 0.0
        # dentro do pool: captura → melhor acerto condicional
        melhor_dentro = np.zeros(16, dtype=np.int64)
        n_dentro = 0

        for i in range(0, total, self.CHUNK):
            chunk = universo[i:i + self.CHUNK]
            melhor = np.zeros(len(chunk), dtype=np.int32)
            soma_premio_chunk = np.zeros(len(chunk), dtype=np.float64)
            for mc in masks_c:
                hits = _popcount(chunk & mc)
                np.maximum(melhor, hits, out=melhor)
                soma_premio_chunk += premios[hits]
            dist_melhor += np.bincount(melhor, minlength=16)
            premio_total += float(soma_premio_chunk.sum())
            if pool_mask is not None:
                dentro = _popcount(chunk & pool_mask) == 15
                n_dentro += int(dentro.sum())
                if dentro.any():
                    melhor_dentro += np.bincount(melhor[dentro], minlength=16)

        custo = len(masks_c) * VALOR_APOSTA
        p_captura = n_dentro / total

        # probabilidades incondicionais do lote
        probs = dist_melhor / total
        resultado = {
            "universo": total,
            "n_cartelas": len(masks_c),
            "custo": round(custo, 2),
            "premio_esperado": round(premio_total / total, 4),
            "ev_lote": round(premio_total / total - custo, 4),
            "retorno_pct": round(100 * (premio_total / total) / custo, 2)
                           if custo > 0 else 0.0,
            "p_melhor_14_mais": float(probs[14:].sum()),
            "p_melhor_15": float(probs[15]),
            "p_captura_exata": p_captura,
            "um_em_captura": round(1 / p_captura, 1) if p_captura > 0 else None,
        }
        if n_dentro > 0:
            cond = melhor_dentro / n_dentro
            resultado.update({
                "cond_min_acertos": int(np.flatnonzero(melhor_dentro)[0]),
                "cond_p_14_mais": float(cond[14:].sum()),
                "cond_p_15": float(cond[15]),
                "cond_distribuicao": {
                    str(k): int(melhor_dentro[k]) for k in range(16)
                    if melhor_dentro[k] > 0
                },
            })
        # distribuição incondicional (para a UI)
        resultado["dist_melhor_acertos"] = {
            str(k): int(dist_melhor[k]) for k in range(16) if dist_melhor[k] > 0
        }
        return resultado
