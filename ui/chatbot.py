from utils.llama_chatbot import llama_chatbot
from .indices import *
import logging

#TODO: Include history as context
#TODO: Save history
#TODO: Limit history

logger = logging.getLogger(__name__)

def get_response_stream(prompt, context, chat_history):
    return st.session_state.openai_service.stream_completion(prompt, context, chat_history)

def stream_and_clean_latex(stream_generator):
    """Required to prevent poor formatting when markdown thinks there is an equation"""
    for chunk in stream_generator:
        cleaned_chunk = chunk.replace('$', '\\$')
        yield cleaned_chunk

@st.fragment
def chat_windows():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False

    with st.container(height=st.session_state.get('window_height', 600), key="shadow_chat"):
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


    placeholder_text = st.session_state.get('common_prompt', None) or "Ask a question"

    user_typed_prompt = st.chat_input(
        placeholder_text,
        disabled=not st.session_state.get('retrieval_service', None)
    )

    effective_prompt = user_typed_prompt or common_prompt_from_state

    # If effective_prompt is truthy and now prompt is set to that
    if prompt := effective_prompt:
        st.session_state.chatbot_info_placeholder.empty()
        st.session_state.chat_started = True
        st.session_state.common_prompt = None #Reinit common prompt
        st.session_state.current_user_prompt = prompt #Used to align prompt in references query

        with user_placeholder:
            st.chat_message("user").markdown(prompt)

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        #===================
        #Separate retriever
        #===================

        with ai_placeholder:
            if not st.session_state.get('use_groundx', True):
                with st.chat_message("assistant"):

                    # Get the original, raw generator from the chat engine.
                    raw_response_generator = st.session_state.chat_engine.stream_chat(prompt).response_gen

                    # Create an instance of your new cleaning generator.
                    cleaned_response_generator = stream_and_clean_latex(raw_response_generator)

                    # Pass the CLEANED generator to st.write_stream.
                    # The 'response' variable will now hold the full, already cleaned string after the stream is done.
                    response = st.write_stream(cleaned_response_generator)
            else:
                # Call to groundx context
                rag_response = st.session_state.retrieval_service.service.search_content(prompt)

                if hasattr(st.session_state.retrieval_service, 'set_cached_response'):
                    st.session_state.retrieval_service.set_cached_response(rag_response)

                # Get groundx llm formatting of response
                context = st.session_state.retrieval_service.service.get_search_context(rag_response)

                # Call to LLM
                with st.chat_message("assistant"):
                    stream = get_response_stream(prompt, context, st.session_state.messages)
                    response = st.write_stream(stream)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


def chat_display():
    try:

        if not st.session_state.get('retrieval_service', False):
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