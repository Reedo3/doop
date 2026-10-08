# DOOP — Agent Development Architecture Plan
**Project:** DOOP (Dupe Whoop) — self-built, subscription-free Whoop replacement.
**Status:** PLAN (v1.1, 2026-10-07) — vetted twice, not yet approved for build.
**Companion docs:** `~/workspace/your_files/diy-whoop-replacement-spec/diy-whoop-replacement-spec.pdf` (product spec v1.1, Oct 4 — hardware tracks, parts, firmware, algorithms, validation gates). This plan does NOT re-spec the product; it defines how agents develop it iteratively.

## 1. Starting position (not from zero)

- Product spec v1.1 exists: three hardware tracks (A bench / B nRF52840 / C XIAO ESP32S3), parts lists, firmware architecture, recovery/sleep/strain algorithms, 8 validation gates, 28-day dual-wear protocol.
- Software head start exists: the Calorie Tracker already computes a Whoop-like recovery score from Apple Health (sleep + resting HR). DOOP's scoring engine can be validated against his live Whoop **today**, before any hardware exists.
- He wears Whoop daily → Whoop is the reference instrument and the ground truth for every gate. Subscription stays until the cancel checklist passes.

## 2. Two lanes, one core

DOOP = device + algorithm + app. The lanes de-risk each other:

| Lane | What | Ships value | Depends on |
|---|---|---|---|
| **Software lane** | Portable scoring core (Recovery/Strain/Sleep) running on Apple HealthKit data, surfaced in his training app | Immediately — validates algorithms against his Whoop with zero hardware | HealthKit sync freshness |
| **Hardware lane** | Band (Track B or C) producing the 6 overnight outputs per spec §1 | Weeks 3+ — replaces the sensor source | His hands (build, flash, wear, charge) |

**Architectural law:** both lanes consume a single portable DSP/scoring core (`doop-core`, plain C, per spec §4 non-negotiables). The phone app and the band firmware never reimplement scoring independently — they call the core. Test vectors generated once, run everywhere. This kills the two-lanes-diverge failure mode structurally.

**Honest interface note (vetting fix):** "one core everywhere" really means "one contract everywhere." The C core is the reference implementation; any port (JS/Python for the app side) must pass the shared test-vector suite within tolerances recorded in FROZEN.md. The test vectors are the law; the C code is the reference. This keeps the software lane unblocked while the band is still on the bench.

## 3. The graph (shape of the work)

Deterministic control plane, agentic execution. The outer loop is a phase state machine; only the inner step is agentic. An agent never rewrites the phase machine.

### Phase machine

```
0 SCAFFOLD → 1 DSP_CORE → 2 BENCH → 3 WEARABLE → 4 OVERNIGHT → 5 DUAL_WEAR → 6 DECISION
                  ↑_________| (gate fail = fix in phase, never skip forward)
```

Each phase has: entry state, work nodes, a verification gate (exit test), and crumbs. A phase is done only when its gate passes on the artifact, not on anyone's claim.

| Phase | Work nodes | Gate (exit test) | Metric (scalar) |
|---|---|---|---|
| 0 Scaffold | repo + git, 3-file contract, CI test runner, fixture captures (public PPG datasets first, his own later), **Whoop history export + archive** | Test runner executes, fixtures load, and a deliberately-broken sample fails as expected (proves the suite can catch regressions) | — |
| 1 DSP core | IBI extraction → artifact rejection → RMSSD/RHR/resp-rate; SQI per window; **software-lane backtest: score last 30 days of HealthKit vs his Whoop history** | RMSSD within 10% of chest strap on captures, seated 10 min; backtest recovery-color agreement reported (no gate yet — calibration baseline) | RMSSD MAE % (lower better) |
| 2 Bench (Track A) | firmware PPG task, FIFO/INT, Wi-Fi logging, wrist-taped motion tests | SQI correctly rejects worst lifting sets; clean fingertip IBI | SQI precision on labeled bad windows |
| 3 Wearable (B or C) | port DSP core, BLE GATT, OTA (MCUboot), power-state logging | Full night worn; measured drain within ±20% of track budget | mAh/night (lower better) |
| 4 Overnight | RHR/RMSSD/sleep heuristic/temp delta; app integration; BJJ off-wrist import path (workout import w/ labeled source quality) | Pipeline runs end-to-end 7 consecutive nights with zero manual fixes | Nightly pipeline success rate |
| 5 Dual-wear | 28-day protocol, shell iterations, strain model | All 8 spec §6 gates pass | Gate pass count (higher better) |
| 6 Decision | Cancel checklist (spec §6) | Signed by the data | — |

