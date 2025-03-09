import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

import click
from httpx import HTTPStatusError
import mcp.types as types
from mcp_server_sentry.client.types.issue_hash import LatestEvent
from .client.client import SentryClient, SENTRY_API_BASE
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
import mcp.server.stdio

MISSING_AUTH_TOKEN_MESSAGE = (
    """Sentry authentication token not found. Please specify your Sentry auth token."""
)


@dataclass
class SentryIssueData:
    title: str
    issue_id: str
    status: str
    level: str
    first_seen: str
    last_seen: str
    count: int
    stacktrace: str

    def to_text(self) -> str:
        return f"""
Sentry Issue: {self.title}
Issue ID: {self.issue_id}
Status: {self.status}
Level: {self.level}
First Seen: {self.first_seen}
Last Seen: {self.last_seen}
Event Count: {self.count}

{self.stacktrace}
        """

    def to_prompt_result(self) -> types.GetPromptResult:
        return types.GetPromptResult(
            description=f"Sentry Issue: {self.title}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=self.to_text()),
                )
            ],
        )

    def to_tool_result(
        self,
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        return [types.TextContent(type="text", text=self.to_text())]


class SentryError(Exception):
    pass


def extract_issue_id(issue_id_or_url: str) -> str:
    """
    Extracts the Sentry issue ID from either a full URL or a standalone ID.

    This function validates the input and returns the numeric issue ID.
    It raises SentryError for invalid inputs, including empty strings,
    non-Sentry URLs, malformed paths, and non-numeric IDs.
    """
    if not issue_id_or_url:
        raise SentryError("Missing issue_id_or_url argument")

    if issue_id_or_url.startswith(("http://", "https://")):
        parsed_url = urlparse(issue_id_or_url)
        if not parsed_url.hostname or not parsed_url.hostname.endswith(".sentry.io"):
            raise SentryError(
                "Invalid Sentry URL. Must be a URL ending with .sentry.io"
            )

        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) < 2 or path_parts[0] != "issues":
            raise SentryError(
                "Invalid Sentry issue URL. Path must contain '/issues/{issue_id}'"
            )

        issue_id = path_parts[-1]
    else:
        issue_id = issue_id_or_url

    if not issue_id.isdigit():
        raise SentryError("Invalid Sentry issue ID. Must be a numeric value.")

    return issue_id


def create_stacktrace(latest_event: LatestEvent) -> str:
    """
    Creates a formatted stacktrace string from the latest Sentry event.

    This function extracts exception information and stacktrace details from the
    provided event dictionary, formatting them into a human-readable string.
    It handles multiple exceptions and includes file, line number, and function
    information for each frame in the stacktrace.

    Args:
        latest_event (dict): A dictionary containing the latest Sentry event data.

    Returns:
        str: A formatted string containing the stacktrace information,
             or "No stacktrace found" if no relevant data is present.
    """
    stacktraces = []
    for entry in latest_event.get("entries", []):
        if entry["type"] != "exception":
            continue

        exception_data = entry["data"]["values"]
        for exception in exception_data:
            exception_type = exception.get("type", "Unknown")
            exception_value = exception.get("value", "")
            stacktrace = exception.get("stacktrace")

            stacktrace_text = f"Exception: {exception_type}: {exception_value}\n\n"
            if stacktrace:
                stacktrace_text += "Stacktrace:\n"
                for frame in stacktrace.get("frames", []):
                    filename = frame.get("filename", "Unknown")
                    lineno = frame.get("lineNo", "?")
                    function = frame.get("function", "Unknown")

                    stacktrace_text += f"{filename}:{lineno} in {function}\n"

                    if "context" in frame:
                        context = frame["context"]
                        for ctx_line in context:
                            stacktrace_text += f"    {ctx_line[1]}\n"

                    stacktrace_text += "\n"

            stacktraces.append(stacktrace_text)

    return "\n".join(stacktraces) if stacktraces else "No stacktrace found"


async def handle_sentry_issue(
    sentry_client: SentryClient, issue_id_or_url: str
) -> SentryIssueData:
    try:
        issue_id = extract_issue_id(issue_id_or_url)

        try:
            issue_data = await sentry_client.get_issue(issue_id)
        except HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise McpError(
                    "Error: Unauthorized. Please check your MCP_SENTRY_AUTH_TOKEN token."
                )
            raise

        # Get issue hashes
        hashes = await sentry_client.get_issue_hashes(issue_id)

        if not hashes:
            raise McpError("No Sentry events found for this issue")

        latest_event = hashes[0]["latestEvent"]
        stacktrace = create_stacktrace(latest_event)

        return SentryIssueData(
            title=issue_data["title"],
            issue_id=issue_id,
            status=issue_data["status"],
            level=issue_data["level"],
            first_seen=issue_data["firstSeen"],
            last_seen=issue_data["lastSeen"],
            count=issue_data["count"],
            stacktrace=stacktrace,
        )

    except SentryError as e:
        raise McpError(str(e))
    except HTTPStatusError as e:
        raise McpError(f"Error fetching Sentry issue: {str(e)}")
    except Exception as e:
        raise McpError(f"An error occurred: {str(e)}")


async def get_project_id(
    sentry_client: SentryClient,
    organization: str,
    project_name: str,
) -> str:
    """
    Look up a project id by name.

    Args:
        project_name: The name of the project to look up

    Returns:
        The project id or None if not found
    """
    try:
        projects = await sentry_client.list_projects(organization=organization)
        for project in projects:
            if project["name"] == project_name or project["id"] == project_name:
                return project["id"]
        raise SentryError(f"Project '{project_name}' not found")
    except Exception as e:
        raise McpError(f"An error occurred: {str(e)}")


