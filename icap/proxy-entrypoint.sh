#!/bin/bash
set -euo pipefail

CA_DIR="/home/mitmproxy/.mitmproxy"
CA_KEY="$CA_DIR/mitmproxy-ca.key"
CA_CERT="$CA_DIR/mitmproxy-ca.pem"

if [ ! -f "$CA_CERT" ]; then
    echo "[proxy] Generating CA..."
    mkdir -p "$CA_DIR"
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$CA_KEY" \
        -out "$CA_CERT" \
        -days 3650 \
        -subj "/CN=mitmproxy/O=BabyClaw/C=SG" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign"
    chmod 600 "$CA_KEY" "$CA_CERT"
    echo "[proxy] CA generated: $CA_CERT"
fi

exec mitmdump \
    --mode "upstream:http://squid:3128" \
    --listen-host 0.0.0.0 \
    --listen-port 1344 \
    --set connection_strategy=lazy \
    --set tls_version_server_min=UNBOUNDED \
    --set tls_version_client_min=UNBOUNDED \
    --scripts /app/addon.py \
    --set stream_large_bodies=5m
