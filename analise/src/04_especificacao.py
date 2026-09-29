"""Passo 2 — A especificação do paper, e tudo que sai dela.

O paper tem UMA especificação, e é a dinâmica com os três termos da decomposição:
intensidade do uso (u), composição substitutiva (a) e o produto entre os dois
(u·a), cada um interagido com as dummies de mês, com efeitos fixos de ocupação e
de mês, WLS pelo tamanho da célula e erro-padrão agrupado por ocupação.

A razão da forma é de teoria. A tradução literal da abordagem de tarefas pediria
os dois VOLUMES, uso complementar e uso substitutivo, e esses dois correlacionam
+0,94 entre si nestes dados, de modo que não se separam. A reparametrização em
intensidade × fração é a forma da teoria que este painel identifica, porque u e a
são quase ortogonais, e o produto é o termo que a teoria exige. A Figura A2, que
o passo 3 desenha, é a evidência dessa afirmação.

Uma regressão por desfecho, e desta mesma regressão saem:

  1. o efeito médio posterior ao evento de cada termo, com erro-padrão próprio,
     que é a **Tabela 1** do paper. O erro-padrão é o da combinação linear c'β,
     com c = 1/n nos coeficientes posteriores, usando o vcov agrupado. Não é
     média de erros-padrão, que ignoraria a covariância entre os coeficientes;
  2. o diagnóstico de pré-tendência por termo, em três janelas, que é a
     **Tabela 2**;
  3. o efeito mínimo detectável, que é o que separa "efeito pequeno" de "efeito
     não medido" na leitura do zero do desemprego;
  4. o efeito marginal da composição por nível de uso;
  5. as **Figuras 2 e 4**, com as três séries.

Saídas:
  tables/tab21_especificacao_dinamica_US_pooled.md
  figures/fig21_es_tres_series_{salarios,desemprego}_US_pooled.png
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

DESFECHOS = [
    ("real_weekly_earnings", "n_earnings_obs", "Salário (US$/sem)", 1.0, "salarios"),
    ("unemployment_rate", "total_labor_force", "Desemprego (p.p. na taxa)", 100.0, "desemprego"),
]

# os três termos, na ordem da Tabela 1
SERIES = [("usage_z", "Uso (*u*)", "#1b7837"),
          ("automation_z", "Automação (*a*)", "#d6604d"),
          ("ua_z", "Interação (*u·a*)", "#8da0cb")]

# as três janelas do diagnóstico, em k (k = 0 é nov/2022)
JANELAS = [("24m convencional (out/2020–set/2022)", -25, -2),
           ("24m pré-pandemia (mar/2018–fev/2020)", -56, -33),
           ("2022, pós-fase-aguda (dez/2021–set/2022)", -11, -2)]


def idx_da_serie(nomes, token, k_min=None, k_max=None):
    """Posições, no vetor de coeficientes, da série de um termo."""
    out = []
    for i, nm in enumerate(nomes):
        if "rel_time" not in nm or f":{token}" not in nm:
            continue
        k = comum.extrai_k(nm)
        if k is None:
            continue
        if k_min is not None and not (k_min <= k <= k_max):
            continue
        out.append((i, k))
    return out


def media_pos(m, token, escala):
    ix = [i for i, k in idx_da_serie(list(m.coef().index), token) if k >= 0]
    est, se = comum.combinacao(m, [(i, 1.0 / len(ix)) for i in ix])
    return est * escala, se * escala, len(ix)


def colinearidade(sub, w):
    """Correlações e VIF dos três regressores, no peso que a WLS usa.

    Existe porque a justificativa da troca de coordenadas é a ortogonalidade, e a
    correlação quase nula entre u e a fala de dois regressores num sistema de
    três. O produto u·a não é ortogonal a a, e o que decide se isso atrapalha não
    é a correlação, é o fator de inflação de variância.
    """
    occ = sub.drop_duplicates("OCC")[["OCC", "usage_z", "automation_z", "ua_z"]]
    peso = sub.groupby("OCC")[w].sum().rename("w")
    occ = occ.set_index("OCC").join(peso, how="inner").dropna()
    X = occ[["usage_z", "automation_z", "ua_z"]].to_numpy()
    p = occ["w"].to_numpy()

    def wcor(x, y):
        mx, my = np.average(x, weights=p), np.average(y, weights=p)
        cov = np.average((x - mx) * (y - my), weights=p)
        return cov / np.sqrt(np.average((x - mx) ** 2, weights=p)
                             * np.average((y - my) ** 2, weights=p))

    def vif(j):
        y = X[:, j]
        Z = np.column_stack([np.ones(len(X))] + [X[:, k] for k in range(3) if k != j])
        sp = np.sqrt(p)
        b = np.linalg.lstsq(Z * sp[:, None], y * sp, rcond=None)[0]
        r = y - Z @ b
        r2 = 1 - np.average(r ** 2, weights=p) / np.average(
            (y - np.average(y, weights=p)) ** 2, weights=p)
        return 1.0 / (1.0 - r2)

    pares = [(0, 1, "u × a"), (0, 2, "u × u·a"), (1, 2, "a × u·a")]
    return ([(rot, wcor(X[:, i], X[:, j])) for i, j, rot in pares],
            [(rot, vif(j)) for j, rot in enumerate(["u", "a", "u·a"])])


def ajusta(y, w, sub):
    fml = (f"{y} ~ i(rel_time, usage_z, ref={comum.EVENT_REF})"
           f" + i(rel_time, automation_z, ref={comum.EVENT_REF})"
           f" + i(rel_time, ua_z, ref={comum.EVENT_REF})"
           " | OCC + yearmonth_idx")
    return pf.feols(fml, data=sub, weights=w, vcov={"CRV1": "OCC"})


def figura(m, escala, rotulo_y, destino, titulo):
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for token, rot, cor in SERIES:
        r = comum.es_coefs(m, f":{token}")
        r = r[r["k"] >= -60]
        datas = [comum.k_para_data(k) for k in r["k"]]
        est = r["est"] * escala
        se = r["se"] * escala
        ax.plot(datas, est, color=cor, lw=1.6, label=rot.replace("*", ""))
        ax.fill_between(datas, est - 1.96 * se, est + 1.96 * se,
                        color=cor, alpha=0.15, lw=0)
    ax.axhline(0, color="#444444", lw=0.9)
    ax.axvline(pd.Timestamp("2020-03-01"), color="#777777", ls=":", lw=1.1)
    ax.axvline(pd.Timestamp("2022-03-01"), color="#777777", ls="--", lw=1.1)
    ax.axvline(pd.Timestamp("2022-11-01"), color="#d6604d", lw=1.3)
    ax.set_ylabel(rotulo_y)
    ax.set_title(titulo, fontsize=11)
    ax.legend(frameon=False, ncol=3, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(destino, dpi=200)
    plt.close(fig)


def main():
    doses = comum.carrega_doses()
    df = comum.carrega_painel(doses)
    df["ua_z"] = df["usage_z"] * df["automation_z"]

    L = ["# Tabela 21 — a especificação dinâmica de três termos", "",
         "Uma única regressão por desfecho: u, a e u×a, cada um interagido com as dummies",
         "de mês, com efeitos fixos de ocupação e de mês, WLS pelo tamanho da célula e",
         "erros-padrão agrupados por ocupação.", "",
         f"Ocupações: {df['OCC'].nunique()} | células: {len(df)}", ""]

    for y, w, rotulo_y, escala, slug in DESFECHOS:
        sub = df.dropna(subset=[y, w])
        occ_u = sub.drop_duplicates("OCC")["usage_z"]
        m = ajusta(y, w, sub)
        nomes = list(m.coef().index)
        casas = 1 if escala == 1.0 else 2
        L += [f"## {rotulo_y}", "",
              f"Células: {len(sub)} | ocupações: {sub['OCC'].nunique()}", ""]

        # ---- colinearidade dos três regressores ----
        cors, vifs = colinearidade(sub, w)
        L += ["**Colinearidade dos três regressores**, no peso que a WLS usa. A ortogonalidade",
              "que justifica a troca de coordenadas é entre u e a; o produto u·a não é",
              "ortogonal a a, e é o VIF que diz se isso atrapalha:", "",
              "| par | correlação ponderada |", "|---|---:|"]
        L += [f"| {rot} | {c:+.3f} |" for rot, c in cors]
        L += ["", "| regressor | VIF |", "|---|---:|"]
        L += [f"| {rot} | {v:.2f} |" for rot, v in vifs]
        L.append("")
        print(f"[4] {y} VIF máximo {max(v for _, v in vifs):.2f}")

        # ---- 1. efeito médio posterior, com e.p. próprio (Tabela 1 do paper) ----
        guardado = {}
        L += ["**Efeito médio pós-tratamento por termo** — média dos coeficientes de k ≥ 0,",
              "com o erro-padrão da combinação linear (c'Vc, vcov agrupado):", "",
              "| Termo | efeito médio pós | e.p. | n coefs |", "|---|---:|---:|---:|"]
        for token, rot, _ in SERIES:
            est, se, n = media_pos(m, token, escala)
            guardado[token] = (est, se)
            L.append(f"| {rot} | {est:+.{casas}f}{comum.estrelas(est, se)} "
                     f"| ({se:.{casas}f}) | {n} |")
            print(f"[4] {y} {token}: {est:+.4g} (e.p. {se:.4g})")
        L.append("")

        # ---- 2. efeito mínimo detectável, NESTA especificação ----
        # O MDE sai dos erros-padrão desta regressão, que é a que o paper reporta.
        # Herdá-lo de qualquer outra forma da especificação daria um número que
        # não descreve a potência deste desenho, e é essa potência que a leitura
        # do zero do desemprego usa.
        L += ["**Efeito mínimo detectável (MDE) por termo** — 2,8 × e.p., que é o menor",
              "efeito verdadeiro que este desenho rejeitaria em 80% das amostras a 5% de",
              "significância:", "",
              "| Termo | e.p. | MDE (80% de potência) |", "|---|---:|---:|"]
        for token, rot, _ in SERIES:
            _, se = guardado[token]
            L.append(f"| {rot} | ({se:.{casas}f}) | {2.8 * se:.{casas}f} |")
        L.append("")

        # ---- 3. pré-tendência por termo, em três janelas (Tabela 2) ----
        L += ["**Diagnóstico de pré-tendência por termo** — mesmo modelo e mesmos",
              "coeficientes; muda só quais meses entram no teste:", "",
              "| Termo | Janela | p (Wald) | \\|pré\\| médio | % indiv. sig. | efeito/violação |",
              "|---|---|---:|---:|---:|---:|"]
        for token, rot, _ in SERIES:
            pos_est = abs(guardado[token][0])
            for nome_j, kmin, kmax in JANELAS:
                sel = [i for i, _ in idx_da_serie(nomes, token, kmin, kmax)]
                b = m.coef().to_numpy()[sel]
                V = np.asarray(m._vcov)[np.ix_(sel, sel)]
                W = float(b @ np.linalg.solve(V, b))
                p = float(stats.chi2.sf(W, len(b)))
                se_ind = m.se().to_numpy()[sel]
                pre_abs = float(np.abs(b).mean()) * escala
                share = float((np.abs(b) > 1.96 * se_ind).mean())
                razao = pos_est / pre_abs if pre_abs > 0 else np.nan
                L.append(f"| {rot} | {nome_j} | {p:.3g} | {pre_abs:.4g} "
                         f"| {share:.0%} | {razao:.2f}× |")
        L.append("")

        # ---- 4. efeito marginal da composição por nível de uso ----
        # O ponto em que ∂y/∂a cruza zero cai DENTRO do intervalo observado, e a
        # tabela mostra os dois extremos justamente por isso: dizer que a
        # penalidade nunca inverte seria falso. O que sustenta a leitura não é a
        # ausência de cruzamento, é o cruzamento cair onde a estimativa já não se
        # separa de zero.
        ia = [i for i, k in idx_da_serie(nomes, "automation_z") if k >= 0]
        iu = [i for i, k in idx_da_serie(nomes, "ua_z") if k >= 0]
        u_min, u_max = float(occ_u.min()), float(occ_u.max())
        g, dl = guardado["automation_z"][0], guardado["ua_z"][0]
        u_zero = -g / dl if dl != 0 else np.nan
        niveis = sorted({round(u_min, 3), -1.0, 0.0, 1.0, 2.0, round(u_max, 3)}
                        | ({round(u_zero, 3)} if u_min < u_zero < u_max else set()))
        L += ["**Efeito marginal da composição, por nível de uso** — ∂y/∂a = γ + δ·u,",
              "com o erro-padrão da mesma combinação linear. Os níveis cobrem o intervalo",
              f"observado de u, de {u_min:+.2f} a {u_max:+.2f} d.p.:", "",
              "| nível de uso | ∂y/∂a | e.p. |", "|---|---:|---:|"]
        for u in niveis:
            pesos = [(i, 1.0 / len(ia)) for i in ia] + [(i, u / len(iu)) for i in iu]
            est, se = comum.combinacao(m, pesos)
            marca = ("  ← mínimo observado" if u == round(u_min, 3) else
                     "  ← máximo observado" if u == round(u_max, 3) else
                     "  ← cruzamento de sinal" if u == round(u_zero, 3) else "")
            L.append(f"| u = {u:+.2f} d.p.{marca} | {est * escala:+.{casas}f}"
                     f"{comum.estrelas(est, se)} | ({se * escala:.{casas}f}) |")
        if u_min < u_zero < u_max:
            n_abaixo = int((occ_u < u_zero).sum())
            L += ["",
                  f"O sinal de ∂y/∂a cruza zero em u = {u_zero:+.2f} d.p., que está **dentro** do",
                  f"intervalo observado: {n_abaixo} das {len(occ_u)} ocupações "
                  f"({n_abaixo / len(occ_u):.1%}) ficam abaixo desse ponto. Ali a estimativa já",
                  "não se separa de zero, de modo que o cruzamento é a reta saindo do suporte,",
                  "e não penalidade medida com o sinal invertido.", ""]
        else:
            L += ["", "O sinal de ∂y/∂a não cruza zero no intervalo observado de u.", ""]

        # ---- 5. a forma contínua contra o recorte por quartos ----
        occ_q = sub.drop_duplicates("OCC")[["OCC", "usage_z", "automation_z"]].copy()
        L += ["**A forma contínua contra o recorte por quartos** — o que o coeficiente por",
              "d.p. prevê para o contraste entre os quartos extremos, dado o vão entre eles.",
              "A estimativa sem reta do mesmo contraste está na `tab02`:", "",
              "| dimensão | coef./d.p. | vão Q4−Q1 (d.p.) | previsão da reta |",
              "|---|---:|---:|---:|"]
        for col, rot in [("usage_z", "Intensidade (*u*)"),
                         ("automation_z", "Composição (*a*)")]:
            q = pd.qcut(occ_q[col], 4, labels=[1, 2, 3, 4])
            medias = occ_q.groupby(q, observed=True)[col].mean()
            vao = float(medias.loc[4] - medias.loc[1])
            coef = guardado[col][0]
            L.append(f"| {rot} | {coef:+.{casas}f} | {vao:.2f} | {coef * vao:+.{casas}f} |")
        L.append("")

        # ---- 6. a figura das três séries ----
        destino = comum.FIG_DIR / f"fig21_es_tres_series_{slug}_{comum.METRICA}.png"
        figura(m, escala, rotulo_y, destino,
               "Três termos na mesma regressão: intensidade, composição e o produto")
        L += [f"Figura: `{destino.name}`", ""]
        print(f"[4] figura: {destino.name}")

    saida = comum.TAB_DIR / f"tab21_especificacao_dinamica_{comum.METRICA}.md"
    saida.write_text("\n".join(L), encoding="utf-8", newline="\n")
    print(f"[4] tabela: {saida.name}")


if __name__ == "__main__":
    main()
