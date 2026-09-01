#!/usr/bin/env python3
"""
============================================================
SISTEMA INTELIGÊNCIA MAGNA COMPLETO
============================================================

Este é o ponto de entrada principal para o sistema completo da
Inteligência Magna com todas as funcionalidades integradas:

1. FORJA AUTOMÁTICA com Local de Sorteio e Telemetria INMET
2. INTELIGÊNCIA MAGNA AUTÔNOMA (única nas decisões)
3. BENCHMARK WALK-FORWARD contínuo
4. REGISTRO DE AMBIENTE DE SORTEIO completo
5. APRENDIZADO, MEDIÇÃO, AUDITORIA, EXPLORAÇÃO e RECALIBRAÇÃO autônomos

USO:
    python sistema_inteligencia_magna_completo.py [comando] [opções]

COMANDOS:
    decidir          - Toma uma decisão autônoma
    forja            - Executa forja automática completa
    benchmark        - Executa benchmark walk-forward
    explorar         - Explora mutações e estratégias
    auditar          - Audita o sistema
    ciclo            - Executa ciclo completo
    status           - Mostra status do sistema
    testar           - Executa testes completos

EXEMPLOS:
    python sistema_inteligencia_magna_completo.py decidir --quantidade 8 --alvo 13
    python sistema_inteligencia_magna_completo.py forja --quantidade 10 --perfil agressivo
    python sistema_inteligencia_magna_completo.py benchmark --testes 40
    python sistema_inteligencia_magna_completo.py ciclo --concurso 3800
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from implementar_inteligencia_magna_forte import (
    InteligenciaMagnaForte,
    get_inteligencia_magna_forte,
    executar_ciclo_completo,
    decidir_autonomo,
    forja_automatica,
    benchmark_completo,
    explorar_sistema,
    auditar_sistema,
    testar_sistema
)


class SistemaCLI:
    """Interface de linha de comando do sistema."""
    
    VERSAO = "1.0.0"
    
    def __init__(self):
        self.parser = self._criar_parser()
        self.magna = None
    
    def _criar_parser(self) -> argparse.ArgumentParser:
        """Cria o parser de argumentos."""
        parser = argparse.ArgumentParser(
            description="Sistema Inteligência Magna Completo - Lotofácil",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog()
        )
        
        subparsers = parser.add_subparsers(
            title="comandos",
            dest="comando",
            required=True
        )
        
        # Comando: decidir
        self._adicionar_comando_decisao(subparsers)
        
        # Comando: forja
        self._adicionar_comando_forja(subparsers)
        
        # Comando: benchmark
        self._adicionar_comando_benchmark(subparsers)
        
        # Comando: explorar
        self._adicionar_comando_explorar(subparsers)
        
        # Comando: auditar
        self._adicionar_comando_auditar(subparsers)
        
        # Comando: ciclo
        self._adicionar_comando_ciclo(subparsers)
        
        # Comando: status
        self._adicionar_comando_status(subparsers)
        
        # Comando: testar
        self._adicionar_comando_testar(subparsers)
        
        return parser
    
    def _get_epilog(self) -> str:
        """Obtém o epílogo da ajuda."""
        return """
