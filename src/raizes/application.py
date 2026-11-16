"""Camada de APLICAÇÃO: orquestra o caso de uso UC-03 'Realizar Pedido com Pagamento'."""
import uuid
from datetime import date
from .domain import (Canal, CANAIS_QUE_EXIGEM_CLIENTE, ErroNegocio, ItemPedido, Pedido,
                     StatusPedido, pontos_fidelidade, validar_quantidade)
from .ports import GatewayIndisponivel, GatewayTimeout

TENTATIVAS_GATEWAY = 2


class PedidoService:
    def __init__(self, cardapios, estoque, repo, gateway, fidelidade, auditoria, hoje=date.today):
        self.cardapios, self.estoque, self.repo = cardapios, estoque, repo
        self.gateway, self.fidelidade, self.auditoria, self.hoje = gateway, fidelidade, auditoria, hoje

    # ---- fluxo principal -------------------------------------------------
    def realizar_pedido(self, unidade_id, canal, itens, token_pagamento, chave_idempotencia,
                        cliente_id=None, consentimento_fidelidade=False, correlation_id=None):
        cid = correlation_id or str(uuid.uuid4())
        existente = self.repo.por_chave(chave_idempotencia)
        if existente:                                  # RN05 idempotência
            self.auditoria.registrar(cid, "PEDIDO_DUPLICADO_IGNORADO")
            return existente
        canal = Canal(canal)
        if canal in CANAIS_QUE_EXIGEM_CLIENTE and not cliente_id:
            raise ErroNegocio("CLIENTE_OBRIGATORIO", "Faça login para continuar com este canal.")
        if not itens:
            raise ErroNegocio("CARRINHO_VAZIO", "Adicione ao menos um item ao pedido.")
        if not token_pagamento:
            raise ErroNegocio("PAGAMENTO_INVALIDO", "Selecione uma forma de pagamento.")
        cardapio = self.cardapios.get(unidade_id)
        if cardapio is None:
            raise ErroNegocio("UNIDADE_INVALIDA", "Unidade não encontrada.")

        linhas = []
        for sku, qtd in itens:
            validar_quantidade(qtd)
            prod = cardapio.get(sku)
            if prod is None or not prod.disponivel_em(self.hoje()):   # RN01
                raise ErroNegocio("ITEM_INDISPONIVEL", f"O item {sku} não está disponível nesta unidade.")
            if self.estoque.disponivel(unidade_id, sku) < qtd:        # RN03
                raise ErroNegocio("ESTOQUE_INSUFICIENTE", f"Estoque insuficiente para {prod.nome}.")
            linhas.append(ItemPedido(sku, qtd, prod.preco_centavos))

        pedido = Pedido(id=f"PED-{uuid.uuid4().hex[:8]}", unidade_id=unidade_id, canal=canal,
                        itens=linhas, cliente_id=cliente_id, correlation_id=cid,
                        consentimento_fidelidade=bool(consentimento_fidelidade))
        for i in linhas:
            self.estoque.reservar(unidade_id, i.sku, i.quantidade)
        pedido.status = StatusPedido.AGUARDANDO_PAGAMENTO
        self.repo.salvar(pedido)
        self.repo.vincular_chave(chave_idempotencia, pedido)
        self.auditoria.registrar(cid, "PEDIDO_CRIADO", detalhe=f"{pedido.id} total={pedido.total}")
        self._cobrar(pedido, token_pagamento, chave_idempotencia)
        return pedido

    # ---- integração com gateway (tolerância a falhas) --------------------
    def _cobrar(self, pedido, token, chave):
        for tentativa in range(1, TENTATIVAS_GATEWAY + 1):
            try:
                r = self.gateway.cobrar(pedido.id, pedido.total, token, chave)
            except GatewayTimeout:
                pedido.status = StatusPedido.PAGAMENTO_PENDENTE          # estoque segue reservado
                pedido.pagamento_ref = f"REF-{pedido.id}"
                self.auditoria.registrar(pedido.correlation_id, "PAGAMENTO_TIMEOUT")
                return
            except GatewayIndisponivel:
                self.auditoria.registrar(pedido.correlation_id, "GATEWAY_INDISPONIVEL", detalhe=f"tentativa={tentativa}")
                continue
            self._aplicar_resultado(pedido, r)
            return
        pedido.status = StatusPedido.PAGAMENTO_FALHOU
        self._liberar_estoque(pedido)
        self.auditoria.registrar(pedido.correlation_id, "PAGAMENTO_FALHOU")

    def conciliar(self, pedido_id):
        """Job de conciliação: resolve pedidos em PAGAMENTO_PENDENTE consultando o gateway."""
        p = self.repo.obter(pedido_id)
        if p is None or p.status != StatusPedido.PAGAMENTO_PENDENTE:
            raise ErroNegocio("PEDIDO_NAO_PENDENTE", "Pedido não está pendente de conciliação.")
        self._aplicar_resultado(p, self.gateway.consultar(p.pagamento_ref))
        self.auditoria.registrar(p.correlation_id, "PEDIDO_CONCILIADO")
        return p

    def _aplicar_resultado(self, pedido, r):
        pedido.pagamento_ref = r.referencia
        if r.aprovado:
            pedido.status = StatusPedido.PAGO
            for i in pedido.itens:
                self.estoque.baixar(pedido.unidade_id, i.sku, i.quantidade)
            if pedido.cliente_id and pedido.consentimento_fidelidade:   # LGPD: só com consentimento
                self.fidelidade.creditar(pedido.cliente_id, pontos_fidelidade(pedido.total))
            self.auditoria.registrar(pedido.correlation_id, "PAGAMENTO_APROVADO")
        else:
            pedido.status = StatusPedido.PAGAMENTO_RECUSADO
            self._liberar_estoque(pedido)
            self.auditoria.registrar(pedido.correlation_id, "PAGAMENTO_RECUSADO", detalhe=r.motivo)

    def _liberar_estoque(self, pedido):
        for i in pedido.itens:
            self.estoque.liberar(pedido.unidade_id, i.sku, i.quantidade)

    # ---- operações sensíveis (auditoria) ---------------------------------
    def cancelar(self, pedido_id, ator, motivo):
        if not ator or not motivo:
            raise ErroNegocio("AUDITORIA_OBRIGATORIA", "Informe responsável e motivo do cancelamento.")
        p = self.repo.obter(pedido_id)
        if p is None:
            raise ErroNegocio("PEDIDO_INEXISTENTE", "Pedido não encontrado.")
        if p.status == StatusPedido.PAGO:
            raise ErroNegocio("CANCELAMENTO_NEGADO", "Pedido pago só pode ser estornado pelo gerente.")
        if p.status in (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.PAGAMENTO_PENDENTE):
            self._liberar_estoque(p)
        p.status = StatusPedido.CANCELADO
        self.auditoria.registrar(p.correlation_id, "PEDIDO_CANCELADO", ator=ator, detalhe=motivo)
        return p
