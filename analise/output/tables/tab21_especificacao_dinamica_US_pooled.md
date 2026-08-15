# Tabela 21 — a especificação dinâmica de três termos

Uma única regressão por desfecho: u, a e u×a, cada um interagido com as dummies
de mês, com efeitos fixos de ocupação e de mês, WLS pelo tamanho da célula e
erros-padrão agrupados por ocupação.

Ocupações: 321 | células: 54717

## Salário (US$/sem)

Células: 52823 | ocupações: 321

**Colinearidade dos três regressores**, no peso que a WLS usa. A ortogonalidade
que justifica a troca de coordenadas é entre u e a; o produto u·a não é
ortogonal a a, e é o VIF que diz se isso atrapalha:

| par | correlação ponderada |
|---|---:|
| u × a | -0.046 |
| u × u·a | -0.022 |
| a × u·a | -0.599 |

| regressor | VIF |
|---|---:|
| u | 1.01 |
| a | 1.57 |
| u·a | 1.56 |

**Efeito médio pós-tratamento por termo** — média dos coeficientes de k ≥ 0,
com o erro-padrão da combinação linear (c'Vc, vcov agrupado):

| Termo | efeito médio pós | e.p. | n coefs |
|---|---:|---:|---:|
| Uso (*u*) | +66.4\*\*\* | (12.5) | 43 |
| Automação (*a*) | -102.8\*\* | (35.2) | 43 |
| Interação (*u·a*) | -53.3\*\* | (18.5) | 43 |

**Efeito mínimo detectável (MDE) por termo** — 2,8 × e.p., que é o menor
efeito verdadeiro que este desenho rejeitaria em 80% das amostras a 5% de
significância:

| Termo | e.p. | MDE (80% de potência) |
|---|---:|---:|
| Uso (*u*) | (12.5) | 35.1 |
| Automação (*a*) | (35.2) | 98.6 |
| Interação (*u·a*) | (18.5) | 51.9 |

**Diagnóstico de pré-tendência por termo** — mesmo modelo e mesmos
coeficientes; muda só quais meses entram no teste:

| Termo | Janela | p (Wald) | \|pré\| médio | % indiv. sig. | efeito/violação |
|---|---|---:|---:|---:|---:|
| Uso (*u*) | 24m convencional (out/2020–set/2022) | 7.47e-05 | 16.91 | 46% | 3.93× |
| Uso (*u*) | 24m pré-pandemia (mar/2018–fev/2020) | 3.45e-05 | 13.99 | 25% | 4.75× |
| Uso (*u*) | 2022, pós-fase-aguda (dez/2021–set/2022) | 0.0248 | 13.11 | 30% | 5.06× |
| Automação (*a*) | 24m convencional (out/2020–set/2022) | 1.05e-05 | 17.6 | 17% | 5.84× |
| Automação (*a*) | 24m pré-pandemia (mar/2018–fev/2020) | 0.018 | 22.8 | 8% | 4.51× |
| Automação (*a*) | 2022, pós-fase-aguda (dez/2021–set/2022) | 0.0386 | 12.01 | 10% | 8.56× |
| Interação (*u·a*) | 24m convencional (out/2020–set/2022) | 2.91e-06 | 14.01 | 25% | 3.80× |
| Interação (*u·a*) | 24m pré-pandemia (mar/2018–fev/2020) | 0.00548 | 13.55 | 8% | 3.93× |
| Interação (*u·a*) | 2022, pós-fase-aguda (dez/2021–set/2022) | 0.00907 | 12.12 | 20% | 4.39× |

**Efeito marginal da composição, por nível de uso** — ∂y/∂a = γ + δ·u,
com o erro-padrão da mesma combinação linear. Os níveis cobrem o intervalo
observado de u, de -2.33 a +2.60 d.p.:

| nível de uso | ∂y/∂a | e.p. |
|---|---:|---:|
| u = -2.33 d.p.  ← mínimo observado | +21.2 | (20.6) |
| u = -1.93 d.p.  ← cruzamento de sinal | +0.0 | (17.3) |
| u = -1.00 d.p. | -49.6\* | (20.8) |
| u = +0.00 d.p. | -102.8\*\* | (35.2) |
| u = +1.00 d.p. | -156.1\*\* | (52.3) |
| u = +2.00 d.p. | -209.3\*\* | (70.1) |
| u = +2.60 d.p.  ← máximo observado | -241.3\*\* | (80.9) |

O sinal de ∂y/∂a cruza zero em u = -1.93 d.p., que está **dentro** do
intervalo observado: 6 das 321 ocupações (1.9%) ficam abaixo desse ponto. Ali a estimativa já
não se separa de zero, de modo que o cruzamento é a reta saindo do suporte,
e não penalidade medida com o sinal invertido.

**A forma contínua contra o recorte por quartos** — o que o coeficiente por
d.p. prevê para o contraste entre os quartos extremos, dado o vão entre eles.
A estimativa sem reta do mesmo contraste está na `tab02`:

| dimensão | coef./d.p. | vão Q4−Q1 (d.p.) | previsão da reta |
|---|---:|---:|---:|
| Intensidade (*u*) | +66.4 | 2.53 | +168.0 |
| Composição (*a*) | -102.8 | 2.44 | -251.4 |

Figura: `fig21_es_tres_series_salarios_US_pooled.png`

## Desemprego (p.p. na taxa)

Células: 54715 | ocupações: 321

**Colinearidade dos três regressores**, no peso que a WLS usa. A ortogonalidade
que justifica a troca de coordenadas é entre u e a; o produto u·a não é
ortogonal a a, e é o VIF que diz se isso atrapalha:

| par | correlação ponderada |
|---|---:|
| u × a | -0.020 |
| u × u·a | -0.055 |
| a × u·a | -0.605 |

| regressor | VIF |
|---|---:|
| u | 1.01 |
| a | 1.58 |
| u·a | 1.59 |

**Efeito médio pós-tratamento por termo** — média dos coeficientes de k ≥ 0,
com o erro-padrão da combinação linear (c'Vc, vcov agrupado):

| Termo | efeito médio pós | e.p. | n coefs |
|---|---:|---:|---:|
| Uso (*u*) | +0.06 | (0.17) | 43 |
| Automação (*a*) | +0.27 | (0.21) | 43 |
| Interação (*u·a*) | +0.07 | (0.17) | 43 |

**Efeito mínimo detectável (MDE) por termo** — 2,8 × e.p., que é o menor
efeito verdadeiro que este desenho rejeitaria em 80% das amostras a 5% de
significância:

| Termo | e.p. | MDE (80% de potência) |
|---|---:|---:|
| Uso (*u*) | (0.17) | 0.47 |
| Automação (*a*) | (0.21) | 0.59 |
| Interação (*u·a*) | (0.17) | 0.49 |

**Diagnóstico de pré-tendência por termo** — mesmo modelo e mesmos
coeficientes; muda só quais meses entram no teste:

| Termo | Janela | p (Wald) | \|pré\| médio | % indiv. sig. | efeito/violação |
|---|---|---:|---:|---:|---:|
| Uso (*u*) | 24m convencional (out/2020–set/2022) | 0.054 | 0.1992 | 8% | 0.32× |
| Uso (*u*) | 24m pré-pandemia (mar/2018–fev/2020) | 0.477 | 0.114 | 0% | 0.56× |
| Uso (*u*) | 2022, pós-fase-aguda (dez/2021–set/2022) | 0.733 | 0.127 | 0% | 0.51× |
| Automação (*a*) | 24m convencional (out/2020–set/2022) | 0.0148 | 0.5963 | 50% | 0.45× |
| Automação (*a*) | 24m pré-pandemia (mar/2018–fev/2020) | 0.314 | 0.2224 | 0% | 1.21× |
| Automação (*a*) | 2022, pós-fase-aguda (dez/2021–set/2022) | 0.136 | 0.2854 | 10% | 0.94× |
| Interação (*u·a*) | 24m convencional (out/2020–set/2022) | 0.0238 | 0.2027 | 4% | 0.32× |
| Interação (*u·a*) | 24m pré-pandemia (mar/2018–fev/2020) | 0.000245 | 0.1664 | 4% | 0.39× |
| Interação (*u·a*) | 2022, pós-fase-aguda (dez/2021–set/2022) | 0.98 | 0.1436 | 0% | 0.46× |

**Efeito marginal da composição, por nível de uso** — ∂y/∂a = γ + δ·u,
com o erro-padrão da mesma combinação linear. Os níveis cobrem o intervalo
observado de u, de -2.33 a +2.60 d.p.:

| nível de uso | ∂y/∂a | e.p. |
|---|---:|---:|
| u = -2.33 d.p.  ← mínimo observado | +0.12 | (0.32) |
| u = -1.00 d.p. | +0.20 | (0.17) |
| u = +0.00 d.p. | +0.27 | (0.21) |
| u = +1.00 d.p. | +0.33 | (0.35) |
| u = +2.00 d.p. | +0.40 | (0.51) |
| u = +2.60 d.p.  ← máximo observado | +0.44 | (0.61) |

O sinal de ∂y/∂a não cruza zero no intervalo observado de u.

**A forma contínua contra o recorte por quartos** — o que o coeficiente por
d.p. prevê para o contraste entre os quartos extremos, dado o vão entre eles.
A estimativa sem reta do mesmo contraste está na `tab02`:

| dimensão | coef./d.p. | vão Q4−Q1 (d.p.) | previsão da reta |
|---|---:|---:|---:|
| Intensidade (*u*) | +0.06 | 2.53 | +0.16 |
| Composição (*a*) | +0.27 | 2.44 | +0.66 |

Figura: `fig21_es_tres_series_desemprego_US_pooled.png`
