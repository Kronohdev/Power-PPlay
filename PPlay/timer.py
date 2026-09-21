"""
===============================================================================
POWER PPLAY 2.1 - TAREFAS AGENDADAS
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
"Daqui a três segundos, abra o portão."

    Timer.after(3, abrir_portao)
    Timer.every(0.5, piscar_alerta)

No lugar de guardar um contador em algum canto, somar `delta_time()` nele todo
quadro e comparar — que é o que todo mundo faz, e erra.

DUAS COISAS QUE FALTAVAM

**Cancelar.** `after` e `every` agora devolvem a tarefa, e `Timer.cancelar(t)`
a tira da fila. Sem isso, uma cena que agendava algo e saía do ar deixava a
função marcada para disparar na cena seguinte — que não pediu nada e
provavelmente nem tem os objetos que a função vai tocar. `Timer.limpar()` zera
tudo, e é o que uma troca de cena quer.

**Não atrasar.** Um `every(0.1)` recomeçava a contagem do zero a cada disparo,
jogando fora o quanto tinha passado além da hora. A 60 quadros por segundo,
isso é até 16ms perdidos por disparo — mais de 10% do intervalo, e o erro se
acumula: dez segundos de jogo e o relógio já está um segundo atrás. Agora o
tempo que sobra é descontado do próximo intervalo.
===============================================================================
"""


class Task:
    """Uma tarefa na fila. Guarde-a se quiser poder cancelar."""

    def __init__(self, delay, funcao, repetir, args):
        self.delay = delay
        self.tempo_restante = delay
        self.funcao = funcao
        self.repetir = repetir
        self.args = args
        self.finalizada = False

    def cancelar(self):
        """Atalho: `tarefa.cancelar()` em vez de `Timer.cancelar(tarefa)`."""
        return Timer.cancelar(self)


class Timer:
    """
    Gerenciador de tarefas agendadas.

    Substitui a criação de variáveis de controle de tempo manuais.
    """

    _tasks = []

    @classmethod
    def after(cls, segundos, funcao, *args):
        """Executa uma função depois de X segundos. Devolve a tarefa."""
        tarefa = Task(segundos, funcao, False, args)
        cls._tasks.append(tarefa)
        return tarefa

    @classmethod
    def every(cls, segundos, funcao, *args):
        """Executa uma função a cada X segundos. Devolve a tarefa."""
        tarefa = Task(segundos, funcao, True, args)
        cls._tasks.append(tarefa)
        return tarefa

    @classmethod
    def cancelar(cls, tarefa):
        """Tira uma tarefa da fila. Devolve True se ela ainda estava lá."""
        if tarefa in cls._tasks:
            cls._tasks.remove(tarefa)
            tarefa.finalizada = True
            return True
        return False

    @classmethod
    def limpar(cls):
        """Esvazia a fila. Devolve quantas tarefas foram embora."""
        quantas = len(cls._tasks)
        for tarefa in cls._tasks:
            tarefa.finalizada = True
        cls._tasks = []
        return quantas

    @classmethod
    def pendentes(cls):
        """As tarefas ainda na fila."""
        return list(cls._tasks)

    @classmethod
    def update(cls):
        """Processa a fila. Chame uma vez por quadro, no laço principal."""
        from .window import Window

        janela = Window.get_instance()
        if not janela:
            return
        dt = janela.delta_time()

        # A cópia importa: a função de uma tarefa pode agendar ou cancelar
        # outras, e mexer na lista que está sendo percorrida pula tarefas.
        for task in list(cls._tasks):
            # Cancelada por outra tarefa desta mesma passada: não dispara.
            if task.finalizada:
                continue
            task.tempo_restante -= dt
            if task.tempo_restante > 0:
                continue
            if task.repetir:
                # O que passou além da hora é descontado do próximo intervalo,
                # em vez de ser esquecido — é isso que impede o atraso de se
                # acumular. O max() cobre o caso de um intervalo menor que um
                # quadro, que não pode empurrar o relógio para trás sem fim.
                task.tempo_restante = max(-task.delay,
                                          task.tempo_restante + task.delay)
                task.funcao(*task.args)
            else:
                task.finalizada = True
                cls.cancelar(task)
                task.funcao(*task.args)
