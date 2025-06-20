import os
import tempfile
from typing import Optional, List, Dict
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import logging

logger = logging.getLogger(__name__)


class AzureRAGService:
    """Azure-based replacement for RAGService"""

    def __init__(self):
        # Initialize Azure clients
        self.blob_service = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )

        self.search_client = SearchClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            index_name="board-documents",  # We'll create this index
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
        )

        self.doc_intelligence = DocumentAnalysisClient(
            endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
        )

        # Ensure container exists
        self.container_name = "board-documents"
        self._ensure_container()

    def _ensure_container(self):
        """Create blob container if it doesn't exist"""
        try:
            container_client = self.blob_service.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except Exception as e:
            logger.error(f"Error ensuring container: {e}")

    async def process_document(self, file_path: str, file_name: str) -> Dict:
        """
        Process a document through the Azure pipeline
        Similar to your upload_file method
        """
        logger.info(f"Processing document: {file_name}")

        # 1. Upload to blob storage
        blob_url = await self._upload_to_blob(file_path, file_name)

        # 2. Process with Document Intelligence
        doc_analysis = await self._analyze_document(file_path)

        # 3. Index in AI Search
        search_results = await self._index_document(file_name, doc_analysis)

        return {
            "status": "success",
            "blob_url": blob_url,
            "pages_processed": len(doc_analysis.pages),
            "indexed_chunks": search_results
        }

    async def _upload_to_blob(self, file_path: str, file_name: str) -> str:
        """Upload file to blob storage"""
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=file_name
        )

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        return blob_client.url

    async def _analyze_document(self, file_path: str):
        """Analyze document with Document Intelligence"""
        with open(file_path, "rb") as f:
            poller = self.doc_intelligence.begin_analyze_document(
                "prebuilt-layout",
                f
            )
            return poller.result()

    async def _index_document(self, file_name: str, doc_analysis) -> List[Dict]:
        """Index document pages in AI Search"""
        documents = []

        for page_num, page in enumerate(doc_analysis.pages):
            # Extract text from page
            page_text = ""
            for line in page.lines:
                page_text += line.content + "\n"

            # Create search document
            doc = {
                "id": f"{file_name}_page_{page_num + 1}",
                "content": page_text,
                "sourcefile": file_name,
                "sourcepage": f"page-{page_num + 1}",
                "page_number": page_num + 1
            }
            documents.append(doc)

        # Upload to search index (we'll create the index later)
        # For now, just return what we would index
        logger.info(f"Would index {len(documents)} pages")
        return documents

    def search_index(self, query: str) -> str:
        """Search documents - mirrors your search_index method"""
        try:
            results = self.search_client.search(
                search_text=query,
                select=["content", "sourcefile", "sourcepage"],
                top=5
            )

            response_text = f"Search results for '{query}':\n\n"
            for i, result in enumerate(results):
                response_text += f"Result {i + 1} (Score: {result['@search.score']:.3f}):\n"
                response_text += f"Source: {result['sourcefile']}\n"
                response_text += f"Page: {result['sourcepage']}\n"
                response_text += f"Content: {result['content'][:200]}...\n\n"

            return response_text
        except Exception as e:
            return f"Search error: {e}"