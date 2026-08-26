"""
============================================================
FORJA ESPACIAL DE LOTES v1.0 — ENGENHARIA ESPACIAL 13/14/15
============================================================
Quatro instrumentos que operam sobre o MESMO universo exato
(C(25,15) = 3.268.760 sorteios) já usado pelo wheeling:

1. REGIOES DE ALTO ACERTO (o "leque" da cartela)
   Uma cartela c atinge ≥ t pontos em pouquíssimos sorteios:
       |R13(c)| = C(15,13)·C(10,2) + C(15,14)·C(10,1) + 1 = 4.876
       |R14(c)| = C(15,14)·C(10,1) + 1                    =   151
   P(melhor do lote ≥ t) = |∪ R_t(c_i)| / 3.268.760.
   Como cada leque é minúsculo, a união EXATA de um lote inteiro
   pode ser calculada e OTIMIZADA diretamente — sem simulação.
   É o equivalente combinatório de trocar "adivinhar o ponto" por
   "projetar a constelação de órbitas que cobre o alvo".

2. FORJA DE LOTES (otimizador exato com pesos de plausibilidade)
   Maximiza Σ_{d ∈ ∪R_t} π(d), onde π(d) ∝ Π_{x∈d} vf_x é o modelo
   de amostragem sucessiva da Magna (odds proporcionais ao vetor
   fundido). O recocido simulado move UMA dezena por vez e mantém
   a união incrementalmente (transições 0↔1 no histograma de
   contagens): avaliar um movimento custa O(|leque|) ≈ 4.9 mil
   operações, não O(3,27 milhões). Modo robusto: média sobre K
   vetores amostrados de uma posteriori Dirichlet em torno de vf —
   o lote resiste à incerteza do ranking em vez de apostar tudo
   num único vetor.

3. FECHAMENTO DUAL (cobertura no espaço dos complementos)
   |c∩d| ≥ t  ⟺  |c̄∩d̄| ≥ α = t+N−30. Projetar o problema no
   espaço dos complementos (s = N−15 dezenas) reduz a cobertura a
   um design de cobertura clássico sobre C(N,s) ≤ 15.504 objetos
   minúsculos — viabiliza garantias de 13 pontos com pools 19 e 20
   (captura 1:843 e 1:211) que o greedy de Johnson não alcança em
   tempo hábil. A cota de esfera reporta o piso teórico do ótimo.

4. GEOMETRIA DO LOTE
   a) Espectro de Johnson: distribuição das interseções par a par
      das cartelas (a "distância entre órbitas" no esquema de
      Johnson J(25,15)) contra a linha de base aleatória.
   b) Mapa informacional: incorporação espectral (MDS clássico)
      das 25 dezenas com DISTÂNCIA DE INFORMAÇÃO (cosseno da
      co-ocorrência) — a geografia estatística do volante. Semeia
      o recocido com constelações espalhadas (Gonzalez) e alimenta
      o mapa da interface.

HONESTIDADE MATEMÁTICA (herdada do wheeling):
   Nenhuma peça prevê o sorteio. A forja maximiza, SOB O MODELO de
   plausibilidade da Magna, a probabilidade de o MELHOR bilhete do
   lote alcançar o alvo — e reporta sempre, ao lado, a probabilidade
   EXATA não-pesada (hipergeométrica pura). O ganho aqui é
   combinatório (como montar o lote), não preditivo.
"""
import math
import time
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import TOTAL_DEZENAS, VALOR_APOSTA
from .wheeling import MotorWheeling, _popcount, dezenas_para_mascara

_N_UNIVERSO = math.comb(TOTAL_DEZENAS, 15)


