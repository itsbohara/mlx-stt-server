#!/bin/bash

# Parakeet STT Server Start Script
# Handles virtual environment activation and prevents duplicate instances

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$SCRIPT_DIR/server.pid"
VENV_PATH="$SCRIPT_DIR/.venv"
SERVER_SCRIPT="$SCRIPT_DIR/openai_server.py"

# Check if already running
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Server is already running (PID: $PID)"
        exit 0
    else
        # Stale PID file, remove it
        rm -f "$PIDFILE"
    fi
fi

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found at $VENV_PATH"
    echo "Please create it first: python3 -m venv .venv"
    exit 1
fi

# Check if server script exists
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo "Server script not found: $SERVER_SCRIPT"
    exit 1
fi

# Activate virtual environment and start server in background
echo "Starting Parakeet STT Server..."
(
    cd "$SCRIPT_DIR"
    source "$VENV_PATH/bin/activate"
    python "$SERVER_SCRIPT" > server.log 2>&1 &
    echo $! > "$PIDFILE"
)

# Wait a moment to check if it started successfully
sleep 2

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Server started successfully (PID: $PID)"
        echo "Logs: server.log"
        echo "Stop with: ./stop.sh"
    else
        echo "Server failed to start. Check server.log for details."
        rm -f "$PIDFILE"
        exit 1
    fi
fi
