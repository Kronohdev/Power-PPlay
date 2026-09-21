import pygame
from .fontes import Fontes
from .window import Window
from .gameobject import GameObject
from .gameimage import GameImage

"""
===============================================================================
POWER PPLAY 2.1 - SISTEMA DE INTERFACE (UI)
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula
Contato: kneves@id.uff.br

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Sistema de widgets com tema centralizado, layout automático e navegação por
teclado. Complementa o uikit.py (Button e ProgressBar), que continua válido.

Widgets: Label, Button, Checkbox, Slider, TextInput, ProgressBar, Caixa,
Imagem, Panel.
Gerência: UIManager (update/draw em massa, foco por TAB, tema global).
===============================================================================
"""


# =============================================================================
# TEMA
# =============================================================================
class UITheme:
    """
    Paleta e tipografia de toda a interface, num lugar só.
    Mude aqui e o jogo inteiro muda de cara.
    """
    fundo        = (26, 30, 40)
    fundo_alt    = (36, 42, 56)
    borda        = (70, 80, 100)
    texto        = (232, 238, 247)
    texto_fraco  = (140, 152, 172)
    destaque     = (214, 60, 150)
    destaque_alt = (255, 110, 190)
    perigo       = (208, 70, 70)
    sucesso      = (70, 190, 120)

    fonte_nome   = "Arial"
    fonte_tam    = 20
    raio         = 0          # 0 = cantos retos; >0 arredonda
    espaco       = 10         # espaçamento padrão entre widgets
    padding      = 12

    @classmethod
    def fonte(cls, tamanho=None, negrito=False, familia=None):
        """
        A fonte do tema, ou a que o widget pediu.

        `familia` pode ser um nome registrado em PPlay.fontes (um .ttf que
        viaja com o jogo) ou uma família do sistema. O cache mora lá: criar uma
        fonte custa caro e o jogo pede a mesma sessenta vezes por segundo.
        """
        return Fontes.obter(familia or cls.fonte_nome,
                            tamanho or cls.fonte_tam, negrito)

    @classmethod
    def aplicar_paleta(cls, **cores):
        """UITheme.aplicar_paleta(destaque=(0,200,255), fundo=(10,12,18))"""
        for nome, valor in cores.items():
            if hasattr(cls, nome):
                setattr(cls, nome, valor)


def _cor(valor, padrao):
    if valor is None:
        return padrao
    if isinstance(valor, str):
        try:
            return tuple(pygame.Color(valor))[:3]
        except ValueError:
            return padrao
    return valor


# =============================================================================
# BASE
# =============================================================================
class Widget(GameObject):
    """
    Base de todos os componentes. Herda de GameObject, então tem x, y,
    width, height e collided() — e funciona dentro de um ObjectGroup.
    """
    def __init__(self, largura=120, altura=32):
        super().__init__()
        self.width = largura
        self.height = altura
        self.visivel = True
        self.ativo = True          # False = desenha apagado e ignora entrada
        self.focado = False        # recebe teclado quando navegando por TAB
        self.hover = False
        self.focavel = False
        self.on_change = None      # callback(valor) para widgets de valor

    # -- ciclo de vida -------------------------------------------------------
    def update(self):
        if not (self.visivel and self.ativo):
            self.hover = False
            return
        self.hover = Window.get_instance().mouse.is_over_object(self)

    def draw(self):
        pass

    def tratar_tecla(self, evento):
        """Chamado pelo UIManager quando este widget tem o foco."""
        return False

    # -- desenho auxiliar ----------------------------------------------------
    def _rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))

    def _caixa(self, superficie, cor_fundo, cor_borda=None, espessura=1):
        r = self._rect()
        if UITheme.raio > 0:
            pygame.draw.rect(superficie, cor_fundo, r, border_radius=UITheme.raio)
            if cor_borda:
                pygame.draw.rect(superficie, cor_borda, r, espessura, border_radius=UITheme.raio)
        else:
            pygame.draw.rect(superficie, cor_fundo, r)
            if cor_borda:
                pygame.draw.rect(superficie, cor_borda, r, espessura)

    def _texto_centro(self, superficie, texto, cor, tamanho=None, negrito=False,
                      familia=None):
        img = UITheme.fonte(tamanho, negrito, familia).render(str(texto), True, cor)
        superficie.blit(img, (self.x + (self.width - img.get_width()) / 2,
                              self.y + (self.height - img.get_height()) / 2))

    def _alpha_ativo(self):
        return 1.0 if self.ativo else 0.45


