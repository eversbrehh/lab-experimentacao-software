"""Heurística de release corretiva (RQ 03, CFR b; RQ 08, rework rate), versão 3.

Histórico (F1 contra o consenso da amostra-ouro, em `dados/rotulagem/versoes_heuristica.csv`):

- v1 (F1 = 0,415): corretiva se (A) só o *patch* muda no SemVer, ou (B) algum commit tem
  `revert`, `hotfix`, `bugfix` ou `fix` na mensagem. Dispara em quase toda release grande.
- v2 (F1 = 0,606): passa a ler as *release notes*, que são o que a classificação humana lê.
- v3: a regra abaixo.

Versão 3. As notas só valem quando descrevem mudanças: tiradas as URLs, o HTML, as imagens e
as frases genéricas ("Full Changelog", "Generated from commits between ..."), ficam ao menos
`MIN_NOTAS` caracteres. Então:

1. Com notas descritivas, lê-se cada linha, sabendo em que seção (título) ela está:
   - sinal de **funcionalidade**: título de seção como *features*, *new*, *added*,
     *enhancements*, *improvements*, *breaking*, *deprecated*, *language*, *compiler*,
     *libraries* ou *stabilized*; item que começa por *added*/*adds*/*introduces*/*new*, ou
     commit `feat:`, quando o item não está numa seção de correções (`Fixed: - Added check`
     é correção);
   - sinal de **correção**: `fix`, `bug fix`, `hotfix`, `regression`, `revert`, `security` ou
     CVE em qualquer linha;
   - com sinal de funcionalidade, não é corretiva; com sinal de correção, é; sem nenhum dos
     dois, só vale (A), e só se as notas não tiverem seção de desempenho, manutenção,
     documentação, dependências ou testes.
2. Sem notas descritivas, vale (A) ou a maioria dos commits: ao menos metade dos assuntos
   (primeira linha da mensagem) com `revert`, `hotfix`, `bugfix` ou `fix`, e nenhum `feat:`.
3. Em ambos os casos, (A) só conta se algum commit não for trivial: docs, chore, ci, test,
   style, build, release, `Merge`, `Bump` ou número de versão. Uma release de patch que só
   traz esses commits não corrige defeito. Sem lista de commits (`None`) ou com lista vazia,
   (A) vale sozinha.

Leitura das tags:

- prefixo `v`/`V` aceito; metadados de build (`+...`) ignorados;
- pré-release (`1.2.0-rc1`): compara-se só o núcleo `major.minor.patch`, então
  `1.2.0-rc1 → 1.2.0` não muda o *patch* e `1.2.0 → 1.2.1-rc1` muda;
- monorepo (`pacote@1.2.3`, `@escopo/pacote@1.2.3`): a versão é o que vem depois do último
  `@`, e (A) só se aplica quando o pacote é o mesmo nas duas tags;
- tag fora do SemVer (`1.2`, `2024.01.05`, `release-5`): (A) não se aplica e decidem as
  notas ou os commits.
"""

import re

