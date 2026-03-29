#!/bin/bash
# =============================================================
# Production entrypoint for Google Cloud Run
# Data is pre-baked in /data/gold (Manticore index files)
# Operational files (pid, logs, binlog) go to /tmp (ephemeral)
# =============================================================
set -e

# Create writable operational directories in /tmp (ephemeral, lost on restart)
mkdir -p /tmp/manticore-binlog /var/log/manticore /var/run/manticore

# Fix ownership for all data and operational directories
if [ "$(id -u)" = '0' ]; then
    echo "Fixing permissions for /data and operational directories..."
    chown -R manticore:manticore /data /var/log/manticore /var/run/manticore /tmp/manticore-binlog
fi

# Start Manticore in the background
# Config points data_dir to /data/gold (read-only by intent)
echo "Starting search-engine (Manticore) from baked index in /data/gold..."

if [ "$(id -u)" = '0' ]; then
    gosu manticore searchd --nodetach &
else
    searchd --nodetach &
fi

# Wait for Manticore to be ready
echo "Waiting for search-engine on port 9308..."
while ! curl -s http://127.0.0.1:9308/ > /dev/null 2>&1; do
    sleep 1
done
echo "search-engine is up!"

# Start the Gradio Dashboard
echo "Starting Dashboard on port ${PORT:-8080}..."
export GRADIO_SERVER_PORT=${PORT:-8080}
export GRADIO_SERVER_NAME="0.0.0.0"
export MANTICORE_URL="http://127.0.0.1:9308"

cd /app
exec python3 main.py
