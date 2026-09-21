import os

# 1. Verifica integridade da Engine Nova
COMPONENTES_VITAIS =[
    "window.py", "sprite.py", "physics.py", "gameimage.py", 
    "camera.py", "collision.py", "animation.py"
]

def verificar_integridade():
    """
    Avisa quando falta um pedaco da engine — mas so quando isso faz sentido.

    A checagem procura os arquivos .py ao lado deste. Num jogo EMPACOTADO eles
    nao existem: o PyInstaller, o Nuitka e qualquer outro congelador guardam a
    engine como bytecode dentro do proprio executavel. O resultado era que todo
    jogo entregue abria imprimindo

        ERRO DE INTEGRIDADE: Faltando ['window.py', 'sprite.py', ...]

    num jogo que estava perfeito. E a primeira linha que o professor via.

    Entao a pergunta vem antes: ha ALGUM .py aqui? Se nao ha, esta e uma
    instalacao congelada, a checagem nao se aplica e o silencio e a resposta
    certa. Se ha alguns e faltam outros, ai sim a copia esta quebrada — que e
    o caso que a checagem existe para pegar.
    """
    diretorio_atual = os.path.dirname(__file__)
    try:
        tem_fonte = any(n.endswith(".py") and n != "__init__.py"
                        for n in os.listdir(diretorio_atual))
    except OSError:
        return                      # nem listar da: nao ha o que conferir
    if not tem_fonte:
        return                      # engine congelada: nada a checar

    faltando = [a for a in COMPONENTES_VITAIS
                if not os.path.exists(os.path.join(diretorio_atual, a))]
    if faltando:
        print(f"ERRO DE INTEGRIDADE: Faltando {faltando}")

verificar_integridade()

# =========================================================
# 2. ATIVADOR DE RETROCOMPATIBILIDADE PPLAY 1.0
# Faz jogos antigos rodarem no motor novo automaticamente.
# =========================================================
try:
    from .retro_bridge import aplicar_retrocompatibilidade
    aplicar_retrocompatibilidade()
except Exception as e:
    print(f"Aviso: Ponte de retrocompatibilidade falhou: {e}")

# =========================================================
__version__ = "2.1"

__all__ = [
    # --- núcleo -------------------------------------------------------------
    "window", "gameobject", "gameimage", "animation", "sprite",
    "physics", "collision", "camera", "point",
    # --- mundo --------------------------------------------------------------
    "tilemap", "parallax", "object_group", "scenemanager", "navigation",
    # --- entrada ------------------------------------------------------------
    "keyboard", "mouse", "input_manager",
    # --- apresentação -------------------------------------------------------
    "sound", "effects", "particles", "uikit", "timer", "tween",
    # --- módulos da versão 2.1 ----------------------------------------------
    "ui",          # interface com tema, layout e foco por teclado
    "debug",       # modo de depuração visual (caixas, velocidade, painel)
    "raycaster",   # renderização pseudo-3D
    "procedural",  # geração procedural de mundos
    "studio",      # editor de código simples (requer tkinter)
    # --- ferramentas --------------------------------------------------------
    "architect",    # refatoração automática de projeto
    "tutor",        # tutor interativo no terminal
    "switcher",     # alterna entre a engine nova e a PPlay 1.0
    "retro_bridge", # ponte de retrocompatibilidade com a PPlay 1.0
]