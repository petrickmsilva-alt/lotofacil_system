"""
============================================================
ALGORITMO GENÉTICO DE ILHAS
Simulação darwinista com populações isoladas que evoluem
independentemente e trocam os melhores indivíduos.
============================================================
"""
import numpy as np
from itertools import combinations
from config import TOTAL_DEZENAS, DEZENAS_POR_JOGO


class AlgoritmoGeneticoIlhas:

    def __init__(
        self,
        n_ilhas=6,
        tamanho_ilha=80,
        n_geracoes=150,
        taxa_mutacao=0.05,
        taxa_crossover=0.75,
        intervalo_migracao=20,
        n_migrantes=5,
    ):
        self.n_ilhas           = n_ilhas
        self.tam_ilha          = tamanho_ilha
        self.n_geracoes        = n_geracoes
        self.taxa_mutacao      = taxa_mutacao
        self.taxa_crossover    = taxa_crossover
        self.intervalo_migr    = intervalo_migracao
        self.n_migrantes       = n_migrantes
        self.melhor_solucao    = None
        self.melhor_fitness    = -np.inf
        self.historico_fitness = []
        self.funcao_fitness    = None

    # =========================================================
    # INDIVÍDUO
    # =========================================================

    def _criar_individuo(self, rng):
        """Cria um jogo aleatório de 15 dezenas"""
        return sorted(rng.choice(TOTAL_DEZENAS, size=DEZENAS_POR_JOGO,
                                  replace=False) + 1)

    def _criar_populacao(self, tamanho, rng):
        """Cria população inicial de jogos"""
        return [self._criar_individuo(rng) for _ in range(tamanho)]

    # =========================================================
    # FITNESS
    # =========================================================

    def _avaliar(self, individuo):
        """Avalia fitness de um indivíduo usando a função externa"""
        if self.funcao_fitness:
            try:
                return float(self.funcao_fitness(individuo))
            except Exception:
                return 0.0
        return 0.5

    def _avaliar_populacao(self, populacao):
        """Avalia toda a população"""
        return np.array([self._avaliar(ind) for ind in populacao])

    # =========================================================
    # OPERADORES GENÉTICOS
    # =========================================================

    def _selecao_torneio(self, pop, fitness, k=3, rng=None):
        """Seleção por torneio"""
        if rng is None:
            rng = np.random.default_rng()

        idx       = rng.choice(len(pop), size=k, replace=False)
        melhor    = idx[np.argmax(fitness[idx])]
        return list(pop[melhor])

    def _crossover_uniforme(self, pai1, pai2, rng):
        """
        Crossover uniforme para jogos.
        União dos pais e seleção de 15 por fitness.
        """
        uniao = list(set(pai1) | set(pai2))

        if len(uniao) < DEZENAS_POR_JOGO:
            # Completar com dezenas aleatórias
            faltam = DEZENAS_POR_JOGO - len(uniao)
            extras = [d for d in range(1, 26) if d not in uniao]
            uniao += list(rng.choice(extras, size=min(faltam, len(extras)),
                                     replace=False))

        # Selecionar 15 por prioridade (maioria dos pais)
        contagem = {}
        for d in pai1 + pai2:
            contagem[d] = contagem.get(d, 0) + 1

        # Ordenar por frequência (dezenas em ambos os pais primeiro)
        uniao_ord = sorted(uniao, key=lambda d: -contagem.get(d, 0))
        filho     = sorted(uniao_ord[:DEZENAS_POR_JOGO])

        return filho

    def _mutacao(self, individuo, rng, taxa=None):
        """
        Mutação: substitui aleatoriamente algumas dezenas.
        """
        if taxa is None:
            taxa = self.taxa_mutacao

        ind = list(individuo)
        for i in range(len(ind)):
            if rng.random() < taxa:
                disponiveis = [d for d in range(1, 26) if d not in ind]
                if disponiveis:
                    ind[i] = int(rng.choice(disponiveis))

        return sorted(list(set(ind))[:DEZENAS_POR_JOGO] +
                       list(rng.choice(
                           [d for d in range(1, 26) if d not in ind[:DEZENAS_POR_JOGO]],
                           size=max(0, DEZENAS_POR_JOGO - len(set(ind))),
                           replace=False
                       )))

    # =========================================================
    # MIGRAÇÃO ENTRE ILHAS
    # =========================================================

    def _migrar(self, ilhas, fitness_ilhas):
        """
        Migração circular: cada ilha envia seus melhores
        para a próxima ilha.
        """
        n = len(ilhas)
        migrantes_por_ilha = []

        for i in range(n):
            # Selecionar melhores
            idx_ord = np.argsort(fitness_ilhas[i])[::-1]
            melhores = [ilhas[i][j] for j in idx_ord[:self.n_migrantes]]
            migrantes_por_ilha.append(melhores)

        # Enviar para próxima ilha (circular)
        for i in range(n):
            prox = (i + 1) % n
            # Substituir os piores da próxima ilha
            idx_piores = np.argsort(fitness_ilhas[prox])
            for k, migrante in enumerate(migrantes_por_ilha[i]):
                if k < len(idx_piores):
                    ilhas[prox][idx_piores[k]] = migrante

        return ilhas

    # =========================================================
    # EVOLUÇÃO PRINCIPAL
    # =========================================================

