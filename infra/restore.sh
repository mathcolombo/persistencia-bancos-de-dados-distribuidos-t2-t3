#!/bin/bash
set -euo pipefail
# Executado somente com destination parado; lab.py verifica isso antes.
[ "$PGDATA" = /var/lib/postgresql/18/docker ]
[ -f /backup/base/PG_VERSION ]
[ -f /backup/target.txt ]
target=$(cat /backup/target.txt)
[[ "$target" =~ ^lab_[a-zA-Z0-9_]+$ ]]
mkdir -p "$PGDATA"
if [ -e "$PGDATA/PG_VERSION" ]; then
  echo 'Destino já contém uma recuperação. Use reset pitr após exportar evidências.' >&2
  exit 2
fi
cp -a /backup/base/. "$PGDATA/"
rm -f "$PGDATA/standby.signal" "$PGDATA/postmaster.pid"
# Backup não recebe -R. Sem primary_conninfo ou streaming no destino.
cat >> "$PGDATA/postgresql.auto.conf" <<EOF
restore_command = 'cp /archive/%f %p'
recovery_target_name = '$target'
recovery_target_action = 'promote'
archive_mode = 'off'
EOF
touch "$PGDATA/recovery.signal"
chown -R postgres:postgres /var/lib/postgresql
chmod 700 "$PGDATA"