# ----------------------------------------------------------------
# 1. REGIÕES DE ALTO ACERTO — o leque exato de cada cartela
# ----------------------------------------------------------------
class RegiaoAltoAcerto:
    """Enumera, de forma vetorial, todos os sorteios d com |c∩d| ≥ t."""

    TAM_LEQUE = {13: 4876, 14: 151, 15: 1}

    def __init__(self):
        self._cache: Dict[Tuple[int, int], np.ndarray] = {}

    def regiao(self, mask_cartela: int, t: int = 13) -> np.ndarray:
        """Máscaras uint32 de TODOS os sorteios com ≥t acertos na cartela."""
        chave = (int(mask_cartela), int(t))
        hit = self._cache.get(chave)
        if hit is not None:
            return hit

        dez = [i for i in range(TOTAL_DEZENAS) if (mask_cartela >> i) & 1]
        fora = [i for i in range(TOTAL_DEZENAS) if not (mask_cartela >> i) & 1]
        pw = (np.uint32(1) << np.arange(TOTAL_DEZENAS, dtype=np.uint32))

        partes = []
        for j in range(t, 16):
            a_idx = np.array(list(combinations(dez, j)), dtype=np.int64)
            b_idx = np.array(list(combinations(fora, 15 - j)), dtype=np.int64)
            ma = np.bitwise_or.reduce(pw[a_idx], axis=1)          # C(15, j)
            mb = np.bitwise_or.reduce(pw[b_idx], axis=1)          # C(10, 15−j)
            partes.append((ma[:, None] | mb[None, :]).ravel())

        reg = np.concatenate(partes) if len(partes) > 1 else partes[0]
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[chave] = reg
        return reg

    def uniao_lote(self, cartelas: List[List[int]], t: int = 13):
        """|∪ R_t| e a própria união (máscaras únicas) do lote."""
        pedacos = [self.regiao(dezenas_para_mascara(c), t) for c in cartelas]
        uniao = np.unique(np.concatenate(pedacos)) if pedacos else \
            np.empty(0, dtype=np.uint32)
        return len(uniao), uniao


# ----------------------------------------------------------------
# 2. MAPA INFORMACIONAL — a geografia estatística das 25 dezenas
# ----------------------------------------------------------------
class MapaInformacional:
    """
    Distância entre dezenas = √(1 − similaridade de cosseno da
    co-ocorrência). MDS clássico (autodecomposição da matriz
    duplo-centralizada) projeta em R^k preservando a geometria
    informacional. Dezenas que "andam juntas" ficam próximas;
    a constelação de um lote é a nuvem dos seus 15 pontos.
    """

    def __init__(self, matriz: np.ndarray):
        m = np.asarray(matriz, dtype=np.float64)
        freq = m.sum(axis=0) + 1e-9
        # co-ocorrência normalizada (cosseno): s_ij = c_ij / √(c_ii·c_jj)
        c = m.T @ m
        norm = np.sqrt(np.outer(freq, freq))
        s = np.clip(c / norm, 0.0, 1.0)
        np.fill_diagonal(s, 1.0)
        d2 = np.clip(1.0 - s, 0.0, None)

        # MDS clássico: B = −½ J D² J, com J = I − 11'/n
        j = np.eye(TOTAL_DEZENAS) - 1.0 / TOTAL_DEZENAS
        b = -0.5 * (j @ d2 @ j)
        b = (b + b.T) / 2.0
        vals, vecs = np.linalg.eigh(b)
        ordem = np.argsort(vals)[::-1]
        vals = np.clip(vals[ordem], 0.0, None)
        vecs = vecs[:, ordem]
        k = min(3, TOTAL_DEZENAS)
        coords = vecs[:, :k] * np.sqrt(vals[:k] + 1e-12)
        escala = float(np.abs(coords).max()) or 1.0
        self.coords = coords / escala
        self.vals_prop = vals / (vals.sum() + 1e-12)

    def coordenadas(self) -> np.ndarray:
        """(25, 3) — posição de cada dezena no espaço informacional."""
        return self.coords.copy()

    @staticmethod
    def constelacao(coordenadas: np.ndarray, cartela: List[int]) -> Dict:
        """Medidas espaciais da cartela: dispersão da constelação."""
        pts = coordenadas[[d - 1 for d in cartela]]
        centro = pts.mean(axis=0)
        raio = float(np.linalg.norm(pts - centro, axis=1).mean())
        d_pares = np.linalg.norm(pts[:, None] - pts[None, :], axis=-1)
        triu = np.triu_indices(len(pts), 1)
        return {
            "raio_medio": round(raio, 4),
            "distancia_media_pares": round(float(d_pares[triu].mean()), 4),
        }

    @staticmethod
    def amostra_gonzalez(coordenadas: np.ndarray, k: int,
                         pool: Optional[List[int]] = None) -> List[int]:
        """k dezenas maximamente distantes (amostragem de pontos distantes).

        Semente "espacial" da forja: começa pela dezena mais distante do
        centróide do pool e sempre incorpora o ponto mais longe dos já
        escolhidos — constelação com cobertura máxima do mapa.
        """
        idx_pool = ([d - 1 for d in pool] if pool
                    else list(range(TOTAL_DEZENAS)))
        pts = coordenadas[idx_pool]
        centro = pts.mean(axis=0)
        escolhidos = [int(np.argmax(np.linalg.norm(pts - centro, axis=1)))]
        alvo_k = min(k, len(idx_pool))
        while len(escolhidos) < alvo_k:
            dist = np.linalg.norm(
                pts[:, None, :] - pts[None, escolhidos, :], axis=-1).min(axis=1)
            dist[escolhidos] = -1.0
            escolhidos.append(int(np.argmax(dist)))
        return [idx_pool[i] + 1 for i in escolhidos]


