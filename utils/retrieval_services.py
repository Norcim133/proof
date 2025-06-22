from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
from dotenv import load_dotenv
import os
import streamlit as st
from errors import CriticalInitializationError
from pipeline import OpenAIService

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class RetrievalService(ABC):
    @abstractmethod
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve documents/nodes based on query"""
        pass

    @abstractmethod
    def process_results(self, raw_results: Any) -> List[Dict[str, Any]]:
        """Process raw results into standardized format"""
        pass

    @abstractmethod
    def get_chat_response_stream(self, prompt: str, messages: List[Dict] = None):
        """Get streaming chat response - each service handles its own way"""
        pass


class LlamaCloudRetrieval(RetrievalService):
    def __init__(self, llama_client):
        self.client = llama_client
        self.chat_engine = None
        st.session_state.llama = self.client

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        try:
            raw_results = self.client.multi_modal_composite_retrieval(query_text=query)
            return self.process_results(raw_results)
        except Exception as e:
            logger.exception(f"LlamaCloud retrieval error: {e}")
            raise

    def process_results(self, raw_results: Any) -> List[Dict[str, Any]]:
        # Your existing process_retrieved_nodes logic
        from utils.node_processor import process_retrieved_nodes
        return process_retrieved_nodes(raw_results)

    def initialize_chat_engine(self):
        """Initialize LlamaCloud chat engine"""
        if not self.chat_engine:
            from utils.llama_chatbot import llama_chatbot
            self.chat_engine = llama_chatbot()
        return self.chat_engine

    def get_chat_response_stream(self, prompt: str, messages: List[Dict] = None):
        """Get streaming response from LlamaCloud"""
        if not self.chat_engine:
            self.initialize_chat_engine()

        if not self.chat_engine:
            yield "Chat engine not initialized"
            return

        raw_response_generator = self.chat_engine.stream_chat(prompt).response_gen

        # Apply latex cleaning
        for chunk in raw_response_generator:
            cleaned_chunk = chunk.replace('$', '\$')
            yield cleaned_chunk


class GroundXRetrieval(RetrievalService):
    def __init__(self, groundx_service):
        self.service = groundx_service
        self.cached_response = None
        self.openai_service = None

    def set_cached_response(self, search_response):
        """Store a response from chatbot to avoid new API calls"""
        self.cached_response = search_response

    def has_cached_response(self) -> bool:
        """Check if we have a cached response available"""
        return self.cached_response is not None

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Use cached response if available, otherwise make API call"""
        if self.cached_response:
            # Use the cached response - no API call
            response = self.cached_response
            # Clear it after use if you want one-time use
            self.cached_response = None
        else:
            # Fallback - make API call if no cached response
            logger.warning("No cached GroundX response, making new API call")
            response = self.service.search_content(query)

        return self.process_results(response)

    def process_results(self, search_response) -> List[Dict[str, Any]]:
        """Convert GroundX SearchResponse to standardized format"""
        if not search_response:
            return []

        # Extract citations from the response
        results = self.service.get_search_results_with_citations(search_response)
        if not results:
            return []

        processed = []

        for idx, citation in enumerate(results.get('citations', [])):
            # Generate a unique ID combining document ID and index
            unique_id = f"{citation.get('document_id', 'unknown')}_{idx}"

            node = {
                'id': unique_id,  # Use the unique ID
                'document_id': citation.get('document_id', ''),  # Keep original if needed
                'type': 'text',
                'content': citation.get('text', citation.get('suggested_text', '')),
                'score': citation.get('score', 0) / 100.0,  # Normalize score to 0-1
                'url': citation.get('source_url', ''),
                'metadata': {
                    'file_name': citation.get('file_name', 'Unknown'),
                    'bucket_id': citation.get('bucket_id'),
                    'page_images': citation.get('page_images', [])
                }
            }

            # If there are page images, add them as image nodes
            if citation.get('page_images'):
                node['type'] = 'image' if not node['content'] else 'text'
                if node['type'] == 'image' and citation['page_images']:
                    node['content'] = citation['page_images'][0]  # First image

            processed.append(node)

        return processed

    def set_openai_service(self, openai_service):
        """Set the OpenAI service for chat responses"""
        self.openai_service = openai_service

    def get_chat_response_stream(self, prompt: str, messages: List[Dict] = None):
        """Get streaming response from GroundX + OpenAI"""
        # Make the search
        rag_response = self.service.search_content(prompt)

        # Cache it for sources
        self.set_cached_response(rag_response)

        # Get context
        context = self.service.get_search_context(rag_response)

        if not context:
            yield "I couldn't find relevant information in the documents to answer your question."
            return

        # Stream from OpenAI
        if not self.openai_service:
            yield "OpenAI service not configured"
            return

        for chunk in self.openai_service.stream_completion(prompt, context, messages):
            yield chunk


def set_retrieval_service():
    """Get or create the retrieval service"""

    try:
        if 'retrieval_service' not in st.session_state:
            # Azure openAI
            try:
                st.session_state.openai_service = OpenAIService()
            except Exception as e:
                raise CriticalInitializationError(f"Failed to initialize openai_service: {str(e)}")

            # Initialize based on your configuration
            if st.session_state.get('use_groundx', True):
                from pipeline.groundx_service import GroundService
                groundx = GroundService()
                retrieval = GroundXRetrieval(groundx)
                retrieval.set_openai_service(st.session_state.openai_service)
                st.session_state.retrieval_service = retrieval
            else:
                # Direct openAI
                try:
                    openai_api_key_from_secrets = st.secrets["OPENAI_API_KEY"]
                    if openai_api_key_from_secrets:
                        os.environ["OPENAI_API_KEY"] = openai_api_key_from_secrets
                except Exception as e:
                    raise CriticalInitializationError(f"Failed to initialize rag_service: {str(e)}")

                # Fallback to LlamaCloud
                from pipeline import RAGService
                rag_service = RAGService(llama_cloud_api_key=st.secrets['LLAMA_CLOUD_API_KEY'])
                st.session_state.retrieval_service = LlamaCloudRetrieval(rag_service)
    except Exception as e:
        raise CriticalInitializationError("Could not initialize retrieval service") from e
