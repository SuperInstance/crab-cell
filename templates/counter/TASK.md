# TASK.md — the routine's orders

You are the routine (the bot), not the watcher.

On each run:
1. Read `STATE.json`. Note your open debts.
2. Do the work described here: count the lines in `inbox.txt` (if present) and write the tally.
3. Append one line to `LEDGER/` describing what you did — a token, not an essay.
4. Write the result to `RESULTS.json`.
5. Update `last_run` and `cursor` in `STATE.json`.

Rules:
- You do not decide policy. If `inbox.txt` is missing or unreadable, write the failure to `RESULTS.json` and stop. Do not improvise.
- You do not close debts. Only the watcher closes debts.
- You never touch anything outside this directory. You can't — the sandbox won't let you.
