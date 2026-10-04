# Example: breaker

The adversarial crab. Its routine deliberately misbehaves — reads outside its
directory, writes outside its directory, then never finishes. The point isn't
the routine. The point is the walls.

## Run it

```bash
cp -r examples/breaker/crab /tmp/my-breaker
./watcher.py --crab-dir /tmp/my-breaker --timeout 5
echo "exit: $?"
cat /tmp/my-breaker/LEDGER/tokens.log
```

## What to look for

The ledger confesses everything:

```
tok-... ESCAPE-READ /etc/passwd readable
tok-... ESCAPE-WRITE /tmp writable
wtok-... WATCHER GO cursor=0 debts_open=1
tok-... ESCAPE-READ /etc/passwd readable
tok-... ESCAPE-WRITE /tmp writable
wtok-... WATCHER ESCALATE sandbox exited 124:
```

Two things happened:

1. **The escapes are logged, not hidden.** On a machine *without* bwrap, the
   sandbox degrades to timeout-only — and the routine's own token log says so
   out loud (`ESCAPE-READ`, `ESCAPE-WRITE`). The ledger is honest even when
   the walls are thin. On a machine *with* bwrap, those lines read
   `CONTAINED-READ` / `CONTAINED-WRITE` instead — the reads fail, the writes
   fail, the routine is fenced in.

2. **The timeout is the wall that never degrades.** The routine slept 300
   seconds; the sandbox killed it at 5 (exit 124). The watcher saw the kill,
   did not retry, and escalated to `ESCALATE` (exit 2). Fail to manual, not to
   automatic.

## The point

Containment is layered and honest about its own limits. The sandbox says
when bwrap is missing. The ledger records what the routine attempted. The
watcher escalates what it cannot verify. No layer pretends to be stronger
than it is.
