# A métrica de uso do AEI: como é construída, e por que cada decisão é essa

> **O que este arquivo é.** O apêndice B do relatório é um resumo só de tabelas extraído
> daqui: o paper leva os números, e a argumentação de cada decisão de construção vive neste
> arquivo. Quem quiser saber por que a métrica é assim, e não do jeito natural, lê aqui.
>
> **Precedência quando algo divergir:** as tabelas em `analise/output/tables/` mandam neste
> arquivo, e este arquivo manda no apêndice B. Um número que só existe no paper é bug.
>
> **Uma ressalva sobre as remissões a script.** Cada bloco diz onde o número nasce, e alguns
> apontam para etapas do pipeline completo que não estão neste pacote, porque reconstroem as
> métricas a partir do Anthropic Economic Index bruto: `07_download_dados.py`,
> `07b_constroi_doses.py` e `08_rerun_com_doses.py`, com as tabelas `diag01_doses`,
> `tab07b_diagnostico_releases` e `tab08_resultados`. O produto delas é o
> `dados/doses_por_ocupacao.csv` que está aqui, e é dele que os quatro scripts deste pacote
> partem.

---

## Como usar este arquivo

Cada bloco abaixo responde **uma pergunta** e tem sempre a mesma forma:

- **A decisão** — o que fazemos.
- **A alternativa** — o que faríamos se não pensássemos nisso, que é quase sempre o caminho
  natural e errado.
- **O número que decide** — porque neste projeto nenhuma decisão de construção se defende
  por argumento, só por medida.
- **Onde o número nasce** — script e tabela, para reconferir sem escavar.

O §9 tem o **mapa de dependências**: que alegação do paper cai se cada número mudar. Comece
por ele quando for mexer na métrica.

---

## 1. O que a métrica é, e o que ela identifica

Cada relatório do AEI é uma amostra do tráfego do Claude.ai, cerca de 1 milhão de conversas
numa janela de uma semana, **com fração amostrada não divulgada**. Consequência direta:
contagens absolutas não medem volume, e nada no trabalho pode depender do nível.

O que a amostragem preserva é o **volume relativo**. Se cada conversa tem a mesma
probabilidade de entrar na amostra, a contagem esperada de cada ocupação é proporcional ao
seu volume verdadeiro; o fator de amostragem, comum a todas, vira constante aditiva no log e
desaparece na padronização. A métrica identifica então a ordenação e as magnitudes relativas
de uso como o tráfego completo identificaria, a menos do ruído amostral.

O nível do uso agregado e sua trajetória ficam de fora, e **não fazem falta**: a
identificação vem da variação entre ocupações, e a dinâmica do efeito vem dos coeficientes
mensais do painel (§3.2 do paper).

---

## 2. Os quatro elos da cadeia, da conversa à ocupação do CPS

### Elo 1 — conversa → tarefa O*NET

O AEI atribui cada conversa a uma tarefa O*NET (por exemplo *"write computer programs"*) e
**herdamos essa classificação**. O erro de medida dela entra na leitura junto das limitações
do §6.

### Elo 2 — tarefa → ocupação SOC (a repartição)

SOC é o sistema de classificação ocupacional do governo americano, do qual os códigos do
levantamento domiciliar são uma versão agregada.

- **A decisão.** Repartir cada conversa **uma única vez** entre as ocupações que contêm
  aquela tarefa, proporcionalmente à importância da tarefa em cada ocupação.
- **A alternativa.** O mapeamento simples, que dá a conversa **inteira** a cada ocupação.
- **Por que a alternativa é errada, e não só imprecisa.** A contagem de conversas é o dado
  real observado e não pode mudar de tamanho no caminho: o AEI atribui cada conversa a
  exatamente uma tarefa, então há exatamente **uma** conversa para distribuir.
- **O número que decide.** No mapeamento simples cada conversa acabava contada **1,48 vez**,
  com ocupações individuais chegando a **6,3 vezes**. Corrigir move todos os efeitos
  salariais **16–33% para cima em módulo**.
- **A régua da repartição não decide nada.** Repartir por importância e repartir em partes
  iguais dão exatamente a mesma métrica (**correlação 1,0000**). Nenhuma conclusão depende de
  *como* a conversa é dividida, só de ela ser dividida **uma vez**. Isso é útil: fecha uma
  linha de questionamento inteira.

### Elo 3 — SOC → código do CPS (a harmonização)

