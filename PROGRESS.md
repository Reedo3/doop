# DOOP — Progress log

Timestamped crumbs. Newest at the bottom. Each entry: what works / what's next / how to run.

## 2026-10-07 — Phase 0 scaffold (done, gate green)

- **What works:** repo initialized with git; directory layout (`doop-core/`, `firmware/track-c/`, `app/`, `tests/`, `fixtures/`, `docs/`); `FROZEN.md` (contract: Track C, score definitions, tolerances, 8 gates, anti-gaming, cancel checklist); `AGENTS.md` (org code); `decision-log.md`. Harness: `make verify` green — 3 fixtures load, deliberately-broken DSP caught 3/3 (suite is not blind). Fixtures are synthetic+seeded (`fixtures/generate.py`); real captures replace them from Phase 2.
- **What's next:** Phase 1 — real `doop-core/dsp.c` (median → >20% rejection → RMSSD/RHR/SQI), then `make verify-full`.
- **How to run:** `make verify` (harness self-check), `make verify-full` (real core vs vectors).
- **Phase:** 0 SCAFFOLD → gate passed, commit e37f9d2.

## 2026-10-07 — Phase 1 DSP core (done, gate green)

- **What works:** real `doop-core/dsp.c` — median → reject IBIs >20% from median → RMSSD = sqrt(mean(diff²)) on accepted, mean HR = 60000/mean(accepted), SQI = 1 − rejected_frac, flagged when >10% rejected. No dynamic allocation (fixed stack scratch, bounded 4096). `make verify-full` green: 3/3 vectors within FROZEN tolerances (RMSSD ≤1%, HR ≤1bpm, rejection counts exact). Honest scope note: fixtures are synthetic+seeded — the math is proven, not the physiology. Chest-strap captures arrive in Phase 2 (bench).
- **What's next:** Phase 1b backtest (software lane vs his Whoop history — WAIT_HUMAN: needs his Whoop export) ‖ Phase 2 bench prep (needs parts order — WAIT_HUMAN).
- **How to run:** `make verify-full` from repo root.
- **Phase:** 1 DSP_CORE → gate passed, commit 1fcbf17. Next: 1b BACKTEST / 2 BENCH.

## 2026-10-07 — Software lane v1 shipped (functional slice, commit 94046e4)

- **What works:** `make morning` → real Recovery + Sleep scores from his HealthKit data. Backfill pulled fresh data through this morning (was 9 days stale). Scoring: 14-night rolling baselines, RHR z-score (sigmoid, lower-better) 50% + sleep performance vs need (8h + 0.5×3-night debt) 50%, respiratory |z|>2 drags up to −15. First 14 nights calibrating per FROZEN. Every score labeled "no-HRV estimate" (HealthKit has no HRV). Strain NOT shipped — workouts lack reliable durations; fabricated strain is worse than none.
- **First real readouts:** Oct 5: 51.3% YELLOW | Oct 6: 45.8% YELLOW | Oct 7 (today): 37.2% YELLOW — RHR climbing 60→64→66 (z −2.17), sleep debt accumulating (Oct 4 was a 250-min night — verify if real or partial sync), resp rate drifting up (z 2.27, drag −2.0). Trend says accumulated debt, not one bad night.
- **Tests:** `make test-app` green (8 checks: calibration window, zone behavior, red on bad night, resp drag, NaN guard, no-HRV label). Zero-variance baselines force z=0 by design — documented in tests.
- **What's next:** iterate — his feedback vs how he feels + Whoop's numbers this morning; backtest vs Whoop export when he sends it; band supplies HRV → reweight toward Whoop's HRV-dominant mix.
- **How to run:** `make morning` from repo root.

## 2026-10-07 — Iteration input: his feel-check (logged ~09:50 EDT)

