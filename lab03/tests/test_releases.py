import json
from datetime import date, datetime, timezone

import pytest

from pipeline import cliente_http, releases

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)


def utc(ano, mes, dia, hora=12):
    return datetime(ano, mes, dia, hora, tzinfo=timezone.utc)


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, cabecalhos=None):
        self.status_code = status
        self._corpo = corpo
        self.headers = cabecalhos or {}

    def json(self):
        return self._corpo


class Rede:
    """Respostas da API em fila; registra as URLs pedidas e o corpo dos POST."""

    def __init__(self):
        self.fila = []
        self.urls = []
        self.envios = []

    def requisitar(self, url, cabecalhos):
        self.urls.append(url)
        assert self.fila, f"chamada inesperada à rede: {url}"
        return self.fila.pop(0)

    def postar(self, url, cabecalhos, envio):
        self.envios.append(envio)
        return self.requisitar(url, cabecalhos)


@pytest.fixture
def rede(monkeypatch, tmp_path):
    falsa = Rede()
    monkeypatch.setattr(cliente_http, "_requisitar", falsa.requisitar)
    monkeypatch.setattr(cliente_http, "_postar", falsa.postar)
    cliente_http.configurar("token-de-teste", str(tmp_path / "cache"))
    return falsa


def release_bruta(tag, publicada, draft=False, prerelease=False):
    return {
        "tag_name": tag,
        "published_at": publicada,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/o/r/releases/tag/{tag}",
        "name": tag,
    }


def commit_bruto(i, data="2025-11-01T10:00:00Z"):
    return {"sha": f"sha{i:04d}", "commit": {"author": {"date": data}, "message": f"mudanca {i}"}}


def release(tag, publicada, draft=False, prerelease=False):
    return {
        "tag_name": tag,
        "published_at": publicada,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/o/r/releases/tag/{tag}",
    }


# coletar_releases e coletar_tags


def test_coletar_releases_grava_campos_e_converte_a_data(rede):
    rede.fila.append(
        RespostaFalsa(
            200,
            [
                release_bruta("v1.1.0", "2026-03-15T12:00:00Z"),
                release_bruta("v1.2.0-rc1", "2026-04-01T08:30:00Z", prerelease=True),
                release_bruta("v1.2.0", None, draft=True),
            ],
        )
    )

    resultado = releases.coletar_releases("o", "r")

    assert resultado[0] == {
        "tag_name": "v1.1.0",
        "published_at": utc(2026, 3, 15),
        "draft": False,
        "prerelease": False,
        "html_url": "https://github.com/o/r/releases/tag/v1.1.0",
        "notas": "",  # sem `body` na resposta, o cliente guarda `None` e as notas ficam vazias
    }
    assert resultado[1]["prerelease"] is True
    assert resultado[2]["draft"] is True and resultado[2]["published_at"] is None
    assert set(resultado[0]) == {"tag_name", "published_at", "draft", "prerelease", "html_url", "notas"}


def test_coletar_releases_traz_as_notas_e_notas_vazias_viram_texto_vazio(rede):
    rede.fila.append(
        RespostaFalsa(
            200,
            [
                {**release_bruta("v1.1.0", "2026-03-15T12:00:00Z"), "body": "## Bug Fixes\n- x"},
                {**release_bruta("v1.0.0", "2026-03-01T12:00:00Z"), "body": None},
            ],
        )
    )

    resultado = releases.coletar_releases("o", "r")

    assert [r["notas"] for r in resultado] == ["## Bug Fixes\n- x", ""]


def test_notas_da_release_busca_pela_tag_e_devolve_none_no_404(rede):
    rede.fila.append(RespostaFalsa(200, {"tag_name": "v1.0.0", "body": "notas"}))
    rede.fila.append(RespostaFalsa(404, {"message": "Not Found"}))

    assert releases.notas_da_release("o", "r", "pacote@1.0.0") == "notas"
    assert releases.notas_da_release("o", "r", "v9") is None
    assert "tags/pacote%401.0.0" in rede.urls[0]


def test_coletar_releases_junta_todas_as_paginas_sem_filtro_de_data(rede):
    rede.fila.append(
        RespostaFalsa(
            200,
            [release_bruta("v2", "2026-01-01T00:00:00Z")],
            {"Link": '<https://api.github.com/repos/o/r/releases?page=2&per_page=100>; rel="next"'},
        )
    )
    rede.fila.append(RespostaFalsa(200, [release_bruta("v1", "2019-01-01T00:00:00Z")]))

    resultado = releases.coletar_releases("o", "r")

    assert [r["tag_name"] for r in resultado] == ["v2", "v1"]
    assert all("created" not in url and "since" not in url for url in rede.urls)


