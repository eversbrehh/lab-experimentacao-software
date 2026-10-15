import math

import pandas as pd
import pytest
from openpyxl import Workbook

from analise import concordancia
from analise.concordancia import (
    ErroDeConcordancia,
    calcular_kappa,
    consolidar,
    interpretar,
    ler_planilha,
    main,
)

TIPOS = ["biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro"]


def escrever_planilha(caminho, repos, releases):
    """repos: [(full_name, tipo, entregas)]; releases: [(full_name, tag, corretiva)]."""
    planilha = Workbook()
    aba = planilha.active
    aba.title = "repositorios"
    aba.append(["full_name", "url", "tipo_projeto", "entregas_reais", "observacao"])
    for nome, tipo, entregas in repos:
        aba.append([nome, f"https://github.com/{nome}", tipo, entregas, None])
    aba = planilha.create_sheet("releases")
    aba.append(["full_name", "tag_name", "url_release", "url_compare", "corretiva", "observacao"])
    for nome, tag, corretiva in releases:
        aba.append([nome, tag, "u", "c", corretiva, None])
    planilha.save(caminho)


def tres_planilhas(pasta, repos_por_avaliador, releases_por_avaliador):
    for n in range(3):
        escrever_planilha(pasta / f"avaliador_{n + 1}.xlsx", repos_por_avaliador[n], releases_por_avaliador[n])


def repos(tipos, entregas):
    return [(f"org/r{i}", t, e) for i, (t, e) in enumerate(zip(tipos, entregas))]


def releases(valores):
    return [(f"org/r{i // 2}", f"v{i}", v) for i, v in enumerate(valores)]


# --- interpretação de Landis e Koch ---


@pytest.mark.parametrize(
    "kappa, esperado",
    [
        (-0.1, "pobre"),
        (0.0, "leve"),
        (0.20, "leve"),
        (0.21, "razoável"),
        (0.40, "razoável"),
        (0.41, "moderada"),
        (0.60, "moderada"),
        (0.61, "substancial"),
        (0.80, "substancial"),
        (0.81, "quase perfeita"),
        (1.0, "quase perfeita"),
    ],
)
def test_interpretar_faixas_de_landis_e_koch(kappa, esperado):
    assert interpretar(kappa) == esperado


def test_interpretar_nan_e_indefinido():
    assert interpretar(float("nan")) == "indefinido"


# --- kappa ---


def test_kappa_e_1_com_concordancia_total():
    rotulos = [["sim", "sim", "sim"], ["não", "não", "não"], ["sim", "sim", "sim"]]
    assert calcular_kappa(rotulos) == pytest.approx(1.0)


def test_kappa_e_negativo_ou_nulo_com_discordancia_total_entre_dois_valores():
    rotulos = [["sim", "sim", "não"], ["não", "não", "sim"], ["sim", "não", "não"], ["não", "sim", "sim"]]
    assert calcular_kappa(rotulos) < 0


def test_kappa_misto_fica_entre_0_e_1():
    rotulos = [["sim", "sim", "sim"], ["não", "não", "não"], ["sim", "sim", "não"], ["não", "não", "sim"]]
    assert 0 < calcular_kappa(rotulos) < 1


def test_kappa_com_uma_unica_categoria_e_nan():
    rotulos = [["não", "não", "não"], ["não", "não", "não"]]
    assert math.isnan(calcular_kappa(rotulos))


# --- leitura das planilhas ---


def test_ler_planilha_devolve_repositorios_e_releases(tmp_path):
    caminho = tmp_path / "a.xlsx"
    escrever_planilha(caminho, repos(TIPOS[:2], ["sim", "não"]), releases(["sim", "não"]))
    reps, rels = ler_planilha(str(caminho), 1)
    assert list(reps["tipo_projeto"]) == TIPOS[:2]
    assert list(rels["corretiva"]) == ["sim", "não"]


def test_rotulo_vazio_falha_com_linha_e_avaliador(tmp_path):
    caminho = tmp_path / "a.xlsx"
    escrever_planilha(caminho, repos(TIPOS[:2], ["sim", None]), releases(["sim", "não"]))
    with pytest.raises(ErroDeConcordancia) as erro:
        ler_planilha(str(caminho), 2)
    mensagem = str(erro.value)
    assert "avaliador 2" in mensagem and "linha 3" in mensagem and "entregas_reais" in mensagem


def test_rotulo_fora_dos_valores_aceitos_falha_com_linha_e_avaliador(tmp_path):
    caminho = tmp_path / "a.xlsx"
    escrever_planilha(caminho, repos(TIPOS[:1], ["sim"]), releases(["sim", "talvez"]))
    with pytest.raises(ErroDeConcordancia) as erro:
        ler_planilha(str(caminho), 3)
    mensagem = str(erro.value)
    assert "avaliador 3" in mensagem and "linha 3" in mensagem and "talvez" in mensagem


def test_planilha_inexistente_falha_com_mensagem(tmp_path):
    with pytest.raises(ErroDeConcordancia, match="avaliador_1"):
        ler_planilha(str(tmp_path / "avaliador_1.xlsx"), 1)


# --- consolidação ---


