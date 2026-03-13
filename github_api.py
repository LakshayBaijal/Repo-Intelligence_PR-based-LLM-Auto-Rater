# github_api.py
import os
import requests
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.github.com"
DEFAULT_PER_PAGE = 100
REQUEST_TIMEOUT = 30

def _headers(token: Optional[str]):
    h = {"Accept": "application/vnd.github.v3+json"}
    token = token or os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"token {token}"
    return h

def _get_raw(url: str, token: Optional[str] = None, params: dict = None):
    resp = requests.get(url, headers=_headers(token), params=params or {}, timeout=REQUEST_TIMEOUT)
    if resp.status_code in (200, 201):
        return resp.json()
    else:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"GitHub API error {resp.status_code} at {url}: {detail}")

def paginate_get(path: str, token: Optional[str] = None, per_page:int=DEFAULT_PER_PAGE, max_pages:int=3, extra_params:dict=None):
    results = []
    for page in range(1, max_pages + 1):
        params = {"per_page": per_page, "page": page}
        if extra_params:
            params.update(extra_params)
        url = f"{BASE_URL}{path}"
        page_data = _get_raw(url, token=token, params=params)
        if not isinstance(page_data, list):
            return page_data
        results.extend(page_data)
        if len(page_data) < per_page:
            break
        time.sleep(0.05)
    return results

def get_repo_data(owner: str, repo: str, token: Optional[str] = None) -> Dict:
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    return _get_raw(url, token=token)

def get_contributors(owner: str, repo: str, token: Optional[str] = None, per_page:int=100, max_pages:int=3) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/contributors", token=token, per_page=per_page, max_pages=max_pages)

def get_commits(owner: str, repo: str, token: Optional[str] = None, per_page:int=100, max_pages:int=3) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/commits", token=token, per_page=per_page, max_pages=max_pages)

def get_commit_details(owner: str, repo: str, sha: str, token: Optional[str] = None) -> Dict:
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits/{sha}"
    return _get_raw(url, token=token)

def get_pulls(owner: str, repo: str, state: str = "all", token: Optional[str] = None, per_page:int=100, max_pages:int=3) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/pulls", token=token, per_page=per_page, max_pages=max_pages, extra_params={"state": state})

def get_pull_details(owner: str, repo: str, pr_number: int, token: Optional[str] = None) -> Dict:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
    return _get_raw(url, token=token)

def get_pull_reviews(owner: str, repo: str, pr_number: int, token: Optional[str] = None, per_page:int=100, max_pages:int=2) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews", token=token, per_page=per_page, max_pages=max_pages)

def get_pull_files(owner: str, repo: str, pr_number: int, token: Optional[str] = None, per_page:int=100, max_pages:int=2) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files", token=token, per_page=per_page, max_pages=max_pages)

def get_issues(owner: str, repo: str, state: str = "all", token: Optional[str] = None, per_page:int=100, max_pages:int=2) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/issues", token=token, per_page=per_page, max_pages=max_pages, extra_params={"state": state})

def get_issue_comments(owner: str, repo: str, issue_number: int, token: Optional[str] = None, per_page:int=100, max_pages:int=2) -> List[Dict]:
    return paginate_get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments", token=token, per_page=per_page, max_pages=max_pages)

def summarize_commits(commits: List[Dict]) -> List[Dict]:
    out = []
    for c in commits:
        sha = c.get("sha")
        commit_meta = c.get("commit", {}) or {}
        author = commit_meta.get("author") or {}
        date = author.get("date")
        author_login = None
        if c.get("author") and isinstance(c["author"], dict):
            author_login = c["author"].get("login")
        author_name = author.get("name")
        out.append({"sha": sha, "date": date, "author_login": author_login, "author_name": author_name, "raw": c})
    return out

def get_contributor_prs(owner: str, repo: str, contributor_login: str, token: Optional[str] = None, per_page:int=100, max_pages:int=5) -> List[Dict]:
    pulls = paginate_get(f"/repos/{owner}/{repo}/pulls", token=token, per_page=per_page, max_pages=max_pages, extra_params={"state":"all"})
    contrib = [p for p in pulls if ((p.get("user") or {}).get("login") == contributor_login)]
    detailed = []
    for p in contrib:
        num = p.get("number")
        if num is None:
            continue
        try:
            det = get_pull_details(owner, repo, num, token=token)
            try:
                det["_reviews"] = get_pull_reviews(owner, repo, num, token=token, max_pages=2)
            except Exception:
                det["_reviews"] = []
            try:
                det["_files"] = get_pull_files(owner, repo, num, token=token, max_pages=2)
            except Exception:
                det["_files"] = []
            detailed.append(det)
            time.sleep(0.05)
        except Exception:
            detailed.append(p)
    return detailed
