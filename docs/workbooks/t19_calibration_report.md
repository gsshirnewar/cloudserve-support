# T19 Classification Calibration Report

- Mode: `mock-labels` | Tickets: **500** | Seed: `42`
- Method: ECE + reliability bins (10). Temperature scaling fit by NLL grid-search on overall confidence; operating threshold selected by sweep on calibrated confidence (target >=0.80 accuracy on selected, max coverage).
- Note: mock-labels mode generates label-informed pseudo-predictions for calibration-pipeline/tooling verification (not real model calibration). Run with --mode real on dev set for true calibration.

## Calibration metrics (joint intent+urgency correctness vs overall confidence)
- ECE (raw): **0.1159**
- Temperature (fitted): **0.8650**
- ECE (calibrated): **0.1112**
- Accuracy (joint/intent/urgency): **0.7660 / 0.8420 / 0.9120**

## Operating threshold (calibrated overall confidence)
- Selected threshold: **0.55** (sweep on calibrated confidence; target >= 0.80 accuracy on selected, maximize coverage)

### Threshold sweep (calibrated)
| threshold | selected | coverage | accuracy_on_selected |
|---:|---:|---:|---:|
| 0.30 | 499 | 0.998 | 0.768 |
| 0.35 | 499 | 0.998 | 0.768 |
| 0.40 | 498 | 0.996 | 0.769 |
| 0.45 | 491 | 0.982 | 0.780 |
| 0.50 | 483 | 0.966 | 0.793 |
| 0.55 | 469 | 0.938 | 0.817 |
| 0.60 | 462 | 0.924 | 0.829 |
| 0.65 | 450 | 0.900 | 0.851 |
| 0.70 | 431 | 0.862 | 0.886 |
| 0.75 | 408 | 0.816 | 0.909 |
| 0.80 | 369 | 0.738 | 0.924 |
| 0.85 | 299 | 0.598 | 0.957 |
| 0.90 | 211 | 0.422 | 0.991 |
| 0.95 | 105 | 0.210 | 0.990 |

### Reliability curve bins (raw)
| bin | count | avg_conf | accuracy |
|---|---:|---:|---:|
| [0.0,0.1] | 0 | 0.000 | 0.000 |
| [0.1,0.2] | 0 | 0.000 | 0.000 |
| [0.2,0.3] | 1 | 0.273 | 0.000 |
| [0.3,0.4] | 1 | 0.372 | 0.000 |
| [0.4,0.5] | 15 | 0.460 | 0.000 |
| [0.5,0.6] | 24 | 0.539 | 0.000 |
| [0.6,0.7] | 38 | 0.655 | 0.079 |
| [0.7,0.8] | 93 | 0.759 | 0.774 |
| [0.8,0.9] | 179 | 0.852 | 0.894 |
| [0.9,1.0] | 149 | 0.948 | 0.993 |

### Reliability curve bins (calibrated)
| bin | count | avg_conf | accuracy |
|---|---:|---:|---:|
| [0.0,0.1] | 0 | 0.000 | 0.000 |
| [0.1,0.2] | 0 | 0.000 | 0.000 |
| [0.2,0.3] | 1 | 0.244 | 0.000 |
| [0.3,0.4] | 1 | 0.353 | 0.000 |
| [0.4,0.5] | 15 | 0.454 | 0.000 |
| [0.5,0.6] | 21 | 0.537 | 0.000 |
| [0.6,0.7] | 31 | 0.658 | 0.032 |
| [0.7,0.8] | 62 | 0.759 | 0.661 |
| [0.8,0.9] | 158 | 0.854 | 0.835 |
| [0.9,1.0] | 211 | 0.950 | 0.991 |

