"""mitmproxy addon: content inspection + Telegram reply enrichment.

Matches response bodies against injection_patterns.txt. Blocks with a 403
page on match. Domains in BYPASS_DOMAINS pass through uninspected.

Additionally caches outbound Telegram sendMessage responses and enriches
inbound getUpdates replies with the original message context so OpenClaw
can identify which digest story was replied to.

Flow: Claw → mitmproxy:1344 → Squid:3128 → internet
"""
import json
import re
import threading
from pathlib import Path

import mitmproxy.http

PATTERNS_FILE = Path("/etc/icap/injection_patterns.txt")
BYPASS_FILE = Path("/etc/icap/bypass_domains.txt")
BLOCK_PAGE = Path("/etc/icap/block-page.html").read_bytes()
MAX_BODY_SIZE = 5 * 1024 * 1024

# ── Telegram reply enrichment state ──────────────────────────────────
STATE_FILE = Path("/proxy-state/sent-messages.json")
MAX_CACHED_MESSAGES = 100
_message_cache = {}
_cache_lock = threading.Lock()


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


def load_message_cache():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", {})
        except Exception as e:
            print(f"[proxy] failed to load message cache: {e}")
    return {}


def save_message_cache():
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _cache_lock:
            # Keep only the most recent MAX_CACHED_MESSAGES
            items = list(_message_cache.items())
            if len(items) > MAX_CACHED_MESSAGES:
                items = items[-MAX_CACHED_MESSAGES:]
            trimmed = dict(items)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "messages": trimmed}, f, ensure_ascii=False)
    except Exception as e:
        print(f"[proxy] failed to save message cache: {e}")


PATTERNS = load_patterns()
BYPASS_DOMAINS = load_bypass_domains()
_message_cache = load_message_cache()
print(f"[babyclaw] loaded {len(PATTERNS)} patterns, {len(BYPASS_DOMAINS)} bypass domains, {len(_message_cache)} cached messages")


# ── Telegram reply enrichment ────────────────────────────────────────

