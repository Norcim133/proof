#Chat related
from pipeline import OpenAIService
import logging
from errors import *
from ui.app_body import app_body
from ui.custom_styles import *
import os
from pipeline import GroundService
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

#TODO: Refactor to combine chat prompts from service and llamabot
#TODO: Fix duplicate nodes
#TODO: Create admin mode (files upload)

# Abstract base class for retrieval services
class RetrievalService(ABC):
    @abstractmethod
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve documents/nodes based on query"""
        pass

    @abstractmethod
    def process_results(self, raw_results: Any) -> List[Dict[str, Any]]:
        """Process raw results into standardized format"""
        pass


# Concrete implementations
class LlamaCloudRetrieval(RetrievalService):
    def __init__(self, llama_client):
        self.client = llama_client
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


class GroundXRetrieval(RetrievalService):
    def __init__(self, groundx_service):
        self.service = groundx_service
        self.cached_response = None

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


def set_retrieval_service():
    """Get or create the retrieval service"""
    try:
        if 'retrieval_service' not in st.session_state:
            # Initialize based on your configuration
            if st.session_state.get('use_groundx', True):
                from pipeline.groundx_service import GroundService
                groundx = GroundService()
                st.session_state.retrieval_service = GroundXRetrieval(groundx)
            else:
                # Fallback to LlamaCloud
                from pipeline import RAGService
                rag_service = RAGService(llama_cloud_api_key=st.secrets['LLAMA_CLOUD_API_KEY'])
                st.session_state.retrieval_service = LlamaCloudRetrieval(rag_service)
    except Exception as e:
        raise CriticalInitializationError("Could not initialize retrieval service") from e

# st.cache_resource
def init_rag_service():

    # Set default retreivers
    if 'use_groundx' not in st.session_state:
        st.session_state['use_groundx'] = False

    set_retrieval_service()

    #Direct openAI
    try:
        openai_api_key_from_secrets = st.secrets["OPENAI_API_KEY"]
        if openai_api_key_from_secrets:
            os.environ["OPENAI_API_KEY"] = openai_api_key_from_secrets

    except Exception as e:
        raise CriticalInitializationError(f"Failed to initialize rag_service: {str(e)}")

    #Azure openAI
    try:
        st.session_state.openai_service = OpenAIService()
    except Exception as e:
        raise CriticalInitializationError(f"Failed to initialize openai_service: {str(e)}")

    st.session_state.refresh_state = False
    st.rerun()

def set_log_level():
    # TODO: To change logging, change here and in config.toml
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum logging level to INFO
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Optional: customize log format
        datefmt='%Y-%m-%d %H:%M:%S'  # Optional: customize date format
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

def main():
    #Refresh state used for changes to llamacloud objects org, project, indices
    #Set to true for first run of app

    #Boilerplate config for all streamlit apps
    st.set_page_config(page_title="Proof",
                       page_icon="assets/favicon_NB.png",
                       layout="wide",
                       menu_items=None,
                       initial_sidebar_state="expanded",
                       )

    set_log_level()

    #State that will trigger reset of the llamacloud client and chat engine
    if 'refresh_state' not in st.session_state:
        st.session_state['refresh_state'] = True


    #HTML for control over streamlit components
    alternate_chat_side_style()
    container_shadow_styles()

    try:
        if not st.user.is_logged_in:

            app_body()

            st.stop()

        else:
            app_body()

            #Init or reset llamacloud and chat engine instances (incl llamacloud and openai calls)
            if st.session_state.refresh_state:
                init_rag_service()

    except CriticalInitializationError as e:
        st.warning(f"The controller could not be initialized\n\n Error code: {e} \n\nPlease try again later.")


if __name__ == "__main__":
    main()