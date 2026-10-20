"""Coleta de releases, tags e dos commits incluídos em cada release ou tag.

O lead time (RQ 02) precisa dos commits entre uma release e a anterior. A anterior pode
estar fora da janela, por isso o histórico completo de releases é coletado (sem filtro
de data) e só depois as releases da janela são consultadas via `compare`. As tags (C3 da
RQ 07) seguem a mesma regra, com a data do commit apontado no lugar de `published_at`.
"""

import logging
from datetime import datetime
from urllib.parse import quote

from metricas.janela import dentro_da_janela
from pipeline import cliente_http

# Só estes campos vão para o cache. A lista de releases traz anexos e o `compare` traz o diff
# de até 300 arquivos; nada disso é usado. O texto das notas (`body`) é usado pela heurística
# de release corretiva.
CAMPOS_RELEASE = ("tag_name", "published_at", "draft", "prerelease", "html_url", "body")
CAMPOS_COMMIT = ("sha", "commit")
CAMPOS_TAG = ("name", "commit")

# Tags com a data do commit apontado, 100 por requisição. Pela REST seria uma chamada por
# tag (`data_da_tag`). A tag anotada aponta para um objeto `Tag`, que aponta para o commit.
CONSULTA_TAGS = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    refs(refPrefix: "refs/tags/", first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        target {
          __typename
          ... on Commit { oid author { date } }
          ... on Tag { target { __typename ... on Commit { oid author { date } } } }
        }
      }
    }
  }
}
"""

log = logging.getLogger(__name__)


def coletar_releases(owner: str, repo: str) -> list[dict]:
    """Todas as releases do repositório, sem filtro de data.

    Cada item traz `tag_name`, `published_at` (`datetime` UTC, ou `None` em rascunhos),
    `draft`, `prerelease`, `html_url` e `notas` (o texto das *release notes*, `""` quando
    vazio e `None` quando a resposta do cache não traz o campo, como as de antes da v3 da
    heurística).
    """
    brutas = cliente_http.get_paginado(f"/repos/{owner}/{repo}/releases", campos=CAMPOS_RELEASE)
    return [
        {
            "tag_name": bruta["tag_name"],
            "published_at": _data(bruta["published_at"]) if bruta.get("published_at") else None,
            "draft": bool(bruta["draft"]),
            "prerelease": bool(bruta["prerelease"]),
            "html_url": bruta["html_url"],
            "notas": (bruta.get("body") or "") if "body" in bruta else None,
        }
        for bruta in brutas
    ]


def coletar_tags(owner: str, repo: str) -> list[dict]:
    """Tags do repositório, com `name` e o `sha` do commit apontado."""
    brutas = cliente_http.get_paginado(f"/repos/{owner}/{repo}/tags", campos=CAMPOS_TAG)
    return [{"name": bruta["name"], "sha": bruta["commit"]["sha"]} for bruta in brutas]


def data_da_tag(owner: str, repo: str, sha: str) -> datetime:
    """Data (`commit.author.date`) do commit apontado pela tag.

    Tags não têm data própria; esta chamada só deve ser feita para repositórios aprovados.
    Usa o endpoint Git, que não traz o diff dos arquivos. O pipeline obtém as datas em
    lote com `tags_com_datas`; esta função atende a consultas avulsas.
    """
    commit = cliente_http.get_json(f"/repos/{owner}/{repo}/git/commits/{sha}", campos=("author",))
    if commit is None:
        raise LookupError(f"commit {sha} não encontrado em {owner}/{repo}")
    return _data(commit["author"]["date"])


def tags_com_datas(owner: str, repo: str) -> tuple[list[dict], int, int]:
    """Todas as tags com o commit apontado e a data dele, via GraphQL.

    Devolve `(tags, sem_commit, paginas)`: cada tag traz `name`, `sha` e `data`
    (`commit.author.date`); `sem_commit` conta as tags cujo alvo não é um commit (árvore,
    blob ou objeto apagado), que ficam de fora; `paginas` é o número de requisições.
    """
    tags = []
    sem_commit = paginas = 0
    cursor = None
    while True:
        dados = cliente_http.post_graphql(CONSULTA_TAGS, {"owner": owner, "repo": repo, "cursor": cursor})
        paginas += 1
        refs = dados["repository"]["refs"]
        for no in refs["nodes"]:
            commit = _commit_do_alvo(no.get("target"))
            if commit is None:
                sem_commit += 1
            else:
                tags.append({"name": no["name"], "sha": commit["oid"], "data": _data(commit["author"]["date"])})
        if not refs["pageInfo"]["hasNextPage"]:
            return tags, sem_commit, paginas
        cursor = refs["pageInfo"]["endCursor"]


def _commit_do_alvo(alvo: dict | None) -> dict | None:
    if alvo and alvo.get("__typename") == "Tag":
        alvo = alvo.get("target")
    if alvo and alvo.get("__typename") == "Commit":
        return alvo
    return None


def commits_entre(owner: str, repo: str, base: str, head: str) -> list[dict] | None:
    """Commits de `base...head`, paginados, com `sha`, `data` e `mensagem`.

    Devolve `None` quando a comparação não existe (404), caso comum de tag apagada ou
    reescrita. Sem paginação a API devolveria no máximo 250 commits.
    """
    caminho = f"/repos/{owner}/{repo}/compare/{base}...{head}"
    # Primeira página à parte: get_paginado devolve [] tanto para 404 quanto para
    # comparação vazia, e aqui os dois casos precisam ser distinguidos. A página fica no
    # cache e é reaproveitada logo abaixo.
    if cliente_http.get_json(caminho, {"per_page": 100}, chave="commits", campos=CAMPOS_COMMIT) is None:
        return None
    brutos = cliente_http.get_paginado(caminho, chave="commits", campos=CAMPOS_COMMIT)
    return [
        {
            "sha": bruto["sha"],
            "data": _data(bruto["commit"]["author"]["date"]),
            "mensagem": bruto["commit"]["message"],
        }
        for bruto in brutos
    ]


def notas_da_release(owner: str, repo: str, tag: str) -> str | None:
    """Texto das *release notes* da release de `tag`, ou `None` se a release não existe (404).

    Notas vazias voltam como `""`. A lista de releases (`coletar_releases`) não guarda o
    texto; esta função serve a quem avalia poucas releases, como `analise.avaliar_heuristica`.
    """
    corpo = cliente_http.get_json(f"/repos/{owner}/{repo}/releases/tags/{quote(tag, safe='')}", campos=("body",))
    return None if corpo is None else (corpo.get("body") or "")


def releases_com_commits(
    owner: str, repo: str, releases: list[dict], inicio, fim, incluir_prereleases: bool = False
) -> tuple[list[dict], int]:
    """Deploys da janela com os commits incluídos em cada um.

    Deploy é release com `draft = false` e `prerelease = false`; com `incluir_prereleases`,
    as pré-releases também contam (C2 da RQ 07). A release anterior de R é o deploy
    imediatamente anterior por `published_at`, dentro ou fora da janela.

    Cada item devolvido traz `tag_name`, `published_at`, `commits` (a lista das datas dos
    commits incluídos), `mensagens` (a lista das mensagens completas desses commits, na
    mesma ordem) e `anterior_tag` (a tag do deploy anterior, mesmo fora da janela, ou `None`
    na primeira release da história) e `notas` (o texto das *release notes*, `None` quando
    não foi coletado). `commits` e `mensagens` são `None` na primeira
    release (sem anterior) e quando o `compare` dá 404; só o segundo caso entra no total
    devolvido. Sem commits novos, as duas listas são vazias.

    Os `compare` passam por `cliente_http.mapear`, em paralelo quando o cliente está
    configurado para isso; a ordem do resultado não muda.
    """
    deploys = sorted(
        (
            {**r, "ref": r["tag_name"]}
            for r in releases
            if not r["draft"] and (incluir_prereleases or not r["prerelease"]) and r["published_at"] is not None
        ),
        key=lambda r: r["published_at"],
    )
    resultado, total_404, _ = _com_commits(owner, repo, deploys, inicio, fim, "release")
    return resultado, total_404


def tags_com_commits(owner: str, repo: str, inicio, fim) -> tuple[list[dict], int]:
    """Tags da janela (C3 da RQ 07) com os commits incluídos em cada uma.

    A data da tag é a do commit apontado, e a anterior de T é a tag imediatamente anterior
    por essa data (empate pelo nome), dentro ou fora da janela. Os itens têm o formato de
    `releases_com_commits`, com a data da tag em `published_at`. Tags no mesmo commit da
    anterior têm `commits = []` sem chamar o `compare`.

    O total devolvido conta os `compare` com 404 (tag fora do lead time), como em
    `releases_com_commits`. Tag cujo alvo não é commit não tem data, então não é deploy:
    fica fora de tudo e só aparece no log. Tags e releases são independentes: uma tag com
    nome de release não é deduplicada.
    """
    tags, sem_commit, paginas = tags_com_datas(owner, repo)
    ordenadas = sorted(
        ({"tag_name": t["name"], "published_at": t["data"], "ref": t["sha"]} for t in tags),
        key=lambda t: (t["published_at"], t["tag_name"]),
    )
    resultado, total_404, comparacoes = _com_commits(owner, repo, ordenadas, inicio, fim, "tag")
    log.info(
        "%s/%s: %d tags (%d na janela, %d sem commit); custo: %d consultas GraphQL e %d compare",
        owner, repo, len(tags), len(resultado), sem_commit, paginas, comparacoes,
    )
    return resultado, total_404


def _com_commits(owner: str, repo: str, ordenados: list[dict], inicio, fim, rotulo: str):
    """Itens da janela com os commits desde o anterior; `(resultado, total_404, comparacoes)`.

    `ordenados` traz `tag_name`, `published_at` e `ref` (o que vai no `compare`), em ordem
    cronológica. `comparacoes` conta os `compare` pedidos.
    """
    na_janela = [
        (ordenados[posicao - 1] if posicao > 0 else None, item)
        for posicao, item in enumerate(ordenados)
        if dentro_da_janela(item["published_at"], inicio, fim)
    ]

    def intervalo(par):
        anterior, item = par
        if anterior is None:
            return None
        if anterior["ref"] == item["ref"]:
            return []  # mesmo commit da anterior: nada novo, sem chamar a API
        return commits_entre(owner, repo, anterior["ref"], item["ref"])

    dos_intervalos = cliente_http.mapear(intervalo, na_janela)
    resultado = []
    total_404 = 0
    for (anterior, item), do_intervalo in zip(na_janela, dos_intervalos):
        commits = None
        mensagens = None
        if anterior is not None:
            if do_intervalo is None:
                total_404 += 1
                log.warning(
                    "%s/%s: compare %s...%s deu 404; %s ignorada no lead time",
                    owner, repo, anterior["tag_name"], item["tag_name"], rotulo,
                )
            else:
                commits = [commit["data"] for commit in do_intervalo]
                mensagens = [commit["mensagem"] for commit in do_intervalo]
        resultado.append(
            {
                "tag_name": item["tag_name"],
                "published_at": item["published_at"],
                "commits": commits,
                "mensagens": mensagens,
                "anterior_tag": anterior["tag_name"] if anterior is not None else None,
                "notas": item.get("notas"),
            }
        )
    comparacoes = sum(1 for anterior, item in na_janela if anterior is not None and anterior["ref"] != item["ref"])
    return resultado, total_404, comparacoes


def _data(texto: str) -> datetime:
    return datetime.fromisoformat(texto)
