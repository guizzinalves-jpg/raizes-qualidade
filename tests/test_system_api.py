"""TESTES DE SISTEMA (via API, ponta a ponta no ambiente controlado) - cenários CT-S01..CT-S14."""
import pytest
from raizes.api import post_pedidos

H = {"Idempotency-Key": "chave-1", "X-Correlation-Id": "corr-sys"}

def corpo(**kw):
    b = {"unidade_id": "REC01", "canal": "APP", "cliente_id": "C1", "token_pagamento": "tok_ok",
         "consentimento_fidelidade": True, "itens": [{"sku": "TAPIOCA", "quantidade": 2}]}
    b.update(kw); return b

def test_CT_S01_app_pedido_pago_201(ctx):
    st, r = post_pedidos(ctx.svc, corpo(), H)
    assert st == 201 and r["status"] == "PAGO" and r["total_centavos"] == 2400 and r["correlation_id"] == "corr-sys"

@pytest.mark.parametrize("canal,cliente", [("TOTEM", None), ("BALCAO", None), ("WEB", "C1"), ("PICKUP", "C1")])
def test_CT_S02_multicanal_todos_os_canais_concluem(ctx, canal, cliente):
    st, r = post_pedidos(ctx.svc, corpo(canal=canal, cliente_id=cliente, consentimento_fidelidade=False), H)
    assert st == 201 and r["status"] == "PAGO"

def test_CT_S03_app_sem_login_422(ctx):
    st, r = post_pedidos(ctx.svc, corpo(cliente_id=None), H)
    assert st == 422 and r["codigo"] == "CLIENTE_OBRIGATORIO" and r["mensagem"] == "Faça login para continuar com este canal."

def test_CT_S04_carrinho_vazio_422(ctx):
    st, r = post_pedidos(ctx.svc, corpo(itens=[]), H)
    assert st == 422 and r["codigo"] == "CARRINHO_VAZIO"

def test_CT_S05_quantidade_acima_do_limite_422(ctx):
    st, r = post_pedidos(ctx.svc, corpo(itens=[{"sku": "CUSCUZ", "quantidade": 21}]), H)
    assert st == 422 and r["codigo"] == "QTD_INVALIDA"

def test_CT_S06_item_inexistente_na_unidade_reduzida_422(ctx):
    st, r = post_pedidos(ctx.svc, corpo(unidade_id="SSA02", itens=[{"sku": "CUSCUZ", "quantidade": 1}]), H)
    assert st == 422 and r["codigo"] == "ITEM_INDISPONIVEL"

def test_CT_S07_produto_sazonal_fora_de_epoca_422(ctx):
    st, r = post_pedidos(ctx.svc, corpo(itens=[{"sku": "CANJICA", "quantidade": 1}]), H)
    assert st == 422 and r["codigo"] == "ITEM_INDISPONIVEL"

def test_CT_S08_produto_sazonal_em_epoca_junina_201(ctx):
    from datetime import date
    ctx.hoje = date(2026, 6, 20)
    st, r = post_pedidos(ctx.svc, corpo(itens=[{"sku": "CANJICA", "quantidade": 1}]), H)
    assert st == 201

def test_CT_S09_estoque_insuficiente_422(ctx):
    st, r = post_pedidos(ctx.svc, corpo(itens=[{"sku": "TAPIOCA", "quantidade": 6}]), H)
    assert st == 422 and r["codigo"] == "ESTOQUE_INSUFICIENTE" and "Tapioca de queijo" in r["mensagem"]

def test_CT_S10_pagamento_recusado_402(ctx):
    ctx.gw.modo = "negar"
    st, r = post_pedidos(ctx.svc, corpo(), H)
    assert st == 402 and r["status"] == "PAGAMENTO_RECUSADO"

def test_CT_S11_timeout_do_gateway_202_pendente(ctx):
    ctx.gw.modo = "timeout"
    st, r = post_pedidos(ctx.svc, corpo(), H)
    assert st == 202 and r["status"] == "PAGAMENTO_PENDENTE"

def test_CT_S12_gateway_fora_do_ar_503(ctx):
    ctx.gw.modo = "indisponivel"
    st, r = post_pedidos(ctx.svc, corpo(), H)
    assert st == 503 and r["status"] == "PAGAMENTO_FALHOU"

def test_CT_S13_sem_idempotency_key_400(ctx):
    st, r = post_pedidos(ctx.svc, corpo(), {})
    assert st == 400 and r["codigo"] == "IDEMPOTENCY_KEY_AUSENTE"

def test_CT_S14_canal_invalido_400(ctx):
    st, r = post_pedidos(ctx.svc, corpo(canal="TELEFONE"), H)
    assert st == 400 and r["codigo"] == "CANAL_INVALIDO"

def test_CT_S15_unidade_invalida_e_pagamento_nao_informado(ctx):
    st, r = post_pedidos(ctx.svc, corpo(unidade_id="XXX"), H)
    assert st == 422 and r["codigo"] == "UNIDADE_INVALIDA"
    st, r = post_pedidos(ctx.svc, corpo(token_pagamento=None), {"Idempotency-Key": "k2"})
    assert st == 422 and r["codigo"] == "PAGAMENTO_INVALIDO"
