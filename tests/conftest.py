import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from datetime import date
import pytest
from raizes.domain import Produto
from raizes.application import PedidoService
from raizes.infrastructure import Auditoria, Estoque, Fidelidade, GatewayMock, RepositorioPedidos

JUNINO = (date(2026, 6, 1), date(2026, 6, 30))


@pytest.fixture
def cardapios():
    return {
        "REC01": {"TAPIOCA": Produto("TAPIOCA", "Tapioca de queijo", 1200),
                  "CUSCUZ": Produto("CUSCUZ", "Cuscuz recheado", 1800),
                  "CANJICA": Produto("CANJICA", "Canjica junina", 900, *JUNINO)},
        "SSA02": {"TAPIOCA": Produto("TAPIOCA", "Tapioca de queijo", 1200)},   # unidade reduzida
    }


@pytest.fixture
def ctx(cardapios):
    estoque = Estoque({("REC01", "TAPIOCA"): 5, ("REC01", "CUSCUZ"): 50,
                       ("REC01", "CANJICA"): 10, ("SSA02", "TAPIOCA"): 10})
    c = type("Ctx", (), {})()
    c.estoque, c.repo, c.gw = estoque, RepositorioPedidos(), GatewayMock("aprovar")
    c.fid, c.aud, c.hoje = Fidelidade(), Auditoria(), date(2026, 11, 15)
    c.svc = PedidoService(cardapios, estoque, c.repo, c.gw, c.fid, c.aud, hoje=lambda: c.hoje)
    return c
