import math
from .window import Window

"""
===============================================================================
POWER PPLAY 2.1 - INTERPOLAÇÃO
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Este software é uma evolução profunda e modernização da biblioteca PPlay,
originalmente concebida pela Equipe PPlay:
    Prof. Esteban Clua, Prof. Anselmo Montenegro, Gabriel Saldanha,
    Adônis Gasiglia, Yuri Nogueira e Sergio Herman.
-------------------------------------------------------------------------------
Leva um atributo de um valor a outro, com o tempo.

    Tween.to(porta, "y", 200, 0.8, "ease_out")

DOIS TWEENS NO MESMO ATRIBUTO

O segundo agora substitui o primeiro. Antes os dois ficavam vivos, e cada
quadro os dois escreviam no mesmo atributo: o valor tremia entre os dois
destinos e nunca chegava a lugar nenhum — e quando o mais curto acabava, o
mais longo continuava puxando de volta para o valor que ele tinha guardado lá
atrás. É o tipo de coisa que se vê acontecendo e não se consegue explicar.

O novo tween parte do valor de AGORA, e não do que estava lá quando o primeiro
começou, que é o que "interromper e ir para outro lugar" quer dizer.

CANCELAR

`Tween.to` devolve o tween, e `Tween.cancelar(t)` o tira. `Tween.limpar()`
esvazia tudo — que é o que uma troca de cena quer, porque a lista é global e um
tween sobrevivente continuaria mexendo num objeto que já saiu do ar.
===============================================================================
"""


class Tween:
    """
    Gerenciador de Interpolação (Juice).

    Faz transições suaves em qualquer atributo de um objeto.
    """

    _ativos = []

    @classmethod
    def to(cls, objeto, atributo, valor_final, duracao, tipo="linear"):
        """
        Interpola um atributo do objeto até o valor final. Devolve o tween.

        Tipos: 'linear', 'ease_in', 'ease_out', 'bounce'.
        """
        valor_inicial = getattr(objeto, atributo)

        # Duração zero (ou negativa) é um pedido legítimo — "põe já no lugar" —
        # mas ia parar numa divisão por zero dentro do update. Resolvemos na
        # hora e não agendamos nada.
        if duracao <= 0:
            cls.cancelar_de(objeto, atributo)
            setattr(objeto, atributo, valor_final)
            return None

        # Quem já estava mexendo neste atributo sai de cena.
        cls.cancelar_de(objeto, atributo)

        tween = {
            "obj": objeto,
            "attr": atributo,
            "ini": valor_inicial,
            "fim": valor_final,
            "dur": duracao,
            "progresso": 0,
            "tipo": tipo,
        }
        cls._ativos.append(tween)
        return tween

    @classmethod
    def cancelar(cls, tween):
        """Para este tween. O atributo fica onde estiver."""
        if tween in cls._ativos:
            cls._ativos.remove(tween)
            return True
        return False

    @classmethod
    def cancelar_de(cls, objeto, atributo=None):
        """
        Para os tweens de um objeto — de um atributo só, ou de todos.

        Devolve quantos pararam.
        """
        antes = len(cls._ativos)
        cls._ativos = [t for t in cls._ativos
                       if not (t["obj"] is objeto
                               and (atributo is None or t["attr"] == atributo))]
        return antes - len(cls._ativos)

    @classmethod
    def limpar(cls):
        """Esvazia a lista. Devolve quantos tweens foram embora."""
        quantos = len(cls._ativos)
        cls._ativos = []
        return quantos

    @classmethod
    def ativos(cls):
        """Os tweens em andamento."""
        return list(cls._ativos)

    @classmethod
    def update(cls):
        janela = Window.get_instance()
        if not janela:
            return
        dt = janela.delta_time()

        for t in list(cls._ativos):
            # Um tween cancelado por outro durante esta mesma passada já saiu
            # da lista; mexer nele seria escrever num objeto que ninguém quer.
            if t not in cls._ativos:
                continue
            t["progresso"] += dt / t["dur"]
            p = min(1.0, t["progresso"])

            # Funções de Easing (Matemática Pura)
            if t["tipo"] == "ease_in":
                f = p * p
            elif t["tipo"] == "ease_out":
                f = 1 - (1 - p) * (1 - p)
            elif t["tipo"] == "bounce":
                # Efeito de rebote simples
                f = 1 - abs(math.cos(p * math.pi * 2) * (1 - p))
            else:  # Linear
                f = p

            novo_valor = t["ini"] + (t["fim"] - t["ini"]) * f
            setattr(t["obj"], t["attr"], novo_valor)

            if p >= 1.0:
                cls.cancelar(t)
