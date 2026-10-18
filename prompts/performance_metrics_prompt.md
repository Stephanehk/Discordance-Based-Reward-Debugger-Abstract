# Prompt: declare candidate performance perspectives

> **Task:** Declare a small set of diverse perspectives that represent
> things *other* reasonable people might find desirable or undesirable. 
> The goal is for the set to capture what different users would
> consider a good or bad outcome — so that when a perspective ranks two runs
> oppositely to the reward rubric, that disagreement can be surfaced.

## Context to use

- `env_config.py` — the task and how it's evaluated.
- `reward_rubric.md` — what the *current* user chose to score. Your
  perspectives should cover **other** viewpoints, not restate this one.
- `gather_evidence/trajectory_features.py` — the characteristics; a
  perspective may care about some of them, but state it as a viewpoint.

## Output requirements

Write `candidate_performance_metrics/performance_metrics.py`. Each
perspective is a module-level **declaration stub** — it is never called;
Claude scores each trajectory from each perspective by hand and writes the
value into the trajectory's features sidecar (`metric_values`).

```python
def performance_metric_<short_name>(traj):
    """One short line describing whose perspective this represents (higher = better)."""
    raise NotImplementedError("declaration only; scored by Claude on disk")
```

The function name must start with `performance_metric_`. The docstring must
be **one short line** — it is the internal label used when a disagreement is
found. Higher scores mean better *by that perspective's lights*.

## Guidance

- **Different perspectives, not different formulations.** Adapt to the env
- Metrics should be **non-trivial** — At least one perspective should **correlate** with the reward rubric (so
  disagreements are surprising) and at least one should be **capable of
  disagreeing** with it (so disagreements exist to surface).
- Pick a count that fits the env — typically 3–6. If two perspectives are
  near-duplicates, keep one.
- These perspectives are **never shown to the user** — they only drive
  comparison selection under the hood.
