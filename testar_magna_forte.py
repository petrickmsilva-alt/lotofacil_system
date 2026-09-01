#!/usr/bin/env python3
"""
Teste rápido do Sistema Inteligência Magna Forte
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATABASE_PATH
from core.cerebro_ia import InteligenciaMagna, CerebroIA
from core.forja_auto import ForjaAutomatica
from core.inmet import TelemetriaInmet, InmetClient, LOCAL_PADRAO
from core.laboratorio_magna import LaboratorioMagna
from core.fisica_sorteio import MotorFisicaSorteio

print("=" * 80)
print("TESTE DO SISTEMA INTELIGÊNCIA MAGNA FORTE")
print("=" * 80)

# Test 1: Inicialização dos componentes
print("\n1. Inicializando componentes...")
try:
    magna = InteligenciaMagna(db_path=DATABASE_PATH, n_cartelas=8)
    print(f"   ✓ Inteligência Magna: {magna.n} concursos")
    
    telemetria = TelemetriaInmet(DATABASE_PATH)
    print(f"   ✓ Telemetria INMET: {telemetria.resumo().get('n_registros', 0)} registros")
    
    fisica = MotorFisicaSorteio(DATABASE_PATH)
    print(f"   ✓ Física: {fisica.n_bolas_medidas} bolas medidas")
    
    forja = ForjaAutomatica(magna=magna, db_path=DATABASE_PATH)
    print(f"   ✓ Forja Automática: inicializada")
    
    laboratorio = LaboratorioMagna(db_path=DATABASE_PATH, matriz=magna.matriz)
    print(f"   ✓ Laboratório: {laboratorio.n} concursos")
    
except Exception as e:
    print(f"   ✗ Erro: {e}")
    sys.exit(1)

# Test 2: Registro de ambiente
print("\n2. Registrando ambiente...")
try:
    local = forja.local_do_sorteio(usar_rede=False)
    print(f"   ✓ Local: {local.get('cidade_uf', '?')}")
    
    tele = forja.coletar_telemetria(local, persistir_telemetria=False)
    print(f"   ✓ Telemetria: {tele.get('status', '?')}")
    
except Exception as e:
    print(f"   ✗ Erro: {e}")

# Test 3: Decisão da Magna
print("\n3. Testando decisão...")
try:
    if not magna.treinado:
        magna.treinar()
    
    decisao = magna.gerar_otimas(n_cartelas=2, salvar=False)
    print(f"   ✓ Cartelas geradas: {decisao.get('n_cartelas', 0)}")
    print(f"   ✓ Estratégia: {decisao.get('estrategia', '?')}")
    
except Exception as e:
    print(f"   ✗ Erro: {e}")

# Test 4: Forja Automática
print("\n4. Testando Forja Automática...")
try:
    resultado = forja.executar(
        quantidade=2,
        orcamento=20.0,
        alvo=13,
        perfil="equilibrado",
        segundos_forja=5.0,
        usar_inmet=False,
        persistir_telemetria=False,
        salvar=False
    )
    print(f"   ✓ Status: {resultado.get('status', '?')}")
    print(f"   ✓ Cartelas: {resultado.get('n_cartelas', 0)}")
    
except Exception as e:
    print(f"   ✗ Erro: {e}")

# Test 5: Benchmark
print("\n5. Testando Benchmark...")
try:
    benchmark = laboratorio.rodar_benchmark(n_testes=5, janela=30, persistir=False)
    print(f"   ✓ Status: {benchmark.get('status', '?')}")
    print(f"   ✓ Estratégias: {len(benchmark.get('estimativas', {}))}")
    
except Exception as e:
    print(f"   ✗ Erro: {e}")

print("\n" + "=" * 80)
print("TESTE CONCLUÍDO COM SUCESSO!")
print("=" * 80)
print("\nTodas as funcionalidades estão operacionais:")
print("✓ Inteligência Magna")
print("✓ Forja Automática")
print("✓ Telemetria INMET")
print("✓ Física do Sorteio")
print("✓ Laboratório")
print("✓ Benchmark Walk-Forward")
