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

class InputManager:
    """
    Gerenciador de Ações. Permite mapear múltiplas teclas para uma única ação.
    """
    _mapa_acoes = {}

    @classmethod
    def define_action(cls, nome_acao, lista_teclas):
        """
        Mapeia um nome (ex.: 'pulo') a uma ou varias teclas.

            InputManager.define_action("pulo", ["space", "up", "w"])
            InputManager.define_action("pausa", "escape")

        Uma tecla sozinha, em vez de uma lista, e aceita de proposito: escrever
        `define_action("pausa", "escape")` e o erro mais natural do mundo, e
        antes ele passava calado — a string virava uma lista de letras, e a
        acao nunca disparava porque ninguem aperta a tecla "e" esperando pausar
        o jogo.
        """
        if isinstance(lista_teclas, str):
            lista_teclas = [lista_teclas]
        cls._mapa_acoes[nome_acao] = list(lista_teclas)

    @classmethod
    def acoes(cls):
        """O mapa de acoes, como esta agora."""
        return {nome: list(teclas) for nome, teclas in cls._mapa_acoes.items()}

    @classmethod
    def limpar(cls):
        """Esquece todas as acoes."""
        cls._mapa_acoes = {}

    @classmethod
    def is_active(cls, nome_acao):
        """Verifica se qualquer uma das teclas mapeadas para a ação está pressionada."""
        from .window import Window
        teclado = Window.get_instance().keyboard
        
        if nome_acao not in cls._mapa_acoes:
            return False
            
        for tecla in cls._mapa_acoes[nome_acao]:
            if teclado.key_pressed(tecla):
                return True
        return False

    @classmethod
    def action_pressed(cls, nome_acao):
        """Verifica se a ação foi disparada (apenas o primeiro frame)."""
        from .window import Window
        teclado = Window.get_instance().keyboard
        
        if nome_acao not in cls._mapa_acoes:
            return False
            
        for tecla in cls._mapa_acoes[nome_acao]:
            if teclado.key_down(tecla):
                return True
        return False