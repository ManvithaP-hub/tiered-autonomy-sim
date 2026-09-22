# tiered-autonomy-sim

A reproducible Monte Carlo simulation of **tiered, blast-radius-aware authority control** for self-healing CI/CD agents.

Each remediation action is assigned one of four tiers based on its estimated blast radius:

| Tier | Authority | Default rule |
|---|---|---|
| 3 | Execute unsupervised | estimated blast < 0.02 and confidence >= 0.7 |
| 2 | Execute with verification gate | estimated blast < 0.20 |
| 1 | Propose, human approves | estimated blast < 0.50 |
| 0 | Observe, human acts | otherwise |

## Run

Requires Python 3.9+ and no third-party packages.

```bash
python experiments.py
```

This reproduces every number in the paper (main comparison, matched-workload sweep, sensitivity to estimation noise, miscalibration and verification strength, and harm by category) and writes `results.json`.

## Important

All parameters (category mix, blast-radius ranges, confidence distribution, miscalibration, catch probabilities, workload weights) are **synthetic and illustrative**. They are exposed in `Params` and `CATEGORIES` in `tiered_autonomy_sim/sim.py` so they can be replaced with values from real remediation data.

## License

Apache License 2.0
