import heapq
import math

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

class Navigation:
    @staticmethod
    def heuristica(a, b, diagonais=False):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if diagonais:
            # Octile: admissível quando a diagonal custa 1.4142
            return (dx + dy) + (1.4142 - 2) * min(dx, dy)
        return dx + dy  # Manhattan

    @classmethod
    def bloqueados(cls, mapa):
        """
        Devolve o conjunto de células (coluna, linha) que realmente bloqueiam
        o movimento — apenas as declaradas em 'solido' no mapeamento.

        Antes, a busca considerava intransponível QUALQUER célula com tile: quem
        mapeasse o chão para uma imagem transformava o mapa inteiro em parede e
        nunca achava caminho.
        """
        tile = mapa.tamanho_tile
        return {(int(s.x // tile), int(s.y // tile)) for s in mapa.get_solidos()}

    @classmethod
    def encontrar_caminho(cls, mapa, inicio_px, fim_px, diagonais=False):
        tile = mapa.tamanho_tile
        # Converte pixels para índices da grade
        start = (int(inicio_px[0] // tile), int(inicio_px[1] // tile))
        goal = (int(fim_px[0] // tile), int(fim_px[1] // tile))

        if not mapa.mapa_tiles:
            return []

        largura = len(mapa.mapa_tiles[0])
        altura = len(mapa.mapa_tiles)
        paredes = cls.bloqueados(mapa)

        vizinhanca = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if diagonais:
            vizinhanca += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        # A* Core
        queue = [(0, start)]
        caminhos = {start: None}
        custos = {start: 0}

        while queue:
            atual = heapq.heappop(queue)[1]
            if atual == goal: break

            for dx, dy in vizinhanca:
                vizinho = (atual[0] + dx, atual[1] + dy)
                if 0 <= vizinho[0] < largura and 0 <= vizinho[1] < altura:
                    # Só bloqueia quem é sólido de verdade
                    if vizinho in paredes: continue

                    # Impede "cortar quina" entre dois blocos na diagonal
                    if dx and dy:
                        if (atual[0] + dx, atual[1]) in paredes: continue
                        if (atual[0], atual[1] + dy) in paredes: continue

                    novo_custo = custos[atual] + (1.4142 if dx and dy else 1)
                    if vizinho not in custos or novo_custo < custos[vizinho]:
                        custos[vizinho] = novo_custo
                        prioridade = novo_custo + cls.heuristica(vizinho, goal, diagonais)
                        heapq.heappush(queue, (prioridade, vizinho))
                        caminhos[vizinho] = atual
        
        if goal not in caminhos: return []
        
        # Reconstrói caminho convertendo de volta para pixels (CENTRO DO TILE)
        percurso = []
        passo = goal
        offset = tile / 2 # Alvo é o centro do quadrado
        while passo is not None:
            percurso.append((passo[0] * tile + offset, passo[1] * tile + offset))
            passo = caminhos[passo]
        return percurso[::-1]