#!/bin/bash
set -euo pipefail

echo "[babyclaw] Initializing OpenClaw..."

# Limit V8 heap to 2GB to prevent OOM kills. Append to any existing NODE_OPTIONS
# (e.g. global-agent --require) so we don't clobber them.
export NODE_OPTIONS="${NODE_OPTIONS:+$NODE_OPTIONS }--max-old-space-size=2048"

# Persistent state in scratch volume — survives container restarts and rsync.
# HOME points to scratch so ~/.openclaw/ lands in the persistent volume.
export HOME=/home/claw/scratch
mkdir -p "$HOME/.openclaw"/{workspace,logs,agents/main/agent,cron}

CONFIG_FILE="$HOME/.openclaw/openclaw.json"
IDENTITY_FILE="$HOME/.openclaw/agents/main/agent/IDENTITY.md"
USER_FILE="$HOME/.openclaw/agents/main/agent/USER.md"

# ── Generate config on first boot, or update model if stale ───────────
GENERATE_CONFIG=false
if [ ! -f "$CONFIG_FILE" ]; then
  echo "[babyclaw] First boot — generating config..."
  GENERATE_CONFIG=true
else
  # Check if existing config still references the old LiteLLM/Claude model
  if grep -q 'claude-haiku-4-5' "$CONFIG_FILE" 2>/dev/null; then
    echo "[babyclaw] Stale model detected (claude-haiku-4-5) — regenerating agent config..."
    GENERATE_CONFIG=true
  fi
fi

if [ "$GENERATE_CONFIG" = true ]; then
  cat > "$CONFIG_FILE" << JSONEOF
{
  "models": {
    "providers": {
      "deepseek": {
        "baseUrl": "https://api.deepseek.com",
        "apiKey": "${DEEPSEEK_API_KEY:-}",
        "api": "openai-completions",
        "models": [
          {
            "id": "deepseek-v4-flash",
            "name": "DeepSeek V4 Flash",
            "reasoning": false,
            "input": ["text"],
            "contextWindow": 200000,
            "maxTokens": 8192
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": { "primary": "deepseek/deepseek-v4-flash", "fallbacks": [] },
      "workspace": "/home/claw/scratch",
      "userTimezone": "${TZ:-UTC}",
      "thinkingDefault": "off",
      "reasoningDefault": "off",
      "sandbox": { "mode": "off" }
    },
    "list": [
      {
        "id": "main",
        "default": true,
        "name": "BabyClaw",
        "model": { "primary": "deepseek/deepseek-v4-flash", "fallbacks": [] },
        "thinkingDefault": "off",
        "reasoningDefault": "off",
        "skills": [],
        "identity": { "name": "BabyClaw", "emoji": "🗞" }
      }
    ]
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "__TELEGRAM_BOT_TOKEN__",
      "dmPolicy": "allowlist",
      "allowFrom": __TELEGRAM_ALLOW_FROM__,
      "groupPolicy": "open",
      "streaming": { "mode": "off" }
    }
  },
  "session": {
    "scope": "per-sender",
    "dmScope": "main",
    "reset": { "mode": "daily", "atHour": 4 },
    "maintenance": {
      "mode": "warn",
      "pruneAfter": "14d"
    }
  },
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "port": 18789
  },
  "plugins": {
    "entries": {
      "deepseek": {
        "enabled": true
      },
      "duckduckgo": {
        "enabled": true
      }
    }
  }
}
JSONEOF
  sed -i "s/__TELEGRAM_BOT_TOKEN__/${TELEGRAM_BOT_TOKEN}/g" "$CONFIG_FILE"
	sed -i "s/__TELEGRAM_ALLOW_FROM__/${TELEGRAM_ALLOW_FROM:-[]}/g" "$CONFIG_FILE"
else
  echo "[babyclaw] Config exists — preserving state from previous run"
fi

# ── Identity files (idempotent — only create if missing) ─────────────
if [ ! -f "$IDENTITY_FILE" ]; then
  cat > "$IDENTITY_FILE" << 'EOF'
name: BabyClaw
emoji: 🗞
vibe: Professional, sharp news curator
mission: Curate geopolitically significant news from independent media
EOF
fi

if [ ! -f "$USER_FILE" ]; then
  cat > "$USER_FILE" << 'EOF'
Operator of BabyClaw. Wants concise, independent-media-sourced geopolitics digests.
No corporate MSM, no state-controlled outlets.
Coverage: Iran, Middle East, Turkey, ASEAN, East Asia, Global.
EOF
fi

# ── Workspace files (refresh from read-only mounts on each boot) ─────
cp /home/claw/.openclaw/soul.md "$HOME/SOUL.md" 2>/dev/null || true
cp /home/claw/.openclaw/agents.md "$HOME/AGENTS.md" 2>/dev/null || true
cp /home/claw/.openclaw/workspace/SOURCES.md "$HOME/SOURCES.md" 2>/dev/null || true
cp /home/claw/.openclaw/cron/jobs.json "$HOME/.openclaw/cron/jobs.json" 2>/dev/null || true

# ── Wait for proxy CA cert and copy to a local path with correct perms ─
# The named volume may have restrictive ownership from the proxy container.
# We poll for the cert (proxy generates it on first boot), copy to tmpfs,
# and export NODE_EXTRA_CA_CERTS so Node.js reads it at startup.
PROXY_CA_SRC=/etc/ssl/certs/proxy-ca/mitmproxy-ca.pem
PROXY_CA_DST=/tmp/proxy-ca/mitmproxy-ca.pem

if [ -f "$PROXY_CA_SRC" ]; then
    mkdir -p /tmp/proxy-ca
    cp -f "$PROXY_CA_SRC" "$PROXY_CA_DST"
    chmod 644 "$PROXY_CA_DST"
    export NODE_EXTRA_CA_CERTS="$PROXY_CA_DST"
    echo "[babyclaw] Proxy CA cert copied to $PROXY_CA_DST"
else
    # Poll for up to 30s — proxy may still be generating on first boot
    for i in $(seq 1 30); do
        if [ -f "$PROXY_CA_SRC" ]; then
            mkdir -p /tmp/proxy-ca
            cp -f "$PROXY_CA_SRC" "$PROXY_CA_DST"
            chmod 644 "$PROXY_CA_DST"
            export NODE_EXTRA_CA_CERTS="$PROXY_CA_DST"
            echo "[babyclaw] Proxy CA cert copied to $PROXY_CA_DST (after ${i}s)"
            break
        fi
        sleep 1
    done
    if [ ! -f "$PROXY_CA_DST" ]; then
        echo "[babyclaw] WARNING: Proxy CA cert not found at $PROXY_CA_SRC — HTTPS through proxy may fail"
    fi
fi

# ── Remove bootstrap blocker if it exists ────────────────────────────
rm -f "$HOME/BOOTSTRAP.md" "$HOME/.openclaw/agents/main/agent/BOOTSTRAP.md"

echo "[babyclaw] State dir: $HOME/.openclaw (workspace: $HOME)"
echo "[babyclaw] Gateway starting with deepseek/deepseek-v4-flash..."
echo "[babyclaw] Telegram bot configured, channel notifications enabled"
exec openclaw gateway --bind loopback
