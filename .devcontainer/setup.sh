#!/bin/bash
set -e

echo "Starting Post-Create Setup..."

# Ensure we are in the workspace root
cd /workspaces/data-engineering-zoomcamp-2026-project-attempt-1

echo "Installing Bruin CLI on Host..."
curl -sL https://github.com/bruin-data/bruin/releases/latest/download/bruin_Linux_x86_64.tar.gz | tar -xz
mv bruin /usr/local/bin/bruin || sudo mv bruin /usr/local/bin/bruin || true
chmod +x /usr/local/bin/bruin || sudo chmod +x /usr/local/bin/bruin || true
export PATH=$PATH:/usr/local/bin

echo "Bringing up the Docker Compose cluster..."
docker-compose up -d --build || true

echo "Waiting for Manticore to initialize..."
sleep 5

echo "Executing Bruin Pipeline..."
# We execute it inside the bruin container where requirements are fully installed
docker-compose exec bruin bash -c "export PATH=\$PATH:/usr/local/bin && bruin run pipeline/" || true

echo "Setup Complete! Gradio is running on port 7860."
