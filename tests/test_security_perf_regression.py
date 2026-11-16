"""SEGURANÇA/LGPD, DESEMPENHO (micro-benchmark em processo) e REGRESSÃO (CT-SEC*, CT-P*, CT-R*)."""
import json, statistics, time
from raizes.api import post_pedidos

def corpo(i):
    return {"unidade_id": "REC01", "canal": "APP", "cliente_id": f"C{i}", "token_pagamento": "tok_ok",
            "consentimento_fidelidade": True, "itens": [{"sku": "CUSCUZ", "quantidade": 1}]}

def test_CT_SEC01_log_de_auditoria_nao_contem_dados_pessoais(ctx):
    ctx.svc.auditoria.registrar("c", "TESTE", detalhe="CPF 123.456.789-09 ana@exemplo.com")
    texto = json.dumps(ctx.aud.eventos)
    assert "123.456.789-09" not in texto and "ana@exemplo.com" not in texto

def test_CT_SEC02_resposta_da_api_nao_expoe_token_nem_dados_de_cartao(ctx):
    st, r = post_pedidos(ctx.svc, corpo(1), {"Idempotency-Key": "s1"})
    assert "tok_ok" not in json.dumps(r) and "cartao" not in json.dumps(r).lower()

def test_CT_SEC03_sem_consentimento_nenhum_ponto_e_registrado(ctx):
    b = corpo(2); b["consentimento_fidelidade"] = False
    post_pedidos(ctx.svc, b, {"Idempotency-Key": "s2"})
    assert ctx.fid.saldo("C2") == 0

def test_CT_SEC04_entrada_maliciosa_nao_quebra_servico(ctx):
    b = corpo(3); b["itens"] = [{"sku": "'; DROP TABLE pedidos;--", "quantidade": 1}]
    st, r = post_pedidos(ctx.svc, b, {"Idempotency-Key": "s3"})
    assert st == 422 and r["codigo"] == "ITEM_INDISPONIVEL"

def test_CT_P01_microbenchmark_500_pedidos_p95_abaixo_de_50ms(ctx):
    ctx.estoque.saldo[("REC01", "CUSCUZ")] = 10_000
    tempos = []
    for i in range(500):
        t = time.perf_counter()
        st, _ = post_pedidos(ctx.svc, corpo(i), {"Idempotency-Key": f"p{i}"})
        tempos.append((time.perf_counter() - t) * 1000); assert st == 201
    p95 = statistics.quantiles(tempos, n=100)[94]
    print(f"\n[CT-P01] n=500  media={statistics.mean(tempos):.3f} ms  p95={p95:.3f} ms  max={max(tempos):.3f} ms")
    assert p95 < 50

def test_CT_R01_regressao_fluxo_critico_completo(ctx):
    """Smoke/regressão do fluxo crítico: pedido -> pagamento -> estoque -> pontos -> auditoria."""
    st, r = post_pedidos(ctx.svc, corpo(9), {"Idempotency-Key": "r1", "X-Correlation-Id": "reg"})
    assert st == 201 and ctx.fid.saldo("C9") == 18 and any(e["correlation_id"] == "reg" for e in ctx.aud.eventos)
