# Relatório T3 — Evolução, transações e recuperação

**Integrante:** Matheus Colombo da Cruz (trabalho individual) · **Data:** 31/10/2026 · **Entrega:** tag `T3` · T1 preservado em `0b4458f` e T2 em `59b3b0a` (tag `T2`)

**Ambiente:** PostgreSQL 18.6 (`postgres:18.6-bookworm@sha256:3725f4e2…6650`, mesma imagem em todas as instâncias) · Flyway Community 13.7.0 · Podman 6.1.4 rootless com Docker Compose v5.3.1 · Linux amd64 · linguagem **Python** (psycopg 3.2.6 em contêiner Python 3.12.9).

**Classificação:** cada resultado é marcado como **MEDIÇÃO** (executado no laboratório), **SIMULAÇÃO** (protocolo analisado sem execução) ou **PROPOSTA** (plano). As evidências estão em `evidencias/T3/<exercício>/` e o registro por cenário (entrada, previsão, saída, horário, interpretação e arquivo) está em `evidencias/T3/registro.csv`. Os horários são UTC. Os nomes dos logs usam a hora local (UTC−3).

## 1. Migração expand/contract (E1 e E2) — MEDIÇÃO

**Autoridade.** Enquanto houver escritor v1, `contato_email` é a única autoridade, e `email` é uma cópia mantida pelo trigger `BEFORE INSERT OR UPDATE OF contato_email` (`NEW.email := NEW.contato_email`), na **mesma transação** da escrita, inclusive para NULL. O backfill copia `email = contato_email` dentro do próprio UPDATE, lendo a autoridade no momento da escrita, e grava o checkpoint na mesma transação do lote.

| Etapa | Evidência (E1/E2) | Resultado |
|---|---|---|
| v1 no esquema inicial | `192242`, `192304`, `192316` | 18 = `bruno@exemplo.test`, 42 = `ana@exemplo.test`. O v1 alterou e leu o 42 (NULL e depois `ana.1@…`). Total de 200 clientes |
| Expansão (Flyway) | `192355`, `192400` | Baseline v0 e V1 `expand` com `success = t` (V1 executada em 25 ms) |
| Cliente 42 pelo v1 | `192426` | `42 \| ana.nova@exemplo.test \| ana.nova@exemplo.test` |
| Cliente 55 com NULL | `192426`, `192437` | `55 \| NULL \| NULL`, sem divergência |
| Comparação de NULL | `192446` | `email <> contato_email` = **0** e `IS DISTINCT FROM` = **179** antes do backfill |
| Convivência e backfill | `192614` (v1 ×60), `192644` e `192746` (v2 ×60, executado duas vezes), backfill `192706` a `192848` | Os clientes registraram cada escrita e a leitura seguinte, sem erros (`exit=0`) |
| Validação final | `192812`, `192905` | Divergência **0** após o backfill e **0** após a repetição |

**Backfill por lotes** (até 25 linhas, checkpoint persistido em `lab_checkpoint`): `backfill 2` processou 0→1021 (25) e 1021→1046 (25) e **parou** com checkpoint 1046 (`192721`). `backfill 100` **retomou** em 1046 e processou 1046→1071 … 1171→1196 (25 cada) e 1196→1197 (1), terminando no checkpoint 1197: 9 lotes e 201 linhas, contando o cliente 55. Para a **repetição**, voltei o checkpoint para 0 durante a convivência (o v2 ainda rodava). `backfill 1` refez 0→1021 e `backfill 100` refez os demais, e a divergência continuou 0. O resultado é coerente porque o lote não grava valores guardados em memória: ele relê a coluna autoritativa. Repetir um lote só reescreve o valor atual, inclusive o do 42, que v1 e v2 alteravam ao mesmo tempo.

**Os três casos de validação** (`192437`, `192905`): iguais e não nulos (18, divergente antes do backfill e igual depois); ambos nulos (1000 e 55: `IS DISTINCT FROM` = falso, enquanto `<>` daria NULL e esconderia a linha); alterado durante a convivência (42, divergência 0 com escritas concorrentes de v1 e v2). As 179 linhas invisíveis ao `<>` mostram por que a comparação comum não substitui a verificação de NULL.

**Janela de retorno e contração** (gate com lock consultivo exclusivo na troca de fase e compartilhado em cada operação):