# =============================================================================
# LABEL
# =============================================================================
class Label(Widget):
    """Texto simples. Aceita alinhamento e quebra automática."""

    def __init__(self, texto="", tamanho=None, cor=None, negrito=False,
                 alinhamento="esquerda", largura=None, altura=None,
                 cor_fundo=None, fonte=None):
        super().__init__(largura or 200, altura or (tamanho or UITheme.fonte_tam) + 6)
        self.texto = texto
        self.tamanho = tamanho or UITheme.fonte_tam
        self.cor = _cor(cor, UITheme.texto)
        self.negrito = negrito
        # None = a fonte do tema. Um nome registrado em PPlay.fontes usa o
        # arquivo que veio com o jogo.
        self.fonte = fonte
        self.alinhamento = alinhamento
        # Sem fundo o rótulo é só o texto; com fundo ele vira uma tarja, e aí
        # a altura precisa ser respeitada mesmo quando a letra é menor.
        self.cor_fundo = None if cor_fundo is None else _cor(cor_fundo, UITheme.fundo_alt)
        self._auto_largura = largura is None
        self._auto_altura = altura is None
        self._medir()

    def set_texto(self, texto):
        if texto != self.texto:
            self.texto = texto
            self._medir()

    def set_fonte(self, fonte):
        """Troca a fonte e remede: o texto muda de largura com ela."""
        self.fonte = fonte
        self._medir()

    def _medir(self):
        img = UITheme.fonte(self.tamanho, self.negrito,
                            self.fonte).render(str(self.texto), True, self.cor)
        if self._auto_largura:
            self.width = img.get_width()
        if self._auto_altura:
            self.height = img.get_height()

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()
        if self.cor_fundo is not None:
            self._caixa(tela, self.cor_fundo)
        img = UITheme.fonte(self.tamanho, self.negrito,
                            self.fonte).render(str(self.texto), True, self.cor)
        if self.alinhamento == "centro":
            px = self.x + (self.width - img.get_width()) / 2
        elif self.alinhamento == "direita":
            px = self.x + self.width - img.get_width()
        else:
            px = self.x
        tela.blit(img, (px, self.y + (self.height - img.get_height()) / 2))


# =============================================================================
# BOTÃO
# =============================================================================
class Button(Widget):
    """
    Botão com estados hover, pressionado, desativado e foco de teclado.
    Dispare com clique do mouse ou com ENTER/ESPAÇO quando focado.
    """

    def __init__(self, texto="", largura=180, altura=44, on_click=None,
                 cor=None, cor_texto=None, fonte=None):
        super().__init__(largura, altura)
        self.fonte = fonte
        self.texto = texto
        self.on_click = on_click
        self.focavel = True
        self.cor = _cor(cor, UITheme.fundo_alt)
        self.cor_texto = _cor(cor_texto, UITheme.texto)
        self._pressionado = False
        self._clicado_agora = False

    def update(self):
        super().update()
        self._clicado_agora = False
        if not (self.visivel and self.ativo):
            self._pressionado = False
            return

        mouse = Window.get_instance().mouse
        self._pressionado = self.hover and mouse.button_pressed(1)
        if self.hover and mouse.button_down(1):
            self._disparar()

    def tratar_tecla(self, evento):
        if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._disparar()
            return True
        return False

    def _disparar(self):
        self._clicado_agora = True
        if self.on_click:
            self.on_click()

    def is_clicked(self):
        """True apenas no frame do disparo (mouse ou teclado)."""
        return self._clicado_agora

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()

        base = self.cor
        if not self.ativo:
            base = UITheme.fundo
        elif self._pressionado:
            base = tuple(max(0, c - 26) for c in self.cor)
        elif self.hover:
            base = tuple(min(255, c + 24) for c in self.cor)

        borda = UITheme.destaque if (self.focado or self.hover) else UITheme.borda
        self._caixa(tela, base, borda, 2 if self.focado else 1)

        cor_txt = self.cor_texto if self.ativo else UITheme.texto_fraco
        deslize = 1 if self._pressionado else 0
        img = UITheme.fonte(None, True, self.fonte).render(str(self.texto), True, cor_txt)
        tela.blit(img, (self.x + (self.width - img.get_width()) / 2,
                        self.y + (self.height - img.get_height()) / 2 + deslize))


