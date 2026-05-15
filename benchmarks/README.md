# OpenClaw Benchmarks

This folder contains a focused benchmark harness for the `openclaw/openclaw` repository only. It captures GitHub API latency, pagination volume, fan-out calls, and optional LLM evaluation timing.

## What It Measures
- API request counts, errors, and latency (p50/p95)
- Pagination volume (pages/items) by endpoint
- Commit detail fan-out
- Optional LLM evaluation time (requires `GROQ_API_KEY`)

## Run
```powershell
python benchmarks\benchmark_openclaw.py
```

### Optional: Save JSON output
```powershell
python benchmarks\benchmark_openclaw.py --output benchmarks\openclaw_benchmark.json
```

### Optional: Include LLM timing
```powershell
$env:GROQ_API_KEY = "<your_key>"
python benchmarks\benchmark_openclaw.py --include-llm
```

### Optional: Use GitHub token
```powershell
$env:GITHUB_TOKEN = "<your_token>"
python benchmarks\benchmark_openclaw.py
```

## Notes
- The benchmark is fixed to `openclaw/openclaw` and does not accept other repos.
- LLM benchmarks are skipped unless `GROQ_API_KEY` is set.
