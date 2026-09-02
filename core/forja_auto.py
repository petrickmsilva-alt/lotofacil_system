"""
====================================================================
FORJA AUTOMÁTICA — telemetria INMET por local do sorteio (v11.7)
====================================================================
Pipeline único em modo automático:

  1. Descobre o LOCAL DO SORTEIO (resultado oficial da Caixa →
     banco local → padrão São Paulo/SP);
  2. Busca a TELEMETRIA INMET daquele local (oficial → Open-Meteo
     → neutro, nunca fabrica dado);
  3. Entrega as condições ao MotorClima da Magna (`definir_condicoes`),
     que já tem shrinkage ±10% e auto-auditoria walk-forward;
  4. Roda a FORJA SUPREMA v11 (mesmo processo da decisão única) e
     devolve lote + telemetria + local auditáveis.

HONESTIDADE:
- A telemetria não prevê sorteio: é ambiente físico leve, com peso
  restrito no consenso e reavaliado a cada ciclo pelo placar.
- O modo automático nunca quebra se a rede falhar: a forja segue com
  clima neutro e o relatório diz exatamente o que foi usado.
====================================================================
"""
from typing import Any, Callable, Dict, Optional

from .inmet import (
    LOCAL_PADRAO, InmetClient, TelemetriaInmet, TerritorioInmet, extrair_local,
)


