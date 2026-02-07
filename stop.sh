#!/bin/bash

# Parakeet STT Server Stop Script
# Gracefully stops the running server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$SCRIPT_DIR/server.pid"

# Check if PID file exists
if [ ! -f "$PIDFILE" ]; then
    echo "Server is not running (no PID file found)"
    exit 0
fi

PID=$(cat "$PIDFILE")

# Check if process is actually running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "Server is not running (stale PID file removed)"
    rm -f "$PIDFILE"
    exit 0
fi

# Gracefully terminate the server
echo "Stopping server (PID: $PID)..."
kill "$PID"

# Wait for process to terminate (max 10 seconds)
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "Server stopped successfully"
        rm -f "$PIDFILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "Force stopping server..."
kill -9 "$PID" 2>/dev/null
rm -f "$PIDFILE"
echo "Server stopped"
