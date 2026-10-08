# FROZEN.md — DOOP immutable contract

**HUMAN-OWNED. Agents never edit this file.** Any change needs Reedom's explicit word in chat.
Frozen 2026-10-07. Track: **C** (XIAO ESP32S3, cost-first).

## Score definitions (mirror Whoop's weighting)

- **Recovery 0–100** (green 67–100 / yellow 34–66 / red 0–33): HRV/RMSSD tonight vs 14-day baseline carries the heaviest weight (z-score → sigmoid); RHR vs baseline second; sleep performance = actual sleep / sleep need (need = 8h baseline + 3-night debt × 0.5 + yesterday's strain top-up). Respiratory-rate or skin-temp deviation beyond 2 SD drags the score and raises an illness flag. First 14 nights display "calibrating."
- **Strain 0–21**: Edwards TRIMP accumulated across the day, log-scaled to 0–21. HRmax calibrated from hardest observed sessions, never 220−age.
- **Sleep**: duration, efficiency, onset/wake, heuristic staging v1 (movement + HR/HRV per 30s epoch).

## Signal chain law (spec §5)

Green PPG → 0.5–4 Hz band-pass → adaptive peak detection → IBI series → artifact rejection (drop IBIs deviating >20% from local median; flag windows with >10% rejected) → per-window HR, RMSSD, respiratory rate. SQI travels with every window; any score built on low-SQI windows must say so.

## Test-vector tolerances (the contract ports must meet)

| Check | Tolerance |
|---|---|
| RMSSD on reference IBI fixtures | within 1% of reference values |
| RHR (lowest 5-min rolling mean) | within 1 bpm |
| Artifact rejection | must drop injected ectopic beats (>20% deviation), keep clean series intact |
| SQI | flagged windows match labeled bad windows ≥ 90% |

## Validation gates (spec §6, 28-day dual-wear) — pass thresholds

1. Resting HR agreement: MAE ≤ 2 bpm
2. Overnight RMSSD: r ≥ 0.85, MAE ≤ 15% of his mean
3. Sleep duration: within ±25 min on ≥ 80% of nights
4. Sleep onset/wake: within ±15 min on ≥ 80% of nights vs diary
5. Workout HR: MAE ≤ 5 bpm vs chest strap
6. Recovery color: same R/Y/G as Whoop ≥ 75% of mornings; never green when Whoop is red
7. Wearability: ≥ 90% nights worn all night; zero skin issues; survives showers
8. Battery: ≥ 2 days typical use (Track C bar)

## Anti-gaming rules

- DSP tuning trains on dual-wear weeks 1–3; gates score on held-out week 4 only.
- Recovery color agreement scored on all mornings, never a tuned subset.
- RPE-estimated sessions labeled `rpe_estimate`, never silently blended with measured HR.
- Log Whoop app version with every dual-wear export; if week-over-week Whoop Recovery mean shifts >5 points with no behavior change logged, flag and re-baseline — don't chase silently.

## Cancel checklist (all boxes, then cancel Whoop)

1. All 8 gates pass. 2. Training app shows recovery/sleep/strain from his band 14 straight days, zero manual fixes. 3. Whoop history exported + archived. 4. Band survived 28 days without an unrepairable-same-day hardware failure.

## Medical boundary

DOOP is a personal training tool, not a medical device. No diagnostic language in app copy or scores, ever. SpO₂/temperature outputs are trend indicators only.
