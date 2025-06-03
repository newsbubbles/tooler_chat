#!/bin/bash

# Load environment variables if .env exists
if [ -f .env ]; then
    source .env
fi

# Use default ports if not set
BACKEND_PORT=${BACKEND_PORT:-34130}
FRONTEND_PORT=${FRONTEND_PORT:-34140}

# Generate nginx-host.conf with environment variables
cat > nginx-host.conf << EOF
# Configuration for Nginx on the host system
# This can be used to add additional proxy rules

server {
    listen 80;
    server_name your_domain.com;  # Replace with your actual domain or IP

    # Frontend proxy
    location / {
        proxy_pass http://localhost:$FRONTEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Backend docs proxy
    location /docs {
        proxy_pass http://localhost:$BACKEND_PORT/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Backend openapi.json proxy
    location /openapi.json {
        proxy_pass http://localhost:$BACKEND_PORT/openapi.json;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "Generated nginx-host.conf with BACKEND_PORT=$BACKEND_PORT and FRONTEND_PORT=$FRONTEND_PORT"
echo "You can use this file in your host Nginx configuration."
