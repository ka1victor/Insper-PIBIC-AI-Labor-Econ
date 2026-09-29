"""Passo 2 — A métrica de uso por ocupação, reconstruída da fonte primária.

Este passo é o único que precisa de rede, e é opcional: o
`dados/doses_por_ocupacao.csv` que ele produz já vem no repositório, e os passos
3 a 6 partem dele. Rode-o quando quiser refazer a métrica do zero, em vez de
confiar no arquivo versionado.

O QUE ELE CONSTRÓI. Do Anthropic Economic Index vêm as conversas classificadas
por tarefa O*NET e por tipo de colaboração. Daí saem, por ocupação:

  intensidade do uso (u)  uso total por trabalhador, em log
  composição (a)          que fração do uso classificado é substitutiva

POR QUE SOMAR TRÊS RELATÓRIOS, e não usar um. A métrica que o desenho supõe é a
composição média do período posterior ao evento, e cada relatório é uma medida
ruidosa dela, numa janela de cerca de uma semana. Usar um só é sortear um ponto
da série, e o de agosto de 2025 é o pico histórico da automação, com 49% contra
45% três meses depois. Somamos as contagens por tarefa entre os três e
recomputamos as frações, que é o procedimento da própria fonte no seu trabalho
que liga o índice a salário e emprego (Massenkoff; McCrory, 2026). O ganho é de
precisão: a mediana de conversas classificadas por ocupação vai de 265 para 809,
e 41 ocupações só têm composição observável quando se juntam as janelas.

FILTRO: nenhum, além da censura da própria fonte, que só publica células-tarefa
com pelo menos 15 conversas. As colunas com sufixo `_min50` saem como
diagnóstico, e não como especificação: elas mostram que a instabilidade entre
relatórios vive nas ocupações de poucas conversas.

A CADEIA, elo a elo, está desenhada na Figura A1 e derivada em
`docs/METRICA-AEI.md`. Os dois elos que falham em silêncio são a repartição
fracionária, sem a qual a mesma conversa é contada várias vezes, e a
harmonização de versão do código de ocupação, sem a qual as ocupações de
tecnologia perdem o período anterior ao evento inteiro.

Saídas:
  dados/doses_por_ocupacao.csv                     as métricas por ocupação
  tables/tab07b_diagnostico_releases.md            Tabelas A1, A2 e A3
"""
import argparse
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum

AUX = comum.DADOS / "aei"
RELEASES = {  # release → (arquivo, janela das conversas)
    "v3": (AUX / "aei_enriched_claude_ai_2025-08-04_to_2025-08-11.csv",
           "04–11/08/2025"),
    "v4": (AUX / "aei_raw_claude_ai_2025-11-13_to_2025-11-20.csv",
           "13–20/11/2025"),
    "v5": (AUX / "aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv",
           "05–12/02/2026"),
}
ONET_TASKS = AUX / "onet_task_statements.csv"    # universo tarefa × ocupação
ONET_RATINGS = AUX / "onet_task_ratings.txt"     # importância da tarefa (escala IM)
SOC_CPS_XWALK = comum.DADOS / "crosswalks" / "nem-occcode-cps-crosswalk.xlsx"

AUTOMATIVE = ["directive", "feedback loop"]
AUGMENTATIVE = ["learning", "task iteration", "validation"]
MIN_MATCH = 0.75  # taxa mínima de match tarefa→universo p/ aceitar um release


# ---------------------------------------------------------------------------
# A cadeia tarefa → SOC → código do CPS.
# Estas três funções e o mapa abaixo vêm do pipeline da réplica de Chen et al.,
# e estão aqui inline para que este pacote não dependa dela.
# ---------------------------------------------------------------------------
SOC_2010_TO_2018 = {
    "11-2031": "11-2032",  # PR & fundraising managers -> PR managers (mesmo CPS)
    "13-1021": "13-1020",  # buyers & purchasing agents (fusão dos 3 detalhados)
    "13-1022": "13-1020",
    "13-1023": "13-1020",
    "13-2021": "13-2023",  # assessors -> appraisers/assessors of real estate
    "15-1132": "15-1252",  # software developers, applications -> software devs
    "15-1133": "15-1252",  # software developers, systems software -> idem
    "15-1199": "15-1253",  # SQA engineers/testers -> SQA analysts & testers
    "15-2091": "15-2099",  # mathematical technicians -> math sci., all other
    "21-1011": "21-1018",  # subst. abuse counselors -> subst./mental health
    "21-1014": "21-1018",  # mental health counselors -> idem
    "23-2091": "27-3092",  # court reporters -> court reporters & captioners
    "25-1191": "25-1199",  # graduate TAs -> postsecondary, all other
    "25-4021": "25-4022",  # librarians -> librarians & media coll. specialists
    "27-3021": "27-3023",  # broadcast news analysts -> news analysts/reporters
    "27-3022": "27-3023",  # reporters & correspondents -> idem
    "29-1062": "29-1215",  # family & general practitioners -> family medicine
    "29-1063": "29-1216",  # internists, general -> general internal medicine
    "29-1067": "29-1249",  # surgeons -> surgeons, all other
    "29-2011": "29-2018",  # med./clinical lab technologists -> lab tech(s)
    "29-2012": "29-2018",  # med./clinical lab technicians -> idem
    "29-2041": "29-2042",  # EMTs & paramedics -> EMTs
    "29-2071": "29-2072",  # medical records techs -> medical records specialists
    "31-1011": "31-1121",  # home health aides
    "35-3021": "35-3023",  # combined food prep/serving -> fast food & counter
    "35-3022": "35-3023",  # counter attendants -> idem
    "39-9021": "31-1122",  # personal care aides
    "43-5081": "53-7065",  # stock clerks, sales floor -> stockers/order fillers
    "51-2022": "51-2028",  # electrical/electronic assemblers
    "51-2023": "51-2028",  # electromechanical assemblers
    "51-4011": "51-9161",  # CNC machine tool operators
    "51-4012": "51-9162",  # CNC machine tool programmers
}

