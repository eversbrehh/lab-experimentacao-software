"""Coleta dos workflow runs do default branch (`event=push`) na janela.

A API limita cada consulta a 1.000 resultados. Por isso a janela é dividida em meses;
um mês que atinge o teto é refeito dia a dia, e um dia que atinge o teto é refeito hora a
hora. Uma hora que ainda atinge o teto gera um aviso (a coleta daquela hora fica truncada).

As fatias de cada nível são consultadas por `cliente_http.mapear`, em paralelo quando o
cliente está configurado para isso.
"""

import calendar
import logging
from datetime import date, datetime, timedelta

from metricas.janela import dentro_da_janela
from pipeline import cliente_http

LIMITE_DA_API = 1000
# Só estes campos de cada run vão para o cache: a resposta completa da API tem cerca de
# 40 KB por run, o que esgota memória e disco em repositórios com muitos runs.
CAMPOS = ("id", "workflow_id", "conclusion", "created_at", "run_started_at", "updated_at")

log = logging.getLogger(__name__)


def dividir_em_meses(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Fatias por mês-calendário, recortadas pelos limites da janela."""
    if fim < inicio:
        raise ValueError("fim não pode ser anterior ao início")
    fatias = []
    atual = inicio
    while atual <= fim:
        ultimo_dia = date(atual.year, atual.month, calendar.monthrange(atual.year, atual.month)[1])
        fatias.append((atual, min(ultimo_dia, fim)))
        atual = ultimo_dia + timedelta(days=1)
    return fatias


def coletar_runs(owner: str, repo: str, branch: str, inicio: date, fim: date) -> list[dict]:
    """Runs criados em [inicio, fim] no `branch`, ordenados por `created_at`.

    Cada item traz `id`, `workflow_id`, `conclusion` (texto ou `None`) e
    `created_at`, `run_started_at`, `updated_at` como `datetime` em UTC.
    """

    def consultar(intervalo: str) -> list[dict]:
        return _consultar(owner, repo, branch, intervalo)

    meses = [(ini, fim_mes, _intervalo_de_dias(ini, fim_mes)) for ini, fim_mes in dividir_em_meses(inicio, fim)]
    brutos, meses_cheios = _coletar(consultar, meses)

    dias = []
    for ini, fim_mes, _ in meses_cheios:
        dia = ini
        while dia <= fim_mes:
            dias.append((dia, dia, _intervalo_de_dias(dia, dia)))
            dia += timedelta(days=1)
    dos_dias, dias_cheios = _coletar(consultar, dias)
    brutos.extend(dos_dias)

    horas = [(dia, hora, _intervalo_da_hora(dia, hora)) for dia, _, _ in dias_cheios for hora in range(24)]
    das_horas, horas_cheias = _coletar(consultar, horas, manter_cheias=True)
    brutos.extend(das_horas)
    for dia, hora, _ in horas_cheias:
        log.warning(
            "%s/%s: %s às %02d h atingiu %d runs; coleta da hora truncada", owner, repo, dia, hora, LIMITE_DA_API
        )

    runs = {}
    for bruto in brutos:
        run = _normalizar(bruto)
        if dentro_da_janela(run["created_at"], inicio, fim):
            runs[run["id"]] = run
    return sorted(runs.values(), key=lambda run: (run["created_at"], run["id"]))


def _coletar(consultar, fatias: list[tuple], manter_cheias: bool = False) -> tuple[list[dict], list[tuple]]:
    """Consulta cada fatia e separa as que atingiram o teto da API.

    Cada fatia é uma tupla cujo último elemento é o intervalo de `created`. Devolve os
    runs das fatias abaixo do teto e a lista das fatias cheias, que precisam ser refeitas
    em intervalos menores. Com `manter_cheias`, os runs das fatias cheias também são
    devolvidos (último nível de subdivisão).
    """
    resultados = cliente_http.mapear(lambda fatia: consultar(fatia[-1]), fatias)
    itens, cheias = [], []
    for fatia, da_fatia in zip(fatias, resultados):
        cheia = len(da_fatia) >= LIMITE_DA_API
        if cheia:
            cheias.append(fatia)
        if not cheia or manter_cheias:
            itens.extend(da_fatia)
    return itens, cheias


def _intervalo_de_dias(inicio: date, fim: date) -> str:
    return f"{inicio.isoformat()}..{fim.isoformat()}"


def _intervalo_da_hora(dia: date, hora: int) -> str:
    return f"{dia.isoformat()}T{hora:02d}:00:00Z..{dia.isoformat()}T{hora:02d}:59:59Z"


def _consultar(owner: str, repo: str, branch: str, intervalo: str) -> list[dict]:
    params = {"branch": branch, "event": "push", "created": intervalo}
    return cliente_http.get_paginado(
        f"/repos/{owner}/{repo}/actions/runs", params, chave="workflow_runs", campos=CAMPOS
    )


def _normalizar(bruto: dict) -> dict:
    criado = _data(bruto["created_at"])
    return {
        "id": bruto["id"],
        "workflow_id": bruto["workflow_id"],
        "conclusion": bruto.get("conclusion") or None,
        "created_at": criado,
        "run_started_at": _data(bruto["run_started_at"]) if bruto.get("run_started_at") else criado,
        "updated_at": _data(bruto["updated_at"]),
    }


def _data(texto: str) -> datetime:
    return datetime.fromisoformat(texto)
