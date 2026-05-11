"""mitmproxy addon: content inspection against regex patterns.

Matches response bodies against injection_patterns.txt. Blocks with a 403
page on match. Domains in BYPASS_DOMAINS pass through uninspected.

Flow: Claw → mitmproxy:1344 → Squid:3128 → internet
"""
import re
from pathlib import Path

import mitmproxy.http

PATTERNS_FILE = Path("/etc/icap/injection_patterns.txt")
BYPASS_FILE = Path("/etc/icap/bypass_domains.txt")
BLOCK_PAGE = Path("/etc/icap/block-page.html").read_bytes()
MAX_BODY_SIZE = 5 * 1024 * 1024


def load_patterns():
    patterns = []
    for line in PATTERNS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        category, pattern = line.split(":", 1)
        try:
            patterns.append((category, re.compile(pattern, re.IGNORECASE)))
        except re.error as e:
            print(f"[babyclaw] invalid regex '{pattern}': {e}")
    return patterns


def load_bypass_domains():
    domains = set()
    if not BYPASS_FILE.exists():
        return domains
    for line in BYPASS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            domains.add(line)
    return domains


PATTERNS = load_patterns()
BYPASS_DOMAINS = load_bypass_domains()
print(f"[babyclaw] loaded {len(PATTERNS)} patterns, {len(BYPASS_DOMAINS)} bypass domains")


class BabyClawInspector:
    def should_inspect(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        host = flow.request.pretty_host
        return host not in BYPASS_DOMAINS

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if not self.should_inspect(flow):
            return
        if not flow.response or not flow.response.content:
            return
        if len(flow.response.content) > MAX_BODY_SIZE:
            return
        try:
            text = flow.response.get_text()
        except Exception:
            return
        for category, pattern in PATTERNS:
            if pattern.search(text):
                print(f"[babyclaw] BLOCK {category}: {pattern.pattern[:80]} [{flow.request.pretty_url}]")
                flow.response = mitmproxy.http.Response.make(
                    403,
                    BLOCK_PAGE,
                    {"Content-Type": "text/html"},
                )
                return


addons = [BabyClawInspector()]
