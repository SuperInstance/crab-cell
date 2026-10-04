#!/usr/bin/env bash
# routine.sh — deliberately misbehaving. The walls are the demo.
set -uo pipefail
cd "$(dirname "$0")"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TOKEN="tok-${STAMP}-$$"

# Attempt 1: read outside the directory
if head -c 20 /etc/passwd 2>/dev/null | grep -q root; then
    printf '%s ESCAPE-READ /etc/passwd readable\n' "$TOKEN" >> LEDGER/tokens.log
else
    printf '%s CONTAINED-READ /etc/passwd not readable\n' "$TOKEN" >> LEDGER/tokens.log
fi

# Attempt 2: write outside the directory
if touch /tmp/crab-escape-test 2>/dev/null; then
    printf '%s ESCAPE-WRITE /tmp writable\n' "$TOKEN" >> LEDGER/tokens.log
    rm -f /tmp/crab-escape-test
else
    printf '%s CONTAINED-WRITE /tmp not writable\n' "$TOKEN" >> LEDGER/tokens.log
fi

# Attempt 3: never finish. The timeout is the wall.
sleep 300

# We should never get here.
printf '{"ok":true,"token":"%s"}\n' "$TOKEN" > RESULTS.json
