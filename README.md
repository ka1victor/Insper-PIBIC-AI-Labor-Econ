# IA generativa e o mercado de trabalho americano

Pacote de replicação da Iniciação Científica (PIBIC/Insper). O trabalho mede o efeito
do uso de modelos de linguagem sobre o salário e o desemprego relativos das ocupações
americanas, decompondo "exposição à IA" em duas dimensões que a literatura costuma
somar num número só: **uso**, o quanto a ocupação usa IA, e **automação**, que fração
desse uso substitui o trabalhador em vez de auxiliá-lo.

Estimadas em conjunto, as duas puxam os salários em direções opostas, e é esse
componente negativo, escondido dentro de um saldo positivo, que a medida única não
mostra. O desemprego não se move, e o relatório explica por que esse zero é ausência
de evidência e não evidência de ausência.

**Autor:** Kauã Victor Dias dos Santos · **Orientador:** Prof. Thomas Victor Conti ·
**Coorientador:** Prof. Naércio Aquino Menezes Filho

Aqui estão o código, os dados derivados e a documentação de método: é o que permite
refazer e conferir os números. **O relatório em si não está neste repositório**, e as
tabelas que os scripts geram, em `analise/output/`, são o que ele imprime.

---

## Como reproduzir

```bash
pip install -r requirements.txt
python analise/src/03_quartis.py         # Figuras 1, 3 e 5, e as tabelas tab02
python analise/src/04_especificacao.py   # Tabelas 1 e 2, e as Figuras 2 e 4
python analise/src/05_ortogonalidade.py  # Figura A2
python analise/src/06_cadeia_metrica.py  # Figura A1
```

Esses quatro são independentes entre si, leem apenas o que está em `dados/` e
levam alguns minutos juntos. Não é preciso rede, nem acesso ao microdado do CPS.
Cada um sobrescreve arquivos de `analise/output/`, que já vêm no repositório:
rodar e comparar é a forma de conferir a reprodução.

Os passos 1 e 2 refazem a **métrica de uso** a partir da fonte primária, e só
eles precisam de rede:

```bash
python analise/src/01_baixa_insumos.py   # ~230 MB do AEI e do O*NET
python analise/src/02_metricas.py        # Tabelas A1, A2 e A3
```

São opcionais para quem só quer conferir os resultados, porque o
`dados/doses_por_ocupacao.csv` que eles produzem já está versionado e é dele que
os passos 3 a 6 partem. Rode-os para refazer a métrica do zero, ou para conferir
os números do apêndice A.

## O que cada script produz

| Script | O que sai | Onde aparece no relatório |
|---|---|---|
| `01_baixa_insumos.py` | os três relatórios do AEI, o universo de tarefas do O*NET e as notas de importância | (insumo do passo 2) |
| `02_metricas.py` | a métrica de uso por ocupação, mais o diagnóstico de repartição, geografia e estabilidade entre relatórios | Tabelas A1, A2 e A3 |
| `03_quartis.py` | event study por quarto de uso e por quarto de composição, com a média dos coeficientes posteriores ao evento e o diagnóstico de pré-tendência, nas tabelas `tab02` | Figuras 1, 3 e 5 |
| `04_especificacao.py` | a especificação do relatório: efeito médio de cada um dos três termos, pré-tendências em três janelas, efeito mínimo detectável e efeito marginal da composição por nível de uso | Tabelas 1 e 2, Figuras 2 e 4 |
| `05_ortogonalidade.py` | intensidade × fração contra os dois volumes, que é a evidência de por que a especificação tem a forma que tem | Figura A2 |
| `06_cadeia_metrica.py` | o diagrama da cadeia, da conversa do AEI à ocupação do painel | Figura A1 |

A Tabela A4, das limitações da métrica, não sai de script: ela tabula tamanhos
medidos por terceiros, com a fonte de cada um na própria tabela.

## Os dados

