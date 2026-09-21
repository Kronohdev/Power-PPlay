import math
import pygame
from .window import Window
from .gameimage import GameImage

"""
===============================================================================
POWER PPLAY 2.1 - MÓDULO 3D (RAYCASTING)
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula
Contato: kneves@id.uff.br

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Renderização pseudo-3D pela técnica de raycasting (Wolfenstein 3D / Doom).

Não existe malha, nem GPU, nem eixo Z: para cada coluna de pixels da tela é
lançado um raio no mapa 2D; a distância até a parede define a altura da faixa
vertical desenhada. Tudo acontece no mesmo buffer virtual da Window.

Classes:
    World3D     - o mapa em grade, com texturas por código
    Camera3D    - posição, direção e plano de projeção; move com colisão
    Billboard   - sprite que sempre encara a câmera (inimigos, itens)
    Raycaster3D - o renderizador: paredes, sprites, z-buffer e névoa
===============================================================================
"""


# =============================================================================
# MUNDO
# =============================================================================
class World3D:
    """
    Mapa em grade. Cada célula guarda um inteiro: 0 é espaço livre, qualquer
    valor maior é parede e indica qual textura usar.
    """

    def __init__(self, grade=None):
        self.grade = grade or []
        self.texturas = {}      # codigo (int) -> pygame.Surface
        self.spawn = (1.5, 1.5)
        self.marcadores = []    # [(caractere, x, y)] para inimigos e itens

    # -- construção ---------------------------------------------------------
    @classmethod
    def de_texto(cls, linhas, mapeamento=None):
        """
        Constrói o mundo a partir de uma lista de strings (ou de um .txt).

        mapeamento liga cada caractere a um código de parede:
            {'#': 1, 'X': 2, 'P': 3, 'inicio': 'A', 'entidades': 'ZM'}

        Dígitos '0' a '9' são entendidos como código diretamente.
        Caracteres listados em 'entidades' viram marcadores e a célula fica livre.
        """
        mundo = cls()
        mapeamento = mapeamento or {}
        inicio = mapeamento.get('inicio', 'A')
        entidades = mapeamento.get('entidades', '')

        for y, linha in enumerate(linhas):
            fila = []
            for x, ch in enumerate(linha.rstrip('\n')):
                if ch == inicio:
                    mundo.spawn = (x + 0.5, y + 0.5)
                    fila.append(0)
                elif ch in entidades:
                    mundo.marcadores.append((ch, x + 0.5, y + 0.5))
                    fila.append(0)
                elif ch in mapeamento and isinstance(mapeamento[ch], int):
                    fila.append(mapeamento[ch])
                elif ch.isdigit():
                    fila.append(int(ch))
                else:
                    fila.append(0)
            mundo.grade.append(fila)
        return mundo

    @classmethod
    def de_arquivo(cls, caminho_txt, mapeamento=None):
        try:
            with open(caminho_txt, 'r', encoding='utf-8') as f:
                return cls.de_texto(f.readlines(), mapeamento)
        except FileNotFoundError:
            print(f"ERRO: mapa 3D nao encontrado: {caminho_txt}")
            return cls([[1, 1, 1], [1, 0, 1], [1, 1, 1]])

    # -- texturas -----------------------------------------------------------
    def set_textura(self, codigo, caminho_ou_surface):
        """Associa uma imagem a um código de parede. Usa o cache da GameImage."""
        if isinstance(caminho_ou_surface, pygame.Surface):
            self.texturas[codigo] = caminho_ou_surface
        else:
            self.texturas[codigo] = GameImage(caminho_ou_surface).image
        return self

    def set_textura_cor(self, codigo, cor, tamanho=64, cor_borda=None):
        """Gera uma textura procedural sólida — útil para prototipar sem arte."""
        surf = pygame.Surface((tamanho, tamanho))
        surf.fill(cor)
        if cor_borda:
            pygame.draw.rect(surf, cor_borda, (0, 0, tamanho, tamanho), 2)
        self.texturas[codigo] = surf
        return self

    # -- consultas ----------------------------------------------------------
    @property
    def largura(self):
        return len(self.grade[0]) if self.grade else 0

    @property
    def altura(self):
        return len(self.grade)

    def celula(self, x, y):
        """Código da célula. Fora do mapa conta como parede (1)."""
        ix, iy = int(x), int(y)
        if iy < 0 or ix < 0 or iy >= len(self.grade) or ix >= len(self.grade[iy]):
            return 1
        return self.grade[iy][ix]

    def livre(self, x, y):
        return self.celula(x, y) == 0

    def set_celula(self, x, y, codigo):
        """Abre ou fecha uma célula em tempo real (portas, paredes destrutíveis)."""
        ix, iy = int(x), int(y)
        if 0 <= iy < len(self.grade) and 0 <= ix < len(self.grade[iy]):
            self.grade[iy][ix] = codigo

    def linha_de_visao(self, ax, ay, bx, by, passo=0.15):
        """True se nenhuma parede bloqueia o segmento entre os dois pontos."""
        d = math.hypot(bx - ax, by - ay)
        if d == 0:
            return True
        ux, uy = (bx - ax) / d, (by - ay) / d
        t = 0.0
        while t < d:
            if self.celula(ax + ux * t, ay + uy * t) > 0:
                return False
            t += passo
        return True


