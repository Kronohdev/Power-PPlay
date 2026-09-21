import pygame
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

class Keyboard:
    def __init__(self):
        # Mapeamento estendido para facilitar a vida do aluno
        self.mapa = {
            "LEFT": pygame.K_LEFT, "RIGHT": pygame.K_RIGHT,
            "UP": pygame.K_UP, "DOWN": pygame.K_DOWN,
            "SPACE": pygame.K_SPACE, "ESC": pygame.K_ESCAPE,
            "ESCAPE": pygame.K_ESCAPE,
            "ENTER": pygame.K_RETURN, "RETURN": pygame.K_RETURN,
            "LSHIFT": pygame.K_LSHIFT, "RSHIFT": pygame.K_RSHIFT,
            "SHIFT": pygame.K_LSHIFT, "CTRL": pygame.K_LCTRL,
            "LCTRL": pygame.K_LCTRL, "RCTRL": pygame.K_RCTRL,
            "ALT": pygame.K_LALT, "TAB": pygame.K_TAB,
            "BACKSPACE": pygame.K_BACKSPACE, "DELETE": pygame.K_DELETE,
        }
        # F1 a F12: o pygame chama de K_F1..K_F12 (maiusculo), ao contrario
        # das letras, que sao K_a..K_z. Sem isto, key_pressed("f1") era
        # sempre falso.
        for n in range(1, 13):
            self.mapa[f"F{n}"] = getattr(pygame, f"K_F{n}")

    def _get_code(self, key):
        """Aceita 'a', 'A', 'SPACE', 'f1', 'F1' ou o codigo cru do pygame."""
        if not isinstance(key, str):
            return key
        nome = key.upper()
        if nome in self.mapa:
            return self.mapa[nome]
        # letras e digitos sao minusculos no pygame (K_a, K_7);
        # os demais nomes sao maiusculos (K_HOME, K_PAGEUP).
        codigo = getattr(pygame, f"K_{key.lower()}", None)
        if codigo is None:
            codigo = getattr(pygame, f"K_{nome}", None)
        return codigo

    def key_pressed(self, key):
        """Verifica se a tecla está sendo segurada (Input contínuo)."""
        codigo = self._get_code(key)
        return pygame.key.get_pressed()[codigo] if codigo else False

    def key_down(self, key):
        """Verifica se a tecla foi apertada NESTE frame (Único)."""
        codigo = self._get_code(key)
        janela = Window.get_instance()
        for evento in janela.eventos:
            if evento.type == pygame.KEYDOWN and evento.key == codigo:
                return True
        return False

    def draw_debug(self, x=10, y=10):
        """Debug: Mostra teclas detectadas no frame."""
        janela = Window.get_instance()
        for evento in janela.eventos:
            if evento.type == pygame.KEYDOWN:
                janela.draw_text(f"Tecla: {pygame.key.name(evento.key)}", x, y, cor="red")