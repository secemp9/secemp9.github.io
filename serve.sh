#!/bin/bash
# Jekyll serve script with automatic port selection and live reload

HOST="127.0.0.1"
START_PORT=4000
END_PORT=4100
LR_START=35729
LR_END=35749
PORT=""
LIVE_RELOAD_PORT=""

is_port_in_use() {
  local host="$1"
  local port="$2"
  if timeout 1 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
    return 0  # in use (connection succeeded)
  else
    return 1  # free (connection failed)
  fi
}

for p in $(seq "$START_PORT" "$END_PORT"); do
  if ! is_port_in_use "$HOST" "$p"; then
    PORT="$p"
    break
  fi
done

if [ -z "$PORT" ]; then
  echo "Error: No free HTTP port found in range $START_PORT-$END_PORT on $HOST"
  exit 1
fi

for lp in $(seq "$LR_START" "$LR_END"); do
  if ! is_port_in_use "$HOST" "$lp"; then
    LIVE_RELOAD_PORT="$lp"
    break
  fi
done

echo "Starting Jekyll server on http://$HOST:$PORT"
if [ -n "$LIVE_RELOAD_PORT" ]; then
  echo "LiveReload will be available on port $LIVE_RELOAD_PORT"
else
  echo "No free LiveReload port available in $LR_START-$LR_END; continuing without LiveReload"
fi
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
if [ -n "$LIVE_RELOAD_PORT" ]; then
  bundle exec jekyll serve --port "$PORT" --livereload --livereload-port "$LIVE_RELOAD_PORT" --host "$HOST"
else
  bundle exec jekyll serve --port "$PORT" --no-livereload --host "$HOST"
fi

