from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, AsyncIterator
from mcp.server.fastmcp import FastMCP

from pipeline import RAGService
from utils.settings import AzureSettings
import logging


# Encapsulates state objects for passing via context
@dataclass
class AppContext:
    settings: AzureSettings
    llama: RAGService

# FastMCP decorated tools accept contexts for managing lifecycle automatically when called by bot
@asynccontextmanager
async def app_lifespan(server: Optional[FastMCP]) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""

    # If authenticated in previous session, graph will hold a valid graph_client
    # If not previously authenticated, graph will hold None and a wrapper will trigger auth before tools are run
    try:
        logging.info("Starting app lifespan")
        settings = AzureSettings()

        rag_service = RAGService()
        logging.info("Settings initialized: in app_lifespan")
    except Exception as e:
        logging.error(f"Error in app_lifespan: {str(e)}")
        raise e

    try:
        yield AppContext(settings=settings, llama=rag_service)
    finally:
        #Add any cleanup if needed
        pass
