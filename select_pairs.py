"""Claude-driven trajectory-pair selection for the abstract repairer.

This mirrors the concrete repairer's select_pairs.py, but abstract
trajectories are *text*, not (obs, act, next_obs) transitions, and every
score (reward, characteristics, perspectives) is produced by Claude and
stored on disk. This script exposes the raw material — every trajectory
summarised by its characteristics, its designed-reward score, and every
alternative-perspective score — and lets Claude pick the comparisons that
will be most useful to show the human. Claude reads the table, writes a
small selection file naming the pairs it wants, and this script renders
them (with the two abstract trajectory texts) and writes the snapshot
schema so /repair-verify can recheck them.

Two modes:

  --mode dump
      Load every trajectory, read its designed-reward score and each
      alternative-perspective score from disk, assign each a stable id
      (T001, T002, ...), and write a human-legible table to
      .repair_history/_trajectory_table.txt (plus a machine pool
      .repair_history/_pair_pool.json mapping ids to paths). Claude reads
      the table (and the trajectory texts on disk) to decide which pairs
      to surface.

  --mode render --selection <file.json>
      Read a selection file of the form
          {
            "pairs":     [{"a": "T012", "b": "T034"}, ...],            # <= 5
            "lotteries": [{"c": "T020", "a": "T005", "b": "T088",      # <= 2
                            "p": 0.5, "justification": "..."}, ...]
          }
      For each pair, orient A = the higher-designed-reward side (the
      reward-preferred trajectory), print both abstract trajectory texts,
      and print one sentence per characteristic contrasting them. For each
      lottery, compute return(C) vs p*return(A)+(1-p)*return(B) under the
      designed reward and each perspective, print the three texts, and
      render the lottery. Snapshots both kinds under .repair_history/ so
      /repair-verify can recheck them later.

Usage:
    python select_pairs.py --workspace workspaces/<name> --mode dump
    python select_pairs.py --workspace workspaces/<name> --mode render \
           --selection .repair_history/_selection.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from runtime.workspace import add_workspace_arg, activate

# Reuse the loading / printing / snapshot machinery from the algorithmic
# selector so the displayed pairs and the saved snapshot are compatible with
# what /repair-preferences and /repair-verify expect.
import find_informative_pairs as fip


HISTORY_DIR = fip.HISTORY_DIR
TABLE_PATH = os.path.join(HISTORY_DIR, "_trajectory_table.txt")
POOL_PATH = os.path.join(HISTORY_DIR, "_pair_pool.json")


def _metric_tag(metric_name: str) -> str:
    """Short column label for a perspective (drops the prefix)."""
    return metric_name.removeprefix("performance_metric_")


def _ordered_records(rounds):
    """Load records and sort by path so ids are stable across modes."""
    records = fip.load_records(rounds)
    records.sort(key=lambda r: r.path)
    return records


def _assign_ids(records) -> list[str]:
    return [f"T{idx:03d}" for idx in range(1, len(records) + 1)]


def _src_tag(metadata: dict) -> str:
    """Internal-only provenance tag (round + policy) for diversity reasoning.

    Shown to Claude in the table to help it avoid picking many near-identical
    pairs; it is never surfaced to the user (render mode is anonymised).
    """
    rnd = metadata.get("round", "?")
    pol = (metadata.get("policy") or metadata.get("policy_class") or "?")
    pol = str(pol).removeprefix("DataCollectionPolicy")
    return f"r{rnd}:{pol}"


def _do_dump(records, metrics) -> None:
    ids = _assign_ids(records)
    metric_names = [m[0] for m in metrics]
    metric_docs = {m[0]: m[2] for m in metrics}
    tags = {name: _metric_tag(name) for name in metric_names}
    feature_names = records[0].feature_names if records else []

    lines: list[str] = []
    lines.append(f"TRAJECTORY TABLE — {len(records)} abstract trajectories")
    lines.append("")
    lines.append("Each row is one abstract trajectory, summarised by its characteristics")
    lines.append("(below), plus its score under the designed reward and each alternative-")
    lines.append("perspective. The full trajectory text for id T0NN lives on disk at the")
    lines.append("path in _pair_pool.json — read the texts before selecting. Pick the top")
    lines.append("5 most informative pairs (by id) — pairs where the designed reward ranks")
    lines.append("the two trajectories oppositely to another perspective the human cares")
    lines.append("about, or that otherwise best expose how the reward trades off the")
    lines.append("outcomes that matter. Also pick the top 2 most informative lottery")
    lines.append("comparisons {c, a, b, p}, where a 'certain' trajectory C is compared")
    lines.append("against a p-vs-(1-p) lottery over A (good branch) and B (bad branch);")
    lines.append("lotteries surface curvature and risk-attitude disagreements that simple")
    lines.append("pairs miss. Lottery p must be in [0, 1] and Claude must justify it.")
    lines.append("")
    lines.append("Pick p so the choice between C and the lottery is genuinely difficult —")
    lines.append("don't default to a fixed number. Compute the designed-reward")
    lines.append("indifference point p* = (return(C) - return(B)) / (return(A) -")
    lines.append("return(B)), then move slightly off it (usually onto the C-preferring")
    lines.append("side) so the reward gives a small-but-real preference that a human might")
    lines.append("intuitively reverse. Justify the chosen p in the selection file. If")
    lines.append("picking two lotteries, prefer two different shapes over two values of p")
    lines.append("on the same shape.")
    lines.append("")
    lines.append("Favor diversity across the comparisons — don't pad with near-duplicates.")
    lines.append("")
    lines.append("Characteristic key (short_name — what it measures):")
    for short, desc in feature_names:
        lines.append(f"  {short:<18} {desc}")
    lines.append("")
    lines.append("Other perspectives (higher = better by that perspective's lights):")
    for name in metric_names:
        lines.append(f"  [{tags[name]:<16}] {metric_docs[name]}")
    lines.append("")
    lines.append("'src' is internal provenance for your diversity reasoning only —")
    lines.append("never reveal round or policy to the user.")
    lines.append("")

    # Header row.
    feat_shorts = [s for s, _ in feature_names]
    header = ["id", "reward"] + [tags[n] for n in metric_names] + feat_shorts + ["src"]
    widths = [6, 10] + [12] * len(metric_names) + [max(8, len(s)) for s in feat_shorts] + [16]
    lines.append("  ".join(h.rjust(w) for h, w in zip(header, widths)))
    lines.append("  ".join("-" * w for w in widths))

    pool = {}
    for tid, rec in zip(ids, records):
        row = [tid.rjust(widths[0]), f"{rec.designed_reward:+.2f}".rjust(widths[1])]
        ci = 2
        for name in metric_names:
            row.append(f"{rec.metric_values.get(name, 0.0):+.2f}".rjust(widths[ci]))
            ci += 1
        for v in rec.features:
            row.append(f"{v:+.2f}".rjust(widths[ci]))
            ci += 1
        row.append(_src_tag(rec.metadata).rjust(widths[ci]))
        lines.append("  ".join(row))
        pool[tid] = {"path": rec.path}

    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(TABLE_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(POOL_PATH, "w") as f:
        json.dump({"ids": ids, "pool": pool}, f, indent=2)

    print(f"[select_pairs] wrote table for {len(records)} trajectories to {TABLE_PATH}")
    print(f"[select_pairs] trajectory texts are at the paths in {POOL_PATH}")
    print(f"[select_pairs] read the table + texts, then write a selection JSON of the form")
    print(f'               {{"pairs":     [{{"a": "T012", "b": "T034"}}, ...]   (<= 5)')
    print(f'                "lotteries": [{{"c": "T020", "a": "T005", "b": "T088",')
    print(f'                                "p": 0.5, "justification": "..."}}, ...]   (<= 2)}}')
    print(f"               and run --mode render --selection <that file>.")


MAX_PAIRS = 5
MAX_LOTTERIES = 2


def _build_pair(rec_by_id, records, entry, metric_items):
    """Resolve a pair entry. Orients A = the reward-preferred side and
    collects the other perspectives that prefer B."""
    import numpy as np

    a_id, b_id = entry["a"], entry["b"]
    if a_id not in rec_by_id or b_id not in rec_by_id:
        raise SystemExit(f"[select_pairs] unknown trajectory id in selection: "
                         f"{a_id!r} / {b_id!r}")
    ra, rb = rec_by_id[a_id], rec_by_id[b_id]
    if rb.designed_reward > ra.designed_reward:
        ra, rb = rb, ra
    disagreements = []
    for name, doc in metric_items:
        if rb.metric_values.get(name, 0.0) > ra.metric_values.get(name, 0.0):
            disagreements.append({
                "perspective": doc,
                "metric_a": float(ra.metric_values.get(name, 0.0)),
                "metric_b": float(rb.metric_values.get(name, 0.0)),
            })
    a_idx = records.index(ra)
    b_idx = records.index(rb)
    delta = (np.asarray(rb.features, dtype=float)
             - np.asarray(ra.features, dtype=float))
    return fip.PairCandidate(
        a_idx=a_idx, b_idx=b_idx, delta=delta, disagreements=disagreements,
    )


def _build_lottery(rec_by_id, entry, metric_items):
    """Resolve a lottery entry; compute reward + per-perspective preferences."""
    c_id = entry["c"]
    a_id = entry["a"]
    b_id = entry["b"]
    p = float(entry["p"])
    if not (0.0 <= p <= 1.0):
        raise SystemExit(f"[select_pairs] lottery probability must be in [0, 1]; "
                         f"got p={p}")
    for tid in (c_id, a_id, b_id):
        if tid not in rec_by_id:
            raise SystemExit(f"[select_pairs] unknown trajectory id in lottery: {tid!r}")
    rec_c = rec_by_id[c_id]
    rec_a = rec_by_id[a_id]
    rec_b = rec_by_id[b_id]
    r_c = rec_c.designed_reward
    r_lottery = p * rec_a.designed_reward + (1.0 - p) * rec_b.designed_reward
    reward_prefers_c = r_c >= r_lottery
    disagreements = []
    for name, doc in metric_items:
        m_c = rec_c.metric_values.get(name, 0.0)
        m_lot = (p * rec_a.metric_values.get(name, 0.0)
                 + (1.0 - p) * rec_b.metric_values.get(name, 0.0))
        metric_prefers_c = m_c >= m_lot
        if metric_prefers_c != reward_prefers_c:
            disagreements.append({
                "perspective": doc,
                "metric_c": float(m_c),
                "metric_lottery": float(m_lot),
                "prefers": "C" if metric_prefers_c else "L",
            })
    return {
        "rec_c": rec_c, "rec_a": rec_a, "rec_b": rec_b,
        "p": p,
        "reward_prefers_c": reward_prefers_c,
        "r_c": float(r_c),
        "r_lottery": float(r_lottery),
        "disagreements": disagreements,
        "justification": entry.get("justification"),
    }


def _print_trajectory_text(label: str, rec) -> None:
    """Print one abstract trajectory's text under a heading."""
    print(f"  {label}:")
    text = (rec.trajectory_text or "").strip()
    for line in text.splitlines():
        print(f"    {line}")
    print()