**WAIT states are explicit.** Phases 2–5 need his hands (flash, wear, charge, order parts). The graph models `WAIT_HUMAN` with a timeout + notify, never a spin loop. Default timeouts: nightly-wear waits resolve next morning; parts-order waits re-notify after 7 days; track-choice waits re-notify after 3 days. Stalled human tasks follow his stalled-task rule: notify once, then the agent does everything else that doesn't need his hands.

### Three-file contract

- **FROZEN.md** (human-owned, agents never touch): the 8 validation gates, recovery/strain/sleep definitions, track choice (B or C), anti-gaming rules (see §5), cancel checklist. Changing a gate needs his explicit word.
- **Mutable surface** (agent-owned): `firmware/`, `doop-core/`, `app/`, `PROGRESS.md`, decision log.
- **Org code** (`AGENTS.md` in repo): roles, workflow, done-definitions, the session-start ritual. The human programs the organization, not the model.

### Parallelism (macro actions, non-interfering)

Non-interfering workers only: DSP core tuning ‖ BLE GATT service ‖ app UI wiring ‖ shell CAD iteration. Never two workers in `doop-core/` at once. The agent may split non-interfering macro tasks autonomously; human approval is needed only for splits touching `doop-core/` or FROZEN-adjacent definitions — otherwise this becomes approval fatigue.

## 4. The harness (survival of the work)

1. **Mistake → structural fix.** Every recurring failure becomes an AGENTS.md line or a check, not a retry. (E.g., if a flash bricks a night of data → black-box recorder rule already in spec; if HealthKit goes stale again → freshness sensor below.)
2. **Verify the artifact, not the report.** Done = the gate's machine-checkable test passes: `make verify` green, drain log re-read from device, dual-wear CSVs re-scored. Never "firmware flashed successfully" without reading back the version string.
3. **Generator ≠ evaluator.** The agent that tunes the DSP never certifies it. Certification = deterministic suite + held-out data (see §5) + his Whoop as reference. For phase gates, a separate verification pass re-reads the artifacts as a skeptic.
4. **Guides + sensors.**
   - Guide: phase checklists in AGENTS.md; each failing check tells the worker how to fix itself.
   - Sensors: HealthKit freshness check (data < 24h old, else flag — his sync went stale Sep 28 once already); battery-drain anomaly (night drain > 130% of budget → investigate before next night); SQI watchdog (score computed on low-SQI windows must say so, per spec).