| Comando | Horário | `lab_gate` (fase, ciclos, retorno) | Evidência |
|---|---|---|---|
| estado inicial | 22:30:14 | `old, 0, f` | `193014` |
| `gate retirar` | 22:30:23 | `window, 0, f` (v1 retirado) | `193023` |
| `gate retorno` e `v1 1` | 22:30:32–22:30:42 | `return-test`; v1 operou com sucesso (408,6 ms), `returned = t` | `193032`, `193041` |
| `gate janela` e `v2 10` | 22:30:48–22:31:06 | `window, 0, t` e depois 10 ciclos, um por segundo, preservando campo e trigger antigos | `193048`, `193056` |
| `gate liberar` | 22:31:10 | `final, 10, t` (exigiu retorno testado, 10 ciclos e divergência 0) | `193110` |
| `migrate contract` | 22:31:20 | V2 `contract` executada em 36 ms. Ela revalida o gate e a divergência antes do DROP | `193117`, `193159` |
| `final 2` | 22:31:46 | Só a v2 final ativa, lendo e escrevendo `email`. Colunas: `id, nome, email` | `193146`, `193215`, `193222` |

O Flyway executou apenas os arquivos da fase. A V2 ficou em `migrations/contract` e só foi incluída no comando de contração, depois da liberação do gate.

**Continuidade observada** (logs dos clientes e `lab_ops`, `193229`):

| Fase | Tentadas | Sucessos | Erros | Maior duração | Maior duração sem a 1ª operação de cada processo |
|---|---|---|---|---|---|
| Antes (v1) | 2 | 2 | 0 | 276,0 ms | 28,2 ms |
| Expansão e backfill (v1 60 + v2 120) | 180 | 180 | 0 | 378,9 ms | 45,1 ms |
| Janela de retorno (v1 1 + v2 10) | 11 | 11 | 0 | 408,6 ms | 60,2 ms |
| Contração (final) | 2 | 2 | 0 | 243,8 ms | 25,4 ms |
| **Total** | **195** | **195** | **0** | | |

A primeira operação de cada processo inclui a abertura da conexão, por isso a coluna extra. O `lab_ops` confirma o total (v1 63, v2 130, final 2). **Espera introduzida no ponto de controle:** é uma **indisponibilidade planejada de escrita**, não uma falha. Entre `gate liberar` (22:31:10) e a primeira operação do cliente final (22:31:46) nenhum cliente podia escrever: cerca de 36 s, dominados pelo intervalo manual entre comandos (a V2 levou 36 ms). Como o gate só troca de fase com lock exclusivo, nenhuma operação ficou pela metade. A amostra demonstra a compatibilidade e a sequência segura com 201 linhas e sem carga concorrente na hora da DDL. Ela **não** demonstra zero downtime: os riscos de lock com transações longas e de volume (backfill de milhões de linhas, `DROP COLUMN` sob carga) continuam abertos.

**Questões.**
- **Renomear direto quebra o v1** porque ele executa `UPDATE … SET contato_email` e `SELECT contato_email`. Depois de um `RENAME`, todas as 63 operações do v1 falhariam com "column does not exist". Com expand/contract, o v1 operou sem erro até ser retirado e voltou a operar no teste de retorno.
- **Limite do COALESCE:** `COALESCE(email, contato_email)` só cobre o caso `email` NULL. Ele não corrige uma cópia **não nula e desatualizada**: se o v1 grava NULL ou um valor novo em `contato_email` e nada sincroniza, o v2 continua lendo o `email` antigo. Ele também não distingue "nulo legítimo" (55, 1000) de "ainda não copiado". Por isso o trigger sincroniza inclusive o NULL.
- **Sucesso do Flyway não comprova ausência de bloqueio:** "Successfully applied" (25 ms e 36 ms) diz apenas que os comandos terminaram. `ADD COLUMN` e `DROP COLUMN` pedem lock `ACCESS EXCLUSIVE`. Sob carga, a DDL espera transações longas e bloqueia as consultas que chegam depois dela. O Flyway não mede a espera dos outros. Aqui não houve contenção porque o gate tinha retirado os clientes. O `lock_timeout = 5s` limita a espera da própria DDL, não o impacto nos outros.
- **Retorno depois da contração:** antes da V2, voltar era religar o v1 (demonstrado). Depois do DROP de `contato_email` e do trigger, o v1 não roda mais. O retorno vira uma migração nova (recriar a coluna, copiar de `email`, sincronizar no sentido inverso) ou um PITR com perda das escritas posteriores. Deixa de ser rollback e passa a ser correção para frente.

