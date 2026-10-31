#!/bin/bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U postgres -d horizonte -f /lab/sql/migration_base.sql
