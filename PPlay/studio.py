"""
===============================================================================
POWER PPLAY 2.1 - STUDIO (IDE INTEGRADA)
===============================================================================
Desenvolvedor Líder e Arquiteto das Versões 2.0 e 2.1:
    Kauã Neves Jesus de Paula
Contato: kneves@id.uff.br

Ano de Lançamento: 2026
Instituição: Universidade Federal Fluminense (IC-UFF) - Niterói, RJ
-------------------------------------------------------------------------------
Ambiente de desenvolvimento mínimo para quem não quer configurar um editor:
árvore do projeto, editor com destaque de sintaxe, console de saída e um botão
que roda o jogo. Feito só com tkinter, que já vem com o Python.

Uso:
    python PPlay/studio.py                 (abre na pasta atual)
    python PPlay/studio.py meu_projeto/    (abre uma pasta específica)

Atalhos:
    F5           rodar          Ctrl+S   salvar
    Shift+F5     parar          Ctrl+N   novo arquivo
    Ctrl+L       limpar console Ctrl+F   procurar
===============================================================================
"""

import os
import re
import sys
import subprocess
import threading
import queue

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog
except ImportError:  # pragma: no cover
    print("ERRO: tkinter nao esta disponivel nesta instalacao do Python.")
    print("No Linux: sudo apt install python3-tk")
    sys.exit(1)


# =============================================================================
# TEMA
# =============================================================================
TEMA = {
    "fundo":      "#12151C",
    "painel":     "#181C25",
    "editor":     "#0E1118",
    "borda":      "#2A3140",
    "texto":      "#E4E9F2",
    "fraco":      "#7B879B",
    "destaque":   "#FF3EC8",
    "selecao":    "#33304A",
    "linha_num":  "#5A6478",
    "kw":         "#FF6BD6",
    "str":        "#7FD8AC",
    "com":        "#6C7A90",
    "num":        "#C4A9FF",
    "def":        "#8DBEFF",
    "pplay":      "#FFB74D",
    "erro":       "#FF6B6B",
    "ok":         "#7FD8AC",
}

PALAVRAS = r"\b(False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|self)\b"
CLASSES_PPLAY = r"\b(Window|Sprite|GameImage|GameObject|Animation|Physics|KinematicBody|Camera|TileMap|ObjectGroup|Scene|SceneManager|Collision|Timer|Tween|Sound|Music|SoundManager|ScreenEffects|LightingSystem|ParticleEmitter|InputManager|Navigation|ParallaxSystem|Button|ProgressBar|UIManager|UITheme|Panel|Label|Slider|Checkbox|TextInput|World3D|Camera3D|Raycaster3D|Billboard)\b"

