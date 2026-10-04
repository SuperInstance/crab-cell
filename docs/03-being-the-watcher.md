# Tutorial 3: Being the watcher

The watcher is the agent. It decides; it does not execute. If you are an AI
supervising crabs, this is your job description.

## The decision, every time

```
./watcher.py --crab-dir <path> [--timeout <secs>]
```

Every run ends in exactly one of:

| Decision | Exit | Meaning |
|----------|------|---------|
| GO | 0 | Preconditions met. The routine ran in the shell. Debts managed. |
| NO-GO | 0 | Preconditions not met (no inbox). The routine never ran. |
| ESCALATE | 2 | Cannot decide — passed up the chain. The next link (named in `watcher.escalate_to`: another watcher, an agent, a human) takes it from here. |

There is no fourth state. There is no silence. A watcher that cannot decide
does not guess — passing it up *is* the decision. That is the mechanism of
action: the chain, not the human. The human is the top link, not the only one.

```mermaid
flowchart TD
    Start(["watcher.py --crab-dir"]) --> Read["read STATE.json"]
    Read -->|"missing / corrupt"| E1["<b>ESCALATE</b><br/>exit 2 → human<br/><i>no state, no named<br/>superior — top link</i>"]
    Read --> Debts{"debts fresh?"}
    Debts -->|"open > 24h"| E2["<b>ESCALATE</b><br/>exit 2 → escalate_to<br/><i>collections, up the chain</i>"]
    Debts --> Inbox{"inbox present?"}
    Inbox -->|"no"| NG["<b>NO-GO</b><br/>exit 0<br/><i>nothing to do</i>"]
    Inbox -->|"yes"| GO["<b>GO</b><br/>shell runs routine"]
    GO -->|"exit ≠ 0"| E3["<b>ESCALATE</b><br/>exit 2 → escalate_to<br/><i>never retry blind</i>"]
    GO --> Account{"RESULTS ok?"}
    Account -->|"no / missing"| E4["<b>ESCALATE</b><br/>exit 2 → escalate_to<br/><i>the halt is information;<br/>the next link decides</i>"]
    Account -->|"yes"| Fulfill["fulfill debts<br/>renew standing debt<br/>log FULFILLED"]
    Fulfill --> Done(["exit 0"])
```

## The chain

`STATE.json` names the next link: `watcher.escalate_to`. It can be
`"human"`, or another watcher's crab (`"watcher:crabs/sentinel-02"`), or an
agent, or an algorithm. The ESCALATE token records the handoff:
`wtok-… WATCHER ESCALATE debt … -> watcher:crabs/sentinel-02`.

A watcher watching watchers is the same loop at a larger scope: its inbox
is the child crabs' escalations, its debt is "no escalation goes
unanswered." That's the tower — supervision composing upward, humans at
the top, every layer passing up what it can't decide.

## What the watcher checks, in order

1. **Can I read the crab?** `STATE.json` missing or corrupt → ESCALATE (straight to human — no state, no named superior).
   Never supervise what you cannot read. Never guess.
2. **Are the debts fresh?** Any open debt older than 24h → ESCALATE up the chain.
   An unfulfilled obligation is not the routine's problem to solve alone.
3. **Are preconditions met?** No inbox → NO-GO. Don't spend a run to learn
   there's nothing to do.
4. **Run.** The sandbox executes the routine. A non-zero sandbox exit →
   ESCALATE. Never retry blind.
5. **Read the account.** `RESULTS.json` missing/corrupt → ESCALATE.
   `ok: false` → ESCALATE (the halt is information; the next link decides what's next).
6. **Manage debts.** On `ok: true`: mark open debts fulfilled (recording the
   routine's token as the fulfiller), then renew the standing obligation.

## What the watcher never does

- **Never executes the routine's work itself.** The sandbox boundary is also
  a responsibility boundary. You decide; it does.
- **Never closes a debt on a failed run.** Fulfillment requires an honest
  `ok: true`.
- **Never retries a halt.** If the routine halted honestly, running it again
  without a human's new information is just hoping.
- **Never edits the routine.** If the routine is wrong, that's ESCALATE —
  a human (or a distiller) rewrites it, not the supervisor mid-watch.

## The ledger is your voice too

Every decision is a `WATCHER` token: `GO`, `NO-GO`, `ESCALATE`, `FULFILLED`.
A future reader — human or agent — reconstructs your supervision from these
lines alone. Write them as if someone will.

Next: [04-reading-the-ledger.md](04-reading-the-ledger.md) — the scroll.
