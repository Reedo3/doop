#!/usr/bin/env python3
"""Scoring unit tests — synthetic nights, FROZEN.md behavior contract."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doop_score import (score_nights, score_nights_v2,
                          apply_hrv_blind_guardrail, BASELINE_NIGHTS)

random.seed(7)

FAILS = []

def check(cond, msg, fix):
    if not cond:
        FAILS.append(msg)
        print(f"FAIL: {msg}\n      fix: {fix}")
    else:
        print(f"  PASS: {msg}")


def flat_nights(n, rhr=55.0, resp=17.0, sleep_min=450.0, jitter=0.0):
    # jitter>0 gives the baseline realistic variance so z-scores are meaningful;
    # a zero-variance baseline forces z=0 by design (no NaN, no fake signal)
    return [{"date": f"2026-09-{i+1:02d}",
             "rhr_bpm": rhr + random.gauss(0, jitter),
             "resp_brpm": resp + random.gauss(0, jitter / 4),
             "sleep_min": sleep_min, "sleep_efficiency": 92.0} for i in range(n)]


# 1. First 14 nights calibrate, 15th scores
res = score_nights(flat_nights(15))
check(all(r["status"] == "calibrating" for r in res[:BASELINE_NIGHTS]),
      "first 14 nights are calibrating",
      "score_nights must require BASELINE_NIGHTS priors before scoring")
check(res[14]["status"] == "scored", "15th night is scored",
      "baseline window logic is off by one")

# 2. Perfect steady state -> green (rhr z=0 -> 50, sleep 450/480=93.75 -> ~71.9)
r = res[14]
check(r["zone"] == "green", f"steady good nights -> green (got {r['zone']} {r['recovery']})",
      "check the 50/50 weighting and zone thresholds (67/34)")

# 3. Terrible night -> red: RHR way up, half the sleep need
#    (baseline needs variance for z-scores to mean anything)
nights = flat_nights(14, jitter=1.5) + [{"date": "2026-09-15", "rhr_bpm": 80.0,
                                        "resp_brpm": 17.0, "sleep_min": 200.0,
                                        "sleep_efficiency": 80.0}]
r = score_nights(nights)[14]
check(r["zone"] == "red", f"bad night -> red (got {r['zone']} {r['recovery']})",
      "rhr z-score sign or sleep_perf math is wrong")

# 4. Respiratory deviation beyond 2 SD drags the score and is reported
nights = flat_nights(14, resp=17.0, jitter=1.5) + [{"date": "2026-09-15", "rhr_bpm": 55.0,
                                                   "resp_brpm": 25.0, "sleep_min": 450.0,
                                                   "sleep_efficiency": 92.0}]
r = score_nights(nights)[14]
check(r["resp_drag"] < 0, f"resp deviation drags score (drag={r['resp_drag']})",
      "resp |z|>2 must apply up to -15 drag")
check(abs(r["resp_z"]) > 2, f"resp_z reported (got {r['resp_z']})",
      "resp z-score computation is wrong")

# 5. Zero-variance baseline must not divide by zero
nights = flat_nights(15, rhr=55.0, resp=17.0, sleep_min=450.0)
r = score_nights(nights)[14]
check(r["status"] == "scored" and r["recovery"] == r["recovery"],  # not NaN
      "zero-variance baseline doesn't produce NaN",
      "guard std==0 before dividing")

# 6. Scores are labeled no-HRV estimates
check(r.get("note") == "no-HRV estimate", "scores labeled no-HRV estimate",
      "every scored night must carry the label until the band supplies RMSSD")

# 7. v2: HRV crash -> lower score than HRV steady (HRV is the dominant input)
def flat_nights_v2(n, rhr=55.0, resp=17.0, sleep_min=450.0, hrv=60.0, jitter=0.0):
    return [{"date": f"2026-09-{i+1:02d}",
             "rhr_bpm": rhr + random.gauss(0, jitter),
             "resp_brpm": resp + random.gauss(0, jitter / 4),
             "sleep_min": sleep_min, "sleep_efficiency": 92.0,
             "hrv_ms": hrv + random.gauss(0, jitter)} for i in range(n)]

base = flat_nights_v2(14, jitter=1.5)
good = score_nights_v2(base + [dict(base[0], date="2026-09-15")])[14]
bad = score_nights_v2(base + [dict(base[0], date="2026-09-15", hrv_ms=25.0)])[14]
check(good["status"] == "scored" and bad["status"] == "scored",
      "v2 scores nights with HRV present",
      "score_nights_v2 must handle hrv_ms inputs")
check(bad["recovery"] < good["recovery"] - 10,
      f"v2: HRV crash drops score hard (good={good['recovery']} bad={bad['recovery']})",
      "HRV z-score must dominate v2 (50% weight)")

# 8. v2: missing HRV -> needs-hrv, never a silent guess
nohrv = flat_nights(15)
r = score_nights_v2(nohrv)[14]
check(r["status"] == "needs-hrv", "v2 without HRV reports needs-hrv",
      "v2 must refuse to score instead of guessing the dominant input")

# 9. Guardrail: HRV-blind green caps at yellow, yellow/red untouched
g = apply_hrv_blind_guardrail({"status": "scored", "zone": "green", "recovery": 80.0})
check(g["zone"] == "yellow" and "guardrail" in g,
      "guardrail caps HRV-blind green at yellow",
      "apply_hrv_blind_guardrail must downgrade green")
y = apply_hrv_blind_guardrail({"status": "scored", "zone": "yellow", "recovery": 50.0})
check(y["zone"] == "yellow" and "guardrail" not in y,
      "guardrail leaves yellow alone",
      "guardrail must not touch non-green zones")
c = apply_hrv_blind_guardrail({"status": "calibrating"})
check(c["status"] == "calibrating",
      "guardrail leaves non-scored results alone",
      "guardrail must pass through calibrating/needs-hrv untouched")

print(f"\n{len(FAILS)} failure(s)" if FAILS else "\nSCORING TESTS GREEN")
sys.exit(1 if FAILS else 0)
