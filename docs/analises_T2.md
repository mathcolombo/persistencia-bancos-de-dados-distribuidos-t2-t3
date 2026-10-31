# Análises T2 — E4 e E5

Todas as respostas deste arquivo são **ANÁLISE**. Os números W e R se referem ao conjunto fixo e simulado A, B, C (N = 3, sem réplicas substitutas) descrito em `dados/quorum.json`. Eles não descrevem a configuração do PostgreSQL usada em E2/E3, que é primário/standby com replicação de WAL, e não quorum.

---

# T2 E4 Quorum e cenário de partição

## Casos obrigatórios

### Conjuntos mínimos e interseção

| W, R | Conjuntos mínimos de escrita | Conjuntos mínimos de leitura | R + W > N? | Toda leitura intersecta toda escrita? |
|---|---|---|---|---|
| 1, 1 | {A}, {B}, {C} | {A}, {B}, {C} | 2 > 3 — não | **Não** |
| 2, 2 | {A,B}, {A,C}, {B,C} | {A,B}, {A,C}, {B,C} | 4 > 3 — sim | **Sim** |
| 3, 1 | {A,B,C} | {A}, {B}, {C} | 4 > 3 — sim | **Sim** |

- **W=1, R=1 — contraexemplo:** a escrita é confirmada só por {A} e a leitura consulta só {B}. Os grupos são disjuntos ({A} ∩ {B} = ∅), então a leitura pode devolver o valor anterior sem que nenhum participante dela conheça a escrita.
- **W=2, R=2 — exemplo de interseção:** escrita em {A,B}, leitura em {B,C} e interseção {B}. Qualquer par de subconjuntos de 2 elementos de um conjunto de 3 compartilha ao menos um elemento.
- **W=3, R=1 — exemplo de interseção:** escrita em {A,B,C}, leitura em {C} e interseção {C}. Como a escrita alcança todos, qualquer leitura de um único nó encontra uma réplica que participou dela.

### Uma réplica inacessível

Com uma réplica inacessível (por exemplo C), restam 2 participantes:

| W, R | Escrita possível? | Leitura possível? |
|---|---|---|
| 1, 1 | Sim (2 ≥ 1) | Sim (2 ≥ 1) |
| 2, 2 | Sim (2 ≥ 2), sem folga | Sim (2 ≥ 2), sem folga |
| 3, 1 | **Não** (2 < 3) | Sim (2 ≥ 1) |

Essa conta considera só a quantidade de participantes. Ela não inclui eleição de líder, detecção de falhas, tempo limite ou outras condições de protocolo. A configuração 3,1 deixa a leitura barata e a escrita frágil: basta uma réplica indisponível para bloquear todas as escritas. A configuração 2,2 tolera uma falha nas duas operações, mas não tolera duas.

### Por que R + W > N é só uma propriedade de interseção

Pelo princípio da casa dos pombos, |Escrita ∩ Leitura| ≥ W + R − N. Se R + W > N, esse limite é ≥ 1, ou seja, **algum** participante da leitura recebeu a última escrita confirmada. Isso é necessário para a leitura poder encontrar o valor mais recente, mas não basta para a linearizabilidade:

1. **Identificar o mais recente.** A leitura recebe R respostas com valores diferentes. Sem versão, timestamp lógico ou número de sequência ordenando as escritas, a interseção não diz qual resposta é a mais nova.
2. **Escritas concorrentes.** Duas escritas simultâneas podem ser confirmadas por quóruns diferentes e em ordens diferentes em cada réplica. A interseção não define uma ordem total única.
3. **Escrita parcial.** Uma escrita que alcançou só 1 réplica e falhou para o cliente pode ser vista por uma leitura e não por outra posterior. Isso cria a inversão "novo depois velho" entre dois leitores.
4. **Leituras sem escrita de volta.** Algoritmos linearizáveis sobre quórum (como o ABD) exigem que o leitor grave de volta o valor escolhido num quórum antes de responder. Só a interseção não faz isso.
5. **Conjunto fixo.** A conta supõe N constante. Reconfiguração, réplicas substitutas e *sloppy quorum* (Dynamo) quebram a garantia de interseção.

Portanto, R + W > N garante que a informação **está alcançável**. A linearizabilidade exige também ordenação e um protocolo de leitura e escrita.

## Partição dois mais um