## 2. Saga e 2PC (E3 a E5)

**Código (E3).** `proxima` decide a próxima etapa apenas pelo estado persistido (PENDENTE→reservar, RESERVADO→pagar, PAGAMENTO_CONFIRMADO→confirmar, COMPENSACAO_PENDENTE→liberar, CONFIRMADO ou CANCELADO→fim). `apos_pagamento` leva aprovado a PAGAMENTO_CONFIRMADO e rejeitado a COMPENSACAO_PENDENTE. `liberar_sql` é `UPDATE reserva SET estado='LIBERADA' WHERE op=%s AND estado='ATIVA' RETURNING op`: o estoque só é devolvido se houve transição, na mesma transação local. O teste unitário passou com 6/6 (`193333`).

**Mapeamento dos estados.** Pedido Saga → `pedidos.saga(op, modo, estado)`, com os nomes do enunciado. Reserva → `estoque.reserva(op, estado ATIVA/LIBERADA)` e `estoque.estoque(op, produto 10, disponivel)`, quantidade 1. Pagamento → `pagamentos.pagamento(op, resultado, cobrancas 0/1)`. Execução → `saga.estado` (última etapa) e `pedidos.evento(op, estado, instante)`. As chaves primárias por `op` e o `WHERE estado='ATIVA'` protegem contra repetição.

**Matriz (E4) — MEDIÇÃO com pagamento simulado.** Cada `op` tem estoque inicial 5 (`E4_saga_cenarios/`):

| Cenário | Comando(s) | Estoque final | Reserva | Cobranças | Pedido | Eventos persistidos |
|---|---|---|---|---|---|---|
| S1 `t3_s1` | `saga … aprovado` | 4 | ATIVA | 1 | CONFIRMADO | RESERVADO → PAGAMENTO_CONFIRMADO → CONFIRMADO |
| S2 `t3_s2` | `saga … rejeitado` | 5 | LIBERADA | 0 | CANCELADO | RESERVADO → COMPENSACAO_PENDENTE → CANCELADO |
| S3 | `liberar t3_s2` ×2 | 5 e 5 | LIBERADA | 0 | CANCELADO | nenhum evento novo (continuam 3) |
| S4 `t3_s4` | `after-reserve` (exit 17), depois retomada | intermediário 4; final **5** | ATIVA → LIBERADA | 0 | PENDENTE → CANCELADO | nenhum antes da falha; os 3 eventos surgem na retomada (22:35:59) |
| S5 `t3_s5` | `after-release` (exit 17), depois retomada | intermediário 5; final **5** | LIBERADA | 0 | COMPENSACAO_PENDENTE → CANCELADO | RESERVADO e COMPENSACAO_PENDENTE (22:36:32); CANCELADO só na retomada (22:36:45) |
| S6 | `saga t3_s1 aprovado` de novo | 4 | ATIVA | 1 | CONFIRMADO | nenhum evento novo |

No S4, a retomada leu `PENDENTE` e chamou `reservar` de novo. O serviço encontrou a reserva da mesma `op` e devolveu `ATIVA` **sem nova baixa**: o estoque terminou em 5, e não em 4. O S5 mostra a diferença entre **efeito confirmado** (reserva LIBERADA e estoque 5 já gravados no banco `estoque`) e **progresso não persistido** (Saga ainda em COMPENSACAO_PENDENTE). A retomada repetiu a liberação, o `UPDATE … WHERE estado='ATIVA'` não retornou linha, nada foi devolvido de novo, e a Saga só registrou CANCELADO. Uma tentativa de reusar `t3_s1` com o modo rejeitado foi recusada (`Modo mudou para a mesma intenção`, `193746`). Os três bancos foram consultados separadamente (`193815` a `193837`), sem transação entre eles.

