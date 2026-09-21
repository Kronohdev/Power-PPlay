import pygame

"""
===============================================================================
POWER PPLAY 2.1 - Framework de Alta Performance para Desenvolvimento de Jogos
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
===============================================================================
"""

class GameObject:
    """
    A classe mais básica da engine. Representa qualquer 'coisa' que
    tenha uma posição e um tamanho no mundo do jogo.
    """
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0

        # Margem entre o quadro do sprite e a caixa que colide, em pixels:
        # (esquerda, topo, direita, base). Zerada, a caixa é o quadro inteiro,
        # que é como a engine sempre funcionou.
        self.margem_colisao = (0, 0, 0, 0)

    # ------------------------------------------------------------------
    # A CAIXA QUE COLIDE
    # ------------------------------------------------------------------
    # Todo teste de colisão da engine passa por estes quatro números, em vez
    # de usar x/y/width/height direto. Assim, mudar a margem de um objeto
    # muda a colisão dele em todos os lugares de uma vez.
    @property
    def caixa_x(self):
        return self.x + self.margem_colisao[0]

    @property
    def caixa_y(self):
        return self.y + self.margem_colisao[1]

    @property
    def caixa_largura(self):
        return max(1.0, self.width - self.margem_colisao[0] - self.margem_colisao[2])

    @property
    def caixa_altura(self):
        return max(1.0, self.height - self.margem_colisao[1] - self.margem_colisao[3])

    def set_caixa_colisao(self, esquerda=0, topo=0, direita=0, base=0):
        """
        Encolhe a caixa de colisão por dentro do quadro, em pixels.

            inimigo.set_caixa_colisao(esquerda=8, direita=8)

        Serve para o personagem colidir pelo corpo e não pelo quadro, que
        costuma ter margem vazia em volta do desenho.
        """
        self.margem_colisao = (max(0, esquerda), max(0, topo),
                               max(0, direita), max(0, base))
        return self

    def collided(self, outro_obj):
        """
        Verifica colisão básica (AABB - Axis-Aligned Bounding Box).
        É o método de colisão mais rápido que existe.
        """
        ox = getattr(outro_obj, "caixa_x", outro_obj.x)
        oy = getattr(outro_obj, "caixa_y", outro_obj.y)
        ol = getattr(outro_obj, "caixa_largura", outro_obj.width)
        oa = getattr(outro_obj, "caixa_altura", outro_obj.height)
        return (self.caixa_x < ox + ol and
                self.caixa_x + self.caixa_largura > ox and
                self.caixa_y < oy + oa and
                self.caixa_y + self.caixa_altura > oy)

    def set_position(self, x, y):
        """Define a posição do objeto no plano cartesiano."""
        self.x = x
        self.y = y