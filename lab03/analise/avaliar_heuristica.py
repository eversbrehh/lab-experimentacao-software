"""Precisão, recall e F1 da heurística de release corretiva contra o consenso (seção 6 do enunciado).

`python -m analise.avaliar_heuristica --versao 1 --regra "<descrição>"`

Para cada release corretiva-ou-não do `consenso.csv` (dimensão `corretiva`), busca as mensagens
dos commits entre ela e a release anterior (`compare`, pela camada HTTP e seu cache), aplica
`metricas.corretiva.eh_corretiva` e compara com o rótulo de consenso. Grava a linha da versão
em `dados/rotulagem/versoes_heuristica.csv`, substituindo a de mesmo número se já existir.

A release anterior e a release sorteada vêm de `url_compare` em `amostra_ouro.csv`; a primeira
release de um repositório (`url_compare` vazia) não tem anterior nem mensagens.
"""

import argparse
import csv
import os
import sys
from urllib.parse import unquote

from metricas.corretiva import eh_corretiva
from metricas.validacao import precisao_recall_f1
from pipeline import cliente_http, releases

COLUNAS = ("versao", "regra", "n", "vp", "fp", "fn", "precisao", "recall", "f1")
REGRA_PADRAO = (
    "(A) só o patch muda no SemVer em relação à release anterior; "
    "(B) revert, hotfix, bugfix ou fix na mensagem de algum commit entre as duas releases"
)


class ErroDeAvaliacao(Exception):
    """Entrada ausente ou inconsistente; a mensagem diz onde corrigir."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        itens = ler_itens(args.pasta)
    except ErroDeAvaliacao as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    cliente_http.configurar(os.environ.get("GITHUB_TOKEN", ""), args.cache, simultaneas=4)
    previstos = cliente_http.mapear(previsto, itens)
    resultado = precisao_recall_f1(previstos, [item["real"] for item in itens])
    linha = {"versao": args.versao, "regra": args.regra, "n": len(itens), **resultado}
    gravar(os.path.join(args.pasta, "versoes_heuristica.csv"), linha)
    print(
        f"versão {args.versao}: n={linha['n']} VP={linha['vp']} FP={linha['fp']} FN={linha['fn']} "
        f"precisão={_fmt(linha['precisao'])} recall={_fmt(linha['recall'])} F1={_fmt(linha['f1'])}"
    )
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="python -m analise.avaliar_heuristica",
        description="Avalia a heurística de release corretiva contra o consenso da amostra-ouro.",
    )
    analisador.add_argument("--versao", required=True, help="número da versão da heurística (ex.: 1)")
    analisador.add_argument("--regra", default=REGRA_PADRAO, help="descrição da regra, para o CSV")
    analisador.add_argument("--pasta", default=os.path.join("dados", "rotulagem"), help="pasta dos CSVs da rotulagem")
    analisador.add_argument("--cache", default=os.path.join("dados", "cache"), help="pasta do cache da API")
    return analisador.parse_args(argv)


def ler_itens(pasta: str) -> list[dict]:
    """Releases da dimensão `corretiva` do consenso, com o rótulo real e os dados de `compare`."""
    consenso = _csv(os.path.join(pasta, "consenso.csv"))
    ouro = {
        (linha["full_name"], linha["tag_name"]): linha
        for linha in _csv(os.path.join(pasta, "amostra_ouro.csv"))
        if linha["papel"] == "amostra"
    }
    itens = []
    for linha in consenso:
        if linha["dimensao"] != "corretiva":
            continue
        chave = (linha["full_name"], linha["tag_name"])
        if chave not in ouro:
            raise ErroDeAvaliacao(f"{chave[0]} {chave[1]} está no consenso mas não em amostra_ouro.csv")
        if linha["consenso"] not in ("sim", "não"):
            raise ErroDeAvaliacao(f"{chave[0]} {chave[1]}: consenso {linha['consenso']!r} (esperado sim ou não)")
        base, head = _extremos(ouro[chave]["url_compare"])
        itens.append({"full_name": chave[0], "tag": chave[1], "base": base, "head": head, "real": linha["consenso"] == "sim"})
    if not itens:
        raise ErroDeAvaliacao("consenso.csv não tem a dimensão corretiva")
    return itens


def previsto(item: dict) -> bool:
    """Saída da heurística para uma release do consenso."""
    owner, repo = item["full_name"].split("/")
    mensagens = None
    if item["base"]:
        commits = releases.commits_entre(owner, repo, item["base"], item["head"])
        mensagens = None if commits is None else [commit["mensagem"] for commit in commits]
    release = {"tag_name": item["tag"], "published_at": None, "mensagens": mensagens}
    anterior = {"tag_name": unquote(item["base"])} if item["base"] else None
    return eh_corretiva(release, anterior)


def gravar(caminho: str, linha: dict) -> None:
    """Grava `linha` em `versoes_heuristica.csv`, trocando a linha da mesma versão."""
    existentes = [l for l in _csv(caminho) if l["versao"] != str(linha["versao"])] if os.path.exists(caminho) else []
    existentes.append({coluna: "" if linha[coluna] is None else linha[coluna] for coluna in COLUNAS})
    existentes.sort(key=lambda l: int(l["versao"]))
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(existentes)


def _extremos(url_compare: str) -> tuple[str, str]:
    if "/compare/" not in url_compare:
        return "", ""
    base, _, head = url_compare.split("/compare/", 1)[1].partition("...")
    return base, head


def _csv(caminho: str) -> list[dict]:
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            return list(csv.DictReader(arquivo))
    except OSError as erro:
        raise ErroDeAvaliacao(f"não foi possível ler {caminho}: {erro.strerror}") from erro


def _fmt(valor) -> str:
    return "indefinido" if valor in (None, "") else f"{float(valor):.3f}"


if __name__ == "__main__":
    sys.exit(main())
