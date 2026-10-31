# Evidências do T3

Cópia sem alteração dos logs gerados por `lab.py` em `evidencias/execucoes/` (pasta ignorada pelo Git) durante o T3, em 31/10/2026, separados por exercício. As execuções que falharam estão incluídas. O nome de cada log começa com a data e a hora locais (UTC−3) da execução. A relação entre cada arquivo, o cenário e a interpretação está em `registro.csv`.

| Pasta | Conteúdo |
|---|---|
| `E1_expansao_backfill/` | Estado inicial com v1, expansão por Flyway, clientes 42 e 55, comparação `<>` × `IS DISTINCT FROM`, convivência v1/v2 com backfill, interrupção, retomada e repetição de lote |
| `E2_contracao/` | Gate (retirada, teste de retorno, janela de 10 ciclos, liberação), contração por Flyway, cliente final e verificações |
| `E3_saga_codigo/` | Teste unitário com as funções da Saga completadas (6/6) |
| `E4_saga_cenarios/` | Cenários S1 a S6, falhas injetadas (código 17), rejeição de mudança de modo e consultas dos três bancos |
| `E6_pitr/tentativa1_falha_podman/` | Primeira tentativa, interrompida: o aviso do Podman contaminou o nome do segmento WAL (`Nome WAL inválido`). Inclui o controle arquivado pelo `reset pitr` |
| `E6_pitr/tentativa2/` | Backup, incidente, restauração até o marcador, consultas do destino e da origem, status e teste de falta de WAL |
| `E7_metricas/` | `pitr-controle.json`, `pitr-metricas.json` e `pitr-operacoes.csv`, gerados pelo kit. O `registro_controle.csv` foi **derivado** desses arquivos e do log do backup, com as colunas pedidas no enunciado |

O comando `pitr medir` não gera arquivo `.log`, porque não executa comandos externos. Sua saída é o `pitr-metricas.json`.
