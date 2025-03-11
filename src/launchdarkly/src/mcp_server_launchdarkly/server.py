"""
LaunchDarkly MCP Server implementation.

This module implements a Model Context Protocol server that integrates with
LaunchDarkly's feature flag management system, allowing clients to query
and evaluate feature flags through the MCP interface.
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union, cast
import contextlib

import httpx  # type: ignore
import ldclient  # type: ignore
from ldclient import LDClient  # type: ignore
from ldclient.config import Config  # type: ignore
from ldclient.context import Context  # type: ignore
import launchdarkly_api as ld_api  # type: ignore
from pydantic import BaseModel, Field  # type: ignore

from mcp.server import NotificationOptions, Server  # type: ignore
from mcp.server.models import InitializationOptions  # type: ignore
from mcp.shared.exceptions import McpError, ErrorData  # type: ignore
from mcp.types import (  # type: ignore
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool,
)


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_server_launchdarkly")

# Error codes
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
NOT_FOUND = 404


class LaunchDarklyTools(str, Enum):
    """Enumeration of available LaunchDarkly tools."""

    GET_FLAG = "get_flag"
    LIST_FLAGS = "list_flags"
    EVALUATE_FLAG = "evaluate_flag"
    GET_SEGMENT = "get_segment"
    LIST_SEGMENTS = "list_segments"
    STREAM_FLAGS = "stream_flags"  # New tool for streaming flag updates


class FlagVariation(BaseModel):
    """Model representing a feature flag variation."""

    value: Any
    description: Optional[str] = None


class FeatureFlag(BaseModel):
    """Model representing a feature flag."""

    key: str
    name: Optional[str] = None
    description: Optional[str] = None
    variations: List[FlagVariation] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    is_enabled: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Segment(BaseModel):
    """Model representing a user segment."""

    key: str
    name: Optional[str] = None
    description: Optional[str] = None
    included: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FlagEvaluation(BaseModel):
    """Model representing a feature flag evaluation result."""

    flag_key: str
    value: Any
    variation_index: Optional[int] = None
    reason: Optional[Dict[str, Any]] = None


class LaunchDarklyClient:
    """Client for interacting with LaunchDarkly."""

    def __init__(self, sdk_key: str, environment: str = "production"):
        """Initialize the LaunchDarkly client.

        Args:
            sdk_key: LaunchDarkly SDK key
            environment: LaunchDarkly environment name
        """
        self.sdk_key = sdk_key
        self.environment = environment
        self.client: Optional[LDClient] = None
        self.api_client: Optional[ld_api.ApiClient] = None
        self._cache: Dict[str, Any] = {}  # Simple in-memory cache

    async def initialize(self) -> None:
        """Initialize the LaunchDarkly client."""
        if not self.sdk_key:
            raise McpError(
                ErrorData(
                    code=INVALID_REQUEST, message="LaunchDarkly SDK key is required"
                )
            )

        try:
            # Configure the LaunchDarkly client
            config = Config(
                sdk_key=self.sdk_key,
                application={"id": "mcp-server-launchdarkly", "version": "0.1.0"},
            )

            # Initialize the SDK client
            self.client = LDClient(config=config)

            # Initialize the API client
            configuration = ld_api.Configuration()
            configuration.api_key["Authorization"] = self.sdk_key
            self.api_client = ld_api.ApiClient(configuration)

            # Wait for client initialization
            if self.client and not self.client.is_initialized():
                logger.info("Waiting for LaunchDarkly client to initialize...")
                timeout = 10  # seconds
                start_time = asyncio.get_event_loop().time()
                while self.client and not self.client.is_initialized():
                    await asyncio.sleep(0.1)
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        raise McpError(
                            ErrorData(
                                code=INTERNAL_ERROR,
                                message=f"LaunchDarkly client initialization timed out after {timeout} seconds",
                            )
                        )

            logger.info("LaunchDarkly client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LaunchDarkly client: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to initialize LaunchDarkly client: {str(e)}",
                )
            )

    def close(self) -> None:
        """Close the LaunchDarkly client."""
        if self.client:
            self.client.close()
            logger.info("LaunchDarkly client closed")

        if self.api_client:
            self.api_client.close()
            logger.info("LaunchDarkly API client closed")

    def get_flag(self, flag_key: str) -> FeatureFlag:
        """Get a feature flag by key.

        Args:
            flag_key: Feature flag key

        Returns:
            FeatureFlag: Feature flag details
        """
        if not self.client or not self.api_client:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="LaunchDarkly client not initialized"
                )
            )

        # Check cache first
        cache_key = f"flag:{flag_key}"
        if cache_key in self._cache:
            logger.info(f"Cache hit for flag {flag_key}")
            return self._cache[cache_key]

        try:
            # Use the LaunchDarkly API to get flag details
            if not self.api_client:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="LaunchDarkly API client not initialized",
                    )
                )
            feature_flags_api = ld_api.FeatureFlagsApi(self.api_client)
            flag_response = feature_flags_api.get_feature_flag(
                project_key="default", feature_flag_key=flag_key, env=self.environment
            )

            # Convert API response to our model
            variations = []
            for variation in flag_response.variations:
                variations.append(
                    FlagVariation(
                        value=variation.value,
                        description=variation.description,
                    )
                )

            flag = FeatureFlag(
                key=flag_response.key,
                name=flag_response.name,
                description=flag_response.description,
                variations=variations,
                tags=flag_response.tags,
                is_enabled=flag_response.on,
                created_at=flag_response._creation_date,
                updated_at=flag_response._last_modified,
            )

            # Cache the result
            self._cache[cache_key] = flag

            return flag
        except ld_api.ApiException as e:
            logger.error(f"API error getting flag {flag_key}: {e}")
            if e.status == 404:
                raise McpError(
                    ErrorData(code=NOT_FOUND, message=f"Flag {flag_key} not found")
                )
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get flag {flag_key}: {str(e)}",
                )
            )
        except Exception as e:
            logger.error(f"Error getting flag {flag_key}: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get flag {flag_key}: {str(e)}",
                )
            )

    def list_flags(self) -> List[FeatureFlag]:
        """List all feature flags.

        Returns:
            List[FeatureFlag]: List of feature flags
        """
        if not self.client or not self.api_client:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="LaunchDarkly client not initialized"
                )
            )

        # Check cache first
        cache_key = "flags:list"
        if cache_key in self._cache:
            logger.info("Cache hit for flag list")
            return self._cache[cache_key]

        try:
            # Use the LaunchDarkly API to list flags
            if not self.api_client:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="LaunchDarkly API client not initialized",
                    )
                )
            feature_flags_api = ld_api.FeatureFlagsApi(self.api_client)
            flags_response = feature_flags_api.get_feature_flags(
                project_key="default", env=self.environment
            )

            flags = []
            for item in flags_response.items:
                variations = []
                for variation in item.variations:
                    variations.append(
                        FlagVariation(
                            value=variation.value,
                            description=variation.description,
                        )
                    )

                flags.append(
                    FeatureFlag(
                        key=item.key,
                        name=item.name,
                        description=item.description,
                        variations=variations,
                        tags=item.tags,
                        is_enabled=item.on,
                        created_at=item._creation_date,
                        updated_at=item._last_modified,
                    )
                )

            # Cache the result
            self._cache[cache_key] = flags

            return flags
        except ld_api.ApiException as e:
            logger.error(f"API error listing flags: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to list flags: {str(e)}"
                )
            )
        except Exception as e:
            logger.error(f"Error listing flags: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to list flags: {str(e)}"
                )
            )

    def evaluate_flag(
        self, flag_key: str, user_key: str, attributes: Optional[Dict[str, Any]] = None
    ) -> FlagEvaluation:
        """Evaluate a feature flag for a user.

        Args:
            flag_key: Feature flag key
            user_key: User identifier
            attributes: Additional user attributes

        Returns:
            FlagEvaluation: Feature flag evaluation result
        """
        if not self.client:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="LaunchDarkly client not initialized"
                )
            )

        try:
            if not self.client:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="LaunchDarkly client not initialized",
                    )
                )

            # Create context object (new in SDK v9+)
            context_builder = Context.builder(user_key)
            if attributes:
                for key, value in attributes.items():
                    context_builder.set(key, value)

            context = context_builder.build()

            # Evaluate the flag
            detail = self.client.variation_detail(flag_key, context, None)

            # Extract reason
            reason = None
            if detail.reason:
                reason = {
                    "kind": detail.reason.get("kind", ""),
                    "rule_index": detail.reason.get("ruleIndex"),
                    "rule_id": detail.reason.get("ruleId"),
                    "prerequisite_key": detail.reason.get("prerequisiteKey"),
                }

            return FlagEvaluation(
                flag_key=flag_key,
                value=detail.value,
                variation_index=detail.variation_index,
                reason=reason,
            )
        except Exception as e:
            logger.error(f"Error evaluating flag {flag_key} for user {user_key}: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to evaluate flag {flag_key}: {str(e)}",
                )
            )

    def get_segment(self, segment_key: str) -> Segment:
        """Get a user segment by key.

        Args:
            segment_key: Segment key

        Returns:
            Segment: User segment details
        """
        if not self.client or not self.api_client:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="LaunchDarkly client not initialized"
                )
            )

        # Check cache first
        cache_key = f"segment:{segment_key}"
        if cache_key in self._cache:
            logger.info(f"Cache hit for segment {segment_key}")
            return self._cache[cache_key]

        try:
            # Use the LaunchDarkly API to get segment details
            if not self.api_client:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="LaunchDarkly API client not initialized",
                    )
                )
            segments_api = ld_api.SegmentsApi(self.api_client)
            segment_response = segments_api.get_segment(
                project_key="default",
                environment_key=self.environment,
                segment_key=segment_key,
            )

            # Convert API response to our model
            segment = Segment(
                key=segment_response.key,
                name=segment_response.name,
                description=segment_response.description,
                included=segment_response.included,
                excluded=segment_response.excluded,
                rules=segment_response.rules,
                created_at=segment_response._creation_date,
                updated_at=segment_response._last_modified,
            )

            # Cache the result
            self._cache[cache_key] = segment

            return segment
        except ld_api.ApiException as e:
            logger.error(f"API error getting segment {segment_key}: {e}")
            if e.status == 404:
                raise McpError(
                    ErrorData(
                        code=NOT_FOUND, message=f"Segment {segment_key} not found"
                    )
                )
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get segment {segment_key}: {str(e)}",
                )
            )
        except Exception as e:
            logger.error(f"Error getting segment {segment_key}: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get segment {segment_key}: {str(e)}",
                )
            )

    def list_segments(self) -> List[Segment]:
        """List all user segments.

        Returns:
            List[Segment]: List of user segments
        """
        if not self.client or not self.api_client:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message="LaunchDarkly client not initialized"
                )
            )

        # Check cache first
        cache_key = "segments:list"
        if cache_key in self._cache:
            logger.info("Cache hit for segment list")
            return self._cache[cache_key]

        try:
            # Use the LaunchDarkly API to list segments
            if not self.api_client:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="LaunchDarkly API client not initialized",
                    )
                )
            segments_api = ld_api.SegmentsApi(self.api_client)
            segments_response = segments_api.get_segments(
                project_key="default", environment_key=self.environment
            )

            segments = []
            for item in segments_response.items:
                segments.append(
                    Segment(
                        key=item.key,
                        name=item.name,
                        description=item.description,
                        included=item.included,
                        excluded=item.excluded,
                        rules=item.rules,
                        created_at=item._creation_date,
                        updated_at=item._last_modified,
                    )
                )

            # Cache the result
            self._cache[cache_key] = segments

            return segments
        except ld_api.ApiException as e:
            logger.error(f"API error listing segments: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to list segments: {str(e)}"
                )
            )
        except Exception as e:
            logger.error(f"Error listing segments: {e}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to list segments: {str(e)}"
                )
            )

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        logger.info("Cache cleared")


@contextlib.asynccontextmanager
async def server_lifespan(server: Server):
    """Lifespan context manager for the server."""
    ld_client = server.ld_client
    try:
        yield
    finally:
        if ld_client:
            ld_client.close()


async def serve(sdk_key: str, environment: str = "production") -> Server:
    """Create and configure the LaunchDarkly MCP server.

    Args:
        sdk_key: LaunchDarkly SDK key
        environment: LaunchDarkly environment name

    Returns:
        Server: Configured MCP server
    """
    ld_client = LaunchDarklyClient(sdk_key, environment)

    # Initialize the LaunchDarkly client
    await ld_client.initialize()

    # Create a custom lifespan function that will close the client
    async def custom_lifespan(server: Server):
        try:
            yield
        finally:
            ld_client.close()

    # Create the server with the custom lifespan
    server = Server("launchdarkly", lifespan=custom_lifespan)

    # Store the client on the server for access in the lifespan
    server.ld_client = ld_client

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        """List available LaunchDarkly tools."""
        return [
            Tool(
                name=LaunchDarklyTools.EVALUATE_FLAG.value,
                description="Evaluate a feature flag for a given user context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flag_key": {
                            "type": "string",
                            "description": "Feature flag key to evaluate",
                        },
                        "user_key": {
                            "type": "string",
                            "description": "Unique user identifier",
                        },
                        "attributes": {
                            "type": "object",
                            "description": "Additional user attributes",
                        },
                    },
                    "required": ["flag_key", "user_key"],
                },
            ),
            Tool(
                name=LaunchDarklyTools.GET_FLAG.value,
                description="Get details about a specific feature flag",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flag_key": {
                            "type": "string",
                            "description": "Feature flag key",
                        },
                    },
                    "required": ["flag_key"],
                },
            ),
            Tool(
                name=LaunchDarklyTools.LIST_FLAGS.value,
                description="List all available feature flags",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name=LaunchDarklyTools.GET_SEGMENT.value,
                description="Get details about a specific user segment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "segment_key": {
                            "type": "string",
                            "description": "User segment key",
                        },
                    },
                    "required": ["segment_key"],
                },
            ),
            Tool(
                name=LaunchDarklyTools.LIST_SEGMENTS.value,
                description="List all available user segments",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name=LaunchDarklyTools.STREAM_FLAGS.value,
                description="Stream flag updates in real-time",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "flag_keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of flag keys to stream. If not provided, all flags will be streamed.",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any]
    ) -> Sequence[Union[TextContent, ImageContent, EmbeddedResource]]:
        """Handle tool calls for LaunchDarkly operations."""
        try:
            if name == LaunchDarklyTools.EVALUATE_FLAG.value:
                if "flag_key" not in arguments or "user_key" not in arguments:
                    raise McpError(
                        ErrorData(
                            code=INVALID_PARAMS,
                            message="Missing required arguments: flag_key and user_key",
                        )
                    )

                flag_key = arguments["flag_key"]
                user_key = arguments["user_key"]
                attributes = arguments.get("attributes", {})

                result = ld_client.evaluate_flag(flag_key, user_key, attributes)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result.dict(), indent=2),
                    )
                ]

            elif name == LaunchDarklyTools.GET_FLAG.value:
                if "flag_key" not in arguments:
                    raise McpError(
                        ErrorData(
                            code=INVALID_PARAMS,
                            message="Missing required argument: flag_key",
                        )
                    )

                flag_key = arguments["flag_key"]
                result = ld_client.get_flag(flag_key)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result.dict(), indent=2),
                    )
                ]

            elif name == LaunchDarklyTools.LIST_FLAGS.value:
                result = ld_client.list_flags()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps([flag.dict() for flag in result], indent=2),
                    )
                ]

            elif name == LaunchDarklyTools.GET_SEGMENT.value:
                if "segment_key" not in arguments:
                    raise McpError(
                        ErrorData(
                            code=INVALID_PARAMS,
                            message="Missing required argument: segment_key",
                        )
                    )

                segment_key = arguments["segment_key"]
                result = ld_client.get_segment(segment_key)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result.dict(), indent=2),
                    )
                ]

            elif name == LaunchDarklyTools.LIST_SEGMENTS.value:
                result = ld_client.list_segments()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [segment.dict() for segment in result], indent=2
                        ),
                    )
                ]

            else:
                raise McpError(
                    ErrorData(code=METHOD_NOT_FOUND, message=f"Unknown tool: {name}")
                )

        except Exception as e:
            logger.error(f"Error handling tool call {name}: {e}")
            if isinstance(e, McpError):
                raise e
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Error handling tool call: {str(e)}"
                )
            )

    return server
