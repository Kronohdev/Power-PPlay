import random

"""
===============================================================================
POWER PPLAY 2.1 - GERAÇÃO PROCEDURAL DE MUNDOS
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula
Contato: kneves@id.uff.br

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Em vez de desenhar cada fase à mão, descreva REGRAS e deixe o computador
construir. Três algoritmos clássicos, cada um com uma "assinatura" visual:

    Autômato Celular  -> cavernas orgânicas, com paredes irregulares
    Walk do Bêbado    -> túneis sinuosos e conectados
    BSP (partição)    -> masmorras de salas retangulares ligadas por corredores

Todos devolvem uma matriz de caracteres compatível com o TileMap e com o
World3D — e podem ser gravados em .txt.

Semente (seed): passando o mesmo número, o mesmo mundo é gerado sempre. É o
que permite compartilhar uma fase interessante apenas com um código.
===============================================================================
"""

PAREDE = '#'
CHAO = '.'


# =============================================================================
# BASE
# =============================================================================
class MapaGerado:
    """Resultado de uma geração: a grade e os pontos notáveis encontrados."""

    def __init__(self, grade, seed=None):
        self.grade = grade
        self.seed = seed
        self.salas = []          # [(x, y, largura, altura)] quando aplicável
        self.inicio = None       # (coluna, linha)
        self.fim = None

    @property
    def largura(self):
        return len(self.grade[0]) if self.grade else 0

    @property
    def altura(self):
        return len(self.grade)

    def em(self, x, y):
        if 0 <= y < self.altura and 0 <= x < self.largura:
            return self.grade[y][x]
        return PAREDE

    def livre(self, x, y):
        return self.em(x, y) == CHAO

    def linhas(self):
        return [''.join(linha) for linha in self.grade]

    def salvar(self, caminho):
        """Grava como .txt, pronto para TileMap.carregar_mapa()."""
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.linhas()))
        return caminho

    def celulas_livres(self):
        return [(x, y) for y in range(self.altura) for x in range(self.largura)
                if self.grade[y][x] == CHAO]

    def posicao_aleatoria(self, rng=None):
        """Uma célula de chão qualquer — para nascer o jogador ou um item."""
        livres = self.celulas_livres()
        if not livres:
            return None
        return (rng or random).choice(livres)

    def marcar(self, x, y, caractere):
        if 0 <= y < self.altura and 0 <= x < self.largura:
            self.grade[y][x] = caractere

    def __str__(self):
        return '\n'.join(self.linhas())


def _grade_cheia(largura, altura, valor=PAREDE):
    return [[valor for _ in range(largura)] for _ in range(altura)]


def _vizinhos_parede(grade, x, y):
    """Conta paredes nas 8 células ao redor. Fora do mapa conta como parede."""
    total = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if ny < 0 or nx < 0 or ny >= len(grade) or nx >= len(grade[0]):
                total += 1
            elif grade[ny][nx] == PAREDE:
                total += 1
    return total


# =============================================================================
# 1. AUTÔMATO CELULAR — CAVERNAS
# =============================================================================
def caverna(largura=64, altura=36, densidade=0.45, passos=5, seed=None,
            conectar=True):
    """
    Cavernas orgânicas em três etapas:

      1. Sorteia ruído: cada célula vira parede com probabilidade 'densidade'.
      2. Suaviza N vezes com a regra do autômato celular: uma célula com 5 ou
         mais vizinhos-parede vira parede; com menos, vira chão. O ruído
         aleatório se organiza em massas contínuas.
      3. Opcionalmente mantém apenas a maior região conectada, para não sobrar
         bolsão inacessível.

    densidade baixa (0.40) -> cavernas amplas; alta (0.50) -> labirínticas.
    """
    rng = random.Random(seed)
    grade = _grade_cheia(largura, altura)

    # 1. ruído (bordas sempre sólidas)
    for y in range(1, altura - 1):
        for x in range(1, largura - 1):
            grade[y][x] = PAREDE if rng.random() < densidade else CHAO

    # 2. suavização
    for _ in range(passos):
        nova = [linha[:] for linha in grade]
        for y in range(1, altura - 1):
            for x in range(1, largura - 1):
                nova[y][x] = PAREDE if _vizinhos_parede(grade, x, y) >= 5 else CHAO
        grade = nova

    mapa = MapaGerado(grade, seed)
    if conectar:
        manter_maior_regiao(mapa)
    return mapa


