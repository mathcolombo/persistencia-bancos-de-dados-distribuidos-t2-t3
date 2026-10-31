# T3 E4 Falhas repetição e comparação com 2PC
Cada linha da matriz deve ser executada em uma massa isolada com estoque inicial igual a cinco. Registrem saldo inicial e final, estado da reserva, quantidade de cobranças, estado do pedido e eventos persistidos.
| Cenário | Procedimento e critério de aceite |
| S1 Sucesso | Reservar pagar e confirmar resulta em estoque quatro uma reserva ativa e uma cobrança |
| S2 Rejeição | Pagamento rejeitado após reserva resulta em CANCELADO estoque cinco reserva LIBERADA e zero cobranças |
| S3 Compensação repetida | Repetir a liberação de S2 duas vezes mantém estoque cinco e um único efeito de devolução |
| S4 Reinício após reserva | Encerrar o orquestrador depois da reserva e antes da etapa seguinte retomar pela mesma intenção sem nova baixa |
| S5 Falha após compensar | Encerrar após commit da liberação mas antes de registrar conclusão na Saga retomar e terminar CANCELADO com estoque cinco |
| S6 Repetição de sucesso | Reenviar a mesma intenção de S1 mantém uma cobrança e uma única reserva |
Em S4, configurem rejeição no pagamento para que a conclusão após retomada seja CANCELADO. Os pontos de parada são controles do simulador, não encerramentos arbitrários do banco. S5 demonstra a diferença entre efeito já confirmado e resposta ou progresso ainda não persistido.
## Resultado desconhecido
Sem executar cobrança externa, analisem um timeout ocorrido depois de uma cobrança possivelmente concluída. Indiquem o estado persistido adequado, a identidade usada na reconciliação e o risco de criar outra chave. Rejeição conhecida e ausência de resposta não podem ser tratadas como equivalentes.
## T3 E5 Traço de Two Phase Commit
Traço fornecido: coordenador C envia PREPARE a P1 e P2; ambos persistem estado preparado e votam SIM; C persiste decisão COMMIT; P1 recebe COMMIT e confirma; C falha antes de enviar a decisão a P2. P2 continua preparado e não recebe informação de P1 enquanto a comunicação necessária está indisponível.
Completem uma tabela com estado de cada participante após cada evento. Expliquem por que P2 não pode abortar apenas porque seu timeout expirou; que informação deve recuperar; e como seria possível retomar quando a decisão durável ficar acessível. Trata-se de simulação de protocolo, sem obrigatoriedade de PREPARE TRANSACTION no banco.
Comparem 2PC e Saga em atomicidade da decisão, visibilidade dos estados intermediários, retenção de recursos, compensação e recuperação. Não confundam protocolo de commit com uma especificação completa de isolamento.

# T3 E8 Plano de disaster recovery
Produzam um plano de até duas páginas para a Loja Horizonte com pedidos, estoque, pagamento simulado, catálogo e projeção de busca. Não contratem nuvem. A proposta cloud native é documental e deve considerar automação de provisionamento, configuração, armazenamento persistente e observabilidade da recuperação.
## Conteúdo obrigatório
- Objetivos de RPO e RTO por componente e sua justificativa de negócio.
- Fontes autoritativas e componentes reconstruíveis como caches e índices quando essa hipótese for válida.
- Ordem de recuperação com dependências entre serviços e validações antes de reabrir operações.
- Estratégia escolhida entre backup e restore pilot light warm standby ou active active com custo e limite reconhecidos.
- Proteção e disponibilidade de backups WAL configurações e chaves necessárias sob o incidente previsto.
- Procedimento de reconciliação para pedido confirmado sem reserva correspondente e pagamento confirmado sem pedido concluído.
- Responsável por cada ação papel que autoriza retorno e critério de suspensão se as validações falharem.
- Ensaio periódico proposto com indicadores e evidências que demonstram capacidade real.
A infraestrutura pode ser descrita de forma independente de provedor. Containers na mesma máquina não representam regiões independentes. Não presuma que backups tirados no mesmo horário oferecem consistência global entre bancos.
## Entrega consolidada
Tag T3 ou commit imutável, código completado, migrações, configuração, README, relatório e diretório de evidências por exercício. Relatório de até oito páginas, incluindo as duas páginas de DR, sem contar código, logs integrais, CSV e referências.
Organização recomendada do relatório: duas páginas para migração; duas para Saga e 2PC; duas para PITR e métricas; duas para DR. Incluam respostas discursivas junto das evidências pertinentes. O registro individual pode ser anexo.
## Lista final de aceite
Confiram divergência zero após backfill; histórico de migrações; encerramento da convivência; seis cenários da Saga; tabela 2PC; restauração em volume separado; ids preservados e excluídos; RPO RTO e perda por operação; plano de coerência entre serviços; contribuição de todos. Um erro de infraestrutura deve ser registrado, não substituído por log de referência apresentado como execução própria.