EXEMPLOS DE USO:

  # Decisão autônoma com 8 cartelas para 13 pontos
  python sistema_inteligencia_magna_completo.py decidir --quantidade 8 --alvo 13

  # Forja automática com telemetria e física
  python sistema_inteligencia_magna_completo.py forja --quantidade 10 --perfil agressivo

  # Benchmark walk-forward com 40 testes
  python sistema_inteligencia_magna_completo.py benchmark --testes 40 --janela 50

  # Exploração do sistema com 30 segundos
  python sistema_inteligencia_magna_completo.py explorar --tempo 30

  # Auditoria completa do sistema
  python sistema_inteligencia_magna_completo.py auditar

  # Ciclo completo para um concurso
  python sistema_inteligencia_magna_completo.py ciclo --concurso 3800

  # Status do sistema
  python sistema_inteligencia_magna_completo.py status

  # Testes completos
  python sistema_inteligencia_magna_completo.py testar
        """
    
    def _adicionar_comando_decisao(self, subparsers):
        """Adiciona o comando 'decidir'."""
        parser = subparsers.add_parser(
            "decidir",
            help="Toma uma decisão autônoma"
        )
        parser.add_argument(
            "--quantidade", "-q",
            type=int, default=8,
            help="Número de cartelas (padrão: 8)"
        )
        parser.add_argument(
            "--orcamento", "-o",
            type=float, default=100.0,
            help="Orçamento disponível (padrão: 100.0)"
        )
        parser.add_argument(
            "--alvo", "-a",
            type=int, choices=[13, 14, 15], default=13,
            help="Alvo de pontos (13, 14, 15)"
        )
        parser.add_argument(
            "--perfil", "-p",
            type=str, choices=["conservador", "equilibrado", "agressivo"],
            default="equilibrado",
            help="Perfil de risco"
        )
        parser.add_argument(
            "--modo", "-m",
            type=str, choices=["auto", "forja", "suprema"],
            default="auto",
            help="Modo de decisão"
        )
        parser.add_argument(
            "--salvar", "-s",
            action="store_true",
            help="Salvar no banco de dados"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--saida", "-O",
            type=str, default=None,
            help="Arquivo de saída JSON"
        )
    
    def _adicionar_comando_forja(self, subparsers):
        """Adiciona o comando 'forja'."""
        parser = subparsers.add_parser(
            "forja",
            help="Executa forja automática completa"
        )
        parser.add_argument(
            "--quantidade", "-q",
            type=int, default=8,
            help="Número de cartelas"
        )
        parser.add_argument(
            "--orcamento", "-o",
            type=float, default=100.0,
            help="Orçamento disponível"
        )
        parser.add_argument(
            "--alvo", "-a",
            type=int, choices=[13, 14, 15], default=13,
            help="Alvo de pontos"
        )
        parser.add_argument(
            "--perfil", "-p",
            type=str, choices=["conservador", "equilibrado", "agressivo"],
            default="equilibrado",
            help="Perfil de risco"
        )
        parser.add_argument(
            "--segundos",
            type=float, default=60.0,
            help="Tempo máximo para forja"
        )
        parser.add_argument(
            "--usar-inmet",
            action="store_true", default=True,
            help="Usar telemetria INMET"
        )
        parser.add_argument(
            "--usar-fisica",
            action="store_true", default=True,
            help="Usar física do ambiente"
        )
        parser.add_argument(
            "--salvar", "-s",
            action="store_true", default=True,
            help="Salvar no banco"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--saida", "-O",
            type=str, default=None,
            help="Arquivo de saída JSON"
        )
    
    def _adicionar_comando_benchmark(self, subparsers):
        """Adiciona o comando 'benchmark'."""
        parser = subparsers.add_parser(
            "benchmark",
            help="Executa benchmark walk-forward"
        )
        parser.add_argument(
            "--testes", "-t",
            type=int, default=40,
            help="Número de testes"
        )
        parser.add_argument(
            "--janela", "-j",
            type=int, default=50,
            help="Janela de treino"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--saida", "-O",
            type=str, default=None,
            help="Arquivo de saída JSON"
        )
    
    def _adicionar_comando_explorar(self, subparsers):
        """Adiciona o comando 'explorar'."""
        parser = subparsers.add_parser(
            "explorar",
            help="Explora mutações e estratégias"
        )
        parser.add_argument(
            "--tempo",
            type=float, default=60.0,
            help="Orçamento de tempo em segundos"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--saida", "-O",
            type=str, default=None,
            help="Arquivo de saída JSON"
        )
    
    def _adicionar_comando_auditar(self, subparsers):
        """Adiciona o comando 'auditar'."""
        parser = subparsers.add_parser(
            "auditar",
            help="Audita o sistema"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--saida", "-O",
            type=str, default=None,
            help="Arquivo de saída JSON"
        )
    
    def _adicionar_comando_ciclo(self, subparsers):
        """Adiciona o comando 'ciclo'."""
        parser = subparsers.add_parser(
            "ciclo",
            help="Executa ciclo completo"
        )
        parser.add_argument(
            "--concurso", "-c",
            type=int, default=None,
            help="Número do concurso (se None, usa último + 1)"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--saida", "-O",
            type=str, default=None,
            help="Arquivo de saída JSON"
        )
    
    def _adicionar_comando_status(self, subparsers):
        """Adiciona o comando 'status'."""
        parser = subparsers.add_parser(
            "status",
            help="Mostra status do sistema"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Saída em JSON"
        )
    
    def _adicionar_comando_testar(self, subparsers):
        """Adiciona o comando 'testar'."""
        parser = subparsers.add_parser(
            "testar",
            help="Executa testes completos"
        )
        parser.add_argument(
            "--db",
            type=str, default=None,
            help="Caminho para o banco de dados"
        )
    
    def executar(self, args: List[str] = None) -> int:
        """Executa o comando."""
        if args is None:
            args = sys.argv[1:]
        
        args_parsed = self.parser.parse_args(args)
        
        # Obtém a instância da Magna
        db_path = getattr(args_parsed, 'db', None)
        
        try:
            # Executa o comando
            resultado = self._executar_comando(args_parsed, db_path)
            
            # Salva em arquivo se solicitado
            if getattr(args_parsed, 'saida', None):
                self._salvar_resultado(resultado, args_parsed.saida)
            
            # Exibe resultado
            if getattr(args_parsed, 'json', False) or args_parsed.comando in ['status']:
                print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
            elif resultado and not getattr(args_parsed, 'json', False):
                self._exibir_resultado(resultado, args_parsed)
            
            return 0
            
        except Exception as e:
            print(f"[ERRO] {e}", file=sys.stderr)
            if getattr(args_parsed, 'json', False):
                print(json.dumps({"status": "erro", "erro": str(e)}))
            return 1
    
    def _executar_comando(self, args: argparse.Namespace, db_path: str) -> Dict[str, Any]:
        """Executa o comando específico."""
        comando = args.comando
        
        if comando == "decidir":
            return decidir_autonomo(
                quantidade=args.quantidade,
                orcamento=args.orcamento,
                alvo=args.alvo,
                perfil=args.perfil,
                db_path=db_path
            )
        
        elif comando == "forja":
            return forja_automatica(
                quantidade=args.quantidade,
                orcamento=args.orcamento,
                alvo=args.alvo,
                perfil=args.perfil,
                db_path=db_path
            )
        
        elif comando == "benchmark":
            return benchmark_completo(
                n_testes=args.testes,
                db_path=db_path
            )
        
        elif comando == "explorar":
            return explorar_sistema(
                orcamento_tempo=args.tempo,
                db_path=db_path
            )
        
        elif comando == "auditar":
            return auditar_sistema(db_path=db_path)
        
        elif comando == "ciclo":
            return executar_ciclo_completo(
                concurso=args.concurso,
                db_path=db_path
            )
        
        elif comando == "status":
            magna = get_inteligencia_magna_forte(db_path=db_path)
            return magna.get_status()
        
        elif comando == "testar":
            testar_sistema()
            return {"status": "ok", "msg": "Testes concluídos"}
        
        else:
            return {"status": "erro", "erro": f"Comando desconhecido: {comando}"}
    
    def _salvar_resultado(self, resultado: Dict, arquivo: str):
        """Salva o resultado em um arquivo."""
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)
        print(f"[INFO] Resultado salvo em: {arquivo}")
    
    def _exibir_resultado(self, resultado: Dict, args: argparse.Namespace):
        """Exibe o resultado de forma amigável."""
        comando = args.comando
        
        if comando == "decidir":
            self._exibir_decisao(resultado)
        elif comando == "forja":
            self._exibir_forja(resultado)
        elif comando == "benchmark":
            self._exibir_benchmark(resultado)
        elif comando == "explorar":
            self._exibir_exploracao(resultado)
        elif comando == "auditar":
            self._exibir_auditoria(resultado)
        elif comando == "ciclo":
            self._exibir_ciclo(resultado)
        elif comando == "status":
            self._exibir_status(resultado)
        else:
            print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
    
    def _exibir_decisao(self, resultado: Dict):
        """Exibe o resultado da decisão."""
        print("\n" + "=" * 80)
        print("DECISÃO AUTÔNOMA - INTELIGÊNCIA MAGNA FORTE")
        print("=" * 80)
        
        print(f"\n📊 STATUS: {resultado.get('status', '?')}")
        print(f"🎯 ESTRATÉGIA: {resultado.get('estrategia', '?')}")
        print(f"💰 ORÇAMENTO: R$ {resultado.get('orcamento', 0):.2f}")
        print(f"📝 CARTELAS: {resultado.get('n_cartelas', 0)}")
        print(f"🎲 ALVO: {resultado.get('alvo', 13)} pontos")
        print(f"👤 PERFIL: {resultado.get('perfil', 'equilibrado')}")
        
        # Exibe ambiente
        ambiente = resultado.get('ambiente', {})
        if ambiente:
            print(f"\n🌍 AMBIENTE:")
            local = ambiente.get('local', {})
            print(f"   Local: {local.get('cidade_uf', '?')}")
            telemetria = ambiente.get('telemetria', {})
            print(f"   Telemetria: {telemetria.get('status', '?')}")
            if telemetria.get('status') == 'ok':
                print(f"   Temperatura: {telemetria.get('temperatura', '?')}K")
                print(f"   Pressão: {telemetria.get('pressao', '?')} atm")
                print(f"   Umidade: {telemetria.get('umidade', '?')}%")
        
        # Exibe cartelas
        cartelas = resultado.get('cartelas', [])
        if cartelas:
            print(f"\n🎫 CARTELAS GERADAS:")
            for i, cartela in enumerate(cartelas[:5], 1):  # Mostra até 5
                dezenas = cartela.get('dezenas', [])
                print(f"   Cartela {i}: {sorted(dezenas)}")
            if len(cartelas) > 5:
                print(f"   ... e mais {len(cartelas) - 5} cartelas")
        
        # Exibe análise
        analise = resultado.get('analise', {})
        if analise:
            print(f"\n📈 ANÁLISE:")
            print(f"   P(≥13): {analise.get('p_melhor_13_mais', 0)*100:.4f}%")
            print(f"   P(≥14): {analise.get('p_melhor_14_mais', 0)*100:.6f}%")
            print(f"   EV: R$ {analise.get('ev_lote', 0):.2f}")
        
        print("\n" + "=" * 80)
    
    def _exibir_forja(self, resultado: Dict):
        """Exibe o resultado da forja."""
        print("\n" + "=" * 80)
        print("FORJA AUTOMÁTICA COMPLETA")
        print("=" * 80)
        
        print(f"\n📊 STATUS: {resultado.get('status', '?')}")
        print(f"🎯 ESTRATÉGIA: {resultado.get('estrategia', '?')}")
        print(f"💰 CUSTO: R$ {resultado.get('custo', 0):.2f}")
        print(f"📝 CARTELAS: {resultado.get('n_cartelas', 0)}")
        
        # Exibe ambiente
        ambiente = resultado.get('ambiente', {})
        if ambiente:
            print(f"\n🌍 AMBIENTE:")
            local = ambiente.get('local', {})
            print(f"   Local: {local.get('cidade_uf', '?')}")
            telemetria = ambiente.get('telemetria', {})
            print(f"   Telemetria: {telemetria.get('status', '?')}")
        
        # Exibe forja
        forja = resultado.get('decisao', {})
        if forja:
            print(f"\n🔨 FORJA:")
            print(f"   Pool: {forja.get('pool_elite', '?')}")
            print(f"   Garantia: {forja.get('garantia', '?')}")
        
        print("\n" + "=" * 80)
    
    def _exibir_benchmark(self, resultado: Dict):
        """Exibe o resultado do benchmark."""
        print("\n" + "=" * 80)
        print("BENCHMARK WALK-FORWARD")
        print("=" * 80)
        
        print(f"\n📊 STATUS: {resultado.get('status', '?')}")
        print(f"📝 TESTES: {resultado.get('n_testes', 0)}")
        print(f"📏 JANELA: {resultado.get('janela', 0)}")
        
        # Exibe estimativas
        estimativas = resultado.get('estimativas', {})
        if estimativas:
            print(f"\n📈 ESTRATÉGIAS:")
            for nome, dados in estimativas.items():
                print(f"   {nome}:")
                print(f"      Média de acertos: {dados.get('media_acertos', 0):.4f}")
                print(f"      Taxa ≥13: {dados.get('taxa_13_mais', 0)*100:.4f}%")
                print(f"      Veredito: {dados.get('veredito', '?')}")
        
        # Exibe quarentena
        quarentena = resultado.get('quarentena', [])
        if quarentena:
            print(f"\n⚠️  QUARENTENA: {', '.join(quarentena)}")
        
        print("\n" + "=" * 80)
    
    def _exibir_exploracao(self, resultado: Dict):
        """Exibe o resultado da exploração."""
        print("\n" + "=" * 80)
        print("EXPLORAÇÃO DO SISTEMA")
        print("=" * 80)
        
        print(f"\n📊 STATUS: {resultado.get('status', '?')}")
        print(f"⏱️  TEMPO: {resultado.get('tempo_total', 0)}s")
        
        # Exibe exploração
        exploracao = resultado.get('exploracao', {})
        if exploracao:
            print(f"\n🔍 EXPLORAÇÃO:")
            print(f"   Status: {exploracao.get('status', '?')}")
            print(f"   Melhoras: {exploracao.get('n_melhoraram', 0)}")
        
        # Exibe benchmark
        benchmark = resultado.get('benchmark', {})
        if benchmark:
            print(f"\n📈 BENCHMARK:")
            print(f"   Status: {benchmark.get('status', '?')}")
        
        # Exibe medição
        medicao = resultado.get('medicao', {})
        if medicao:
            print(f"\n📊 MEDIÇÃO:")
            print(f"   Média de acertos: {medicao.get('media_acertos', 0):.4f}")
            print(f"   Taxa ≥13: {medicao.get('taxa_13_mais', 0)*100:.4f}%")
        
        print("\n" + "=" * 80)
    
    def _exibir_auditoria(self, resultado: Dict):
        """Exibe o resultado da auditoria."""
        print("\n" + "=" * 80)
        print("AUDITORIA DO SISTEMA")
        print("=" * 80)
        
        print(f"\n📊 STATUS: {resultado.get('status', '?')}")
        
        # Exibe magna base
        magna_base = resultado.get('magna_base', {})
        if magna_base:
            print(f"\n🧠 MAGNA BASE:")
            print(f"   O que aprende: {len(magna_base.get('o_que_aprende', []))} itens")
            print(f"   Como aprende: {magna_base.get('como_aprende', '?')[:100]}...")
        
        # Exibe banco de dados
        banco = resultado.get('banco_dados', {})
        if banco:
            print(f"\n🗃️  BANCO DE DADOS:")
            print(f"   Decisões: {banco.get('n_decisoes', 0)}")
            print(f"   Conferidas: {banco.get('n_conferidas', 0)}")
        
        # Exibe telemetria
        telemetria = resultado.get('telemetria', {})
        if telemetria:
            print(f"\n🌤️  TELEMETRIA:")
            print(f"   Registros: {telemetria.get('n_registros', 0)}")
            print(f"   Status: {telemetria.get('status', '?')}")
        
        # Exibe física
        fisica = resultado.get('fisica', {})
        if fisica:
            print(f"\n⚛️  FÍSICA:")
            print(f"   Bolas medidas: {fisica.get('bolas_medidas', 0)}")
            print(f"   Ambientes: {fisica.get('ambientes_registrados', 0)}")
        
        # Exibe quarentena
        quarentena = resultado.get('quarentena', [])
        if quarentena:
            print(f"\n⚠️  QUARENTENA: {', '.join(quarentena)}")
        
        print("\n" + "=" * 80)
    
    def _exibir_ciclo(self, resultado: Dict):
        """Exibe o resultado do ciclo."""
        print("\n" + "=" * 80)
        print("CICLO COMPLETO")
        print("=" * 80)
        
        print(f"\n📊 STATUS: {resultado.get('status', '?')}")
        print(f"🎲 CONCURSO: {resultado.get('concurso', 0)}")
        
        # Exibe ambiente
        ambiente = resultado.get('ambiente', {})
        if ambiente:
            print(f"\n🌍 AMBIENTE:")
            local = ambiente.get('local', {})
            print(f"   Local: {local.get('cidade_uf', '?')}")
        
        # Exibe decisão
        decisao = resultado.get('decisao', {})
        if decisao:
            print(f"\n🎯 DECISÃO:")
            print(f"   Estratégia: {decisao.get('estrategia', '?')}")
            print(f"   Cartelas: {decisao.get('n_cartelas', 0)}")
        
        # Exibe aprendizado
        aprendizado = resultado.get('aprendizado', {})
        if aprendizado:
            print(f"\n📚 APRENDIZADO:")
            print(f"   Status: {aprendizado.get('status', '?')}")
        
        # Exibe recalibração
        recalibracao = resultado.get('recalibracao', False)
        print(f"\n🔄 RECALIBRAÇÃO: {'Sim' if recalibracao else 'Não'}")
        
        print("\n" + "=" * 80)
    
    def _exibir_status(self, resultado: Dict):
        """Exibe o status do sistema."""
        print("\n" + "=" * 80)
        print("STATUS DO SISTEMA - INTELIGÊNCIA MAGNA FORTE")
        print("=" * 80)
        
        print(f"\n📋 VERSÃO: {resultado.get('versao', '?')}")
        print(f"📊 ESTADO: {resultado.get('estado', '?')}")
        print(f"✅ TREINADO: {resultado.get('treinado', False)}")
        print(f"📝 N CARTELAS: {resultado.get('n_cartelas', 0)}")
        print(f"🗃️  BANCO: {resultado.get('db_path', '?')}")
        
        # Exibe magna base
        magna_base = resultado.get('magna_base', {})
        if magna_base:
            print(f"\n🧠 MAGNA BASE:")
            print(f"   Total de concursos: {magna_base.get('total_concursos', 0)}")
            print(f"   Última execução: {magna_base.get('ultima_exec', '?')}")
        
        # Exibe telemetria
        telemetria = resultado.get('telemetria', {})
        if telemetria:
            print(f"\n🌤️  TELEMETRIA:")
            print(f"   Registros: {telemetria.get('n_registros', 0)}")
        
        # Exibe física
        fisica = resultado.get('fisica', {})
        if fisica:
            print(f"\n⚛️  FÍSICA:")
            print(f"   Bolas medidas: {fisica.get('bolas_medidas', 0)}")
            print(f"   Dados reais: {fisica.get('tem_dados_reais', False)}")
        
        print("\n" + "=" * 80)


def main():
    """Função principal."""
    cli = SistemaCLI()
    return cli.executar()


if __name__ == "__main__":
    sys.exit(main())
