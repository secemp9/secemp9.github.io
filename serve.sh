#!/bin/bash
# Serve either the development build or production settings on localhost.
set -euo pipefail

site_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$site_dir"

settings="pelicanconf.py"
output="output"
port="${PORT:-4001}"

# Each supported option consumes itself (and its value), leaving no unchecked arguments.
while (($#)); do
    case "$1" in
        --production)
            settings="publishconf.py"
            output="output-preview"
            shift
            ;;
        --port|-p)
            if (($# < 2)); then
                printf '%s\n' 'Missing value for --port.' >&2
                exit 2
            fi
            port="$2"
            shift 2
            ;;
        --help|-h)
            printf '%s\n' 'Usage: ./serve.sh [--production] [--port PORT]' \
                'Default: http://localhost:4001 (override with PORT or --port).' \
                'Production preview uses publishconf.py and output-preview/.'
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

if [[ ! "$port" =~ ^[0-9]{1,5}$ ]] || ((10#$port < 1 || 10#$port > 65535)); then
    printf '%s\n' 'Port must be a number from 1 to 65535.' >&2
    exit 2
fi

if [[ -x .venv/bin/pelican ]]; then
    pelican_bin="$site_dir/.venv/bin/pelican"
elif command -v pelican >/dev/null 2>&1; then
    pelican_bin="$(command -v pelican)"
else
    printf '%s\n' 'Pelican is missing. Set up the local environment:' \
        '  python3 -m venv .venv' \
        '  .venv/bin/python -m pip install -r requirements.txt' >&2
    exit 1
fi

printf 'Serving %s at http://localhost:%s (output: %s/)\n' "$settings" "$port" "$output"
exec "$pelican_bin" content --settings "$settings" --output "$output" \
    --autoreload --listen --bind 127.0.0.1 --port "$port" --fatal errors \
    --extra-settings "SITEURL=\"http://localhost:$port\""
