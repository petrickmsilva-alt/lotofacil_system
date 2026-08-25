"""
============================================================
FÍSICA DO SORTEIO — Perfil Físico das Bolas e Ambiente
============================================================
Fonte de evidência para a Inteligência Magna.

Cada bola (1..25) possui propriedades mecânicas individuais:
  massa, diâmetro, circunferência, cor, desgaste, rugosidade,
  coeficiente de restituição e ciclos de uso.

Cada sorteio pode registrar o ambiente:
  máquina/globo, temperatura, pressão, umidade, densidade do ar,
  velocidade de rotação, duração da mistura, data da última manutenção.

Quando NÃO existem medições reais, a fonte permanece neutra
(vetor uniforme) e a Magna a ignora no consenso.

AVISO IMPORTANTE: sem medições reais de cada bola e de cada
sorteio, desgaste, cor e ambiente são apenas valores simulados.
Nesse caso, aparecem como experimento físico, não como evidência
preditiva comprovada.
============================================================
"""
import math
import sqlite3
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from config import (
    DATABASE_PATH, TOTAL_DEZENAS,
    MASSA_BOLA_KG, DIAMETRO_BOLA_M, RAIO_BOLA_M,
    COEF_RESTITUICAO, TEMPERATURA_K, PRESSAO_ATM,
    DENSIDADE_AR, UMIDADE_RELATIVA, GRAVIDADE,
)


# ============================================================
# CORES OFICIAIS DAS BOLAS DA LOTOFÁCIL
# ============================================================
# As cores são conhecimento público e constante.
# Não recebem coeficiente preditivo sem relação medida.
CORES_BOLAS = {
    1:  "branca",    2:  "branca",    3:  "branca",
    4:  "branca",    5:  "branca",    6:  "amarela",
    7:  "amarela",   8:  "amarela",   9:  "amarela",
    10: "amarela",   11: "azul",      12: "azul",
    13: "azul",      14: "azul",      15: "azul",
    16: "vermelha",  17: "vermelha",  18: "vermelha",
    19: "vermelha",  20: "vermelha",  21: "verde",
    22: "verde",     23: "verde",     24: "verde",
    25: "verde",
}

CORES_RGB = {
    "branca":   (255, 255, 255),
    "amarela":  (255, 215, 0),
    "azul":     (30, 90, 200),
    "vermelha": (200, 30, 30),
    "verde":    (30, 160, 50),
}

# Massa nominal e variação típica por pigmentação (gramas)
# Valores de referência da indústria de borracha pigmentada
MASSA_POR_COR = {
    "branca":   66.0,
    "amarela":  66.2,
    "azul":     66.5,
    "vermelha": 66.3,
    "verde":    66.4,
}

# Densidade do pigmento relativa à base (afeta desgaste)
DESGASTE_POR_COR = {
    "branca":   1.00,
    "amarela":  1.02,
    "azul":     1.05,
    "vermelha": 1.03,
    "verde":    1.04,
}


class PerfilBola:
    """Propriedades mecânicas individuais de uma bola."""

    __slots__ = (
        "numero", "massa", "diametro", "raio", "circunferencia",
        "cor", "material", "rugosidade", "coef_restituicao",
        "ciclos_uso", "indice_desgaste",
    )

    def __init__(self, numero: int, massa: float = None,
                 diametro: float = None, cor: str = None,
                 rugosidade: float = None, coef_restituicao: float = None,
                 ciclos_uso: int = 0):
        if not 1 <= numero <= 25:
            raise ValueError("numero deve estar entre 1 e 25")
        self.numero = numero
        self.cor = cor or CORES_BOLAS.get(numero, "branca")
        self.massa = massa or MASSA_POR_COR.get(self.cor, MASSA_BOLA_KG * 1000) / 1000.0
        self.diametro = diametro or DIAMETRO_BOLA_M
        self.raio = self.diametro / 2.0
        self.circunferencia = math.pi * self.diametro
        self.material = "borracha_macica"
        self.rugosidade = rugosidade or 0.0
        self.coef_restituicao = coef_restituicao or COEF_RESTITUICAO
        self.ciclos_uso = ciclos_uso
        self.indice_desgaste = self._calcular_desgaste()

    def _calcular_desgaste(self) -> float:
        """Índice de desgaste [0.0 = nova, 1.0 = totalmente desgastada].

        Modelo simplificado: desgaste cresce com raiz quadrada dos ciclos
        e é modificado pela resistência do pigmento.
        """
        fator_cor = DESGASTE_POR_COR.get(self.cor, 1.0)
        # 5000 ciclos como referência de "desgaste total"
        raw = math.sqrt(self.ciclos_uso / 5000.0) * fator_cor
        return min(1.0, max(0.0, raw))

    def massa_atual(self) -> float:
        """Massa ajustada pelo desgaste (perda de material superficial)."""
        # Perda máxima de ~2% da massa
        return self.massa * (1.0 - 0.02 * self.indice_desgaste)

    def coef_restituicao_atual(self) -> float:
        """Coeficiente de restituição degradado pelo desgaste."""
        # Desgaste reduz a elasticidade em até 8%
        return self.coef_restituicao * (1.0 - 0.08 * self.indice_desgaste)

    def to_dict(self) -> Dict:
        return {
            "numero": self.numero,
            "massa_g": round(self.massa * 1000, 2),
            "massa_atual_g": round(self.massa_atual() * 1000, 2),
            "diametro_mm": round(self.diametro * 1000, 2),
            "circunferencia_mm": round(self.circunferencia * 1000, 2),
            "cor": self.cor,
            "material": self.material,
            "rugosidade": round(self.rugosidade, 4),
            "coef_restituicao": round(self.coef_restituicao, 4),
            "coef_restituicao_atual": round(self.coef_restituicao_atual(), 4),
            "ciclos_uso": self.ciclos_uso,
            "indice_desgaste": round(self.indice_desgaste, 4),
        }


