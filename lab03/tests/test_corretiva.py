from datetime import datetime, timezone

import pytest

from metricas.corretiva import (
    eh_corretiva,
    maioria_de_correcao,
    rework_rate,
    sinais_das_notas,
    so_patch_mudou,
    tem_commit_nao_trivial,
    tem_palavra_chave,
    texto_das_notas,
    versao_semver,
)

PUBLICACAO = datetime(2026, 5, 10, tzinfo=timezone.utc)


def release(tag, mensagens=(), notas=None):
    return {
        "tag_name": tag,
        "published_at": PUBLICACAO,
        "mensagens": None if mensagens is None else list(mensagens),
        "notas": notas,
    }


@pytest.fixture
def exemplo(fixture_json):
    return {item["tag_name"]: item for item in fixture_json("corretiva")["exemplo_rq03"]}


def test_exemplo_rq03_v2_3_1_e_corretiva(exemplo):
    assert eh_corretiva(exemplo["v2.3.1"], exemplo["v2.3.0"])


def test_exemplo_rq03_v2_5_0_nao_e_corretiva(exemplo):
    assert not eh_corretiva(exemplo["v2.5.0"], exemplo["v2.4.0"])


def test_so_patch_basta_mesmo_sem_palavra_chave():
    assert eh_corretiva(release("v2.3.1", ["feat: novo botão"]), release("v2.3.0"))


def test_maioria_de_commits_de_correcao_basta_mesmo_com_minor_novo():
    assert eh_corretiva(release("v2.4.0", ["fix: x", "fix: y", "docs: z"]), release("v2.3.0"))


def test_um_feat_entre_commits_de_correcao_impede_sem_notas():
    assert not eh_corretiva(release("v2.4.0", ["feat: x", "fix: y"]), release("v2.3.0"))


def test_minor_novo_sem_palavra_chave_nao_e_corretiva():
    assert not eh_corretiva(release("v2.4.0", ["feat: x"]), release("v2.3.0"))


def test_primeira_release_sem_anterior_e_sem_mensagens_nao_e_corretiva():
    assert not eh_corretiva(release("v0.0.1", None), None)


def test_primeira_release_com_palavra_chave_e_corretiva():
    assert eh_corretiva(release("v0.0.1", ["fix: typo"]), None)


def test_release_sem_commits_novos_depende_so_da_versao():
    assert not eh_corretiva(release("v2.4.0", []), release("v2.3.0"))
    assert eh_corretiva(release("v2.3.1", []), release("v2.3.0"))


def test_mensagens_desconhecidas_dependem_so_da_versao():
    assert not eh_corretiva(release("v2.4.0", None), release("v2.3.0"))
    assert eh_corretiva(release("v2.3.1", None), release("v2.3.0"))


@pytest.mark.parametrize(
    "tag, esperado",
    [
        ("1.2.3", ("", (1, 2, 3))),
        ("v1.2.3", ("", (1, 2, 3))),
        ("V10.20.30", ("", (10, 20, 30))),
        ("v1.2.0-rc1", ("", (1, 2, 0))),
        ("1.2.0-alpha.1+build.5", ("", (1, 2, 0))),
        ("1.2.3+20260510", ("", (1, 2, 3))),
        ("pacote@1.2.3", ("pacote", (1, 2, 3))),
        ("@escopo/pacote@v1.2.3", ("@escopo/pacote", (1, 2, 3))),
    ],
)
def test_tags_semver_aceitas(tag, esperado):
    assert versao_semver(tag) == esperado


@pytest.mark.parametrize(
    "tag", ["1.2", "v1", "1.2.3.4", "2024.01.05", "release-5", "latest", "v1.2.x", "pacote@", "1.2.3-", ""]
)
def test_tags_fora_do_semver(tag):
    assert versao_semver(tag) is None


@pytest.mark.parametrize(
    "tag, anterior, esperado",
    [
        ("v2.3.1", "v2.3.0", True),
        ("v2.3.9", "v2.3.1", True),
        ("2.3.1", "v2.3.0", True),
        ("v2.4.0", "v2.3.0", False),
        ("v3.0.0", "v2.3.0", False),
        ("v2.3.0", "v2.3.1", False),
        ("v2.3.1", "v2.3.1", False),
        ("v1.9.3", "v2.0.0", False),
    ],
)
def test_so_patch_mudou(tag, anterior, esperado):
    assert so_patch_mudou(tag, anterior) is esperado


