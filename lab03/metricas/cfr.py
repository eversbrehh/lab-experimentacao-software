"""CFR (RQ 03): variante (a), proporção de workflow runs com falha; variante (b), proporção
de releases seguidas por uma release corretiva."""

from datetime import date, datetime, time, timedelta, timezone

from metricas.conclusao import FALHA, SUCESSO, classificar_conclusao
from metricas.corretiva import eh_corretiva

PRAZO_CORRECAO = timedelta(days=7)


def cfr_ci(runs: list[dict]) -> float | None:
    """`falhas ÷ (falhas + sucessos)`, com todos os workflows juntos.

    Runs ignorados (`cancelled`, `skipped`, em andamento etc.) não entram. Devolve `None`
    quando não há nenhum run de sucesso ou falha.
    """
    classes = [classificar_conclusao(run.get("conclusion")) for run in runs]
    falhas = classes.count(FALHA)
    total = falhas + classes.count(SUCESSO)
    return falhas / total if total else None


def cfr_entrega(releases: list[dict], fim: date) -> float | None:
    """`releases que falharam ÷ releases avaliadas`, com os deploys da janela.

    `releases` segue o formato de `metricas.corretiva.eh_corretiva` e é ordenada aqui por
    `published_at`. R falhou quando a release seguinte saiu em até 7 dias depois de R
    (inclusive) e é corretiva em relação a R.

    Censura: R só é avaliada quando os 7 dias seguintes cabem na janela, isto é,
    `published_at + 7 dias ≤ fim 23:59:59.999999 UTC`; as demais ficam fora do denominador.
    Devolve `None` quando nenhuma release é avaliável.
    """
    limite = datetime.combine(fim, time.max, tzinfo=timezone.utc)
    ordenadas = sorted(releases, key=lambda release: release["published_at"])
    avaliadas = falhas = 0
    for posicao, release in enumerate(ordenadas):
        if release["published_at"] + PRAZO_CORRECAO > limite:
            continue
        avaliadas += 1
        seguinte = ordenadas[posicao + 1] if posicao + 1 < len(ordenadas) else None
        if (
            seguinte is not None
            and seguinte["published_at"] - release["published_at"] <= PRAZO_CORRECAO
            and eh_corretiva(seguinte, release)
        ):
            falhas += 1
    return falhas / avaliadas if avaliadas else None
