import httpx
from typing import cast
from .types import SentryIssue, SentryIssueHash, SentryProject

SENTRY_API_BASE = "https://sentry.io/api/0/"


class SentryClient:
    def __init__(self, auth_token: str, base_url: str = SENTRY_API_BASE):
        self._client = httpx.AsyncClient(base_url=base_url)
        self._auth_token = auth_token

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self._auth_token}"
        kwargs["headers"] = headers
        return self._client.request(method, url, **kwargs)

    async def get_issue(self, issue_id: str) -> SentryIssue:
        url = f"issues/{issue_id}/"
        response = await self.get(url)
        response.raise_for_status()
        issue = cast(SentryIssue, response.json())
        return issue

    async def get_issue_hashes(self, issue_id: str) -> list[SentryIssueHash]:
        url = f"issues/{issue_id}/hashes/"
        response = await self.get(url)
        response.raise_for_status()
        hashes = cast(list[SentryIssueHash], response.json())
        return hashes

    async def list_project_issues(
        self,
        organization: str,
        environment: str,
        project: str,
        statsPeriod: str = "24h",
        query: str = "is:unresolved",
        shortIdLookup: bool = False,
        sort: str = None,
        cursor: str = None,
        limit: int = None,
    ) -> list[SentryIssue]:
        params = {
            "environment": environment,
            "statsPeriod": statsPeriod,
        }
        if project:
            params["project"] = project
        if query:
            params["query"] = query
        if sort:
            params["sort"] = sort
        if limit:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        response = await self._client.get(
            f"organizations/{organization}/issues/",
            params=params,
        )
        response.raise_for_status()
        issues = cast(list[SentryIssue], response.json())
        return issues

    async def list_projects(self, organization: str) -> list[SentryProject]:
        # TODO: Add support for pagination
        response = await self._client.get(f"organizations/{organization}/projects/")
        response.raise_for_status()
        projects = cast(list[SentryProject], response.json())
        return projects
