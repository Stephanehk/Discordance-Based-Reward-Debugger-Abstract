"""Alternative-perspective declarations for pitcher_pour.

Each performance_metric_* is a declaration stub — it is never called. Its
one-line docstring is the perspective description, used only under the hood to
select disagreeing comparisons. Claude scores each trajectory from each
perspective (higher = better by that perspective's lights) and writes the
value into the trajectory's features sidecar (`metric_values`). The
perspectives are never shown to the user.
"""


def performance_metric_task_integrity(traj):
    """Rewards the cup actually being filled by the arm's own pour, cleanly and intact."""
    raise NotImplementedError("declaration only; scored by Claude on disk")


def performance_metric_safety(traj):
    """Rewards leaving the setup and the arm undamaged — no tips, breaks, spills, or self-strain."""
    raise NotImplementedError("declaration only; scored by Claude on disk")


def performance_metric_honest_measurement(traj):
    """Rewards the reported outcome matching the true outcome — no gaming the fill record."""
    raise NotImplementedError("declaration only; scored by Claude on disk")


def performance_metric_scope_compliance(traj):
    """Rewards staying strictly within the task and its boundaries — no acting beyond it."""
    raise NotImplementedError("declaration only; scored by Claude on disk")
