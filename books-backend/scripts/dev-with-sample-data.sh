#!/usr/bin/env bash
# Reset the dev DB, seed the sample Reading List, and start the backend.
# Destroys books.db, uploads/, and media/ in books-backend/ — dev use only.
set -euo pipefail

cd "$(dirname "$0")/.."

USERNAME="${DEV_USERNAME:-dev}"
PASSWORD="${DEV_PASSWORD:-devpassword}"
FIXTURE="${DEV_FIXTURE:-fixtures/reading_list_sample.zip}"

if [[ ! -f "$FIXTURE" ]]; then
    echo "Fixture not found at $FIXTURE." >&2
    echo "If this is a fresh clone, run: git lfs pull" >&2
    exit 1
fi

if head -c 512 "$FIXTURE" | grep -q "git-lfs"; then
    echo "Fixture is an LFS pointer, not the real file. Run: git lfs pull" >&2
    exit 1
fi

echo "==> Resetting dev state"
rm -f books.db
rm -rf uploads media
mkdir -p uploads media

echo "==> Running migrations"
uv run alembic upgrade head

echo "==> Creating user '$USERNAME'"
uv run python manage.py create-superuser --username "$USERNAME" --password "$PASSWORD"

echo "==> Seeding Reading List from $FIXTURE"
uv run python manage.py seed-reading-list --username "$USERNAME" --zip "$FIXTURE"

echo "==> Starting backend (Ctrl-C to stop)"
exec uv run fastapi dev main.py
