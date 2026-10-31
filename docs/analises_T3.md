# Análises T3 — E4 (resultado desconhecido), E5 (2PC) e E8

Classificação: **SIMULAÇÃO/ANÁLISE**. Nenhuma cobrança externa nem `PREPARE TRANSACTION` foi executado. Os cenários S1 a S6 da matriz foram executados de verdade e estão no relatório (seção 2) e em `evidencias/T3/E4_saga_cenarios/`.

---

# T3 E4 Falhas, repetição e comparação com 2PC

A matriz S1–S6 foi executada com massas isoladas (estoque inicial 5 por `op`). Os resultados estão no relatório.

## Resultado desconhecido

**Cenário analisado.** O orquestrador chama o pagamento da intenção `op = X`. A chamada termina em timeout **depois** que o provedor possivelmente lançou a cobrança. O orquestrador não sabe se houve cobrança.

**Estado persistido adequado.** Registrar na Saga um estado explícito de incerteza, por exemplo `PAGAMENTO_INCERTO`, ou manter `RESERVADO` com um evento "tentativa de pagamento sem resposta" e o número de tentativas. **Não** registrar `COMPENSACAO_PENDENTE`, porque isso liberaria a reserva e cancelaria o pedido com base num "não" que nunca foi recebido. A reserva continua ATIVA até a reconciliação. Na política de `proxima`, esse estado leva à ação "consultar pagamento" e nunca a "liberar".

**Identidade usada na reconciliação.** A **mesma** `operacao_id` (`op`) da intenção original, que funciona como chave de idempotência no provedor. O orquestrador consulta o pagamento por `op`:
- se o resultado for aprovado, persiste `PAGAMENTO_CONFIRMADO` e segue para confirmar;
- se o resultado for rejeitado, persiste `COMPENSACAO_PENDENTE` e libera a reserva;
- se não houver registro, repete a chamada com o **mesmo** `op`.

No kit, `pay()` faz isso com `INSERT … ON CONFLICT DO NOTHING` sobre a chave primária `op` e devolve o resultado anterior. Uma repetição com outro modo é recusada (evidência real: `Modo mudou para a mesma intenção`, log `193746`).

**Risco de criar outra chave.** Repetir com um `op` novo faz o provedor tratar a repetição como uma **segunda intenção**. Se a primeira cobrança tiver acontecido, o cliente é cobrado duas vezes, e uma das cobranças fica sem pedido correspondente. A incerteza não desaparece: ela vira duplicidade, e a reconciliação passa a envolver estorno.

**Rejeição conhecida e ausência de resposta não são equivalentes.** A rejeição é um resultado definitivo e durável no provedor: compensar é seguro. A ausência de resposta é desconhecimento: compensar pode cancelar um pedido que foi pago, e repetir com outra chave pode cobrar duas vezes. É o mesmo fenômeno observado no T2 (id 2004): o cliente não recebeu resposta a tempo, e a verdade foi obtida consultando pelo mesmo identificador.

---

# T3 E5 Traço de Two Phase Commit

A tabela completa está em `dados/2pc.csv`.

| # | Evento | C (coordenador) | P1 | P2 |
|---|---|---|---|---|
| 1 | C envia PREPARE | Preparando; pode abortar | Ativo; pode abortar | Ativo; pode abortar |
| 2 | P1 e P2 persistem PREPARED e votam SIM | Votos SIM recebidos; sem decisão durável | **Preparado** (durável; recursos retidos) | **Preparado** |
| 3 | C persiste COMMIT | **COMMIT durável** (ponto de decisão) | Preparado | Preparado |
| 4 | P1 recebe COMMIT e confirma | Aguarda P2 | **Confirmado**; recursos liberados | Preparado |
| 5 | C falha antes de notificar P2 | Indisponível; COMMIT gravado no log | Confirmado | Preparado e incerto |
| 6 | P2 não alcança C nem P1 | Indisponível | Confirmado | **Bloqueado**, retendo recursos |

**Por que P2 não pode abortar só porque o timeout expirou.** Ao votar SIM e persistir PREPARED, P2 abriu mão do direito de decidir sozinho: prometeu confirmar se a decisão for COMMIT. Neste traço, a decisão **é** COMMIT e P1 **já confirmou**. Se P2 abortasse, a transação ficaria confirmada em P1 e abortada em P2, e a atomicidade, que é a única garantia do protocolo, seria violada. O timeout só autoriza abortar **antes** do voto. Depois dele, o silêncio de C não informa qual foi a decisão, porque C pode ter falhado antes ou depois de persistir COMMIT. É a mesma indistinguibilidade da partição do T2 E4.

**Informação que P2 deve recuperar.** O **resultado da decisão** para o identificador global da transação (*gid*): COMMIT ou ABORT. As fontes são:
- o **log durável de C**, depois que C se recuperar;
- **outro participante que conheça o resultado**: se P2 alcançar P1 e souber que P1 confirmou, a decisão só pode ter sido COMMIT (protocolo de terminação cooperativa).

Se todos os participantes alcançáveis estiverem apenas preparados, P2 continua bloqueado.

**Como retomar quando a decisão durável ficar acessível.** Ao reiniciar, C lê seu log, encontra COMMIT para o *gid* sem a confirmação de P2 e reenvia COMMIT. P2 aplica a confirmação; no PostgreSQL isso seria `COMMIT PREPARED 'gid'`. P2 responde, e só então C pode descartar o registro da transação. Por isso C não pode apagar a decisão antes de todos os participantes confirmarem. Se P2 se recuperar primeiro, ele consulta C, ou P1, pelo *gid*. Enquanto isso, os recursos de P2 ficam retidos. Esse é o custo de bloqueio do 2PC, que variantes como o Paxos Commit (Gray e Lamport) reduzem replicando a decisão.

## Comparação 2PC × Saga

| Critério | 2PC | Saga (como no kit) |
|---|---|---|
| Atomicidade da decisão | Atômica: todos confirmam ou todos abortam, com um ponto de decisão único e durável no coordenador | Não atômica: cada etapa confirma localmente. A "atomicidade" é semântica e depende de compensações corretas |
| Visibilidade de estados intermediários | Participantes preparados não expõem o efeito antes da decisão | Visíveis: estoque 4 com Saga `PENDENTE` (S4) e reserva LIBERADA com Saga `COMPENSACAO_PENDENTE` (S5) foram observados |
| Retenção de recursos | Locks retidos do PREPARE até a decisão chegar. Com o coordenador falho, retenção por tempo indeterminado (P2 bloqueado) | Cada transação local libera seus locks ao confirmar. A "retenção" é de negócio (a reserva ATIVA), com estado explícito |
| Compensação | Desnecessária: o abort desfaz o que estava preparado | Obrigatória e precisa ser idempotente: `UPDATE … WHERE estado='ATIVA' RETURNING` impediu estoque 6 (S3, S5) |
| Recuperação | Pelo log do coordenador e pelo estado preparado dos participantes. Pode bloquear | Pelo estado persistido da Saga e pela repetição idempotente por `op`. Não bloqueia, mas exige que cada serviço reconheça repetições |

Um protocolo de commit decide **se** a transação distribuída confirma. Ele não especifica **isolamento**. Em 2PC, o isolamento entre transações concorrentes continua dependendo de cada participante (níveis de isolamento e locks locais). A Saga sem bloqueios semânticos (*semantic locks*, versões) expõe estados intermediários a outras transações, o que exige contramedidas próprias.

---

# T3 E8 Plano de disaster recovery

O plano está em `modelos/DR.md` e foi incorporado à seção 4 do relatório (`modelos/relatorio.md`).
