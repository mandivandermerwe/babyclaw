#!/bin/bash
set -euo pipefail

CA_DIR="/home/mitmproxy/.mitmproxy"
CA_TMP="/tmp/mitmproxy-ca"
CA_KEY="$CA_DIR/mitmproxy-ca.key"
CA_CERT="$CA_DIR/mitmproxy-ca.pem"

if [ ! -f "$CA_CERT" ]; then
    echo "[proxy] Generating CA..."
    mkdir -p "$CA_TMP"
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$CA_TMP/mitmproxy-ca.key" \
        -out "$CA_TMP/mitmproxy-ca.pem" \
        -days 3650 \
        -subj "/CN=mitmproxy/O=BabyClaw/C=SG" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign"
    mkdir -p "$CA_DIR"
    cp "$CA_TMP"/mitmproxy-ca.* "$CA_DIR"/
    chmod 600 "$CA_KEY" "$CA_CERT"
    rm -rf "$CA_TMP"
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
