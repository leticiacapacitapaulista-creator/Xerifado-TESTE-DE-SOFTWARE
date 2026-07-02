from app import is_estoque_baixo, get_itens_estoque_baixo


def test_estoque_baixo_conta_quando_atinge_o_minimo():
    assert is_estoque_baixo(5, 5) is True
    assert is_estoque_baixo(4, 5) is True
    assert is_estoque_baixo(6, 5) is False
    assert is_estoque_baixo(2, 5, True) is True


def test_get_itens_estoque_baixo_retorna_apenas_itens_abaixo_do_minimo():
    produtos = [
        {"nome": "Caneta", "quantidade": 5, "estoque_min": 10},
        {"nome": "Caderno", "quantidade": 15, "estoque_min": 10},
    ]

    itens = get_itens_estoque_baixo(produtos)

    assert len(itens) == 1
    assert itens[0]["nome"] == "Caneta"


def test_get_itens_estoque_baixo_inclui_itens_solicitados_em_falta():
    produtos = [
        {"nome": "Caneta", "quantidade": 2, "estoque_min": 10, "em_falta": False},
        {"nome": "Caderno", "quantidade": 5, "estoque_min": 10, "em_falta": True},
    ]

    itens = get_itens_estoque_baixo(produtos)

    assert len(itens) == 2
    assert [item["nome"] for item in itens] == ["Caneta", "Caderno"]
