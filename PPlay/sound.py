import pygame

from .ambiente import no_navegador
import time
import os

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

class SoundManager:
    """
    Gerenciador estático de áudio. Controla volumes globais e canais.
    """
    _sfx_cache = {}
    _volume_sfx = 1.0  # 0.0 a 1.0
    _volume_music = 1.0

    # --- formato do áudio ---------------------------------------------------
    # O buffer é o ponto delicado. Ele é o fôlego que a placa de som tem
    # enquanto o jogo prepara o próximo pedaço: 512 amostras a 44100 Hz são
    # 11 ms, e qualquer engasgo do laço maior que isso corta o som — é o
    # chiado picotado clássico. 1024 dá 23 ms de fôlego, que um jogo em
    # Python alcança com folga, sem atraso perceptível no efeito sonoro.
    FREQUENCIA = 44100
    BUFFER = 1024
    CANAIS = 2              # 2 = estéreo
    VOZES = 16              # quantos efeitos podem soar ao mesmo tempo

    # Alguns "dispositivos de áudio" do Windows não são placas de som: são
    # programas que se fazem passar por uma (Steam Streaming, FxSound, drivers
    # de captura). Quando um desses é o dispositivo padrão, ele consome o som
    # mais devagar do que deveria, e o jogo toca picotado e arrastado. Como o
    # problema é do dispositivo, nenhum ajuste de buffer resolve: o jeito é
    # medir e trocar de saída.
    VERIFICAR_DISPOSITIVO = True
    TEMPO_TESTE = 0.20          # segundos de medição por dispositivo
    TEMPO_AQUECER = 0.10        # o começo é descartado: o SDL enche o buffer
    TOLERANCIA = 0.85           # abaixo disso, a saída é considerada ruim
    DISPOSITIVO = None          # None = a saída padrão do sistema

    # Pedaços de nome que denunciam uma saída que não é uma placa de som de
    # verdade. Uma delas pode até entregar o som na velocidade certa, mas
    # escolhê-la deixaria o jogo mudo se o programa dono dela estiver fechado
    # ou o aparelho desligado. Servem de desempate, nunca de eliminação.
    MARCAS_VIRTUAIS = ("virtual", "streaming", "fxsound", "voicemeeter",
                       "cable", "steam", "nvidia", "loopback", "obs")

    _configurado = False
    _pre_aplicado = False      # preparar() rodou antes do mixer existir
    _avisou_dispositivo = False
    _verificado = False        # a medição das saídas já foi feita
    _escolhido = None          # a saída que a medição escolheu

    @classmethod
    def configurar(cls, frequencia=None, buffer=None, vozes=None,
                   dispositivo=None, verificar=None):
        """
        Ajusta o formato do áudio. Chame ANTES de criar qualquer som.

            SoundManager.configurar(buffer=2048)      # som picotando
            SoundManager.configurar(dispositivo="Alto-falantes (Realtek(R) Audio)")
            SoundManager.configurar(verificar=False)  # não testar a saída

        Buffer maior = som mais estável, porém com mais atraso entre a ação e
        o efeito. Buffer menor = resposta imediata, com risco de picotar.
        """
        if frequencia:
            cls.FREQUENCIA = int(frequencia)
        if buffer:
            cls.BUFFER = int(buffer)
        if vozes:
            cls.VOZES = int(vozes)
        if dispositivo is not None:
            cls.DISPOSITIVO = dispositivo or None
        if verificar is not None:
            cls.VERIFICAR_DISPOSITIVO = bool(verificar)
        if dispositivo is not None or verificar is not None:
            # Quem mexeu na saída quer que a decisão seja tomada de novo, e não
            # que a escolha da vez passada continue valendo.
            cls._verificado = False
            cls._escolhido = None
        cls._configurado = False
        cls.inicializar()

    # =====================================================================
    # DIAGNÓSTICO DA SAÍDA DE ÁUDIO
    # =====================================================================
    @classmethod
    def _preferencia_do_ambiente(cls):
        """
        A saída pedida por PPLAY_AUDIO, quando existir.

        Serve para a IDE, ou para quem roda o jogo, escolher a saída sem
        mexer no código do jogo.
        """
        nome = os.environ.get("PPLAY_AUDIO", "").strip()
        return nome or None

    @classmethod
    def _ligar_audio(cls):
        """
        Liga o áudio do SDL, sem o qual não dá nem para listar as saídas.

        Devolve True quando foi este método que ligou — nesse caso cabe a quem
        chamou desligar depois. Devolve False quando já estava ligado.
        """
        if pygame.mixer.get_init():
            return False
        try:
            pygame.mixer.init(cls.FREQUENCIA, -16, cls.CANAIS, cls.BUFFER)
        except pygame.error:
            return False
        return bool(pygame.mixer.get_init())

    @classmethod
    def taxa_real(cls, dispositivo=None, segundos=None):
        """
        Quantas amostras por segundo a saída REALMENTE consome.

        Abre a saída por um instante, em silêncio, e conta o que ela pede.
        Numa saída sadia o número bate com a frequência pedida; numa saída
        defeituosa vem bem menor, e é essa diferença que faz o som arrastar.
        Devolve None quando não dá para medir.
        """
        try:
            from pygame._sdl2 import audio as sdl_audio
        except Exception:
            return None

        abriu = cls._ligar_audio()
        try:
            return cls._medir(sdl_audio, dispositivo, segundos)
        finally:
            if abriu:
                pygame.mixer.quit()

    @classmethod
    def _medir(cls, sdl_audio, dispositivo, segundos):
        """A medição em si, com o áudio do SDL já ligado."""
        contagem = {"bytes": 0}

        def callback(_saida, buffer):
            contagem["bytes"] += len(buffer)
            try:
                buffer[:] = bytes(len(buffer))     # o teste é mudo
            except Exception:
                pass

        try:
            saida = sdl_audio.AudioDevice(
                devicename=dispositivo, iscapture=False,
                frequency=cls.FREQUENCIA, audioformat=sdl_audio.AUDIO_S16,
                numchannels=cls.CANAIS, chunksize=cls.BUFFER,
                allowed_changes=0, callback=callback)
        except Exception:
            return None

        try:
            saida.pause(0)
            # Ao abrir, o SDL pede vários buffers de uma vez para encher a fila.
            # Contar esse começo daria uma taxa alta demais e faria uma saída
            # ruim passar por boa, então ele é descartado.
            time.sleep(cls.TEMPO_AQUECER)
            contagem["bytes"] = 0
            inicio = time.perf_counter()
            time.sleep(segundos or cls.TEMPO_TESTE)
            decorrido = time.perf_counter() - inicio
            saida.pause(1)
        finally:
            try:
                saida.close()
            except Exception:
                pass

        if decorrido <= 0:
            return None
        quadros = contagem["bytes"] / (2 * cls.CANAIS)      # 16 bits por amostra
        return quadros / decorrido

    @classmethod
    def dispositivos(cls):
        """
        Lista as saídas de áudio com a taxa medida de cada uma.

            for nome, taxa, ok in SoundManager.dispositivos():
                print(nome, round(taxa or 0), "ok" if ok else "PROBLEMA")

        Serve para descobrir qual saída usar quando o som sai picotado.
        """
        try:
            from pygame._sdl2 import audio as sdl_audio
        except Exception:
            return []
        abriu = cls._ligar_audio()
        try:
            nomes = list(sdl_audio.get_audio_device_names(False))
        except Exception:
            nomes = []
        saida = []
        try:
            for nome in nomes:
                taxa = cls._medir(sdl_audio, nome, None)
                ok = taxa is not None and taxa >= cls.FREQUENCIA * cls.TOLERANCIA
                saida.append((nome, taxa, ok))
        finally:
            if abriu:
                pygame.mixer.quit()
        return saida

    @classmethod
    def _saida_utilizavel(cls):
        """
        O nome de uma saída que entrega o som na velocidade certa.

        Se a saída padrão estiver boa, que é o caso comum, devolve None e nada
        muda. Se estiver ruim, procura outra e avisa qual escolheu.
        """
        abriu = cls._ligar_audio()
        try:
            return cls._procurar_saida()
        finally:
            if abriu:
                pygame.mixer.quit()

    @classmethod
    def _virtual(cls, nome):
        """1 para saídas que parecem virtuais, 0 para as demais."""
        baixo = (nome or "").lower()
        return 1 if any(marca in baixo for marca in cls.MARCAS_VIRTUAIS) else 0

    @classmethod
    def _procurar_saida(cls):
        # No navegador não há placa de som para escolher: existe uma saída, a
        # do navegador, e medir a velocidade dela não levaria a lugar nenhum.
        if no_navegador():
            return None
        padrao = cls.taxa_real(None)
        if padrao is None or padrao >= cls.FREQUENCIA * cls.TOLERANCIA:
            return None

        porcento = padrao / cls.FREQUENCIA * 100
        # Entre as saídas sadias, fica a que entrega mais perto da velocidade
        # pedida — nem devagar demais, nem depressa demais.
        boas = [(cls._virtual(nome), abs(taxa - cls.FREQUENCIA), nome)
                for nome, taxa, ok in cls.dispositivos() if ok]
        if boas:
            boas.sort()
            nome = boas[0][2]
            if not cls._avisou_dispositivo:
                cls._avisou_dispositivo = True
                print("AVISO: a saida de audio padrao entrega som a "
                      f"{porcento:.0f}% da velocidade, o que deixa o jogo picotado.")
                print(f"       Usando '{nome}' no lugar. Para escolher outra: "
                      "SoundManager.configurar(dispositivo=...)")
            return nome

        if not cls._avisou_dispositivo:
            cls._avisou_dispositivo = True
            print("AVISO: nenhuma saida de audio deste computador entrega som na "
                  "velocidade certa; o jogo vai soar picotado.")
            print("       Veja SoundManager.dispositivos().")
        return None

    @classmethod
    def preparar(cls):
        """
        Anuncia o formato desejado ao pygame. Só vale ANTES de pygame.init().
        A Window chama isto antes de ligar o pygame, para o mixer já nascer
        com o buffer certo.
        """
        if no_navegador():
            # No navegador quem decide o formato do áudio é o navegador, e
            # tocar no pygame antes do init() ali é tocar num esboço vazio.
            return
        try:
            pygame.mixer.pre_init(cls.FREQUENCIA, -16, cls.CANAIS, cls.BUFFER)
            cls._pre_aplicado = pygame.mixer.get_init() is None
        except Exception:  # noqa: BLE001
            # pygame.error no computador; noutro lugar, o que aparecer.
            pass

    @classmethod
    def inicializar(cls):
        """
        Garante que o mixer está aberto com o formato da engine.

        Se alguém (o próprio pygame.init(), por exemplo) já abriu o mixer com
        outro formato, ele é fechado e reaberto. Isto acontece na primeira vez
        que o jogo pede som, antes de qualquer arquivo ser carregado, então
        nada se perde.
        """
        if cls._configurado and pygame.mixer.get_init():
            return

        dispositivo = (cls.DISPOSITIVO or cls._preferencia_do_ambiente()
                       or cls._escolhido)
        if dispositivo is None and cls.VERIFICAR_DISPOSITIVO and not cls._verificado:
            cls._verificado = True
            if pygame.mixer.get_init():
                pygame.mixer.quit()          # a medição precisa da saída livre
            dispositivo = cls._escolhido = cls._saida_utilizavel()

        if dispositivo is None and pygame.mixer.get_init() and cls._pre_aplicado:
            # O mixer já nasceu com o nosso formato (a Window avisou a tempo)
            # e a saída padrão está boa: reabrir seria desperdício.
            pygame.mixer.set_num_channels(cls.VOZES)
            cls._configurado = True
            return

        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            pygame.mixer.pre_init(cls.FREQUENCIA, -16, cls.CANAIS, cls.BUFFER)
            if dispositivo:
                pygame.mixer.init(cls.FREQUENCIA, -16, cls.CANAIS, cls.BUFFER,
                                  devicename=dispositivo)
            else:
                pygame.mixer.init(cls.FREQUENCIA, -16, cls.CANAIS, cls.BUFFER)
            pygame.mixer.set_num_channels(cls.VOZES)
            cls._configurado = True
        except pygame.error as erro:
            print(f"AVISO: não foi possível preparar o áudio ({erro})")

    @classmethod
    def set_sfx_volume(cls, volume):
        """Define o volume de todos os efeitos sonoros (0 a 100)."""
        cls._volume_sfx = volume / 100.0
        for sfx in cls._sfx_cache.values():
            sfx.set_volume(cls._volume_sfx)

    @classmethod
    def set_music_volume(cls, volume):
        """Define o volume da música de fundo (0 a 100)."""
        cls._volume_music = volume / 100.0
        pygame.mixer.music.set_volume(cls._volume_music)