Elo mecânico, e é onde um descuido destrói o painel. Os códigos ocupacionais do CPS **mudam
de versão ao longo da amostra**, e sem harmonização as ocupações que trocaram de código em
2020 perdem o **período pré-tratamento inteiro** na junção das bases. São, ironicamente, as
de tecnologia — as que lideram qualquer ranking de uso, isto é, exatamente as que o trabalho
não pode perder.

Harmonizamos com os crosswalks oficiais do Census, **78 pares inequívocos**, com diagnóstico
de cobertura rodando a cada execução.

### Elo 4 — agregação

As conversas assim repartidas viram as duas métricas por ocupação que o painel recebe.

---

## 3. As duas dimensões

- **Intensidade do uso ($u$)** — uso total por trabalhador, em log. Existe onde a ocupação
  tem uso americano mensurável: **322 das 491** ocupações. A análise conjunta das duas
  métricas, que exige também composição observada, fica com **321**.
- **Automação ($a$)** — que fração da penetração existente é substitutiva, pela participação
  dos tipos de uso delegativos no total classificado.

### 3.1 Por que per capita, e per capita de quando

- **A decisão.** Dividir pelo emprego médio **pré-tratamento**, de 2019 a 2022.
- **A alternativa 1: o total cru.** Confundiria ocupação que usa muito com ocupação grande,
  porque o uso total cresce mecanicamente com o número de pessoas que a exercem.
- **A alternativa 2, mais sutil e mais perigosa: o emprego contemporâneo.** Emprego pós-2022
  é **desfecho**. Se a IA encolheu uma ocupação, o denominador cai, a métrica per capita
  sobe, e o tratamento fica contaminado pelo próprio efeito — a definição de *bad control*.
- **O número que decide.** Trocar o denominador antigo pelo pré-tratamento **derrubou os
  efeitos estimados de duas a três vezes**. A precaução não era teórica.

### 3.2 Por que log puro, e não log(1 + x)

- **A decisão.** Log puro.
- **A alternativa.** A transformação log(1 + x), que admite zeros e por isso é tentadora.
- **Por que não.** O "1" dessa transformação está **na unidade da variável**, de modo que ela
  muda de forma quando a unidade muda — defeito que Chen e Roth (2024) demonstram
  formalmente e **que nos atingiu de fato** ao trocar o denominador (§3.1). O log puro é
  invariante à unidade.
- **O preço, declarado.** As ocupações com uso americano zero saem da análise de duas
  métricas, o que equivale a medir a margem em que a composição existe.

### 3.3 As duas dimensões são separáveis (e é isso que o trabalho inteiro explora)

Fato empírico que viabiliza estimar as duas juntas: uso e automação variam de forma
praticamente independente entre ocupações, com correlação de **−0,04** na métrica principal
e entre **−0,01 e −0,16** nas variantes, cujo extremo é a métrica global. Mesmo no pior caso
a inflação de variância do **par** é de **1,03** (erros-padrão menos de 2% maiores que no
caso ortogonal exato).

**Cuidado, e isto foi um achado da revisão de 12/08/2026:** esses números são do *par*. A
especificação do corpo tem **três** regressores, porque inclui o produto, e a ortogonalidade
não se estende a ele:

| par | correlação (peso da WLS) | sem peso |
|---|---:|---:|
| $u \times a$ | −0,046 | −0,026 |
| $u \times u{\cdot}a$ | −0,054 | −0,016 |
| $a \times u{\cdot}a$ | **−0,593** | −0,353 |

VIF do sistema de três: **1,01** ($u$), **1,56** ($a$), **1,56** ($u{\cdot}a$) — 1,59 na
margem de desemprego, que é o pior caso.

Não é problema de identificação, e é por isso que **o VIF decide e a correlação não**. Mas a
frase do paper afirmava ortogonalidade dos três, e isso era falso: quem calcular
cor($a$, $u{\cdot}a$) encontra −0,59. Comparação que dá a escala: a especificação em volumes,
que é a que **não** roda, tem regressores a +0,94.

Produzido por `21_especificacao_dinamica.py` (bloco de colinearidade), em
`tab21_especificacao_dinamica_US_pooled.md`.

---

## 4. A geografia: por que só-EUA, e o que fica de fora

Os desfechos do CPS são americanos por construção, enquanto o agregado global do AEI mistura
padrões de uso de outros países. O descasamento **não é hipotético**: os EUA são o maior
usuário único do Claude no relatório e ainda assim respondem por apenas **21,6%** do uso
global.