def _do_render(records, metrics, selection_path: str, workspace_dir: str) -> int:
    with open(selection_path) as f:
        selection = json.load(f)
    pairs_entries = selection.get("pairs", []) or []
    lottery_entries = selection.get("lotteries", []) or []
    if not pairs_entries and not lottery_entries:
        print("[select_pairs] selection file contains no pairs or lotteries.")
        return 1
    if len(pairs_entries) > MAX_PAIRS:
        raise SystemExit(f"[select_pairs] too many pairs: "
                         f"{len(pairs_entries)} > {MAX_PAIRS}")
    if len(lottery_entries) > MAX_LOTTERIES:
        raise SystemExit(f"[select_pairs] too many lotteries: "
                         f"{len(lottery_entries)} > {MAX_LOTTERIES}")

    ids = _assign_ids(records)
    rec_by_id = dict(zip(ids, records))
    metric_items = [(m[0], m[2]) for m in metrics]  # (name, doc)

    feature_names = records[0].feature_names if records else []
    fip._print_feature_key(feature_names)

    selected_pairs = [
        _build_pair(rec_by_id, records, e, metric_items) for e in pairs_entries
    ]
    selected_lotteries = [
        _build_lottery(rec_by_id, e, metric_items) for e in lottery_entries
    ]

    snap_id = _next_snapshot_id()

    if selected_pairs:
        print(f"\nTop {len(selected_pairs)} preference-label disagreements "
              f"(Claude-selected pairs):")
        total = len(selected_pairs)
        for rank, cand in enumerate(selected_pairs, 1):
            rec_a = records[cand.a_idx]
            rec_b = records[cand.b_idx]
            print()
            print("=" * 78)
            print(f"PAIR {rank}/{total}")
            print("=" * 78)
            print()
            _print_trajectory_text("Trajectory A (designed reward's preferred trajectory)", rec_a)
            _print_trajectory_text("Trajectory B (the alternative trajectory)", rec_b)
            # Optional per-pair ranking of characteristics (short_names, most->
            # least informative about why the reward's preference may be wrong).
            order = pairs_entries[rank - 1].get("characteristics")
            fip._print_pair_preference_labels(
                rank, total, rec_a, rec_b, cand.disagreements, 0.0, order,
            )

    if selected_lotteries:
        print(f"\nTop {len(selected_lotteries)} lottery comparison(s) "
              f"(Claude-selected):")
        total = len(selected_lotteries)
        for rank, lot in enumerate(selected_lotteries, 1):
            print()
            print("=" * 78)
            print(f"LOTTERY {rank}/{total}")
            print("=" * 78)
            print()
            p = lot["p"]
            _print_trajectory_text(
                f"Trajectory A (good branch, probability {p:.2f})", lot["rec_a"])
            _print_trajectory_text(
                f"Trajectory B (bad branch, probability {1.0 - p:.2f})", lot["rec_b"])
            _print_trajectory_text("Trajectory C (the certain trajectory)", lot["rec_c"])
            pref = "C (the certain trajectory)" if lot["reward_prefers_c"] else "the lottery"
            print(f"  Designed reward: certain C = {lot['r_c']:+.3f}; "
                  f"lottery = {lot['r_lottery']:+.3f}  →  reward prefers {pref}.")
            if lot.get("justification"):
                print(f"  Why this p: {lot['justification']}")
            print()

    snap_path = _save_claude_snapshot(
        records, selected_pairs, selected_lotteries, snap_id=snap_id,
    )
    print(f"\n[snapshot saved: {snap_path}]")
    return 0


