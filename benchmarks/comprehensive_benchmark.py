import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
import pandas as pd
from dotenv import load_dotenv

# Add root to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from github_api import (
    get_repo_data,
    get_contributors,
    get_commits,
    get_pulls,
    get_contributor_prs,
    reset_metrics,
    get_metrics,
)
from autorater import rate_repo
from autorater_llm import evaluate_contributor_with_groq, reset_llm_metrics, get_llm_metrics

# Default repositories to benchmark
DEFAULT_REPOS = [
    "openclaw/openclaw",
    "pallets/flask",
    "streamlit/streamlit",
    "octocat/Hello-World"
]

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

def _calculate_consistency(scores):
    """Calculate variance/consistency across multiple runs for the same contributor."""
    if len(scores) < 2:
        return 0.0
    s = pd.Series(scores)
    return float(s.std())

def run_benchmark(args):
    token = args.token or os.getenv("GITHUB_TOKEN")
    groq_key = os.getenv("GROQ_API_KEY")
    
    if not token:
        print("Warning: GITHUB_TOKEN not set. You will likely hit rate limits.")
    
    llm_enabled = bool(args.include_llm and groq_key)
    
    results = []
    
    for repo_full_name in args.repos:
        print(f"--- Benchmarking: {repo_full_name} ---")
        owner, repo = repo_full_name.split("/")
        
        reset_metrics()
        reset_llm_metrics()
        start_time = time.perf_counter()
        
        repo_res = {
            "repo": repo_full_name,
            "status": "success",
            "error": None,
            "data": {}
        }
        
        try:
            # 1. Fetch Basic Repo Data
            repo_data = get_repo_data(owner, repo, token=token)
            contributors = get_contributors(owner, repo, token=token, max_pages=1)
            commits = get_commits(owner, repo, token=token, max_pages=1)
            
            # 2. Heuristic Rating
            commit_dates = [c.get("commit", {}).get("author", {}).get("date") for c in commits]
            heuristic_rating = rate_repo(repo_data, contributors, commit_dates)
            
            repo_res["data"]["heuristic"] = heuristic_rating
            
            # 3. LLM Contributor Evaluation (if enabled)
            llm_results = []
            if llm_enabled:
                # Take top N contributors
                top_contributors = [c.get("login") for c in contributors if c.get("login")][:args.num_contributors]
                for login in top_contributors:
                    print(f"  Evaluating contributor: {login}")
                    prs = get_contributor_prs(owner, repo, login, token=token, max_pages=1)
                    
                    # Run evaluation multiple times to check consistency
                    eval_scores = []
                    for i in range(args.consistency_runs):
                        res = evaluate_contributor_with_groq(prs)
                        if "total_score" in res:
                            eval_scores.append(res["total_score"])
                    
                    llm_results.append({
                        "login": login,
                        "num_prs": len(prs),
                        "scores": eval_scores,
                        "consistency_std": _calculate_consistency(eval_scores) if len(eval_scores) > 1 else 0.0,
                        "average_score": sum(eval_scores)/len(eval_scores) if eval_scores else 0.0
                    })
            
            repo_res["data"]["llm_evals"] = llm_results
            repo_res["data"]["metrics"] = get_metrics()
            repo_res["data"]["llm_metrics"] = get_llm_metrics()
            
        except Exception as e:
            print(f"  Error benchmarking {repo_full_name}: {e}")
            repo_res["status"] = "failed"
            repo_res["error"] = str(e)
            
        repo_res["elapsed_s"] = time.perf_counter() - start_time
        results.append(repo_res)
        
    # Final Summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "params": {
            "num_contributors": args.num_contributors,
            "consistency_runs": args.consistency_runs,
            "llm_enabled": llm_enabled
        },
        "results": results
    }
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
            
    _print_markdown_summary(summary)

def _print_markdown_summary(summary):
    print("\n## Benchmark Summary Report")
    print("| Repository | Status | Health Score | Top Contributor Avg LLM Score | Consistency (StdDev) | Time (s) |")
    print("|------------|--------|--------------|------------------------------|---------------------|----------|")
    
    for res in summary["results"]:
        repo = res["repo"]
        status = res["status"]
        if status == "success":
            health = res["data"]["heuristic"].get("total", "N/A")
            llm_evals = res["data"].get("llm_evals", [])
            if llm_evals:
                avg_llm = round(llm_evals[0].get("average_score", 0), 2)
                consistency = round(llm_evals[0].get("consistency_std", 0), 2)
            else:
                avg_llm = "N/A"
                consistency = "N/A"
            elapsed = round(res["elapsed_s"], 2)
            print(f"| {repo} | SUCCESS | {health} | {avg_llm} | {consistency} | {elapsed} |")
        else:
            print(f"| {repo} | FAILED  | N/A | N/A | N/A | {round(res['elapsed_s'], 2)} |")

def main():
    parser = argparse.ArgumentParser(description="Comprehensive Benchmark for Repo-Intelligence")
    parser.add_argument("--repos", nargs="+", default=DEFAULT_REPOS, help="Repositories to benchmark (owner/repo)")
    parser.add_argument("--token", help="GitHub token")
    parser.add_argument("--num-contributors", type=int, default=2, help="Number of contributors to evaluate per repo")
    parser.add_argument("--consistency-runs", type=int, default=2, help="Number of times to run LLM eval per contributor")
    parser.add_argument("--include-llm", action="store_true", help="Include LLM evaluations")
    parser.add_argument("--output", default="benchmarks/benchmark_results.json", help="Output JSON path")
    
    args = parser.parse_args()
    run_benchmark(args)

if __name__ == "__main__":
    main()