def load_onet_universe():
    """Universo de tarefas O*NET por SOC (6 dígitos). Cada linha = (SOC, tarefa).

    Mantém também o título O*NET (para o fallback de match por título).
    """
    df = pd.read_csv(ONET_TASKS, usecols=["O*NET-SOC Code", "Title", "Task"])
    df = df.dropna(subset=["O*NET-SOC Code", "Task"])
    # O*NET usa código detalhado "11-1011.00"; o crosswalk usa 6 dígitos "11-1011".
    df["SOC"] = df["O*NET-SOC Code"].str.split(".").str[0]
    df["onet_title"] = df["Title"].astype(str).str.strip().str.lower()
    df["task"] = df["Task"].str.strip().str.lower()
    # DECISÃO: dedup por (SOC, tarefa) — evita contar a mesma tarefa 2x no mesmo
    # SOC caso o O*NET liste duplicatas de texto.
    df = df.drop_duplicates(subset=["SOC", "task"])
    return df[["SOC", "onet_title", "task"]]


def harmonize_socs(onet, xwalk):
    """Harmoniza os SOCs 2010 do O*NET com os SOCs 2018 do crosswalk NEM.

    Devolve o universo O*NET com coluna ``SOC`` já na taxonomia do crosswalk
    (códigos sem correspondência são descartados) e um dict de diagnóstico.
    """
    xsocs = set(xwalk["SOC"])
    titles = onet.drop_duplicates("SOC")[["SOC", "onet_title"]]

    # (ii) fallback: título O*NET == título NEM (lowercase/strip)
    tmap = (
        xwalk.assign(title_n=xwalk["nem_title"].astype(str).str.strip().str.lower())
        .drop_duplicates("title_n")
        .set_index("title_n")["SOC"]
    )

    def resolve(row):
        if row.SOC in xsocs:                     # (i) código bate direto
            return row.SOC
        by_title = tmap.get(row.onet_title)      # (ii) título idêntico
        if by_title is not None:
            return by_title
        manual = SOC_2010_TO_2018.get(row.SOC)   # (iii) mapa manual (guardado)
        if manual is not None and manual in xsocs:
            return manual
        return None

    titles = titles.assign(SOC_2018=titles.apply(resolve, axis=1))
    diag = {
        "n_socs": len(titles),
        "direct": int(titles["SOC"].isin(xsocs).sum()),
        "unresolved": sorted(titles.loc[titles["SOC_2018"].isna(), "SOC"]),
    }
    onet = onet.merge(titles[["SOC", "SOC_2018"]], on="SOC", how="left")
    onet = onet.dropna(subset=["SOC_2018"])
    # SOC_orig (código pré-harmonização) viaja junto: é a chave com que o
    # O*NET Task Ratings indexa a importância da tarefa (melhoria 7 — crosswalk
    # fracionário). Os consumidores que agregam por SOC ignoram a coluna extra.
    onet = onet.rename(columns={"SOC": "SOC_orig", "SOC_2018": "SOC"})
    # Re-dedup: fusões 2010->2018 (ex.: 15-1132 e 15-1133 -> 15-1252) podem
    # gerar a mesma tarefa 2x no SOC combinado.
    onet = onet.drop_duplicates(subset=["SOC", "task"])
    return onet[["SOC", "task", "SOC_orig"]], diag


def load_xwalk():
    """Crosswalk BLS/NEM: SOC (6 díg.) -> código CPS numérico + título CPS."""
    xw = pd.read_excel(SOC_CPS_XWALK, sheet_name=0, header=0)
    xw = xw.rename(
        columns={
            "National Employment Matrix code": "SOC",
            "National Employment Matrix title": "nem_title",
            "CPS code": "CPS_CODE",
            "CPS occupation title": "occ_title",
        }
    )
    xw = xw[["SOC", "nem_title", "CPS_CODE", "occ_title"]].dropna(
        subset=["SOC", "CPS_CODE"]
    )
    xw["SOC"] = xw["SOC"].astype(str).str.strip()
    xw["CPS_CODE"] = pd.to_numeric(xw["CPS_CODE"], errors="coerce")
    xw = xw.dropna(subset=["CPS_CODE"])
    xw["CPS_CODE"] = xw["CPS_CODE"].astype(int)
    return xw