class TelegramReplyEnricher:
    """Caches Telegram bot message IDs and enriches reply context."""

    def is_telegram_api(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        return flow.request.pretty_host == "api.telegram.org"

    def is_send_message(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        return self.is_telegram_api(flow) and "sendMessage" in flow.request.path

    def is_get_updates(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        return self.is_telegram_api(flow) and "getUpdates" in flow.request.path

    def request(self, flow: mitmproxy.http.HTTPFlow):
        if self.is_telegram_api(flow):
            print(f"[proxy] telegram req: {flow.request.method} {flow.request.path}")

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if not self.is_telegram_api(flow):
            return
        if not flow.response or not flow.response.content:
            print(f"[proxy] telegram response empty: {flow.request.path}")
            return

        try:
            data = json.loads(flow.response.content.decode("utf-8", errors="replace"))
        except Exception as e:
            print(f"[proxy] failed to parse telegram response: {e}")
            return

        if self.is_send_message(flow):
            print(f"[proxy] handling sendMessage response")
            self._cache_sent_message(data)
        elif self.is_get_updates(flow):
            print(f"[proxy] handling getUpdates response ({len(data.get('result', []))} updates)")
            self._enrich_updates(data, flow)
        else:
            print(f"[proxy] unhandled telegram endpoint: {flow.request.path}")

    def _cache_sent_message(self, data):
        if not data.get("ok") or "result" not in data:
            return
        result = data["result"]
        msg_id = result.get("message_id")
        text = result.get("text", "")
        if msg_id and text:
            with _cache_lock:
                _message_cache[str(msg_id)] = text
            save_message_cache()
            print(f"[proxy] cached sent message {msg_id}")

    def _enrich_updates(self, data, flow: mitmproxy.http.HTTPFlow):
        if not data.get("ok") or "result" not in data:
            print(f"[proxy] getUpdates response not ok or missing result")
            return
        updates = data.get("result", [])
        if not updates:
            print(f"[proxy] getUpdates returned 0 updates")
            return
        print(f"[proxy] processing {len(updates)} update(s)")
        modified = False
        channel_posts_converted = False
        for i, update in enumerate(updates):
            update_id = update.get("update_id", "?")
            msg = update.get("message", {})
            if not msg:
                # Convert channel_post / edited_channel_post → message so OpenClaw processes them
                for key in ("channel_post", "edited_channel_post"):
                    if key in update:
                        print(f"[proxy] update {i} (id={update_id}) is {key}, converting to message")
                        update["message"] = update.pop(key)
                        msg = update["message"]
                        channel_posts_converted = True
                        # OpenClaw expects 'from'; channel posts only have 'sender_chat'
                        if "from" not in msg:
                            sender = msg.get("sender_chat", {})
                            msg["from"] = {
                                "id": sender.get("id", 0),
                                "is_bot": False,
                                "first_name": sender.get("title", "Channel"),
                            }
                            print(f"[proxy]   added synthetic 'from' id={msg['from']['id']}")
                        # OpenClaw drops messages where chat.type == 'channel'
                        # Rewrite to 'group' so it routes through groupPolicy
                        if msg.get("chat", {}).get("type") == "channel":
                            msg["chat"]["type"] = "group"
                            print(f"[proxy]   rewritten chat.type channel → group")
                        break
                else:
                    # Other update types we don't handle
                    for key in ("edited_message", "callback_query", "inline_query", "chosen_inline_result"):
                        if key in update:
                            print(f"[proxy] update {i} (id={update_id}) is '{key}', skipping")
                            break
                    else:
                        print(f"[proxy] update {i} (id={update_id}) has no recognized message field: {list(update.keys())}")
                    continue

            msg_id = msg.get("message_id", "?")
            # Skip messages the bot itself sent — prevents feedback loops in channels
            if str(msg_id) in _message_cache:
                print(f"[proxy] update {i} (msg_id={msg_id}) is a bot-sent message — skipping")
                continue

            reply_to = msg.get("reply_to_message", {})
            user_text = msg.get("text", "")[:60]
            print(f"[proxy] update {i} (id={update_id}) msg_id={msg_id} text='{user_text}' reply_to={bool(reply_to)}")

            if not reply_to:
                print(f"[proxy] update {i} (msg_id={msg_id}) has no reply_to_message — skipping enrichment")
                continue

            reply_msg_id = reply_to.get("message_id")
            if not reply_msg_id:
                print(f"[proxy] update {i} (msg_id={msg_id}) reply_to_message missing message_id — skipping")
                continue

            original_text = _message_cache.get(str(reply_msg_id), "")
            if not original_text:
                # Message not in our cache — check if it's a confirmed non-bot reply
                from_user = reply_to.get("from", {})
                if from_user.get("is_bot") is False:
                    print(f"[proxy] reply to non-bot msg {reply_msg_id} — skipping")
                else:
                    print(f"[proxy] reply to msg {reply_msg_id} not in cache (is_bot={from_user.get('is_bot')}) — skipping")
                continue

            # Message is in our cache — enrich regardless of is_bot
            # (if it's in our cache, we sent it; message IDs are unique within a chat)
            truncated = original_text.replace("\n", " ").strip()
            if len(truncated) > 200:
                truncated = truncated[:197] + "..."
            prefix = f"[Reply to BabyClaw msg:{reply_msg_id} — \"{truncated}\"]\n\n"

            current_text = msg.get("text", "")
            if prefix not in current_text:  # idempotent — don't double-prefix
                msg["text"] = prefix + current_text
                modified = True
                print(f"[proxy] ✓ enriched reply to msg {reply_msg_id}")
            else:
                print(f"[proxy] reply to msg {reply_msg_id} already enriched")

        if modified or channel_posts_converted:
            new_body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            flow.response.content = new_body
            flow.response.headers["content-length"] = str(len(new_body))
            action = "enriched" if modified else "converted channel_post"
            print(f"[proxy] getUpdates response {action} and returned")


# ── Content inspection ───────────────────────────────────────────────

class BabyClawInspector:
    def should_inspect(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        host = flow.request.pretty_host
        # Skip Telegram API for injection scanning (JSON responses, not web content)
        if host == "api.telegram.org":
            return False
        return host not in BYPASS_DOMAINS

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if not self.should_inspect(flow):
            return
        if not flow.response or not flow.response.content:
            return
        if len(flow.response.content) > MAX_BODY_SIZE:
            return
        try:
            text = flow.response.content.decode("utf-8", errors="replace")
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


addons = [TelegramReplyEnricher(), BabyClawInspector()]
