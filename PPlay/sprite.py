from .animation import Animation
from .window import Window

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

class Sprite(Animation):
    def __init__(self, caminho_imagem, total_frames=1, loop=True, linhas=1):
        # 'linhas' permite spritesheet em grade; 1 = tira horizontal (padrão)
        super().__init__(caminho_imagem, total_frames, loop, linhas)
        self.vx = 0
        self.vy = 0
        self.no_chao = False
        self.body = None

    # MÉTODOS TRADICIONAIS (Mantidos)
    def move_key_x(self, velocidade):
        janela = Window.get_instance()
        teclado = janela.keyboard
        dt = janela.delta_time()
        if teclado.key_pressed("left"): self.x -= velocidade * dt
        if teclado.key_pressed("right"): self.x += velocidade * dt

    def move_key_y(self, velocidade):
        janela = Window.get_instance()
        teclado = janela.keyboard
        dt = janela.delta_time()
        if teclado.key_pressed("up"): self.y -= velocidade * dt
        if teclado.key_pressed("down"): self.y += velocidade * dt

    def move_x(self, velocidade):
        self.x += velocidade * Window.get_instance().delta_time()

    def move_y(self, velocidade):
        self.y += velocidade * Window.get_instance().delta_time()

    def pular(self, forca_pulo):
        """Impulso manual (Use apenas se não usar o update_physics)."""
        if self.no_chao:
            self.vy = -forca_pulo
            self.no_chao = False

    # SISTEMA DE FÍSICA CINEMÁTICA
    def setup_physics(self, engine, controlavel=True, caixa_na_arte=True):
        """
        Acopla um corpo cinemático ao Sprite.

        controlavel=True  -> o corpo lê as setas e o espaço do teclado (jogador).
        controlavel=False -> o corpo NÃO lê o teclado. Use body.mover(-1/0/1) e
                             body.pular() para dirigi-lo por código (inimigos, NPCs).

        caixa_na_arte=True faz a colisão seguir o desenho, e não o quadro do
        sprite. Um quadro de 32x32 com um personagem de 15 px de largura
        colidia nove pixels antes de a arte encostar na parede, e era isso que
        se via na tela. Passe False para colidir pelo quadro inteiro, como nas
        versões anteriores.
        """
        from .physics import KinematicBody
        if caixa_na_arte:
            self.ajustar_caixa_a_arte()
        self.body = KinematicBody(self, engine, controlavel)

    def update_physics(self, lista_solidos):
        if self.body:
            # O KinematicBody gerencia inércia, pulo e colisão
            self.body.update(lista_solidos)

        # Sincroniza animação (herança de Animation) — UMA vez por frame
        self.update()

    # Atalhos para dirigir um corpo não-controlável (IA)
    def mover(self, direcao):
        """direcao: -1 esquerda, 0 parado, +1 direita. Requer setup_physics."""
        if self.body:
            self.body.mover(direcao)

    def solicitar_pulo(self):
        """Pede um pulo ao corpo cinemático (respeita coyote time e buffer)."""
        if self.body:
            self.body.pular()

    def acabou_de_pular(self):
        """
        True só no quadro em que o pulo saiu do chão. Serve para tocar o som
        de pulo sem precisar adivinhar quando o KinematicBody pulou.

            if jogador.acabou_de_pular():
                som_pulo.play()
        """
        return bool(self.body and self.body.pulou)