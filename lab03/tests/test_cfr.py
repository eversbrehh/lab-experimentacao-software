from datetime import date, datetime, timedelta, timezone

import pytest

from metricas.cfr import cfr_ci, cfr_entrega

FIM = date(2026, 6, 30)


def runs(*conclusoes):
    return [{"id": i, "workflow_id": 1, "conclusion": c} for i, c in enumerate(conclusoes)]


def test_cfr_e_falhas_sobre_falhas_mais_sucessos():
    assert cfr_ci(runs("success", "success", "success", "failure")) == pytest.approx(0.25)


@pytest.mark.parametrize("falha", ["failure", "timed_out", "startup_failure"])
def test_os_tres_tipos_de_falha_contam(falha):
    assert cfr_ci(runs("success", falha)) == 0.5


def test_runs_ignorados_nao_entram_na_conta():
    ignorados = ["cancelled", "skipped", "neutral", "action_required", "stale", None, ""]

    assert cfr_ci(runs("success", "failure", *ignorados)) == 0.5


def test_repositorio_sem_falhas_tem_cfr_zero():
    assert cfr_ci(runs("success", "success")) == 0.0


def test_so_falhas_da_cfr_um():
    assert cfr_ci(runs("failure", "timed_out")) == 1.0


def test_sem_runs_ou_so_ignorados_o_cfr_e_indefinido():
    assert cfr_ci([]) is None
    assert cfr_ci(runs("cancelled", "skipped", None)) is None


def test_todos_os_workflows_entram_juntos():
    mistos = [
        {"workflow_id": 1, "conclusion": "success"},
        {"workflow_id": 1, "conclusion": "success"},
        {"workflow_id": 2, "conclusion": "failure"},
        {"workflow_id": 3, "conclusion": "success"},
    ]

    assert cfr_ci(mistos) == pytest.approx(0.25)


def test_run_sem_a_chave_conclusion_e_ignorado():
    assert cfr_ci([{"id": 1}, {"id": 2, "conclusion": "success"}]) == 0.0


# CFR (b): proxy de entrega


def deploy(tag, quando, mensagens=()):
    return {"tag_name": tag, "published_at": quando, "mensagens": list(mensagens)}


def dia(dia, mes=6, hora=12):
    return datetime(2026, mes, dia, hora, tzinfo=timezone.utc)


@pytest.fixture
def exemplo_rq03(fixture_json):
    return [
        {**item, "published_at": datetime.fromisoformat(item["published_at"])}
        for item in fixture_json("corretiva")["exemplo_rq03"]
    ]


def test_exemplo_rq03_so_v2_3_0_falha_entre_quatro_avaliadas(exemplo_rq03):
    assert cfr_entrega(exemplo_rq03, FIM) == pytest.approx(0.25)


def test_exemplo_rq03_v2_4_0_seguida_por_v2_5_0_nao_falha(exemplo_rq03):
    v2_4_0, v2_5_0 = exemplo_rq03[2:]

    assert cfr_entrega([v2_4_0, v2_5_0], FIM) == 0.0


def test_correcao_em_exatamente_7_dias_conta_como_falha():
    releases = [deploy("v1.0.0", dia(1)), deploy("v1.0.1", dia(8))]

    assert cfr_entrega(releases, FIM) == 0.5


def test_correcao_depois_de_7_dias_nao_conta():
    releases = [deploy("v1.0.0", dia(1)), deploy("v1.0.1", dia(8) + timedelta(seconds=1))]

    assert cfr_entrega(releases, FIM) == 0.0


def test_so_a_release_seguinte_e_considerada():
    releases = [deploy("v1.0.0", dia(1)), deploy("v1.1.0", dia(2), ["feat: x"]), deploy("v1.1.1", dia(3))]

    # v1.0.0 é seguida por v1.1.0 (não corretiva); v1.1.0 é seguida por v1.1.1 (corretiva).
    assert cfr_entrega(releases, FIM) == pytest.approx(1 / 3)


def test_a_correcao_e_julgada_em_relacao_a_release_avaliada():
    releases = [deploy("v1.1.0", dia(1)), deploy("v1.0.5", dia(2), ["feat: backport"])]

    assert cfr_entrega(releases, FIM) == 0.0


def test_entrada_fora_de_ordem_e_ordenada_por_data(exemplo_rq03):
    assert cfr_entrega(list(reversed(exemplo_rq03)), FIM) == pytest.approx(0.25)


def test_release_no_ultimo_dia_avaliavel_entra_no_denominador():
    # fim = 30/06: a release de 23/06 23:59:59 tem os 7 dias seguintes dentro da janela.
    assert cfr_entrega([deploy("v1.0.0", datetime(2026, 6, 23, 23, 59, 59, tzinfo=timezone.utc))], FIM) == 0.0


def test_release_nos_ultimos_7_dias_e_censurada():
    releases = [deploy("v1.0.0", dia(10)), deploy("v1.0.1", dia(24, hora=0)), deploy("v1.0.2", dia(30))]

    # Só v1.0.0 é avaliada (e não falhou, porque v1.0.1 sai 13,5 dias depois).
    assert cfr_entrega(releases, FIM) == 0.0


def test_release_censurada_ainda_serve_de_correcao_para_a_anterior():
    releases = [deploy("v1.0.0", dia(20)), deploy("v1.0.1", dia(25))]

    assert cfr_entrega(releases, FIM) == 1.0


def test_censura_respeita_o_fuso():
    # 23/06 21:00 em -03:00 é 24/06 00:00 UTC, já nos últimos 7 dias da janela.
    quando = datetime(2026, 6, 23, 21, tzinfo=timezone(timedelta(hours=-3)))

    assert cfr_entrega([deploy("v1.0.0", quando)], FIM) is None


def test_repositorio_com_uma_unica_release_avaliavel_tem_cfr_zero():
    assert cfr_entrega([deploy("v1.0.0", dia(1))], FIM) == 0.0


def test_sem_releases_o_cfr_e_indefinido():
    assert cfr_entrega([], FIM) is None


def test_so_releases_censuradas_o_cfr_e_indefinido():
    releases = [deploy("v1.0.0", dia(25)), deploy("v1.0.1", dia(26))]

    assert cfr_entrega(releases, FIM) is None


def test_todas_falham():
    releases = [deploy("v1.0.0", dia(1)), deploy("v1.0.1", dia(2)), deploy("v1.0.2", dia(3), ["fix: z"])]

    # A última (03/06) é avaliada e não tem seguinte: 2 falhas em 3.
    assert cfr_entrega(releases, FIM) == pytest.approx(2 / 3)