# =============================================================================
# CÂMERA
# =============================================================================
class Camera3D:
    """
    Posição e orientação do observador. O 'plano' é o plano de projeção: seu
    comprimento define o campo de visão (0.66 = ~66 graus; 0.85 = widescreen).
    """

    def __init__(self, x=1.5, y=1.5, fov=0.85):
        self.x = x
        self.y = y
        self.dir_x, self.dir_y = -1.0, 0.0
        self.plane_x, self.plane_y = 0.0, fov

        self.velocidade = 3.2      # células por segundo
        self.vel_rotacao = 2.6     # radianos por segundo
        self.raio_colisao = 0.22

        self.head_bob = 0.0
        self._bob_angulo = 0.0

    # -- movimento ----------------------------------------------------------
    def girar(self, radianos):
        cos_r, sin_r = math.cos(radianos), math.sin(radianos)
        odx = self.dir_x
        self.dir_x = self.dir_x * cos_r - self.dir_y * sin_r
        self.dir_y = odx * sin_r + self.dir_y * cos_r
        opx = self.plane_x
        self.plane_x = self.plane_x * cos_r - self.plane_y * sin_r
        self.plane_y = opx * sin_r + self.plane_y * cos_r

    def andar(self, mundo, quantidade):
        """Anda na direção que está olhando, deslizando nas paredes."""
        self._mover(mundo, self.dir_x * quantidade, self.dir_y * quantidade)

    def lateral(self, mundo, quantidade):
        """Passo lateral (strafe)."""
        self._mover(mundo, self.plane_x * quantidade, self.plane_y * quantidade)

    def _mover(self, mundo, dx, dy):
        # Eixos resolvidos separadamente — o mesmo princípio da física 2D
        margem = self.raio_colisao
        nx = self.x + dx
        if mundo.livre(nx + math.copysign(margem, dx), self.y):
            self.x = nx
        ny = self.y + dy
        if mundo.livre(self.x, ny + math.copysign(margem, dy)):
            self.y = ny

        if dx or dy:
            self._bob_angulo += 13 * abs(dx + dy)
            self.head_bob = math.sin(self._bob_angulo) * 5
        else:
            self.head_bob *= 0.85

    def controlar_com_teclado(self, mundo, avancar="w", recuar="s",
                              esquerda="a", direita="d", strafe=False):
        """Controle padrão WASD. Chame uma vez por frame."""
        janela = Window.get_instance()
        kb = janela.keyboard
        dt = janela.delta_time()

        if kb.key_pressed(avancar) or kb.key_pressed("up"):
            self.andar(mundo, self.velocidade * dt)
        if kb.key_pressed(recuar) or kb.key_pressed("down"):
            self.andar(mundo, -self.velocidade * dt)

        if strafe:
            if kb.key_pressed(esquerda):
                self.lateral(mundo, -self.velocidade * dt)
            if kb.key_pressed(direita):
                self.lateral(mundo, self.velocidade * dt)
        else:
            if kb.key_pressed(esquerda) or kb.key_pressed("left"):
                self.girar(self.vel_rotacao * dt)
            if kb.key_pressed(direita) or kb.key_pressed("right"):
                self.girar(-self.vel_rotacao * dt)

    def frente(self, distancia=1.0):
        """Ponto à frente da câmera — útil para interagir com portas."""
        return (self.x + self.dir_x * distancia, self.y + self.dir_y * distancia)


