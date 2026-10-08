# DOOP — Decision log

Why-notes. Newest at the bottom.

## 2026-10-07 — Track C chosen (Reedom, in chat)

XIAO ESP32S3 wearable ($60–80 BOM, 2–4 day battery) over Track B nRF52840 ($95–120, 4–7 days). Reason: cheapest, fastest start; he already lives in the ESP32 ecosystem. Battery tax accepted knowingly; v1 iterates weekly so charge frequency is tolerable. DSP core stays portable — migration to Track B later changes MCU/power states only, not algorithms.

## 2026-10-07 — Two lanes, one contract (plan v1.1)

Software lane (Apple HealthKit scoring, immediate) de-risks algorithms before hardware exists. Single `doop-core` in C as reference; test vectors + FROZEN tolerances are the real contract so ports (JS/Python app side) can't diverge silently.
