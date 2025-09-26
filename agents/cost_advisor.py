# agents/cost_advisor.py
import json
import logging
from utils.claude_client import call_claude_json

logger = logging.getLogger(__name__)

async def estimate_cost(sql: str, explain):
    base = {"agent": "cost_advisor", "status": None, "query": sql, "details": {}}
    prompt = f"""
You are a Cost Advisor for MariaDB.

SQL:
{sql}

EXPLAIN:
{json.dumps(explain, indent=2, default=str)}

Estimate relative cost/IO/runtime based on EXPLAIN (e.g., rows examined, type, key usage) and give concrete tips to reduce cost.
Focus on MariaDB specifics: buffer pool efficiency, query cache hits, index covering, avoiding temp tables/filesort.
Return JSON ONLY:
{{
  "estimated_cost": "low|medium|high or numeric (e.g., based on rows * selectivity)",
  "cost_saving_tips": ["..."],
  "warnings": ["..."]
}}
"""
    resp = await call_claude_json(prompt, max_tokens=800)
    if "error" in resp:
        return {**base, "status": "error", "details": {"error": resp.get("error")}}
    details = {
        "estimated_cost": resp.get("estimated_cost"),
        "cost_saving_tips": resp.get("cost_saving_tips", []),
        "warnings": resp.get("warnings", [])
    }
    return {**base, "status": "success", "details": details}