**Lados que atingem o limiar.** Com a política de 2 participantes por operação, o lado {A, B} tem 2 participantes e atinge o limiar de leitura e de escrita. O lado {C} tem 1 participante e **não atinge** o limiar de nenhuma das duas operações. C não está desligado: ele continua acessível ao cliente e consegue receber pedidos, mas não consegue formar um quórum.

### Histórico obrigatório

Estado inicial x = 0 em A, B e C. A escrita x = 1 é confirmada em {A, B} (W = 2 atingido). **Depois** dessa confirmação, outro cliente inicia uma leitura em C. Como a leitura começa após a escrita terminar, a linearizabilidade exige que ela devolva 1 (ou um valor posterior).

| Comportamento de C | Linearizabilidade | Disponibilidade (CAP) | Comentário |
|---|---|---|---|
| Devolve 0 | **Violada**: leitura posterior a uma escrita concluída devolve o valor anterior | Preservada: um nó não falho respondeu | C respondeu sozinho, ou seja, R = 1 na prática, o que viola a política de 2 participantes |
| Espera comunicação com A ou B | Preservada: não devolve valor errado | **Violada enquanto a partição durar**: não há resposta em tempo finito | Se a partição terminar, C consulta A ou B e devolve 1 |
| Responde erro sem executar a leitura | Preservada: não afirma nenhum valor | **Violada**: erro não é resposta à leitura solicitada | É a escolha típica de sistema CP: recusar quando não forma quórum |

**A tensão do CAP (Gilbert e Lynch).** Durante a partição, um nó não falho que recebe uma leitura tem duas opções. Pode responder com seu estado local, mantendo a disponibilidade e arriscando devolver um valor desatualizado. Ou pode recusar ou esperar, mantendo a consistência linearizável e deixando de ser disponível. Não existe opção que preserve as duas enquanto as mensagens entre os lados não chegam. Sem partição, não há esse dilema.

### Histórico indistinguível para C

**H′:** mesmo estado inicial (x = 0 em A, B, C) e mesma partição {A,B} | {C}. Nenhum cliente escreve x. A não recebe pedido de escrita e nada é confirmado. Um cliente inicia leitura em C.

Do ponto de vista de C, H e H′ são **idênticos**: o valor local é x = 0 e nenhuma mensagem chegou de A ou B desde o início da partição. Em H′, devolver 0 é correto. Em H, é uma violação. Como C não recebe nenhuma informação que diferencie os dois casos, **o silêncio não permite deduzir o valor correto**. O único jeito de não errar em nenhum dos dois é não afirmar um valor, isto é, esperar ou recusar.

### C de CAP versus C de ACID

- **C do CAP** é consistência como **linearizabilidade**: todas as operações sobre o objeto parecem acontecer numa ordem única, compatível com o tempo real, como se houvesse uma única cópia. É uma propriedade entre réplicas.
- **C do ACID** é a preservação de **restrições de integridade**: cada transação leva o banco de um estado válido a outro válido (`PRIMARY KEY`, `CHECK (versao > 0)`, chaves estrangeiras, invariantes da aplicação).

As duas são independentes. No E2, a leitura no standby durante a pausa devolveu um estado que satisfazia todas as restrições de `evento_lab` (C do ACID preservado) e ainda assim estava desatualizado em relação a um commit já confirmado (sem linearizabilidade entre primário e standby).

---

# T2 E5 Garantias de sessão e BASE

## H1 e H2

| Histórico | Operações comparadas | Garantia violada |
|---|---|---|
| **H1**: leitura v8, depois leitura v7, mesma sessão e mesmo objeto | **Leitura com leitura**: a 2ª leitura com a 1ª leitura | **Leituras monotônicas** (*monotonic reads*): depois de observar v8, a sessão não pode observar uma versão anterior |
| **H2**: escrita própria confirmada v9, depois primeira leitura v8 | **Escrita própria com leitura posterior** | **Ler as próprias escritas** (*read your writes*): a leitura deve refletir ao menos v9 |

Os dois históricos não se confundem. Em H1 não há escrita da sessão, só duas observações em que a mais recente regride. Em H2 a regressão é em relação a algo que a própria sessão escreveu, não em relação a algo que ela leu.

## Mecanismo para evitar H1

Usar um **token de progresso por sessão**:

1. Cada resposta de leitura devolve o progresso da réplica que respondeu: a versão do objeto ou, no PostgreSQL, o LSN aplicado (`pg_last_wal_replay_lsn()` no standby).
2. A sessão guarda o maior token já observado.
3. Cada nova leitura leva o token. O roteador só envia a leitura a uma réplica cujo progresso aplicado seja ≥ token. Se nenhuma réplica estiver nesse ponto, ele espera, redireciona para outra réplica ou lê do primário.

