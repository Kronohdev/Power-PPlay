"""
===============================================================================
POWER PPLAY 2.1 - A ABERTURA ANIMADA
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
A marca da engine, animada, antes do jogo começar — a mesma coisa que a Unity,
a Godot e a Unreal fazem, e pelo mesmo motivo: quem joga o trabalho do aluno
fica sabendo com o que ele foi feito.

Ela aparece sozinha. Nenhuma linha do `main.py` a chama: a `Window` a toca ao
nascer, porque uma abertura que dependesse de o aluno lembrar de chamá-la não
apareceria em jogo nenhum. Para tirá-la há três caminhos, do mais local ao mais
amplo:

    Window(640, 360, "Meu jogo", intro=False)    # este jogo
    PPLAY_SEM_INTRO=1                            # esta máquina
    aba Projeto → Tela → "Abertura"              # este projeto, pela IDE

-------------------------------------------------------------------------------
COMO ELA É FEITA

Tudo é desenhado em cima da tela real — a janela de verdade, não o buffer
virtual do jogo. É de propósito: o buffer do jogo costuma ter 640×360 e seria
ampliado na hora de mostrar, e a marca sairia borrada numa janela grande.
Desenhando na tela real, a abertura fica nítida em qualquer resolução, e o
buffer do jogo nem chega a existir enquanto ela roda.

As peças caras — o halo, a vinheta, o anel, o brilho difuso do logo — são
desenhadas UMA vez, pequenas, e ampliadas com `smoothscale`. Um degradê radial
calculado pixel a pixel numa tela de 1080p custaria mais do que o quadro
inteiro; feito em 96×96 e ampliado fica igual, porque degradê suave é
exatamente o que a interpolação sabe fazer. Pela mesma razão nenhuma superfície
nasce dentro do laço: as que mudam de tamanho são redimensionadas a partir das
pequenas, e a camada das faíscas é uma só, limpa a cada quadro.

O tempo é medido em segundos de relógio, não em número de quadros. Numa máquina
que não segure 60 fps a animação fica menos fluida, mas dura o mesmo — e não
vira uma abertura de oito segundos.

NO NAVEGADOR ELA NÃO TOCA. O navegador tem uma linha de execução só, e ela
também é a que responde ao clique e ao botão de fechar: um laço de dois
segundos que não devolve o controle congela a aba inteira. O jogo exportado
para a web ganha a mesma marca em HTML, na tela de carregamento, onde ela não
disputa a linha de execução com ninguém (ver PPlay/editor/web.py).
===============================================================================
"""

import math
import os
import random
import sys

import pygame

# =============================================================================
# IDENTIDADE
# =============================================================================
# As mesmas cores da IDE (ide/src/shared/temas.ts, tema "magenta"). A abertura
# é a marca da engine e não segue o tema do jogo — é o único momento em que a
# Power PPlay aparece como ela mesma.
FUNDO = (14, 16, 21)
ACENTO = (255, 62, 200)
TEXTO = (226, 232, 242)
TEXTO_FRACO = (122, 134, 154)

TITULO = "Power PPlay"
FRASE = "jogos em Python, do desenho ao executável"

# Uma lista, e não uma fonte: `SysFont` aceita nomes separados por vírgula e
# usa o primeiro que existir. Assim a abertura sai com a fonte da interface de
# cada sistema — Segoe no Windows, DejaVu no Linux, Helvetica no macOS — em vez
# de cair na fonte padrão do pygame, que é datada.
FAMILIAS = ("segoeui,seguisb,dejavusans,ubuntu,cantarell,"
            "helveticaneue,roboto,arial,freesans")

DURACAO = 2.2          # segundos, da primeira luz ao último apagar
FPS = 60
SAIDA = 0.30           # quanto dura o apagar do fim
CORTE = 0.22           # quanto dura o apagar de quem pulou

# Abaixo disto a marca não cabe de pé: o texto ficaria ilegível e o logo, um
# borrão. Melhor não aparecer do que aparecer quebrada.
LADO_MINIMO = 220


# =============================================================================
# CURVAS
# =============================================================================
# Nenhuma animação boa é linear. Cada curva abaixo responde a uma pergunta
# diferente: "como uma coisa entra", "como ela assenta", "como ela passa".
def _fatia(t, inicio, fim):
    """Onde `t` está dentro do trecho [inicio, fim], de 0 a 1."""
    if t <= inicio:
        return 0.0
    if t >= fim:
        return 1.0
    return (t - inicio) / (fim - inicio)


