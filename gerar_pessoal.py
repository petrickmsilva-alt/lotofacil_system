#!/usr/bin/env python3
"""
SISTEMA ÚNICO PESSOAL — MAGNA SUPREMA v10
Uso próprio em potência máxima, sem erros.

Gera cartelas para 13/14/15 com tudo que é possível e impossível dentro da honestidade matemática:
- 14 motores + 15 oráculos + física + espectro + informação
- Pool elite extraordinário MotorGrafos vf+diversidade
- Forja suprema 60s 7 seeds k=7 25 candidatas
- Detector de regime K-means, memória vetorial com atenção, juiz 8 critérios, verificador exaustivo, alocador orçamento, aprendizado Bayesiano momentum

Uso:
  python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 13 --modo suprema
  python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 14 --modo suprema
  python gerar_pessoal.py --qtd 16 --orcamento 200 --alvo 15 --modo suprema
"""
import argparse
import json
import sys
from core.cerebro_ia import InteligenciaMagna

def main():
    parser = argparse.ArgumentParser(description="Magna Suprema v10 — Sistema único pessoal potência máxima")
    parser.add_argument("--qtd", type=int, default=8, help="Quantidade de cartelas (1-30)")
    parser.add_argument("--orcamento", type=float, default=100.0, help="Orçamento R$ (ex: 100)")
    parser.add_argument("--alvo", type=int, default=13, choices=[13,14,15], help="Alvo 13/14/15")
    parser.add_argument("--modo", type=str, default="suprema", choices=["auto","forja","suprema"], help="Modo: auto/forja/suprema")
    parser.add_argument("--salvar", action="store_true", help="Salvar no banco")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════╗
║   MAGNA SUPREMA v10 — SISTEMA ÚNICO PESSOAL          ║
║   Potência máxima, sem erros, uso próprio            ║
║   Qtd={args.qtd} Orçamento=R${args.orcamento:.2f} Alvo={args.alvo} Modo={args.modo}
╚══════════════════════════════════════════════════════╝
""")

    magna = InteligenciaMagna(n_cartelas=args.qtd)
    print(f"[SISTEMA] {magna.n} concursos carregados, treinando em potência máxima...")
    magna.treinar()

    # Detecta regime
    regime = magna.detectar_regime_atual()
    print(f"[REGIME] Atual={regime.get('regime_atual')} — {regime.get('descricao')}")

    # Alocação
    aloc = magna.alocar_orcamento_inteligente(args.orcamento, args.qtd, args.alvo)
    print(f"[ORÇAMENTO] {aloc.get('recomendacao')} — R${aloc.get('total_custo')} {aloc.get('total_cartelas')} cartelas")

    # Decisão suprema
    if args.modo == "suprema":
        resultado = magna.decidir_suprema(
            quantidade=args.qtd,
            orcamento=args.orcamento,
            alvo=args.alvo,
            modo="suprema",
            registrar=args.salvar,
        )
    else:
        resultado = magna.decidir_e_gerar(
            quantidade=args.qtd,
            orcamento=args.orcamento,
            alvo=args.alvo,
            modo=args.modo,
            registrar=args.salvar,
        )

    print(f"\n[DECISÃO] {resultado['estrategia']} — {resultado['n_cartelas']} cartelas R${resultado['custo']}")
    print(f"[ANÁLISE] P≥13={resultado['analise']['p_melhor_13_mais']*100:.4f}% 1 em {1/resultado['analise']['p_melhor_13_mais']:.1f}")
    print(f"         P≥14={resultado['analise']['p_melhor_14_mais']*100:.6f}% 1 em {1/resultado['analise']['p_melhor_14_mais']:.1f} EV R${resultado['analise']['ev_lote']:.2f}")
    if "julgamento" in resultado:
        print(f"[JUIZ] {resultado['julgamento']['veredito']} nota {resultado['julgamento']['nota']} reprovados {resultado['julgamento']['reprovados']}")
    if "verificacao_exaustiva" in resultado:
        print(f"[VERIFICAÇÃO] {resultado['verificacao_exaustiva'].get('honestidade')}")

    print("\n[CARTELAS]")
    for i, c in enumerate(resultado["cartelas"], 1):
        print(f"{i:02d}: {c['dezenas']} — soma {c['soma']} pares {c['pares']} score {c['score_total']}")

    print(f"\n[POOL ELITE] {resultado['pool_elite']}")
    print(f"[JUSTIFICATIVA] {resultado.get('justificativa_magna','')}")

    # Salva JSON
    out_path = f"lote_supremo_{args.alvo}_{args.qtd}_{int(args.orcamento)}.json"
    with open(out_path, "w") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"\n[ARQUIVO] Lote salvo em {out_path}")

if __name__ == "__main__":
    main()
