import streamlit as st
import logging

logger = logging.getLogger(__name__)

def sync_documents():
    logger.info("Syncing documents")
    rag = st.session_state.get('llama', None)
    if rag:
        rag.run_retriever_sync()

def handle_auth():
    if st.user.is_logged_in:
        st.logout()
    else:
        st.login()

def handle_settings_pills():
    try:
        selection = st.session_state.get('settings_pills', None)

        if selection == "Reset Chat":
            logger.info("Resetting chat settings")
            if st.session_state.chat_engine:
                st.session_state.chat_engine.reset()
            st.session_state.chat_started = False
            st.session_state.messages = []
            st.session_state.query_nodes = None

            logger.info("Resetting chat")

        elif selection == "Sync Documents":
            sync_documents()

        elif selection == st.session_state.login_button_label:
            handle_auth()

        else:
            pass
    except Exception as e:
        st.warning("Issue resetting chat settings")
        logger.exception(e)

def header():
    col1, col2 = st.columns([3,1])
    with col1:
        st.image("https://i.postimg.cc/vTQrtbS0/horizontal-name-only.jpg", output_format="auto", width=200)


    if st.user.is_logged_in:
        st.session_state.login_button_label = "Logout"
    else:
        st.session_state.login_button_label = "Login"

    with col2:
        st.session_state.settings_pills = None
        st.pills("First",
                 options=["Sync Documents", "Reset Chat", st.session_state.login_button_label],
                 label_visibility="hidden",
                 selection_mode="single",
                 default=None,
                 key="settings_pills",
                 on_change=handle_settings_pills
                 )

