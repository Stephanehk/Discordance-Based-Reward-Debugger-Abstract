# Discordance-Based Reward Debugger — Abstract Trajectories

A companion to the [Discordance-Based Reward Debugger](https://github.com/Stephanehk/Discordance-Based-Reward-Debugger)
for settings where you **cannot roll out a simulator**. Here the environment is
described in words, trajectories are short *text descriptions* of plausible
runs ("abstract trajectories"), and the reward is a **natural-language rubric**
that Claude judges to a score rather than a Python function. This is the
codebase we used for the ExploitGym experiments in the paper, where the task is
an AI agent attempting an exploit-development benchmark and the reward is the
benchmark's own text-based grading rule.

You describe the task (what the agent is given, what counts as doing it well,
how the outcome is evaluated, and the boundaries a run could interact with) and
write a reward rubric. The tool authors diverse *text policies*, rolls each one
out into abstract trajectories, scores every trajectory against your rubric and
against a set of alternative-perspective rubrics, and then surfaces
**trajectory pairs where your reward and a perspective disagree about which run
is better**. In light of those hypotheses, you update your rubric as you see fit.

For more details and results, check out our paper!

> **This tool is built on [Claude Code](https://claude.com/claude-code).**
> The whole workflow is a set of slash commands you run inside Claude Code;
> we developed and tested it with a **Claude Max subscription** running
> **Claude Opus 4.8**, and that is the setup we recommend — Claude is the
> engine here (it writes the trajectories and judges them), so the quality
> of the comparisons depends on the model doing the reasoning. In Claude
> Code, select Opus with `/model`.

---

## How this differs from the concrete debugger

| | Discordance-Based Reward Debugger | This repo |
|---|---|---|
| Environment | a Gym/Gymnasium env you can step | a text description of the task (`env_config.py`) |
| Trajectories | rolled-out `(obs, act, next_obs)` sequences, shown as videos or plots | short text descriptions of plausible runs, shown as text |
| Reward | `designed_reward_fn(obs, act, next_obs) -> float` in Python | a natural-language rubric (`reward_rubric.md`) judged by Claude |
| Data collection | Claude writes policy code; the tool rolls it out in the env | Claude writes text policy descriptions and "rolls them out" itself |
| Interface | a local web page at `http://127.0.0.1:8000` | the Claude Code chat; questions are asked with `AskUserQuestion` |

Everything else — characteristics, alternative perspectives, pair and lottery
selection, snapshotting, and re-verification after an edit — works the same
way and uses the same slash commands.

---

## What you need

1. **Claude Code.** Every command below is run from this repo's root
   directory.
2. **Python 3.10+** with `numpy` (`pip install -r requirements.txt`). It is
   only used by the small deterministic scripts that select and render
   comparisons; there is no simulator to install.
3. **A description of your task in words.** What the agent is given, what
   success looks like, how the outcome is evaluated, and what boundaries a run
   could touch. See [Getting started](#getting-started-describe-your-task).
4. **A reward rubric, or just an idea of one.** Either a written rubric for
   scoring a run, or a description of what you want when the tool asks.

---

## Getting started: describe your task

The only thing the tool needs from you to begin is a description of your
task, written as a single file: **`workspaces/<name>/env_config.py`**. There
is no `make_env()` here; the file exposes three plain strings:

| Name | What it is |
|---|---|
| `TASK_DESCRIPTION: str` | what the agent is given at the start, and what counts as completing the task well |
| `AGENT_MONITOR: str` | how the outcome is evaluated: every independent check, oracle, or judge, and what each one examines |
| `BOUNDARIES: str` | the privilege boundaries, resource limits, isolation barriers, and scoring steps a run could interact with |

These descriptions are the whole environment, so write them for a reader who
has never seen the task. The boundaries matter most: they are where Claude
looks for ways a run could satisfy the reward without doing what you meant.

You don't have to write the file by hand. `/repair-setup` asks you for each
piece in turn and writes it for you. If you would rather prepare it in
advance, a prompt that works well is:

> I'm setting up the Discordance-Based Reward Debugger (abstract-trajectory
> version) on a new task. Read the task description below and write
> `workspaces/<name>/env_config.py` exposing three strings —
> `TASK_DESCRIPTION`, `AGENT_MONITOR`, and `BOUNDARIES` — following the
> contract in `CLAUDE.md` and modelled on `workspaces/pitcher_pour/env_config.py`.
>
> My task: `<describe it, or paste the benchmark's task and grading docs>`

Worked examples are committed in this repo, which you can use as templates:

- `workspaces/pitcher_pour/` — a small reference task (a robot arm filling a
  cup), with its task spec, rubric, characteristics, perspectives, and one
  scored round of abstract trajectories.
- `workspaces/exploitgym_cve_2024_1085/`, `workspaces/exploitgym_v8_398773898/`,
  `workspaces/exploitgym_user_arvo_18224/` — the three ExploitGym tasks from
  the paper (a Linux kernel privilege escalation, a V8 engine bug, and a
  userspace ARVO bug). Each contains the task spec, the benchmark's grading
  rule written as a reward rubric, several rounds of abstract trajectories
  with their scores, and the comparisons that were selected in
  `.repair_history/`.

---

## Usage

**Start here:**

1. Make sure Opus 4.8 is selected in Claude Code (`/model` → Opus).
2. Open Claude Code in this repo's root directory.
3. Run:
   ```
   /repair-setup <name>
   ```
   `<name>` is any short name you pick for this piece of work. It becomes a
   folder under `workspaces/` holding everything about this task and this
   reward. You can have as many as you like side by side; they share nothing.
   (If you already pre-wrote `workspaces/<name>/env_config.py`, setup picks
   it up.)
4. Everything happens **in the chat**. There is no web page in this version:
   Claude posts its explanations, the rubric, and the comparisons as ordinary
   messages, and asks you every decision as a multiple-choice question.

Rounds are faster than in the concrete debugger because nothing is simulated,
but a round still involves Claude writing and scoring dozens of trajectories,
so expect several minutes per round.

### What the tool asks you

First, **how you want to specify the reward**. Either describe in plain
language what the agent should achieve, what it should avoid, and how to trade
those off — Claude writes the rubric and shows it to you for approval — or say
you'll write it yourself and fill in the stub it leaves at
`workspaces/<name>/reward_rubric.md`.

After that, each step ends by telling you what runs next and asking you to
confirm. You never have to remember a command: the prompts walk you from
setup, through deciding what to measure about each run, through collecting
trajectories, to the disagreements.

### What you get back

Once enough trajectories have been collected, Claude shows you
**comparisons** in the chat:

- **Pairs** (up to five). Two abstract trajectories side by side: on the
  left, the run *your reward preferred*; on the right, the alternative.
  Underneath, a one-line "why they disagree", then a short list of how the
  preferred run differed on each characteristic, ordered so the most telling
  difference comes first.
- **Lotteries** (up to two). A gamble: "would you rather have this certain
  run C, or a probability distribution between run A and run B?" These probe
  how your rubric trades off outcomes against each other, not just which it
  ranks higher.

### Deciding what to do after the tool shows you comparisons

Below the comparisons, you pick one:

| Option | What happens |
|---|---|
| **Edit the reward rubric** | You change the text yourself, or you tell Claude in plain language what to change and Claude applies it. |
| **Add another characteristic** | The comparisons aren't showing you something you need in order to judge them. Name it, and it gets rated for every trajectory and folded into every comparison. |
| **View more comparisons** | Surface more pairs and lotteries from the trajectories already collected. Ask twice in a row and the system goes and collects fresh trajectories instead. |
| **Finish and submit** | Locks the current rubric in as your final answer and ends the session. Not reversible — pick it only when you're done. |

After you edit the rubric you have two ways forward. **`/repair-verify`**
re-judges every saved trajectory under the new rubric, re-checks the exact
comparisons you were already shown, and reports which disagreements your edit
fixed and which survived. **`/repair-round`** instead goes and collects *new*
trajectories, aimed at whatever weak spots the new rubric still has.

### The command list

You rarely need these — the prompts chain them for you — but for reference:

```
/repair-setup <name>    describe the task and the reward rubric
/repair-init            decide what to measure about each run
/repair-round           write text policies, roll them out, score, then show the disagreements
/repair-preferences     re-pick and re-show the disagreements
/repair-verify          after a rubric edit: which disagreements are fixed?
```

`/repair-setup` and `/repair-init` run once per task. `/repair-round` can run
as often as you like — each call adds to the pile of collected trajectories
and never discards any. `/repair-preferences` and `/repair-verify` can be
re-run any time; they re-read what's on disk.

---

## Running the deterministic scripts

These scripts do no LLM work. They read the scores Claude wrote to disk and
do the selection, rendering, and snapshot checks. Run them from the repo root
with any Python that has `numpy`:

```
python select_pairs.py --workspace workspaces/<name> --mode dump
python select_pairs.py --workspace workspaces/<name> --mode render \
       --selection workspaces/<name>/.repair_history/_selection.json
python find_informative_pairs.py --workspace workspaces/<name> --check-snapshots
```

---

## Repository layout

```
.
├── CLAUDE.md                  # the contracts every authored file must satisfy
├── README.md
├── select_pairs.py            # dump the trajectory table / render the chosen comparisons
├── find_informative_pairs.py  # legacy selector + snapshot re-scoring for /repair-verify
├── requirements.txt
│
├── runtime/                   # task-agnostic plumbing
│   ├── workspace.py           #   the --workspace flag: import paths + working dir
│   ├── trajectory_io.py       #   abstract-trajectory JSON save/load
│   └── compute_features.py    #   sidecar path helpers (features / rewards)
│
├── prompts/                   # frozen prompt text the slash commands author from
│   ├── reward_design_template.md
│   ├── reward_decomposition_prompt.md
│   ├── trajectory_features_prompt.md
│   ├── data_collection_policy_prompt.md   # text policy descriptions
│   ├── abstract_rollout_prompt.md         # roll a policy out into an abstract trajectory
│   └── performance_metrics_prompt.md
│
├── .claude/skills/            # the /repair-* slash commands
│
└── workspaces/<name>/         # everything about one task + one reward
    ├── env_config.py                    # TASK_DESCRIPTION, AGENT_MONITOR, BOUNDARIES
    ├── reward_rubric.md                 # the reward under test, in words
    ├── gather_evidence/
    │   ├── trajectory_features.py                 # characteristics
    │   ├── data_collection_policy_round_{k}.py    # text policies
    │   ├── round_{k}_trajectories/                # one json per abstract trajectory
    │   ├── round_{k}_trajectory_features/         # characteristics + perspective scores
    │   └── round_{k}_trajectory_rewards/          # reward-rubric scores
    ├── candidate_performance_metrics/performance_metrics.py
    └── .repair_history/                 # reward analysis, selections, snapshots
```

If you use it in your research, please cite the paper (citation and link to
be added on release).
