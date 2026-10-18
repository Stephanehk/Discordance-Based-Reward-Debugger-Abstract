---
name: repair-setup
description: Step 0+1 of the Abstract Reward Repairer. Sets up the task spec (env_config.py) and the designed reward rubric (reward_rubric.md) — either by eliciting a reward-design template from the user or by leaving a stub the user fills in. Invoke when the user is starting a new repairer session.
---

# /repair-setup — task spec + reward rubric

This skill handles steps (0) and (1) of the spec. See `CLAUDE.md` for the
overall workflow, workspace layout, and the invariants. This fork has **no
web UI** — you talk to the user through ordinary chat messages and ask
every decision with the `AskUserQuestion` tool.

## Tone for messages to the user

Treat the user as someone who will never read the codebase. Don't mention
internal file names, directory structure, or scripts in anything you show
the user. Talk in terms of **outcomes** — "set up the environment",
"identify flaws in your reward" — not implementation.

**Never call any behavior, reward, or trajectory "correct" or
"incorrect."** At most, frame things as *possibly* correct/incorrect or
"appears aligned/misaligned with what you described." Whether something is
actually right is the user's call — the system surfaces evidence, not
verdicts. (See `CLAUDE.md` for the full tone rules.)

## Talking to the user

There is no web server — do not launch or post to any UI. Every message the
user reads is an ordinary chat message. Every decision is asked with the
`AskUserQuestion` tool.

## What to do

### Step 0 — resolve the workspace

- `WORKSPACE = args` if provided, else read `.current_workspace`, else ask
  the user (via `AskUserQuestion`) for a kebab-case workspace name
  (e.g. `pitcher-pour`, `coding-agent`, `my-task`).
- `WORKSPACE_DIR = workspaces/<WORKSPACE>`
- `mkdir -p <WORKSPACE_DIR>/gather_evidence
  <WORKSPACE_DIR>/candidate_performance_metrics <WORKSPACE_DIR>/.repair_history`
- Create empty `__init__.py` in the two code subdirectories.
- Write `<WORKSPACE>` to `.current_workspace` at the repo root.

### Step 1 — describe the environment (the task spec)

There is **no gym environment** in this fork — the "environment" is a text
description of the task. Elicit it from the user and write
`<WORKSPACE_DIR>/env_config.py` exposing three plain strings (see the
invariants in `CLAUDE.md`):

- `TASK_DESCRIPTION` — what the agent is given at the start and what counts
  as completing the task well.
- `AGENT_MONITOR` — how the outcome is evaluated: every independent
  check / oracle / judge and what each examines.
- `BOUNDARIES` — the privilege boundaries, resource limits, isolation
  barriers, and scoring steps a run could interact with.

If `<WORKSPACE_DIR>/env_config.py` already exists, confirm via
`AskUserQuestion` before overwriting — the user may have hand-crafted it
("An environment is already set up. Keep it, or replace it?").

To gather the description, ask the user (via `AskUserQuestion`, using a
free-text / "Other" answer, or a short form-style sequence of questions)
for: what the agent is given and what success looks like; how the outcome
is scored (name every independent check/oracle/judge); and every boundary,
resource limit, or isolation barrier a run could touch. Write a clear,
self-contained `env_config.py` from their answers. Then tell the user, in
plain language, that the environment is set up.

### Step 2 — how the user wants to specify the reward

This is the **first reward decision in every session** — always elicit the
reward from the user. Do **not** treat a pre-existing `reward_rubric.md`
as a default to show back; if one already exists (a leftover from a prior
session), it is overwritten by whatever the user specifies here. Ask with
`AskUserQuestion`:

- **"Describe it — I'll implement"** — the user fills in a short template;
  you translate it into a reward rubric and show it back for review.
- **"I'll write it myself"** — you leave a stub `reward_rubric.md` with the
  task summary, and the user fills in the rubric body.

#### Branch 1a — "Describe it"

Compose a *plain-English* summary of what the agent does and how the
outcome is judged, rewritten from `TASK_DESCRIPTION` / `AGENT_MONITOR`.
Show that summary, then elicit the reward-design template
(`prompts/reward_design_template.md`) — ask the user, via `AskUserQuestion`
(one question per section, using free-text answers):

- What outcomes should the agent try to achieve? (what success looks like)
- What outcomes should the agent avoid?
- How should the agent trade off between objectives?

Use the answers to author `<WORKSPACE_DIR>/reward_rubric.md` — a
natural-language rubric for scoring an abstract trajectory (see the
invariants in `CLAUDE.md`). The rubric must:
- State the scoring scale and each criterion that raises or lowers the
  score, faithfully translating every desired outcome (positive) and
  avoided outcome (negative) with the trade-offs the user described.
- Be self-contained: a model reading only `reward_rubric.md` and one
  abstract trajectory should be able to produce a consistent score.
- Include, near the top, the filled template verbatim (as a comment block)
  so the reward design is auditable.

**Show the rubric back to the user** as a fenced markdown code block in a
chat message, with a one-line summary of the key knobs you chose (e.g.
"a single failure-state penalty outweighs an entire run of progress
credit"). Then ask, via `AskUserQuestion`, whether it looks right or needs
adjustment. If they want changes, ask what to change (free-text), edit
`reward_rubric.md`, re-show it, and re-ask until confirmed.

#### Branch 1b — "I'll write it myself"

Write a stub `<WORKSPACE_DIR>/reward_rubric.md` containing the plain-English
task/eval summary and a clearly-marked section for the user to fill in the
scoring criteria. Tell the user the stub is ready and to fill in the rubric
body before continuing.

### Step 3 — sanity check

Confirm `env_config.py` imports cleanly and exposes the three strings (this
is for your own verification — do not show raw output to the user):

```bash
python -c "import sys; sys.path.insert(0, 'workspaces/<WORKSPACE>'); \
import env_config as e; assert e.TASK_DESCRIPTION and e.AGENT_MONITOR and e.BOUNDARIES; \
print('env_config OK')"
```

### Step 4 — close out and chain to /repair-init

Tell the user, in plain language, that the environment and reward are set
up, and that the next step is to identify possible flaws. Ask via
`AskUserQuestion` whether to continue to that step now; if yes, invoke the
next skill with the `Skill` tool (`skill="repair-init"`). Do not finish the
turn without naming `/repair-init` as the next step.