# =============================================================================
# CHECKBOX
# =============================================================================
class Checkbox(Widget):
    """Caixa de marcação com rótulo à direita."""

    def __init__(self, texto="", marcado=False, on_change=None, tamanho=24):
        super().__init__(220, tamanho)
        self.texto = texto
        self.marcado = marcado
        self.on_change = on_change
        self.focavel = True
        self.caixa = tamanho
        img = UITheme.fonte().render(str(texto), True, UITheme.texto)
        self.width = self.caixa + 10 + img.get_width()

    def update(self):
        super().update()
        if not (self.visivel and self.ativo):
            return
        if self.hover and Window.get_instance().mouse.button_down(1):
            self.alternar()

    def tratar_tecla(self, evento):
        if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.alternar()
            return True
        return False

    def alternar(self):
        self.marcado = not self.marcado
        if self.on_change:
            self.on_change(self.marcado)

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()
        r = pygame.Rect(int(self.x), int(self.y), self.caixa, self.caixa)

        borda = UITheme.destaque if (self.focado or self.hover) else UITheme.borda
        pygame.draw.rect(tela, UITheme.fundo_alt, r)
        pygame.draw.rect(tela, borda, r, 2 if self.focado else 1)

        if self.marcado:
            m = 5
            pygame.draw.lines(tela, UITheme.destaque, False, [
                (r.left + m, r.centery),
                (r.centerx - 1, r.bottom - m),
                (r.right - m, r.top + m)
            ], 3)

        img = UITheme.fonte().render(str(self.texto), True,
                                     UITheme.texto if self.ativo else UITheme.texto_fraco)
        tela.blit(img, (self.x + self.caixa + 10,
                        self.y + (self.caixa - img.get_height()) / 2))


