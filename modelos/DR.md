# Plano de recuperação — Loja Horizonte

Classificação: **PROPOSTA** documental, independente de provedor e sem contratação de nuvem. Incidente previsto: perda do ambiente primário (região ou datacenter) **ou** corrupção lógica (exclusão ou atualização indevida, como no E6). Contêineres na mesma máquina, como os do laboratório, não representam regiões independentes.

## Escopo e objetivos

| Componente | Autoritativo ou reconstruível | RPO | RTO | Justificativa de negócio |
|---|---|---|---|---|
| Pedidos (inclui estado da Saga) | Autoritativo | 60 s | 10 min | Registra a obrigação com o cliente; sem ele não há venda nem atendimento |
| Estoque (reservas) | Autoritativo | 60 s | 10 min | Evita vender o que não existe. Uma perda pequena é reconciliável pelas reservas e pedidos |
| Pagamentos (intenções e resultados) | Autoritativo local; verdade final no provedor | 60 s locais (lacuna coberta pelo extrato do provedor) | 10 min | Dinheiro do cliente; uma cobrança sem pedido gera estorno e risco legal |
| Catálogo | Autoritativo, baixa taxa de mudança | 15 min | 30 min | Sem catálogo não se vende, mas as alterações são raras e podem ser refeitas pelo time de produto |
| Busca e cache | **Reconstruível** a partir do catálogo | Não se aplica | 2 h (modo degradado antes disso) | É uma projeção. Enquanto é reconstruída, a navegação usa consulta direta ao catálogo |

Os valores de 60 s e 10 min repetem as metas didáticas do T3. No ensaio local (E7) observamos RTO de 46,3 s e janela de perda de 0,68 s, mas uma execução local não garante esses números em produção.

## Incidente e estratégia

- **Pedidos, estoque e pagamentos: warm standby.** Uma réplica assíncrona em outra região, com arquivamento contínuo de WAL e backups físicos diários em armazenamento de objetos em **outra conta e região**. O custo é a instância da réplica ligada permanentemente mais o armazenamento. Limites reconhecidos: (a) sendo assíncrona, o RPO não é zero (T2 E2); (b) **a réplica não protege contra corrupção lógica**, porque replica o DELETE. Para esse caso vale o PITR a partir do backup e do WAL até um ponto anterior (T3 E6), com perda das transações legítimas posteriores ao alvo.
- **Catálogo: backup e restore** (custo baixo e RTO maior, aceitável).
- **Busca e cache: reconstrução** por reindexação a partir do catálogo restaurado.
- Rejeitamos o **active-active** por causa do custo, dos conflitos de escrita no estoque e da complexidade de consistência. O **pilot light** não atenderia o RTO de 10 min para o núcleo transacional.

**Cloud native.** Provisionamento por IaC (por exemplo OpenTofu) versionada em Git. PostgreSQL em Kubernetes com um operador que gerencia réplica, WAL e backups (por exemplo CloudNativePG). Configuração por GitOps. Volumes persistentes por *storage class* com snapshots. Observabilidade da recuperação: atraso de replicação, `pg_stat_archiver.failed_count`, idade do último backup válido e tempo de cada etapa do runbook em painel e alertas.

## Proteção de backups, WAL, configurações e chaves

- Backups e WAL em armazenamento **imutável** (WORM ou *object lock*) com retenção mínima de 14 dias, em conta separada, inacessível com as credenciais do ambiente primário. Isso protege contra exclusão acidental e ransomware.
- Verificação diária: `pg_verifybackup` mais a checagem da **cadeia contínua de WAL**. Sem um segmento, a recuperação para antes do alvo, como observado no teste do E6 (`recovery ended before configured recovery target was reached`).
- Chaves de criptografia em KMS **replicado** para a região de DR. Segredos em cofre replicado. Acesso de emergência (*break-glass*) com dupla aprovação.
- IaC, configurações e runbooks em repositório espelhado fora do ambiente primário.

