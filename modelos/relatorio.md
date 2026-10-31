# Relatório T2 — Distribuição e consistência

**Integrantes:** Matheus Colombo da Cruz · **Data:** 31/10/2026

**Ambiente:** PostgreSQL 18.6 (Debian 18.6-1.pgdg12+2), imagem `postgres:18.6-bookworm@sha256:3725f4e2499eef5134592b3b4ab79a543ed7f8e533b05b5b637af926630f6650` no primário e no standby · Podman 6.1.4 rootless com Docker Compose v5.3.1 (o README do kit pressupõe Docker Engine) · Linux amd64 · linguagem **Python** (cliente psycopg 3.2.6 em contêiner Python 3.12.9).

Cada resultado está identificado como **REAL** (executado no PostgreSQL do laboratório), **SIMULADO** (simulador determinístico) ou **ANÁLISE** (raciocínio sobre um cenário). Os logs integrais estão em `evidencias/T2/` e são relacionados um a um em `modelos/evidencias.csv`. A seção 3.3 lista as evidências que **não** foram obtidas.

## 1. Objetivo e decisões

O objetivo é avaliar, para a Loja Horizonte, (O2) como distribuir chaves entre nós e quanto custa adicionar um nó, e (O3) que garantias de leitura uma réplica PostgreSQL oferece em cada modo de confirmação. As decisões foram:

- **Hash determinístico** H = 8 primeiros bytes do SHA-256 em big endian, sem sinal. O hash nativo do Python é aleatorizado por execução, o que impediria a reprodução.
- **Movimentação medida por nó físico.** No anel virtual, a troca de ponto dentro do mesmo nó não é transferência de dados entre máquinas.
- **Um identificador novo por experimento** e consulta pelo mesmo id em caso de resultado incerto, para não esconder uma escrita duplicada.
- **Pausa de replay como controle de aplicação do WAL.** Ela não é tratada como partição de rede nem como perda de máquina.

## 2. Resultados por exercício

### E1 — Distribuição e movimentação (SIMULADO)

Massa: K:0000–K:0999. Nós A B C e depois A B C D. Código completado: `modulo`, `sucessor` e `movidas` em `exercicios/respostas.py`. Duas execuções (`shard-python-1` e `shard-python-2`) produziram CSVs **idênticos** (`diff -r` sem diferenças). Em todas as configurações, cada chave tem exatamente um destino e as contagens somam 1000. Nenhuma colisão de pontos foi observada no anel.

| Configuração | Antes A/B/C | Menor–maior antes | Depois A/B/C/D | Menor–maior depois | Movidas | % |
|---|---|---|---|---|---|---|
| Faixa (0–333, 334–666, 667–999) | 334/333/333 | 333–334 | sem D | 333–334 | 0 | 0,0 |
| Módulo | 366/333/301 | 301–366 | 266/244/225/265 | 225–266 | 746 | 74,6 |
| Anel, 1 ponto por nó | 285/4/711 | 4–711 | 285/4/646/65 | 4–646 | 65 | 6,5 |
| Anel, 16 pontos por nó | 273/410/317 | 273–410 | 264/193/225/318 | 193–318 | 318 | 31,8 |

Na faixa, a movimentação é 0 porque o ensaio compara a configuração consigo mesma (D não é adicionado). Isso não demonstra expansão sem transferência. Nos dois anéis, o número de chaves movidas é igual à contagem de D (65 e 318): todas as chaves transferidas foram para o nó novo, e nenhuma foi trocada entre A, B e C. O teste unitário confirma isso (`test_add_only_moves_to_new_node`). 5 de 6 testes passam. `test_saga_paths` pertence ao T3 e falha por `TODO_ALUNO`, como esperado nesta entrega.