# =============================================================================
# SLIDER
# =============================================================================
class Slider(Widget):
    """Controle deslizante para valores contínuos (volume, dificuldade...)."""

    def __init__(self, minimo=0, maximo=100, valor=50, largura=220, altura=24,
                 on_change=None, passo=1):
        super().__init__(largura, altura)
        self.minimo = minimo
        self.maximo = maximo
        self.passo = passo
        self.valor = valor
        self.on_change = on_change
        self.focavel = True
        self._arrastando = False

    def set_valor(self, novo):
        novo = max(self.minimo, min(self.maximo, novo))
        if self.passo:
            novo = round(novo / self.passo) * self.passo
        if novo != self.valor:
            self.valor = novo
            if self.on_change:
                self.on_change(self.valor)

    def _fracao(self):
        intervalo = (self.maximo - self.minimo) or 1
        return (self.valor - self.minimo) / intervalo

    def update(self):
        super().update()
        if not (self.visivel and self.ativo):
            self._arrastando = False
            return

        mouse = Window.get_instance().mouse
        if self.hover and mouse.button_down(1):
            self._arrastando = True
        if not mouse.button_pressed(1):
            self._arrastando = False

        if self._arrastando:
            mx = mouse.get_position()[0]
            f = max(0.0, min(1.0, (mx - self.x) / max(1, self.width)))
            self.set_valor(self.minimo + f * (self.maximo - self.minimo))

    def tratar_tecla(self, evento):
        incremento = self.passo or (self.maximo - self.minimo) / 20.0
        if evento.key == pygame.K_LEFT:
            self.set_valor(self.valor - incremento)
            return True
        if evento.key == pygame.K_RIGHT:
            self.set_valor(self.valor + incremento)
            return True
        return False

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()
        cy = int(self.y + self.height / 2)

        pygame.draw.rect(tela, UITheme.fundo_alt,
                         (int(self.x), cy - 3, int(self.width), 6))
        preenchido = int(self.width * self._fracao())
        pygame.draw.rect(tela, UITheme.destaque,
                         (int(self.x), cy - 3, preenchido, 6))

        cx = int(self.x + preenchido)
        raio = 9 if (self.hover or self.focado or self._arrastando) else 7
        pygame.draw.circle(tela, UITheme.texto, (cx, cy), raio)
        if self.focado:
            pygame.draw.circle(tela, UITheme.destaque, (cx, cy), raio + 3, 2)


# =============================================================================
# ENTRADA DE TEXTO
# =============================================================================
class TextInput(Widget):
    """Campo de texto de uma linha. Útil para nome do jogador e comandos."""

    def __init__(self, texto="", largura=260, altura=40, placeholder="",
                 max_caracteres=32, on_enter=None):
        super().__init__(largura, altura)
        self.texto = texto
        self.placeholder = placeholder
        self.max_caracteres = max_caracteres
        self.on_enter = on_enter
        self.focavel = True
        self._cursor_visivel = True
        self._piscar = 0.0

    def update(self):
        super().update()
        if not (self.visivel and self.ativo):
            return

        if self.hover and Window.get_instance().mouse.button_down(1):
            self.focado = True

        self._piscar += Window.get_instance().delta_time()
        if self._piscar >= 0.5:
            self._piscar = 0.0
            self._cursor_visivel = not self._cursor_visivel

    def tratar_tecla(self, evento):
        if evento.key == pygame.K_BACKSPACE:
            self.texto = self.texto[:-1]
            return True
        if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.on_enter:
                self.on_enter(self.texto)
            return True
        if evento.key == pygame.K_TAB:
            return False       # deixa o UIManager mudar o foco
        if evento.unicode and evento.unicode.isprintable():
            if len(self.texto) < self.max_caracteres:
                self.texto += evento.unicode
            return True
        return False

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()
        borda = UITheme.destaque if self.focado else UITheme.borda
        self._caixa(tela, UITheme.fundo_alt, borda, 2 if self.focado else 1)

        mostrando = self.texto or self.placeholder
        cor = UITheme.texto if self.texto else UITheme.texto_fraco
        img = UITheme.fonte().render(mostrando, True, cor)
        px = self.x + 10
        py = self.y + (self.height - img.get_height()) / 2
        tela.blit(img, (px, py))

        if self.focado and self._cursor_visivel:
            cx = px + (UITheme.fonte().size(self.texto)[0] if self.texto else 0)
            pygame.draw.line(tela, UITheme.texto,
                             (cx + 2, py + 2), (cx + 2, py + img.get_height() - 2), 2)


