
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
class Camera:
    _instance = None

    def __init__(self, largura_janela, altura_janela):
        self.x = 0
        self.y = 0
        self.largura = largura_janela
        self.altura = altura_janela
        
        self.limite_topo = None
        self.limite_esquerda = None
        self.limite_base = None
        self.limite_direita = None

        Camera._instance = self

    @classmethod
    def get_instance(cls):
        return cls._instance

    def follow(self, target, suavizacao=0.1, zona_morta_x=0, zona_morta_y=0):
        """
        Centraliza a câmera no alvo.

        `suavizacao` é o quanto da distância que falta a câmera percorre a cada
        quadro: 1 gruda no alvo, 0,1 vai atrás com atraso, 0,02 flutua. Não é
        uma velocidade — é uma fração —, e por isso a câmera desacelera sozinha
        ao chegar perto, que é o que faz o movimento parecer natural.

        `zona_morta_x` e `zona_morta_y` são a folga, em pixels, que o alvo tem
        para se mexer sem que a câmera reaja. Sem folga, a câmera responde a
        cada passo do personagem e a tela inteira balança junto com um pulinho
        de dois pixels; com uma zona morta horizontal, ela só começa a andar
        quando o personagem realmente avança. É o ajuste que separa uma câmera
        de plataforma tolerável de uma enjoativa.

        Os dois são medidos a partir do CENTRO da tela, e o que a câmera
        persegue é o excedente: o alvo que saiu 30 px de uma zona de 20 puxa a
        câmera em 10.
        """
        # O alvo centralizado na tela
        alvo_x = (target.x + target.width / 2) - self.largura / 2
        alvo_y = (target.y + target.height / 2) - self.altura / 2

        if zona_morta_x > 0:
            alvo_x = self._com_folga(alvo_x, self.x, zona_morta_x)
        if zona_morta_y > 0:
            alvo_y = self._com_folga(alvo_y, self.y, zona_morta_y)

        # LERP (Movimento Suave)
        self.x += (alvo_x - self.x) * suavizacao
        self.y += (alvo_y - self.y) * suavizacao
        
        self._aplicar_limites()

    @staticmethod
    def _com_folga(alvo, atual, folga):
        """Para onde a câmera mira quando o alvo tem folga para se mexer."""
        distancia = alvo - atual
        if distancia > folga:
            return atual + (distancia - folga)
        if distancia < -folga:
            return atual + (distancia + folga)
        return atual       # dentro da folga: a câmera não se mexe

    def set_world_bounds(self, largura_mundo, altura_mundo):
        self.limite_esquerda = 0
        self.limite_topo = 0
        # max(0, ...) porque um mundo MENOR que a janela dava limite negativo:
        # a câmera era então "colada" nesse valor e o jogo aparecia deslocado
        # para fora do mundo. Numa fase de tela única o certo é ficar em zero.
        self.limite_direita = max(0, largura_mundo - self.largura)
        self.limite_base = max(0, altura_mundo - self.altura)

    def _aplicar_limites(self):
        if self.limite_esquerda is not None:
            # Primeiro o teto, depois o piso: assim, se os dois se cruzarem,
            # quem vence é o limite mínimo (a origem do mundo) e não o máximo.
            if self.x > self.limite_direita: self.x = self.limite_direita
            if self.x < self.limite_esquerda: self.x = self.limite_esquerda
            if self.y > self.limite_base: self.y = self.limite_base
            if self.y < self.limite_topo: self.y = self.limite_topo

    def transform_x(self, world_x):
        return world_x - self.x

    def transform_y(self, world_y):
        return world_y - self.y