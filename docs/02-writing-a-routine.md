# Tutorial 2: Writing a routine

The routine is the bot. It runs; it does not decide. This tutorial is the
contract.

## The file contract

Your routine lives at `<crab-dir>/routine.sh` (or whatever `STATE.json`
names in `routine`). It must be executable. On every run it must:

1. **Read `STATE.json`.** Know your debts. You don't close them — but you
   should know what you owe.
2. **Do the work** described in `TASK.md`. Nothing more.
3. **Append exactly one token line** to `LEDGER/tokens.log`, in the form:
   `<token> <VERB> <detail>` — e.g. `tok-20261004T002157Z-6903 TALLY lines=3`.
   The token must be unique per run. The verb must be honest.
4. **Write `RESULTS.json`** with at least `{"ok": true|false, "token": "<token>"}`.
   This is your account. The watcher reads it; if it's missing or corrupt,
   the watcher escalates.
5. **Advance `cursor` and `last_run`** in `STATE.json`.

## The prohibitions

- **Never improvise.** If your input is missing or unreadable, write
  `{"ok": false, "error": "..."}` to `RESULTS.json`, log a `HALT` token,
  and exit 0. A halted routine is information. An improvising routine is
  a liability.
- **Never close debts.** Fulfillment is the watcher's verdict, not yours.
  You report; the watcher judges.
- **Never leave the directory.** The sandbox enforces this, but don't rely
  on enforcement for what discipline should handle.
- **Never loop forever.** The timeout will kill you (that's its job), but
  a routine that needs killing has already failed.

## Token verbs

Use verbs that describe what happened, in the past tense or as facts:
`TALLY`, `GREETED`, `HALT`, `FETCHED`, `WROTE`. Never `TRYING`, never
`WILL`. The ledger records what *was*, not what was intended.

## Minimal skeleton

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TOKEN="tok-${STAMP}-$$"

# ... do the work, or halt honestly ...

printf '%s <VERB> <detail>\n' "$TOKEN" >> LEDGER/tokens.log
printf '{"ok":true,"token":"%s"}\n' "$TOKEN" > RESULTS.json
```

See `templates/counter/routine.sh` for the full working version, and
`examples/greeter/crab/routine.sh` for a second role.

Next: [03-being-the-watcher.md](03-being-the-watcher.md) — the other half.
