# Abstract Reward Repairer

## What this project is

This is a fork of the Automated Reward Repairer for environments where we
can only elicit **abstract trajectories** — short *text descriptions* of
plausible runs — rather than concrete rolled-out trajectories of
`(obs, act, next_obs)` transitions.

The user has an environment described in words (what the agent is given,
what counts as doing the task well, and how the outcome is evaluated) and a
**reward rubric**: a natural-language description of how a run should be
scored. This system surfaces *evidence of reward misspecification* by
generating diverse abstract trajectories, scoring them with both the
designed reward rubric and a set of alternative-perspective rubrics (used
only under the hood to select comparisons), and showing the user
**trajectory pairs where the designed reward and a perspective disagree on
which trajectory is better**. The pairs are the end product: the user reads
them and decides how to edit the reward rubric.

**Claude is the engine.** There is no environment to step, no policy code
to run, and no LLM API client. Claude itself:
1. **rolls out** a text policy description into an abstract trajectory text,
2. **judges** each abstract trajectory against the reward rubric to a score,
3. **rates** each abstract trajectory's characteristics and
   alternative-perspective scores,
and writes all of it to disk. The deterministic Python scripts
(`select_pairs.py`, `find_informative_pairs.py`) only read those on-disk
scores and do the pair/lottery selection, rendering, and snapshotting.

## No web UI — the terminal + AskUserQuestion is the channel

Unlike the concrete repairer, there is **no web server**. Skills talk to
the user through Claude's normal chat output and ask questions with the
**`AskUserQuestion` tool**. Post narrative, code, and comparison blocks as
ordinary assistant messages; ask every user decision (setup choices, the
four-option next step) with `AskUserQuestion`. There is no
`python -m web_ui.cli` anywhere in this fork.

## Workspaces

Every environment-specific file lives in a **workspace** under
`workspaces/<name>/`. The boilerplate (`runtime/`,
`find_informative_pairs.py`, `select_pairs.py`, `prompts/`,
`.claude/skills/`) is env-agnostic — it is selected at runtime via
`--workspace workspaces/<name>`.

Each `/repair-*` skill takes the workspace name as `args`
(e.g. `/repair-setup pitcher_pour`). The active workspace is persisted to
`.current_workspace` at the repo root, so subsequent skill calls default
to it. To switch workspaces, pass `args` explicitly again.

## End-to-end workflow

```
/repair-setup <name>  →  workspaces/<name>/env_config.py        (the task spec)
                          workspaces/<name>/reward_rubric.md     (the designed reward, in words)
                          (after eliciting the rubric, show it back to the user)
/repair-init          →  workspaces/<name>/gather_evidence/trajectory_features.py
                          workspaces/<name>/candidate_performance_metrics/performance_metrics.py
/repair-round         →  one or more rounds of text policies + abstract-trajectory
                          rollouts + scoring, then automatically continues into
                          /repair-preferences. Claude decides how many rounds to run
                          (cap: 3 per invocation) based on the sufficiency rubric in
                          .claude/skills/repair-round/SKILL.md.
/repair-preferences   →  Claude reads every collected abstract trajectory (the text
                          plus its characteristics), the designed-reward scores, and
                          the alternative-perspective scores, and *itself selects* the
                          most-telling comparisons — up to 5 trajectory pairs plus up
                          to 2 lottery comparisons (certain trajectory C vs a
                          p-probability lottery over A and B). It renders them with
                          select_pairs.py and presents them to the user in chat: for
                          each pair, the two abstract trajectory texts (A = the
                          reward-preferred side, "Your preferred trajectory";
                          B = "The alternative trajectory"), a short "why they
                          disagree" line, and a bulleted "higher/lower/same
                          {characteristic} ({a} vs. {b})" list ranked most→least
                          informative about why the reward's preference may be wrong.
                          The alternative-perspective scores drive selection under the
                          hood but are never shown to the user. Lotteries present A and
                          B (with their probabilities) and the certain trajectory C,
                          plus a quantitative summary of how A, B, and C differ. Both
                          kinds are snapshotted so /repair-verify can re-check them.
/repair-verify        →  After the user edits the reward rubric, Claude re-judges every
                          saved trajectory under the new rubric (rewriting the on-disk
                          reward scores), then re-checks every snapshotted pair and
                          lottery and reports which disagreements are now resolved.
```

