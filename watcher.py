#!/usr/bin/env python3
"""watcher.py — the agent. It decides; it does not run the routine itself.

The loop:
    1. Read STATE.json (role, debts, policy, cursor).
    2. Decide: GO (run the routine), NO-GO (don't run, say why), or MANUAL
       (escalate — a human must look).
    3. On GO: invoke the shell (shells/sandbox.sh by default), then read
       RESULTS.json and the new ledger tokens.
    4. Record every decision as a token in LEDGER/tokens.log.
    5. Manage debts: fulfill on honest report, renew standing debts,
       escalate stale ones.

The watcher never runs on silence. Every run ends in an explicit decision.
A watcher that cannot read the crab's state does not guess — it escalates.

Exit codes: 0 = handled (GO or NO-GO), 2 = MANUAL escalation needed.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STALE_DEBT_HOURS = 24


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log_token(ledger, token, kind, detail):
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a") as f:
        f.write(f"{token} WATCHER {kind} {detail}\n")


def parse_age_hours(opened):
    try:
        opened_dt = datetime.strptime(
            opened, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - opened_dt).total_seconds() / 3600
    except (ValueError, TypeError):
        return 0.0


def main():
    crab_dir = None
    sandbox_path = None
    sandbox_timeout = "30"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--crab-dir" and i + 1 < len(args):
            crab_dir = Path(args[i + 1])
            i += 2
        elif args[i] == "--sandbox" and i + 1 < len(args):
            sandbox_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--timeout" and i + 1 < len(args):
            sandbox_timeout = args[i + 1]
            i += 2
        else:
            print(f"Unknown: {args[i]}", file=sys.stderr)
            sys.exit(1)
    if not crab_dir or not crab_dir.is_dir():
        print("Usage: watcher.py --crab-dir <path> [--sandbox <path>] "
              "[--timeout <secs>]", file=sys.stderr)
        sys.exit(1)

    state_path = crab_dir / "STATE.json"
    results_path = crab_dir / "RESULTS.json"
    ledger = crab_dir / "LEDGER" / "tokens.log"
    sandbox = sandbox_path or (Path(__file__).parent / "shells" / "sandbox.sh")

    now = stamp()
    token = f"wtok-{now}"

    # --- 0. If the crab's state is unreadable, do not guess. Escalate. ---
    try:
        state = json.loads(state_path.read_text())
    except FileNotFoundError:
        log_token(ledger, token, "MANUAL", "STATE.json missing — cannot supervise")
        print("MANUAL: STATE.json missing. Cannot supervise what I cannot read.")
        sys.exit(2)
    except json.JSONDecodeError as e:
        log_token(ledger, token, "MANUAL", f"STATE.json corrupt: {e}")
        print(f"MANUAL: STATE.json corrupt ({e}). Escalating, not guessing.")
        sys.exit(2)
    if not isinstance(state, dict):
        log_token(ledger, token, "MANUAL", "STATE.json is not an object")
        print("MANUAL: STATE.json is not an object. Escalating.")
        sys.exit(2)

    debts = state.get("debt", [])
    if not isinstance(debts, list):
        log_token(ledger, token, "MANUAL", "debt field is not a list")
        print("MANUAL: debt field malformed. Escalating.")
        sys.exit(2)

    # --- 1. Check debts: stale open debt -> MANUAL ---
    for debt in debts:
        if not isinstance(debt, dict) or debt.get("status") != "open":
            continue
        opened = debt.get("opened")
        if not opened:
            debt["opened"] = now  # first sighting starts the clock
            continue
        age_h = parse_age_hours(opened)
        if age_h > STALE_DEBT_HOURS:
            log_token(ledger, token, "MANUAL",
                      f"debt {debt.get('id', '?')} open {age_h:.1f}h — human must look")
            state_path.write_text(json.dumps(state, indent=2))
            print(f"MANUAL: debt {debt.get('id', '?')} stale ({age_h:.1f}h). "
                  "Escalating.")
            sys.exit(2)

    # --- 2. Check preconditions: the routine needs an inbox ---
    inbox = crab_dir / "inbox.txt"
    if not inbox.is_file():
        log_token(ledger, token, "NO-GO", "no inbox — nothing to count")
        print("NO-GO: no inbox. Not running the routine.")
        sys.exit(0)

    # --- 3. GO: run the routine inside the sandbox ---
    open_count = sum(1 for d in debts
                     if isinstance(d, dict) and d.get("status") == "open")
    log_token(ledger, token, "GO",
              f"cursor={state.get('cursor', 0)} debts_open={open_count}")
    try:
        proc = subprocess.run(
            [str(sandbox), "--crab-dir", str(crab_dir),
             "--timeout", sandbox_timeout],
            capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        log_token(ledger, token, "MANUAL",
                  "sandbox wrapper itself timed out — supervisor overdue")
        print("MANUAL: sandbox wrapper timed out. Escalating.")
        sys.exit(2)
    except OSError as e:
        log_token(ledger, token, "MANUAL", f"cannot invoke sandbox: {e}")
        print(f"MANUAL: cannot invoke sandbox ({e}). Escalating.")
        sys.exit(2)

    if proc.returncode != 0:
        log_token(ledger, token, "MANUAL",
                  f"sandbox exited {proc.returncode}: "
                  f"{proc.stderr.strip()[:200]}")
        print(f"MANUAL: sandbox failed (exit {proc.returncode}). Escalating.")
        sys.exit(2)

    # --- 4. Read the account, not the mind ---
    try:
        results = json.loads(results_path.read_text())
    except FileNotFoundError:
        log_token(ledger, token, "MANUAL",
                  "RESULTS.json missing after run — routine left no account")
        print("MANUAL: routine left no account (RESULTS.json missing). "
              "Escalating.")
        sys.exit(2)
    except json.JSONDecodeError as e:
        log_token(ledger, token, "MANUAL", f"RESULTS.json corrupt: {e}")
        print(f"MANUAL: RESULTS.json corrupt ({e}). Escalating.")
        sys.exit(2)

    if not isinstance(results, dict) or not results.get("ok"):
        err = results.get("error", "unknown") if isinstance(results, dict) else "unreadable"
        # The routine halted honestly. That's information, not failure.
        # Do not blindly retry: escalate.
        log_token(ledger, token, "MANUAL", f"routine halted: {err}")
        print(f"MANUAL: routine halted honestly ({err}). "
              "Not retrying blind. Human decides.")
        sys.exit(2)

    # --- 5. Honest report: fulfill open debts, renew the standing one ---
    # Re-read STATE.json: the routine advanced cursor/last_run during its run,
    # and this watcher's in-memory copy is now stale. The ledger is the truth;
    # the file on disk is newer than what we loaded.
    try:
        state = json.loads(state_path.read_text())
        debts = state.get("debt", [])
        if not isinstance(debts, list):
            debts = []
    except (json.JSONDecodeError, FileNotFoundError):
        log_token(ledger, token, "MANUAL",
                  "STATE.json changed under us and is now unreadable")
        print("MANUAL: state changed under us and is unreadable. Escalating.")
        sys.exit(2)

    rt = results.get("token", "?")
    for debt in debts:
        if isinstance(debt, dict) and debt.get("status") == "open":
            debt["status"] = "fulfilled"
            debt["fulfilled_by"] = rt
            debt["fulfilled_at"] = now
    # The standing obligation renews: there is always a next tally.
    debts.append({
        "id": f"debt-{now}-{os.getpid()}",
        "obligation": "count what passes through and report honestly",
        "opened": now,
        "owed_to": "the-quilt",
        "status": "open",
    })
    state["debt"] = debts
    state_path.write_text(json.dumps(state, indent=2))
    log_token(ledger, token, "FULFILLED",
              f"routine token {rt} reported honestly — debt renewed")
    print(f"GO complete: routine reported {results}. Debt fulfilled and renewed.")


if __name__ == "__main__":
    main()