**Resultado desconhecido e 2PC — SIMULAÇÃO** (texto completo em `docs/analises_T3.md` e tabela em `dados/2pc.csv`). Num timeout após uma cobrança possível, persiste-se um estado de **incerteza** (não COMPENSACAO_PENDENTE) e reconcilia-se pela **mesma `op`**. Uma chave nova pode gerar cobrança dupla, e rejeição conhecida não equivale a ausência de resposta. No traço de 2PC, P2 votou SIM e está preparado. Ele não pode abortar por timeout, porque a decisão durável é COMMIT e P1 já confirmou. P2 precisa recuperar o resultado do *gid* (log de C ou P1) e fica bloqueado, retendo recursos, até isso acontecer. Na comparação, o 2PC dá decisão atômica com bloqueio e retenção de locks. A Saga não bloqueia, mas expõe estados intermediários (vistos no S4 e no S5) e exige compensação idempotente. Nenhum dos dois define isolamento.

## 3. Backup físico e PITR (E6 e E7) — MEDIÇÃO

Perfil exclusivo `pitr` com volumes separados: `origin_data`, `archive_data` (WAL), `backup_data` e `destination_data`. O destino monta o arquivo de WAL somente leitura e recebe `restore_command = 'cp /archive/%f %p'`, `recovery_target_name` e `recovery.signal`, sem `primary_conninfo`, ou seja, sem streaming da origem. A **tentativa 1 falhou** (seção 5) e foi preservada. Os resultados abaixo são da **tentativa 2**, execução `lab_1793486783654013149`.

**Base e cadeia de WAL** (`E6_pitr/tentativa2/`): `wal_level = replica`, `archive_mode = on`, `archive_command = bash /lab/archive.sh %p %f`; `pg_stat_archiver` com 4 arquivados e **0 falhas**. `pg_basebackup -Xs` em 3,33 s, `START WAL LOCATION 0/3000028` (segmento …03), `START TIME 22:46:20`, fim às 22:46:23,65, e `pg_verifybackup`: *backup successfully verified*. Incidente (`194709`): id 2 confirmado (22:47:09,904); `pg_create_restore_point` retornou o LSN **0/4055350**; id 3 confirmado (22:47:10,404); `DELETE` de 3 linhas com contagem **0** (22:47:10,580); `pg_switch_wal` em 0/40554F8; e o segmento `000000010000000000000004` foi **confirmado no arquivo** (`test -f` com exit 0), em vez de presumido a partir do `pg_switch_wal`.

**Alvo alcançado** (log do destino em `194751`): `restored log file …03` → `starting point-in-time recovery to "lab_1793486783654013149"` → `redo starts at 0/3000028` → `restored log file …04` → `consistent recovery state reached` → **`recovery stopping at restore point "lab_1793486783654013149", time 22:47:10.046`** → `selected new timeline ID: 2` → `archive recovery complete` → `ready to accept connections`. Com `recovery_target_action = promote`, a recuperação foi finalizada pelo próprio PostgreSQL, sem promoção manual. O standby do T2 não foi tocado.

| Verificação | Resultado | Significado |
|---|---|---|
| Destino (`194821`) | `1 BASE` e `2 ANTES_DO_MARCADOR`; **sem id 3** | O id 2 prova replay posterior à base, e a ausência do id 3 prova que a recuperação não passou do marcador |
| Destino `pg_is_in_recovery()` (`194829`) | `f` | Recuperação finalizada |
| Origem (`194835`) | `count = 0` | A exclusão continua demonstrada na origem; o destino não a contém |

**Métricas (E7).** Mesmo relógio monotônico do host para durações. Instantes UTC observados pelo cliente **depois do retorno** de cada comando, com resolução limitada pela latência do `docker compose exec` (dezenas a centenas de ms). As etapas foram montadas a partir do `pitr-controle.json`, do nome dos logs, do horário de gravação do `pitr.json` e do log do PostgreSQL do destino (mesmo host).

| Etapa do RTO | Intervalo (UTC) | Duração |
|---|---|---|
| Operação: troca e confirmação do WAL e edição do `pitr.json` | 22:47:10,580 → 22:47:42,651 | 32,1 s |
| Operação: disparo do `pitr restaurar` | → 22:47:51,321 | 8,7 s |
| Preparação do destino (cópia da base, contêiner) | → PostgreSQL iniciado 22:47:52,612 | 1,3 s |
| Inicialização até o início da recuperação | → 22:47:55,275 | 2,7 s |
| Restauração do WAL, replay até o alvo e promoção | → pronto 22:47:55,434 | 0,16 s |
| Validação (ids, origem, alvo no log) | → 22:47:56,905 | 1,5 s |
| **RTO observado** | incidente → validação | **46,3 s** (meta 600 s: atendida) |