5. **Leave crumbs.** `PROGRESS.md` (timestamped, what works / what's next / how to run), decision log (why Track B vs C, why each algorithm choice), per-phase run logs. Future sessions start from crumbs, not from chat history.
6. **Session-start ritual.** Read MEMORY.md, PROGRESS.md, `git log --oneline -10`, spec gates. Pick up actual state; never assume.
7. **Preconditions check (honest autonomy):** verifiable outputs ✓ (gates), reversible actions ✓ (git), short feedback cycles ✓ (bench/laptop tests), bounded action space ✓ (phased tasks). Code work can run autonomously; the physical world (ordering, flashing, wearing) is his.

## 5. Metrics, ratchet, anti-gaming

- **One scalar per phase** (§3 table). Keep-if-strictly-better, else roll back via git. No ambiguity about what "better" means inside a phase.
- **Ratchet trap acknowledged:** a strict ratchet can't tolerate temporary regressions (local-minimum trap). Mitigation: time-boxed "spike branches" may regress freely; they merge only on gate improvement. Spikes are recorded in the decision log either way.
- **Anti-gaming (FROZEN):**
  - DSP tuning trains on weeks 1–3 of dual-wear, gates score on held-out week 4. Tuning to the test window is forbidden.
  - Recovery color agreement is scored on mornings, never on a tuned subset of "good nights."
  - Estimated (RPE) sessions are labeled `rpe_estimate`, never silently blended with measured HR (spec Appendix B).
- **Human judgment never delegated:** gate definitions, track choice (B vs C), parts purchases (his money), Week 9 cancel decision, the key insight itself.

## 6. Human gates (explicit, not implied)

1. **Track choice** — B (battery-first, $95–120) or C (cost-first, $60–80). His call; recorded in FROZEN.md.
2. **Parts order** — agent prepares the cart/list; he buys.
3. **Nightly wear & charging** — his body, his habit. Agent analyzes; he wears.
4. **Week 9 decision** — cancel Whoop or extend. Data presents; he decides.

## 7. Roadmap to first value

- **This week:** Phase 0+1 — repo, `doop-core` with RMSSD/RHR on laptop, test vectors from his Apple Health exports. Software lane starts scoring his nights immediately.
- **Weeks 2–3:** Phase 2 bench rig (needs parts order → human gate 2).
- **Weeks 3–4:** Phase 3 wearable port (needs track choice → human gate 1).
- **Weeks 5–8:** Phases 4–5, dual-wear.
- **Week 9+:** Phase 6 decision.

## 8. Red-team notes (vetting record)

First pass 2026-10-07 (fixes applied inline):

1. *"Two lanes diverge."* → Fixed structurally: single `doop-core` law (§2). Any scoring change lands in the core with test vectors, or it doesn't land.
2. *"Tuning to the test set."* → Fixed: held-out week 4 for gate scoring (§5 anti-gaming).
3. *"Agent spins waiting for human."* → Fixed: explicit WAIT_HUMAN states with timeout + notify (§3).
4. *"HealthKit goes stale again."* → Fixed: freshness sensor in harness (§4.4). His sync was 9 days stale on Oct 4; the software lane is worthless on stale data.
5. *"Strict ratchet traps progress."* → Mitigated: spike branches (§5).
6. *"Whoop moves under us."* → Accepted risk: Whoop's algorithms update server-side; the reference can drift mid-validation. Mitigation: log Whoop app version with each dual-wear export; if week-over-week Whoop Recovery mean shifts >5 points with no behavior change logged, flag it in the decision log and re-baseline — don't chase it silently.
7. *"v1 ugliness kills motivation."* → Accepted, bounded: Week 9 decision is time-boxed per spec §7; Whoop stays live so a stall costs evenings, never data continuity.
8. *"Scope creep into medical claims."* → FROZEN rule: DOOP is a personal training tool, not a medical device. No diagnostic language in app copy, ever. (Spec already states this; repeated here because agents love impressive-sounding claims.)

Second pass 2026-10-07 (skeptical re-read — fixes applied):

9. *"Phase 0 gate was trivially true."* → Fixed: gate now proves the suite can fail, not just pass (§3 table).
10. *"Phase 1 had a hidden human dependency."* → Fixed: start fixtures from public PPG datasets (WESAD/TROIKA class); his own chest-strap captures upgrade the fixtures later, not a blocker now.
11. *"One core everywhere was hand-waved."* → Fixed: the honest contract is the test vectors + tolerances in FROZEN.md; C is the reference implementation (§2 note).
12. *"Phase 4 gate was an event, not a test."* → Fixed: 7 consecutive nights, zero manual fixes (§3 table). Also owns the BJJ off-wrist import path now.
13. *"Whoop history export had no owner."* → Fixed: Phase 0 work node — export and archive before anything else (§3 table).
14. *"Approval on every split = bottleneck."* → Fixed: agent splits non-interfering work autonomously; human approval only for `doop-core/` or FROZEN-adjacent splits (§3).
15. *"WAIT timeouts were vibes."* → Fixed: concrete defaults (§3).

---
*Plan version: 1.1 (2026-10-07, vetted twice). Next: his approval → Phase 0 scaffold.*
