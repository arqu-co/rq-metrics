"""Aggregation functions for per-user metrics and leaderboard.

Provides user-level stats: first-pass rate, build count, violation rate,
avg fix cycles, and a ranked leaderboard.
"""

from collections import defaultdict


def resolve_user_key(metric):
    """Return a stable user identifier from a metrics record.

    Prefers user_email (schema v2+), falls back to user name.
    Skips 'unknown' users entirely.
    """
    email = metric.get("user_email") or ""
    name = metric.get("user", "unknown")
    if name == "unknown" and not email:
        return None
    return email if email else name


def compute_per_user(metrics):
    """Compute per-user statistics."""
    by_user = defaultdict(list)
    # Track name<->email mapping for display
    user_names = {}

    for m in metrics:
        key = resolve_user_key(m)
        if key is None:
            continue
        by_user[key].append(m)
        name = m.get("user", "unknown")
        if name != "unknown":
            user_names[key] = name

    result = {}
    for user_key, user_metrics in by_user.items():
        total = len(user_metrics)
        first_pass = sum(
            1 for m in user_metrics if m.get("gates_first_pass", False)
        )
        total_violations = sum(
            m.get("critic_findings_count", 0)
            + m.get("gate_failures_after_critic", 0)
            for m in user_metrics
        )
        run_numbers = [
            m.get("run_number", 1) for m in user_metrics
        ]
        avg_cycles = (
            round(sum(run_numbers) / len(run_numbers), 1)
            if run_numbers else 1.0
        )
        raw_display = user_names.get(user_key, user_key)
        # If display name is still an email, use the local part
        if "@" in raw_display:
            raw_display = raw_display.split("@")[0]
        result[user_key] = {
            "display_name": raw_display,
            "email": user_key if "@" in user_key else None,
            "total_builds": total,
            "first_pass_count": first_pass,
            "first_pass_rate": (
                round(first_pass / total * 100, 1) if total else 0
            ),
            "total_violations": total_violations,
            "avg_violations_per_build": (
                round(total_violations / total, 2) if total else 0
            ),
            "avg_fix_cycles": avg_cycles,
        }
    return result


def compute_leaderboard(per_user):
    """Rank users by effectiveness (first-pass rate, then build count).

    Returns a sorted list of user stats with rank.
    """
    entries = []
    for user_key, stats in per_user.items():
        if stats["total_builds"] < 1:
            continue
        entries.append({
            "user": user_key,
            "display_name": stats["display_name"],
            "email": stats["email"],
            "total_builds": stats["total_builds"],
            "first_pass_rate": stats["first_pass_rate"],
            "first_pass_count": stats["first_pass_count"],
            "avg_violations": stats["avg_violations_per_build"],
            "avg_fix_cycles": stats["avg_fix_cycles"],
        })

    # Sort: highest first-pass rate first, then most builds
    entries.sort(
        key=lambda e: (-e["first_pass_rate"], -e["total_builds"])
    )
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1
    return entries
