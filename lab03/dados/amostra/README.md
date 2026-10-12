# Amostra prevista (sondagem de 11/10/2026)

Lista dos repositórios que devem compor a amostra de 300, obtida antes do download completo dos workflow runs. Serve de base para o sorteio da amostra-ouro e para dividir a coleta entre os integrantes. **É uma previsão:** a amostra final é a que o pipeline grava em `dados/saida/repositorios.csv`.

## Como foi gerada

Os candidatos da faixa `stars:>10000` foram percorridos por estrelas decrescentes, na mesma ordem do pipeline, até 330 aprovados previstos (774 candidatos). Para cada um foram consultados:

- uso de GitHub Actions e a lista de releases, com as mesmas funções do pipeline (`selecao.usa_actions`, `releases.coletar_releases`, `funil.aprovado`);
- a contagem de runs de `push` no *default branch* na janela, por `status` (`success` e `failure`; `timed_out` e `startup_failure` quando a soma ficava abaixo de 50), sem baixar os runs.

O critério é o do funil: ao menos 5 deploys e ao menos 50 runs válidos na janela de 01/10/2025 a 30/09/2026.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `sondagem.csv` | Os 774 candidatos examinados, com o resultado previsto de cada um |
| `amostra_prevista.csv` | Os 300 primeiros aprovados previstos, em ordem de estrelas (`ordem` de 1 a 300) |

| `fatia-1.txt`, `fatia-2.txt`, `fatia-3.txt` | Os 300 repositórios divididos em três listas para a coleta em paralelo, um `owner/repo` por linha, no formato do `--repos` |
| `reservas.txt` | Os aprovados previstos de 301 a 330, para coletar só se algum dos 300 sair da amostra |

`posicao` é a posição do candidato na busca por estrelas. `runs_validos_previstos` vem das contagens da API, que param em 2.500 por `status`: valores de 2.500 ou 5.000 indicam "pelo menos isso", não o total.

## Coleta dividida

As fatias foram equilibradas pelo custo estimado em requisições (páginas de runs e `compare` por deploy), não pela quantidade de repositórios, e cada uma está em ordem de estrelas. A `fatia-1` inclui os cinco repositórios já coletados no teste de 12/10.

| Fatia | Repositórios | Com algum mês no teto de 2.500 runs | Mais caro |
|---|---|---|---|
| `fatia-1.txt` | 102 | 14 | `ggml-org/llama.cpp` |
| `fatia-2.txt` | 99 | 12 | `TanStack/query` |
| `fatia-3.txt` | 99 | 11 | `anomalyco/opencode` |

Cada integrante roda a sua fatia com o próprio token e envia a pasta `dados/cache/`; o passo a passo está na seção "Coleta dividida entre máquinas" do [README do Lab03](../../README.md). A execução final, sem `--repos`, deve ser feita na máquina que tem o cache da sondagem, porque ela também percorre os candidatos descartados.

## Limites

- Um repositório previsto pode sair da amostra final se a API falhar durante o download. Nesse caso entra o próximo aprovado previsto de `sondagem.csv`.
- A lista é fixa: o sorteio da amostra-ouro deve usar `amostra_prevista.csv` como está, uma única vez. Alterar o número ou a ordem das linhas muda o resultado de `df.sample`.