# =============================================================================
# 2. WALK DO BÊBADO — TÚNEIS
# =============================================================================
def tuneis(largura=64, altura=36, passos=2200, seed=None, espessura=1):
    """
    Um "escavador" parte do centro e caminha em direções aleatórias, abrindo
    chão por onde passa. Simples e sempre conectado por construção — o caminho
    do escavador é, ele próprio, a garantia de que tudo se liga.

    'espessura' controla a largura do túnel escavado (1 = estreito, 2 = largo).
    """
    rng = random.Random(seed)
    grade = _grade_cheia(largura, altura)

    x, y = largura // 2, altura // 2
    for _ in range(passos):
        for dy in range(-espessura + 1, espessura):
            for dx in range(-espessura + 1, espessura):
                nx, ny = x + dx, y + dy
                if 1 <= nx < largura - 1 and 1 <= ny < altura - 1:
                    grade[ny][nx] = CHAO
        direcao = rng.choice(((0, 1), (0, -1), (1, 0), (-1, 0)))
        x = max(1, min(largura - 2, x + direcao[0]))
        y = max(1, min(altura - 2, y + direcao[1]))

    mapa = MapaGerado(grade, seed)
    mapa.inicio = (largura // 2, altura // 2)
    return mapa


# =============================================================================
# 3. BSP — MASMORRA DE SALAS
# =============================================================================
class _No:
    def __init__(self, x, y, largura, altura):
        self.x, self.y = x, y
        self.largura, self.altura = largura, altura
        self.esq = self.dir = None
        self.sala = None

    def folha(self):
        return self.esq is None and self.dir is None

    def centro_sala(self):
        if self.sala:
            sx, sy, sw, sh = self.sala
            return (sx + sw // 2, sy + sh // 2)
        # sobe pelos filhos até achar uma sala
        for filho in (self.esq, self.dir):
            if filho:
                c = filho.centro_sala()
                if c:
                    return c
        return None


def masmorra(largura=64, altura=40, profundidade=4, sala_minima=6, seed=None):
    """
    Partição Binária do Espaço (BSP):

      1. Corta o retângulo do mapa ao meio, na horizontal ou na vertical.
      2. Repete em cada metade, 'profundidade' vezes.
      3. Desenha uma sala dentro de cada folha, com margem aleatória.
      4. Liga as salas irmãs com corredores em L, subindo pela árvore.

    O resultado tem a cara de masmorra de RPG: salas retangulares distintas,
    conectadas, sem áreas isoladas.
    """
    rng = random.Random(seed)
    grade = _grade_cheia(largura, altura)
    raiz = _No(1, 1, largura - 2, altura - 2)

    def dividir(no, nivel):
        if nivel <= 0:
            return
        if no.largura < sala_minima * 2 + 2 and no.altura < sala_minima * 2 + 2:
            return

        # Corta no lado mais comprido, para não gerar salas espremidas
        if no.largura / max(1, no.altura) > 1.25:
            horizontal = False
        elif no.altura / max(1, no.largura) > 1.25:
            horizontal = True
        else:
            horizontal = rng.random() < 0.5

        if horizontal:
            if no.altura < sala_minima * 2 + 2:
                return
            corte = rng.randint(sala_minima + 1, no.altura - sala_minima - 1)
            no.esq = _No(no.x, no.y, no.largura, corte)
            no.dir = _No(no.x, no.y + corte, no.largura, no.altura - corte)
        else:
            if no.largura < sala_minima * 2 + 2:
                return
            corte = rng.randint(sala_minima + 1, no.largura - sala_minima - 1)
            no.esq = _No(no.x, no.y, corte, no.altura)
            no.dir = _No(no.x + corte, no.y, no.largura - corte, no.altura)

        dividir(no.esq, nivel - 1)
        dividir(no.dir, nivel - 1)

    def criar_salas(no, mapa):
        if no.folha():
            larg = rng.randint(sala_minima, max(sala_minima, no.largura - 2))
            alt = rng.randint(sala_minima, max(sala_minima, no.altura - 2))
            sx = no.x + rng.randint(1, max(1, no.largura - larg - 1))
            sy = no.y + rng.randint(1, max(1, no.altura - alt - 1))
            no.sala = (sx, sy, larg, alt)
            mapa.salas.append(no.sala)
            for y in range(sy, min(sy + alt, altura - 1)):
                for x in range(sx, min(sx + larg, largura - 1)):
                    grade[y][x] = CHAO
            return
        criar_salas(no.esq, mapa)
        criar_salas(no.dir, mapa)
        # corredor em L ligando os dois lados
        a, b = no.esq.centro_sala(), no.dir.centro_sala()
        if a and b:
            _corredor_em_L(grade, a, b, largura, altura, rng)

    mapa = MapaGerado(grade, seed)
    dividir(raiz, profundidade)
    criar_salas(raiz, mapa)

    if mapa.salas:
        sx, sy, sw, sh = mapa.salas[0]
        mapa.inicio = (sx + sw // 2, sy + sh // 2)
        ex, ey, ew, eh = mapa.salas[-1]
        mapa.fim = (ex + ew // 2, ey + eh // 2)
    return mapa


def _corredor_em_L(grade, a, b, largura, altura, rng):
    ax, ay = a
    bx, by = b
    if rng.random() < 0.5:
        for x in range(min(ax, bx), max(ax, bx) + 1):
            if 0 < x < largura - 1 and 0 < ay < altura - 1:
                grade[ay][x] = CHAO
        for y in range(min(ay, by), max(ay, by) + 1):
            if 0 < bx < largura - 1 and 0 < y < altura - 1:
                grade[y][bx] = CHAO
    else:
        for y in range(min(ay, by), max(ay, by) + 1):
            if 0 < ax < largura - 1 and 0 < y < altura - 1:
                grade[y][ax] = CHAO
        for x in range(min(ax, bx), max(ax, bx) + 1):
            if 0 < x < largura - 1 and 0 < by < altura - 1:
                grade[by][x] = CHAO


# =============================================================================
# PÓS-PROCESSAMENTO
# =============================================================================
def regioes(mapa):
    """
    Devolve a lista de regiões conectadas de chão, cada uma como conjunto de
    células. Usa busca em largura (flood fill) — o mesmo princípio do balde de
    tinta de um editor de imagem.
    """
    vistos = set()
    achadas = []
    for y in range(mapa.altura):
        for x in range(mapa.largura):
            if mapa.grade[y][x] != CHAO or (x, y) in vistos:
                continue
            fila = [(x, y)]
            regiao = set()
            vistos.add((x, y))
            while fila:
                cx, cy = fila.pop()
                regiao.add((cx, cy))
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in vistos:
                        continue
                    if 0 <= ny < mapa.altura and 0 <= nx < mapa.largura and \
                       mapa.grade[ny][nx] == CHAO:
                        vistos.add((nx, ny))
                        fila.append((nx, ny))
            achadas.append(regiao)
    return achadas


def manter_maior_regiao(mapa):
    """Fecha todas as cavidades isoladas, deixando só a maior área acessível."""
    achadas = regioes(mapa)
    if len(achadas) <= 1:
        return mapa
    maior = max(achadas, key=len)
    for regiao in achadas:
        if regiao is maior:
            continue
        for (x, y) in regiao:
            mapa.grade[y][x] = PAREDE
    return mapa


def erodir(mapa, passos=1):
    """Engrossa o chão (remove paredes finas). Suaviza cantos agressivos."""
    for _ in range(passos):
        nova = [linha[:] for linha in mapa.grade]
        for y in range(1, mapa.altura - 1):
            for x in range(1, mapa.largura - 1):
                if mapa.grade[y][x] == PAREDE and _vizinhos_parede(mapa.grade, x, y) <= 3:
                    nova[y][x] = CHAO
        mapa.grade = nova
    return mapa


def contornar(mapa, caractere_borda='X'):
    """
    Marca com outro caractere toda parede que faz fronteira com o chão.
    Serve para usar uma arte diferente na "casca" da caverna.
    """
    for y in range(mapa.altura):
        for x in range(mapa.largura):
            if mapa.grade[y][x] != PAREDE:
                continue
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if mapa.em(x + dx, y + dy) == CHAO:
                    mapa.grade[y][x] = caractere_borda
                    break
    return mapa


def espalhar(mapa, caractere, quantidade, seed=None, longe_de=None, distancia_min=6):
    """
    Distribui itens/inimigos em células de chão livres.
    'longe_de' é uma célula (x, y) — normalmente onde o jogador nasce.
    """
    rng = random.Random(seed)
    livres = mapa.celulas_livres()
    rng.shuffle(livres)
    postos = 0
    for (x, y) in livres:
        if postos >= quantidade:
            break
        if longe_de:
            dx, dy = x - longe_de[0], y - longe_de[1]
            if (dx * dx + dy * dy) ** 0.5 < distancia_min:
                continue
        mapa.grade[y][x] = caractere
        postos += 1
    return mapa
