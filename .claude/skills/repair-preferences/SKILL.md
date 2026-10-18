---
name: repair-preferences
description: Present up to 5 trajectory pairs plus up to 2 lottery comparisons (certain trajectory C vs a p-probability lottery over A and B) to the user in chat. For each: the two abstract trajectory texts, a short "why they disagree" line, and one bullet per characteristic contrasting them.
---

# /repair-preferences — surface preference-label disagreements

## ⚠ CORE CONTRACT (do not skip)

**Every comparison the render returns — up to 5 PAIR blocks and up to 2
LOTTERY blocks — MUST be presented to the user in chat, each with its own
one-sentence "why they disagree" interpretation.** Then **always** close
with the four-option `AskUserQuestion` (edit the reward / add a
characteristic / view more / finish and submit). The skill has not delivered
its output until that question is asked. There is **no web UI** — the
presentation is your chat message; the render's stdout is your source, not
something to paste raw.

## Tone for messages to the user

The user will never read the codebase. Don't show file names, ids, or
provenance. The alternative-perspective scores are **under-the-hood
selection signals only** — never mention a perspective, metric, or
"stakeholder".

**Never call any behavior, reward, or trajectory "correct" or
"incorrect."** (See `CLAUDE.md` for the full tone rules.) Post brief plain
chat status lines at key transitions ("Analysing the collected
trajectories.", "Selecting the most informative comparisons.").

## Resolve the workspace

The skill takes the workspace name as `args`. If empty, read
`.current_workspace`; if that doesn't exist, tell the user to run
`/repair-setup` first and stop. `WORKSPACE_DIR = workspaces/<WORKSPACE>`.

## Preconditions

- At least one round of scored evidence exists. If none, tell the user to
  run `/repair-round` first and stop.

## Procedure

### 1. Select the comparisons — you choose them, not an algorithm

Comparison selection is **Claude-driven**. You read every collected
trajectory — its text **and** its characteristics — plus the designed-reward
score and every alternative-perspective score, and pick the comparisons most
useful for the user to see.

**Informativeness is judged against the reward rubric and its suspected
flaws.** Read `<WORKSPACE_DIR>/reward_rubric.md` and the reward decomposition
`<WORKSPACE_DIR>/.repair_history/_reward_analysis.md` (its criterion
breakdown and exploit hypotheses `H1, H2, …`). A comparison is informative to
the extent that it exposes one of those suspected flaws — a case where a
specific rubric criterion or exploit hypothesis drives the reward to prefer
a trajectory the user would plausibly reject (e.g. the reward prefers a
trajectory that games the fill record over one that genuinely fills the
cup). Comparisons you can tie to a criterion or hypothesis outrank generic
disagreements.

**1a-pre. Refresh the reward decomposition and re-judge if stale.** Ensure
`_reward_analysis.md` matches the current rubric hash; if the user edited
the rubric since it was written, regenerate it following
`prompts/reward_decomposition_prompt.md`, **and re-judge every trajectory's
reward sidecar under the current `reward_rubric.md`** (see `CLAUDE.md` →
"Agent-in-the-loop") so selection reasons about the current reward. All this
reasoning stays **internal** — the user-facing text still follows the tone
rules (no criterion names, perspectives, or "exploit").

**1a. Dump the trajectory table.**

```bash
python select_pairs.py --workspace workspaces/<WORKSPACE> --mode dump
```

This writes `<WORKSPACE_DIR>/.repair_history/_trajectory_table.txt` (one row
per trajectory: a stable id `T001…`, its designed-reward score, every
perspective score, and every characteristic) plus `_pair_pool.json` (id →
trajectory path).

**1b. Read the table AND the trajectory texts.** Read the table with the
Read tool, then read the actual trajectory texts at the paths in
`_pair_pool.json` — the texts are what let you reason about what happened.

For **pairs**, identify head-to-head comparisons where the designed reward
ranks the two trajectories oppositely to another perspective the user
plausibly cares about, or that otherwise best expose where the reward is
flawed. **Prioritize pairs you can tie to a specific rubric criterion or
exploit hypothesis `H#`**: the strongest comparison is one where the reward
prefers A because a criterion fired on a proxy (e.g. the fill record) while
B actually achieves the underlying outcome — confirm the decoupling in the
proxy vs. true-outcome characteristic columns.

For **lotteries**, identify triples `(C, A, B)` where A is clearly good and
B clearly bad under some lens, and C is a midpoint. Let `p` = probability of
the **good** branch (A). Pick `p` so the choice between C and the lottery is
genuinely difficult: compute the designed-reward indifference point `p* =
(return(C) − return(B)) / (return(A) − return(B))`, then move slightly off
it (usually onto the C-preferring side) so the reward gives a small-but-real
preference a human might reverse. Don't hardcode a round number — compute
it, and justify it in the selection file. Two lotteries → prefer two
*different shapes* over two `p` values on one shape.

Use the internal `src` column only to judge diversity; never reveal round or
policy to the user.

**1c. Write the selection and render it.** Write
`<WORKSPACE_DIR>/.repair_history/_selection.json`:

```json
{
  "pairs": [
    {"a": "T012", "b": "T034",
     "characteristics": ["<short_name_1>", "<short_name_2>", "<short_name_3>"]},
    {"a": "T100", "b": "T077",
     "characteristics": ["<short_name_1>", "<short_name_2>"]}
  ],
  "lotteries": [
    {"c": "T020", "a": "T005", "b": "T088", "p": 0.6,
     "justification": "what makes THIS p the hard one for the human"}
  ]
}
```

For each pair, rank the `"characteristics"` — the characteristic
`short_name`s (the table's characteristic columns), ordered most→least
informative about *why the designed reward's preference may be wrong for this
pair*. Put the proxy and true-outcome characteristics that explain the
preference first. Then render:

```bash
python select_pairs.py --workspace workspaces/<WORKSPACE> --mode render \
       --selection workspaces/<WORKSPACE>/.repair_history/_selection.json
```

The render orients A = the reward-preferred side, prints both abstract
trajectory texts, prints one bullet per characteristic ("higher/lower/same …
(a vs. b, unit)") in your chosen order, renders each lottery (A/B with
probabilities, certain C, and the reward's preference), and writes a
snapshot `pref_round_*.json` so `/repair-verify` can recheck later.

(If the table holds fewer than 3 trajectories forming any useful disagreeing
comparison, skip to Step 3 and tell the user there's not yet enough evidence
to surface diverse disagreements.)

### 2. Present the comparisons to the user

Present **only** the comparisons (pairs first, in render order; then
lotteries) — no characteristic key, overall summary, or misalignment
orientation. For each comparison, relay the render's content in your chat
message:

- **Pair:** show Trajectory A as **"Your preferred trajectory"** and
  Trajectory B as **"The alternative trajectory"** (the two abstract
  trajectory texts, verbatim from the render), then one sentence — "Why they
  disagree:" — naming the trade-off (what your preferred trajectory gains and
  what it gives up; no perspectives/metrics), then the render's
  characteristic bullets in order. Show the **first pair in full**; the rest
  may be more compact but must still include both texts and the "why" line.
- **Lottery:** show Trajectory A (good branch) and Trajectory B (bad branch)
  with their probabilities, and the certain Trajectory C; a **quantitative**
  2–3 sentence summary of how A, B, and C differ (actual characteristic
  values with units — not "safe"/"smooth"/"aggressive"); and one sentence on
  the risk-attitude trade-off between C and the lottery.

Never mention a perspective, metric, or "stakeholder"; never re-introduce
ids, round numbers, or policy names.

### 3. Always close by asking what to do next

Ask via `AskUserQuestion` with these four options:

- **Edit the reward rubric** — modify the reward to reflect what you actually
  want, based on the disagreements above.
- **Add another characteristic** — add a new characteristic to the trajectory
  summary so comparisons show more detail.
- **View more comparisons** — surface additional pairs or lotteries from the
  evidence already collected.
- **Finish and submit (not reversible)** — lock in the current reward as the
  final answer; ends the session.

### 4. Act on the answer

- **Edit the reward rubric** → ask (via `AskUserQuestion`) whether the user
  or Claude makes the edit.
  - *Claude makes it:* first show the reward-edit tips (below), then ask the
    user (free-text) to describe the change, apply it to
    `reward_rubric.md` with `Edit`, show the new rubric, and **re-judge**
    the affected trajectories' reward sidecars under the new rubric (new
    `rubric_hash`). Then re-present (re-run this skill) or suggest
    `/repair-verify`.
  - *User edits it themselves:* tell them that when ready they can run
    `/repair-verify` to re-check the surfaced pairs, or `/repair-round` for
    fresh evidence under the new reward.
- **Add another characteristic** → ask (free-text) what characteristic they
  want, edit `gather_evidence/trajectory_features.py` to add it, **rate the
  new characteristic on every existing trajectory** (append it to each
  features sidecar's `features`/`names`), then re-present (Steps 1–3) with it
  visible.
- **View more comparisons** → depends on whether this is the *first* "View
  more" in a row or the *second consecutive* one (since the last reward edit,
  characteristic add, or fresh `/repair-round`).
  - **Second consecutive click → hand off to `/repair-round`.** The existing
    trajectories are largely exhausted of distinct disagreements; invoke
    `Skill(skill="repair-round")`. The reward is unchanged, so the new
    round's policies see the same reward that produced the disagreements —
    the intended effect. Reset the counter on any reward edit, characteristic
    add, or fresh round.
  - **First click → re-select within existing evidence.** Re-run Step 1, but
    treat every previously-shown trajectory as one whose reward ranking the
    user has now *agreed with*: don't re-surface a pair whose disagreement is
    already inferable from the agreed set; prefer pairs that introduce a
    trajectory the user hasn't seen and a new axis of disagreement; for
    lotteries, explore a different `(C, A, B, p)` shape. Then present per
    Steps 2–3.
- **Finish and submit (not reversible)** → follow "Finish and submit" in
  `CLAUDE.md`: write `<WORKSPACE_DIR>/.repair_history/SUBMISSION.md` (UTC
  timestamp + full current `reward_rubric.md`), tell the user the reward is
  submitted and the session is complete, and stop.

#### Reward-edit tips (show when Claude is about to edit the reward)

> 💡 **Tips for guiding a reward edit**
> - Be concrete: name the criterion to change, and — if you can — which
>   trajectory should come out ahead for each shown pair (e.g. "for pair 2,
>   the alternative trajectory should become the preferred one").
> - You can pin an edit to an outcome: e.g. "strengthen this penalty until
>   the preference for pair 2 flips," and Claude will adjust the rubric to
>   produce it (then re-judge to confirm).

## When the user edits the reward and asks you to recheck

Re-run this skill; the trajectory texts on disk are unchanged, so it just
re-judges the reward sidecars under the new rubric and re-selects. Or use
`/repair-verify` to re-check the previously-surfaced comparisons directly.
