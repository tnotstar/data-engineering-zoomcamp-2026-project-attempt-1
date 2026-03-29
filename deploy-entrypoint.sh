#!/bin/bash
set -e

# Change ownership of manticore directories if running as root
if [ "$(id -u)" = '0' ]; then
    mkdir -p /var/log/manticore /var/run/manticore /var/lib/manticore
    chown -R manticore:manticore /var/lib/manticore /var/log/manticore /var/run/manticore /etc/manticoresearch
fi

# Start Manticore search tightly coupled in the background
echo "Starting search-engine (Manticore) in the background..."

if [ "$(id -u)" = '0' ]; then
    gosu manticore searchd --nodetach &
else
    searchd --nodetach &
fi

# Wait for Manticore to be ready (internal port 9308)
echo "Waiting for search-engine on port 9308..."
while ! curl -s http://127.0.0.1:9308/ >/dev/null; do
    sleep 1
done
echo "search-engine is up!"

# Start the dashboard
echo "Starting Dashboard on port ${PORT:-8080}..."
export GRADIO_SERVER_PORT=${PORT:-8080}
export GRADIO_SERVER_NAME="0.0.0.0"
export MANTICORE_URL="http://127.0.0.1:9308"

cd /app
exec python3 main.py
