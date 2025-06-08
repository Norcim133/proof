import streamlit as st

from ui.chatbot import chat_display
from ui.common_queries import common_queries
from ui.indices import indices
from ui.sources import sources
from ui.header import header


def st_side_bar():
    with st.sidebar:

        indices()

        st.divider()

        common_queries()
        #dashboard()


def app_body():

    header()

    st.logo(
        "assets/horizontal_NB.png",
        size="medium",
        icon_image="assets/square_NB.png"
    )

    st_side_bar()

    c1, c2 = st.columns([2,1], vertical_alignment="top", gap="large")
    with c1:
        st.header("Board Chat")
        chat_display()

    with c2:
        st.header('Source Documents')
        sources()
        #file_manager()
