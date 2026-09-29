"""Passo 1 — Os event studies por quarto, que são as Figuras 1, 3 e 5 do paper.

POR QUE O RECORTE POR QUARTOS EXISTE: o event study de métrica contínua impõe
linearidade, ou seja, assume que subir de 0,1 para 0,2 de uso faz o mesmo que
subir de 0,4 para 0,5. Os quartos relaxam isso. Cada quarto ganha a sua própria
série de coeficientes mensais contra o primeiro, que é o grupo de comparação. Se
a resposta cresce com a métrica, a forma contínua da seção 3.2 ganha crédito; se
não cresce, ela está mal especificada.

A regressão sempre estima os quatro quartos juntos, porque é isso que dá a cada
coeficiente a sua precisão correta. A figura desenha só o contraste extremo, o
quarto mais alto contra o mais baixo, porque três séries sobrepostas ficavam
ilegíveis na página.

Duas leituras saem daqui, e são perguntas diferentes:
  por intensidade  quem usa mais descolou de quem usa menos?
  por composição   dado que se usa, quem usa de forma mais substitutiva descolou
                   de quem usa de forma mais complementar?

Saídas:
  figures/fig01_es_quartis_desemprego_US_pooled.png              (Figura 1)
  figures/fig02_es_quartis_salarios_US_pooled.png                (Figura 3)
  figures/fig02_es_quartis_salarios_US_pooled_por_automacao.png  (Figura 5)
  tables/tab02_quartis_pos_medio_US_pooled[_por_automacao].md
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum

QUARTOS = [2, 3, 4]
COR_Q4 = "#d6604d"


def monta(por: str):
    """Painel com a coluna do quarto, cortada pela métrica escolhida."""
    doses = comum.carrega_doses(so_uso=(por == "intensidade"))
    base = "usage_z" if por == "intensidade" else "automation_z"
    # rank antes do corte para quebrar empates de forma determinística;
    # Q4 = mais usa, ou mais substitutivo
    doses = doses.assign(quarto=pd.qcut(
        doses[base].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int))
    df = pd.read_csv(comum.PAINEL_CSV)
    df = df[df["OCC"] > 0].drop(columns=["exposure_quartile"], errors="ignore")
    df = df.merge(doses[["OCC", "quarto"]], on="OCC", how="inner")
    return df, doses, base


def ajusta(df, y, w):
    sub = df.dropna(subset=[y, w]).copy()
    for q in QUARTOS:
        sub[f"q{q}"] = (sub["quarto"] == q).astype(float)
    termos = " + ".join(f"i(rel_time, q{q}, ref={comum.EVENT_REF})" for q in QUARTOS)
    return pf.feols(f"{y} ~ {termos} | OCC + yearmonth_idx",
                    data=sub, weights=w, vcov={"CRV1": "OCC"})


def contraste_pos(m, tokens, pesos):
    """Contraste linear dos coeficientes posteriores ao evento, com o vcov agrupado.

    Somar coeficientes é fácil; somar a incerteza deles exige a matriz de
    covariância, porque as séries mensais de um mesmo quarto são fortemente
    correlacionadas e tratar cada mês como independente subestimaria o
    erro-padrão. `tokens` identifica as séries e `pesos` diz com que sinal cada
    uma entra, de modo que [":q4", ":q3"] com [+1, −1] dá a diferença entre elas.
    """
    nomes = list(m.coef().index)
    b = m.coef().to_numpy()
    V = np.asarray(m._vcov)
    L = np.zeros(len(b))
    for tok, peso in zip(tokens, pesos):
        sel = [i for i, nm in enumerate(nomes)
               if tok in nm and "rel_time" in nm
               and comum.extrai_k(nm) is not None and comum.extrai_k(nm) >= 0]
        if not sel:
            raise SystemExit(f"nenhum coeficiente posterior ao evento para {tok}")
        L[sel] += peso / len(sel)
    est = float(L @ b)
    se = float(np.sqrt(L @ V @ L))
    return {"est": est, "se": se, "lo": est - 1.96 * se, "hi": est + 1.96 * se}


def figura(m, rotulo_y, titulo, nome):
    fig, ax = plt.subplots(figsize=(13, 5.5))
    r = comum.es_coefs(m, ":q4")
    datas = r["k"].map(comum.k_para_data)
    ax.fill_between(datas, r["est"] - 1.96 * r["se"], r["est"] + 1.96 * r["se"],
                    color=COR_Q4, alpha=0.13, linewidth=0)
    ax.plot(datas, r["est"], ".", ms=4, color=COR_Q4)
    comum.eixos_es(ax, rotulo_y)
    ax.set_title(titulo, fontsize=12)
    comum.rodape(fig)
    fig.tight_layout()
    fig.savefig(comum.FIG_DIR / nome, dpi=150)
    plt.close(fig)
    print(f"[3] figura: {nome}")


def equilibrio(doses, base):
    """Os quartos de uma métrica ficam equilibrados na outra?

    A seção 2.1.3 do relatório critica os desenhos que ordenam as ocupações por uma
    dimensão do uso de cada vez, porque isso deixa a outra solta, e o corte por
    quartos faz exatamente isso. A defesa aqui é empírica: medida como fração, a
    composição é quase não correlacionada com a intensidade, então os quartos de
    uma saem equilibrados na outra. Devolve None quando a outra métrica não está
    na amostra, que é o caso do corte por intensidade.
    """
    outra = "automation_z" if base == "usage_z" else "usage_z"
    if outra not in doses.columns:
        return None
    d = doses[["quarto", base, outra]].dropna()
    med = d.groupby("quarto")[outra].agg(["mean", "count"])
    q1 = d.loc[d["quarto"] == 1, outra]
    q4 = d.loc[d["quarto"] == 4, outra]
    t = stats.ttest_ind(q4, q1, equal_var=False)
    return {"outra": outra, "medias": med, "dif": float(q4.mean() - q1.mean()),
            "t": float(t.statistic), "p": float(t.pvalue),
            "cor": float(d[[base, outra]].corr().iloc[0, 1]), "n": len(d)}


def roda(por: str, figuras: dict, sufixo: str):
    df, doses, base = monta(por)
    print(f"[3] corte por {por} | {df['OCC'].nunique()} ocupações | {len(df)} células")

    mu = ajusta(df, "unemployment_rate", "total_labor_force")
    me = ajusta(df, "real_weekly_earnings", "n_earnings_obs")

    rot = ("quarto que mais usa vs. o que menos usa" if por == "intensidade"
           else "quarto de uso mais substitutivo vs. o mais complementar")
    if "desemprego" in figuras:
        figura(mu, "Efeito vs. Q1 (p.p. de desemprego)",
               f"Event study por {rot} — Desemprego", figuras["desemprego"])
    if "salarios" in figuras:
        figura(me, "Efeito vs. Q1 (US$ semanais de jan/2010)",
               f"Event study por {rot} — Salários reais", figuras["salarios"])

    cu = {q: contraste_pos(mu, [f":q{q}"], [1.0]) for q in QUARTOS}
    ce = {q: contraste_pos(me, [f":q{q}"], [1.0]) for q in QUARTOS}
    du = contraste_pos(mu, [":q4", ":q3"], [1.0, -1.0])
    de = contraste_pos(me, [":q4", ":q3"], [1.0, -1.0])

    diag = []
    for nome, m, cc in [("Desemprego (pontos de taxa)", mu, cu),
                        ("Salário (US$/sem)", me, ce)]:
        pw = comum.wald_pretendencia(m, ":q4", k_min=-25, k_max=-2)
        ps = comum.inclinacao_pretendencia(m, ":q4", k_min=-25, k_max=-2)
        r = comum.es_coefs(m, ":q4")
        vi = float(r.loc[(r["k"] >= -25) & (r["k"] <= -2), "est"].abs().mean())
        diag.append((nome, pw, vi, ps, cc))

    L = [f"# Tabela 02 — Média dos coeficientes posteriores a nov/2022 por quarto (vs. Q1)",
         "",
         f"Quartos cortados por: {'intensidade do uso' if por == 'intensidade' else 'composição substitutiva do uso'}",
         "",
         f"Ocupações: {df['OCC'].nunique()} | células: {len(df)}",
         "",
         "| Quarto | Desemprego (pontos de taxa) [IC 95%] | Salário (US$/sem) [IC 95%] |",
         "|---|---:|---:|"]
    L += [f"| Q{q} | {cu[q]['est']:+.4f} [{cu[q]['lo']:+.4f}; {cu[q]['hi']:+.4f}] "
          f"| {ce[q]['est']:+.2f} [{ce[q]['lo']:+.2f}; {ce[q]['hi']:+.2f}] |"
          for q in QUARTOS]
    L += [f"| Q4 − Q3 | {du['est']:+.4f} (e.p. {du['se']:.4f}) "
          f"| {de['est']:+.2f} (e.p. {de['se']:.2f}) |",
          "",
          "Leitura: a resposta que cresce com a métrica sustenta a especificação contínua",
          "da seção 3.2; a ausência disso indicaria não-linearidade que a forma contínua",
          "mascararia. A linha Q4 − Q3 é o teste do achatamento no topo: indistinguível de",
          "zero significa que a resposta cresce e satura, em vez de crescer sem parar.",
          "",
          "## Diagnóstico de pré-tendência da série Q4 (k = −25..−2)",
          "",
          "Veredito de pré-teste não vai sozinho: com 24 coeficientes bem estimados o Wald",
          "rejeita desvios economicamente irrelevantes, então quem decide são a escala das",
          "violações e a direção da inclinação. Inclinação que corre contra o efeito",
          "posterior não pode fabricá-lo, porque extrapolá-la preveria o oposto.",
          "",
          "| Desfecho | Wald 24m (p) | Violação média | Efeito posterior | razão ef/viol | Inclinação (p) |",
          "|---|---:|---:|---:|---:|---:|"]
    L += [f"| {nome} | {pw['p']:.3g} | {vi:.4f} | {cc[4]['est']:+.4f} | "
          f"{abs(cc[4]['est']) / vi if vi else float('nan'):.2f} | "
          f"{ps['inclinacao']:+.5f} ({ps['p']:.2g}) |"
          for nome, pw, vi, ps, cc in diag]
    L += ["",
          "Razão abaixo de 1 significa que as oscilações anteriores ao evento são maiores",
          "que o efeito que se quer medir: ali o desfecho não é testado por este desenho, o",
          "que é conclusão diferente de não haver efeito."]

    eq = equilibrio(doses[doses["OCC"].isin(df["OCC"].unique())], base)
    if eq is not None:
        rot_outra = "intensidade" if eq["outra"] == "usage_z" else "composição substitutiva"
        L += ["",
              f"## Equilíbrio dos quartos na outra métrica do uso ({rot_outra})",
              "",
              "Cortar por uma dimensão do uso deixa a outra solta? É a objeção que a seção",
              "2.1.3 do relatório levanta contra os desenhos que ordenam por uma de cada vez.",
              "Aqui ela é medida, e não argumentada.",
              "",
              f"| Quarto do corte | {rot_outra} média (d.p.) | Ocupações |",
              "|---|---:|---:|"]
        L += [f"| Q{int(q)} | {row['mean']:+.3f} | {int(row['count'])} |"
              for q, row in eq["medias"].iterrows()]
        L += [f"| **Q4 − Q1** | **{eq['dif']:+.3f}** (t = {eq['t']:+.2f}, "
              f"p = {eq['p']:.3f}) | {eq['n']} |",
              "",
              f"Correlação entre as duas métricas nesta amostra: {eq['cor']:+.3f}. Quanto mais",
              "perto de zero, mais o corte por uma delas preserva o equilíbrio na outra, e é",
              "isso que separa a composição medida como fração da medida como nível, que",
              "ordena as ocupações quase como a intensidade."]

    destino = comum.TAB_DIR / f"tab02_quartis_pos_medio_{comum.METRICA}{sufixo}.md"
    destino.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"[3] tabela: {destino.name}")


def main():
    # Figuras 1 e 3 do paper: o corte por intensidade do uso.
    roda("intensidade",
         {"desemprego": f"fig01_es_quartis_desemprego_{comum.METRICA}.png",
          "salarios": f"fig02_es_quartis_salarios_{comum.METRICA}.png"},
         sufixo="")
    # Figura 5: o corte por composição. O paper leva só a margem salarial daqui,
    # porque é nela que a decomposição tem o que mostrar.
    roda("composicao",
         {"salarios": f"fig02_es_quartis_salarios_{comum.METRICA}_por_automacao.png"},
         sufixo="_por_automacao")


if __name__ == "__main__":
    main()
