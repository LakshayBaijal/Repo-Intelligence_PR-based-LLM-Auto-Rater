# autorater_llm.py
import os
import json
import re
import time
from dotenv import load_dotenv

load_dotenv()

USE_GROQ = False
groq_client = None
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    try:
        from openai import OpenAI
        groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        USE_GROQ = True
    except Exception:
        USE_GROQ = False
        groq_client = None

USE_FALLBACK = True
FALLBACK_MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
fallback_model = None
if USE_FALLBACK:
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        fallback_model = SentenceTransformer(FALLBACK_MODEL_NAME)
    except Exception:
        fallback_model = None
        USE_FALLBACK = False

PROMPT_TEMPLATE = """
You are an expert open-source maintainer.

Below are example PRs (title, body, changed files summary, and review summaries).
For the given contributor, produce ONLY valid JSON with EXACT keys:

{{
  "code_quality": int,            // 0-25
  "problem_significance": int,    // 0-25
  "review_engagement": int,       // 0-25
  "consistency": int,             // 0-25
  "total_score": int,             // 0-100
  "reasoning": "one-sentence explanation"
}}

PRs:
{prs}
"""

def _summarize_pr_for_prompt(pr):
    title = pr.get("title", "") or ""
    body = (pr.get("body") or "")[:1000]
    files = pr.get("_files") or pr.get("files") or []
    files_sample = []
    if isinstance(files, list):
        for f in files[:10]:
            if isinstance(f, dict):
                files_sample.append(f.get("filename", ""))
            else:
                files_sample.append(str(f))
    else:
        files_sample = [str(files)]
    reviews = pr.get("_reviews") or []
    reviews_sample = []
    for r in reviews[:8]:
        reviewer = (r.get("user") or {}).get("login") or str(r.get("author_association") or "")
        state = r.get("state") or ""
        body_r = r.get("body") or ""
        reviews_sample.append(f"{reviewer}:{state}:{body_r[:200]}")
    return f"TITLE: {title}\nBODY: {body}\nFILES_SAMPLE: {files_sample}\nREVIEWS_SAMPLE: {reviews_sample}\n---\n"

def _format_prs_for_prompt(prs):
    if not prs:
        return "NO_PRS"
    prs_sorted = sorted(prs, key=lambda p: (1 if p.get("merged_at") else 0, p.get("changed_files") or 0), reverse=True)[:6]
    return "\n\n".join(_summarize_pr_for_prompt(p) for p in prs_sorted)

def _extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

def _fallback_from_prs(prs):
    if not fallback_model:
        return {"error": "fallback embedding model unavailable"}
    QUALITY_PATTERNS = ["fix", "bug", "refactor", "test", "cleanup", "improve", "optimize"]
    SIGNIFICANCE_PATTERNS = ["major", "core", "security", "critical", "performance", "feature"]
    REVIEW_PATTERNS = ["review", "approved", "request changes", "comment"]
    texts = []
    review_texts = []
    for p in prs[:20]:
        texts.append((p.get("title","") + "\n" + (p.get("body") or ""))[:1000])
        for r in (p.get("_reviews") or [])[:5]:
            review_texts.append((r.get("body") or "")[:400] + " " + (r.get("state") or ""))
    if not any(texts):
        return {
            "code_quality": 0,
            "problem_significance": 0,
            "review_engagement": 0,
            "consistency": 0,
            "total_score": 0,
            "reasoning": "No PR text available"
        }
    emb_texts = fallback_model.encode(texts)
    emb_q = fallback_model.encode(QUALITY_PATTERNS)
    emb_s = fallback_model.encode(SIGNIFICANCE_PATTERNS)
    emb_r = fallback_model.encode(REVIEW_PATTERNS)
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    sim_q = cosine_similarity(emb_texts, emb_q) if emb_q.size else None
    sim_s = cosine_similarity(emb_texts, emb_s) if emb_s.size else None
    sim_r = cosine_similarity(fallback_model.encode(review_texts) if review_texts else [fallback_model.encode([""])], emb_r) if emb_r.size else None
    qscore = float(sim_q.max()) if sim_q is not None and sim_q.size else 0.0
    sscore = float(sim_s.max()) if sim_s is not None and sim_s.size else 0.0
    rscore = float(sim_r.max()) if sim_r is not None and sim_r.size else 0.0
    consistency = min(len(prs)/6.0, 1.0)
    code_quality = int(qscore*25)
    problem_significance = int(sscore*25)
    review_engagement = int(rscore*25)
    consistency_i = int(consistency*25)
    total = max(0, min(100, code_quality + problem_significance + review_engagement + consistency_i))
    return {
        "code_quality": code_quality,
        "problem_significance": problem_significance,
        "review_engagement": review_engagement,
        "consistency": consistency_i,
        "total_score": total,
        "reasoning": "Fallback semantic scoring from PR titles/bodies/reviews."
    }

def evaluate_contributor_with_groq(prs):
    """
    Primary: call Groq with PR summaries (title, body, files, reviews).
    Fallback: use local embedding-based scorer if Groq not available or returns non-JSON.
    """
    if not prs:
        return {
            "code_quality": 0,
            "problem_significance": 0,
            "review_engagement": 0,
            "consistency": 0,
            "total_score": 0,
            "reasoning": "No PRs available"
        }

    if USE_GROQ and groq_client is not None:
        prompt = PROMPT_TEMPLATE.format(prs=_format_prs_for_prompt(prs))
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert open-source maintainer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            text = resp.choices[0].message.content
            parsed = _extract_json(text)
            if isinstance(parsed, dict):
                for k in ["code_quality","problem_significance","review_engagement","consistency","total_score"]:
                    if k in parsed:
                        try:
                            parsed[k] = int(parsed[k])
                        except Exception:
                            pass
                return parsed
        except Exception:
            time.sleep(0.1)

    if USE_FALLBACK and fallback_model is not None:
        try:
            return _fallback_from_prs(prs)
        except Exception as e:
            return {"error": f"fallback error: {e}"}

    return {"error": "No LLM available (GROQ missing and fallback not available)."}