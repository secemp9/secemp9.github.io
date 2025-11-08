#!/bin/bash
# Jekyll serve script with automatic port selection and live reload

HOST="127.0.0.1"
START_PORT=4000
END_PORT=4100
LR_START=35729
LR_END=35749
PORT=""
LIVE_RELOAD_PORT=""
VERBOSE=false
TRACE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -t|--trace)
      TRACE=true
      VERBOSE=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -v, --verbose   Show verbose output"
      echo "  -t, --trace     Show trace output (includes verbose)"
      echo "  -h, --help      Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use -h or --help for usage information"
      exit 1
      ;;
  esac
done

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

# Build Jekyll command with appropriate flags
JEKYLL_CMD="bundle exec jekyll serve --port $PORT --host $HOST"

if [ -n "$LIVE_RELOAD_PORT" ]; then
  JEKYLL_CMD="$JEKYLL_CMD --livereload --livereload-port $LIVE_RELOAD_PORT"
else
  JEKYLL_CMD="$JEKYLL_CMD --no-livereload"
fi

if [ "$VERBOSE" = true ]; then
  JEKYLL_CMD="$JEKYLL_CMD --verbose"
fi

if [ "$TRACE" = true ]; then
  JEKYLL_CMD="$JEKYLL_CMD --trace"
fi

# Run Jekyll and ensure errors are visible
echo "Running: $JEKYLL_CMD"
echo ""
# Use eval to properly execute the command with all arguments
# 2>&1 ensures both stdout and stderr are visible
eval "$JEKYLL_CMD" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo ""
  echo "ERROR: Jekyll server failed to start (exit code: $EXIT_CODE)!"
  echo "Check the error messages above for details."
  exit $EXIT_CODE
fi