| Arquivo | O que é |
|---|---|
| `dados/panel.csv` | o painel: CPS por ocupação × mês, de jan/2010 a jun/2026, com o código de ocupação já harmonizado entre versões e o salário deflacionado para dólares de jan/2010, mesclado com as métricas de uso |
| `dados/doses_por_ocupacao.csv` | as métricas por ocupação, saída do passo 2, com as construções alternativas como colunas com sufixo |
| `dados/emp_pretreat_por_ocupacao.csv` | o emprego médio de 2019 a 2022, que é o denominador per capita da métrica |
| `dados/cps-ipums/cps_00008_ddi.xml` | a definição completa do extract do IPUMS: janela, variáveis e codificação |
| `dados/crosswalks/nem-occcode-cps-crosswalk.xlsx` | o crosswalk SOC → código do CPS, derivado da National Employment Matrix do BLS |

**O microdado do CPS/IPUMS não está aqui**, e não é escolha nossa: os termos de uso
que aceitamos ao baixar o extract proíbem redistribuí-lo. O que está no lugar são os
agregados de ocupação × mês, já no painel final que a análise de fato consome
(`dados/panel.csv`), mais a definição completa do extract no DDI, com a qual
qualquer pessoa o re-obtém de graça em [cps.ipums.org](https://cps.ipums.org).

**Os insumos de terceiros também não são versionados**, porque o passo 1 os baixa:
são cerca de 230 MB de dado público, do conjunto `Anthropic/EconomicIndex` no
Hugging Face e do banco do O*NET em `onetcenter.org`. O que está versionado é o que
sai deles, que é a métrica por ocupação.

## Além do que o relatório reporta

Este pacote é a versão enxuta: tem o código que produz o que está impresso no
relatório, e só. Ficam de fora dele, como ficam do relatório, os placebos em data
falsa, a análise de sensibilidade de Rambachan e Roth (2023), a réplica
independente de Chen *et al.* (2025) que valida o encanamento dos dados, e os
diagnósticos adicionais de identificação; a seção 5 do relatório aponta os dois
primeiros como passo seguinte para a margem de emprego. As dez construções
alternativas da métrica, essas, saem do passo 2: elas estão todas no
`dados/doses_por_ocupacao.csv`, como colunas com sufixo.

A derivação de cada decisão de construção da métrica, que é o que o apêndice A
resume em figuras e tabelas, está em [`docs/METRICA-AEI.md`](docs/METRICA-AEI.md).

## Uma nota sobre a reprodução

Os números deste pacote foram conferidos contra os do pipeline completo, linha a
linha, e batem. Três ressalvas honestas para quem for rodar:

Reexecutar a mesma regressão na mesma máquina pode mover o último dígito impresso,
porque a ordem de soma das bibliotecas de álgebra linear depende de quantas threads
elas usam. Vimos isso num p-valor, que foi de `1,05e-05` a `1,06e-05`, e em limites
de intervalo de confiança, que se moveram um centavo (de `+6,40` a `+6,39`). As
estimativas pontuais não se moveram em nenhuma execução, e nenhuma significância ou
conclusão do relatório depende disso. Se você rodar e vir esse tipo de diferença, é
esperado; diferença maior que essa não é.

O passo 2 é o mais sensível a insumo incompleto, e a falha é silenciosa: um "Task
Ratings" baixado pela metade deixa a maioria dos pares sem nota de importância, a
repartição cai no rateio uniforme, e a métrica sai ligeiramente diferente sem que
nada acuse erro. Aconteceu conosco. O passo 1 confere a integridade do que baixa
justamente por isso, e vale reler o que ele imprime antes de rodar o passo 2.

Os scripts imprimem acentuação e sinais matemáticos. No terminal do Windows, onde a
página de código padrão não é UTF-8, isso derruba a execução no meio: rode com
`set PYTHONIOENCODING=utf-8` antes, ou use `chcp 65001`.

## Referências

CHEN, Danqing; KANE, Carina; KOZLOWSKI, Austin; KUNIEVSKY, Nadav; EVANS, James A. **The (Short-Term) Effects of Large Language Models on Unemployment and Earnings**. arXiv:2509.15510, 19 set. 2025. DOI: 10.48550/arXiv.2509.15510. Disponível em: https://doi.org/10.48550/arXiv.2509.15510. Acesso em: 22 set. 2026.

RAMBACHAN, Ashesh; ROTH, Jonathan. A More Credible Approach to Parallel Trends. **The Review of Economic Studies**, v. 90, n. 5, p. 2555–2591, 2023. DOI: 10.1093/restud/rdad018. Disponível em: https://doi.org/10.1093/restud/rdad018. Acesso em: 22 set. 2026.
