import pygame
from .window import Window
from .camera import Camera
from .gameimage import GameImage

"""
===============================================================================
POWER PPLAY 2.1 - O FUNDO EM CAMADAS
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
O truque mais barato de profundidade que existe num jogo 2D: desenhar o fundo
em camadas e fazer cada uma andar mais devagar que a anterior.

    fundo = ParallaxSystem()
    fundo.add_layer("assets/ceu.png", 0.15)        # longe, quase parado
    fundo.add_layer("assets/montanhas.png", 0.35)
    fundo.add_layer("assets/arvores.png", 0.65)    # perto, quase junto

O fator é a fração da câmera que a camada acompanha: 0 fica parada na tela, 1
anda colada ao cenário. Quanto menor, mais longe a camada parece.

DUAS COISAS QUE MUDARAM, E POR QUÊ

**A imagem se repete até cobrir a janela.** Antes eram dois blits, o que só
bastava quando a imagem era pelo menos tão larga quanto a janela. Uma faixa de
256px num jogo de 640 deixava o resto da tela vazio, e o aluno via uma listra
de fundo do lado direito sem entender de onde vinha. Agora a conta é quantas
cópias cabem, e sai o número certo.

**O movimento vertical é opcional.** `fator_y` nasce em 0, que é exatamente o
que a camada sempre fez: ficar grudada no topo da tela mesmo quando a câmera
sobe. É o certo para um céu. Para uma caverna, em que a câmera sobe e desce
tanto quanto anda para o lado, um fator vertical pequeno dá a mesma sensação de
profundidade que o horizontal.
===============================================================================
"""


class ParallaxLayer:
    """Uma camada do fundo, com a sua própria velocidade de rolagem."""

    def __init__(self, caminho_imagem, fator_velocidade, fator_y=0.0):
        # GameImage tem cache: a mesma imagem em duas cenas é carregada uma vez.
        self.sprite = GameImage(caminho_imagem)
        self.largura = self.sprite.width
        self.altura = self.sprite.height

        # 0.0 = parada na tela; 1.0 = anda junto com o cenário.
        self.fator = fator_velocidade
        self.fator_y = fator_y

    def draw(self):
        janela = Window.get_instance()
        cam = Camera.get_instance()
        screen = Window.get_screen()

        if not cam or self.largura <= 0:
            self.sprite.draw()
            return

        # O resto da divisão é o que faz o fundo parecer infinito: a imagem
        # volta ao começo a cada `largura` pixels percorridos.
        deslocamento_x = (cam.x * self.fator) % self.largura
        inicio_x = -deslocamento_x
        topo = -(cam.y * self.fator_y) if self.fator_y else 0

        # Quantas cópias cobrem a janela a partir daqui. O +2 é a cópia que
        # começa antes da borda esquerda mais a que fecha a direita.
        largura_janela = janela.largura if janela else self.largura
        copias = int((largura_janela - inicio_x) / self.largura) + 1

        for i in range(max(1, copias)):
            screen.blit(self.sprite.image, (inicio_x + i * self.largura, topo))


class ParallaxSystem:
    """
    Várias camadas, desenhadas da mais distante para a mais próxima.

    A ordem é a de entrada: a primeira camada acrescentada é o fundo de tudo, e
    cada uma seguinte é pintada por cima.
    """

    def __init__(self):
        self.camadas = []

    def add_layer(self, caminho_imagem, fator_velocidade, fator_y=0.0):
        """
        Acrescenta uma camada ao fundo e a devolve.

        Fatores menores (0,1 -- 0,2) para o que está longe; maiores (0,8 --
        0,9) para o que está perto.
        """
        nova_camada = ParallaxLayer(caminho_imagem, fator_velocidade, fator_y)
        self.camadas.append(nova_camada)
        return nova_camada

    def limpar(self):
        """Tira todas as camadas."""
        self.camadas = []

    def draw(self):
        """Desenha todas as camadas na ordem em que foram acrescentadas."""
        for camada in self.camadas:
            camada.draw()
