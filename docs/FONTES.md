# Fontes técnicas

O kit foi elaborado a partir dos três enunciados da disciplina e destas fontes primárias. Os dados e cenários são didáticos. A bibliografia do curso permanece no Plano; não se afirma ter consultado páginas de livros que não estavam disponíveis.

- PostgreSQL 18 — consultas e restrições: https://www.postgresql.org/docs/18/queries.html e https://www.postgresql.org/docs/18/ddl-constraints.html
- Replicação e confirmação: https://www.postgresql.org/docs/18/warm-standby.html e https://www.postgresql.org/docs/18/runtime-config-wal.html
- Funções administrativas, pausa e restore point: https://www.postgresql.org/docs/18/functions-admin.html
- Backup físico e PITR: https://www.postgresql.org/docs/18/continuous-archiving.html
- Verificação de backup: https://www.postgresql.org/docs/18/app-pgverifybackup.html
- Imagem oficial PostgreSQL, layout de PGDATA: https://hub.docker.com/_/postgres
- Especificação Compose: https://compose-spec.github.io/compose-spec/spec.html
- Flyway CLI: https://documentation.red-gate.com/fd/command-line-277579359.html
- Migrações versionadas: https://documentation.red-gate.com/flyway/flyway-concepts/migrations/versioned-migrations
- Psycopg, parâmetros: https://www.psycopg.org/psycopg3/docs/basic/params.html
- JDBC PreparedStatement: https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/PreparedStatement.html
- Saga: https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
- Compensação: https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction
- Expand and Contract: https://martinfowler.com/bliki/ParallelChange.html
- Dynamo: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
- CAP, Gilbert e Lynch: https://www.cs.princeton.edu/courses/archive/spr22/cos418/papers/cap.pdf
- Gray e Lamport, commit: https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/

As tags do Compose e do Dockerfile são fixadas para este kit; não significam recomendação de versão para produção. A documentação consultada explica a semântica, mas não substitui o teste de integração deste código.
