# app.py
import os
import time
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import warnings
warnings.filterwarnings("ignore")

from github_api import (
    get_repo_data, get_contributors, get_commits, get_pulls, get_issues, get_commit_details,
    summarize_commits, get_contributor_prs, get_pull_reviews
)
from autorater import rate_repo

# import module (not function) so we can initialize LLM client after sidebar input
import autorater_llm

st.set_page_config(page_title="Repo Intelligence (PR-based LLM + Heatmap)", layout="wide")

with st.sidebar:
    st.header("Settings")
    github_token = st.text_input("GitHub token (optional)", type="password")
    groq_key = st.text_input("Groq API Key (optional - enables PR LLM)", type="password")

    # store GitHub token (used by github_api functions)
    if github_token:
        os.environ["GITHUB_TOKEN"] = github_token.strip()

    owner = st.text_input("Repo owner", value="openclaw")
    repo = st.text_input("Repo name", value="openclaw")
    max_commit_pages = st.slider("Commit pages to fetch (100/page)", 1, 4, 2)
    max_pull_pages = st.slider("Pull pages to fetch (100/page)", 1, 2, 1)
    fetch_files = st.checkbox("Fetch commit file paths (heatmap) — extra API calls", value=True)
    num_sample = st.slider("Contributors to evaluate (sample)", 1, 10, 6)
    analyze = st.button("Analyze")

    # IMPORTANT: set Groq API key *after* reading sidebar so autorater_llm can init client
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
        # Immediately set and initialize Groq client in autorater_llm
        autorater_llm.set_groq_api_key(groq_key)
    else:
        # ensure autorater_llm will read environment on demand
        autorater_llm.init_from_env()

st.title("Repo Intelligence — PR-based LLM Autorater + Heatmap by Lakshay Baijal")

