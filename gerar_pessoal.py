#!/usr/bin/env python3
"""
SISTEMA ÚNICO PESSOAL — MAGNA SUPREMA v11
Uso próprio em potência máxima, sem erros — evoluções completas.

Evoluções v11:
- Aprender: EWC continual, meta por regime, clustering adaptativo K=2..4 silhouette, balança 0.001g
- Decidir: perfil risco pessoal conservador/equilibrado/agressivo, MCTS pool UCT 800 iterações,
           multi-rota 60/30/10, utilidade esperada com prêmios reais médios
- Julgar: juiz 8 critérios + adversarial fraquezas comuns + NIST chi2 + p-value ratio + juiz que aprende
- Entender: explainability por dezena/cartela, chat "por que 22?", fingerprint SHA256 anti-repetição pessoal
- Verificar: backtest walk-forward 50 concursos, binomial significância, curva aprendizado mm5

Único gerador: mesma pipeline para decisão única e 3 âncoras 01/02/03.

Uso:
  python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 13 --perfil conservador --modo suprema
  python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 14 --perfil equilibrado --modo suprema --mcts --multi-rota
  python gerar_pessoal.py --qtd 16 --orcamento 200 --alvo 15 --perfil agressivo --modo suprema --segundos 60
  python gerar_pessoal.py --ancoras --perfil conservador
"""
import argparse
import json
import sys
from core.cerebro_ia import InteligenciaMagna

def main():
    parser = argparse.ArgumentParser(description="Magna Suprema v11 — Sistema único pessoal potência máxima evoluído")
    parser.add_argument("--qtd", type=int, default=8, help="Quantidade de cartelas (1-30)")
    parser.add_argument("--orcamento", type=float, default=100.0, help="Orçamento R$ (ex: 100)")
    parser.add_argument("--alvo", type=int, default=13, choices=[13,14,15], help="Alvo 13/14/15")
    parser.add_argument("--perfil", type=str, default="equilibrado", choices=["conservador","equilibrado","agressivo"], help="Perfil risco pessoal")
    parser.add_argument("--modo", type=str, default="suprema", choices=["auto","forja","suprema"], help="Modo: auto/forja/suprema")
    parser.add_argument("--segundos", type=float, default=60.0, help="Segundos forja suprema (total, ex: 60)")
    parser.add_argument("--tentativas", type=int, default=2, help="Tentativas juiz (1-3)")
    parser.add_argument("--mcts", action="store_true", help="Usar MCTS pool UCT")
    parser.add_argument("--multi-rota", action="store_true", help="Usar alocação multi-rota 60/30/10")
    parser.add_argument("--ancoras", action="store_true", help="Gerar 3 âncoras 01/02/03 (mesmo processo supremo)")
    parser.add_argument("--salvar", action="store_true", help="Salvar no banco")
    parser.add_argument("--chat", type=str, default="", help="Pergunta para chat Magna ex: 'por que 22?'")
    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║   MAGNA SUPREMA v11 — SISTEMA ÚNICO PESSOAL EVOLUÍDO           ║
