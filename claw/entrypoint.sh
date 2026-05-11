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

# ── Resolve LiteLLM host IP ───────────────────────────────────────────
HOST_IP="host.docker.internal"
if ! getent hosts host.docker.internal >/dev/null 2>&1; then
  HOST_IP=$(ip route show default 2>/dev/null | awk '{print $3}' | head -1 || echo "172.17.0.1")
  echo "[babyclaw] host.docker.internal not resolvable, using gateway: $HOST_IP"
fi

# ── Generate config on first boot (preserve across restarts) ──────────
if [ ! -f "$CONFIG_FILE" ]; then
  echo "[babyclaw] First boot — generating config..."
  cat > "$CONFIG_FILE" << JSONEOF
{
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "http://$HOST_IP:4000/v1",
        "apiKey": "${LITELLM_API_KEY:-ollama}",
        "api": "openai-completions",
        "request": { "allowPrivateNetwork": true },
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

# ── Remove bootstrap blocker if it exists ────────────────────────────
rm -f "$HOME/BOOTSTRAP.md" "$HOME/.openclaw/agents/main/agent/BOOTSTRAP.md"

echo "[babyclaw] State dir: $HOME/.openclaw (workspace: $HOME)"
echo "[babyclaw] Gateway starting with deepseek/deepseek-v4-flash..."
echo "[babyclaw] Telegram bot configured, channel notifications enabled"
exec openclaw gateway --bind loopback
