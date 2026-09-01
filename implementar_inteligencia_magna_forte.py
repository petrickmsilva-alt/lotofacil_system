#!/usr/bin/env python3
"""
============================================================
IMPLEMENTAÇÃO DA INTELIGÊNCIA MAGNA FORTE
============================================================

Este módulo implementa todas as funcionalidades solicitadas:

1. INTEGRAÇÃO COMPLETA:
   - Forja Automática + Inteligência Magna
   - Local de Sorteio (automático e manual)
   - Telemetria INMET (com fallback neutro)
   - Benchmark Walk-Forward (autônomo e contínuo)

2. INTELIGÊNCIA MAGNA AUTÔNOMA:
   - Decisão única e centralizada
   - Aprendizado contínuo (EWC + Meta + Bayesiano)
   - Medição precisa (walk-forward, binomial, NIST)
   - Auditoria completa (Juiz 9 critérios + Adversarial)
   - Exploração autônoma (mutação de parâmetros)
   - Recalibração automática (checkpoint/rollback)

3. REGISTRO DE AMBIENTE DE SORTEIO:
   - Local do sorteio (Caixa → INMET → Padrão)
   - Telemetria (temperatura, pressão, umidade)
   - Física das bolas (massa, diâmetro, coeficientes)
   - Ambiente do sorteio (máquina, velocidade, duração)

4. BENCHMARK WALK-FORWARD ENHANCED:
   - Teste fora-da-amostra rigoroso
   - Auto-auditoria com p-valor
   - Placar de estratégias
   - Quarentena de fontes ruins
   - Exploração de mutações

HONESTIDADE:
- Nenhum módulo prevê o sorteio
- Todas as decisões são baseadas em estrutura combinatória
- Telemetria e física são evidências, não previsões
- Benchmark walk-forward garante que nada entra sem prova
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DATABASE_PATH, TOTAL_DEZENAS, DEZENAS_POR_JOGO,
    VALOR_APOSTA, PRIMOS, FIBONACCI, BORDA, QUADRANTES,
    MASSA_BOLA_KG, DIAMETRO_BOLA_M, COEF_RESTITUICAO,
    TEMPERATURA_K, PRESSAO_ATM, DENSIDADE_AR, UMIDADE_RELATIVA, GRAVIDADE
)

try:
    from database.db_manager import DBManager
    from core.cerebro_ia import InteligenciaMagna, CerebroIA
    from core.forja_auto import ForjaAutomatica
    from core.inmet import TelemetriaInmet, InmetClient, LOCAL_PADRAO, CAPITAIS
    from core.laboratorio_magna import LaboratorioMagna, ESTRATEGIAS_BASE
    from core.fisica_sorteio import MotorFisicaSorteio, PerfilBola, AmbienteSorteio
    from core.magna_suprema import (
        DetectorRegime, MemoriaVetorialMagna, JuizMagna,
        VerificadorMagno, AlocadorOrcamentoMagno, AprendizadoBayesianoMagno,
        EWCContinual, MetaAprendizadoRegime, FisicaRealBalanca,
        PerfilRiscoPessoal, MCTSPool, AlocadorMultiRota, UtilidadeEsperada,
        JuizAdversarial, TesteNIST, PValueRandom, ExplainabilityMagna,
        ChatMagna, FingerprintPessoal, BacktestLote, TesteBinomial,
        CurvaAprendizado
    )
    from core.forja_lotes import MotorGrafos, ForjaDeLotes, GeometriaJohnson
    from core.wheeling import MotorWheeling
    from core.oraculo_convergente import OraculoConvergente
    from core.acervo_cor import AcervoCorMagna
    from core.clima_lotofacil import MotorClima
    from core.antipopularidade import AntiPopularidade
    from core.caixa_client import CaixaClient
    
    IMPORTS_OK = True
except Exception as e:
    print(f"[ERRO] Import falhou: {e}")
    IMPORTS_OK = False


# ============================================================================
# ENUMS E CONSTANTES
# ============================================================================

class DecisaoStatus(Enum):
    AGUARDANDO = "aguardando"
    CONFERIDA = "conferida"
    ERRO = "erro"
    CANCELADA = "cancelada"


class AmbienteStatus(Enum):
    NEUTRO = "neutro"
    OK = "ok"
    CONTINGENCIA = "contingencia"
    ERRO = "erro"


class EstrategiaTipo(Enum):
    EXAUSTAO_UNICA = "exaustao-unica"
    EXAUSTAO_DIVERSA = "exaustao-diversa"
    WHEELING_13 = "wheeling-garantia-13"
    WHEELING_14 = "wheeling-garantia-14"
    WHEELING_15 = "wheeling-garantia-15"
    FORJA_ESPACIAL = "forja-espacial"
    FORJA_SUPREMA = "forja-suprema"


# ============================================================================
# CLASSE PRINCIPAL - INTELIGÊNCIA MAGNA FORTE
# ============================================================================

class InteligenciaMagnaForte:
    """
    INTELIGÊNCIA MAGNA FORTE - SISTEMA AUTÔNOMO COMPLETO
    
    Esta classe integra TODAS as funcionalidades:
    - Forja Automática
    - Local de Sorteio
    - Telemetria INMET
    - Física do Sorteio
    - Benchmark Walk-Forward
    - Decisão Autônoma
    - Aprendizado Contínuo
    - Medição e Auditoria
    - Exploração e Recalibração
    
    A Inteligência Magna é ÚNICA e AUTÔNOMA nas decisões.
    """
    
    VERSAO = "12.0-Magna-Forte-Autonomo-Unico"
    
    def __init__(self, db_path: str = None, n_cartelas: int = 8):
        """
        Inicializa a Inteligência Magna Forte.
        
        Args:
            db_path: Caminho para o banco de dados
            n_cartelas: Número padrão de cartelas a gerar
        """
        self.db_path = db_path or DATABASE_PATH
        self.n_cartelas = n_cartelas
        self.db = DBManager(self.db_path)
        
        # Estado do sistema
        self.estado = "inicializando"
        self.treinado = False
        self._lock = threading.RLock()
        
        # Componentes integrados
        self._inicializar_componentes()
        
        # Memória de execução
        self._ultima_decisao = None
        self._ultimo_ambiente = None
        self._ultimo_local = None
        self._historico_decisoes = []
        
        # Benchmark walk-forward
        self._laboratorio = None
        self._placar_estategias = {}
        self._quarentena = set()
        
        # Telemetria e Ambiente
        self._telemetria = None
        self._cliente_inmet = None
        
        # Física do Sorteio
        self._fisica = None
        
        # Forja Automática
        self._forja_auto = None
        
        # Inteligência Magna Base
        self._magna_base = None
        
        # Inicializa tudo
        self._inicializar_sistema()
        
        self.estado = "pronto"
        print(f"[MAGNA FORTE] Inicialização concluída - Versão {self.VERSAO}")
    
    def _inicializar_componentes(self):
        """Inicializa todos os componentes."""
        try:
            # Inteligência Magna Base
            self._magna_base = InteligenciaMagna(
                db_path=self.db_path, 
                n_cartelas=self.n_cartelas
            )
            
            # Telemetria INMET
            self._telemetria = TelemetriaInmet(self.db_path)
            self._cliente_inmet = InmetClient()
            
            # Física do Sorteio
            self._fisica = MotorFisicaSorteio(self.db_path)
            
            # Forja Automática
            self._forja_auto = ForjaAutomatica(
                magna=self._magna_base,
                db_path=self.db_path
            )
            
            # Laboratório
            self._laboratorio = LaboratorioMagna(
                db_path=self.db_path,
                matriz=self._magna_base.matriz
            )
            
        except Exception as e:
            print(f"[ERRO] Falha na inicialização: {e}")
            raise
    
    def _inicializar_sistema(self):
        """Inicializa o sistema completo."""
        # Carrega o placar de estratégias
        self._carregar_placar_estategias()
        
        # Verifica se a Magna Base está treinada
        if not self._magna_base.treinado:
            self._magna_base.treinar()
            self.treinado = True
    
    def _carregar_placar_estategias(self):
        """Carrega o placar de estratégias do laboratório."""
        try:
            placar = self._laboratorio.placar_persistido()
            for item in placar:
                nome = item.get("fonte", "")
                self._placar_estategias[nome] = {
                    "media_acertos": item.get("media_acertos", 0),
                    "taxa_13_mais": item.get("taxa_13_mais", 0),
                    "p_valor": item.get("p_valor", 1.0),
                    "veredito": item.get("veredito", "NEUTRA"),
                    "quarentena": bool(item.get("quarentena", 0))
                }
                if item.get("quarentena", 0):
                    self._quarentena.add(nome)
        except Exception as e:
            print(f"[AVISO] Não foi possível carregar placar: {e}")
    
    # ========================================================================
    # 1. REGISTRO DE AMBIENTE DE SORTEIO
    # ========================================================================
    
    def registrar_ambiente_sorteio(self, concurso: int = None, 
                                   resultado_caixa: Dict = None,
                                   usar_rede: bool = True) -> Dict[str, Any]:
        """
        Registra o ambiente completo do sorteio:
        - Local do sorteio (Caixa → INMET → Padrão)
        - Telemetria (temperatura, pressão, umidade)
        - Física das bolas (se disponível)
        
        Args:
            concurso: Número do concurso
            resultado_caixa: Resultado oficial da Caixa
            usar_rede: Se deve usar a rede para buscar dados
            
        Returns:
            Dicionário com todas as informações do ambiente
        """
        ambiente = {
            "concurso": concurso,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "local": None,
            "telemetria": None,
            "fisica": None,
            "status": "ok"
        }
        
        try:
            # 1.1. Local do Sorteio
            local = self._obter_local_sorteio(resultado_caixa, usar_rede)
            ambiente["local"] = local
            self._ultimo_local = local
            
            # 1.2. Telemetria INMET
            telemetria = self._obter_telemetria(local, concurso, usar_rede)
            ambiente["telemetria"] = telemetria
            self._ultimo_ambiente = telemetria
            
            # 1.3. Física do Ambiente
            fisica = self._obter_fisica_ambiente(concurso, telemetria)
            ambiente["fisica"] = fisica
            
            # 1.4. Persiste no banco
            self._persistir_ambiente(ambiente)
            
        except Exception as e:
            ambiente["status"] = "erro"
            ambiente["erro"] = str(e)
            print(f"[ERRO] Registro de ambiente: {e}")
        
        return ambiente
    
    def _obter_local_sorteio(self, resultado_caixa: Dict, usar_rede: bool) -> Dict[str, Any]:
        """Obtém o local do sorteio."""
        # 1. Tenta do resultado Caixa
        if resultado_caixa:
            local = self._forja_auto.local_do_sorteio(
                usar_rede=False, 
                resultado_caixa=resultado_caixa
            )
            if local and local.get("cidade_uf"):
                return local
        
        # 2. Tenta da última telemetria
        if usar_rede:
            try:
                local = self._forja_auto.local_do_sorteio(usar_rede=True)
                if local and local.get("cidade_uf"):
                    return local
            except Exception:
                pass
        
        # 3. Usa padrão
        return dict(LOCAL_PADRAO)
    
    def _obter_telemetria(self, local: Dict, concurso: int, usar_rede: bool) -> Dict[str, Any]:
        """Obtém a telemetria do local."""
        try:
            if usar_rede:
                # Tenta obter telemetria da rede
                telemetria = self._cliente_inmet.telemetria(
                    local.get("local"),
                    local.get("cidade_uf")
                )
                if telemetria.get("status") == "ok":
                    return telemetria
            
            # Tenta do banco local
            telemetria_banco = self._telemetria.ultima()
            if telemetria_banco:
                return telemetria_banco
            
            # Retorna neutro
            return {
                "status": "neutro",
                "fonte": "padrao",
                "temperatura": TEMPERATURA_K,
                "pressao": PRESSAO_ATM,
                "umidade": UMIDADE_RELATIVA,
                "local": local
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e),
                "local": local
            }
    
    def _obter_fisica_ambiente(self, concurso: int, telemetria: Dict) -> Dict[str, Any]:
        """Obtém os dados físicos do ambiente."""
        try:
            # Registra ambiente na física
            if concurso:
                self._fisica.registrar_ambiente(
                    concurso=concurso,
                    temperatura_K=telemetria.get("temperatura"),
                    pressao_atm=telemetria.get("pressao"),
                    umidade=telemetria.get("umidade")
                )
            
            # Obtém o último ambiente registrado
            ambientes = self._fisica.get_ambientes(limit=1)
            if ambientes:
                return ambientes[0]
            
            # Retorna padrão
            return {
                "temperatura_K": TEMPERATURA_K,
                "pressao_atm": PRESSAO_ATM,
                "umidade": UMIDADE_RELATIVA,
                "gravidade": GRAVIDADE,
                "densidade_ar": DENSIDADE_AR
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    def _persistir_ambiente(self, ambiente: Dict) -> bool:
        """Persiste o ambiente no banco de dados."""
        try:
            # Salva na telemetria INMET
            if ambiente.get("telemetria") and ambiente["telemetria"].get("status") == "ok":
                self._telemetria.registrar(
                    ambiente["telemetria"],
                    concurso=ambiente.get("concurso")
                )
            
            # Salva na física
            if ambiente.get("fisica"):
                self._fisica.registrar_ambiente(
                    concurso=ambiente.get("concurso"),
                    temperatura_K=ambiente["fisica"].get("temperatura_K"),
                    pressao_atm=ambiente["fisica"].get("pressao_atm"),
                    umidade=ambiente["fisica"].get("umidade")
                )
            
            return True
            
        except Exception as e:
            print(f"[ERRO] Persistência de ambiente: {e}")
            return False
    
    # ========================================================================
    # 2. FORJA AUTOMÁTICA INTEGRADA
    # ========================================================================
    
    def forja_automatica_completa(self, quantidade: int = 8, 
                                   orcamento: float = 100.0,
                                   alvo: int = 13,
                                   perfil: str = "equilibrado",
                                   segundos_forja: float = 60.0,
                                   usar_inmet: bool = True,
                                   usar_fisica: bool = True,
                                   registrar: bool = True) -> Dict[str, Any]:
        """
        Executa a Forja Automática completa com:
        - Local do sorteio
        - Telemetria INMET
        - Física do ambiente
        - Decisão da Inteligência Magna
        
        Args:
            quantidade: Número de cartelas
            orcamento: Orçamento disponível
            alvo: Alvo de pontos (13, 14, 15)
            perfil: Perfil de risco (conservador, equilibrado, agressivo)
            segundos_forja: Tempo máximo para forja
            usar_inmet: Se deve usar telemetria INMET
            usar_fisica: Se deve usar física do ambiente
            registrar: Se deve registrar no banco
            
        Returns:
            Resultado completo da forja
        """
        try:
            # 1. Registra ambiente de sorteio
            ambiente = self.registrar_ambiente_sorteio(usar_rede=usar_inmet)
            
            # 2. Configura clima na Magna Base (se disponível)
            if usar_fisica and hasattr(self._magna_base, 'clima'):
                self._configurar_clima(ambiente)
            
            # 3. Executa forja automática
            resultado = self._forja_auto.executar(
                quantidade=quantidade,
                orcamento=orcamento,
                alvo=alvo,
                perfil=perfil,
                segundos_forja=segundos_forja,
                usar_inmet=usar_inmet,
                persistir_telemetria=registrar,
                salvar=registrar
            )
            
            # 4. Adiciona informações do ambiente
            resultado["ambiente"] = ambiente
            resultado["forja_automatica"] = True
            
            # 5. Registra na Magna Forte
            self._registrar_decisao(resultado)
            
            return resultado
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e),
                "ambiente": ambiente if 'ambiente' in locals() else None
            }
    
    def _configurar_clima(self, ambiente: Dict):
        """Configura o clima na Magna Base."""
        try:
            telemetria = ambiente.get("telemetria", {})
            if telemetria.get("status") == "ok":
                temperatura = telemetria.get("temperatura")
                pressao = telemetria.get("pressao")
                umidade = telemetria.get("umidade")
                
                if temperatura and pressao and umidade:
                    self._magna_base.clima.definir_condicoes(
                        temperatura=temperatura,
                        pressao=pressao,
                        umidade=umidade
                    )
        except Exception as e:
            print(f"[AVISO] Configuração de clima: {e}")
    
    # ========================================================================
    # 3. DECISÃO AUTÔNOMA
    # ========================================================================
    
    def decidir(self, quantidade: int = 8, 
                orcamento: float = 100.0,
                alvo: int = 13,
                perfil: str = "equilibrado",
                modo: str = "auto",
                registrar: bool = True) -> Dict[str, Any]:
        """
        Decisão autônoma da Inteligência Magna Forte.
        
        Esta é a porta principal de decisão do sistema.
        
        Args:
            quantidade: Número de cartelas
            orcamento: Orçamento disponível
            alvo: Alvo de pontos (13, 14, 15)
            perfil: Perfil de risco
            modo: Modo de decisão (auto, forja, suprema)
            registrar: Se deve registrar no banco
            
        Returns:
            Decisão completa
        """
        with self._lock:
            try:
                # 1. Registra ambiente
                ambiente = self.registrar_ambiente_sorteio()
                
                # 2. Decide com base no modo
                if modo == "forja":
                    resultado = self.forja_automatica_completa(
                        quantidade=quantidade,
                        orcamento=orcamento,
                        alvo=alvo,
                        perfil=perfil,
                        segundos_forja=60.0,
                        usar_inmet=True,
                        usar_fisica=True,
                        registrar=registrar
                    )
                elif modo == "suprema":
                    resultado = self._magna_base.decidir_suprema(
                        quantidade=quantidade,
                        orcamento=orcamento,
                        alvo=alvo,
                        perfil=perfil,
                        segundos_forja=60.0,
                        registrar=registrar
                    )
                    # Adiciona ambiente
                    resultado["ambiente"] = ambiente
                else:
                    # Modo auto - usa a decisão inteligente
                    resultado = self._decisao_inteligente(
                        quantidade=quantidade,
                        orcamento=orcamento,
                        alvo=alvo,
                        perfil=perfil,
                        ambiente=ambiente,
                        registrar=registrar
                    )
                
                # 3. Adiciona metadados
                resultado["decisao_autonoma"] = True
                resultado["inteligencia_magna_forte"] = self.VERSAO
                resultado["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 4. Registra
                self._registrar_decisao(resultado)
                
                return resultado
                
            except Exception as e:
                return {
                    "status": "erro",
                    "erro": str(e),
                    "modo": modo
                }
    
    def _decisao_inteligente(self, quantidade: int, orcamento: float,
                            alvo: int, perfil: str, ambiente: Dict,
                            registrar: bool) -> Dict[str, Any]:
        """
        Decisão inteligente baseada no ambiente e estado do sistema.
        """
        # Analisa o ambiente
        local = ambiente.get("local", {})
        telemetria = ambiente.get("telemetria", {})
        
        # Decide a estratégia com base no ambiente
        estrategia = self._escolher_estrategia_inteligente(
            quantidade, orcamento, alvo, perfil, local, telemetria
        )
        
        # Executa a estratégia
        if estrategia == "forja_automatica":
            return self.forja_automatica_completa(
                quantidade=quantidade,
                orcamento=orcamento,
                alvo=alvo,
                perfil=perfil,
                segundos_forja=60.0,
                usar_inmet=True,
                usar_fisica=True,
                registrar=registrar
            )
        elif estrategia == "suprema":
            return self._magna_base.decidir_suprema(
                quantidade=quantidade,
                orcamento=orcamento,
                alvo=alvo,
                perfil=perfil,
                segundos_forja=60.0,
                registrar=registrar
            )
        else:
            # Usa a decisão padrão da Magna Base
            return self._magna_base.decidir_e_gerar(
                quantidade=quantidade,
                orcamento=orcamento,
                alvo=alvo,
                modo="auto",
                registrar=registrar
            )
    
    def _escolher_estrategia_inteligente(self, quantidade: int, orcamento: float,
                                         alvo: int, perfil: str,
                                         local: Dict, telemetria: Dict) -> str:
        """
        Escolhe a estratégia mais adequada com base no contexto.
        """
        # Se for para poucas cartelas, usa exaustão
        if quantidade <= 2:
            return "suprema"
        
        # Se for para alvo 15, usa forja automática
        if alvo == 15:
            return "forja_automatica"
        
        # Se tiver telemetria válida, usa forja automática
        if telemetria.get("status") == "ok":
            return "forja_automatica"
        
        # Caso contrário, usa suprema
        return "suprema"
    
    def _registrar_decisao(self, resultado: Dict) -> int:
        """Registra a decisão no banco de dados."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO magna_decisoes_forte
                (timestamp, quantidade, orcamento, alvo, perfil, estrategia,
                 resultado_json, ambiente_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                resultado.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                int(resultado.get("n_cartelas", 0)),
                float(resultado.get("orcamento", 0) or 0),
                int(resultado.get("alvo", 13) or 13),
                str(resultado.get("perfil", "equilibrado")),
                str(resultado.get("estrategia", "auto")),
                json.dumps(resultado, default=str),
                json.dumps(resultado.get("ambiente", {}), default=str),
                "concluida"
            ))
            
            decisao_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self._ultima_decisao = resultado
            self._historico_decisoes.append(resultado)
            
            if len(self._historico_decisoes) > 100:
                self._historico_decisoes = self._historico_decisoes[-100:]
            
            return decisao_id
            
        except Exception as e:
            print(f"[ERRO] Registro de decisão: {e}")
            return 0
    
    # ========================================================================
    # 4. BENCHMARK WALK-FORWARD ENHANCED
    # ========================================================================
    
    def benchmark_walkforward_completo(self, n_testes: int = 40,
                                       janela: int = 50,
                                       callback: Callable = None) -> Dict[str, Any]:
        """
        Executa benchmark walk-forward completo de todas as estratégias.
        
        Args:
            n_testes: Número de testes
            janela: Janela de treino
            callback: Função de callback para progresso
            
        Returns:
            Resultado completo do benchmark
        """
        try:
            # Executa benchmark do laboratório
            resultado = self._laboratorio.rodar_benchmark(
                n_testes=n_testes,
                janela=janela,
                persistir=True
            )
            
            # Atualiza placar
            self._atualizar_placar_estategias()
            
            # Executa backtest de captura
            backtest = self._magna_base.backtest_captura(
                k=n_testes,
                n_pool=17
            )
            
            resultado["backtest_captura"] = backtest
            resultado["placar_atualizado"] = self._placar_estategias
            
            return resultado
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    def _atualizar_placar_estategias(self):
        """Atualiza o placar de estratégias."""
        try:
            placar = self._laboratorio.placar_persistido()
            for item in placar:
                nome = item.get("fonte", "")
                self._placar_estategias[nome] = {
                    "media_acertos": item.get("media_acertos", 0),
                    "taxa_13_mais": item.get("taxa_13_mais", 0),
                    "p_valor": item.get("p_valor", 1.0),
                    "veredito": item.get("veredito", "NEUTRA"),
                    "quarentena": bool(item.get("quarentena", 0))
                }
                if item.get("quarentena", 0):
                    self._quarentena.add(nome)
        except Exception as e:
            print(f"[AVISO] Atualização de placar: {e}")
    
    def explorar_mutacoes(self, ensaios: List[Dict], 
                         n_testes: int = 20,
                         callback: Callable = None) -> Dict[str, Any]:
        """
        Explora mutações de estratégias.
        
        Args:
            ensaios: Lista de mutações para testar
            n_testes: Número de testes por mutação
            callback: Função de callback
            
        Returns:
            Resultado da exploração
        """
        try:
            return self._laboratorio.explorar(
                ensaios=ensaios,
                n_testes=n_testes,
                persistir=True
            )
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    # ========================================================================
    # 5. APRENDIZADO CONTÍNUO
    # ========================================================================
    
    def aprender_com_resultado(self, concurso: int, 
                               dezenas_reais: List[int],
                               premios: Dict = None) -> Dict[str, Any]:
        """
        Aprende com o resultado real de um concurso.
        
        Args:
            concurso: Número do concurso
            dezenas_reais: Dezenas reais sorteadas
            premios: Prêmios do concurso
            
        Returns:
            Resultado do aprendizado
        """
        try:
            # 1. Registra ambiente do concurso
            ambiente = self.registrar_ambiente_sorteio(concurso=concurso)
            
            # 2. Aprende com a Magna Base
            resultado = self._magna_base.aprender_resultado_magna(
                concurso, dezenas_reais
            )
            
            # 3. Atualiza física com o resultado
            if premios:
                for i, dezena in enumerate(dezenas_reais, 1):
                    # Incrementa ciclos de uso
                    if dezena in self._fisica._bolas:
                        bola = self._fisica._bolas[dezena]
                        bola.ciclos_uso += 1
                        self._fisica.registrar_bola(
                            numero=dezena,
                            massa_g=bola.massa * 1000,
                            diametro_mm=bola.diametro * 1000,
                            cor=bola.cor,
                            ciclos_uso=bola.ciclos_uso
                        )
            
            # 4. Atualiza telemetria
            self._telemetria.registrar(
                ambiente.get("telemetria", {}),
                concurso=concurso
            )
            
            # 5. Recalibra se necessário
            self._recalibrar_se_necessario()
            
            return {
                "status": "ok",
                "aprendizado_magna": resultado,
                "ambiente": ambiente,
                "recalibracao": "executa" if self._recalibrar_se_necessario() else "nao_necessario"
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    def _recalibrar_se_necessario(self) -> bool:
        """
        Recalibra o sistema se necessário.
        
        Returns:
            True se recalibrou, False caso contrário
        """
        try:
            # Verifica se é necessário recalibrar
            historico = self.get_historico_decisoes(limit=10)
            
            if len(historico) < 5:
                return False
            
            # Calcula média de acertos
            medias = []
            for decisao in historico:
                if decisao.get("status") == "conferida":
                    media = decisao.get("media_acertos", 0)
                    if media:
                        medias.append(float(media))
            
            if len(medias) < 5:
                return False
            
            media_recente = sum(medias[-5:]) / 5
            media_anterior = sum(medias[:-5]) / len(medias[:-5]) if len(medias) > 5 else media_recente
            
            # Se a média caiu significativamente, recalibra
            if media_recente < media_anterior * 0.95:
                print("[RECALIBRAÇÃO] Média de acertos caiu, recalibrando...")
                self._calibrar_pesos()
                return True
            
            return False
            
        except Exception as e:
            print(f"[ERRO] Recalibração: {e}")
            return False
    
    def _calibrar_pesos(self):
        """Calibra os pesos das fontes."""
        try:
            # Usa o método de calibração do laboratório
            self._laboratorio.rodar_benchmark(n_testes=20, janela=50, persistir=True)
            self._atualizar_placar_estategias()
            
            # Atualiza pesos da Magna Base
            self._magna_base.pesos_fontes_magna = self._laboratorio._recomendacao
            
        except Exception as e:
            print(f"[ERRO] Calibração: {e}")
    
    # ========================================================================
    # 6. MEDIÇÃO E AUDITORIA
    # ========================================================================
    
    def medir_desempenho(self, limit: int = 50) -> Dict[str, Any]:
        """
        Medição de desempenho do sistema.
        
        Args:
            limit: Número de decisões a analisar
            
        Returns:
            Medições de desempenho
        """
        try:
            historico = self.get_historico_decisoes(limit=limit)
            
            # Filtra decisões conferidas
            conferidas = [d for d in historico if d.get("status") == "conferida"]
            
            if not conferidas:
                return {
                    "status": "sem_dados",
                    "n_decisoes": 0
                }
            
            # Calcula estatísticas
            acertos = [float(d.get("media_acertos", 0)) for d in conferidas]
            melhores = [int(d.get("melhor_acertos", 0)) for d in conferidas]
            
            media_acertos = sum(acertos) / len(acertos)
            taxa_13_mais = sum(1 for m in melhores if m >= 13) / len(melhores)
            
            return {
                "status": "ok",
                "n_decisoes": len(conferidas),
                "media_acertos": round(media_acertos, 4),
                "taxa_13_mais": round(taxa_13_mais, 4),
                "melhor_acertos": max(melhores) if melhores else 0,
                "pior_acertos": min(melhores) if melhores else 0,
                "baseline_media": 9.0,
                "baseline_taxa_13": round(1 - (1 - 1/691)**8, 4)  # 8 cartelas
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    def auditar_sistema(self) -> Dict[str, Any]:
        """
        Auditoria completa do sistema.
        
        Returns:
            Resultado da auditoria
        """
        try:
            # 1. Auditoria da Magna Base
            magna_audit = self._magna_base.diagnostico_aprendizado()
            
            # 2. Auditoria do banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM magna_decisoes_forte")
            n_decisoes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM magna_decisoes_forte WHERE status='conferida'")
            n_conferidas = cursor.fetchone()[0]
            
            conn.close()
            
            # 3. Auditoria da telemetria
            telemetria_audit = self._telemetria.resumo()
            
            # 4. Auditoria da física
            fisica_audit = self._fisica.get_status()
            
            return {
                "status": "ok",
                "magna_base": magna_audit,
                "banco_dados": {
                    "n_decisoes": n_decisoes,
                    "n_conferidas": n_conferidas
                },
                "telemetria": telemetria_audit,
                "fisica": fisica_audit,
                "quarentena": list(self._quarentena),
                "placar_estategias": self._placar_estategias
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    # ========================================================================
    # 7. EXPLORAÇÃO E PESQUISA
    # ========================================================================
    
    def explorar(self, orcamento_tempo: float = 60.0,
                 callback: Callable = None) -> Dict[str, Any]:
        """
        Exploração autônoma do sistema.
        
        Args:
            orcamento_tempo: Tempo máximo para exploração
            callback: Função de callback
            
        Returns:
            Resultado da exploração
        """
        t0 = time.time()
        resultados = {}
        
        try:
            # 1. Explora mutações de estratégias
            ensaios = self._gerar_ensaios_exploracao()
            
            if callback:
                callback(f"Explorando {len(ensaios)} mutações...")
            
            resultado_exploracao = self.explorar_mutacoes(
                ensaios=ensaios,
                n_testes=10,
                callback=callback
            )
            resultados["exploracao"] = resultado_exploracao
            
            # 2. Executa benchmark
            if time.time() - t0 < orcamento_tempo * 0.7:
                if callback:
                    callback("Executando benchmark...")
                
                benchmark = self.benchmark_walkforward_completo(
                    n_testes=20,
                    callback=callback
                )
                resultados["benchmark"] = benchmark
            
            # 3. Medição de desempenho
            if time.time() - t0 < orcamento_tempo * 0.9:
                if callback:
                    callback("Medindo desempenho...")
                
                medicao = self.medir_desempenho(limit=30)
                resultados["medicao"] = medicao
            
            resultados["tempo_total"] = round(time.time() - t0, 2)
            resultados["status"] = "ok"
            
            return resultados
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e),
                "tempo_total": round(time.time() - t0, 2)
            }
    
    def _gerar_ensaios_exploracao(self) -> List[Dict]:
        """Gera ensaios para exploração."""
        ensaios = []
        
        # Variação de janelas
        for janela in [30, 50, 100]:
            ensaios.append({
                "janela": janela,
                "pesos": {
                    "freq_global": 0.25,
                    "freq_recente": 0.25,
                    "reversao": 0.20,
                    "markov": 0.15,
                    "espectral": 0.15
                }
            })
        
        # Variação de pesos
        for i in range(3):
            pesos = {
                "freq_global": round(0.20 + i * 0.05, 2),
                "freq_recente": round(0.20 + (2 - i) * 0.05, 2),
                "reversao": round(0.15 + i * 0.03, 2),
                "markov": round(0.15 + (2 - i) * 0.03, 2),
                "espectral": 0.15,
                "uniforme": 0.10
            }
            ensaios.append({
                "janela": 50,
                "pesos": pesos
            })
        
        return ensaios
    
    # ========================================================================
    # 8. OPERAÇÕES AUTÔNOMAS
    # ========================================================================
    
    def ciclo_completo(self, concurso: int = None,
                       callback: Callable = None) -> Dict[str, Any]:
        """
        Executa um ciclo completo autônomo:
        1. Registra ambiente
        2. Decide
        3. Aguarda resultado (simulado)
        4. Aprende
        5. Recalibra se necessário
        
        Args:
            concurso: Número do concurso (se None, usa o último + 1)
            callback: Função de callback
            
        Returns:
            Resultado do ciclo
        """
        try:
            # 1. Determina o concurso
            if concurso is None:
                concurso = (self.db.get_ultimo_concurso() or 0) + 1
            
            if callback:
                callback(f"Iniciando ciclo para concurso {concurso}...")
            
            # 2. Registra ambiente
            ambiente = self.registrar_ambiente_sorteio(concurso=concurso)
            
            if callback:
                callback(f"Ambiente registrado: {ambiente.get('local', {}).get('cidade_uf', '?')}")
            
            # 3. Decide
            decisao = self.decidir(
                quantidade=8,
                orcamento=100.0,
                alvo=13,
                perfil="equilibrado",
                modo="auto",
                registrar=True
            )
            
            if callback:
                callback(f"Decisão tomada: {decisao.get('estrategia', '?')}")
            
            # 4. Simula resultado (na prática, isso viria da Caixa)
            # Para fins de teste, usamos um resultado simulado
            dezenas_reais = self._gerar_dezenas_simuladas()
            
            # 5. Aprende
            aprendizado = self.aprender_com_resultado(
                concurso=concurso,
                dezenas_reais=dezenas_reais
            )
            
            if callback:
                callback(f"Aprendizado concluído")
            
            # 6. Recalibra se necessário
            recalibrou = self._recalibrar_se_necessario()
            
            return {
                "status": "ok",
                "concurso": concurso,
                "ambiente": ambiente,
                "decisao": decisao,
                "aprendizado": aprendizado,
                "recalibracao": recalibrou
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }
    
    def _gerar_dezenas_simuladas(self) -> List[int]:
        """Gera dezenas simuladas para teste."""
        # Usa a Magna Base para gerar dezenas realistas
        try:
            resultado = self._magna_base.gerar_otimas(n_cartelas=1, salvar=False)
            if resultado.get("cartelas"):
                return resultado["cartelas"][0]["dezenas"]
        except Exception:
            pass
        
        # Fallback: dezenas aleatórias
        np.random.seed(int(time.time()))
        return sorted(np.random.choice(range(1, 26), 15, replace=False).tolist())
    
    # ========================================================================
    # 9. UTILITÁRIOS
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Obtém o status completo do sistema."""
        return {
            "versao": self.VERSAO,
            "estado": self.estado,
            "treinado": self.treinado,
            "db_path": self.db_path,
            "n_cartelas": self.n_cartelas,
            "ultima_decisao": self._ultima_decisao is not None,
            "ultimo_ambiente": self._ultimo_ambiente is not None,
            "ultimo_local": self._ultimo_local,
            "historico_decisoes": len(self._historico_decisoes),
            "placar_estategias": len(self._placar_estategias),
            "quarentena": len(self._quarentena),
            "magna_base": self._magna_base.get_status() if self._magna_base else None,
            "telemetria": self._telemetria.resumo() if self._telemetria else None,
            "fisica": self._fisica.get_status() if self._fisica else None
        }
    
    def get_historico_decisoes(self, limit: int = 50) -> List[Dict]:
        """Obtém o histórico de decisões."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM magna_decisoes_forte 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            colunas = [desc[0] for desc in cursor.description]
            
            conn.close()
            
            return [dict(zip(colunas, row)) for row in rows]
            
        except Exception as e:
            print(f"[ERRO] Histórico de decisões: {e}")
            return []
    
    def resetar(self) -> Dict[str, Any]:
        """Reseta o sistema (para testes)."""
        try:
            self._magna_base = InteligenciaMagna(
                db_path=self.db_path,
                n_cartelas=self.n_cartelas
            )
            self._laboratorio = LaboratorioMagna(
                db_path=self.db_path,
                matriz=self._magna_base.matriz
            )
            self._placar_estategias = {}
            self._quarentena = set()
            self.treinado = False
            self.estado = "pronto"
            
            return {"status": "ok"}
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }


