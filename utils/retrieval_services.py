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
        # existing process_retrieved_nodes logic
        from utils.node_processor import process_retrieved_nodes
        return process_retrieved_nodes(raw_results)

    def initialize_chat_engine(self):
        """Initialize LlamaCloud chat engine"""
        logger.info("Initializing LlamaCloud chat engine")
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

        results = self.service.get_search_results_with_citations(search_response)
        if not results:
            return []

        processed = []
        seen_urls = set()  # Track URLs we've already processed
        node_index = 0

        for citation in results.get('citations', []):
            # Base information for all nodes from this citation
            base_info = {
                'score': citation.get('score', 0) / 100.0,  # Normalize score to 0-1
                'url': citation.get('source_url', ''),
                'metadata': {
                    'file_name': citation.get('file_name', 'Unknown'),
                    'bucket_id': citation.get('bucket_id'),
                    'document_id': citation.get('document_id'),
                }
            }

            # Add text node if there's text content
            if citation.get('text') or citation.get('suggested_text'):
                text_node = {
                    **base_info,
                    'id': f"{citation.get('document_id', 'unknown')}_{node_index}",
                    'type': 'text',
                    'content': citation.get('text', citation.get('suggested_text', '')),
                }

                # Add JSON data to metadata if present
                if citation.get('json'):
                    text_node['metadata']['json_data'] = citation['json']

                processed.append(text_node)
                node_index += 1

            # Add multimodal image node if present (charts/figures)
            if citation.get('multimodalUrl') and citation['multimodalUrl'] not in seen_urls:
                seen_urls.add(citation['multimodalUrl'])
                multimodal_node = {
                    **base_info,
                    'id': f"{citation.get('document_id', 'unknown')}_{node_index}_multimodal",
                    'type': 'image',
                    'content': citation['multimodalUrl'],
                    'metadata': {
                        **base_info['metadata'],
                        'image_type': 'figure',
                        'caption': citation.get('suggested_text', 'Figure from document')[:200]
                    }
                }
                processed.append(multimodal_node)
                node_index += 1

            # Add nodes for each page image
            page_images = citation.get('page_images', [])
            for img_idx, page_image_url in enumerate(page_images):
                if page_image_url not in seen_urls:
                    seen_urls.add(page_image_url)
                    page_node = {
                        **base_info,
                        'id': f"{citation.get('document_id', 'unknown')}_{node_index}_page_{img_idx}",
                        'type': 'image',
                        'content': page_image_url,
                        'metadata': {
                            **base_info['metadata'],
                            'image_type': 'page',
                            'page_index': img_idx,
                            'caption': f"Page view from {citation.get('file_name', 'document')}"
                        }
                    }
                    processed.append(page_node)
                    node_index += 1

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
        # Azure openAI
        try:
            st.session_state.openai_service = OpenAIService()
        except Exception as e:
            raise CriticalInitializationError(f"Failed to initialize openai_service: {str(e)}")

        # Initialize based on configuration
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
