"""Utilitários compartilhados pelos quatro scripts deste pacote.

Convenções que valem em todos eles, e que o relatório declara:

1. DADOS. Tudo sai de `dados/panel.csv` (CPS por ocupação × mês, 2010-01→2026-06,
   com o vintage de código de ocupação já harmonizado e o salário já deflacionado)
   e de `dados/doses_por_ocupacao.csv` (as métricas de uso por ocupação,
   construídas do Anthropic Economic Index).

2. AS DUAS MÉTRICAS, por ocupação e fixas no tempo:
     uso        u_i = intensidade de uso, conversas por trabalhador, em log
     automação  a_i = fração do uso classificada como substitutiva
   Padronizadas (z-score) entre ocupações, de modo que o coeficiente é o efeito
   de um desvio-padrão.

3. EVENTO. rel_time = 0 ⇔ nov/2022 (lançamento do ChatGPT); a categoria omitida
   do event study é k = −1 (out/2022, o último mês anterior).

4. PESOS. Toda regressão é WLS com peso igual ao tamanho da célula do CPS
   (`n_earnings_obs` para salários, `total_labor_force` para desemprego). É peso
   de precisão, e não de tratamento.

5. INFERÊNCIA. Erro-padrão agrupado por ocupação (CRV1), que é o nível em que a
   métrica de tratamento varia.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "dados"
PAINEL_CSV = DADOS / "panel.csv"
DOSES_CSV = DADOS / "doses_por_ocupacao.csv"

SAIDA = RAIZ / "analise" / "output"
FIG_DIR = SAIDA / "figures"
TAB_DIR = SAIDA / "tables"
for _d in (FIG_DIR, TAB_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# A métrica do paper: os três relatórios do AEI somados, recorte americano.
METRICA = "US_pooled"

EVENT_REF = -1   # categoria omitida do event study: k = -1 (out/2022)
K_COVID = -32    # mar/2020, para a linha vertical das figuras
K_JUROS = -8     # mar/2022, início do aperto de juros do Fed


# --------------------------------------------------------------------------
# Carregamento
# --------------------------------------------------------------------------
def carrega_doses(so_uso: bool = False) -> pd.DataFrame:
    """As métricas por ocupação, repadronizadas na amostra que sai daqui.

    `so_uso=True` devolve apenas a intensidade e exige apenas ela não-nula, o que
    dá uma amostra maior: a composição só existe para as ocupações cujo uso a
    fonte publica com detalhe suficiente.

    A repadronização importa e não é cosmética. O arquivo traz cada métrica
    padronizada sobre todas as ocupações em que ela existe, e esses conjuntos não
    coincidem: a composição vinha de um conjunto maior, cujas ocupações de poucas
    conversas têm fração ruidosa e desvio-padrão alto. Sem repadronizar, "um
    desvio-padrão de automação" e "um desvio-padrão de uso" não seriam a mesma
    unidade, e a comparação entre os dois coeficientes não seria de igual para
    igual. É reescalonamento puro: t, p-valor e valores ajustados não mudam.
    """
    d = pd.read_csv(DOSES_CSV)
    cols = {f"usage_z_{METRICA}": "usage_z", f"automation_z_{METRICA}": "automation_z"}
    faltando = [c for c in cols if c not in d.columns]
    if faltando:
        raise SystemExit(f"colunas ausentes no arquivo de métricas: {faltando}")
    d = d[["OCC", *cols]].rename(columns=cols)
    d = d[["OCC", "usage_z"]].dropna() if so_uso else d.dropna()
    return repadroniza(d)


def repadroniza(d: pd.DataFrame) -> pd.DataFrame:
    """Z-score das métricas na amostra recebida. Ver `carrega_doses`."""
    d = d.copy()
    for c in ("usage_z", "automation_z"):
        if c in d.columns:
            d[c] = (d[c] - d[c].mean()) / d[c].std(ddof=1)
    return d


def carrega_painel(doses: pd.DataFrame) -> pd.DataFrame:
    """Painel do CPS mesclado com as métricas, só nas ocupações que têm as duas."""
    df = pd.read_csv(PAINEL_CSV)
    df = df[df["OCC"] > 0]
    df = df.merge(doses, on="OCC", how="inner")
    df["post"] = (df["rel_time"] >= 0).astype(float)
    return df


# --------------------------------------------------------------------------
# Leitura dos coeficientes de event study
# --------------------------------------------------------------------------
def extrai_k(nome_do_coef: str):
    """Extrai o tempo relativo k do nome do coeficiente que o pyfixest devolve."""
    m = re.search(r"\[T\.(-?\d+)(?:\.0)?\]", nome_do_coef)
    if m is None:
        m = re.search(r"::(-?\d+)(?:\.0)?", nome_do_coef)
    return int(m.group(1)) if m else None


def es_coefs(modelo, token: str) -> pd.DataFrame:
    """DataFrame (k, est, se) da série de event study de um termo."""
    linhas = []
    se = modelo.se()
    for nm, est in modelo.coef().items():
        if "rel_time" not in nm or (token and token not in nm):
            continue
        k = extrai_k(nm)
        if k is None:
            continue
        linhas.append({"k": k, "est": est, "se": se[nm]})
    out = pd.DataFrame(linhas).sort_values("k").reset_index(drop=True)
    # o ponto de referência (k = -1) é normalizado a zero e não tem coeficiente
    out = pd.concat([out, pd.DataFrame([{"k": EVENT_REF, "est": 0.0, "se": 0.0}])])
    return out.sort_values("k").reset_index(drop=True)


def combinacao(modelo, pesos):
    """Estimativa e erro-padrão de c'β, com o vcov agrupado do modelo.

    É assim que uma média de coeficientes mensais ganha erro-padrão. Tirar a
    média dos erros-padrão daria número errado, porque ignora a covariância entre
    os coeficientes, que aqui é grande: todos compartilham o mês de referência.
    """
    b = modelo.coef().to_numpy()
    V = np.asarray(modelo._vcov)
    c = np.zeros(len(b))
    for i, w in pesos:
        c[i] = w
    return float(c @ b), float(np.sqrt(c @ V @ c))


def estrelas(est, se):
    from scipy import stats
    if se <= 0:
        return ""
    p = 2 * stats.norm.sf(abs(est / se))
    return "\\*\\*\\*" if p < 0.001 else "\\*\\*" if p < 0.01 else "\\*" if p < 0.05 else ""


# --------------------------------------------------------------------------
# Diagnóstico de pré-tendência
# --------------------------------------------------------------------------
def wald_pretendencia(modelo, token: str, k_min: int, k_max: int = -2):
    """Wald conjunto de H0: coeficientes anteriores ao evento = 0 em [k_min, k_max].

    Monta W = b' V^-1 b ~ χ²(len(b)) com o vcov agrupado do próprio modelo, de
    modo que a covariância entre os coeficientes mensais entra no teste.
    """
    from scipy import stats

    nomes = list(modelo.coef().index)
    sel, ks = [], []
    for i, nm in enumerate(nomes):
        if "rel_time" not in nm or (token and token not in nm):
            continue
        k = extrai_k(nm)
        if k is not None and k_min <= k <= k_max:
            sel.append(i)
            ks.append(k)
    b = modelo.coef().to_numpy()[sel]
    V = np.asarray(modelo._vcov)[np.ix_(sel, sel)]
    W = float(b @ np.linalg.solve(V, b))
    return {"chi2": W, "df": len(b), "p": float(stats.chi2.sf(W, len(b))),
            "k_range": (min(ks), max(ks))}


def inclinacao_pretendencia(modelo, token: str, k_min: int, k_max: int = -2):
    """Inclinação dos coeficientes anteriores ao evento contra o tempo, por GLS.

    Existe porque o Wald e a escala não perguntam a mesma coisa que a direção. O
    Wald pergunta se os coeficientes anteriores são zero, e a escala pergunta se
    são pequenos perto do efeito. Nenhum dos dois pergunta se eles têm direção, e
    é a direção que ameaça o contrafactual: coeficientes deslocados de zero mas
    sem tendência dizem que o mês de referência é atípico, enquanto coeficientes
    em tendência dizem que as trajetórias já divergiam antes do evento.
    """
    from scipy import stats

    nomes = list(modelo.coef().index)
    sel, ks = [], []
    for i, nm in enumerate(nomes):
        if "rel_time" not in nm or (token and token not in nm):
            continue
        k = extrai_k(nm)
        if k is not None and k_min <= k <= k_max:
            sel.append(i)
            ks.append(float(k))
    b = modelo.coef().to_numpy()[sel]
    V = np.asarray(modelo._vcov)[np.ix_(sel, sel)]
    X = np.column_stack([np.ones(len(ks)), np.asarray(ks)])
    Vi = np.linalg.pinv(V)
    A = np.linalg.pinv(X.T @ Vi @ X)
    theta = A @ (X.T @ Vi @ b)
    se = np.sqrt(np.diag(A))
    z = theta[1] / se[1]
    return {"nivel": float(theta[0]), "inclinacao": float(theta[1]),
            "se_inclinacao": float(se[1]),
            "p": float(2 * stats.norm.sf(abs(z))), "n": len(ks)}


# --------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------
def k_para_data(k) -> pd.Timestamp:
    """k = 0 ⇔ nov/2022."""
    idx = 2022 * 12 + 10 + int(k)
    y, m = divmod(idx, 12)
    return pd.Timestamp(y, m + 1, 1)


# O rodapé traz só a referência. O significado das três linhas verticais
# (mar/2020, pandemia; mar/2022, juros; nov/2022, ChatGPT, em vermelho) está na
# Nota de cada figura no relatório: a frase inteira não cabe na largura da
# página num corpo legível.
NOTA_FIG = "Referência: Out/2022"


def eixos_es(ax, rotulo_y: str):
    """Linhas de marco e formatação comum das figuras de event study."""
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(k_para_data(K_COVID), color="grey", ls=":", lw=0.9)
    ax.axvline(k_para_data(K_JUROS), color="grey", ls="--", lw=0.9)
    ax.axvline(k_para_data(0), color="red", lw=1.1)
    ax.set_xlabel("Ano")
    ax.set_ylabel(rotulo_y)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def rodape(fig):
    fig.text(0.99, 0.01, NOTA_FIG, ha="right", va="bottom", fontsize=9.5,
             color="0.25")