def load_collab(df, geo_mask, label):
    sub = df[geo_mask
             & (df["facet"] == "onet_task::collaboration")
             & (df["variable"] == "onet_task_collaboration_count")].copy()
    if sub.empty:
        print(f"[2] AVISO: sem faceta de colaboração p/ {label}.")
        return None
    split = sub["cluster_name"].str.rsplit("::", n=1, expand=True)
    sub["task"] = split[0].str.strip().str.lower()
    sub["ctype"] = split[1].str.strip().str.lower()
    sub["value"] = pd.to_numeric(sub["value"], errors="coerce").fillna(0.0)
    g = sub.groupby(["task", "ctype"], as_index=False)["value"].sum()
    piv = g.pivot(index="task", columns="ctype", values="value").fillna(0.0)
    out = pd.DataFrame(index=piv.index)
    out["usage"] = piv.sum(axis=1)
    out["auto"] = piv[[c for c in AUTOMATIVE if c in piv.columns]].sum(axis=1)
    out["classified"] = out["auto"] + piv[
        [c for c in AUGMENTATIVE if c in piv.columns]].sum(axis=1)
    print(f"[2] {label}: {len(out)} tarefas | uso total {out['usage'].sum():,.0f}")
    return out.reset_index()


def load_us_task_counts(df, label):
    """Contagens por tarefa no recorte país=US (numerador da adoção só-EUA)."""
    sub = df[df["geography"].eq("country")
             & df["geo_id"].astype(str).isin(["US", "USA"])
             & df["facet"].eq("onet_task")
             & df["variable"].eq("onet_task_count")].copy()
    if sub.empty:  # V3 enriched não traz a variable p/ onet_task simples
        sub = df[df["geography"].eq("country")
                 & df["geo_id"].astype(str).isin(["US", "USA"])
                 & df["facet"].eq("onet_task")].copy()
        sub = sub[~sub["variable"].astype(str).str.contains("pct", na=False)]
    if sub.empty:
        return None
    sub["task"] = sub["cluster_name"].str.strip().str.lower()
    sub["value"] = pd.to_numeric(sub["value"], errors="coerce").fillna(0.0)
    out = sub.groupby("task", as_index=False)["value"].sum().rename(
        columns={"value": "usage"})
    out["auto"] = np.nan
    out["classified"] = np.nan
    print(f"[2] {label}: {len(out)} tarefas US | uso {out['usage'].sum():,.0f}")
    return out


def country_agg_automation(df, label):
    """Participação automativa agregada (faceta collaboration) US vs. global.

    Conferência do par 49,1% (EUA) × 51,1% (global) citado na Tabela A2 do relatório."""
    res = {}
    for geo, mask in [
            ("US", df["geography"].eq("country")
             & df["geo_id"].astype(str).isin(["US", "USA"])),
            ("global", df["geography"].eq("global"))]:
        sub = df[mask & df["facet"].eq("collaboration")
                 & df["variable"].astype(str).str.endswith("_count")].copy()
        if sub.empty:
            res[geo] = np.nan
            continue
        sub["ctype"] = sub["cluster_name"].str.strip().str.lower()
        sub["value"] = pd.to_numeric(sub["value"], errors="coerce").fillna(0.0)
        tot = sub.groupby("ctype")["value"].sum()
        auto = tot.reindex(AUTOMATIVE).fillna(0.0).sum()
        classified = auto + tot.reindex(AUGMENTATIVE).fillna(0.0).sum()
        res[geo] = auto / classified if classified > 0 else np.nan
    print(f"[2] {label}: automação agregada US = {res.get('US', np.nan):.3f} "
          f"| global = {res.get('global', np.nan):.3f}")
    return res


def build_frac_weights(onet):
    """Pesos do crosswalk fracionário tarefa→SOC (melhoria 7 / P4 do Plano).

    O mapeamento tarefa→SOC é 1-para-muitos: uma tarefa compartilhada por N
    ocupações tinha sua contagem de conversas atribuída INTEIRA a cada uma
    (não-injetividade — limitação 5 do paper). O remédio é fracionar: cada
    conversa é alocada UMA vez, repartida entre as ocupações que compartilham a
    tarefa proporcionalmente à IMPORTÂNCIA da tarefa em cada ocupação (O*NET
    Task Ratings, escala IM, 1–5).

    Devolve `onet` com duas colunas de peso, normalizadas por tarefa (somam 1
    dentro de cada tarefa):
      w_frac — proporcional à importância IM (construção CORE);
      w_unif — repartição uniforme 1/N (isola o efeito de fracionar do efeito
               de ponderar por importância; robustez do apêndice D);
    e um dict de diagnóstico de cobertura.

    Fallbacks documentados: par (SOC, tarefa) sem IM recebe a IM média da
    própria tarefa nos SOCs onde ela é avaliada (peso relativo neutro); tarefa
    sem IM em lugar nenhum cai na repartição uniforme. Se o arquivo de ratings
    não existir, w_frac degenera em w_unif com aviso ruidoso."""
    onet = onet.copy()
    grp_task = onet.groupby("task")["SOC"]
    onet["w_unif"] = 1.0 / grp_task.transform("size")

    ratings_path = ONET_RATINGS
    uni_path = ONET_TASKS
    diag = {"n_pairs": len(onet)}
    im_pair = None
    if ratings_path.exists() and ratings_path.stat().st_size > 100_000:
        try:
            uni = pd.read_csv(uni_path, dtype=str,
                              usecols=["O*NET-SOC Code", "Task ID", "Task"])
        except ValueError:  # universo sem "Task ID": cai no rateio uniforme
            uni = None
        if uni is not None:
            rat = pd.read_csv(ratings_path, sep="\t", dtype=str)
            rat = rat[rat["Scale ID"] == "IM"][
                ["O*NET-SOC Code", "Task ID", "Data Value"]].copy()
            rat["im"] = pd.to_numeric(rat["Data Value"], errors="coerce")
            m = uni.merge(rat[["O*NET-SOC Code", "Task ID", "im"]],
                          on=["O*NET-SOC Code", "Task ID"], how="inner")
            m["SOC_orig"] = m["O*NET-SOC Code"].str.split(".").str[0]
            m["task"] = m["Task"].str.strip().str.lower()
            # média entre códigos detalhados (.00/.01…) do mesmo SOC 6 dígitos
            im_pair = m.groupby(["SOC_orig", "task"], as_index=False)["im"].mean()
    if im_pair is None:
        print("[2] AVISO (melhoria 7): O*NET Task Ratings indisponível ou "
              "universo sem Task ID — w_frac DEGENERA em repartição uniforme. "
              "Rodar 07 para baixar aux_data/onet_task_ratings.txt.")
        onet["w_frac"] = onet["w_unif"]
        diag.update({"rated_pairs": 0, "rated_after_fallback": 0})
        return onet, diag

    onet = onet.merge(im_pair, on=["SOC_orig", "task"], how="left")
    diag["rated_pairs"] = int(onet["im"].notna().sum())
    # fallback 1: IM média da própria tarefa (peso relativo neutro no rateio)
    onet["im_filled"] = onet["im"].fillna(
        onet.groupby("task")["im"].transform("mean"))
    diag["rated_after_fallback"] = int(onet["im_filled"].notna().sum())
    # fallback 2: tarefa sem IM em nenhum SOC → uniforme (im constante)
    onet["im_filled"] = onet["im_filled"].fillna(1.0)
    onet["w_frac"] = onet["im_filled"] / onet.groupby("task")[
        "im_filled"].transform("sum")
    tasks_multi = grp_task.size()
    diag["n_tasks"] = int(len(tasks_multi))
    diag["n_tasks_shared"] = int((tasks_multi > 1).sum())
    return onet.drop(columns=["im", "im_filled"]), diag