SEMVER = re.compile(
    r"^[vV]?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
# Início de palavra: casa `fix:`, `Fixes #12`, `fixed`, `Revert "..."`, `hotfix/x`, mas não
# `prefix` nem `suffix`. `fixture` casa e fica como falso positivo conhecido da versão 1.
PALAVRA_CHAVE = re.compile(r"\b(revert|hotfix|bugfix|fix)", re.IGNORECASE)

MIN_NOTAS = 20
FRACAO_COMMITS_DE_CORRECAO = 0.5

_LIXO_DAS_NOTAS = re.compile(
    r"https?://\S+|<[^>]+>|!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)"
    r"|^\W*(?:full changelog|see \S*changelog\S*|generated from commits between)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
_TITULO = re.compile(r"^\s*(?:#{1,6}\s|<h[1-6]>|\*\*[^*\n]+\*\*\s*:?\s*$)")
_SIMBOLOS_INICIAIS = re.compile(r"^[^\w]*(?:\d+[.)]\s*)?")
_TITULO_DE_FUNCIONALIDADE = re.compile(
    r"^(?:new(?: features?)?|features?|added|enhancements?|improvements?|breaking(?: changes?)?"
    r"|deprecat\w*|language|compiler|libraries|stabili[sz]ed\w*)\b",
    re.IGNORECASE,
)
_ITEM_DE_FUNCIONALIDADE = re.compile(r"^(?:added|adds?|introduc\w*|new)\b", re.IGNORECASE)
_COMMIT_FEAT = re.compile(r"\bfeat(?:\([^)]*\))?:", re.IGNORECASE)
_TITULO_DE_CORRECAO = re.compile(r"\b(?:bug ?fix(?:es)?|fix(?:es|ed)?|hotfix|security)\b", re.IGNORECASE)
_TITULO_SEM_CORRECAO = re.compile(
    r"^(?:performance|chores?|documentation|docs|dependenc\w*|maintenance|refactor\w*|tests?)\b", re.IGNORECASE
)
SINAL_CORRECAO = re.compile(
    r"\b(?:bug ?fix(?:es)?|fix(?:es|ed)?|hotfix|regress\w*|revert\w*|security|cve-\d)",
    re.IGNORECASE,
)
_COMMIT_TRIVIAL = re.compile(
    r"^(?:(?:docs?|chore|ci|tests?|style|build|release)\b[(:!]|v?\d+\.\d+|merge\b|bump\b)", re.IGNORECASE
)


def versao_semver(tag: str) -> tuple[str, tuple[int, int, int]] | None:
    """`(pacote, (major, minor, patch))` da tag, ou `None` fora do SemVer.

    `pacote` é o que vem antes do último `@` (vazio quando a tag não tem `@`).
    """
    pacote, _, versao = tag.rpartition("@")
    casamento = SEMVER.match(versao)
    if casamento is None:
        return None
    major, minor, patch = (int(parte) for parte in casamento.groups())
    return pacote, (major, minor, patch)


def so_patch_mudou(tag: str, tag_anterior: str) -> bool:
    """Critério (A): mesmo pacote, mesmo `major.minor` e *patch* maior que o da anterior."""
    atual, anterior = versao_semver(tag), versao_semver(tag_anterior)
    if atual is None or anterior is None or atual[0] != anterior[0]:
        return False
    (major, minor, patch), (major_ant, minor_ant, patch_ant) = atual[1], anterior[1]
    return major == major_ant and minor == minor_ant and patch > patch_ant


def tem_palavra_chave(mensagens: list[str] | None) -> bool:
    """Critério (B): alguma mensagem tem `revert`, `hotfix`, `bugfix` ou `fix`."""
    return any(PALAVRA_CHAVE.search(mensagem) for mensagem in mensagens or [])


def texto_das_notas(notas: str | None) -> str:
    """Notas sem URLs, HTML, imagens nem frases genéricas; vazio quando não descrevem mudança."""
    texto = _LIXO_DAS_NOTAS.sub(lambda m: m.group(1) or "", notas or "").strip()
    return texto if len(texto) >= MIN_NOTAS else ""


def sinais_das_notas(texto: str) -> tuple[bool, bool, bool]:
    """`(funcionalidade, correcao, sem_correcao)` das notas, lendo linha a linha com a seção.

    `sem_correcao` indica seção de desempenho, manutenção, documentação, dependências ou testes.
    """
    funcionalidade = correcao = sem_correcao = False
    em_secao_de_correcao = False
    for linha in texto.splitlines():
        conteudo = _SIMBOLOS_INICIAIS.sub("", linha).strip()
        if not conteudo:
            continue
        if _TITULO.match(linha) or len(conteudo.split()) <= 3:
            em_secao_de_correcao = _TITULO_DE_CORRECAO.search(conteudo) is not None
            if _TITULO_DE_FUNCIONALIDADE.match(conteudo) and not re.search(r"\bnone\b", conteudo, re.IGNORECASE):
                funcionalidade = True
            if _TITULO_SEM_CORRECAO.match(conteudo):
                sem_correcao = True
        elif _ITEM_DE_FUNCIONALIDADE.match(conteudo) and not em_secao_de_correcao:
            funcionalidade = True
        if _COMMIT_FEAT.search(conteudo):
            funcionalidade = True
        if SINAL_CORRECAO.search(conteudo):
            correcao = True
    return funcionalidade, correcao, sem_correcao


def _assunto(mensagem: str) -> str:
    return mensagem.strip().split("\n", 1)[0]


def tem_commit_nao_trivial(mensagens: list[str] | None) -> bool:
    """False só quando há commits e todos são docs, chore, ci, test, style, build, release, merge ou versão."""
    if not mensagens:
        return True
    return any(not _COMMIT_TRIVIAL.match(_assunto(m)) for m in mensagens)


def maioria_de_correcao(mensagens: list[str] | None) -> bool:
    """Ao menos `FRACAO_COMMITS_DE_CORRECAO` dos assuntos com palavra-chave de correção e nenhum `feat:`."""
    if not mensagens:
        return False
    assuntos = [_assunto(m) for m in mensagens]
    if any(_COMMIT_FEAT.search(a) for a in assuntos):
        return False
    com_palavra = sum(1 for a in assuntos if PALAVRA_CHAVE.search(a))
    return com_palavra / len(assuntos) >= FRACAO_COMMITS_DE_CORRECAO


def eh_corretiva(release: dict, anterior: dict | None) -> bool:
    """True se `release` é corretiva em relação ao deploy imediatamente `anterior`.

    Formato de `release` (e de `anterior`):

    - `tag_name: str`;
    - `published_at: datetime`, com fuso (só `cfr_entrega` usa);
    - `mensagens: list[str] | None`, as mensagens completas (`commit.message` do
      `compare anterior...release`) dos commits incluídos na release. `None` quando não se
      sabe: primeira release da história ou `compare` com 404. Lista vazia é release sem
      commits novos;
    - `notas: str | None` (opcional), o texto das *release notes*.

    Sem `anterior` (primeira release), (A) não se aplica; com `mensagens` `None`, os
    critérios que olham commits não se aplicam. A regra completa está no cabeçalho do módulo.
    """
    mensagens = release.get("mensagens")
    patch = (
        anterior is not None
        and so_patch_mudou(release["tag_name"], anterior["tag_name"])
        and tem_commit_nao_trivial(mensagens)
    )
    texto = texto_das_notas(release.get("notas"))
    if texto:
        funcionalidade, correcao, sem_correcao = sinais_das_notas(texto)
        if funcionalidade:
            return False
        if correcao:
            return True
        return patch and not sem_correcao
    return patch or maioria_de_correcao(mensagens)


def rework_rate(releases: list[dict]) -> float | None:
    """Proporção de releases corretivas (RQ 08, *rework rate*).

    `releases` são os deploys da janela como devolve `pipeline.releases.releases_com_commits`:
    cada item traz `tag_name`, `mensagens` (`None` quando não se sabe) e `anterior_tag` (`None`
    na primeira release da história). Só entram as releases com `mensagens` conhecidas:
    a primeira release da história e as de `compare` com 404 ficam fora do numerador e do
    denominador. Releases sem commits novos (`mensagens = []`) entram e só podem ser
    corretivas pelo critério (A). Devolve `None` quando nenhuma release entra.
    """
    avaliadas = corretivas = 0
    for release in releases:
        if release.get("mensagens") is None:
            continue
        avaliadas += 1
        anterior = {"tag_name": release["anterior_tag"]} if release.get("anterior_tag") else None
        if eh_corretiva(release, anterior):
            corretivas += 1
    return corretivas / avaliadas if avaliadas else None
