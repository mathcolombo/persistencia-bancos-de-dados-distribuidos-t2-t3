# Contribuições — T3

Grupo, integrantes e commit: trabalho individual — Matheus Colombo da Cruz. Entrega na tag `T3` (T1 em `0b4458f`, T2 em `59b3b0a`).

Execução e análise: todos os comandos foram executados por Matheus Colombo da Cruz na própria máquina (Linux, Podman 6.1.4 rootless com Docker Compose v5.3.1), e a análise dos resultados também foi feita por ele.

## Matheus Colombo da Cruz

- **Atividade concreta realizada:**
  - implementação da sincronização em `V1__expand.sql`;
  - implementação de `proxima`, `apos_pagamento` e `liberar_sql`;
  - execução da migração com convivência e backfill, dos cenários S1 a S6 e do PITR, incluindo o diagnóstico da tentativa 1 e a nova execução;
  - redação das análises de resultado desconhecido e 2PC, do plano de DR e do relatório.
- **Arquivo, teste ou resultado em que trabalhou:**
  - `migrations/expand/V1__expand.sql`, `exercicios/respostas.py` e `exercicios/pitr.json`;
  - `docs/analises_T3.md`, `dados/2pc.csv`, `modelos/DR.md` e `modelos/relatorio.md`;
  - teste unitário 6/6;
  - evidências em `evidencias/T3/`.
- **Explicação de uma evidência (S5, falha após compensar):** No cenário t3_s5, o orquestrador foi interrompido logo depois do commit da liberação da reserva. O snapshot intermediário mostrou reserva LIBERADA e estoque 5 no banco de estoque, enquanto a Saga continuava em COMPENSACAO_PENDENTE no banco de pedidos. O efeito já estava confirmado, mas o progresso não. Na retomada, o orquestrador leu o estado persistido e repetiu a liberação. Como o UPDATE só altera reservas ATIVA, nenhuma linha retornou, o estoque não subiu para 6, e a Saga apenas registrou CANCELADO. Isso mostra que a retomada depende do armazenamento e da idempotência, não da memória do processo anterior.
- **Limitação identificada:** os três bancos da Saga estão na mesma instância PostgreSQL, e as falhas injetadas são controles do simulador. O ensaio não reproduz perda de máquina, partição de rede nem um timeout real do provedor de pagamento, que foi tratado apenas por análise.