**Janela observada de perda:** incidente menos a confirmação legítima mais recente presente no destino (id 2) = **0,68 s** (meta 60 s: atendida). Operações legítimas confirmadas antes do incidente e ausentes do destino: **1, o id 3** (confirmado 0,18 s antes do incidente), excluído deliberadamente pelo alvo. Isso é perda **no estado recuperado**, não destruição: o id 3 continua documentado em `E7_metricas/registro_controle.csv`, em `pitr-controle.json` e no WAL arquivado. **Etapa dominante:** a operação manual, com 40,8 s dos 46,3 s (88%). Melhoria verificável: selecionar o marcador automaticamente (modo `AUTO` ou passar o nome ao `restaurar`) e encadear os comandos, medindo a redução do RTO num novo ensaio com outra execução. Atingir a meta numa execução local não garante o desempenho em produção.

**Falta de WAL** (`194857`, executado depois do `medir`, sem afetar o RTO): com um arquivo de WAL vazio, o destino de teste parou em 0/3000120 com **`FATAL: recovery ended before configured recovery target was reached`** e foi desligado. O PostgreSQL não abre com um estado parcial silencioso.

**Questões.**
- **Réplica não substitui backup:** a réplica aplica o `DELETE` em segundos (T2 E2) e não guarda o histórico de pontos anteriores. Só a base com a cadeia de WAL permite voltar a 22:47:10,046.
- **Dump lógico isolado não faz PITR:** ele representa um único instante e não pode ser avançado com WAL até um marcador. Aqui, um dump do momento da base só teria o id 1. O id 2 só existe no destino porque o WAL foi reaplicado depois da base.
- **Falta de um segmento:** a recuperação para antes do alvo (evidência acima). Ou se recupera o segmento, ou se aceita um alvo anterior ao último segmento contínuo, com mais perda.
- **Recuperar todo o banco até o marcador** volta o cluster inteiro: tudo o que foi confirmado depois do marcador some do estado recuperado (aqui o id 3; em produção, os pedidos de todos os clientes nesse intervalo).
- **Reconciliar o id 3 com segurança:** confirmar no registro externo que ele é legítimo e anterior ao incidente; extraí-lo de uma segunda restauração isolada com alvo em LSN imediatamente anterior ao `DELETE`, ou do registro externo; reinseri-lo no destino com a **mesma identidade** e de forma idempotente (`INSERT … ON CONFLICT (id) DO NOTHING`), com aprovação registrada. Nunca avançar o PITR até depois do DELETE, porque isso reintroduziria o incidente.

## 4. Plano de disaster recovery (E8) — PROPOSTA

Classificação: **PROPOSTA** documental, independente de provedor e sem contratação de nuvem. Incidente previsto: perda do ambiente primário (região ou datacenter) **ou** corrupção lógica (exclusão ou atualização indevida, como no E6). Contêineres na mesma máquina, como os do laboratório, não representam regiões independentes.

### Escopo e objetivos

| Componente | Autoritativo ou reconstruível | RPO | RTO | Justificativa de negócio |
|---|---|---|---|---|
| Pedidos (inclui estado da Saga) | Autoritativo | 60 s | 10 min | Registra a obrigação com o cliente; sem ele não há venda nem atendimento |
| Estoque (reservas) | Autoritativo | 60 s | 10 min | Evita vender o que não existe. Uma perda pequena é reconciliável pelas reservas e pedidos |
| Pagamentos (intenções e resultados) | Autoritativo local; verdade final no provedor | 60 s locais (lacuna coberta pelo extrato do provedor) | 10 min | Dinheiro do cliente; uma cobrança sem pedido gera estorno e risco legal |
| Catálogo | Autoritativo, baixa taxa de mudança | 15 min | 30 min | Sem catálogo não se vende, mas as alterações são raras e podem ser refeitas pelo time de produto |
| Busca e cache | **Reconstruível** a partir do catálogo | Não se aplica | 2 h (modo degradado antes disso) | É uma projeção. Enquanto é reconstruída, a navegação usa consulta direta ao catálogo |

