# Repo-Intelligence---PR-based-LLM-Auto-Rater
This project implements a repository analysis dashboard that provides insights into the health and activity of a GitHub repository. The system retrieves data from the GitHub API and presents analytics related to commits, contributors, pull requests, and issues. It also includes a repository scoring system and an LLM-based contributor evaluation module.

The dashboard is built using Streamlit and allows users to interactively analyze any public GitHub repository.

## Live Project Link
```br
https://github-repository-analysis-lakshay-baijal.onrender.com/
```

## Demo Screen Record
https://github.com/user-attachments/assets/92775fe9-5e60-4065-8ef9-9d832a97473b

## Report
```br
https://github.com/LakshayBaijal/Repo-Intelligence_PR-based-LLM-Auto-Rater/blob/main/Report.md
```

## Repository Statistics

The dashboard retrieves and displays key repository metrics including:

- Number of stars

- Number of forks

- Number of open issues

- Total contributors

- Number of commits fetched

These statistics provide a quick overview of the repository's popularity and activity.

## Commit Activity Visualization
The system analyzes commit timestamps and visualizes repository activity over time using a time-series graph. This helps identify development patterns and active periods within the project.

## Contributor Leaderboard
A contributor leaderboard is generated using multiple signals:

- Commits fetched from the repository

- Pull requests created by contributors

- Issues opened by contributors

- Recent activity in the last 30 days

The leaderboard helps identify the most active contributors in the repository.

## Code Ownership Heatmap
The dashboard generates a heatmap representing the relationship between contributors and repository modules.

This is computed by:

- Fetching commit details from the GitHub API

- Extracting file paths modified in each commit

- Mapping files to their top-level modules

- Aggregating contributions across contributors and modules

The heatmap helps visualize which contributors are responsible for different parts of the codebase.

## Repository Autorater

A heuristic scoring system evaluates repository health using several metrics:

| Metric | Maximum Score |
|------|------|
| Stars | 25 |
| Forks | 10 |
| Contributors | 20 |
| Recent Activity | 30 |
| Issue Health | 15 |

The final score is normalized to a scale of **0–100**.

The scoring is implemented in the repository autorater module.

## LLM-Based Contributor Evaluation

The system evaluates individual contributors using pull request information.

For each contributor, the following data is analyzed:

- Pull request title
- Pull request description
- Files modified
- Review feedback

The contributor is evaluated across four dimensions:

| Metric | Range |
|------|------|
| Code Quality | 0–25 |
| Problem Significance | 0–25 |
| Review Engagement | 0–25 |
| Consistency | 0–25 |

The total contributor score is computed on a scale of **0–100**.

## Bus Factor Estimation
The system estimates the repository bus factor based on the commit distribution among contributors.

The bus factor is estimated as follows:

| < 25% | 3 |
| 25–50% | 2 |
| > 50% | 1 |

A lower bus factor indicates higher dependency on a small number of contributors.

## Benchmarks

The system includes an automated benchmarking suite that evaluates performance, consistency, and scoring accuracy across multiple repositories.

### 📊 Live Performance & Quality Summary
Latest benchmark run results (2026-05-15):

| Repository | Scale | Health Score | Top Contributor Avg LLM Score | Consistency (StdDev) | Avg API Latency | Status |
|------------|-------|--------------|------------------------------|---------------------|-----------------|--------|
| **openclaw/openclaw** | AI-Focused | **85.0/100** | **70.0** | 0.0 | 0.81s | SUCCESS |
| **pallets/flask** | Mature/Stable | **71.58/100** | **55.0** | 0.0 | 0.82s | SUCCESS |

---

### 🔍 Heuristic Score Breakdown
The "Health Score" is calculated using a multi-signal heuristic model:

| Metric | openclaw/openclaw | pallets/flask | Max Possible |
|--------|-------------------|---------------|--------------|
| **Stars Score** | 25.0 | 25.0 | 25.0 |
| **Forks Score** | 10.0 | 10.0 | 10.0 |
| **Contributors Score**| 20.0 | 20.0 | 20.0 |
| **Activity (30d) Score**| 30.0 | 1.8 | 30.0 |
| **Issue Health Score** | 0.0 | 14.78 | 15.0 |
| **Total Health Score** | **85.0** | **71.58** | **100.0** |

---

### 📦 Data Processing Volume
The dashboard processes significant metadata to generate insights:

| Repository | Total Requests | Pages Processed | Items Fetched | Elapsed Time |
|------------|----------------|-----------------|---------------|--------------|
| **openclaw/openclaw** | 74 | 50 | 742 | 68.2s |
| **pallets/flask** | 35 | 24 | 449 | 35.8s |

---

### 🧠 LLM Intelligence Metrics (Groq Llama-3.3-70b)
Qualitative analysis performance for contributor evaluation:

| Repository | Groq Calls | Total LLM Time | Avg Time per Eval | Prompt Volume (Chars) |
|------------|------------|----------------|-------------------|-----------------------|
| **openclaw/openclaw** | 2 | 2.35s | 1.17s | 23,676 |
| **pallets/flask** | 2 | 2.27s | 1.13s | 6,706 |

---

### 🛡️ System Efficiency & Reliability
- **Consistency**: The system demonstrates 0.0 Standard Deviation across multiple evaluation runs, ensuring highly reproducible qualitative scores.
- **Latency Optimization**: Throughput is maximized using optimized pagination (100 items/page) and selective fan-out calls for commit/PR details.
- **Rate Limit Resilience**: Intelligent header tracking keeps the system within GitHub API quotas (current remaining: 4,800+ requests).

For full technical details, raw logs, and endpoint-level latency distribution, refer to [benchmarks/README.md](benchmarks/README.md).

## Modules:

- **app.py**  
  Streamlit dashboard implementation and visualization logic.

- **github_api.py**  
  GitHub API client used to fetch repository data such as commits, pull requests, issues, and contributors.

- **autorater.py**  
  Implements the heuristic repository scoring system.

- **autorater_llm.py**  
  Implements LLM-based contributor evaluation with a fallback semantic scoring mechanism.

# Installation
- Environment Variables
Create a **.env** file in the project directory and add the following variables:
```br
GITHUB_TOKEN=your_github_token
GROQ_API_KEY=your_groq_api_key
```
The GitHub token helps avoid API rate limits, while the Groq API key enables LLM-based contributor evaluation.
You can also add them in sidebar during execution

- Clone the repository
- Install Dependency
```br
pip install -r requirements.txt
```

- Running the Dashboard
```br
streamlit run app.py
```
- Dashboard Brower Local Host
```br
http://localhost:8501
``` 

## Technology Used
- Python
- Streamlit
- GitHub REST API
- Pandas
- Altair
- SentenceTransformers
- Scikit-learn

## Author
**Lakshay Baijal**
