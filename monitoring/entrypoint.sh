#!/bin/sh
set -e

# If a .env file exists in the mounted directory, load it (useful for local testing)
if [ -f /etc/prometheus/.env ]; then
    export $(grep -v '^#' /etc/prometheus/.env | xargs)
fi

# Substitute environment variables into the template to produce the final Prometheus config
sed -e "s|\${GF_PROMETHEUS_URL}|${GF_PROMETHEUS_URL}|g" \
    -e "s|\${GF_USER}|${GF_USER}|g" \
    -e "s|\${GF_API_KEY}|${GF_API_KEY}|g" \
    /etc/prometheus/prometheus.yml.template > /prometheus/prometheus.yml

# Start Prometheus (pass through any additional CLI args, e.g. --web.listen-address)
exec /bin/prometheus --web.listen-address=:9090 --storage.tsdb.path=/prometheus "$@"
