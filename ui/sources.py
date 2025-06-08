import logging
import urllib.parse

import streamlit as st

from utils.node_processor import process_retrieved_nodes
from ui.custom_styles import big_dialog_styles
from errors.errors import LlamaOperationFailedError

import logging

logger = logging.getLogger(__name__)

def render_sources(nodes_list, source_type, title, render_content_func):
    """Generic source renderer that handles common logic."""
    st.subheader(title)
    try:
        node_count = 0
        for node in nodes_list:
            if node['type'] == source_type and node.get('score', 0) >= 0.08:
                node_count += 1
                with st.container(border=True):
                    # Call the specific rendering function, passing the whole node
                    render_content_func(node)  # Specific renderer now takes the whole node

                    # Common elements
                    source_doc_url = node.get('url')  # Use .get for safety
                    if source_doc_url:
                        encoded_s3_url = urllib.parse.quote_plus(source_doc_url)
                        google_viewer_url = f"https://docs.google.com/gview?url={encoded_s3_url}&embedded=true"

                        st.link_button("See file", url=google_viewer_url, type='tertiary', use_container_width=True)
                    st.write(f"Relevancy: {node['score']:.2f}")
        if node_count == 0:
            st.info("No sources of this type found")
    except Exception as e:
        logging.exception(f"Error rendering {source_type} sources: {e}")  # More specific logging
        st.warning(f"Error displaying {source_type} sources.")

@st.dialog("Preview")
def file_dialog_preview(node_element=None, img=None):
    st.html("<span class='big-dialog'></span>")

    if node_element:
        st.text_area(
            label="Content",
            value=node_element['content'],
            height=600,  # Adjust height as needed, or it will auto-size
            disabled=False,  # Makes it read-only
            label_visibility="collapsed"  # Hides the "Content" label above the text area
        )

    else:
        st.image(img, width=1000)

def text_preview_expander(node):
    file_name = "Source"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Source')

    expander = st.expander(f"File: {file_name}")
    #expander.write(node['content'])
    expander.text_area(
        label="Content",
        value=node['content'],
        height=200,  # Adjust height as needed, or it will auto-size
        disabled=False,  # Makes it read-only
        label_visibility="collapsed"  # Hides the "Content" label above the text area
    )

@st.fragment
def render_text_content(node):

    text_preview_expander(node)

    if st.button("Expanded Summary", use_container_width=True, key=f"{node['id'] }_expand_summary_button"):
        file_dialog_preview(node_element=node)

@st.fragment
def render_image_content(node):
    file_name = "Image"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Image')

    st.image(node['content'], caption=f"{file_name}")
    if st.button("Expanded Image", use_container_width=True, key=f"{node['id']}_expand_image_button"):
        file_dialog_preview(img=node['content'])

@st.cache_data
def run_retrieval(current_user_prompt):
    if current_user_prompt is None:
        raise ValueError("No user prompt provided to source retrieval")

    try:
        query_nodes_from_state = st.session_state.llama.multi_modal_composite_retrieval(
            query_text=current_user_prompt)
    except Exception as e:
        logging.exception(f"RUN_RETRIEVAL: Error running multi-modal retrieval: {e}")
        raise LlamaOperationFailedError

    try:
        # Assuming llama_retrieval is defined and accessible
        processed_nodes_list = process_retrieved_nodes(query_nodes_from_state)

        return processed_nodes_list

    except Exception as e:
        logger.exception(f"Error processing {current_user_prompt}: {e}")
        raise


def source_viewer_display():

    try:
        if st.session_state.get("current_user_prompt", None) is None:
            return

        processed_nodes_list = run_retrieval(st.session_state.current_user_prompt)

        # Call the generic renderer directly
        render_sources(
            nodes_list=processed_nodes_list,
            source_type='text',
            title="Text Sources",
            render_content_func=render_text_content
        )

        st.divider()

        render_sources(
            nodes_list=processed_nodes_list,
            source_type='image',
            title="Image Sources",
            render_content_func=render_image_content
        )

    except Exception as e:
        logging.exception(f"Error in source_viewer_display: {e}")
        st.error(f"An error occurred while displaying sources: {e}")

def source_waiting():
    st.info("Awaiting AI response to begin...")


def sources():
    container_height = 1000 if st.session_state.get('chat_started', False) else 500  # Adjusted for waiting message
    big_dialog_styles()
    with st.container(border=True, height=container_height):  # Determine height based on state first

        st.header('Source Documents')
        if not st.session_state.get('chat_started', False):
            source_waiting()
        else:
            source_viewer_display()


