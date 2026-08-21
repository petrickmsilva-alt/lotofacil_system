"""
Corrige o método get_status no cerebro_ia.py
Remove versões antigas e substitui pela correta
"""
import re

ARQUIVO = "core/cerebro_ia.py"

# Método correto e completo
NOVO_METODO = '''    def get_status(self) -> Dict:
        """Status completo do Cerebro"""

        def _conv(v):
            if hasattr(v, 'item'):
                return v.item()
            if isinstance(v, list):
                return [_conv(x) for x in v]
            if isinstance(v, dict):
                return {k: _conv(vv) for k, vv in v.items()}
            return v

        return {
            "versao":           "7.0",
            "estado":           self.estado,
            "treinado":         bool(self.treinado),
            "total_concursos":  int(self.n),
            "ultima_exec":      self.ultima_exec,
            "metricas":         _conv(self.metricas),
            "pesos_modulos":    {k: float(v) for k, v in self.pesos.items()},
            "filtros": {
                "soma":      [int(self._gaussiano.SOMA_MIN),   int(self._gaussiano.SOMA_MAX)],
                "pares":     [int(self._gaussiano.PARES_MIN),  int(self._gaussiano.PARES_MAX)],
                "primos":    [int(self._gaussiano.PRIMOS_MIN), int(self._gaussiano.PRIMOS_MAX)],
                "fibonacci": [int(self._gaussiano.FIB_MIN),    int(self._gaussiano.FIB_MAX)],
                "borda":     [int(self._gaussiano.BORDA_MIN),  int(self._gaussiano.BORDA_MAX)],
            },
            "ciclo": {
                "rodando":          bool(self._rodando),
                "pausado":          bool(self._pausado),
                "n_cartelas":       int(self.n_cartelas),
                "ciclos_ok":        int(self._ciclos_ok),
                "ciclos_erro":      int(self._ciclos_err),
                "ultimo_processado": int(self._ultimo_processado),
                "proximo_sorteio":  self.proximo_sorteio,
            },
            "oraculo": {
                "ativo":     self._oraculo is not None,
                "n_oraculos": 15,
            },
            "log_recente": self.log[-20:],
        }
'''


def corrigir():
    print("Lendo arquivo...")
    with open(ARQUIVO, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Fazer backup
    with open(ARQUIVO + ".backup", "w", encoding="utf-8") as f:
        f.write(conteudo)
    print("Backup salvo em: {}.backup".format(ARQUIVO))

    linhas = conteudo.split("\n")

    # Encontrar todas as ocorrências de "def get_status"
    inicios = []
    for i, linha in enumerate(linhas):
        if "def get_status" in linha:
            inicios.append(i)

    if not inicios:
        print("ERRO: Nenhum get_status encontrado!")
        return

    print("Encontrado(s) {} get_status na(s) linha(s): {}".format(
        len(inicios), [i + 1 for i in inicios]
    ))

    # Remover TODAS as versões (de trás para frente)
    for inicio in reversed(inicios):
        # Achar o fim do método (próximo "    def " ou EOF)
        fim = len(linhas)
        for j in range(inicio + 1, len(linhas)):
            l = linhas[j]
            # Próximo método da classe (indentado com 4 espaços)
            if l.startswith("    def ") and not l.startswith("        "):
                fim = j
                break
            # Fim da classe
            if l.startswith("class ") or (l.strip() and not l.startswith(" ") and not l.startswith("\t")):
                fim = j
                break

        print("Removendo bloco linhas {} a {}...".format(
            inicio + 1, fim
        ))
        del linhas[inicio:fim]

    # Achar onde adicionar o novo método (antes do fim da classe CerebroIA)
    # Vamos adicionar antes do último método visível
    posicao_insercao = len(linhas)

    # Achar a última linha que é método da classe (indentação de 4 espaços)
    for i in range(len(linhas) - 1, -1, -1):
        if linhas[i].startswith("    def "):
            # Achar fim desse último método
            for j in range(i + 1, len(linhas)):
                l = linhas[j]
                if l.startswith("    def ") or l.startswith("class ") or \
                   (l.strip() and not l.startswith(" ")):
                    posicao_insercao = j
                    break
            break

    print("Inserindo novo get_status na posição {}...".format(
        posicao_insercao + 1
    ))

    novo_conteudo_linhas = NOVO_METODO.split("\n")
    linhas[posicao_insercao:posicao_insercao] = novo_conteudo_linhas

    # Salvar
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print("OK! Arquivo corrigido.")
    print("Se der problema, o backup está em: {}.backup".format(ARQUIVO))


if __name__ == "__main__":
    corrigir()