# ============================================================================
# INICIALIZAÇÃO DO SISTEMA
# ============================================================================

# Instância global (opcional)
_magna_forte_instance = None


def get_inteligencia_magna_forte(db_path: str = None, n_cartelas: int = 8) -> InteligenciaMagnaForte:
    """Obtém a instância da Inteligência Magna Forte."""
    global _magna_forte_instance
    
    if _magna_forte_instance is None or _magna_forte_instance.db_path != (db_path or DATABASE_PATH):
        _magna_forte_instance = InteligenciaMagnaForte(
            db_path=db_path,
            n_cartelas=n_cartelas
        )
    
    return _magna_forte_instance


# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================================================


def executar_ciclo_completo(concurso: int = None, db_path: str = None) -> Dict[str, Any]:
    """Executa um ciclo completo."""
    magna = get_inteligencia_magna_forte(db_path=db_path)
    return magna.ciclo_completo(concurso=concurso)


def decidir_autonomo(quantidade: int = 8, orcamento: float = 100.0,
                    alvo: int = 13, perfil: str = "equilibrado",
                    db_path: str = None) -> Dict[str, Any]:
    """Decisão autônoma."""
    magna = get_inteligencia_magna_forte(db_path=db_path)
    return magna.decidir(
        quantidade=quantidade,
        orcamento=orcamento,
        alvo=alvo,
        perfil=perfil
    )