def test_coletar_tags_devolve_nome_e_sha(rede):
    rede.fila.append(
        RespostaFalsa(200, [{"name": "v1.0.0", "commit": {"sha": "abc123", "url": "x"}, "zipball_url": "y"}])
    )

    assert releases.coletar_tags("o", "r") == [{"name": "v1.0.0", "sha": "abc123"}]


def test_cache_de_tags_guarda_so_nome_e_commit(rede, tmp_path):
    rede.fila.append(
        RespostaFalsa(200, [{"name": "v1", "commit": {"sha": "abc", "url": "x"}, "zipball_url": "y", "node_id": "z"}])
    )

    releases.coletar_tags("o", "r")

    (corpo,) = _corpos_no_cache(tmp_path)
    assert set(corpo[0]) == {"name", "commit"}


def git_commit_bruto(data):
    """Corpo de `/git/commits/{sha}`: a data fica em `author`, no nível de cima."""
    return {"sha": "abc123", "author": {"name": "a", "date": data}, "tree": {"sha": "t"}, "message": "m"}


def test_data_da_tag_usa_a_data_do_commit_apontado(rede):
    rede.fila.append(RespostaFalsa(200, git_commit_bruto("2026-02-03T04:05:06Z")))

    assert releases.data_da_tag("o", "r", "abc123") == utc(2026, 2, 3, 4).replace(minute=5, second=6)
    assert rede.urls == ["https://api.github.com/repos/o/r/git/commits/abc123"]


def test_cache_de_data_da_tag_guarda_so_o_autor(rede, tmp_path):
    rede.fila.append(RespostaFalsa(200, git_commit_bruto("2026-02-03T04:05:06Z")))

    releases.data_da_tag("o", "r", "abc123")

    (corpo,) = _corpos_no_cache(tmp_path)
    assert set(corpo) == {"author"}


def test_data_da_tag_com_commit_inexistente_levanta_erro(rede):
    rede.fila.append(RespostaFalsa(404))

    with pytest.raises(LookupError):
        releases.data_da_tag("o", "r", "abc123")


def _corpos_no_cache(tmp_path):
    return [json.loads(a.read_text(encoding="utf-8"))["corpo"] for a in (tmp_path / "cache").glob("*.json")]


# tags_com_datas (GraphQL)


def no_leve(nome, sha, data):
    return {"name": nome, "target": {"__typename": "Commit", "oid": sha, "author": {"date": data}}}


def no_anotado(nome, sha, data):
    alvo = {"__typename": "Commit", "oid": sha, "author": {"date": data}}
    return {"name": nome, "target": {"__typename": "Tag", "target": alvo}}


def pagina_de_tags(nos, proximo=None):
    refs = {"pageInfo": {"hasNextPage": proximo is not None, "endCursor": proximo}, "nodes": nos}
    return RespostaFalsa(200, {"data": {"repository": {"refs": refs}}})


def test_tags_com_datas_le_tag_leve_e_anotada(rede):
    rede.fila.append(
        pagina_de_tags(
            [
                no_leve("v1.0", "aaa", "2026-01-10T12:00:00Z"),
                no_anotado("v1.1", "bbb", "2026-02-10T09:00:00-03:00"),
            ]
        )
    )

    tags, sem_commit, paginas = releases.tags_com_datas("o", "r")

    assert tags == [
        {"name": "v1.0", "sha": "aaa", "data": utc(2026, 1, 10)},
        {"name": "v1.1", "sha": "bbb", "data": utc(2026, 2, 10)},
    ]
    assert (sem_commit, paginas) == (0, 1)
    assert rede.urls == ["https://api.github.com/graphql"]
    assert rede.envios[0]["variables"] == {"owner": "o", "repo": "r", "cursor": None}


def test_tags_com_datas_conta_alvo_que_nao_e_commit(rede):
    rede.fila.append(
        pagina_de_tags(
            [
                no_leve("v1.0", "aaa", "2026-01-10T12:00:00Z"),
                {"name": "arvore", "target": {"__typename": "Tree"}},
                {"name": "anotada-de-blob", "target": {"__typename": "Tag", "target": {"__typename": "Blob"}}},
                {"name": "apagada", "target": None},
            ]
        )
    )

    tags, sem_commit, _ = releases.tags_com_datas("o", "r")

    assert [t["name"] for t in tags] == ["v1.0"]
    assert sem_commit == 3