class AmbienteSorteio:
    """Condições ambientais de um sorteio específico."""

    __slots__ = (
        "maquina", "conjunto_bolas", "temperatura", "pressao",
        "umidade", "densidade_ar", "gravidade",
        "velocidade_rotacao", "duracao_mistura",
        "data_ultima_manutencao",
    )

    def __init__(self, maquina: str = "padrao",
                 conjunto_bolas: str = "A",
                 temperatura: float = None,
                 pressao: float = None,
                 umidade: float = None,
                 densidade_ar: float = None,
                 gravidade: float = None,
                 velocidade_rotacao: float = 30.0,
                 duracao_mistura: float = 60.0,
                 data_ultima_manutencao: str = None):
        self.maquina = maquina
        self.conjunto_bolas = conjunto_bolas
        self.temperatura = temperatura or TEMPERATURA_K
        self.pressao = pressao or PRESSAO_ATM
        self.umidade = umidade or UMIDADE_RELATIVA
        self.densidade_ar = densidade_ar or DENSIDADE_AR
        self.gravidade = gravidade or GRAVIDADE
        self.velocidade_rotacao = velocidade_rotacao
        self.duracao_mistura = duracao_mistura
        self.data_ultima_manutencao = data_ultima_manutencao

    def to_dict(self) -> Dict:
        return {
            "maquina": self.maquina,
            "conjunto_bolas": self.conjunto_bolas,
            "temperatura_K": round(self.temperatura, 2),
            "temperatura_C": round(self.temperatura - 273.15, 2),
            "pressao_atm": round(self.pressao, 4),
            "umidade_pct": round(self.umidade * 100, 1),
            "densidade_ar": round(self.densidade_ar, 4),
            "gravidade": round(self.gravidade, 4),
            "velocidade_rotacao_rpm": round(self.velocidade_rotacao, 1),
            "duracao_mistura_s": round(self.duracao_mistura, 1),
            "data_ultima_manutencao": self.data_ultima_manutencao,
        }