def to_cps(task_df, onet, xwalk, weight_col=None):
    """Agrega contagens tarefa→SOC→CPS.

    weight_col=None reproduz o crosswalk ANTIGO (duplicativo: a contagem
    inteira da tarefa em cada SOC que a contém). Com weight_col ("w_frac" ou
    "w_unif"), cada tarefa é repartida entre os SOCs — melhoria 7."""
    m = onet.merge(task_df, on="task", how="left").fillna(
        {"usage": 0.0, "auto": 0.0, "classified": 0.0})
    if weight_col is not None:
        for c in ("usage", "auto", "classified"):
            m[c] = m[c] * m[weight_col]
    soc = m.groupby("SOC", as_index=False)[["usage", "auto", "classified"]].sum()
    cps = (xwalk.merge(soc, on="SOC", how="inner")
                .groupby("CPS_CODE", as_index=False)[["usage", "auto", "classified"]]
                .sum().rename(columns={"CPS_CODE": "OCC"}))
    cps["automation_share"] = np.where(
        cps["classified"] > 0, cps["auto"] / cps["classified"], np.nan)
    return cps[["OCC", "usage", "classified", "automation_share"]]


def match_rate(task_df, onet, label, lines):
    """% do uso do release cujas tarefas casam com o universo O*NET (por texto).

    Guarda-corpo do vintage: V5 usa O*NET-SOC 2019; se a redação das tarefas
    tivesse mudado a ponto de quebrar o merge, a taxa cairia aqui."""
    uni = set(onet["task"])
    m = task_df["task"].isin(uni)
    rate_t = m.mean()
    rate_u = task_df.loc[m, "usage"].sum() / task_df["usage"].sum()
    lines.append(f"| {label} | {100 * rate_t:.1f}% | {100 * rate_u:.1f}% |")
    print(f"[2] match {label}: {100 * rate_t:.1f}% das tarefas | "
          f"{100 * rate_u:.1f}% do uso")
    return rate_u


def zscore(s):
    return (s - s.mean()) / s.std(ddof=1)


def tail_stats(collab, label, lines):
    """Concentração de cauda no nível TAREFA (motivação do limiar de robustez)."""
    u = collab["usage"].sort_values(ascending=False)
    n5 = max(1, int(np.ceil(0.05 * len(u))))
    top5 = u.iloc[:n5].sum() / u.sum()
    med = collab["classified"].median()
    below = (collab["classified"] < 15).mean()
    lines.append(
        f"| {label} | {len(u):,} | {100 * top5:.1f}% | {med:,.0f} | "
        f"{100 * below:.1f}% |")
    print(f"[2] cauda {label}: top-5% das tarefas = {100 * top5:.1f}% do uso "
          f"| mediana classificadas/tarefa = {med:,.0f} "
          f"| tarefas <15 classificadas = {100 * below:.1f}%")


