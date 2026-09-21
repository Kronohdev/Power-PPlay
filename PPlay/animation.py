import math
import pygame
from .gameimage import GameImage
from .window import Window
from .camera import Camera

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


class Animation(GameImage):
    """
    Gerencia sequências de frames (Spritesheets) com controle de tempo
    baseado em Delta Time e suporte a Câmera.
    """
    def __init__(self, caminho_imagem, total_frames, loop=True, linhas=1):
        super().__init__(caminho_imagem)

        # max(1, ...) porque total_frames=0 (erro de digitação comum, ou uma
        # variável que ficou zerada) derrubava o construtor com divisão por
        # zero logo abaixo. Uma folha com zero quadros não existe: o mínimo é 1.
        self.total_frames = max(1, int(total_frames))
        self.loop = loop

        # Suporte a spritesheet em GRADE: com linhas=1 (padrão) o comportamento
        # é idêntico ao de antes — uma única tira horizontal.
        self.linhas = max(1, int(linhas))
        self.colunas = math.ceil(self.total_frames / self.linhas)

        # Ajusta as dimensões para o tamanho de UM frame
        self.width = self.width / self.colunas
        self.height = self.height / self.linhas

        self.frame_atual = 0
        self.rodando = True

        # Trecho da folha que está tocando. Por padrão é a folha inteira, então
        # o comportamento é exatamente o de sempre; quem limita o intervalo é
        # o set_intervalo_frames (usado pelo set_sequence da PPlay 1.0).
        self.frame_inicial = 0
        self.frame_final = self.total_frames - 1

        # Controle de tempo (em segundos)
        self.tempo_por_frame = 0.1  # Padrão: 10 FPS
        self.tempo_acumulado = 0

    def set_intervalo_frames(self, inicio, fim):
        """
        Limita a animação a um trecho da folha (ambos os índices entram).

            heroi.set_intervalo_frames(4, 7)   # só a corrida

        Serve de base para o set_sequence(inicio, fim) da PPlay 1.0, que até
        então recebia os dois índices e os jogava fora.
        """
        inicio = max(0, min(int(inicio), self.total_frames - 1))
        fim = max(inicio, min(int(fim), self.total_frames - 1))
        self.frame_inicial = inicio
        self.frame_final = fim
        if not (inicio <= self.frame_atual <= fim):
            self.frame_atual = inicio
        return self

    def set_total_duration(self, tempo_total_ms):
        """Define a duração total de uma volta completa da animação."""
        tempo_total_seg = tempo_total_ms / 1000.0
        self.tempo_por_frame = tempo_total_seg / self.total_frames

    def _recorte_atual(self):
        """O quadro que está tocando, recortado da folha."""
        col = int(self.frame_atual) % self.colunas
        lin = int(self.frame_atual) // self.colunas
        largura, altura = int(self.width), int(self.height)
        try:
            return self.image.subsurface(
                (col * largura, lin * altura, largura, altura))
        except ValueError:
            return None

    def set_curr_frame(self, frame):
        """Define manualmente o frame atual (0 até total_frames - 1)."""
        if 0 <= frame < self.total_frames:
            self.frame_atual = frame

    def get_curr_frame(self):
        """Retorna o índice do frame sendo exibido."""
        return self.frame_atual

    def set_loop(self, loop):
        """Define se a animação deve recomeçar ao chegar no fim."""
        self.loop = loop

    def update(self):
        """Troca os frames baseando-se no tempo real transcorrido (Delta Time)."""
        if not self.rodando:
            return

        self.tempo_acumulado += Window.get_instance().delta_time()

        if self.tempo_acumulado >= self.tempo_por_frame:
            self.frame_atual += 1
            self.tempo_acumulado = 0

            # Com o intervalo padrão (0 .. total_frames-1) isto é idêntico ao
            # que havia antes; com um intervalo menor, a volta acontece dentro
            # do trecho escolhido.
            if self.frame_atual > self.frame_final:
                if self.loop:
                    self.frame_atual = self.frame_inicial
                else:
                    self.frame_atual = self.frame_final
                    self.rodando = False

    def draw(self):
        """Desenha o frame atual considerando a Câmera."""
        # A PPlay 1.0 tinha hide()/unhide(), que apenas ligam e desligam este
        # atributo. A ponte de retrocompatibilidade continuava a oferecer os
        # dois métodos, mas ninguém lia a marca: hide() não escondia nada.
        if not self.drawable:
            return

        cam = Camera.get_instance()
        
        # Coordenadas virtuais para suporte a Câmera
        draw_x = cam.transform_x(self.x) if cam else self.x
        draw_y = cam.transform_y(self.y) if cam else self.y

        # Define o retângulo de corte na Spritesheet (linha x coluna)
        col = self.frame_atual % self.colunas
        lin = self.frame_atual // self.colunas
        area_corte = pygame.Rect(
            col * self.width, lin * self.height,
            self.width, self.height
        )
        
        # Desenha apenas o pedaço (frame) no buffer virtual. Quando o objeto
        # está espelhado, a folha usada é a virada — com os quadros no mesmo
        # lugar, então o recorte acima continua valendo.
        Window.get_screen().blit(self._superficie(self.colunas, self.linhas),
                                 (draw_x, draw_y), area_corte)

    def play(self): self.rodando = True
    def stop(self): self.rodando = False; self.frame_atual = 0
    def pause(self): self.rodando = False