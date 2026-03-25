"""Aggregation functions for per-user metrics and leaderboard.

Provides user-level stats: first-pass rate, build count, violation rate,
avg fix cycles, and a ranked leaderboard.
"""

from collections import defaultdict


def resolve_user_key(metric):
    """Return a stable user identifier from a metrics record.

    Always uses the user name as the canonical key. Skips 'unknown' users
    unless they have an email.
    """
    name = metric.get("user", "unknown")
    if name != "unknown":
        return name
    email = metric.get("user_email") or ""
    if email:
        return email.split("@")[0]
    return None


def _build_email_to_name_map(metrics):
    """Build a mapping from email to name for dedup.

    When a record has both user and user_email, we learn that email
    belongs to that user name. Later, email-only records can be merged.
    """
    email_to_name = {}
    for m in metrics:
        name = m.get("user", "unknown")
        email = m.get("user_email") or ""
        if name != "unknown" and email:
            email_to_name[email] = name
    return email_to_name


def group_by_user(metrics):
    """Group metrics by canonical user key with email-to-name dedup."""
    email_to_name = _build_email_to_name_map(metrics)
    by_user = defaultdict(list)

    for m in metrics:
        name = m.get("user", "unknown")
        email = m.get("user_email") or ""

        if name != "unknown":
            key = name
        elif email and email in email_to_name:
            key = email_to_name[email]
        elif email:
            key = email.split("@")[0]
        else:
            continue

        by_user[key].append(m)
    return by_user


def compute_per_user(metrics):
    """Compute per-user statistics."""
    by_user = group_by_user(metrics)

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
        # Collect email from any record that has one
        email = None
        for m in user_metrics:
            e = m.get("user_email") or ""
            if e:
                email = e
                break

        result[user_key] = {
            "display_name": user_key,
            "email": email,
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