MODELOS = {
    "Jogo mínimo": '''from PPlay.window import Window

janela = Window(800, 600, "Meu Jogo")

while True:
    janela.set_background_color("darkblue")
    janela.update()
''',
    "Personagem com física": '''from PPlay.window import Window
from PPlay.sprite import Sprite
from PPlay.physics import Physics
from PPlay.camera import Camera
from PPlay.tilemap import TileMap

janela = Window(640, 360, "Plataforma", pixel_art=True)
camera = Camera(640, 360)
fisica = Physics(gravidade=2500)

mapa = TileMap(tamanho_tile=32)
mapa.carregar_mapa("assets/fase1.txt", {
    '#': "assets/parede.png",
    'solido': ['#']
})

player = Sprite("assets/hero.png", 4)
player.set_total_duration(400)
player.set_position(64, 64)
player.setup_physics(fisica)

while True:
    janela.set_background_color((18, 22, 31))
    player.update_physics(mapa.get_solidos())
    camera.follow(player, 0.1)
    mapa.draw()
    player.draw()
    janela.update()
''',
    "Menu com cenas": '''from PPlay.window import Window
from PPlay.scenemanager import Scene, SceneManager
from PPlay.ui import UIManager, Panel, Label, Button

janela = Window(800, 600, "Menu")

class Menu(Scene):
    def __init__(self):
        super().__init__()
        self.ui = UIManager()
        painel = Panel(direcao="vertical", titulo="MEU JOGO")
        painel.add(
            Label("Escolha uma opcao", cor=(140, 152, 172)),
            Button("Jogar", on_click=self.jogar),
            Button("Sair", on_click=self.janela.close),
        )
        painel.centralizar()
        self.ui.add(painel)

    def jogar(self):
        print("comecando...")

    def loop(self):
        self.ui.update()

    def draw(self):
        self.janela.set_background_color((14, 16, 22))
        self.ui.draw()

SceneManager.change_scene(Menu())

while True:
    SceneManager.run()
    janela.update()
''',
    "Mundo procedural": '''from PPlay.window import Window
from PPlay.camera import Camera
from PPlay.tilemap import TileMap
from PPlay import procedural

janela = Window(640, 360, "Caverna gerada")
camera = Camera(640, 360)

mapa_gerado = procedural.caverna(largura=80, altura=45, seed=42)
procedural.contornar(mapa_gerado, 'X')
mapa_gerado.salvar("assets/caverna.txt")

mapa = TileMap(tamanho_tile=16)
mapa.carregar_mapa("assets/caverna.txt", {
    '#': "assets/pedra.png",
    'X': "assets/borda.png",
    'solido': ['#', 'X']
})

while True:
    janela.set_background_color((10, 12, 18))
    mapa.draw()
    janela.update()
''',
    "Mundo 3D (raycasting)": '''from PPlay.window import Window
from PPlay.raycaster import World3D, Camera3D, Raycaster3D

janela = Window(426, 240, "3D", pixel_art=True)

MAPA = [
    "1111111111",
    "1000000001",
    "1011100101",
    "100A100001",
    "1010001101",
    "1000000001",
    "1111111111",
]

mundo = World3D.de_texto(MAPA, {'inicio': 'A'})
mundo.set_textura_cor(1, (88, 94, 104), cor_borda=(50, 55, 64))

camera = Camera3D(*mundo.spawn)
render = Raycaster3D(mundo, camera)

while True:
    camera.controlar_com_teclado(mundo)
    render.draw()
    render.draw_minimapa()
    render.draw_mira()
    janela.update()
''',
}