class MotorFisicaSorteio:
    """Motor de física do sorteio — fonte de evidência para a Magna.

    Produz um vetor de escore por dezena (1..25) baseado nas propriedades
    físicas individuais das bolas e nas condições ambientais.

    Quando NÃO existem medições reais no banco, retorna vetor neutro
    (uniforme) — a Magna o ignora naturalmente pelo peso zero.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        self._bolas: Dict[int, PerfilBola] = {}
        self._ambientes: List[AmbienteSorteio] = []
        self._tem_dados = False
        self._criar_tabelas()
        self._carregar_dados()

    def _criar_tabelas(self):
        """Cria tabelas de física se não existirem."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fisica_bolas (
                numero INTEGER PRIMARY KEY,
                massa_g REAL,
                diametro_mm REAL,
                circunferencia_mm REAL,
                cor TEXT,
                material TEXT,
                rugosidade REAL,
                coef_restituicao REAL,
                ciclos_uso INTEGER DEFAULT 0,
                indice_desgaste REAL DEFAULT 0,
                atualizado_em TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fisica_ambientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concurso INTEGER,
                maquina TEXT,
                conjunto_bolas TEXT,
                temperatura_K REAL,
                pressao_atm REAL,
                umidade REAL,
                densidade_ar REAL,
                gravidade REAL,
                velocidade_rotacao REAL,
                duracao_mistura REAL,
                data_ultima_manutencao TEXT,
                registrado_em TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _carregar_dados(self):
        """Carrega perfis de bolas e ambientes do banco."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            # Bolas
            rows = conn.execute("SELECT * FROM fisica_bolas").fetchall()
            for r in rows:
                numero = int(r["numero"])
                self._bolas[numero] = PerfilBola(
                    numero=numero,
                    massa=float(r["massa_g"]) / 1000.0,
                    diametro=float(r["diametro_mm"]) / 1000.0,
                    cor=r["cor"],
                    rugosidade=float(r["rugosidade"] or 0),
                    coef_restituicao=float(r["coef_restituicao"] or COEF_RESTITUICAO),
                    ciclos_uso=int(r["ciclos_uso"] or 0),
                )
            # Ambientes
            rows_a = conn.execute(
                "SELECT * FROM fisica_ambientes ORDER BY id DESC LIMIT 50"
            ).fetchall()
            for r in rows_a:
                self._ambientes.append(AmbienteSorteio(
                    maquina=r["maquina"] or "padrao",
                    conjunto_bolas=r["conjunto_bolas"] or "A",
                    temperatura=float(r["temperatura_K"] or TEMPERATURA_K),
                    pressao=float(r["pressao_atm"] or PRESSAO_ATM),
                    umidade=float(r["umidade"] or UMIDADE_RELATIVA),
                    densidade_ar=float(r["densidade_ar"] or DENSIDADE_AR),
                    gravidade=float(r["gravidade"] or GRAVIDADE),
                    velocidade_rotacao=float(r["velocidade_rotacao"] or 30),
                    duracao_mistura=float(r["duracao_mistura"] or 60),
                    data_ultima_manutencao=r["data_ultima_manutencao"],
                ))
            conn.close()
            self._tem_dados = len(self._bolas) > 0
        except Exception as e:
            print("[FISICA] Erro ao carregar dados: {}".format(e))

    @property
    def tem_dados_reais(self) -> bool:
        """True se existem medições reais de pelo menos uma bola."""
        return self._tem_dados

    @property
    def n_bolas_medidas(self) -> int:
        return len(self._bolas)

    @property
    def n_ambientes(self) -> int:
        return len(self._ambientes)

    def registrar_bola(self, numero: int, massa_g: float = None,
                       diametro_mm: float = None, cor: str = None,
                       rugosidade: float = None,
                       coef_restituicao: float = None,
                       ciclos_uso: int = 0) -> Dict:
        """Registra ou atualiza o perfil físico de uma bola."""
        bola = PerfilBola(
            numero=numero,
            massa=massa_g / 1000.0 if massa_g else None,
            diametro=diametro_mm / 1000.0 if diametro_mm else None,
            cor=cor,
            rugosidade=rugosidade,
            coef_restituicao=coef_restituicao,
            ciclos_uso=ciclos_uso,
        )
        self._bolas[numero] = bola

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO fisica_bolas
            (numero, massa_g, diametro_mm, circunferencia_mm, cor,
             material, rugosidade, coef_restituicao, ciclos_uso,
             indice_desgaste, atualizado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            bola.numero,
            round(bola.massa * 1000, 2),
            round(bola.diametro * 1000, 2),
            round(bola.circunferencia * 1000, 2),
            bola.cor,
            bola.material,
            round(bola.rugosidade, 4),
            round(bola.coef_restituicao, 4),
            bola.ciclos_uso,
            round(bola.indice_desgaste, 4),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
        conn.close()
        self._tem_dados = True
        return bola.to_dict()

    def registrar_ambiente(self, concurso: int = None,
                           maquina: str = "padrao",
                           conjunto_bolas: str = "A",
                           temperatura_K: float = None,
                           pressao_atm: float = None,
                           umidade: float = None,
                           densidade_ar: float = None,
                           gravidade: float = None,
                           velocidade_rotacao: float = 30.0,
                           duracao_mistura: float = 60.0,
                           data_ultima_manutencao: str = None) -> Dict:
        """Registra as condições ambientais de um sorteio."""
        amb = AmbienteSorteio(
            maquina=maquina,
            conjunto_bolas=conjunto_bolas,
            temperatura=temperatura_K,
            pressao=pressao_atm,
            umidade=umidade,
            densidade_ar=densidade_ar,
            gravidade=gravidade,
            velocidade_rotacao=velocidade_rotacao,
            duracao_mistura=duracao_mistura,
            data_ultima_manutencao=data_ultima_manutencao,
        )
        self._ambientes.insert(0, amb)
        if len(self._ambientes) > 50:
            self._ambientes = self._ambientes[:50]

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO fisica_ambientes
            (concurso, maquina, conjunto_bolas, temperatura_K,
             pressao_atm, umidade, densidade_ar, gravidade,
             velocidade_rotacao, duracao_mistura,
             data_ultima_manutencao, registrado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            concurso, maquina, conjunto_bolas,
            amb.temperatura, amb.pressao, amb.umidade,
            amb.densidade_ar, amb.gravidade,
            amb.velocidade_rotacao, amb.duracao_mistura,
            data_ultima_manutencao,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
        conn.close()
        return amb.to_dict()

    def score_fisico(self) -> np.ndarray:
        """Produz o vetor de escore físico por dezena (1..25).

        Se NÃO existem medições reais, retorna vetor uniforme (neutro).
        A Magna ignora naturalmente fontes neutras pelo peso baixo.

        Quando existem medições, o escore combina:
          1. Massa atual (bolas mais leves tendem a subir mais)
          2. Coeficiente de restituição (bolas mais elásticas ganham
             mais energia nas colisões)
          3. Desgaste (bolas desgastadas têm superfície irregular,
             alterando a aerodinâmica)
          4. Rugosidade (afeta arrasto)
          5. Cor/pigmento (propriedades térmicas diferentes)
          6. Condições ambientais (se disponíveis)
        """
        if not self._tem_dados:
            return np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

        scores = np.zeros(TOTAL_DEZENAS)

        # Último ambiente disponível (se houver)
        amb = self._ambientes[0] if self._ambientes else None

        for numero in range(1, TOTAL_DEZENAS + 1):
            idx = numero - 1
            bola = self._bolas.get(numero)

            if bola is None:
                # Bola sem medição: usa valores nominais
                scores[idx] = 0.5
                continue

            # Componente 1: massa (bolas mais leves → maior mobilidade)
            massa_norm = 1.0 - (bola.massa_atual() - 0.064) / 0.004
            massa_norm = max(0.0, min(1.0, massa_norm))

            # Componente 2: elasticidade
            elast_norm = (bola.coef_restituicao_atual() - 0.75) / 0.10
            elast_norm = max(0.0, min(1.0, elast_norm))

            # Componente 3: desgaste (moderadamente desgastada pode ter
            # irregularidades que favorecem certas trajetórias)
            # Curva em U: nem nova nem totalmente desgastada
            desg = bola.indice_desgaste
            desg_score = 1.0 - abs(desg - 0.3) * 2  # pico em 0.3
            desg_score = max(0.0, min(1.0, desg_score))

            # Componente 4: rugosidade (normalizada)
            rug_norm = min(1.0, bola.rugosidade / 0.1) if bola.rugosidade > 0 else 0.5

            # Componente 5: cor (efeito térmico — bolas escuras absorvem
            # mais radiação, podem ter temperatura ligeiramente diferente)
            cor = bola.cor
            if cor in ("vermelha", "azul", "verde"):
                termico = 0.55  # cores escuras absorvem mais
            elif cor == "amarela":
                termico = 0.50
            else:
                termico = 0.45  # branca reflete mais

            # Combinação ponderada
            score = (
                massa_norm * 0.25 +
                elast_norm * 0.25 +
                desg_score * 0.20 +
                rug_norm   * 0.10 +
                termico    * 0.20
            )
            scores[idx] = score

        # Ajuste ambiental (se disponível)
        if amb is not None:
            # Temperatura mais alta → ar menos denso → bolas mais leves
            # voam mais longe
            fator_temp = (amb.temperatura - 290) / 10.0  # normalizado
            # Umidade alta → ar mais pesado → mais arrasto
            fator_umid = -(amb.umidade - 0.5) * 0.5
            # Rotação mais rápida → mais mistura → mais aleatoriedade
            fator_rot = amb.velocidade_rotacao / 60.0  # normalizado

            ajuste = 1.0 + 0.05 * (fator_temp + fator_umid)
            scores *= ajuste

        # Normalização
        s = scores.sum()
        return scores / s if s > 0 else np.ones(TOTAL_DEZENAS) / TOTAL_DEZENAS

    def get_status(self) -> Dict:
        """Retorna o estado atual da fonte física."""
        return {
            "tem_dados_reais": self._tem_dados,
            "bolas_medidas": self.n_bolas_medidas,
            "ambientes_registrados": self.n_ambientes,
            "estado": (
                "medida e ativa" if self._tem_dados
                else "neutra sem medições"
            ),
            "bolas": {
                n: b.to_dict() for n, b in sorted(self._bolas.items())
            },
            "ultimo_ambiente": (
                self._ambientes[0].to_dict() if self._ambientes else None
            ),
        }

    def get_bolas(self) -> List[Dict]:
        """Lista todos os perfis de bolas registrados."""
        return [b.to_dict() for _, b in sorted(self._bolas.items())]

    def get_ambientes(self, limit: int = 20) -> List[Dict]:
        """Lista os últimos ambientes registrados."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM fisica_ambientes ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []
