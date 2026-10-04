#!/usr/bin/env python3
"""watcher.py — the agent. It decides; it does not run the routine itself.

The loop:
    1. Read STATE.json (role, debts, policy, cursor).
    2. Decide: GO (run the routine), NO-GO (don't run, say why), or ESCALATE
       (cannot decide — pass it up the chain of command).
    3. On GO: invoke the shell (shells/sandbox.sh by default), then read
       RESULTS.json and the new ledger tokens.
    4. Record every decision as a token in LEDGER/tokens.log.
    5. Manage debts: fulfill on honest report, renew standing debts,
       escalate stale ones.

The chain of command: a watcher that cannot decide does not guess — it
passes the decision up. The next link can be another watcher, another
agent, another algorithm; at the top, a human. STATE.json names the next
link in `watcher.escalate_to`. Exit 2 means "escalated" — the caller (parent
watcher, cron, human) takes it from here.

The watcher never runs on silence. Every run ends in an explicit decision.
A watcher that cannot read the crab's state does not guess — it escalates.

Exit codes: 0 = handled (GO or NO-GO), 2 = escalated up the chain.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stamp_plus_hours(base_stamp, hours):
    """The float plan: when the report is due, given when the debt opened."""
    try:
        base = datetime.strptime(base_stamp, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
    except (ValueError, TypeError):
        base = datetime.now(timezone.utc)
    due = base + timedelta(hours=hours)
    return due.strftime("%Y%m%dT%H%M%SZ")


def is_overdue(due_stamp, now_stamp):
    """Binary from the next level up: the report arrived, or it didn't."""
    try:
        due = datetime.strptime(due_stamp, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
        now = datetime.strptime(now_stamp, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc)
        return now > due
    except (ValueError, TypeError):
        return False


def log_token(ledger, token, kind, detail):
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a") as f:
        f.write(f"{token} WATCHER {kind} {detail}\n")


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
    # No state means no named superior — these go straight to the human.
    try:
        state = json.loads(state_path.read_text())
    except FileNotFoundError:
        log_token(ledger, token, "ESCALATE",
                  "STATE.json missing — cannot supervise -> human")
        print("ESCALATE: STATE.json missing. Cannot supervise what I cannot "
              "read. Passing up to human.")
        sys.exit(2)
    except json.JSONDecodeError as e:
        log_token(ledger, token, "ESCALATE", f"STATE.json corrupt: {e} -> human")
        print(f"ESCALATE: STATE.json corrupt ({e}). Not guessing. Passing up "
              "to human.")
        sys.exit(2)
    if not isinstance(state, dict):
        log_token(ledger, token, "ESCALATE",
                  "STATE.json is not an object -> human")
        print("ESCALATE: STATE.json is not an object. Passing up to human.")
        sys.exit(2)

    # The next link up the chain. A watcher that cannot decide passes to
    # whoever this names — another watcher, an agent, a human.
    def escalate_to():
        try:
            return state.get("watcher", {}).get("escalate_to", "human")
        except AttributeError:
            return "human"

    def escalate(reason):
        dest = escalate_to()
        log_token(ledger, token, "ESCALATE", f"{reason} -> {dest}")
        print(f"ESCALATE: {reason} Passing up to {dest}.")
        sys.exit(2)

    debts = state.get("debt", [])
    if not isinstance(debts, list):
        escalate("debt field is not a list")

    # --- 1. Check debts: overdue open debt -> escalate up the chain ---
    # The float plan: every debt carries its own due date. It's the
    # expectation of a report that makes silence meaningful — without a
    # deadline, a non-report is just quiet; with one, it's overdue.
    report_every = state.get("watcher", {}).get("report_every_hours", 24)
    try:
        report_every = float(report_every)
    except (ValueError, TypeError):
        report_every = 24
    for debt in debts:
        if not isinstance(debt, dict) or debt.get("status") != "open":
            continue
        opened = debt.get("opened")
        if not opened:
            debt["opened"] = now  # first sighting starts the clock
            opened = now
        if not debt.get("due"):
            # Backfill the float plan for debts opened before due dates.
            debt["due"] = stamp_plus_hours(opened, report_every)
        if is_overdue(debt["due"], now):
            state_path.write_text(json.dumps(state, indent=2))
            escalate(f"debt {debt.get('id', '?')} OVERDUE "
                     f"(due {debt['due']}, no honest report)")

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
        escalate("sandbox wrapper itself timed out — supervisor overdue")
    except OSError as e:
        escalate(f"cannot invoke sandbox: {e}")

    if proc.returncode != 0:
        escalate(f"sandbox exited {proc.returncode}: "
                 f"{proc.stderr.strip()[:200]}")

    # --- 4. Read the account, not the mind ---
    try:
        results = json.loads(results_path.read_text())
    except FileNotFoundError:
        escalate("RESULTS.json missing after run — routine left no account")
    except json.JSONDecodeError as e:
        escalate(f"RESULTS.json corrupt: {e}")

    if not isinstance(results, dict) or not results.get("ok"):
        err = results.get("error", "unknown") if isinstance(results, dict) else "unreadable"
        # The routine halted honestly. That's information, not failure.
        # Do not blindly retry: pass it up.
        escalate(f"routine halted honestly: {err} — not retrying blind")

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
        escalate("STATE.json changed under us and is now unreadable")

    rt = results.get("token", "?")
    for debt in debts:
        if isinstance(debt, dict) and debt.get("status") == "open":
            debt["status"] = "fulfilled"
            debt["fulfilled_by"] = rt
            debt["fulfilled_at"] = now
    # The standing obligation renews: there is always a next tally.
    # The renewed debt files a new float plan — report due by its own deadline.
    report_every = state.get("watcher", {}).get("report_every_hours", 24)
    try:
        report_every = float(report_every)
    except (ValueError, TypeError):
        report_every = 24
    debts.append({
        "id": f"debt-{now}-{os.getpid()}",
        "obligation": "count what passes through and report honestly",
        "opened": now,
        "due": stamp_plus_hours(now, report_every),
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
