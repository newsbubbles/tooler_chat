#!/bin/sh
set -e

# Generate nginx.conf with environment variables
envsubst < /etc/nginx/conf.d/default.template > /etc/nginx/conf.d/default.conf

# Execute the CMD from the Dockerfile
exec "$@"
