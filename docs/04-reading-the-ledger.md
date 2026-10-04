# Tutorial 4: Reading the ledger

`LEDGER/tokens.log` is the scroll: the replayable account of everything the
crab and its watcher did. One line per event. No prose.

## The grammar

```
<token> <ACTOR> <VERB> <detail>
```

- **token** — unique per event. `tok-` prefix for routine events,
  `wtok-` for watcher decisions. The token is the event's name; everything
  else refers to it.
- **ACTOR** — who acted. The routine's verbs are bare (`TALLY`, `HALT`);
  the watcher's are namespaced (`WATCHER GO`, `WATCHER MANUAL`).
- **VERB** — what happened, past tense or fact. Never intention.
- **detail** — `key=value` pairs. Enough to understand, never the whole story.

## A complete history, in five lines

```
wtok-20261004T002155Z WATCHER NO-GO no inbox — nothing to count
wtok-20261004T002157Z WATCHER GO cursor=0 debts_open=1
tok-20261004T002157Z-6903 TALLY lines=3
wtok-20261004T002157Z WATCHER FULFILLED routine token tok-20261004T002157Z-6903 reported honestly — debt renewed
wtok-20261004T002200Z WATCHER MANUAL debt debt-20261004T002157Z open 72.4h — human must look
```

Read it as a story: the watcher declined once (nothing to do), then ran the
crab, the crab tallied honestly, the watcher fulfilled the debt — and three
days later the renewed debt went stale and a human was called. The whole
moral history of the crab, in five lines.

## What the ledger is not

- **Not the mind.** It records what was done and decided, never *why* in
  full. Inference stays inside the room; the token crosses the boundary.
- **Not editable.** Append-only. If a line is wrong, a later line says so.
  History is corrected by addition, never revision.
- **Not the debt itself.** Debts live in `STATE.json`. The ledger records
  their openings, fulfillments, and escalations — the *events*, not the
  *obligations*.

## Replaying

Because every state change is a token, the crab's history can be recomputed
from the log rather than trusted as prose. `STATE.json` is a cache of what
the ledger says. If they disagree, the ledger wins — it's the older truth.

(The grown-up version of this file is naDir: same idea, with real
double-entry bookkeeping. This log is the seed it grows from.)

Next: [05-debt.md](05-debt.md) — the moral physics.