Assim, a sessão nunca recebe um estado anterior ao que já viu.

**Quando fixar a sessão numa réplica deixa de bastar.** Fixar a sessão (*sticky session*) funciona apenas enquanto todas as leituras vão para a **mesma** réplica e essa réplica nunca regride. A garantia se perde quando a sessão muda de réplica: a réplica fixada cai ou é retirada, o balanceador redistribui as conexões, o cliente reconecta em outro nó, há failover, ou a mesma sessão lógica usa várias conexões (pool, vários dispositivos). A nova réplica pode estar atrasada em relação à anterior. Também se perde se a própria réplica regredir, por exemplo restaurada de um backup antigo. O token resolve esses casos porque o progresso viaja com a sessão e não com a conexão.

## Como assegurar a leitura da própria escrita (H2)

- **Token de escrita:** ao confirmar a escrita v9, a sessão guarda a versão 9 ou o LSN do commit (por exemplo `pg_current_wal_lsn()` logo após o commit). Uma leitura posterior só é atendida por réplica com LSN aplicado ≥ esse valor. Caso contrário, ela espera ou vai para o primário.
- **Ler do primário** por um período depois de cada escrita da sessão, ou para os objetos que a sessão alterou.
- **Confirmação com aplicação remota:** escrever com `synchronous_commit = remote_apply` faz o commit só retornar depois que o standby síncrono aplicou a mudança (E3). Leituras nesse standby verão a escrita. Não há garantia para standbys fora de `synchronous_standby_names`, e a latência e a disponibilidade de escrita passam a depender do standby.

## BASE

**BASE** (*Basically Available, Soft state, Eventually consistent*) é um **conjunto de propriedades e uma filosofia de projeto**, não um protocolo. Ele descreve sistemas que priorizam responder durante falhas, aceitam que o estado das réplicas mude sem novas escritas (porque a propagação ainda está em curso) e prometem só convergência eventual. Sistemas diferentes chegam a isso com mecanismos diferentes: replicação assíncrona, *gossip*, anti-entropia com árvores de Merkle, *hinted handoff*, *read repair*, vetores de versão, *last-writer-wins*, CRDTs. Dizer que um sistema "é BASE" não informa qual desses mecanismos ele usa nem que garantias de sessão ele dá.

**Condições necessárias à convergência eventual:**

1. **Fim das escritas** sobre o objeto: a definição clássica (Vogels) é "se não houver novas atualizações, eventualmente todas as leituras devolvem o último valor".
2. **Entrega de toda atualização a toda réplica:** a comunicação acaba sendo restabelecida, e mensagens perdidas são reenviadas (retentativas, anti-entropia, log retido, como o WAL mantido até o standby consumir).
3. **Aplicação determinística e resolução de conflitos idêntica:** todas as réplicas aplicam as atualizações na mesma ordem, ou usam operações comutativas e uma regra de conflito igual em todas (vetores de versão mais uma regra determinística, CRDTs).
4. **Réplicas não perdem estado de forma permanente.** Uma réplica que perde atualizações já reconhecidas impede a convergência para o valor confirmado.

**Por que eventual não define prazo máximo.** A convergência eventual é uma propriedade de vivacidade sem limite de tempo: afirma que a convergência acontece, não quando. O tempo depende de quanto dura a partição, do atraso de propagação e dos intervalos de retentativa, e nenhum desses tem limite pela definição. No E2, o standby só convergiu depois do `pg_wal_replay_resume()`. Se a pausa durasse indefinidamente, o sistema continuaria dentro da definição de "eventual" sem nunca convergir no período observado.

**Por que eventual não define sequência monotônica por sessão.** A garantia fala do **estado final** quando as escritas param, não do caminho até lá. Uma sessão que lê réplicas diferentes durante a propagação pode ver 8 e depois 7 (H1) e o sistema continua eventualmente consistente. O histórico H3 de `dados/sessao.json` mostra isso: antes da convergência, as leituras foram [8, 7, 6] (não monotônicas). Depois, sem novas escritas e com propagação, foram [8, 8, 8]. Leituras monotônicas e ler as próprias escritas são **garantias de sessão adicionais** (Terry et al.) que precisam ser implementadas por cima, por exemplo com os tokens descritos acima.
