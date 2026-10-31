#!/bin/bash
set -euo pipefail
src="$1"; dest="/archive/$2"
if [ -f "$dest" ]; then cmp -s "$src" "$dest"; exit $?; fi
cp "$src" "$dest.tmp"
sync "$dest.tmp"
mv "$dest.tmp" "$dest"
sync /archive