Por isso reconstruímos as métricas com o recorte por país dos três relatórios que somamos,
usando apenas as linhas dos Estados Unidos (APPEL et al., 2025, 2026; MASSENKOFF; McCRORY,
2026).

**A fonte impõe um limite que afeta só uma das duas métricas.** Para cada país o AEI publica
quantas conversas houve em cada tarefa, e publica a distribuição do país pelos modos de
colaboração, **mas não publica o cruzamento entre as duas coisas** — que é justamente o que a
composição exige. Então: a intensidade é genuinamente americana, e **a composição vem do
mundo**.

O próprio AEI oferece o dado para avaliar o custo disso, porque as proporções agregadas de
uso substitutivo dos EUA e do mundo ficam próximas e se movem juntas:

| janela de coleta | EUA | mundo |
|---|---:|---:|
| agosto de 2025 | 49,1% | 51,1% |
| novembro de 2025 | 44,9% | 46,7% |
| fevereiro de 2026 | 41,4% | 45,5% |

**O que isso não garante.** Tudo acima é sobre o **nível** da composição. Não garante que a
**ordenação das ocupações** seja a mesma nos dois recortes: se nos EUA os advogados
delegassem mais e os programadores menos, não teríamos como saber. É hipótese em aberto, e
deve continuar declarada como tal.

---

## 5. Por que somar três relatórios, e não usar um

O desenho precisa de uma métrica **fixa por ocupação**, e o AEI não publica uma métrica
assim: publica fotografias, uma semana de coleta a cada poucos meses, e o que elas medem muda
bastante entre janelas. Isso torna a escolha do relatório uma decisão com consequência.

- **A alternativa natural, e por que é a pior possível.** O relatório de setembro de 2025, o
  primeiro com recorte geográfico, seria a escolha óbvia — e é justamente **o pico da série**,
  a única semana em que o uso substitutivo superou o complementar no mundo.
- **O tamanho do problema, medido por terceiros.** Yin e Ogut (2026) reestimam o mesmo
  desenho trocando **apenas** a janela de coleta: o coeficiente de emprego quase dobra, e
  **41,8%** das ocupações mudam de quartil de exposição entre a primeira e a última janela.
- **A decisão.** Somar as conversas de cada tarefa nos três relatórios comparáveis — janelas
  em agosto de 2025 (dias 04–11), novembro de 2025 (13–20) e fevereiro de 2026 (05–12) — e
  recalcular as proporções sobre o total de **2,9 milhões** de conversas.
- **O argumento.** Se o que a regressão precisa é a composição *típica* do período, cada
  semana observada é uma estimativa imprecisa dela, e várias semanas juntas estimam melhor do
  que uma. É também o procedimento da própria fonte no seu único trabalho que liga o AEI a
  salário e emprego (MASSENKOFF; McCRORY, 2026) — precedente que vale citar quando a escolha
  for questionada.
- **Os números do ganho**, todos na direção das ocupações de poucas conversas, cuja composição
  muda de um relatório para outro por sorteio de amostra:

| o que melhora | um relatório | três somados |
|---|---:|---:|
| mediana de conversas classificadas por ocupação | 265 | 809 |
| imprecisão típica da proporção | ±3,1 p.p. | ±1,8 p.p. |
| ocupações com composição observável | 330 | 371 |

### 5.1 Estabilidade da ordenação entre relatórios

| Métrica | Spearman entre relatórios | troca de quartil |
|---|---:|---:|
| intensidade do uso (total por trabalhador, EUA) | 0,93–0,98 | 15–28% |
| composição substitutiva, todas as ocupações | 0,70–0,81 | 35–41% |
| composição substitutiva, ocupações com ≥50 conversas | 0,83–0,88 | 33–40% |

Três leituras, e a segunda é a menos óbvia:

1. **A ordenação do uso é estável**, com Spearman nunca abaixo de 0,93.
2. **Ordenação estável não é quartil estável.** Até 28% das ocupações cruzam uma linha de
   quartil de um relatório para outro — e é **por quartil** que a §4 do paper lê as figuras.
   Isso dá à soma dos três relatórios uma função que vai além de ganhar precisão.
3. **A composição é o caso problemático**, com duas em cada cinco ocupações trocando de
   quartil entre uma semana e outra. A terceira linha mostra que a instabilidade se concentra
   nas ocupações de poucas conversas, exatamente as que a soma fortalece.

### 5.2 A troca de classificador, que não podemos testar direto

