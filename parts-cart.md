# DOOP Parts Cart — prepared 2026-10-07 (research stage)

Human gate #2 (PLAN.md): agent prepares the cart/list; he buys. Prices are spec estimates unless noted; delivery verifies live price + stock before he pays.

## ⚠️ SKU change since spec v1.1 (Oct 4)
The spec's **SparkFun MAX30105 (SEN-14045) is discontinued** — Core Electronics lists it as "replaced by SEN-16474, no longer available." The replacement is the **SparkFun Photodetector Breakout - MAX30101 (Qwiic), SEN-16474** — Maxim's MAX30101 is the MAX30105 renamed (same sensor, same green+red+IR LEDs, I2C 0x57, 0.1" pins broken out for breadboard). ~$34.39 per SparkFun's own learn page (spec's $25–28 was the old SKU). Do NOT order SEN-14045.

## Track A — BUY NOW (Phase 2 bench rig)
| # | Part | Vendor | SKU | Est. | Buy link / notes |
|---|------|--------|-----|------|------------------|
| 1 | ESP32-S3 MCU — ESP32-S3-DevKitC-1 **or** Seeed XIAO ESP32S3 | — | — | $12–15 | **Check his drawer first** — he lives in the ESP32 ecosystem. XIAO: https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html (~$7.50–10) |
| 2 | PPG sensor (primary) | SparkFun | **SEN-16474** | ~$34 | https://robot-italy.com/en/collections/all/products/sen-16474-sparkfun-photodetector-breakout-max30101-qwiic (listed in stock at crawl; verify live). Or SparkFun direct. |
| 3 | PPG sensor (backup, fingertip SpO2) | Generic | MAX30102 module | $8–12 | Amazon/generic — delivery picks a listing |
| 4 | Breadboard + jumper wires + USB-C **data** cable | — | — | $12–15 | **Skip if bench stocked** (likely) |
| 5 | Velcro elastic strap + foam tape | — | — | $5–8 | Amazon/hardware store — foam-tape RING with cutout per corrected mount diagram |

Track A total: ~$70–85 (was $62–78 in spec; the SEN-16474 replacement accounts for the delta).

## Track C — wearable (Phase 3; buy with Track A to save shipping, or wait for bench results)
| # | Part | Vendor | SKU | Est. | Buy link / notes |
|---|------|--------|-----|------|------------------|
| 6 | Seeed XIAO ESP32S3 (wearable board) | Seeed | — | $7.50–10 | https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html — skip if he already owns spares |
| 7 | 2nd PPG sensor (bench rig survives) | SparkFun | SEN-16474 | ~$34 | same as #2 |
| 8 | IMU 6-DoF | Adafruit | 4503 | $9.95 | Adafruit LSM6DS3TR-C STEMMA QT/Qwiic — DigiKey 1528-4503-ND in stock $9.95: http://www.digikey.com/en/products/detail/4503/1528-4503-ND/16637690 |
| 9 | Skin-temp sensor | Adafruit | 4821 | ~$15 | Adafruit TMP117 ±0.1°C STEMMA QT: https://www.adafruit.com/product/4821 |
| 10 | LiPo 250–400 mAh 3.7V JST-PH | Adafruit | 3898 | ~$7 | 400 mAh, in stock $6.95 at electromaker.io (crawled 1 day ago); Adafruit direct also carries it |
| 11 | Elastic sport strap 20–22 mm + PETG/TPU filament | — | — | $10–15 | Amazon |
| 12 | STEMMA QT/Qwiic cables (100 mm), M2 hardware, Kapton tape | Adafruit/SparkFun | — | $6–10 | bundle with the Adafruit/SparkFun orders |

Track C total: ~$88–108 buying everything new (spec's $60–80 assumed reusing the bench MAX30105; the replacement sensor reprices it).

## Vendor consolidation (fewer shipments)
- **Adafruit order:** IMU (#8), TMP117 (#9), LiPo (#10), Qwiic cables (#12)
- **SparkFun order:** SEN-16474 ×1–2 (#2, #7)
- **Seeed order:** XIAO ESP32S3 (#1 or #6) — ships from China, longest lead; order earliest
- **Amazon:** MAX30102 (#3), breadboard kit (#4), strap/tape (#5, #11)

## Open questions for him (one ask)
1. Which ESP32-S3 boards do you already own? (decides #1/#6)
2. Breadboard, jumpers, USB-C data cables on hand? (decides #4)
