#!/usr/bin/env python3
"""
SISTEMA ÚNICO PESSOAL — MAGNA SUPREMA v11
Uso próprio em potência máxima, sem erros — evoluções completas.

Evoluções v11:
- Aprender: EWC continual, meta por regime, clustering adaptativo K=2..4 silhouette, balança 0.001g
- Decidir: perfil risco pessoal conservador/equilibrado/agressivo, MCTS pool UCT 800 iterações,
           multi-rota 60/30/10, utilidade esperada com prêmios reais médios
- Julgar: juiz 9 critérios + adversarial fraquezas comuns + NIST chi2 + p-value ratio + juiz que aprende
- Entender: explainability por dezena/cartela, chat "por que 22?", fingerprint SHA256 anti-repetição pessoal
- Verificar: backtest walk-forward 50 concursos, binomial significância, curva aprendizado mm5

Único gerador: mesma pipeline para decisão única, forja suprema e forja auto.

Uso:
  python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 13 --perfil conservador --modo suprema
  python gerar_pessoal.py --qtd 8 --orcamento 100 --alvo 14 --perfil equilibrado --modo suprema --mcts --multi-rota
  python gerar_pessoal.py --qtd 16 --orcamento 200 --alvo 15 --perfil agressivo --modo suprema --segundos 60
  python gerar_pessoal.py --auto --perfil conservador
  python gerar_pessoal.py --auto --sem-inmet --qtd 4
  python gerar_pessoal.py --qtd 8 --temp 19.5 --pressao 0.912 --umidade 42
  python gerar_pessoal.py --assimilar --calibrar-pesos --conhecimento --qtd 1
  python gerar_pessoal.py --memorizar-abertura "3774:07" --conhecimento

Evolução v11.4 (Acervo de conhecimento único):
- O antigo painel/módulo de padrões de abertura foi absorvido pela Magna:
  `AcervoAberturaMagna` vive em core/cerebro_ia.py e é a fonte `abertura`
- A Magna lê a base histórica inteira no boot (nada de cold start) e memoriza
  em magna_conhecimento / magna_memoria; cada conferência reassimila e julga
- Peso da fonte no consenso é medido, não prometido: walk-forward fora-da-amostra
  decide (RUÍDO → vetor atenuado 0,5; abertura nunca muda a hipergeométrica)

Evolução v11.2 (Clima Físico):
- Fonte de clima assimilada à Magna (peso 6%, shrinkage 50/50, teto ±10%)
- 3 testes matemáticos: ímpares×pressão, soma×umidade, frequência×temperatura
- Auto-auditoria walk-forward escala a confiança da fonte (0.5-1.0×)
- Aprendizado contínuo: cada sorteio com clima recalibra os testes
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
    # v11.7 — forja automática com telemetria INMET por local do sorteio
    parser.add_argument("--auto", action="store_true",
                        help="Forja automática: local do sorteio → telemetria "
                             "INMET → forja suprema")
    parser.add_argument("--sem-inmet", action="store_true",
                        help="Com --auto: não consulta o INMET (clima neutro)")
    parser.add_argument("--salvar", action="store_true", help="Salvar no banco")
    parser.add_argument("--chat", type=str, default="", help="Pergunta para chat Magna ex: 'por que 22?'")
    # v11.4 — acervo de conhecimento (órgão da própria Magna, sem módulo paralelo)
    parser.add_argument("--assimilar", action="store_true",
                        help="A Magna relê a base histórica inteira e memoriza o "
                             "que aprendeu antes de gerar (abertura + posterior)")
    parser.add_argument("--calibrar-pesos", action="store_true",
                        help="Com --assimilar: recalibra o peso das 8 fontes do "
                             "consenso em walk-forward fora-da-amostra")
    parser.add_argument("--limite-calibracao", type=float, default=90.0,
                        help="Orçamento de segundos da calibração walk-forward")
    parser.add_argument("--conhecimento", action="store_true",
                        help="Mostra o acervo (o que a Magna já sabe) e o placar "
                             "walk-forward; combinável com as opções acima")
    parser.add_argument("--memorizar-abertura", type=str, default="",
                        help="Memoriza a abertura real de um concurso: "
                             "'3774:07' (só a 1ª bola) ou '3774:07 01 22 ...' "
                             "(as 15 bolas na ordem extraída)")
    # v11.2 — clima do sorteio (boletim do dia)
    parser.add_argument("--temp", type=float, default=None,
                        help="Temperatura °C do próximo sorteio (ex: 19.5)")
    parser.add_argument("--pressao", type=float, default=None,
                        help="Pressão atm do próximo sorteio (ex: 0.912)")
    parser.add_argument("--umidade", type=float, default=None,
                        help="Umidade %% do próximo sorteio (ex: 42)")
    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║   MAGNA SUPREMA v11.7 — SISTEMA ÚNICO PESSOAL EVOLUÍDO         ║
║   Potência máxima, sem erros, uso próprio                      ║
║   Qtd={args.qtd} Orçamento=R${args.orcamento:.2f} Alvo={args.alvo} Perfil={args.perfil} Modo={args.modo}
║   Segundos={args.segundos} Tentativas={args.tentativas} MCTS={args.mcts} MultiRota={args.multi_rota}
║   {"FORJA AUTO · INMET" if args.auto and not args.sem_inmet else "FORJA AUTO · CLIMA NEUTRO" if args.auto else "DECISÃO ÚNICA"}
╚════════════════════════════════════════════════════════════════╝
""")

    magna = InteligenciaMagna(n_cartelas=args.qtd)
    print(f"[SISTEMA] {magna.n} concursos carregados, treinando em potência máxima v11.4...")
    magna.treinar()

    # ── v11.4 — ACERVO DE CONHECIMENTO ────────────────────────────────────
    # A Magna aprende da própria base histórica (os 3.700+ concursos que já
    # estão no banco) e memoriza o resultado: quem abre, com que frequência,
    # o que está em sequência, o placar walk-forward das regras populares e o
    # posterior do próximo início. Não é módulo à parte: é a fonte `abertura`
    # do consenso, julgada a cada conferência.
    if args.memorizar_abertura:
        try:
            concurso_txt, _, resto = args.memorizar_abertura.replace("=", " ")                 .replace(":", " ").partition(" ")
            concurso = int(concurso_txt)
            bolas = [int(d) for d in resto.replace(",", " ").split() if d.strip()]
            if len(bolas) == 1:
                res_ab = magna.aprender_abertura_medida(concurso, bolas[0],
                                                         origem="cli")
            else:
                res_ab = magna.aprender_ordem_sorteio(concurso, bolas)
            print(f"[ACERVO] concurso {concurso} memorizado: {res_ab.get('status')} "
                  f"· abertura real {bolas[0]:02d}")
        except (ValueError, IndexError) as e:
            print(f"[ACERVO] entrada inválida em --memorizar-abertura: {e}")
            sys.exit(2)

    if args.assimilar or args.conhecimento:
        try:
            if args.assimilar:
                print(f"[ACERVO] Relendo a base histórica inteira "
                      f"(calibrar pesos = {args.calibrar_pesos})...")
                res = magna.assimilar_acervo(
                    forcar=True, calibrar_fontes=args.calibrar_pesos,
                    limite_segundos=args.limite_calibracao)
                print(f"[ACERVO] {res.get('status')} até o concurso "
                      f"{res.get('aprendido_ate')} · veredito "
                      f"{res.get('veredito')} · fator "
                      f"{res.get('fator_confianca')}")
                if res.get("calibracao"):
                    cal = res["calibracao"]
                    print(f"[ACERVO] calibração: {cal.get('provas')} provas em "
                          f"{cal.get('tempo_seg')}s"
                          f"{' (parcial)' if cal.get('parcial') else ''}")
            kn = magna.conhecimento(detalhes=False)
            ev = magna.evidencia_abertura()
            print(f"[ACERVO] {kn['versao_acervo']} · {kn['base']['concursos']} "
                  f"concursos lidos (1–{kn['base']['ultimo']}) · a decidir: "
                  f"concurso {kn['base']['proximo_concurso']}")
            print(f"[ACERVO] leitura: {ev['leitura']}")
            top = ", ".join(f"{int(r['dezena']):02d} {r['prob']:.1%}"
                            for r in (ev["ranking_completo"] or [])[:3])
            print(f"[ACERVO] abertura mais provável: {top or '—'}")
            plac = ev["placar"]
            if plac.get("aplicavel"):
                print(f"[ACERVO] placar walk-forward ({plac['n_provas']} provas): "
                      f"{plac['leitura']}")
            print("[ACERVO] pesos do consenso: " +
                  " · ".join(f"{n} {v:.3f}" for n, v in
                             kn["pesos_fontes"].items()))
            print(f"[ACERVO] memória conferida: "
                  f"{kn['placar_abertura'].get('provas', 0)} palpite(s) de "
                  f"abertura julgado(s) · top1 "
                  f"{kn['placar_abertura'].get('acerto_top1', 0)}")
            print(f"[ACERVO] honestidade: {kn['honestidade']}")
        except Exception as e:
            print(f"[ACERVO] Erro (não bloqueia a decisão): {e}")
        # `--conhecimento` sozinho é consulta: mostra e sai sem gerar.
        if args.conhecimento and not args.assimilar and "--qtd" not in sys.argv:
            print("[ACERVO] --conhecimento sem geração: nada criado.")
            return

    # v11.2 — Clima: boletim do dia (se informado) + auto-auditoria
    if args.temp is not None or args.pressao is not None or args.umidade is not None:
        magna.clima.definir_condicoes(args.temp, args.pressao, args.umidade)
        print(f"[CLIMA] Boletim definido: temp={args.temp}°C pressao={args.pressao} atm umidade={args.umidade}%")
    try:
        rep_c = magna.clima.relatorio()
        prev = rep_c["clima_previsto"]
        auto = rep_c["auto_ponderacao"]
        print(f"[CLIMA v11.2] {rep_c['n_registros']} registros | próximo: "
              f"{prev['temperatura']}°C {prev['pressao']} atm {prev['umidade']}% "
              f"({prev['fonte']}) | top5 {rep_c['top5_clima_previsto']} | "
              f"confiança {auto.get('fator_confianca')}")
        tf = rep_c["testes_fisicos"]
        for nome, t in (("T1", tf["T1_impares_pressao"]),
                        ("T2", tf["T2_soma_umidade"]),
                        ("T3", tf["T3_frequencia_temperatura"])):
            if t.get("aplicavel"):
                print(f"      {nome}: {t.get('veredito', '-')} — "
                      f"{str(t.get('leitura', ''))[:110]}")
        print(f"      honestidade: {tf['honestidade']['resumo']}")
    except Exception as e:
        print(f"[CLIMA] Erro (não bloqueia): {e}")

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
    if args.auto:
        # v11.7 — forja automática: local do sorteio → telemetria INMET →
        # forja suprema (clima local com peso restrito no consenso)
        from core.forja_auto import ForjaAutomatica
        print("\n[GERANDO] Forja automática v11.7 (telemetria INMET por local "
              "do sorteio)...")
        auto = ForjaAutomatica(magna=magna)
        auto_res = auto.executar(
            quantidade=args.qtd,
            orcamento=args.orcamento,
            alvo=args.alvo,
            perfil=args.perfil,
            segundos_forja=args.segundos,
            salvar=args.salvar,
            usar_inmet=not args.sem_inmet,
        )
        if auto_res.get("status") != "ok":
            print("\n[AUTO] ERRO: {}".format(auto_res.get("msg")))
            sys.exit(1)
        local = auto_res.get("local", {})
        print("[AUTO] local do sorteio: {}/{} ({})".format(
            local.get("cidade"), local.get("uf"), local.get("fonte")))
        tel = auto_res.get("telemetria", {})
        print("[AUTO] telemetria: {} · fonte {} · {}°C {} atm {}%".format(
            tel.get("status"), tel.get("fonte"),
            (tel.get("telemetria") or {}).get("temperatura"),
            (tel.get("telemetria") or {}).get("pressao"),
            (tel.get("telemetria") or {}).get("umidade")))
        resultado = auto_res.get("decisao", {})
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
