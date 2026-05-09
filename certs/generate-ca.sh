#!/bin/bash
# Generate self-signed CA for TLS interception.
# Run once before docker compose build. Keep the key secure — it's in .gitignore.
set -euo pipefail
cd "$(dirname "$0")"
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout babyclaw-ca.key \
  -out babyclaw-ca.pem \
  -days 3650 \
  -subj "/CN=BabyClaw Inspection CA/O=BabyClaw/C=SG"
echo "CA generated: babyclaw-ca.pem"
echo "Mount this cert in the Claw container to trust the inspection proxy."
