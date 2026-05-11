#!/bin/bash
set -euo pipefail

CA_DIR="/home/mitmproxy/.mitmproxy"
CA_SHARE="/ca-share"
CA_COMBINED="$CA_DIR/mitmproxy-ca.pem"

if [ ! -f "$CA_COMBINED" ]; then
    echo "[proxy] Generating CA..."
    mkdir -p "$CA_DIR"

    # Generate key and cert to temp files
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$CA_DIR/key.tmp" \
        -out "$CA_DIR/cert.tmp" \
        -days 3650 \
        -subj "/CN=mitmproxy/O=BabyClaw/C=SG" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign"

    # mitmproxy expects mitmproxy-ca.pem to contain BOTH key and cert
    cat "$CA_DIR/key.tmp" "$CA_DIR/cert.tmp" > "$CA_COMBINED"
    chmod 600 "$CA_COMBINED"
    rm -f "$CA_DIR/key.tmp" "$CA_DIR/cert.tmp"

    echo "[proxy] CA generated: $CA_COMBINED"
fi

# Share CA cert (public portion only) with claw container via named volume
if [ -d "$CA_SHARE" ] && [ -w "$CA_SHARE" ]; then
    # Extract just the certificate portion for the trust store
    openssl x509 -in "$CA_COMBINED" -out "$CA_SHARE/mitmproxy-ca.pem"
    chmod 644 "$CA_SHARE/mitmproxy-ca.pem"
fi

exec mitmdump \
    --mode "upstream:http://squid:3128" \
    --listen-host 0.0.0.0 \
    --listen-port 1344 \
    --set connection_strategy=lazy \
    --set tls_version_server_min=UNBOUNDED \
    --set tls_version_client_min=UNBOUNDED \
    --set ignore_hosts=api.telegram.org \
    --scripts /app/addon.py \
    --set stream_large_bodies=5m \
    --set confdir="$CA_DIR"
