# TASK.md — the routine's orders

You are the routine (the bot), not the watcher.

On each run:
1. Read `STATE.json`. Note your open debts.
2. Read the names in `inbox.txt`, one per line. Write one greeting per name
   into `RESULTS.json` under the key `greetings`.
3. Append one token line to `LEDGER/tokens.log`.
4. Update `last_run` and `cursor` in `STATE.json`.

Rules:
- Empty lines are skipped, not greeted. A blank line is not a person.
- If `inbox.txt` is missing, write the failure to `RESULTS.json` and stop.
  Do not invent guests.
- You do not close debts. Only the watcher closes debts.
- You never touch anything outside this directory.
