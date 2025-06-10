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

@st.dialog("Demo Explainer")
def explainer_modal():
    #st.html("<span class='big-dialog'></span>")
    st.markdown("""### Board X-Ray

Proof's AI-powered agent provides instant clarity across all Board materials as it...
- Re-surfaces material information
- Untangles complex accountabilities, and
- Surfaces unknown risks.

### Demo Data
The demo data is based on public materials from the Teacher Retirement System of Texas (TRS), including 2 years of original documents from its main Board and key committees (Benefits, Budget, Investment, Governance).

Original documents are supplemented with synthetic risk documents typical of the confidential documents an enterprise Board might examine.

### How to Use the Application
1.  Ask a question using the chat input or a "Common Query" button on the left.
2.  Review the AI's answer in the main chat window, which draws on all historical reference materials.
3.  If you want more detail, see the specific evidence for the response in the "Reference Documents" panel on the right.
4.  If you run into an unexpected response or error, press "Reset Chat" in the top right."""
    )

def handle_settings_pills():
    selection = st.session_state.get('settings_pills', None)

    try:
        if selection == "Reset Chat":
            logger.info("Resetting chat settings")
            if st.session_state.chat_engine:
                st.session_state.chat_engine.reset()
            st.session_state.chat_started = False
            st.session_state.messages = []
            st.session_state.query_nodes = None

            logger.info("Resetting chat")
    except Exception as e:
        logger.exception(f"Failed to reset chat settings: {e}")
        st.warning("Issue resetting chat settings. Try again later.")

    try:
        if selection == "Sync Documents":
            sync_documents()
    except Exception as e:
        logger.exception(f"Failed to sync documents: {e}")
        st.warning("Issue syncing documents. Try again later.")

    try:
        if selection == st.session_state.login_button_label:
            handle_auth()
    except Exception as e:
        logger.exception(f"Failed to handle auth: {e}")
        st.warning("Issue handling login/logout. Refresh browser or again later.")

    try:
        if selection == "Explainer":
            explainer_modal()
    except Exception as e:
        logger.exception(f"Failed to launch explainer: {e}")
        st.warning("Issue launching explainer. Try again later.")



def header():
    col1, col2 = st.columns([2,1])
    with col1:
        st.image("https://i.postimg.cc/vTQrtbS0/horizontal-name-only.jpg", output_format="auto", width=200)


    if st.user.is_logged_in:
        st.session_state.login_button_label = "Logout"
    else:
        st.session_state.login_button_label = "Login"

    with col2:
        st.session_state.settings_pills = None
        st.pills("First",
                 options=["Explainer", "Sync Documents", "Reset Chat", st.session_state.login_button_label],
                 label_visibility="hidden",
                 selection_mode="single",
                 default=None,
                 key="settings_pills",
                 on_change=handle_settings_pills
                 )

