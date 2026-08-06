"""
CI/CD Integration Service
Provides GitHub/GitLab integration for performance regression testing in PRs.
"""
import httpx
import hashlib
import hmac
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import settings
from app.models.baseline import Baseline
from app.services.lighthouse_runner import LighthouseRunner


class CICDService:
    """Service for CI/CD integrations (GitHub, GitLab)."""

    def __init__(self):
        self.github_token = settings.GITHUB_TOKEN
        self.gitlab_token = settings.GITLAB_TOKEN
        self.base_url_github = "https://api.github.com"
        self.base_url_gitlab = "https://gitlab.com/api/v4"

    async def verify_github_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        if not self.github_token:
            return False
        
        expected_signature = "sha256=" + hmac.new(
            self.github_token.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

    async def verify_gitlab_webhook(self, token: str) -> bool:
        """Verify GitLab webhook token."""
        if not self.gitlab_token:
            return False
        return hmac.compare_digest(self.gitlab_token, token)

    async def post_comment_github(
        self, 
        repo: str, 
        pr_number: int, 
        comment: str
    ) -> bool:
        """Post a comment to a GitHub PR."""
        if not self.github_token:
            return False
            
        url = f"{self.base_url_github}/repos/{repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {"body": comment}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                return response.status_code == 201
        except Exception:
            return False

    async def post_comment_gitlab(
        self,
        project_id: str,
        mr_iid: int,
        comment: str
    ) -> bool:
        """Post a comment to a GitLab MR."""
        if not self.gitlab_token:
            return False
            
        url = f"{self.base_url_gitlab}/projects/{project_id}/merge_requests/{mr_iid}/notes"
        headers = {
            "PRIVATE-TOKEN": self.gitlab_token
        }
        data = {"body": comment}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                return response.status_code == 201
        except Exception:
            return False

    def generate_report_comment(
        self,
        domain: str,
        current_score: float,
        baseline_score: Optional[float],
        metrics: Dict[str, Any],
        is_regression: bool
    ) -> str:
        """Generate a formatted comment for PR."""
        status_emoji = "🔴" if is_regression else "🟢"
        delta_str = ""
        
        if baseline_score is not None:
            delta = current_score - baseline_score
            sign = "+" if delta >= 0 else ""
            delta_str = f" ({sign}{delta:.1f})"
        
        comment = f"""
### {status_emoji} Performance Report

**URL:** `{domain}`
**Score:** `{current_score:.1f}{delta_str}`

| Metric | Value | Status |
|--------|-------|--------|
| LCP | {metrics.get('lcp', 'N/A')} | {'⚠️' if metrics.get('lcp', 0) > 2500 else '✅'} |
| FID | {metrics.get('fid', 'N/A')} | {'⚠️' if metrics.get('fid', 0) > 100 else '✅'} |
| CLS | {metrics.get('cls', 'N/A')} | {'⚠️' if metrics.get('cls', 0) > 0.1 else '✅'} |

{"⚠️ **Warning:** Performance regression detected!" if is_regression else "✅ No performance regressions detected."}
"""
        return comment

    async def handle_pull_request_event(
        self,
        provider: str,
        event_data: Dict[str, Any],
        audit_results: Dict[str, Any]
    ) -> bool:
        """Handle pull request event and post performance report."""
        if provider == "github":
            repo = event_data.get("repository", {}).get("full_name")
            pr_number = event_data.get("number")
            if not repo or not pr_number:
                return False
                
            comment = self.generate_report_comment(
                domain=audit_results.get("url", ""),
                current_score=audit_results.get("performance_score", 0),
                baseline_score=audit_results.get("baseline_score"),
                metrics=audit_results.get("metrics", {}),
                is_regression=audit_results.get("is_regression", False)
            )
            return await self.post_comment_github(repo, pr_number, comment)
            
        elif provider == "gitlab":
            project_id = str(event_data.get("project", {}).get("id"))
            mr_iid = event_data.get("object_attributes", {}).get("iid")
            if not project_id or not mr_iid:
                return False
                
            comment = self.generate_report_comment(
                domain=audit_results.get("url", ""),
                current_score=audit_results.get("performance_score", 0),
                baseline_score=audit_results.get("baseline_score"),
                metrics=audit_results.get("metrics", {}),
                is_regression=audit_results.get("is_regression", False)
            )
            return await self.post_comment_gitlab(project_id, mr_iid, comment)
            
        return False


cicd_service = CICDService()
