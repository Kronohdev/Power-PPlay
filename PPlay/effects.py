import random
import pygame
from .window import Window
from .camera import Camera

"""
===============================================================================
POWER PPLAY 2.1 - EFEITOS DE TELA
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
Tremor, flash e escuridão: o tempero que faz um acerto parecer um acerto.

    ScreenEffects.shake(intensidade=7, duracao=0.3)
    ScreenEffects.flash(cor=(200, 40, 80), duracao=0.08)

No laço da cena, três chamadas em ordem:

    ScreenEffects.update()          # conta o tempo
    ScreenEffects.apply_to_camera() # empurra a câmera, no loop()
    ...
    ScreenEffects.draw_flash()      # o véu colorido, por último no draw()

O TREMOR DEVOLVE O QUE PEGOU EMPRESTADO

`apply_to_camera` empurra a câmera alguns pixels para um lado aleatório. O
empurrão do quadro anterior é DESFEITO antes do próximo — e isso não é
detalhe: sem desfazer, cada quadro somava um deslocamento que ninguém tirava,
e a câmera saía andando sozinha. Numa cena que segue o jogador o estrago
passava meio despercebido, porque o `follow` puxava de volta aos poucos; numa
tela parada, a câmera ia embora e não voltava mais.
===============================================================================
"""


class ScreenEffects:
    """Tremor e flash. Tudo de classe: existe um por jogo."""

    _shake_time = 0
    _shake_intensity = 0
    _flash_time = 0
    _flash_color = (255, 255, 255)
    # O quanto o tremor empurrou a câmera no último quadro, para devolver.
    _empurrao = (0.0, 0.0)
    # O véu do flash, guardado entre quadros: alocar uma superfície de tela
    # cheia sessenta vezes por segundo é caro e não muda nada no desenho.
    _veu = None

    @classmethod
    def shake(cls, intensidade=5, duracao=0.3):
        """Faz a tela tremer por X segundos."""
        cls._shake_intensity = intensidade
        cls._shake_time = duracao

    @classmethod
    def flash(cls, cor=(255, 255, 255), duracao=0.1):
        """Faz a tela piscar com uma cor (ex.: vermelho para dano)."""
        cls._flash_color = cor
        cls._flash_time = duracao

    @classmethod
    def parar(cls):
        """
        Corta os efeitos e devolve a câmera ao lugar.

        Existe por causa da troca de cena: o estado daqui é global, e uma fase
        que sai do ar no meio de um tremor deixava a cena seguinte tremendo
        sem ter pedido.
        """
        cls._shake_time = 0
        cls._flash_time = 0
        cls._devolver_empurrao()

    @classmethod
    def update(cls):
        """Atualiza os temporizadores dos efeitos."""
        janela = Window.get_instance()
        if not janela:
            return
        dt = janela.delta_time()
        if cls._shake_time > 0:
            cls._shake_time -= dt
        if cls._flash_time > 0:
            cls._flash_time -= dt

    @classmethod
    def _devolver_empurrao(cls):
        """Tira da câmera o deslocamento que o tremor pôs no quadro anterior."""
        dx, dy = cls._empurrao
        if dx or dy:
            cam = Camera.get_instance()
            if cam:
                cam.x -= dx
                cam.y -= dy
        cls._empurrao = (0.0, 0.0)

    @classmethod
    def apply_to_camera(cls):
        """Aplica o tremor na câmera atual."""
        cls._devolver_empurrao()
        cam = Camera.get_instance()
        if cam and cls._shake_time > 0:
            dx = random.uniform(-cls._shake_intensity, cls._shake_intensity)
            dy = random.uniform(-cls._shake_intensity, cls._shake_intensity)
            cam.x += dx
            cam.y += dy
            cls._empurrao = (dx, dy)

    @classmethod
    def draw_flash(cls):
        """Desenha o véu do flash, se ele estiver no ar."""
        if cls._flash_time <= 0:
            return
        janela = Window.get_instance()
        if not janela:
            return
        tamanho = (janela.largura, janela.altura)
        if cls._veu is None or cls._veu.get_size() != tamanho:
            cls._veu = pygame.Surface(tamanho)
        cls._veu.fill(cls._flash_color)
        cls._veu.set_alpha(150)
        Window.get_screen().blit(cls._veu, (0, 0))


class LightingSystem:
    """Cria atmosfera de escuridão com fontes de luz dinâmicas."""

    def __init__(self, opacidade_noite=240):
        self.fog = None
        self.lights = []
        self.set_opacidade(opacidade_noite)

    def set_opacidade(self, opacidade_noite):
        """
        0 = dia claro (nao escurece nada), 255 = escuridao total.

        A nevoa e aplicada com BLEND_RGBA_MULT, entao a cor dela funciona
        como um multiplicador: quanto mais escura, mais escuro o mundo.
        """
        self.opacidade = max(0, min(255, int(opacidade_noite)))
        base = 255 - self.opacidade
        # tom azulado: o azul fica mais vivo que o vermelho e o verde
        self.cor_noite = (int(base * 0.4), int(base * 0.4), base)

    def _nevoa(self, janela):
        """
        A superfície da névoa, do tamanho da janela de agora.

        Ela era criada uma vez, no construtor, com o tamanho que a janela tinha
        naquele instante — e ficava do tamanho errado para sempre se a
        resolução mudasse depois.
        """
        tamanho = (janela.largura, janela.altura)
        if self.fog is None or self.fog.get_size() != tamanho:
            self.fog = pygame.Surface(tamanho)
        return self.fog

    def draw(self):
        janela = Window.get_instance()
        if not janela:
            return
        fog = self._nevoa(janela)

        # Preenche a névoa com o tom de noite escolhido
        fog.fill(self.cor_noite)

        # 'Fura' a escuridão com as luzes
        for (lx, ly, raio, intensidade) in self.lights:
            # O raio vira range() logo abaixo, então precisa ser inteiro: um
            # raio calculado em conta de float (raio = distancia * 0.5) dava
            # TypeError no meio do desenho. E raio <= 0 dividiria por zero.
            raio = int(raio)
            if raio <= 0:
                continue

            cam = Camera.get_instance()
            tx = cam.transform_x(lx) if cam else lx
            ty = cam.transform_y(ly) if cam else ly

            # Superfície da luz com canal Alpha para degradê
            luz_surf = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
            for r in range(raio, 0, -15):
                alpha = int(intensidade * (1 - r / raio))
                pygame.draw.circle(luz_surf, (255, 200, 100, alpha), (raio, raio), r)

            # Modo ADD faz as luzes se somarem se cruzarem
            fog.blit(luz_surf, (tx - raio, ty - raio), special_flags=pygame.BLEND_RGBA_ADD)

        # A lista é zerada ANTES do blit final: as luzes são reenviadas a cada
        # quadro, e se o desenho falhasse a mesma luz problemática ficava
        # guardada e quebrava todos os quadros seguintes.
        self.lights = []

        # MULT escurece o que está embaixo mantendo a cor das luzes
        Window.get_screen().blit(fog, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
