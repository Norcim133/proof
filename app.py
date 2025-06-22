#Chat related
from pipeline import OpenAIService
import logging
from errors import *
from ui.app_body import app_body
from ui.custom_styles import *
import os
from dotenv import load_dotenv

from utils.retrieval_services import set_retrieval_service

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

#TODO: Refactor retrievalservices to other file
#TODO: Fix duplicate nodes
#TODO: Create admin mode (files upload)


#@st.cache_resource
def init_rag_service():

    # Set default retriever
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