# =============================================================================
# BILLBOARD
# =============================================================================
class Billboard:
    """
    Sprite posicionado no mundo 3D que sempre encara a câmera. É assim que
    inimigos e itens aparecem em jogos de raycasting.
    """

    def __init__(self, x, y, imagem, escala=1.0, altura_relativa=0.0):
        self.x = x
        self.y = y
        self.escala = escala
        self.altura_relativa = altura_relativa   # >0 sobe, <0 desce
        self.visivel = True
        self.tint = None                         # (r, g, b, a) para flash de dano
        self.imagem = imagem if isinstance(imagem, pygame.Surface) else GameImage(imagem).image

    def distancia_de(self, camera):
        return math.hypot(self.x - camera.x, self.y - camera.y)


# =============================================================================
# RENDERIZADOR
# =============================================================================
class Raycaster3D:
    """
    Desenha o mundo em pseudo-3D no buffer virtual da Window.

    Um raio por coluna de pixels; DDA para achar a parede; altura da faixa
    inversamente proporcional à distância perpendicular (o que evita a
    distorção 'olho de peixe').
    """

    def __init__(self, mundo, camera=None, alcance=50):
        self.mundo = mundo
        self.camera = camera or Camera3D(*mundo.spawn)
        self.alcance = alcance            # passos máximos do DDA por raio

        self.cor_teto = (20, 20, 26)
        self.cor_chao = (40, 35, 34)
        self.distancia_nevoa = 12.0       # 0 desliga a névoa
        self.cor_nevoa = (6, 7, 10)
        self.sombrear_lateral = True      # escurece paredes de face norte/sul

        self.tremor = 0.0                 # em pixels; some sozinho
        self._zbuffer = []
        self._textura_padrao = None

        # Estatísticas do último frame (bom para HUD de depuração)
        self.colunas_tracadas = 0
        self.passos_dda = 0
        self.sprites_desenhados = 0

    # -- utilidades ---------------------------------------------------------
    def _textura(self, codigo):
        tex = self.mundo.texturas.get(codigo)
        if tex is not None:
            return tex
        if self._textura_padrao is None:
            self._textura_padrao = pygame.Surface((64, 64))
            self._textura_padrao.fill((255, 0, 255))   # textura faltando
        return self._textura_padrao

    def aplicar_tremor(self, intensidade):
        self.tremor = max(self.tremor, intensidade)

    # -- render -------------------------------------------------------------
    def draw(self, billboards=None):
        """Desenha o mundo inteiro. Chame antes do HUD e do janela.update()."""
        janela = Window.get_instance()
        tela = Window.get_screen()
        largura, altura = janela.largura, janela.altura
        cam = self.camera

        if self.tremor > 0:
            self.tremor = max(0.0, self.tremor - 60 * janela.delta_time())
        desvio = (pygame.time.get_ticks() % 7 - 3) * (self.tremor / 6.0) if self.tremor else 0
        horizonte = altura / 2 + desvio + cam.head_bob

        # Teto e chão
        pygame.draw.rect(tela, self.cor_teto, (0, 0, largura, max(0, int(horizonte))))
        pygame.draw.rect(tela, self.cor_chao, (0, int(horizonte), largura, altura))

        self._zbuffer = [1e9] * largura
        self.colunas_tracadas = largura
        self.passos_dda = 0

        for coluna in range(largura):
            self._coluna(tela, coluna, largura, altura, horizonte)

        self.sprites_desenhados = 0
        if billboards:
            self._sprites(tela, billboards, largura, altura, horizonte)

    def _coluna(self, tela, x, largura, altura, horizonte):
        cam = self.camera
        camera_x = 2 * x / largura - 1
        ray_dx = cam.dir_x + cam.plane_x * camera_x
        ray_dy = cam.dir_y + cam.plane_y * camera_x

        map_x, map_y = int(cam.x), int(cam.y)
        delta_dx = abs(1 / ray_dx) if ray_dx else 1e30
        delta_dy = abs(1 / ray_dy) if ray_dy else 1e30

        if ray_dx < 0:
            step_x, side_dx = -1, (cam.x - map_x) * delta_dx
        else:
            step_x, side_dx = 1, (map_x + 1.0 - cam.x) * delta_dx
        if ray_dy < 0:
            step_y, side_dy = -1, (cam.y - map_y) * delta_dy
        else:
            step_y, side_dy = 1, (map_y + 1.0 - cam.y) * delta_dy

        hit, side, passos = 0, 0, 0
        while hit == 0 and passos < self.alcance:
            if side_dx < side_dy:
                side_dx += delta_dx
                map_x += step_x
                side = 0
            else:
                side_dy += delta_dy
                map_y += step_y
                side = 1
            passos += 1
            codigo = self.mundo.celula(map_x, map_y)
            if codigo > 0:
                hit = codigo

        self.passos_dda += passos
        if hit == 0:
            return

        # Distância PERPENDICULAR ao plano da câmera (sem olho de peixe)
        if side == 0:
            perp = (map_x - cam.x + (1 - step_x) / 2) / (ray_dx or 1e-9)
        else:
            perp = (map_y - cam.y + (1 - step_y) / 2) / (ray_dy or 1e-9)
        perp = max(0.2, perp)
        self._zbuffer[x] = perp

        linha_h = altura / perp
        topo = -linha_h / 2 + horizonte

        tex = self._textura(hit)
        tw, th = tex.get_width(), tex.get_height()

        # Onde exatamente o raio bateu na parede (0.0 a 1.0)
        if side == 0:
            wall_x = cam.y + perp * ray_dy
        else:
            wall_x = cam.x + perp * ray_dx
        wall_x -= math.floor(wall_x)

        tex_x = int(wall_x * tw)
        if side == 0 and ray_dx > 0:
            tex_x = tw - tex_x - 1
        if side == 1 and ray_dy < 0:
            tex_x = tw - tex_x - 1
        tex_x = max(0, min(tex_x, tw - 1))

        fatia = tex.subsurface((tex_x, 0, 1, th))
        try:
            fatia = pygame.transform.scale(fatia, (1, max(1, int(linha_h))))
        except pygame.error:
            return

        tela.blit(fatia, (x, int(topo)))

        # Sombreamento de face + névoa por distância
        escuro = 0
        if self.sombrear_lateral and side == 1:
            escuro += 60
        if self.distancia_nevoa > 0:
            escuro += min(200, int((perp / self.distancia_nevoa) * 210))
        if escuro > 0:
            veu = pygame.Surface((1, max(1, int(linha_h))), pygame.SRCALPHA)
            veu.fill((*self.cor_nevoa, min(235, escuro)))
            tela.blit(veu, (x, int(topo)))

    def _sprites(self, tela, billboards, largura, altura, horizonte):
        cam = self.camera
        visiveis = [b for b in billboards if b.visivel]
        # Painter's algorithm: dos mais distantes para os mais próximos
        visiveis.sort(key=lambda b: b.distancia_de(cam), reverse=True)

        for b in visiveis:
            sx, sy = b.x - cam.x, b.y - cam.y
            det = (cam.plane_x * cam.dir_y - cam.dir_x * cam.plane_y)
            if det == 0:
                continue
            inv = 1.0 / det
            trans_x = inv * (cam.dir_y * sx - cam.dir_x * sy)
            trans_y = inv * (-cam.plane_y * sx + cam.plane_x * sy)
            if trans_y <= 0.25:            # atrás da câmera ou colado nela
                continue

            centro_x = (largura / 2) * (1 + trans_x / trans_y)
            tam = abs(altura / trans_y) * b.escala
            topo = -tam / 2 + horizonte - b.altura_relativa * tam
            esquerda = -tam / 2 + centro_x

            try:
                img = pygame.transform.scale(b.imagem, (max(1, int(tam)), max(1, int(tam))))
            except pygame.error:
                continue

            if b.tint:
                marca = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                marca.fill(b.tint)
                img = img.copy()
                img.blit(marca, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # Recorta coluna a coluna respeitando o z-buffer das paredes
            largura_img = img.get_width()
            inicio = max(0, int(-esquerda))
            fim = min(largura_img, int(largura - esquerda))
            desenhou = False
            for coluna in range(inicio, fim):
                px = int(esquerda + coluna)
                if 0 <= px < largura and trans_y < self._zbuffer[px]:
                    tela.blit(img, (px, int(topo)), (coluna, 0, 1, img.get_height()))
                    desenhou = True
            if desenhou:
                self.sprites_desenhados += 1

    # -- extras -------------------------------------------------------------
    def draw_minimapa(self, x=8, y=8, escala=6, raio_visao=9, billboards=None):
        """Minimapa canto-superior com a grade, o observador e os sprites."""
        tela = Window.get_screen()
        cam = self.camera
        largura = int(raio_visao * 2 * escala)
        fundo = pygame.Surface((largura, largura), pygame.SRCALPHA)
        fundo.fill((10, 12, 18, 190))
        tela.blit(fundo, (x, y))

        cx, cy = x + largura / 2, y + largura / 2
        for gy in range(int(cam.y) - raio_visao, int(cam.y) + raio_visao + 1):
            for gx in range(int(cam.x) - raio_visao, int(cam.x) + raio_visao + 1):
                if self.mundo.celula(gx, gy) > 0:
                    px = cx + (gx - cam.x) * escala
                    py = cy + (gy - cam.y) * escala
                    if x <= px < x + largura and y <= py < y + largura:
                        pygame.draw.rect(tela, (90, 105, 130),
                                         (px, py, escala - 1, escala - 1))

        if billboards:
            for b in billboards:
                if not b.visivel:
                    continue
                px = cx + (b.x - cam.x) * escala
                py = cy + (b.y - cam.y) * escala
                if x <= px < x + largura and y <= py < y + largura:
                    pygame.draw.rect(tela, (220, 90, 120), (px - 1, py - 1, 3, 3))

        pygame.draw.circle(tela, (255, 0, 255), (int(cx), int(cy)), 3)
        pygame.draw.line(tela, (255, 0, 255), (cx, cy),
                         (cx + cam.dir_x * escala * 1.8, cy + cam.dir_y * escala * 1.8), 2)

    def draw_mira(self, cor=(255, 255, 255), tamanho=5):
        tela = Window.get_screen()
        janela = Window.get_instance()
        cx, cy = janela.largura // 2, janela.altura // 2
        pygame.draw.line(tela, cor, (cx - tamanho, cy), (cx - 2, cy))
        pygame.draw.line(tela, cor, (cx + 2, cy), (cx + tamanho, cy))
        pygame.draw.line(tela, cor, (cx, cy - tamanho), (cx, cy - 2))
        pygame.draw.line(tela, cor, (cx, cy + 2), (cx, cy + tamanho))

    def mirando(self, billboard, tolerancia=0.93):
        """True se o billboard está sob a mira e visível (para tiro instantâneo)."""
        cam = self.camera
        vx, vy = billboard.x - cam.x, billboard.y - cam.y
        d = math.hypot(vx, vy)
        if d == 0:
            return True
        alinhamento = (vx / d) * cam.dir_x + (vy / d) * cam.dir_y
        if alinhamento < tolerancia:
            return False
        return self.mundo.linha_de_visao(cam.x, cam.y, billboard.x, billboard.y)
