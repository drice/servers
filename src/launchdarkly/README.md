# LaunchDarkly MCP Server

A Model Context Protocol (MCP) server that integrates with LaunchDarkly's feature flag management system, enabling seamless access to feature flag data through the MCP interface.

## Features

- Retrieve feature flag details
- List all available feature flags
- Evaluate feature flags for user contexts
- Access user segment information
- List available user segments
- Stream flag updates in real-time
- Caching for improved performance

## Installation

### Prerequisites

- Python 3.13 or higher
- LaunchDarkly SDK key
- LaunchDarkly API key (same as SDK key)

### From Source

```bash
# Clone the repository
git clone https://github.com/modelcontextprotocol/servers.git
cd servers/src/launchdarkly

# Install using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### Using Docker

```bash
# Build the Docker image
docker build -t mcp-server-launchdarkly .

# Run the container
docker run -e LAUNCHDARKLY_SDK_KEY=your-sdk-key mcp-server-launchdarkly
```

### Using uv

```bash
# Install uv if you don't have it
pip install uv

# Install the package with uv
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

## Configuration

The LaunchDarkly MCP server requires the following configuration:

| Environment Variable | Description | Required | Default |
|----------------------|-------------|----------|---------|
| `LAUNCHDARKLY_SDK_KEY` | LaunchDarkly SDK key | Yes | - |
| `LAUNCHDARKLY_ENVIRONMENT` | LaunchDarkly environment | No | `production` |

## Usage

### Running the Server

```bash
# Set environment variables
export LAUNCHDARKLY_SDK_KEY=your-sdk-key
export LAUNCHDARKLY_ENVIRONMENT=development

# Run the server
python -m mcp_server_launchdarkly
```

### Available Tools

The LaunchDarkly MCP server provides the following tools:

#### 1. Evaluate Feature Flag

Evaluates a feature flag for a given user context.

```json
{
  "name": "evaluate_flag",
  "arguments": {
    "flag_key": "my-feature-flag",
    "user_key": "user-123",
    "attributes": {
      "email": "user@example.com",
      "country": "US"
    }
  }
}
```

#### 2. Get Feature Flag

Retrieves details about a specific feature flag.

```json
{
  "name": "get_flag",
  "arguments": {
    "flag_key": "my-feature-flag"
  }
}
```

#### 3. List Feature Flags

Lists all available feature flags.

```json
{
  "name": "list_flags",
  "arguments": {}
}
```

#### 4. Get User Segment

Retrieves details about a specific user segment.

```json
{
  "name": "get_segment",
  "arguments": {
    "segment_key": "beta-users"
  }
}
```

#### 5. List User Segments

Lists all available user segments.

```json
{
  "name": "list_segments",
  "arguments": {}
}
```

#### 6. Stream Flag Updates

Stream flag updates in real-time.

```json
{
  "name": "stream_flags",
  "arguments": {
    "flag_keys": ["my-feature-flag", "another-flag"]
  }
}
```

## Development

### Setup Development Environment

```bash
# Install development dependencies with uv
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Run formatting
ruff format .

# Run type checking
mypy src/
```

### Project Structure

```
src/launchdarkly/
├── src/
│   └── mcp_server_launchdarkly/
│       ├── __init__.py      # Package initialization
│       ├── __main__.py      # Entry point
│       └── server.py        # Server implementation
├── tests/                   # Test suite
├── pyproject.toml           # Project configuration
├── uv.lock                  # Dependency lock file
├── README.md                # Documentation
└── Dockerfile               # Container definition
```

## License

MIT
