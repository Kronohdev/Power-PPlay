"""
===============================================================================
POWER PPLAY 2.1 - AS FONTES DO JOGO
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Um lugar só para as fontes, e um motivo claro para ele existir.

Até aqui toda letra do jogo saía de `pygame.font.SysFont("Arial", ...)`. Isso
tem três problemas, e os três aparecem no mesmo dia:

1. **A fonte é do computador, não do jogo.** `SysFont` procura a família pelo
   nome no sistema. Se ela não estiver lá, o pygame devolve a fonte padrão sem
   avisar --- e o jogo que estava lindo na sua máquina abre com outra letra na
   do professor. Num jogo de pixel art, com uma fonte de pixel escolhida a
   dedo, isso não é um detalhe: é o jogo inteiro parecendo outro.

2. **Não dava para usar a fonte que você baixou.** Um `.ttf` na pasta do
   projeto era invisível para a engine.

3. **No navegador não existe fonte do sistema.** O jogo exportado para a web
   roda num interpretador dentro da aba, sem as fontes do Windows. `SysFont`
   ali devolve sempre a mesma letra genérica.

Um arquivo `.ttf` ou `.otf` dentro do projeto resolve os três de uma vez: ele
viaja com o jogo, é o mesmo em toda máquina e funciona no navegador.

-------------------------------------------------------------------------------
COMO SE USA

    from PPlay.fontes import Fontes

    Fontes.registrar("Pixel", "assets/fontes/pixel.ttf")

    Label("Vidas: 3", tamanho=18, fonte="Pixel")
    janela.draw_text("Pontos: 0", 12, 12, fonte="Pixel")

`registrar` só guarda o caminho --- não abre o arquivo e não precisa do pygame
inicializado. A fonte é criada na primeira vez que alguém a pede, e guardada
num cache por (nome, tamanho, negrito), porque criar uma fonte custa caro e o
jogo pede a mesma sessenta vezes por segundo.

Um nome que ninguém registrou continua indo para o `SysFont` de sempre: é o que
mantém funcionando todo código escrito antes deste arquivo existir.

-------------------------------------------------------------------------------
O ARQUIVO SUMIU: O QUE ACONTECE

Cai na fonte do sistema e avisa UMA vez no console. Não estoura, porque um jogo
que morre na tela de abertura por causa de uma letra é pior do que um jogo com
a letra errada --- e o aviso diz exatamente qual arquivo faltou.
===============================================================================
"""

import os

import pygame

# O que a engine usa quando ninguém escolheu nada. É uma família do sistema, e
# não um arquivo: a engine não carrega fonte nenhuma consigo.
PADRAO = "Arial"

EXTENSOES = (".ttf", ".otf", ".ttc")


class Fontes:
    """Registro das fontes do jogo, com cache."""

    _arquivos = {}      # nome -> caminho do .ttf/.otf
    _cache = {}         # (nome, tamanho, negrito) -> pygame.font.Font
    _reclamados = set()  # nomes cujo arquivo já foi dado como sumido

    # ------------------------------------------------------------------
    # REGISTRO
    # ------------------------------------------------------------------
    @classmethod
    def registrar(cls, nome, caminho):
        """
        Dá um nome a um arquivo de fonte. Devolve o nome.

        Não abre o arquivo: registrar é barato de propósito, para poder
        acontecer no topo de um módulo, antes de o pygame existir.
        """
        nome = str(nome).strip()
        if not nome:
            return None
        cls._arquivos[nome] = str(caminho).replace("\\", "/")
        # Trocar o arquivo de um nome já usado tem de invalidar o que foi
        # desenhado com o anterior.
        cls._cache = {c: f for c, f in cls._cache.items() if c[0] != nome}
        cls._reclamados.discard(nome)
        return nome

    @classmethod
    def registrar_muitas(cls, mapa):
        """`Fontes.registrar_muitas({'Pixel': 'assets/fontes/pixel.ttf'})`."""
        for nome, caminho in dict(mapa).items():
            cls.registrar(nome, caminho)

    @classmethod
    def registradas(cls):
        """`{nome: caminho}` do que foi registrado até agora."""
        return dict(cls._arquivos)

    @classmethod
    def arquivo_de(cls, nome):
        """O caminho do arquivo desta fonte, ou None se for do sistema."""
        return cls._arquivos.get(str(nome).strip())

    @classmethod
    def esquecer_todas(cls):
        """Limpa registro e cache. Usado por testes e ao trocar de projeto."""
        cls._arquivos.clear()
        cls._cache.clear()
        cls._reclamados.clear()

    # ------------------------------------------------------------------
    # USO
    # ------------------------------------------------------------------
    @classmethod
    def obter(cls, nome=None, tamanho=20, negrito=False):
        """
        A fonte pronta para renderizar. Nunca devolve None.

        `nome` pode ser uma fonte registrada, uma família do sistema, ou None
        para o padrão.
        """
        nome = (str(nome).strip() if nome else "") or PADRAO
        tamanho = max(1, int(tamanho or 1))
        negrito = bool(negrito)

        chave = (nome, tamanho, negrito)
        pronta = cls._cache.get(chave)
        if pronta is not None:
            return pronta

        if not pygame.font.get_init():
            pygame.font.init()

        fonte = cls._do_arquivo(nome, tamanho, negrito)
        if fonte is None:
            fonte = pygame.font.SysFont(nome, tamanho, negrito)
        cls._cache[chave] = fonte
        return fonte

    @classmethod
    def _do_arquivo(cls, nome, tamanho, negrito):
        """A fonte vinda de um arquivo registrado, ou None."""
        caminho = cls._arquivos.get(nome)
        if not caminho:
            return None
        if not os.path.isfile(caminho):
            cls._reclamar(nome, caminho, "não achei o arquivo")
            return None
        try:
            fonte = pygame.font.Font(caminho, tamanho)
        except (OSError, pygame.error) as erro:
            cls._reclamar(nome, caminho, erro)
            return None
        if negrito:
            # Um arquivo de fonte traz um peso só. `set_bold` engrossa o
            # desenho por conta própria — não é o mesmo que a versão negrito
            # da família, mas é o que existe, e é melhor do que ignorar.
            fonte.set_bold(True)
        return fonte

    @classmethod
    def _reclamar(cls, nome, caminho, motivo):
        if nome in cls._reclamados:
            return
        cls._reclamados.add(nome)
        print("[Power PPlay] a fonte '%s' não pôde ser carregada de '%s' (%s); "
              "usando a fonte do sistema" % (nome, caminho, motivo))


def registrar(nome, caminho):
    """Atalho de módulo: `from PPlay.fontes import registrar`."""
    return Fontes.registrar(nome, caminho)


def obter(nome=None, tamanho=20, negrito=False):
    """Atalho de módulo."""
    return Fontes.obter(nome, tamanho, negrito)
