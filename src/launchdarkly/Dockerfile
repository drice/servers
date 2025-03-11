FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install uv and use it to install dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --no-cache-dir .

# Set environment variables
ENV LAUNCHDARKLY_SDK_KEY=""
ENV LAUNCHDARKLY_ENVIRONMENT="production"

# Run the server
CMD ["python", "-m", "mcp_server_launchdarkly"]
