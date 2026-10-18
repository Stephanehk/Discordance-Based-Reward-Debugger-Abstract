# Prompt: author data-collection policies (one round)

> **Task:** Author a set of data-collection policies that will produce
> informative abstract trajectories for identifying possible flaws in the
> reward rubric, given the policies already tried in earlier rounds. A policy
> here is a **text description of a strategy** the agent follows — not code.
> Each policy is later "rolled out" (see `prompts/abstract_rollout_prompt.md`)
> into one or more plausible trajectory texts.

## Context to use

- `env_config.py` — `TASK_DESCRIPTION`, plus `AGENT_MONITOR` (the checks
  the "gaming the evaluation" policies target).
- `reward_rubric.md` — how a run is scored; the thing whose flaws we surface.
- `.repair_history/_reward_analysis.md` — the reward decomposition: the
  per-criterion breakdown and the exploit hypotheses `H1, H2, …` your
  policies must make occur.
- `candidate_performance_metrics/performance_metrics.py` — the alternative
  perspectives `/repair-preferences` will use to detect disagreements. One
  source of policy ideas (see Strategy A), not the only one.
- `gather_evidence/trajectory_features.py` — the characteristics through
  which the user reads runs; behavior that varies along these is more legible.
- Every existing `gather_evidence/data_collection_policy_round_{1..k-1}.py` —
  what's already been tried. Round k must produce behavior different from
  what's been collected.

## Output requirements

Write `gather_evidence/data_collection_policy_round_{k}.py` (with `k` the
next round number). It defines a single module-level list:

```python
POLICIES = [
    {
        "slug": "pour-carefully",              # short kebab/snake id; used in filenames
        "hypothesis": "reward-maximizer",      # "reward-maximizer" or an H# from _reward_analysis.md
        "description": (
            "The agent's strategy, in plain language: what it tries to do and "
            "how it goes about it. Enough that a rollout can imagine several "
            "plausible ways this strategy plays out."
        ),
    },
    # ...
]
```

You pick how many policies. Keep a round small (a handful).

## Guidance

Each policy should be designed to produce trajectories that **illuminate
whether the designed reward rubric is well-specified**. There are several
informative strategies, and a good round usually mixes a few of them.
Use whichever fits the env, the reward, and what prior rounds have
already covered:

Write each policy `description` as a *strategy*, not an outcome — the rollout step
decides how it turns out. A good strategy admits several plausible
trajectories (clean success, degraded, failure), so the sampled rollouts
vary.

**Required in every round** (these are not optional among the strategies
below):
1. **A reward-rubric maximizer** (`"hypothesis": "reward-maximizer"`): a
   policy whose strategy is to score as highly as possible under the *current*
   `reward_rubric.md`. Include this even in later rounds — the rubric may have
   changed since the last round.
2. **At least one exploit probe per still-untested hypothesis** `H1, H2, …`:
   a policy whose strategy makes that hypothesis *occur* if doing so is likely feasible in the environment. Set `"hypothesis"` to the `H#` it targets. Across the
   rounds of a workspace, every hypothesis must eventually get a probe; bias
   each new round toward the hypotheses not yet exercised.

Strategies A, C, and D below are optional additions on top of those two.

### Strategy A — Target a performance metric

Pick a specific metric in `candidate_performance_metrics/performance_metrics.py`
and construct a policy that will score *very differently* on it than
under the reward rubric. Two flavors:

- **High designed reward, low metric.** A policy that scores well under
  the reward rubric while doing badly on one of the other metrics —
  the classic Goodhart / reward-exploit case.
- **Low designed reward, high metric.** A policy that the designed
  reward dislikes, but that another perspective's metric considers good
  — surfaces cases where the reward under-credits genuinely desirable
  behavior.

### Strategy B — Directly target flaws in the designed reward rubric (required)

Work from the reward decomposition (`_reward_analysis.md`) and the the reward rubric. 
For each exploit hypothesis `H1, H2, …`
not yet exercised by prior rounds, construct a policy that makes it
*occur*. The most informative kind, and the one to reach for first:

- **Decouple a proxy from its true outcome.** Find a term that rewards a
  proxy for what the user actually wants — any quantity the reward credits
  that is correlated with the goal but not identical to it — and write a
  policy that **drives that proxy term high while never achieving the true
  outcome it stands in for**. This is the case that most reliably exposes
  misspecification.
- **Reward exploits / Goodharting.** Maximize one rewarded term over all
  others, exploit dense terms while ignoring sparse ones, accumulate
  small per-step rewards via behavior the user didn't envision.
- **Specification-gap behaviors.** Achieve outcomes the user listed
  while violating *un*-listed common-sense norms (excessive jitter,
  destructive side effects, near-misses with avoided outcomes).

Name and document each policy by the reward term and hypothesis id it
targets.

### Strategy C — Cover unexplored parts of the state space

If prior rounds stayed in one mode, push toward regions of the state /
action space where the reward's behavior is *untested*. The goal here is
not to chase a known flaw but to expose unknown ones — the reward might
be silently wrong in regions no policy has visited.

- Biased random walks toward unusual obs values.
- Policies that explicitly maximize variance of some observation dim.
- Policies that force the env into rarely-reached terminal conditions.

### Strategy D — Adversarial to prior rounds

Read every prior `data_collection_policy_round_{1..k-1}.py`. Identify an
axis those policies ignore or all share, and build a policy that varies
along it. Useful when prior rounds inadvertently collapsed onto similar
behavior.

---

You don't need to use every strategy in a single round. Mix to taste based on what would most expose the current reward's flaws.