# =============================================================================
# BARRA DE PROGRESSO
# =============================================================================
class ProgressBar(Widget):
    """Barra de vida, mana ou carregamento, com rótulo opcional."""

    def __init__(self, largura=220, altura=20, valor=100, valor_max=100,
                 cor=None, mostrar_texto=False, cor_fundo=None, fonte=None):
        super().__init__(largura, altura)
        self.fonte = fonte
        self.valor = valor
        self.valor_max = valor_max
        self.cor = _cor(cor, UITheme.destaque)
        self.cor_fundo = _cor(cor_fundo, UITheme.fundo_alt)
        self.mostrar_texto = mostrar_texto

    def set_valor(self, valor):
        self.valor = max(0, min(valor, self.valor_max))

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()
        self._caixa(tela, self.cor_fundo, UITheme.borda, 1)

        fracao = self.valor / self.valor_max if self.valor_max else 0
        preenchido = int((self.width - 2) * fracao)
        if preenchido > 0:
            pygame.draw.rect(tela, self.cor,
                             (int(self.x) + 1, int(self.y) + 1, preenchido, int(self.height) - 2))
        if self.mostrar_texto:
            self._texto_centro(tela, f"{int(self.valor)}/{int(self.valor_max)}",
                               UITheme.texto, max(11, int(self.height * 0.6)),
                               familia=self.fonte)


# =============================================================================
# CAIXA
# =============================================================================
class Caixa(Widget):
    """
    Um retângulo pintado, e nada mais.

    Existe porque a interface de um jogo quase sempre começa por uma tarja
    atrás do placar: o Panel organiza filhos e pinta com as cores do tema, e
    quem só quer um fundo próprio acabava desenhando na mão com pygame.
    """

    def __init__(self, largura=200, altura=60, cor=None, cor_borda=None,
                 espessura=1):
        super().__init__(largura, altura)
        self.cor = _cor(cor, UITheme.fundo)
        self.cor_borda = None if cor_borda is None else _cor(cor_borda, UITheme.borda)
        self.espessura = espessura

    def draw(self):
        if not self.visivel:
            return
        self._caixa(Window.get_screen(), self.cor, self.cor_borda, self.espessura)


# =============================================================================
# IMAGEM
# =============================================================================
class Imagem(Widget):
    """
    Uma figura da pasta do jogo dentro da interface: retrato de vida, ícone de
    chave, moldura do placar.

    Reaproveita o GameImage (e o cache de imagens dele); a diferença é que
    aqui a figura é esticada para a largura e a altura pedidas, porque numa
    interface quem manda no tamanho é o layout, não o arquivo.
    """

    def __init__(self, caminho_imagem, largura=None, altura=None):
        super().__init__(largura or 32, altura or 32)
        self.figura = GameImage(caminho_imagem)
        if largura is None:
            self.width = self.figura.width
        if altura is None:
            self.height = self.figura.height
        self._escalada = None
        self._tamanho_escala = None

    def _superficie(self):
        """Redimensionar é caro: guardamos a versão do tamanho atual."""
        alvo = (max(1, int(self.width)), max(1, int(self.height)))
        if self._tamanho_escala != alvo:
            self._escalada = pygame.transform.smoothscale(self.figura._superficie(), alvo) \
                if self.figura._superficie().get_bitsize() >= 24 \
                else pygame.transform.scale(self.figura._superficie(), alvo)
            self._tamanho_escala = alvo
        return self._escalada

    def draw(self):
        if not self.visivel:
            return
        Window.get_screen().blit(self._superficie(), (int(self.x), int(self.y)))


