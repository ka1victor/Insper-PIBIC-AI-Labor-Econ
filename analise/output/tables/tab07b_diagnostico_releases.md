# Diagnóstico 07b — releases, pooling e estabilidade

Entidades: v3 = 04–11/08/2025; v4 = 13–20/11/2025; v5 = 05–12/02/2026; pooled = soma das contagens (v3+v4+v5), procedimento de Massenkoff & McCrory (2026). Core sem exclusão além da censura da fonte (célula-tarefa ≥15 conversas); limiar ≥50 e média de z-scores intra-release como robustez.

## Concentração de cauda (nível tarefa)

| release | tarefas publicadas | uso no top-5% de tarefas | mediana de conversas classificadas por tarefa | tarefas com <15 classificadas |
|---|---|---|---|---|
| v3 | 2,617 | 67.7% | 39 | 30.9% |
| v4 | 3,169 | 68.6% | 32 | 34.1% |
| v5 | 3,259 | 65.5% | 36 | 32.5% |

## Match tarefa→universo O*NET (guarda-corpo de vintage)

| release | tarefas casadas com o universo O*NET | % do uso casado |
|---|---|---|
| v3 | 81.5% | 76.6% |
| v4 | 81.7% | 77.9% |
| v5 | 81.5% | 77.5% |

## Automação agregada por geografia (conferência do §4.3)

| release | automação agregada US | global |
|---|---|---|
| v3 | 0.491 | 0.511 |
| v4 | 0.449 | 0.467 |
| v5 | 0.414 | 0.455 |

## Limiar de robustez (nível ocupação, dose pooled)

| entidade | ocupações c/ share definida | excluídas pelo limiar ≥50 | % do uso retido |
|---|---|---|---|
| pooled | 371 | 36 (9.7%) | 99.8% |
O limiar conta conversas OBSERVADAS (contagem duplicativa `classified_global_pooled_dup`): fracionar a alocação de uma conversa entre ocupações não a torna menos observada, e usar a contagem fracionária endureceria o limiar sem que ninguém decidisse isso.

## Crosswalk fracionário por importância (melhoria 7 / P4)

O mapeamento tarefa→ocupação é 1-para-muitos. Até o P4, a contagem de conversas de uma tarefa compartilhada entrava INTEIRA em cada ocupação que a contém (não-injetividade — limitação 5). O core agora reparte cada conversa uma única vez entre essas ocupações, proporcionalmente à **importância** da tarefa em cada uma (O*NET Task Ratings, escala IM). `pooled_unif` reparte em partes iguais (1/N) e isola o efeito de *fracionar* do de *ponderar por importância*; `pooled_dup` é a construção antiga.

Cobertura: 17,309 de 18,321 pares (ocupação, tarefa) têm nota de importância própria; 325 de 17,176 tarefas são compartilhadas por mais de uma ocupação (só nelas o peso muda algo). Pares sem nota herdam a média da própria tarefa; tarefas sem nota alguma caem na repartição uniforme.

| comparação | medida | Pearson | dif. média (d.p.) | dif. máx. (d.p.) | Spearman | % muda de quartil | N |
|---|---|---|---|---|---|---|---|
| fracionário IM × duplicativo | adoção US | 0.9928 | 0.0462 | 1.052 | 0.994 | 3.0% | 331 |
| fracionário IM × duplicativo | automação global | 0.9996 | 0.0076 | 0.348 | 0.999 | 1.1% | 371 |
| fracionário IM × uniforme | adoção US | 1.0000 | 0.0003 | 0.020 | 1.000 | 0.0% | 331 |
| fracionário IM × uniforme | automação global | 1.0000 | 0.0001 | 0.011 | 1.000 | 0.0% | 371 |
| uniforme × duplicativo | adoção US | 0.9927 | 0.0463 | 1.073 | 0.994 | 3.0% | 331 |
| uniforme × duplicativo | automação global | 0.9995 | 0.0076 | 0.348 | 0.999 | 1.1% | 371 |
Pearson e a diferença média em desvios-padrão vêm antes do Spearman de propósito: a regressão usa o nível padronizado da dose, não o posto, então ordenação preservada não implica coeficiente preservado.

Conservação: das 2,886,021 conversas no nível tarefa, 2,233,043 casam com o universo O*NET e chegam ao nível CPS. O crosswalk antigo as transformava em 3,311,933 — cada conversa casada contada **1.48 vez**, que é a dupla contagem que o P4 remove. O fracionário aloca 2,254,752 (1.010×; excede 1 apenas porque 3 SOCs mapeiam a mais de um código CPS).

Essa inflação é concentrada, não difusa — por ocupação: mediana 1.000, p90 1.023, máximo 6.30. Um fator comum a todas as ocupações seria inócuo (viraria constante aditiva no log e morreria no z-score); é a concentração que desloca a dose.

## Estabilidade da ordenação entre releases (Spearman/quartil)

| medida | par | Spearman | % muda de quartil | N |
|---|---|---|---|---|
| adoção US (log pc) | v3×v4 | 0.945 | 19.8% | 268 |
| automação global | v3×v4 | 0.707 | 37.5% | 315 |
| automação global (≥50/release) | v3×v4 | 0.834 | 35.8% | 254 |
| adoção US (log pc) | v3×v5 | 0.931 | 28.2% | 273 |
| automação global | v3×v5 | 0.761 | 41.0% | 312 |
| automação global (≥50/release) | v3×v5 | 0.848 | 39.7% | 257 |
| adoção US (log pc) | v4×v5 | 0.983 | 14.6% | 287 |
| automação global | v4×v5 | 0.813 | 35.0% | 331 |
| automação global (≥50/release) | v4×v5 | 0.884 | 32.9% | 277 |

Protocolo de estabilidade de Yin & Ogut (2026) aplicado às nossas doses. A migração de quartil concentra-se nas ocupações de poucas conversas — motivação do limiar de robustez.
