#!/bin/sh
# Generate config.js from environment variables at container startup
# This runs before nginx starts via docker-entrypoint.d mechanism

set -e

# Use envsubst to replace ${API_URL} in template
envsubst '${API_URL}' < /etc/nginx/templates/config.template.js > /usr/share/nginx/html/config.js

echo "Generated config.js with API_URL=${API_URL}"

# Substitute NGINX_LOG_LEVEL in nginx configuration
envsubst '${NGINX_LOG_LEVEL}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

echo "Configured nginx with log level: ${NGINX_LOG_LEVEL}"
