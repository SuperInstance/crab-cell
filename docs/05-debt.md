# Tutorial 5: Debt

Debt is the moral physics of the crab. Everything else — the sandbox, the
watcher, the ledger — exists to serve it.

## The claim

**An assigned role creates an obligation.** The moment a crab has a role
("counter", "greeter"), it owes the world the honest performance of that
role. That owing is a *debt*: a first-class object, not a feeling.

```mermaid
stateDiagram-v2
    [*] --> open: role assigned
    open --> fulfilled: watcher sees honest ok:true
    fulfilled --> open: standing debt renews
    open --> ESCALATE: stale > 24h
    ESCALATE --> open: next link resolves,<br/>next run proceeds
    ESCALATE --> [*]: top link retires the crab
    fulfilled --> [*]: one-shot debt,<br/>no renewal
```

## The lifecycle

A debt in `STATE.json`:

```json
{
  "id": "debt-20261004T002157Z",
  "obligation": "count what passes through and report honestly",
  "opened": "20261004T002157Z",
  "owed_to": "the-quilt",
  "status": "open"
}
```

| Transition | Who | When |
|------------|-----|------|
| open → fulfilled | watcher | The routine reported honestly (`ok: true`). The fulfilling token is recorded. |
| open → (stale) → ESCALATE | watcher | Open longer than 24h. Not auto-closed, not forgotten — passed up the chain. |
| fulfilled → open (renewed) | watcher | Standing obligations renew. There is always a next tally. |

The routine never transitions a debt. It *earns* fulfillment; the watcher
*grants* it.

## Why debt, not tasks

A task list says what *will* be done. A debt says what is *owed*. The
difference matters when things fail: an uncompleted task is rescheduled;
an unfulfilled debt is *escalated*. The 24-hour rule exists because an
obligation nobody checks is not an obligation — it's a wish.

`owed_to` names the creditor. For now it's always "the-quilt" — the
surrounding system the crab serves. When cells talk to cells, debts will
name each other, and the quilt will be woven from what they owe.

## The naDir analogy

- Open debt = open entry in the ledger.
- The watcher's check = servicing it.
- Fulfillment = settled account.
- ESCALATE on stale debt = collections, up the chain.
- Abandonment = default.

This is why the ledger and the debt live side by side: the log records the
servicing, `STATE.json` holds the balance.

## For the human reading this

You don't need to understand the code to understand the crab. Read
`STATE.json`'s `debt` array: that's what it owes. Read the ledger's last
five lines: that's what it did about it. If a debt is open and old, the
watcher has already passed it up — check for the `ESCALATE` token and see
which link it went to. If that link is you, it's your move.

That's the whole system. A crab is something that owes, a watcher is
something that checks, and the ledger is where they meet.