def test_tags_com_datas_pagina_pelo_cursor_e_usa_o_cache(rede):
    rede.fila.append(pagina_de_tags([no_leve(f"v{i}", f"s{i}", "2026-01-10T12:00:00Z") for i in range(100)], "c1"))
    rede.fila.append(pagina_de_tags([no_leve("v100", "s100", "2026-01-11T12:00:00Z")]))

    tags, _, paginas = releases.tags_com_datas("o", "r")
    de_novo = releases.tags_com_datas("o", "r")

    assert len(tags) == 101 and paginas == 2
    assert [e["variables"]["cursor"] for e in rede.envios] == [None, "c1"]
    assert de_novo[0] == tags and len(rede.urls) == 2  # a segunda leitura vem só do cache


def test_tags_com_datas_com_erro_do_graphql_levanta_erro_http(rede):
    rede.fila.append(RespostaFalsa(200, {"data": {"repository": None}, "errors": [{"type": "NOT_FOUND"}]}))

    with pytest.raises(cliente_http.ErroHTTP):
        releases.tags_com_datas("o", "r")


def test_cache_de_releases_guarda_so_os_campos_usados(rede, tmp_path):
    bruta = {**release_bruta("v1", "2026-01-01T00:00:00Z"), "body": "notas longas", "assets": [{"size": 1}]}
    rede.fila.append(RespostaFalsa(200, [bruta]))

    releases.coletar_releases("o", "r")

    (corpo,) = _corpos_no_cache(tmp_path)
    assert set(corpo[0]) == {"tag_name", "published_at", "draft", "prerelease", "html_url", "body"}


def test_cache_do_compare_descarta_o_diff_dos_arquivos(rede, tmp_path):
    corpo = {"total_commits": 1, "files": [{"patch": "diff enorme"}], "commits": [{**commit_bruto(1), "author": {}}]}
    rede.fila.append(RespostaFalsa(200, corpo))

    resultado = releases.commits_entre("o", "r", "v1", "v2")

    assert [c["sha"] for c in resultado] == ["sha0001"]
    (no_cache,) = _corpos_no_cache(tmp_path)
    assert set(no_cache) == {"total_commits", "commits"}
    assert set(no_cache["commits"][0]) == {"sha", "commit"}
    assert len(rede.urls) == 1  # a conferência do 404 e a paginação usam a mesma página


# commits_entre


def test_commits_entre_devolve_sha_data_e_mensagem(rede):
    rede.fila.append(
        RespostaFalsa(200, {"commits": [commit_bruto(1, "2026-03-02T09:00:00Z"), commit_bruto(2, "2026-03-14T18:00:00Z")]})
    )

    commits = releases.commits_entre("o", "r", "v1.0.0", "v1.1.0")

    assert commits == [
        {"sha": "sha0001", "data": utc(2026, 3, 2, 9), "mensagem": "mudanca 1"},
        {"sha": "sha0002", "data": utc(2026, 3, 14, 18), "mensagem": "mudanca 2"},
    ]
    assert len(rede.urls) == 1  # a primeira página é reaproveitada do cache


def test_commits_entre_pagina_alem_de_250_commits(rede):
    def pagina(inicio, fim, proxima=None):
        cabecalhos = {}
        if proxima:
            cabecalhos["Link"] = (
                f'<https://api.github.com/repos/o/r/compare/v1...v2?page={proxima}&per_page=100>; rel="next"'
            )
        return RespostaFalsa(200, {"total_commits": 260, "commits": [commit_bruto(i) for i in range(inicio, fim)]}, cabecalhos)

    rede.fila.extend([pagina(0, 100, 2), pagina(100, 200, 3), pagina(200, 260)])

    commits = releases.commits_entre("o", "r", "v1", "v2")

    assert len(commits) == 260
    assert len({c["sha"] for c in commits}) == 260
    assert len(rede.urls) == 3
    assert all("per_page=100" in url for url in rede.urls)
    assert "page=2" in rede.urls[1] and "page=3" in rede.urls[2]


def test_commits_entre_com_404_devolve_none(rede):
    rede.fila.append(RespostaFalsa(404))

    assert releases.commits_entre("o", "r", "v1", "v2") is None
    assert len(rede.urls) == 1


