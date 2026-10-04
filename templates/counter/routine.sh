#!/usr/bin/env bash
# routine.sh — the bot. It runs; it does not decide.
set -euo pipefail
cd "$(dirname "$0")"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TOKEN="tok-${STAMP}-$$"

if [[ ! -f inbox.txt ]]; then
    printf '{"ok":false,"error":"inbox.txt missing — halting, not improvising","token":"%s"}\n' "$TOKEN" > RESULTS.json
    printf '%s HALT no-inbox\n' "$TOKEN" >> LEDGER/tokens.log
    exit 0
fi

COUNT=$(wc -l < inbox.txt | tr -d ' ')
printf '{"ok":true,"lines":%s,"token":"%s"}\n' "$COUNT" "$TOKEN" > RESULTS.json
printf '%s TALLY lines=%s\n' "$TOKEN" "$COUNT" >> LEDGER/tokens.log

# advance the cursor
python3 - "$STAMP" <<'EOF'
import json, sys
stamp = sys.argv[1]
s = json.load(open('STATE.json'))
s['last_run'] = stamp
s['cursor'] = s.get('cursor', 0) + 1
json.dump(s, open('STATE.json', 'w'), indent=2)
EOF