if analyze:
    token = os.getenv("GITHUB_TOKEN", None)
    try:
        with st.spinner("Fetching repository data..."):
            repo_data = get_repo_data(owner, repo, token=token)
            contributors = get_contributors(owner, repo, token=token, max_pages=2)
            commits = get_commits(owner, repo, token=token, max_pages=max_commit_pages)
            pulls = get_pulls(owner, repo, token=token, max_pages=max_pull_pages)
            issues = get_issues(owner, repo, token=token, max_pages=1)
    except Exception as e:
        st.error(f"GitHub API error: {e}")
        st.stop()

    # Summarize commits into simplified structures
    commit_summary = summarize_commits(commits)
    commit_dates = [c.get("date") for c in commit_summary if c.get("date")]

    # Repository metrics
    st.subheader("Repository Statistics")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Stars", repo_data.get("stargazers_count", 0))
    c2.metric("Forks", repo_data.get("forks_count", 0))
    c3.metric("Open issues", repo_data.get("open_issues_count", 0))
    c4.metric("Contributors", len(contributors))
    c5.metric("Commits fetched", len(commits))

    st.markdown("---")
    left, right = st.columns([3,1.6])

    with left:
        # --- Commit Activity chart (restored)
        st.subheader("Commit Activity")
        if commit_dates:
            # convert to date-only strings and count per day
            df_dates = pd.DataFrame({"date":[d[:10] for d in commit_dates]})
            counts = df_dates["date"].value_counts().sort_index()
            counts.index = pd.to_datetime(counts.index)
            st.line_chart(counts)
        else:
            st.info("No commit dates available.")

        # --- Leaderboard
        st.subheader("Leaderboard — volume, PRs, recency (top 50)")
        authors = [(c.get("author_login") or c.get("author_name") or "unknown") for c in commit_summary]
        commits_count = pd.Series(authors).value_counts().rename_axis("login").reset_index(name="commits_fetched")
        contrib_df = pd.DataFrame([{"login": c.get("login"), "contributions": c.get("contributions", 0)} for c in contributors])
        pr_authors = [ (p.get("user") or {}).get("login") or "unknown" for p in pulls ]
        pr_counts = pd.Series(pr_authors).value_counts().rename_axis("login").reset_index(name="prs_fetched")
        issue_authors = [ (i.get("user") or {}).get("login") or "unknown" for i in issues if 'pull_request' not in i ]
        issue_counts = pd.Series(issue_authors).value_counts().rename_axis("login").reset_index(name="issues_fetched")

        # last active per author
        last_active = {}
        for c in commit_summary:
            login = c.get("author_login") or c.get("author_name") or "unknown"
            date = c.get("date")
            if not date:
                continue
            prev = last_active.get(login)
            if (prev is None) or (date > prev):
                last_active[login] = date
        last_active_df = pd.DataFrame([{"login":k, "last_active":v} for k,v in last_active.items()])

        # Merge into leaderboard df
        lb = pd.merge(commits_count, contrib_df, on="login", how="outer").merge(pr_counts, on="login", how="left").merge(issue_counts, on="login", how="left").merge(last_active_df, on="login", how="left")
        lb["contributions"] = lb.get("contributions", 0).fillna(0).astype(int)
        lb["commits_fetched"] = lb.get("commits_fetched", 0).fillna(0).astype(int)
        lb["prs_fetched"] = lb.get("prs_fetched", 0).fillna(0).astype(int)
        lb["issues_fetched"] = lb.get("issues_fetched", 0).fillna(0).astype(int)

        # recent activity (30 days)
        lb["recent_commits_30d"] = 0
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)
        for idx, row in lb.iterrows():
            login = row["login"]
            r = [d for d in commit_summary if (d.get("author_login") == login) and d.get("date") and pd.to_datetime(d["date"], utc=True) >= cutoff]
            lb.at[idx, "recent_commits_30d"] = len(r)

        lb["last_active"] = lb["last_active"].fillna("N/A")
        lb = lb.sort_values(["commits_fetched","prs_fetched"], ascending=False).reset_index(drop=True)
        st.dataframe(lb.head(50))

        st.markdown("---")

        # --- Code ownership heatmap
        st.subheader("Code ownership heatmap (modules vs contributors)")
        file_rows = []
        sample_commits = commits[:200]
        if fetch_files:
            with st.spinner("Fetching commit file lists (this may take time)..."):
                for c in sample_commits:
                    sha = c.get("sha")
                    try:
                        details = get_commit_details(owner, repo, sha, token)
                        files = details.get("files", [])
                        author = (c.get("author") or {}).get("login") or (c.get("commit") or {}).get("author",{}).get("name","unknown")
                    except Exception:
                        author = (c.get("author") or {}).get("login") or (c.get("commit") or {}).get("author",{}).get("name","unknown")
                        files = []
                    for f in files:
                        path = f.get("filename","")
                        if not path:
                            continue
                        module = path.split("/")[0]
                        file_rows.append({"author": author, "module": module})
                time.sleep(0.1)
        else:
            st.info("Enable file fetching to compute full heatmap (extra API calls).")

        if file_rows:
            df_fp = pd.DataFrame(file_rows)
            heat = df_fp.groupby(["author","module"]).size().reset_index(name="count")
            top_authors = heat.groupby("author")["count"].sum().sort_values(ascending=False).head(20).index.tolist()
            top_modules = heat.groupby("module")["count"].sum().sort_values(ascending=False).head(30).index.tolist()
            heat = heat[heat["author"].isin(top_authors) & heat["module"].isin(top_modules)]
            chart = alt.Chart(heat).mark_rect().encode(
                x=alt.X('module:N', sort=top_modules, title="module"),
                y=alt.Y('author:N', sort=top_authors, title="contributor"),
                color=alt.Color('count:Q', scale=alt.Scale(scheme='greens'), title='files touched'),
                tooltip=['author','module','count']
            ).properties(width=900, height=400)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No file-level data to show. Enable 'Fetch commit file paths' and re-run analysis.")

    with right:
        # --- Repo autorater (heuristic)
        st.subheader("Repo autorater (heuristic)")
        repo_score = rate_repo(repo_data, contributors, commit_dates)
        st.metric("Overall score", f"{repo_score['total']} / 100")
        br = pd.DataFrame.from_dict(repo_score["breakdown"], orient="index", columns=["score"])
        st.table(br)
        st.markdown("Quick recommendations")
        raw = repo_score["raw"]
        if raw.get("commits_last_30_days",0) < 5:
            st.write("- Low recent activity.")
        if raw.get("contributors",0) < 3:
            st.write("- Low contributor count.")
        if raw.get("open_issues",0) > 50:
            st.write("- Many open issues.")

    st.markdown("---")
    st.subheader("LLM based contributor autorater (PR-based)")

    # select sample contributors for LLM scoring
    candidate_list = lb["login"].tolist() if not lb.empty else []
    sample = candidate_list[:max(1, num_sample)]
    for login in sample:
        st.write(f"Evaluating contributor: **{login}**")
        try:
            prs = get_contributor_prs(owner, repo, login, token=token, per_page=100, max_pages=3)
        except Exception:
            prs = []
        if not prs:
            contributor_commits = [c for c in commits if (c.get("author") or {}).get("login") == login]
            prs = []
            for cc in contributor_commits[:20]:
                msg = (cc.get("commit") or {}).get("message", "")
                prs.append({
                    "title": msg.splitlines()[0] if msg else "",
                    "body": "\n".join(msg.splitlines()[1:]) if msg else "",
                    "_files": [],
                    "_reviews": []
                })
        # evaluate using autorater_llm (module handles lazy init)
        result = autorater_llm.evaluate_contributor_with_groq(prs)
        st.json(result)
        time.sleep(0.25)

    st.markdown("---")
    st.subheader("Bus factor & final notes")
    try:
        total_commits = len(commit_summary) if commit_summary else 1
        top_share = (pd.Series([a for a in authors]).value_counts().iloc[0] / total_commits) * 100 if len(authors)>0 else 0
        st.metric("Top contributor commit share (%)", f"{round(top_share,2)}%")
        bus_factor = 1
        if top_share < 25:
            bus_factor = 3
        elif top_share < 50:
            bus_factor = 2
        st.write(f"Estimated bus factor: {bus_factor}")
    except Exception:
        st.write("Unable to compute bus factor.")
