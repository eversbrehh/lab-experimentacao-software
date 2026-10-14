"""Sensibilidade da classificação DORA às definições operacionais (RQ 07).

Cada combinação (C1, C2, C3) tem a sua unidade de deploy e as suas variantes de lead time e
CFR; a categoria geral usa a mesma tabela e a mesma regra da mediana das notas de
`metricas.classificacao`.
"""

from metricas.classificacao import SEMANAS_DA_JANELA, classificar

METRICAS = ("frequencia_semana", "lead_time_h", "cfr", "recuperacao_h")


def classificar_combinacao(metricas: dict) -> str | None:
    """Categoria geral de uma combinação; `None` quando nenhuma métrica está definida.

    `metricas` traz as quatro chaves de `METRICAS` (valor `None` = métrica indefinida) e,
    opcionalmente, `semanas_janela`. Chave ausente ou desconhecida levanta `KeyError`, para
    que um nome trocado não vire uma métrica indefinida sem aviso.
    """
    desconhecidas = set(metricas) - set(METRICAS) - {"semanas_janela"}
    if desconhecidas:
        raise KeyError(f"chaves desconhecidas: {sorted(desconhecidas)}")
    categoria, _ = classificar(
        *(metricas[nome] for nome in METRICAS), metricas.get("semanas_janela", SEMANAS_DA_JANELA)
    )
    return categoria


def percentual_mudanca(cat_x: list, cat_y: list) -> float:
    """Percentual (0 a 100) de repositórios com categoria diferente entre duas combinações.

    As listas são pareadas pela posição (mesmo repositório). Pares com `None` em qualquer
    lado ficam fora. Listas de tamanhos diferentes ou sem nenhum par válido levantam
    `ValueError`.
    """
    if len(cat_x) != len(cat_y):
        raise ValueError(f"listas de tamanhos diferentes: {len(cat_x)} e {len(cat_y)}")
    pares = [(x, y) for x, y in zip(cat_x, cat_y) if x is not None and y is not None]
    if not pares:
        raise ValueError("nenhum par com as duas categorias definidas")
    return 100 * sum(x != y for x, y in pares) / len(pares)
