#!/bin/bash
set -euo pipefail
for db in pedidos estoque pagamentos; do
  createdb -U postgres "$db"
  psql -v ON_ERROR_STOP=1 -U postgres -d "$db" -f "/lab/sql/saga_$db.sql"
done
