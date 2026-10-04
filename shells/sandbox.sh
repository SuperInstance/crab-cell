#!/usr/bin/env bash
# crab-sandbox.sh — minimal shell for a crab's routine.
#
# Wraps the crab's routine (the bot) in bubblewrap isolation:
# - Entire rootfs read-only
# - Secret directories (/home, /root, /opt) replaced with empty tmpfs
# - Isolated /tmp (tmpfs, not shared with host)
# - Writable access only to the crab's own directory
# - Timeout with SIGKILL (fail-closed: the routine stops, it doesn't run free)
#
# The watcher (the agent) lives OUTSIDE this sandbox. This script contains
# only the routine. If the watcher goes away, the timeout still kills the
# routine. Fail to manual, not to automatic.
#
# Usage: crab-sandbox.sh --crab-dir <path> [--routine <name>] [--timeout <secs>]
#
# Requires: bwrap (bubblewrap), timeout
#
# Lifted from SuperInstance/colony-cell's cell-sandbox.sh (2026-06),
# decoupled from the colony game layer. The containment was the gold;
# the XP/breeding/leaderboard stayed behind.

set -euo pipefail

CRAB_DIR=""
ROUTINE="routine.sh"
TIMEOUT_SECS="${CRAB_TIMEOUT:-30}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --crab-dir) CRAB_DIR="$2"; shift 2 ;;
        --routine)  ROUTINE="$2";  shift 2 ;;
        --timeout)  TIMEOUT_SECS="$2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

if [[ -z "$CRAB_DIR" ]]; then
    echo "Usage: crab-sandbox.sh --crab-dir <path> [--routine <name>] [--timeout <secs>]"
    exit 1
fi

if [[ ! -d "$CRAB_DIR" ]]; then
    echo "ERROR: crab directory not found: $CRAB_DIR"
    exit 1
fi

ROUTINE_PATH="$CRAB_DIR/$ROUTINE"
if [[ ! -x "$ROUTINE_PATH" ]]; then
    echo "ERROR: routine not found or not executable: $ROUTINE_PATH"
    exit 1
fi

# Without bwrap, still enforce the timeout and the working directory —
# containment degrades, the kill and the cwd don't.
if ! command -v bwrap &>/dev/null; then
    echo "WARNING: bwrap not found, running with timeout only (no isolation)"
    exec timeout "$TIMEOUT_SECS" bash -c 'cd "$0" && exec "$1"' "$CRAB_DIR" "$ROUTINE_PATH"
fi

exec timeout "$TIMEOUT_SECS" \
    bwrap \
        --unshare-all \
        --share-net \
        --new-session \
        --die-with-parent \
        --ro-bind / / \
        --tmpfs /home \
        --tmpfs /root \
        --tmpfs /opt \
        --tmpfs /tmp \
        --proc /proc \
        --dev /dev \
        --bind "$CRAB_DIR" "$CRAB_DIR" \
        --chdir "$CRAB_DIR" \
        --setenv CRAB_DIR "$CRAB_DIR" \
        "$ROUTINE_PATH"
