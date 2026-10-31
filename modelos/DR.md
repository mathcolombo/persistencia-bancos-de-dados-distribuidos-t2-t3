# Plano de recuperação — Loja Horizonte

Até duas páginas, incluídas no relatório T3.

## Escopo e objetivos
| Componente | Fonte autoritativa ou reconstruível | RPO | RTO | Justificativa |
|---|---|---|---|---|
| Pedidos | | | | |
| Estoque | | | | |
| Pagamentos | | | | |
| Catálogo | | | | |
| Busca e cache | | | | |

## Incidente e estratégia
[Backup/restore, pilot light, warm standby ou active-active. Custos e limites.]

## Dependências e sequência
[Ordem de restauração, infraestrutura, configurações, acessos e dados.]

## Coerência entre serviços
[Como tratar pagamento confirmado sem pedido finalizado e pedido sem reserva. Não supor que horários iguais de backup garantem snapshot global.]

## Validação e liberação
[Responsáveis, testes, métricas e critério para suspender a reabertura.]

## Proteção e ensaio
[Disponibilidade dos backups, WAL e chaves sob o incidente; periodicidade do teste e evidências.]
