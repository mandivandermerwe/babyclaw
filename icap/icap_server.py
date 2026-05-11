"""
BabyClaw Content Inspection Proxy

Sits between Claw and Squid. Handles both HTTP (plain, with inspection)
and HTTPS (TLS-terminated, with inspection) through Squid upstream.

Chain: Claw -> Inspection Proxy :1344 -> Squid :3128 -> Internet

For TLS interception: client trusts our self-signed CA, proxy generates
per-host certs on-the-fly, terminates TLS, scans the response body,
then re-encrypts with the generated cert.
"""
import re
import sys
import socket
import select
import ssl
import threading
import tempfile
import os
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

# ── Load patterns ────────────────────────────────────────────────────────
PATTERNS = []
PATTERNS_FILE = Path("/etc/icap/injection_patterns.txt")
BLOCK_PAGE = Path("/etc/icap/block-page.html").read_text().encode("utf-8")
MAX_BODY_SIZE = 5 * 1024 * 1024  # 5MB

if PATTERNS_FILE.exists():
    for line in PATTERNS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        category, pattern = line.split(":", 1)
        try:
            PATTERNS.append((category, re.compile(pattern, re.IGNORECASE)))
        except re.error as e:
            print(f"[proxy] Invalid regex '{pattern}': {e}", file=sys.stderr)

print(f"[proxy] Loaded {len(PATTERNS)} patterns", file=sys.stderr)

# ── CA for TLS interception ──────────────────────────────────────────────
CA_CERT = Path("/etc/icap/ca/babyclaw-ca.pem")
CA_KEY = Path("/etc/icap/ca/babyclaw-ca.key")
HAS_TLS = CA_CERT.exists() and CA_KEY.exists()
if HAS_TLS:
    print(f"[proxy] TLS interception enabled with CA: {CA_CERT}", file=sys.stderr)
else:
    print(f"[proxy] TLS interception disabled (no CA found)", file=sys.stderr)

# ── Squid upstream proxy ─────────────────────────────────────────────────
UPSTREAM_PROXY = "http://squid:3128"
proxy_handler = urllib.request.ProxyHandler({"http": UPSTREAM_PROXY, "https": UPSTREAM_PROXY})
opener = urllib.request.build_opener(proxy_handler)


def check_body(body: bytes) -> tuple[str, str] | None:
    if len(body) > MAX_BODY_SIZE:
        return None
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return None
    for category, pattern in PATTERNS:
        if pattern.search(text):
            return (category, pattern.pattern)
    return None


def build_http_response(status: int, body: bytes, content_type: str = "text/html") -> bytes:
    return (
        f"HTTP/1.0 {status} OK\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("utf-8") + body


def parse_http_request(data: bytes) -> tuple[str, str, dict]:
    header_end = data.find(b"\r\n\r\n")
    if header_end == -1:
        return ("", "", {})
    header_section = data[:header_end].decode("utf-8", errors="replace")
    lines = header_section.split("\r\n")
    if not lines:
        return ("", "", {})
    parts = lines[0].split(" ")
    method = parts[0] if parts else ""
    url = parts[1] if len(parts) > 1 else ""
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k.lower()] = v
    return method, url, headers


