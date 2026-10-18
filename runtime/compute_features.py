"""Path helpers for the per-trajectory sidecar score files.

In the abstract repairer there is no batch featurizer: Claude reads each
abstract trajectory (as text) and writes its characteristics, perspective
scores, and reward score to sidecar JSON files. These helpers map a
trajectory path to the location of each sidecar so the selection code and
the skills agree on where they live.

For a trajectory at
    gather_evidence/round_{k}_trajectories/X.json
the sidecars are:
    gather_evidence/round_{k}_trajectory_features/X.json   (stable: characteristics + perspectives)
        {"features": [...], "names": [[short, desc], ...],
         "metric_values": {name: float, ...}, "source": "..."}
    gather_evidence/round_{k}_trajectory_rewards/X.json    (rubric-dependent: reward score)
        {"designed_reward": float, "rubric_hash": "..."}

The features file is objective — it does not change when the reward rubric
is edited. The rewards file is regenerated whenever the reward rubric
changes (its `rubric_hash` stamps which rubric produced it).
"""
from __future__ import annotations

import os


def _swap_subdir(traj_path: str, new_suffix: str) -> str:
    d, fname = os.path.split(traj_path)
    d2 = d.replace("_trajectories", new_suffix)
    return os.path.join(d2, fname)


def features_path_for(traj_path: str) -> str:
    """.../round_K_trajectories/X.json -> .../round_K_trajectory_features/X.json"""
    return _swap_subdir(traj_path, "_trajectory_features")


def rewards_path_for(traj_path: str) -> str:
    """.../round_K_trajectories/X.json -> .../round_K_trajectory_rewards/X.json"""
    return _swap_subdir(traj_path, "_trajectory_rewards")