def test_commits_entre_sem_commits_novos_devolve_lista_vazia(rede):
    rede.fila.append(RespostaFalsa(200, {"total_commits": 0, "commits": []}))

    assert releases.commits_entre("o", "r", "v1", "v2") == []


# releases_com_commits


@pytest.fixture
def comparacoes(monkeypatch):
    """Substitui `commits_entre`: respostas por (base, head); chave ausente = 404."""
    respostas = {}
    chamadas = []

    def falsa(owner, repo, base, head):
        chamadas.append((base, head))
        if (base, head) not in respostas:
            return None
        return [{"sha": "x", "data": data, "mensagem": "m"} for data in respostas[(base, head)]]

    monkeypatch.setattr(releases, "commits_entre", falsa)
    falsa.respostas = respostas
    falsa.chamadas = chamadas
    return falsa


def test_exemplo_do_enunciado_traz_as_datas_dos_commits(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 3, 2), utc(2026, 3, 10), utc(2026, 3, 14)]
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.1", utc(2026, 3, 15))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert total_404 == 0
    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1"]
    assert resultado[1] == {
        "tag_name": "v1.1",
        "published_at": utc(2026, 3, 15),
        "commits": [utc(2026, 3, 2), utc(2026, 3, 10), utc(2026, 3, 14)],
        "mensagens": ["m", "m", "m"],
        "anterior_tag": "v1.0",
        "notas": None,
    }


def test_primeira_release_da_historia_tem_commits_none_e_nao_e_404(comparacoes):
    todas = [release("v1.0", utc(2026, 2, 1))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert resultado == [
        {
            "tag_name": "v1.0", "published_at": utc(2026, 2, 1), "commits": None, "mensagens": None,
            "anterior_tag": None, "notas": None,
        }
    ]
    assert total_404 == 0
    assert comparacoes.chamadas == []


def test_mensagens_acompanham_os_commits_na_mesma_ordem(monkeypatch):
    commits = [
        {"sha": "a", "data": utc(2026, 3, 2), "mensagem": "feat: login\n\ncorpo longo"},
        {"sha": "b", "data": utc(2026, 3, 10), "mensagem": "fix: crash ao abrir arquivo"},
    ]
    monkeypatch.setattr(releases, "commits_entre", lambda owner, repo, base, head: commits)
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.1", utc(2026, 3, 15))]

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert resultado[1]["mensagens"] == ["feat: login\n\ncorpo longo", "fix: crash ao abrir arquivo"]
    assert resultado[1]["commits"] == [utc(2026, 3, 2), utc(2026, 3, 10)]


def test_compare_com_404_deixa_mensagens_none_mas_guarda_a_tag_anterior(comparacoes):
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.1", utc(2026, 3, 1))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert (resultado[1]["mensagens"], resultado[1]["anterior_tag"]) == (None, "v1.0")
    assert total_404 == 1


def test_release_anterior_fora_da_janela_e_usada_como_base(comparacoes):
    comparacoes.respostas[("v0.9", "v1.0")] = [utc(2025, 9, 20), utc(2025, 10, 2)]
    todas = [release("v0.9", utc(2025, 9, 15)), release("v1.0", utc(2025, 10, 5))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1.0"]  # v0.9 está fora da janela
    assert resultado[0]["commits"] == [utc(2025, 9, 20), utc(2025, 10, 2)]
    assert resultado[0]["anterior_tag"] == "v0.9"  # a anterior fora da janela continua sendo a base
    assert comparacoes.chamadas == [("v0.9", "v1.0")]


def test_compare_com_404_vira_none_e_e_contado(comparacoes):
    comparacoes.respostas[("v1.1", "v1.2")] = [utc(2026, 4, 1)]
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.1", utc(2026, 3, 1)), release("v1.2", utc(2026, 4, 2))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    por_tag = {r["tag_name"]: r["commits"] for r in resultado}
    assert por_tag["v1.0"] is None  # primeira da história
    assert por_tag["v1.1"] is None  # 404
    assert por_tag["v1.2"] == [utc(2026, 4, 1)]
    assert total_404 == 1


def test_prerelease_e_draft_nao_sao_deploys_nem_servem_de_base(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 3, 1)]
    todas = [
        release("v1.0", utc(2026, 2, 1)),
        release("v1.1-rc1", utc(2026, 2, 20), prerelease=True),
        release("v1.1-rascunho", None, draft=True),
        release("v1.1", utc(2026, 3, 2)),
    ]

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1"]
    assert comparacoes.chamadas == [("v1.0", "v1.1")]


def test_ordena_por_data_de_publicacao_e_nao_pela_ordem_da_lista(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 3, 1)]
    todas = [release("v1.1", utc(2026, 3, 2)), release("v1.0", utc(2026, 2, 1))]  # ordem da API: mais nova primeiro

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1"]
    assert comparacoes.chamadas == [("v1.0", "v1.1")]


