# crab

The smallest working piece of the quilt: a supervised agent cell.

A **crab** is a directory containing a **routine** (the bot — it runs, it
doesn't decide) and a **watcher** (`watcher.py` — the agent — it decides,
it doesn't execute). The routine runs inside a shell (`shells/sandbox.sh`:
bwrap + Landlock, timeout-killed — or the instance itself, see
`docs/06-shells.md`). Every run appends a token to the ledger.
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

## The ideas, in one paragraph

An assigned role creates an obligation — a **debt**. The routine owes honest
work; the watcher owes supervision. The routine reports via tokens in an
append-only ledger; the watcher fulfills debts on honest reports and calls
for a human (MANUAL, exit 2) on anything stale or broken. The routine never
decides policy, never closes debts, never leaves its directory — and halts
honestly rather than improvising. Fail to manual, not to automatic.

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