def montar(pasta, tipos, entregas, corretivas):
    """tipos/entregas: três listas (uma por avaliador); corretivas: três listas."""
    tres_planilhas(
        pasta,
        [repos(tipos[n], entregas[n]) for n in range(3)],
        [releases(corretivas[n]) for n in range(3)],
    )
    return [ler_planilha(str(pasta / f"avaliador_{n + 1}.xlsx"), n + 1) for n in range(3)]


def test_consolidar_calcula_as_tres_dimensoes(tmp_path):
    lidas = montar(
        tmp_path,
        [TIPOS[:3]] * 3,
        [["sim", "não", "incerto"]] * 3,
        [["sim", "não", "sim", "não"]] * 3,
    )
    kappa, divergencias, consenso = consolidar(lidas)
    assert list(kappa["dimensao"]) == ["tipo_projeto", "entregas_reais", "corretiva"]
    assert list(kappa["kappa"]) == pytest.approx([1.0, 1.0, 1.0])
    assert list(kappa["interpretacao"]) == ["quase perfeita"] * 3
    assert divergencias.empty
    assert set(consenso["situacao"]) == {"3-0"}
    assert not consenso["reuniao"].any()


def test_consenso_usa_a_maioria_em_2_1_e_lista_a_divergencia(tmp_path):
    lidas = montar(
        tmp_path,
        [["outro", "outro"], ["outro", "ferramenta CLI"], ["outro", "outro"]],
        [["sim", "sim"]] * 3,
        [["sim", "sim"]] * 3,
    )
    _, divergencias, consenso = consolidar(lidas)
    linha = consenso[(consenso["dimensao"] == "tipo_projeto") & (consenso["full_name"] == "org/r1")].iloc[0]
    assert linha["situacao"] == "2-1"
    assert linha["consenso"] == "outro"
    assert not linha["reuniao"]
    assert len(divergencias) == 1
    assert divergencias.iloc[0]["avaliador_2"] == "ferramenta CLI"


def test_caso_1_1_1_fica_marcado_para_a_reuniao_sem_consenso(tmp_path):
    lidas = montar(
        tmp_path,
        [["outro"], ["ferramenta CLI"], ["biblioteca/framework"]],
        [["sim"]] * 3,
        [["sim", "sim"]] * 3,
    )
    _, divergencias, consenso = consolidar(lidas)
    linha = consenso[consenso["dimensao"] == "tipo_projeto"].iloc[0]
    assert linha["situacao"] == "1-1-1"
    assert linha["reuniao"]
    assert pd.isna(linha["consenso"]) or linha["consenso"] == ""
    assert (divergencias["situacao"] == "1-1-1").sum() == 1


def test_corretiva_nunca_gera_1_1_1(tmp_path):
    lidas = montar(
        tmp_path,
        [["outro"]] * 3,
        [["sim"]] * 3,
        [["sim", "não"], ["não", "sim"], ["sim", "sim"]],
    )
    _, _, consenso = consolidar(lidas)
    assert "1-1-1" not in set(consenso[consenso["dimensao"] == "corretiva"]["situacao"])


def test_itens_diferentes_entre_planilhas_falham(tmp_path):
    escrever_planilha(tmp_path / "avaliador_1.xlsx", repos(TIPOS[:2], ["sim", "sim"]), releases(["sim"]))
    escrever_planilha(tmp_path / "avaliador_2.xlsx", repos(TIPOS[:2], ["sim", "sim"]), releases(["sim"]))
    escrever_planilha(tmp_path / "avaliador_3.xlsx", repos(TIPOS[:1], ["sim"]), releases(["sim"]))
    lidas = [ler_planilha(str(tmp_path / f"avaliador_{n}.xlsx"), n) for n in (1, 2, 3)]
    with pytest.raises(ErroDeConcordancia, match="avaliador 3"):
        consolidar(lidas)


# --- linha de comando ---


def test_main_grava_os_tres_csvs(tmp_path, capsys):
    tres_planilhas(
        tmp_path,
        [repos(TIPOS[:3], ["sim", "não", "incerto"])] * 3,
        [releases(["sim", "não", "sim", "não"])] * 3,
    )
    assert main(["--pasta", str(tmp_path)]) == 0
    kappa = pd.read_csv(tmp_path / "kappa.csv")
    assert list(kappa.columns) == ["dimensao", "kappa", "interpretacao"]
    assert len(kappa) == 3
    assert (tmp_path / "divergencias.csv").exists()
    assert (tmp_path / "consenso.csv").exists()


def test_main_com_rotulo_invalido_sai_com_erro_e_nao_grava(tmp_path, capsys):
    tres_planilhas(
        tmp_path,
        [repos(TIPOS[:1], ["sim"]), repos(TIPOS[:1], [None]), repos(TIPOS[:1], ["sim"])],
        [releases(["sim", "não"])] * 3,
    )
    assert main(["--pasta", str(tmp_path)]) == 1
    assert "avaliador 2" in capsys.readouterr().err
    assert not (tmp_path / "kappa.csv").exists()


def test_main_expoe_o_modulo_executavel():
    assert hasattr(concordancia, "main")
