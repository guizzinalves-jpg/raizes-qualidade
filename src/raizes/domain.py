"""Camada de DOMÍNIO: entidades e regras de negócio puras (sem I/O)."""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Canal(str, Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


CANAIS_QUE_EXIGEM_CLIENTE = {Canal.APP, Canal.WEB, Canal.PICKUP}


class StatusPedido(str, Enum):
    CRIADO = "CRIADO"
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGAMENTO_PENDENTE = "PAGAMENTO_PENDENTE"
    PAGO = "PAGO"
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    PAGAMENTO_FALHOU = "PAGAMENTO_FALHOU"
    CANCELADO = "CANCELADO"


class ErroNegocio(Exception):
    """Erro de regra de negócio com código estável e mensagem amigável ao usuário."""

    def __init__(self, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


@dataclass(frozen=True)
class Produto:
    sku: str
    nome: str
    preco_centavos: int
    sazonal_de: Optional[date] = None   # início da janela sazonal (ex.: período junino)
    sazonal_ate: Optional[date] = None

    def disponivel_em(self, dia: date) -> bool:
        if self.sazonal_de and self.sazonal_ate:
            return self.sazonal_de <= dia <= self.sazonal_ate
        return True


@dataclass
class ItemPedido:
    sku: str
    quantidade: int
    preco_unit_centavos: int

    @property
    def subtotal(self) -> int:
        return self.quantidade * self.preco_unit_centavos


QTD_MIN, QTD_MAX = 1, 20


def validar_quantidade(qtd: int) -> None:
    if not isinstance(qtd, int) or qtd < QTD_MIN or qtd > QTD_MAX:
        raise ErroNegocio("QTD_INVALIDA", f"Quantidade deve estar entre {QTD_MIN} e {QTD_MAX}.")


def pontos_fidelidade(total_centavos: int) -> int:
    """RN06: 1 ponto a cada R$ 1,00 inteiro pago."""
    return total_centavos // 100


@dataclass
class Pedido:
    id: str
    unidade_id: str
    canal: Canal
    itens: list
    cliente_id: Optional[str] = None
    status: StatusPedido = StatusPedido.CRIADO
    correlation_id: str = ""
    pagamento_ref: Optional[str] = None
    consentimento_fidelidade: bool = False

    @property
    def total(self) -> int:
        return sum(i.subtotal for i in self.itens)
