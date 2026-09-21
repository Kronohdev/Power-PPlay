"""
===============================================================================
POWER PPLAY 2.1 - RETRO-COMPATIBILITY BRIDGE v2.2
===============================================================================
Correção de Métodos de Classe e Atributos Estáticos.
Mapeia o comportamento da 1.0 injetando lógica na 2.0.
===============================================================================
"""
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

_ponte_aplicada = False


def aplicar_retrocompatibilidade():
    # Guarda de idempotência: o __init__.py também chama esta função, e sem
    # isto a ponte era aplicada (e anunciada) duas vezes por execução.
    global _ponte_aplicada
    if _ponte_aplicada:
        return
    _ponte_aplicada = True

    try:
        from .window import Window
        from .mouse import Mouse
        from .keyboard import Keyboard
        from .animation import Animation
        from .sound import Sound
        from .sprite import Sprite
        from .gameimage import GameImage
        from .collision import Collision
    except ImportError:
        return

    # --- 1. WINDOW: TRADUÇÃO DE ATRIBUTOS E CLASSMETHODS ---
    
    # Redireciona Window.width -> Window.largura (Instância)
    Window.width = property(lambda self: self.largura)
    Window.height = property(lambda self: self.altura)

    # Injeção de Métodos de Classe (Corrigindo o erro de missing 'cls')
    Window.get_keyboard = classmethod(lambda cls: cls.get_instance().keyboard)
    Window.get_mouse = classmethod(lambda cls: cls.get_instance().mouse)
    
    # Métodos de Instância Legados
    Window.set_title = lambda self, t: pygame.display.set_caption(t)
    Window.delay = lambda self, ms: pygame.time.delay(ms)
    Window.time_elapsed = lambda self: pygame.time.get_ticks()
    Window.clear = lambda self: [self.set_background_color((255,255,255)), self.update()]

    # Draw Text Híbrido: aceita a assinatura POSICIONAL da 2.0
    # (texto, x, y, tamanho, cor, fonte) E os nomes da 1.0 (size, color,
    # font_name, bold, italic). O padrão continua branco, como na 2.0.
    def draw_text_compat(self, texto, x, y, tamanho=20, cor=(255, 255, 255),
                         fonte="Arial", **kwargs):
        size = kwargs.get('size', tamanho)
        color = kwargs.get('color', cor)
        font_name = kwargs.get('font_name', fonte)
        bold = kwargs.get('bold', False)
        italic = kwargs.get('italic', False)
        try:
            f = pygame.font.SysFont(font_name, int(size), bold, italic)
            self.screen.blit(f.render(str(texto), True, color), [x, y])
        except Exception:
            pass
    Window.draw_text = draw_text_compat

    # --- 2. INPUTS: TRADUÇÃO DE TECLAS E BOTÕES ---
    # Algumas versões da 1.0 aceitavam 'LEFT' (string) ou constantes. 
    # Nossa 2.0 já trata strings, então aqui apenas mapeamos métodos.
    Keyboard.key_pressed_legacy = lambda self, k: self.key_pressed(k)
    # Patch para o método show_key_pressed que o PPlay 1.0 possuía
    def show_key_legacy(self):
        for e in Window.get_instance().eventos:
            if e.type == pygame.KEYDOWN: print(e.key)
    Keyboard.show_key_pressed = show_key_legacy

    # Constantes do Mouse
    Mouse.BUTTON_LEFT = 1; Mouse.BUTTON_MIDDLE = 2; Mouse.BUTTON_RIGHT = 3
    Mouse.WHEEL_UP = 4; Mouse.WHEEL_DOWN = 5
    # Traduz click.is_button_pressed(True) -> click.button_pressed(1)
    Mouse.is_button_pressed = lambda self, b: self.button_pressed(1 if b is True else b)
    Mouse.set_position = lambda self, x, y: pygame.mouse.set_pos([x, y])
    Mouse.hide = lambda self: pygame.mouse.set_visible(False)
    Mouse.unhide = lambda self: pygame.mouse.set_visible(True)
    Mouse.is_over_area = lambda self, sp, ep: (sp[0] <= self.get_position()[0] <= ep[0]) and (sp[1] <= self.get_position()[1] <= ep[1])

    # --- 3. ANIMAÇÃO E SPRITE ---
    # Traduz o sistema de fatiamento de tempo da 1.0
    # Na PPlay 1.0 o 'final_frame' é EXCLUSIVO (set_sequence(0, total_frames)
    # toca a folha inteira), enquanto o intervalo da 2.1 é inclusivo — daí o
    # 'end - 1'. Antes estes dois métodos recebiam start/end e os descartavam
    # em silêncio: a animação continuava rodando a folha toda.
    def set_sequence_legacy(self, start, end, loop=True):
        self.set_loop(loop)
        self.set_intervalo_frames(start, end - 1)
        self.frame_atual = self.frame_inicial

    def set_sequence_time_legacy(self, start, end, duration, loop=True):
        set_sequence_legacy(self, start, end, loop)
        # Na 1.0 a duração vale para o TRECHO escolhido, não para a folha
        # inteira; por isso o tempo de cada quadro sai da conta do trecho.
        quadros = max(1, self.frame_final - self.frame_inicial + 1)
        self.tempo_por_frame = (duration / 1000.0) / quadros

    Animation.set_sequence_time = set_sequence_time_legacy
    Animation.set_sequence = set_sequence_legacy
    Animation.hide = lambda self: setattr(self, 'drawable', False)
    Animation.unhide = lambda self: setattr(self, 'drawable', True)

    # --- 4. COLISÃO E IMAGEM ---
    Collision.collided_perfect = lambda obj1, obj2: Collision.perfect_collision(obj1, obj2)
    GameImage.collided_perfect = lambda self, target: Collision.perfect_collision(self, target)

    print("[Power PPlay 2.1] Ponte v2.4 ativa: Métodos de classe vinculados.")

# A ativação é feita pelo PPlay/__init__.py. Não chame aqui: ao importar este
# módulo diretamente a ponte rodaria duas vezes.