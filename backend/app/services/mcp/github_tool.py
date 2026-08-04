import httpx
from typing import Dict, Any, List
from app.services.mcp.base_tool import BaseMCPTool
from app.schemas.mcp import ToolDefinition, ToolParameter
from app.models.user import User
from app.core.config import settings

class GitHubMCPTool(BaseMCPTool):
    """
    GitHub MCP Tool providing repository and issue intelligence.
    Uses async httpx to interact with the GitHub API.
    """
    
    def __init__(self):
        self.base_url = "https://api.github.com"

    async def _get_client(self, user: User) -> httpx.AsyncClient:
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        
        from app.db.session import AsyncSessionLocal
        from app.models.settings import Settings
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            stmt = select(Settings).where(Settings.user_id == user.id)
            result = await db.execute(stmt)
            user_settings = result.scalars().first()
            
            pat = None
            if user_settings and user_settings.github_pat:
                pat = user_settings.github_pat
            elif settings.GITHUB_ACCESS_TOKEN:
                # Fallback to global setting if no user-specific token
                pat = settings.GITHUB_ACCESS_TOKEN
                
            if pat:
                headers["Authorization"] = f"token {pat}"
                
        return httpx.AsyncClient(headers=headers)

    def get_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="github.list_repositories",
                description="List repositories for the authenticated user.",
                parameters=[]
            ),
            ToolDefinition(
                name="github.repository_summary",
                description="Get a summary of a specific repository.",
                parameters=[
                    ToolParameter(name="repo_name", type="string", description="The full name of the repository (e.g. 'owner/repo')", required=True)
                ]
            ),
            ToolDefinition(
                name="github.list_prs",
                description="List pull requests for a specific repository.",
                parameters=[
                    ToolParameter(name="repo_name", type="string", description="The full name of the repository (e.g. 'owner/repo')", required=True),
                    ToolParameter(name="state", type="string", description="State of the PRs (open, closed, all)", required=False)
                ]
            ),
            ToolDefinition(
                name="github.list_issues",
                description="List issues for a specific repository.",
                parameters=[
                    ToolParameter(name="repo_name", type="string", description="The full name of the repository (e.g. 'owner/repo')", required=True),
                    ToolParameter(name="state", type="string", description="State of the issues (open, closed, all)", required=False)
                ]
            )
        ]

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user: User) -> Any:
        # Route execution based on tool_name
        async with await self._get_client(user) as client:
            if tool_name == "github.list_repositories":
                return await self._list_repositories(client)
            elif tool_name == "github.repository_summary":
                return await self._repository_summary(client, arguments.get("repo_name"))
            elif tool_name == "github.list_prs":
                return await self._list_prs(client, arguments.get("repo_name"), arguments.get("state", "open"))
            elif tool_name == "github.list_issues":
                return await self._list_issues(client, arguments.get("repo_name"), arguments.get("state", "open"))
            else:
                raise ValueError(f"Unknown GitHub tool: {tool_name}")

    async def _list_repositories(self, client: httpx.AsyncClient) -> Any:
        response = await client.get(f"{self.base_url}/user/repos?sort=updated")
        response.raise_for_status()
        repos = response.json()
        return [{"name": r["full_name"], "description": r["description"], "url": r["html_url"], "stars": r["stargazers_count"]} for r in repos[:10]]

    async def _repository_summary(self, client: httpx.AsyncClient, repo_name: str) -> Any:
        if not repo_name:
            raise ValueError("repo_name is required")
        response = await client.get(f"{self.base_url}/repos/{repo_name}")
        response.raise_for_status()
        data = response.json()
        return {
            "name": data["full_name"],
            "description": data["description"],
            "language": data["language"],
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"]
        }

    async def _list_prs(self, client: httpx.AsyncClient, repo_name: str, state: str) -> Any:
        if not repo_name:
            raise ValueError("repo_name is required")
        response = await client.get(f"{self.base_url}/repos/{repo_name}/pulls?state={state}")
        response.raise_for_status()
        prs = response.json()
        return [{"number": pr["number"], "title": pr["title"], "user": pr["user"]["login"], "url": pr["html_url"]} for pr in prs[:10]]

    async def _list_issues(self, client: httpx.AsyncClient, repo_name: str, state: str) -> Any:
        if not repo_name:
            raise ValueError("repo_name is required")
        response = await client.get(f"{self.base_url}/repos/{repo_name}/issues?state={state}")
        response.raise_for_status()
        issues = response.json()
        # GitHub API returns PRs as issues too, we can filter them out if needed, but for simplicity returning all
        return [{"number": issue["number"], "title": issue["title"], "user": issue["user"]["login"], "url": issue["html_url"], "is_pr": "pull_request" in issue} for issue in issues[:10]]
