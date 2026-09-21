import pygame
import math

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

class Physics:
    """
    MOTOR DE FÍSICA CINEMÁTICA 4.5 - THE FEELING UPDATE.
    """
    # Folga usada no teste de sobreposição. Encostar não é colidir: sem esta
    # tolerância, um corpo apoiado no chão contaria como dentro dele.
    EPS = 0.001

    def __init__(self, gravidade=2500, vel_terminal=1500):
        self.gravidade = gravidade
        self.vel_terminal = vel_terminal
        # Em pixels. Zero aqui dividiria por zero na varredura do movimento,
        # então o valor é sempre saneado na hora de usar.
        self.PASSO_MINIMO = 1.0

    def _passo(self):
        """O PASSO_MINIMO, saneado: é atributo público e pode chegar zerado."""
        return max(0.01, float(self.PASSO_MINIMO or 1.0))

    @classmethod
    def sobrepoe(cls, x, y, largura, altura, solido):
        """
        Teste de sobreposição em ponto flutuante.

        O pygame.Rect trunca as coordenadas para inteiro: um corpo em y=287.9
        virava y=287 e passava a invadir o bloco de cima por um pixel. Num
        corredor da altura exata do personagem, isso o prendia no lugar.
        Comparando em float, o encaixe perfeito continua sendo encaixe.
        """
        e = cls.EPS
        return (x + e < solido.x + solido.width and
                x + largura - e > solido.x and
                y + e < solido.y + solido.height and
                y + altura - e > solido.y)

    def _primeiro_solido(self, x, y, largura, altura, lista_solidos):
        for solido in lista_solidos:
            if self.sobrepoe(x, y, largura, altura, solido):
                return solido
        return None

    def _candidatos(self, objeto, dx, dy, lista_solidos):
        """
        Filtra os sólidos que o objeto pode alcançar ao andar (dx, dy).

        Sem isto, cada passo da física percorria a lista inteira: num mapa de
        500 blocos com alguns personagens, são dezenas de milhares de
        comparações por quadro, e o jogo engasga. Aqui a lista é varrida uma
        vez por eixo, montando a caixa que envolve o começo e o fim do
        movimento.

        A margem não é enfeite: ao bater num bloco, o objeto é reposicionado
        encostado nele, e esse reposicionamento pode jogá-lo até a largura de
        um bloco para fora da caixa. A margem cobre esse deslocamento, para o
        eixo seguinte não perder o chão de vista.
        """
        if len(lista_solidos) <= 12:
            return lista_solidos          # não compensa filtrar

        margem = max(objeto.width, objeto.height)
        x0 = min(objeto.x, objeto.x + dx) - margem
        y0 = min(objeto.y, objeto.y + dy) - margem
        x1 = max(objeto.x, objeto.x + dx) + objeto.width + margem
        y1 = max(objeto.y, objeto.y + dy) + objeto.height + margem

        # A lista de um TileMap sabe responder por região (ver
        # tilemap.ListaSolidos) e essa resposta custa o tamanho da vizinhança,
        # e não o do mapa. Era aqui que o jogo gastava quase um terço do
        # quadro: quinhentos blocos comparados catorze vezes por quadro para
        # encontrar os poucos ao redor do personagem.
        #
        # Qualquer outra lista — a do aluno, ou a soma de duas camadas — não
        # tem o método e segue pela varredura de sempre, sem mudança nenhuma.
        por_regiao = getattr(lista_solidos, "perto", None)
        if por_regiao is not None:
            return por_regiao(x0, y0, x1, y1)

        perto = []
        for solido in lista_solidos:
            if (solido.x < x1 and solido.x + solido.width > x0 and
                    solido.y < y1 and solido.y + solido.height > y0):
                perto.append(solido)
        return perto

    def processar_movimento(self, objeto, lista_solidos):
        from .window import Window
        dt = Window.get_instance().delta_time()

        # 1. Gravidade
        objeto.vy += self.gravidade * dt
        if objeto.vy > self.vel_terminal:
            objeto.vy = self.vel_terminal

        # 2. Deslocamentos
        dx = objeto.vx * dt
        dy = objeto.vy * dt

        # 3. Cada eixo olha só os blocos que pode alcançar. O filtro do eixo Y
        #    é refeito depois do X, porque o X pode ter reposicionado o objeto.
        perto_x = self._candidatos(objeto, dx, 0, lista_solidos)

        # A colisão usa a caixa do objeto, que pode ser menor que o quadro do
        # sprite. `folga_*` é a distância entre o canto do quadro e o canto da
        # caixa: é por ela que se volta da caixa para a posição do objeto.
        folga_e, folga_t, folga_d, folga_b = getattr(objeto, "margem_colisao", (0, 0, 0, 0))
        largura = getattr(objeto, "caixa_largura", objeto.width)
        altura = getattr(objeto, "caixa_altura", objeto.height)

        # --- EIXO X (Horizontal) ---
        passos_x = int(abs(dx) / self._passo()) + 1
        dist_por_passo_x = dx / passos_x

        for _ in range(passos_x):
            proximo_x = objeto.x + dist_por_passo_x
            solido = self._primeiro_solido(proximo_x + folga_e, objeto.y + folga_t,
                                           largura, altura, perto_x)
            if solido is not None:
                # Encaixe exato ao lado do bloco, sem folga extra
                if dist_por_passo_x > 0:
                    objeto.x = solido.x - largura - folga_e
                elif dist_por_passo_x < 0:
                    objeto.x = solido.x + solido.width - folga_e
                objeto.vx = 0
                break
            objeto.x = proximo_x

        # --- EIXO Y (Vertical) ---
        perto_y = self._candidatos(objeto, 0, dy, lista_solidos)
        passos_y = int(abs(dy) / self._passo()) + 1
        dist_por_passo_y = dy / passos_y

        objeto.no_chao = False
        for _ in range(passos_y):
            proximo_y = objeto.y + dist_por_passo_y
            solido = self._primeiro_solido(objeto.x + folga_e, proximo_y + folga_t,
                                           largura, altura, perto_y)
            if solido is not None:
                if dist_por_passo_y > 0:      # caindo: pousa no topo
                    objeto.y = solido.y - altura - folga_t
                    objeto.no_chao = True
                elif dist_por_passo_y < 0:    # subindo: bate no teto
                    objeto.y = solido.y + solido.height - folga_t
                objeto.vy = 0
                break
            objeto.y = proximo_y