def evoluir(self, funcao_fitness, callback=None):
        """
        AG de Ilhas com timeout de segurança.
        Máximo 15 segundos.
        """
        import time
        t_inicio = time.time()
        TIMEOUT  = 15  # segundos

        self.funcao_fitness = funcao_fitness

        # Inicializar ilhas
        ilhas = []
        rngs  = []
        for i in range(self.n_ilhas):
            rng = np.random.default_rng(seed=i * 100 + 7)
            rngs.append(rng)
            pop = self._criar_populacao(self.tam_ilha, rng)
            ilhas.append(pop)

        # Avaliar populações iniciais
        fitness_ilhas = []
        for ilha in ilhas:
            fit = self._avaliar_populacao_rapido(ilha)
            fitness_ilhas.append(fit)

        self.melhor_fitness = -np.inf
        self.melhor_solucao = None

        geracao = 0
        while geracao < self.n_geracoes:
            # Verificar timeout
            if time.time() - t_inicio > TIMEOUT:
                print("[AG] Timeout atingido na geração {}".format(geracao))
                break

            for ilha_idx in range(self.n_ilhas):
                pop     = ilhas[ilha_idx]
                fitness = fitness_ilhas[ilha_idx]
                rng     = rngs[ilha_idx]

                nova_pop = []

                # Elitismo: top 3
                idx_elite = np.argsort(fitness)[::-1][:3]
                for ie in idx_elite:
                    nova_pop.append(list(pop[ie]))

                # Gerar filhos
                tentativas = 0
                while len(nova_pop) < self.tam_ilha and tentativas < 100:
                    tentativas += 1
                    try:
                        i1 = int(rng.integers(0, len(pop)))
                        i2 = int(rng.integers(0, len(pop)))
                        pai1 = list(pop[i1])
                        pai2 = list(pop[i2])

                        if rng.random() < self.taxa_crossover:
                            filho = self._crossover_uniforme(pai1, pai2, rng)
                        else:
                            filho = pai1[:]

                        filho = self._mutacao(filho, rng)

                        if len(filho) == 15:
                            nova_pop.append(filho)
                    except Exception:
                        continue

                ilhas[ilha_idx] = nova_pop[:self.tam_ilha]

                # Avaliar
                fitness_ilhas[ilha_idx] = \
                    self._avaliar_populacao_rapido(ilhas[ilha_idx])

                # Atualizar melhor
                idx_m = int(np.argmax(fitness_ilhas[ilha_idx]))
                f_m   = float(fitness_ilhas[ilha_idx][idx_m])
                if f_m > self.melhor_fitness:
                    self.melhor_fitness = f_m
                    self.melhor_solucao = list(ilhas[ilha_idx][idx_m])

            # Migração a cada 10 gerações
            if (geracao + 1) % 10 == 0:
                try:
                    ilhas = self._migrar(ilhas, fitness_ilhas)
                except Exception:
                    pass

            geracao += 1

        if self.melhor_solucao is None:
            # Retornar melhor de todas as ilhas
            for ilha, fitness in zip(ilhas, fitness_ilhas):
                if len(fitness) > 0:
                    idx = int(np.argmax(fitness))
                    if len(ilha) > idx:
                        self.melhor_solucao = list(ilha[idx])
                        self.melhor_fitness = float(fitness[idx])
                        break

        tempo = time.time() - t_inicio
        print("[AG] Concluido: {} geracoes em {:.1f}s".format(
            geracao, tempo
        ))

        return self.melhor_solucao, self.melhor_fitness


def _avaliar_populacao_rapido(self, populacao):
        """Avalia população sem travar"""
        fitness = np.zeros(len(populacao))
        for i in range(len(populacao)):
            try:
                fitness[i] = self._avaliar(populacao[i])
            except Exception:
                fitness[i] = 0.0
        return fitness


def _mutacao(self, individuo, rng, taxa=None):
        """Mutação simples e segura"""
        if taxa is None:
            taxa = self.taxa_mutacao

        ind = list(individuo)

        for i in range(len(ind)):
            if rng.random() < taxa:
                disponiveis = [d for d in range(1, 26) if d not in ind]
                if disponiveis:
                    novo = int(rng.choice(disponiveis))
                    ind[i] = novo

        # Garantir 15 dezenas únicas
        ind_set = list(set(ind))

        if len(ind_set) < 15:
            faltam      = 15 - len(ind_set)
            disponiveis = [d for d in range(1, 26) if d not in ind_set]
            np.random.shuffle(disponiveis)
            ind_set += disponiveis[:faltam]

        return sorted(ind_set[:15])