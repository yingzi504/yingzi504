#!/usr/bin/env sh
set -eu

mkdir -p /app/data /app/uploads /app/output /app/templates

if [ -d /app/default-data ]; then
  for file in /app/default-data/*; do
    [ -e "$file" ] || continue
    target="/app/data/$(basename "$file")"
    if [ ! -e "$target" ]; then
      cp -a "$file" "$target"
    fi
  done
fi

if [ -d /app/default-templates ]; then
  for file in /app/default-templates/*; do
    [ -e "$file" ] || continue
    target="/app/templates/$(basename "$file")"
    if [ ! -e "$target" ]; then
      cp -a "$file" "$target"
    fi
  done
fi

exec "$@"
