# Raízes do Nordeste – Projeto de Qualidade de Software

Projeto Multidisciplinar (UNINTER) – Trilha Qualidade de Software
Aluno: Guilherme Alves dos Santos Corrêa – RU 4899688

Protótipo de referência do fluxo **Realizar Pedido com Pagamento** (pagamento apenas simulado) usado como objeto de teste.

## Como executar
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest pytest-cov
pytest -v --cov=src/raizes --cov-branch --cov-report=term-missing --junitxml=out/junit.xml -s
python3 mutation.py   # teste de mutação manual (12 defeitos injetados)
```

## Estrutura
- `src/raizes/` – domain, ports, application, infrastructure, api
- `tests/` – unitário, integração, sistema (API), segurança/desempenho/regressão
- `perf/k6_checkout.js` – script de carga (k6) para homologação
- `out/` – resultados da execução (junit.xml, pytest_output.txt, mutation.json)
