"""TESTES DE INTEGRAÇÃO - Aplicação + Infraestrutura + Gateway simulado (CT-I*)."""
import pytest
from raizes.domain import StatusPedido, ErroNegocio
from raizes.infrastructure import GatewayMock


def pedir(ctx, **kw):
    base = dict(unidade_id="REC01", canal="APP", itens=[("CUSCUZ", 2)], token_pagamento="tok_ok",
                chave_idempotencia="k1", cliente_id="C1", consentimento_fidelidade=True)
    base.update(kw)
    return ctx.svc.realizar_pedido(**base)

def test_CT_I01_pagamento_aprovado_baixa_estoque_e_pontua(ctx):
    p = pedir(ctx)
    assert p.status == StatusPedido.PAGO
    assert ctx.estoque.saldo[("REC01", "CUSCUZ")] == 48 and ctx.estoque.disponivel("REC01", "CUSCUZ") == 48
    assert ctx.fid.saldo("C1") == 36            # R$ 36,00 -> 36 pontos

def test_CT_I02_pagamento_recusado_libera_reserva(ctx):
    ctx.gw.modo = "negar"
    p = pedir(ctx)
    assert p.status == StatusPedido.PAGAMENTO_RECUSADO
    assert ctx.estoque.disponivel("REC01", "CUSCUZ") == 50 and ctx.fid.saldo("C1") == 0

def test_CT_I03_timeout_gera_pendente_e_mantem_reserva(ctx):
    ctx.gw.modo = "timeout"
    p = pedir(ctx)
    assert p.status == StatusPedido.PAGAMENTO_PENDENTE
    assert ctx.estoque.disponivel("REC01", "CUSCUZ") == 48

def test_CT_I04_conciliacao_resolve_pendente(ctx):
    ctx.gw.modo = "timeout"
    p = pedir(ctx)
    ctx.gw.modo = "aprovar"
    ctx.svc.conciliar(p.id)
    assert p.status == StatusPedido.PAGO and ctx.fid.saldo("C1") == 36

def test_CT_I05_gateway_instavel_retry_com_sucesso(ctx):
    ctx.gw.modo = "falha_uma_vez"
    p = pedir(ctx)
    assert p.status == StatusPedido.PAGO and ctx.gw.chamadas == 2

def test_CT_I06_gateway_indisponivel_falha_controlada(ctx):
    ctx.gw.modo = "indisponivel"
    p = pedir(ctx)
    assert p.status == StatusPedido.PAGAMENTO_FALHOU and ctx.gw.chamadas == 2
    assert ctx.estoque.disponivel("REC01", "CUSCUZ") == 50

def test_CT_I07_idempotencia_nao_duplica_pedido_nem_cobranca(ctx):
    a, b = pedir(ctx), pedir(ctx)
    assert a is b and ctx.gw.chamadas == 1 and ctx.estoque.saldo[("REC01", "CUSCUZ")] == 48

def test_CT_I08_auditoria_com_correlation_id_em_todo_fluxo(ctx):
    p = pedir(ctx, correlation_id="corr-123")
    evs = [e for e in ctx.aud.eventos if e["correlation_id"] == "corr-123"]
    assert {"PEDIDO_CRIADO", "PAGAMENTO_APROVADO"} <= {e["evento"] for e in evs}

def test_CT_I09_cancelamento_exige_ator_e_motivo_e_audita(ctx):
    ctx.gw.modo = "timeout"
    p = pedir(ctx)
    with pytest.raises(ErroNegocio):
        ctx.svc.cancelar(p.id, "", "")
    ctx.svc.cancelar(p.id, "gerente.rec01", "cliente desistiu")
    assert p.status == StatusPedido.CANCELADO and ctx.estoque.disponivel("REC01", "CUSCUZ") == 50
    assert any(e["evento"] == "PEDIDO_CANCELADO" and e["ator"] == "gerente.rec01" for e in ctx.aud.eventos)

def test_CT_I10_cancelar_pedido_pago_negado(ctx):
    p = pedir(ctx)
    with pytest.raises(ErroNegocio) as e:
        ctx.svc.cancelar(p.id, "atendente1", "erro")
    assert e.value.codigo == "CANCELAMENTO_NEGADO"

def test_CT_I11_consentimento_ausente_nao_acumula_pontos(ctx):
    p = pedir(ctx, consentimento_fidelidade=False)
    assert p.status == StatusPedido.PAGO and ctx.fid.saldo("C1") == 0

def test_CT_I12_conciliar_pedido_nao_pendente(ctx):
    p = pedir(ctx)
    with pytest.raises(ErroNegocio) as e:
        ctx.svc.conciliar(p.id)
    assert e.value.codigo == "PEDIDO_NAO_PENDENTE"

def test_CT_I13_cancelar_pedido_inexistente(ctx):
    with pytest.raises(ErroNegocio) as e:
        ctx.svc.cancelar("PED-X", "a", "b")
    assert e.value.codigo == "PEDIDO_INEXISTENTE"

def test_CT_I14_gateway_mock_consulta_referencia_desconhecida():
    assert GatewayMock().consultar("XYZ").aprovado is False
