#!/usr/bin/env sh
# Wait for the database, apply migrations, then hand off to the CMD.
#
# Migrations run here rather than in the image build because they need the real
# database, which does not exist at build time. On a multi-replica deploy this
# should move to a dedicated release step so N replicas do not race -- Django's
# migration table makes that safe but noisy.
set -eu

echo "==> Waiting for the database..."
python - <<'PY'
import os, sys, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()
from django.db import connections
from django.db.utils import OperationalError

for attempt in range(1, 31):
    try:
        connections["default"].ensure_connection()
        print("    database is up")
        sys.exit(0)
    except OperationalError as exc:
        print(f"    attempt {attempt}/30 not ready: {exc}")
        time.sleep(2)
print("    database never became available", file=sys.stderr)
sys.exit(1)
PY

echo "==> Applying migrations..."
python manage.py migrate --noinput

echo "==> Starting: $*"
exec "$@"
