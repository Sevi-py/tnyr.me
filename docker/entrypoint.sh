#!/usr/bin/env sh
set -eu

DIST_DIR="/app/backend/dist"

if [ -z "${TNYR_SALT1_HEX:-}" ] || [ -z "${TNYR_SALT2_HEX:-}" ]; then
  echo "Legacy salts not set (TNYR_SALT1_HEX/TNYR_SALT2_HEX). That's OK: default mode needs no secrets."
  echo "If you need legacy server-side links (/shorten-server and old /<id>), generate salts with: python3 backend/generate_salts.py --env"
fi

PUBLIC_URL="${TNYR_PUBLIC_URL:-}"
PORT="${TNYR_PORT:-5502}"
DB_PATH="${TNYR_DB_PATH:-}"

if [ -z "$PUBLIC_URL" ]; then
  echo "ERROR: Missing required env var: TNYR_PUBLIC_URL (https://example.com or http://1.2.3.4:5502)"
  exit 1
fi

INFO="$(python - <<'PY'
import os
from urllib.parse import urlparse
u = os.environ.get("TNYR_PUBLIC_URL","").strip()
p = urlparse(u)
if p.scheme not in ("http","https") or not p.netloc:
    raise SystemExit("Invalid TNYR_PUBLIC_URL (must be http(s)://host[:port])")
print(f"{p.scheme}://{p.netloc}")
print(p.netloc)
PY
)"

read -r NORMALIZED_PUBLIC_URL DOMAIN <<EOF
$INFO
EOF

if [ -n "${DB_PATH:-}" ]; then
  DB_DIR="$(dirname "$DB_PATH")"
  mkdir -p "$DB_DIR" || true
fi

mkdir -p /data || true

if [ -d "$DIST_DIR" ]; then
  if [ -n "$DOMAIN" ]; then
    echo "Applying public URL + domain to static files: $NORMALIZED_PUBLIC_URL ($DOMAIN)"
    SED_PUBLIC_URL="$(printf '%s' "$NORMALIZED_PUBLIC_URL" | sed 's/[\/&]/\\&/g')"
    SED_DOMAIN="$(printf '%s' "$DOMAIN" | sed 's/[\/&]/\\&/g')"
    find "$DIST_DIR" -type f \( -name "*.html" -o -name "*.xml" -o -name "*.json" -o -name "*.webmanifest" \) -print0 \
      | xargs -0 -r sed -i \
          -e "s/__TNYR_PUBLIC_URL__/$SED_PUBLIC_URL/g" \
          -e "s/__TNYR_DOMAIN__/$SED_DOMAIN/g" \
          -e "s/%VITE_PUBLIC_URL%/$SED_PUBLIC_URL/g" \
          -e "s/%VITE_DOMAIN%/$SED_DOMAIN/g"
  else
    echo "Could not derive domain from TNYR_PUBLIC_URL; leaving placeholders as-is in static files."
  fi
fi

cd /app/backend
python -c "import main; main.init_db()"
exec gunicorn --workers 2 --bind "0.0.0.0:${PORT}" wsgi:app


