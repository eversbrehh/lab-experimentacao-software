from datetime import date, datetime

import pytest

from metricas.classificacao import classificar
from metricas.frequencia import deploys_na_janela, frequencia_deploy
from metricas.janela import semanas
from metricas.lead_time import lead_time_por_commit, lead_time_por_release
from metricas.sensibilidade import classificar_combinacao, percentual_mudanca

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)


@pytest.fixture
def repo(fixture_json):
    """Repositório fictício de `fixtures/sensibilidade.json`, com as datas já convertidas."""
    dados = fixture_json("sensibilidade")

    def data(texto):
        return texto and datetime.fromisoformat(texto)

    for release in dados["releases"]:
        release["published_at"] = data(release["published_at"])
    for combinacao in ("c1", "c2", "c3"):
        dados[combinacao] = [
            {"published_at": data(item["published_at"]), "commits": [data(c) for c in item["commits"]]}
            for item in dados[combinacao]
        ]
    return dados


# fixture calculada à mão (os passos estão em `_calculo_manual` no JSON)


def test_frequencias_das_tres_combinacoes(repo):
    esperado = repo["esperado"]
    pre = [r for r in deploys_na_janela(repo["releases"], INICIO, FIM, incluir_prereleases=True) if r["prerelease"]]

    assert len(deploys_na_janela(repo["releases"], INICIO, FIM)) == esperado["n_deploys_c1"]
    assert len(pre) == esperado["n_prereleases"]
    assert frequencia_deploy(repo["releases"], INICIO, FIM) == pytest.approx(esperado["frequencia_semana"])
    assert frequencia_deploy(repo["releases"], INICIO, FIM, incluir_prereleases=True) == pytest.approx(
        esperado["frequencia_semana_c2"]
    )
    assert len(repo["c3"]) == esperado["n_tags_janela"]
    assert len(repo["c3"]) / semanas(INICIO, FIM) == pytest.approx(esperado["frequencia_semana_c3"])


def test_lead_times_das_tres_combinacoes(repo):
    esperado = repo["esperado"]

    assert lead_time_por_release(repo["c1"]) == esperado["lead_time_a_h"]
    assert lead_time_por_commit(repo["c1"]) == esperado["lead_time_b_h"]
    assert lead_time_por_commit(repo["c2"]) == esperado["lead_time_b_h_c2"]
    assert lead_time_por_commit(repo["c3"]) == esperado["lead_time_b_h_c3"]


def test_categorias_das_tres_combinacoes(repo):
    esperado = repo["esperado"]
    recuperacao = repo["recuperacao_mediana_h"]
    c1 = {
        "frequencia_semana": frequencia_deploy(repo["releases"], INICIO, FIM),
        "lead_time_h": lead_time_por_release(repo["c1"]),
        "cfr": repo["cfr_a"],
        "recuperacao_h": recuperacao,
    }
    c2 = {
        "frequencia_semana": frequencia_deploy(repo["releases"], INICIO, FIM, incluir_prereleases=True),
        "lead_time_h": lead_time_por_commit(repo["c2"]),
        "cfr": None,  # CFR (b) depende da #158
        "recuperacao_h": recuperacao,
    }
    c3 = {
        "frequencia_semana": len(repo["c3"]) / semanas(INICIO, FIM),
        "lead_time_h": lead_time_por_commit(repo["c3"]),
        "cfr": repo["cfr_a"],
        "recuperacao_h": recuperacao,
    }

    assert classificar_combinacao(c1) == esperado["categoria_c1"]
    assert classificar_combinacao(c2) == esperado["categoria_c2"]
    assert classificar_combinacao(c3) == esperado["categoria_c3"]


# classificar_combinacao


def test_classificar_combinacao_e_a_mesma_regra_de_c1():
    metricas = {"frequencia_semana": 0.5, "lead_time_h": 48, "cfr": 0.6, "recuperacao_h": 0.5}

    assert classificar_combinacao(metricas) == classificar(0.5, 48, 0.6, 0.5)[0]


def test_classificar_combinacao_sem_metricas_devolve_none():
    vazias = {"frequencia_semana": None, "lead_time_h": None, "cfr": None, "recuperacao_h": None}

    assert classificar_combinacao(vazias) is None


def test_classificar_combinacao_repassa_as_semanas_da_janela():
    # 0,5 deploy/semana: Medium numa janela de 1 ano, Low numa de 12 semanas (corte = 1/semana)
    metricas = {"frequencia_semana": 0.5, "lead_time_h": None, "cfr": None, "recuperacao_h": None}

    assert classificar_combinacao(metricas) == "Medium"
    assert classificar_combinacao({**metricas, "semanas_janela": 12}) == "Low"


def test_classificar_combinacao_recusa_chave_ausente():
    with pytest.raises(KeyError):
        classificar_combinacao({"frequencia_semana": 1, "lead_time_h": 1, "cfr": 0.1})


def test_classificar_combinacao_recusa_chave_desconhecida():
    metricas = {"frequencia_semana": 1, "lead_time_b_h": 1, "lead_time_h": 1, "cfr": 0.1, "recuperacao_h": 1}

    with pytest.raises(KeyError, match="lead_time_b_h"):
        classificar_combinacao(metricas)


# percentual_mudanca


def test_percentual_mudanca_conta_pares_diferentes():
    assert percentual_mudanca(["Elite", "High", "Medium", "Low"], ["Elite", "Medium", "Medium", "High"]) == 50


def test_percentual_mudanca_identicas_e_todas_diferentes():
    assert percentual_mudanca(["High", "Low"], ["High", "Low"]) == 0
    assert percentual_mudanca(["High", "Low"], ["Low", "High"]) == 100


def test_percentual_mudanca_ignora_pares_com_none():
    # só os pares 1 e 4 entram: 1 mudança em 2
    assert percentual_mudanca(["High", None, "Low", "Medium"], ["High", "Low", None, "Elite"]) == 50


def test_percentual_mudanca_com_tamanhos_diferentes_levanta_erro():
    with pytest.raises(ValueError):
        percentual_mudanca(["High"], ["High", "Low"])


@pytest.mark.parametrize("cat_x, cat_y", [([], []), ([None, "High"], ["Low", None])])
def test_percentual_mudanca_sem_par_valido_levanta_erro(cat_x, cat_y):
    with pytest.raises(ValueError):
        percentual_mudanca(cat_x, cat_y)