# =============================================================================
# EDITOR COM NUMERAÇÃO E DESTAQUE
# =============================================================================
class Editor(tk.Frame):
    def __init__(self, mestre, ao_modificar=None):
        super().__init__(mestre, bg=TEMA["editor"])
        self.ao_modificar = ao_modificar

        self.numeros = tk.Text(self, width=5, padx=8, pady=8, takefocus=0,
                               border=0, bg=TEMA["painel"], fg=TEMA["linha_num"],
                               font=("Consolas", 11), state="disabled", cursor="arrow")
        self.numeros.pack(side="left", fill="y")

        self.texto = tk.Text(self, wrap="none", undo=True, padx=10, pady=8,
                             border=0, bg=TEMA["editor"], fg=TEMA["texto"],
                             insertbackground=TEMA["destaque"],
                             selectbackground=TEMA["selecao"],
                             font=("Consolas", 11), tabs="4c")
        self.texto.pack(side="left", fill="both", expand=True)

        barra = ttk.Scrollbar(self, command=self._rolar)
        barra.pack(side="right", fill="y")
        self.texto.config(yscrollcommand=lambda *a: (barra.set(*a), self._sincronizar()))

        for nome, cor in (("kw", TEMA["kw"]), ("str", TEMA["str"]), ("com", TEMA["com"]),
                          ("num", TEMA["num"]), ("def", TEMA["def"]), ("pplay", TEMA["pplay"])):
            self.texto.tag_configure(nome, foreground=cor)
        self.texto.tag_configure("com", foreground=TEMA["com"], font=("Consolas", 11, "italic"))
        self.texto.tag_configure("busca", background=TEMA["destaque"], foreground="#0E1118")

        self.texto.bind("<KeyRelease>", self._mudou)
        self.texto.bind("<ButtonRelease>", lambda e: self._sincronizar())
        self.texto.bind("<MouseWheel>", lambda e: self.after(1, self._sincronizar))
        self.texto.bind("<Return>", self._auto_indentar)
        self.texto.bind("<Tab>", self._tab)

    # -- rolagem sincronizada ----------------------------------------------
    def _rolar(self, *args):
        self.texto.yview(*args)
        self.numeros.yview(*args)

    def _sincronizar(self):
        self.numeros.yview_moveto(self.texto.yview()[0])

    # -- edição -------------------------------------------------------------
    def _tab(self, evento):
        self.texto.insert("insert", "    ")
        return "break"

    def _auto_indentar(self, evento):
        linha = self.texto.get("insert linestart", "insert")
        recuo = len(linha) - len(linha.lstrip())
        extra = 4 if linha.rstrip().endswith(":") else 0
        self.texto.insert("insert", "\n" + " " * (recuo + extra))
        return "break"

    def _mudou(self, evento=None):
        self.realcar()
        self.numerar()
        if self.ao_modificar:
            self.ao_modificar()

    def numerar(self):
        total = int(self.texto.index("end-1c").split(".")[0])
        self.numeros.config(state="normal")
        self.numeros.delete("1.0", "end")
        self.numeros.insert("1.0", "\n".join(str(i) for i in range(1, total + 1)))
        self.numeros.config(state="disabled")
        self._sincronizar()

    def realcar(self):
        conteudo = self.texto.get("1.0", "end-1c")
        for tag in ("kw", "str", "com", "num", "def", "pplay"):
            self.texto.tag_remove(tag, "1.0", "end")

        def aplicar(padrao, tag):
            for m in re.finditer(padrao, conteudo):
                ini = f"1.0+{m.start()}c"
                fim = f"1.0+{m.end()}c"
                self.texto.tag_add(tag, ini, fim)

        aplicar(r"\b\d+\.?\d*\b", "num")
        aplicar(PALAVRAS, "kw")
        aplicar(CLASSES_PPLAY, "pplay")
        aplicar(r"\b(?:def|class)\s+(\w+)", "def")
        aplicar(r"(\"\"\".*?\"\"\"|'''.*?'''|\"[^\"\n]*\"|'[^'\n]*')", "str")
        aplicar(r"#[^\n]*", "com")

    def get(self):
        return self.texto.get("1.0", "end-1c")

    def set(self, conteudo):
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", conteudo)
        self.texto.edit_reset()
        self._mudou()

    def ir_para(self, linha):
        self.texto.mark_set("insert", f"{linha}.0")
        self.texto.see(f"{linha}.0")
        self.texto.focus_set()


