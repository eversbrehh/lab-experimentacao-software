# Registro da coleta por fatia

A coleta dos 300 repositórios foi dividida em três fatias (`dados/amostra/fatia-N.txt`). O plano era cada integrante executar uma fatia com o próprio token; por decisão do grupo, as três foram executadas em sequência na mesma máquina, com um único token. Esta pasta guarda o que cada execução gravou.

**Não é o dataset.** O dataset é `dados/saida/repositorios.csv`, gerado pela execução final, que lê o cache das três fatias. As análises leem só `dados/saida/`.

## Conteúdo

Cada pasta `fatia-N/` tem os dois arquivos gravados por `python -m pipeline --config config.yaml --repos dados/amostra/fatia-N.txt`:

| Arquivo | Conteúdo |
|---|---|
| `funil_subamostra.csv` | Funil dos repositórios da fatia |
| `repositorios_subamostra.csv` | Metadados e métricas dos aprovados da fatia |

| Fatia | Integrante | Execução | Examinados | Aprovados |
|---|---|---|---|---|
| `fatia-1/` | Brenda | 12/10/2026, 19:50, a 13/10/2026, 00:54 | 151 | 102 |
| `fatia-2/` | Brenda | 13/10/2026, 14:16, a 13/10/2026, 20:48 | 99 | 99 |
| `fatia-3/` | Brenda | 13/10/2026, 20:48, a 14/10/2026, 10:15 | 99 | 99 |

A fatia 1 examinou 151 repositórios, e não 102, porque incluiu os 49 candidatos que a sondagem reprovou por "menos de 50 runs" (`dados/amostra/sondagem.csv`). Eles não estão em nenhuma fatia e foram coletados para que a execução final não precise da rede. Os 49 foram reprovados pelo mesmo motivo.

As fatias 2 e 3 foram executadas mais de uma vez. Às 19:28 de 13/10 o Wi-Fi caiu e o pipeline, que ainda tratava falta de conexão como erro da API, descartou os repositórios restantes; as duas fatias foram repetidas pelo cache depois da correção do PR #176. A fatia 3 também foi retomada após uma falta de memória do Windows e após 5 horas de suspensão do computador. Os registros desta pasta são das execuções que terminaram sem nenhum descarte por erro da API.

## Diferenças em relação ao dataset

- `estrelas` é o valor do dia da execução. No dataset, é o valor do dia da busca. Pelo mesmo motivo, `linguagem` pode diferir quando o GitHub a reclassificou nesse intervalo (2 casos).
- O funil de uma fatia começa nos repositórios do arquivo. O funil do dataset começa nos candidatos da busca.
- As demais colunas são calculadas da mesma forma e devem coincidir com as do dataset.