# ----------------------------------------------------------------
# 3. GEOMETRIA DE JOHNSON — espectro de distâncias do lote
# ----------------------------------------------------------------
class GeometriaJohnson:
    """
    No esquema de Johnson J(25,15), cada cartela é um vértice e a
    distância entre duas cartelas é 15 − |interseção|. O espectro de
    interseções par a par é a "formação da esquadrilha": lotes com
    espectro deslocado para baixo cobrem mundos mais independentes;
    lotes concentrados formam um leque estreito em torno do núcleo.
    """

    def __init__(self):
        self._regioes = RegiaoAltoAcerto()

    @staticmethod
    def espectro_intersecoes(cartelas: List[List[int]]) -> Dict[str, int]:
        contagem: Dict[str, int] = {}
        for a, b in combinations(cartelas, 2):
            k = str(len(set(a) & set(b)))
            contagem[k] = contagem.get(k, 0) + 1
        return dict(sorted(contagem.items(), key=lambda kv: int(kv[0])))

    def relatorio(self, cartelas: List[List[int]], n_sim: int = 200,
                  semente: int = 7) -> Dict:
        """Espectro observado vs baseline de lotes aleatórios (mesmo m)."""
        m = len(cartelas)
        esp = self.espectro_intersecoes(cartelas)
        inter_obs = [len(set(a) & set(b))
                     for a, b in combinations(cartelas, 2)]
        media_obs = float(np.mean(inter_obs)) if inter_obs else 15.0

        rng = np.random.default_rng(semente)
        medias = []
        for _ in range(n_sim):
            lote = [rng.choice(25, size=15, replace=False).tolist()
                    for _ in range(m)]
            ints = [len(set(a) & set(b))
                    for a, b in combinations(lote, 2)]
            medias.append(float(np.mean(ints)) if ints else 15.0)
        base_mu = float(np.mean(medias))
        base_sd = float(np.std(medias)) or 1.0
        z = (media_obs - base_mu) / base_sd

        # massa combinatória: quanto o lote inteiro amplifica o leque
        u_total, _ = self._regioes.uniao_lote(cartelas, 13)
        u_1, _ = self._regioes.uniao_lote(cartelas[:1], 13)
        return {
            "espectro_intersecoes": esp,
            "intersecao_media": round(media_obs, 3),
            "intersecao_media_acaso": round(base_mu, 3),
            "z_dispersao": round(z, 3),
            "leque_13_total": int(u_total),
            "leque_13_primeira_cartela": int(u_1),
            "amplificacao_leque": round(u_total / u_1, 3) if u_1 else 0.0,
            "leitura": (
                "lote mais concentrado que o acaso (leque em leque)"
                if z > 1 else
                "lote mais espalhado que o acaso (mundos independentes)"
                if z < -1 else
                "espalhamento típico de lote aleatório"
            ),
        }


