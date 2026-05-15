import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from github_api import (
    get_repo_data,
    get_contributors,
    get_commits,
    get_pulls,
    get_issues,
    get_commit_details,
    get_contributor_prs,
    reset_metrics,
    get_metrics,
)
from autorater_llm import evaluate_contributor_with_groq, reset_llm_metrics, get_llm_metrics

OWNER = "openclaw"
REPO = "openclaw"


def _percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def _summarize_latencies(latencies):
    if not latencies:
        return {"count": 0, "min": None, "max": None, "avg": None, "p50": None, "p95": None}
    total = sum(latencies)
    return {
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "avg": total / len(latencies),
        "p50": _percentile(latencies, 50),
        "p95": _percentile(latencies, 95),
    }


def _summarize_metrics(metrics):
    requests = metrics.get("requests", {})
    pagination = metrics.get("pagination", {})
    rate_limit = metrics.get("rate_limit", {})

    by_endpoint = {}
    for endpoint, data in (requests.get("by_endpoint") or {}).items():
        by_endpoint[endpoint] = {
            "count": data.get("count", 0),
            "errors": data.get("errors", 0),
            "latency": _summarize_latencies(data.get("latencies") or []),
        }

    pagination_by_endpoint = {}
    for endpoint, data in (pagination.get("by_endpoint") or {}).items():
        pagination_by_endpoint[endpoint] = {
            "pages": data.get("pages", 0),
            "items": data.get("items", 0),
        }

    return {
        "requests": {
            "count": requests.get("count", 0),
            "errors": requests.get("errors", 0),
            "latency": _summarize_latencies(requests.get("latencies") or []),
            "by_endpoint": by_endpoint,
        },
        "pagination": {
            "pages": pagination.get("pages", 0),
            "items": pagination.get("items", 0),
            "by_endpoint": pagination_by_endpoint,
        },
        "rate_limit": rate_limit,
    }


def run_benchmark(args):
    reset_metrics()
    reset_llm_metrics()

    token = args.token or os.getenv("GITHUB_TOKEN")
    start = time.perf_counter()

    errors = []

    def _safe_call(label, func, default):
        try:
            return func()
        except Exception as e:
            errors.append(f"{label}:{e}")
            return default

    repo_data = _safe_call("repo_data", lambda: get_repo_data(OWNER, REPO, token=token), {})
    contributors = _safe_call(
        "contributors",
        lambda: get_contributors(OWNER, REPO, token=token, max_pages=args.contributor_pages),
        [],
    )
    commits = _safe_call(
        "commits",
        lambda: get_commits(OWNER, REPO, token=token, max_pages=args.commit_pages),
        [],
    )
    pulls = _safe_call(
        "pulls",
        lambda: get_pulls(OWNER, REPO, token=token, max_pages=args.pull_pages),
        [],
    )
    issues = _safe_call(
        "issues",
        lambda: get_issues(OWNER, REPO, token=token, max_pages=args.issue_pages),
        [],
    )

    commit_details = []
    for c in commits[: args.commit_details]:
        sha = c.get("sha")
        if not sha:
            continue
        try:
            commit_details.append(get_commit_details(OWNER, REPO, sha, token=token))
        except Exception as e:
            errors.append(f"commit_details:{sha}:{e}")

    top_contributors = [c.get("login") for c in contributors if c.get("login")][: args.contributors]
    contributor_pr_counts = {}
    llm_scores = {}
    llm_skipped_reason = None

    llm_enabled = bool(args.include_llm and (os.getenv("GROQ_API_KEY") or ""))
    if args.include_llm and not llm_enabled:
        llm_skipped_reason = "GROQ_API_KEY not set; LLM benchmark skipped"

    for login in top_contributors:
        try:
            prs = get_contributor_prs(OWNER, REPO, login, token=token, max_pages=args.pr_pages)
            contributor_pr_counts[login] = len(prs)
            if llm_enabled:
                llm_scores[login] = evaluate_contributor_with_groq(prs)
        except Exception as e:
            errors.append(f"contributor_prs:{login}:{e}")

    elapsed = time.perf_counter() - start

    metrics = get_metrics()
    llm_metrics = get_llm_metrics()

    output = {
        "repo": f"{OWNER}/{REPO}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed,
        "params": {
            "commit_pages": args.commit_pages,
            "pull_pages": args.pull_pages,
            "issue_pages": args.issue_pages,
            "contributor_pages": args.contributor_pages,
            "commit_details": args.commit_details,
            "contributors": args.contributors,
            "pr_pages": args.pr_pages,
            "include_llm": args.include_llm,
        },
        "counts": {
            "contributors": len(contributors),
            "commits": len(commits),
            "pulls": len(pulls),
            "issues": len(issues),
            "commit_details": len(commit_details),
        },
        "metrics": _summarize_metrics(metrics),
        "llm_metrics": llm_metrics,
        "llm_skipped_reason": llm_skipped_reason,
        "llm_scores": llm_scores,
        "errors": errors,
        "repo_stats": {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
        },
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Benchmark OpenClaw repository analysis")
    parser.add_argument("--token", default=None, help="GitHub token (optional)")
    parser.add_argument("--commit-pages", type=int, default=2)
    parser.add_argument("--pull-pages", type=int, default=1)
    parser.add_argument("--issue-pages", type=int, default=1)
    parser.add_argument("--contributor-pages", type=int, default=2)
    parser.add_argument("--commit-details", type=int, default=50)
    parser.add_argument("--contributors", type=int, default=5)
    parser.add_argument("--pr-pages", type=int, default=2)
    parser.add_argument("--include-llm", action="store_true")
    parser.add_argument("--output", default=None, help="Optional output JSON path")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    run_benchmark(args)


if __name__ == "__main__":
    main()
