"""Passo 4 — A Figura A1: a cadeia da conversa do AEI até a ocupação do painel.

É figura conceitual, e não tem dado: desenha os quatro elos que levam de uma
conversa do Anthropic Economic Index a uma métrica por ocupação do CPS, e mostra
onde essa cadeia se junta ao painel de desfechos. Dois dos elos falham em
silêncio, e o apêndice A do relatório diz quais e por quê.

Nasceu como bloco Mermaid dentro do Markdown, o que o Word não renderiza: a
figura conceitual chegava à página entregue como texto corrido. Aqui ela é
matplotlib, com a mesma paleta das figuras de resultado.

Saída: figures/fig01_cadeia_metrica.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum

# Cor por papel do nó, na paleta das figuras de resultado.
COR = {
    "motor": "#8da0cb",      # a especificação
    "tratamento": "#fc8d62",  # o que estimamos
    "desfecho": "#4f5d75",    # o que medimos
    "dado": "#66c2a5",        # fonte de dados
}
TEXTO_CLARO = {"desfecho"}
CINZA = "#3d3d3d"


def caixa(ax, x, y, w, h, texto, papel, fs=8.5, arredonda=0.02):
    """Nó do diagrama, com cor pelo papel e texto centrado. `arredonda` é o raio
    do canto em unidades de dados, que aqui são polegadas."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.008,rounding_size={arredonda}",
        linewidth=1.1, edgecolor=COR[papel],
        facecolor=COR[papel] if papel in TEXTO_CLARO else COR[papel] + "33"))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs,
            color="white" if papel in TEXTO_CLARO else CINZA,
            linespacing=1.45, zorder=3)
    return (x, y, w, h)


def liga(ax, a, b, rotulo=None, estilo="-", lado="auto", fs=7.2,
         off_a=0.0, off_b=0.0, lab=(0.0, 0.0)):
    """Seta entre dois nós. `off_a`/`off_b` deslocam o encaixe ao longo da borda,
    o que evita que várias setas convirjam no mesmo pixel."""
    ax_, ay, aw, ah = a
    bx, by, bw, bh = b
    ca, cb = (ax_ + aw / 2, ay + ah / 2), (bx + bw / 2, by + bh / 2)
    if lado == "auto":
        lado = "h" if abs(cb[0] - ca[0]) >= abs(cb[1] - ca[1]) else "v"
    if lado == "h":
        p1 = ((ax_ + aw, ca[1] + off_a) if cb[0] > ca[0] else (ax_, ca[1] + off_a))
        p2 = ((bx, cb[1] + off_b) if cb[0] > ca[0] else (bx + bw, cb[1] + off_b))
    else:
        p1 = ((ca[0] + off_a, ay + ah) if cb[1] > ca[1] else (ca[0] + off_a, ay))
        p2 = ((cb[0] + off_b, by) if cb[1] > ca[1] else (cb[0] + off_b, by + bh))
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=11, linewidth=1.1,
        linestyle=estilo, color="#9a9a9a" if estilo != "-" else "#6f6f6f",
        connectionstyle="arc3,rad=0.0", shrinkA=0, shrinkB=0, zorder=1, alpha=0.95))
    if rotulo:
        mx = (p1[0] + p2[0]) / 2 + lab[0]
        my = (p1[1] + p2[1]) / 2 + 0.022 + lab[1]
        ax.text(mx, my, rotulo, ha="center", va="bottom", fontsize=fs,
                color="#4a4a4a", style="italic", linespacing=1.3, zorder=4,
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                          edgecolor="none", alpha=0.95))


def legenda(ax, papeis, y=0.02, fs=7.6):
    handles = [Line2D([], [], marker="s", linestyle="", markersize=8,
                      markerfacecolor=COR[p] if p in TEXTO_CLARO else COR[p] + "55",
                      markeredgecolor=COR[p], label=rot)
               for p, rot in papeis]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, y),
              ncol=len(papeis), frameon=False, fontsize=fs,
              handletextpad=0.5, columnspacing=1.6)