class KinematicBody:
    """Componente Pro: Gerencia inércia e 'Input Buffering' para pulos perfeitos."""
    def __init__(self, sprite, physics_engine, controlavel=True):
        self.sprite = sprite
        self.engine = physics_engine

        # Se False, o corpo IGNORA o teclado. Dirija-o com mover() e pular().
        # Isso impede que inimigos com física respondam às setas do jogador.
        self.controlavel = controlavel
        self._direcao = 0          # preenchido por mover() quando não controlável
        self._direcao_y = 0        # idem, para o eixo vertical (visto de cima)
        self._pulo_pedido = False  # preenchido por pular()

        # Configurações de Movimento.
        # Calibradas para tiles de 32 px numa janela de 640x360: o herói
        # atravessa a tela em pouco mais de 3 s e o pulo alcança 3 blocos.
        # Para um jogo maior, aumente proporcionalmente.
        self.accel = 2200
        self.friccao = 0.22
        self.pulo = 620
        self.max_vel_x = 190

        # --- JUMP FEELING (A MÁGICA) ---
        self.coyote_timer = 0
        self.coyote_max = 0.15 # 150ms de tolerância após sair da plataforma

        self.jump_buffer_timer = 0
        self.jump_buffer_max = 0.15 # 150ms de memória para o botão de pulo

        # True apenas no quadro em que o pulo foi de fato executado.
        # É o gancho para tocar o som de pulo ou soltar partículas.
        self.pulou = False

    @property
    def visto_de_cima(self):
        """
        True quando o jogo não tem gravidade.

        Sem gravidade não existe chão, e portanto não existe pulo: as setas de
        cima e de baixo, que num jogo de plataforma pulam, aqui andam. É a
        diferença entre um jogo de plataforma e um visto de cima, e ela cabe
        num único teste porque tudo o mais é igual.
        """
        return abs(self.engine.gravidade) < 1.0

    def _freada(self, dt):
        """
        Quanto da velocidade sobra depois de um quadro sem acelerar.

        `friccao` foi escrita pensando em 60 quadros por segundo: a cada
        quadro sobrava 78% da velocidade. Aplicada assim, crua, ela dependia
        do computador — a 144 fps o personagem freava na metade da distância,
        a 30 fps deslizava o dobro. Elevar ao número de quadros que caberiam
        no tempo decorrido tira essa dependência e deixa o resultado a 60 fps
        igual ao que sempre foi.
        """
        sobra = max(0.0, min(1.0, 1 - self.friccao))
        if sobra <= 0:
            return 0.0
        return sobra ** max(0.0, dt * 60.0)

    def mover(self, direcao):
        """
        Define a direção horizontal desejada: -1, 0 ou +1.

        Vale até alguém mudar: um inimigo mandado para a direita continua indo
        para a direita sozinho. O `mover_vertical` é o oposto, e de propósito.
        """
        self._direcao = max(-1, min(1, int(direcao)))

    def mover_vertical(self, direcao):
        """
        Direção vertical desejada num jogo visto de cima: -1, 0 ou +1.

        Ao contrário do `mover`, vale por um quadro só: quem quer subir sem
        parar chama isto a cada volta do laço. A diferença existe porque o
        movimento vertical é uma adição ao modelo de plataforma, e mudar o
        `mover` para o mesmo comportamento quebraria todo inimigo já escrito.
        """
        self._direcao_y = max(-1, min(1, int(direcao)))

    def pular(self):
        """Solicita um pulo. Respeita coyote time e jump buffer."""
        self._pulo_pedido = True

    def update(self, lista_solidos):
        from .window import Window
        janela = Window.get_instance()
        teclado = janela.keyboard
        dt = janela.delta_time()

        # 0. De onde vem a intenção: teclado (jogador) ou código (IA)
        self.pulou = False

        de_cima = self.visto_de_cima

        if self.controlavel:
            dir = 0
            if teclado.key_pressed("left"): dir = -1
            if teclado.key_pressed("right"): dir = 1
            dir_y = 0
            if de_cima:
                if teclado.key_pressed("up"): dir_y = -1
                if teclado.key_pressed("down"): dir_y = 1
            pulo_apertado = (not de_cima) and (teclado.key_down("space") or teclado.key_down("up"))
            pulo_segurado = teclado.key_pressed("space") or teclado.key_pressed("up")
        else:
            dir = self._direcao
            dir_y = self._direcao_y
            pulo_apertado = self._pulo_pedido
            # Sem teclado, o pulo variável é desligado: a subida vale integralmente
            pulo_segurado = True
        self._pulo_pedido = False
        self._direcao_y = 0

        # 1. Movimento Horizontal
        if dir != 0:
            self.sprite.vx += dir * self.accel * dt
        else:
            self.sprite.vx *= self._freada(dt)

        if abs(self.sprite.vx) > self.max_vel_x:
            self.sprite.vx = self.max_vel_x * (1 if self.sprite.vx > 0 else -1)

        # 1b. Movimento vertical, só no jogo visto de cima. Usa a mesma
        # aceleração e a mesma fricção do eixo horizontal, para andar na
        # diagonal não dar a impressão de dois personagens diferentes.
        if de_cima:
            if dir_y != 0:
                self.sprite.vy += dir_y * self.accel * dt
            else:
                self.sprite.vy *= self._freada(dt)
            if abs(self.sprite.vy) > self.max_vel_x:
                self.sprite.vy = self.max_vel_x * (1 if self.sprite.vy > 0 else -1)

        # 2. Lógica de Pulo com Tolerância (Coyote Time & Buffer).
        # Num jogo visto de cima não há para onde pular, e deixar o bloco rodar
        # daria um solavanco vertical a cada toque na seta de cima.
        
        # Update Coyote Timer (Tempo no chão)
        if self.sprite.no_chao:
            self.coyote_timer = self.coyote_max
        else:
            self.coyote_timer -= dt

        # Update Jump Buffer (Memória do botão)
        if pulo_apertado:
            self.jump_buffer_timer = self.jump_buffer_max
        else:
            self.jump_buffer_timer -= dt

        # Executa o pulo se ambas as condições de satisfação forem atendidas
        if not de_cima and self.jump_buffer_timer > 0 and self.coyote_timer > 0:
            self.sprite.vy = -self.pulo
            self.sprite.no_chao = False
            self.pulou = True
            self.coyote_timer = 0       # Consome a tolerância
            self.jump_buffer_timer = 0  # Consome o buffer
            
        # Pulo Variável (Soltar o botão corta a subida - opcional)
        if not de_cima and not pulo_segurado and self.sprite.vy < -300:
            self.sprite.vy = -300

        # 3. Processar a Física
        self.engine.processar_movimento(self.sprite, lista_solidos)