# =============================================================================
# PAINEL COM LAYOUT
# =============================================================================
class Panel(Widget):
    """
    Contêiner que POSICIONA os filhos sozinho — o fim do set_position() na mão.

    direcao="vertical"   empilha de cima para baixo
    direcao="horizontal" enfileira da esquerda para a direita
    """

    def __init__(self, x=0, y=0, direcao="vertical", espaco=None, padding=None,
                 fundo=True, titulo=""):
        super().__init__(0, 0)
        self.set_position(x, y)
        self.direcao = direcao
        self.espaco = UITheme.espaco if espaco is None else espaco
        self.padding = UITheme.padding if padding is None else padding
        self.fundo = fundo
        self.titulo = titulo
        self.filhos = []

    def add(self, *widgets):
        for w in widgets:
            self.filhos.append(w)
        self.organizar()
        return self

    def organizar(self):
        """Recalcula a posição de cada filho e o tamanho do painel."""
        topo = self.y + self.padding
        if self.titulo:
            topo += UITheme.fonte_tam + 8

        cx = self.x + self.padding
        cy = topo
        larg = 0
        alt = 0

        for w in self.filhos:
            if not w.visivel:
                continue
            w.set_position(cx, cy)
            if self.direcao == "vertical":
                cy += w.height + self.espaco
                larg = max(larg, w.width)
                alt = cy - topo
            else:
                cx += w.width + self.espaco
                larg = cx - (self.x + self.padding)
                alt = max(alt, w.height)

        if self.direcao == "vertical" and self.filhos:
            alt -= self.espaco
        if self.direcao == "horizontal" and self.filhos:
            larg -= self.espaco

        self.width = larg + self.padding * 2
        self.height = (topo - self.y) + max(0, alt) + self.padding

    def centralizar(self, eixo="ambos"):
        """Centraliza o painel na tela (chame depois de organizar)."""
        janela = Window.get_instance()
        if eixo in ("x", "ambos"):
            self.x = (janela.largura - self.width) / 2
        if eixo in ("y", "ambos"):
            self.y = (janela.altura - self.height) / 2
        self.organizar()
        return self

    def update(self):
        super().update()
        for w in self.filhos:
            w.update()

    def draw(self):
        if not self.visivel:
            return
        tela = Window.get_screen()
        if self.fundo:
            self._caixa(tela, UITheme.fundo, UITheme.borda, 1)
        if self.titulo:
            img = UITheme.fonte(None, True).render(self.titulo, True, UITheme.destaque)
            tela.blit(img, (self.x + self.padding, self.y + self.padding - 2))
        for w in self.filhos:
            w.draw()


# =============================================================================
# GERENCIADOR
# =============================================================================
class UIManager:
    """
    Mantém a lista de widgets, atualiza e desenha todos, e cuida do foco de
    teclado (TAB avança, SHIFT+TAB volta, ENTER aciona).
    """

    def __init__(self):
        self.widgets = []
        self._foco = -1

    def add(self, *widgets):
        for w in widgets:
            self.widgets.append(w)
        return self

    def remove(self, widget):
        if widget in self.widgets:
            self.widgets.remove(widget)

    def limpar(self):
        self.widgets = []
        self._foco = -1

    # -- foco ---------------------------------------------------------------
    def _focaveis(self):
        lista = []
        for w in self.widgets:
            if isinstance(w, Panel):
                lista += [f for f in w.filhos if f.focavel and f.visivel and f.ativo]
            elif w.focavel and w.visivel and w.ativo:
                lista.append(w)
        return lista

    def _mover_foco(self, passo):
        alvos = self._focaveis()
        if not alvos:
            return
        atual = next((i for i, w in enumerate(alvos) if w.focado), -1)
        for w in alvos:
            w.focado = False
        novo = (atual + passo) % len(alvos)
        alvos[novo].focado = True

    def focar(self, widget):
        for w in self._focaveis():
            w.focado = (w is widget)

    # -- ciclo de vida ------------------------------------------------------
    def update(self):
        janela = Window.get_instance()

        for evento in janela.eventos:
            if evento.type != pygame.KEYDOWN:
                continue
            focado = next((w for w in self._focaveis() if w.focado), None)
            if focado and focado.tratar_tecla(evento):
                continue
            if evento.key == pygame.K_TAB:
                mods = pygame.key.get_mods()
                self._mover_foco(-1 if (mods & pygame.KMOD_SHIFT) else 1)
            elif evento.key == pygame.K_DOWN:
                self._mover_foco(1)
            elif evento.key == pygame.K_UP:
                self._mover_foco(-1)

        for w in self.widgets:
            w.update()

    def draw(self):
        for w in self.widgets:
            w.draw()