def is_project_id(project_name: str) -> bool:
    """
    Check if the project name is a numeric ID.

    Args:
        project_name: The project name to check

    Returns:
        True if the project name is a numeric ID, False otherwise
    """
    return isinstance(project_name, int) or (
        isinstance(project_name, str) and project_name.isdigit()
    )


async def handle_list_sentry_issues(
    sentry_client: SentryClient,
    organization: str,
    environment: str,
    project: str,
    statsPeriod: str = "24h",
    query: str = None,
    sort: str = None,
    limit: int = None,
    cursor: str = None,
) -> list[str]:
    if not is_project_id(project):
        project = await get_project_id(sentry_client, organization, project)

    issues = await sentry_client.list_project_issues(
        organization=organization,
        environment=environment,
        project=project,
        statsPeriod=statsPeriod,
        query=query,
        sort=sort,
        limit=limit,
    )

    return [
        SentryIssueData(
            title=issue_data["title"],
            issue_id=issue_data["id"],
            status=issue_data["status"],
            level=issue_data["level"],
            first_seen=issue_data["firstSeen"],
            last_seen=issue_data["lastSeen"],
            count=issue_data["count"],
        )
        for issue_data in issues
    ]


async def serve(auth_token: str) -> Server:
    server = Server("sentry")
    sentry_client = SentryClient(auth_token=auth_token, base_url=SENTRY_API_BASE)

    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        return [
            types.Prompt(
                name="sentry-issue",
                description="Retrieve a Sentry issue by ID or URL",
                arguments=[
                    types.PromptArgument(
                        name="issue_id_or_url",
                        description="Sentry issue ID or URL",
                        required=True,
                    )
                ],
            )
        ]

    @server.get_prompt()
    async def handle_get_prompt(
        name: str, arguments: dict[str, str] | None
    ) -> types.GetPromptResult:
        if name != "sentry-issue":
            raise ValueError(f"Unknown prompt: {name}")

        issue_id_or_url = (arguments or {}).get("issue_id_or_url", "")
        issue_data = await handle_sentry_issue(sentry_client, issue_id_or_url)
        return issue_data.to_prompt_result()

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="get_sentry_issue",
                description="""Retrieve and analyze a Sentry issue by ID or URL. Use this tool when you need to:
                - Investigate production errors and crashes
                - Access detailed stacktraces from Sentry
                - Analyze error patterns and frequencies
                - Get information about when issues first/last occurred
                - Review error counts and status""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_id_or_url": {
                            "type": "string",
                            "description": "Sentry issue ID or URL to analyze",
                        }
                    },
                    "required": ["issue_id_or_url"],
                },
            ),
            types.Tool(
                name="list_sentry_issues",
                description="""List Sentry issues for a project. Use this tool when you need to:
                - Retrieve a list of issues for a specific project
                - Filter issues by status, level, or date range
                - Get a summary of issues for analysis""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "organization": {
                            "type": "string",
                            "description": "Sentry organization identifier",
                        },
                        "environment": {
                            "type": "string",
                            "description": "Environment (e.g., production, staging)",
                        },
                        "project": {
                            "type": "string",
                            "description": "Sentry project identifier in the format of id or name (performs lookup)",
                        },
                        "duration": {
                            "type": "string",
                            "description": "Time range for issues (e.g. '7d' for the last 7 days)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Optional query for filtering issues (e.g., 'is:unresolved')",
                        },
                        "sort": {
                            "type": "string",
                            "description": "Optional sort order (e.g., 'new', 'old', 'priority', 'freq')",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Optional limit on the number of results",
                        },
                    },
                    "required": ["organization", "environment"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        try:
            if name not in ("get_sentry_issue", "list_sentry_issues"):
                raise ValueError(f"Unknown tool: {name}")
            if not arguments:
                raise ValueError("Missing required arguments")
            if name == "get_sentry_issue":
                if "issue_id_or_url" not in arguments:
                    raise ValueError("Missing required argument: issue_id_or_url")
                issue_data = await handle_sentry_issue(
                    sentry_client, arguments["issue_id_or_url"]
                )
                return issue_data.to_tool_result()
            elif name == "list_sentry_issues":
                if "project" not in arguments or "environment" not in arguments:
                    raise ValueError(
                        "Missing required arguments for list_sentry_issues"
                    )
                duration = arguments.get("duration", "7d")
                project = arguments.get("project")
                query = arguments.get("query")
                sort = arguments.get("sort")
                limit = arguments.get("limit")
                issues_summaries = await handle_list_sentry_issues(
                    sentry_client=sentry_client,
                    organization=arguments["organization"],
                    environment=arguments["environment"],
                    project=project,
                    duration=duration,
                    query=query,
                    sort=sort,
                    limit=limit,
                )
                return [
                    types.TextContent(type="text", text=summary)
                    for summary in issues_summaries
                ]
        except HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise McpError(
                    "Error: Unauthorized. Please check your MCP_SENTRY_AUTH_TOKEN token."
                )
        except Exception as err:
            message = getattr(err, "message", str(err))
            return [types.TextContent(type="text", text=f"Error: {message}")]

    return server


@click.command()
@click.option(
    "--auth-token",
    envvar="SENTRY_TOKEN",
    required=True,
    help="Sentry authentication token",
)
def main(auth_token: str):
    async def _run():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            server = await serve(auth_token)
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sentry",
                    server_version="0.4.1",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    asyncio.run(_run())