class ForjaAutomatica:
    """Orquestra local do sorteio + telemetria INMET + forja suprema."""

    def __init__(self, magna: Any = None,
                 client: Optional[InmetClient] = None,
                 telemetria: Optional[TelemetriaInmet] = None,
                 db_path: Optional[str] = None,
                 getter: Optional[Callable[[str], Optional[Any]]] = None):
        self.magna = magna
        self.telemetria = telemetria or TelemetriaInmet(db_path)
        self.client = client or InmetClient(getter=getter)
        self.db_path = db_path
        self.ultimo: Dict[str, Any] = {}

    # ------------------------------------------------------------
    # 1. LOCAL DO SORTEIO
    # ------------------------------------------------------------
    def local_do_sorteio(self, usar_rede: bool = True,
                         resultado_caixa: Optional[Dict[str, Any]] = None
                         ) -> Dict[str, Any]:
        """Resolve o local físico do sorteio com cascata de fontes.

        Fontes: resultado oficial da Caixa → última telemetria no banco
        → padrão climatizado de São Paulo/SP. Nunca levanta exceção.
        """
        if resultado_caixa is not None:
            local = extrair_local(resultado_caixa)
            if local:
                territorio = TerritorioInmet().resolver(
                    local.get("local"), local.get("cidade_uf"))
                territorio["fonte"] = "caixa_remota"
                territorio["fonte_dados"] = "resultado_caixa"
                return territorio

        if usar_rede:
            try:
                from .caixa_client import CaixaClient
                resultado = CaixaClient().buscar_ultimo()
                if resultado:
                    local = extrair_local(resultado)
                    if local:
                        territorio = TerritorioInmet().resolver(
                            local.get("local"), local.get("cidade_uf"))
                        territorio["fonte"] = "caixa_remota"
                        territorio["fonte_dados"] = "resultado_caixa"
                        return territorio
            except Exception:
                pass

        ult = self.telemetria.ultima()
        if ult and ult.get("cidade_uf"):
            territorio = TerritorioInmet().resolver(
                ult.get("local"), ult.get("cidade_uf"))
            territorio["fonte"] = "banco_local"
            territorio["fonte_dados"] = "inmet_telemetria"
            return territorio

        padrao = dict(LOCAL_PADRAO)
        padrao["fonte"] = "padrao"
        padrao["fonte_dados"] = "padrao"
        return padrao

    # ------------------------------------------------------------
    # 2. TELEMETRIA
    # ------------------------------------------------------------
    def coletar_telemetria(self, local_dados: Optional[Dict[str, Any]] = None,
                           concurso: Optional[int] = None,
                           salvar: bool = True) -> Dict[str, Any]:
        """Consulta e (opcionalmente) persiste a telemetria do local."""
        local_dados = local_dados or self.local_do_sorteio(usar_rede=False)
        dados = self.client.telemetria(
            local_dados.get("local"), local_dados.get("cidade_uf"))
        if salvar and isinstance(dados, dict):
            dados["_registro_id"] = self.telemetria.registrar(
                dados, concurso=concurso)
        cond = (
            {"temperatura": dados["temperatura"],
             "pressao": dados["pressao"],
             "umidade": dados["umidade"]}
            if all(k is not None for k in
                   (dados.get("temperatura"), dados.get("pressao"),
                    dados.get("umidade")))
            else None
        )
        return {
            "status": dados.get("status"),
            "fonte": dados.get("fonte"),
            "telemetria": dados,
            "condicoes_clima": cond,
            "local": local_dados,
        }

    # ------------------------------------------------------------
    # 3+4. FORJA AUTOMÁTICA COMPLETA
    # ------------------------------------------------------------
    def executar(self, quantidade: int = 8, orcamento: float = 100.0,
                 alvo: int = 13, perfil: str = "equilibrado",
                 segundos_forja: float = 60.0, salvar: bool = True,
                 usar_inmet: bool = True,
                 persistir_telemetria: bool = True,
                 callback: Optional[Callable[[str], None]] = None,
                 resultado_caixa: Optional[Dict[str, Any]] = None
                 ) -> Dict[str, Any]:
        """Pipeline automático completo. Nunca levanta exceção para rede.

        `salvar` controla a persistência do LOTE (cartelas); `usar_inmet`
        liga a telemetria; `persistir_telemetria` controla o registro
        meteorológico (auditoria), independente das cartelas.
        """
        from .cerebro_ia import InteligenciaMagna

        magna = self.magna or InteligenciaMagna(
            n_cartelas=int(quantidade), db_path=self.db_path)

        def cb(msg: str) -> None:
            if callback:
                callback(msg)

        # 1. Local do sorteio
        try:
            local = self.local_do_sorteio(
                usar_rede=bool(usar_inmet), resultado_caixa=resultado_caixa)
        except Exception:
            local = dict(LOCAL_PADRAO)
        cb("[AUTO] local do sorteio: {}/{} ({})".format(
            local.get("cidade"), local.get("uf"), local.get("fonte")))

        # 2. Telemetria INMET
        tele = {"status": "neutro", "fonte": None, "telemetria": None,
                "condicoes_clima": None, "local": local}
        if usar_inmet:
            try:
                tele = self.coletar_telemetria(
                    local, salvar=bool(persistir_telemetria))
                cb("[AUTO] telemetria: {} ({})".format(
                    tele.get("status"), tele.get("fonte")))
            except Exception as exc:
                tele["erro"] = "{}: {}".format(type(exc).__name__, exc)
                cb("[AUTO] telemetria indisponível ({}); seguindo neutro"
                   .format(type(exc).__name__))

        # 3. Condições do MotorClima (peso restrito + auto-auditoria)
        ambiente_registrado = False
        if tele.get("condicoes_clima") and hasattr(magna, "clima"):
            try:
                c = tele["condicoes_clima"]
                res_clima = magna.clima.definir_condicoes(
                    temperatura=c["temperatura"],
                    pressao=c["pressao"],
                    umidade=c["umidade"])
                cb("[AUTO] clima do local definido: {}/{} atm/{}% → {}".format(
                    c["temperatura"], c["pressao"], c["umidade"],
                    res_clima.get("status", "ok")))
                # v12.0 — a Magna também REGISTRA o ambiente de sorteio na
                # fonte física (tabela fisica_ambientes): o que antes era o
                # formulário manual "Registrar Ambiente de Sorteio" agora é
                # um passo interno do pipeline automático.
                try:
                    db_magna = getattr(magna, "db", None)
                    concurso_alvo = (
                        (db_magna.get_ultimo_concurso() if db_magna else 0)
                        or 0) + 1
                    magna.fisica.registrar_ambiente(
                        concurso=concurso_alvo,
                        maquina="padrao-caixa",
                        conjunto_bolas="A",
                        temperatura_K=float(c["temperatura"]) + 273.15,
                        pressao_atm=float(c["pressao"]),
                        umidade=float(c["umidade"]) / 100.0,
                        velocidade_rotacao=30.0,
                        duracao_mistura=60.0)
                    ambiente_registrado = True
                    cb("[AUTO] ambiente de sorteio registrado pela Magna "
                       "(física): {:.1f}°C / {:.3f} atm / {:.0f}%".format(
                           float(c["temperatura"]), float(c["pressao"]),
                           float(c["umidade"])))
                except Exception as exc:
                    cb("[AUTO] registro de ambiente indisponível ({}); "
                       "seguindo".format(type(exc).__name__))
            except Exception as exc:
                cb("[AUTO] clima indisponível ({}); seguindo sem boletim"
                   .format(type(exc).__name__))

        # 4. Forja suprema (mesmo processo da decisão única)
        try:
            if not getattr(magna, "treinado", False):
                if hasattr(magna, "treinar"):
                    magna.treinar()
            decisao = magna.decidir_suprema(
                quantidade=quantidade,
                orcamento=orcamento,
                alvo=alvo,
                modo="suprema",
                perfil=perfil,
                segundos_forja=segundos_forja,
                usar_mcts=True,
                usar_multi_rota=True,
                tentativas_juiz=2,
                registrar=bool(salvar),
            )
        except Exception as exc:
            return {
                "status": "erro",
                "msg": "{}: {}".format(type(exc).__name__, exc),
                "local": local,
                "telemetria": tele,
            }

        resumo = {
            "status": "ok",
            "local": local,
            "telemetria": tele,
            "ambiente_registrado": ambiente_registrado,
            "decisao": decisao,
            "concurso_alvo": decisao.get("concurso_alvo"),
            "n_cartelas": decisao.get("n_cartelas"),
            "estrategia": decisao.get("estrategia"),
            "custo": decisao.get("custo"),
            "registrada": bool(salvar),
        }
        self.ultimo = resumo
        return resumo

    def resumo(self) -> Dict[str, Any]:
        """Estado para auditoria: última execução + base de telemetria."""
        return {
            "ultima_execucao": self.ultimo,
            "telemetria_banco": self.telemetria.resumo(),
        }
