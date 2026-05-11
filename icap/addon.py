"""mitmproxy addon: content inspection against regex patterns.

Matches response bodies against injection_patterns.txt (same format the
hand-rolled proxy used). Blocks with a 403 page on match, passes all other
traffic through transparently.
"""
import re
from pathlib import Path

import mitmproxy.http
from mitmproxy import flowfilter

PATTERNS_FILE = Path("/etc/icap/injection_patterns.txt")
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


PATTERNS = load_patterns()
print(f"[babyclaw] loaded {len(PATTERNS)} inspection patterns")


class BabyClawInspector:
    def response(self, flow: mitmproxy.http.HTTPFlow):
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