def test_release_sem_commits_novos_mantem_lista_vazia(comparacoes):
    comparacoes.respostas[("v1.0", "v1.0.1")] = []
    todas = [release("v1.0", utc(2026, 2, 1)), release("v1.0.1", utc(2026, 2, 2))]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert resultado[1]["commits"] == []
    assert resultado[1]["mensagens"] == []
    assert total_404 == 0


def test_limites_da_janela_sao_fechados(comparacoes):
    comparacoes.respostas[("v1", "v2")] = []
    comparacoes.respostas[("v2", "v3")] = []
    todas = [
        release("v0", datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc)),
        release("v1", datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)),
        release("v2", datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)),
        release("v3", datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)),
    ]
    comparacoes.respostas[("v0", "v1")] = []

    resultado, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v1", "v2"]


def test_sem_releases_devolve_vazio(comparacoes):
    assert releases.releases_com_commits("o", "r", [], INICIO, FIM) == ([], 0)


def test_releases_com_commits_em_paralelo_da_o_mesmo_resultado(monkeypatch):
    lista = [release(f"v{i}", utc(2026, 1, i + 1)) for i in range(12)]
    lista.insert(0, release("v-antiga", utc(2024, 1, 1)))

    def falso_commits_entre(owner, repo, base, head):
        if head == "v5":
            return None  # compare com 404
        return [{"sha": head, "data": utc(2025, 12, 1), "mensagem": f"{base}...{head}"}]

    monkeypatch.setattr(releases, "commits_entre", falso_commits_entre)
    monkeypatch.setitem(cliente_http._estado, "simultaneas", 1)
    em_sequencia = releases.releases_com_commits("o", "r", lista, INICIO, FIM)

    monkeypatch.setitem(cliente_http._estado, "simultaneas", 6)
    em_paralelo = releases.releases_com_commits("o", "r", lista, INICIO, FIM)

    assert em_paralelo == em_sequencia
    assert [r["tag_name"] for r in em_paralelo[0]] == [f"v{i}" for i in range(12)]
    assert em_paralelo[1] == 1


def test_c2_conta_prerelease_como_deploy_e_como_base(comparacoes):
    comparacoes.respostas[("v1.0", "v1.1-rc1")] = [utc(2026, 2, 10)]
    comparacoes.respostas[("v1.1-rc1", "v1.1")] = [utc(2026, 2, 25)]
    todas = [
        release("v1.0", utc(2026, 2, 1)),
        release("v1.1-rc1", utc(2026, 2, 20), prerelease=True),
        release("v1.1-rascunho", None, draft=True),
        release("v1.1", utc(2026, 3, 2)),
    ]

    resultado, total_404 = releases.releases_com_commits("o", "r", todas, INICIO, FIM, incluir_prereleases=True)

    assert [r["tag_name"] for r in resultado] == ["v1.0", "v1.1-rc1", "v1.1"]
    assert resultado[2]["commits"] == [utc(2026, 2, 25)]  # só os commits desde a pré-release
    assert comparacoes.chamadas == [("v1.0", "v1.1-rc1"), ("v1.1-rc1", "v1.1")]
    assert total_404 == 0


# tags_com_commits (C3)


@pytest.fixture
def tags(monkeypatch):
    """Substitui `tags_com_datas`: lista de `(nome, sha, data)` e o total sem commit."""
    estado = {"tags": [], "sem_commit": 0}

    def falsa(owner, repo):
        lista = [{"name": nome, "sha": sha, "data": data} for nome, sha, data in estado["tags"]]
        return lista, estado["sem_commit"], 1

    monkeypatch.setattr(releases, "tags_com_datas", falsa)
    return estado


