"""
===============================================================================
POWER PPLAY 2.1 - OS EVENTOS DO JOGO
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Um lugar onde o jogo avisa que algo aconteceu, e qualquer um pode escutar.

O PROBLEMA QUE ISTO RESOLVE

O jogo gerado pelo editor sabia fazer coisas interessantes — pegar um item,
levar dano, cair do mapa, ficar sem vidas — e não tinha como contar a ninguém.
Quem quisesse reagir a uma dessas coisas tinha duas saídas ruins: editar o
arquivo da cena, que a próxima exportação reescreve, ou pedir ao editor um
interruptor novo para cada ideia ("ao vencer, vá para a cena X"). O segundo
caminho é o que estava sendo trilhado, e ele não tem fim: cada ideia nova do
aluno vira um campo novo no inspetor, e o que ele queria fazer não cabe em
lista nenhuma.

A saída é o jogo AVISAR, e o aluno decidir o que fazer com o aviso:

    from PPlay.eventos import Eventos

    def ganhou_uma_gema(cena, item=None, pontos=0, **resto):
        print("pegou!", pontos)
        cena.jogador.body.pulo += 10

    Eventos.quando("item_coletado", ganhou_uma_gema)

A cena gerada dispara; o código do aluno escuta. O arquivo da cena continua
sendo reescrito a cada exportação, e o código dele não está lá dentro.

-------------------------------------------------------------------------------
O QUE UM OUVINTE RECEBE

Sempre o primeiro argumento posicional `cena` — a instância da `Scene` que
disparou — e depois os dados daquele evento, por nome. Um ouvinte que não quer
saber de tudo termina com `**resto`, e assim continua funcionando quando o
evento passar a levar um dado a mais.

-------------------------------------------------------------------------------
UM OUVINTE QUE QUEBRA

O erro é impresso inteiro, com a pilha, e o jogo continua. A escolha é
deliberada e vale explicar: engolir o erro em silêncio faria o aluno passar uma
tarde procurando por que a função dele "não é chamada"; deixar estourar mataria
o jogo por causa de um `print` com erro de digitação. Imprimir e seguir mostra
o problema no console da IDE, onde ele já está olhando, sem tirar o jogo do ar.

Um ouvinte com erro não impede os outros ouvintes do mesmo evento de rodarem.
===============================================================================
"""

import traceback

# Os eventos que o jogo gerado pelo editor dispara. A lista está aqui, e não
# espalhada pelo gerador, para ser a resposta a "o que dá para escutar?" —
# inclusive para a IDE, que monta o menu do inspetor a partir dela.
#
# Não é uma lista fechada: `disparar` aceita qualquer nome, e um jogo escrito à
# mão pode ter os seus.
CATALOGO = {
    "cena_iniciada": "a cena terminou de se montar",
    "jogador_pulou": "o pulo saiu do chão",
    "item_coletado": "o jogador encostou num item (item, pontos)",
    "itens_acabaram": "o último item da cena foi coletado",
    "jogador_levou_dano": "um inimigo encostou no jogador (vidas)",
    "jogador_caiu": "o jogador passou do limite de queda (vidas)",
    "vidas_acabaram": "as vidas chegaram a zero",
}


class Eventos:
    """Central de avisos do jogo. Tudo aqui é de classe: existe uma só."""

    _ouvintes = {}     # nome -> [(funcao, uma_vez)]
    _disparando = 0    # profundidade, para detectar disparo dentro de ouvinte

    # ------------------------------------------------------------------
    # ESCUTAR
    # ------------------------------------------------------------------
    @classmethod
    def quando(cls, nome, funcao):
        """
        Chama `funcao` toda vez que o evento acontecer. Devolve a função.

        Devolver a função é o que permite usar isto como decorador:

            @Eventos.quando("item_coletado")   # não: precisa da função
        """
        cls._ouvintes.setdefault(nome, []).append((funcao, False))
        return funcao

    @classmethod
    def uma_vez(cls, nome, funcao):
        """Como `quando`, mas o ouvinte sai depois de atender uma vez."""
        cls._ouvintes.setdefault(nome, []).append((funcao, True))
        return funcao

    @classmethod
    def esquecer(cls, nome, funcao=None):
        """
        Tira um ouvinte, ou todos os de um evento quando `funcao` é None.

        Devolve quantos saíram.
        """
        atuais = cls._ouvintes.get(nome)
        if not atuais:
            return 0
        if funcao is None:
            del cls._ouvintes[nome]
            return len(atuais)
        restantes = [(f, u) for (f, u) in atuais if f is not funcao]
        saiu = len(atuais) - len(restantes)
        if restantes:
            cls._ouvintes[nome] = restantes
        else:
            del cls._ouvintes[nome]
        return saiu

    @classmethod
    def esquecer_todos(cls):
        """Zera a central. Trocar de jogo, ou de teste, começa daqui."""
        cls._ouvintes.clear()

    @classmethod
    def ouvintes(cls, nome=None):
        """Quem está escutando: uma lista, ou o mapa inteiro."""
        if nome is None:
            return {k: [f for f, _ in v] for k, v in cls._ouvintes.items()}
        return [f for f, _ in cls._ouvintes.get(nome, [])]

    # ------------------------------------------------------------------
    # AVISAR
    # ------------------------------------------------------------------
    @classmethod
    def disparar(cls, nome, cena=None, **dados):
        """
        Avisa quem estiver escutando. Devolve quantos ouvintes atenderam.

        É barato quando ninguém escuta — uma busca num dicionário — porque isto
        acontece dentro do laço do jogo, e o custo de avisar não pode depender
        de alguém estar interessado.
        """
        atuais = cls._ouvintes.get(nome)
        if not atuais:
            return 0

        # A cópia importa: um ouvinte pode registrar ou esquecer outro enquanto
        # o evento corre, e mexer na lista que está sendo percorrida pula
        # ouvintes sem avisar.
        sobreviventes = []
        atendidos = 0
        cls._disparando += 1
        try:
            for funcao, uma_vez in list(atuais):
                try:
                    funcao(cena, **dados)
                    atendidos += 1
                except Exception:
                    # Ver o cabeçalho deste arquivo: imprimir e seguir.
                    print("[Power PPlay] erro no ouvinte de '%s':" % nome)
                    traceback.print_exc()
                if not uma_vez:
                    sobreviventes.append((funcao, uma_vez))
        finally:
            cls._disparando -= 1

        # Só mexe na lista se algum `uma_vez` saiu; e respeita quem foi
        # registrado durante o próprio disparo.
        if len(sobreviventes) != len(atuais):
            novos = [par for par in cls._ouvintes.get(nome, [])
                     if par not in atuais]
            juntos = sobreviventes + novos
            if juntos:
                cls._ouvintes[nome] = juntos
            else:
                cls._ouvintes.pop(nome, None)
        return atendidos


def quando(nome, funcao):
    """Atalho de módulo: `from PPlay.eventos import quando`."""
    return Eventos.quando(nome, funcao)


def disparar(nome, cena=None, **dados):
    """Atalho de módulo."""
    return Eventos.disparar(nome, cena, **dados)
