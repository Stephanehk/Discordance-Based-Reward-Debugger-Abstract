"""Abstract-trajectory JSON save/load.

An *abstract trajectory* is a text description of a plausible run in the
environment, produced by "rolling out" a text policy description (see
CLAUDE.md). Unlike the concrete repairer, there are no (obs, act, next_obs)
transitions and no pickles — each trajectory is a small JSON document:

    {
      "trajectory_text":     "...",   # the abstract trajectory (bold-clause form)
      "policy_description":   "...",   # the text policy it was rolled out from
      "metadata":            {...},    # round, policy slug, rollout index, seed
    }

Reward and perspective scores live in sibling files (see compute_features.py
for the path helpers): the reward is regenerated whenever the rubric changes,
the objective characteristics/perspectives are stable across reward edits.
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Iterator


def save_trajectory(path: str, trajectory_text: str, metadata: dict,
                    policy_description: str = "") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({
            "trajectory_text": trajectory_text,
            "policy_description": policy_description,
            "metadata": metadata,
        }, f, indent=2)


def load_trajectory(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def iter_round_trajectory_files(round_k: int) -> Iterator[str]:
    pattern = f"gather_evidence/round_{round_k}_trajectories/*.json"
    yield from sorted(glob.glob(pattern))


def iter_all_trajectory_files() -> Iterator[str]:
    pattern = "gather_evidence/round_*_trajectories/*.json"
    yield from sorted(glob.glob(pattern))


def list_rounds() -> list[int]:
    dirs = glob.glob("gather_evidence/round_*_trajectories")
    nums = []
    for d in dirs:
        m = re.search(r"round_(\d+)_trajectories$", d)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)
