import pygame
from .sprite import Sprite
from .camera import Camera
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

class ListaSolidos(list):
    """
    A lista de blocos sólidos de um mapa, com um índice espacial por dentro.

    É uma `list` de verdade: itera, indexa, soma e mede como qualquer outra, e
    todo o código que já recebia a lista antiga continua funcionando sem saber
    que ela mudou. O que ela tem a mais é o método `perto()`, que devolve só os
    blocos de uma região — e é ele que tira a física de uma varredura de
    quinhentos blocos por chamada.

    O índice é construído na primeira pergunta, não no carregamento: um mapa
    que nunca colide com nada não paga por ele.

    **Quando o índice se desfaz.** Qualquer método que mude a lista (append,
    remove, sort, atribuição por índice…) o joga fora, e a próxima pergunta o
    reconstrói. O que o índice NÃO percebe é um bloco que se mova sozinho, sem
    a lista mudar — mas um bloco de mapa não se move: ele nasce no
    `carregar_mapa`, na posição da grade, e fica. Quem quiser plataformas
    móveis monta a própria lista, e essa cai no caminho antigo.
    """

    def __init__(self, iteravel=(), tamanho_celula=128):
        super().__init__(iteravel)
        # A célula é maior que o tile de propósito. Pequena demais, um bloco
        # cai em várias células e o índice incha; grande demais, cada consulta
        # devolve meio mapa. Quatro tiles de lado é o meio-termo, e foi o que
        # as medidas confirmaram.
        self._celula = max(8, int(tamanho_celula))
        self._grade = None

    # -- o índice ----------------------------------------------------------
    def _montar(self):
        grade = {}
        c = self._celula
        for solido in self:
            x0 = int(solido.x // c)
            y0 = int(solido.y // c)
            x1 = int((solido.x + solido.width) // c)
            y1 = int((solido.y + solido.height) // c)
            for gx in range(x0, x1 + 1):
                for gy in range(y0, y1 + 1):
                    chave = (gx, gy)
                    caixa = grade.get(chave)
                    if caixa is None:
                        grade[chave] = [solido]
                    else:
                        caixa.append(solido)
        self._grade = grade

    def invalidar(self):
        """Joga o índice fora. A próxima consulta o reconstrói."""
        self._grade = None

    def perto(self, x0, y0, x1, y1):
        """Os blocos que podem tocar o retângulo (x0, y0)-(x1, y1)."""
        if self._grade is None:
            self._montar()
        grade = self._grade
        c = self._celula
        gx0 = int(x0 // c)
        gy0 = int(y0 // c)
        gx1 = int(x1 // c)
        gy1 = int(y1 // c)

        # Uma célula só é o caso comum — um personagem cabe folgado nela — e
        # nesse caso a lista da célula serve como está, sem copiar nada.
        if gx0 == gx1 and gy0 == gy1:
            return grade.get((gx0, gy0), ())

        # Várias células: junta sem repetir. `vistos` guarda a identidade, e
        # não o objeto, porque um Sprite não é comparável por igualdade.
        achados = []
        vistos = set()
        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                for solido in grade.get((gx, gy), ()):
                    marca = id(solido)
                    if marca not in vistos:
                        vistos.add(marca)
                        achados.append(solido)
        return achados

    # -- mudou a lista, o índice morre --------------------------------------
    def _mudou(metodo):                      # noqa: N805
        def envolvido(self, *args, **kwargs):
            self._grade = None
            return metodo(self, *args, **kwargs)
        envolvido.__name__ = metodo.__name__
        envolvido.__doc__ = metodo.__doc__
        return envolvido

    append = _mudou(list.append)
    extend = _mudou(list.extend)
    insert = _mudou(list.insert)
    remove = _mudou(list.remove)
    pop = _mudou(list.pop)
    clear = _mudou(list.clear)
    sort = _mudou(list.sort)
    reverse = _mudou(list.reverse)
    __setitem__ = _mudou(list.__setitem__)
    __delitem__ = _mudou(list.__delitem__)
    __iadd__ = _mudou(list.__iadd__)
    del _mudou


class TileMap:
    """
    Carrega e gerencia um mapa baseado em uma grade (grid) de um arquivo .txt.
    """
    def __init__(self, tamanho_tile):
        self.tamanho_tile = tamanho_tile
        self.mapa_tiles = [] # Matriz de objetos Sprite
        # Lista apenas dos que bloqueiam movimento. É uma `list` com um índice
        # espacial por dentro (ver ListaSolidos): a física pergunta por região
        # em vez de varrer o mapa inteiro a cada passo.
        self.tiles_colidiveis = ListaSolidos(tamanho_celula=tamanho_tile * 4)
        
        self.largura_mapa_px = 0
        self.altura_mapa_px = 0

    def carregar_mapa(self, caminho_txt, mapeamento):
        """
        Lê o arquivo .txt e cria os Sprites.
        mapeamento: dicionário {'#': 'chao.png', '@': 'parede.png', 'solido': ['#', '@']}
        """
        self.mapa_tiles = []
        self.tiles_colidiveis = ListaSolidos(tamanho_celula=self.tamanho_tile * 4)
        
        try:
            # UTF-8 explícito: é o que o procedural.MapaGerado.salvar() grava e
            # o que o raycaster já lia. Sem isto, no Windows o arquivo era lido
            # na codificação local e qualquer caractere acentuado no mapa
            # deixava de bater com o 'mapeamento' — o tile sumia sem avisar.
            # O fallback mantém funcionando os mapas antigos gravados no
            # bloco de notas com a codificação da máquina.
            try:
                with open(caminho_txt, 'r', encoding='utf-8') as f:
                    linhas = f.readlines()
            except UnicodeDecodeError:
                with open(caminho_txt, 'r') as f:
                    linhas = f.readlines()
        except FileNotFoundError:
            print(f"ERRO: Arquivo de mapa {caminho_txt} não encontrado.")
            return

        for linha_idx, linha in enumerate(linhas):
            linha_objetos = []
            for col_idx, char in enumerate(linha.strip()):
                if char in mapeamento:
                    # Cria o tile na posição correta do grid
                    tile = Sprite(mapeamento[char], 1)
                    px = col_idx * self.tamanho_tile
                    py = linha_idx * self.tamanho_tile
                    tile.set_position(px, py)
                    
                    linha_objetos.append(tile)
                    
                    # Se o caractere estiver na lista de 'solidos' do mapeamento
                    if 'solido' in mapeamento and char in mapeamento['solido']:
                        self.tiles_colidiveis.append(tile)
                else:
                    linha_objetos.append(None) # Espaço vazio
            
            self.mapa_tiles.append(linha_objetos)

        # Calcula o tamanho total do mundo para a câmera.
        # A largura é a da linha MAIS COMPRIDA: arquivos de mapa quase sempre
        # têm linhas de tamanhos diferentes (o editor de texto corta os espaços
        # do fim), e usar só a primeira linha encolhia o mundo sem motivo.
        self.altura_mapa_px = len(self.mapa_tiles) * self.tamanho_tile
        if len(self.mapa_tiles) > 0:
            mais_longa = max(len(linha) for linha in self.mapa_tiles)
            self.largura_mapa_px = mais_longa * self.tamanho_tile
            
        # Ajusta a câmera automaticamente se ela existir
        if Camera.get_instance():
            Camera.get_instance().set_world_bounds(self.largura_mapa_px, self.altura_mapa_px)

    def draw(self):
        """
        Desenha apenas os tiles que estão visíveis na tela (Culling).
        Isso permite mapas gigantes com performance máxima.
        """
        # Mapa vazio (arquivo não encontrado, ou carregar_mapa ainda não
        # chamado): sem isto o acesso a mapa_tiles[0] logo abaixo estourava
        # um IndexError em vez de simplesmente não desenhar nada.
        if not self.mapa_tiles:
            return

        cam = Camera.get_instance()
        if not cam:
            # Se não houver câmera, desenha tudo (não recomendado para mapas grandes)
            for linha in self.mapa_tiles:
                for tile in linha:
                    if tile: tile.draw()
            return

        # OTIMIZAÇÃO: Descobre quais índices do grid estão na tela
        inicio_col = max(0, int(cam.x // self.tamanho_tile))
        fim_col = int((cam.x + cam.largura) // self.tamanho_tile) + 1

        inicio_linha = max(0, int(cam.y // self.tamanho_tile))
        fim_linha = min(len(self.mapa_tiles), int((cam.y + cam.altura) // self.tamanho_tile) + 1)

        # Desenha apenas o que é necessário.
        # O corte de colunas é feito POR LINHA porque as linhas do arquivo de
        # mapa podem ter comprimentos diferentes; antes o limite vinha da
        # primeira linha e uma linha mais curta estourava IndexError.
        for r in range(inicio_linha, fim_linha):
            linha = self.mapa_tiles[r]
            for c in range(inicio_col, min(fim_col, len(linha))):
                tile = linha[c]
                if tile:
                    tile.draw()

    def get_solidos(self):
        """Retorna a lista de tiles que possuem colisão."""
        return self.tiles_colidiveis