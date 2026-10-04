# AGENTS.md — for the agent picking up this repo

You are an AI agent. A human pointed you here. This file tells you how to
use this repo — whether you're here to run a crab for a while and throw it
away, or to build on it.

## The 30-second orientation

- A crab is a directory: `STATE.json` (who it is, what it owes), `TASK.md`
  (its orders), `routine.sh` (the bot), `RESULTS.json` (its last account),
  `LEDGER/tokens.log` (its history).
- `watcher.py --crab-dir <path>` supervises it. Exit 0 = handled, exit 2 =
  the decision passes up the chain (ESCALATE).
- `shells/sandbox.sh --crab-dir <path>` runs the routine contained on a
  shared machine. You will rarely call this directly — the watcher does.
  (The default shell is the instance itself: a crab is a machine.)
- Start with `docs/01-your-first-crab.md`. It takes five minutes.

## If you're running a crab transiently

1. `cp -r templates/counter /tmp/<name>` — never run the template in place.
2. Edit `STATE.json`: set the role, write the debt in plain words, name
   `owed_to`.
3. Write `TASK.md` and `routine.sh` per `docs/02-writing-a-routine.md`.
4. Feed it: write `inbox.txt` (or whatever input your TASK.md names).
5. `./watcher.py --crab-dir /tmp/<name>` and read the exit code.
6. When done, delete the directory. The ledger was the point; the crab was
   disposable.

## If you're building on this repo

- **New roles**: copy `templates/counter`, change the role/debt/routine.
  The watcher needs no modification — that's the test that the abstraction
  holds. See `examples/greeter` for the pattern.
- **New watcher policies**: the decision order in `watcher.py` is
  read → debts → preconditions → run → account → manage. Add checks in
  that order; keep the three-state exit contract (GO / NO-GO / ESCALATE).
- **New sandbox backends**: `shells/sandbox.sh` is the minimal shell; the
  default is instance-as-shell; the fleet shell is OpenShell. The contract
  between watcher and shell is just "run this directory's routine,
  contained, with a timeout, and exit non-zero if containment fails."
  See `docs/06-shells.md`.
- **Don't**: put secrets in crab directories (they're inspectable by
  design), let the routine close debts, or let the watcher execute work.
  The responsibility boundary is the architecture.

## Conventions

- Tokens: `<token> <VERB> <detail>`, past tense, `tok-` for routine,
  `wtok-` for watcher. Append-only.
- Debts: open → fulfilled (watcher, on honest report) → renewed (standing
  obligations) or ESCALATE (past due — see the float plan in docs/05-debt.md).
  Two kinds: `standing` (report settles it) and `commitment` (only the real
  world settles it, via `--fulfill`).
- Time: UTC, `YYYYMMDDTHHMMSSZ`.
- The ledger is the source of truth; `STATE.json` is its cache.

## What good looks like

A new crab an agent built in this repo should be reviewable by a human in
two minutes: read `STATE.json`'s debt, read the last five ledger lines,
check the exit code of the last watcher run. If a human can't do that,
the crab is too clever.