class Sound:
    """
    Classe para Efeitos Sonoros (SFX) curtos.
    Carregados na RAM para execução instantânea.
    """
    def __init__(self, caminho_arquivo):
        SoundManager.inicializar()
        
        # Sistema de Cache de Áudio
        if caminho_arquivo in SoundManager._sfx_cache:
            self.sound = SoundManager._sfx_cache[caminho_arquivo]
        else:
            if os.path.exists(caminho_arquivo):
                self.sound = pygame.mixer.Sound(caminho_arquivo)
                SoundManager._sfx_cache[caminho_arquivo] = self.sound
            else:
                print(f"ERRO: Arquivo de som não encontrado: {caminho_arquivo}")
                self.sound = None

        if self.sound:
            self.sound.set_volume(SoundManager._volume_sfx)

    def play(self, repeticoes=0):
        """Toca o som. repeticoes=-1 para loop infinito."""
        if self.sound:
            self.sound.play(loops=repeticoes)

    def stop(self):
        if self.sound:
            self.sound.stop()

    def set_volume(self, volume_percentual):
        """Define o volume deste som específico (0 a 100)."""
        if self.sound:
            self.sound.set_volume(volume_percentual / 100.0)

class Music:
    """
    Classe para Música de Fundo (BGM).
    Lida via streaming para economizar memória.
    """
    def __init__(self, caminho_arquivo):
        SoundManager.inicializar()
        self.caminho = caminho_arquivo

    def play(self, loops=-1, fade_in_ms=2000):
        """Toca a música com efeito de fade-in opcional."""
        if os.path.exists(self.caminho):
            pygame.mixer.music.load(self.caminho)
            pygame.mixer.music.set_volume(SoundManager._volume_music)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_in_ms)
        else:
            print(f"ERRO: Arquivo de música não encontrado: {self.caminho}")

    def stop(self, fade_out_ms=1000):
        pygame.mixer.music.fadeout(fade_out_ms)

    def pause(self):
        pygame.mixer.music.pause()

    def unpause(self):
        pygame.mixer.music.unpause()

    def is_playing(self):
        return pygame.mixer.music.get_busy()