from . import server
from .client import client
import asyncio


def main():
    """Main entry point for the package."""
    asyncio.run(server.main())


# Optionally expose other important items at package level
__all__ = ["main", "server", "client"]
