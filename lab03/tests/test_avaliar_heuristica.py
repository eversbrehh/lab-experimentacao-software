import csv

import pytest

from analise import avaliar_heuristica as avaliacao
from analise.avaliar_heuristica import ErroDeAvaliacao

CONSENSO = [
    "dimensao", "full_name", "tag_name", "avaliador_1", "avaliador_2", "avaliador_3",
    "situacao", "consenso", "reuniao", "justificativa",
]  # fmt: skip
OURO = ["ordem_sorteio", "papel", "full_name", "tag_name", "published_at", "url_release", "url_compare"]


def gravar(pasta, nome, colunas, linhas):
    with open(pasta / nome, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def linha_consenso(repo, tag, rotulo, dimensao="corretiva"):
    return {"dimensao": dimensao, "full_name": repo, "tag_name": tag, "consenso": rotulo}


def linha_ouro(repo, tag, base, papel="amostra"):
    url = f"https://github.com/{repo}/compare/{base}...{tag}" if base else ""
    return {"ordem_sorteio": 1, "papel": papel, "full_name": repo, "tag_name": tag, "url_compare": url}


@pytest.fixture
def pasta(tmp_path):
    gravar(
        tmp_path, "consenso.csv", CONSENSO,
        [
            linha_consenso("o/a", "v1.0.1", "sim"),  # só o patch muda: a heurística acerta
            linha_consenso("o/a", "v1.1.0", "não"),  # sem palavra-chave: acerta
            linha_consenso("o/b", "v2.0.0", "sim"),  # corretiva real, sem patch nem palavra-chave: erra (FN)
            linha_consenso("o/b", "v2.1.0", "não"),  # tem fix na mensagem: erra (FP)
            linha_consenso("o/c", "v0.1.0", "não"),  # primeira da história
            linha_consenso("o/a", "", "biblioteca/framework", dimensao="tipo_projeto"),  # outra dimensão
        ],
    )  # fmt: skip
    gravar(
        tmp_path, "amostra_ouro.csv", OURO,
        [
            linha_ouro("o/a", "v1.0.1", "v1.0.0"),
            linha_ouro("o/a", "v1.1.0", "v1.0.1"),
            linha_ouro("o/b", "v2.0.0", "v1.9.0"),
            linha_ouro("o/b", "v2.1.0", "v2.0.0"),
            linha_ouro("o/c", "v0.1.0", ""),
            linha_ouro("o/a", "v9.9.9", "v9.9.8", papel="reserva"),  # reserva: ignorada
        ],
    )  # fmt: skip
    return tmp_path


@pytest.fixture
def api(monkeypatch):
    mensagens = {
        ("v1.0.0", "v1.0.1"): ["fix: crash ao abrir arquivo"],
        ("v1.0.1", "v1.1.0"): ["feat: novo"],
        ("v1.9.0", "v2.0.0"): ["feat: grande mudança"],
        ("v2.0.0", "v2.1.0"): ["fix: erro de digitação"],
    }
    notas = {
        "v1.0.1": "## Bug Fixes\n- Corrige o crash ao abrir arquivo",
        "v1.1.0": "## Features\n- Novo recurso de exportação",
        "v2.0.0": "Release grande, com várias mudanças internas",
        "v2.1.0": "## Bug Fixes\n- Corrige erro de digitação",
        "v0.1.0": "",
    }

    def commits_entre(owner, repo, base, head):
        return [{"sha": "x", "data": None, "mensagem": m} for m in mensagens[(base, head)]]

    monkeypatch.setattr(avaliacao.releases, "commits_entre", commits_entre)
    monkeypatch.setattr(avaliacao.releases, "notas_da_release", lambda owner, repo, tag: notas[tag])
    monkeypatch.setattr(avaliacao.cliente_http, "configurar", lambda *a, **k: None)
    monkeypatch.setattr(avaliacao.cliente_http, "mapear", lambda funcao, itens: [funcao(i) for i in itens])


def test_ler_itens_usa_so_a_dimensao_corretiva_e_so_a_amostra(pasta):
    itens = avaliacao.ler_itens(str(pasta))

    assert [(i["full_name"], i["tag"], i["real"]) for i in itens] == [
        ("o/a", "v1.0.1", True), ("o/a", "v1.1.0", False), ("o/b", "v2.0.0", True),
        ("o/b", "v2.1.0", False), ("o/c", "v0.1.0", False),
    ]  # fmt: skip
    assert itens[0]["base"] == "v1.0.0" and itens[4]["base"] == ""  # primeira release: sem base


def test_previsto_aplica_a_heuristica_com_as_mensagens_do_compare(pasta, api):
    itens = avaliacao.ler_itens(str(pasta))

    assert [avaliacao.previsto(i) for i in itens] == [True, False, False, True, False]


def test_main_grava_precisao_recall_e_f1_da_versao(pasta, api, capsys):
    codigo = avaliacao.main(["--versao", "1", "--pasta", str(pasta), "--cache", str(pasta / "cache")])

    assert codigo == 0
    with open(pasta / "versoes_heuristica.csv", encoding="utf-8", newline="") as arquivo:
        (linha,) = list(csv.DictReader(arquivo))
    assert (linha["versao"], linha["n"], linha["vp"], linha["fp"], linha["fn"]) == ("1", "5", "1", "1", "1")
    assert float(linha["precisao"]) == 0.5 and float(linha["recall"]) == 0.5 and float(linha["f1"]) == 0.5
    assert "F1=0.500" in capsys.readouterr().out


def test_rodar_a_mesma_versao_de_novo_substitui_a_linha_e_mantem_as_outras(pasta, api):
    argumentos = ["--pasta", str(pasta), "--cache", str(pasta / "cache")]
    avaliacao.main(["--versao", "1", *argumentos])
    avaliacao.main(["--versao", "2", "--regra", "outra regra", *argumentos])
    avaliacao.main(["--versao", "1", *argumentos])

    with open(pasta / "versoes_heuristica.csv", encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert [(linha["versao"], linha["regra"] == "outra regra") for linha in linhas] == [("1", False), ("2", True)]


def test_consenso_com_rotulo_invalido_encerra_com_erro(pasta, api, capsys):
    gravar(pasta, "consenso.csv", CONSENSO, [linha_consenso("o/a", "v1.0.1", "talvez")])

    assert avaliacao.main(["--versao", "1", "--pasta", str(pasta)]) == 1
    assert "talvez" in capsys.readouterr().err


def test_release_fora_da_amostra_ouro_encerra_com_erro(pasta):
    gravar(pasta, "consenso.csv", CONSENSO, [linha_consenso("o/z", "v1.0.0", "sim")])

    with pytest.raises(ErroDeAvaliacao, match="o/z"):
        avaliacao.ler_itens(str(pasta))


def test_arquivo_ausente_encerra_com_erro(tmp_path, capsys):
    assert avaliacao.main(["--versao", "1", "--pasta", str(tmp_path)]) == 1
    assert "consenso.csv" in capsys.readouterr().err


def test_compare_404_sem_notas_deixa_so_o_criterio_do_patch(pasta, monkeypatch):
    monkeypatch.setattr(avaliacao.releases, "commits_entre", lambda *a: None)
    monkeypatch.setattr(avaliacao.releases, "notas_da_release", lambda owner, repo, tag: "")
    itens = avaliacao.ler_itens(str(pasta))

    assert avaliacao.previsto(itens[0]) is True  # v1.0.0 -> v1.0.1 muda só o patch
    assert avaliacao.previsto(itens[3]) is False  # sem mensagens, v2.0.0 -> v2.1.0 muda o minor
