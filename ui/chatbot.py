from utils.llama_chatbot import llama_chatbot
from .indices import *
import logging

#TODO: Include history as context
#TODO: Save history
#TODO: Limit history

logger = logging.getLogger(__name__)

@st.fragment
def chat_windows():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False

    with st.container(height=500):
        st.session_state.chatbot_info_placeholder = chatbot_info_placeholder = st.empty()

        if not st.session_state.chat_started:
            chatbot_info_placeholder.info("Ask a question about your files")
            logger.info("Chat not started")

        else:
            logger.info("Chat has started")
            # Display chat messages from history on app rerun
            chatbot_info_placeholder.empty()
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        user_placeholder = st.empty()

        ai_placeholder = st.empty()

    common_prompt_from_state = st.session_state.get('common_prompt', None)

    default_chat_prompt = st.session_state.get('common_prompt', None) or "Ask a question"

    user_typed_prompt = st.chat_input(
        default_chat_prompt,
        disabled=not st.session_state.get('llama', None)
    )

    effective_prompt = user_typed_prompt or common_prompt_from_state
    # If effective_prompt is truthy and now prompt is set to that
    if prompt := effective_prompt:
        st.session_state.chatbot_info_placeholder.empty()
        st.session_state.chat_started = True
        st.session_state.common_prompt = None #Reinit common prompt
        st.session_state.current_user_prompt = prompt

        with user_placeholder:
            st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        #===================
        #Separate retriever
        #===================

        with ai_placeholder:
            with st.chat_message("assistant"):

                response = st.write_stream(st.session_state.chat_engine.stream_chat(prompt).response_gen)
                #response = "Hi there testing"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()




def chat_display():
    try:

        if not st.session_state.get('llama', False):
            st.warning("Waiting for chatbot to load...")
            return

        if 'chat_engine' not in st.session_state:
            try:
                st.session_state.chat_engine = llama_chatbot()
            except Exception as e:
                logging.exception(f"CHATBOT: {e}")
                st.warning("There was a problem connecting to the chat engine. Please try again later.")
                return

        chat_windows()
    except Exception as e:
        st.error(e)
        logging.exception(e)
        st.warning(f"An error occurred with chat. Please try again later.")