@pytest.mark.parametrize(
    "tag, anterior, esperado",
    [
        ("v1.2.0", "v1.2.0-rc1", False),
        ("v1.2.0-rc2", "v1.2.0-rc1", False),
        ("v1.2.1-rc1", "v1.2.0", True),
        ("v1.2.1", "v1.2.0-rc1", True),
    ],
)
def test_pre_release_compara_so_o_nucleo(tag, anterior, esperado):
    assert so_patch_mudou(tag, anterior) is esperado


@pytest.mark.parametrize(
    "tag, anterior, esperado",
    [
        ("pacote@1.2.4", "pacote@1.2.3", True),
        ("@escopo/pacote@1.2.4", "@escopo/pacote@1.2.3", True),
        ("outro@1.2.4", "pacote@1.2.3", False),
        ("pacote@1.2.4", "v1.2.3", False),
    ],
)
def test_monorepo_so_compara_o_mesmo_pacote(tag, anterior, esperado):
    assert so_patch_mudou(tag, anterior) is esperado


@pytest.mark.parametrize("tag, anterior", [("v1.3", "v1.2"), ("2024.01.06", "2024.01.05"), ("v2.3.1", "nightly")])
def test_tag_fora_do_semver_decide_so_pela_palavra_chave(tag, anterior):
    assert not eh_corretiva(release(tag, ["feat: x"]), release(anterior))
    assert eh_corretiva(release(tag, ["hotfix: y"]), release(anterior))


@pytest.mark.parametrize(
    "mensagem",
    [
        "fix: crash ao abrir arquivo",
        "fix(parser): aceita vírgula",
        "Fixes #12",
        "Fixed a race condition",
        "FIX: maiúsculas",
        'Revert "feat: novo cache"',
        "reverts commit abc123",
        "hotfix: produção fora do ar",
        "bugfix: contador negativo",
        "Merge pull request #7 from user/fix-typo",
        "chore: atualiza deps\n\nTambém fix no script de build",
    ],
)
def test_mensagens_com_palavra_chave(mensagem):
    assert tem_palavra_chave([mensagem])


@pytest.mark.parametrize(
    "mensagem",
    ["feat: novo prefix nas rotas", "refactor: remove suffix", "docs: atualiza o README", "chore: release 2.3.1"],
)
def test_mensagens_sem_palavra_chave(mensagem):
    assert not tem_palavra_chave([mensagem])


def test_fixture_casa_como_falso_positivo_conhecido_da_versao_1():
    assert tem_palavra_chave(["test: nova fixture de releases"])


def test_uma_mensagem_com_palavra_chave_entre_varias_basta():
    assert tem_palavra_chave(["feat: a", "docs: b", "fix: c"])


def test_sem_mensagens_nao_ha_palavra_chave():
    assert not tem_palavra_chave([])
    assert not tem_palavra_chave(None)


# rework rate (RQ 08)


def item(tag, anterior, mensagens):
    return {"tag_name": tag, "anterior_tag": anterior, "mensagens": mensagens}


def test_rework_rate_e_a_proporcao_de_corretivas_entre_as_avaliadas():
    releases = [
        item("v1.0.0", "v0.9.0", ["feat: a"]),
        item("v1.1.0", "v1.0.0", ["fix: crash"]),  # corretiva pela mensagem
        item("v1.1.1", "v1.1.0", ["feat: c"]),  # corretiva só pelo patch (commit não trivial)
        item("v1.2.0", "v1.1.1", ["feat: b"]),
    ]

    assert rework_rate(releases) == 2 / 4


def test_rework_rate_ignora_primeira_release_e_compare_404():
    releases = [
        item("v1.0.0", None, None),  # primeira da história
        item("v1.1.0", "v1.0.0", None),  # compare 404
        item("v1.2.0", "v1.1.0", ["fix: x"]),
    ]

    assert rework_rate(releases) == 1 / 1


def test_rework_rate_conta_release_sem_commits_novos_no_denominador():
    releases = [item("v1.0.0", "v0.9.0", []), item("v1.0.1", "v1.0.0", [])]

    assert rework_rate(releases) == 1 / 2  # a segunda é corretiva só pelo patch


def test_rework_rate_usa_a_anterior_fora_da_janela():
    # a primeira release da janela tem a anterior fora dela: o patch ainda é comparado
    assert rework_rate([item("v2.0.1", "v2.0.0", ["feat: y"])]) == 1.0


def test_rework_rate_sem_releases_avaliaveis_e_indefinido():
    assert rework_rate([]) is None
    assert rework_rate([item("v1.0.0", None, None)]) is None


# versão 3: release notes, commits triviais e maioria de commits de correção


