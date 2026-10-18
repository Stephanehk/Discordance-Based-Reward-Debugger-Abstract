---
name: repair-verify
description: Check whether the updated reward rubric resolves the disagreements surfaced by past /repair-preferences runs. Re-judges every saved trajectory under the current reward_rubric.md, then re-checks every snapshotted pair and lottery and reports which disagreements are now resolved. Use after the user edits the reward and wants to confirm the fix.
---

# /repair-verify — confirm the reward fix addresses past disagreements

Whenever `/repair-preferences` runs, it saves a snapshot of the surfaced
pairs and lottery comparisons (which trajectories, the lottery `p`, and the
surfaced preference). This skill **re-judges** every saved trajectory under
the **current** reward rubric, then re-checks each snapshotted comparison and
reports which the new reward now agrees with — and which still disagree.

There is **no web UI** — talk to the user in ordinary chat messages and ask
any decision with the `AskUserQuestion` tool.

## Tone for messages to the user

The user will never read the codebase. Don't show file names, snapshot
paths, or scripts. The alternative-perspective scores are under-the-hood
signals only — never mention a perspective, metric, or "stakeholder". Speak
in outcomes: "every past disagreement is resolved" or "1 pair still
disagrees — here it is".

**Never call any behavior, reward, or trajectory "correct" or
"incorrect."** A pair being "resolved" means the reward's preference now
matches the surfaced one — not that the reward is "right". (See `CLAUDE.md`
for the full tone rules.)

## Resolve the workspace

The skill takes the workspace name as `args`. If empty, read
`.current_workspace`; if that doesn't exist, tell the user to run
`/repair-setup` first and stop. `WORKSPACE_DIR = workspaces/<WORKSPACE>`.

## What to do

### 1. Re-judge every saved trajectory under the current rubric

The reward is a rubric judged by a model, so verifying a fix means
**re-scoring**. For every trajectory on disk whose reward sidecar's
`rubric_hash` does not match the current `reward_rubric.md` hash, re-judge it
against the current `reward_rubric.md` and overwrite its reward sidecar
(`designed_reward`, new `rubric_hash`) — averaging a few independent reads
for stability, and keeping the scale consistent across trajectories (anchor
to the rubric). The characteristics and perspective sidecars are objective
and stay untouched. (See `CLAUDE.md` → "Agent-in-the-loop".)

If there are no snapshots to verify against, tell the user there's nothing
to verify yet and recommend running `/repair-round` to collect evidence
first, then stop.

### 2. Run the snapshot check

```bash
python find_informative_pairs.py --workspace workspaces/<WORKSPACE> --check-snapshots
```

The script loads every saved snapshot, re-scores both trajectories in every
pair (and `return(C)` vs `p·return(A) + (1−p)·return(B)` in every lottery)
using the **re-judged on-disk reward scores**, reports the resolved /
unresolved counts for pairs and lotteries separately, and pretty-prints any
comparisons that still disagree. The output is for your analysis — don't
paste it raw; relay the relevant parts in the tone rules.

### 3. Report the result

Tell the user, in plain language, how many previously-surfaced disagreements
are now resolved and how many still disagree (e.g. "3 of 4 are now resolved;
1 pair still disagrees — here it is").

### 3b. If some comparisons still disagree

Present each still-disagreeing comparison exactly as `/repair-preferences`
would present a fresh one: for a pair, the two abstract trajectory texts
(A = "Your preferred trajectory", B = "The alternative trajectory") and its
characteristic bullets from the script output, plus a one-sentence "why they
disagree" line; for a lottery, A/B (with probabilities) + certain C, a
quantitative summary, and the risk-attitude "why". No perspectives, no ids.

### 4. Always ask whether to continue

Ask via `AskUserQuestion` with three options:

- **Look for new disagreements** — re-analyse existing trajectories under the
  current reward, surfacing up to 5 pairs plus up to 2 lotteries (a new
  snapshot). Runs `/repair-preferences`.
- **Collect more evidence first** — roll out a fresh round of policies before
  re-analysing. Runs `/repair-round` (which auto-continues into
  `/repair-preferences`).
- **Finish and submit (not reversible)** — lock in the current reward as the
  final answer; ends the session.

### 5. Act on the answer

- **Look for new disagreements** → run `/repair-preferences` (its full
  contract — comparisons with "why" lines, closing four-option question).
- **Collect more evidence first** → run `/repair-round`.
- **Finish and submit (not reversible)** → follow "Finish and submit" in
  `CLAUDE.md`: write `<WORKSPACE_DIR>/.repair_history/SUBMISSION.md` (UTC
  timestamp + full current `reward_rubric.md`), confirm to the user that the
  reward is submitted and the session is complete, and stop.
- "Other" / decline → just stop.
