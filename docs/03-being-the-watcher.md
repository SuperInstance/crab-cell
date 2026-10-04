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
    Read --> Debts{"debts overdue?"}
    Debts -->|"overdue: past due"| E2["<b>ESCALATE</b><br/>exit 2 → escalate_to<br/><i>collections, up the chain</i>"]
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

## The four positions

A ternary wire is usually drawn as three values: +1, 0, −1. But a real
wire has a fourth position: *nothing sent yet*. The message not yet on
the wire is itself a position — and with a deadline, it's information.

The watcher's three decisions are the three sent values. The fourth is
what the float plan watches for:

| Wire | Decision | The pilot | What the layer above hears |
|------|----------|-----------|----------------------------|
| +1 | GO | fly | decided — flying |
| 0 | NO-GO | take another loop | decided — not flying, fine |
| −1 | ESCALATE | manual — "I'm in trouble" | **watch this one** |
| — | silence past `due` → ESCALATE | missed check-in | **watch this one** |

NO-GO is zero, not minus. The pilot taking another loop isn't failing —
it's a decision, neutral and complete. Nothing is wrong; there's just
nothing to do yet.

And the last two rows are the same signal. Flipping to manual says "I'm
in trouble" out loud; going overdue *implies* it — the report that was
due never came. Explicit distress and implied distress converge on one
meaning for everyone above: watch this one. The watcher treats them the
same way, because they are the same thing — trouble, spoken or unspoken.

That's why the overdue check has no state of its own. It produces an
ESCALATE. There was never a fourth decision, only a fourth position on
the wire — and the chain already knows what it means.

## What the watcher checks, in order

1. **Can I read the crab?** `STATE.json` missing or corrupt → ESCALATE (straight to human — no state, no named superior).
   Never supervise what you cannot read. Never guess.
2. **Are the debts overdue?** Any open debt past its `due` → ESCALATE up the chain.
   The float plan said when the report was expected; it didn't come.
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