**Respostas discursivas (ANÁLISE).**
- *Consulta por faixa de identificadores:* a **distribuição por faixa** é a única em que ids consecutivos ficam no mesmo nó. Uma consulta K:0100–K:0200 atinge um único nó. Com hash (módulo ou anel), ids vizinhos se espalham e a consulta precisa ir a todos os nós.
- *Por que D exige transferência mesmo no anel:* D passa a ser dono do arco entre seu ponto e o ponto anterior. Essas chaves estavam no sucessor de D e precisam ser copiadas para D. O anel **limita** a movimentação ao arco de D (65 chaves, contra 746 no módulo, em que cerca de 3/4 das chaves mudam porque o divisor muda de 3 para 4), mas não a elimina.
- *Nós virtuais garantem equilíbrio perfeito?* **Não.** Com 16 pontos, a diferença caiu de 4–711 para 273–410 antes de D e ficou em 193–318 depois. Pontos virtuais reduzem a variância do tamanho dos arcos, mas com 1000 chaves e 16 pontos por nó o desequilíbrio continua visível. Os 31,8% movidos no anel virtual, contra 6,5% no anel simples, não indicam pior estratégia: no anel simples, D caiu por acaso num arco pequeno. No virtual, D recebeu uma fatia próxima de 1/4, que é o desejado.
- *Chave com 60% das requisições:* as contagens medem **chaves armazenadas**, não **requisições**. Se uma chave recebe 60% das requisições, o nó que a guarda recebe ao menos 60% do tráfego, mesmo tendo cerca de 250 das 1000 chaves. Mover outras chaves ou adicionar nós não divide uma única chave quente. Isso exige replicar a leitura dessa chave, usar cache ou dividir a chave (por exemplo com sufixos).
- *Distribuição uniforme de chaves não é distribuição uniforme de trabalho* porque o trabalho depende da frequência de acesso, do tamanho dos valores e do custo de cada operação, e nada disso é uniforme. O hash equilibra **quantas** chaves cada nó tem, não **quanto** cada chave é usada.

### Configuração e identidades (REAL)

Houve duas instâncias do perfil `replica`: um volume preexistente, usado nas verificações iniciais, e um volume novo, criado por `reset replica`, usado em todos os experimentos (seção 3.3). As duas usam a mesma imagem e o mesmo `compose.yaml`.

| Verificação | Volume | Primário (`primary`) | Standby (`standby`) |
|---|---|---|---|
| `version()` | anterior | PostgreSQL 18.6 | PostgreSQL 18.6 |
| `pg_is_in_recovery()` explícito | anterior | `f` | `t` |
| `pg_is_in_recovery()` verificado pelo cliente (asserção que interrompe o experimento se falhar) | **novo**, a cada experimento | `f` | `t` |
| `pg_stat_replication` | **novo** | `standby1 \| streaming \| sync` (antes do `on`) e `\| async` (final) | — |
| Propagação inicial (id 1000) | anterior | `INSERT 0 1` | `1000\|1\|sanidade pre-pausa` |
| `pg_get_wal_replay_pause_state()` | anterior (antes) e **novo** (final) | — | `not paused` |
| Recriação | **novo** | volumes `Created`; serviços `Healthy` | idem |

As conexões são identificadas pelo nome de serviço Compose (`primary` e `standby`). O cliente abre uma conexão administrativa em cada servidor e uma **terceira conexão independente** no primário para a escrita, numa thread separada. Isso permite retomar o replay mesmo com a escrita bloqueada.

### E2 — Replicação assíncrona com replay pausado (REAL, id 2001)

Configuração: o cliente define `synchronous_standby_names = ''` no primário, espera o valor ficar efetivo e usa `synchronous_commit = on` na sessão de escrita. Com a lista vazia, `on` não exige nenhuma confirmação remota. Os valores `'' | on` também foram consultados explicitamente no volume anterior.

| Etapa | Observação |
|---|---|
| Pausa | `pg_wal_replay_pause()` e espera até `pg_get_wal_replay_pause_state() = 'paused'` |
| Escrita | `INSERT (2001, 8, 'async')` em conexão própria: **confirmado em 20,6 ms** (relógio monotônico do cliente) |
| Leitura durante a pausa | `SELECT count(*) FROM evento_lab WHERE id=2001` em nova transação no standby: **0** |
| Retomada | `pg_wal_replay_resume()`. A linha apareceu no standby dentro do limite de 30 s |
| Final | `2001\|8\|async` no primário e no standby |

**Interpretação.** O primário confirmou o commit sem que a alteração estivesse aplicada no standby. A ausência temporária no standby **não é perda de dados**: o commit estava durável no primário e a linha apareceu depois da retomada. **Não foi testado:** se o WAL já tinha sido recebido e gravado pelo standby durante a pausa (não coletamos `write_lsn`, `flush_lsn` e `replay_lsn`), partição de rede, perda de máquina e número de tentativas até a linha aparecer (o cliente registra só que ela apareceu dentro de 30 s).

**Respostas.** (a) **Não**: no modo assíncrono, o sucesso depende só de o WAL ser gravado no primário. O standby não precisa receber, persistir nem aplicar. (b) **Não**: a linha não estava visível porque ainda não tinha sido **aplicada**. Ela existia no primário e estava no WAL. (c) **Não**: pausar o replay interrompe apenas a **aplicação**. O walreceiver continua **recebendo** o WAL pela rede e **persistindo** em disco no standby. Uma interrupção de rede pararia o recebimento, que é um fenômeno diferente.

### E3 — Confirmação síncrona (REAL)

Antes das medições síncronas: `synchronous_standby_names = 'FIRST 1 (standby1)'` e `pg_stat_replication` mostrando `standby1 | streaming | sync`. Antes de cada escrita síncrona, o cliente também espera essa condição.

