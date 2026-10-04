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

Call and response: an ESCALATE is a call — it raises the toggle
(`pending_escalation` in STATE.json). The next link answers with an ACK
("I heard that"), written as a ledger token. The mere image of the ACK in
the ledger is what toggles the switch back: the next run sees it, stands
the escalation down, and returns to normal. No separate flags — the tokens
are the state machine. Record an ack with:
    watcher.py --crab-dir <path> --ack <escalation-token> [--by <who>]
If the ack itself never arrives (silence past `watcher.ack_every_hours`),
the escalation passes to the next link after the unresponsive one.

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


def chain(state):
    """The chain of command as a list. escalate_to may name one link or many."""
    raw = state.get("watcher", {}).get("escalate_to", "human")
    if isinstance(raw, str):
        return [raw]
    return list(raw) or ["human"]


def next_link(state, after):
    """The link after `after`. Silence from a link passes over it."""
    c = chain(state)
    if after in c:
        i = c.index(after)
        return c[i + 1] if i + 1 < len(c) else "human"
    return c[0]


def ack_every_hours(state):
    try:
        return float(state.get("watcher", {}).get("ack_every_hours", 1))
    except (ValueError, TypeError):
        return 1.0


def ledger_has_ack(ledger, escalation_token):
    """The mirror image: has the next link's 'I heard that' arrived?"""
    try:
        lines = ledger.read_text().splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        parts = line.split(" ", 3)
        if (len(parts) >= 4 and parts[1] == "WATCHER" and parts[2] == "ACK"
                and parts[3].split(" ", 1)[0] == escalation_token):
            return line
    return None


def main():
    crab_dir = None
    sandbox_path = None
    sandbox_timeout = "30"
    ack_token = None
    ack_by = "human"
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
        elif args[i] == "--ack" and i + 1 < len(args):
            ack_token = args[i + 1]
            i += 2
        elif args[i] == "--by" and i + 1 < len(args):
            ack_by = args[i + 1]
            i += 2
        else:
            print(f"Unknown: {args[i]}", file=sys.stderr)
            sys.exit(1)
    if not crab_dir or not crab_dir.is_dir():
        print("Usage: watcher.py --crab-dir <path> [--sandbox <path>] "
              "[--timeout <secs>] [--ack <escalation-token> [--by <who>]]",
              file=sys.stderr)
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

    # --- 0b. Recording an ack: "I heard that." ---
    # This only writes the token. The toggle flips on the next run, when the
    # watcher sees the image in the ledger. The image is the switch.
    if ack_token:
        pending = state.get("pending_escalation")
        if not pending or pending.get("token") != ack_token:
            print(f"No pending escalation {ack_token} — nothing to ack.",
                  file=sys.stderr)
            sys.exit(1)
        atoken = f"wtok-{now}"
        log_token(ledger, atoken, "ACK",
                  f"{ack_token} heard by {ack_by} — standing by")
        print(f"ACK recorded: {ack_token} heard by {ack_by}. "
              "The next run stands the escalation down.")
        sys.exit(0)

    # --- 0c. The pending escalation: call and response. ---
    pending = state.get("pending_escalation")
    if pending:
        ptoken = pending.get("token", "?")
        pdest = pending.get("dest", "human")
        ack_line = ledger_has_ack(ledger, ptoken)
        if ack_line:
            # Response received. Toggle back: stand the escalation down.
            # The covered debts move to the next link — no more nagging.
            acked_by = ack_line.split("heard by ", 1)[1].split(" ", 1)[0] \
                if "heard by " in ack_line else pdest
            covered = set(pending.get("debts", []))
            for debt in state.get("debt", []):
                if isinstance(debt, dict) and debt.get("id") in covered \
                        and debt.get("status") == "open":
                    debt["status"] = "escalated"
                    debt["escalated_to"] = pdest
                    debt["escalated_at"] = now
            state["pending_escalation"] = None
            state_path.write_text(json.dumps(state, indent=2))
            log_token(ledger, token, "ACKNOWLEDGED",
                      f"{ptoken} heard by {acked_by} — escalation stood down")
            print(f"ACKNOWLEDGED: {pdest} heard {ptoken}. "
                  "Back to normal — no longer escalating.")
        elif is_overdue(pending.get("ack_due", now), now):
            # The ack itself went silent past its deadline — the fourth
            # position on the ack wire. Pass over the unresponsive link.
            ndest = next_link(state, pdest)
            ntoken = f"wtok-{now}"
            state["pending_escalation"] = {
                "token": ntoken,
                "reason": f"no ack from {pdest} by {pending.get('ack_due')}",
                "dest": ndest,
                "raised_at": now,
                "ack_due": stamp_plus_hours(now, ack_every_hours(state)),
                "debts": pending.get("debts", []),
            }
            state_path.write_text(json.dumps(state, indent=2))
            log_token(ledger, ntoken, "ESCALATE",
                      f"no ack from {pdest} by {pending.get('ack_due')} "
                      f"— passing over -> {ndest}")
            print(f"ESCALATE: {pdest} never acked. Passing over to {ndest}.")
            sys.exit(2)
        else:
            # Call already on the wire. No need to raise it again.
            log_token(ledger, token, "ESCALATE-PENDING",
                      f"{ptoken} awaiting ack from {pdest} "
                      f"(due {pending.get('ack_due')})")
            print(f"ESCALATE-PENDING: {ptoken} already raised, awaiting ack "
                  f"from {pdest}. Not raising again.")
            sys.exit(2)

    # The next link up the chain. A watcher that cannot decide passes to
    # whoever this names — another watcher, an agent, a human.
    def escalate_to():
        return chain(state)[0]

    def escalate(reason):
        dest = escalate_to()
        # The call raises the toggle. The ack will lower it.
        open_ids = [d.get("id") for d in state.get("debt", [])
                    if isinstance(d, dict) and d.get("status") == "open"]
        state["pending_escalation"] = {
            "token": token,
            "reason": reason,
            "dest": dest,
            "raised_at": now,
            "ack_due": stamp_plus_hours(now, ack_every_hours(state)),
            "debts": open_ids,
        }
        state_path.write_text(json.dumps(state, indent=2))
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
            # Escalated debts belong to the next link now — no nagging.
            # Fulfilled/retired debts are history.
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
        # An honest report settles every outstanding obligation — open or
        # escalated. The next link holding it doesn't stop the truth.
        if isinstance(debt, dict) and debt.get("status") in ("open",
                                                             "escalated"):
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
