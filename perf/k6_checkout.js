import http from 'k6/http'; import { check, sleep } from 'k6'; import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
export const options = {
  stages: [ {duration:'1m',target:200}, {duration:'10m',target:200}, {duration:'2m',target:500}, {duration:'5m',target:500}, {duration:'1m',target:0} ],
  thresholds: { http_req_duration: ['p(95)<2000'], http_req_failed: ['rate<0.01'] },
};
const UNIDADES = Array.from({length:20}, (_, i) => `U${String(i+1).padStart(2,'0')}`);
export default function () {
  const body = JSON.stringify({ unidade_id: UNIDADES[__VU % 20], canal: 'APP', cliente_id: `C${__VU}`,
    token_pagamento: 'tok_ok', consentimento_fidelidade: false, itens: [{sku:'CUSCUZ', quantidade:1}] });
  const r = http.post(`${__ENV.BASE_URL}/v1/pedidos`, body,
    { headers: {'Content-Type':'application/json','Idempotency-Key': uuidv4(), 'X-Correlation-Id': uuidv4()} });
  check(r, { 'status 201': (x) => x.status === 201 });
  sleep(1);
}
