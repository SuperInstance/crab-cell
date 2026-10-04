# Example: counter

The minimal crab. It counts lines, owes an honest tally, and halts rather
than improvising.

## Run it

```bash
# from the repo root
cp -r examples/counter/crab /tmp/my-counter
./watcher.py --crab-dir /tmp/my-counter
echo "exit: $?"
cat /tmp/my-counter/LEDGER/tokens.log
```

## What to look for

The ledger after a good run — three voices, one story:

```
wtok-... WATCHER GO cursor=0 debts_open=1
tok-... TALLY lines=5
wtok-... WATCHER FULFILLED routine token tok-... reported honestly — debt renewed
```

The watcher decided. The routine acted. The watcher closed the debt and
renewed the standing obligation. Read `STATE.json` — `debt-001` is fulfilled,
and a new open debt has taken its place. There is always a next tally.

## Try breaking it

```bash
rm /tmp/my-counter/inbox.txt
./watcher.py --crab-dir /tmp/my-counter
echo "exit: $?"
```

`NO-GO`, exit 0. The watcher checks preconditions — it doesn't spend a run
to learn there's nothing to count.
