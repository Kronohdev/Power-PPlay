"""
===============================================================================
POWER PPLAY 2.1 - ONDE O JOGO ESTÁ RODANDO
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Por que este módulo existe:

Um jogo exportado para a web roda sobre um pygame compilado para WebAssembly,
e ele não é idêntico ao do computador. A diferença que mais dói aparece cedo:
antes de `pygame.init()`, aquele pygame é quase um esboço vazio — `get_init`,
`error` e `mixer` ainda não existem. Cada um derruba o jogo num ponto
diferente, e sair caçando atributo por atributo nunca termina.

Perguntar uma vez onde estamos resolve a classe inteira: o que é decisão do
computador (formato do mixer, escolha de placa de som, medir a saída) o
navegador decide sozinho, e simplesmente não se faz lá.

    from .ambiente import no_navegador

    if not no_navegador():
        SoundManager.preparar()
===============================================================================
"""

import sys


def no_navegador():
    """
    O jogo está rodando dentro de um navegador?

    O pygbag executa sobre Emscripten, e é isso que `sys.platform` informa —
    "emscripten" em vez de "win32" ou "linux".
    """
    return sys.platform == "emscripten"


def descricao():
    """Uma linha dizendo onde o jogo está, para mensagens de diagnóstico."""
    return "navegador (WebAssembly)" if no_navegador() else sys.platform
