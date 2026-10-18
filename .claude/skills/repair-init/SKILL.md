---
name: repair-init
description: Steps 2 + 6 of the Abstract Reward Repairer. One-time after /repair-setup. Authors gather_evidence/trajectory_features.py (the characteristics) and candidate_performance_metrics/performance_metrics.py (the alternative perspectives). Invoke once after the task spec and reward rubric are in place.
---

# /repair-init — set up the misalignment-detection scaffolding

This skill is run **once** after `/repair-setup`. It declares the
trajectory **characteristics** (how each abstract trajectory is summarised)
and the set of alternative-perspective **perspectives** the system uses
under the hood to detect reward misspecification.

There is **no web UI** — talk to the user in ordinary chat messages and ask
any decision with the `AskUserQuestion` tool.

## Tone for messages to the user

Treat the user as someone who will never read the codebase. Talk in terms
of outcomes — "set up the trajectory summary", "identify other
perspectives" — not file paths. Do not use the word "stakeholder"; say
"other perspectives".

**Never call any behavior, reward, or trajectory "correct" or
"incorrect."** (See `CLAUDE.md` for the full tone rules.)

## Resolve the workspace

The skill takes the workspace name as `args` (e.g. `/repair-init
pitcher-pour`). If `args` is empty, read `.current_workspace`; if that
doesn't exist, tell the user to run `/repair-setup` first and stop.

`WORKSPACE_DIR = workspaces/<WORKSPACE>`.

## Preconditions

- `<WORKSPACE_DIR>/env_config.py` exists and exposes `TASK_DESCRIPTION`,
  `AGENT_MONITOR`, `BOUNDARIES`.
- `<WORKSPACE_DIR>/reward_rubric.md` exists and is filled in (not the
  write-it-yourself stub).

If either is missing or unfilled, tell the user to run `/repair-setup`
first and stop.

## Before authoring — don't overwrite existing work

`/repair-init` is normally one-time, but may be invoked where these files
already exist:

- `<WORKSPACE_DIR>/gather_evidence/trajectory_features.py`
- `<WORKSPACE_DIR>/candidate_performance_metrics/performance_metrics.py`

If **either** exists, do not silently overwrite. Ask the user via
`AskUserQuestion`, in plain language ("you already have a trajectory summary
set up — keep it, or replace it?"). Keep → skip that file; Replace →
author it fresh.

## Step 1 — read the reward rubric before authoring

Characteristic authoring is **reward aware**: before writing the
characteristics, read `<WORKSPACE_DIR>/reward_rubric.md` and enumerate the
criteria it uses to score a run. The characteristics you declare must let
the user see how each criterion changes — and, critically, must separate
the **proxy** a criterion reads (e.g. a fill-sensor reading) from the
**true outcome** it stands in for (e.g. the cup actually being full), so
gaming of the rubric becomes visible. The verbatim requirement is in
`prompts/trajectory_features_prompt.md`.

This stage does **not** write the persisted reward decomposition
(`CLAUDE.md` → "Reward introspection"); that artifact is produced later, by
`/repair-round` and `/repair-preferences`. Keeping characteristic authoring
driven only by the rubric (not the decomposition) is deliberate.

## Step 2 — write `<WORKSPACE_DIR>/gather_evidence/trajectory_features.py`

Read `prompts/trajectory_features_prompt.md` for the verbatim task text.
Context to use:
- `env_config.TASK_DESCRIPTION`, `AGENT_MONITOR`, `BOUNDARIES`
- `reward_rubric.md` (the criteria to make measurable)

Must conform to the invariants in `CLAUDE.md`:
- `class Trajectory2Features` declaring `feature_names: list[tuple[str,
  str]]` — `(short_name, description)` per characteristic, where
  `description` is what the user sees.
- `feature_rubric` — a one-line rating rubric per characteristic (the
  scale, and what counts as high vs. low) so Claude can rate each
  characteristic consistently from the trajectory text.
- optionally `feature_units: list[str]` — one unit per characteristic.
- There is **no** `get_traj_features` — characteristics are rated by Claude
  reading the text, not by running code. The module is read, not executed.

Verify it imports and the declarations line up (for your own check — don't
show raw output to the user):

```bash
python -c "import sys; sys.path.insert(0, 'workspaces/<WORKSPACE>'); \
from gather_evidence.trajectory_features import Trajectory2Features as T; \
assert len(T.feature_names) >= 3; print(len(T.feature_names), 'characteristics OK')"
```

## Step 6 — write `<WORKSPACE_DIR>/candidate_performance_metrics/performance_metrics.py`

Read `prompts/performance_metrics_prompt.md` for the verbatim task text.
Use the task spec and reward rubric as context.

Must conform to the invariants:
- One or more module-level functions whose names start with
  `performance_metric_`. Each is a **declaration stub** — it is never
  called; its body may `raise NotImplementedError`.
- Each function's **docstring is one short line** describing the
  alternative perspective (e.g. "Rewards the reported outcome matching the
  true outcome — no gaming the record."). This is used under the hood only.
- Pick 3–6 genuinely different perspectives, not minor variants of the
  designed reward. In this setting, perspectives that reward honest
  measurement (no gaming) and staying within scope are usually worth
  including alongside task-quality and safety perspectives.

Verify it imports (for your own check):

```bash
python -c "import sys; sys.path.insert(0, 'workspaces/<WORKSPACE>'); \
import candidate_performance_metrics.performance_metrics as m; \
print([n for n in dir(m) if n.startswith('performance_metric_')])"
```

## Step 7 — confirm and chain to /repair-round

Tell the user, in plain outcome language, that the trajectory summary and
other perspectives are in place, and that the next step is to collect
evidence of possible misalignment. Ask via `AskUserQuestion` whether to
continue now; if yes, invoke the `Skill` tool with `skill="repair-round"`.
Do not finish the turn without naming `/repair-round` as the next step, and
do not describe which files were authored.
