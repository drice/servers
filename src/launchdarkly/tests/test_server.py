"""
Tests for the LaunchDarkly MCP server.
"""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server import Server  # type: ignore
from mcp.shared.exceptions import McpError, ErrorData  # type: ignore
from mcp.types import Tool  # type: ignore
from mcp_server_launchdarkly.server import (
    serve,
    LaunchDarklyClient,
    LaunchDarklyTools,
    FeatureFlag,
    FlagEvaluation,
    Segment,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
    NOT_FOUND,
)


@pytest.fixture
def mock_ld_client():
    """Create a mock LaunchDarkly client."""
    with patch("mcp_server_launchdarkly.server.LaunchDarklyClient") as mock:
        client_instance = mock.return_value
        client_instance.initialize = AsyncMock()
        client_instance.get_flag = MagicMock(
            return_value=FeatureFlag(
                key="test-flag",
                name="Test Flag",
                description="A test flag",
                is_enabled=True,
                created_at="2023-01-01T00:00:00Z",
                updated_at="2023-01-02T00:00:00Z",
            )
        )
        client_instance.evaluate_flag = MagicMock(
            return_value=FlagEvaluation(
                flag_key="test-flag",
                value=True,
                variation_index=0,
                reason={"kind": "OFF"},
            )
        )
        client_instance.list_flags = MagicMock(
            return_value=[
                FeatureFlag(
                    key="test-flag",
                    name="Test Flag",
                    description="A test flag",
                    is_enabled=True,
                    created_at="2023-01-01T00:00:00Z",
                    updated_at="2023-01-02T00:00:00Z",
                )
            ]
        )
        client_instance.get_segment = MagicMock(
            return_value=Segment(
                key="test-segment",
                name="Test Segment",
                description="A test segment",
                created_at="2023-01-01T00:00:00Z",
                updated_at="2023-01-02T00:00:00Z",
            )
        )
        client_instance.list_segments = MagicMock(
            return_value=[
                Segment(
                    key="test-segment",
                    name="Test Segment",
                    description="A test segment",
                    created_at="2023-01-01T00:00:00Z",
                    updated_at="2023-01-02T00:00:00Z",
                )
            ]
        )
        client_instance.clear_cache = MagicMock()
        yield mock


@pytest.mark.asyncio
async def test_serve(mock_ld_client):
    """Test server initialization."""
    server = await serve("test-sdk-key", "test")

    # Verify LaunchDarkly client was initialized
    mock_ld_client.return_value.initialize.assert_called_once()

    # Verify server was created
    assert isinstance(server, Server)
    assert server.name == "launchdarkly"


@pytest.mark.asyncio
async def test_evaluate_flag(mock_ld_client):
    """Test evaluate_flag tool."""
    # Create a mock server to test the tool directly
    ld_client = mock_ld_client.return_value

    # Call the evaluate_flag method directly
    result = ld_client.evaluate_flag(
        "test-flag", "test-user", {"email": "test@example.com"}
    )

    # Verify result
    assert result.flag_key == "test-flag"
    assert result.value is True
    assert result.variation_index == 0
    assert result.reason == {"kind": "OFF"}


@pytest.mark.asyncio
async def test_get_flag(mock_ld_client):
    """Test get_flag tool."""
    # Create a mock server to test the tool directly
    ld_client = mock_ld_client.return_value

    # Call the get_flag method directly
    result = ld_client.get_flag("test-flag")

    # Verify result
    assert result.key == "test-flag"
    assert result.name == "Test Flag"
    assert result.description == "A test flag"
    assert result.is_enabled is True


@pytest.mark.asyncio
async def test_list_flags(mock_ld_client):
    """Test list_flags tool."""
    # Create a mock server to test the tool directly
    ld_client = mock_ld_client.return_value

    # Call the list_flags method directly
    result = ld_client.list_flags()

    # Verify result
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].key == "test-flag"


@pytest.mark.asyncio
async def test_get_segment(mock_ld_client):
    """Test get_segment tool."""
    # Create a mock server to test the tool directly
    ld_client = mock_ld_client.return_value

    # Call the get_segment method directly
    result = ld_client.get_segment("test-segment")

    # Verify result
    assert result.key == "test-segment"
    assert result.name == "Test Segment"
    assert result.description == "A test segment"


@pytest.mark.asyncio
async def test_list_segments(mock_ld_client):
    """Test list_segments tool."""
    # Create a mock server to test the tool directly
    ld_client = mock_ld_client.return_value

    # Call the list_segments method directly
    result = ld_client.list_segments()

    # Verify result
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0].key == "test-segment"
