---
name: repair-round
description: Steps 3-5 of the Abstract Reward Repairer. Authors text policy descriptions, rolls each out into abstract trajectories, scores them, evaluates whether the evidence is sufficient, and either adds another round automatically or hands off to /repair-preferences to surface the disagreements. Invoke whenever the user asks to collect more evidence.
---

# /repair-round — collect evidence of reward misspecification

This skill is the autonomous evidence-collection step. A single invocation
may run **one or more** rounds — Claude decides whether the evidence
gathered is sufficient, or whether another round would help. When it is
sufficient, it continues automatically into the `/repair-preferences`
deliverable.

There is **no web UI** — talk to the user in ordinary chat messages and ask
any decision with the `AskUserQuestion` tool.

## Agent-in-the-loop: you generate and score everything

There is no environment to step, no policy code to run, and no batch
rollout/scoring script. **Claude itself** (a) writes each abstract
trajectory text from a text policy description, and (b) scores each
trajectory (characteristics, perspectives, reward), writing JSON to disk.
The exact on-disk formats and the rollout/scoring procedure are in
`CLAUDE.md` → "Agent-in-the-loop generation and scoring" — follow them
precisely.

## Tone for messages to the user

Treat the user as someone who will never read the codebase. Talk about what
the system is **doing** in plain language ("collecting trajectories that
probe a particular part of your reward", "checking whether the evidence is
rich enough"), never file names, counts, or scripts.

**Never call any behavior, reward, or trajectory "correct" or
"incorrect."** The alternative-perspective scores are under-the-hood
selection signals only — never mention a perspective, metric, or
"stakeholder". (See `CLAUDE.md` for the full tone rules.) Post brief plain
chat status lines at key transitions ("Designing the next round of
probes.", "Generating trajectories.", "Round complete — analysing what came
out.").

## Resolve the workspace

The skill takes the workspace name as `args`. If empty, read
`.current_workspace`; if that doesn't exist, tell the user to run
`/repair-setup` first and stop. `WORKSPACE_DIR = workspaces/<WORKSPACE>`.

## Preconditions

- `<WORKSPACE_DIR>/env_config.py`, `<WORKSPACE_DIR>/reward_rubric.md`,
  `<WORKSPACE_DIR>/gather_evidence/trajectory_features.py`, and
  `<WORKSPACE_DIR>/candidate_performance_metrics/performance_metrics.py` all
  exist. If any is missing, tell the user to run `/repair-setup` or
  `/repair-init` first (in plain terms) and stop.

## The autonomous loop

Run up to **3 rounds per invocation**. After each round, evaluate the
evidence so far and decide: run another round targeting a gap, or stop and
proceed to `/repair-preferences`. Tell the user the decision in one short
sentence each time. Don't dump per-round statistics.

## Per-round procedure

### Step 1 — figure out the next round number

```python
import glob, re
existing = glob.glob(f"{WORKSPACE_DIR}/gather_evidence/data_collection_policy_round_*.py")
nums = [int(re.search(r"round_(\d+)\.py$", p).group(1)) for p in existing]
k = (max(nums) + 1) if nums else 1
```

### Step 2 — author the round's policies (text descriptions)

**First, build or refresh the reward decomposition.** Following
`prompts/reward_decomposition_prompt.md`, write/update
`<WORKSPACE_DIR>/.repair_history/_reward_analysis.md` (the criterion-by-
criterion breakdown of `reward_rubric.md` plus exploit hypotheses `H1, H2,
…`); reuse it if its stamped rubric hash already matches the current rubric,
otherwise regenerate it (see `CLAUDE.md` → "Reward introspection"). The
round exists to make those hypotheses *occur* in generated trajectories.

Write `<WORKSPACE_DIR>/gather_evidence/data_collection_policy_round_{k}.py`.
Read `prompts/data_collection_policy_prompt.md` for the verbatim task text.
Context to use:
- `env_config.TASK_DESCRIPTION`, `AGENT_MONITOR`
- `reward_rubric.md`
- **all prior rounds'** policy files, so this round is genuinely different
- `gather_evidence/trajectory_features.py` — the characteristics worth varying
- the decomposition's hypotheses `H#`

The file exposes a module-level `POLICIES: list[dict]` (see the invariants
in `CLAUDE.md`), each entry:

```python
POLICIES = [
    {"slug": "reward-maximizer",
     "hypothesis": "reward-maximizer",
     "description": "The strategy the agent follows, in plain language. This one plays purely to maximize the score under reward_rubric.md."},
    {"slug": "game-the-record",
     "hypothesis": "H2",
     "description": "The strategy that targets exploit hypothesis H2 (naming the rubric criterion it games)."},
    # ...
]
```

`slug` is a short kebab/snake id used in trajectory filenames and as the
internal provenance tag. **Required in every round:** a policy that
maximizes the score under the *current* `reward_rubric.md`, and at least one
policy targeting a still-untested exploit hypothesis `H#`. Across a
workspace's rounds, every hypothesis must eventually get a probe. How many
policies? 3–6 for round 1 (broad coverage incl. the maximizer); 2–4 for
later rounds (focused on the gap, still re-including the maximizer).

### Step 3 — roll out each policy into abstract trajectories

For each policy, and for each of its `k` samples (**keep the round small**:
~1–5 samples/policy, ≤ ~30 trajectories per round), Claude writes one
plausible abstract trajectory text following
`prompts/abstract_rollout_prompt.md` (a short bold plain-English account of
what the agent does and how it comes out; optional italic detail; every
trajectory identifiable from a single run). **Vary** the samples — different
plausible ways that policy could play out — don't paraphrase one outcome.
Write each to disk via `runtime.trajectory_io.save_trajectory` at
`gather_evidence/round_{k}_trajectories/{slug}__traj_{i:03d}.json` with
metadata `{round, policy: slug, rollout_index, seed}` (see `CLAUDE.md`).

### Step 4 — score every trajectory

For every trajectory just written, produce two sidecar files (formats in
`CLAUDE.md`):
- **features sidecar** — rate each characteristic (per the `feature_rubric`
  in `trajectory_features.py`) and score each perspective (per the
  docstrings in `performance_metrics.py`), writing `features`, `names`,
  `metric_values`, `source`.
- **reward sidecar** — judge the trajectory against `reward_rubric.md`,
  averaging a few independent reads for stability, and write
  `designed_reward` with the current `rubric_hash`.

Keep the reward and characteristic scales consistent across all
trajectories (anchor to the rubric and the rubric definitions, not to
whichever trajectory you scored first). Score **every** trajectory before
selection — unscored trajectories are silently skipped downstream.

### Step 5 — evaluate sufficiency

Read the features + reward sidecars written so far and reason with the
rubric below.

## Sufficiency rubric

The evidence is **sufficient** when *all* hold:

1. **Every reward criterion AND every exploit hypothesis has been exercised
   by at least one trajectory.** Use `_reward_analysis.md` to enumerate
   both. For each *criterion*, there must be a trajectory whose
   characteristics show that criterion clearly firing (or clearly failing).
   For each *exploit hypothesis* `H#`, at least one trajectory must
   **instantiate** it — the proxy characteristic scored high while the
   true-outcome characteristic scored low (the decoupling is actually
   present, not just hypothesized). If a criterion is silent, or a
   hypothesis is never instantiated, design a round targeting it.

2. **The trajectories are meaningfully diverse** on the key
   characteristics. If every policy collapses to the same outcome, add
   policies that diverge.

3. **At least 5 distinct disagreeing pairs** can be found in the dumped
   table (`select_pairs.py --mode dump`) — pairs where the designed reward
   and another perspective rank the two trajectories oppositely. Judge this
   directly from the table; do **not** run the legacy
   `find_informative_pairs.py --top-overall` probe. (`--check-snapshots` is
   fine.) If fewer than 5, generate more diverging behavior.

4. **You covered every behavior you suspected would expose a flaw.** If —
   after reading `reward_rubric.md` — you can still name a behavior you
   suspect would expose a flaw (a way to game the rubric, act beyond the
   task's scope, or satisfy the letter of a criterion against its intent)
   and no trajectory realizes it, design a round that produces it.

If any of (1)–(4) fails AND we haven't hit the 3-round cap, run another
round targeting the failing axis.

## Targeting the gap

- Rubric (1) failed on a criterion → author a policy whose explicit goal is
  to make that criterion fire (or fail).
- Rubric (2) failed (collapse) → author policies along an ignored axis
  (degraded-but-successful, partial-progress, disturb-the-setup variants).
- Rubric (3) failed (too few disagreements) → author a policy that would
  score high under the rubric while being clearly worse from a perspective
  the user cares about (gaming the evaluation, acting beyond scope).

Round 1 has no prior evidence; design a broad-coverage round of 3–6
policies spanning the taxonomy families in `prompts/abstract_rollout_prompt.md`
(clean success, degraded success, correct-end-state-by-illegitimate-route,
partial progress, honest failure, gaming the evaluation, acting beyond the
task).

## When the loop ends — produce the /repair-preferences deliverable

When the rubric is satisfied (or the 3-round cap is reached), continue
immediately into the `/repair-preferences` deliverable — do **not** stop and
ask. Execute `repair-preferences/SKILL.md` inline. In summary:

1. **Select the comparisons.** Dump the table (`select_pairs.py --mode
   dump`), read the table **and the trajectory texts on disk**, choose **up
   to 5 pairs plus up to 2 lottery comparisons** (`{c, a, b, p}`; justify
   `p` in the selection JSON), write
   `<WORKSPACE_DIR>/.repair_history/_selection.json`, and render it
   (`select_pairs.py --mode render`). For each pair add a `"characteristics"`
   list — the characteristic `short_name`s ranked most→least informative
   about why the designed reward's preference may be wrong. For lotteries,
   `p` = probability of the good branch (A); pick `p` off the reward
   indifference point `p* = (return(C) − return(B)) / (return(A) −
   return(B))` so the choice is genuinely difficult, and justify it. Prefer
   two *different* lottery shapes over two values of `p` on one shape.

2. **Present the comparisons to the user in chat** (from the render's
   output), pairs first then lotteries. For each pair: the two abstract
   trajectory texts (A = "Your preferred trajectory", B = "The alternative
   trajectory"), a one-sentence "why they disagree" line, and the
   characteristics list ("higher/lower/same … (a vs. b)"). Show the first
   pair in full; the rest may be more compact. For each lottery: Trajectory
   A and B (with their probabilities) and the certain Trajectory C, plus a
   **quantitative** summary of how A, B, C differ (actual characteristic
   values, not qualitative words). Strip all internal ids, provenance, and
   never mention perspectives or metrics.

3. **Always close with the four-option question** via `AskUserQuestion`:
   - **Edit the reward rubric** — modify the reward to reflect what you
     actually want, based on the disagreements above.
   - **Add another characteristic** — add a new characteristic to the
     trajectory summary so comparisons show more detail.
   - **View more comparisons** — surface additional pairs or lotteries from
     the evidence already collected.
   - **Finish and submit (not reversible)** — lock in the current reward as
     the final answer; ends the session.
   Act on the answer per `repair-preferences/SKILL.md` Step 4. In
   particular: the **second consecutive** "View more comparisons" click
   (with no reward edit / characteristic add / fresh round in between) hands
   off to a fresh `/repair-round` under the unchanged reward, rather than
   re-selecting from disk a third time.

Skipping the presented comparisons, the per-comparison "why", or the closing
question is not optional — they are the core deliverable of this skill.