Os valores de 60 s e 10 min repetem as metas didáticas do T3. No ensaio local (E7) observamos RTO de 46,3 s e janela de perda de 0,68 s, mas uma execução local não garante esses números em produção.

### Incidente e estratégia

- **Pedidos, estoque e pagamentos: warm standby.** Uma réplica assíncrona em outra região, com arquivamento contínuo de WAL e backups físicos diários em armazenamento de objetos em **outra conta e região**. O custo é a instância da réplica ligada permanentemente mais o armazenamento. Limites reconhecidos: (a) sendo assíncrona, o RPO não é zero (T2 E2); (b) **a réplica não protege contra corrupção lógica**, porque replica o DELETE. Para esse caso vale o PITR a partir do backup e do WAL até um ponto anterior (T3 E6), com perda das transações legítimas posteriores ao alvo.
- **Catálogo: backup e restore** (custo baixo e RTO maior, aceitável).
- **Busca e cache: reconstrução** por reindexação a partir do catálogo restaurado.
- Rejeitamos o **active-active** por causa do custo, dos conflitos de escrita no estoque e da complexidade de consistência. O **pilot light** não atenderia o RTO de 10 min para o núcleo transacional.

**Cloud native.** Provisionamento por IaC (por exemplo OpenTofu) versionada em Git. PostgreSQL em Kubernetes com um operador que gerencia réplica, WAL e backups (por exemplo CloudNativePG). Configuração por GitOps. Volumes persistentes por *storage class* com snapshots. Observabilidade da recuperação: atraso de replicação, `pg_stat_archiver.failed_count`, idade do último backup válido e tempo de cada etapa do runbook em painel e alertas.

### Proteção de backups, WAL, configurações e chaves

- Backups e WAL em armazenamento **imutável** (WORM ou *object lock*) com retenção mínima de 14 dias, em conta separada, inacessível com as credenciais do ambiente primário. Isso protege contra exclusão acidental e ransomware.
- Verificação diária: `pg_verifybackup` mais a checagem da **cadeia contínua de WAL**. Sem um segmento, a recuperação para antes do alvo, como observado no teste do E6 (`recovery ended before configured recovery target was reached`).
- Chaves de criptografia em KMS **replicado** para a região de DR. Segredos em cofre replicado. Acesso de emergência (*break-glass*) com dupla aprovação.
- IaC, configurações e runbooks em repositório espelhado fora do ambiente primário.

### Dependências e sequência

1. Declarar o incidente e congelar as escritas (modo manutenção). Registrar o instante de início do RTO.
2. Infraestrutura base na região de DR: rede, identidade, KMS, cofre de segredos (IaC).
3. Bancos autoritativos **em paralelo**: promover o warm standby (perda de região) ou fazer PITR até o alvo escolhido (corrupção lógica). Validar o alvo pelo log de recuperação, não só pelo processo iniciado.
4. Catálogo (restore).
5. Serviços de aplicação em **somente leitura**.
6. Reconciliação entre serviços (abaixo).
7. Reindexação da busca e aquecimento de cache.
8. Validação e reabertura gradual das escritas.

Os backups dos três bancos **não formam um snapshot global**, mesmo que tirados no mesmo horário. Cada banco volta a um ponto próprio, e a coerência entre eles é restabelecida pela reconciliação, nunca presumida.

### Coerência entre serviços

A chave de junção é a `operacao_id` (`op`) da Saga, presente nos três bancos. Um job consulta cada banco separadamente (sem transação entre bancos) e lista as divergências:
- **Pedido confirmado sem reserva correspondente:** retomar a Saga pelo **mesmo** `op` (a reserva é idempotente por `op`). Se não houver estoque, marcar o pedido para tratamento manual: contato com o cliente, cancelamento e estorno pelo mesmo `op`. Nunca criar outra intenção.
- **Pagamento confirmado sem pedido concluído:** consultar o provedor pelo `op`, que é a fonte da verdade da cobrança. Se a Saga existir em estado não terminal, retomá-la (reservar se necessário e confirmar). Se o pedido se perdeu no ponto de restauração, recriá-lo a partir do registro de pagamento ou estornar, de forma idempotente pelo `op`, conforme a decisão do financeiro.
- **Sagas em estado não terminal** (PENDENTE, RESERVADO, COMPENSACAO_PENDENTE, PAGAMENTO_INCERTO): retomar pelo estado persistido (S4 e S5 do T3).

