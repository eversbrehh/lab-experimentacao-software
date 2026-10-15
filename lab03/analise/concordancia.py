"""Kappa de Fleiss e consenso da amostra-ouro (seção 6 do enunciado).

`python -m analise.concordancia`

Lê `avaliador_1.xlsx` a `avaliador_3.xlsx` de `--pasta` (padrão `dados/rotulagem`), calcula
o kappa de Fleiss nas 3 dimensões do protocolo e grava na mesma pasta `kappa.csv`,
`divergencias.csv` e `consenso.csv`. O consenso segue `docs/protocolo-rotulagem.md`
(seção 6): 3-0 e 2-1 ficam com o rótulo da maioria; 1-1-1 fica sem rótulo e marcado
para a reunião.
"""

import argparse
import math
import os
import sys
import warnings

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from analise.sorteio import (
    ABA_RELEASES,
    ABA_REPOSITORIOS,
    COLUNAS_RELEASE,
    COLUNAS_REPOSITORIO,
    N_AVALIADORES,
    VALORES_ACEITOS,
)

# dimensão -> (nível, aba, colunas que identificam o item)
DIMENSOES = {
    "tipo_projeto": ("repositório", ["full_name"]),
    "entregas_reais": ("repositório", ["full_name"]),
    "corretiva": ("release", ["full_name", "tag_name"]),
}
ABAS = {"repositório": (ABA_REPOSITORIOS, COLUNAS_REPOSITORIO), "release": (ABA_RELEASES, COLUNAS_RELEASE)}
COLUNAS_AVALIADOR = [f"avaliador_{n}" for n in range(1, N_AVALIADORES + 1)]

# Landis e Koch (1977): limite superior de cada faixa.
FAIXAS = ((0.0, "pobre"), (0.20, "leve"), (0.40, "razoável"), (0.60, "moderada"), (0.80, "substancial"), (1.0, "quase perfeita"))


class ErroDeConcordancia(Exception):
    """Planilha ausente, malformada ou com rótulo inválido; a mensagem diz onde corrigir."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        lidas = [
            ler_planilha(os.path.join(args.pasta, f"avaliador_{n}.xlsx"), n)
            for n in range(1, N_AVALIADORES + 1)
        ]
        kappa, divergencias, consenso = consolidar(lidas)
    except ErroDeConcordancia as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    kappa.to_csv(os.path.join(args.pasta, "kappa.csv"), index=False)
    divergencias.to_csv(os.path.join(args.pasta, "divergencias.csv"), index=False)
    consenso.to_csv(os.path.join(args.pasta, "consenso.csv"), index=False)
    print(kappa.to_string(index=False))
    print(f"{int(consenso['reuniao'].sum())} itens 1-1-1 para a reunião; saídas em {args.pasta}")
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m analise.concordancia",
        description="Calcula o kappa de Fleiss e consolida o consenso da amostra-ouro.",
    )
    parser.add_argument("--pasta", default=os.path.join("dados", "rotulagem"), help="pasta das planilhas e das saídas")
    return parser.parse_args(argv)


def interpretar(kappa: float) -> str:
    """Faixa de Landis e Koch (1977) do kappa."""
    if math.isnan(kappa):
        return "indefinido"
    if kappa < 0:
        return "pobre"
    for limite, nome in FAIXAS[1:]:
        if kappa <= limite:
            return nome
    return FAIXAS[-1][1]


def calcular_kappa(rotulos: list[list[str]]) -> float:
    """Kappa de Fleiss de uma matriz itens × avaliadores.

    Com uma única categoria usada em todos os itens o kappa é 0/0: devolve NaN.
    """
    tabela, _ = aggregate_raters(np.array(rotulos))
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        return float(fleiss_kappa(tabela, method="fleiss"))


def ler_planilha(caminho: str, avaliador: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tabelas `(repositorios, releases)` de um avaliador, com os rótulos validados.

    Falha, citando o avaliador, a aba e a linha da planilha, se um rótulo estiver vazio
    ou fora dos valores aceitos.
    """
    try:
        planilha = load_workbook(caminho, read_only=True, data_only=True)
    except (OSError, ValueError) as erro:
        raise ErroDeConcordancia(f"avaliador {avaliador}: não foi possível ler {caminho}: {erro}") from erro
    tabelas = []
    for aba, colunas in (ABAS["repositório"], ABAS["release"]):
        if aba not in planilha.sheetnames:
            raise ErroDeConcordancia(f"avaliador {avaliador}: {caminho} não tem a aba {aba}")
        linhas = list(planilha[aba].iter_rows(values_only=True))
        if not linhas or tuple(linhas[0][: len(colunas)]) != colunas:
            raise ErroDeConcordancia(f"avaliador {avaliador}: aba {aba} deve ter as colunas {', '.join(colunas)}")
        tabela = pd.DataFrame([linha[: len(colunas)] for linha in linhas[1:]], columns=list(colunas), dtype=object)
        for dimensao, valores in VALORES_ACEITOS.items():
            if dimensao not in colunas:
                continue
            for posicao, valor in enumerate(tabela[dimensao]):
                if valor not in valores:
                    mostrado = "vazio" if valor is None else repr(valor)
                    raise ErroDeConcordancia(
                        f"avaliador {avaliador}, aba {aba}, linha {posicao + 2}: {dimensao} {mostrado}; "
                        f"valores aceitos: {', '.join(valores)}"
                    )
        tabelas.append(tabela)
    planilha.close()
    return tabelas[0], tabelas[1]