- **`on` com standby síncrono (id 2002):** com o replay pausado e verificado, o commit foi **confirmado em 24,0 ms**, e a leitura no standby retornou **0 linhas** naquele momento. Depois da retomada, a linha apareceu. Conclusão: `on` esperou o **flush** remoto do WAL, que continua acontecendo com o replay pausado, e não a aplicação.
- **`remote_apply` (observado no id 2004):** o cenário dedicado (id 2003, limite de 30 s) **não tem evidência registrada** e não foi repetido (seção 3.3). O comportamento do `remote_apply` foi observado no cenário de timeout, que usa a mesma configuração: `synchronous_commit = remote_apply`, standby síncrono, replay pausado e verificado. A única diferença é `statement_timeout = 1500ms` em vez de `30s`. Resultado: aos 3 s o cliente **continuava esperando** (`cliente_esperando: true`, sem resultado), com **0 linhas** no standby. Depois da retomada, o commit foi **confirmado em 3010 ms** (≈ 3 s de pausa mais a aplicação), e `2004|11|timeout` apareceu no primário e no standby.

**Tabela comparativa.**

| Modo | Requisito remoto para confirmar | Replay | Duração observada | Commit | Visível no standby durante a pausa | Limite da conclusão |
|---|---|---|---|---|---|---|
| Assíncrono (`on`, lista vazia), id 2001 | Nenhum | Pausado | 20,6 ms | Confirmado durante a pausa | Não (0 linhas) | Não mede recebimento nem flush remoto |
| `on` com `FIRST 1 (standby1)`, id 2002 | Flush do WAL no standby | Pausado | 24,0 ms | Confirmado durante a pausa | Não (0 linhas) | Flush inferido pela documentação e pelo comportamento; LSNs não coletados |
| `remote_apply` com `FIRST 1 (standby1)`, id 2004 | Aplicação do WAL no standby | Pausado por 3 s e depois retomado | 3010 ms | Pendente durante a pausa; confirmado só após a retomada | Não durante a pausa; sim após o commit | Observado no cenário de timeout (não no 2003); execução única; garante só para os standbys da lista síncrona |

As durações não são um benchmark. A diferença essencial é o **ponto de confirmação**: o assíncrono confirma localmente, `on` confirma quando o standby persistiu e `remote_apply` confirma quando o standby aplicou. 2002 e 2004 rodaram nas mesmas condições (standby síncrono, replay pausado). Só no `remote_apply` o commit não terminou durante a pausa, e só nele a confirmação implica que uma nova leitura no standby verá a linha.

**Snapshot anterior.** Uma transação de leitura no standby em `REPEATABLE READ` ou `SERIALIZABLE` fixa o snapshot na primeira consulta. Linhas aplicadas depois desse instante continuam invisíveis até a transação terminar, mesmo com `remote_apply` já confirmado. Em `READ COMMITTED`, cada comando tira um snapshot novo. Por isso o roteiro sempre lê em transação nova.

**Restauração.** Ao final: `pg_get_wal_replay_pause_state() = 'not paused'`, `synchronous_standby_names = ''` e `standby1 | streaming | async`. Os parâmetros de teste não são recomendação para produção.

### E4 e E5 — Quorum, CAP e garantias de sessão (ANÁLISE)

As respostas completas estão em `docs/analises_T2.md`. Resumo:
- **Quórum:** (1,1) não garante interseção (contraexemplo {A} e {B}). (2,2) e (3,1) garantem. Com uma réplica inacessível, (3,1) perde a escrita. R + W > N garante interseção, mas não ordem nem linearizabilidade.
- **Partição 2+1:** só {A,B} atinge o limiar. Se C devolve 0, viola a linearizabilidade. Se espera ou devolve erro, viola a disponibilidade. Para C, o histórico é indistinguível de outro em que não houve escrita.
- **Sessão:** H1 (leitura com leitura) viola leituras monotônicas. H2 (escrita própria com leitura) viola ler as próprias escritas. Os mecanismos propostos são tokens de versão ou LSN e leitura no primário ou com `remote_apply`. BASE não é protocolo e "eventual" não define prazo nem monotonicidade.

## 3. Falhas e limites

### 3.1 Falha 1 — Leitura desatualizada e espera de commit não interrompida pelo timeout (REAL, induzida)

