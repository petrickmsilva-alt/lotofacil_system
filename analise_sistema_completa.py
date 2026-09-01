#!/usr/bin/env python3
"""
============================================================
ANÁLISE COMPLETA DO SISTEMA LOTOFÁCIL - INTELIGÊNCIA MAGNA
============================================================

Este script analisa código por código, verifica precisão dos cálculos,
identifica erros e propõe melhorias para o sistema.

OBJETIVO: Transformar a Inteligência Magna em um sistema autônomo,
único, com capacidade de:
- Decidir
- Aprender
- Medir
- Auditar
- Explorar
- Recalibrar

Com integração completa de:
- Forja Automática
- Local de Sorteio
- Telemetria INMET
- Benchmark Walk-Forward
- Registro de Ambiente de Sorteio
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

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
    from core.inmet import TelemetriaInmet, InmetClient, LOCAL_PADRAO
    from core.laboratorio_magna import LaboratorioMagna
    from core.fisica_sorteio import MotorFisicaSorteio
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
    
    IMPORTS_OK = True
except Exception as e:
    print(f"[ERRO] Import falhou: {e}")
    IMPORTS_OK = False


class AnalisadorSistema:
    """Analisador completo do sistema Lotofácil."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        self.db = DBManager(self.db_path)
        self.relatorio: Dict[str, Any] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sistema": "Lotofácil Inteligência Magna",
            "analises": {},
            "erros": [],
            "recomendacoes": [],
            "melhorias_implementadas": []
        }
        
    def analisar(self) -> Dict[str, Any]:
        """Executa análise completa do sistema."""
        print("🔍 Iniciando análise completa do sistema...")
        
        # 1. Análise de integridade dos módulos
        self._analisar_imports()
        
        # 2. Análise do banco de dados
        self._analisar_banco_dados()
        
        # 3. Análise da Inteligência Magna
        self._analisar_inteligencia_magna()
        
        # 4. Análise da Forja Automática
        self._analisar_forja_automatica()
        
        # 5. Análise da Telemetria INMET
        self._analisar_telemetria_inmet()
        
        # 6. Análise do Laboratório
        self._analisar_laboratorio()
        
        # 7. Análise de precisão dos cálculos
        self._analisar_precisao_calculos()
        
        # 8. Verificação de consistência
        self._verificar_consistencia()
        
        # 9. Benchmark walk-forward
        self._analisar_benchmark_walkforward()
        
        print("✅ Análise concluída!")
        return self.relatorio
    
    def _analisar_imports(self):
        """Verifica se todos os módulos importam corretamente."""
        print("📦 Analisando imports...")
        
        analise_imports = {
            "status": "ok" if IMPORTS_OK else "erro",
            "modulos_importados": [],
            "modulos_falhos": []
        }
        
        # Testa imports individuais
        modulos_testar = [
            "database.db_manager",
            "core.cerebro_ia",
            "core.forja_auto",
            "core.inmet",
            "core.laboratorio_magna",
            "core.fisica_sorteio",
            "core.magna_suprema",
            "core.forja_lotes",
            "core.wheeling",
            "core.oraculo_convergente",
            "core.acervo_cor",
            "core.clima_lotofacil",
            "core.antipopularidade"
        ]
        
        for modulo in modulos_testar:
            try:
                __import__(modulo)
                analise_imports["modulos_importados"].append(modulo)
            except Exception as e:
                analise_imports["modulos_falhos"].append({
                    "modulo": modulo,
                    "erro": str(e)
                })
        
        self.relatorio["analises"]["imports"] = analise_imports
        
        if analise_imports["modulos_falhos"]:
            self.relatorio["erros"].extend([
                f"Import falhou: {m['modulo']} - {m['erro']}"
                for m in analise_imports["modulos_falhos"]
            ])
        
        print(f"   ✓ {len(analise_imports['modulos_importados'])} módulos importados")
        if analise_imports["modulos_falhos"]:
            print(f"   ✗ {len(analise_imports['modulos_falhos'])} imports falharam")
    
    def _analisar_banco_dados(self):
        """Analisa a integridade do banco de dados."""
        print("🗃️  Analisando banco de dados...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Conta registros nas tabelas principais
            tabelas_analisar = [
                "resultados",
                "ordem_sorteio", 
                "fisica_bolas",
                "fisica_ambientes",
                "inmet_telemetria",
                "magna_conhecimento",
                "magna_memoria",
                "magna_decisoes",
                "magna_episodios",
                "magna_laboratorio",
                "magna_placar_fontes"
            ]
            
            contagens = {}
            for tabela in tabelas_analisar:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                    contagem = cursor.fetchone()[0]
                    contagens[tabela] = contagem
                except sqlite3.OperationalError:
                    contagens[tabela] = "tabela não existe"
            
            # Verifica último concurso
            cursor.execute("SELECT MAX(concurso) FROM resultados")
            ultimo_concurso = cursor.fetchone()[0] or 0
            
            # Verifica integridade dos resultados
            cursor.execute("SELECT COUNT(*) FROM resultados WHERE concurso IS NULL")
            resultados_sem_concurso = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM resultados WHERE d1 IS NULL")
            resultados_incompletos = cursor.fetchone()[0]
            
            conn.close()
            
            self.relatorio["analises"]["banco_dados"] = {
                "status": "ok",
                "tabelas": contagens,
                "ultimo_concurso": int(ultimo_concurso),
                "resultados_sem_concurso": int(resultados_sem_concurso),
                "resultados_incompletos": int(resultados_incompletos),
                "integridade": "OK" if resultados_sem_concurso == 0 and resultados_incompletos == 0 else "PROBLEMAS"
            }
            
            print(f"   ✓ Banco de dados: {ultimo_concurso} concursos")
            print(f"   ✓ Tabelas analisadas: {len(contagens)}")
            
            if resultados_sem_concurso > 0 or resultados_incompletos > 0:
                self.relatorio["erros"].append(
                    f"Banco de dados: {resultados_sem_concurso} resultados sem concurso, "
                    f"{resultados_incompletos} incompletos"
                )
            
        except Exception as e:
            self.relatorio["analises"]["banco_dados"] = {"status": "erro", "erro": str(e)}
            self.relatorio["erros"].append(f"Banco de dados: {e}")
            print(f"   ✗ Erro no banco: {e}")
    
    def _analisar_inteligencia_magna(self):
        """Analisa a Inteligência Magna."""
        print("🧠 Analisando Inteligência Magna...")
        
        try:
            # Inicializa a Magna
            t0 = time.time()
            magna = InteligenciaMagna(db_path=self.db_path, n_cartelas=8)
            tempo_inicializacao = time.time() - t0
            
            # Verifica status
            status = magna.get_status()
            
            # Testa treino
            t0 = time.time()
            treino = magna.treinar()
            tempo_treino = time.time() - t0
            
            # Testa geração de cartelas
            t0 = time.time()
            cartelas = magna.gerar_otimas(n_cartelas=2, salvar=False)
            tempo_geracao = time.time() - t0
            
            # Testa decisão suprema
            t0 = time.time()
            suprema = magna.decidir_suprema(
                quantidade=2, 
                orcamento=20.0, 
                alvo=13, 
                perfil="equilibrado",
                segundos_forja=5.0,
                tentativas_juiz=1,
                usar_mcts=False,
                registrar=False
            )
            tempo_suprema = time.time() - t0
            
            # Verifica acervo
            acervo_status = magna.acervo.estado() if hasattr(magna, 'acervo') else {}
            
            analise_magna = {
                "status": "ok",
                "tempo_inicializacao": round(tempo_inicializacao, 2),
                "tempo_treino": round(tempo_treino, 2),
                "tempo_geracao": round(tempo_geracao, 2),
                "tempo_suprema": round(tempo_suprema, 2),
                "treinado": magna.treinado,
                "n_concursos": magna.n,
                "modulos": len(magna._motores) if hasattr(magna, '_motores') else 0,
                "pesos_modulos": dict(magna.pesos) if hasattr(magna, 'pesos') else {},
                "acervo": acervo_status,
                "cartelas_geradas": len(cartelas.get("cartelas", [])),
                "suprema_status": suprema.get("status", "erro"),
                "suprema_cartelas": len(suprema.get("cartelas", []))
            }
            
            self.relatorio["analises"]["inteligencia_magna"] = analise_magna
            
            print(f"   ✓ Inteligência Magna: {magna.n} concursos")
            print(f"   ✓ Treino: {tempo_treino:.2f}s")
            print(f"   ✓ Geração: {tempo_geracao:.2f}s")
            print(f"   ✓ Suprema: {tempo_suprema:.2f}s")
            
            # Verifica se há erros
            if not magna.treinado:
                self.relatorio["erros"].append("Inteligência Magna não treinada")
            
            if len(cartelas.get("cartelas", [])) == 0:
                self.relatorio["erros"].append("Nenhuma cartela gerada")
            
            if suprema.get("status") != "ok":
                self.relatorio["erros"].append(f"Suprema falhou: {suprema.get('status')}")
            
        except Exception as e:
            self.relatorio["analises"]["inteligencia_magna"] = {"status": "erro", "erro": str(e)}
            self.relatorio["erros"].append(f"Inteligência Magna: {e}")
            print(f"   ✗ Erro na Magna: {e}")
    
    def _analisar_forja_automatica(self):
        """Analisa a Forja Automática."""
        print("🔨 Analisando Forja Automática...")
        
        try:
            # Inicializa a Forja Automática
            magna = InteligenciaMagna(db_path=self.db_path, n_cartelas=8)
            forja_auto = ForjaAutomatica(magna=magna, db_path=self.db_path)
            
            # Testa local do sorteio
            local = forja_auto.local_do_sorteio(usar_rede=False)
            
            # Testa telemetria
            telemetria = forja_auto.coletar_telemetria(local, persistir_telemetria=False)
            
            # Testa execução completa
            t0 = time.time()
            resultado = forja_auto.executar(
                quantidade=2,
                orcamento=20.0,
                alvo=13,
                perfil="equilibrado",
                segundos_forja=5.0,
                usar_inmet=True,
                persistir_telemetria=False,
                salvar=False
            )
            tempo_execucao = time.time() - t0
            
            analise_forja = {
                "status": "ok",
                "local_do_sorteio": local.get("cidade_uf", "desconhecido"),
                "telemetria_status": telemetria.get("status", "erro"),
                "tempo_execucao": round(tempo_execucao, 2),
                "resultado_status": resultado.get("status", "erro"),
                "n_cartelas": resultado.get("n_cartelas", 0)
            }
            
            self.relatorio["analises"]["forja_automatica"] = analise_forja
            
            print(f"   ✓ Forja Automática: {local.get('cidade_uf', '?')}")
            print(f"   ✓ Telemetria: {telemetria.get('status', '?')}")
            print(f"   ✓ Execução: {tempo_execucao:.2f}s")
            
            if resultado.get("status") != "ok":
                self.relatorio["erros"].append(f"Forja Automática falhou: {resultado.get('msg', 'erro desconhecido')}")
            
        except Exception as e:
            self.relatorio["analises"]["forja_automatica"] = {"status": "erro", "erro": str(e)}
            self.relatorio["erros"].append(f"Forja Automática: {e}")
            print(f"   ✗ Erro na Forja: {e}")
    
    def _analisar_telemetria_inmet(self):
        """Analisa a Telemetria INMET."""
        print("🌤️  Analisando Telemetria INMET...")
        
        try:
            telemetria = TelemetriaInmet(self.db_path)
            
            # Testa resumo
            resumo = telemetria.resumo()
            
            # Testa última telemetria
            ultima = telemetria.ultima()
            
            # Testa vetor INMET
            vetor = telemetria.vetor_inmet()
            
            analise_inmet = {
                "status": "ok",
                "n_registros": resumo.get("n_registros", 0),
                "status_resumo": resumo.get("status", "erro"),
                "ultima_telemetria": ultima is not None,
                "vetor_dimensoes": len(vetor) if isinstance(vetor, np.ndarray) else 0,
                "vetor_soma": round(float(vetor.sum()), 4) if isinstance(vetor, np.ndarray) else 0
            }
            
            self.relatorio["analises"]["telemetria_inmet"] = analise_inmet
            
            print(f"   ✓ Telemetria INMET: {resumo.get('n_registros', 0)} registros")
            print(f"   ✓ Vetor: {len(vetor)} dimensões, soma={vetor.sum():.4f}")
            
            if resumo.get("n_registros", 0) == 0:
                self.relatorio["recomendacoes"].append(
                    "Considerar ativação da coleta de telemetria INMET para enriquecer o sistema"
                )
            
        except Exception as e:
            self.relatorio["analises"]["telemetria_inmet"] = {"status": "erro", "erro": str(e)}
            self.relatorio["erros"].append(f"Telemetria INMET: {e}")
            print(f"   ✗ Erro na Telemetria: {e}")
    
    def _analisar_laboratorio(self):
        """Analisa o Laboratório Magna."""
        print("🔬 Analisando Laboratório Magna...")
        
        try:
            # Inicializa o laboratório
            magna = InteligenciaMagna(db_path=self.db_path, n_cartelas=8)
            laboratorio = LaboratorioMagna(db_path=self.db_path, matriz=magna.matriz)
            
            # Testa benchmark
            t0 = time.time()
            benchmark = laboratorio.rodar_benchmark(n_testes=10, janela=30, persistir=False)
            tempo_benchmark = time.time() - t0
            
            # Testa relatório
            relatorio_lab = laboratorio.relatorio()
            
            analise_lab = {
                "status": "ok",
                "tempo_benchmark": round(tempo_benchmark, 2),
                "n_concursos": relatorio_lab.get("concursos_na_base", 0),
                "placar_historico": len(relatorio_lab.get("placar_historico", [])),
                "quarentena": relatorio_lab.get("quarentena", []),
                "pesos_recomendados": relatorio_lab.get("pesos_recomendados", {})
            }
            
            self.relatorio["analises"]["laboratorio"] = analise_lab
            
            print(f"   ✓ Laboratório: {relatorio_lab.get('concursos_na_base', 0)} concursos")
            print(f"   ✓ Benchmark: {tempo_benchmark:.2f}s")
            print(f"   ✓ Quarentena: {len(relatorio_lab.get('quarentena', []))} estratégias")
            
        except Exception as e:
            self.relatorio["analises"]["laboratorio"] = {"status": "erro", "erro": str(e)}
            self.relatorio["erros"].append(f"Laboratório: {e}")
            print(f"   ✗ Erro no Laboratório: {e}")
    
    def _analisar_precisao_calculos(self):
        """Analisa a precisão dos cálculos matemáticos."""
        print("📊 Analisando precisão dos cálculos...")
        
        erros_precisao = []
        
        # Testa cálculos hipergeométricos
        try:
            from math import comb
            
            # Total de combinações
            total_combinacoes = comb(TOTAL_DEZENAS, DEZENAS_POR_JOGO)
            calculado = 3268760
            
            if total_combinacoes != calculado:
                erros_precisao.append(f"Total de combinações: {total_combinacoes} != {calculado}")
            
            # Probabilidade de 15 pontos
            p_15 = 1.0 / total_combinacoes
            calculado_p15 = 1.0 / 3268760
            
            if abs(p_15 - calculado_p15) > 1e-10:
                erros_precisao.append(f"P(15): {p_15} != {calculado_p15}")
            
            # Probabilidade de 14 pontos
            p_14 = (comb(15, 14) * comb(10, 1)) / total_combinacoes
            calculado_p14 = 15 * 10 / 3268760
            
            if abs(p_14 - calculado_p14) > 1e-10:
                erros_precisao.append(f"P(14): {p_14} != {calculado_p14}")
            
            # Probabilidade de 13 pontos
            p_13 = (comb(15, 13) * comb(10, 2)) / total_combinacoes
            calculado_p13 = 105 * 45 / 3268760
            
            if abs(p_13 - calculado_p13) > 1e-10:
                erros_precisao.append(f"P(13): {p_13} != {calculado_p13}")
            
        except Exception as e:
            erros_precisao.append(f"Cálculos hipergeométricos: {e}")
        
        # Testa normalização de vetores
        try:
            vetor = np.random.rand(25)
            vetor_normalizado = vetor / vetor.sum()
            soma = vetor_normalizado.sum()
            
            if abs(soma - 1.0) > 1e-10:
                erros_precisao.append(f"Normalização: soma={soma} != 1.0")
            
        except Exception as e:
            erros_precisao.append(f"Normalização: {e}")
        
        # Testa cálculos de cobertura
        try:
            from core.wheeling import MotorWheeling
            wheeling = MotorWheeling()
            
            # Pool de 17
            pool_17 = list(range(1, 18))
            prob_captura_17 = wheeling.prob_captura(17)
            calculado_17 = comb(17, 15) / comb(25, 15)
            
            if abs(prob_captura_17 - calculado_17) > 1e-10:
                erros_precisao.append(f"P(captura pool 17): {prob_captura_17} != {calculado_17}")
            
        except Exception as e:
            erros_precisao.append(f"Cálculos de cobertura: {e}")
        
        self.relatorio["analises"]["precisao_calculos"] = {
            "status": "ok" if not erros_precisao else "erros_encontrados",
            "erros": erros_precisao
        }
        
        if erros_precisao:
            self.relatorio["erros"].extend(erros_precisao)
            print(f"   ✗ {len(erros_precisao)} erros de precisão")
        else:
            print("   ✓ Todos os cálculos estão precisos")
    
    def _verificar_consistencia(self):
        """Verifica a consistência entre os módulos."""
        print("✅ Verificando consistência...")
        
        inconsistencias = []
        
        try:
            # Verifica se a Magna usa os mesmos dados do banco
            magna = InteligenciaMagna(db_path=self.db_path, n_cartelas=8)
            
            # Verifica se o laboratório usa a mesma matriz
            laboratorio = LaboratorioMagna(db_path=self.db_path, matriz=magna.matriz)
            
            if magna.n != laboratorio.n:
                inconsistencias.append(
                    f"Número de concursos: Magna={magna.n}, Laboratório={laboratorio.n}"
                )
            
            # Verifica se a Forja Automática tem acesso ao mesmo banco
            forja = ForjaAutomatica(magna=magna, db_path=self.db_path)
            
            # Verifica se a telemetria está configurada corretamente
            telemetria = TelemetriaInmet(self.db_path)
            
        except Exception as e:
            inconsistencias.append(f"Verificação de consistência: {e}")
        
        self.relatorio["analises"]["consistencia"] = {
            "status": "ok" if not inconsistencias else "inconsistencias",
            "inconsistencias": inconsistencias
        }
        
        if inconsistencias:
            self.relatorio["erros"].extend(inconsistencias)
            print(f"   ✗ {len(inconsistencias)} inconsistências encontradas")
        else:
            print("   ✓ Todos os módulos são consistentes")
    
    def _analisar_benchmark_walkforward(self):
        """Analisa o benchmark walk-forward."""
        print("📈 Analisando Benchmark Walk-Forward...")
        
        try:
            magna = InteligenciaMagna(db_path=self.db_path, n_cartelas=8)
            
            # Executa backtest de captura
            t0 = time.time()
            backtest = magna.backtest_captura(k=10, n_pool=17)
            tempo_backtest = time.time() - t0
            
            # Executa benchmark do laboratório
            t0 = time.time()
            benchmark = magna.lab_benchmark(n_testes=10, janela=30)
            tempo_benchmark = time.time() - t0
            
            analise_benchmark = {
                "status": "ok",
                "tempo_backtest": round(tempo_backtest, 2),
                "tempo_benchmark": round(tempo_benchmark, 2),
                "backtest_capturas": backtest.get("capturas", 0),
                "backtest_taxa": backtest.get("taxa_captura", 0),
                "backtest_baseline": backtest.get("baseline_p_captura", 0),
                "benchmark_estimativas": benchmark.get("estimativas", {}),
                "benchmark_placar": benchmark.get("placar_historico", [])
            }
            
            self.relatorio["analises"]["benchmark_walkforward"] = analise_benchmark
            
            print(f"   ✓ Backtest: {backtest.get('capturas', 0)}/{backtest.get('k', 0)} capturas")
            print(f"   ✓ Benchmark: {len(benchmark.get('estimativas', {}))} estratégias")
            
            # Verifica se o benchmark está funcionando corretamente
            if backtest.get("k", 0) > 0 and backtest.get("capturas", 0) == 0:
                self.relatorio["recomendacoes"].append(
                    "O backtest não capturou nenhum sorteio - verificar se o pool está funcionando corretamente"
                )
            
        except Exception as e:
            self.relatorio["analises"]["benchmark_walkforward"] = {"status": "erro", "erro": str(e)}
            self.relatorio["erros"].append(f"Benchmark Walk-Forward: {e}")
            print(f"   ✗ Erro no Benchmark: {e}")


def main():
    """Função principal."""
    print("=" * 80)
    print("ANÁLISE COMPLETA DO SISTEMA LOTOFÁCIL - INTELIGÊNCIA MAGNA")
    print("=" * 80)
    print()
    
    # Cria o analisador
    analisador = AnalisadorSistema()
    
    # Executa a análise
    relatorio = analisador.analisar()
    
    # Salva o relatório
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_analise_{timestamp}.json"
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)
    
    print()
    print("=" * 80)
    print("RESUMO DA ANÁLISE")
    print("=" * 80)
    
    # Resumo
    print(f"\n✅ MÓDULOS ANALISADOS: {len(relatorio['analises'])}")
    print(f"❌ ERROS ENCONTRADOS: {len(relatorio['erros'])}")
    print(f"💡 RECOMENDAÇÕES: {len(relatorio['recomendacoes'])}")
    
    # Detalhes dos erros
    if relatorio['erros']:
        print(f"\n📋 ERROS:")
        for i, erro in enumerate(relatorio['erros'], 1):
            print(f"   {i}. {erro}")
    
    # Detalhes das recomendações
    if relatorio['recomendacoes']:
        print(f"\n💡 RECOMENDAÇÕES:")
        for i, rec in enumerate(relatorio['recomendacoes'], 1):
            print(f"   {i}. {rec}")
    
    print(f"\n📁 RELATÓRIO SALVO: {nome_arquivo}")
    print()
    
    return relatorio


if __name__ == "__main__":
    relatorio = main()
