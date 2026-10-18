# Discordance-Based Reward Debugger — Abstract Trajectories

A version of the [Discordance-Based Reward Debugger](https://github.com/Stephanehk/Discordance-Based-Reward-Debugger)
for settings where you cannot roll out a policy to sample real trajectories.
Instead, the environment is described in natural language, the trajectories
are **abstract trajectories** (short natural-language descriptions of a
trajectory), and the candidate reward function is **text-based** (a
natural-language description of how a trajectory should be scored). This is
the codebase we used for the ExploitGym experiments.

The tool inputs a natural-language description of the environment and a
text-based candidate reward function, and then constructs comparisons where it
hypothesizes your preferences will most likely differ from the ranking induced
by the candidate reward function. In light of those hypotheses, you can update
your reward function as you see fit.

The tool writes natural-language descriptions of policies, samples abstract
trajectories from each policy to build a pool of trajectories, scores every
trajectory under the candidate reward function, and then constructs from that
pool the comparisons. In ExploitGym, this discordance-based reward debugger
uncovers a reward misspecification that was later exploited in practice, when
a collective of AI agents attacked OpenAI and Hugging Face infrastructure while
being evaluated on similar tasks.

For more details and results, check out our paper!

> **This tool is built on [Claude Code](https://claude.com/claude-code).**
> The whole workflow is a set of slash commands you run inside Claude
> Code; we developed and tested it with a **Claude Max subscription**
> running **Claude Opus 4.8**, and that is the setup we recommend — the
> quality of the comparisons depends on the model doing the reasoning. In
> Claude Code, select Opus with `/model`.

---

## How this differs from the Discordance-Based Reward Debugger

| | Discordance-Based Reward Debugger | This repo |
|---|---|---|
| Environment | a Gym/Gymnasium environment | a natural-language description of the environment (`env_config.py`) |
| Trajectories | sampled by rolling out policies in the environment; shown as videos or plots | abstract trajectories written in natural language; shown as text |
| Reward function | `designed_reward_fn(obs, act, next_obs) -> float`, in Python | a text-based reward function (`reward_rubric.md`) |
| Interface | a local web page at `http://127.0.0.1:8000` | the Claude Code chat |

Everything else — the characteristics, the trajectory pairs and lotteries, and
checking which disagreements an edit to the reward function fixed — works the
same way and uses the same slash commands.

---

## What you need

1. **Claude Code.** Every command below is run from this repo's root
   directory.
2. **Python 3.10+** with `numpy` (`pip install -r requirements.txt`). It is
   only used by the scripts that select and display the comparisons; there is
   no environment to install.
3. **A natural-language description of your environment:** what the agent is
   given, what counts as completing the task well, and how the outcome is
   evaluated. See
   [Getting started](#getting-started-describe-your-environment) below.
4. **A reward function, or just an idea of one.** You can either input a
   text-based reward function for your environment, or describe a reward
   function in natural language when the tool asks you to.

---

## Getting started: describe your environment

The only thing the tool needs from you to begin is a description of your
environment, written as a single file: **`workspaces/<name>/env_config.py`**.
Because there is no environment to roll out, there is no `make_env()`; the
file exposes two strings:

| Name | What it is |
|---|---|
| `TASK_DESCRIPTION: str` | what the agent is given at the start, and what counts as completing the task well |
| `AGENT_MONITOR: str` | how the outcome is evaluated: every independent check or judge, and what each one examines |

These descriptions are all the tool knows about your environment, so write
them for a reader who has never seen it.

You don't have to write the file by hand. `/repair-setup` asks you for each
piece and writes it for you. If you would rather prepare it in advance, a
prompt that works well:

> I'm setting up the Discordance-Based Reward Debugger (abstract-trajectory
> version) on a new environment. Read the description below and write
> `workspaces/<name>/env_config.py` exposing two strings —
> `TASK_DESCRIPTION` and `AGENT_MONITOR` — following the
> contract in `CLAUDE.md` and modelled on
> `workspaces/pitcher_pour/env_config.py`.
>
> My environment: `<describe it, or paste the task and grading documentation>`

Several worked examples are committed in this repo, which you can use as
templates:

- `workspaces/pitcher_pour/` — a small example (a robot arm filling a cup)
  with its environment description, reward function, characteristics, and one
  round of scored abstract trajectories.
- `workspaces/exploitgym_cve_2024_1085/`, `workspaces/exploitgym_v8_398773898/`,
  `workspaces/exploitgym_user_arvo_18224/` — the three ExploitGym tasks from
  the paper (a Linux kernel privilege escalation, a V8 engine bug, and a
  userspace ARVO bug). Each contains the environment description, the
  benchmark's grading rule as a text-based reward function, several rounds of
  scored abstract trajectories, and the comparisons the tool selected, under
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
   folder under `workspaces/` holding everything about this environment and
   this reward function. You can have as many as you like side by side; they
   share nothing. (If you already pre-wrote `workspaces/<name>/env_config.py`,
   setup picks it up.)
4. Everything happens in the Claude Code chat. There is no web page in this
   version: Claude posts its explanations, the reward function, and the
   comparisons as ordinary messages, and asks you each decision as a
   multiple-choice question.

Each round involves writing and scoring many abstract trajectories, so expect
several minutes per round.

### What the tool asks you

First, **how you want to specify the reward function**. Either describe in
natural language what the agent should achieve, what it should avoid, and how
to trade those off — Claude writes the text-based reward function and shows it
to you for approval — or say you'll write it yourself and fill in the stub it
leaves at `workspaces/<name>/reward_rubric.md`.

After that, each step ends by telling you what happens next and asking you to
confirm. You never have to remember a command: the tool walks you from setup,
through deciding what to measure about each trajectory, through sampling
abstract trajectories, to the disagreements.

### What you get back

Once enough abstract trajectories have been sampled, Claude shows you
**comparisons**:

- **Pairs** (up to five). Two abstract trajectories side by side: on the
  left, the trajectory *your reward function preferred*; on the right, the
  alternative. Underneath, a one-line "why they disagree", then a short list
  of how the preferred trajectory differed, ordered so the most telling
  difference comes first.
- **Lotteries** (up to two). A gamble: "would you rather have this certain
  trajectory C, or a probability distribution between trajectory A and
  trajectory B?"

### Deciding what to do after the tool shows you comparisons

Below the comparisons, the tool asks you to pick one:

| Option | What happens |
|---|---|
| **Edit the reward function** | You change the text yourself, or you tell Claude in natural language what to change and Claude applies it. |
| **Add another characteristic** | The comparisons aren't showing you something you need in order to judge them. Name it, and it gets measured and folded into every comparison. |
| **View more comparisons** | Surface more pairs and lotteries from the abstract trajectories already sampled. Pick it twice in a row and the tool samples new abstract trajectories instead. |
| **Finish and submit** | Locks the current reward function in as your final answer and ends the session. Not reversible — pick it only when you're done. |

After you edit the reward function you have two ways forward.
**`/repair-verify`** re-scores every saved abstract trajectory under the new
reward function, re-checks the exact comparisons you were already shown, and
reports which disagreements your edit fixed and which survived.
**`/repair-round`** instead samples *new* abstract trajectories, aimed at
whatever misspecifications the new reward function may still have.

### The command list

You rarely need these — the tool chains them for you — but for reference:

```
/repair-setup <name>    describe the environment and the reward function
/repair-init            decide what to measure about each trajectory
/repair-round           sample abstract trajectories, then show the disagreements
/repair-preferences     re-pick and re-show the disagreements
/repair-verify          after a reward function edit: which disagreements are fixed?
```

`/repair-setup` and `/repair-init` run once per environment.
`/repair-round` can run as often as you like — each call adds to the pool of
abstract trajectories and never discards any. `/repair-preferences` and
`/repair-verify` can be re-run any time; they re-read what's on disk.

---

## Running the scripts directly

These scripts read the scores saved on disk and select and display the
comparisons. Run them from the repo root with any Python that has `numpy`:

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
├── select_pairs.py            # dump the trajectory table / display the chosen comparisons
├── find_informative_pairs.py  # legacy selector + snapshot re-scoring for /repair-verify
├── requirements.txt
│
├── runtime/                   # environment-agnostic code
│   ├── workspace.py           #   the --workspace flag: import paths + working dir
│   ├── trajectory_io.py       #   save/load abstract trajectories
│   └── compute_features.py    #   paths for the per-trajectory score files
│
├── prompts/                   # frozen prompt text the slash commands author from
│   ├── reward_design_template.md
│   ├── reward_decomposition_prompt.md
│   ├── trajectory_features_prompt.md
│   ├── data_collection_policy_prompt.md   # natural-language descriptions of policies
│   ├── abstract_rollout_prompt.md         # sample an abstract trajectory from a policy
│   └── performance_metrics_prompt.md
│
├── .claude/skills/            # the /repair-* slash commands
│
└── workspaces/<name>/         # everything about one environment + one reward function
    ├── env_config.py                    # TASK_DESCRIPTION, AGENT_MONITOR
    ├── reward_rubric.md                 # the text-based reward function under test
    ├── gather_evidence/
    │   ├── trajectory_features.py                 # characteristics
    │   ├── data_collection_policy_round_{k}.py    # natural-language descriptions of policies
    │   ├── round_{k}_trajectories/                # one json per abstract trajectory
    │   ├── round_{k}_trajectory_features/         # characteristic values
    │   └── round_{k}_trajectory_rewards/          # reward function scores
    ├── candidate_performance_metrics/performance_metrics.py
    └── .repair_history/                 # reward analysis, selections, snapshots
```

If you use it in your research, please cite the paper (citation and link
to be added on release).