║   Potência máxima, sem erros, uso próprio                      ║
║   Qtd={args.qtd} Orçamento=R${args.orcamento:.2f} Alvo={args.alvo} Perfil={args.perfil} Modo={args.modo}
║   Segundos={args.segundos} Tentativas={args.tentativas} MCTS={args.mcts} MultiRota={args.multi_rota}
║   { "ÂNCORAS 01/02/03" if args.ancoras else "DECISÃO ÚNICA" }
╚════════════════════════════════════════════════════════════════╝
""")

    magna = InteligenciaMagna(n_cartelas=args.qtd)
    print(f"[SISTEMA] {magna.n} concursos carregados, treinando em potência máxima v11...")
    magna.treinar()

    # Regime adaptativo
    try:
        from core.magna_suprema import DetectorRegime
        det = DetectorRegime(magna.matriz)
        regime = det.detectar_adaptativo(janela=100)
        print(f"[REGIME ADAPTATIVO] k_otimo={regime.get('k_otimo')} sil={regime.get('silhouette')} atual={regime.get('regime_atual')} — {regime.get('descricao')}")
    except Exception as e:
        regime = magna.detectar_regime_atual()
        print(f"[REGIME] Atual={regime.get('regime_atual')} — {regime.get('descricao')} (fallback: {e})")

    # Perfil + multi-rota
    try:
        from core.magna_suprema import PerfilRiscoPessoal, AlocadorMultiRota
        perfil_obj = PerfilRiscoPessoal(args.perfil)
        print(f"[PERFIL] {args.perfil}: {perfil_obj.relatorio()['descricao']}")
        aloc_multi = AlocadorMultiRota().alocar(args.orcamento, args.qtd, args.perfil)
        print(f"[MULTI-ROTA] {aloc_multi.get('recomendacao')} — {aloc_multi.get('explicacao')}")
    except Exception as e:
        print(f"[PERFIL] Erro: {e}")

    # Alocação
    aloc = magna.alocar_orcamento_inteligente(args.orcamento, args.qtd, args.alvo)
    print(f"[ORÇAMENTO] {aloc.get('recomendacao')} — R${aloc.get('total_custo')} {aloc.get('total_cartelas')} cartelas")

    # Decisão
    if args.ancoras:
        print("\n[GERANDO] 3 âncoras 01/02/03 via MESMO processo supremo...")
        resultado = magna.decidir_ancoradas_01_02_03(
            registrar=args.salvar,
            orcamento=args.orcamento,
            perfil=args.perfil,
        )
    elif args.modo == "suprema":
        print(f"\n[GERANDO] Suprema v11 {args.qtd} cartelas alvo {args.alvo} perfil {args.perfil} {args.segundos}s MCTS={args.mcts}...")
        resultado = magna.decidir_suprema(
            quantidade=args.qtd,
            orcamento=args.orcamento,
            alvo=args.alvo,
            modo="suprema",
            perfil=args.perfil,
            segundos_forja=args.segundos,
            usar_mcts=args.mcts,
            usar_multi_rota=args.multi_rota,
            tentativas_juiz=args.tentativas,
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
    analise = resultado.get('analise', {})
    print(f"[ANÁLISE] P≥13={analise.get('p_melhor_13_mais',0)*100:.4f}% 1 em {1/max(analise.get('p_melhor_13_mais',1e-12),1e-12):.1f}")
    print(f"         P≥14={analise.get('p_melhor_14_mais',0)*100:.6f}% 1 em {1/max(analise.get('p_melhor_14_mais',1e-12),1e-12):.1f} EV R${analise.get('ev_lote',0):.2f}")

    if "julgamento" in resultado:
        j = resultado['julgamento']
        print(f"[JUIZ 8 CRITÉRIOS] {j.get('veredito')} nota {j.get('nota')} reprovados {j.get('reprovados')}")
    if "julgamento_adversarial" in resultado:
        ja = resultado['julgamento_adversarial']
        print(f"[JUIZ ADVERSARIAL] {ja.get('veredito')} fraquezas {ja.get('fraquezas')} communs {ja.get('comuns')}")
    if "teste_nist" in resultado:
        nist = resultado['teste_nist']
        print(f"[NIST] {nist.get('veredito')} chi2 {nist.get('chi2')} gap {nist.get('gap_medio')}")
    if "p_value_random" in resultado:
        pv = resultado['p_value_random']
        print(f"[P-VALUE RANDOM] {pv.get('veredito')} ratio {pv.get('ratio')} p_random {pv.get('p_random')}")
    if "backtest_lote" in resultado:
        bt = resultado['backtest_lote']
        print(f"[BACKTEST 50] média {bt.get('media_acertos_lote')} taxa13+ {bt.get('taxa_13_mais')} vs baseline {bt.get('baseline_media')}")
    if "curva_aprendizado" in resultado:
        curva = resultado['curva_aprendizado']
        print(f"[CURVA] tendência {curva.get('tendencia')} slope {curva.get('slope')}")
    if "utilidade_esperada" in resultado:
        util = resultado['utilidade_esperada']
        print(f"[UTILIDADE] EV real R${util.get('ev_real_premios_medios')} ROI {util.get('roi')}% util_perfil {util.get('utilidade_perfil')}")
    if "fingerprint" in resultado:
        fp = resultado['fingerprint']
        print(f"[FINGERPRINT] {fp.get('fingerprint')} hashes {fp.get('total_hashes') if 'total_hashes' in fp else ''}")
    if "verificacao_exaustiva" in resultado:
        ver = resultado['verificacao_exaustiva']
        print(f"[VERIFICAÇÃO] {ver.get('honestidade') or ver.get('p13_exata')}")

    print("\n[CARTELAS]")
    for i, c in enumerate(resultado["cartelas"], 1):
        exp = c.get('explicacao') or c.get('explicacao_llm') or {}
        print(f"{i:02d}: {c['dezenas']} — soma {c.get('soma')} pares {c.get('pares')} score {c.get('score_total')}")
        if exp:
            print(f"    → {exp.get('explicacao') or exp.get('motivo','')[:120]}")

    print(f"\n[POOL ELITE] {resultado['pool_elite']}")
    print(f"[JUSTIFICATIVA] {resultado.get('justificativa_magna','')[:500]}")

    # Chat se pedido
    if args.chat:
        try:
            from core.magna_suprema import ExplainabilityMagna, ChatMagna
            exp = ExplainabilityMagna()
            chat = ChatMagna(exp)
            contexto = {
                "vf": magna._vetor_combinado(),
                "fontes": magna._fontes_assimiladas_magna()[0],
                "votos": magna._fontes_assimiladas_magna()[1]["votos"],
                "cartelas": [c["dezenas"] for c in resultado["cartelas"]],
                "pool": resultado["pool_elite"],
                "analise": analise,
                "regime": regime,
            }
            resposta = chat.responder(args.chat, contexto)
            print(f"\n[CHAT MAGNA] Q: {args.chat}\nA: {resposta}")
        except Exception as e:
            print(f"[CHAT] Erro: {e}")

    # Salva JSON
    out_path = f"lote_supremo_v11_{args.alvo}_{args.qtd}_{int(args.orcamento)}_{args.perfil}.json"
    with open(out_path, "w") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"\n[ARQUIVO] Lote salvo em {out_path}")

if __name__ == "__main__":
    main()
