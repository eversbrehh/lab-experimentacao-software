# Registro da coleta por fatia

A coleta dos 300 repositórios foi dividida em três fatias (`dados/amostra/fatia-N.txt`), cada uma executada por um integrante com o próprio token. Esta pasta guarda o que cada execução gravou, como registro de quem coletou o quê.

**Não é o dataset.** O dataset é `dados/saida/repositorios.csv`, gerado pela execução final, que junta os três caches. As análises leem só `dados/saida/`.

## Conteúdo

Cada pasta `fatia-N/` tem os dois arquivos gravados por `python -m pipeline --config config.yaml --repos dados/amostra/fatia-N.txt`:

| Arquivo | Conteúdo |
|---|---|
| `funil_subamostra.csv` | Funil dos repositórios da fatia |
| `repositorios_subamostra.csv` | Metadados e métricas dos aprovados da fatia |

| Fatia | Integrante | Execução | Examinados | Aprovados |
|---|---|---|---|---|
| `fatia-1/` | Brenda | 12/10/2026, 19:50, a 13/10/2026, 00:54 | 151 | 102 |

A fatia 1 examinou 151 repositórios, e não 102, porque incluiu os 49 candidatos que a sondagem reprovou por "menos de 50 runs" (`dados/amostra/sondagem.csv`). Eles não estão em nenhuma fatia e foram coletados para que a execução final não precise da rede. Os 49 foram reprovados pelo mesmo motivo.

## Diferenças em relação ao dataset

- `estrelas` é o valor do dia da execução. No dataset, é o valor do dia da busca.
- O funil de uma fatia começa nos repositórios do arquivo. O funil do dataset começa nos candidatos da busca.
- As demais colunas são calculadas da mesma forma e devem coincidir com as do dataset.
