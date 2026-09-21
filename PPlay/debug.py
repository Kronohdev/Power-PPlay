"""
===============================================================================
POWER PPLAY 2.1 - MODO DE DEPURAÇÃO VISUAL
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Por que este módulo existe:

O aluno vê o desenho do sprite; a engine enxerga uma caixa de colisão que
quase nunca tem o mesmo tamanho. Quando o personagem "enrosca numa quina
invisível" ou "flutua um pouco acima do chão", o que está errado não é o
desenho, é a distância entre esses dois retângulos — e ela é invisível.

Este módulo desenha por cima do jogo o modelo que a engine tem do mundo: a
caixa que de fato colide, o quadro do sprite por trás dela, a velocidade, se
o corpo está apoiado e quais blocos são sólidos. O aluno aperta uma tecla e
para de adivinhar.

    from PPlay.debug import Debug
    Debug.observar(jogador, "heroi")     # uma vez, na preparação do jogo
    Debug.tecla("f3")                    # dentro do laço: liga e desliga
    Debug.solidos(mapa.get_solidos())    # dentro do laço, antes de desenhar
    Debug.desenhar()                     # último desenho do quadro
===============================================================================
"""

import contextlib
import time
import weakref

import pygame

from .camera import Camera
from .window import Window


# =============================================================================
# PALETA
# =============================================================================
# Todas as cores levam um contorno escuro atrás (COR_CONTORNO). Sem isso, o
# verde da caixa some num cenário claro e o cinza do quadro some num cenário
# escuro — e o depurador só serve se for legível nos dois.
COR_CONTORNO = (10, 12, 18, 220)
COR_CAIXA_COLISAO = (60, 255, 140, 255)   # o que a engine usa para colidir
COR_QUADRO_SPRITE = (225, 230, 240, 110)  # o quadro do desenho, apagado
COR_VELOCIDADE = (255, 205, 60, 255)
COR_NO_CHAO = (90, 255, 170, 255)
COR_NO_AR = (150, 158, 175, 180)
COR_SOLIDO = (90, 165, 255, 190)
COR_PAINEL_FUNDO = (14, 17, 24, 165)      # translúcido: o cenário aparece atrás
COR_PAINEL_BORDA = (90, 160, 255, 120)
COR_TEXTO = (236, 241, 250, 255)
COR_TEXTO_FRACO = (150, 162, 185, 255)
COR_LEGENDA_FUNDO = (14, 17, 24, 170)
COR_ACENTO = (90, 200, 255, 255)