O modelo que classifica as conversas muda de um relatório para outro. A fonte mediu **uma
única vez** o efeito de uma dessas trocas: cerca de **4 pontos percentuais** na taxa
agregada. É a **banda mínima de incerteza** com que os nossos números de composição devem ser
lidos, e esse erro tampouco é do tipo inofensivo que apenas encolhe coeficientes (§6.1).

Duas coisas limitam o dano, e as duas são indiretas:

- Se a troca de classificador embaralhasse a ordenação das ocupações, as correlações de §5.1
  seriam baixas. Não são.
- Refizemos a agregação por um caminho **imune a diferenças de nível** entre relatórios,
  padronizando cada relatório separadamente e tirando a média: a ordenação resultante é a
  mesma, com correlação de **0,97**.

---

## 6. As limitações, e o tamanho de cada uma

Cinco governam a leitura e estão enunciadas no §3.1 do paper. **Duas têm tamanho medido** —
esta seção existe sobretudo por elas.

### 6.1 Seleção de plataforma — a mais séria (tamanho medido)

É a limitação que mais ameaça o trabalho, porque um paper recente a atacou de frente **com o
mesmo tipo de desenho que usamos**. Yin e Ogut (2026) montam dez medidas de exposição a
partir de cinco fontes de telemetria — entre elas o próprio AEI nos canais Claude.ai e API —
e estimam com elas o mesmo DiD contínuo sobre o mesmo desfecho, a mesma amostra, os mesmos
controles e o mesmo estimador, **variando só a plataforma de origem do log**.

Três resultados nos atingem diretamente:

1. O coeficiente de emprego pós-ChatGPT muda por um **fator de 1,9** entre plataformas.
2. Os canais **consumer e enterprise de um mesmo fornecedor produzem estimativas que
   discordam no sinal**, em todas as ondas. O desacordo não é entre empresas rivais: é entre
   duas janelas do mesmo produto.
3. Reponderar as ocupações pela composição ocupacional real da força de trabalho **atenua as
   estimativas entre 42% e 93%**, chegando a devolver coeficiente indistinguível de zero na
   medida composta.

**O que muda a leitura** é a formalização: erro de medida **não-clássico**. Erro clássico
apenas atenua; erro correlacionado com o nível da variável latente pode atenuar, **inflar ou
inverter** o sinal. Duas medidas do tamanho do descolamento: nenhuma medida derivada de
plataforma que eles testam correlaciona com a participação de emprego do BLS acima de **0,33**
de Spearman, e a razão entre densidade de conversas e densidade de emprego varia por um
**fator de 72** entre ocupações.

Nossa métrica é uma dessas medidas, construída de uma dessas fontes, e **neste desenho não há
como escapar do problema**, que é propriedade da fonte e não do estimador.

**A direção do viés, que corre a nosso favor no ponto que mais importa.** O trabalhador
efetivamente substituído deixa de gerar conversas na plataforma, enquanto o que a IA
complementa continua no emprego e continua gerando dado. A seleção subestima, por isso, a
substituição mais do que subestima a complementação. **A penalidade da automação que
estimamos é limite inferior da pressão de deslocamento, e não estimativa pontual dela.** É a
leitura que a assimetria de sinal do resultado já sugeria, e é a que este documento
recomenda.

### 6.2 Classificação por modelo (tamanho medido)

A classificação de cada conversa como substitutiva ou complementar é feita por modelo, e é a
parte mais frágil da medição. Tamanho: os ~4 p.p. do §5.2. É também o ponto em que a analogia
com a teoria é mais frouxa — a classificação captura o padrão de interação de uma conversa, e
não a realocação de tarefas de que fala o modelo de Acemoglu e Restrepo.

### 6.3 As três sem remédio nesta base

- **Quem está na conversa.** O AEI observa a conversa, e não a pessoa: nenhuma informação de
  ocupação, emprego ou profissão do usuário. Quando dizemos que uma ocupação usa IA, o que
  medimos é que **as tarefas que compõem aquele ofício aparecem nas conversas**, e não que
  trabalhadores dela as tenham escrito — quem digitou pode ser um profissional da ocupação, um
  estudante, um curioso, ou alguém de outra profissão fazendo tarefa vizinha. **É a suposição
  mais forte de toda a cadeia**, e nada no desenho separa esses casos.
- **A composição vem do agregado mundial** (§4).
- **A ponte temporal.** A métrica é de 2025–26 e o pós-período começa em novembro de 2022:
  assumimos que a ordenação das ocupações nas janelas observadas representa a de 2023 e 2024.
  **Nenhuma combinação de relatórios permite testar isso**, porque o AEI nasce em dezembro de
  2024. Confiabilidade (§5.1) não é validade: as três janelas cobrem agosto de 2025 a
  fevereiro de 2026, e nenhuma observa 2023.

