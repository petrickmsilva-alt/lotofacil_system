"""
============================================================
MOTOR HEAVYWEIGHT v10.0 — EXAUSTÃO TOTAL DO ESPAÇO AMOLSTRAGEM
Sem Atalhos. Sem Heurísticas.
Calcula o Valor Esperado (EV) de TODAS as 3.268.760 combinações
possíveis da Lotofácil em milissegundos via Tensores Vetorizados.
============================================================
"""
import os
import time
import itertools
import numpy as np
try:
    import torch
    TORCH_DISPONIVEL = True
except ImportError:
    TORCH_DISPONIVEL = False

from config import TOTAL_DEZENAS, DEZENAS_POR_JOGO


class MotorExaustaoUniverso:
    """
    Carrega a Matriz de 3.268.760 x 25 na memória RAM/VRAM.
    Aplica álgebra linear tensorial para avaliar 100% da Lotofácil simultaneamente.
    """
    _MATRIZ_UNIVERSO = None  # Cache em RAM (81 MB)

    def __init__(self):
        self.device = 'cuda' if (TORCH_DISPONIVEL and torch.cuda.is_available()) else 'cpu'
        self._garantir_universo_carregado()

    @classmethod
    def _garantir_universo_carregado(cls):
        """Gera e armazena em RAM os 3.268.760 jogos da Lotofácil em formato binário uint8"""
        if cls._MATRIZ_UNIVERSO is None:
            t0 = time.time()
            print("[🚀 HEAVYWEIGHT] Gerando Matriz do Universo Completo (3.268.760 x 25)...")
            
            # Gera todos os índices C(25, 15)
            combos = list(itertools.combinations(range(25), DEZENAS_POR_JOGO))
            n_combos = len(combos)  # Exact: 3.268.760
            
            matriz = np.zeros((n_combos, TOTAL_DEZENAS), dtype=np.uint8)
            for i, c in enumerate(combos):
                matriz[i, list(c)] = 1

            cls._MATRIZ_UNIVERSO = matriz
            print(f"[🚀 HEAVYWEIGHT] Universo carregado em {time.time() - t0:.2f}s! ({matriz.nbytes / (1024**2):.1f} MB em RAM)")

    def avaliar_universo_completo(
        self, 
        vetor_probabilidades_25: np.ndarray, 
        pesos_penalidade_duplicatas: np.ndarray = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Executa a multiplicação tensorial das 3.268.760 combinações contra o vetor de 25 probabilidades.
        Retorna:
        - indices_ordenados: Os índices dos jogos do melhor para o pior.
        - scores_ordenados: O EV exato de cada um dos 3.268.760 jogos.
        """
        t0 = time.time()
        v_prob = vetor_probabilidades_25.astype(np.float32)

        if TORCH_DISPONIVEL and self.device == 'cuda':
            # 🚀 EXECUÇÃO VIA GPU (NVIDIA CUDA) — Ultrarrápido
            tensor_universo = torch.from_numpy(self._MATRIZ_UNIVERSO).float().to(self.device)
            tensor_prob = torch.from_numpy(v_prob).float().to(self.device)

            # Multiplicação Matricial Paralela na GPU (3.268.760 x 25 @ 25 x 1)
            scores = torch.matmul(tensor_universo, tensor_prob)

            if pesos_penalidade_duplicatas is not None:
                tensor_pen = torch.from_numpy(pesos_penalidade_duplicatas).float().to(self.device)
                scores *= tensor_pen

            scores_top, indices_top = torch.sort(scores, descending=True)
            
            indices_res = indices_top.cpu().numpy()
            scores_res = scores_top.cpu().numpy()
        else:
            # ⚡ EXECUÇÃO VIA CPU VETORIZADA (BLAS / C-Speed)
            scores = np.dot(self._MATRIZ_UNIVERSO.astype(np.float32), v_prob)

            if pesos_penalidade_duplicatas is not None:
                scores *= pesos_penalidade_duplicatas

            # Ordenação exaustiva de 3.26M elementos
            indices_res = np.argsort(scores)[::-1]
            scores_res = scores[indices_res]

        print(f"[🚀 HEAVYWEIGHT] 3.268.760 jogos avaliados exaustivamente em {time.time() - t0:.3f}s!")
        return indices_res, scores_res

    def obter_dezenas_por_indice(self, idx: int) -> List[int]:
        """Converte o índice da matriz de volta para dezenas (1 a 25)"""
        linha_binaria = self._MATRIZ_UNIVERSO[idx]
        return [int(i + 1) for i in range(TOTAL_DEZENAS) if linha_binaria[i] == 1]