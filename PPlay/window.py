import pygame
import sys
# As constantes (QUIT, KEYDOWN, K_F11) são lidas como pygame.QUIT, e não
# importadas de pygame.locals. O motivo é a exportação para a web: o compilador
# não resolve o nome "pygame.locals" — procura um pacote com esse nome no PyPI,
# não acha, e o jogo não sobe. Como atributo do pacote, a leitura acontece em
# tempo de execução e funciona nos dois lugares.

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

def _pygame_iniciado():
    """
    O pygame já foi iniciado?

    `pygame.get_init()` não existe no pygame compilado para WebAssembly, onde
    o pacote é montado aos poucos. Sem a resposta, dizemos que não: chamar
    `pygame.init()` de novo não custa nada nem desfaz o que já está feito.
    """
    consultar = getattr(pygame, "get_init", None)
    if consultar is None:
        return False
    try:
        return bool(consultar())
    except Exception:  # noqa: BLE001
        return False


class Window:
    """
    POWER PPLAY 2.1 - Janela de Alta Performance e Resolução Virtual.
    Versão 2.6.2: Blindada contra erros de escalonamento e minimização.
    """
    _instance = None 
    screen = None # Atributo estático para compatibilidade legada

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Window, cls).__new__(cls)
        return cls._instance

    def __init__(self, largura_virtual=800, altura_virtual=600, titulo="Power PPlay 2.1", resizavel=True, pixel_art=True, fps=60, intro=None):
        """
        `intro` liga ou desliga a abertura animada da engine (ver PPlay/intro.py).

        O padrão é `None`, e não `True`, porque quem decide nesse caso é o
        ambiente: a variável PPLAY_SEM_INTRO desliga a abertura na máquina
        inteira. Passar `False` aqui desliga só neste jogo — é o que a IDE
        escreve no main.py quando o projeto pede.
        """
        if hasattr(self, '_already_init'):
            return

        if not _pygame_iniciado():
            # O formato do áudio tem de ser anunciado ANTES do pygame.init():
            # depois, o mixer já está aberto e o pedido é ignorado.
            from .sound import SoundManager
            SoundManager.preparar()
            pygame.init()

        # Resolução interna do jogo
        self.largura = largura_virtual
        self.altura = altura_virtual
        self.titulo = titulo
        self.pixel_art = pixel_art

        # Teto de quadros por segundo. 0 = sem limite (roda o mais rápido que
        # a máquina permitir e esquenta o notebook à toa).
        self.fps_limite = fps

        self._clock = pygame.time.Clock()
        self._delta_time = 0
        self.eventos = []
        self.cor_fundo = (0, 0, 0)

        # Configura flags de vídeo
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
        if resizavel:
            flags |= pygame.RESIZABLE
            
        # Cria a janela real do Windows
        self.real_screen = pygame.display.set_mode([self.largura, self.altura], flags)
        
        # Cria o Buffer Virtual (Canvas)
        self.screen = pygame.Surface((self.largura, self.altura))
        Window.screen = self.screen # Sincroniza atributo estático
        
        pygame.display.set_caption(self.titulo)
        
        # Subsistemas
        from .keyboard import Keyboard
        from .mouse import Mouse
        self.keyboard = Keyboard()
        self.mouse = Mouse()
        
        self._already_init = True

        # A abertura da engine, por último: a janela já existe, os subsistemas
        # já estão de pé, e se algo aqui falhar o jogo continua inteiro. Ela
        # desenha na tela REAL, e não no buffer virtual — é o único desenho da
        # engine que não passa pela escala do jogo, para a marca sair nítida
        # numa janela grande em vez de ampliada de 640×360.
        # O `try` nao e zelo excessivo: projetos criados antes da abertura
        # existir tem uma copia da engine SEM o intro.py dentro deles, e um
        # ImportError aqui mataria um jogo que funcionava. Sem o modulo, nao ha
        # abertura — e so.
        try:
            from .intro import abrir as _abrir_intro
        except ImportError:
            _abrir_intro = None
        if _abrir_intro is not None:
            _abrir_intro(self.real_screen, ativa=intro)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            Window()
        return cls._instance

    @classmethod
    def get_screen(cls):
        return cls.get_instance().screen

    def update(self):
        """Finaliza o desenho e projeta na tela real com proteção contra crash."""
        largura_real, altura_real = self.real_screen.get_size()
        
        # PROTEÇÃO: Se a janela estiver minimizada (tamanho 0), não tenta desenhar
        if largura_real < 1 or altura_real < 1:
            pygame.display.flip()
            self._delta_time = self._clock.tick(self.fps_limite) / 1000.0
            self.eventos = pygame.event.get()
            return

        # Cálculo do escalonamento mantendo Aspect Ratio
        ratio = min(largura_real / self.largura, altura_real / self.altura)
        nova_w = max(1, int(self.largura * ratio))
        nova_h = max(1, int(self.altura * ratio))
        pos_x = (largura_real - nova_w) // 2
        pos_y = (altura_real - nova_h) // 2
        
        # Preenche fundo (faixas pretas). Quando a imagem cobre a tela inteira
        # nao ha faixa nenhuma para pintar, e pintar mesmo assim e um quadro
        # inteiro de trabalho jogado fora todo quadro.
        if pos_x or pos_y or nova_w != largura_real or nova_h != altura_real:
            self.real_screen.fill((0, 0, 0))
        
        # Tenta realizar o redimensionamento com tratamento de erro
        try:
            if nova_w == self.largura and nova_h == self.altura:
                # A janela tem exatamente o tamanho da tela virtual — o caso
                # mais comum, porque e assim que a janela nasce. Escalar de
                # 640x360 para 640x360 nao muda pixel nenhum, mas aloca uma
                # superficie nova e a copia inteira: media, era o maior item do
                # quadro, mais caro que desenhar os cento e vinte sprites.
                # Aqui o buffer vai direto para a tela.
                self.real_screen.blit(self.screen, (pos_x, pos_y))
            elif self.pixel_art:
                scaled = pygame.transform.scale(self.screen, (nova_w, nova_h))
                self.real_screen.blit(scaled, (pos_x, pos_y))
            else:
                scaled = pygame.transform.smoothscale(self.screen, (nova_w, nova_h))
                self.real_screen.blit(scaled, (pos_x, pos_y))
        except pygame.error:
            # Fallback caso o transform falhe por algum motivo de hardware
            self.real_screen.blit(self.screen, (0, 0))
            
        pygame.display.flip()
        
        # Limpa o buffer para o próximo frame
        self.screen.fill(self.cor_fundo)
        
        # Eventos
        self.eventos = pygame.event.get()
        for ev in self.eventos:
            if ev.type == pygame.QUIT:
                self.close()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

        # Sincroniza o tempo (Delta Time) respeitando o teto de FPS
        self._delta_time = self._clock.tick(self.fps_limite) / 1000.0

    def delta_time(self):
        return self._delta_time

    def set_fps_limit(self, fps):
        """Define o teto de quadros por segundo. Use 0 para desativar o limite."""
        self.fps_limite = max(0, int(fps))

    def get_fps(self):
        return self._clock.get_fps()

    def set_background_color(self, cor):
        if isinstance(cor, str):
            try: self.cor_fundo = pygame.Color(cor)
            except: self.cor_fundo = (0,0,0)
        else:
            self.cor_fundo = cor

    def draw_text(self, texto, x, y, tamanho=20, cor=(255, 255, 255), fonte=None):
        """
        Escreve na tela, em coordenadas de tela.

        `fonte` aceita o nome de uma fonte registrada em PPlay.fontes (um .ttf
        que viaja com o jogo) ou uma família do sistema. None usa o padrão.
        """
        try:
            from .fontes import Fontes
            img = Fontes.obter(fonte, tamanho).render(str(texto), True, cor)
            self.screen.blit(img, (x, y))
        except Exception:
            # Escrever um texto nunca pode derrubar o quadro: na pior das
            # hipóteses o jogo continua sem essa linha.
            pass

    def screen_to_virtual_coords(self, px, py):
        lw, lh = self.real_screen.get_size()
        if lw < 1 or lh < 1: return px, py
        ratio = min(lw / self.largura, lh / self.altura)
        vx = (px - (lw - self.largura * ratio) // 2) / ratio
        vy = (py - (lh - self.altura * ratio) // 2) / ratio
        return vx, vy

    def close(self):
        pygame.quit()
        sys.exit()