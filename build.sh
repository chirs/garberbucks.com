#!/bin/bash
# Rebuild the local postgres database from the mongo database.
# Run from this directory after a `../build/build.sh` build.
# Writes everything to logs/build.log as well as the terminal.
set -e
cd "$(dirname "$0")"

mkdir -p logs
LOG=logs/build.log
exec > >(tee "$LOG") 2>&1

echo "build started $(date)"

dropdb --if-exists garberbucks_build
createdb garberbucks_build --owner=soccerstats

.venv/bin/python manage.py migrate --noinput --settings=build_settings
.venv/bin/python -m build
.venv/bin/python manage.py smoketest --settings=build_settings

dropdb --if-exists garberbucks_backup
psql -d postgres -c 'ALTER DATABASE garberbucks_dev RENAME TO garberbucks_backup' || true
psql -d postgres -c 'ALTER DATABASE garberbucks_build RENAME TO garberbucks_dev'

echo "garberbucks_dev rebuilt (previous version saved as garberbucks_backup)."
