# crab-cell

**A crab is something that owes, a watcher is something that checks, and the ledger is where they meet.**

An assigned role creates an obligation — a debt. The routine (the bot) does
the work, contained, and reports honestly. The watcher (the agent) decides
whether it runs, fulfills debts on honest reports, and calls for a human
the moment anything goes stale or breaks. Nothing fails silently. Nothing
runs free.

This is not a building block. It's a stewardship loop — the smallest
mechanism by which untrusted work becomes trustworthy over time. The crab
is the unit of selection: what persists, gets judged, and improves. The
watcher is the selection pressure. The ledger is the record.

Concretely: a **crab** is a directory containing a **routine** (the bot —
it runs, it doesn't decide) and a **watcher** (`watcher.py` — the agent —
it decides, it doesn't execute). The routine runs inside a shell
(`shells/sandbox.sh`: bwrap + Landlock, timeout-killed — or the instance
itself, see `docs/06-shells.md`). Every run appends a token to the ledger.
The watcher fulfills debts on honest reports and escalates to a human when
anything is stale, broken, or halted.

The whole loop, in one diagram:

```
watcher decides (GO / NO-GO / MANUAL)
  → sandbox runs routine (GO only)
    → routine appends token, writes RESULTS.json
  → watcher reads the account, fulfills/renews debts, logs its decision
```

## 60-second test

```bash
cp -r templates/counter /tmp/my-crab
printf 'one\ntwo\n' > /tmp/my-crab/inbox.txt
./watcher.py --crab-dir /tmp/my-crab
cat /tmp/my-crab/LEDGER/tokens.log
```

If the ledger shows `WATCHER GO`, a routine token, and `WATCHER FULFILLED` —
it works, and you understand it. That's the go/no-go.

## What's here

| Path | What |
|------|------|
| `watcher.py` | The agent. Decides GO / NO-GO / MANUAL, manages debts. |
| `shells/` | The boundary. `sandbox.sh` (bwrap + Landlock + timeout); see `docs/06-shells.md` for the instance and OpenShell options. |
| `templates/counter/` | The blank crab. Copy it, give it a role and a debt. |
| `examples/` | Three worked crabs: `counter` (minimal), `greeter` (different role, same loop), `breaker` (adversarial — watch the walls hold). |
| `docs/` | Seven tutorials: first crab, writing a routine, being the watcher, reading the ledger, debt, shells, building workflows. |

## What this is, exactly

A stewardship loop — not a task runner with audit logging. The difference:
a task runner asks "did it finish?"; this asks "is it still worthy of
running?" Every cycle, the watcher re-examines the crab: are its debts
fresh, are its preconditions met, did it report honestly last time? GO
means it earned another round. MANUAL means something has to change. The
routine never decides policy, never closes debts, never leaves its
directory — and halts honestly rather than improvising. Fail to manual,
not to automatic.

Over time, the crab accumulates: cursor advances, debts fulfill and renew,
the ledger lengthens, lineage extends. That accumulation is the point.
The loop doesn't just supervise work — it's the mechanism by which a
routine becomes trustworthy: selected round after round, or escalated the
moment it stops deserving trust.

## Provenance

Extracted from `SuperInstance/colony-cell` (2026-06): the bwrap+Landlock
sandbox, the cell-as-directory convention, and lineage-as-state. Decoupled
from its XP/breeding/culling game layer — a colony that evolves is a
different project from cells that owe.

## Status

Prototype. The watcher supervises one crab; there is no inter-cell protocol
yet, no ACP wiring, no redirect-or-rewrite (the watcher halts and escalates
instead). The shell is pluggable — instance, sandbox, or OpenShell
(`docs/06-shells.md`). The default is instance-as-shell: a crab is a machine,
and the machine's edge is the wall.
