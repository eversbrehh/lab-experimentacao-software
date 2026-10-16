import pytest

from metricas.validacao import precisao_recall_f1


def rotulos(vp=0, fp=0, fn=0, vn=0):
    """Listas `(previsto, real)` com as contagens pedidas."""
    pares = [(True, True)] * vp + [(True, False)] * fp + [(False, True)] * fn + [(False, False)] * vn
    return [p for p, _ in pares], [r for _, r in pares]


def test_exemplo_da_secao_6():
    # 40 marcadas, 30 confirmadas; 50 corretivas no consenso.
    resultado = precisao_recall_f1(*rotulos(vp=30, fp=10, fn=20, vn=40))

    assert resultado["precisao"] == pytest.approx(0.75)
    assert resultado["recall"] == pytest.approx(0.60)
    assert resultado["f1"] == pytest.approx(2 / 3)
    assert round(resultado["f1"], 2) == 0.67
    assert (resultado["vp"], resultado["fp"], resultado["fn"]) == (30, 10, 20)


def test_a_ordem_dos_argumentos_importa():
    # Trocar previsto e real troca precisão e recall.
    previsto, real = rotulos(vp=30, fp=10, fn=20)

    resultado = precisao_recall_f1(real, previsto)

    assert resultado["precisao"] == pytest.approx(0.60)
    assert resultado["recall"] == pytest.approx(0.75)


def test_heuristica_perfeita():
    resultado = precisao_recall_f1(*rotulos(vp=5, vn=5))

    assert (resultado["precisao"], resultado["recall"], resultado["f1"]) == (1.0, 1.0, 1.0)


def test_nenhum_positivo_previsto_deixa_a_precisao_indefinida_e_o_f1_zero():
    # F1 = 2·VP / (2·VP + FP + FN) = 0 / 3: definido, porque há positivos reais.
    resultado = precisao_recall_f1(*rotulos(fn=3, vn=7))

    assert resultado["precisao"] is None
    assert resultado["recall"] == 0.0
    assert resultado["f1"] == 0.0


def test_nenhum_positivo_real_deixa_o_recall_indefinido_e_o_f1_zero():
    resultado = precisao_recall_f1(*rotulos(fp=2, vn=8))

    assert resultado["precisao"] == 0.0
    assert resultado["recall"] is None
    assert resultado["f1"] == 0.0


def test_so_negativos_nas_duas_listas_deixa_tudo_indefinido():
    resultado = precisao_recall_f1(*rotulos(vn=10))

    assert (resultado["precisao"], resultado["recall"], resultado["f1"]) == (None, None, None)


def test_precisao_e_recall_zero_dao_f1_zero():
    resultado = precisao_recall_f1(*rotulos(fp=3, fn=4, vn=3))

    assert (resultado["precisao"], resultado["recall"], resultado["f1"]) == (0.0, 0.0, 0.0)


def test_listas_vazias_deixam_tudo_indefinido():
    assert precisao_recall_f1([], []) == {"precisao": None, "recall": None, "f1": None, "vp": 0, "fp": 0, "fn": 0}


def test_listas_de_tamanhos_diferentes_levantam_erro():
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        precisao_recall_f1([True, False], [True])


def test_devolve_floats_nativos():
    resultado = precisao_recall_f1(*rotulos(vp=1, fp=1, fn=1))

    assert all(type(resultado[chave]) is float for chave in ("precisao", "recall", "f1"))
