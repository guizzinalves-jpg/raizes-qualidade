"""Contratos (portas) entre Aplicação e Infraestrutura - permitem MOCK nos testes."""
from dataclasses import dataclass
from typing import Protocol


class GatewayIndisponivel(Exception):
    pass


class GatewayTimeout(Exception):
    pass


@dataclass
class RespostaPagamento:
    referencia: str
    aprovado: bool
    motivo: str = ""


class GatewayPagamento(Protocol):
    def cobrar(self, pedido_id: str, valor_centavos: int, token_pagamento: str,
               idempotency_key: str) -> RespostaPagamento: ...
    def consultar(self, referencia: str) -> RespostaPagamento: ...