def generate_host_cert(hostname: str) -> tuple[str, str]:
    """Generate a self-signed cert for a hostname, signed by our CA.
    Returns (cert_path, key_path). Cached by hostname in /tmp."""
    cached_cert = Path(f"/tmp/cert_{hostname}.pem")
    cached_key = Path(f"/tmp/cert_{hostname}.key")
    # Validate cache — must be non-empty
    if cached_cert.exists() and cached_key.exists() and cached_cert.stat().st_size > 0:
        return (str(cached_cert), str(cached_key))
    # Remove stale files
    for p in [cached_cert, cached_key]:
        try:
            p.unlink()
        except OSError:
            pass

    key_path = f"/tmp/cert_{hostname}.key"
    csr_path = f"/tmp/cert_{hostname}.csr"
    cert_path = f"/tmp/cert_{hostname}.pem"

    # Generate key and CSR
    rc = os.system(
        f"openssl req -new -newkey rsa:2048 -nodes "
        f"-keyout {key_path} -out {csr_path} "
        f"-subj /CN={hostname} 2>/dev/null"
    )
    if rc != 0 or not os.path.exists(csr_path) or os.path.getsize(csr_path) == 0:
        print(f"[proxy] CERTGEN: CSR generation failed (rc={rc})", file=sys.stderr)
        return (None, None)

    # Sign with CA. Set serial manually to avoid writing .srl next to read-only CA cert.
    serial = abs(hash(hostname)) % (10 ** 8)
    rc = os.system(
        f"openssl x509 -req -in {csr_path} "
        f"-CA {CA_CERT} -CAkey {CA_KEY} "
        f"-set_serial {serial} "
        f"-out {cert_path} -days 365 2>/dev/null"
    )
    try:
        os.unlink(csr_path)
    except OSError:
        pass

    if rc != 0 or not os.path.exists(cert_path) or os.path.getsize(cert_path) == 0:
        print(f"[proxy] CERTGEN: Signing failed (rc={rc})", file=sys.stderr)
        return (None, None)

    print(f"[proxy] CERTGEN: generated cert for {hostname} ({os.path.getsize(cert_path)}B)", file=sys.stderr)
    return (cert_path, key_path)


