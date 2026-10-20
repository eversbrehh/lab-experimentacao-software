# Ata da reunião de consenso da amostra-ouro

- **Data:** 15/10/2026 (quinta-feira), das 14h às 15h30, por videoconferência
- **Presentes:** Brenda Evers, Carlos José Gomes Batista Figueiredo e Gabriela Alvarenga Cardoso
- **Origem dos dados:** `avaliador_1.xlsx` a `avaliador_3.xlsx`, processados por `python -m analise.concordancia` (Issue #160)

## 1. Concordância (kappa de Fleiss)

Calculado sobre os rótulos individuais, antes do consenso (`kappa.csv`).

| Dimensão | Itens | Kappa | Faixa (Landis e Koch) | Acordo total (3-0) |
|---|---|---|---|---|
| `tipo_projeto` | 60 repositórios | 0,82 | quase perfeita | 49 |
| `entregas_reais` | 60 repositórios | 0,19 | leve | 53 |
| `corretiva` | 300 releases | 0,78 | substancial | 263 |

Não houve nenhum item 1-1-1: todos têm um rótulo majoritário, e por isso nenhum caso precisou do desempate previsto na seção 6 do protocolo. Os 55 itens que ficaram 2-1 (11 + 7 + 37) estão listados em `divergencias.csv`.

**Achado para o artigo.** O kappa baixo (0,19) em `entregas_reais` se explica pela prevalência de uma única categoria: o rótulo `sim` foi usado em 59, 58 e 54 dos 60 repositórios pelos avaliadores 1, 2 e 3, respectivamente. Quando uma categoria domina dessa forma, o kappa tende a cair mesmo havendo bastante concordância real — aqui, 53 dos 60 itens (88%) tiveram acordo total entre os três avaliadores. Decidimos relatar esse kappa junto do percentual de acordo, deixando claro que ele reflete a distribuição dos dados e não um critério ambíguo.

## 2. Casos revisados em reunião

Nós revisamos os itens que ficaram 2-1 e confirmamos o rótulo da maioria em todos eles, conforme prevê a seção 6 do [protocolo de rotulagem](../../docs/protocolo-rotulagem.md). Nenhum rótulo foi alterado: o `consenso.csv` gerado pelo script já é o consenso final.

Nas tabelas abaixo, "Proposta" é o rótulo que já vinha da maioria, e "Decisão" é o rótulo confirmado pela reunião.

### 2.1 Tipo do projeto (11 repositórios em 2-1)

| Repositório | Av. 1 | Av. 2 | Av. 3 | Proposta | Decisão | Observação |
|---|---|---|---|---|---|---|
| babel/babel | outro | biblioteca/framework | biblioteca/framework | biblioteca/framework | biblioteca/framework | Proposta mantida. |
| firecrawl/firecrawl | biblioteca/framework | aplicação/serviço | aplicação/serviço | aplicação/serviço | aplicação/serviço | Proposta mantida. |
| sickn33/agentic-awesome-skills | biblioteca/framework | outro | outro | outro | outro | Proposta mantida: é um catálogo de skills, sem um modo de uso dominante. |
| prettier/prettier | outro | ferramenta CLI | ferramenta CLI | ferramenta CLI | ferramenta CLI | Proposta mantida. |
| headroomlabs-ai/headroom | aplicação/serviço | biblioteca/framework | biblioteca/framework | biblioteca/framework | biblioteca/framework | Proposta mantida: o README apresenta a biblioteca em primeiro lugar. |
| anomalyco/opencode | aplicação/serviço | ferramenta CLI | ferramenta CLI | ferramenta CLI | ferramenta CLI | Proposta mantida. |
| JuliaLang/julia | outro | ferramenta CLI | ferramenta CLI | ferramenta CLI | ferramenta CLI | Proposta mantida. |
| jestjs/jest | biblioteca/framework | biblioteca/framework | ferramenta CLI | biblioteca/framework | biblioteca/framework | Proposta mantida. O avaliador 2 observou que o README mostra tanto a instalação como dependência quanto o uso por linha de comando; o avaliador 3 rotulou como ferramenta CLI. Pelo critério da seção 4.1 do protocolo — vale o modo de uso que o README apresenta primeiro —, é um caso de fronteira, e a maioria foi mantida. |
| rust-lang/rust | outro | ferramenta CLI | ferramenta CLI | ferramenta CLI | ferramenta CLI | Proposta mantida. |
| ggml-org/llama.cpp | ferramenta CLI | biblioteca/framework | ferramenta CLI | ferramenta CLI | ferramenta CLI | Proposta mantida: os avaliadores 1 e 3 leram o README como CLI (o avaliador 3 anotou que ele apresenta primeiro `llama cli` e `llama serve`); o avaliador 2 viu a biblioteca como produto principal. |
| jgm/pandoc | biblioteca/framework | ferramenta CLI | biblioteca/framework | biblioteca/framework | biblioteca/framework | Proposta mantida: os avaliadores 1 e 3 anotaram que o README apresenta primeiro a biblioteca Haskell; o avaliador 2 viu o comando `pandoc` como uso principal. |

**Discussão.** Em 8 dos 11 casos, o avaliador 1 foi o único a divergir, e em quatro deles (babel, prettier, Julia, rust) usou o rótulo `outro` para projetos que são ferramentas de desenvolvimento. Entendemos que isso reflete uma interpretação diferente do critério de `outro`, e não casos pontuais isolados. Decidimos registrar esse ponto como limitação do protocolo (seção 4 desta ata), sem alterar o documento do protocolo em si.

### 2.2 Entregas reais ao usuário (7 repositórios em 2-1)

| Repositório | Av. 1 | Av. 2 | Av. 3 | Proposta | Decisão | Observação |
|---|---|---|---|---|---|---|
| toeverything/AFFiNE | sim | sim | não | sim | sim | Há versões estáveis curadas e com notas de lançamento, apesar do grande volume de builds canary. |
| supabase/supabase | incerto | incerto | não | incerto | incerto | Proposta mantida. Os três avaliadores descreveram o mesmo fato: as "releases" são boletins mensais de uma plataforma hospedada, sem artefato nem versão instalada. A divergência foi só de classificação — os avaliadores 1 e 2 usaram `incerto` (não fica claro que a tag represente uma versão distribuída), e o avaliador 3 usou `não`. Manteve-se a maioria (`incerto`). |
| microsoft/monaco-editor | sim | sim | não | sim | sim | As versões estáveis são publicadas no npm, e os builds diários aparecem como marcadores separados. |
| ggml-org/llama.cpp | sim | sim | incerto | sim | sim | Há binários anexados e releases curadas (v0.4.1), apesar das tags por commit. |
| rtk-ai/rtk | sim | sim | não | sim | sim | As versões estáveis têm binários e notas de lançamento. |
| abhigyanpatwari/GitNexus | sim | sim | incerto | sim | sim | As versões estáveis são instaladas via npm. |
| openbq-org/OpenBB | sim | incerto | sim | sim | sim | Proposta mantida. |

**Discussão.** O avaliador 3 concentrou a maior parte dos rótulos `não` (4 dos 60 no total) e foi o único a divergir em seis dos sete casos. Por fim, concluímos que ele aplicou a regra de predominância de builds automáticos de forma mais rígida que os demais, e que essa regra pode ser detalhada em uma futura versão do protocolo.

### 2.3 Release corretiva (37 releases em 2-1)

A lista completa está em `divergencias.csv` (dimensão `corretiva`). A maioria propõe 23 `não` e 14 `sim`. Os repositórios com mais releases divergentes são bitcoin/bitcoin (4), metabase/metabase (4), babel/babel (3), serverless/serverless (2), denoland/deno (2) e spring-projects/spring-boot (2).

- **Releases revisadas na reunião:** as 4 de bitcoin/bitcoin e as 4 de metabase/metabase — que juntas somam 8 das 37 divergências e vêm de apenas dois repositórios —, além das 3 de babel/babel e das 2 de spring-projects/spring-boot. As demais permaneceram com o rótulo da maioria.
- **Por que bitcoin e metabase foram revisados:** nos dois casos, o `url_compare` cruza ramos de versão diferentes (por exemplo, `v30.2...v29.3` e `v0.62.2...v0.58.18`), o que faz a lista de commits não isolar corretamente a release. Isso levou os avaliadores a reagir de formas diferentes, conforme as observações registradas nas planilhas:
  - O avaliador 1 julgou pelos commits desde a release anterior da mesma linha (backports de correções) e deu `sim` em 3 das 4 releases de bitcoin e nas 4 de metabase.
  - O avaliador 2 deu `sim` nas releases de bitcoin, que trazem notas com correções e nenhuma funcionalidade nova relevante, e `não` nas de metabase, cujas notas não listam as mudanças e, em 3 das 4, a comparação está inflada (de 463 a 707 commits); na quarta (`v0.56.19`), com 7 commits, metade é de CI e as correções não predominam.
  - O avaliador 3 deu `não` em todas, aplicando a regra do protocolo para notas externas, ausência de lista de mudanças e inconsistência nos commits.
- **Resultado:** todas as releases revisadas permaneceram com o rótulo da maioria.
  - bitcoin/bitcoin: `v28.3` ficou `não`; `v29.3`, `v30.3` e `v29.4` ficaram `sim`.
  - metabase/metabase: as 4 releases ficaram `não`.
  - babel/babel: `v7.28.6` ficou `sim`; `v7.29.3` e `v8.0.1` ficaram `não`.
  - spring-projects/spring-boot: `v4.0.3` ficou `sim`; `v4.1.0` ficou `não`.
- **Observações levantadas:**
  - babel `v7.29.3`: os avaliadores 1 e 2 observaram que a release mistura correções com suporte novo (Flow) e melhorias de desempenho, sem que haja predomínio claro de correção; o avaliador 3 deu `sim`. A maioria (`não`) segue a regra de release mista da seção 4.3.
  - spring-boot `v4.0.3`: o `url_compare` parte de outra linha de versão (`v3.5.11`, com 2898 commits), e o avaliador 1 julgou pelos commits desde a `v4.0.2`. O avaliador 2 identificou dez correções ligadas à nova constante `JavaVersion.TWENTY_SIX`; o avaliador 1 registrou "dúvida moderada", por haver também ajustes de compatibilidade (Java 26, Flyway 12). O avaliador 3 deu `não`. A maioria (`sim`) foi mantida.
  - **Inconsistência registrada:** bitcoin e metabase têm o mesmo tipo de release (manutenção de uma linha antiga via backport), mas a maioria chegou a rótulos opostos (`sim` para bitcoin, `não` para metabase), porque cada avaliador interpretou a evidência de um jeito diferente. Optamos por manter os rótulos do consenso e relatar esse caso como limitação (seção 4).

## 3. Protocolo de desempate usado

- 3-0: prevalece o rótulo comum.
- 2-1: prevalece o rótulo da maioria. Nenhuma decisão da reunião divergiu da maioria.
- 1-1-1: seria decidido na reunião pelos critérios da seção 4 do protocolo e, sem acordo, receberia `outro` em `tipo_projeto` e `incerto` em `entregas_reais`. Não houve, porém, nenhum caso 1-1-1.

## 4. Limitações do protocolo (para o artigo)

O protocolo não é alterado após a rotulagem (seção 1 do protocolo). Os pontos abaixo devem ser relatados no artigo como limitações:

- O rótulo `outro` para ferramentas de desenvolvimento foi interpretado de forma diferente entre os avaliadores (ver seção 2.1).
- A seção 4.2 não detalha como ponderar versões estáveis curadas em relação a builds automáticos diários na página de releases (ver seção 2.2). O caso de um "boletim mensal de novidades" (supabase), que o protocolo não previa e que gerou os rótulos `incerto` e `não`, é um exemplo.
- A seção 4.3 determina decidir com base na lista de commits do `url_compare`, mas não prevê releases de backport cuja comparação cruza ramos diferentes e traz centenas de commits que não pertencem de fato à release (bitcoin/bitcoin, metabase/metabase, spring-boot `v4.0.3`). Cada avaliador contornou esse problema à sua maneira, o que gerou rótulos opostos para releases do mesmo tipo (ver seção 2.3).
- A mistura de correção e novidade em uma mesma release (babel `v7.29.3`, spring-boot `v4.0.3`) depende de julgamento sobre o que predomina, e o protocolo não define um limiar objetivo para isso.

## 5. Saídas

- `kappa.csv`: kappa calculado para as três dimensões.
- `consenso.csv`: rótulo de consenso por item e dimensão, gerado pelo script. Nenhum item foi alterado na reunião, e a coluna `justificativa` permanece vazia.
- `divergencias.csv`: os 55 itens que ficaram 2-1.
- `ata_consenso.md`: este documento.
