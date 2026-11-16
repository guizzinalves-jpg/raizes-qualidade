"""Mutação manual (poor man's mutation testing): injeta defeitos e verifica se a suíte os detecta."""
import shutil, subprocess, json, pathlib, re
M = [
 ("M01", "domain.py", "return total_centavos // 100", "return total_centavos // 10", "Pontos: 1 por R$ 1 → 1 por R$ 0,10"),
 ("M02", "domain.py", "QTD_MIN, QTD_MAX = 1, 20", "QTD_MIN, QTD_MAX = 1, 21", "Limite de quantidade 20 → 21"),
 ("M03", "domain.py", "self.sazonal_de <= dia <= self.sazonal_ate", "self.sazonal_de <= dia < self.sazonal_ate", "Fim da janela sazonal exclusivo"),
 ("M04", "application.py", "if existente:", "if False:", "Remove idempotência (RN05)"),
 ("M05", "application.py", "if pedido.cliente_id and pedido.consentimento_fidelidade:", "if pedido.cliente_id:", "Pontua sem consentimento (LGPD)"),
 ("M06", "application.py", "            pedido.status = StatusPedido.PAGAMENTO_RECUSADO\n            self._liberar_estoque(pedido)", "            pedido.status = StatusPedido.PAGAMENTO_RECUSADO", "Não libera estoque na recusa"),
 ("M07", "application.py", "TENTATIVAS_GATEWAY = 2", "TENTATIVAS_GATEWAY = 1", "Sem retentativa no gateway"),
 ("M08", "application.py", "if p.status == StatusPedido.PAGO:\n            raise ErroNegocio(\"CANCELAMENTO_NEGADO\"", "if False:\n            raise ErroNegocio(\"CANCELAMENTO_NEGADO\"", "Permite cancelar pedido pago"),
 ("M09", "infrastructure.py", "return re.sub(r\"[\\w.+-]+@[\\w-]+\\.[\\w.]+\", \"***@***\", texto)", "return texto", "Desativa mascaramento de e-mail"),
 ("M10", "api.py", "\"PAGAMENTO_PENDENTE\": 202", "\"PAGAMENTO_PENDENTE\": 200", "HTTP do timeout 202 → 200"),
 ("M11", "application.py", "if canal in CANAIS_QUE_EXIGEM_CLIENTE and not cliente_id:", "if False:", "Não exige login nos canais APP/WEB/PICKUP"),
 ("M12", "application.py", "if self.estoque.disponivel(unidade_id, sku) < qtd:", "if False:", "Ignora verificação de estoque"),
]
res = []
for mid, f, a, b, desc in M:
    d = pathlib.Path("/tmp/mut"); shutil.rmtree(d, ignore_errors=True); shutil.copytree(".", d, ignore=shutil.ignore_patterns("out", "img", "__pycache__", ".pytest_cache", ".coverage"))
    p = d / "src/raizes" / f; t = p.read_text()
    if a not in t: res.append((mid, desc, "ERRO-trecho-nao-encontrado", "")); continue
    p.write_text(t.replace(a, b, 1))
    r = subprocess.run(["python3", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=d, capture_output=True, text=True)
    failed = re.findall(r"FAILED tests/\S+::(\S+)", r.stdout)
    res.append((mid, desc, "MORTO" if r.returncode != 0 else "SOBREVIVEU", failed[0] if failed else ""))
json.dump(res, open("out/mutation.json", "w"), ensure_ascii=False, indent=1)
for x in res: print(x)
k = sum(1 for x in res if x[2] == "MORTO"); print(f"{k}/{len(res)} mortos")
