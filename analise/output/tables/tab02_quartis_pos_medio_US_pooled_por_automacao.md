# Tabela 02 — Média dos coeficientes posteriores a nov/2022 por quarto (vs. Q1)

Quartos cortados por: composição substitutiva do uso

Ocupações: 321 | células: 54717

| Quarto | Desemprego (pontos de taxa) [IC 95%] | Salário (US$/sem) [IC 95%] |
|---|---:|---:|
| Q2 | +0.0016 [-0.0043; +0.0074] | -10.60 [-153.44; +132.24] |
| Q3 | +0.0038 [-0.0033; +0.0108] | -132.39 [-261.77; -3.02] |
| Q4 | +0.0028 [-0.0057; +0.0112] | -148.08 [-273.60; -22.56] |
| Q4 − Q3 | -0.0010 (e.p. 0.0047) | -15.69 (e.p. 22.90) |

Leitura: a resposta que cresce com a métrica sustenta a especificação contínua
da seção 3.2; a ausência disso indicaria não-linearidade que a forma contínua
mascararia. A linha Q4 − Q3 é o teste do achatamento no topo: indistinguível de
zero significa que a resposta cresce e satura, em vez de crescer sem parar.

## Diagnóstico de pré-tendência da série Q4 (k = −25..−2)

Veredito de pré-teste não vai sozinho: com 24 coeficientes bem estimados o Wald
rejeita desvios economicamente irrelevantes, então quem decide são a escala das
violações e a direção da inclinação. Inclinação que corre contra o efeito
posterior não pode fabricá-lo, porque extrapolá-la preveria o oposto.

| Desfecho | Wald 24m (p) | Violação média | Efeito posterior | razão ef/viol | Inclinação (p) |
|---|---:|---:|---:|---:|---:|
| Desemprego (pontos de taxa) | 2.08e-06 | 0.0098 | +0.0028 | 0.28 | -0.00090 (1.4e-07) |
| Salário (US$/sem) | 0.0142 | 18.2165 | -148.0825 | 8.13 | +2.11475 (5.2e-05) |

Razão abaixo de 1 significa que as oscilações anteriores ao evento são maiores
que o efeito que se quer medir: ali o desfecho não é testado por este desenho, o
que é conclusão diferente de não haver efeito.

## Equilíbrio dos quartos na outra métrica do uso (intensidade)

Cortar por uma dimensão do uso deixa a outra solta? É a objeção que a seção
2.2 do relatório levanta contra os desenhos que ordenam por uma de cada vez.
Aqui ela é medida, e não argumentada.

| Quarto do corte | intensidade média (d.p.) | Ocupações |
|---|---:|---:|
| Q1 | -0.079 | 82 |
| Q2 | +0.200 | 80 |
| Q3 | -0.220 | 79 |
| Q4 | +0.017 | 80 |
| **Q4 − Q1** | **+0.096** (t = +0.60, p = 0.547) | 321 |

Correlação entre as duas métricas nesta amostra: -0.026. Quanto mais
perto de zero, mais o corte por uma delas preserva o equilíbrio na outra, e é
isso que separa a composição medida como fração da medida como nível, que
ordena as ocupações quase como a intensidade.
