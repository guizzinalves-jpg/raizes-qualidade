"""Camada de INFRAESTRUTURA: repositórios em memória, auditoria e gateway de pagamento SIMULADO."""
import re
from datetime import datetime
from .ports import GatewayIndisponivel, GatewayTimeout, RespostaPagamento


class RepositorioPedidos:
    def __init__(self):
        self._dados, self._por_chave = {}, {}

    def salvar(self, p): self._dados[p.id] = p
    def obter(self, pid): return self._dados.get(pid)
    def por_chave(self, chave): return self._por_chave.get(chave)
    def vincular_chave(self, chave, p): self._por_chave[chave] = p


class Estoque:
    """Estoque local por unidade (RN03): reserva -> baixa/liberação."""
    def __init__(self, saldo: dict):
        self.saldo = dict(saldo)          # {(unidade, sku): qtd}
        self.reservado = {}

    def disponivel(self, unidade, sku):
        return self.saldo.get((unidade, sku), 0) - self.reservado.get((unidade, sku), 0)

    def reservar(self, unidade, sku, qtd): 
        self.reservado[(unidade, sku)] = self.reservado.get((unidade, sku), 0) + qtd

    def liberar(self, unidade, sku, qtd):
        self.reservado[(unidade, sku)] = max(0, self.reservado.get((unidade, sku), 0) - qtd)

    def baixar(self, unidade, sku, qtd):
        self.liberar(unidade, sku, qtd)
        self.saldo[(unidade, sku)] = self.saldo.get((unidade, sku), 0) - qtd


class Fidelidade:
    def __init__(self): self.pontos = {}
    def creditar(self, cliente_id, pts): self.pontos[cliente_id] = self.pontos.get(cliente_id, 0) + pts
    def saldo(self, cliente_id): return self.pontos.get(cliente_id, 0)


def mascarar(texto: str) -> str:
    """Minimização em logs: mascara CPF e e-mail (LGPD)."""
    texto = re.sub(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b", r"***.***.***-**", texto)
    return re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "***@***", texto)


class Auditoria:
    """Trilha de auditoria append-only com correlation-id (observabilidade)."""
    def __init__(self): self.eventos = []

    def registrar(self, correlation_id, evento, ator="sistema", detalhe=""):
        self.eventos.append({"ts": datetime.now().isoformat(timespec="seconds"),
                             "correlation_id": correlation_id, "evento": evento,
                             "ator": ator, "detalhe": mascarar(detalhe)})


class GatewayMock:
    """Gateway SIMULADO. modos: aprovar | negar | timeout | indisponivel | falha_uma_vez"""
    def __init__(self, modo="aprovar"):
        self.modo, self.chamadas, self._cobrancas = modo, 0, {}

    def cobrar(self, pedido_id, valor_centavos, token_pagamento, idempotency_key):
        self.chamadas += 1
        if self.modo == "indisponivel":
            raise GatewayIndisponivel("503")
        if self.modo == "falha_uma_vez" and self.chamadas == 1:
            raise GatewayIndisponivel("503")
        if self.modo == "timeout":
            ref = f"REF-{pedido_id}"
            self._cobrancas[ref] = RespostaPagamento(ref, True)
            raise GatewayTimeout("timeout")
        if idempotency_key in self._cobrancas:
            return self._cobrancas[idempotency_key]
        r = RespostaPagamento(f"REF-{pedido_id}", self.modo != "negar",
                              "" if self.modo != "negar" else "Cartão recusado")
        self._cobrancas[idempotency_key] = r
        return r

    def consultar(self, referencia):
        return self._cobrancas.get(referencia, RespostaPagamento(referencia, False, "não encontrado"))