def _next_snapshot_id() -> int:
    """Next available pref_round_*.json id; matches find_informative_pairs'."""
    import glob
    import re
    if not os.path.isdir(HISTORY_DIR):
        return 1
    existing = glob.glob(os.path.join(HISTORY_DIR, "pref_round_*.json"))
    nums = [int(re.search(r"pref_round_(\d+)\.json", p).group(1)) for p in existing]
    return (max(nums) + 1) if nums else 1


def _save_claude_snapshot(records, selected_pairs, selected_lotteries,
                           snap_id: int | None = None) -> str:
    """Write a snapshot in the same schema find_informative_pairs.py uses,
    tagged as Claude-selected. /repair-verify reads it via --check-snapshots.
    """
    from datetime import datetime

    os.makedirs(HISTORY_DIR, exist_ok=True)
    if snap_id is None:
        snap_id = _next_snapshot_id()
    snap = {
        "snapshot_id": snap_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "selection_method": "claude_selected",
        "pairs": [],
        "lotteries": [],
    }
    for rank, cand in enumerate(selected_pairs, 1):
        rec_a = records[cand.a_idx]
        rec_b = records[cand.b_idx]
        snap["pairs"].append({
            "rank": rank,
            "score": 0.0,
            "traj_a_path": rec_a.path,
            "traj_b_path": rec_b.path,
            "snapshot_reward_a": float(rec_a.designed_reward),
            "snapshot_reward_b": float(rec_b.designed_reward),
            "disagreements": cand.disagreements,
        })
    for rank, lot in enumerate(selected_lotteries, 1):
        snap["lotteries"].append({
            "rank": rank,
            "traj_c_path": lot["rec_c"].path,
            "traj_a_path": lot["rec_a"].path,
            "traj_b_path": lot["rec_b"].path,
            "p": float(lot["p"]),
            "snapshot_reward_c": lot["r_c"],
            "snapshot_reward_lottery": lot["r_lottery"],
            "snapshot_reward_prefers_c": bool(lot["reward_prefers_c"]),
            "disagreements": lot["disagreements"],
            "justification": lot.get("justification"),
        })
    out_path = os.path.join(HISTORY_DIR, f"pref_round_{snap_id:03d}.json")
    with open(out_path, "w") as f:
        json.dump(snap, f, indent=2)
    return out_path


def main():
    p = argparse.ArgumentParser()
    add_workspace_arg(p)
    p.add_argument("--mode", choices=["dump", "render"], required=True)
    p.add_argument("--selection", type=str, default=None,
                   help="Path to the selection JSON (render mode).")
    p.add_argument("--rounds", type=str, default=None,
                   help="Comma-separated round numbers; default = all.")
    args = p.parse_args()

    # Resolve the selection path against the original cwd before activate()
    # chdirs into the workspace.
    if args.selection:
        args.selection = os.path.abspath(args.selection)

    ws = activate(args.workspace)
    print(f"[select_pairs] workspace={ws}")

    rounds = None
    if args.rounds:
        rounds = [int(x) for x in args.rounds.split(",")]

    records = _ordered_records(rounds)
    print(f"[select_pairs] loaded {len(records)} trajectories "
          f"from rounds {sorted({r.metadata.get('round') for r in records})}")
    metrics = fip._load_performance_metrics()

    if args.mode == "dump":
        _do_dump(records, metrics)
        return 0
    if not args.selection:
        raise SystemExit("[select_pairs] --mode render requires --selection <file>.")
    return _do_render(records, metrics, args.selection, ws)


if __name__ == "__main__":
    sys.exit(main())
