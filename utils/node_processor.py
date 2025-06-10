from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core.schema import ImageNode, TextNode, NodeWithScore, MetadataMode
import logging
from PIL import Image
import os
import json
import streamlit as st

import logging

logger = logging.getLogger(__name__)

#@st.cache_data(show_spinner="Formatting response...")
def process_retrieved_nodes(_nodes_with_scores, prompt):
    try:
        with st.spinner("Formatting response..."):
            if _nodes_with_scores is None:
                raise ValueError("LLAMA_RETRIEVAL: _nodes_with_scores cannot be None")
            nodes = []
            for node_with_score in _nodes_with_scores:
                node = node_with_score.node
                score = node_with_score.score
                if isinstance(node, ImageNode):
                    image_source = node.resolve_image()
                    content = Image.open(image_source)
                    node_type = "image"
                else:
                    content = node.get_text()
                    node_type = "text"
                metadata = node.metadata

                file_id = node.metadata.get('file_id', None)
                logger.info(f"PROCESS_RETRIEVED_NODES: original file_id {file_id}")

                if file_id is None:
                    file_name = node.metadata.get('file_name', None)
                    file_id = st.session_state.llama.file_id_name_dict[file_name]
                    logger.info(f"PROCESS_RETRIEVED_NODES: alternate approach yields file_id {file_id}")
                file_url = st.session_state.llama.get_file_content_url(file_id=file_id)
                node_dict = {'metadata': metadata,
                             'type': node_type,
                             'content': content,
                             'url': file_url,
                             'score': score,
                             'id': node.node_id
                            }
                nodes.append(node_dict)
            return nodes
    except Exception as e:
        raise Exception(f"LLAMA_RETRIEVAL error processing retrieval nodes: {e}")
