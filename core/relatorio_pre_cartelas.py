"""
============================================================
RELATÓRIO PRÉ-CARTELAS — TRILHA DE AUDITORIA DA DECISÃO
============================================================
Instrumento da Inteligência Magna que registra, EM ORDEM e
com duração medida, TUDO que ela processa antes de gerar as
cartelas para o sorteio:

  validação → treino/memória → regime → acervo (abertura+cores)
  → percepção do ambiente (INMET/clima/física) → escolha do método
  → fontes assimiladas → consenso (vetor único) → memória episódica
  → antipopularidade → rota extraordinária → pool elite → geração

O relatório acompanha a própria decisão (`relatorio_pre_cartelas`)
e pode ser consultado sozinho (sem gerar cartela nenhuma) via
`InteligenciaMagna.relatorio_pre_cartelas()` ou
`GET /api/magna/pre-cartelas`.

HONESTIDADE: o relatório descreve o PROCESSO (o que foi lido,
pesado e decidido) — ele não altera probabilidades nem valida
previsibilidade. As frações hipergeométricas continuam exatas.
============================================================
"""
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import time


class _EtapaAtiva:
    """Handle de uma etapa em andamento — coleta detalhes/status."""

    def __init__(self, registro: Dict[str, Any]):
        self._registro = registro

    def detalhe(self, **kwargs) -> None:
        """Adiciona/atualiza detalhes que vão para o relatório."""
        self._registro["detalhes"].update(kwargs)

    def aviso(self, msg: str) -> None:
        self._registro["status"] = "aviso"
        avisos = self._registro.setdefault("avisos", [])
        avisos.append(str(msg))

    def erro(self, msg: str) -> None:
        self._registro["status"] = "erro"
        erros = self._registro.setdefault("erros", [])
        erros.append(str(msg))


class GravadorEtapas:
    """Registra, ordenado e cronometrado, o pré-processamento da decisão."""

    def __init__(self, titulo: str = "Pré-processamento da decisão"):
        self.titulo = str(titulo)
        self._etapas: List[Dict[str, Any]] = []
        self._t0 = time.time()
        self.iniciado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    @contextmanager
    def etapa(self, nome: str, descricao: str = "",
              detalhes: Optional[Dict[str, Any]] = None):
        """Context manager: cronometra e registra a etapa.

        Uso:
            with grav.etapa("acervo_abertura", "Relê a base histórica") as et:
                ...
                et.detalhe(digest="sha256:...")
        """
        registro: Dict[str, Any] = {
            "ordem": len(self._etapas) + 1,
            "nome": str(nome),
            "descricao": str(descricao or ""),
            "status": "ok",
            "duracao_ms": 0.0,
            "detalhes": dict(detalhes or {}),
        }
        self._etapas.append(registro)
        handle = _EtapaAtiva(registro)
        t0 = time.time()
        try:
            yield handle
        except Exception as exc:  # a etapa falha sem derrubar a decisão
            registro["status"] = "erro"
            registro.setdefault("erros", []).append(
                "{}: {}".format(type(exc).__name__, exc))
        finally:
            registro["duracao_ms"] = round((time.time() - t0) * 1000.0, 1)

    def registrar(self, nome: str, descricao: str = "",
                  status: str = "ok",
                  duracao_ms: float = 0.0,
                  detalhes: Optional[Dict[str, Any]] = None) -> None:
        """Registra uma etapa instantânea (sem bloco de código)."""
        self._etapas.append({
            "ordem": len(self._etapas) + 1,
            "nome": str(nome),
            "descricao": str(descricao or ""),
            "status": str(status or "ok"),
            "duracao_ms": round(float(duracao_ms or 0.0), 1),
            "detalhes": dict(detalhes or {}),
        })

    # ------------------------------------------------------------------
    def detalhar(self, nome: str, **detalhes) -> None:
        """Enriquece (depois) a etapa registrada com `nome`."""
        for et in reversed(self._etapas):
            if et["nome"] == nome:
                et["detalhes"].update(detalhes)
                return

    def avisar(self, nome: str, msg: str) -> None:
        """Marca aviso numa etapa já registrada com `nome`."""
        for et in reversed(self._etapas):
            if et["nome"] == nome:
                et["status"] = "aviso"
                et.setdefault("avisos", []).append(str(msg))
                return

    def resumo(self) -> Dict[str, Any]:
        contagem: Dict[str, int] = {}
        for et in self._etapas:
            contagem[et["status"]] = contagem.get(et["status"], 0) + 1
        return {
            "total_etapas": len(self._etapas),
            "status_por_tipo": contagem,
            "tempo_total_ms": round((time.time() - self._t0) * 1000.0, 1),
            "erros": [et["nome"] for et in self._etapas
                      if et["status"] == "erro"],
        }

    def relatorio(self) -> Dict[str, Any]:
        """Estrutura final que acompanha a decisão / resposta da API."""
        return {
            "titulo": self.titulo,
            "iniciado_em": self.iniciado_em,
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "etapas": [dict(et) for et in self._etapas],
            "resumo": self.resumo(),
        }

    # ------------------------------------------------------------------
    def para_markdown(self) -> str:
        """Versão legível do relatório (logs, relatórios, revisão humana)."""
        rel = self.relatorio()
        linhas = [
            "# {}".format(rel["titulo"]),
            "",
            "- Início: `{}`".format(rel["iniciado_em"]),
            "- Etapas processadas: **{}**".format(rel["resumo"]["total_etapas"]),
            "- Tempo total: `{:.1f} ms`".format(rel["resumo"]["tempo_total_ms"]),
            "- Status: {}".format(
                ", ".join("{} {}".format(v, k)
                          for k, v in sorted(rel["resumo"]["status_por_tipo"].items()))
                or "—"),
            "",
        ]
        for et in rel["etapas"]:
            icone = {"ok": "✅", "neutro": "⚪", "aviso": "⚠️",
                     "erro": "❌", "ignorado": "⏭️"}.get(et["status"], "•")
            linhas.append("## {}. {} {} — `{:.1f} ms` [{}]".format(
                et["ordem"], icone, et["nome"], et["duracao_ms"], et["status"]))
            if et["descricao"]:
                linhas.append("{}".format(et["descricao"]))
            if et.get("avisos"):
                for a in et["avisos"]:
                    linhas.append("- ⚠️ {}".format(a))
            if et.get("erros"):
                for e in et["erros"]:
                    linhas.append("- ❌ {}".format(e))
            if et["detalhes"]:
                linhas.append("")
                linhas.append("| campo | valor |")
                linhas.append("|---|---|")
                for k, v in et["detalhes"].items():
                    linhas.append("| {} | `{}` |".format(k, v))
            linhas.append("")
        return "\n".join(linhas)