# =============================================================================
# APLICAÇÃO
# =============================================================================
class Studio(tk.Tk):
    def __init__(self, raiz="."):
        super().__init__()
        self.raiz = os.path.abspath(raiz)
        self.arquivo = None
        self.sujo = False
        self.processo = None
        self.fila = queue.Queue()

        self.title("Power PPlay Studio")
        self.geometry("1180x740")
        self.configure(bg=TEMA["fundo"])
        self.minsize(880, 560)

        self._estilo()
        self._barra()
        self._corpo()
        self._rodape()
        self._atalhos()

        self.recarregar_arvore()
        self.after(60, self._drenar_saida)
        self.protocol("WM_DELETE_WINDOW", self.sair)

    # -- interface ----------------------------------------------------------
    def _estilo(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TFrame", background=TEMA["painel"])
        s.configure("Treeview", background=TEMA["painel"], fieldbackground=TEMA["painel"],
                    foreground=TEMA["texto"], borderwidth=0, rowheight=22)
        s.configure("Treeview.Heading", background=TEMA["fundo"], foreground=TEMA["fraco"],
                    borderwidth=0)
        s.map("Treeview", background=[("selected", TEMA["selecao"])])
        s.configure("TPanedwindow", background=TEMA["fundo"])

    def _botao(self, pai, texto, comando, destaque=False):
        b = tk.Button(pai, text=texto, command=comando, relief="flat", bd=0,
                      padx=13, pady=5, font=("Segoe UI", 9, "bold"),
                      bg=TEMA["destaque"] if destaque else TEMA["borda"],
                      fg="#0E1118" if destaque else TEMA["texto"],
                      activebackground=TEMA["destaque"], activeforeground="#0E1118",
                      cursor="hand2")
        b.pack(side="left", padx=(0, 6))
        return b

    def _barra(self):
        topo = tk.Frame(self, bg=TEMA["fundo"], height=44)
        topo.pack(fill="x", padx=10, pady=(9, 5))

        tk.Label(topo, text="POWER PPLAY  STUDIO", bg=TEMA["fundo"], fg=TEMA["destaque"],
                 font=("Consolas", 11, "bold")).pack(side="left", padx=(2, 18))

        self.btn_rodar = self._botao(topo, "▶  Rodar  (F5)", self.rodar, destaque=True)
        self.btn_parar = self._botao(topo, "■  Parar", self.parar)
        self.btn_parar.config(state="disabled")
        self._botao(topo, "Salvar", self.salvar)
        self._botao(topo, "Novo", self.novo)

        modelo = tk.Menubutton(topo, text="Modelos ▾", relief="flat", bd=0,
                               padx=13, pady=5, font=("Segoe UI", 9, "bold"),
                               bg=TEMA["borda"], fg=TEMA["texto"],
                               activebackground=TEMA["destaque"], cursor="hand2")
        menu = tk.Menu(modelo, tearoff=0, bg=TEMA["painel"], fg=TEMA["texto"],
                       activebackground=TEMA["destaque"], activeforeground="#0E1118",
                       bd=0)
        for nome in MODELOS:
            menu.add_command(label=nome, command=lambda n=nome: self.inserir_modelo(n))
        modelo.config(menu=menu)
        modelo.pack(side="left", padx=(0, 6))

        self._botao(topo, "Tutor", self.abrir_tutor)
        self._botao(topo, "Pasta...", self.escolher_pasta)

    def _corpo(self):
        painel = ttk.Panedwindow(self, orient="horizontal")
        painel.pack(fill="both", expand=True, padx=10, pady=4)

        # esquerda: arvore
        esq = tk.Frame(painel, bg=TEMA["painel"])
        tk.Label(esq, text="PROJETO", bg=TEMA["painel"], fg=TEMA["fraco"],
                 font=("Consolas", 8, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 4))
        self.arvore = ttk.Treeview(esq, show="tree", selectmode="browse")
        self.arvore.pack(fill="both", expand=True, padx=(4, 0))
        self.arvore.bind("<<TreeviewSelect>>", self.selecionar_arquivo)
        painel.add(esq, weight=1)

        # direita: editor + console
        dir_ = ttk.Panedwindow(painel, orient="vertical")

        caixa_editor = tk.Frame(dir_, bg=TEMA["editor"])
        self.rotulo_arquivo = tk.Label(caixa_editor, text="nenhum arquivo aberto",
                                       bg=TEMA["painel"], fg=TEMA["fraco"], anchor="w",
                                       font=("Consolas", 9), padx=10, pady=4)
        self.rotulo_arquivo.pack(fill="x")
        self.editor = Editor(caixa_editor, ao_modificar=self.marcar_sujo)
        self.editor.pack(fill="both", expand=True)
        dir_.add(caixa_editor, weight=3)

        caixa_console = tk.Frame(dir_, bg=TEMA["painel"])
        cab = tk.Frame(caixa_console, bg=TEMA["painel"])
        cab.pack(fill="x")
        tk.Label(cab, text="CONSOLE", bg=TEMA["painel"], fg=TEMA["fraco"],
                 font=("Consolas", 8, "bold"), padx=10, pady=4).pack(side="left")
        tk.Button(cab, text="limpar", command=self.limpar_console, relief="flat", bd=0,
                  bg=TEMA["painel"], fg=TEMA["fraco"], activebackground=TEMA["painel"],
                  activeforeground=TEMA["destaque"], font=("Consolas", 8),
                  cursor="hand2").pack(side="right", padx=8)

        self.console = tk.Text(caixa_console, height=9, bg=TEMA["editor"], fg=TEMA["fraco"],
                               border=0, padx=10, pady=6, font=("Consolas", 10),
                               state="disabled", wrap="word")
        self.console.pack(fill="both", expand=True)
        self.console.tag_configure("erro", foreground=TEMA["erro"])
        self.console.tag_configure("ok", foreground=TEMA["ok"])
        self.console.tag_configure("info", foreground=TEMA["destaque"])
        dir_.add(caixa_console, weight=1)

        painel.add(dir_, weight=4)

    def _rodape(self):
        self.status = tk.Label(self, text="pronto", bg=TEMA["fundo"], fg=TEMA["fraco"],
                               anchor="w", font=("Consolas", 9), padx=12, pady=5)
        self.status.pack(fill="x")

    def _atalhos(self):
        self.bind("<F5>", lambda e: self.rodar())
        self.bind("<Shift-F5>", lambda e: self.parar())
        self.bind("<Control-s>", lambda e: self.salvar())
        self.bind("<Control-n>", lambda e: self.novo())
        self.bind("<Control-l>", lambda e: self.limpar_console())
        self.bind("<Control-f>", lambda e: self.procurar())

    # -- projeto ------------------------------------------------------------
    def recarregar_arvore(self):
        self.arvore.delete(*self.arvore.get_children())
        self._popular("", self.raiz)
        self.title(f"Power PPlay Studio  -  {os.path.basename(self.raiz)}")

    def _popular(self, pai, caminho, nivel=0):
        if nivel > 3:
            return
        try:
            itens = sorted(os.listdir(caminho),
                           key=lambda n: (not os.path.isdir(os.path.join(caminho, n)), n.lower()))
        except OSError:
            return
        for nome in itens:
            if nome.startswith('.') or nome in ("__pycache__", "venv", ".venv", "node_modules"):
                continue
            completo = os.path.join(caminho, nome)
            if os.path.isdir(completo):
                no = self.arvore.insert(pai, "end", text="  " + nome, open=(nivel == 0),
                                        values=(completo,))
                self._popular(no, completo, nivel + 1)
            elif nome.endswith((".py", ".txt", ".md", ".json")):
                self.arvore.insert(pai, "end", text="  " + nome, values=(completo,))

    def selecionar_arquivo(self, evento=None):
        sel = self.arvore.selection()
        if not sel:
            return
        valores = self.arvore.item(sel[0], "values")
        if valores and os.path.isfile(valores[0]):
            self.abrir(valores[0])

    def escolher_pasta(self):
        pasta = filedialog.askdirectory(initialdir=self.raiz, title="Abrir pasta do projeto")
        if pasta:
            self.raiz = pasta
            self.recarregar_arvore()
            self.log(f"projeto: {pasta}", "info")

    # -- arquivo ------------------------------------------------------------
    def abrir(self, caminho):
        if self.sujo and not self._confirmar_descarte():
            return
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                self.editor.set(f.read())
        except (OSError, UnicodeDecodeError) as erro:
            self.log(f"nao foi possivel abrir: {erro}", "erro")
            return
        self.arquivo = caminho
        self.sujo = False
        self.rotulo_arquivo.config(text=os.path.relpath(caminho, self.raiz))
        self.status.config(text=f"aberto: {os.path.basename(caminho)}")

    def salvar(self):
        if not self.arquivo:
            caminho = filedialog.asksaveasfilename(initialdir=self.raiz,
                                                   defaultextension=".py",
                                                   filetypes=[("Python", "*.py"),
                                                              ("Texto", "*.txt")])
            if not caminho:
                return
            self.arquivo = caminho
        try:
            with open(self.arquivo, "w", encoding="utf-8") as f:
                f.write(self.editor.get())
        except OSError as erro:
            self.log(f"nao foi possivel salvar: {erro}", "erro")
            return
        self.sujo = False
        self.rotulo_arquivo.config(text=os.path.relpath(self.arquivo, self.raiz))
        self.status.config(text=f"salvo: {os.path.basename(self.arquivo)}")
        self.recarregar_arvore()

    def novo(self):
        if self.sujo and not self._confirmar_descarte():
            return
        self.arquivo = None
        self.sujo = False
        self.editor.set(MODELOS["Jogo mínimo"])
        self.rotulo_arquivo.config(text="novo arquivo (nao salvo)")

    def inserir_modelo(self, nome):
        self.editor.texto.insert("insert", MODELOS[nome])
        self.editor._mudou()
        self.status.config(text=f"modelo inserido: {nome}")

    def marcar_sujo(self):
        if not self.sujo:
            self.sujo = True
            atual = self.rotulo_arquivo.cget("text").lstrip("* ")
            self.rotulo_arquivo.config(text="* " + atual)

    def _confirmar_descarte(self):
        return messagebox.askyesno("Alterações não salvas",
                                   "Você tem alterações não salvas. Descartar?")

    def procurar(self):
        alvo = simpledialog.askstring("Procurar", "Texto:", parent=self)
        if not alvo:
            return
        self.editor.texto.tag_remove("busca", "1.0", "end")
        inicio = "1.0"
        achou = 0
        while True:
            pos = self.editor.texto.search(alvo, inicio, stopindex="end")
            if not pos:
                break
            fim = f"{pos}+{len(alvo)}c"
            self.editor.texto.tag_add("busca", pos, fim)
            inicio = fim
            achou += 1
        self.status.config(text=f"{achou} ocorrencia(s) de '{alvo}'")

    # -- execução -----------------------------------------------------------
    def rodar(self):
        if self.processo and self.processo.poll() is None:
            self.log("ja existe um jogo rodando. pare antes (Shift+F5).", "erro")
            return
        if self.sujo or not self.arquivo:
            self.salvar()
        if not self.arquivo:
            return

        self.limpar_console()
        self.log(f"executando {os.path.basename(self.arquivo)} ...", "info")
        self.btn_rodar.config(state="disabled")
        self.btn_parar.config(state="normal")

        pasta = os.path.dirname(os.path.abspath(self.arquivo)) or self.raiz
        ambiente = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        try:
            self.processo = subprocess.Popen(
                [sys.executable, os.path.abspath(self.arquivo)],
                cwd=pasta, env=ambiente,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as erro:
            self.log(f"falha ao iniciar: {erro}", "erro")
            self._encerrou()
            return

        threading.Thread(target=self._ler_saida, daemon=True).start()

    def _ler_saida(self):
        try:
            for linha in self.processo.stdout:
                self.fila.put(linha.rstrip("\n"))
        except (ValueError, OSError):
            pass
        codigo = self.processo.wait()
        self.fila.put(("__FIM__", codigo))

    def _drenar_saida(self):
        try:
            while True:
                item = self.fila.get_nowait()
                if isinstance(item, tuple) and item[0] == "__FIM__":
                    codigo = item[1]
                    if codigo == 0:
                        self.log("jogo encerrado normalmente.", "ok")
                    else:
                        self.log(f"jogo encerrado com codigo {codigo}.", "erro")
                    self._encerrou()
                else:
                    tag = "erro" if ("Error" in item or "Traceback" in item
                                     or "ERRO" in item) else None
                    self.log(item, tag)
        except queue.Empty:
            pass
        self.after(60, self._drenar_saida)

    def _encerrou(self):
        self.btn_rodar.config(state="normal")
        self.btn_parar.config(state="disabled")
        self.processo = None

    def parar(self):
        if self.processo and self.processo.poll() is None:
            self.processo.terminate()
            self.log("interrompido pelo usuario.", "info")
        self._encerrou()

    def abrir_tutor(self):
        tutor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutor.py")
        if not os.path.exists(tutor):
            self.log("tutor.py nao encontrado ao lado do studio.py", "erro")
            return
        try:
            if os.name == "nt":
                subprocess.Popen([sys.executable, tutor],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([sys.executable, tutor])
            self.log("tutor aberto em outra janela.", "info")
        except OSError as erro:
            self.log(f"nao foi possivel abrir o tutor: {erro}", "erro")

    # -- console ------------------------------------------------------------
    def log(self, mensagem, tag=None):
        self.console.config(state="normal")
        self.console.insert("end", mensagem + "\n", tag or "")
        self.console.see("end")
        self.console.config(state="disabled")

    def limpar_console(self):
        self.console.config(state="normal")
        self.console.delete("1.0", "end")
        self.console.config(state="disabled")

    def sair(self):
        if self.processo and self.processo.poll() is None:
            self.processo.terminate()
        if self.sujo and not self._confirmar_descarte():
            return
        self.destroy()


def abrir(raiz="."):
    """Abre o Studio programaticamente: from PPlay.studio import abrir; abrir()"""
    Studio(raiz).mainloop()


if __name__ == "__main__":
    pasta_inicial = sys.argv[1] if len(sys.argv) > 1 else "."
    abrir(pasta_inicial)