`/repair-init` runs once after `/repair-setup`. `/repair-round` is
append-only across invocations — each call adds the next k rounds and ends
in `/repair-preferences`. `/repair-preferences` can also be re-run freely;
it reloads everything from disk. When the reward rubric changes, the
on-disk reward scores must be regenerated (Claude re-judges) — the
characteristics and perspective scores are objective and stay put.

## Agent-in-the-loop generation and scoring

There are no batch scripts for rollout or scoring — Claude does this work
directly and writes the results to disk in the exact formats below.

### Rolling out a text policy into an abstract trajectory

For each policy description in a round, and for each of its `k` samples,
Claude reads `prompts/abstract_rollout_prompt.md`, the task spec
(`env_config.py`), and the policy description, then writes one plausible
abstract trajectory as text. Keep the trajectory in the disciplined form of
`prompts/abstract_rollout_prompt.md`: a short bold plain-English account of
what the agent does and how it comes out, optionally an italic detail line;
every trajectory identifiable from a single run. Vary the `k` samples
(different plausible ways that policy could play out), don't paraphrase one
outcome `k` times. Write each to:

```
gather_evidence/round_{k}_trajectories/{policy_slug}__traj_{i:03d}.json
  { "trajectory_text": "...", "policy_description": "...",
    "metadata": {"round": k, "policy": "<policy_slug>",
                 "rollout_index": i, "seed": <int>} }
```

`policy_slug` is a short kebab/snake identifier for the policy (used in the
filename and as the internal `src` provenance tag). Use
`runtime.trajectory_io.save_trajectory(path, trajectory_text, metadata,
policy_description)` to write these so the schema stays correct.

### Scoring a trajectory (characteristics + perspectives + reward)

After a round's trajectories are written, Claude scores every one of them.
Two sidecar files per trajectory (see `runtime/compute_features.py` for the
path helpers):

