"""Validação da heurística de release corretiva frente à amostra-ouro: precisão, recall e F1."""

import math

import numpy as np
from sklearn.metrics import precision_recall_fscore_support


def precisao_recall_f1(previsto: list[bool], real: list[bool]) -> dict:
    """Precisão, recall e F1 da classe positiva (corretiva), com as contagens.

    `previsto` é a saída da heurística e `real` o rótulo do consenso, pareados pela posição.
    Devolve `{"precisao", "recall", "f1", "vp", "fp", "fn"}`; uma métrica indefinida (por
    exemplo, precisão sem nenhum positivo previsto) vale `None`, não 0. O F1 segue o sklearn,
    `2·VP / (2·VP + FP + FN)`: só é indefinido quando não há positivo em nenhuma das listas.
    Listas de tamanhos diferentes levantam `ValueError`.
    """
    if len(previsto) != len(real):
        raise ValueError(f"listas de tamanhos diferentes: {len(previsto)} e {len(real)}")
    pares = list(zip(previsto, real))
    contagens = {
        "vp": sum(p and r for p, r in pares),
        "fp": sum(p and not r for p, r in pares),
        "fn": sum(r and not p for p, r in pares),
    }
    if not pares:
        return {"precisao": None, "recall": None, "f1": None, **contagens}
    # A ordem do sklearn é (real, previsto); `labels=[True]` evita o erro de "classe
    # positiva ausente" quando só há um valor nas duas listas.
    precisao, recall, f1, _ = precision_recall_fscore_support(
        [bool(r) for r in real],
        [bool(p) for p in previsto],
        labels=[True],
        average=None,
        zero_division=np.nan,
    )
    return {
        "precisao": _definida(precisao[0]),
        "recall": _definida(recall[0]),
        "f1": _definida(f1[0]),
        **contagens,
    }


def _definida(valor) -> float | None:
    return None if math.isnan(valor) else float(valor)