def _chaves(tabela: pd.DataFrame, colunas: list[str]) -> list[tuple]:
    return list(tabela[colunas].itertuples(index=False, name=None))


def _situacao(rotulos: list[str]) -> str:
    contagens = sorted((rotulos.count(r) for r in set(rotulos)), reverse=True)
    return "3-0" if contagens == [3] else "-".join(str(c) for c in contagens)


def consolidar(lidas: list[tuple[pd.DataFrame, pd.DataFrame]]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """`(kappa, divergencias, consenso)` a partir das planilhas dos três avaliadores.

    O kappa é calculado sobre os rótulos individuais. `consenso` tem uma linha por item e
    dimensão, com `situacao` (3-0, 2-1 ou 1-1-1), `consenso` (vazio em 1-1-1) e `reuniao`;
    `divergencias` são as linhas de `consenso` que não são 3-0.
    """
    kappas, linhas = [], []
    for dimensao, (nivel, colunas_chave) in DIMENSOES.items():
        indice = 0 if nivel == "repositório" else 1
        tabelas = [par[indice].set_index(colunas_chave) for par in lidas]
        chaves = list(tabelas[0].index)
        for n, tabela in enumerate(tabelas[1:], start=2):
            if set(tabela.index) != set(chaves) or len(tabela) != len(chaves):
                raise ErroDeConcordancia(
                    f"avaliador {n}: os {nivel}s da planilha não são os mesmos do avaliador 1 ({dimensao})"
                )
        matriz = [[tabela.loc[chave, dimensao] for tabela in tabelas] for chave in chaves]
        valor = calcular_kappa(matriz)
        kappas.append({"dimensao": dimensao, "kappa": valor, "interpretacao": interpretar(valor)})
        for chave, rotulos in zip(chaves, matriz):
            chave = chave if isinstance(chave, tuple) else (chave,)
            situacao = _situacao(rotulos)
            linha = {
                "dimensao": dimensao,
                "full_name": chave[0],
                "tag_name": chave[1] if len(chave) > 1 else "",
                **dict(zip(COLUNAS_AVALIADOR, rotulos)),
                "situacao": situacao,
                "consenso": max(set(rotulos), key=rotulos.count) if situacao != "1-1-1" else "",
                "reuniao": situacao == "1-1-1",
                "justificativa": "",
            }
            linhas.append(linha)
    consenso = pd.DataFrame(linhas)
    divergencias = consenso[consenso["situacao"] != "3-0"].drop(columns=["consenso", "justificativa"]).reset_index(drop=True)
    return pd.DataFrame(kappas), divergencias, consenso


if __name__ == "__main__":
    sys.exit(main())
