/* doop-core — portable DSP/scoring core (plain C, no platform deps).
 * Reference implementation. Ports must pass the shared test vectors
 * within FROZEN.md tolerances. See PLAN.md §2 "Honest interface note".
 */
#ifndef DOOP_DSP_H
#define DOOP_DSP_H

typedef struct {
    double rmssd_ms;      /* RMSSD of accepted IBIs */
    double mean_hr_bpm;   /* 60000 / mean accepted IBI */
    double sqi;           /* 1.0 - rejected fraction; <0.9 means flagged window */
    int    rejected;      /* count of rejected IBIs */
    int    accepted;      /* count of accepted IBIs */
    int    flagged;       /* 1 if rejected fraction > 10% */
} doop_window_t;

/* Process one window of inter-beat intervals (ms).
 * Artifact rejection: drop IBIs deviating >20% from local median (FROZEN.md).
 * Returns 0 on success, -1 on bad input (n < 2).
 */
int doop_process_window(const double *ibi_ms, int n, doop_window_t *out);

/* Lowest mean HR across windows (resting-HR building block). */
double doop_resting_hr(const double *window_hr_bpm, int n_windows);

#endif