def com_notas(tag, anterior, notas, mensagens=("feat: x",)):
    return eh_corretiva(release(tag, mensagens, notas), release(anterior))


def test_notas_com_secao_de_funcionalidade_nao_sao_corretivas_mesmo_com_fix():
    notas = "## Features\n- Novo painel\n## Bug Fixes\n- Corrige o login"

    assert not com_notas("v2.4.0", "v2.3.0", notas)
    assert not com_notas("v2.3.1", "v2.3.0", notas)  # nem o patch salva


def test_notas_so_com_correcoes_sao_corretivas_mesmo_com_minor_novo():
    assert com_notas("v2.4.0", "v2.3.0", "## Bug Fixes\n- Corrige o travamento ao salvar")


def test_item_added_dentro_de_secao_fixed_continua_correcao():
    notas = "### Fixed\n- Added validation for the workspace path\n- Resolve crash on startup"

    assert com_notas("v2.4.0", "v2.3.0", notas)


def test_item_added_fora_de_secao_de_correcao_e_funcionalidade():
    notas = "### Changes\n- Added support for HTTP/3\n- Fix a typo in the docs"

    assert not com_notas("v2.4.0", "v2.3.0", notas)


def test_breaking_none_nao_e_funcionalidade():
    notas = "This release focuses on compatibility fixes.\n## Breaking Changes: None identified"

    assert com_notas("v2.4.0", "v2.3.0", notas)


def test_feat_na_linha_das_notas_e_funcionalidade():
    assert not com_notas("v2.3.1", "v2.3.0", "Changes since v2.3.0: fix(a): x, feat(b): y")


def test_notas_sem_sinal_dependem_do_patch():
    notas = "Prevent trailing comma in the SCSS function"

    assert com_notas("v3.8.3", "v3.8.2", notas)
    assert not com_notas("v3.9.0", "v3.8.3", notas)


def test_notas_com_secao_de_manutencao_e_so_patch_nao_sao_corretivas():
    notas = "### Performance\n- Faster cache lookups\n### Chores\n- Update tooling"

    assert not com_notas("v0.13.5", "v0.13.4", notas)


def test_notas_genericas_caem_nos_commits():
    notas = "Generated from commits between `v1.0.0` and `HEAD`\n\nFull Changelog: https://x/compare/a...b"

    assert not eh_corretiva(release("v1.1.0", ["feat: x"], notas), release("v1.0.0"))
    assert eh_corretiva(release("v1.1.0", ["fix: a", "fix: b"], notas), release("v1.0.0"))


def test_patch_so_com_commits_triviais_nao_e_corretiva():
    assert not eh_corretiva(release("v1.0.1", ["docs: readme", "chore: bump", "v1.0.1"]), release("v1.0.0"))
    assert eh_corretiva(release("v1.0.1", ["docs: readme", "refactor interno"]), release("v1.0.0"))


def test_texto_das_notas_tira_links_html_e_frases_genericas():
    assert texto_das_notas("![img](https://x/a.png)\n<br>\nFull Changelog: https://x") == ""
    assert texto_das_notas("- Corrige [o login](https://x/1) no Safari") == "- Corrige o login no Safari"
    assert texto_das_notas(None) == ""


def test_sinais_das_notas_devolve_funcionalidade_correcao_e_manutencao():
    assert sinais_das_notas("## Features\n- Algo novo") == (True, False, False)
    assert sinais_das_notas("## Bug Fixes\n- Corrige algo") == (False, True, False)
    assert sinais_das_notas("## Dependencies\n- bump lib") == (False, False, True)


def test_tem_commit_nao_trivial():
    assert tem_commit_nao_trivial(None) and tem_commit_nao_trivial([])
    assert not tem_commit_nao_trivial(["Merge pull request #1", "ci: cache", "Bump x from 1 to 2", "docs(a): b"])
    assert tem_commit_nao_trivial(["Merge pull request #1", "Improve parser"])


def test_maioria_de_correcao_usa_o_assunto_e_exige_metade():
    assert maioria_de_correcao(["fix: a", "Fix b\n\nfeat: no corpo nao conta", "docs: c", "x"]) is True
    assert not maioria_de_correcao(["fix: a", "docs: b", "docs: c"])
    assert not maioria_de_correcao(["feat(x): novo", "fix: a", "fix: b"])
    assert not maioria_de_correcao([]) and not maioria_de_correcao(None)


def test_notas_ausentes_usam_so_commits():
    sem_campo = {"tag_name": "v1.0.1", "published_at": PUBLICACAO, "mensagens": ["fix: x"]}

    assert eh_corretiva(sem_campo, release("v1.0.0"))
