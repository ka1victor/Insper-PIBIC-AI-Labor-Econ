# Tabela 02 — Média dos coeficientes posteriores a nov/2022 por quarto (vs. Q1)

Quartos cortados por: intensidade do uso

Ocupações: 322 | células: 54794

| Quarto | Desemprego (pontos de taxa) [IC 95%] | Salário (US$/sem) [IC 95%] |
|---|---:|---:|
| Q2 | +0.0010 [-0.0056; +0.0076] | +104.31 [+6.40; +202.22] |
| Q3 | +0.0023 [-0.0035; +0.0080] | +173.83 [+53.79; +293.86] |
| Q4 | +0.0024 [-0.0078; +0.0127] | +169.07 [+105.89; +232.25] |
| Q4 − Q3 | +0.0002 (e.p. 0.0052) | -4.75 (e.p. 66.96) |

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
| Desemprego (pontos de taxa) | 0.000342 | 0.0073 | +0.0024 | 0.33 | +0.00015 (0.51) |
| Salário (US$/sem) | 2.27e-05 | 72.4655 | +169.0710 | 2.33 | -1.88567 (0.0011) |

Razão abaixo de 1 significa que as oscilações anteriores ao evento são maiores
que o efeito que se quer medir: ali o desfecho não é testado por este desenho, o
que é conclusão diferente de não haver efeito.
