import logging
import time

import streamlit as st

from errors import LlamaOperationFailedError

def indices_list_view():
    """Display list of indices/buckets"""
    st.subheader("Source IDs")

    try:
        storage_items = get_storage_items()

        if not storage_items:
            st.info("No sources found.")
        else:
            for key, value in storage_items.items():
                st.write(f"**{key}**: {value}")

    except Exception as e:
        st.warning(f"API call to fetch sources failed: {e}")
        logging.error(f"API call to fetch sources failed: {e}")


def get_storage_items():
    """Get storage items (indices or buckets) from the retrieval service"""
    retrieval_service = st.session_state.get('retrieval_service')
    if not retrieval_service:
        return {}

    names = retrieval_service.list_storage_names()
    # Convert to dict format that the UI expects (name: id)
    return {name: retrieval_service.get_storage_id(name) for name in names}

@st.fragment
def set_index_state_with_selector():
    st.session_state.current_index_name = st.session_state.get('indices_selector', None)

@st.fragment
def indices_selector():
    """Selector for indices/buckets"""
    storage_names = st.session_state.get('retrieval_service', {}).list_storage_names() or []

    st.selectbox(
        "Manage a Source",
        options=storage_names,
        key="indices_selector",
        on_change=set_index_state_with_selector,
        index=next((i for i, name in enumerate(storage_names) if name == st.session_state.get('current_index_name')),
                   None)
    )

@st.fragment
def rename_index():
    """Rename the current index/bucket"""
    current_index_name = st.session_state.get('current_index_name', None)
    new_name = st.session_state.get("rename_dialog_new_name_input", None)

    if not current_index_name or not new_name:
        return False

    try:
        retrieval_service = st.session_state.get('retrieval_service')
        if not retrieval_service:
            raise Exception("Retrieval service not initialized")

        retrieval_service.rename_storage(current_index_name, new_name)
        st.session_state['current_index_name'] = new_name
        st.session_state.refresh_state = True
        return True

    except Exception as e:
        st.error(f"Error renaming: {e}")
        return False


@st.dialog("Rename Source")
def index_rename_dialog():
    st.session_state['show_rename_index_dialog'] = False
    current_index_name = st.session_state.get('current_index_name', None)

    if current_index_name is None:
        st.warning("No source selected.")
    else:
        st.write(f"Changing name for source: {current_index_name}")
        st.text_input(
            "New name:",
            key="rename_dialog_new_name_input",
            placeholder="Enter new name"
        )

        if st.button("Save Rename", key="rename_dialog_save_btn"):
            if rename_index():
                st.success(
                    f"Successfully renamed '{current_index_name}' to '{st.session_state.get('rename_dialog_new_name_input', '')}'.")
            else:
                st.error(f"Failed to rename '{current_index_name}'.")
            time.sleep(2)
            st.rerun()

def rename_index_component():
    """Component for renaming indices/buckets"""

    st.button(
        "Rename Source",
        on_click=index_rename_dialog,
        disabled=not st.session_state.get('indices_selector', False)
    )

    if st.session_state.get("show_rename_index_dialog", False):
        index_rename_dialog()


def indices_edit():
    """Edit controls for indices/buckets"""
    col1, col2 = st.columns(2)
    with col1:
        rename_index_component()

    with col2:
        st.button("Delete Source")

@st.fragment
def indices():
    """Main function for the indices/buckets sidebar component"""
    try:
        if "current_index_name" not in st.session_state:
            st.session_state['current_index_name'] = None

        if not st.user.is_logged_in:
            st.info("Please log in to get started.")
        elif st.session_state.get('retrieval_service', None) is None:
            st.info("Please wait for chatbot to initialize")
        else:
            st.subheader("Document Sources")
            st.text("")
            indices_selector()

        st.text("")
        st.text("")

        indices_edit()

    except Exception as e:
        st.error(e)