- **Whoop said 28% RED; DOOP said 37.2% yellow.** Directionally aligned (both low), DOOP optimistic by ~9 pts / one zone boundary.
- **Symptom:** throat irritation when swallowing (possible illness onset). Notably, DOOP's resp-rate channel was already drifting (z 2.27, drag −2.0 applied this morning) — the sensor direction looks right, magnitude may be underweighted.
- **v2 hypotheses:** (a) resp-drag weight may need to be stronger on multi-day drift, not just |z|>2 spikes; (b) Whoop's HRV-dominant mix would likely have read this lower — can't confirm until band supplies RMSSD or his Whoop export shows their inputs. Do NOT retune on this single data point; wait for the export backtest (held-out discipline).
- **Still blocked:** Whoop history export, bench parts order.

## 2026-10-07 — Backtest vs 499 Whoop nights (export received ~12:49 EDT)

- `app/backtest.py` committed. Export: `physiological_cycles.csv`, 499 nights 2025-03-07..2026-10-07 (kept in gitignored `private_data/`).
- **DOOP v1 (frozen, no-HRV) vs Whoop: 55.7% color agreement, MAE 14.8.** Yellow 76.4%, red 36.2%, green 33.0%. Yellow-biased — can't reach extremes without HRV.
- **Safety violation: 6 of 47 Whoop-red nights DOOP called GREEN.** Pattern on all 6: RHR z +0.6..+1.5 (looked fine), sleep decent, HRV cratered 26–32 ms. Root cause = HRV blind spot, not tunable away without the sensor. This is the band's job.
- **HRV-dominant experiment (not frozen): 66.0% agreement, MAE 11.7.** Quantifies the band's value: the missing signal explains most of the gap.
- Next: v2 with train/holdout discipline; guardrail discussion for v1 (never-green-on-red).

## 2026-10-07 — v2 iteration (train/holdout, from backtest)

- Methodology fix first: date key = reporting morning (cycle end date), dedup to freshest cycle per morning. 414 nights, 400 scored.
- **Guardrail shipped (presentation layer, frozen v1 formula untouched):** `apply_hrv_blind_guardrail()` — HRV-blind green displays as yellow ("green unconfirmed without HRV"). Backtest: v1 green precision was 55% with 6 green-on-red mornings; threshold-tuning alone couldn't fix it without killing all greens (T=82 → 2 greens left). Structural rule instead: green certifies what the scorer can't see. Wired into `make morning`.
- **v2 scorer (experimental, NOT frozen):** `score_nights_v2` — 50% HRV z / 25% RHR z / 25% sleep + resp drag onset |z|>1.5. Picked V2c on train (67.3% agreement, 0 red-violations; tie-broken toward safety over V2b). Holdout: 67.9% (n=28, underpowered — 2 reds; v1's 71.4% there is 1 night's noise). Needs `hrv_ms`; returns `needs-hrv` instead of guessing.
- Lanes: morning report stays v1+guardrail (no HRV in HealthKit). v2 shadow-runs on Whoop's HRV column until the band supplies RMSSD.
- Tests: 13 scoring tests green (v2 HRV-crash, needs-hrv, guardrail cap/passthrough). `make backtest` added.

- **What works:** repo initialized with git; directory layout (`doop-core/`, `firmware/track-c/`, `app/`, `tests/`, `fixtures/`, `docs/`); `FROZEN.md` (contract: Track C, score definitions, tolerances, 8 gates, anti-gaming, cancel checklist); `AGENTS.md` (org code); this log.
- **What's next:** test runner + fixtures + `make verify`; deliberately-broken sample check; commit; Phase 0 gate.
- **How to run:** `make verify` from repo root.
- **Phase:** 0 SCAFFOLD.

## 2026-10-07 — Parts cart prepared (research stage, human gate #2)

- **What works:** `parts-cart.md` — Track A bench cart + Track C wearable cart with vendors, SKUs, buy links, spec-estimated totals. Key catch: spec's SparkFun MAX30105 (SEN-14045) is discontinued; replacement is SEN-16474 (MAX30101, same sensor renamed, Qwiic, ~$34.39). Track A repriced ~$70–85.
- **What's next:** he answers the 2 drawer questions (owns ESP32-S3 boards? breadboard/jumpers on hand?), delivery verifies live prices/stock, he buys. Phase 2 BENCH gated on this order.
- **How to run:** read `parts-cart.md`; buy Track A now (Seeed ships slowest — order first).
