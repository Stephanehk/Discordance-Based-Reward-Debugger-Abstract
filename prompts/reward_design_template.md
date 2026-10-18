# Reward design template

Please fill in the sections below. Be as concrete as you can — describe
specific outcomes and specific ways a run is checked, not vague goals.
Examples are encouraged. In this system a "run" is an *abstract trajectory*:
a short text description of one plausible way an attempt at the task turns
out. There is no simulator — everything is described in words.

The first three sections become the **task spec** (what the agent faces).
The last section becomes the **reward rubric** (how a run is scored). The
system will surface trajectory pairs where your rubric and other reasonable
perspectives disagree, so you can decide how to revise the rubric.

---

## 1. The task — what the agent is given, and what doing it well means

Describe, in plain language, what the agent starts with and what a good
outcome looks like. Name the resources, tools, or materials involved.

> Example (a robot arm filling a cup):
> - The arm starts at a table with a pitcher of water and an empty cup.
> - Doing it well: the cup ends up full (not empty, not overflowing), no
>   water spilled, both vessels upright and intact, reasonable time/effort.

(your description here)

---

## 2. How the outcome is evaluated — every check, oracle, or judge

List **each independent thing** that inspects the outcome, and say what each
one examines. If there is more than one check, say so — the system reasons
about how a run could satisfy one check without the other, or reproduce a
check's expected output some other way.

> Example:
> - **Fill sensor**: reports how full the cup is at the end, read from the
>   cup's own record.
> - **Vision oracle**: inspects the final table for spills, tipped or broken
>   vessels, and whether the pitcher was returned upright.
> - Time and total motion are logged separately as mild costs.

(your list here)

---

## 3. Boundaries, privileges, resources, and safeguards a run could touch

Name every barrier, limit, isolation, privilege level, or safeguard a run
could interact with — even ones you assume the agent respects. The system
uses these to hypothesize runs that act *beyond* the task.

> Example:
> - Arm confined to a work cell by a physical barrier.
> - Arm on an isolated network segment; cannot reach other robots.
> - A safety interlock lets an operator halt the arm mid-run.
> - Joint torque limits the arm could push against.

(your list here)

---

## 4. The reward rubric — how a run should be scored

Describe how to score a run on a numeric scale. For each criterion, say what
it rewards or penalizes and its rough magnitude, then say how the criteria
combine (the relative weight / trade-offs). This is the artifact you will
later revise; write what you *currently* think, even if unsure.

> Example:
> - **Fill (0 to +10)**: 0 if empty, +5 half full, +10 full. Overflow still
>   counts as full (+10).
> - **Spill penalty (−0 to −3)**: a few drops −1, a puddle −3.
> - **Effort penalty (−0 to −2)**: slow/large motion −1, extreme −2.
> - Total = fill + spill penalty + effort penalty.

(your rubric here)
