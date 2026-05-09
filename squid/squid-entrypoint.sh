#!/bin/bash
# BabyClaw squid entrypoint

# Create writable dirs (some may already exist from volume mounts)
mkdir -p /var/spool/squid /var/log/squid /run/squid 2>/dev/null || true

# Initialize cache directory structure
/usr/sbin/squid -z -f /etc/squid/squid.conf 2>&1 || true
rm -f /run/squid/squid.pid 2>/dev/null || true

# Run squid in foreground
exec /usr/sbin/squid -N -f /etc/squid/squid.conf "$@"
