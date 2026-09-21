import pygame
from .gameobject import GameObject
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

class GameImage(GameObject):
    """
    GameImage cuida de carregar, armazenar e desenhar imagens na tela.
    Inclui um sistema de cache para evitar carregamentos redundantes do disco.
    """
    
    # Nosso "Almoxarifado" de imagens (Cache)
    # Chave: nome do arquivo, Valor: superfície do pygame carregada
    _resource_cache = {}

    # Versões espelhadas, feitas sob encomenda e guardadas.
    # Chave: (nome do arquivo, colunas, linhas)
    _espelho_cache = {}

    def __init__(self, caminho_imagem):
        super().__init__()
        self.caminho = caminho_imagem
        self.espelhado = False
        # Marca lida pelo draw(). Existe para os hide()/unhide() da PPlay 1.0,
        # que a ponte de retrocompatibilidade continua oferecendo.
        self.drawable = True

        # Tenta buscar do cache primeiro
        if caminho_imagem in GameImage._resource_cache:
            self.image = GameImage._resource_cache[caminho_imagem]
        else:
            # Se não estiver lá, carrega do disco e otimiza
            try:
                # convert_alpha() faz o blit ser até 5x mais rápido
                self.image = pygame.image.load(caminho_imagem).convert_alpha()
                # Guarda no cache para o próximo objeto que pedir
                GameImage._resource_cache[caminho_imagem] = self.image
            except (pygame.error, OSError):
                # OSError entra junto porque o erro MAIS comum — nome de
                # arquivo errado — chega como FileNotFoundError, que não é um
                # pygame.error: a rede de segurança abaixo nunca era usada
                # justamente no caso para o qual foi escrita, e o jogo do
                # aluno morria no carregamento.
                print(f"ERRO: Não foi possível carregar a imagem: {caminho_imagem}")
                # Cria uma superfície rosa choque temporária para não crashar o jogo
                self.image = pygame.Surface((32, 32))
                self.image.fill((255, 0, 255))

        # Define as dimensões do GameObject baseadas na imagem
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        
        # Rect interno para operações do Pygame
        self.rect = self.image.get_rect()

    # =====================================================================
    # ESPELHAMENTO HORIZONTAL
    # =====================================================================
    def ajustar_caixa_a_arte(self, folga=0):
        """
        Encolhe a caixa de colisão até onde há desenho.

            heroi.ajustar_caixa_a_arte()

        Um quadro de sprite quase nunca é todo desenho: sobra transparência em
        volta. Colidindo pelo quadro, o personagem para longe da parede, com um
        vão visível entre a arte e o bloco. Esta medida é feita uma vez, sobre o
        quadro exibido, e não a cada passo: a caixa tem de ser estável, ou o
        personagem mudaria de tamanho no meio de um pulo.

        `folga` afrouxa a caixa em pixels, para quem quiser um pouco de
        tolerância. Sem desenho nenhum, a caixa fica como estava.
        """
        try:
            recorte = self._recorte_atual()
        except Exception:  # noqa: BLE001 - sem imagem utilizável, fica como está
            return self
        if recorte is None:
            return self
        caixa = recorte.get_bounding_rect()
        if caixa.width <= 0 or caixa.height <= 0:
            return self
        return self.set_caixa_colisao(
            esquerda=max(0, caixa.left - folga),
            topo=max(0, caixa.top - folga),
            direita=max(0, int(self.width) - caixa.right - folga),
            base=max(0, int(self.height) - caixa.bottom - folga))

    def _recorte_atual(self):
        """A superfície do que está sendo desenhado agora. Uma imagem simples
        é ela mesma; um Animation devolve só o quadro atual."""
        return self.image

    def set_espelhado(self, espelhado=True):
        """
        Vira o desenho para o outro lado, sem mexer na posição nem na colisão.

            if jogador.vx < 0:
                jogador.set_espelhado(True)     # olhando para a esquerda

        A imagem virada é feita uma vez e guardada: virar o personagem a cada
        quadro não custa nada.
        """
        self.espelhado = bool(espelhado)
        return self

    def _superficie(self, colunas=1, linhas=1):
        """A imagem a usar no desenho: a original ou a espelhada."""
        if not self.espelhado:
            return self.image
        chave = (self.caminho, colunas, linhas)
        espelho = GameImage._espelho_cache.get(chave)
        if espelho is None:
            espelho = GameImage.espelhar(self.image, colunas, linhas)
            GameImage._espelho_cache[chave] = espelho
        return espelho

    @staticmethod
    def espelhar(superficie, colunas=1, linhas=1):
        """
        Espelha cada quadro NO LUGAR, sem trocar a ordem deles.

        Virar a folha inteira de uma vez não serve numa spritesheet: além de
        espelhar os desenhos, isso inverteria a ordem dos quadros, e a
        animação passaria a rodar de trás para frente. Aqui cada célula da
        grade é recortada, virada e devolvida à mesma posição.
        """
        if colunas <= 1 and linhas <= 1:
            return pygame.transform.flip(superficie, True, False)

        largura_total, altura_total = superficie.get_size()
        largura = largura_total // colunas
        altura = altura_total // linhas

        nova = pygame.Surface((largura_total, altura_total), pygame.SRCALPHA)
        for lin in range(linhas):
            for col in range(colunas):
                area = (col * largura, lin * altura, largura, altura)
                quadro = superficie.subsurface(area)
                nova.blit(pygame.transform.flip(quadro, True, False),
                          (col * largura, lin * altura))
        return nova

    def draw(self):
        """Desenha a imagem na tela na posição atual (x, y)."""
        # hide()/unhide() da PPlay 1.0 só desligam esta marca; sem esta
        # verificação, chamar hide() não escondia coisa alguma.
        if not self.drawable:
            return

        # Atualizamos o rect interno antes de desenhar
        self.rect.x = self.x
        self.rect.y = self.y
        
        # Pega a tela da Window e desenha
        Window.get_screen().blit(self._superficie(), self.rect)

    def draw_collision_box(self, cor=(0, 255, 0)):
        """Método de Debug: Desenha a caixa de colisão do objeto."""
        pygame.draw.rect(Window.get_screen(), cor, (self.x, self.y, self.width, self.height), 1)

    @classmethod
    def get_cache_size(cls):
        """Retorna quantas imagens únicas estão carregadas na memória."""
        return len(cls._resource_cache)