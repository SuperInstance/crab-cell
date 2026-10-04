# Example: greeter

A crab with a different role and a different debt. Same watcher, same sandbox,
same loop — the *role* is what changes.

The greeter's debt: "greet everyone who arrives, by name, and mean it."
Its routine reads names from `inbox.txt` (one per line), skips blanks
(a blank line is not a person), and writes greetings to `RESULTS.json`.

## Run it

```bash
cp -r examples/greeter/crab /tmp/my-greeter
./watcher.py --crab-dir /tmp/my-greeter
echo "exit: $?"
cat /tmp/my-greeter/RESULTS.json
cat /tmp/my-greeter/LEDGER/tokens.log
```

## What to look for

- The routine greeted Ada, Grace, and Alan — and skipped the blank line.
- The debt is fulfilled by the routine's token and renewed, exactly like
  the counter. The watcher doesn't care what the role *is*; it cares that
  the debt was *honored*.

## The point

Roles are interchangeable. Debts are structural. If you can write a new
`STATE.json` (role + debt) and a new `routine.sh` (the work + the token),
you have a new crab — and the watcher supervises it without modification.