def test_tags_ordenadas_pela_data_do_commit_com_anterior_fora_da_janela(tags, comparacoes):
    tags["tags"] = [
        ("v2.0", "s20", utc(2026, 3, 1)),
        ("v1.0", "s10", utc(2025, 6, 1)),  # fora da janela: só serve de base
        ("v1.5", "s15", utc(2026, 1, 1)),
    ]
    comparacoes.respostas[("s10", "s15")] = [utc(2025, 12, 1)]
    comparacoes.respostas[("s15", "s20")] = [utc(2026, 2, 1), utc(2026, 2, 20)]

    resultado, ignoradas = releases.tags_com_commits("o", "r", INICIO, FIM)

    assert resultado == [
        {
            "tag_name": "v1.5", "published_at": utc(2026, 1, 1), "commits": [utc(2025, 12, 1)],
            "mensagens": ["m"], "anterior_tag": "v1.0", "notas": None,
        },
        {
            "tag_name": "v2.0", "published_at": utc(2026, 3, 1), "commits": [utc(2026, 2, 1), utc(2026, 2, 20)],
            "mensagens": ["m", "m"], "anterior_tag": "v1.5", "notas": None,
        },
    ]
    assert ignoradas == 0
    assert comparacoes.chamadas == [("s10", "s15"), ("s15", "s20")]  # compare pelo sha, não pelo nome


def test_tag_sem_anterior_fica_sem_commits_e_nao_e_ignorada(tags, comparacoes):
    tags["tags"] = [("v1.0", "s10", utc(2026, 1, 1))]

    resultado, ignoradas = releases.tags_com_commits("o", "r", INICIO, FIM)

    assert resultado[0]["commits"] is None
    assert ignoradas == 0
    assert comparacoes.chamadas == []


def test_tags_no_mesmo_commit_nao_chamam_o_compare(tags, comparacoes):
    tags["tags"] = [
        ("pacote-a@1.0", "s1", utc(2026, 1, 1)),
        ("pacote-b@1.0", "s1", utc(2026, 1, 1)),
        ("v0", "s0", utc(2025, 12, 1)),
    ]
    comparacoes.respostas[("s0", "s1")] = [utc(2025, 12, 15)]

    resultado, _ = releases.tags_com_commits("o", "r", INICIO, FIM)

    assert [r["tag_name"] for r in resultado] == ["v0", "pacote-a@1.0", "pacote-b@1.0"]  # empate pelo nome
    assert resultado[2]["commits"] == []
    assert comparacoes.chamadas == [("s0", "s1")]


def test_ignoradas_contam_so_compare_com_404_e_nao_tags_sem_commit(tags, comparacoes):
    tags["tags"] = [("v1", "s1", utc(2026, 1, 1)), ("v2", "s2", utc(2026, 2, 1))]
    tags["sem_commit"] = 2  # ("s1", "s2") sem resposta: 404

    resultado, ignoradas = releases.tags_com_commits("o", "r", INICIO, FIM)

    assert resultado[1]["commits"] is None
    assert ignoradas == 1  # como releases_ignoradas_404; as 2 sem commit ficam só no log


def test_tag_com_nome_de_release_nao_e_deduplicada(tags, comparacoes):
    tags["tags"] = [("v1.0", "s10", utc(2026, 1, 1)), ("v1.1", "s11", utc(2026, 2, 1))]
    comparacoes.respostas[("s10", "s11")] = [utc(2026, 1, 20)]
    todas = [release("v1.0", utc(2026, 1, 2)), release("v1.1", utc(2026, 2, 2))]
    comparacoes.respostas[("v1.0", "v1.1")] = [utc(2026, 1, 20)]

    das_tags, _ = releases.tags_com_commits("o", "r", INICIO, FIM)
    das_releases, _ = releases.releases_com_commits("o", "r", todas, INICIO, FIM)

    assert [t["tag_name"] for t in das_tags] == [r["tag_name"] for r in das_releases] == ["v1.0", "v1.1"]
    assert das_tags[1]["published_at"] == utc(2026, 2, 1)  # data do commit, não da release


def test_custo_das_tags_vai_para_o_log(tags, comparacoes, caplog):
    tags["tags"] = [("v1", "s1", utc(2026, 1, 1)), ("v2", "s2", utc(2026, 2, 1)), ("v3", "s2", utc(2026, 2, 1))]
    comparacoes.respostas[("s1", "s2")] = []

    with caplog.at_level("INFO", logger=releases.log.name):
        releases.tags_com_commits("o", "r", INICIO, FIM)

    assert "o/r: 3 tags (3 na janela, 0 sem commit); custo: 1 consultas GraphQL e 1 compare" in caplog.text