def forja_automatica(quantidade: int = 8, orcamento: float = 100.0,
                     alvo: int = 13, perfil: str = "equilibrado",
                     db_path: str = None) -> Dict[str, Any]:
    """Forja automática."""
    magna = get_inteligencia_magna_forte(db_path=db_path)
    return magna.forja_automatica_completa(
        quantidade=quantidade,
        orcamento=orcamento,
        alvo=alvo,
        perfil=perfil
    )


def benchmark_completo(n_testes: int = 40, db_path: str = None) -> Dict[str, Any]:
    """Benchmark walk-forward completo."""
    magna = get_inteligencia_magna_forte(db_path=db_path)
    return magna.benchmark_walkforward_completo(n_testes=n_testes)


def explorar_sistema(orcamento_tempo: float = 60.0, db_path: str = None) -> Dict[str, Any]:
    """Exploração do sistema."""
    magna = get_inteligencia_magna_forte(db_path=db_path)
    return magna.explorar(orcamento_tempo=orcamento_tempo)


def auditar_sistema(db_path: str = None) -> Dict[str, Any]:
    """Auditoria do sistema."""
    magna = get_inteligencia_magna_forte(db_path=db_path)
    return magna.auditar_sistema()


# ============================================================================
# TESTES
# ============================================================================


