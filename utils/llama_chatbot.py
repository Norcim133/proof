import streamlit as st
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI
import logging

logger = logging.getLogger(__name__)

def llama_chatbot():
    try:
        if st.user.is_logged_in:
            api_key = st.secrets["OPENAI_API_KEY"]
        else:
            return None

        llm = OpenAI(model="gpt-3.5-turbo", api_key=api_key)

        memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

        chat_engine = CondensePlusContextChatEngine.from_defaults(
            retriever=st.session_state.llama.composite_retriever,
            chat_mode="condense_plus_context",
            memory=memory,
            llm=llm,
            context_prompt=(
                "You are a chatbot in the role of expert on the documents stored by the company."
                "Your only focus is on understanding those documents at a factual level."
                "The content for those documents is here:\n"
                "{context_str}"
                "\nInstruction: Use the previous chat history, or the context above, to interact and answer user questions about the documents."
                "IMPORTANT: You do not return technical details like file_ids or pipeline names as you only deal in content, inference, and filenames."
                "IMPORTANT: You do not bring other knowledge to responses beyond the document and chat context."
                "IMPORTANT: You do respond with general answers on theory or concepts or guesses outside of these documents."
                "If a question asks you to speculate beyond the scope discussed above, simply say 'Answers to that question are outside the scope of my function'."
            ),
            verbose=False,
        )

        return chat_engine
    except Exception as e:
        logger.error(e)
        return None
