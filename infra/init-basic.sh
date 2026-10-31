#!/bin/bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U postgres -d horizonte -f /lab/sql/01_schema.sql
psql -v ON_ERROR_STOP=1 -U postgres -d horizonte -f /lab/sql/02_seed.sql