def _suave(p):
    """Começa rápido e freia (cúbica de saída). O movimento do dia a dia."""
    return 1 - (1 - p) ** 3


def _expo(p):
    """Freia muito mais forte: serve para o que 'chega' e para de vez."""
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def _costas(p):
    """
    Passa do ponto e volta — o exagero de um selo batendo na mesa.

    É o que separa um logo que aparece de um logo que *chega*. A sobra é
    pequena de propósito: acima de uns 10% vira desenho animado.
    """
    c = 1.70158 * 0.62
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def _sino(p):
    """Sobe até a metade e desce: para o que passa e some."""
    return math.sin(math.pi * max(0.0, min(1.0, p)))


def _alfa(v):
    return max(0, min(255, int(v)))


# =============================================================================
# PEÇAS DESENHADAS UMA VEZ
# =============================================================================
_cache = {}


def caminho_do_logo():
    """O PNG da marca, que viaja dentro do pacote `PPlay`."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "recursos", "logo.png")


def _guardado(chave, montar):
    """Memória das peças caras. Elas não mudam enquanto a janela não muda."""
    if chave not in _cache:
        _cache[chave] = montar()
    return _cache[chave]


def _logo(altura):
    """A marca na altura pedida, já convertida."""
    def montar():
        imagem = pygame.image.load(caminho_do_logo())
        try:
            imagem = imagem.convert_alpha()
        except pygame.error:
            pass    # sem modo de vídeo definido; a superfície crua serve
        largura = max(1, round(imagem.get_width() * altura / imagem.get_height()))
        return pygame.transform.smoothscale(imagem, (largura, altura))

    return _guardado(("logo", altura), montar)


def _radial(lado, cor, perfil):
    """
    Um disco desenhado pixel a pixel, onde `perfil(d)` dá o alfa em cada raio.

    Pixel a pixel porque é a única forma de acertar o degradê: `draw.circle`
    empilhado COMPÕE alfa em vez de substituí-lo, e a soma de vinte discos
    translúcidos satura o meio em vez de fazer um degradê. Em 96×96 são nove
    mil contas, uma única vez — e o `smoothscale` faz o resto.
    """
    base = pygame.Surface((lado, lado), pygame.SRCALPHA)
    centro = (lado - 1) / 2.0
    for y in range(lado):
        dy = (y - centro) / centro
        for x in range(lado):
            dx = (x - centro) / centro
            base.set_at((x, y), cor + (_alfa(perfil(math.hypot(dx, dy))),))
    return base


def _halo(cor):
    """O clarão redondo atrás da marca, pequeno — o quadro o amplia."""
    return _guardado(
        ("halo", cor),
        lambda: _radial(96, cor, lambda d: 0 if d >= 1 else 255 * (1 - d) ** 2.4 * 0.58))


def _anel(cor):
    """
    A onda de choque da batida: um aro macio, pronto para ser ampliado.

    Guardar o aro e escalá-lo troca uma superfície de 1200×1200 por quadro —
    seis megabytes, sessenta vezes por segundo — por um `smoothscale` de 200.

    O aro é FINO, e isso precisou de duas tentativas. Com o vinco largo que ele
    tinha antes, a ampliação de três vezes transformava a onda numa rosquinha
    gorda parada em volta do logo: o que deveria ser um estalo virava um
    enfeite. A largura aqui é a que sobrevive à ampliação.
    """
    def perfil(d):
        if d >= 1:
            return 0
        return 255 * math.exp(-(((d - 0.82) / 0.030) ** 2))

    return _guardado(("anel", cor), lambda: _radial(200, cor, perfil))


def _vinheta(tamanho):
    """Escurece os cantos. É sutil de propósito: some quando se olha direto."""
    def montar():
        pequena = _radial(64, (0, 0, 0), lambda d: 118 * min(1.0, d) ** 2.6)
        return pygame.transform.smoothscale(pequena, tamanho)

    return _guardado(("vinheta", tamanho), montar)


def _borrar(superficie, passos=3):
    """
    Borra encolhendo e devolvendo ao tamanho, uma metade de cada vez.

    Encolher direto a um oitavo e devolver de uma vez NÃO borra: deixa blocos.
    Foi o primeiro jeito que tentei, e o brilho do logo saiu como um retângulo
    quadriculado atrás do desenho — dava para contar os quadrados. O filtro do
    `smoothscale` enxerga poucos vizinhos; quem suaviza é a repetição. Descendo
    e subindo de dois em dois, cada passo mistura de novo, e o que sai é um
    borrão de verdade.
    """
    largura, altura = superficie.get_size()
    atual = superficie
    for _ in range(passos):
        atual = pygame.transform.smoothscale(
            atual, (max(2, atual.get_width() // 2), max(2, atual.get_height() // 2)))
    for _ in range(passos):
        atual = pygame.transform.smoothscale(
            atual, (min(largura, atual.get_width() * 2),
                    min(altura, atual.get_height() * 2)))
    return pygame.transform.smoothscale(atual, (largura, altura))


def _difuso(logo, cor):
    """
    O brilho colorido que vaza por trás da marca.

    Discreto de propósito. Forte, ele engole o desenho: a marca vira uma mancha
    rosa e some justamente a parte que se queria mostrar. Aqui ele só dá o
    contorno de luz, e quem carrega a imagem continua sendo o logo.
    """
    def montar():
        largura, altura = logo.get_size()
        # A folga transparente em volta não é enfeite, é o que faz o brilho ter
        # forma. O PNG da marca é recortado rente ao desenho, então o desenho
        # encosta nas quatro bordas; borrado assim, ele espalha cor até o limite
        # da superfície e o que aparece atrás do logo é um RETÂNGULO rosa. Com a
        # folga, o borrão tem para onde se apagar, e vira um halo.
        folga = max(4, round(max(largura, altura) * 0.22))
        campo = pygame.Surface((largura + folga * 2, altura + folga * 2),
                               pygame.SRCALPHA)
        campo.blit(logo, (folga, folga))
        grande = _borrar(campo)
        # A cor vira o acento e a forma continua sendo a do logo: zera o RGB e
        # soma o acento por cima. O canal alfa — que é o desenho — não é tocado.
        grande.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
        grande.fill(cor + (0,), special_flags=pygame.BLEND_RGB_ADD)
        return grande

    return _guardado(("difuso", logo.get_size(), cor), montar)


def _mascara_branca(logo):
    """
    O recorte da marca, todo branco.

    BLEND_RGB_MAX leva o RGB para branco e NÃO encosta no alfa — que é o que
    interessa aqui, porque o alfa é o desenho. Serve de molde para o reflexo:
    multiplicado por ele, qualquer coisa passa a existir só onde há marca.
    """
    def montar():
        copia = logo.copy()
        copia.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
        return copia

    return _guardado(("mascara", logo.get_size()), montar)


def _faixa_de_luz(logo):
    """
    A lâmina de luz que atravessa a marca, pronta e já inclinada.

    Girar a cada quadro seria desperdício: a faixa é sempre a mesma, só muda de
    lugar. Fica guardada inclinada, e o quadro só a desloca.
    """
    def montar():
        largura, altura = logo.get_size()
        espessura = max(8, largura // 5)
        alto = int(math.hypot(largura, altura)) + espessura * 2
        tira = pygame.Surface((espessura, alto), pygame.SRCALPHA)
        for x in range(espessura):
            # Um vinco: apagado nas pontas, forte no meio, elevado ao quadrado
            # para a borda do reflexo ficar macia em vez de chapada.
            intensidade = _sino(x / (espessura - 1)) ** 2
            pygame.draw.line(tira, (255, 255, 255, _alfa(210 * intensidade)),
                             (x, 0), (x, alto))
        return pygame.transform.rotate(tira, 22)

    return _guardado(("faixa", logo.get_size()), montar)


def _linha_gradiente(largura, altura, cor):
    """Um traço que nasce e morre transparente, com o acento no meio."""
    def montar():
        base = pygame.Surface((max(2, largura), max(1, altura)), pygame.SRCALPHA)
        for x in range(base.get_width()):
            p = x / (base.get_width() - 1)
            pygame.draw.line(base, cor + (_alfa(255 * _sino(p) ** 0.7),),
                             (x, 0), (x, base.get_height()))
        return base

    return _guardado(("linha", largura, altura, cor), montar)


def _fonte(tamanho, negrito=False):
    def montar():
        try:
            return pygame.font.SysFont(FAMILIAS, tamanho, bold=negrito)
        except Exception:  # noqa: BLE001 - sistema sem fontes: a padrão resolve
            return pygame.font.Font(None, tamanho)

    return _guardado(("fonte", tamanho, negrito), montar)


# =============================================================================
# TEXTO COM ESPAÇAMENTO ANIMADO
# =============================================================================
def _escrever_espacado(destino, fonte, texto, centro_x, topo, cor, alpha, folga):
    """
    Escreve letra por letra, com `folga` pixels a mais entre elas.

    Desenhar a frase inteira de uma vez não permitiria animar o espaçamento, e
    é ele que faz a diferença: o nome entra largo e se fecha, como um letreiro
    assentando. O preço é perder o kerning do par de letras — invisível com
    folga, e por isso a folga nunca chega a zero.
    """
    if alpha <= 0:
        return
    glifos = [fonte.render(ch, True, cor) for ch in texto]
    total = sum(g.get_width() for g in glifos) + folga * (len(glifos) - 1)
    x = centro_x - total / 2
    for g in glifos:
        g.set_alpha(alpha)
        destino.blit(g, (round(x), topo))
        x += g.get_width() + folga


# =============================================================================
# AS FAÍSCAS
# =============================================================================
def _semear_faiscas(centro, raio, quantas=30):
    """
    O estouro do momento em que a marca bate.

    Cada faísca é um risco, e não um ponto: um risco na direção do movimento lê
    como velocidade, um ponto lê como sujeira na tela. O sorteio tem semente
    fixa — a abertura é a marca da engine, e marca não sai diferente a cada vez.
    """
    sorteio = random.Random(20261)
    faiscas = []
    for i in range(quantas):
        angulo = (i / quantas) * math.tau + sorteio.uniform(-0.12, 0.12)
        velocidade = raio * sorteio.uniform(1.2, 2.3)
        faiscas.append({
            "x": centro[0] + math.cos(angulo) * raio * 0.55,
            "y": centro[1] + math.sin(angulo) * raio * 0.55,
            "vx": math.cos(angulo) * velocidade,
            "vy": math.sin(angulo) * velocidade,
            "vida": sorteio.uniform(0.34, 0.72),
            "grossura": sorteio.choice((1, 1, 2)),
        })
    return faiscas


def _desenhar_faiscas(destino, faiscas, decorrido, cor):
    for f in faiscas:
        if decorrido >= f["vida"]:
            continue
        p = decorrido / f["vida"]
        # Desaceleram como se houvesse ar: rápidas no começo, quase paradas no
        # fim. `_expo` dá exatamente essa forma.
        avanco = _expo(p)
        x = f["x"] + f["vx"] * avanco * f["vida"]
        y = f["y"] + f["vy"] * avanco * f["vida"]
        rastro = max(3.0, (1 - p) * 22)
        modulo = math.hypot(f["vx"], f["vy"]) or 1.0
        dx, dy = f["vx"] / modulo, f["vy"] / modulo
        alpha = _alfa(255 * (1 - p) ** 1.4)
        if alpha <= 0:
            continue
        pygame.draw.line(destino, cor + (alpha,),
                         (x - dx * rastro, y - dy * rastro), (x, y),
                         f["grossura"])


# =============================================================================
# UM QUADRO
# =============================================================================
def _quadro(tela, t, cena, saindo):
    """Desenha o instante `t` da abertura. Sem estado: só lê o relógio."""
    largura, altura = tela.get_size()
    centro_x = largura // 2
    centro_y = cena["centro_y"]
    logo = cena["logo"]

    # O fundo ja vem com a vinheta embutida. Antes eram duas passagens pela
    # tela inteira por quadro — pintar e depois escurecer as bordas — e a 1080p
    # isso sozinho comia um terco do orcamento de 16 ms. Assim e uma copia so.
    # A vinheta passou a ficar por baixo do desenho em vez de por cima; nos
    # cantos, onde ela existe, nao ha desenho nenhum, entao a imagem e a mesma.
    tela.blit(cena["fundo"], (0, 0))

    # -- halo ---------------------------------------------------------------
    p_halo = _suave(_fatia(t, 0.00, 0.95))
    if p_halo > 0:
        # Depois de aberto, respira. É pouco — 4% — mas é o que impede a tela
        # de parecer uma imagem parada enquanto o texto entra.
        if p_halo < 1:
            # Abrindo: o tamanho muda a cada quadro, e nao ha o que guardar.
            lado = max(2, round(cena["lado_halo"] * (0.55 + 0.45 * p_halo)))
            halo = pygame.transform.smoothscale(cena["halo"], (lado, lado))
            halo.set_alpha(_alfa(255 * p_halo))
        else:
            # Aberto: o halo respira. O sopro era uma mudanca de TAMANHO, e
            # redimensionar um disco de novecentos pixels sessenta vezes por
            # segundo custava mais do que todo o resto do quadro. Respirando
            # pelo alfa o efeito e o mesmo aos olhos e a superficie e sempre a
            # mesma, ja pronta.
            halo = cena["halo_aberto"]
            lado = halo.get_width()
            halo.set_alpha(_alfa(255 * (0.90 + 0.10 * math.sin((t - 0.4) * 2.1))))
        tela.blit(halo, (centro_x - lado // 2, centro_y - lado // 2))

    # -- a marca ------------------------------------------------------------
    p_entrada = _fatia(t, 0.10, 0.74)
    if p_entrada > 0:
        escala = 0.70 + 0.30 * _costas(p_entrada)
        opacidade = _alfa(255 * _expo(_fatia(t, 0.10, 0.44)))
        subida = (1 - _suave(p_entrada)) * altura * 0.022
        lado_l = max(1, round(logo.get_width() * escala))
        lado_a = max(1, round(logo.get_height() * escala))
        pos = (centro_x - lado_l // 2, round(centro_y - lado_a // 2 + subida))

        difuso = pygame.transform.smoothscale(
            cena["difuso"], (max(1, round(cena["difuso"].get_width() * escala)),
                             max(1, round(cena["difuso"].get_height() * escala))))
        # O brilho pulsa mais forte logo depois da batida e assenta.
        forca = 0.55 + 0.45 * math.exp(-max(0.0, t - 0.66) * 3.1)
        difuso.set_alpha(_alfa(118 * (opacidade / 255.0) * forca))
        tela.blit(difuso, (centro_x - difuso.get_width() // 2,
                           round(centro_y - difuso.get_height() // 2 + subida)))

        marca = pygame.transform.smoothscale(logo, (lado_l, lado_a))
        marca.set_alpha(opacidade)
        tela.blit(marca, pos)

        # -- o reflexo que atravessa ---------------------------------------
        p_luz = _fatia(t, 0.76, 1.34)
        if 0 < p_luz < 1:
            faixa = cena["faixa"]
            # Quando o reflexo comeca (0,76 s) a marca ja assentou no tamanho
            # dela, entao o molde guardado serve como esta e a camada pode ser
            # sempre a mesma, so limpa. O caminho de baixo existe para o caso
            # de alguem mexer nos tempos e as duas coisas deixarem de coincidir.
            if (lado_l, lado_a) == logo.get_size():
                molde = cena["molde"]
                camada = cena["camada_luz"]
                camada.fill((0, 0, 0, 0))
            else:
                molde = pygame.transform.smoothscale(
                    _mascara_branca(logo), (lado_l, lado_a))
                camada = pygame.Surface((lado_l, lado_a), pygame.SRCALPHA)
            # Vai de fora à esquerda até fora à direita, com folga dos dois
            # lados para não aparecer nem sumir dentro do desenho.
            x = -faixa.get_width() + _suave(p_luz) * (lado_l + faixa.get_width())
            camada.blit(faixa, (round(x), (lado_a - faixa.get_height()) // 2))
            # Existe só onde há marca: multiplicar pelo molde zera o resto.
            camada.blit(molde, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            camada.set_alpha(_alfa(255 * _sino(p_luz) ** 0.5))
            tela.blit(camada, pos)

    # -- a batida: onda e faíscas -------------------------------------------
    p_onda = _fatia(t, 0.62, 1.18)
    # Para no 0,72 e nao no 1: dali para a frente o alfa ja caiu para menos de
    # dez em 255 — invisivel — e o aro e o maior de todos, quase um megapixel
    # de `smoothscale` por quadro. Os quadros mais caros da animacao eram os
    # que nao mostravam nada.
    if 0 < p_onda < 0.72:
        lado = max(4, round(cena["raio"] * 2 * (1.0 + 2.0 * _suave(p_onda))))
        anel = pygame.transform.smoothscale(cena["anel"], (lado, lado))
        anel.set_alpha(_alfa(165 * (1 - p_onda) ** 2.0))
        tela.blit(anel, (centro_x - lado // 2, centro_y - lado // 2))

    if 0.62 <= t < 1.40:
        # A camada cobre so o alcance das faiscas, e nao a tela: limpar e
        # compor dois megapixels por quadro para desenhar trinta risquinhos no
        # meio deles era o maior desperdicio da animacao.
        camada = cena["camada_faiscas"]
        camada.fill((0, 0, 0, 0))
        _desenhar_faiscas(camada, cena["faiscas"], t - 0.62, ACENTO)
        tela.blit(camada, cena["pos_faiscas"])

    # -- o nome --------------------------------------------------------------
    p_nome = _fatia(t, 0.80, 1.42)
    if p_nome > 0:
        suave = _suave(p_nome)
        _escrever_espacado(
            tela, cena["fonte_titulo"], TITULO, centro_x,
            round(cena["y_titulo"] + (1 - suave) * altura * 0.016),
            TEXTO, _alfa(255 * _expo(_fatia(t, 0.80, 1.20))),
            cena["folga_titulo"] * (1 - suave) + cena["folga_final"])

    # -- a frase -------------------------------------------------------------
    p_frase = _fatia(t, 1.04, 1.58)
    if p_frase > 0:
        imagem = cena["fonte_frase"].render(FRASE, True, TEXTO_FRACO)
        imagem.set_alpha(_alfa(255 * _expo(p_frase)))
        tela.blit(imagem, (centro_x - imagem.get_width() // 2,
                           round(cena["y_frase"]
                                 + (1 - _suave(p_frase)) * altura * 0.012)))

    # -- o traço -------------------------------------------------------------
    p_traco = _fatia(t, 1.24, 1.86)
    if p_traco > 0:
        cheio = cena["linha"]
        largura_atual = max(2, round(cheio.get_width() * _suave(p_traco)))
        traco = pygame.transform.smoothscale(
            cheio, (largura_atual, cheio.get_height()))
        traco.set_alpha(_alfa(210 * _expo(p_traco)))
        tela.blit(traco, (centro_x - largura_atual // 2, cena["y_linha"]))

    # -- a saída -------------------------------------------------------------
    if saindo is not None:
        veu = cena["veu"]
        veu.set_alpha(_alfa(255 * _expo(min(1.0, saindo))))
        tela.blit(veu, (0, 0))


# =============================================================================
# TOCAR
# =============================================================================
def _montar(tela):
    """Tudo o que não muda de quadro para quadro, calculado uma vez só."""
    largura, altura = tela.get_size()
    # A marca ocupa 30% do menor lado. Em 640×360 dá 108 px; em 1920×1080, 324.
    # Proporcional, e não fixa, para a abertura ter o mesmo peso em qualquer
    # janela.
    lado = max(48, round(min(largura, altura) * 0.30))
    logo = _logo(lado)
    escala = altura / 720.0

    centro_y = round(altura * 0.42)
    raio = max(logo.get_width(), logo.get_height()) // 2

    tamanho_titulo = max(15, round(34 * escala))
    tamanho_frase = max(10, round(15 * escala))
    fonte_titulo = _fonte(tamanho_titulo, negrito=True)
    fonte_frase = _fonte(tamanho_frase)

    y_titulo = centro_y + raio + round(altura * 0.055)
    y_frase = y_titulo + fonte_titulo.get_height() + round(altura * 0.012)
    y_linha = y_frase + fonte_frase.get_height() + round(altura * 0.038)

    veu = pygame.Surface((largura, altura))
    veu.fill(FUNDO)

    # O fundo pronto: a cor e a vinheta numa superfície opaca só.
    fundo = pygame.Surface((largura, altura))
    fundo.fill(FUNDO)
    fundo.blit(_vinheta((largura, altura)), (0, 0))

    lado_halo = max(120, round(min(largura, altura) * 0.84))
    halo = _halo(ACENTO)
    halo_aberto = pygame.transform.smoothscale(halo, (lado_halo, lado_halo))

    # As faíscas só alcançam um pedaço da tela; a camada delas tem esse pedaço
    # e mais uma folga para o rastro. Elas nascem no centro DA CAMADA, e é a
    # camada que vai para o lugar certo na hora de compor.
    alcance = round(raio * 2.3) + 30
    pos_faiscas = (largura // 2 - alcance, centro_y - alcance)

    return {
        "logo": logo,
        "difuso": _difuso(logo, ACENTO),
        "faixa": _faixa_de_luz(logo),
        "halo": halo,
        "halo_aberto": halo_aberto,
        "lado_halo": lado_halo,
        "anel": _anel(ACENTO),
        "fundo": fundo,
        "molde": _mascara_branca(logo),
        "camada_luz": pygame.Surface(logo.get_size(), pygame.SRCALPHA),
        "faiscas": _semear_faiscas((alcance, alcance), raio),
        "camada_faiscas": pygame.Surface((alcance * 2, alcance * 2),
                                         pygame.SRCALPHA),
        "pos_faiscas": pos_faiscas,
        "linha": _linha_gradiente(max(60, round(200 * escala)),
                                  max(2, round(3 * escala)), ACENTO),
        "veu": veu,
        "fonte_titulo": fonte_titulo,
        "fonte_frase": fonte_frase,
        "folga_titulo": tamanho_titulo * 0.34,   # aberto, no começo
        "folga_final": tamanho_titulo * 0.02,    # quase fechado, no fim
        "centro_y": centro_y,
        "raio": raio,
        "y_titulo": y_titulo,
        "y_frase": y_frase,
        "y_linha": y_linha,
    }


def desativada():
    """A variável de ambiente que desliga a abertura nesta máquina."""
    return os.environ.get("PPLAY_SEM_INTRO", "").strip().lower() in (
        "1", "true", "sim", "yes", "on")


def suportada(tela=None):
    """
    Dá para tocar a abertura aqui?

    O navegador fica de fora por construção (ver o cabeçalho do módulo), e uma
    janela pequena demais também: a marca não caberia de pé.
    """
    if sys.platform == "emscripten":
        return False
    if desativada():
        return False
    if not os.path.isfile(caminho_do_logo()):
        return False
    if tela is not None:
        largura, altura = tela.get_size()
        if min(largura, altura) < LADO_MINIMO:
            return False
    return True


def tocar(tela, duracao=DURACAO, fps=FPS):
    """
    Toca a abertura na superfície `tela` e devolve quando terminar.

    Qualquer tecla, clique ou botão do controle corta para o fim — e corta com
    um apagar de 0,22 s, porque um corte seco parece travamento. Fechar a
    janela durante a abertura fecha o jogo, como fecharia depois.
    """
    relogio = pygame.time.Clock()
    cena = _montar(tela)
    inicio = pygame.time.get_ticks() / 1000.0
    pulou_em = None

    while True:
        agora = pygame.time.get_ticks() / 1000.0
        t = agora - inicio

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if pulou_em is None and evento.type in (
                    pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
                pulou_em = agora

        if pulou_em is None:
            if t >= duracao:
                break
            saindo = None if t < duracao - SAIDA else (t - (duracao - SAIDA)) / SAIDA
        else:
            saindo = (agora - pulou_em) / CORTE
            if saindo >= 1:
                break

        _quadro(tela, min(t, duracao), cena, saindo)
        pygame.display.flip()
        relogio.tick(fps)

    tela.fill(FUNDO)
    pygame.display.flip()


def abrir(tela, ativa=None):
    """
    O ponto por onde a `Window` chama — e que nunca deixa um erro passar.

    Uma abertura que quebrasse levaria junto o jogo do aluno, que não tem nada
    a ver com ela. Qualquer falha aqui é engolida: o jogo começa sem a marca, e
    é como se ela nunca tivesse existido.
    """
    if ativa is False:
        return False
    try:
        if not suportada(tela):
            return False
        if not pygame.font.get_init():
            pygame.font.init()
        tocar(tela)
        return True
    except SystemExit:
        raise                  # fechar a janela durante a abertura fecha o jogo
    except Exception:  # noqa: BLE001
        try:
            tela.fill(FUNDO)
            pygame.display.flip()
        except Exception:  # noqa: BLE001
            pass
        return False