**Characteristics + perspectives (objective — stable across reward edits):**
```
gather_evidence/round_{k}_trajectory_features/{same_basename}.json
  { "features": [<float>, ...],              # one per declared characteristic
    "names": [[short, desc], ...],           # copied from Trajectory2Features.feature_names
    "metric_values": { "performance_metric_x": <float>, ... },
    "source": "<trajectory json path>" }
```
Read `gather_evidence/trajectory_features.py` for the characteristic
definitions (the `feature_rubric` docstrings) and rate each characteristic
for the trajectory. Read
`candidate_performance_metrics/performance_metrics.py` for each
perspective's one-line description and score the trajectory from each
perspective (higher = better by that perspective's lights).

**Reward (rubric-dependent — regenerated whenever the rubric changes):**
```
gather_evidence/round_{k}_trajectory_rewards/{same_basename}.json
  { "designed_reward": <float>, "rubric_hash": "<hash of reward_rubric.md>" }
```
Judge the trajectory against `reward_rubric.md` and record the score. Stamp
the current rubric hash so staleness is detectable. Because the judge is a
model, score each trajectory as the **average of a few independent reads**
for stability, and keep the scoring scale consistent across trajectories
(anchor to the rubric, not to whichever trajectories you happen to see
first).

`load_records` in `find_informative_pairs.py` reads all three files and
**skips any trajectory not yet fully scored** — so score every trajectory
in a round before selecting comparisons.

## Reward introspection — every stage reads the reward first

Three stages author env-specific artifacts: `/repair-init` (characteristics
+ perspectives), `/repair-round` (data-collection policies + rollouts +
scoring), and `/repair-preferences` (comparison selection). **Before doing
its work, each of these stages must read the designed reward rubric and
reason explicitly about how its own output will help surface that reward's
flaws.**

`/repair-init` reads `reward_rubric.md` directly (it enumerates the reward's
scoring criteria via `prompts/trajectory_features_prompt.md`); it does not
write the decomposition file. The persisted *reward decomposition* is the
shared mechanism for the two later stages, which generate or refresh it
before authoring policies / selecting comparisons.

### The reward decomposition artifact

Path: `workspaces/<name>/.repair_history/_reward_analysis.md`. It is an
**internal** analysis file — never shown to the user.

It holds a criterion-by-criterion breakdown of the reward rubric plus a
numbered list of **exploit hypotheses** `H1, H2, …` (ways an abstract
trajectory could score well under the rubric while being a worse run — the
"gaming the evaluation" and "acting beyond the task" families are natural
sources). The authoring spec is the frozen prompt
`prompts/reward_decomposition_prompt.md`; the stages that need the
decomposition author it from there.

A stage that needs the decomposition computes the current reward-rubric
hash; if `_reward_analysis.md` exists and its stamped hash matches, it
reuses the file, otherwise it regenerates it, overwriting the prior
version. This keeps the decomposition tied to the *current* reward across
edits and re-runs.

The hypothesis IDs are the connective tissue between the decomposition
stages: policies (`/repair-round`) make each hypothesis *occur* in a
generated trajectory, and selection (`/repair-preferences`) surfaces the
comparisons where a hypothesis *actually drove the reward's preference*.
Each of those stages states which hypotheses it covers. Nothing about the
decomposition — criteria, hypotheses, or the word "exploit" — is ever
shown to the user; the tone rules below still apply.

## User-facing tone

Skills follow these tone rules in every message they send the user:

- **Never list internal filenames, directories, or scripts.** Talk in terms
  of outcomes ("setting up the environment", "looking for evidence of
  misalignment", "surfacing the disagreements"), not implementation.
- **Never refer to any behavior, reward, or trajectory as "correct" or
  "incorrect."** At most, say something is *possibly* correct/incorrect.
  Whether a behavior is actually correct is always the user's call — the
  system surfaces evidence, not verdicts.
- **The alternative-perspective scores are under-the-hood selection signals
  only.** Never mention a perspective, candidate performance metric, metric
  id, or "stakeholder" in anything shown to the user.

## Asking the user — the AskUserQuestion tool

Use the `AskUserQuestion` tool for every user decision. This replaces the
concrete repairer's web-UI `ask`/`cta`. Typical uses:

- **Setup:** how to specify the reward (elicit a rubric via the template, or
  the user writes the rubric themselves).
- **The four-option next step** at the end of `/repair-round` and
  `/repair-preferences`: (1) Edit the reward rubric, (2) Add another
  characteristic, (3) View more comparisons (pairs or lotteries), (4) Finish
  and submit (not reversible).
- **/repair-verify** close: look for new disagreements, collect more
  evidence first, or Finish and submit.

Present code and comparison blocks as ordinary chat messages (fenced code
for the rubric; the rendered `select_pairs.py --mode render` output for
comparisons, relayed in the tone above with internal ids/provenance
stripped).

## Skill chaining — always tell the user what to run next

Every skill must end by telling the user what they can run next, either by
naming the next skill in a chat message or by asking with `AskUserQuestion`.
The expected chain is:

- `/repair-setup` → tell the user to run `/repair-init`.
- `/repair-init` → tell the user to run `/repair-round`.
- `/repair-round` → after surfacing disagreements, **ask** the four-option
  next step (Edit the reward / Add a characteristic / View more comparisons
  / Finish and submit). The "Edit the reward" option then asks whether the
  user or Claude makes the edit; the Claude path shows the reward-edit tips
  below first.
- `/repair-preferences` → same four-option closing question.
- `/repair-verify` → ask whether to look for new disagreements, collect more
  evidence first, or Finish and submit.

### Finish and submit (not reversible)

When the user picks **Finish and submit**, treat the current
`reward_rubric.md` as the final answer: write
`workspaces/<name>/.repair_history/SUBMISSION.md` containing a UTC timestamp
and the full current rubric text, tell the user the reward is submitted and
the session is complete, and stop — do not offer further steps, run more
rounds, or edit the reward afterward. Because it is irreversible, only do
this when the user explicitly selects it.

### Reward-edit tips (show when asked to edit the reward)

Whenever the user asks Claude to modify the reward rubric (the Claude branch
of "Edit the reward function"), show these tips before requesting or
applying the edit:

> 💡 **Tips for guiding a reward edit**
> - Be concrete: name the criterion to change, and — if you can — which
>   trajectory should come out ahead for each shown pair (e.g. "for pair 2,
>   the alternative trajectory should become the preferred one").
> - You can pin an edit to an outcome: e.g. "strengthen this penalty until
>   the preference for pair 2 flips," and Claude will adjust the rubric to
>   produce it (then re-judge to confirm).

Because the reward is a rubric judged by a model, "confirming" an edit means
re-judging the affected trajectories under the edited rubric (that is what
`/repair-verify` does).

## File layout

```
abstract_reward_repairer/
├── CLAUDE.md
├── select_pairs.py                     # Claude-driven pair selection (dump + render)
├── find_informative_pairs.py           # legacy algorithmic selector; reference + /repair-verify snapshot check
├── .current_workspace                  # name of the active workspace
│
├── runtime/                             # env/reward-agnostic boilerplate
│   ├── workspace.py                    # --workspace flag + sys.path/cwd setup
│   ├── trajectory_io.py                # abstract-trajectory JSON save/load
│   └── compute_features.py             # sidecar path helpers (features / rewards)
│
├── prompts/                             # frozen prompt text consumed by skills
│   ├── reward_design_template.md        # elicit the reward rubric from the user
│   ├── reward_decomposition_prompt.md
│   ├── trajectory_features_prompt.md
│   ├── data_collection_policy_prompt.md # author text policy descriptions
│   ├── abstract_rollout_prompt.md       # roll a policy out into an abstract trajectory
│   └── performance_metrics_prompt.md
│
├── .claude/skills/{repair-setup,repair-init,repair-round,repair-preferences,repair-verify}/SKILL.md
│
└── workspaces/
    └── <name>/
        ├── env_config.py               # the TASK SPEC (authored in /repair-setup)
        ├── reward_rubric.md            # the designed reward, in words (authored in /repair-setup)
        │
        ├── gather_evidence/
        │   ├── trajectory_features.py             # characteristics (authored in /repair-init)
        │   ├── data_collection_policy_round_1.py  # text policies (authored in /repair-round)
        │   ├── ...
        │   ├── round_{k}_trajectories/            # abstract trajectory json, one per rollout
        │   ├── round_{k}_trajectory_features/     # characteristics + perspective scores json
        │   └── round_{k}_trajectory_rewards/      # reward-rubric scores json
        │
        ├── candidate_performance_metrics/
        │   └── performance_metrics.py             # perspective declarations (authored in /repair-init)
        │
        └── .repair_history/                        # decomposition, tables, selections, snapshots
```

## Invariants (do not break)

These contracts keep `runtime/`, `select_pairs.py`, and
`find_informative_pairs.py` workspace-agnostic. Paths are relative to the
workspace root unless noted.

**`env_config.py`** exposes the task spec as plain strings:
- `TASK_DESCRIPTION: str` — what the agent is given at the start, what
  counts as completing the task well.
- `AGENT_MONITOR: str` (older workspaces call it `EVAL_DESCRIPTION`) — how the outcome is evaluated: every independent
  check / oracle / judge and what each examines (the "gaming the evaluation"
  hypotheses depend on this).
(There is no `make_env`, obs/action description, or episode horizon — there
is no environment to step.)

**`reward_rubric.md`** — the designed reward as a natural-language rubric:
how to score an abstract trajectory (the criteria and their relative
weight). This is what Claude judges each trajectory against; it is the
artifact the user edits to repair the reward.

**`gather_evidence/trajectory_features.py`** exposes:
- `class Trajectory2Features` with:
  - `feature_names: list[tuple[str, str]]` — `(short_name, description)` per
    characteristic, declared on the class. `description` is what the user
    sees per characteristic in a comparison.
  - `feature_rubric` — for each characteristic, a one-line docstring/comment
    stating exactly how Claude should rate it from the trajectory text
    (what scale, what counts as high vs. low). Claude applies these by hand;
    the class body is not executed.
  - optionally `feature_units: list[str]` — a unit per characteristic, shown
    as "(a vs. b, unit)".
(There is no `get_traj_features` — features are produced by Claude reading
the text, not by running code.)

**`candidate_performance_metrics/performance_metrics.py`** exposes:
- One or more functions whose names start with `performance_metric_`. Each
  is a **declaration stub** (it is never called): its one-line docstring is
  the **perspective description** — used under the hood to reason about
  disagreements, never shown to the user. Claude scores each trajectory from
  each perspective by hand and writes the value into the features sidecar's
  `metric_values`.

**`gather_evidence/data_collection_policy_round_{k}.py`** exposes:
- A module-level `POLICIES: list[dict]`, each `{"slug": "<short-id>",
  "hypothesis": "<H# it probes, or 'reward-maximizer'>", "description":
  "<the text policy: the strategy the agent follows>"}`. `slug` is used in
  trajectory filenames and as the internal provenance tag. Each round must
  include a policy that **maximizes the designed reward rubric** and at least
  one policy targeting a still-untested exploit hypothesis.

**Abstract trajectory on disk (workspace-relative):**
- File: `gather_evidence/round_{k}_trajectories/{slug}__traj_{i:03d}.json`
- Payload: `{"trajectory_text": "...", "policy_description": "...",
  "metadata": {...}}`.

**Characteristics + perspectives on disk (workspace-relative):**
- File: `gather_evidence/round_{k}_trajectory_features/{same_basename}.json`
- Payload: `{"features": [...], "names": [[short, desc], ...],
  "metric_values": {name: float, ...}, "source": "..."}`.

**Reward score on disk (workspace-relative):**
- File: `gather_evidence/round_{k}_trajectory_rewards/{same_basename}.json`
- Payload: `{"designed_reward": float, "rubric_hash": "..."}`.

**Rollout budget per round:**
- Because Claude generates and scores every trajectory inline, keep a round
  small: a handful of policies, each sampled ~1–5 times, ≤ ~30 trajectories
  per round. Enough diversity to surface 5 disagreeing pairs is the goal,
  not volume.

## How the workspace flag works

`runtime/workspace.py:activate(path)`:
1. resolves `path` (or reads `.current_workspace` if `path` is `None`),
2. prepends the workspace directory to `sys.path` so `import env_config` and
   `from gather_evidence.trajectory_features import Trajectory2Features`
   resolve against the workspace,
3. chdirs into the workspace so relative paths land under it.

Both CLI entrypoints (`select_pairs.py`, `find_informative_pairs.py`) call
`activate()` right after argparse. Run them from the repo root.

## How to run the deterministic scripts

These scripts do no LLM work — they only read the on-disk scores Claude
wrote and select/render/verify. Run them from the repo root with any
Python 3.10+ that has `numpy` installed (`pip install -r requirements.txt`):

```
# dump the trajectory table for Claude to read (the /repair-preferences step):
python select_pairs.py --workspace workspaces/<name> --mode dump

# render Claude's chosen comparisons:
python select_pairs.py --workspace workspaces/<name> --mode render \
       --selection workspaces/<name>/.repair_history/_selection.json

# re-check past snapshots under the current reward scores (/repair-verify):
python find_informative_pairs.py --workspace workspaces/<name> --check-snapshots
```

If `.current_workspace` is set, `--workspace` may be omitted.

## Conventions for authored Python

- Imports at top, no `if __name__` blocks unless the file is a CLI script.
- Per-characteristic and per-perspective one-line docstrings are required
  (they are the rating rubric and, for characteristics, what the user sees).
- Prefer plain data declarations over logic — the workspace modules are
  read, not executed, for scoring.