## Dependências e sequência

1. Declarar o incidente e congelar as escritas (modo manutenção). Registrar o instante de início do RTO.
2. Infraestrutura base na região de DR: rede, identidade, KMS, cofre de segredos (IaC).
3. Bancos autoritativos **em paralelo**: promover o warm standby (perda de região) ou fazer PITR até o alvo escolhido (corrupção lógica). Validar o alvo pelo log de recuperação, não só pelo processo iniciado.
4. Catálogo (restore).
5. Serviços de aplicação em **somente leitura**.
6. Reconciliação entre serviços (abaixo).
7. Reindexação da busca e aquecimento de cache.
8. Validação e reabertura gradual das escritas.

Os backups dos três bancos **não formam um snapshot global**, mesmo que tirados no mesmo horário. Cada banco volta a um ponto próprio, e a coerência entre eles é restabelecida pela reconciliação, nunca presumida.

## Coerência entre serviços

A chave de junção é a `operacao_id` (`op`) da Saga, presente nos três bancos. Um job consulta cada banco separadamente (sem transação entre bancos) e lista as divergências:
- **Pedido confirmado sem reserva correspondente:** retomar a Saga pelo **mesmo** `op` (a reserva é idempotente por `op`). Se não houver estoque, marcar o pedido para tratamento manual: contato com o cliente, cancelamento e estorno pelo mesmo `op`. Nunca criar outra intenção.
- **Pagamento confirmado sem pedido concluído:** consultar o provedor pelo `op`, que é a fonte da verdade da cobrança. Se a Saga existir em estado não terminal, retomá-la (reservar se necessário e confirmar). Se o pedido se perdeu no ponto de restauração, recriá-lo a partir do registro de pagamento ou estornar, de forma idempotente pelo `op`, conforme a decisão do financeiro.
- **Sagas em estado não terminal** (PENDENTE, RESERVADO, COMPENSACAO_PENDENTE, PAGAMENTO_INCERTO): retomar pelo estado persistido (S4 e S5 do T3).

## Validação e liberação

| Ação | Responsável | Autoriza |
|---|---|---|
| Declarar incidente, congelar escritas, decidir o alvo do PITR | Coordenador de incidente (plantão) | Coordenador |
| Restore, PITR e validação do alvo | DBA | DBA, com registro no runbook |
| Infraestrutura (IaC) e serviços | SRE / plataforma | SRE |
| Reconciliação de pagamentos e estornos | Financeiro, com o dono do produto Pagamentos | Financeiro |
| Testes funcionais e reabertura | QA e dono do produto | **Coordenador de incidente** (decisão final de retorno) |

**Validações obrigatórias antes de reabrir:** alvo confirmado no log de recuperação; contagens e somas de controle por banco comparadas com o registro externo; zero divergências abertas sem dono na reconciliação; Saga sem estados não terminais antigos; teste de compra completo (reservar, pagar, confirmar) com valor simbólico.

**Critério de suspensão:** qualquer validação falha, alvo não confirmado, cadeia de WAL incompleta ou divergência de pagamento sem explicação. Nesses casos o sistema permanece em somente leitura e o coordenador não autoriza o retorno.

## Ensaio periódico

- **Mensal:** PITR automatizado de um backup sorteado para um ambiente isolado, como no E6/E7, com validação de ids e medição de RTO por etapa.
- **Trimestral:** exercício completo de troca de região, incluindo reconciliação e reabertura, com observadores.
- **Indicadores:** RTO e RPO observados contra as metas; percentual de backups restaurados com sucesso; duração da etapa dominante (no E7 foi a operação manual, cerca de 41 s de 46 s); divergências encontradas e resolvidas; falhas de arquivamento de WAL.
- **Evidências:** logs com horário, arquivos de métricas, registro externo de operações e relatório pós-ensaio com uma ação de melhoria verificável. Exemplo: automatizar a seleção do marcador e medir a redução do RTO no ensaio seguinte.
