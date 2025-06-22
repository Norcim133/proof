import streamlit as st
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI
from utils.system_prompt import SYSTEM_PROMPT
from llama_index.core import PromptTemplate
import logging

logger = logging.getLogger(__name__)

def llama_chatbot():
    try:
        if st.user.is_logged_in:
            logger.info("Fetching openai_api_key for llama_chatbot")
            api_key = st.secrets["OPENAI_API_KEY"]
        else:
            return None

        llm = OpenAI(model="o4-mini-2025-04-16", api_key=api_key)

        memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

        context_prompt_template = PromptTemplate(
            "\n\nRelevant documents and context are here:\n{context_str}\n\n" + SYSTEM_PROMPT
        )

        chat_engine = CondensePlusContextChatEngine.from_defaults(
            retriever=st.session_state.llama.composite_retriever,
            chat_mode="condense_plus_context",
            memory=memory,
            llm=llm,
            context_prompt=context_prompt_template,
            verbose=False,
        )
        logger.info("Returning chat_engine")
        return chat_engine
    except Exception as e:
        logger.error(e)
        return None
