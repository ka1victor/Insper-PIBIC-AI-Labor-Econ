"""Passo 3 — A Figura A2: por que a especificação é em intensidade e fração.

A tradução literal da abordagem de tarefas pediria os dois VOLUMES, uso
complementar e uso substitutivo por trabalhador, que é o que a literatura mede em
nível. Esses dois ordenam as ocupações quase como um vetor só, e por isso não se
separam neste painel. Intensidade e fração, que é a reparametrização que o paper
usa, variam de forma independente.

Os dois painéis da figura mostram exatamente isso, com os mesmos insumos e a mesma
amostra: à esquerda o par de regressores que o paper estima, à direita o par que a
tradução literal pediria. A única diferença entre eles é a escolha de coordenadas.

Nenhum dado novo entra aqui: as duas construções saem das mesmas contagens do AEI
que já estão em `dados/doses_por_ocupacao.csv`.

Saída: figures/fig16_ortogonalidade_vs_volumes_US_pooled.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum

VERDE, TIJOLO = "#1b7837", "#d6604d"


def doses_de_nivel():
    """Reconstrói as métricas de NÍVEL à moda da literatura, do mesmo insumo.

    Volume substitutivo é o uso total vezes a fração substitutiva, por
    trabalhador, em log padronizado; o complementar usa a fração restante. O
    denominador de emprego é o pré-tratamento, pela mesma razão que vale no resto
    do trabalho: emprego posterior ao evento é desfecho, e usá-lo contaminaria o
    tratamento com o próprio efeito.
    """
    d = pd.read_csv(comum.DOSES_CSV)
    tot, sh = f"total_usage_{comum.METRICA}", f"automation_share_{comum.METRICA}"
    faltando = [c for c in (tot, sh, "emp_pretreat_2019_2022") if c not in d.columns]
    if faltando:
        raise SystemExit(f"colunas ausentes no arquivo de métricas: {faltando}")
    emp = d["emp_pretreat_2019_2022"]
    auto_pc = (d[tot] * d[sh]) / emp
    aug_pc = (d[tot] * (1 - d[sh])) / emp

    def zl(s):
        v = np.log(s.where(s > 0))
        return (v - v.mean()) / v.std(ddof=1)

    return pd.DataFrame({"OCC": d["OCC"], "auto_pc_z": zl(auto_pc),
                         "aug_pc_z": zl(aug_pc)})


def figura(occ, cor_volumes):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3))
    paineis = [
        (axes[0], occ["usage_z"], occ["automation_z"], VERDE,
         "A. O que estimamos: intensidade × fração",
         "intensidade do uso $u$ (d.p.)", "fração substitutiva $a$ (d.p.)",
         occ["usage_z"].corr(occ["automation_z"])),
        (axes[1], occ["aug_pc_z"], occ["auto_pc_z"], TIJOLO,
         "B. A tradução literal: os dois volumes",
         "volume complementar (d.p.)", "volume substitutivo (d.p.)",
         cor_volumes),
    ]
    for ax, x, y, cor, titulo, xlab, ylab, r in paineis:
        ax.scatter(x, y, s=13, color=cor, alpha=0.5, linewidth=0)
        # a reta de ajuste é o que separa visualmente uma nuvem de uma reta
        b = np.polyfit(x, y, 1)
        xx = np.linspace(x.min(), x.max(), 50)
        ax.plot(xx, np.polyval(b, xx), color=cor, lw=1.7)
        ax.set_title(titulo, fontsize=10.5)
        ax.set_xlabel(xlab, fontsize=9.5)
        ax.set_ylabel(ylab, fontsize=9.5)
        # menos tipográfico e vírgula decimal, que é o que a página do paper usa
        ax.text(0.04, 0.94, f"r = {r:+.2f}".replace(".", ",").replace("-", "−"),
                transform=ax.transAxes, fontsize=12, fontweight="bold",
                color=cor, va="top")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8.5)
    # mesma escala nos dois painéis: sem isso a comparação visual é enganosa
    lim = min(a.get_xlim()[0] for a in axes), max(a.get_xlim()[1] for a in axes)
    for ax in axes:
        ax.set_xlim(*lim)
        ax.set_ylim(*lim)

    fig.tight_layout()
    destino = comum.FIG_DIR / f"fig16_ortogonalidade_vs_volumes_{comum.METRICA}.png"
    fig.savefig(destino, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[5] figura: {destino.name}")


def main():
    nossas = comum.carrega_doses()
    niveis = doses_de_nivel()
    df = pd.read_csv(comum.PAINEL_CSV)
    df = df[df["OCC"] > 0].merge(nossas, on="OCC").merge(niveis, on="OCC")
    df = df.dropna(subset=["auto_pc_z", "aug_pc_z", "usage_z", "automation_z"])

    occ = df.drop_duplicates("OCC")
    print(f"[5] {len(occ)} ocupações em que os dois pares existem")
    for rot, a, b in [("volume substitutivo × intensidade", "auto_pc_z", "usage_z"),
                      ("volume complementar × intensidade", "aug_pc_z", "usage_z"),
                      ("volume substitutivo × volume complementar", "auto_pc_z", "aug_pc_z"),
                      ("volume substitutivo × fração", "auto_pc_z", "automation_z")]:
        print(f"[5] correlação {rot}: {occ[a].corr(occ[b]):+.3f}")

    figura(occ, occ["auto_pc_z"].corr(occ["aug_pc_z"]))


if __name__ == "__main__":
    main()
