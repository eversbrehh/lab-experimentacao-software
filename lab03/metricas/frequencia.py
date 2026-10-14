"""Frequência de deploy (RQ 01): releases publicadas por semana."""

from datetime import date

from metricas.janela import dentro_da_janela, semanas


def deploys_na_janela(
    releases: list[dict], inicio: date, fim: date, incluir_prereleases: bool = False
) -> list[dict]:
    """Releases que contam como deploy: `draft` e `prerelease` falsos e `published_at` na janela.

    Com `incluir_prereleases`, as pré-releases também contam (C2 da RQ 07).
    """
    return [
        release
        for release in releases
        if not release["draft"]
        and (incluir_prereleases or not release["prerelease"])
        and release["published_at"] is not None
        and dentro_da_janela(release["published_at"], inicio, fim)
    ]


def frequencia_deploy(releases: list[dict], inicio: date, fim: date, incluir_prereleases: bool = False) -> float:
    """Deploys na janela divididos pelas semanas da janela, em deploys por semana."""
    return len(deploys_na_janela(releases, inicio, fim, incluir_prereleases)) / semanas(inicio, fim)