- **Hipótese:** com o replay pausado, (i) uma leitura no standby não reflete um commit já confirmado no primário, e (ii) com `remote_apply`, o cliente fica bloqueado até a aplicação remota, num estado em que a aplicação ainda não sabe se a escrita valeu.
- **Evidência:** id 2001 confirmado no primário e 0 linhas no standby durante a pausa. Id 2004 com `cliente_esperando: true` aos 3 s e sem resultado. O `statement_timeout` de 1500 ms **não** interrompeu a espera, e a confirmação chegou em 3010 ms, logo após a retomada. Nossa interpretação (hipótese, não testada isoladamente) é que o PostgreSQL desativa o `statement_timeout` antes de executar a confirmação da transação, onde ocorre a espera pela replicação síncrona. Por isso esse limite não cobre essa espera.
- **Limite:** o caso "resultado desconhecido" com erro ou aviso não foi reproduzido. Seria preciso um limite no cliente (por exemplo, abandonar a espera aos 1,5 s) ou um cancelamento explícito (`pg_cancel_backend`), que segundo a documentação deixa a transação confirmada localmente, com um aviso. Execução única e sem LSNs.
- **Recuperação e mitigação:** `pg_wal_replay_resume()` pelo terminal administrativo independente, seguido de consulta **pelo mesmo id** (2004) no primário antes de qualquer repetição. A escrita estava confirmada, então repetir com outro id criaria um registro duplicado. Para leituras de quem acabou de escrever, rotear ao primário ou esperar o LSN do commit (ver E5). Em `remote_apply`, definir um limite de espera no cliente e um procedimento de reconciliação por id.

### 3.2 Falha 2 — Leitura em C durante a partição 2+1 (ANÁLISE, partição simulada)

- **Hipótese:** um nó isolado que responde sozinho devolve um valor desatualizado após uma escrita confirmada.
- **Evidência:** histórico de `dados/quorum.json`: x = 1 confirmado em {A,B} e leitura iniciada depois em C, cujo estado local é x = 0. C não distingue esse histórico de H′, em que nenhuma escrita ocorreu.
- **Limite:** análise de modelo com conjunto fixo, sem implementação de protocolo, eleição, reconfiguração ou relógios. Não representa o PostgreSQL do E2/E3.
- **Mitigação:** exigir R = 2 também na leitura. C não forma quórum e responde erro (CP), preservando a linearizabilidade à custa da disponibilidade de C. A alternativa AP é aceitar a resposta local com versão e, ao fim da partição, convergir por *read repair* ou anti-entropia, declarando ao cliente que a leitura pode estar desatualizada.

### 3.3 Lacunas de evidência (declaradas)

1. **Cenário `remote_apply` dedicado (id 2003) sem registro.** Não há log nem linha 2003 em `evento_lab`, e o cenário não foi repetido. O comportamento foi observado no id 2004 (seção E3). O que não foi medido: a conclusão com o limite de 30 s do roteiro, e a asserção específica do cliente para `remote_apply`, que exige `cliente_esperando = true`. Essa condição foi observada no 2004, mas sem essa asserção.
2. **Prontidão e propagação inicial verificadas no volume anterior.** As consultas explícitas de `version()`, `pg_is_in_recovery()` e a escrita de sanidade (id 1000) foram feitas antes do `reset replica`. No volume novo, a prontidão é sustentada pelos healthchecks (`Healthy`), pela asserção de `pg_is_in_recovery()` que o cliente executa antes de cada experimento, por `pg_stat_replication` em `streaming` e pela propagação dos ids 2001, 2002 e 2004 após a retomada. A verificação de propagação **antes da primeira pausa** não foi repetida no volume novo.
3. **Uma única execução por modo**, sem coleta de LSNs.

### 3.4 Problemas de ambiente registrados

| Comando | Erro | Causa | Ação |
|---|---|---|---|
| `lab.py doctor` | `can't evaluate field OSType` (exit 125) | Podman no lugar de Docker. O campo `.OSType` não existe no `info` do Podman | Nenhuma: as outras três verificações passaram. Registrado |
| `lab.py client python shard …` | `PermissionError` em `evidencias/execucoes` | Podman rootless com `--user 1000:1000` mapeia para um subuid sem permissão na pasta montada | `userns_mode: keep-id` no serviço `tools` do `compose.yaml` |
| `lab.py client python replica async` | `ID já usado` | Volumes do perfil `replica` de uma execução anterior (o `up` mostrou `Starting`, sem `Creating`) | Logs preservados, `reset replica --confirmar APAGAR-LAB` e `up replica` |

## 4. Referências e contribuições

PostgreSQL 18: *warm standby*, funções administrativas e `synchronous_commit` · DeCandia et al., *Dynamo* (2007) · Gilbert e Lynch, *Brewer's conjecture* (2002) · Vogels, *Eventually Consistent* (2008) · Terry et al., *Session Guarantees for Weakly Consistent Replicated Data* (1994) · MongoDB, *read isolation, consistency and recency*.

Registro individual de contribuição: `modelos/contribuicoes.md`.
