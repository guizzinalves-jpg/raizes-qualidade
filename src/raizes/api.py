"""Camada de API: traduz o serviço em respostas HTTP (status + corpo JSON)."""
from .domain import ErroNegocio


def post_pedidos(service, corpo: dict, headers: dict):
    """POST /v1/pedidos  -> (status_http, corpo)."""
    try:
        chave = headers.get("Idempotency-Key")
        if not chave:
            return 400, {"codigo": "IDEMPOTENCY_KEY_AUSENTE", "mensagem": "Cabeçalho Idempotency-Key é obrigatório."}
        p = service.realizar_pedido(
            unidade_id=corpo.get("unidade_id"), canal=corpo.get("canal", ""),
            itens=[(i["sku"], i["quantidade"]) for i in corpo.get("itens", [])],
            token_pagamento=corpo.get("token_pagamento"), chave_idempotencia=chave,
            cliente_id=corpo.get("cliente_id"),
            consentimento_fidelidade=corpo.get("consentimento_fidelidade", False),
            correlation_id=headers.get("X-Correlation-Id"))
        http = {"PAGO": 201, "PAGAMENTO_PENDENTE": 202, "PAGAMENTO_RECUSADO": 402,
                "PAGAMENTO_FALHOU": 503}.get(p.status.value, 200)
        return http, {"pedido_id": p.id, "status": p.status.value, "total_centavos": p.total,
                      "correlation_id": p.correlation_id}
    except ErroNegocio as e:
        return 422, {"codigo": e.codigo, "mensagem": e.mensagem}
    except ValueError:
        return 400, {"codigo": "CANAL_INVALIDO", "mensagem": "Canal de atendimento inválido."}