# ----------------------------------------------------------------
# 4. FORJA DE LOTES — otimizador exato de P(melhor ≥ alvo)
# ----------------------------------------------------------------
class ForjaDeLotes:
    """Recocido simulado sobre a união exata dos leques.

    Objetivo: massa de plausibilidade M(C) = Σ_{d∈∪R_t(c_i)} π(d),
    com π(d) ∝ Π_{x∈d} vf_x (modelo de amostragem sucessiva). Cada
    movimento troca UMA dezena de UMA cartela; a massa é mantida
    incrementalmente pelas transições 0↔1 do histograma de contagens.
    Modo robusto: K vetores Dirichlet em torno de vf e média das
    massas — a constelação resiste à incerteza do vetor fundido.
    """

    def __init__(self):
        self.universo = MotorWheeling.universo()
        self._regioes = RegiaoAltoAcerto()
        self._univ_ordem: Optional[np.ndarray] = None
        self._univ_ordenado: Optional[np.ndarray] = None

    def _indices_sorteios(self, masks: np.ndarray) -> np.ndarray:
        """Converte máscaras de sorteio em posições no array do universo.

        O universo de 3.268.760 máscaras está em ordem combinatória, não
        numérica; a busca binária no espelho ordenado (construído uma única
        vez) devolve a posição original de cada máscara.
        """
        if self._univ_ordenado is None:
            self._univ_ordem = np.argsort(self.universo.astype(np.uint32))
            self._univ_ordenado = self.universo[self._univ_ordem]
        pos = np.searchsorted(self._univ_ordenado, masks.astype(np.uint32))
        return self._univ_ordem[pos]

    # ---------------- pesos de plausibilidade ----------------
    def pesos_plausibilidade(self, vf: np.ndarray) -> np.ndarray:
        """w[d] = Π_{x∈d} vf_x para os 3.268.760 sorteios (float64)."""
        v = np.clip(np.asarray(vf, dtype=np.float64), 1e-6, None)
        lv = np.log(v)
        univ = self.universo
        logw = np.zeros(len(univ), dtype=np.float64)
        for d in range(TOTAL_DEZENAS):
            bits = ((univ >> np.uint32(d)) & np.uint32(1)).astype(bool)
            logw[bits] += lv[d]
        return np.exp(logw)

    def pesos_robustos(self, vf: np.ndarray, k_amostras: int,
                       concentracao: float = 900.0,
                       semente=None) -> List[np.ndarray]:
        """K vetores de plausibilidade de uma posteriori Dirichlet."""
        if k_amostras <= 1:
            return [self.pesos_plausibilidade(vf)]
        rng = np.random.default_rng(semente)
        alpha = np.clip(np.asarray(vf, dtype=np.float64), 1e-4, None)
        alpha = alpha * (concentracao / alpha.sum())
        return [self.pesos_plausibilidade(rng.dirichlet(alpha))
                for _ in range(k_amostras)]

    # ---------------- API principal ----------------
    def forjar(self, vf: np.ndarray, n_cartelas: int, alvo: int = 13,
               segundos: float = 10.0, n_candidatas: int = 20,
               k_robusto: int = 1, semente=None,
               mapa: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Devolve o lote que maximiza a massa de plausibilidade da união."""
        t0 = time.time()
        n_cartelas = max(1, min(int(n_cartelas), 30))
        alvo = int(alvo) if int(alvo) in (13, 14) else 13
        rng = np.random.default_rng(semente)

        vf = np.asarray(vf, dtype=np.float64)
        ordem = np.argsort(vf)[::-1]
        candidatas = sorted(int(d) + 1 for d in ordem[:n_candidatas])

        ws = self.pesos_robustos(vf, k_robusto, semente=semente)

        # estado incremental: contagem de leques por sorteio + massa viva
        n_univ = len(self.universo)
        cnt = np.zeros(n_univ, dtype=np.int8)
        massas = [[0.0] for _ in ws]  # células mutáveis (fechamento SA)

        def adiciona(mask_c: int) -> None:
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_c, alvo))
            u, c = np.unique(reg, return_counts=True)
            novos = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] += float(wi[u[novos]].sum())
            cnt[u] += c.astype(np.int8)

        def remove(mask_c: int) -> None:
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_c, alvo))
            u, c = np.unique(reg, return_counts=True)
            cnt[u] -= c.astype(np.int8)
            zerados = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] -= float(wi[u[zerados]].sum())

        def massa_troca(mask_velho: int, mask_novo: int) -> float:
            """Aplica a troca; devolve o ganho relativo total de massa."""
            antes = sum(m[0] for m in massas)
            remove(mask_velho)
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_novo, alvo))
            u, _ = np.unique(reg, return_counts=True)
            livres = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] += float(wi[u[livres]].sum())
            cnt[u] += 1  # u é único; a cartela nova acrescenta 1 em cada
            depois = sum(m[0] for m in massas)
            return (depois - antes) / max(abs(antes), 1e-300)

        def desfaz_troca(mask_velho: int, mask_novo: int) -> None:
            reg = self._indices_sorteios(
                self._regioes.regiao(mask_novo, alvo))
            u, _ = np.unique(reg, return_counts=True)
            cnt[u] -= 1
            zerados = cnt[u] == 0
            for wi, ms in zip(ws, massas):
                ms[0] -= float(wi[u[zerados]].sum())
            adiciona(mask_velho)

        # ---- sementes: constelações espaciais + sorteio ponderado ----
        sementes_lote: List[List[int]] = []
        if mapa is not None:
            for _ in range(max(1, n_cartelas // 2)):
                sementes_lote.append(
                    MapaInformacional.amostra_gonzalez(mapa, 15, candidatas))
        p_sem = vf[np.array(candidatas) - 1]
        p_sem = np.clip(p_sem, 1e-9, None) / p_sem.sum()
        while len(sementes_lote) < n_cartelas:
            sementes_lote.append(sorted(rng.choice(
                candidatas, size=15, replace=False, p=p_sem).tolist()))

        lote = [sorted(s) for s in sementes_lote[:n_cartelas]]
        masks = [dezenas_para_mascara(c) for c in lote]
        for mk in masks:
            adiciona(mk)

        melhor_lote = [list(c) for c in lote]
        melhor_massa = sum(m[0] for m in massas)

        # ---- recocido simulado ----
        moves = aceites = 0
        temp0, temp_fim = 1.0, 0.02
        while time.time() - t0 < segundos:
            progresso = (time.time() - t0) / max(segundos, 1e-6)
            temp = temp0 * (temp_fim / temp0) ** progresso

            i = int(rng.integers(0, n_cartelas))
            fora_c = [d for d in candidatas if d not in lote[i]]
            if not fora_c or len(lote[i]) != 15:
                continue
            sai = int(lote[i][int(rng.integers(0, 15))])
            entra = int(fora_c[int(rng.integers(0, len(fora_c)))])

            novo = sorted((set(lote[i]) - {sai}) | {entra})
            novo_mask = dezenas_para_mascara(novo)
            if novo_mask == masks[i]:
                continue

            delta = massa_troca(masks[i], novo_mask)
            moves += 1
            if delta >= 0 or rng.random() < math.exp(
                    min(delta * 400.0 / temp, 0.0)):
                aceites += 1
                masks[i] = novo_mask
                lote[i] = novo
                agora = sum(m[0] for m in massas)
                if agora > melhor_massa:
                    melhor_massa = sum(m[0] for m in massas)
                    melhor_lote = [list(c) for c in lote]
            else:
                desfaz_troca(masks[i], novo_mask)

        melhor_lote = sorted(sorted(c) for c in melhor_lote)
        n_uniao, _ = self._regioes.uniao_lote(melhor_lote, alvo)
        p_exata = n_uniao / n_univ

        return {
            "cartelas": melhor_lote,
            "alvo": alvo,
            "p_exata_melhor_ge_alvo": round(p_exata, 12),
            "um_em_exata": round(1 / p_exata, 1) if p_exata > 0 else None,
            "massa_plausibilidade": float(melhor_massa),
            "moves": moves,
            "aceites": aceites,
            "candidatas": candidatas,
            "k_robusto": k_robusto,
            "tempo": round(time.time() - t0, 2),
        }


# ----------------------------------------------------------------
# 5. FECHAMENTO DUAL — garantias de 13 no espaço dos complementos
# ----------------------------------------------------------------
class FechamentoDual:
    """
    Cobertura no espaço dual. Para pool N e garantia t:
        |c∩d| ≥ t  ⟺  |c̄∩d̄| ≥ α = t+N−30,  c̄, d̄ ∈ C(pool, N−15).
    O greedy roda sobre os C(N,s) ≤ 15.504 complementos com popcount
    vetorial e a garantia é RE-VERIFICADA pelo verificador exato do
    MotorWheeling. A cota de esfera dá o piso teórico de cartelas —
    honestidade sobre o gap entre o greedy e o ótimo.
    """

    def __init__(self):
        self.wheeling = MotorWheeling()

    @staticmethod
    def cota_esfera(n_pool: int, t: int) -> int:
        """Piso: cada cartela cobre Σ_{i=α..s} C(s,i)·C(N−s, s−i) duais."""
        s = n_pool - 15
        alpha = t + n_pool - 30
        if alpha < 1:
            return 1
        bola = sum(math.comb(s, i) * math.comb(n_pool - s, s - i)
                   for i in range(alpha, s + 1))
        return math.ceil(math.comb(n_pool, s) / bola)

    def fechar(self, pool, t: int = 13, max_cartelas: int = 40,
               limite_segundos: float = 20.0) -> Dict:
        t0 = time.time()
        pool = sorted(int(d) for d in pool)
        n = len(pool)
        s = n - 15
        alpha = t + n - 30
        if not (16 <= n <= TOTAL_DEZENAS):
            raise ValueError("pool deve ter 16 a 25 dezenas")
        if alpha < 2:
            raise ValueError("use a família exata do MotorWheeling (α < 2)")
        if not (8 <= t <= 15):
            raise ValueError("garantia deve estar entre 8 e 15")

        pw = (np.uint32(1) << np.arange(TOTAL_DEZENAS, dtype=np.uint32))
        duals = np.array(
            [np.bitwise_or.reduce(pw[np.array(c, dtype=np.int64) - 1])
             for c in combinations(pool, s)], dtype=np.uint32)

        coberto = np.zeros(len(duals), dtype=bool)
        escolhidos: List[int] = []
        while not coberto.all() and len(escolhidos) < max_cartelas:
            if time.time() - t0 > limite_segundos:
                break
            livres = duals[~coberto]
            melhor_ganho, melhor_mask = 0, None
            for i in range(0, len(duals), 512):
                bloco = duals[i:i + 512]
                ands = (livres[:, None] & bloco[None, :]).ravel()
                hits = (_popcount(ands) >= alpha).reshape(
                    len(livres), len(bloco))
                ganho = hits.sum(axis=0)
                j = int(np.argmax(ganho))
                if ganho[j] > melhor_ganho:
                    melhor_ganho = int(ganho[j])
                    melhor_mask = int(bloco[j])
            if melhor_ganho <= 0:
                break
            escolhidos.append(melhor_mask)
            coberto |= _popcount(duals & np.uint32(melhor_mask)) >= alpha

        cartelas = [sorted(set(pool) -
                           {i + 1 for i in range(TOTAL_DEZENAS)
                            if (mk >> i) & 1})
                   for mk in escolhidos]
        ok, exato = (self.wheeling.verificar(cartelas, pool, t)
                     if cartelas else (False, True))
        return {
            "cartelas": cartelas,
            "garantia": t,
            "garantia_verificada": bool(ok),
            "verificacao_exata": bool(exato),
            "cobertura_pct": round(100 * float(coberto.mean()), 3),
            "metodo": "dual-cobertura",
            "cota_inferior_cartelas": self.cota_esfera(n, t),
            "tempo": round(time.time() - t0, 2),
        }


# ----------------------------------------------------------------
# 6. MENU DE CAPTURA — a decisão 13 × 14 com números exatos
# ----------------------------------------------------------------
def menu_captura(orcamento: Optional[float] = None) -> List[Dict]:
    """
    A escolha que o sistema não oferecia (escada completa):
      alvo 15 → pool 16, garantia 15 (16 cartelas, captura 1:204.297)
      alvo 14 → pool 17, garantia 14 (8 cartelas, captura 1:24.032)
      alvo 13 → pool 18, família exata (6 cartelas, captura 1:4.006)
                pool 19, dual (13 cartelas, captura 1:843)
                pool 20, dual (captura 1:211)
    Cada linha traz a probabilidade EXATA de a condição acontecer;
    a decisão financeira fica explícita para o usuário.
    """
    opcoes = [
        {"alvo": 15, "n_pool": 16, "metodo": "exato-alfa1",
         "cartelas_teoricas": 16},
        {"alvo": 14, "n_pool": 17, "metodo": "exato-alfa1",
         "cartelas_teoricas": 8},
        {"alvo": 13, "n_pool": 18, "metodo": "exato-alfa1",
         "cartelas_teoricas": math.ceil(16 / 3)},
        {"alvo": 13, "n_pool": 19, "metodo": "dual-cobertura",
         "cartelas_teoricas": 13},
        {"alvo": 13, "n_pool": 20, "metodo": "dual-cobertura",
         "cartelas_teoricas": None},
    ]
    linhas = []
    for op in opcoes:
        n = op["n_pool"]
        p_cap = MotorWheeling.prob_captura(n)
        custo = ((op["cartelas_teoricas"] or 0) * VALOR_APOSTA) or None
        linhas.append({
            "alvo": op["alvo"],
            "n_pool": n,
            "metodo": op["metodo"],
            "garantia": op["alvo"],
            "cartelas_teoricas": op["cartelas_teoricas"],
            "custo_teorico": round(custo, 2) if custo else None,
            "p_captura": round(p_cap, 8),
            "um_em_captura": round(1 / p_cap, 1),
            "dentro_do_orcamento": (
                True if orcamento is None
                else (custo <= orcamento if custo else None)
            ),
        })
    return linhas
