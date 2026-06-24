# VALI Architecture Map

```text
User / researcher
       |
       v
vali.application + vali.cli
  command parsing and orchestration
       |
       +-------------------------+
       |                         |
       v                         v
vali.research               vali.providers
  pipeline, folds,            public read-only collection
  calibration, sensitivity    Kalshi + Google Trends components
       |                         |
       +------------+------------+
                    v
       vali.data + vali.configuration
         schemas, provenance, point-in-time
         contracts, typed config, validation
                    |
                    v
              vali.domain
         A, P, velocities, S_t, M_t,
         regime classification
                    |
          +---------+---------+
          |                   |
          v                   v
    vali.execution       vali.artifacts
      liquidity, fees,     metrics, manifests,
      snapshots, exits     serialization, reports

Cross-cutting controls:
  tests/{unit,contract,leakage,integration}
  docs/{adr,methodology,operational,submission}
  data/{raw,interim,processed,quarantine}
```

Legacy modules remain compatibility facades over the extracted boundaries. The
provider layer has no order-entry API; the execution layer is simulation-only.
Outcome labels remain outside signal-time tables, and quarantined build/data
copies are never import sources.
