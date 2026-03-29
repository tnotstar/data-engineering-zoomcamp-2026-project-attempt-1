#!/bin/bash
# =============================================================
# Build-time helper — Stage 2 (Gold): TSV → Manticore index files
# Runs inside the Docker multi-stage build, NOT at container runtime.
# Starts Manticore, loads Silver TSV data, stops Manticore.
# Result: /data/gold/ contains the baked Manticore index files.
# =============================================================
set -e

mkdir -p /data/gold /var/log/manticore /var/run/manticore /tmp/manticore-binlog-build
chown -R manticore:manticore /data/gold /var/log/manticore /var/run/manticore

# Write Manticore config pointing data_dir to /data/gold
cat > /etc/manticoresearch/manticore.conf << 'EOF'
searchd {
    listen = 127.0.0.1:9306:mysql
    listen = 127.0.0.1:9308:http
    pid_file = /var/run/manticore/searchd.pid
    data_dir = /data/gold
    log = /var/log/manticore/searchd.log
    query_log = /var/log/manticore/query.log
    binlog_path = /tmp/manticore-binlog-build
}
EOF

# Start Manticore in the background
echo "Starting Manticore (build phase, gold layer)..."
gosu manticore searchd --nodetach &

# Wait for Manticore HTTP API to be ready
echo "Waiting for Manticore on 127.0.0.1:9308..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:9308/ > /dev/null 2>&1; then
        echo "Manticore ready (attempt $i)."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Manticore did not start within 60 seconds." >&2
        exit 1
    fi
    sleep 2
done

# Load the Silver TSV data into Manticore (gold layer)
echo "Loading data into Gold layer..."
export MANTICORE_URL="http://127.0.0.1:9308"
python3 /tmp/load_to_manticore.py

# Stop Manticore cleanly
echo "Stopping Manticore..."
gosu manticore searchd --stop || true
sleep 3

# Remove the transient binlog (not needed in final image)
rm -rf /tmp/manticore-binlog-build

echo "Gold layer complete. Files in /data/gold:"
ls -lh /data/gold/