### Validação e liberação

| Ação | Responsável | Autoriza |
|---|---|---|
| Declarar incidente, congelar escritas, decidir o alvo do PITR | Coordenador de incidente (plantão) | Coordenador |
| Restore, PITR e validação do alvo | DBA | DBA, com registro no runbook |
| Infraestrutura (IaC) e serviços | SRE / plataforma | SRE |
| Reconciliação de pagamentos e estornos | Financeiro, com o dono do produto Pagamentos | Financeiro |
| Testes funcionais e reabertura | QA e dono do produto | **Coordenador de incidente** (decisão final de retorno) |

**Validações obrigatórias antes de reabrir:** alvo confirmado no log de recuperação; contagens e somas de controle por banco comparadas com o registro externo; zero divergências abertas sem dono na reconciliação; Saga sem estados não terminais antigos; teste de compra completo (reservar, pagar, confirmar) com valor simbólico.

**Critério de suspensão:** qualquer validação falha, alvo não confirmado, cadeia de WAL incompleta ou divergência de pagamento sem explicação. Nesses casos o sistema permanece em somente leitura e o coordenador não autoriza o retorno.

### Ensaio periódico

- **Mensal:** PITR automatizado de um backup sorteado para um ambiente isolado, como no E6/E7, com validação de ids e medição de RTO por etapa.
- **Trimestral:** exercício completo de troca de região, incluindo reconciliação e reabertura, com observadores.
- **Indicadores:** RTO e RPO observados contra as metas; percentual de backups restaurados com sucesso; duração da etapa dominante (no E7 foi a operação manual, cerca de 41 s de 46 s); divergências encontradas e resolvidas; falhas de arquivamento de WAL.
- **Evidências:** logs com horário, arquivos de métricas, registro externo de operações e relatório pós-ensaio com uma ação de melhoria verificável. Exemplo: automatizar a seleção do marcador e medir a redução do RTO no ensaio seguinte.

## 5. Falhas e problemas de ambiente

**Falha — tentativa 1 do PITR (MEDIÇÃO, erro de infraestrutura).**
- **Hipótese:** o aviso `>>>> Executing external compose provider …` que o Podman imprime em toda chamada de `docker compose` contamina os valores que o `lab.py` lê da saída do `psql`.
- **Evidência:** `E6_pitr/tentativa1_falha_podman/` (`194026`). O id 2, o marcador `lab_1793486343033978164`, o id 3 e o DELETE foram executados, mas o nome do segmento chegou com o aviso grudado, foi recusado (`Nome WAL inválido`) e o `pg_switch_wal` nem a confirmação de arquivamento foram executados. O LSN gravado no controle arquivado também contém o aviso. O `restaurar` recusou continuar (`Arquivamento não confirmado`).
- **Limite:** o RTO da tentativa 1 não é medível. O controle não foi editado à mão.
- **Ação:** suprimir o aviso com `PODMAN_COMPOSE_WARNING_LOGS=false` (sem alterar o kit), preservar as evidências, `reset pitr` (que arquiva o controle) e fazer uma nova execução com outra identidade e outro marcador.

As falhas injetadas no S4 e no S5 (exit 17, `FALHA_INJETADA`) são controles do simulador, não defeitos. Continua valendo o ajuste do T2 para o Podman rootless (`userns_mode: keep-id` no serviço `tools`).

**Limites do ensaio.** Execução única por cenário. A recusa do v1 depois do `gate retirar` está garantida pelo gate, mas não tem log próprio. A Saga do kit não persiste o número de tentativas nem uma referência de lançamento separada (só `cobrancas` 0/1). Os três bancos da Saga estão numa só instância, o que não simula falha entre máquinas. Os tempos são de uma máquina local.

## 6. Referências e contribuição

Fowler, *ParallelChange* · Flyway, *versioned migrations* · Microsoft, padrões *Saga* e *Compensating Transaction* · Gray e Lamport, *Consensus on Transaction Commit* · PostgreSQL 18, *continuous archiving and PITR* e funções administrativas · AWS, *disaster recovery options in the cloud*. Registro individual de contribuição: `modelos/contribuicoes_T3.md`.
