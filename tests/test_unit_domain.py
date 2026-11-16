"""TESTES UNITÁRIOS - camada de domínio (CT-U*)."""
from datetime import date
import pytest
from raizes.domain import ErroNegocio, ItemPedido, Pedido, Canal, Produto, pontos_fidelidade, validar_quantidade
from raizes.infrastructure import mascarar


def test_CT_U01_subtotal_e_total():
    p = Pedido("P1", "REC01", Canal.APP, [ItemPedido("A", 2, 1200), ItemPedido("B", 1, 1800)])
    assert p.total == 4200

@pytest.mark.parametrize("qtd", [1, 10, 20])
def test_CT_U02_quantidade_valida_limites(qtd):
    validar_quantidade(qtd)

@pytest.mark.parametrize("qtd", [0, -1, 21, 1.5, None])
def test_CT_U03_quantidade_invalida(qtd):
    with pytest.raises(ErroNegocio) as e:
        validar_quantidade(qtd)
    assert e.value.codigo == "QTD_INVALIDA"

@pytest.mark.parametrize("total,pts", [(0, 0), (99, 0), (100, 1), (4299, 42), (10000, 100)])
def test_CT_U04_pontos_fidelidade(total, pts):
    assert pontos_fidelidade(total) == pts

def test_CT_U05_produto_sazonal_janela():
    p = Produto("CANJICA", "Canjica", 900, date(2026, 6, 1), date(2026, 6, 30))
    assert p.disponivel_em(date(2026, 6, 15)) and not p.disponivel_em(date(2026, 11, 15))
    assert p.disponivel_em(date(2026, 6, 1)) and p.disponivel_em(date(2026, 6, 30))

def test_CT_U06_produto_regular_sempre_disponivel():
    assert Produto("T", "Tapioca", 1200).disponivel_em(date(2026, 11, 15))

def test_CT_U07_mascara_dados_pessoais_em_log():
    s = mascarar("cliente 123.456.789-09 email ana@exemplo.com")
    assert "123.456" not in s and "ana@exemplo.com" not in s