class Debug:
    """
    Modo de depuração visual, com estado de classe — como o SoundManager.

    É de classe de propósito: o aluno liga o depurador em qualquer ponto do
    programa sem ter de carregar um objeto de uma função para a outra.
    """

    # --- estado visível -----------------------------------------------------
    ativo = False
    TECLA = "f3"                 # guardada para a legenda dizer o que desliga

    # Onde os números aparecem:
    #   "auto"     - na IDE quando ela está ouvindo, senão a tarja no jogo
    #   "compacto" - só a tarja de uma linha
    #   "completo" - a tarja mais a lista de objetos (o formato antigo)
    #   "nenhum"   - nada escrito sobre o jogo, só a geometria
    PAINEL = "auto"
    SEGUNDOS_LEGENDA = 4.0       # depois disso a dica de tecla some sozinha
    HZ_CANAL = 12.0              # quantas vezes por segundo a IDE é avisada

    # --- ajustes ------------------------------------------------------------
    ESCALA_VELOCIDADE = 0.12     # pixels de linha por pixel/segundo
    COMPRIMENTO_MAXIMO = 130     # teto do vetor, senão a queda livre sai da tela
    TAMANHO_FONTE = 13
    NOME_FONTE = "Consolas"      # largura fixa: os números do painel não dançam
    MARGEM = 8

    # --- estado interno -----------------------------------------------------
    _observados = []             # lista de (weakref, rotulo)
    _solidos_do_quadro = ()      # referência à lista do quadro, nunca uma cópia
    _solidos_desenhados = 0
    _tempos_quadro = {}          # medições somadas dentro do quadro atual
    _tempos = {}                 # o que o painel mostra (o quadro anterior)
    _camada = None               # superfície com canal alfa, reaproveitada
    _fonte = None
    _fonte_forte = None
    _canal = None                # para onde mandar os números (a IDE)
    _ultimo_envio = 0.0
    _ligado_em = 0.0             # para a legenda saber quando se apagar

    # =========================================================================
    # LIGAR E DESLIGAR
    # =========================================================================
    @classmethod
    def alternar(cls):
        """Inverte o modo e devolve o novo estado."""
        cls.ativo = not cls.ativo
        if cls.ativo:
            cls._ligado_em = time.monotonic()
        if not cls.ativo:
            # Desligar tem de devolver a memória: a lista de sólidos do último
            # quadro pode ter centenas de tiles presos aqui.
            cls._esvaziar_quadro()
        return cls.ativo

    @classmethod
    def ligar(cls):
        if not cls.ativo:
            cls._ligado_em = time.monotonic()
        cls.ativo = True
        return cls.ativo

    @classmethod
    def desligar(cls):
        cls.ativo = False
        cls._esvaziar_quadro()
        return cls.ativo

    @classmethod
    def tecla(cls, nome="f3"):
        """
        Confere a tecla e alterna sozinho. Chame UMA vez por quadro.

            Debug.tecla("f3")

        Usa key_down (o quadro em que a tecla desceu), e não key_pressed, para
        segurar a tecla não piscar o modo dezenas de vezes por segundo.
        """
        cls.TECLA = str(nome)
        try:
            teclado = Window.get_instance().keyboard
        except Exception:
            # Sem janela não há teclado — e o depurador nunca pode ser o
            # motivo de o jogo do aluno parar de rodar.
            return cls.ativo
        if teclado.key_down(cls.TECLA):
            cls.alternar()
        return cls.ativo

    # =========================================================================
    # OBJETOS OBSERVADOS
    # =========================================================================
    @classmethod
    def observar(cls, objeto, rotulo=None):
        """
        Passa a seguir este objeto enquanto o modo estiver ligado.

        Vale chamar na preparação do jogo, com o modo ainda desligado: só o
        desenho depende de estar ligado, o cadastro não.
        """
        if objeto is None or cls._ja_observado(objeto):
            return objeto
        try:
            referencia = weakref.ref(objeto)
        except TypeError:
            # Nem todo objeto aceita weakref (tuplas, por exemplo). Preferimos
            # ignorá-lo a segurá-lo forte e vazar memória do jogo.
            return objeto
        cls._observados.append((referencia, rotulo or cls._rotulo_padrao(objeto)))
        return objeto

    @classmethod
    def esquecer(cls, objeto):
        """Para de seguir o objeto. Devolve True se ele estava na lista."""
        antes = len(cls._observados)
        cls._observados = [(r, n) for (r, n) in cls._observados
                           if r() is not None and r() is not objeto]
        return len(cls._observados) < antes

    @classmethod
    def esquecer_todos(cls):
        cls._observados = []

    @classmethod
    def observados(cls):
        """
        Os objetos vivos que estão sendo seguidos, como [(objeto, rotulo)].

        A limpeza dos mortos acontece aqui: guardamos weakref, então um inimigo
        destruído pelo jogo some da lista sozinho, sem o aluno ter de avisar.
        """
        vivos = []
        sobreviventes = []
        for referencia, rotulo in cls._observados:
            objeto = referencia()
            if objeto is None:
                continue
            sobreviventes.append((referencia, rotulo))
            vivos.append((objeto, rotulo))
        cls._observados = sobreviventes
        return vivos

    @classmethod
    def _ja_observado(cls, objeto):
        return any(r() is objeto for r, _ in cls._observados)

    @classmethod
    def _rotulo_padrao(cls, objeto):
        for atributo in ("nome", "rotulo"):
            valor = getattr(objeto, atributo, None)
            if isinstance(valor, str) and valor:
                return valor
        return type(objeto).__name__.lower()

    # =========================================================================
    # DADOS DO QUADRO
    # =========================================================================
    @classmethod
    def solidos(cls, lista):
        """
        Entrega os blocos sólidos deste quadro, para o depurador desenhá-los.

            Debug.solidos(mapa.get_solidos())

        Desligado, não guarda nada: esta chamada acontece todo quadro com a
        lista inteira do mapa, e é justamente o custo que não pode existir com
        o modo fora do ar.
        """
        if not cls.ativo:
            return
        cls._solidos_do_quadro = lista if lista is not None else ()

    # =========================================================================
    # O CANAL PARA A IDE
    # =========================================================================
    @classmethod
    def canal(cls, funcao):
        """
        Define para onde mandar os números do quadro; None desliga.

        Quem chama isto é o executor da IDE, não o aluno. A função recebe um
        dicionário pronto para virar JSON — nada de objetos do pygame, porque
        do outro lado do cano há um processo diferente.
        """
        cls._canal = funcao
        cls._ultimo_envio = 0.0
        return funcao

    @classmethod
    def ouvindo(cls):
        """Alguém está recebendo os números? (a IDE, normalmente)"""
        return cls._canal is not None

    @classmethod
    def dados(cls, janela=None, observados=None):
        """
        O estado do quadro como números puros, pronto para serializar.

        É a mesma informação que a tarja mostraria — a diferença é que aqui
        ela sai inteira, sem caber em 40 colunas de fonte monoespaçada.
        """
        if janela is None:
            janela = Window.get_instance()
        if observados is None:
            observados = cls.observados()

        objetos = []
        for objeto, rotulo in observados:
            objetos.append({
                "rotulo": rotulo,
                "x": cls._numero(getattr(objeto, "x", None)),
                "y": cls._numero(getattr(objeto, "y", None)),
                "vx": cls._numero(getattr(objeto, "vx", None)),
                "vy": cls._numero(getattr(objeto, "vy", None)),
                "no_chao": cls._apoiado(objeto),
                "caixa": cls._medidas_caixa(objeto),
                "quadro": cls._medidas_quadro(objeto),
            })

        return {
            "ativo": cls.ativo,
            "fps": round(float(janela.get_fps()), 1),
            "ms": round(float(janela.delta_time()) * 1000.0, 2),
            "solidos": len(cls._solidos_do_quadro),
            "solidos_na_tela": cls._solidos_desenhados,
            "objetos": objetos,
            "tempos": {n: round(v, 3) for n, v in cls._tempos.items()},
        }

    @classmethod
    def _avisar_canal(cls, janela, observados):
        """Manda os números para a IDE, no máximo HZ_CANAL vezes por segundo."""
        if cls._canal is None:
            return
        agora = time.monotonic()
        if agora - cls._ultimo_envio < 1.0 / max(1.0, cls.HZ_CANAL):
            return
        cls._ultimo_envio = agora
        try:
            cls._canal(cls.dados(janela, observados))
        except Exception:
            # Um cano quebrado (a IDE fechou) não pode derrubar o jogo.
            cls._canal = None

    @classmethod
    def _apoiado(cls, objeto):
        no_chao = getattr(objeto, "no_chao", None)
        if no_chao is None:
            corpo = getattr(objeto, "body", None)
            no_chao = getattr(corpo, "no_chao", None) if corpo is not None else None
        return None if no_chao is None else bool(no_chao)

    @classmethod
    def _medidas_caixa(cls, objeto):
        x = cls._numero(getattr(objeto, "caixa_x", None))
        y = cls._numero(getattr(objeto, "caixa_y", None))
        larg = cls._numero(getattr(objeto, "caixa_largura", None))
        alt = cls._numero(getattr(objeto, "caixa_altura", None))
        if None in (x, y, larg, alt):
            return None
        return [round(x, 1), round(y, 1), round(larg, 1), round(alt, 1)]

    @classmethod
    def _medidas_quadro(cls, objeto):
        larg = cls._numero(getattr(objeto, "width", None))
        alt = cls._numero(getattr(objeto, "height", None))
        if None in (larg, alt):
            return None
        return [round(larg, 1), round(alt, 1)]

    @classmethod
    def medir(cls, nome):
        """
        Cronometra um trecho. Serve de contexto e de decorador.

            with Debug.medir("fisica"):
                jogador.update_physics(solidos)

            @Debug.medir("inimigos")
            def atualizar_inimigos(): ...

        Desligado, não cronometra nem soma nada.
        """
        return _Medicao(nome)

    @classmethod
    def _somar_tempo(cls, nome, milissegundos):
        cls._tempos_quadro[nome] = cls._tempos_quadro.get(nome, 0.0) + milissegundos

    @classmethod
    def _esvaziar_quadro(cls):
        cls._solidos_do_quadro = ()
        cls._solidos_desenhados = 0
        cls._tempos_quadro = {}
        cls._tempos = {}

    # =========================================================================
    # DESENHO
    # =========================================================================
    @classmethod
    def desenhar(cls, camera=None):
        """
        Desenha o modelo do mundo por cima do jogo. Chame por último.

        A primeira linha é a que importa: desligado, isto custa uma
        comparação de booleano e mais nada.
        """
        if not cls.ativo:
            return

        janela = Window.get_instance()
        camada = cls._obter_camada(janela)
        if camada is None:
            return

        if camera is None:
            camera = Camera.get_instance()

        observados = cls.observados()
        cls._desenhar_solidos(camada, camera, janela)
        for objeto, _rotulo in observados:
            cls._desenhar_objeto(camada, camera, objeto)

        # Os números vão para a IDE se ela estiver ouvindo. Isso acontece
        # antes de decidir o que escrever na tela, porque é justamente o que
        # decide: com a IDE mostrando, o jogo não precisa escrever nada.
        cls._avisar_canal(janela, observados)

        modo = cls._modo_do_painel()
        if modo != "nenhum":
            cls._desenhar_tarja(camada, janela, observados)
        if modo == "completo":
            cls._desenhar_lista(camada, janela, observados)
        cls._desenhar_legenda(camada, janela)

        janela.screen.blit(camada, (0, 0))

        # As medições valem por quadro: o painel mostra as do quadro que
        # acabou de rodar e o próximo começa do zero.
        cls._tempos = cls._tempos_quadro
        cls._tempos_quadro = {}

    # -- blocos sólidos -------------------------------------------------------
    @classmethod
    def _desenhar_solidos(cls, camada, camera, janela):
        cls._solidos_desenhados = 0
        tela = pygame.Rect(0, 0, janela.largura, janela.altura)
        for solido in cls._solidos_do_quadro:
            retangulo = cls._retangulo_quadro(solido, camera)
            if retangulo is None or not tela.colliderect(retangulo):
                continue
            pygame.draw.rect(camada, COR_SOLIDO, retangulo, 1)
            cls._solidos_desenhados += 1

    # -- um objeto observado --------------------------------------------------
    @classmethod
    def _desenhar_objeto(cls, camada, camera, objeto):
        quadro = cls._retangulo_quadro(objeto, camera)
        caixa = cls._retangulo_caixa(objeto, camera)

        # O quadro vem primeiro e apagado; a caixa por cima e viva. A diferença
        # entre os dois é o que o aluno veio ver.
        if quadro is not None and quadro != caixa:
            cls._contornar(camada, quadro, COR_QUADRO_SPRITE, 1)
        if caixa is not None:
            cls._contornar(camada, caixa, COR_CAIXA_COLISAO, 2)
            cls._desenhar_velocidade(camada, objeto, caixa)
            cls._desenhar_apoio(camada, objeto, caixa)

    @classmethod
    def _desenhar_velocidade(cls, camada, objeto, caixa):
        vx = cls._numero(getattr(objeto, "vx", None))
        vy = cls._numero(getattr(objeto, "vy", None))
        if vx is None and vy is None:
            return
        vx = vx or 0.0
        vy = vy or 0.0

        comprimento = (vx * vx + vy * vy) ** 0.5 * cls.ESCALA_VELOCIDADE
        if comprimento < 2:
            return
        fator = min(1.0, cls.COMPRIMENTO_MAXIMO / comprimento)
        origem = caixa.center
        destino = (origem[0] + vx * cls.ESCALA_VELOCIDADE * fator,
                   origem[1] + vy * cls.ESCALA_VELOCIDADE * fator)

        pygame.draw.line(camada, COR_CONTORNO, origem, destino, 5)
        pygame.draw.line(camada, COR_VELOCIDADE, origem, destino, 2)
        cls._desenhar_ponta(camada, origem, destino)

    @classmethod
    def _desenhar_ponta(cls, camada, origem, destino):
        """A setinha na ponta: sem ela, a linha não diz para que lado o corpo vai."""
        dx = destino[0] - origem[0]
        dy = destino[1] - origem[1]
        tamanho = (dx * dx + dy * dy) ** 0.5
        if tamanho < 6:
            return
        ux, uy = dx / tamanho, dy / tamanho
        recuo = 8
        largura = 4
        base = (destino[0] - ux * recuo, destino[1] - uy * recuo)
        pontos = [destino,
                  (base[0] - uy * largura, base[1] + ux * largura),
                  (base[0] + uy * largura, base[1] - ux * largura)]
        pygame.draw.polygon(camada, COR_VELOCIDADE, pontos)

    @classmethod
    def _desenhar_apoio(cls, camada, objeto, caixa):
        """A marca sob os pés: barra acesa quando o corpo está apoiado."""
        no_chao = getattr(objeto, "no_chao", None)
        if no_chao is None:
            corpo = getattr(objeto, "body", None)
            no_chao = getattr(corpo, "no_chao", None) if corpo is not None else None
        if no_chao is None:
            return

        altura = 3 if no_chao else 2
        barra = pygame.Rect(caixa.left, caixa.bottom + 2, caixa.width, altura)
        pygame.draw.rect(camada, COR_CONTORNO, barra.inflate(2, 2))
        pygame.draw.rect(camada, COR_NO_CHAO if no_chao else COR_NO_AR, barra)

    # -- a tarja de uma linha -------------------------------------------------
    @classmethod
    def _modo_do_painel(cls):
        """
        Decide o que escrever sobre o jogo.

        "auto" é o padrão e significa: se a IDE está mostrando os números, o
        jogo não escreve nada — dois lugares com a mesma informação, um deles
        por cima do cenário, é pior do que um só.
        """
        modo = str(cls.PAINEL).lower()
        if modo == "auto":
            return "nenhum" if cls.ouvindo() else "compacto"
        if modo not in ("compacto", "completo", "nenhum"):
            return "compacto"
        return modo

    @classmethod
    def _desenhar_tarja(cls, camada, janela, observados):
        """Uma linha só, no alto à esquerda, com o cenário visível atrás."""
        fonte = cls._obter_fonte()
        tecla = str(cls.TECLA).upper()
        texto = (f"{tecla}  {janela.get_fps():.0f} fps  "
                 f"{janela.delta_time() * 1000.0:.1f} ms  "
                 f"{len(observados)} obj  {len(cls._solidos_do_quadro)} sol")
        if cls._tempos:
            mais_caro = max(cls._tempos.items(), key=lambda par: par[1])
            texto += f"  {mais_caro[0]} {mais_caro[1]:.1f} ms"

        imagem = fonte.render(texto, True, COR_TEXTO)
        fundo = pygame.Rect(cls.MARGEM, cls.MARGEM,
                            imagem.get_width() + 18, imagem.get_height() + 8)
        pygame.draw.rect(camada, COR_PAINEL_FUNDO, fundo, border_radius=4)
        pygame.draw.rect(camada, COR_PAINEL_BORDA, fundo, 1, border_radius=4)
        # um ponto de cor à esquerda diz "ligado" sem gastar palavra
        pygame.draw.circle(camada, COR_ACENTO, (fundo.left + 8, fundo.centery), 3)
        camada.blit(imagem, (fundo.left + 15, fundo.top + 4))

    # -- a lista, quando pedida -----------------------------------------------
    @classmethod
    def _desenhar_lista(cls, camada, janela, observados):
        """
        A lista de objetos, encostada à direita.

        Só entra com PAINEL="completo". Fica à direita porque o começo de fase
        põe o jogador à esquerda, e era ali que o painel antigo caía em cima.
        """
        linhas = [(cls._linha_do_objeto(o, r), COR_TEXTO) for o, r in observados]
        for nome in sorted(cls._tempos):
            linhas.append((f"{nome}: {cls._tempos[nome]:.2f} ms", COR_TEXTO_FRACO))
        if not linhas:
            return

        fonte = cls._obter_fonte()
        altura_linha = fonte.get_linesize()
        largura = max(fonte.size(t)[0] for t, _c in linhas) + 16
        altura = altura_linha * len(linhas) + 10
        fundo = pygame.Rect(janela.largura - cls.MARGEM - largura,
                            cls.MARGEM * 2 + fonte.get_linesize() + 8,
                            largura, altura)

        pygame.draw.rect(camada, COR_PAINEL_FUNDO, fundo, border_radius=4)
        pygame.draw.rect(camada, COR_PAINEL_BORDA, fundo, 1, border_radius=4)
        y = fundo.top + 5
        for texto, cor in linhas:
            camada.blit(fonte.render(texto, True, cor), (fundo.left + 8, y))
            y += altura_linha

    @classmethod
    def _linha_do_objeto(cls, objeto, rotulo):
        x = cls._numero(getattr(objeto, "x", None)) or 0.0
        y = cls._numero(getattr(objeto, "y", None)) or 0.0
        partes = [f"{rotulo[:14]:<14}", f"pos {x:6.0f},{y:6.0f}"]

        vx = cls._numero(getattr(objeto, "vx", None))
        vy = cls._numero(getattr(objeto, "vy", None))
        if vx is None and vy is None:
            partes.append("vel    --,    --")
        else:
            partes.append(f"vel {vx or 0.0:6.0f},{vy or 0.0:6.0f}")

        no_chao = getattr(objeto, "no_chao", None)
        if no_chao is not None:
            partes.append("chao" if no_chao else " ar ")
        return "  ".join(partes)

    # -- legenda --------------------------------------------------------------
    @classmethod
    def _desenhar_legenda(cls, camada, janela):
        """
        A dica da tecla, que se apaga sozinha.

        Ela serve para o aluno descobrir como desligar na primeira vez. Depois
        disso é só mancha sobre o cenário, então some ao fim de
        SEGUNDOS_LEGENDA — com um esmaecer, para não parecer defeito.
        """
        vivo = time.monotonic() - cls._ligado_em
        if vivo > cls.SEGUNDOS_LEGENDA + 1.0:
            return
        opacidade = 1.0
        if vivo > cls.SEGUNDOS_LEGENDA:
            opacidade = 1.0 - (vivo - cls.SEGUNDOS_LEGENDA)

        fonte = cls._obter_fonte()
        texto = f"depuracao ligada - aperte {str(cls.TECLA).upper()} para desligar"
        explicacao = "  |  verde = caixa que colide, cinza = quadro"
        # A explicação só entra se couber inteira: meia frase cortada na borda
        # confunde mais do que ajuda.
        disponivel = janela.largura - cls.MARGEM * 2 - 12
        if fonte.size(texto + explicacao)[0] <= disponivel:
            texto += explicacao

        imagem = fonte.render(texto, True, COR_TEXTO)
        altura = imagem.get_height() + 6
        fundo = pygame.Rect(cls.MARGEM, janela.altura - cls.MARGEM - altura,
                            imagem.get_width() + 12, altura)

        cor_fundo = COR_LEGENDA_FUNDO[:3] + (int(COR_LEGENDA_FUNDO[3] * opacidade),)
        pygame.draw.rect(camada, cor_fundo, fundo, border_radius=4)
        imagem.set_alpha(int(255 * opacidade))
        camada.blit(imagem, (fundo.left + 6, fundo.top + 3))

    # =========================================================================
    # APOIO
    # =========================================================================
    @classmethod
    def _obter_camada(cls, janela):
        """
        A superfície transparente onde tudo é desenhado, criada uma vez só.

        Desenhar direto na tela impediria o cinza apagado do quadro do sprite:
        as funções do pygame.draw não misturam alfa com o que está embaixo.
        """
        tamanho = (janela.largura, janela.altura)
        if cls._camada is None or cls._camada.get_size() != tamanho:
            try:
                cls._camada = pygame.Surface(tamanho, pygame.SRCALPHA)
            except pygame.error:
                return None
        cls._camada.fill((0, 0, 0, 0))
        return cls._camada

    @classmethod
    def _obter_fonte(cls):
        if cls._fonte is None:
            cls._fonte = pygame.font.SysFont(cls.NOME_FONTE, cls.TAMANHO_FONTE)
        return cls._fonte

    @staticmethod
    def _numero(valor):
        """Converte para float o que der; devolve None para o que não for número."""
        if isinstance(valor, bool) or valor is None:
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _retangulo(cls, camera, x, y, largura, altura):
        if x is None or y is None or not largura or not altura:
            return None
        if camera is not None:
            x = camera.transform_x(x)
            y = camera.transform_y(y)
        return pygame.Rect(int(x), int(y), max(1, int(largura)), max(1, int(altura)))

    @classmethod
    def _retangulo_quadro(cls, objeto, camera):
        """O retângulo do quadro do sprite, em coordenadas de tela."""
        return cls._retangulo(camera,
                              cls._numero(getattr(objeto, "x", None)),
                              cls._numero(getattr(objeto, "y", None)),
                              cls._numero(getattr(objeto, "width", None)),
                              cls._numero(getattr(objeto, "height", None)))

    @classmethod
    def _retangulo_caixa(cls, objeto, camera):
        """
        O retângulo que de fato colide, em coordenadas de tela.

        Um objeto sem caixa_* (um GameObject cru, um bloco improvisado pelo
        aluno) cai no quadro do sprite, que é o que a engine usaria mesmo.
        """
        x = cls._numero(getattr(objeto, "caixa_x", None))
        y = cls._numero(getattr(objeto, "caixa_y", None))
        largura = cls._numero(getattr(objeto, "caixa_largura", None))
        altura = cls._numero(getattr(objeto, "caixa_altura", None))
        if None in (x, y, largura, altura):
            return cls._retangulo_quadro(objeto, camera)
        return cls._retangulo(camera, x, y, largura, altura)

    @classmethod
    def _contornar(cls, camada, retangulo, cor, espessura):
        """Traço colorido com halo escuro atrás, para sobreviver a qualquer fundo."""
        pygame.draw.rect(camada, COR_CONTORNO, retangulo.inflate(2, 2), espessura + 2)
        pygame.draw.rect(camada, cor, retangulo, espessura)


class _Medicao(contextlib.ContextDecorator):
    """O cronômetro devolvido por Debug.medir(). Inerte com o modo desligado."""

    def __init__(self, nome):
        self.nome = str(nome)
        self._inicio = None

    def _recreate_cm(self):
        # Usado como decorador, o mesmo objeto seria reaproveitado em todas as
        # chamadas; uma função recursiva zeraria o próprio cronômetro.
        return _Medicao(self.nome)

    def __enter__(self):
        if Debug.ativo:
            self._inicio = time.perf_counter()
        return self

    def __exit__(self, *erro):
        if self._inicio is not None:
            Debug._somar_tempo(self.nome, (time.perf_counter() - self._inicio) * 1000.0)
            self._inicio = None
        return False
