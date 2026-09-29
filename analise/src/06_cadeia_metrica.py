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


def caixa(ax, x, y, w, h, texto, papel, fs=8.5):
    """Nó do diagrama, com cor pelo papel e texto centrado."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.02",
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


def legenda(ax, papeis, y=0.02):
    handles = [Line2D([], [], marker="s", linestyle="", markersize=8,
                      markerfacecolor=COR[p] if p in TEXTO_CLARO else COR[p] + "55",
                      markeredgecolor=COR[p], label=rot)
               for p, rot in papeis]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, y),
              ncol=len(papeis), frameon=False, fontsize=7.6,
              handletextpad=0.5, columnspacing=1.6)


def main():
    # A GEOMETRIA É PARA PÁGINA EM RETRATO, e é ela que decide a legibilidade. O
    # tamanho do texto NA PÁGINA é proporcional ao corpo da fonte dividido pela
    # largura em polegadas, então estreitar a figura aumenta a fonte impressa: em
    # 13x4 o docx a escalava para a largura útil e o texto das caixas ficava
    # microscópico, ainda que impecável no .png solto. Rótulo curto é requisito
    # pela mesma razão, porque as cinco caixas dividem cerca de 16 cm de página.
    # Quem carrega o detalhe é a Nota da figura e a Tabela A1; a figura carrega a
    # forma. Ao mexer aqui, regere e olhe o PDF.
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    y1, h = 0.58, 0.28
    c = caixa(ax, 0.015, y1, 0.17, h, "conversas do AEI\n(2,9 milhões)", "dado")
    t = caixa(ax, 0.250, y1, 0.16, h, "tarefa O*NET\n+ tipo de uso", "dado")
    s = caixa(ax, 0.480, y1, 0.14, h, "ocupação\nSOC", "dado")
    o = caixa(ax, 0.665, y1, 0.13, h, "código\nCPS", "dado")
    d = caixa(ax, 0.830, y1, 0.155, h,
              "métrica por ocupação:\nuso $u$, automação $a$", "tratamento")
    liga(ax, c, t, "classificação\npor modelo")
    liga(ax, t, s, "repartição\nfracionária")
    liga(ax, s, o, "harmonização\nde versão")
    liga(ax, o, d, "agregação", lab=(-0.010, 0.012))

    y2 = 0.10
    p = caixa(ax, 0.105, y2, 0.17, 0.24, "CPS / IPUMS\nocupação × mês\n2010–2026", "dado")
    yy = caixa(ax, 0.380, y2, 0.17, 0.24,
               "desfechos: salário real\ne taxa de desemprego", "desfecho")
    es = caixa(ax, 0.700, y2, 0.19, 0.24,
               "event study com\ntratamento contínuo\n(seção 3.2.2)", "motor")
    liga(ax, p, yy)
    liga(ax, yy, es)
    liga(ax, d, es, "entra como\ntratamento",
         estilo=(0, (4, 3)), lado="v", off_a=-0.02, lab=(0.052, -0.06))

    legenda(ax, [("dado", "dado observado"), ("tratamento", "tratamento estimado"),
                 ("desfecho", "desfecho"), ("motor", "especificação")], y=-0.02)
    fig.tight_layout()
    destino = comum.FIG_DIR / "fig01_cadeia_metrica.png"
    fig.savefig(destino, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[6] figura: {destino.name}")


if __name__ == "__main__":
    main()