```json
{
  "mode": "mock-labels",
  "n_tickets": 500,
  "seed": 42,
  "method": "ECE + reliability bins (10). Temperature scaling fit by NLL grid-search on overall confidence; operating threshold selected by sweep on calibrated confidence (target >=0.80 accuracy on selected, max coverage).",
  "note": "mock-labels mode generates label-informed pseudo-predictions for calibration-pipeline/tooling verification (not real model calibration). Run with --mode real on dev set for true calibration.",
  "ece_raw_joint": 0.11593718699968547,
  "temperature": 0.865,
  "ece_calibrated_joint": 0.1112411679225736,
  "reliability_bins_raw": [
    {
      "bin_lower": 0.0,
      "bin_upper": 0.1,
      "count": 0,
      "avg_confidence": 0.0,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.1,
      "bin_upper": 0.2,
      "count": 0,
      "avg_confidence": 0.0,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.2,
      "bin_upper": 0.30000000000000004,
      "count": 1,
      "avg_confidence": 0.27284103794284376,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.30000000000000004,
      "bin_upper": 0.4,
      "count": 1,
      "avg_confidence": 0.37203526176919205,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.4,
      "bin_upper": 0.5,
      "count": 15,
      "avg_confidence": 0.4598719439242432,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.5,
      "bin_upper": 0.6000000000000001,
      "count": 24,
      "avg_confidence": 0.5393460986629283,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.6000000000000001,
      "bin_upper": 0.7000000000000001,
      "count": 38,
      "avg_confidence": 0.6553281573323936,
      "accuracy": 0.07894736842105263
    },
    {
      "bin_lower": 0.7000000000000001,
      "bin_upper": 0.8,
      "count": 93,
      "avg_confidence": 0.7594960427518365,
      "accuracy": 0.7741935483870968
    },
    {
      "bin_lower": 0.8,
      "bin_upper": 0.9,
      "count": 179,
      "avg_confidence": 0.851899386406487,
      "accuracy": 0.8938547486033519
    },
    {
      "bin_lower": 0.9,
      "bin_upper": 1.0,
      "count": 149,
      "avg_confidence": 0.9483088333059879,
      "accuracy": 0.9932885906040269
    }
  ],
  "reliability_bins_calibrated": [
    {
      "bin_lower": 0.0,
      "bin_upper": 0.1,
      "count": 0,
      "avg_confidence": 0.0,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.1,
      "bin_upper": 0.2,
      "count": 0,
      "avg_confidence": 0.0,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.2,
      "bin_upper": 0.30000000000000004,
      "count": 1,
      "avg_confidence": 0.24356299275599408,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.30000000000000004,
      "bin_upper": 0.4,
      "count": 1,
      "avg_confidence": 0.3531556117393287,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.4,
      "bin_upper": 0.5,
      "count": 15,
      "avg_confidence": 0.45370072901179204,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.5,
      "bin_upper": 0.6000000000000001,
      "count": 21,
      "avg_confidence": 0.5372200294025986,
      "accuracy": 0.0
    },
    {
      "bin_lower": 0.6000000000000001,
      "bin_upper": 0.7000000000000001,
      "count": 31,
      "avg_confidence": 0.658392647289239,
      "accuracy": 0.03225806451612903
    },
    {
      "bin_lower": 0.7000000000000001,
      "bin_upper": 0.8,
      "count": 62,
      "avg_confidence": 0.7588389650687424,
      "accuracy": 0.6612903225806451
    },
    {
      "bin_lower": 0.8,
      "bin_upper": 0.9,
      "count": 158,
      "avg_confidence": 0.8538939812517556,
      "accuracy": 0.8354430379746836
    },
    {
      "bin_lower": 0.9,
      "bin_upper": 1.0,
      "count": 211,
      "avg_confidence": 0.9499369816769944,
      "accuracy": 0.990521327014218
    }
  ],
  "threshold_sweep_calibrated": [
    {
      "threshold": 0.3,
      "selected": 499,
      "coverage": 0.998,
      "accuracy_on_selected": 0.7675350701402806
    },
    {
      "threshold": 0.35,
      "selected": 499,
      "coverage": 0.998,
      "accuracy_on_selected": 0.7675350701402806
    },
    {
      "threshold": 0.4,
      "selected": 498,
      "coverage": 0.996,
      "accuracy_on_selected": 0.7690763052208835
    },
    {
      "threshold": 0.45,
      "selected": 491,
      "coverage": 0.982,
      "accuracy_on_selected": 0.780040733197556
    },
    {
      "threshold": 0.5,
      "selected": 483,
      "coverage": 0.966,
      "accuracy_on_selected": 0.7929606625258799
    },
    {
      "threshold": 0.55,
      "selected": 469,
      "coverage": 0.938,
      "accuracy_on_selected": 0.8166311300639659
    },
    {
      "threshold": 0.6,
      "selected": 462,
      "coverage": 0.924,
      "accuracy_on_selected": 0.829004329004329
    },
    {
      "threshold": 0.65,
      "selected": 450,
      "coverage": 0.9,
      "accuracy_on_selected": 0.8511111111111112
    },
    {
      "threshold": 0.7,
      "selected": 431,
      "coverage": 0.862,
      "accuracy_on_selected": 0.8863109048723898
    },
    {
      "threshold": 0.75,
      "selected": 408,
      "coverage": 0.816,
      "accuracy_on_selected": 0.9093137254901961
    },
    {
      "threshold": 0.8,
      "selected": 369,
      "coverage": 0.738,
      "accuracy_on_selected": 0.924119241192412
    },
    {
      "threshold": 0.85,
      "selected": 299,
      "coverage": 0.598,
      "accuracy_on_selected": 0.9565217391304348
    },
    {
      "threshold": 0.9,
      "selected": 211,
      "coverage": 0.422,
      "accuracy_on_selected": 0.990521327014218
    },
    {
      "threshold": 0.95,
      "selected": 105,
      "coverage": 0.21,
      "accuracy_on_selected": 0.9904761904761905
    }
  ],
  "selected_operating_threshold_overall_confidence": 0.55,
  "accuracy_overall": 0.766,
  "intent_accuracy": 0.842,
  "urgency_accuracy": 0.912
}
```