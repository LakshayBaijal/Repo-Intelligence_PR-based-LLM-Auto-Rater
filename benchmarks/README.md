# Repo-Intelligence Benchmarks

This folder contains benchmark tools to evaluate the performance and quality of the repository analysis system.

## 1. Comprehensive Benchmark (`comprehensive_benchmark.py`)

This is the recommended tool for evaluating the system across multiple repositories and checking LLM scoring consistency.

### What It Measures
- **Heuristic Health Score**: Standardized health rating for multiple repositories.
- **LLM Scoring Quality**: Evaluates top contributors and checks for scoring consistency across multiple runs.
- **Performance**: Latency and throughput for GitHub API calls and LLM evaluations.
- **API Metrics**: Detailed breakdown of requests, errors, and pagination.

### Run
```powershell
python benchmarks\comprehensive_benchmark.py --repos openclaw/openclaw pallets/flask --include-llm
```

### Options
- `--repos`: List of repositories to test (e.g., `owner/repo`).
- `--num-contributors`: Number of top contributors to evaluate per repo (default: 2).
- `--consistency-runs`: Number of times to run LLM eval per contributor to check for variance (default: 2).
- `--include-llm`: Flag to enable LLM-based evaluation (requires `GROQ_API_KEY`).
- `--output`: Path to save the detailed JSON results (default: `benchmarks/benchmark_results.json`).

---

## 2. OpenClaw Legacy Benchmark (`benchmark_openclaw.py`)

A focused benchmark harness for the `openclaw/openclaw` repository only.

### Run
```powershell
python benchmarks\benchmark_openclaw.py
```

## Setup
Ensure you have the following in your `.env` file:
- `GITHUB_TOKEN`: To avoid rate limits.
- `GROQ_API_KEY`: To enable LLM evaluations.