### 6.4 Duas outras, que merecem registro

- **Só Claude.ai.** A interface de programação, que o AEI publica em separado, tem perfil
  muito mais substitutivo (**77%**) e fica de fora por comparabilidade entre relatórios. Se o
  trabalho substitutivo migra para essas superfícies, nossa métrica de automação **subestima**
  a exposição das ocupações que as usam.
- **Um produto de um provedor**, cuja participação de mercado muda depressa. A métrica vale
  como **ordenação entre ocupações**, não como nível de uso de IA em geral, e é assim que o
  desenho a emprega.

---

## 7. De onde os números saem

| bloco | script | tabela |
|---|---|---|
| doses por ocupação, as duas dimensões | `07b_constroi_doses.py` | `diag01_doses.md` |
| repartição, harmonização, cobertura | `07_download_dados.py`, `07b` | `tab07b_diagnostico_releases.md` |
| estabilidade entre relatórios (§5.1) | `07b` | `tab07b_diagnostico_releases.md` |
| colinearidade e VIF dos três termos (§3.3) | `21_especificacao_dinamica.py` | `tab21_especificacao_dinamica_US_pooled.md` |
| contraste entre construções da métrica | `16_contraste_mesmo_estimador.py` | `tab16_contraste_mesmo_estimador_US_pooled.md` |
| variantes da métrica (global, task_based, min50…) | `08_rerun_com_doses.py --doses` | `tab08_resultados_<tag>.md` |

Números de terceiros (Yin e Ogut 2026; Chen e Roth 2024; Massenkoff e McCrory 2026) não têm
script: vêm da fonte, e estão na lista de referências do relatório.

---

## 8. Onde isto aparece no paper

| no paper | o que leva |
|---|---|
| §3.1.1 Fontes | o que a métrica é, as três janelas, os 2,9 milhões |
| §3.1.2 Manipulações críticas | as quatro decisões, em prosa curta |
| §3.1.3 Métricas | as duas dimensões, as cinco limitações, o −0,04 |
| §3.2.2 Especificação | por que intensidade × fração, e o VIF de 1,6 |
| §4.2 | os 41–49% da composição americana, a ponte temporal |
| **Apêndice B** | **só tabelas**: B1 decisões, B2 estabilidade, B3 limitações, B4 composição por janela, B5 colinearidade |

---

## 9. Mapa de dependências: o que cai se um número mudar

Consulte antes de mexer na métrica. À esquerda o número; à direita a alegação do paper que
depende dele e morre com ele.

| se mudar… | cai… |
|---|---|
| a repartição da conversa (1,48×; 16–33%) | a magnitude de **todos** os efeitos salariais, e a Tabela 1 inteira |
| o denominador pré-tratamento (2–3×) | idem, e a defesa contra *bad control* do §3.1.2 |
| cor($u$, $a$) = −0,04 | a contribuição central: sem quase-ortogonalidade a decomposição não se estima, e o §3.2.2 desaba junto com a §2.1.3 |
| o VIF de 1,6 dos três termos | a justificativa do termo de interação no §3.2.2 |
| a estabilidade 0,93–0,98 / 0,83–0,88 | a mitigação da ponte temporal no §4.2 (é o que o parágrafo cita) |
| a direção do viés de seleção (substituído não gera conversa) | a leitura de **limite inferior** da penalidade, no Resumo, no Abstract e nas Considerações Finais |
| os 41–49% de composição americana | o argumento do §4.2 de que o saldo positivo **não** é composicional |
| o 21,6% de uso americano | a motivação do recorte por país (§4) |
| os ~4 p.p. da troca de classificador | a banda mínima de incerteza da composição, citada no §2.2 e no §3.1.3 |

---

## 10. Histórico das decisões

| quando | o que mudou |
|---|---|
| 27/07/2026 | a dose deixa de ser *snapshot*: pooling de relatórios entra |
| 30/07/2026 | crosswalk fracionário e harmonização do denominador |
| 06/08/2026 | métrica principal passa de *task-based* a *usage-based*; robustez toda refeita |
| 11/08/2026 | vocabulário: "adoção" → "uso"/"intensidade do uso" |
| 12/08/2026 | recorte por plataforma entra como quinta limitação; VIF dos três termos medido; apêndice B reduzido a tabelas e a prosa migrada para este arquivo |
