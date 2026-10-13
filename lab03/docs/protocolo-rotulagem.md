# Protocolo de rotulagem da amostra-ouro

Este documento define como os três integrantes rotulam a amostra-ouro do Lab03 (seção 6 do enunciado) e como o grupo chega ao rótulo de consenso. Ele foi escrito antes do sorteio e não muda depois que a rotulagem começa.

## 1. Objetivo e escopo

A amostra-ouro são 60 repositórios sorteados da amostra prevista, com 5 releases sorteadas de cada um, o que dá 300 releases. Cada integrante rotula todos os repositórios e todas as releases na própria planilha, sem contato com os demais.

| Dimensão | Nível | Uso |
|---|---|---|
| (i) Tipo do projeto | Repositório | Fator da RQ 06 |
| (ii) As releases representam entregas reais ao usuário | Repositório | Ameaça de construto (release como proxy de deploy) |
| (iii) A release é corretiva | Release | Referência para precisão, recall e F1 da heurística do CFR (b), RQ 03 |

A concordância entre os três avaliadores é medida pelo kappa de Fleiss em cada dimensão, sobre os rótulos individuais, antes do consenso.

## 2. Planilhas

Cada avaliador recebe um arquivo `dados/rotulagem/avaliador_<n>.xlsx` com duas tabelas. As colunas não são renomeadas, removidas nem reordenadas.

Nível repositório, uma linha por repositório:

| Coluna | Preenchida por | Conteúdo |
|---|---|---|
| `full_name` | Script | `owner/repo` |
| `url` | Script | Link do repositório no GitHub |
| `tipo_projeto` | Avaliador | Rótulo da dimensão (i) |
| `entregas_reais` | Avaliador | Rótulo da dimensão (ii) |
| `observacao` | Avaliador | Texto livre; pode ficar vazia |

Nível release, uma linha por release sorteada:

| Coluna | Preenchida por | Conteúdo |
|---|---|---|
| `full_name` | Script | `owner/repo` |
| `tag_name` | Script | Tag da release |
| `url_release` | Script | Link da página da release |
| `url_compare` | Script | Link da comparação com a release anterior |
| `corretiva` | Avaliador | Rótulo da dimensão (iii) |
| `observacao` | Avaliador | Texto livre; pode ficar vazia |

Valores aceitos, escritos exatamente assim, em minúsculas e com acentos:

| Coluna | Valores aceitos |
|---|---|
| `tipo_projeto` | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro` |
| `entregas_reais` | `sim`, `não`, `incerto` |
| `corretiva` | `sim`, `não` |

Nenhuma célula de rótulo fica vazia. Quando a evidência não basta, vale a regra de dúvida da dimensão e o motivo vai para `observacao`.

## 3. Fontes de evidência

| Nível | O que consultar |
|---|---|
| Repositório | O README e a página de releases do repositório (`url` + `/releases`) |
| Release | As *release notes* (`url_release`) e a lista de commits entre a release e a anterior (`url_compare`) |

O número da versão não é evidência. Uma release não é corretiva por mudar só o *patch*, nem deixa de ser por mudar o *minor*: decide o conteúdo das *release notes* e dos commits. Essa regra existe porque a heurística automática usa o número da versão, e o rótulo humano precisa ser uma medida independente dela.

Issues, *pull requests* e o *changelog* do repositório podem ser abertos quando as *release notes* apontam para eles. Buscas fora do GitHub não são necessárias.

## 4. Critérios

### 4.1 Tipo do projeto (`tipo_projeto`)

Decide o modo principal de uso, conforme o README apresenta o projeto.

| Valor | Critério |
|---|---|
| `biblioteca/framework` | O projeto é importado ou estendido por outro código, como dependência |
| `aplicação/serviço` | O projeto é executado ou implantado por quem o usa: aplicativo, servidor, site, plataforma |
| `ferramenta CLI` | A interface principal é a linha de comando, e o uso típico é invocar um comando |
| `outro` | Nenhum dos anteriores: listas, documentação, cursos, conjuntos de dados, especificações, ou repositório sem modo de uso dominante |

Exemplos fictícios:

| Repositório | Descrição no README | Rótulo |
|---|---|---|
| `acme/httpx-lite` | "Cliente HTTP para Python. Instale com `pip install httpx-lite` e importe no seu código." | `biblioteca/framework` |
| `acme/painel` | "Plataforma de monitoramento auto-hospedada. Suba com `docker compose up`." | `aplicação/serviço` |
| `acme/fzgrep` | "Busca textual rápida no terminal. Uso: `fzgrep <padrão> <pasta>`." | `ferramenta CLI` |

Casos de dúvida:

| Caso | Regra |
|---|---|
| Biblioteca que também distribui uma CLI, ou CLI que também expõe uma API de biblioteca | Vale o modo que o README apresenta primeiro |
| Servidor ou banco de dados iniciado por um comando | `aplicação/serviço`: o comando só inicia um processo que fica em execução |
| Monorepo com vários pacotes | O tipo do pacote que o README apresenta como principal; sem pacote principal, `outro` |
| Extensão ou *plugin* de outra ferramenta | `biblioteca/framework` |
| Repositório de exemplos, modelos de projeto ou material didático | `outro` |

### 4.2 Entregas reais ao usuário (`entregas_reais`)

A pergunta é se uma release desse repositório corresponde a uma versão que chega a quem usa o projeto. O julgamento considera a página de releases do repositório como um todo, e não só as 5 releases sorteadas.

| Valor | Critério |
|---|---|
| `sim` | As releases publicam uma versão que o usuário instala, atualiza ou usa (pacote, binário, imagem), com as mudanças descritas ou identificáveis pelos commits |
| `não` | As releases são marcadores sem relação com uma versão usada por alguém: uma por commit ou por dia sem curadoria, espelho automático de outro repositório, ou marcos internos do time |
| `incerto` | A evidência não permite decidir entre `sim` e `não` |

Exemplos fictícios:

| Repositório | O que a página de releases mostra | Rótulo |
|---|---|---|
| `acme/httpx-lite` | Uma release a cada duas ou três semanas, com notas de mudanças e a mesma versão publicada no PyPI | `sim` |
| `acme/painel-nightly` | Uma release por dia, chamada `nightly-AAAAMMDD`, com texto gerado e sem notas de mudanças | `não` |
| `acme/kit` | Releases com notas vazias e sem artefatos; o README não diz como instalar uma versão | `incerto` |

Casos de dúvida:

| Caso | Regra |
|---|---|
| Releases geradas por automação (ex.: *semantic-release*), com notas de mudanças e pacote publicado | `sim`: a automação não tira o caráter de entrega |
| Repositório que publica só versões automáticas, sem notas e sem artefato | `não` |
| Parte das releases é entrega e parte é marcador automático | Vale o que predomina; se não houver predomínio claro, `incerto` |
| Biblioteca cujas releases são publicadas em um registro de pacotes | `sim`: o usuário é quem depende da biblioteca |

`incerto` é para falta de evidência, não para evitar a decisão. Todo `incerto` vem com o motivo em `observacao`.

### 4.3 Release corretiva (`corretiva`)

Uma release é corretiva quando seu objetivo principal é corrigir um defeito de uma versão já publicada (RQ 03).

| Valor | Critério |
|---|---|
| `sim` | As correções de defeito são o conteúdo predominante, e a release não anuncia funcionalidade nova nem quebra de compatibilidade |
| `não` | Qualquer outro caso, inclusive quando a evidência não basta para afirmar `sim` |

Conta como correção de defeito: falha, travamento, resultado errado, regressão, reversão de mudança (*revert*) e vulnerabilidade no código do próprio projeto. Não conta: funcionalidade nova, melhoria de desempenho sem defeito relatado, refatoração, documentação, testes, CI e atualização de dependências.

Exemplos fictícios:

| Release | Notas e commits | Rótulo |
|---|---|---|
| `acme/httpx-lite` `v2.3.1` | Notas: "Corrige travamento ao abrir arquivo vazio". Dois commits, ambos de correção | `sim` |
| `acme/httpx-lite` `v2.4.0` | Notas: "Suporte a HTTP/3; novo parâmetro `timeout`; corrige vazamento de conexão" | `não` |
| `acme/fzgrep` `v1.9.2` | Sem notas. Cinco commits: quatro atualizam dependências e um corrige um erro de digitação na documentação | `não` |

Casos de dúvida:

| Caso | Regra |
|---|---|
| Release que mistura correção e funcionalidade nova | `não`, a menos que as correções predominem e nenhuma funcionalidade nova ou quebra de compatibilidade seja anunciada |
| Release sem *release notes* | Decide a lista de commits do `url_compare` |
| Sem *release notes* e sem commits legíveis (comparação vazia, erro 404 ou mensagens que não dizem o que mudou) | `não`, com o motivo em `observacao` |
| Página da release que não abre | `não`, com o motivo em `observacao` |
| Correção de vulnerabilidade no código do próprio projeto | `sim` |
| Só atualização de dependências, mesmo que por segurança | `não` |
| *Revert* de uma mudança publicada na release anterior | `sim` |
| Notas dizem "correções e melhorias", sem detalhar | Decide a lista de commits |
| Primeira release do repositório, sem anterior | `não` |
| Não se sabe quando o defeito corrigido foi introduzido | Não se investiga: basta que o defeito esteja em uma versão já publicada |

A coluna não aceita `incerto`. Na dúvida, o rótulo é `não` e a dúvida é descrita em `observacao`.

## 5. Regras de cegamento

1. Cada avaliador rotula sozinho. Até a reunião de consenso, ninguém conversa sobre repositórios, releases ou rótulos da amostra, por nenhum canal.
2. Ninguém abre a planilha de outro avaliador, no repositório ou fora dele, antes de commitar a própria.
3. Ninguém executa a heurística de release corretiva (`metricas/corretiva.py`) sobre a amostra nem consulta uma saída dela. As planilhas não têm coluna da heurística.
4. Cada avaliador commita apenas o próprio arquivo, citando a própria Issue.
5. Depois do commit, o arquivo individual não é alterado. O kappa de Fleiss é calculado sobre esses arquivos, e o consenso fica em um arquivo separado.

Dúvida sobre o protocolo durante a rotulagem não é resolvida com os colegas: o avaliador aplica a regra de dúvida da dimensão e registra o caso em `observacao`.

## 6. Consenso e desempate

O consenso é definido depois que as três planilhas estão commitadas e o kappa foi calculado.

| Situação | Rótulo de consenso |
|---|---|
| Os três concordam (3-0) | O rótulo comum |
| Dois concordam (2-1) | O rótulo da maioria |
| Os três divergem (1-1-1) | Decidido na reunião de consenso, com base nos critérios da seção 4 |

O caso 1-1-1 só ocorre em `tipo_projeto` e `entregas_reais`; `corretiva` tem dois valores e sempre tem maioria.

Na reunião, cada avaliador apresenta a evidência que usou, e o grupo aplica os critérios deste documento. Se não houver acordo, o rótulo é `outro` em `tipo_projeto` e `incerto` em `entregas_reais`. O arquivo de consenso registra, para cada item, a situação (3-0, 2-1 ou 1-1-1) e, nos casos 1-1-1, a justificativa da decisão.

## 7. Coluna `observacao`

A coluna é preenchida quando:

- o rótulo foi dado pela regra de dúvida, e não por evidência direta;
- `entregas_reais` é `incerto`;
- a página da release ou a comparação não abriu;
- o caso não está previsto neste protocolo.

O texto diz o que faltou ou o que gerou a dúvida, em uma frase. Os casos não previstos são levados à reunião de consenso e relatados no artigo como limitação do protocolo.
