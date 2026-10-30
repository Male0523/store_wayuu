#!/usr/bin/env bash
set -euo pipefail

container='store-wayuu-postgres-dev'
if [[ $# -eq 0 ]]; then
  printf 'Uso: bash backend/with-local-postgres.sh <comando> [argumentos...]\n' >&2
  exit 2
fi
if [[ -n "${DATABASE_URL:-}" ]]; then
  printf 'Refusing to run development commands while DATABASE_URL is set; unset the production URL first.\n' >&2
  exit 2
fi
if ! docker inspect "$container" >/dev/null 2>&1; then
  printf 'El contenedor local %s no existe.\n' "$container" >&2
  exit 2
fi
health="$(docker inspect --format '{{.State.Health.Status}}' "$container")"
if [[ "$health" != 'healthy' ]]; then
  printf 'PostgreSQL local no está healthy (estado: %s). Inicia el contenedor y vuelve a intentar.\n' "$health" >&2
  exit 2
fi
password="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container" | sed -n 's/^POSTGRES_PASSWORD=//p')"
if [[ -z "$password" ]]; then
  printf 'No se pudo recuperar el secreto del contenedor PostgreSQL local.\n' >&2
  exit 2
fi
export DJANGO_ENV=development
export DB_ENGINE=postgresql
export DEV_DATABASE_URL="postgresql://wayuu_dev:${password}@127.0.0.1:5432/wayuu_dev"
if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  export DJANGO_SECRET_KEY="$(printf 'store-wayuu-development-secret-v1:%s' "$password" | sha256sum | awk '{print $1}')"
fi
unset password
cd "$(dirname "$0")"
exec "$@"
