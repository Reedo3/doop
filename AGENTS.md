# DOOP — Org Code (agent operating instructions)

This file programs the organization, not the model. Agents working in this repo follow it.

## Roles

- **Builder** (agent): implements one phase's work nodes, commits, runs `make verify`.
- **Verifier** (separate pass, never the same turn as the builder): re-reads the artifacts as a skeptic against FROZEN.md tolerances/gates. A builder never certifies its own work.
- **Human** (Reedom): owns FROZEN.md, track choice, parts purchases, wearing/charging, Week-9 cancel decision, decomposition of `doop-core/`-touching work.

## Session-start ritual (every session, before acting)

1. Read `PROGRESS.md` (tail), `git log --oneline -10`, `decision-log.md` (tail).
2. Read the current phase's gate in `PLAN.md` §3.
3. Never touch `FROZEN.md`. Never assume state — pick it up from crumbs.

## Phase machine

```
0 SCAFFOLD → 1 DSP_CORE → 1b BACKTEST → 2 BENCH → 3 WEARABLE → 4 OVERNIGHT → 5 DUAL_WEAR → 6 DECISION
```
Gate fail = fix inside the phase. Never skip forward. Current phase is in `PROGRESS.md`.

## Done definitions

- **Phase done**: gate's machine-checkable test passes on the artifact. `make verify` green where applicable; drain logs re-read from device; dual-wear CSVs re-scored. Claims don't count.
- **Commit**: one work node per commit, message names the node + gate status.
- **Crumbs**: every session appends to `PROGRESS.md`: date, what works, what's next, how to run it.

## Guides + sensors (harness)

- Failing checks must say how to fix themselves (remediation in the check message).
- Sensors: HealthKit freshness (<24h or flag), battery-drain anomaly (>130% of budget → investigate before next night), SQI watchdog (low-SQI windows must be labeled in any score).
- `WAIT_HUMAN` states: nightly-wear waits resolve next morning; parts-order re-notify after 7 days; track-choice re-notify after 3 days. Timeout → notify once → do everything else that doesn't need hands (stalled-task rule).

## Parallelism

Non-interfering macro tasks may be split autonomously (DSP tuning ‖ BLE GATT ‖ app UI ‖ shell CAD). Never two workers in `doop-core/` at once. Splits touching `doop-core/` or FROZEN-adjacent definitions need human approval first.

## Mistake → structural fix log

Every recurring failure gets a line here or a new check — never just a retry.

- 2026-10-07: (init) HealthKit went 9 days stale once (Oct 4) → freshness sensor added.
- 2026-10-07: (init) "New project" claim without memory/workspace grep → session-start ritual requires the grep.
- 2026-10-07: STANDING RULE (his words: "in the second brain log the progress as we go") → after every substantive DOOP session, append to the live-vault build log `20-projects/doop/progress-log.md` (staged at `~/workspace/second-brain/pending/doop-progress-log.md` when his Mac is offline; sync on reconnect). He writes the build post from these notes.
