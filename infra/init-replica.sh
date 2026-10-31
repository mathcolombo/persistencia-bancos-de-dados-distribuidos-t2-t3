#!/bin/bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U postgres -d horizonte <<'SQL'
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replica_local';
CREATE TABLE evento_lab(id integer PRIMARY KEY, versao integer NOT NULL CHECK(versao>0), descricao text NOT NULL);
SQL
printf '\nhost replication replicator all scram-sha-256\n' >> "$PGDATA/pg_hba.conf"
