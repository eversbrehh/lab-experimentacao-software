"""Heurística de release corretiva (RQ 03, CFR b; RQ 08, rework rate), versão 1.

Uma release é corretiva quando vale (A) ou (B):

- (A) só o *patch* muda no SemVer em relação à release anterior;
- (B) algum commit entre as duas releases tem `revert`, `hotfix`, `bugfix` ou `fix` na
  mensagem.

Leitura das tags:

- prefixo `v`/`V` aceito; metadados de build (`+...`) ignorados;
- pré-release (`1.2.0-rc1`): compara-se só o núcleo `major.minor.patch`, então
  `1.2.0-rc1 → 1.2.0` não muda o *patch* e `1.2.0 → 1.2.1-rc1` muda;
- monorepo (`pacote@1.2.3`, `@escopo/pacote@1.2.3`): a versão é o que vem depois do último
  `@`, e (A) só se aplica quando o pacote é o mesmo nas duas tags;
- tag fora do SemVer (`1.2`, `2024.01.05`, `release-5`): (A) não se aplica e só (B) decide.
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


def eh_corretiva(release: dict, anterior: dict | None) -> bool:
    """True se `release` é corretiva em relação ao deploy imediatamente `anterior`.

    Formato de `release` (e de `anterior`):

    - `tag_name: str`;
    - `published_at: datetime`, com fuso (só `cfr_entrega` usa);
    - `mensagens: list[str] | None`, as mensagens completas (`commit.message` do
      `compare anterior...release`) dos commits incluídos na release. `None` quando não se
      sabe: primeira release da história ou `compare` com 404. Lista vazia é release sem
      commits novos.

    Sem `anterior` (primeira release), (A) não se aplica; com `mensagens` `None`, (B) não
    se aplica.
    """
    if anterior is not None and so_patch_mudou(release["tag_name"], anterior["tag_name"]):
        return True
    return tem_palavra_chave(release["mensagens"])