def main():
    # O TEXTO TEM DE SER LEGÍVEL NA PÁGINA, e é a largura que decide. O relatório
    # põe a figura a 16 cm (6,3 pol), e o corpo impresso da fonte é
    # pt × 6,3 / largura em polegadas. A versão em fileira única (9,2 pol, cinco
    # caixas lado a lado) imprimia o texto das caixas a 5,9 pt e o das setas a
    # 5 pt. Cinco caixas mais quatro rótulos de seta não cabem em 6,6 pol num
    # corpo de 9–10 pt, então a construção da métrica dobra em duas fileiras (a
    # segunda corre da direita para a esquerda) e o painel de desfechos fica na
    # terceira. Quem carrega o detalhe é a Nota da figura e a Tabela A1; a
    # figura carrega a forma.
    # A tela está em POLEGADAS (0–W, 0–H), para que distância e fonte falem a
    # mesma unidade. Ao mexer aqui, regere e OLHE o PNG.
    W, H = 6.6, 3.75
    fig = plt.figure(figsize=(W, H))
    # eixos ocupando a figura inteira e sem tight_layout: é o que mantém a
    # unidade de dados igual à polegada real (o tight_layout encolheria os eixos
    # para caber a legenda, e as caixas sairiam menores que o texto delas)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    FS, FS_SETA, R = 9.5, 9, 0.08
    bw, bh = 1.58, 0.74
    c1, c2, c3 = 0.05, 2.51, 4.97         # colunas (x da borda esquerda)
    ya, yb, yc = 2.96, 1.78, 0.42          # fileiras (y da borda inferior)

    c = caixa(ax, c1, ya, bw, bh, "conversas do AEI\n(2,9 milhões)", "dado", FS, R)
    t = caixa(ax, c2, ya, bw, bh, "tarefa O*NET\n+ tipo de uso", "dado", FS, R)
    s = caixa(ax, c3, ya, bw, bh, "ocupação\nSOC", "dado", FS, R)
    o = caixa(ax, c3, yb, bw, bh, "código\nCPS", "dado", FS, R)
    d = caixa(ax, c2, yb, bw, bh, "métrica por ocupação:\nuso $u$,\nautomação $a$",
              "tratamento", FS, R)
    liga(ax, c, t, "classificação\npor modelo", fs=FS_SETA, lab=(0, 0.02))
    liga(ax, t, s, "repartição\nfracionária", fs=FS_SETA, lab=(0, 0.02))
    liga(ax, s, o, "harmonização\nde versão", fs=FS_SETA, lado="v",
         lab=(-0.62, -0.19))
    liga(ax, o, d, "agregação", fs=FS_SETA, lab=(0, 0.02))

    p = caixa(ax, c1, yc, bw, bh, "CPS / IPUMS\nocupação × mês\n2010–2026", "dado", FS, R)
    yy = caixa(ax, c2, yc, bw, bh, "desfechos:\nsalário real e taxa\nde desemprego",
               "desfecho", FS, R)
    es = caixa(ax, c3, yc, bw, bh, "event study com\ntratamento contínuo\n(seção 3.2.2)",
               "motor", FS, R)
    liga(ax, p, yy)
    liga(ax, yy, es)
    liga(ax, d, es, "entra como\ntratamento", fs=FS_SETA,
         estilo=(0, (4, 3)), lado="v", off_a=0.55, off_b=-0.55, lab=(-0.80, -0.20))

    legenda(ax, [("dado", "dado observado"), ("tratamento", "tratamento estimado"),
                 ("desfecho", "desfecho"), ("motor", "especificação")], y=-0.03, fs=9.5)
    destino = comum.FIG_DIR / "fig01_cadeia_metrica.png"
    fig.savefig(destino, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[6] figura: {destino.name}")


if __name__ == "__main__":
    main()