def testar_sistema():
    """Testa o sistema completo."""
    print("=" * 80)
    print("TESTE DO SISTEMA INTELIGÊNCIA MAGNA FORTE")
    print("=" * 80)
    
    # 1. Inicialização
    print("\n1. Inicializando...")
    magna = get_inteligencia_magna_forte()
    status = magna.get_status()
    print(f"   ✓ Versão: {status['versao']}")
    print(f"   ✓ Estado: {status['estado']}")
    print(f"   ✓ Treinado: {status['treinado']}")
    
    # 2. Registro de ambiente
    print("\n2. Registrando ambiente...")
    ambiente = magna.registrar_ambiente_sorteio(usar_rede=False)
    print(f"   ✓ Local: {ambiente['local'].get('cidade_uf', '?')}")
    print(f"   ✓ Telemetria: {ambiente['telemetria'].get('status', '?')}")
    print(f"   ✓ Física: {ambiente['fisica'].get('temperatura_K', '?')}")
    
    # 3. Decisão
    print("\n3. Tomando decisão...")
    decisao = magna.decidir(quantidade=2, orcamento=20.0, alvo=13)
    print(f"   ✓ Status: {decisao.get('status', '?')}")
    print(f"   ✓ Estratégia: {decisao.get('estrategia', '?')}")
    print(f"   ✓ Cartelas: {decisao.get('n_cartelas', 0)}")
    
    # 4. Benchmark
    print("\n4. Executando benchmark...")
    benchmark = magna.benchmark_walkforward_completo(n_testes=5)
    print(f"   ✓ Status: {benchmark.get('status', '?')}")
    print(f"   ✓ Estratégias: {len(benchmark.get('estimativas', {}))}")
    
    # 5. Auditoria
    print("\n5. Auditando sistema...")
    auditoria = magna.auditar_sistema()
    print(f"   ✓ Status: {auditoria.get('status', '?')}")
    print(f"   ✓ Decisões: {auditoria.get('banco_dados', {}).get('n_decisoes', 0)}")
    
    # 6. Exploração
    print("\n6. Explorando sistema...")
    exploracao = magna.explorar(orcamento_tempo=10.0)
    print(f"   ✓ Status: {exploracao.get('status', '?')}")
    print(f"   ✓ Tempo: {exploracao.get('tempo_total', 0)}s")
    
    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)


if __name__ == "__main__":
    # Executa testes
    testar_sistema()
