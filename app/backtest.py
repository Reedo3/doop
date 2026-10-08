#!/usr/bin/env python3
"""DOOP backtest vs Whoop history export.

Reads private_data/physiological_cycles.csv (Whoop's own per-night numbers)
and compares against DOOP scoring. Three analyses:

  A. FORMULA TEST: DOOP v1 (frozen, no-HRV) fed with Whoop's own RHR/sleep/
     resp inputs vs Whoop's Recovery %. Isolates the algorithm from the
     input-source gap.
  B. PIPELINE TEST: DOOP v1 fed with HealthKit inputs (the deployed path)
     vs Whoop's Recovery % on the overlap window.
  C. HRV EXPERIMENT (not frozen, analysis only): adds an HRV term to see
     how much of the gap the missing HRV explains — i.e., what the band
     buys us.

Metrics: color-agreement % (FROZEN gate 6 needs >=75%), MAE, bias.
"""
import csv
import math
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doop_score import score_nights, sigmoid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CYCLES = os.path.join(ROOT, "private_data", "physiological_cycles.csv")


def f(x):
    try:
        v = float(x)
        return v if v == v else None  # NaN -> None
    except (TypeError, ValueError):
        return None


def report_date(row):
    """The morning a Recovery score is reported = cycle end date (wake);
    for the still-open latest cycle, fall back to cycle start date."""
    end = (row["Cycle end time"] or "").strip()
    start = (row["Cycle start time"] or "").strip()
    try:
        if end:
            return datetime.strptime(end, "%Y-%m-%d %H:%M:%S").date().isoformat()
        return datetime.strptime(start, "%Y-%m-%d %H:%M:%S").date().isoformat()
    except ValueError:
        return None


def load_cycles():
    nights = []
    with open(CYCLES, newline="") as fh:
        for row in csv.DictReader(fh):
            rec = f(row["Recovery score %"])
            rhr = f(row["Resting heart rate (bpm)"])
            hrv = f(row["Heart rate variability (ms)"])
            resp = f(row["Respiratory rate (rpm)"])
            asleep = f(row["Asleep duration (min)"])
            eff = f(row["Sleep efficiency %"])
            if rec is None or rhr is None or asleep is None or resp is None:
                continue
            date = report_date(row)
            if date is None:
                continue
            nights.append({
                "date": date,
                "cycle_start": row["Cycle start time"].strip(),
                "whoop_recovery": rec,
                "rhr_bpm": rhr,
                "hrv_ms": hrv,
                "resp_brpm": resp,
                "sleep_min": asleep,
                "sleep_efficiency": eff or 0,
            })
    # one row per reporting morning: on collision keep the freshest cycle
    # (latest cycle start)
    nights.sort(key=lambda n: (n["date"], n["cycle_start"]))
    deduped, seen = [], set()
    for n in reversed(nights):
        if n["date"] not in seen:
            d = dict(n)
            del d["cycle_start"]
            deduped.append(d)
            seen.add(n["date"])
    deduped.sort(key=lambda n: n["date"])
    return deduped


def zone(x):
    return "green" if x >= 67 else ("yellow" if x >= 34 else "red")


def report(name, pairs):
    """pairs: list of (doop_score, whoop_score)."""
    pairs = [(d, w) for d, w in pairs if d is not None and w is not None]
    n = len(pairs)
    if not n:
        print(f"{name}: no comparable nights")
        return
    agree = sum(1 for d, w in pairs if zone(d) == zone(w)) / n * 100
    mae = sum(abs(d - w) for d, w in pairs) / n
    bias = sum(d - w for d, w in pairs) / n
    print(f"{name}: n={n} color-agreement={agree:.1f}% MAE={mae:.1f} "
          f"bias={bias:+.1f} (DOOP optimistic if +)")
    # confusion detail
    for zt in ("red", "yellow", "green"):
        sub = [(d, w) for d, w in pairs if zone(w) == zt]
        if sub:
            a = sum(1 for d, w in sub if zone(d) == zt) / len(sub) * 100
            print(f"   when Whoop={zt} (n={len(sub)}): DOOP agrees {a:.1f}%")


def doop_v1_inputs(nights):
    return [{"date": n["date"], "rhr_bpm": n["rhr_bpm"], "resp_brpm": n["resp_brpm"],
             "sleep_min": n["sleep_min"], "sleep_efficiency": n["sleep_efficiency"]}
            for n in nights]


def hrv_experiment(nights):
    """Experimental scorer: HRV-dominant mix mirroring Whoop's weighting.
    NOT frozen. Analysis only."""
    out = []
    for i, night in enumerate(nights):
        priors = nights[max(0, i - 14):i]
        if len(priors) < 14 or night["hrv_ms"] is None:
            out.append(None)
            continue
        def mean(xs): return sum(xs) / len(xs)
        def std(xs, m): return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0
        hrv_m, rhr_m, resp_m = mean([p["hrv_ms"] for p in priors]), mean([p["rhr_bpm"] for p in priors]), mean([p["resp_brpm"] for p in priors])
        hrv_s, rhr_s, resp_s = std([p["hrv_ms"] for p in priors], hrv_m), std([p["rhr_bpm"] for p in priors], rhr_m), std([p["resp_brpm"] for p in priors], resp_m)
        hrv_z = (night["hrv_ms"] - hrv_m) / hrv_s if hrv_s > 0 else 0
        rhr_z = (rhr_m - night["rhr_bpm"]) / rhr_s if rhr_s > 0 else 0
        # sleep performance via doop v1 need calc
        debt = sum(max(0.0, 480.0 - p["sleep_min"]) for p in priors[-3:])
        need = 480.0 + 0.5 * debt
        sleep_perf = 100.0 * min(night["sleep_min"], need) / need if need > 0 else 0
        resp_z = (night["resp_brpm"] - resp_m) / resp_s if resp_s > 0 else 0
        drag = -15.0 * min(1.0, (abs(resp_z) - 2.0) / 2.0) if abs(resp_z) > 2 else 0.0
        score = (0.50 * 100 * sigmoid(hrv_z) + 0.25 * 100 * sigmoid(rhr_z)
                 + 0.25 * sleep_perf + drag)
        out.append(max(0.0, min(100.0, score)))
    return out


def main():
    nights = load_cycles()
    print(f"loaded {len(nights)} Whoop nights "
          f"({nights[0]['date']}..{nights[-1]['date']})")

    # A. formula test: frozen DOOP v1 on Whoop's own inputs
    v1 = score_nights(doop_v1_inputs(nights))
    pairs_a = [(r["recovery"] if r["status"] == "scored" else None, n["whoop_recovery"])
               for r, n in zip(v1, nights)]
    report("A. DOOP v1 (Whoop inputs) vs Whoop", pairs_a)

    # C. HRV experiment
    exp = hrv_experiment(nights)
    pairs_c = [(e, n["whoop_recovery"]) for e, n in zip(exp, nights)]
    report("C. HRV-dominant experiment vs Whoop", pairs_c)

    # recent window detail (last 14 scored nights)
    scored = [(n["date"], r["recovery"], n["whoop_recovery"])
              for r, n in zip(v1, nights) if r["status"] == "scored"]
    print("\nlast 10 scored nights (date, DOOP, Whoop):")
    for d, ds, ws in scored[-10:]:
        print(f"  {d}: DOOP {ds:5.1f} [{zone(ds):6s}]  Whoop {ws:5.1f} [{zone(ws):6s}]"
              f"  {'MATCH' if zone(ds) == zone(ws) else 'miss'}")


if __name__ == "__main__":
    main()
