# autorater.py
import pandas as pd

def _count_recent(commit_dates_iso, days=30):
    if not commit_dates_iso:
        return 0
    ts = pd.to_datetime(commit_dates_iso, utc=True, errors="coerce")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return int((ts >= cutoff).sum())

def rate_repo(repo_data: dict, contributors_list: list, commit_dates_iso: list):
    stars = int(repo_data.get("stargazers_count", 0) or 0)
    forks = int(repo_data.get("forks_count", 0) or 0)
    open_issues = int(repo_data.get("open_issues_count", 0) or 0)
    contributors = len(contributors_list) if contributors_list else 0
    commits_30 = _count_recent(commit_dates_iso or [], 30)

    stars_score = min(stars / 500.0, 1.0) * 25.0
    forks_score = min(forks / 200.0, 1.0) * 10.0
    contributors_score = min(contributors / 50.0, 1.0) * 20.0
    activity_score = min(commits_30 / 100.0, 1.0) * 30.0
    issues_penalty = min(open_issues / 200.0, 1.0)
    issues_score = (1.0 - issues_penalty) * 15.0

    total = stars_score + forks_score + contributors_score + activity_score + issues_score
    total = max(0.0, min(100.0, total))

    breakdown = {
        "stars_score": round(stars_score,2),
        "forks_score": round(forks_score,2),
        "contributors_score": round(contributors_score,2),
        "activity_score": round(activity_score,2),
        "issues_score": round(issues_score,2),
    }

    raw = {"stars": stars, "forks": forks, "contributors": contributors, "commits_last_30_days": commits_30, "open_issues": open_issues}

    return {"total": round(total,2), "breakdown": breakdown, "raw": raw}
