#!/bin/bash
set -euo pipefail
mkdir -p /archive /backup
chown postgres:postgres /archive /backup
chmod 700 /archive /backup
exec /usr/local/bin/docker-entrypoint.sh "$@"
