#!/bin/bash
set -euo pipefail
mkdir -p "$PGDATA"
chown -R postgres:postgres /var/lib/postgresql
chmod 700 "$PGDATA"
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  export PGPASSWORD=replica_local
  gosu postgres pg_basebackup -d 'host=primary user=replicator application_name=standby1 connect_timeout=10' -D "$PGDATA" -Fp -Xs -P -R
  printf "\nprimary_conninfo = 'host=primary user=replicator password=replica_local application_name=standby1 connect_timeout=10'\n" >> "$PGDATA/postgresql.auto.conf"
fi
exec gosu postgres postgres -D "$PGDATA" -c hot_standby=on
