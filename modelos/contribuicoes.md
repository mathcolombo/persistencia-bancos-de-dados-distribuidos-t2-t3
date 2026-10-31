# Contribuições

Grupo, integrantes e commit: trabalho individual — Matheus Colombo da Cruz. Entrega na tag `T2` do repositório do T1 (T1 preservado em [hash do commit T1]).

Execução e análise: todos os comandos foram executados por Matheus Colombo da Cruz na própria máquina (Linux, Podman 6.1.4 rootless com Docker Compose v5.3.1), e a análise dos resultados também foi feita por ele.

## Matheus Colombo da Cruz

- **Atividade concreta realizada:**
  - implementação de `modulo`, `sucessor` e `movidas` para o simulador de distribuição;
  - preparação do ambiente, incluindo a correção de permissão do Podman rootless com `userns_mode: keep-id`;
  - execução dos cenários de replicação async, `on` e timeout com `remote_apply`;
  - redação das análises de quorum, CAP e garantias de sessão, e do relatório.
- **Arquivo, teste ou resultado em que trabalhou:**
  - `exercicios/respostas.py`, `compose.yaml`, `docs/analises_T2.md`, `modelos/relatorio.md` e `modelos/evidencias.csv`;
  - teste `python lab.py test unit` (5/6 aprovados, e o que falha é do T3);
  - CSVs `shard-python-1` e `shard-python-2`;
  - logs dos ids 2001, 2002 e 2004 em `evidencias/T2/`.
- **Explicação de uma evidência (on versus remote_apply):** No id 2002, com `synchronous_commit = on` e `standby1` configurado como síncrono, o commit foi confirmado em 24 ms enquanto o replay do standby estava pausado, e uma nova transação de leitura no standby não encontrou a linha. Isso mostra que `on` espera apenas o flush do WAL no standby, porque o walreceiver continua recebendo e gravando o WAL mesmo com a aplicação suspensa. No id 2004, com `remote_apply` nas mesmas condições, o cliente ainda esperava após três segundos e só recebeu a confirmação depois de `pg_wal_replay_resume()`, em 3010 ms. A diferença está no ponto de confirmação, e não na latência.
- **Limitação identificada:** não coletei `write_lsn`, `flush_lsn` e `replay_lsn` de `pg_stat_replication` durante a pausa. Por isso, a afirmação de que o standby recebeu e persistiu o WAL antes da aplicação se apoia na documentação e no comportamento do commit, e não numa medição direta.