def https_connect_inspect(conn: socket.socket, target_host: str, target_port: str) -> None:
    """Handle CONNECT with TLS termination and content inspection."""
    # 1. Connect to target through Squid
    upstream_sock = socket.socket()
    upstream_sock.settimeout(10)
    upstream_sock.connect(("squid", 3128))
    connect_req = f"CONNECT {target_host}:{target_port} HTTP/1.0\r\nHost: {target_host}:{target_port}\r\n\r\n"
    upstream_sock.sendall(connect_req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += upstream_sock.recv(4096)
    if b"200" not in resp[:20]:
        conn.sendall(b"HTTP/1.0 403 Forbidden\r\n\r\n")
        upstream_sock.close()
        return

    # 2. Tell client tunnel is established
    conn.sendall(b"HTTP/1.0 200 Connection Established\r\n\r\n")

    # 3. TLS handshake with client using generated cert
    cert_path, key_path = generate_host_cert(target_host)
    if cert_path is None:
        conn.sendall(b"HTTP/1.0 500 Internal Server Error\r\n\r\n")
        upstream_sock.close()
        return
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    try:
        tls_conn = context.wrap_socket(conn, server_side=True)
    except ssl.SSLError:
        return  # Client may have disconnected (health check, etc.)

    # 4. Read the HTTP request from the client over TLS
    data = b""
    try:
        while b"\r\n\r\n" not in data and len(data) < 65536:
            data += tls_conn.recv(65536)
    except ssl.SSLError:
        pass

    if not data:
        tls_conn.close()
        upstream_sock.close()
        return

    method, url, req_headers = parse_http_request(data)

    # 5. Fetch the URL over real TLS through Squid
    try:
        upstream_headers = {"User-Agent": "BabyClaw/1.0", "Accept": "*/*"}
        for key, val in req_headers.items():
            if key in ("authorization", "content-type", "x-api-key"):
                upstream_headers[key] = val
        upstream_req = urllib.request.Request(
            url if url.startswith("http") else f"https://{target_host}{url}",
            headers=upstream_headers,
            method=method if method in ("GET", "HEAD") else "GET"
        )
        with opener.open(upstream_req, timeout=15) as up_resp:
            body = up_resp.read(MAX_BODY_SIZE + 1)
            content_type = up_resp.headers.get("Content-Type", "text/html")

        # 6. Scan for prompt injection
        result = check_body(body)
        if result:
            category, pattern = result
            print(f"[proxy] BLOCK {category}: {pattern[:80]} [https://{target_host}]", file=sys.stderr)
            tls_conn.sendall(build_http_response(403, BLOCK_PAGE, "text/html"))
        else:
            tls_conn.sendall(build_http_response(200, body, content_type))
    except Exception as e:
        print(f"[proxy] HTTPS fetch error for {target_host}: {e}", file=sys.stderr)
        tls_conn.sendall(build_http_response(502, f"Upstream error: {e}".encode("utf-8")))

    try:
        tls_conn.close()
    except Exception:
        pass
    upstream_sock.close()


# ── Server ────────────────────────────────────────────────────────────────

HOST = "0.0.0.0"
PORT = 1344

print(f"[proxy] Starting inspection proxy on {HOST}:{PORT}", file=sys.stderr)
print(f"[proxy] Upstream: {UPSTREAM_PROXY}", file=sys.stderr)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen(32)

while True:
    try:
        readable, _, _ = select.select([sock], [], [], 1.0)
        if not readable:
            continue

        conn, addr = sock.accept()
        conn.settimeout(30)
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 65536:
            try:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break

        if not data:
            conn.close()
            continue

        method, url, req_headers = parse_http_request(data)
        print(f"[proxy] {method} {url}", file=sys.stderr)

        if method == "CONNECT" and HAS_TLS:
            target_host, target_port = url.split(":") if ":" in url else (url, "443")
            try:
                https_connect_inspect(conn, target_host, target_port)
            except Exception as e:
                print(f"[proxy] CONNECT error: {e}", file=sys.stderr)
            conn.close()
            continue

        if method == "CONNECT" and not HAS_TLS:
            # Blind tunnel without inspection (fallback, no CA configured)
            target_host, target_port = url.split(":") if ":" in url else (url, "443")
            try:
                upstream_sock = socket.socket()
                upstream_sock.settimeout(10)
                upstream_sock.connect(("squid", 3128))
                connect_req = f"CONNECT {target_host}:{target_port} HTTP/1.0\r\nHost: {target_host}:{target_port}\r\n\r\n"
                upstream_sock.sendall(connect_req.encode())
                resp = b""
                while b"\r\n\r\n" not in resp:
                    resp += upstream_sock.recv(4096)
                if b"200" not in resp[:20]:
                    conn.sendall(b"HTTP/1.0 403 Forbidden\r\n\r\n")
                    upstream_sock.close()
                    conn.close()
                    continue
                conn.sendall(b"HTTP/1.0 200 Connection Established\r\n\r\n")
                conn.setblocking(False)
                upstream_sock.setblocking(False)
                for _ in range(300):
                    r, _, _ = select.select([conn, upstream_sock], [], [], 0.1)
                    if conn in r:
                        d = conn.recv(65536)
                        if d:
                            upstream_sock.sendall(d)
                    if upstream_sock in r:
                        d = upstream_sock.recv(65536)
                        if d:
                            conn.sendall(d)
                upstream_sock.close()
            except Exception as e:
                print(f"[proxy] CONNECT error: {e}", file=sys.stderr)
            conn.close()
            continue

        with conn:
            if method not in ("GET", "HEAD", "POST"):
                conn.sendall(build_http_response(405, b"Method Not Allowed"))
                continue

            # Plain HTTP — fetch upstream, scan, return
            try:
                upstream_headers = {"User-Agent": "BabyClaw/1.0", "Accept": "*/*"}
                for key, val in req_headers.items():
                    if key in ("authorization", "content-type", "x-api-key"):
                        upstream_headers[key] = val
                upstream_req = urllib.request.Request(
                    url,
                    headers=upstream_headers,
                    method=method
                )
                with opener.open(upstream_req, timeout=15) as resp:
                    body = resp.read(MAX_BODY_SIZE + 1)
                    content_type = resp.headers.get("Content-Type", "text/html")

                result = check_body(body)
                if result:
                    category, pattern = result
                    print(f"[proxy] BLOCK {category}: {pattern[:80]}", file=sys.stderr)
                    conn.sendall(build_http_response(403, BLOCK_PAGE, "text/html"))
                else:
                    conn.sendall(build_http_response(200, body, content_type))
            except urllib.error.HTTPError as e:
                conn.sendall(build_http_response(e.code, str(e).encode("utf-8")))
            except Exception as e:
                print(f"[proxy] Fetch error for {url}: {e}", file=sys.stderr)
                conn.sendall(build_http_response(502, f"Upstream error: {e}".encode("utf-8")))
    except Exception as e:
        print(f"[proxy] Error: {e}", file=sys.stderr)
