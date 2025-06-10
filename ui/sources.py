import logging
import urllib.parse

import streamlit as st

from utils.node_processor import process_retrieved_nodes
from ui.custom_styles import big_dialog_styles
from errors.errors import LlamaOperationFailedError

import logging

logger = logging.getLogger(__name__)

import streamlit as st
import httpx
import base64
import mimetypes

# This is the HTML and JavaScript needed to render a .docx file in the browser.
# It uses the popular 'docx-preview.js' library loaded from a CDN.
DOCX_VIEWER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/docx-preview@0.1.21/dist/docx-preview.js"></script>
    <style>
        body {{ margin: 0; }}
        .docx-wrapper {{ background: #f7f7f7; }} /* Light grey background for contrast */
        .docx-wrapper .docx-content {{ padding: 20px; }}
    </style>
</head>
<body>
    <div id="docx-container" style="width:100%; height:100vh;"></div>
    <script>
        // Data is passed from Streamlit via the 'data' variable
        const base64Data = "{data}";

        // Decode the base64 string to a Uint8Array
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);

        // Create a Blob from the Uint8Array
        const docxBlob = new Blob([byteArray], {{
            type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }});

        // Render the Blob in the container
        const container = document.getElementById('docx-container');
        docx.renderAsync(docxBlob, container)
            .then(x => console.log("docx: render finished."))
            .catch(err => console.error("Error rendering docx:", err));
    </script>
</body>
</html>
"""

import streamlit as st
import httpx
import base64
import mimetypes

@st.dialog("File Preview", width="large")
def file_preview_dialog(file_id: str, file_name: str):
    """
    Generates a fresh URL, downloads file content, and displays it using the
    best available method (embed, JS viewer, text_area, or download).
    """
    st.subheader(file_name)

    try:
        with st.spinner("Generating secure link..."):
            fresh_file_url = st.session_state.llama.get_file_content_url(file_id=file_id)

        with st.spinner("Loading file..."):
            response = httpx.get(fresh_file_url)
            response.raise_for_status()
            file_content_bytes = response.content

        # Guess the MIME type from the file name
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # --- NEW & IMPROVED RENDER/DOWNLOAD LOGIC ---

        # 1. Handle PDFs using a more reliable <embed> tag
        if mime_type == 'application/pdf':
            base64_pdf = base64.b64encode(file_content_bytes).decode('utf-8')
            # The <embed> tag is more robust for PDF rendering in browsers
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'
            st.components.v1.html(pdf_display, height=800)

        # 2. Handle plain text files natively with st.text_area
        elif mime_type == 'text/plain':
            # Decode bytes to a string, replacing any errors
            text_content = file_content_bytes.decode('utf-8', errors='replace')
            st.text_area("File Content", text_content, height=600, disabled=True)

        # 3. Handle simple image types with a direct iframe
        elif mime_type in ['image/jpeg', 'image/png', 'image/gif']:
            base64_image = base64.b64encode(file_content_bytes).decode('utf-8')
            image_html = f'<img src="data:{mime_type};base64,{base64_image}" style="max-width: 100%;">'
            st.components.v1.html(image_html, height=800, scrolling=True)

        # 4. Handle DOCX files with our custom JavaScript component
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            # (Assuming DOCX_VIEWER_HTML is defined in this file as per the previous answer)
            base64_content = base64.b64encode(file_content_bytes).decode('utf-8')
            html_to_render = DOCX_VIEWER_HTML.format(data=base64_content)
            st.components.v1.html(html_to_render, height=800, scrolling=True)

        # 5. For other complex types like PPTX and XLSX, inform the user and offer download
        elif mime_type in [
            'application/vnd.openxmlformats-officedocument.presentationml.presentation', # .pptx
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' # .xlsx
        ]:
            st.info(f"PowerPoint and Excel files cannot be previewed directly. Please download the file to view.")
            st.download_button(
                label=f"Download {file_name}",
                data=file_content_bytes,
                file_name=file_name,
                mime=mime_type
            )
        # 6. Fallback for all other types
        else:
            st.warning(f"This file type ({mime_type}) cannot be previewed.")
            st.download_button(
                label=f"Download {file_name}",
                data=file_content_bytes,
                file_name=file_name,
                mime=mime_type
            )

    except httpx.HTTPStatusError as e:
        st.error(f"Failed to load file. The link may have expired or access was denied. (Status code: {e.response.status_code})")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

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
                    if False:
                        source_doc_url = node.get('url')  # Use .get for safety
                        if source_doc_url:
                            encoded_s3_url = urllib.parse.quote_plus(source_doc_url)
                            google_viewer_url = f"https://docs.google.com/gview?url={encoded_s3_url}&embedded=true"

                            st.link_button("See original file", url=google_viewer_url, type='tertiary', use_container_width=True)
                    else:
                        if st.button("View source", key=f"{node['id']}"):
                            file_preview_dialog(file_id=node['file_id'], file_name=node['name'])
                    st.write(f"Relevancy: {node['score']:.2f}")
        if node_count == 0:
            st.info("No reference of this type found")
    except Exception as e:
        logging.exception(f"Error rendering {source_type} sources: {e}")  # More specific logging
        st.warning(f"Error displaying {source_type} sources.")

@st.dialog("AI Reference Point")
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

    if st.button("AI Reference", use_container_width=True, key=f"{node['id'] }_expand_summary_button"):
        file_dialog_preview(node_element=node)

@st.fragment
def render_image_content(node):
    file_name = "Image"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Image')

    st.image(node['content'], caption=f"{file_name}")
    if st.button("Expanded Image", use_container_width=True, key=f"{node['id']}_expand_image_button"):
        file_dialog_preview(img=node['content'])

@st.cache_data(show_spinner="Retrieving references...")
def run_retrieval(current_user_prompt):
    if current_user_prompt is None:
        raise ValueError("No user prompt provided to run retrieval")

    try:
        query_nodes_from_state = st.session_state.llama.multi_modal_composite_retrieval(
            query_text=current_user_prompt)

        return query_nodes_from_state
    except Exception as e:
        logging.exception(f"RUN_RETRIEVAL: Error running multi-modal retrieval: {e}")
        raise LlamaOperationFailedError


def source_viewer_display():

    big_dialog_styles()
    try:
        if st.session_state.get("current_user_prompt", None) is None:
            return

        prompt = st.session_state.current_user_prompt

        query_nodes_from_state = run_retrieval(prompt)

        processed_nodes_list = process_retrieved_nodes(query_nodes_from_state, prompt)


        # Call the generic renderer directly
        render_sources(
            nodes_list=processed_nodes_list,
            source_type='text',
            title="Text References",
            render_content_func=render_text_content
        )

        st.divider()

        render_sources(
            nodes_list=processed_nodes_list,
            source_type='image',
            title="Image References",
            render_content_func=render_image_content
        )

    except Exception as e:
        logging.exception(f"Error in source_viewer_display: {e}")
        st.error(f"An error occurred while displaying references.")

def source_waiting():
    st.info("Awaiting AI response to begin...")


def sources():


        container_height = 1000 if st.session_state.get('chat_started', False) else 500  # Adjusted for waiting message

        with st.container(border=True, height=container_height):  # Determine height based on state first

            if not st.session_state.get('chat_started', False):
                source_waiting()
            else:
                source_viewer_display()


