import logging

from typing import List, Dict, Any, Optional
from errors import *

import streamlit as st

logger = logging.getLogger(__name__)


def render_sources(nodes_list: List[Dict], source_type: str, title: str, render_func):
    """Generic source renderer that handles common logic"""
    st.subheader(title)

    try:
        filtered_nodes = [
            node for node in nodes_list
            if node['type'] == source_type and node.get('score', 0) >= 0.08
        ]

        if not filtered_nodes:
            st.info(f"No {source_type} references found")
            return

        for idx, node in enumerate(filtered_nodes):
            with st.container(border=True, key=f"shadow_node_{source_type}_{idx}"):
                render_func(node)
                render_common_elements(node)

    except Exception as e:
        logger.exception(f"Error rendering {source_type} sources: {e}")
        st.warning(f"Error displaying {source_type} sources.")


def render_common_elements(node: Dict):
    """Render common elements for all node types"""
    source_url = node.get('url')
    if source_url:
        st.link_button(
            "Open original file",
            url=source_url,
            type='tertiary',
            use_container_width=True
        )

    st.write(f"Relevancy: {node['score']:.2f}")


def text_preview_expander(node: Dict):
    """Show text preview in expander"""
    file_name = node.get('metadata', {}).get('file_name', 'Source')

    with st.expander(f"File: {file_name}"):
        st.text_area(
            label="Content",
            value=node['content'],
            height=200,
            disabled=False,
            label_visibility="collapsed"
        )


@st.dialog("AI Reference Point", width='large')
def file_dialog_preview(node_element: Optional[Dict] = None, img: Optional[Any] = None):
    """Show expanded preview in dialog"""
    if node_element:
        st.text_area(
            label="Content",
            value=node_element['content'],
            height=800,
            disabled=False,
            label_visibility="collapsed"
        )
    elif img:
        st.image(img, width=700)


@st.fragment
def render_text_content(node: Dict):
    """Render text content"""
    text_preview_expander(node)

    if st.button("AI Reference", use_container_width=True, key=f"{node['id']}_expand_summary"):
        file_dialog_preview(node_element=node)


@st.fragment
def render_image_content(node: Dict):
    """Render image content"""
    file_name = node.get('metadata', {}).get('file_name', 'Image')
    st.image(node['content'], caption=file_name)

    if st.button("Expanded Image", use_container_width=True, key=f"{node['id']}_expand_image"):
        file_dialog_preview(img=node['content'])



def display_sources():
    """Main function to display sources"""
    # Check if we have a prompt
    if not st.session_state.get("current_user_prompt"):
        st.info("Awaiting AI response to begin...")
        return

    # Get the retrieval service
    if not st.session_state.get('retrieval_service', None):
        st.error("No retrieval service configured")
        return


    try:
        with st.spinner("Retrieving references..."):

            nodes = st.session_state.retrieval_service.retrieve(st.session_state.current_user_prompt)

        # Render images
        render_sources(
            nodes_list=nodes,
            source_type='image',
            title="Image References",
            render_func=render_image_content
        )

        st.divider()

        # Render text
        render_sources(
            nodes_list=nodes,
            source_type='text',
            title="Text References",
            render_func=render_text_content
        )

    except Exception as e:
        logger.exception(f"Error displaying sources: {e}")
        st.error("An error occurred while displaying references.")


# Streamlit fragment for the sources section
@st.fragment
def sources():
    """Main entry point for sources display"""
    display_sources()