def occ_doses(tag, glob_tasks, us_tasks, onet, xwalk, emp, us_fallback,
              weight_col="w_frac"):
    """Doses por ocupação de uma entidade (release individual ou pooled).

    weight_col: "w_frac" (CORE — crosswalk fracionário por importância,
    melhoria 7), "w_unif" (fracionário uniforme) ou None (crosswalk antigo,
    duplicativo)."""
    cps_g = to_cps(glob_tasks, onet, xwalk, weight_col)
    cps_u = to_cps(us_tasks, onet, xwalk, weight_col)
    out = cps_g.rename(columns={
        "usage": f"total_usage_global_{tag}",
        "classified": f"classified_global_{tag}",
        "automation_share": f"automation_share_global_{tag}"}).merge(
        cps_u.rename(columns={
            "usage": f"total_usage_US_{tag}",
            "classified": f"classified_US_{tag}",
            "automation_share": f"automation_share_US_{tag}"}),
        on="OCC", how="outer")
    if us_fallback:
        out[f"automation_share_US_{tag}"] = out[f"automation_share_global_{tag}"]
        out[f"classified_US_{tag}"] = out[f"classified_global_{tag}"]
    out = out.merge(emp, on="OCC", how="inner")
    for g in ("global", "US"):
        pc = out[f"total_usage_{g}_{tag}"] / out["emp_pretreat_2019_2022"]
        # log puro (invariante de unidade do denominador); uso 0 -> NaN.
        # Ver "TRANSFORMAÇÃO DA ADOÇÃO" no docstring.
        out[f"usage_z_{g}_{tag}"] = zscore(np.log(pc.where(pc > 0)))
        out[f"automation_z_{g}_{tag}"] = zscore(out[f"automation_share_{g}_{tag}"])
    return out.drop(columns=["emp_pretreat_2019_2022"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-classified", type=int, default=50,
                    help="limiar de ROBUSTEZ (não é o core): mínimo de "
                         "conversas classificadas agregadas por ocupação "
                         "(SE da share ≈7 p.p. em n=50)")
    args = ap.parse_args()

    frames = {tag: path for tag, (path, _) in RELEASES.items()
              if path.exists() and path.stat().st_size > 1_000_000}
    for tag in RELEASES:
        if tag not in frames:
            print(f"[2] AVISO: {RELEASES[tag][0].name} ausente — release "
                  f"{tag} fora desta rodada (rodar 07 antes).")
    if "v3" not in frames:
        sys.exit("[2] aux_data do V3 ausente — rodar 07 antes.")



    onet = load_onet_universe()
    xwalk = load_xwalk()
    onet, soc_diag = harmonize_socs(onet, xwalk)
    print(f"[2] O*NET harmonizado: {len(onet):,} pares tarefa×SOC | "
          f"{onet['SOC'].nunique()} SOCs | "
          f"{len(soc_diag['unresolved'])} SOCs sem correspondência no crosswalk")

    # ---- melhoria 7 (P4): pesos do crosswalk fracionário ---------------------
    onet, w_diag = build_frac_weights(onet)
    n_socs_multi_cps = int(
        (xwalk.groupby("SOC")["CPS_CODE"].nunique() > 1).sum())
    print(f"[2] crosswalk fracionário: {w_diag.get('rated_pairs', 0):,}/"
          f"{w_diag['n_pairs']:,} pares (SOC, tarefa) com IM própria; "
          f"{w_diag.get('n_tasks_shared', 0):,}/{w_diag.get('n_tasks', 0):,} "
          f"tarefas em >1 SOC | SOCs mapeados a >1 código CPS: {n_socs_multi_cps}")

    emp = pd.read_csv(comum.DADOS / "emp_pretreat_por_ocupacao.csv")
    usecols = ["geography", "geo_id", "facet", "variable", "cluster_name",
               "value", "platform_and_product"]
    diag_tail = ["| release | tarefas publicadas | uso no top-5% de tarefas | "
                 "mediana de conversas classificadas por tarefa | tarefas com "
                 "<15 classificadas |", "|---|---|---|---|---|"]
    diag_match = ["| release | tarefas casadas com o universo O*NET | % do uso "
                  "casado |", "|---|---|---|"]
    agg_lines = ["| release | automação agregada US | global |", "|---|---|---|"]

    glob_by_rel, us_by_rel, fallback_by_rel = {}, {}, {}
    for tag, path in frames.items():
        print(f"[2] === release {tag} ({RELEASES[tag][1]}): {path.name} ===")
        df = pd.read_csv(path, usecols=lambda c: c in usecols, low_memory=False)
        if "platform_and_product" in df.columns:
            plats = sorted(df["platform_and_product"].dropna().unique())
            print(f"[2] {tag}: superfícies = {plats}")
        agg = country_agg_automation(df, tag)
        agg_lines.append(f"| {tag} | {agg.get('US', np.nan):.3f} | "
                         f"{agg.get('global', np.nan):.3f} |")
        glob = load_collab(df, df["geography"].eq("global"), f"{tag} GLOBAL")
        if glob is None:
            sys.exit(f"[2] {tag}: sem faceta global de colaboração.")
        tail_stats(glob, tag, diag_tail)
        rate = match_rate(glob, onet, tag, diag_match)
        if rate < MIN_MATCH:
            print(f"[2] AVISO: match de {tag} abaixo de {MIN_MATCH:.0%} — "
                  "release EXCLUÍDO do pooling (vintage O*NET incompatível?).")
            continue
        us_collab = load_collab(
            df, df["geography"].eq("country")
            & df["geo_id"].astype(str).isin(["US", "USA"]), f"{tag} US")
        us_fallback = us_collab is None
        if us_fallback:
            us = load_us_task_counts(df, f"{tag} US (contagens simples)")
            if us is None:
                sys.exit(f"[2] {tag}: nenhuma faceta onet_task p/ US.")
            print(f"[2] {tag}: US usa contagens onet_task simples; automação "
                  "US herda a composição GLOBAL (declarar no relatório).")
        else:
            us = us_collab
        glob_by_rel[tag], us_by_rel[tag] = glob, us
        fallback_by_rel[tag] = us_fallback
        del df

    # ---- doses por release + POOLED (soma de contagens) ----------------------
    out = None
    for tag in glob_by_rel:
        d = occ_doses(tag, glob_by_rel[tag], us_by_rel[tag], onet, xwalk, emp,
                      fallback_by_rel[tag])
        d[f"us_automation_is_global_fallback_{tag}"] = fallback_by_rel[tag]
        out = d if out is None else out.merge(d, on="OCC", how="outer")

    pooled_tags = list(glob_by_rel)
    cols = ["usage", "auto", "classified"]
    glob_pool = (pd.concat(glob_by_rel.values())
                 .groupby("task", as_index=False)[cols].sum())
    us_pool = (pd.concat(us_by_rel.values())
               .groupby("task", as_index=False)[cols].sum(min_count=1))
    pool_fallback = any(fallback_by_rel.values())
    print(f"[2] POOLED ({'+'.join(pooled_tags)}): "
          f"{len(glob_pool)} tarefas globais | uso {glob_pool['usage'].sum():,.0f}")
    d = occ_doses("pooled", glob_pool, us_pool, onet, xwalk, emp, pool_fallback)
    d["us_automation_is_global_fallback_pooled"] = pool_fallback
    out = out.merge(d, on="OCC", how="outer")

    # ---- variantes do crosswalk na dose pooled (apêndice D) ------------------
    # pooled_dup  = crosswalk ANTIGO (duplicativo — contagem inteira em cada
    #               ocupação que compartilha a tarefa; era o core até o P4);
    # pooled_unif = fracionário SEM importância (repartição uniforme 1/N) —
    #               isola o efeito de fracionar do efeito de ponderar por IM.
    for vtag, wcol in (("pooled_dup", None), ("pooled_unif", "w_unif")):
        d = occ_doses(vtag, glob_pool, us_pool, onet, xwalk, emp,
                      pool_fallback, weight_col=wcol)
        out = out.merge(d, on="OCC", how="outer")

    # Pearson e a diferença média em d.p. vêm ANTES do Spearman de propósito:
    # a regressão usa o nível padronizado da dose, não o posto, então ordenação
    # preservada NÃO implica coeficiente preservado. Aqui o Spearman de 0,994
    # entre o fracionário e o duplicativo conviveu com 17% de deslocamento no
    # coeficiente de adoção e 33% no de interação (apêndice E.14 do relatório).
    diag_cw = ["| comparação | medida | Pearson | dif. média (d.p.) | "
               "dif. máx. (d.p.) | Spearman | % muda de quartil | N |",
               "|---|---|---|---|---|---|---|---|"]
    for va, vb, lab in (("pooled", "pooled_dup", "fracionário IM × duplicativo"),
                        ("pooled", "pooled_unif", "fracionário IM × uniforme"),
                        ("pooled_unif", "pooled_dup", "uniforme × duplicativo")):
        for meas, ca, cb in (
                ("adoção US", f"usage_z_US_{va}", f"usage_z_US_{vb}"),
                ("automação global", f"automation_z_global_{va}",
                 f"automation_z_global_{vb}")):
            pair = out[[ca, cb]].dropna()
            r = pair[ca].corr(pair[cb])
            dif = (pair[ca] - pair[cb]).abs()
            rho = pair[ca].corr(pair[cb], method="spearman")
            qa = pd.qcut(pair[ca].rank(method="first"), 4, labels=False)
            qb = pd.qcut(pair[cb].rank(method="first"), 4, labels=False)
            mig = (qa != qb).mean()
            diag_cw.append(f"| {lab} | {meas} | {r:.4f} | {dif.mean():.4f} | "
                           f"{dif.max():.3f} | {rho:.3f} | {100 * mig:.1f}% "
                           f"| {len(pair)} |")
            print(f"[2] crosswalk {lab} ({meas}): Pearson = {r:.4f} | "
                  f"dif. média = {dif.mean():.4f} d.p. (máx {dif.max():.3f}) | "
                  f"Spearman = {rho:.3f} | muda quartil = {100 * mig:.1f}% | "
                  f"N = {len(pair)}")

    # A dupla contagem que importa é a DIFERENCIAL entre ocupações: um fator
    # comum viraria constante aditiva no log e morreria no z-score da dose.
    infl = (out["total_usage_global_pooled_dup"]
            / out["total_usage_global_pooled"]).dropna()
    print(f"[2] inflação do duplicativo POR OCUPAÇÃO: mediana "
          f"{infl.median():.3f} | p90 {infl.quantile(0.9):.3f} | "
          f"máx {infl.max():.2f} — é a concentração, não o nível médio, que "
          f"desloca a dose")
    # conservação: o fracionário aloca cada conversa uma vez — o total no nível
    # CPS deve cair para ~o uso casado, contra a inflação do duplicativo.
    tot_frac = out["total_usage_global_pooled"].sum()
    tot_dup = out["total_usage_global_pooled_dup"].sum()
    tot_task = glob_pool["usage"].sum()
    # Uso que CASA com o universo O*NET — o denominador certo do "contada N
    # vezes": conversas cuja tarefa não está no universo nunca chegam ao nível
    # CPS, então incluí-las subestimaria a duplicação. É este o número citado
    # na Tabela A1 do relatório.
    tot_matched = glob_pool.loc[
        glob_pool["task"].isin(set(onet["task"])), "usage"].sum()
    print(f"[2] conservação de contagens (global pooled): tarefa-nível "
          f"{tot_task:,.0f} | casado ao universo {tot_matched:,.0f} | "
          f"CPS fracionário {tot_frac:,.0f} | CPS duplicativo {tot_dup:,.0f}")
    print(f"[2] dupla contagem do crosswalk antigo: cada conversa casada era "
          f"contada {tot_dup / tot_matched:.3f} vez no nível CPS "
          f"(o fracionário aloca {tot_frac / tot_matched:.3f}× — excede 1 só "
          f"porque {n_socs_multi_cps} SOCs mapeiam a >1 código CPS)")

    # ---- legado: nomes antigos = V3 (compatibilidade com resultados antigos) -
    for g in ("global", "US"):
        out[f"total_usage_{g}"] = out[f"total_usage_{g}_v3"]
        out[f"automation_share_{g}"] = out[f"automation_share_{g}_v3"]
        out[f"usage_z_{g}"] = out[f"usage_z_{g}_v3"]
        out[f"automation_z_{g}"] = out[f"automation_z_{g}_v3"]
    out["us_automation_is_global_fallback"] = \
        out["us_automation_is_global_fallback_v3"]

    # ---- robustez 1: limiar de conversas classificadas na dose pooled --------
    # O limiar mede RUÍDO AMOSTRAL da share, então conta conversas OBSERVADAS
    # atrás da ocupação — a contagem duplicativa (`_pooled_dup`), não a
    # fracionária: repartir uma conversa entre as ocupações que compartilham a
    # tarefa não a torna menos observada. Usar a contagem fracionária aqui
    # endureceria o limiar de forma silenciosa (÷N nas tarefas compartilhadas).
    n_min = args.min_classified
    n_col = "classified_global_pooled_dup"
    diag_filter = [f"| entidade | ocupações c/ share definida | excluídas pelo "
                   f"limiar ≥{n_min} | % do uso retido |", "|---|---|---|---|"]
    for g in ("global", "US"):
        share = out[f"automation_share_{g}_pooled"]
        keep = out[n_col] >= n_min
        out[f"automation_z_{g}_pooled_min{n_min}"] = zscore(share.where(keep))
        out[f"usage_z_{g}_pooled_min{n_min}"] = out[f"usage_z_{g}_pooled"]
    defined = out["automation_share_global_pooled"].notna()
    below = defined & (out[n_col] < n_min)
    kept_usage = (out.loc[defined & ~below, "total_usage_global_pooled"].sum()
                  / out.loc[defined, "total_usage_global_pooled"].sum())
    diag_filter.append(f"| pooled | {int(defined.sum())} | {int(below.sum())} "
                       f"({100 * below.sum() / defined.sum():.1f}%) | "
                       f"{100 * kept_usage:.1f}% |")
    print(f"[2] limiar de robustez ≥{n_min}: exclui {int(below.sum())} de "
          f"{int(defined.sum())} ocupações com share definida "
          f"({100 * kept_usage:.1f}% do uso retido)")

    # ---- robustez 2: média dos z-scores intra-release ------------------------
    if len(pooled_tags) >= 2:
        for g in ("global", "US"):
            uz = pd.concat([out[f"usage_z_{g}_{t}"] for t in pooled_tags],
                           axis=1)
            az = pd.concat([out[f"automation_z_{g}_{t}"] for t in pooled_tags],
                           axis=1)
            out[f"usage_z_{g}_zmean"] = zscore(uz.mean(axis=1))
            out[f"automation_z_{g}_zmean"] = zscore(
                az.mean(axis=1).where(az.notna().sum(axis=1) >= 2))
        cmp = out[["automation_z_global_pooled",
                   "automation_z_global_zmean"]].dropna()
        print(f"[2] pooled (contagens) × zmean: Spearman = "
              f"{cmp.iloc[:, 0].corr(cmp.iloc[:, 1], method='spearman'):.4f} "
              f"(N={len(cmp)}) — os dois métodos de agregação coincidem?")

    # ---- estabilidade entre releases (protocolo Yin & Ogut, nossas doses) ----
    diag_stab = ["| medida | par | Spearman | % muda de quartil | N |",
                 "|---|---|---|---|---|"]
    for a, b in combinations(pooled_tags, 2):
        for label, ca, cb, extra in [
                ("adoção US (log pc)", f"usage_z_US_{a}", f"usage_z_US_{b}",
                 None),
                ("automação global", f"automation_z_global_{a}",
                 f"automation_z_global_{b}", None),
                (f"automação global (≥{n_min}/release)",
                 f"automation_share_global_{a}", f"automation_share_global_{b}",
                 (f"classified_global_{a}", f"classified_global_{b}"))]:
            if extra:
                pair = pd.DataFrame({
                    "a": out[ca].where(out[extra[0]] >= n_min),
                    "b": out[cb].where(out[extra[1]] >= n_min)}).dropna()
            else:
                pair = out[[ca, cb]].dropna().rename(
                    columns={ca: "a", cb: "b"})
            if len(pair) < 10:
                continue
            rho = pair["a"].corr(pair["b"], method="spearman")
            qa = pd.qcut(pair["a"].rank(method="first"), 4, labels=False)
            qb = pd.qcut(pair["b"].rank(method="first"), 4, labels=False)
            mig = (qa != qb).mean()
            diag_stab.append(f"| {label} | {a}×{b} | {rho:.3f} | "
                             f"{100 * mig:.1f}% | {len(pair)} |")
            print(f"[2] estabilidade {label} {a}×{b}: Spearman = {rho:.3f} "
                  f"| muda quartil = {100 * mig:.1f}% | N = {len(pair)}")

    for tag in ("v3", "pooled"):
        c1, c2 = f"usage_z_US_{tag}", f"automation_z_US_{tag}"
        print(f"[2] cor(u,a) {tag} = {out[c1].corr(out[c2]):.4f} "
              "(verificar ortogonalidade — premissa da spec aditiva)")

    out = out.merge(emp, on="OCC", how="inner")
    dest = comum.DOSES_CSV
    out.to_csv(dest, index=False)
    print(f"[2] {dest.name}: {len(out)} ocupações | {len(out.columns)} colunas.")

    diag = ["# Diagnóstico 07b — releases, pooling e estabilidade",
            "",
            "Entidades: " + "; ".join(
                f"{t} = {RELEASES[t][1]}" for t in pooled_tags) +
            f"; pooled = soma das contagens ({'+'.join(pooled_tags)}), "
            "procedimento de Massenkoff e McCrory (2026). Core sem exclusão "
            "além da censura da fonte (célula-tarefa ≥15 conversas); limiar "
            f"≥{n_min} e média de z-scores intra-release como robustez.",
            "", "## Concentração de cauda (nível tarefa)", "", *diag_tail, "",
            "## Match tarefa→universo O*NET (guarda-corpo de vintage)", "",
            *diag_match, "",
            "## Automação agregada por geografia (conferência da Tabela A2)", "",
            *agg_lines, "",
            "## Limiar de robustez (nível ocupação, dose pooled)", "",
            *diag_filter,
            f"O limiar conta conversas OBSERVADAS (contagem duplicativa "
            f"`{n_col}`): fracionar a alocação de uma conversa entre ocupações "
            "não a torna menos observada, e usar a contagem fracionária "
            "endureceria o limiar sem que ninguém decidisse isso.", "",
            "## Crosswalk fracionário por importância (melhoria 7 / P4)", "",
            "O mapeamento tarefa→ocupação é 1-para-muitos. Até o P4, a contagem "
            "de conversas de uma tarefa compartilhada entrava INTEIRA em cada "
            "ocupação que a contém (não-injetividade — limitação 5). O core "
            "agora reparte cada conversa uma única vez entre essas ocupações, "
            "proporcionalmente à **importância** da tarefa em cada uma (O*NET "
            "Task Ratings, escala IM). `pooled_unif` reparte em partes iguais "
            "(1/N) e isola o efeito de *fracionar* do de *ponderar por "
            "importância*; `pooled_dup` é a construção antiga.", "",
            f"Cobertura: {w_diag.get('rated_pairs', 0):,} de "
            f"{w_diag['n_pairs']:,} pares (ocupação, tarefa) têm nota de "
            f"importância própria; {w_diag.get('n_tasks_shared', 0):,} de "
            f"{w_diag.get('n_tasks', 0):,} tarefas são compartilhadas por mais "
            "de uma ocupação (só nelas o peso muda algo). Pares sem nota herdam "
            "a média da própria tarefa; tarefas sem nota alguma caem na "
            "repartição uniforme.", "",
            *diag_cw,
            "Pearson e a diferença média em desvios-padrão vêm antes do "
            "Spearman de propósito: a regressão usa o nível padronizado da "
            "dose, não o posto, então ordenação preservada não implica "
            "coeficiente preservado.", "",
            f"Conservação: das {tot_task:,.0f} conversas no nível tarefa, "
            f"{tot_matched:,.0f} casam com o universo O*NET e chegam ao nível "
            f"CPS. O crosswalk antigo as transformava em {tot_dup:,.0f} — cada "
            f"conversa casada contada **{tot_dup / tot_matched:.2f} vez**, que "
            "é a dupla contagem que o P4 remove. O fracionário aloca "
            f"{tot_frac:,.0f} ({tot_frac / tot_matched:.3f}×; excede 1 apenas "
            f"porque {n_socs_multi_cps} SOCs mapeiam a mais de um código CPS).",
            "",
            f"Essa inflação é concentrada, não difusa — por ocupação: mediana "
            f"{infl.median():.3f}, p90 {infl.quantile(0.9):.3f}, máximo "
            f"{infl.max():.2f}. Um fator comum a todas as ocupações seria "
            "inócuo (viraria constante aditiva no log e morreria no z-score); "
            "é a concentração que desloca a dose.", "",
            "## Estabilidade da ordenação entre releases (Spearman/quartil)",
            "", *diag_stab, "",
            "Protocolo de estabilidade de Yin e Ogut (2026) aplicado às "
            "nossas doses. A migração de quartil concentra-se nas ocupações "
            "de poucas conversas — motivação do limiar de robustez.", ""]
    # Os dois argumentos são obrigatórios no Windows, e por motivos distintos:
    # sem `encoding` a gravação usa a página de código local, que não tem o "≥"
    # desta tabela e derruba o script; sem `newline` ela sai em CRLF, e o
    # arquivo deixa de ser comparável byte a byte com o que está versionado.
    (comum.TAB_DIR / "tab07b_diagnostico_releases.md").write_text(
        "\n".join(diag), encoding="utf-8", newline="\n")
    print("[2] diagnóstico → tables/tab07b_diagnostico_releases.md "
          "(Tabelas A1, A2 e A3 do relatório)")


if __name__ == "__main__":
    main()
