#!/usr/bin/env python3
"""Generate DOOP test fixtures with self-consistent expected values.

Provenance: SYNTHETIC (seeded RNG). These prove the math, not the physiology.
Real chest-strap + PPG captures replace/augment them from Phase 2 onward.

Expected values are computed with the exact FROZEN.md definitions:
  median -> reject IBIs deviating >20% from median ->
  RMSSD = sqrt(mean(diff^2)) on accepted IBIs.
The C core must reproduce them within FROZEN.md tolerances (1%).
"""
import json, math, random, os

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(20261007)

def expected(ibi):
    s = sorted(ibi)
    med = s[len(s) // 2]
    acc = [x for x in ibi if abs(x - med) / med <= 0.20]
    rej = len(ibi) - len(acc)
    diffs = [acc[i+1] - acc[i] for i in range(len(acc) - 1)]
    rmssd = math.sqrt(sum(d*d for d in diffs) / len(diffs)) if diffs else 0.0
    mean_hr = 60000.0 / (sum(acc) / len(acc)) if acc else 0.0
    frac = rej / len(ibi)
    return {
        "expected_rmssd_ms": round(rmssd, 3),
        "expected_mean_hr_bpm": round(mean_hr, 3),
        "expected_rejected": rej,
        "expected_sqi": round(1.0 - frac, 4),
        "expected_flagged": 1 if frac > 0.10 else 0,
    }

def synth_clean(n=340, base=857.0, jitter=38.0):
    # ~5 min window at ~70 bpm with healthy variability
    return [base + random.gauss(0, jitter) for _ in range(n)]

def save(name, ibi, note):
    payload = {"name": name, "note": note, "ibi_ms": [round(x, 2) for x in ibi]}
    payload.update(expected(ibi))
    path = os.path.join(HERE, name + ".json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=1)
    print(f"wrote {path}: rmssd={payload['expected_rmssd_ms']} "
          f"hr={payload['expected_mean_hr_bpm']} rejected={payload['expected_rejected']} "
          f"flagged={payload['expected_flagged']}")

def main():
    clean = synth_clean()
    save("ibi_clean", clean, "synthetic clean 5-min window, ~70bpm")

    ectopic = list(clean)
    # inject 3 ectopic beats: premature short beat + compensatory long beat
    for idx in (50, 150, 280):
        ectopic[idx] = ectopic[idx] * 0.55
        ectopic[idx + 1] = ectopic[idx + 1] * 1.45
    save("ibi_ectopic", ectopic, "clean + 3 injected ectopic pairs (>20% deviation, must be rejected)")

    noisy = list(clean)
    # corrupt 25% of beats with motion-artifact-like garbage
    idxs = random.sample(range(len(noisy)), len(noisy) // 4)
    for i in idxs:
        noisy[i] = noisy[i] * random.choice([0.3, 2.2])
    save("ibi_noisy", noisy, "25% corrupted beats -> window must be flagged (SQI < 0.9)")

if __name__ == "__main__":
    main()
